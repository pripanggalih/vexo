# Phase 1: Firewall Package Refactor + Status Dashboard

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor monolithic firewall.py into organized firewall/ package with enhanced status dashboard.

**Architecture:** Split firewall.py into common utilities, status display, and quick setup modules. Add comprehensive dashboard showing UFW status, rule count, and default policies.

**Tech Stack:** Python, Rich (tables, panels), UFW CLI

---

## Task 1: Create Package Structure

**Files:**
- Create: `modules/firewall/__init__.py`
- Create: `modules/firewall/common.py`

**Step 1: Create common.py with shared utilities**

```python
"""Common utilities for firewall module."""

import re
from utils.shell import run_command, is_installed


# Config paths
VEXO_FIREWALL_DIR = "/etc/vexo/firewall"
VEXO_FIREWALL_BACKUPS = f"{VEXO_FIREWALL_DIR}/backups"
IP_GROUPS_FILE = f"{VEXO_FIREWALL_DIR}/ip-groups.json"
RATE_LIMITS_FILE = f"{VEXO_FIREWALL_DIR}/rate-limits.json"
SETTINGS_FILE = f"{VEXO_FIREWALL_DIR}/settings.json"


def is_ufw_installed():
    """Check if UFW is installed."""
    return is_installed("ufw")


def is_ufw_active():
    """Check if UFW is active."""
    if not is_ufw_installed():
        return False
    result = run_command("ufw status", check=False, silent=True)
    if result.returncode == 0:
        return "active" in result.stdout.lower() and "inactive" not in result.stdout.lower()
    return False


def get_ufw_status_text():
    """Get UFW status as formatted text."""
    if not is_ufw_installed():
        return "[dim]Not installed[/dim]"
    
    result = run_command("ufw status", check=False, silent=True)
    if result.returncode == 0:
        if "inactive" in result.stdout.lower():
            return "[yellow]Inactive[/yellow]"
        elif "active" in result.stdout.lower():
            return "[green]Active[/green]"
    return "[dim]Unknown[/dim]"


def get_ufw_rules():
    """Get list of UFW rules as list of dicts."""
    result = run_command("ufw status numbered", check=False, silent=True)
    if result.returncode != 0:
        return []
    
    rules = []
    for line in result.stdout.strip().split('\n'):
        if line.strip().startswith('['):
            match = re.match(r'\[\s*(\d+)\]\s+(.+)', line)
            if match:
                rules.append({
                    "number": int(match.group(1)),
                    "rule": match.group(2).strip()
                })
    return rules


def get_ufw_defaults():
    """Get UFW default policies."""
    result = run_command("ufw status verbose", check=False, silent=True)
    if result.returncode != 0:
        return {"incoming": "unknown", "outgoing": "unknown", "routed": "unknown"}
    
    defaults = {"incoming": "unknown", "outgoing": "unknown", "routed": "unknown"}
    
    for line in result.stdout.split('\n'):
        line_lower = line.lower()
        if "default:" in line_lower:
            if "deny (incoming)" in line_lower:
                defaults["incoming"] = "deny"
            elif "allow (incoming)" in line_lower:
                defaults["incoming"] = "allow"
            if "allow (outgoing)" in line_lower:
                defaults["outgoing"] = "allow"
            elif "deny (outgoing)" in line_lower:
                defaults["outgoing"] = "deny"
            if "disabled (routed)" in line_lower:
                defaults["routed"] = "disabled"
            elif "deny (routed)" in line_lower:
                defaults["routed"] = "deny"
    
    return defaults


def get_rule_count():
    """Get total number of UFW rules."""
    return len(get_ufw_rules())


def ensure_config_dir():
    """Ensure vexo firewall config directory exists."""
    import os
    os.makedirs(VEXO_FIREWALL_DIR, exist_ok=True)
    os.makedirs(VEXO_FIREWALL_BACKUPS, exist_ok=True)
```

**Step 2: Create package __init__.py**

