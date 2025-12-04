"""Postfix domain management."""

import os

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, require_root
from modules.email.postfix.utils import (
    is_postfix_ready, get_postfix_mode, load_domains_config, save_domains_config,
    validate_domain, reload_postfix, POSTFIX_VIRTUAL, POSTFIX_MASTER_CF,
)


# Pipe script path
VEXO_PIPE_SCRIPT = "/usr/local/bin/vexo-pipe"
VEXO_EMAIL_LOG = "/var/log/vexo-email.log"


def show_domains_menu():
    """Display domain management menu."""
    def get_status():
        config = load_domains_config()
        count = len(config)
        return f"Domains: {count}"
    
    options = [
        ("list", "1. List Domains"),
        ("add", "2. Add Domain"),
        ("edit", "3. Edit Domain"),
        ("remove", "4. Remove Domain"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "list": list_domains,
        "add": add_domain_interactive,
        "edit": edit_domain_interactive,
        "remove": remove_domain_interactive,
    }
    
    run_menu_loop("Domain Management", options, handlers, get_status)


def list_domains():
    """Display all configured email domains."""
    clear_screen()
    show_header()
    show_panel("Email Domains", title="Domain Management", style="cyan")
    
    config = load_domains_config()
    
    if not config:
        show_info("No domains configured.")
        console.print()
        console.print("[dim]Use 'Add Domain' to configure one.[/dim]")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Domain", "style": "cyan"},
        {"name": "Type"},
        {"name": "Destination"},
        {"name": "Status"},
    ]
    
    rows = []
    for domain, cfg in config.items():
        domain_type = cfg.get("type", "catchall")
        
        if domain_type == "catchall":
            dest = f"→ {cfg.get('command', 'N/A')}"
        elif domain_type == "forward":
            dest = f"→ {cfg.get('forward_to', 'N/A')}"
        else:
            dest = cfg.get("path", "N/A")
        
        status = "[green]Active[/green]" if cfg.get("active", True) else "[red]Inactive[/red]"
        rows.append([domain, domain_type, dest, status])
    
    show_table("Configured Domains", columns, rows, show_header=True)
    press_enter_to_continue()


