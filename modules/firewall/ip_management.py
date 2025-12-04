"""IP management for firewall."""

import re
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
    load_ip_groups,
    save_ip_groups,
    create_ip_group,
    delete_ip_group,
    add_ip_to_group,
    remove_ip_from_group,
    ensure_config_dir,
)


def show_ip_menu():
    """Display IP management submenu."""
    def get_status():
        groups = load_ip_groups()
        return f"UFW: {get_ufw_status_text()} | IP Groups: {len(groups)}"
    
    options = [
        ("allow", "1. Allow IP"),
        ("deny", "2. Deny/Block IP"),
        ("whitelist", "3. IP Whitelist"),
        ("groups", "4. IP Groups"),
        ("list", "5. List IP Rules"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "allow": allow_ip,
        "deny": deny_ip,
        "whitelist": manage_whitelist,
        "groups": manage_ip_groups,
        "list": list_ip_rules,
    }
    
    run_menu_loop("IP Management", options, handlers, get_status)


def allow_ip():
    """Allow traffic from an IP address."""
    clear_screen()
    show_header()
    show_panel("Allow IP", title="IP Management", style="cyan")
    
    if not is_ufw_installed():
        show_error("UFW is not installed.")
        press_enter_to_continue()
        return
    
    # Mode selection
    mode = select_from_list(
        title="Mode",
        message="Select mode:",
        options=["Simple (IP only)", "Advanced (IP + port/protocol)"]
    )
    
    if not mode:
        press_enter_to_continue()
        return
    
    # Get IP
    ip = text_input(
        title="IP Address",
        message="Enter IP address or CIDR (e.g., 192.168.1.100 or 10.0.0.0/8):"
    )
    
    if not ip:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not _validate_ip_or_cidr(ip):
        show_error("Invalid IP address or CIDR notation.")
        press_enter_to_continue()
        return
    
    if "Simple" in mode:
        # Simple mode - allow all from IP
        _apply_ip_rule(ip, "allow")
    else:
        # Advanced mode
        _apply_advanced_ip_rule(ip, "allow")
    
    press_enter_to_continue()


def deny_ip():
    """Deny/block traffic from an IP address."""
    clear_screen()
    show_header()
    show_panel("Deny/Block IP", title="IP Management", style="cyan")
    
    if not is_ufw_installed():
        show_error("UFW is not installed.")
        press_enter_to_continue()
        return
    
    # Mode selection
    mode = select_from_list(
        title="Mode",
        message="Select mode:",
        options=["Simple (block all)", "Advanced (block specific ports)"]
    )
    
    if not mode:
        press_enter_to_continue()
        return
    
    # Get IP
    ip = text_input(
        title="IP Address",
        message="Enter IP address or CIDR to block:"
    )
    
    if not ip:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not _validate_ip_or_cidr(ip):
        show_error("Invalid IP address or CIDR notation.")
        press_enter_to_continue()
        return
    
    # Action type
    action = select_from_list(
        title="Action",
        message="Select action type:",
        options=["deny (silent drop)", "reject (send rejection)"]
    )
    
    if not action:
        press_enter_to_continue()
        return
    
    action_cmd = "deny" if "deny" in action else "reject"
    
    if "Simple" in mode:
        _apply_ip_rule(ip, action_cmd)
    else:
        _apply_advanced_ip_rule(ip, action_cmd)
    
    press_enter_to_continue()


def _apply_ip_rule(ip, action):
    """Apply a simple IP rule (all ports)."""
    if not confirm_action(f"{action.upper()} all traffic from {ip}?"):
        show_warning("Cancelled.")
        return
    
    try:
        require_root()
    except PermissionError:
        return
    
    cmd = f"ufw {action} from {ip}"
    result = run_command(cmd, check=False, silent=True)
    
    if result.returncode == 0:
        show_success(f"Rule added: {action} from {ip}")
    else:
        show_error(f"Failed to add rule: {result.stderr}")


def _apply_advanced_ip_rule(ip, action):
    """Apply an advanced IP rule with port/protocol options."""
    # Direction
    direction = select_from_list(
        title="Direction",
        message="Select direction:",
        options=["in (incoming)", "out (outgoing)"]
    )
    
    if not direction:
        show_warning("Cancelled.")
        return
    
    direction_cmd = "in" if "in" in direction else "out"
    
    # Port (optional)
    port = text_input(
        title="Port",
        message="Enter port number (leave empty for all ports):",
        default=""
    )
    
    if port and not _validate_port(port):
        show_error("Invalid port number.")
        return
    
    # Protocol
    protocol = None
    if port:
        protocol = select_from_list(
            title="Protocol",
            message="Select protocol:",
            options=["tcp", "udp", "both"]
        )
        if not protocol:
            show_warning("Cancelled.")
            return
    
    # Build command
    if port:
        if protocol == "both":
            protocols = ["tcp", "udp"]
        else:
            protocols = [protocol]
        
        for proto in protocols:
            cmd = f"ufw {action} {direction_cmd} from {ip} to any port {port} proto {proto}"
            _execute_rule(cmd, f"{action} {ip} to port {port}/{proto}")
    else:
        cmd = f"ufw {action} {direction_cmd} from {ip}"
        _execute_rule(cmd, f"{action} {ip}")


def _execute_rule(cmd, description):
    """Execute a UFW rule command."""
    try:
        require_root()
    except PermissionError:
        return False
    
    result = run_command(cmd, check=False, silent=True)
    
    if result.returncode == 0:
        console.print(f"  [green]✓[/green] {description}")
        return True
    else:
        console.print(f"  [red]✗[/red] {description}: {result.stderr}")
        return False


def manage_whitelist():
    """Manage IP whitelist (always allowed IPs)."""
    def get_status():
        groups = load_ip_groups()
        whitelist = groups.get("_whitelist", {}).get("ips", [])
        return f"Whitelisted IPs: {len(whitelist)}"
    
    options = [
        ("add", "1. Add to Whitelist"),
        ("remove", "2. Remove from Whitelist"),
        ("list", "3. View Whitelist"),
        ("apply", "4. Apply Whitelist Rules"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "add": _add_to_whitelist,
        "remove": _remove_from_whitelist,
        "list": _view_whitelist,
        "apply": _apply_whitelist,
    }
    
    run_menu_loop("IP Whitelist", options, handlers, get_status)


def _add_to_whitelist():
    """Add an IP to the whitelist."""
    clear_screen()
    show_header()
    show_panel("Add to Whitelist", title="IP Whitelist", style="cyan")
    
    ip = text_input(
        title="IP Address",
        message="Enter IP address or CIDR to whitelist:"
    )
    
    if not ip:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not _validate_ip_or_cidr(ip):
        show_error("Invalid IP address or CIDR.")
        press_enter_to_continue()
        return
    
    # Add to whitelist group
    groups = load_ip_groups()
    if "_whitelist" not in groups:
        groups["_whitelist"] = {"ips": [], "rules": ["allow all"]}
    
    if ip in groups["_whitelist"]["ips"]:
        show_info(f"{ip} is already in whitelist.")
    else:
        groups["_whitelist"]["ips"].append(ip)
        save_ip_groups(groups)
        show_success(f"Added {ip} to whitelist.")
        
        if confirm_action("Apply firewall rule now?"):
            _execute_rule(f"ufw allow from {ip}", f"Allow {ip}")
    
    press_enter_to_continue()


def _remove_from_whitelist():
    """Remove an IP from the whitelist."""
    clear_screen()
    show_header()
    show_panel("Remove from Whitelist", title="IP Whitelist", style="cyan")
    
    groups = load_ip_groups()
    whitelist = groups.get("_whitelist", {}).get("ips", [])
    
    if not whitelist:
        show_info("Whitelist is empty.")
        press_enter_to_continue()
        return
    
    ip = select_from_list(
        title="Select IP",
        message="Select IP to remove:",
        options=whitelist
    )
    
    if not ip:
        press_enter_to_continue()
        return
    
    groups["_whitelist"]["ips"].remove(ip)
    save_ip_groups(groups)
    show_success(f"Removed {ip} from whitelist.")
    
    if confirm_action("Remove firewall rule too?"):
        _execute_rule(f"ufw delete allow from {ip}", f"Remove rule for {ip}")
    
    press_enter_to_continue()


def _view_whitelist():
    """View current whitelist."""
    clear_screen()
    show_header()
    show_panel("Whitelist", title="IP Whitelist", style="cyan")
    
    groups = load_ip_groups()
    whitelist = groups.get("_whitelist", {}).get("ips", [])
    
    if not whitelist:
        show_info("Whitelist is empty.")
    else:
        console.print("[bold]Whitelisted IPs:[/bold]")
        for ip in whitelist:
            console.print(f"  • {ip}")
    
    press_enter_to_continue()


def _apply_whitelist():
    """Apply all whitelist rules to firewall."""
    clear_screen()
    show_header()
    show_panel("Apply Whitelist", title="IP Whitelist", style="cyan")
    
    groups = load_ip_groups()
    whitelist = groups.get("_whitelist", {}).get("ips", [])
    
    if not whitelist:
        show_info("Whitelist is empty.")
        press_enter_to_continue()
        return
    
    if not confirm_action(f"Apply {len(whitelist)} whitelist rules?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    for ip in whitelist:
        _execute_rule(f"ufw allow from {ip}", f"Allow {ip}")
    
    console.print()
    show_success("Whitelist rules applied!")
    press_enter_to_continue()


def manage_ip_groups():
    """Manage IP groups."""
    def get_status():
        groups = load_ip_groups()
        user_groups = {k: v for k, v in groups.items() if not k.startswith('_')}
        return f"Groups: {len(user_groups)}"
    
    options = [
        ("create", "1. Create Group"),
        ("edit", "2. Edit Group"),
        ("delete", "3. Delete Group"),
        ("list", "4. List Groups"),
        ("apply", "5. Apply Group Rules"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "create": _create_group,
        "edit": _edit_group,
        "delete": _delete_group,
        "list": _list_groups,
        "apply": _apply_group_rules,
    }
    
    run_menu_loop("IP Groups", options, handlers, get_status)


def _create_group():
    """Create a new IP group."""
    clear_screen()
    show_header()
    show_panel("Create IP Group", title="IP Groups", style="cyan")
    
    name = text_input(
        title="Group Name",
        message="Enter group name (e.g., office, blocked, monitoring):"
    )
    
    if not name:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if name.startswith('_'):
        show_error("Group name cannot start with underscore.")
        press_enter_to_continue()
        return
    
    groups = load_ip_groups()
    if name in groups:
        show_error(f"Group '{name}' already exists.")
        press_enter_to_continue()
        return
    
    # Add initial IPs
    console.print("Enter IP addresses (one per line, empty line to finish):")
    ips = []
    while True:
        ip = text_input(title="IP", message=f"IP {len(ips)+1}:", default="")
        if not ip:
            break
        if _validate_ip_or_cidr(ip):
            ips.append(ip)
            console.print(f"  [green]✓[/green] Added {ip}")
        else:
            console.print(f"  [red]✗[/red] Invalid: {ip}")
    
    # Default rule
    rule = select_from_list(
        title="Default Rule",
        message="Default action for this group:",
        options=["allow (all ports)", "deny (all ports)", "custom (configure later)"]
    )
    
    rules = []
    if rule and "allow" in rule:
        rules = ["allow all"]
    elif rule and "deny" in rule:
        rules = ["deny all"]
    
    create_ip_group(name, ips, rules)
    show_success(f"Group '{name}' created with {len(ips)} IPs.")
    
    press_enter_to_continue()


def _edit_group():
    """Edit an existing IP group."""
    clear_screen()
    show_header()
    show_panel("Edit IP Group", title="IP Groups", style="cyan")
    
    groups = load_ip_groups()
    user_groups = [k for k in groups.keys() if not k.startswith('_')]
    
    if not user_groups:
        show_info("No groups to edit.")
        press_enter_to_continue()
        return
    
    name = select_from_list(
        title="Select Group",
        message="Select group to edit:",
        options=user_groups
    )
    
    if not name:
        press_enter_to_continue()
        return
    
    group = groups[name]
    
    action = select_from_list(
        title="Action",
        message="What to edit:",
        options=["Add IP", "Remove IP", "Change default rule"]
    )
    
    if action == "Add IP":
        ip = text_input(title="IP", message="Enter IP to add:")
        if ip and _validate_ip_or_cidr(ip):
            add_ip_to_group(name, ip)
            show_success(f"Added {ip} to group '{name}'.")
        else:
            show_error("Invalid IP.")
    
    elif action == "Remove IP":
        if not group["ips"]:
            show_info("No IPs in group.")
        else:
            ip = select_from_list(
                title="Select IP",
                message="Select IP to remove:",
                options=group["ips"]
            )
            if ip:
                remove_ip_from_group(name, ip)
                show_success(f"Removed {ip} from group '{name}'.")
    
    elif action == "Change default rule":
        rule = select_from_list(
            title="Rule",
            message="New default rule:",
            options=["allow all", "deny all"]
        )
        if rule:
            groups[name]["rules"] = [rule]
            save_ip_groups(groups)
            show_success(f"Updated rule for group '{name}'.")
    
    press_enter_to_continue()


def _delete_group():
    """Delete an IP group."""
    clear_screen()
    show_header()
    show_panel("Delete IP Group", title="IP Groups", style="cyan")
    
    groups = load_ip_groups()
    user_groups = [k for k in groups.keys() if not k.startswith('_')]
    
    if not user_groups:
        show_info("No groups to delete.")
        press_enter_to_continue()
        return
    
    name = select_from_list(
        title="Select Group",
        message="Select group to delete:",
        options=user_groups
    )
    
    if not name:
        press_enter_to_continue()
        return
    
    group = groups[name]
    
    if not confirm_action(f"Delete group '{name}' ({len(group['ips'])} IPs)?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    delete_ip_group(name)
    show_success(f"Group '{name}' deleted.")
    
    press_enter_to_continue()


def _list_groups():
    """List all IP groups."""
    clear_screen()
    show_header()
    show_panel("IP Groups", title="IP Groups", style="cyan")
    
    groups = load_ip_groups()
    user_groups = {k: v for k, v in groups.items() if not k.startswith('_')}
    
    if not user_groups:
        show_info("No IP groups configured.")
        press_enter_to_continue()
        return
    
    for name, data in user_groups.items():
        rule_str = data["rules"][0] if data["rules"] else "no rule"
        console.print(f"[bold cyan]{name}[/bold cyan] ({len(data['ips'])} IPs) → {rule_str}")
        for ip in data["ips"][:5]:
            console.print(f"    {ip}")
        if len(data["ips"]) > 5:
            console.print(f"    [dim]... and {len(data['ips']) - 5} more[/dim]")
        console.print()
    
    press_enter_to_continue()


def _apply_group_rules():
    """Apply rules for an IP group to firewall."""
    clear_screen()
    show_header()
    show_panel("Apply Group Rules", title="IP Groups", style="cyan")
    
    groups = load_ip_groups()
    user_groups = [k for k in groups.keys() if not k.startswith('_')]
    
    if not user_groups:
        show_info("No groups to apply.")
        press_enter_to_continue()
        return
    
    name = select_from_list(
        title="Select Group",
        message="Select group to apply:",
        options=user_groups
    )
    
    if not name:
        press_enter_to_continue()
        return
    
    group = groups[name]
    
    if not group["ips"]:
        show_info("Group has no IPs.")
        press_enter_to_continue()
        return
    
    if not group["rules"]:
        show_error("Group has no rules configured.")
        press_enter_to_continue()
        return
    
    rule_type = group["rules"][0]
    action = "allow" if "allow" in rule_type else "deny"
    
    if not confirm_action(f"Apply '{action}' rule for {len(group['ips'])} IPs?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    for ip in group["ips"]:
        _execute_rule(f"ufw {action} from {ip}", f"{action.capitalize()} {ip}")
    
    console.print()
    show_success(f"Applied rules for group '{name}'!")
    
    press_enter_to_continue()


def list_ip_rules():
    """List all IP-related firewall rules."""
    clear_screen()
    show_header()
    show_panel("IP Rules", title="IP Management", style="cyan")
    
    if not is_ufw_installed():
        show_error("UFW is not installed.")
        press_enter_to_continue()
        return
    
    rules = get_ufw_rules()
    
    # Filter IP-related rules (those with "from" in them)
    ip_rules = [r for r in rules if "from" in r["rule"].lower() or "to" in r["rule"].lower()]
    
    if not ip_rules:
        show_info("No IP-specific rules found.")
        console.print("[dim]Only port-based rules are configured.[/dim]")
        press_enter_to_continue()
        return
    
    console.print("[bold]IP-Specific Rules:[/bold]")
    console.print()
    
    for rule in ip_rules:
        console.print(f"  [{rule['number']}] {rule['rule']}")
    
    press_enter_to_continue()


def _validate_ip_or_cidr(ip_str):
    """Validate IP address or CIDR notation."""
    # IPv4 pattern
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}(/\d{1,2})?$'
    
    if re.match(ipv4_pattern, ip_str):
        # Validate octets
        parts = ip_str.split('/')[0].split('.')
        for part in parts:
            if int(part) > 255:
                return False
        # Validate CIDR if present
        if '/' in ip_str:
            cidr = int(ip_str.split('/')[1])
            if cidr > 32:
                return False
        return True
    
    return False


def _validate_port(port_str):
    """Validate port number."""
    try:
        port = int(port_str)
        return 1 <= port <= 65535
    except ValueError:
        return False