```python
"""Firewall (UFW) management module for vexo."""

from ui.menu import run_menu_loop
from modules.firewall.common import is_ufw_installed, get_ufw_status_text


def show_menu():
    """Display the Firewall (UFW) main menu."""
    from modules.firewall.status import show_status_dashboard
    from modules.firewall.quick_setup import (
        install_ufw,
        enable_firewall,
        disable_firewall,
    )
    from modules.firewall.ports import show_ports_menu
    from modules.firewall.ip_management import show_ip_menu
    from modules.firewall.rate_limiting import show_rate_limit_menu
    from modules.firewall.profiles import show_profiles_menu
    from modules.firewall.logs import show_logs_menu
    from modules.firewall.backup import show_backup_menu
    
    def get_status():
        return f"UFW Status: {get_ufw_status_text()}"
    
    def get_options():
        options = []
        if is_ufw_installed():
            options.extend([
                ("status", "1. Status Dashboard"),
                ("enable", "2. Enable Firewall"),
                ("disable", "3. Disable Firewall"),
                ("ports", "4. Port Management"),
                ("ip", "5. IP Management"),
                ("rate", "6. Rate Limiting"),
                ("profiles", "7. Application Profiles"),
                ("logs", "8. Logs & Monitoring"),
                ("backup", "9. Backup & Restore"),
            ])
        else:
            options.append(("install", "1. Install UFW"))
        options.append(("back", "← Back to Main Menu"))
        return options
    
    handlers = {
        "install": install_ufw,
        "status": show_status_dashboard,
        "enable": enable_firewall,
        "disable": disable_firewall,
        "ports": show_ports_menu,
        "ip": show_ip_menu,
        "rate": show_rate_limit_menu,
        "profiles": show_profiles_menu,
        "logs": show_logs_menu,
        "backup": show_backup_menu,
    }
    
    run_menu_loop("Firewall (UFW)", get_options, handlers, get_status)
```

**Step 3: Commit**

```bash
git add modules/firewall/__init__.py modules/firewall/common.py
git commit -m "feat(firewall): create package structure with common utilities"
```

---

## Task 2: Create Status Dashboard

**Files:**
- Create: `modules/firewall/status.py`

**Step 1: Create status.py with dashboard**

```python
"""Firewall status dashboard."""

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_error,
    press_enter_to_continue,
)
from modules.firewall.common import (
    is_ufw_installed,
    is_ufw_active,
    get_ufw_rules,
    get_ufw_defaults,
    get_rule_count,
)
from utils.shell import run_command


def show_status_dashboard():
    """Display comprehensive firewall status dashboard."""
    clear_screen()
    show_header()
    
    if not is_ufw_installed():
        show_error("UFW is not installed.")
        console.print()
        console.print("[dim]Use 'Enable Firewall' to install and configure UFW.[/dim]")
        press_enter_to_continue()
        return
    
    # Build status info
    active = is_ufw_active()
    defaults = get_ufw_defaults()
    rule_count = get_rule_count()
    
    # Status line
    status_color = "green" if active else "yellow"
    status_text = "Active" if active else "Inactive"
    
    # Header panel
    header_content = f"""[bold]UFW Status:[/bold] [{status_color}]{status_text}[/{status_color}]
[bold]Rules:[/bold] {rule_count} active
[bold]Default Incoming:[/bold] {_format_policy(defaults['incoming'])}
[bold]Default Outgoing:[/bold] {_format_policy(defaults['outgoing'])}"""
    
    show_panel(header_content, title="Firewall (UFW) Dashboard", style="cyan")
    
    # Show rules table
    _show_rules_table()
    
    # Show app profiles summary
    _show_app_profiles_summary()
    
    press_enter_to_continue()


def _format_policy(policy):
    """Format policy with color."""
    if policy == "deny":
        return "[green]deny[/green]"
    elif policy == "allow":
        return "[yellow]allow[/yellow]"
    elif policy == "disabled":
        return "[dim]disabled[/dim]"
    return f"[dim]{policy}[/dim]"


def _show_rules_table():
    """Display rules in a table format."""
    rules = get_ufw_rules()
    
    if not rules:
        console.print("[dim]No rules configured.[/dim]")
        console.print()
        return
    
    console.print("[bold]Active Rules:[/bold]")
    console.print()
    
    columns = [
        {"name": "#", "style": "dim", "justify": "right"},
        {"name": "Rule", "style": "cyan"},
    ]
    
    rows = [[str(r["number"]), r["rule"]] for r in rules[:15]]
    
    show_table("", columns, rows, show_header=True)
    
    if len(rules) > 15:
        console.print(f"[dim]... and {len(rules) - 15} more rules[/dim]")
        console.print()


def _show_app_profiles_summary():
    """Show summary of available app profiles."""
    result = run_command("ufw app list", check=False, silent=True)
    
    if result.returncode != 0:
        return
    
    lines = result.stdout.strip().split('\n')
    profiles = [l.strip() for l in lines if l.strip() and "Available" not in l]
    
    if profiles:
        console.print(f"[bold]App Profiles:[/bold] {len(profiles)} available")
        console.print(f"[dim]{', '.join(profiles[:5])}", end="")
        if len(profiles) > 5:
            console.print(f" +{len(profiles) - 5} more[/dim]")
        else:
            console.print("[/dim]")
        console.print()
```