def add_domain_interactive():
    """Interactive prompt to add a new email domain."""
    clear_screen()
    show_header()
    show_panel("Add Domain", title="Domain Management", style="cyan")
    
    if not is_postfix_ready():
        show_error("Postfix is not running.")
        press_enter_to_continue()
        return
    
    mode = get_postfix_mode()
    if mode == "send-only":
        show_warning("Postfix is in send-only mode.")
        console.print("[dim]Switch to receive mode to accept incoming email.[/dim]")
        press_enter_to_continue()
        return
    
    domain = text_input("Domain name (e.g., example.com):")
    if not domain:
        return
    
    domain = domain.lower().strip()
    
    if not validate_domain(domain):
        show_error("Invalid domain format.")
        press_enter_to_continue()
        return
    
    config = load_domains_config()
    if domain in config:
        show_error(f"Domain '{domain}' already configured.")
        press_enter_to_continue()
        return
    
    # Domain type
    domain_types = [
        "Catch-all to Laravel (pipe to artisan)",
        "Forward to external email",
        "Local delivery (requires Dovecot)",
    ]
    
    domain_type = select_from_list("Domain Type", "How to handle email:", domain_types)
    if not domain_type:
        return
    
    domain_config = {"active": True}
    
    if "Laravel" in domain_type:
        domain_config["type"] = "catchall"
        
        laravel_path = text_input("Laravel project path:", default="/var/www/html")
        if not laravel_path:
            return
        
        if not _validate_laravel_path(laravel_path):
            show_error("Invalid Laravel path (artisan not found).")
            press_enter_to_continue()
            return
        
        artisan_cmd = text_input("Artisan command:", default="email:incoming")
        if not artisan_cmd:
            return
        
        domain_config["path"] = laravel_path
        domain_config["command"] = artisan_cmd
        
    elif "Forward" in domain_type:
        domain_config["type"] = "forward"
        
        forward_to = text_input("Forward all email to:")
        if not forward_to or "@" not in forward_to:
            show_error("Invalid email address.")
            press_enter_to_continue()
            return
        
        domain_config["forward_to"] = forward_to
        
    else:
        domain_config["type"] = "local"
        console.print("[yellow]Local delivery requires Dovecot to be installed.[/yellow]")
    
    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  Domain: {domain}")
    console.print(f"  Type: {domain_config['type']}")
    console.print()
    
    if not confirm_action(f"Add domain {domain}?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    config[domain] = domain_config
    
    if save_domains_config(config):
        _regenerate_postfix_files()
        reload_postfix()
        show_success(f"Domain '{domain}' added!")
    else:
        show_error("Failed to add domain.")
    
    press_enter_to_continue()


def edit_domain_interactive():
    """Edit domain configuration."""
    clear_screen()
    show_header()
    show_panel("Edit Domain", title="Domain Management", style="cyan")
    
    config = load_domains_config()
    if not config:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    domains = list(config.keys())
    domain = select_from_list("Select Domain", "Edit:", domains)
    if not domain:
        return
    
    current = config[domain]
    
    console.print(f"[bold]Current configuration for {domain}:[/bold]")
    console.print(f"  Type: {current.get('type', 'catchall')}")
    if current.get('path'):
        console.print(f"  Path: {current.get('path')}")
    if current.get('command'):
        console.print(f"  Command: {current.get('command')}")
    if current.get('forward_to'):
        console.print(f"  Forward to: {current.get('forward_to')}")
    console.print(f"  Active: {current.get('active', True)}")
    console.print()
    
    # Toggle active
    if confirm_action("Toggle active status?"):
        current["active"] = not current.get("active", True)
        config[domain] = current
        save_domains_config(config)
        _regenerate_postfix_files()
        reload_postfix()
        status = "activated" if current["active"] else "deactivated"
        show_success(f"Domain {domain} {status}!")
    
    press_enter_to_continue()


def remove_domain_interactive():
    """Remove a domain."""
    clear_screen()
    show_header()
    show_panel("Remove Domain", title="Domain Management", style="red")
    
    config = load_domains_config()
    if not config:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    domains = list(config.keys())
    domain = select_from_list("Select Domain", "Remove:", domains)
    if not domain:
        return
    
    console.print(f"[bold red]WARNING: This will stop receiving emails for {domain}![/bold red]")
    
    if not confirm_action(f"Remove domain {domain}?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    del config[domain]
    
    if save_domains_config(config):
        _regenerate_postfix_files()
        reload_postfix()
        show_success(f"Domain '{domain}' removed!")
    else:
        show_error("Failed to remove domain.")
    
    press_enter_to_continue()


def _validate_laravel_path(path):
    """Check if path contains Laravel artisan."""
    return os.path.exists(os.path.join(path, 'artisan'))


def _regenerate_postfix_files():
    """Regenerate Postfix virtual and master.cf files."""
    config = load_domains_config()
    
    # Generate virtual file
    lines = ["# Generated by vexo\n"]
    
    for domain, cfg in config.items():
        if not cfg.get("active", True):
            continue
        
        if cfg.get("type") == "catchall":
            transport_name = f"laravel-{domain.replace('.', '-')}"
            lines.append(f"@{domain}    {transport_name}\n")
        elif cfg.get("type") == "forward":
            forward_to = cfg.get("forward_to", "")
            lines.append(f"@{domain}    {forward_to}\n")
    
    try:
        with open(POSTFIX_VIRTUAL, 'w') as f:
            f.writelines(lines)
        run_command(f"postmap {POSTFIX_VIRTUAL}", check=False, silent=True)
    except IOError:
        return False
    
    # Generate master.cf entries for catchall domains
    _update_master_cf(config)
    
    # Update main.cf virtual settings
    _update_virtual_settings(config)
    
    # Install pipe script if needed
    catchall_domains = [d for d, c in config.items() if c.get("type") == "catchall" and c.get("active", True)]
    if catchall_domains:
        _install_vexo_pipe()
    
    return True


def _update_master_cf(config):
    """Update master.cf with pipe transports."""
    try:
        with open(POSTFIX_MASTER_CF, 'r') as f:
            content = f.read()
        
        # Remove existing vexo entries
        lines = content.split('\n')
        new_lines = []
        skip_next = False
        
        for line in lines:
            if '# vexo-start' in line:
                skip_next = True
                continue
            if '# vexo-end' in line:
                skip_next = False
                continue
            if skip_next:
                continue
            new_lines.append(line)
        
        # Add new entries
        new_lines.append("# vexo-start")
        
        for domain, cfg in config.items():
            if cfg.get("type") == "catchall" and cfg.get("active", True):
                transport_name = f"laravel-{domain.replace('.', '-')}"
                new_lines.append(f"{transport_name} unix - n n - - pipe")
                new_lines.append(f"  flags=F user=www-data argv={VEXO_PIPE_SCRIPT} {domain}")
        
        new_lines.append("# vexo-end")
        
        with open(POSTFIX_MASTER_CF, 'w') as f:
            f.write('\n'.join(new_lines))
        
        return True
    except IOError:
        return False


def _update_virtual_settings(config):
    """Update main.cf virtual alias settings."""
    from modules.email.postfix.utils import set_postfix_settings
    
    active_domains = [d for d, c in config.items() if c.get("active", True)]
    
    if active_domains:
        settings = {
            "virtual_alias_domains": ", ".join(active_domains),
            "virtual_alias_maps": f"hash:{POSTFIX_VIRTUAL}",
        }
    else:
        settings = {
            "virtual_alias_domains": "",
            "virtual_alias_maps": "",
        }
    
    set_postfix_settings(settings)


def _install_vexo_pipe():
    """Install the vexo-pipe script."""
    script_content = '''#!/bin/bash
DOMAIN="$1"
CONFIG_FILE="/etc/vexo/email-domains.json"
LOG_FILE="/var/log/vexo-email.log"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "$(date): ERROR - Config file not found" >> "$LOG_FILE"
    exit 75
fi

PATH_VALUE=$(jq -r ".\\\"$DOMAIN\\\".path" "$CONFIG_FILE")
CMD_VALUE=$(jq -r ".\\\"$DOMAIN\\\".command" "$CONFIG_FILE")

if [ "$PATH_VALUE" == "null" ] || [ -z "$PATH_VALUE" ]; then
    echo "$(date): ERROR - Domain $DOMAIN not configured" >> "$LOG_FILE"
    exit 75
fi

echo "$(date): Incoming email for $DOMAIN -> $CMD_VALUE" >> "$LOG_FILE"

cd "$PATH_VALUE" && /usr/bin/php artisan $CMD_VALUE 2>> "$LOG_FILE"
exit $?
'''
    
    try:
        # Install jq if needed
        from utils.shell import is_installed
        if not is_installed("jq"):
            run_command("apt install -y jq", check=False, silent=True)
        
        with open(VEXO_PIPE_SCRIPT, 'w') as f:
            f.write(script_content)
        os.chmod(VEXO_PIPE_SCRIPT, 0o755)
        
        if not os.path.exists(VEXO_EMAIL_LOG):
            with open(VEXO_EMAIL_LOG, 'w') as f:
                f.write("")
            os.chmod(VEXO_EMAIL_LOG, 0o666)
        
        return True
    except IOError:
        return False
