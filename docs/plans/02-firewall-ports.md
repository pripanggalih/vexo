# Phase 2: Port Management + Presets

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement comprehensive port management with custom port addition, port presets for common services, and port removal functionality.

**Architecture:** Create presets.py for port definitions, update ports.py with full implementation including multi-select preset application.

**Tech Stack:** Python, Rich (tables, checkboxes), InquirerPy (multi-select), UFW CLI

---

## Task 1: Create Port Presets Definitions

**Files:**
- Create: `modules/firewall/presets.py`

**Step 1: Create presets.py with all port categories**

```python
"""Port preset definitions for common services."""

# Web Stack
WEB_PRESETS = [
    {"port": "80", "protocol": "tcp", "name": "HTTP", "description": "Web server"},
    {"port": "443", "protocol": "tcp", "name": "HTTPS", "description": "Secure web server"},
    {"port": "443", "protocol": "udp", "name": "HTTP/3", "description": "QUIC protocol"},
]

# Database
DATABASE_PRESETS = [
    {"port": "3306", "protocol": "tcp", "name": "MySQL", "description": "MySQL/MariaDB"},
    {"port": "5432", "protocol": "tcp", "name": "PostgreSQL", "description": "PostgreSQL"},
    {"port": "27017", "protocol": "tcp", "name": "MongoDB", "description": "MongoDB"},
    {"port": "6379", "protocol": "tcp", "name": "Redis", "description": "Redis cache"},
    {"port": "11211", "protocol": "tcp", "name": "Memcached", "description": "Memcached"},
]

# Mail Server
MAIL_PRESETS = [
    {"port": "25", "protocol": "tcp", "name": "SMTP", "description": "Mail transfer"},
    {"port": "587", "protocol": "tcp", "name": "Submission", "description": "Mail submission"},
    {"port": "465", "protocol": "tcp", "name": "SMTPS", "description": "SMTP over SSL"},
    {"port": "143", "protocol": "tcp", "name": "IMAP", "description": "Mail access"},
    {"port": "993", "protocol": "tcp", "name": "IMAPS", "description": "IMAP over SSL"},
    {"port": "110", "protocol": "tcp", "name": "POP3", "description": "Mail retrieval"},
    {"port": "995", "protocol": "tcp", "name": "POP3S", "description": "POP3 over SSL"},
]

# Development
DEV_PRESETS = [
    {"port": "21", "protocol": "tcp", "name": "FTP", "description": "File transfer"},
    {"port": "22", "protocol": "tcp", "name": "SSH", "description": "Secure shell"},
    {"port": "9418", "protocol": "tcp", "name": "Git", "description": "Git protocol"},
    {"port": "3000", "protocol": "tcp", "name": "Node.js", "description": "Node.js dev server"},
    {"port": "5000", "protocol": "tcp", "name": "Flask", "description": "Flask/Django dev"},
    {"port": "8080", "protocol": "tcp", "name": "Alt HTTP", "description": "Alternative HTTP"},
    {"port": "8443", "protocol": "tcp", "name": "Alt HTTPS", "description": "Alternative HTTPS"},
]

# Other Services
OTHER_PRESETS = [
    {"port": "53", "protocol": "tcp", "name": "DNS (TCP)", "description": "Domain name system"},
    {"port": "53", "protocol": "udp", "name": "DNS (UDP)", "description": "Domain name system"},
    {"port": "123", "protocol": "udp", "name": "NTP", "description": "Network time"},
    {"port": "51820", "protocol": "udp", "name": "WireGuard", "description": "WireGuard VPN"},
    {"port": "1194", "protocol": "udp", "name": "OpenVPN", "description": "OpenVPN"},
]

# All presets grouped by category
ALL_PRESETS = {
    "web": {"name": "Web Stack", "ports": WEB_PRESETS},
    "database": {"name": "Database", "ports": DATABASE_PRESETS},
    "mail": {"name": "Mail Server", "ports": MAIL_PRESETS},
    "dev": {"name": "Development", "ports": DEV_PRESETS},
    "other": {"name": "Other Services", "ports": OTHER_PRESETS},
}


def get_preset_display(preset, is_open=False):
    """Get display string for a preset."""
    status = "[green]✓[/green] " if is_open else "  "
    return f"{status}{preset['name']} ({preset['port']}/{preset['protocol']}) - {preset['description']}"


def get_all_presets_flat():
    """Get all presets as a flat list."""
    all_ports = []
    for category in ALL_PRESETS.values():
        all_ports.extend(category["ports"])
    return all_ports
```

**Step 2: Commit**

```bash
git add modules/firewall/presets.py
git commit -m "feat(firewall): add port preset definitions for all categories"
```