**Step 2: Commit**

```bash
git add modules/firewall/status.py
git commit -m "feat(firewall): add status dashboard with rules overview"
```

---

## Task 3: Create Quick Setup Module

**Files:**
- Create: `modules/firewall/quick_setup.py`

**Step 1: Create quick_setup.py with enable/disable**

```python
"""Quick setup functions for firewall."""

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_success,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import confirm_action
from utils.shell import (
    run_command,
    run_command_with_progress,
    is_installed,
    require_root,
)
from modules.firewall.common import is_ufw_installed, is_ufw_active


def install_ufw():
    """Install UFW if not already installed."""
    clear_screen()
    show_header()
    show_panel("Install UFW", title="Firewall (UFW)", style="cyan")
    
    if is_installed("ufw"):
        show_info("UFW is already installed.")
        press_enter_to_continue()
        return True
    
    if not confirm_action("Install UFW firewall?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return False
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return False
    
    show_info("Installing UFW...")
    
    result = run_command_with_progress(
        "apt install -y ufw",
        "Installing UFW..."
    )
    
    if result.returncode != 0:
        show_error("Failed to install UFW.")
        press_enter_to_continue()
        return False
    
    show_success("UFW installed successfully!")
    press_enter_to_continue()
    return True


def enable_firewall():
    """Enable UFW with default security rules."""
    clear_screen()
    show_header()
    show_panel("Enable Firewall", title="Firewall (UFW)", style="cyan")
    
    console.print("[bold]This will configure UFW with:[/bold]")
    console.print("  • Default: deny incoming, allow outgoing")
    console.print("  • Allow SSH (port 22)")
    console.print("  • Allow HTTP (port 80)")
    console.print("  • Allow HTTPS (port 443)")
    console.print()
    
    if is_ufw_active():
        show_info("UFW is already active.")
        if not confirm_action("Reconfigure with default rules?"):
            press_enter_to_continue()
            return
    
    if not confirm_action("Enable firewall with these rules?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if not is_ufw_installed():
        if not install_ufw():
            return
    
    show_info("Configuring firewall rules...")
    
    run_command("ufw --force reset", check=False, silent=True)
    run_command("ufw default deny incoming", check=False, silent=True)
    run_command("ufw default allow outgoing", check=False, silent=True)
    
    rules = [
        ("22/tcp", "SSH"),
        ("80/tcp", "HTTP"),
        ("443/tcp", "HTTPS"),
    ]
    
    for port, name in rules:
        result = run_command(f"ufw allow {port}", check=False, silent=True)
        if result.returncode == 0:
            console.print(f"  [green]✓[/green] Allowed {name} ({port})")
        else:
            console.print(f"  [red]✗[/red] Failed to allow {name}")
    
    console.print()
    show_info("Enabling UFW...")
    
    result = run_command("ufw --force enable", check=False, silent=True)
    
    if result.returncode == 0:
        show_success("Firewall enabled successfully!")
    else:
        show_error("Failed to enable UFW.")
    
    press_enter_to_continue()


def disable_firewall():
    """Disable UFW firewall."""
    clear_screen()
    show_header()
    show_panel("Disable Firewall", title="Firewall (UFW)", style="cyan")
    
    if not is_ufw_installed():
        show_error("UFW is not installed.")
        press_enter_to_continue()
        return
    
    if not is_ufw_active():
        show_info("UFW is already disabled.")
        press_enter_to_continue()
        return
    
    console.print("[red bold]WARNING: Disabling the firewall will expose all ports![/red bold]")
    console.print()
    console.print("[yellow]This is NOT recommended for production servers.[/yellow]")
    console.print()
    
    if not confirm_action("Are you sure you want to disable the firewall?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    result = run_command("ufw --force disable", check=False, silent=True)
    
    if result.returncode == 0:
        show_warning("Firewall disabled!")
        console.print("[dim]Your server is now unprotected.[/dim]")
    else:
        show_error("Failed to disable UFW.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/firewall/quick_setup.py
git commit -m "feat(firewall): add quick setup with enable/disable functions"
```

