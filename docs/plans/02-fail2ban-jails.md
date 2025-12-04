# Fail2ban Phase 2: Jail Management + Templates

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement comprehensive jail management with templates for common applications, custom jail wizard, and enable/disable controls.

**Architecture:** Create jail templates for WordPress, phpMyAdmin, bad bots, etc. Add wizard for custom jail creation with step-by-step guidance. Support enable/disable and editing of existing jails.

**Tech Stack:** Python, Rich (tables, panels), Fail2ban jail.d configs

---

## Task 1: Create Jail Templates Module

**Files:**
- Create: `modules/fail2ban/templates/__init__.py`
- Create: `modules/fail2ban/templates/web_apps.py`
- Create: `modules/fail2ban/templates/web_security.py`

**Step 1: Create templates package init**

```python
"""Jail templates for fail2ban module."""

from .web_apps import WEB_APP_TEMPLATES
from .web_security import WEB_SECURITY_TEMPLATES

# All available templates
ALL_TEMPLATES = {
    **WEB_APP_TEMPLATES,
    **WEB_SECURITY_TEMPLATES,
}


def get_template(name):
    """Get a template by name."""
    return ALL_TEMPLATES.get(name)


def get_templates_by_category():
    """Get templates organized by category."""
    return {
        "Web Applications": WEB_APP_TEMPLATES,
        "Web Security": WEB_SECURITY_TEMPLATES,
    }


def list_templates():
    """List all available templates with descriptions."""
    templates = []
    for name, template in ALL_TEMPLATES.items():
        templates.append({
            "name": name,
            "display_name": template.get("display_name", name),
            "description": template.get("description", ""),
            "category": template.get("category", "Other"),
        })
    return templates
```

**Step 2: Create web_apps.py with WordPress, phpMyAdmin templates**

```python
"""Web application jail templates."""

WEB_APP_TEMPLATES = {
    "wordpress-login": {
        "display_name": "WordPress Login",
        "description": "Protect wp-login.php and xmlrpc.php from brute force",
        "category": "Web Applications",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "5",
            "findtime": "5m",
            "bantime": "1h",
        },
        "filter_content": """[Definition]
# WordPress login brute force protection
failregex = ^<HOST> .* "POST /wp-login\.php
            ^<HOST> .* "POST /xmlrpc\.php
ignoreregex =
""",
        "requirements": ["nginx"],
    },
    
    "wordpress-xmlrpc": {
        "display_name": "WordPress XML-RPC",
        "description": "Block XML-RPC abuse (pingback attacks)",
        "category": "Web Applications",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "3",
            "findtime": "1m",
            "bantime": "24h",
        },
        "filter_content": """[Definition]
# WordPress XML-RPC abuse protection
failregex = ^<HOST> .* "POST /xmlrpc\.php.*" (200|403)
ignoreregex =
""",
        "requirements": ["nginx"],
    },
    
    "phpmyadmin": {
        "display_name": "phpMyAdmin",
        "description": "Protect phpMyAdmin login from brute force",
        "category": "Web Applications",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "5",
            "findtime": "5m",
            "bantime": "1h",
        },
        "filter_content": """[Definition]
# phpMyAdmin brute force protection
failregex = ^<HOST> .* "POST .*/phpmyadmin/index\.php.*" 200
            ^<HOST> .* "POST .*/pma/index\.php.*" 200
            ^<HOST> .* "POST .*/phpMyAdmin/index\.php.*" 200
ignoreregex =
""",
        "requirements": ["nginx"],
    },
    
    "drupal-login": {
        "display_name": "Drupal Login",
        "description": "Protect Drupal user login from brute force",
        "category": "Web Applications",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "5",
            "findtime": "5m",
            "bantime": "1h",
        },
        "filter_content": """[Definition]
# Drupal login brute force protection
failregex = ^<HOST> .* "POST /user/login.*" 200
            ^<HOST> .* "POST /user\?.*" 200
ignoreregex =
""",
        "requirements": ["nginx"],
    },
    
    "joomla-login": {
        "display_name": "Joomla Login",
        "description": "Protect Joomla administrator login",
        "category": "Web Applications",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "5",
            "findtime": "5m",
            "bantime": "1h",
        },
        "filter_content": """[Definition]
# Joomla login brute force protection
failregex = ^<HOST> .* "POST /administrator/index\.php.*" 200
            ^<HOST> .* "POST /administrator/.*" 303
ignoreregex =
""",
        "requirements": ["nginx"],
    },
    
    "laravel-login": {
        "display_name": "Laravel Login",
        "description": "Protect Laravel application login",
        "category": "Web Applications",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "5",
            "findtime": "5m",
            "bantime": "1h",
        },
        "filter_content": """[Definition]
# Laravel login brute force protection
failregex = ^<HOST> .* "POST /login.*" (200|302|422)
            ^<HOST> .* "POST /auth/login.*" (200|302|422)
ignoreregex =
""",
        "requirements": ["nginx"],
    },
}
```