---

## Task 2: Implement Add Custom Port

**Files:**
- Modify: `modules/firewall/ports.py`

**Step 1: Replace ports.py with full implementation**

```python
"""Port management for firewall."""

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
from ui.menu import run_menu_loop, text_input, select_from_list, confirm_action
from utils.shell import run_command, require_root
from modules.firewall.common import (
    is_ufw_installed,
    get_ufw_status_text,
    get_ufw_rules,
)


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
        "add": add_custom_port,
        "presets": show_presets_menu,
        "remove": remove_port,
        "list": list_ports,
    }
    
    run_menu_loop("Port Management", options, handlers, get_status)


def add_custom_port():
    """Add a custom port to firewall."""
    clear_screen()
    show_header()
    show_panel("Add Custom Port", title="Port Management", style="cyan")
    
    if not is_ufw_installed():
        show_error("UFW is not installed. Enable firewall first.")
        press_enter_to_continue()
        return
    
    # Get port number
    port = text_input(
        title="Port",
        message="Enter port number (e.g., 8080) or range (e.g., 6000:6010):"
    )
    
    if not port:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Validate port
    if not _validate_port(port):
        show_error("Invalid port. Use single port (1-65535) or range (e.g., 6000:6010).")
        press_enter_to_continue()
        return
    
    # Get protocol
    protocol = select_from_list(
        title="Protocol",
        message="Select protocol:",
        options=["tcp", "udp", "both"]
    )
    
    if not protocol:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Ask for IP restriction (optional)
    restrict_ip = confirm_action("Restrict to specific IP/CIDR? (default: allow from anywhere)")
    
    from_ip = None
    if restrict_ip:
        from_ip = text_input(
            title="Source IP",
            message="Enter source IP or CIDR (e.g., 192.168.1.0/24):"
        )
        if from_ip and not _validate_ip(from_ip):
            show_error("Invalid IP address or CIDR notation.")
            press_enter_to_continue()
            return
    
    # Confirm
    rule_desc = f"Port {port}/{protocol}"
    if from_ip:
        rule_desc += f" from {from_ip}"
    else:
        rule_desc += " from anywhere"
    
    if not confirm_action(f"Add rule: {rule_desc}?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Add the rule
    success = _add_port_rule(port, protocol, from_ip)
    
    if success:
        show_success(f"Port {port} added successfully!")
    else:
        show_error(f"Failed to add port {port}")
    
    press_enter_to_continue()


def _validate_port(port_str):
    """Validate port number or range."""
    if ':' in port_str:
        parts = port_str.split(':')
        if len(parts) != 2:
            return False
        try:
            start, end = int(parts[0]), int(parts[1])
            return 1 <= start <= 65535 and 1 <= end <= 65535 and start < end
        except ValueError:
            return False
    else:
        try:
            port = int(port_str)
            return 1 <= port <= 65535
        except ValueError:
            return False


def _validate_ip(ip_str):
    """Basic validation for IP or CIDR."""
    import re
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}(/\d{1,2})?$'
    return bool(re.match(ip_pattern, ip_str))


def _add_port_rule(port, protocol, from_ip=None):
    """Add a port rule to UFW."""
    protocols = ["tcp", "udp"] if protocol == "both" else [protocol]
    success = True
    
    for proto in protocols:
        if from_ip:
            cmd = f"ufw allow from {from_ip} to any port {port} proto {proto}"
        else:
            cmd = f"ufw allow {port}/{proto}"
        
        result = run_command(cmd, check=False, silent=True)
        if result.returncode != 0:
            success = False
            console.print(f"  [red]✗[/red] Failed: {port}/{proto}")
        else:
            console.print(f"  [green]✓[/green] Added: {port}/{proto}")
    
    return success


def list_ports():
    """List all open ports."""
    clear_screen()
    show_header()
    show_panel("Open Ports", title="Port Management", style="cyan")
    
    if not is_ufw_installed():
        show_error("UFW is not installed.")
        press_enter_to_continue()
        return
    
    rules = get_ufw_rules()
    
    if not rules:
        show_info("No firewall rules configured.")
        press_enter_to_continue()
        return
    
    # Parse and display rules
    columns = [
        {"name": "#", "style": "dim", "justify": "right"},
        {"name": "Port/Service", "style": "cyan"},
        {"name": "Action", "justify": "center"},
        {"name": "From"},
    ]
    
    rows = []
    for rule in rules:
        parts = _parse_rule(rule["rule"])
        rows.append([
            str(rule["number"]),
            parts["port"],
            parts["action"],
            parts["from"],
        ])
    
    show_table("Firewall Rules", columns, rows)
    
    press_enter_to_continue()


def _parse_rule(rule_str):
    """Parse UFW rule string into components."""
    parts = {"port": "", "action": "", "from": "Anywhere"}
    
    rule_parts = rule_str.split()
    if len(rule_parts) >= 1:
        parts["port"] = rule_parts[0]
    
    if "ALLOW" in rule_str:
        parts["action"] = "[green]ALLOW[/green]"
    elif "DENY" in rule_str:
        parts["action"] = "[red]DENY[/red]"
    elif "LIMIT" in rule_str:
        parts["action"] = "[yellow]LIMIT[/yellow]"
    elif "REJECT" in rule_str:
        parts["action"] = "[red]REJECT[/red]"
    
    if "from" in rule_str.lower():
        from_idx = rule_str.lower().find("from")
        parts["from"] = rule_str[from_idx:].split()[1] if from_idx >= 0 else "Anywhere"
    
    return parts


def remove_port():
    """Remove a port rule."""
    clear_screen()
    show_header()
    show_panel("Remove Port", title="Port Management", style="cyan")
    
    if not is_ufw_installed():
        show_error("UFW is not installed.")
        press_enter_to_continue()
        return
    
    rules = get_ufw_rules()
    
    if not rules:
        show_info("No rules to remove.")
        press_enter_to_continue()
        return
    
    # Display rules
    console.print("[bold]Current rules:[/bold]")
    for rule in rules:
        console.print(f"  {rule['number']}. {rule['rule']}")
    console.print()
    
    # Get rule number
    rule_num = text_input(
        title="Remove",
        message="Enter rule number to remove:"
    )
    
    if not rule_num:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        num = int(rule_num)
        if num < 1 or num > len(rules):
            raise ValueError()
    except ValueError:
        show_error("Invalid rule number.")
        press_enter_to_continue()
        return
    
    selected_rule = rules[num - 1]["rule"]
    
    if not confirm_action(f"Remove rule: {selected_rule}?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    result = run_command(f"ufw --force delete {num}", check=False, silent=True)
    
    if result.returncode == 0:
        show_success("Rule removed successfully!")
    else:
        show_error("Failed to remove rule.")
    
    press_enter_to_continue()


def show_presets_menu():
    """Show port presets submenu."""
    from modules.firewall.presets import ALL_PRESETS
    
    def get_status():
        return f"UFW: {get_ufw_status_text()}"
    
    options = [
        ("web", "1. Web Stack (HTTP, HTTPS, HTTP/3)"),
        ("database", "2. Database (MySQL, PostgreSQL, etc.)"),
        ("mail", "3. Mail Server (SMTP, IMAP, POP3)"),
        ("dev", "4. Development (FTP, Git, Node.js, etc.)"),
        ("other", "5. Other Services (DNS, NTP, VPN)"),
        ("all", "6. Quick Select All Categories"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "web": lambda: apply_preset_category("web"),
        "database": lambda: apply_preset_category("database"),
        "mail": lambda: apply_preset_category("mail"),
        "dev": lambda: apply_preset_category("dev"),
        "other": lambda: apply_preset_category("other"),
        "all": apply_all_presets,
    }
    
    run_menu_loop("Port Presets", options, handlers, get_status)


def apply_preset_category(category):
    """Apply ports from a specific preset category."""
    from modules.firewall.presets import ALL_PRESETS
    from InquirerPy import inquirer
    from InquirerPy.base.control import Choice
    
    clear_screen()
    show_header()
    
    preset_info = ALL_PRESETS.get(category)
    if not preset_info:
        show_error(f"Unknown category: {category}")
        press_enter_to_continue()
        return
    
    show_panel(f"Select {preset_info['name']} Ports", title="Port Presets", style="cyan")
    
    if not is_ufw_installed():
        show_error("UFW is not installed. Enable firewall first.")
        press_enter_to_continue()
        return
    
    # Get currently open ports
    open_ports = _get_open_ports()
    
    # Build choices
    choices = []
    for preset in preset_info["ports"]:
        port_key = f"{preset['port']}/{preset['protocol']}"
        is_open = port_key in open_ports
        status = "[green]✓[/green] " if is_open else ""
        label = f"{status}{preset['name']} ({port_key}) - {preset['description']}"
        choices.append(Choice(value=preset, name=label, enabled=is_open))
    
    try:
        selected = inquirer.checkbox(
            message="Select ports to open (space to toggle, enter to apply):",
            choices=choices,
            cycle=True,
        ).execute()
    except KeyboardInterrupt:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not selected:
        show_info("No ports selected.")
        press_enter_to_continue()
        return
    
    # Filter out already open ports
    to_add = [p for p in selected if f"{p['port']}/{p['protocol']}" not in open_ports]
    
    if not to_add:
        show_info("All selected ports are already open.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print("[bold]Ports to add:[/bold]")
    for p in to_add:
        console.print(f"  • {p['name']} ({p['port']}/{p['protocol']})")
    console.print()
    
    if not confirm_action(f"Add {len(to_add)} port(s)?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Add ports
    success_count = 0
    for preset in to_add:
        cmd = f"ufw allow {preset['port']}/{preset['protocol']}"
        result = run_command(cmd, check=False, silent=True)
        if result.returncode == 0:
            console.print(f"  [green]✓[/green] {preset['name']} ({preset['port']}/{preset['protocol']})")
            success_count += 1
        else:
            console.print(f"  [red]✗[/red] {preset['name']} ({preset['port']}/{preset['protocol']})")
    
    console.print()
    if success_count == len(to_add):
        show_success(f"Added {success_count} port(s) successfully!")
    else:
        show_warning(f"Added {success_count}/{len(to_add)} ports.")
    
    press_enter_to_continue()


def apply_all_presets():
    """Quick apply all preset categories."""
    from modules.firewall.presets import get_all_presets_flat
    from InquirerPy import inquirer
    from InquirerPy.base.control import Choice
    from InquirerPy.separator import Separator
    
    clear_screen()
    show_header()
    show_panel("Quick Select All Categories", title="Port Presets", style="cyan")
    
    if not is_ufw_installed():
        show_error("UFW is not installed. Enable firewall first.")
        press_enter_to_continue()
        return
    
    open_ports = _get_open_ports()
    all_presets = get_all_presets_flat()
    
    # Build choices with separators
    from modules.firewall.presets import ALL_PRESETS
    
    choices = []
    for cat_key, cat_info in ALL_PRESETS.items():
        choices.append(Separator(f"── {cat_info['name']} ──"))
        for preset in cat_info["ports"]:
            port_key = f"{preset['port']}/{preset['protocol']}"
            is_open = port_key in open_ports
            status = "[green]✓[/green] " if is_open else ""
            label = f"{status}{preset['name']} ({port_key})"
            choices.append(Choice(value=preset, name=label, enabled=is_open))
    
    try:
        selected = inquirer.checkbox(
            message="Select ports (space to toggle, enter to apply):",
            choices=choices,
            cycle=True,
        ).execute()
    except KeyboardInterrupt:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not selected:
        show_info("No ports selected.")
        press_enter_to_continue()
        return
    
    to_add = [p for p in selected if f"{p['port']}/{p['protocol']}" not in open_ports]
    
    if not to_add:
        show_info("All selected ports are already open.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print(f"[bold]Adding {len(to_add)} port(s)...[/bold]")
    
    if not confirm_action("Proceed?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success_count = 0
    for preset in to_add:
        cmd = f"ufw allow {preset['port']}/{preset['protocol']}"
        result = run_command(cmd, check=False, silent=True)
        if result.returncode == 0:
            console.print(f"  [green]✓[/green] {preset['name']}")
            success_count += 1
        else:
            console.print(f"  [red]✗[/red] {preset['name']}")
    
    console.print()
    show_success(f"Added {success_count}/{len(to_add)} ports!")
    
    press_enter_to_continue()


def _get_open_ports():
    """Get set of currently open ports (port/protocol format)."""
    result = run_command("ufw status", check=False, silent=True)
    if result.returncode != 0:
        return set()
    
    open_ports = set()
    for line in result.stdout.split('\n'):
        line = line.strip()
        if not line or line.startswith('Status') or line.startswith('To') or line.startswith('--'):
            continue
        
        parts = line.split()
        if len(parts) >= 1:
            port_proto = parts[0]
            if '/' in port_proto:
                open_ports.add(port_proto.lower())
            else:
                open_ports.add(f"{port_proto}/tcp")
                open_ports.add(f"{port_proto}/udp")
    
    return open_ports
```

**Step 2: Commit**

```bash
git add modules/firewall/ports.py
git commit -m "feat(firewall): implement port management with custom ports and presets"
```

---

## Verification

After completing all tasks, verify:

1. **Add Custom Port works:**
   - Single port (8080)
   - Port range (6000:6010)
   - Both protocols
   - IP restriction option

2. **Port Presets work:**
   - Each category shows correct ports
   - Already open ports marked with ✓
   - Multi-select with checkbox works
   - Only new ports are added

3. **Remove Port works:**
   - Lists current rules
   - Removes selected rule

4. **List Ports works:**
   - Shows all current rules in table format