---

## Task 4: Create Placeholder Submodules

**Files:**
- Create: `modules/firewall/ports.py`
- Create: `modules/firewall/ip_management.py`
- Create: `modules/firewall/rate_limiting.py`
- Create: `modules/firewall/profiles.py`
- Create: `modules/firewall/logs.py`
- Create: `modules/firewall/backup.py`

**Step 1: Create ports.py placeholder**

```python
"""Port management for firewall."""

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_info,
    press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.firewall.common import get_ufw_status_text


def show_ports_menu():
    """Display port management submenu."""
    def get_status():
        return f"UFW: {get_ufw_status_text()}"
    
    options = [
        ("add", "1. Add Custom Port"),
        ("presets", "2. Port Presets"),
        ("remove", "3. Remove Port"),
        ("list", "4. List Open Ports"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "add": _placeholder,
        "presets": _placeholder,
        "remove": _placeholder,
        "list": _placeholder,
    }
    
    run_menu_loop("Port Management", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Port Management", style="cyan")
    show_info("This feature will be implemented in Phase 2.")
    press_enter_to_continue()
```

**Step 2: Create ip_management.py placeholder**

```python
"""IP management for firewall."""

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_info,
    press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.firewall.common import get_ufw_status_text


def show_ip_menu():
    """Display IP management submenu."""
    def get_status():
        return f"UFW: {get_ufw_status_text()}"
    
    options = [
        ("allow", "1. Allow IP"),
        ("deny", "2. Deny/Block IP"),
        ("whitelist", "3. IP Whitelist"),
        ("groups", "4. IP Groups"),
        ("list", "5. List IP Rules"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "allow": _placeholder,
        "deny": _placeholder,
        "whitelist": _placeholder,
        "groups": _placeholder,
        "list": _placeholder,
    }
    
    run_menu_loop("IP Management", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="IP Management", style="cyan")
    show_info("This feature will be implemented in Phase 3.")
    press_enter_to_continue()
```

**Step 3: Create rate_limiting.py placeholder**

```python
"""Rate limiting for firewall."""

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_info,
    press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.firewall.common import get_ufw_status_text


def show_rate_limit_menu():
    """Display rate limiting submenu."""
    def get_status():
        return f"UFW: {get_ufw_status_text()}"
    
    options = [
        ("enable", "1. Enable Rate Limit"),
        ("config", "2. Configure Limits"),
        ("list", "3. List Rate Limits"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "enable": _placeholder,
        "config": _placeholder,
        "list": _placeholder,
    }
    
    run_menu_loop("Rate Limiting", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Rate Limiting", style="cyan")
    show_info("This feature will be implemented in Phase 4.")
    press_enter_to_continue()
```

