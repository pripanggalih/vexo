"""Rate limiting for firewall."""

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
    load_rate_limits,
    save_rate_limits,
    add_rate_limit_config,
    remove_rate_limit_config,
)


# Rate limit presets
RATE_PRESETS = {
    "ssh_recommended": {
        "name": "SSH Recommended",
        "description": "6 connections per 30 seconds",
        "threshold": "6/30sec"
    },
    "web_standard": {
        "name": "Web Standard",
        "description": "100 connections per minute",
        "threshold": "100/min"
    },
    "web_strict": {
        "name": "Web Strict",
        "description": "30 connections per minute",
        "threshold": "30/min"
    },
    "api_standard": {
        "name": "API Standard",
        "description": "60 requests per minute",
        "threshold": "60/min"
    },
    "custom": {
        "name": "Custom",
        "description": "Define your own threshold",
        "threshold": None
    }
}


def show_rate_limit_menu():
    """Display rate limiting submenu."""
    def get_status():
        limits = load_rate_limits()
        enabled = sum(1 for l in limits.values() if l.get("enabled", True))
        return f"UFW: {get_ufw_status_text()} | Rate Limits: {enabled} active"
    
    options = [
        ("enable", "1. Enable Rate Limit"),
        ("quick", "2. Quick SSH Protection"),
        ("config", "3. Configure Limits"),
        ("list", "4. List Rate Limits"),
        ("remove", "5. Remove Rate Limit"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "enable": enable_rate_limit,
        "quick": quick_ssh_protection,
        "config": configure_limits,
        "list": list_rate_limits,
        "remove": remove_rate_limit,
    }
    
    run_menu_loop("Rate Limiting", options, handlers, get_status)


def enable_rate_limit():
    """Enable rate limiting on a port."""
    clear_screen()
    show_header()
    show_panel("Enable Rate Limit", title="Rate Limiting", style="cyan")
    
    if not is_ufw_installed():
        show_error("UFW is not installed.")
        press_enter_to_continue()
        return
    
    # Get port
    port = text_input(
        title="Port",
        message="Enter port number to rate limit:"
    )
    
    if not port:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not _validate_port(port):
        show_error("Invalid port number (1-65535).")
        press_enter_to_continue()
        return
    
    # Get protocol
    protocol = select_from_list(
        title="Protocol",
        message="Select protocol:",
        options=["tcp", "udp"]
    )
    
    if not protocol:
        press_enter_to_continue()
        return
    
    # Select preset
    preset_options = [f"{p['name']} - {p['description']}" for p in RATE_PRESETS.values()]
    
    preset_choice = select_from_list(
        title="Preset",
        message="Select rate limit preset:",
        options=preset_options
    )
    
    if not preset_choice:
        press_enter_to_continue()
        return
    
    # Find selected preset
    preset_key = None
    for key, preset in RATE_PRESETS.items():
        if preset["name"] in preset_choice:
            preset_key = key
            break
    
    threshold = None
    if preset_key == "custom":
        threshold = text_input(
            title="Threshold",
            message="Enter threshold (e.g., 10/min, 5/sec, 100/hour):"
        )
        if not threshold:
            show_warning("Cancelled.")
            press_enter_to_continue()
            return
    else:
        threshold = RATE_PRESETS[preset_key]["threshold"]
    
    # Confirm and apply
    console.print()
    console.print(f"[bold]Rate Limit Configuration:[/bold]")
    console.print(f"  Port: {port}/{protocol}")
    console.print(f"  Preset: {RATE_PRESETS[preset_key]['name']}")
    console.print(f"  Threshold: {threshold}")
    console.print()
    
    if not confirm_action("Apply rate limit?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Apply UFW limit rule
    success = _apply_rate_limit(port, protocol)
    
    if success:
        # Save configuration
        add_rate_limit_config(port, protocol, preset_key, threshold)
        show_success(f"Rate limit enabled for {port}/{protocol}!")
    else:
        show_error("Failed to apply rate limit.")
    
    press_enter_to_continue()


def quick_ssh_protection():
    """Quick enable SSH rate limiting."""
    clear_screen()
    show_header()
    show_panel("Quick SSH Protection", title="Rate Limiting", style="cyan")
    
    if not is_ufw_installed():
        show_error("UFW is not installed.")
        press_enter_to_continue()
        return
    
    console.print("[bold]SSH Rate Limiting Protection[/bold]")
    console.print()
    console.print("This will limit SSH connections to prevent brute-force attacks.")
    console.print("UFW will allow 6 connections per 30 seconds from a single IP.")
    console.print()
    console.print("[dim]IPs exceeding this limit will be temporarily blocked.[/dim]")
    console.print()
    
    if not confirm_action("Enable SSH rate limiting?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # First, delete existing SSH allow rules
    show_info("Updating SSH rules...")
    
    # Get current rules and find SSH rules
    rules = get_ufw_rules()
    ssh_rules = [r for r in rules if "22" in r["rule"] and "ALLOW" in r["rule"]]
    
    # Delete existing SSH allow rules (in reverse order to maintain numbering)
    for rule in reversed(ssh_rules):
        run_command(f"ufw --force delete {rule['number']}", check=False, silent=True)
    
    # Add limit rule
    result = run_command("ufw limit 22/tcp", check=False, silent=True)
    
    if result.returncode == 0:
        add_rate_limit_config("22", "tcp", "ssh_recommended", "6/30sec")
        show_success("SSH rate limiting enabled!")
        console.print()
        console.print("[dim]SSH is now protected against brute-force attacks.[/dim]")
    else:
        show_error("Failed to enable SSH rate limiting.")
    
    press_enter_to_continue()


def configure_limits():
    """Configure existing rate limits."""
    clear_screen()
    show_header()
    show_panel("Configure Rate Limits", title="Rate Limiting", style="cyan")
    
    limits = load_rate_limits()
    
    if not limits:
        show_info("No rate limits configured.")
        show_info("Use 'Enable Rate Limit' to add one.")
        press_enter_to_continue()
        return
    
    # Select a limit to configure
    options = [f"{k} ({v['preset']})" for k, v in limits.items()]
    
    choice = select_from_list(
        title="Select",
        message="Select rate limit to configure:",
        options=options
    )
    
    if not choice:
        press_enter_to_continue()
        return
    
    port_proto = choice.split(" ")[0]
    limit_config = limits.get(port_proto)
    
    if not limit_config:
        show_error("Rate limit not found.")
        press_enter_to_continue()
        return
    
    # Show current config
    console.print()
    console.print(f"[bold]Current Configuration:[/bold]")
    console.print(f"  Port: {limit_config['port']}/{limit_config['protocol']}")
    console.print(f"  Preset: {limit_config['preset']}")
    console.print(f"  Threshold: {limit_config.get('threshold', 'default')}")
    console.print(f"  Status: {'[green]Enabled[/green]' if limit_config.get('enabled', True) else '[yellow]Disabled[/yellow]'}")
    console.print()
    
    # Actions
    action = select_from_list(
        title="Action",
        message="What to do:",
        options=["Toggle enabled/disabled", "Change preset", "Delete rate limit"]
    )
    
    if action == "Toggle enabled/disabled":
        limit_config["enabled"] = not limit_config.get("enabled", True)
        limits[port_proto] = limit_config
        save_rate_limits(limits)
        
        status = "enabled" if limit_config["enabled"] else "disabled"
        show_success(f"Rate limit {status}.")
        
        # Note: UFW doesn't have a disable for limit, would need to delete/re-add
        if not limit_config["enabled"]:
            show_info("Note: To fully disable in firewall, remove and re-add as 'allow' rule.")
    
    elif action == "Change preset":
        preset_options = [f"{p['name']} - {p['description']}" for p in RATE_PRESETS.values()]
        
        new_preset = select_from_list(
            title="Preset",
            message="Select new preset:",
            options=preset_options
        )
        
        if new_preset:
            for key, preset in RATE_PRESETS.items():
                if preset["name"] in new_preset:
                    limit_config["preset"] = key
                    limit_config["threshold"] = preset["threshold"]
                    break
            
            limits[port_proto] = limit_config
            save_rate_limits(limits)
            show_success("Preset updated.")
            show_info("Note: UFW limit rules use fixed thresholds. Config updated for reference.")
    
    elif action == "Delete rate limit":
        if confirm_action(f"Delete rate limit for {port_proto}?"):
            remove_rate_limit_config(limit_config["port"], limit_config["protocol"])
            show_success("Rate limit configuration removed.")
            show_info("Note: UFW rule still exists. Use 'Remove Rate Limit' to delete from firewall.")
    
    press_enter_to_continue()


def list_rate_limits():
    """List all rate limits."""
    clear_screen()
    show_header()
    show_panel("Rate Limits", title="Rate Limiting", style="cyan")
    
    # Show configured rate limits
    limits = load_rate_limits()
    
    console.print("[bold]Configured Rate Limits:[/bold]")
    console.print()
    
    if not limits:
        console.print("[dim]No rate limits configured in vexo.[/dim]")
    else:
        columns = [
            {"name": "Port", "style": "cyan"},
            {"name": "Preset", "style": "white"},
            {"name": "Threshold"},
            {"name": "Status", "justify": "center"},
        ]
        
        rows = []
        for key, config in limits.items():
            status = "[green]Active[/green]" if config.get("enabled", True) else "[yellow]Disabled[/yellow]"
            rows.append([
                key,
                config.get("preset", "custom"),
                config.get("threshold", "default"),
                status
            ])
        
        show_table("", columns, rows)
    
    # Show UFW limit rules
    console.print()
    console.print("[bold]UFW Limit Rules:[/bold]")
    console.print()
    
    rules = get_ufw_rules()
    limit_rules = [r for r in rules if "LIMIT" in r["rule"]]
    
    if not limit_rules:
        console.print("[dim]No limit rules in UFW.[/dim]")
    else:
        for rule in limit_rules:
            console.print(f"  [{rule['number']}] {rule['rule']}")
    
    press_enter_to_continue()


def remove_rate_limit():
    """Remove a rate limit from firewall."""
    clear_screen()
    show_header()
    show_panel("Remove Rate Limit", title="Rate Limiting", style="cyan")
    
    if not is_ufw_installed():
        show_error("UFW is not installed.")
        press_enter_to_continue()
        return
    
    rules = get_ufw_rules()
    limit_rules = [r for r in rules if "LIMIT" in r["rule"]]
    
    if not limit_rules:
        show_info("No rate limit rules to remove.")
        press_enter_to_continue()
        return
    
    # Display limit rules
    console.print("[bold]Current Rate Limit Rules:[/bold]")
    for rule in limit_rules:
        console.print(f"  {rule['number']}. {rule['rule']}")
    console.print()
    
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
        # Find the rule
        selected = None
        for rule in limit_rules:
            if rule["number"] == num:
                selected = rule
                break
        
        if not selected:
            show_error("Invalid rule number.")
            press_enter_to_continue()
            return
    except ValueError:
        show_error("Invalid input.")
        press_enter_to_continue()
        return
    
    if not confirm_action(f"Remove rate limit: {selected['rule']}?"):
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
        # Extract port from rule and remove from config
        port_match = selected["rule"].split()[0]  # e.g., "22/tcp"
        if "/" in port_match:
            port, proto = port_match.split("/")
            remove_rate_limit_config(port, proto)
        
        show_success("Rate limit removed!")
        
        # Offer to add back as allow rule
        if confirm_action("Add back as regular allow rule?"):
            run_command(f"ufw allow {port_match}", check=False, silent=True)
            show_success(f"Added allow rule for {port_match}.")
    else:
        show_error("Failed to remove rate limit.")
    
    press_enter_to_continue()


def _apply_rate_limit(port, protocol):
    """Apply UFW limit rule."""
    try:
        require_root()
    except PermissionError:
        return False
    
    # First remove any existing allow rule for this port
    rules = get_ufw_rules()
    for rule in reversed(rules):
        if f"{port}/{protocol}" in rule["rule"] and "ALLOW" in rule["rule"]:
            run_command(f"ufw --force delete {rule['number']}", check=False, silent=True)
    
    # Add limit rule
    result = run_command(f"ufw limit {port}/{protocol}", check=False, silent=True)
    return result.returncode == 0


def _validate_port(port_str):
    """Validate port number."""
    try:
        port = int(port_str)
        return 1 <= port <= 65535
    except ValueError:
        return False
