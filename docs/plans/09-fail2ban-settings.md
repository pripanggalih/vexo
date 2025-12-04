# Fail2ban Phase 9: Settings & Service Control

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the settings module with global ban settings, recidive configuration, service control, and health checks.

**Architecture:** Enhance settings.py with recidive jail management, service controls, and health monitoring.

**Tech Stack:** Python, Rich (panels), fail2ban-client, systemctl

---

## Task 1: Complete Settings Module

**Files:**
- Modify: `modules/fail2ban/settings.py`

**Step 1: Complete settings.py with all features**

```python
"""Settings and service control for fail2ban module."""

import os
from datetime import datetime

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
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import (
    run_command,
    run_command_realtime,
    service_control,
    require_root,
    is_service_running,
)

from .common import (
    is_fail2ban_installed,
    is_fail2ban_running,
    get_fail2ban_version,
    detect_services,
    get_active_jails,
    JAIL_LOCAL,
    JAIL_D_DIR,
    FILTER_D_DIR,
    FAIL2BAN_LOG,
    FAIL2BAN_DB,
    DEFAULT_BANTIME,
    DEFAULT_FINDTIME,
    DEFAULT_MAXRETRY,
)


RECIDIVE_JAIL_FILE = os.path.join(JAIL_D_DIR, "recidive.conf")


def show_menu():
    """Display settings menu."""
    def get_status():
        if is_fail2ban_running():
            return "[green]Running[/green]"
        elif is_fail2ban_installed():
            return "[red]Stopped[/red]"
        return "[dim]Not installed[/dim]"
    
    def get_options():
        return [
            ("global", "1. Global Ban Settings"),
            ("recidive", "2. Recidive (Repeat Offenders)"),
            ("service", "3. Service Control"),
            ("health", "4. Health Check"),
            ("logging", "5. Logging Settings"),
            ("back", "← Back"),
        ]
    
    handlers = {
        "global": configure_global_settings,
        "recidive": configure_recidive,
        "service": service_control_menu,
        "health": health_check,
        "logging": configure_logging,
    }
    
    run_menu_loop("Settings", get_options, handlers, get_status)


def install_fail2ban():
    """Install Fail2ban with auto-detected jail configuration."""
    clear_screen()
    show_header()
    show_panel("Install Fail2ban", title="Fail2ban", style="cyan")
    
    if is_fail2ban_installed():
        show_info("Fail2ban is already installed.")
        
        if is_fail2ban_running():
            console.print("[dim]Service is running.[/dim]")
        else:
            if confirm_action("Start Fail2ban service?"):
                service_control("fail2ban", "start")
                show_success("Fail2ban started!")
        
        press_enter_to_continue()
        return True
    
    # Detect services
    detected = detect_services()
    
    console.print("[bold]Fail2ban will protect against brute force attacks.[/bold]")
    console.print()
    console.print("[bold]Detected services to protect:[/bold]")
    
    if detected['ssh']:
        console.print("  [green]✓[/green] SSH (sshd)")
    if detected['nginx']:
        console.print("  [green]✓[/green] Nginx (http-auth, botsearch)")
    if detected['apache']:
        console.print("  [green]✓[/green] Apache (http-auth)")
    if detected['postfix']:
        console.print("  [green]✓[/green] Postfix (mail)")
    if detected['dovecot']:
        console.print("  [green]✓[/green] Dovecot (imap/pop3)")
    
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
    _create_initial_config(detected)
    
    # Start service
    service_control("fail2ban", "start")
    service_control("fail2ban", "enable")
    
    if is_fail2ban_running():
        show_success("Fail2ban installed and running!")
        console.print()
        console.print("[dim]Use Dashboard to see status.[/dim]")
    else:
        show_warning("Fail2ban installed but service may not be running.")
    
    press_enter_to_continue()
    return True


def _create_initial_config(detected_services):
    """Create initial jail.local configuration."""
    config = f"""# Fail2ban local configuration
# Generated by vexo-cli

[DEFAULT]
bantime = {DEFAULT_BANTIME}
findtime = {DEFAULT_FINDTIME}
maxretry = {DEFAULT_MAXRETRY}
banaction = iptables-multiport
ignoreip = 127.0.0.1/8 ::1

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
    
    if detected_services.get('apache'):
        config += """[apache-auth]
enabled = true
port = http,https
filter = apache-auth
logpath = /var/log/apache2/error.log

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
    
    if detected_services.get('dovecot'):
        config += """[dovecot]
enabled = true
port = pop3,pop3s,imap,imaps
filter = dovecot
logpath = /var/log/mail.log

"""
    
    try:
        with open(JAIL_LOCAL, "w") as f:
            f.write(config)
        return True
    except Exception as e:
        show_error(f"Failed to create config: {e}")
        return False


def configure_global_settings():
    """Configure global ban settings."""
    clear_screen()
    show_header()
    show_panel("Global Ban Settings", title="Settings", style="cyan")
    
    if not is_fail2ban_installed():
        show_error("Fail2ban is not installed.")
        press_enter_to_continue()
        return
    
    current = _get_current_settings()
    
    console.print("[bold]Current Settings:[/bold]")
    console.print(f"  Ban Time:   {current.get('bantime', DEFAULT_BANTIME)}")
    console.print(f"  Find Time:  {current.get('findtime', DEFAULT_FINDTIME)}")
    console.print(f"  Max Retry:  {current.get('maxretry', DEFAULT_MAXRETRY)}")
    console.print(f"  Ban Action: {current.get('banaction', 'iptables-multiport')}")
    console.print()
    
    console.print("[dim]Ban Time: How long an IP stays banned[/dim]")
    console.print("[dim]Find Time: Time window to count failures[/dim]")
    console.print("[dim]Max Retry: Failures before ban[/dim]")
    console.print()
    
    if not confirm_action("Modify settings?"):
        press_enter_to_continue()
        return
    
    bantime = text_input(
        title="Ban Time",
        message="Ban duration (e.g., 1h, 30m, 1d):",
        default=current.get('bantime', DEFAULT_BANTIME)
    )
    
    if not bantime:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    findtime = text_input(
        title="Find Time",
        message="Time window (e.g., 10m, 1h):",
        default=current.get('findtime', DEFAULT_FINDTIME)
    )
    
    maxretry = text_input(
        title="Max Retry",
        message="Max retry count:",
        default=current.get('maxretry', DEFAULT_MAXRETRY)
    )
    
    banaction = select_from_list(
        title="Ban Action",
        message="Firewall action:",
        options=[
            "iptables-multiport",
            "iptables-allports",
            "nftables-multiport",
            "ufw",
        ]
    )
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = _update_settings({
        'bantime': bantime,
        'findtime': findtime,
        'maxretry': maxretry,
        'banaction': banaction or 'iptables-multiport',
    })
    
    if success:
        service_control("fail2ban", "reload")
        show_success("Settings updated!")
    else:
        show_error("Failed to update settings.")
    
    press_enter_to_continue()


def configure_recidive():
    """Configure recidive jail for repeat offenders."""
    clear_screen()
    show_header()
    show_panel("Recidive Settings", title="Settings", style="cyan")
    
    console.print("[bold]Recidive Jail[/bold]")
    console.print("[dim]Automatically ban repeat offenders for longer periods.[/dim]")
    console.print()
    
    # Check if recidive is enabled
    recidive_enabled = _is_recidive_enabled()
    
    console.print(f"Status: {'[green]Enabled[/green]' if recidive_enabled else '[dim]Disabled[/dim]'}")
    console.print()
    
    if recidive_enabled:
        current = _get_recidive_settings()
        console.print("[bold]Current Settings:[/bold]")
        console.print(f"  Trigger: Ban in any jail {current.get('maxretry', 5)} times")
        console.print(f"  Within: {current.get('findtime', '1d')}")
        console.print(f"  Then ban for: {current.get('bantime', '1w')}")
        console.print()
    
    action = select_from_list(
        title="Action",
        message="What to do?",
        options=[
            "Enable/Configure" if not recidive_enabled else "Configure",
            "Disable" if recidive_enabled else None,
            "Back"
        ]
    )
    
    if action and action.startswith("Enable") or action == "Configure":
        _configure_recidive()
    elif action == "Disable":
        _disable_recidive()
    
    press_enter_to_continue()


def _configure_recidive():
    """Configure recidive jail settings."""
    console.print()
    console.print("[bold]Configure Recidive:[/bold]")
    console.print()
    
    current = _get_recidive_settings()
    
    maxretry = text_input(
        title="Trigger Count",
        message="Ban after how many bans in other jails:",
        default=str(current.get('maxretry', 5))
    )
    
    findtime = text_input(
        title="Time Window",
        message="Within time period (e.g., 1d, 12h):",
        default=current.get('findtime', '1d')
    )
    
    bantime = text_input(
        title="Ban Duration",
        message="Recidive ban time (e.g., 1w, 30d):",
        default=current.get('bantime', '1w')
    )
    
    try:
        require_root()
    except PermissionError:
        return
    
    # Create recidive jail
    recidive_config = f"""[recidive]
# Recidive jail - ban repeat offenders
# Generated by vexo-cli

enabled = true
filter = recidive
logpath = /var/log/fail2ban.log
banaction = iptables-allports
maxretry = {maxretry}
findtime = {findtime}
bantime = {bantime}
"""
    
    try:
        os.makedirs(JAIL_D_DIR, exist_ok=True)
        with open(RECIDIVE_JAIL_FILE, 'w') as f:
            f.write(recidive_config)
        
        service_control("fail2ban", "reload")
        show_success("Recidive jail configured!")
    except Exception as e:
        show_error(f"Failed to configure: {e}")


def _disable_recidive():
    """Disable recidive jail."""
    try:
        require_root()
    except PermissionError:
        return
    
    if os.path.exists(RECIDIVE_JAIL_FILE):
        os.remove(RECIDIVE_JAIL_FILE)
        service_control("fail2ban", "reload")
        show_success("Recidive jail disabled!")
    else:
        show_info("Recidive jail not configured.")


def _is_recidive_enabled():
    """Check if recidive jail is enabled."""
    jails = get_active_jails()
    return 'recidive' in jails


def _get_recidive_settings():
    """Get current recidive settings."""
    settings = {'maxretry': '5', 'findtime': '1d', 'bantime': '1w'}
    
    if os.path.exists(RECIDIVE_JAIL_FILE):
        try:
            with open(RECIDIVE_JAIL_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        if key in settings:
                            settings[key] = value.strip()
        except Exception:
            pass
    
    return settings


def service_control_menu():
    """Service control menu."""
    clear_screen()
    show_header()
    show_panel("Service Control", title="Settings", style="cyan")
    
    # Show status
    if is_fail2ban_running():
        console.print("Status: [green]● Running[/green]")
        version = get_fail2ban_version()
        console.print(f"Version: {version}")
    else:
        console.print("Status: [red]● Stopped[/red]")
    
    console.print()
    
    # Get uptime
    uptime = _get_service_uptime()
    if uptime:
        console.print(f"Uptime: {uptime}")
    
    # Get PID
    result = run_command("pgrep -f fail2ban-server", check=False, silent=True)
    if result.returncode == 0:
        console.print(f"PID: {result.stdout.strip()}")
    
    console.print()
    
    # Actions
    options = []
    if is_fail2ban_running():
        options.extend([
            ("stop", "Stop Service"),
            ("restart", "Restart Service"),
            ("reload", "Reload Config"),
        ])
    else:
        options.append(("start", "Start Service"))
    
    options.append(("boot", "Toggle Start on Boot"))
    options.append(("back", "← Back"))
    
    action = select_from_list(
        title="Action",
        message="Select action:",
        options=[o[0] for o in options],
        display_options=[o[1] for o in options]
    )
    
    if not action or action == "back":
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if action in ["start", "stop", "restart", "reload"]:
        service_control("fail2ban", action)
        show_success(f"Service {action} completed!")
    elif action == "boot":
        # Check current state
        result = run_command("systemctl is-enabled fail2ban", check=False, silent=True)
        if "enabled" in result.stdout:
            service_control("fail2ban", "disable")
            show_success("Disabled start on boot.")
        else:
            service_control("fail2ban", "enable")
            show_success("Enabled start on boot.")
    
    press_enter_to_continue()


def health_check():
    """Run health check on fail2ban."""
    clear_screen()
    show_header()
    show_panel("Health Check", title="Settings", style="cyan")
    
    console.print("[bold]Running health check...[/bold]")
    console.print()
    
    checks = []
    
    # Check 1: Service running
    running = is_fail2ban_running()
    checks.append({
        'name': 'Service Status',
        'status': 'OK' if running else 'FAIL',
        'message': 'Running' if running else 'Not running',
    })
    
    # Check 2: Config syntax
    result = run_command("fail2ban-client -t", check=False, silent=True)
    config_ok = result.returncode == 0
    checks.append({
        'name': 'Configuration',
        'status': 'OK' if config_ok else 'FAIL',
        'message': 'Valid' if config_ok else 'Syntax error',
    })
    
    # Check 3: Active jails
    jails = get_active_jails()
    checks.append({
        'name': 'Active Jails',
        'status': 'OK' if jails else 'WARN',
        'message': f'{len(jails)} jails active' if jails else 'No jails active',
    })
    
    # Check 4: Log file
    log_exists = os.path.exists(FAIL2BAN_LOG)
    log_writable = os.access(FAIL2BAN_LOG, os.W_OK) if log_exists else False
    checks.append({
        'name': 'Log File',
        'status': 'OK' if log_writable else 'WARN',
        'message': 'OK' if log_writable else 'Not writable or missing',
    })
    
    # Check 5: Database
    db_exists = os.path.exists(FAIL2BAN_DB) if FAIL2BAN_DB else False
    checks.append({
        'name': 'Database',
        'status': 'OK' if db_exists else 'WARN',
        'message': 'OK' if db_exists else 'Not found',
    })
    
    # Check 6: Firewall
    result = run_command("iptables -L -n | grep -c f2b", check=False, silent=True)
    try:
        fw_rules = int(result.stdout.strip())
    except:
        fw_rules = 0
    checks.append({
        'name': 'Firewall Rules',
        'status': 'OK' if fw_rules > 0 else 'WARN',
        'message': f'{fw_rules} fail2ban chains' if fw_rules else 'No chains found',
    })
    
    # Display results
    columns = [
        {"name": "Check", "style": "cyan"},
        {"name": "Status"},
        {"name": "Details"},
    ]
    
    rows = []
    for check in checks:
        status = check['status']
        if status == 'OK':
            status_display = '[green]✓ OK[/green]'
        elif status == 'WARN':
            status_display = '[yellow]! WARN[/yellow]'
        else:
            status_display = '[red]✗ FAIL[/red]'
        
        rows.append([check['name'], status_display, check['message']])
    
    show_table("Health Check Results", columns, rows)
    
    # Summary
    console.print()
    failed = sum(1 for c in checks if c['status'] == 'FAIL')
    warned = sum(1 for c in checks if c['status'] == 'WARN')
    
    if failed > 0:
        console.print(f"[red]Health check: {failed} issue(s) found[/red]")
    elif warned > 0:
        console.print(f"[yellow]Health check: {warned} warning(s)[/yellow]")
    else:
        console.print("[green]Health check: All OK[/green]")
    
    press_enter_to_continue()


def configure_logging():
    """Configure logging settings."""
    clear_screen()
    show_header()
    show_panel("Logging Settings", title="Settings", style="cyan")
    
    console.print("[bold]Current Logging:[/bold]")
    console.print(f"  Log File: {FAIL2BAN_LOG}")
    
    # Get log size
    if os.path.exists(FAIL2BAN_LOG):
        size = os.path.getsize(FAIL2BAN_LOG) / (1024 * 1024)
        console.print(f"  Log Size: {size:.2f} MB")
    
    console.print()
    
    # Get current log level
    result = run_command("fail2ban-client get loglevel", check=False, silent=True)
    if result.returncode == 0:
        console.print(f"  Log Level: {result.stdout.strip()}")
    
    console.print()
    
    action = select_from_list(
        title="Action",
        message="What to do?",
        options=["Change Log Level", "Rotate Log Now", "View Recent Log", "Back"]
    )
    
    if action == "Change Log Level":
        level = select_from_list(
            title="Log Level",
            message="Select log level:",
            options=["CRITICAL", "ERROR", "WARNING", "NOTICE", "INFO", "DEBUG"]
        )
        if level:
            try:
                require_root()
                run_command(f"fail2ban-client set loglevel {level}", check=False, silent=True)
                show_success(f"Log level set to {level}")
            except PermissionError:
                pass
    
    elif action == "Rotate Log Now":
        try:
            require_root()
            run_command("logrotate -f /etc/logrotate.d/fail2ban", check=False, silent=True)
            show_success("Log rotated!")
        except PermissionError:
            pass
    
    elif action == "View Recent Log":
        if os.path.exists(FAIL2BAN_LOG):
            result = run_command(f"tail -50 {FAIL2BAN_LOG}", check=False, silent=True)
            console.print(result.stdout)
        else:
            show_error("Log file not found.")
    
    press_enter_to_continue()


# Helper functions

def _get_current_settings():
    """Get current settings from jail.local."""
    settings = {}
    
    if not os.path.exists(JAIL_LOCAL):
        return settings
    
    try:
        with open(JAIL_LOCAL, 'r') as f:
            in_default = False
            for line in f:
                line = line.strip()
                if line == '[DEFAULT]':
                    in_default = True
                    continue
                elif line.startswith('['):
                    in_default = False
                
                if in_default and '=' in line:
                    key, value = line.split('=', 1)
                    settings[key.strip()] = value.strip()
    except Exception:
        pass
    
    return settings


def _update_settings(settings):
    """Update settings in jail.local."""
    try:
        if os.path.exists(JAIL_LOCAL):
            with open(JAIL_LOCAL, 'r') as f:
                lines = f.readlines()
        else:
            lines = ["[DEFAULT]\n"]
        
        new_lines = []
        in_default = False
        updated = {key: False for key in settings}
        
        for line in lines:
            if line.strip() == '[DEFAULT]':
                in_default = True
                new_lines.append(line)
                continue
            elif line.strip().startswith('[') and line.strip() != '[DEFAULT]':
                # Add missing settings before leaving DEFAULT
                if in_default:
                    for key, value in settings.items():
                        if not updated[key]:
                            new_lines.append(f"{key} = {value}\n")
                in_default = False
            
            if in_default:
                for key, value in settings.items():
                    if line.strip().startswith(f"{key} ") or line.strip().startswith(f"{key}="):
                        new_lines.append(f"{key} = {value}\n")
                        updated[key] = True
                        break
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        with open(JAIL_LOCAL, 'w') as f:
            f.writelines(new_lines)
        
        return True
    except Exception as e:
        show_error(f"Error: {e}")
        return False


def _get_service_uptime():
    """Get fail2ban service uptime."""
    result = run_command(
        "systemctl show fail2ban --property=ActiveEnterTimestamp",
        check=False,
        silent=True
    )
    
    if result.returncode != 0:
        return None
    
    try:
        timestamp_str = result.stdout.split('=')[-1].strip()
        if not timestamp_str:
            return None
        
        # Parse and calculate uptime
        from datetime import datetime
        start_time = datetime.strptime(timestamp_str, "%a %Y-%m-%d %H:%M:%S %Z")
        delta = datetime.now() - start_time
        
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except Exception:
        return None
```

