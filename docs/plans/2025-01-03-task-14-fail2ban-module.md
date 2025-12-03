# Task 14.0: Fail2ban Module Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create Fail2ban brute force protection module with smart auto-detect for installed services.

**Architecture:** Single `modules/fail2ban.py` with smart jail detection based on installed services. Auto-enables sshd, nginx, postfix jails as needed. Configurable ban settings.

**Tech Stack:** Fail2ban, fail2ban-client CLI, existing shell.py utilities, Rich UI components

---

## Sub-tasks Overview

| Sub-task | Description | Commit |
|----------|-------------|--------|
| 14.1 | Create fail2ban.py with show_menu() | Yes |
| 14.2 | Add install_fail2ban() with auto-detect | Yes |
| 14.3 | Add show_status() and view_jail_status() | Yes |
| 14.4 | Add list_banned_ips() | Yes |
| 14.5 | Add unban_ip() and ban_ip() | Yes |
| 14.6 | Add configure_settings() | Yes |
| 14.7 | Add helpers and update __init__.py | Yes |

**Total: 7 sub-tasks, 7 commits**

---

## Task 14.1: Create fail2ban.py with show_menu()

**Files:**
- Create: `modules/fail2ban.py`

**Step 1: Create Fail2ban module with menu**

```python
"""Fail2ban (brute force protection) module for vexo-cli."""

import os

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_success,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import show_submenu, confirm_action, text_input, select_from_list
from utils.shell import (
    run_command,
    run_command_with_progress,
    run_command_realtime,
    is_installed,
    is_service_running,
    service_control,
    require_root,
)


# Default Fail2ban settings
DEFAULT_BANTIME = "1h"
DEFAULT_FINDTIME = "10m"
DEFAULT_MAXRETRY = "5"


def show_menu():
    """
    Display the Fail2ban submenu and handle user selection.
    """
    while True:
        clear_screen()
        show_header()
        
        # Show Fail2ban status
        if is_service_running("fail2ban"):
            status = "[green]Running[/green]"
        elif is_installed("fail2ban"):
            status = "[red]Stopped[/red]"
        else:
            status = "[dim]Not installed[/dim]"
        
        console.print(f"[dim]Fail2ban: {status}[/dim]")
        console.print()
        
        choice = show_submenu(
            title="Fail2ban (Brute Force Protection)",
            options=[
                ("install", "1. Install Fail2ban"),
                ("status", "2. Show Status"),
                ("banned", "3. List Banned IPs"),
                ("unban", "4. Unban IP"),
                ("ban", "5. Ban IP Manually"),
                ("config", "6. Configure Ban Settings"),
                ("jails", "7. View Jail Status"),
                ("back", "← Back to Main Menu"),
            ],
        )
        
        if choice == "install":
            install_fail2ban()
        elif choice == "status":
            show_status()
        elif choice == "banned":
            list_banned_ips_interactive()
        elif choice == "unban":
            unban_ip_interactive()
        elif choice == "ban":
            ban_ip_interactive()
        elif choice == "config":
            configure_settings()
        elif choice == "jails":
            view_jail_status_interactive()
        elif choice == "back" or choice is None:
            break
```

**Step 2: Commit**

```bash
git add modules/fail2ban.py
git commit -m "feat(fail2ban): add fail2ban.py with menu structure"
```

---

## Task 14.2: Add install_fail2ban() with auto-detect

**Files:**
- Modify: `modules/fail2ban.py`

**Step 1: Add installation with smart jail detection**

Append to `modules/fail2ban.py`:

```python
def install_fail2ban():
    """Install Fail2ban with auto-detected jail configuration."""
    clear_screen()
    show_header()
    show_panel("Install Fail2ban", title="Fail2ban", style="cyan")
    
    if is_installed("fail2ban"):
        show_info("Fail2ban is already installed.")
        
        if is_service_running("fail2ban"):
            console.print("[dim]Service is running.[/dim]")
        else:
            if confirm_action("Start Fail2ban service?"):
                service_control("fail2ban", "start")
                show_success("Fail2ban started!")
        
        press_enter_to_continue()
        return True
    
    # Detect services
    detected = _detect_services()
    
    console.print("[bold]Fail2ban will protect against brute force attacks.[/bold]")
    console.print()
    console.print("[bold]Detected services to protect:[/bold]")
    
    if detected['ssh']:
        console.print("  [green]✓[/green] SSH (sshd)")
    if detected['nginx']:
        console.print("  [green]✓[/green] Nginx (http-auth, botsearch)")
    if detected['postfix']:
        console.print("  [green]✓[/green] Postfix (mail)")
    
    if not any(detected.values()):
        console.print("  [dim]No services detected (will enable sshd by default)[/dim]")
    
    console.print()
    console.print(f"[dim]Default settings: bantime={DEFAULT_BANTIME}, maxretry={DEFAULT_MAXRETRY}[/dim]")
    console.print()
    
    if not confirm_action("Install and configure Fail2ban?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return False
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return False
    
    show_info("Installing Fail2ban...")
    
    returncode = run_command_realtime(
        "apt install -y fail2ban",
        "Installing Fail2ban..."
    )
    
    if returncode != 0:
        show_error("Failed to install Fail2ban.")
        press_enter_to_continue()
        return False
    
    # Create local config
    show_info("Configuring Fail2ban...")
    
    _create_local_config(detected)
    
    # Start service
    service_control("fail2ban", "start")
    service_control("fail2ban", "enable")
    
    if is_service_running("fail2ban"):
        show_success("Fail2ban installed and running!")
        console.print()
        console.print("[dim]Use 'Show Status' to see active jails.[/dim]")
    else:
        show_warning("Fail2ban installed but service may not be running.")
    
    press_enter_to_continue()
    return True


def _detect_services():
    """Detect installed services for jail configuration."""
    return {
        'ssh': is_installed("openssh-server") or os.path.exists("/etc/ssh/sshd_config"),
        'nginx': is_installed("nginx"),
        'postfix': is_installed("postfix"),
    }


def _create_local_config(detected_services):
    """Create /etc/fail2ban/jail.local with detected services."""
    config = f"""# Fail2ban local configuration
# Generated by vexo-cli

[DEFAULT]
bantime = {DEFAULT_BANTIME}
findtime = {DEFAULT_FINDTIME}
maxretry = {DEFAULT_MAXRETRY}
banaction = iptables-multiport

"""
    
    # Always enable sshd
    config += """[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 5

"""
    
    if detected_services.get('nginx'):
        config += """[nginx-http-auth]
enabled = true
port = http,https
filter = nginx-http-auth
logpath = /var/log/nginx/error.log

[nginx-botsearch]
enabled = true
port = http,https
filter = nginx-botsearch
logpath = /var/log/nginx/access.log

"""
    
    if detected_services.get('postfix'):
        config += """[postfix]
enabled = true
port = smtp,465,submission
filter = postfix
logpath = /var/log/mail.log

[postfix-sasl]
enabled = true
port = smtp,465,submission
filter = postfix-sasl
logpath = /var/log/mail.log

"""
    
    try:
        with open("/etc/fail2ban/jail.local", "w") as f:
            f.write(config)
        return True
    except Exception as e:
        show_error(f"Failed to create config: {e}")
        return False
```

**Step 2: Commit**

```bash
git add modules/fail2ban.py
git commit -m "feat(fail2ban): add install_fail2ban() with auto-detect jails"
```

---

## Task 14.3: Add show_status() and view_jail_status()

**Files:**
- Modify: `modules/fail2ban.py`

**Step 1: Add status display functions**

Append to `modules/fail2ban.py`:

```python
def show_status():
    """Display overall Fail2ban status."""
    clear_screen()
    show_header()
    show_panel("Fail2ban Status", title="Fail2ban", style="cyan")
    
    if not is_installed("fail2ban"):
        show_error("Fail2ban is not installed.")
        press_enter_to_continue()
        return
    
    if not is_service_running("fail2ban"):
        show_warning("Fail2ban service is not running.")
        console.print()
        if confirm_action("Start Fail2ban?"):
            service_control("fail2ban", "start")
            show_success("Started!")
        else:
            press_enter_to_continue()
            return
    
    result = run_command("fail2ban-client status", check=False, silent=True)
    
    if result.returncode != 0:
        show_error("Failed to get Fail2ban status.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Fail2ban Status:[/bold]")
    console.print()
    console.print(result.stdout)
    
    # Get summary of bans
    jails = _get_active_jails()
    if jails:
        console.print()
        console.print("[bold]Jail Summary:[/bold]")
        
        columns = [
            {"name": "Jail", "style": "cyan"},
            {"name": "Currently Banned", "justify": "center"},
            {"name": "Total Banned", "justify": "center"},
        ]
        
        rows = []
        for jail in jails:
            stats = _get_jail_stats(jail)
            rows.append([
                jail,
                str(stats.get('currently_banned', 0)),
                str(stats.get('total_banned', 0)),
            ])
        
        show_table("Active Jails", columns, rows)
    
    press_enter_to_continue()


def view_jail_status_interactive():
    """Interactive view of specific jail status."""
    clear_screen()
    show_header()
    show_panel("Jail Status", title="Fail2ban", style="cyan")
    
    if not is_installed("fail2ban"):
        show_error("Fail2ban is not installed.")
        press_enter_to_continue()
        return
    
    jails = _get_active_jails()
    
    if not jails:
        show_info("No active jails found.")
        press_enter_to_continue()
        return
    
    jail = select_from_list(
        title="View Jail",
        message="Select jail to view:",
        options=jails
    )
    
    if not jail:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    view_jail_status(jail)
    press_enter_to_continue()


def view_jail_status(jail):
    """Display detailed status for a specific jail."""
    result = run_command(f"fail2ban-client status {jail}", check=False, silent=True)
    
    if result.returncode != 0:
        show_error(f"Failed to get status for jail: {jail}")
        return
    
    console.print(f"[bold]Jail: {jail}[/bold]")
    console.print()
    console.print(result.stdout)


def _get_active_jails():
    """Get list of active jails."""
    result = run_command("fail2ban-client status", check=False, silent=True)
    if result.returncode != 0:
        return []
    
    jails = []
    for line in result.stdout.split('\n'):
        if 'Jail list:' in line:
            jail_part = line.split(':')[-1].strip()
            jails = [j.strip() for j in jail_part.split(',') if j.strip()]
            break
    
    return jails


def _get_jail_stats(jail):
    """Get statistics for a jail."""
    result = run_command(f"fail2ban-client status {jail}", check=False, silent=True)
    if result.returncode != 0:
        return {}
    
    stats = {'currently_banned': 0, 'total_banned': 0}
    
    for line in result.stdout.split('\n'):
        if 'Currently banned:' in line:
            try:
                stats['currently_banned'] = int(line.split(':')[-1].strip())
            except ValueError:
                pass
        elif 'Total banned:' in line:
            try:
                stats['total_banned'] = int(line.split(':')[-1].strip())
            except ValueError:
                pass
    
    return stats
```

**Step 2: Commit**

```bash
git add modules/fail2ban.py
git commit -m "feat(fail2ban): add show_status() and view_jail_status()"
```

---

## Task 14.4: Add list_banned_ips()

**Files:**
- Modify: `modules/fail2ban.py`

**Step 1: Add banned IP listing**

Append to `modules/fail2ban.py`:

```python
def list_banned_ips_interactive():
    """Interactive list of banned IPs per jail."""
    clear_screen()
    show_header()
    show_panel("Banned IPs", title="Fail2ban", style="cyan")
    
    if not is_installed("fail2ban"):
        show_error("Fail2ban is not installed.")
        press_enter_to_continue()
        return
    
    jails = _get_active_jails()
    
    if not jails:
        show_info("No active jails found.")
        press_enter_to_continue()
        return
    
    # Show all jails option
    options = ["(all jails)"] + jails
    
    jail = select_from_list(
        title="List Banned IPs",
        message="Select jail (or all):",
        options=options
    )
    
    if not jail:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if jail == "(all jails)":
        list_all_banned_ips(jails)
    else:
        list_banned_ips(jail)
    
    press_enter_to_continue()


def list_banned_ips(jail):
    """List banned IPs for a specific jail."""
    result = run_command(f"fail2ban-client status {jail}", check=False, silent=True)
    
    if result.returncode != 0:
        show_error(f"Failed to get banned IPs for {jail}")
        return
    
    console.print(f"[bold]Banned IPs in {jail}:[/bold]")
    console.print()
    
    # Parse banned IPs
    banned_ips = []
    for line in result.stdout.split('\n'):
        if 'Banned IP list:' in line:
            ip_part = line.split(':')[-1].strip()
            if ip_part:
                banned_ips = [ip.strip() for ip in ip_part.split() if ip.strip()]
            break
    
    if banned_ips:
        for ip in banned_ips:
            console.print(f"  • {ip}")
        console.print()
        console.print(f"[dim]Total: {len(banned_ips)} IP(s)[/dim]")
    else:
        console.print("[dim]No IPs currently banned in this jail.[/dim]")


def list_all_banned_ips(jails):
    """List banned IPs across all jails."""
    console.print("[bold]Banned IPs (All Jails):[/bold]")
    console.print()
    
    total = 0
    for jail in jails:
        result = run_command(f"fail2ban-client status {jail}", check=False, silent=True)
        if result.returncode != 0:
            continue
        
        banned_ips = []
        for line in result.stdout.split('\n'):
            if 'Banned IP list:' in line:
                ip_part = line.split(':')[-1].strip()
                if ip_part:
                    banned_ips = [ip.strip() for ip in ip_part.split() if ip.strip()]
                break
        
        if banned_ips:
            console.print(f"[cyan]{jail}:[/cyan]")
            for ip in banned_ips:
                console.print(f"  • {ip}")
            total += len(banned_ips)
    
    console.print()
    if total > 0:
        console.print(f"[dim]Total banned: {total} IP(s)[/dim]")
    else:
        console.print("[dim]No IPs currently banned.[/dim]")
```

**Step 2: Commit**

```bash
git add modules/fail2ban.py
git commit -m "feat(fail2ban): add list_banned_ips()"
```

---

## Task 14.5: Add unban_ip() and ban_ip()

**Files:**
- Modify: `modules/fail2ban.py`

**Step 1: Add ban/unban functions**

Append to `modules/fail2ban.py`:

```python
def unban_ip_interactive():
    """Interactive prompt to unban an IP."""
    clear_screen()
    show_header()
    show_panel("Unban IP", title="Fail2ban", style="cyan")
    
    if not is_installed("fail2ban"):
        show_error("Fail2ban is not installed.")
        press_enter_to_continue()
        return
    
    ip = text_input(
        title="Unban IP",
        message="Enter IP address to unban:"
    )
    
    if not ip:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Validate IP format (basic)
    if not _is_valid_ip(ip):
        show_error("Invalid IP address format.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = unban_ip(ip)
    
    if success:
        show_success(f"IP {ip} unbanned!")
    else:
        show_warning(f"IP {ip} may not be banned or unban failed.")
    
    press_enter_to_continue()


def unban_ip(ip):
    """
    Unban an IP from all jails.
    
    Args:
        ip: IP address
    
    Returns:
        bool: True if unbanned from at least one jail
    """
    jails = _get_active_jails()
    unbanned = False
    
    for jail in jails:
        result = run_command(
            f"fail2ban-client set {jail} unbanip {ip}",
            check=False,
            silent=True
        )
        if result.returncode == 0:
            unbanned = True
    
    return unbanned


def ban_ip_interactive():
    """Interactive prompt to manually ban an IP."""
    clear_screen()
    show_header()
    show_panel("Ban IP", title="Fail2ban", style="cyan")
    
    if not is_installed("fail2ban"):
        show_error("Fail2ban is not installed.")
        press_enter_to_continue()
        return
    
    jails = _get_active_jails()
    
    if not jails:
        show_error("No active jails to ban IP in.")
        press_enter_to_continue()
        return
    
    ip = text_input(
        title="Ban IP",
        message="Enter IP address to ban:"
    )
    
    if not ip:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not _is_valid_ip(ip):
        show_error("Invalid IP address format.")
        press_enter_to_continue()
        return
    
    jail = select_from_list(
        title="Select Jail",
        message="Ban in which jail?",
        options=jails
    )
    
    if not jail:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print(f"[yellow]This will ban {ip} in {jail}.[/yellow]")
    console.print()
    
    if not confirm_action(f"Ban {ip}?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = ban_ip(ip, jail)
    
    if success:
        show_success(f"IP {ip} banned in {jail}!")
    else:
        show_error(f"Failed to ban {ip}")
    
    press_enter_to_continue()


def ban_ip(ip, jail):
    """
    Ban an IP in a specific jail.
    
    Args:
        ip: IP address
        jail: Jail name
    
    Returns:
        bool: True if successful
    """
    result = run_command(
        f"fail2ban-client set {jail} banip {ip}",
        check=False,
        silent=True
    )
    return result.returncode == 0


def _is_valid_ip(ip):
    """Basic IP address validation."""
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    
    try:
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
    except ValueError:
        return False
    
    return True
```

**Step 2: Commit**

```bash
git add modules/fail2ban.py
git commit -m "feat(fail2ban): add unban_ip() and ban_ip()"
```

---

## Task 14.6: Add configure_settings()

**Files:**
- Modify: `modules/fail2ban.py`

**Step 1: Add settings configuration**

Append to `modules/fail2ban.py`:

```python
def configure_settings():
    """Configure Fail2ban ban settings."""
    clear_screen()
    show_header()
    show_panel("Configure Ban Settings", title="Fail2ban", style="cyan")
    
    if not is_installed("fail2ban"):
        show_error("Fail2ban is not installed.")
        press_enter_to_continue()
        return
    
    # Get current settings
    current = _get_current_settings()
    
    console.print("[bold]Current Settings:[/bold]")
    console.print(f"  Ban Time:   {current.get('bantime', 'unknown')}")
    console.print(f"  Find Time:  {current.get('findtime', 'unknown')}")
    console.print(f"  Max Retry:  {current.get('maxretry', 'unknown')}")
    console.print()
    console.print("[dim]Ban Time: How long an IP stays banned[/dim]")
    console.print("[dim]Find Time: Time window to count failures[/dim]")
    console.print("[dim]Max Retry: Failures before ban[/dim]")
    console.print()
    
    bantime = text_input(
        title="Ban Time",
        message="Enter ban time (e.g., 1h, 30m, 1d):",
        default=current.get('bantime', DEFAULT_BANTIME)
    )
    
    if not bantime:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    findtime = text_input(
        title="Find Time",
        message="Enter find time (e.g., 10m, 1h):",
        default=current.get('findtime', DEFAULT_FINDTIME)
    )
    
    if not findtime:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    maxretry = text_input(
        title="Max Retry",
        message="Enter max retry count:",
        default=current.get('maxretry', DEFAULT_MAXRETRY)
    )
    
    if not maxretry:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Update config
    success = _update_settings(bantime, findtime, maxretry)
    
    if success:
        # Restart fail2ban
        service_control("fail2ban", "restart")
        show_success("Settings updated!")
        console.print()
        console.print(f"[dim]Ban Time: {bantime}[/dim]")
        console.print(f"[dim]Find Time: {findtime}[/dim]")
        console.print(f"[dim]Max Retry: {maxretry}[/dim]")
    else:
        show_error("Failed to update settings.")
    
    press_enter_to_continue()


def _get_current_settings():
    """Get current Fail2ban settings from config."""
    settings = {}
    config_path = "/etc/fail2ban/jail.local"
    
    if not os.path.exists(config_path):
        return settings
    
    try:
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('bantime'):
                    settings['bantime'] = line.split('=')[-1].strip()
                elif line.startswith('findtime'):
                    settings['findtime'] = line.split('=')[-1].strip()
                elif line.startswith('maxretry'):
                    settings['maxretry'] = line.split('=')[-1].strip()
    except Exception:
        pass
    
    return settings


def _update_settings(bantime, findtime, maxretry):
    """Update Fail2ban settings in jail.local."""
    config_path = "/etc/fail2ban/jail.local"
    
    try:
        # Read existing config
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                lines = f.readlines()
        else:
            lines = ["[DEFAULT]\n"]
        
        # Update settings
        new_lines = []
        in_default = False
        updated = {'bantime': False, 'findtime': False, 'maxretry': False}
        
        for line in lines:
            if line.strip() == '[DEFAULT]':
                in_default = True
                new_lines.append(line)
                continue
            elif line.strip().startswith('[') and line.strip() != '[DEFAULT]':
                # Add missing settings before leaving DEFAULT section
                if in_default:
                    if not updated['bantime']:
                        new_lines.append(f"bantime = {bantime}\n")
                    if not updated['findtime']:
                        new_lines.append(f"findtime = {findtime}\n")
                    if not updated['maxretry']:
                        new_lines.append(f"maxretry = {maxretry}\n")
                in_default = False
            
            if in_default:
                if line.strip().startswith('bantime'):
                    new_lines.append(f"bantime = {bantime}\n")
                    updated['bantime'] = True
                elif line.strip().startswith('findtime'):
                    new_lines.append(f"findtime = {findtime}\n")
                    updated['findtime'] = True
                elif line.strip().startswith('maxretry'):
                    new_lines.append(f"maxretry = {maxretry}\n")
                    updated['maxretry'] = True
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        with open(config_path, 'w') as f:
            f.writelines(new_lines)
        
        return True
    except Exception as e:
        show_error(f"Error updating config: {e}")
        return False
```

**Step 2: Commit**

```bash
git add modules/fail2ban.py
git commit -m "feat(fail2ban): add configure_settings()"
```

---

## Task 14.7: Update __init__.py

**Files:**
- Modify: `modules/__init__.py`

**Step 1: Add fail2ban import**

```python
from modules import fail2ban
```

**Step 2: Commit**

```bash
git add modules/__init__.py
git commit -m "feat(fail2ban): export fail2ban module"
```

---

## Summary

After completion, `modules/fail2ban.py` will have:

**Menu Function:**
- `show_menu()` - 7-option fail2ban submenu

**Core Functions:**
- `install_fail2ban()` - Install with auto-detect jails
- `show_status()` - Overall status with jail summary
- `view_jail_status()` - Detailed jail info
- `list_banned_ips()` - Show banned IPs
- `unban_ip()` - Unban from all jails
- `ban_ip()` - Manual ban
- `configure_settings()` - Update bantime/findtime/maxretry

**Helper Functions:**
- `_detect_services()` - Detect SSH/Nginx/Postfix
- `_create_local_config()` - Generate jail.local
- `_get_active_jails()` - List active jails
- `_get_jail_stats()` - Get jail statistics
- `_is_valid_ip()` - IP validation
- `_get_current_settings()` - Read current config
- `_update_settings()` - Write new settings

**Auto-Detected Jails:**
- `sshd` - Always enabled
- `nginx-http-auth`, `nginx-botsearch` - If Nginx installed
- `postfix`, `postfix-sasl` - If Postfix installed
