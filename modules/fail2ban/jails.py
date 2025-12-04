"""Jail management for fail2ban module."""

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
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, require_root, service_control

from .common import (
    is_fail2ban_installed,
    is_fail2ban_running,
    get_active_jails,
    get_jail_stats,
    JAIL_LOCAL,
    JAIL_D_DIR,
    FILTER_D_DIR,
)
from .templates import get_template, get_templates_by_category


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
    
    jail_file = os.path.join(JAIL_D_DIR, f"{jail}.conf")
    if os.path.exists(jail_file):
        console.print()
        console.print(f"[dim]Config: {jail_file}[/dim]")


def toggle_jail():
    """Enable or disable a jail."""
    clear_screen()
    show_header()
    show_panel("Enable/Disable Jail", title="Jail Management", style="cyan")
    
    all_jails = _get_all_configured_jails()
    active_jails = get_active_jails()
    
    if not all_jails:
        show_info("No jails configured.")
        press_enter_to_continue()
        return
    
    options = []
    display_options = []
    for jail in all_jails:
        status = "[green]enabled[/green]" if jail in active_jails else "[red]disabled[/red]"
        options.append(jail)
        display_options.append(f"{jail} ({status})")
    
    jail = select_from_list(
        title="Select Jail",
        message="Select jail to toggle:",
        options=options
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
    
    name = text_input(
        title="Step 1: Jail Name",
        message="Enter jail name (lowercase, no spaces):"
    )
    
    if not name:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    name = name.lower().replace(" ", "-")
    if not name.replace("-", "").replace("_", "").isalnum():
        show_error("Invalid name. Use only letters, numbers, dashes, underscores.")
        press_enter_to_continue()
        return
    
    if _jail_exists(name):
        show_error(f"Jail '{name}' already exists.")
        press_enter_to_continue()
        return
    
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
    
    templates = templates_by_cat[category]
    template_options = []
    
    for name, template in templates.items():
        installed = " (installed)" if _jail_exists(name) else ""
        template_options.append(f"{template['display_name']}{installed}")
    
    template_names = list(templates.keys())
    
    choice = select_from_list(
        title=f"Select Template - {category}",
        message="Choose template to install:",
        options=template_options
    )
    
    if not choice:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    idx = template_options.index(choice)
    template_name = template_names[idx]
    template = get_template(template_name)
    
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
    
    current = _read_jail_config(jail)
    
    if not current:
        show_error(f"Could not read config for {jail}")
        press_enter_to_continue()
        return
    
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


def _get_all_configured_jails():
    """Get all configured jails (enabled and disabled)."""
    jails = set()
    
    if os.path.exists(JAIL_LOCAL):
        try:
            with open(JAIL_LOCAL, 'r') as f:
                for line in f:
                    if line.strip().startswith('[') and line.strip() != '[DEFAULT]':
                        jail = line.strip()[1:-1]
                        jails.add(jail)
        except Exception:
            pass
    
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
    filter_content = f"""[Definition]
# Custom filter: {name}
# Generated by vexo

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
    
    jail_content = f"""[{name}]
# Custom jail: {name}
# Generated by vexo

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
    filter_file = os.path.join(FILTER_D_DIR, f"{name}.conf")
    try:
        with open(filter_file, 'w') as f:
            f.write(template['filter_content'])
    except Exception as e:
        show_error(f"Failed to create filter: {e}")
        return False
    
    config = template['jail_config']
    jail_content = f"""[{name}]
# Template: {template['display_name']}
# {template['description']}
# Generated by vexo

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
            pass
    
    return success