**Step 3: Create web_security.py with security templates**

```python
"""Web security jail templates."""

WEB_SECURITY_TEMPLATES = {
    "nginx-badbots": {
        "display_name": "Bad Bots & Scanners",
        "description": "Block known bad bots, scanners, and crawlers",
        "category": "Web Security",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "1",
            "findtime": "1d",
            "bantime": "7d",
        },
        "filter_content": """[Definition]
# Bad bots and vulnerability scanners
failregex = ^<HOST> .* "(GET|POST).*(?i)(sqlmap|nikto|nmap|masscan|zgrab).*"
            ^<HOST> .* ".*(?i)(acunetix|nessus|openvas|w3af).*"
            ^<HOST> .* ".*User-Agent:.*(?i)(sqlmap|nikto|masscan).*"
ignoreregex =
""",
        "requirements": ["nginx"],
    },
    
    "nginx-noscript": {
        "display_name": "Script Kiddies",
        "description": "Block requests for common vulnerable paths",
        "category": "Web Security",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "2",
            "findtime": "10m",
            "bantime": "1d",
        },
        "filter_content": """[Definition]
# Script kiddie and probe protection
failregex = ^<HOST> .* "(GET|POST).*/(?i)(wp-config|\.env|\.git|\.svn|\.htaccess).*"
            ^<HOST> .* "(GET|POST).*(?i)(phpunit|vendor/phpunit|eval-stdin).*"
            ^<HOST> .* "(GET|POST).*(?i)(shell|c99|r57|b374k).*"
ignoreregex =
""",
        "requirements": ["nginx"],
    },
    
    "nginx-sqli": {
        "display_name": "SQL Injection",
        "description": "Block SQL injection attempts",
        "category": "Web Security",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "1",
            "findtime": "1h",
            "bantime": "1d",
        },
        "filter_content": """[Definition]
# SQL injection attempt protection
failregex = ^<HOST> .* "(GET|POST).*(?i)(union.*select|select.*from|insert.*into|drop.*table|delete.*from).*"
            ^<HOST> .* "(GET|POST).*(?i)(\/\*.*\*\/|;.*--|'.*or.*'|".*or.*).*"
            ^<HOST> .* "(GET|POST).*(?i)(benchmark|sleep|load_file|into.*outfile).*"
ignoreregex =
""",
        "requirements": ["nginx"],
    },
    
    "nginx-traversal": {
        "display_name": "Path Traversal",
        "description": "Block directory traversal attempts",
        "category": "Web Security",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "2",
            "findtime": "10m",
            "bantime": "1d",
        },
        "filter_content": """[Definition]
# Path traversal protection
failregex = ^<HOST> .* "(GET|POST).*(?i)(\.\.\/|\.\.\\\\|%2e%2e%2f|%252e%252e).*"
            ^<HOST> .* "(GET|POST).*(?i)(\/etc\/passwd|\/etc\/shadow|\/proc\/self).*"
            ^<HOST> .* "(GET|POST).*(?i)(boot\.ini|win\.ini|system32).*"
ignoreregex =
""",
        "requirements": ["nginx"],
    },
    
    "nginx-http-flood": {
        "display_name": "HTTP Flood (DDoS)",
        "description": "Rate limit aggressive request patterns",
        "category": "Web Security",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "100",
            "findtime": "1m",
            "bantime": "10m",
        },
        "filter_content": """[Definition]
# HTTP flood/DDoS protection
failregex = ^<HOST> -.*"(GET|POST|HEAD).*
ignoreregex = ^<HOST> .* "(GET|POST).*/health.*"
              ^<HOST> .* "(GET|POST).*/api/.*"
""",
        "requirements": ["nginx"],
        "warning": "May cause false positives on high-traffic sites. Adjust maxretry accordingly.",
    },
    
    "nginx-403-flood": {
        "display_name": "403 Flood",
        "description": "Ban IPs generating many 403 errors",
        "category": "Web Security",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "10",
            "findtime": "5m",
            "bantime": "1h",
        },
        "filter_content": """[Definition]
# 403 error flood protection
failregex = ^<HOST> .* "(GET|POST|HEAD).*" 403
ignoreregex =
""",
        "requirements": ["nginx"],
    },
    
    "nginx-404-flood": {
        "display_name": "404 Flood",
        "description": "Ban IPs generating many 404 errors (scanning)",
        "category": "Web Security",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "20",
            "findtime": "5m",
            "bantime": "30m",
        },
        "filter_content": """[Definition]
# 404 error flood protection (directory scanning)
failregex = ^<HOST> .* "(GET|POST|HEAD).*" 404
ignoreregex = ^<HOST> .* "(GET|POST).*/favicon\.ico.*" 404
              ^<HOST> .* "(GET|POST).*/robots\.txt.*" 404
""",
        "requirements": ["nginx"],
    },
}
```