**Step 4: Create profiles.py placeholder**

```python
"""Application profiles for firewall."""

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_info,
    press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.firewall.common import get_ufw_status_text


def show_profiles_menu():
    """Display application profiles submenu."""
    def get_status():
        return f"UFW: {get_ufw_status_text()}"
    
    options = [
        ("list", "1. List Profiles"),
        ("apply", "2. Apply Profile"),
        ("create", "3. Create Custom Profile"),
        ("edit", "4. Edit/Delete Profile"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "list": _placeholder,
        "apply": _placeholder,
        "create": _placeholder,
        "edit": _placeholder,
    }
    
    run_menu_loop("Application Profiles", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Application Profiles", style="cyan")
    show_info("This feature will be implemented in Phase 5.")
    press_enter_to_continue()
```

**Step 5: Create logs.py placeholder**

```python
"""Logging and monitoring for firewall."""

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_info,
    press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.firewall.common import get_ufw_status_text


def show_logs_menu():
    """Display logs and monitoring submenu."""
    def get_status():
        return f"UFW: {get_ufw_status_text()}"
    
    options = [
        ("view", "1. View Firewall Logs"),
        ("stats", "2. Blocked Attempts Stats"),
        ("settings", "3. Log Settings"),
        ("live", "4. Live Monitor"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "view": _placeholder,
        "stats": _placeholder,
        "settings": _placeholder,
        "live": _placeholder,
    }
    
    run_menu_loop("Logs & Monitoring", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Logs & Monitoring", style="cyan")
    show_info("This feature will be implemented in Phase 6.")
    press_enter_to_continue()
```

**Step 6: Create backup.py placeholder**

```python
"""Backup and restore for firewall."""

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_info,
    press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.firewall.common import get_ufw_status_text


def show_backup_menu():
    """Display backup and restore submenu."""
    def get_status():
        return f"UFW: {get_ufw_status_text()}"
    
    options = [
        ("create", "1. Create Backup"),
        ("restore", "2. Restore Backup"),
        ("compare", "3. Compare Configs"),
        ("auto", "4. Auto-Backup Settings"),
        ("manage", "5. Manage Backups"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "create": _placeholder,
        "restore": _placeholder,
        "compare": _placeholder,
        "auto": _placeholder,
        "manage": _placeholder,
    }
    
    run_menu_loop("Backup & Restore", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Backup & Restore", style="cyan")
    show_info("This feature will be implemented in Phase 7.")
    press_enter_to_continue()
```

**Step 7: Commit**

```bash
git add modules/firewall/ports.py modules/firewall/ip_management.py modules/firewall/rate_limiting.py modules/firewall/profiles.py modules/firewall/logs.py modules/firewall/backup.py
git commit -m "feat(firewall): add placeholder submodules for all features"
```

---

## Task 5: Update Main Module Import

**Files:**
- Modify: `main.py` (update firewall import)

**Step 1: Update main.py import**

Find the line:
```python
from modules import firewall
```

Verify it still works since we're now importing from `modules/firewall/__init__.py` instead of `modules/firewall.py`.

If needed, the import should work automatically due to Python package resolution.

**Step 2: Remove old firewall.py**

```bash
rm modules/firewall.py
```

**Step 3: Commit**

```bash
git add -A
git commit -m "refactor(firewall): complete migration to package structure

- Remove old monolithic firewall.py
- Package now provides all submenus
- All features accessible from main menu"
```

---

## Verification

After completing all tasks, verify:

1. **Menu loads correctly:**
   - Main menu shows "Firewall (UFW)" option
   - Firewall submenu shows all 9 options
   - Status dashboard displays UFW info

2. **All submenus accessible:**
   - Port Management → shows placeholder
   - IP Management → shows placeholder
   - Rate Limiting → shows placeholder
   - Application Profiles → shows placeholder
   - Logs & Monitoring → shows placeholder
   - Backup & Restore → shows placeholder

3. **Enable/Disable work:**
   - Enable creates default rules
   - Disable warns and disables UFW