**Step 2: Commit settings module**

```bash
git add modules/fail2ban/settings.py
git commit -m "feat(fail2ban): complete settings with recidive, health check, logging"
```

---

## Task 2: Final Integration

**Files:**
- Verify: `modules/fail2ban/__init__.py`

**Step 1: Verify all imports work**

Ensure all submodules are properly imported in __init__.py. The lazy import pattern should handle this automatically.

**Step 2: Final commit**

```bash
git add -A
git commit -m "feat(fail2ban): complete fail2ban enhancement - all 9 phases"
```

---

## Verification

After completing all tasks:

1. Settings features:
   - Global ban settings (bantime, findtime, maxretry, banaction)
   - Recidive jail configuration
   - Service control (start/stop/restart/reload)
   - Health check with diagnostics
   - Logging configuration

2. Complete fail2ban package structure:
```
modules/fail2ban/
├── __init__.py
├── common.py
├── dashboard.py
├── jails.py
├── bans.py
├── whitelist.py
├── filters.py
├── history.py
├── notifications.py
├── backup.py
├── settings.py
└── templates/
    ├── __init__.py
    ├── web_apps.py
    └── web_security.py
```

3. All 9 phases implemented:
   - Phase 1: Package structure + Dashboard
   - Phase 2: Jail management + Templates
   - Phase 3: Ban management + Permanent bans
   - Phase 4: Whitelist management
   - Phase 5: Filter management + Testing
   - Phase 6: History & Analytics
   - Phase 7: Notification system
   - Phase 8: Backup & Restore
   - Phase 9: Settings & Service control