**Step 4: Commit templates**

```bash
git add modules/fail2ban/templates/
git commit -m "feat(fail2ban): add jail templates for web apps and security"
```

---

## Task 2: Implement Jail Management Module

**Files:**
- Modify: `modules/fail2ban/jails.py`

**Step 1: Implement full jails.py**

```python
"""Jail management for fail2ban module."""

import os

from rich.table import Table

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
from utils.shell import run_command, require_root, service_control

from .common import (
    is_fail2ban_installed,
    is_fail2ban_running,
    get_active_jails,
    get_jail_stats,
    JAIL_D_DIR,
    FILTER_D_DIR,
)
from .templates import get_template, get_templates_by_category, list_templates


def show_menu():
    """Display jail management menu."""
    def get_status():
        jails = get_active_jails()
        return f"{len(jails)} active jails"
    
    def get_options():
        return [
            ("view", "1. View Active Jails"),
            ("enable", "2. Enable/Disable Jail"),
            ("create", "3. Create Custom Jail"),
            ("templates", "4. Install from Template"),
            ("edit", "5. Edit Jail Settings"),
            ("delete", "6. Delete Custom Jail"),
            ("back", "← Back"),
        ]
    
    handlers = {
        "view": view_active_jails,
        "enable": toggle_jail,
        "create": create_custom_jail,
        "templates": install_from_template,
        "edit": edit_jail,
        "delete": delete_jail,
    }
    
    run_menu_loop("Jail Management", get_options, handlers, get_status)


def view_active_jails():
    """View all active jails with statistics."""
    clear_screen()
    show_header()
    show_panel("Active Jails", title="Jail Management", style="cyan")
    
    jails = get_active_jails()
    
    if not jails:
        show_info("No active jails found.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Jail", "style": "cyan"},
        {"name": "Currently Banned", "justify": "center"},
        {"name": "Total Banned", "justify": "center"},
        {"name": "Failed", "justify": "center"},
    ]
    
    rows = []
    for jail in jails:
        stats = get_jail_stats(jail)
        rows.append([
            jail,
            str(stats.get('currently_banned', 0)),
            str(stats.get('total_banned', 0)),
            str(stats.get('failed', 0)),
        ])
    
    show_table("Active Jails", columns, rows)
    
    # Option to view details
    console.print()
    jail = select_from_list(
        title="View Details",
        message="Select jail for details (or cancel):",
        options=jails + ["(cancel)"]
    )
    
    if jail and jail != "(cancel)":
        view_jail_details(jail)
    
    press_enter_to_continue()


def view_jail_details(jail):
    """View detailed information for a specific jail."""
    console.print()
    result = run_command(f"fail2ban-client status {jail}", check=False, silent=True)
    
    if result.returncode != 0:
        show_error(f"Failed to get details for {jail}")
        return
    
    console.print(f"[bold cyan]Jail: {jail}[/bold cyan]")
    console.print()
    console.print(result.stdout)
    
    # Show config file location
    jail_file = os.path.join(JAIL_D_DIR, f"{jail}.conf")
    if os.path.exists(jail_file):
        console.print()
        console.print(f"[dim]Config: {jail_file}[/dim]")


def toggle_jail():
    """Enable or disable a jail."""
    clear_screen()
    show_header()
    show_panel("Enable/Disable Jail", title="Jail Management", style="cyan")
    
    # Get all configured jails (not just active)
    all_jails = _get_all_configured_jails()
    active_jails = get_active_jails()
    
    if not all_jails:
        show_info("No jails configured.")
        press_enter_to_continue()
        return
    
    # Build options with status
    options = []
    for jail in all_jails:
        status = "[green]enabled[/green]" if jail in active_jails else "[red]disabled[/red]"
        options.append((jail, f"{jail} ({status})"))
    
    jail = select_from_list(
        title="Select Jail",
        message="Select jail to toggle:",
        options=[o[0] for o in options],
        display_options=[o[1] for o in options]
    )
    
    if not jail:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    is_enabled = jail in active_jails
    action = "disable" if is_enabled else "enable"
    
    if not confirm_action(f"{action.capitalize()} jail '{jail}'?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = _toggle_jail_state(jail, not is_enabled)
    
    if success:
        service_control("fail2ban", "reload")
        show_success(f"Jail '{jail}' {action}d!")
    else:
        show_error(f"Failed to {action} jail.")
    
    press_enter_to_continue()


def create_custom_jail():
    """Create a custom jail with wizard."""
    clear_screen()
    show_header()
    show_panel("Create Custom Jail", title="Jail Management", style="cyan")
    
    console.print("[bold]Custom Jail Wizard[/bold]")
    console.print("[dim]Create a jail for any log file with custom pattern.[/dim]")
    console.print()
    
    # Step 1: Jail name
    name = text_input(
        title="Step 1: Jail Name",
        message="Enter jail name (lowercase, no spaces):"
    )
    
    if not name:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Validate name
    name = name.lower().replace(" ", "-")
    if not name.replace("-", "").replace("_", "").isalnum():
        show_error("Invalid name. Use only letters, numbers, dashes, underscores.")
        press_enter_to_continue()
        return
    
    # Check if exists
    if _jail_exists(name):
        show_error(f"Jail '{name}' already exists.")
        press_enter_to_continue()
        return
    
    # Step 2: Log file
    console.print()
    logpath = text_input(
        title="Step 2: Log File",
        message="Enter path to log file:",
        default="/var/log/nginx/access.log"
    )
    
    if not logpath:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not os.path.exists(logpath):
        show_warning(f"Log file does not exist: {logpath}")
        if not confirm_action("Continue anyway?"):
            press_enter_to_continue()
            return
    
    # Step 3: Fail regex
    console.print()
    console.print("[dim]Enter the regex pattern to match failed attempts.[/dim]")
    console.print("[dim]Use <HOST> to capture the IP address.[/dim]")
    console.print("[dim]Example: ^<HOST> .* \"POST /login\" .* 401[/dim]")
    console.print()
    
    failregex = text_input(
        title="Step 3: Fail Pattern",
        message="Enter failregex pattern:"
    )
    
    if not failregex:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Step 4: Settings
    console.print()
    maxretry = text_input(
        title="Step 4: Max Retry",
        message="Max failures before ban:",
        default="5"
    )
    
    findtime = text_input(
        title="Step 4: Find Time",
        message="Time window for failures:",
        default="10m"
    )
    
    bantime = text_input(
        title="Step 4: Ban Time",
        message="Ban duration:",
        default="1h"
    )
    
    port = text_input(
        title="Step 4: Port",
        message="Port(s) to block:",
        default="http,https"
    )
    
    # Confirm
    console.print()
    console.print("[bold]Review:[/bold]")
    console.print(f"  Name: {name}")
    console.print(f"  Log: {logpath}")
    console.print(f"  Pattern: {failregex}")
    console.print(f"  Max Retry: {maxretry}")
    console.print(f"  Find Time: {findtime}")
    console.print(f"  Ban Time: {bantime}")
    console.print(f"  Port: {port}")
    console.print()
    
    if not confirm_action("Create this jail?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Create filter and jail
    success = _create_jail(
        name=name,
        logpath=logpath,
        failregex=failregex,
        maxretry=maxretry,
        findtime=findtime,
        bantime=bantime,
        port=port
    )
    
    if success:
        service_control("fail2ban", "reload")
        show_success(f"Jail '{name}' created and enabled!")
    else:
        show_error("Failed to create jail.")
    
    press_enter_to_continue()


def install_from_template():
    """Install a jail from predefined template."""
    clear_screen()
    show_header()
    show_panel("Install from Template", title="Jail Management", style="cyan")
    
    templates_by_cat = get_templates_by_category()
    
    # Build category menu
    categories = list(templates_by_cat.keys())
    category = select_from_list(
        title="Select Category",
        message="Choose template category:",
        options=categories
    )
    
    if not category:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Build template menu for category
    templates = templates_by_cat[category]
    template_options = []
    template_display = []
    
    for name, template in templates.items():
        template_options.append(name)
        installed = "[green](installed)[/green]" if _jail_exists(name) else ""
        template_display.append(f"{template['display_name']} {installed}")
    
    template_name = select_from_list(
        title=f"Select Template - {category}",
        message="Choose template to install:",
        options=template_options,
        display_options=template_display
    )
    
    if not template_name:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    template = get_template(template_name)
    
    # Show template details
    console.print()
    console.print(f"[bold]{template['display_name']}[/bold]")
    console.print(f"[dim]{template['description']}[/dim]")
    console.print()
    
    config = template['jail_config']
    console.print("[bold]Settings:[/bold]")
    console.print(f"  Log Path: {config['logpath']}")
    console.print(f"  Max Retry: {config['maxretry']}")
    console.print(f"  Find Time: {config['findtime']}")
    console.print(f"  Ban Time: {config['bantime']}")
    
    if template.get('warning'):
        console.print()
        console.print(f"[yellow]Warning: {template['warning']}[/yellow]")
    
    console.print()
    
    if _jail_exists(template_name):
        show_warning(f"Jail '{template_name}' already exists.")
        if not confirm_action("Overwrite existing jail?"):
            press_enter_to_continue()
            return
    
    if not confirm_action("Install this template?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = _install_template(template_name, template)
    
    if success:
        service_control("fail2ban", "reload")
        show_success(f"Template '{template['display_name']}' installed!")
    else:
        show_error("Failed to install template.")
    
    press_enter_to_continue()


def edit_jail():
    """Edit an existing jail's settings."""
    clear_screen()
    show_header()
    show_panel("Edit Jail Settings", title="Jail Management", style="cyan")
    
    # Get custom jails only (from jail.d)
    custom_jails = _get_custom_jails()
    
    if not custom_jails:
        show_info("No custom jails to edit. System jails should be edited in jail.local.")
        press_enter_to_continue()
        return
    
    jail = select_from_list(
        title="Select Jail",
        message="Choose jail to edit:",
        options=custom_jails
    )
    
    if not jail:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Read current settings
    current = _read_jail_config(jail)
    
    if not current:
        show_error(f"Could not read config for {jail}")
        press_enter_to_continue()
        return
    
    # Edit settings
    console.print(f"[bold]Editing: {jail}[/bold]")
    console.print()
    
    maxretry = text_input(
        title="Max Retry",
        message="Max failures before ban:",
        default=current.get('maxretry', '5')
    )
    
    findtime = text_input(
        title="Find Time",
        message="Time window for failures:",
        default=current.get('findtime', '10m')
    )
    
    bantime = text_input(
        title="Ban Time",
        message="Ban duration:",
        default=current.get('bantime', '1h')
    )
    
    if not confirm_action("Save changes?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = _update_jail_config(jail, {
        'maxretry': maxretry,
        'findtime': findtime,
        'bantime': bantime,
    })
    
    if success:
        service_control("fail2ban", "reload")
        show_success(f"Jail '{jail}' updated!")
    else:
        show_error("Failed to update jail.")
    
    press_enter_to_continue()


def delete_jail():
    """Delete a custom jail."""
    clear_screen()
    show_header()
    show_panel("Delete Custom Jail", title="Jail Management", style="cyan")
    
    custom_jails = _get_custom_jails()
    
    if not custom_jails:
        show_info("No custom jails to delete.")
        press_enter_to_continue()
        return
    
    jail = select_from_list(
        title="Select Jail",
        message="Choose jail to delete:",
        options=custom_jails
    )
    
    if not jail:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print(f"[yellow]Warning: This will delete jail '{jail}' and its filter.[/yellow]")
    console.print()
    
    if not confirm_action(f"Delete jail '{jail}'?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = _delete_jail(jail)
    
    if success:
        service_control("fail2ban", "reload")
        show_success(f"Jail '{jail}' deleted!")
    else:
        show_error("Failed to delete jail.")
    
    press_enter_to_continue()


# Helper functions

def _get_all_configured_jails():
    """Get all configured jails (enabled and disabled)."""
    jails = set()
    
    # From jail.local
    from .common import JAIL_LOCAL
    if os.path.exists(JAIL_LOCAL):
        try:
            with open(JAIL_LOCAL, 'r') as f:
                for line in f:
                    if line.strip().startswith('[') and line.strip() != '[DEFAULT]':
                        jail = line.strip()[1:-1]
                        jails.add(jail)
        except Exception:
            pass
    
    # From jail.d/
    if os.path.exists(JAIL_D_DIR):
        for filename in os.listdir(JAIL_D_DIR):
            if filename.endswith('.conf'):
                jails.add(filename[:-5])
    
    return sorted(list(jails))


def _get_custom_jails():
    """Get jails defined in jail.d/ directory."""
    jails = []
    if os.path.exists(JAIL_D_DIR):
        for filename in os.listdir(JAIL_D_DIR):
            if filename.endswith('.conf'):
                jails.append(filename[:-5])
    return sorted(jails)


def _jail_exists(name):
    """Check if a jail already exists."""
    jail_file = os.path.join(JAIL_D_DIR, f"{name}.conf")
    return os.path.exists(jail_file) or name in get_active_jails()


def _toggle_jail_state(jail, enable):
    """Enable or disable a jail."""
    jail_file = os.path.join(JAIL_D_DIR, f"{jail}.conf")
    
    if os.path.exists(jail_file):
        # Update enabled state in jail.d file
        try:
            with open(jail_file, 'r') as f:
                lines = f.readlines()
            
            new_lines = []
            for line in lines:
                if line.strip().startswith('enabled'):
                    new_lines.append(f"enabled = {'true' if enable else 'false'}\n")
                else:
                    new_lines.append(line)
            
            with open(jail_file, 'w') as f:
                f.writelines(new_lines)
            
            return True
        except Exception:
            return False
    
    return False


def _create_jail(name, logpath, failregex, maxretry, findtime, bantime, port):
    """Create a custom jail with filter."""
    # Create filter
    filter_content = f"""[Definition]
# Custom filter: {name}
# Generated by vexo-cli

failregex = {failregex}
ignoreregex =
"""
    
    filter_file = os.path.join(FILTER_D_DIR, f"{name}.conf")
    try:
        with open(filter_file, 'w') as f:
            f.write(filter_content)
    except Exception as e:
        show_error(f"Failed to create filter: {e}")
        return False
    
    # Create jail
    jail_content = f"""[{name}]
# Custom jail: {name}
# Generated by vexo-cli

enabled = true
port = {port}
filter = {name}
logpath = {logpath}
maxretry = {maxretry}
findtime = {findtime}
bantime = {bantime}
"""
    
    jail_file = os.path.join(JAIL_D_DIR, f"{name}.conf")
    try:
        os.makedirs(JAIL_D_DIR, exist_ok=True)
        with open(jail_file, 'w') as f:
            f.write(jail_content)
    except Exception as e:
        show_error(f"Failed to create jail: {e}")
        return False
    
    return True


def _install_template(name, template):
    """Install a jail from template."""
    # Create filter
    filter_file = os.path.join(FILTER_D_DIR, f"{name}.conf")
    try:
        with open(filter_file, 'w') as f:
            f.write(template['filter_content'])
    except Exception as e:
        show_error(f"Failed to create filter: {e}")
        return False
    
    # Create jail config
    config = template['jail_config']
    jail_content = f"""[{name}]
# Template: {template['display_name']}
# {template['description']}
# Generated by vexo-cli

enabled = {config['enabled']}
port = {config['port']}
filter = {name}
logpath = {config['logpath']}
maxretry = {config['maxretry']}
findtime = {config['findtime']}
bantime = {config['bantime']}
"""
    
    jail_file = os.path.join(JAIL_D_DIR, f"{name}.conf")
    try:
        os.makedirs(JAIL_D_DIR, exist_ok=True)
        with open(jail_file, 'w') as f:
            f.write(jail_content)
    except Exception as e:
        show_error(f"Failed to create jail: {e}")
        return False
    
    return True


def _read_jail_config(jail):
    """Read jail configuration from file."""
    jail_file = os.path.join(JAIL_D_DIR, f"{jail}.conf")
    config = {}
    
    if not os.path.exists(jail_file):
        return config
    
    try:
        with open(jail_file, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    except Exception:
        pass
    
    return config


def _update_jail_config(jail, updates):
    """Update jail configuration."""
    jail_file = os.path.join(JAIL_D_DIR, f"{jail}.conf")
    
    try:
        with open(jail_file, 'r') as f:
            lines = f.readlines()
        
        new_lines = []
        for line in lines:
            updated = False
            for key, value in updates.items():
                if line.strip().startswith(f"{key} ") or line.strip().startswith(f"{key}="):
                    new_lines.append(f"{key} = {value}\n")
                    updated = True
                    break
            if not updated:
                new_lines.append(line)
        
        with open(jail_file, 'w') as f:
            f.writelines(new_lines)
        
        return True
    except Exception:
        return False


def _delete_jail(jail):
    """Delete a jail and its filter."""
    jail_file = os.path.join(JAIL_D_DIR, f"{jail}.conf")
    filter_file = os.path.join(FILTER_D_DIR, f"{jail}.conf")
    
    success = True
    
    if os.path.exists(jail_file):
        try:
            os.remove(jail_file)
        except Exception:
            success = False
    
    if os.path.exists(filter_file):
        try:
            os.remove(filter_file)
        except Exception:
            pass  # Filter might be shared
    
    return success
```

**Step 2: Update jails.py imports in __init__.py (if needed)**

The __init__.py already has lazy imports, so no change needed.

**Step 3: Commit jail management**

```bash
git add modules/fail2ban/jails.py
git commit -m "feat(fail2ban): implement jail management with templates and wizard"
```

---

## Verification

After completing all tasks:

1. Templates available in `modules/fail2ban/templates/`:
   - `web_apps.py` - WordPress, phpMyAdmin, Drupal, Joomla, Laravel
   - `web_security.py` - Bad bots, SQL injection, path traversal, floods

2. Jail management features:
   - View active jails with statistics
   - Enable/disable jails
   - Create custom jails with wizard
   - Install from templates
   - Edit jail settings
   - Delete custom jails

3. All jails stored in `/etc/fail2ban/jail.d/` for clean organization
