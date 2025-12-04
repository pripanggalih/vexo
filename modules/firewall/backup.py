"""Backup and restore for firewall."""

import os
import json
import socket
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
from ui.menu import run_menu_loop, text_input, select_from_list, confirm_action
from utils.shell import run_command, require_root
from modules.firewall.common import (
    is_ufw_installed,
    get_ufw_status_text,
    get_ufw_rules,
    get_ufw_defaults,
    load_ip_groups,
    save_ip_groups,
    load_rate_limits,
    save_rate_limits,
    ensure_config_dir,
    VEXO_FIREWALL_BACKUPS,
    SETTINGS_FILE,
)


def show_backup_menu():
    """Display backup and restore submenu."""
    def get_status():
        backups = _list_backups()
        return f"UFW: {get_ufw_status_text()} | Backups: {len(backups)}"
    
    options = [
        ("create", "1. Create Backup"),
        ("restore", "2. Restore Backup"),
        ("compare", "3. Compare Configs"),
        ("auto", "4. Auto-Backup Settings"),
        ("manage", "5. Manage Backups"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "create": create_backup,
        "restore": restore_backup,
        "compare": compare_configs,
        "auto": auto_backup_settings,
        "manage": manage_backups,
    }
    
    run_menu_loop("Backup & Restore", options, handlers, get_status)


def _list_backups():
    """List all backup files."""
    if not os.path.exists(VEXO_FIREWALL_BACKUPS):
        return []
    
    backups = []
    for filename in os.listdir(VEXO_FIREWALL_BACKUPS):
        if filename.endswith('.json'):
            filepath = os.path.join(VEXO_FIREWALL_BACKUPS, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    backups.append({
                        "filename": filename,
                        "filepath": filepath,
                        "name": data.get("name", filename),
                        "created": data.get("created", "unknown"),
                        "description": data.get("description", ""),
                        "rule_count": len(data.get("ufw_rules", []))
                    })
            except (json.JSONDecodeError, IOError):
                continue
    
    # Sort by creation date (newest first)
    backups.sort(key=lambda x: x["created"], reverse=True)
    return backups


def _get_current_config():
    """Get current firewall configuration."""
    return {
        "ufw_rules": get_ufw_rules(),
        "ufw_defaults": get_ufw_defaults(),
        "ip_groups": load_ip_groups(),
        "rate_limits": load_rate_limits()
    }


def create_backup():
    """Create a new backup."""
    clear_screen()
    show_header()
    show_panel("Create Backup", title="Backup & Restore", style="cyan")
    
    if not is_ufw_installed():
        show_error("UFW is not installed.")
        press_enter_to_continue()
        return
    
    # Backup name
    default_name = f"backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    name = text_input(
        title="Backup Name",
        message="Enter backup name:",
        default=default_name
    )
    
    if not name:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Sanitize name for filename
    safe_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in name)
    
    # Description
    description = text_input(
        title="Description",
        message="Description (optional):",
        default=""
    )
    
    # What to include
    console.print()
    console.print("[bold]Include in backup:[/bold]")
    
    include_rules = confirm_action("Include UFW rules?")
    include_ip_groups = confirm_action("Include IP groups?")
    include_rate_limits = confirm_action("Include rate limit configs?")
    
    # Get current config
    show_info("Gathering configuration...")
    
    config = _get_current_config()
    
    # Build backup data
    backup_data = {
        "version": "1.0",
        "name": name,
        "created": datetime.now().isoformat(),
        "server": socket.gethostname(),
        "description": description,
    }
    
    if include_rules:
        backup_data["ufw_rules"] = config["ufw_rules"]
        backup_data["ufw_defaults"] = config["ufw_defaults"]
    
    if include_ip_groups:
        backup_data["ip_groups"] = config["ip_groups"]
    
    if include_rate_limits:
        backup_data["rate_limits"] = config["rate_limits"]
    
    # Save backup
    ensure_config_dir()
    filename = f"{safe_name}.json"
    filepath = os.path.join(VEXO_FIREWALL_BACKUPS, filename)
    
    try:
        with open(filepath, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        show_success(f"Backup created: {filename}")
        console.print()
        console.print(f"[dim]Location: {filepath}[/dim]")
        console.print(f"[dim]Rules: {len(backup_data.get('ufw_rules', []))}[/dim]")
    except IOError as e:
        show_error(f"Failed to create backup: {e}")
    
    press_enter_to_continue()


def restore_backup():
    """Restore from a backup."""
    clear_screen()
    show_header()
    show_panel("Restore Backup", title="Backup & Restore", style="cyan")
    
    backups = _list_backups()
    
    if not backups:
        show_info("No backups available.")
        press_enter_to_continue()
        return
    
    # Select backup
    options = [f"{b['name']} ({b['rule_count']} rules, {b['created'][:10]})" for b in backups]
    
    choice = select_from_list(
        title="Backup",
        message="Select backup to restore:",
        options=options
    )
    
    if not choice:
        press_enter_to_continue()
        return
    
    # Find selected backup
    idx = options.index(choice)
    backup = backups[idx]
    
    # Load backup data
    try:
        with open(backup["filepath"], 'r') as f:
            backup_data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        show_error(f"Failed to load backup: {e}")
        press_enter_to_continue()
        return
    
    # Show backup details
    console.print()
    console.print(f"[bold]Backup Details:[/bold]")
    console.print(f"  Name: {backup_data.get('name')}")
    console.print(f"  Created: {backup_data.get('created')}")
    console.print(f"  Server: {backup_data.get('server')}")
    console.print(f"  Description: {backup_data.get('description') or '[dim]No description[/dim]'}")
    console.print()
    
    # What to restore
    console.print("[bold]Available to restore:[/bold]")
    
    has_rules = "ufw_rules" in backup_data
    has_ip_groups = "ip_groups" in backup_data
    has_rate_limits = "rate_limits" in backup_data
    
    if has_rules:
        console.print(f"  UFW Rules: {len(backup_data['ufw_rules'])} rules")
    if has_ip_groups:
        console.print(f"  IP Groups: {len(backup_data['ip_groups'])} groups")
    if has_rate_limits:
        console.print(f"  Rate Limits: {len(backup_data['rate_limits'])} configs")
    
    console.print()
    
    if not confirm_action("Restore this backup?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Warning about overwriting
    console.print()
    console.print("[red bold]WARNING: This will overwrite current configuration![/red bold]")
    console.print()
    
    if not confirm_action("Are you sure you want to continue?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Create backup of current config first
    show_info("Creating backup of current config...")
    _auto_backup("pre-restore")
    
    # Restore UFW rules
    if has_rules:
        show_info("Restoring UFW rules...")
        _restore_ufw_rules(backup_data["ufw_rules"], backup_data.get("ufw_defaults", {}))
    
    # Restore IP groups
    if has_ip_groups:
        show_info("Restoring IP groups...")
        save_ip_groups(backup_data["ip_groups"])
    
    # Restore rate limits
    if has_rate_limits:
        show_info("Restoring rate limit configs...")
        save_rate_limits(backup_data["rate_limits"])
    
    console.print()
    show_success("Backup restored successfully!")
    
    press_enter_to_continue()


def _restore_ufw_rules(rules, defaults):
    """Restore UFW rules from backup."""
    # Reset UFW
    run_command("ufw --force reset", check=False, silent=True)
    
    # Set defaults
    if defaults.get("incoming"):
        run_command(f"ufw default {defaults['incoming']} incoming", check=False, silent=True)
    if defaults.get("outgoing"):
        run_command(f"ufw default {defaults['outgoing']} outgoing", check=False, silent=True)
    
    # Add rules
    for rule in rules:
        rule_str = rule.get("rule", "")
        
        # Parse and reconstruct UFW command from rule string
        if "ALLOW" in rule_str:
            action = "allow"
        elif "DENY" in rule_str:
            action = "deny"
        elif "LIMIT" in rule_str:
            action = "limit"
        elif "REJECT" in rule_str:
            action = "reject"
        else:
            continue
        
        # Extract port/protocol
        parts = rule_str.split()
        if parts:
            port_proto = parts[0]
            cmd = f"ufw {action} {port_proto}"
            result = run_command(cmd, check=False, silent=True)
            if result.returncode == 0:
                console.print(f"  [green]✓[/green] {action} {port_proto}")
            else:
                console.print(f"  [red]✗[/red] {action} {port_proto}")
    
    # Enable UFW
    run_command("ufw --force enable", check=False, silent=True)


def _auto_backup(prefix="auto"):
    """Create an automatic backup."""
    ensure_config_dir()
    
    config = _get_current_config()
    
    backup_data = {
        "version": "1.0",
        "name": f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "created": datetime.now().isoformat(),
        "server": socket.gethostname(),
        "description": f"Automatic backup ({prefix})",
        "ufw_rules": config["ufw_rules"],
        "ufw_defaults": config["ufw_defaults"],
        "ip_groups": config["ip_groups"],
        "rate_limits": config["rate_limits"]
    }
    
    filename = f"{backup_data['name']}.json"
    filepath = os.path.join(VEXO_FIREWALL_BACKUPS, filename)
    
    try:
        with open(filepath, 'w') as f:
            json.dump(backup_data, f, indent=2)
        return filepath
    except IOError:
        return None


def compare_configs():
    """Compare two backup configurations."""
    clear_screen()
    show_header()
    show_panel("Compare Configurations", title="Backup & Restore", style="cyan")
    
    backups = _list_backups()
    
    if len(backups) < 2:
        show_info("Need at least 2 backups to compare.")
        press_enter_to_continue()
        return
    
    options = [f"{b['name']} ({b['created'][:10]})" for b in backups]
    
    # Select first config
    console.print("[bold]Select first configuration:[/bold]")
    choice1 = select_from_list(
        title="First",
        message="Select first backup:",
        options=["Current configuration"] + options
    )
    
    if not choice1:
        press_enter_to_continue()
        return
    
    # Select second config
    console.print()
    console.print("[bold]Select second configuration:[/bold]")
    choice2 = select_from_list(
        title="Second",
        message="Select second backup:",
        options=["Current configuration"] + options
    )
    
    if not choice2:
        press_enter_to_continue()
        return
    
    if choice1 == choice2:
        show_info("Please select two different configurations.")
        press_enter_to_continue()
        return
    
    # Load configurations
    def load_config(choice):
        if choice == "Current configuration":
            return _get_current_config(), "Current"
        else:
            idx = options.index(choice)
            backup = backups[idx]
            with open(backup["filepath"], 'r') as f:
                return json.load(f), backup["name"]
    
    try:
        config1, name1 = load_config(choice1)
        config2, name2 = load_config(choice2)
    except Exception as e:
        show_error(f"Failed to load configs: {e}")
        press_enter_to_continue()
        return
    
    # Compare rules
    clear_screen()
    show_header()
    show_panel(f"Comparing: {name1} vs {name2}", title="Config Comparison", style="cyan")
    
    rules1 = set(r.get("rule", "") for r in config1.get("ufw_rules", []))
    rules2 = set(r.get("rule", "") for r in config2.get("ufw_rules", []))
    
    added = rules2 - rules1
    removed = rules1 - rules2
    
    # Display comparison
    console.print(f"[bold]Rules in {name1}:[/bold] {len(rules1)}")
    console.print(f"[bold]Rules in {name2}:[/bold] {len(rules2)}")
    console.print()
    
    if added:
        console.print(f"[green bold]Added in {name2} (+{len(added)}):[/green bold]")
        for rule in list(added)[:10]:
            console.print(f"  [green]+[/green] {rule}")
        if len(added) > 10:
            console.print(f"  [dim]... and {len(added) - 10} more[/dim]")
        console.print()
    
    if removed:
        console.print(f"[red bold]Removed from {name1} (-{len(removed)}):[/red bold]")
        for rule in list(removed)[:10]:
            console.print(f"  [red]-[/red] {rule}")
        if len(removed) > 10:
            console.print(f"  [dim]... and {len(removed) - 10} more[/dim]")
        console.print()
    
    if not added and not removed:
        console.print("[green]No differences in UFW rules.[/green]")
    
    # Compare IP groups
    groups1 = set(config1.get("ip_groups", {}).keys())
    groups2 = set(config2.get("ip_groups", {}).keys())
    
    if groups1 != groups2:
        console.print()
        console.print("[bold]IP Groups Differences:[/bold]")
        for g in groups2 - groups1:
            console.print(f"  [green]+[/green] {g}")
        for g in groups1 - groups2:
            console.print(f"  [red]-[/red] {g}")
    
    press_enter_to_continue()


def auto_backup_settings():
    """Configure automatic backup settings."""
    clear_screen()
    show_header()
    show_panel("Auto-Backup Settings", title="Backup & Restore", style="cyan")
    
    # Load current settings
    settings = _load_settings()
    
    console.print("[bold]Current Settings:[/bold]")
    console.print(f"  Auto-backup enabled: {'[green]Yes[/green]' if settings.get('auto_backup_enabled') else '[dim]No[/dim]'}")
    console.print(f"  Keep last N backups: {settings.get('keep_backups', 7)}")
    console.print(f"  Backup before changes: {'[green]Yes[/green]' if settings.get('backup_before_changes') else '[dim]No[/dim]'}")
    console.print()
    
    action = select_from_list(
        title="Action",
        message="What to configure:",
        options=[
            "Toggle auto-backup",
            "Set backup retention",
            "Toggle backup before changes",
            "Run cleanup now"
        ]
    )
    
    if not action:
        press_enter_to_continue()
        return
    
    if action == "Toggle auto-backup":
        settings["auto_backup_enabled"] = not settings.get("auto_backup_enabled", False)
        _save_settings(settings)
        status = "enabled" if settings["auto_backup_enabled"] else "disabled"
        show_success(f"Auto-backup {status}.")
    
    elif action == "Set backup retention":
        current = settings.get("keep_backups", 7)
        new_value = text_input(
            title="Retention",
            message="Keep last N backups:",
            default=str(current)
        )
        if new_value:
            try:
                settings["keep_backups"] = int(new_value)
                _save_settings(settings)
                show_success(f"Will keep last {new_value} backups.")
            except ValueError:
                show_error("Invalid number.")
    
    elif action == "Toggle backup before changes":
        settings["backup_before_changes"] = not settings.get("backup_before_changes", True)
        _save_settings(settings)
        status = "enabled" if settings["backup_before_changes"] else "disabled"
        show_success(f"Backup before changes {status}.")
    
    elif action == "Run cleanup now":
        keep_n = settings.get("keep_backups", 7)
        deleted = _cleanup_old_backups(keep_n)
        show_success(f"Cleanup complete. Deleted {deleted} old backups.")
    
    press_enter_to_continue()


def _load_settings():
    """Load backup settings."""
    if not os.path.exists(SETTINGS_FILE):
        return {
            "auto_backup_enabled": False,
            "keep_backups": 7,
            "backup_before_changes": True
        }
    
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_settings(settings):
    """Save backup settings."""
    ensure_config_dir()
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)


def _cleanup_old_backups(keep_n):
    """Delete old backups, keeping only the last N."""
    backups = _list_backups()
    
    # Keep system backups (pre-restore, etc.) separately
    auto_backups = [b for b in backups if b["name"].startswith("auto-") or b["name"].startswith("backup-")]
    
    deleted = 0
    if len(auto_backups) > keep_n:
        to_delete = auto_backups[keep_n:]
        for backup in to_delete:
            try:
                os.remove(backup["filepath"])
                deleted += 1
            except IOError:
                pass
    
    return deleted


def manage_backups():
    """Manage existing backups."""
    clear_screen()
    show_header()
    show_panel("Manage Backups", title="Backup & Restore", style="cyan")
    
    backups = _list_backups()
    
    if not backups:
        show_info("No backups available.")
        press_enter_to_continue()
        return
    
    # Show backup list
    console.print("[bold]Available Backups:[/bold]")
    console.print()
    
    columns = [
        {"name": "#", "style": "dim", "justify": "right"},
        {"name": "Name", "style": "cyan"},
        {"name": "Rules"},
        {"name": "Created"},
    ]
    
    rows = []
    for i, b in enumerate(backups, 1):
        rows.append([
            str(i),
            b["name"][:30],
            str(b["rule_count"]),
            b["created"][:10]
        ])
    
    show_table("", columns, rows)
    
    # Actions
    action = select_from_list(
        title="Action",
        message="Select action:",
        options=["View details", "Rename backup", "Delete backup", "Export backup"]
    )
    
    if not action:
        press_enter_to_continue()
        return
    
    # Select backup
    options = [f"{b['name']}" for b in backups]
    
    selected = select_from_list(
        title="Backup",
        message="Select backup:",
        options=options
    )
    
    if not selected:
        press_enter_to_continue()
        return
    
    idx = options.index(selected)
    backup = backups[idx]
    
    if action == "View details":
        _view_backup_details(backup)
    
    elif action == "Rename backup":
        new_name = text_input(
            title="New Name",
            message="Enter new name:",
            default=backup["name"]
        )
        if new_name and new_name != backup["name"]:
            _rename_backup(backup, new_name)
    
    elif action == "Delete backup":
        if confirm_action(f"Delete backup '{backup['name']}'?"):
            _delete_backup(backup)
    
    elif action == "Export backup":
        _export_backup(backup)
    
    press_enter_to_continue()


def _view_backup_details(backup):
    """View detailed backup information."""
    try:
        with open(backup["filepath"], 'r') as f:
            data = json.load(f)
    except Exception as e:
        show_error(f"Failed to load backup: {e}")
        return
    
    console.print()
    console.print(f"[bold cyan]Backup: {data.get('name')}[/bold cyan]")
    console.print()
    console.print(f"[bold]Created:[/bold] {data.get('created')}")
    console.print(f"[bold]Server:[/bold] {data.get('server')}")
    console.print(f"[bold]Description:[/bold] {data.get('description') or '[dim]None[/dim]'}")
    console.print()
    console.print(f"[bold]Contents:[/bold]")
    console.print(f"  UFW Rules: {len(data.get('ufw_rules', []))}")
    console.print(f"  IP Groups: {len(data.get('ip_groups', {}))}")
    console.print(f"  Rate Limits: {len(data.get('rate_limits', {}))}")
    console.print()
    console.print(f"[dim]File: {backup['filepath']}[/dim]")


def _rename_backup(backup, new_name):
    """Rename a backup."""
    try:
        # Load and update data
        with open(backup["filepath"], 'r') as f:
            data = json.load(f)
        
        data["name"] = new_name
        
        # Save with new filename
        safe_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in new_name)
        new_filepath = os.path.join(VEXO_FIREWALL_BACKUPS, f"{safe_name}.json")
        
        with open(new_filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Remove old file if different
        if new_filepath != backup["filepath"]:
            os.remove(backup["filepath"])
        
        show_success(f"Backup renamed to '{new_name}'.")
    except Exception as e:
        show_error(f"Failed to rename: {e}")


def _delete_backup(backup):
    """Delete a backup."""
    try:
        os.remove(backup["filepath"])
        show_success(f"Backup '{backup['name']}' deleted.")
    except IOError as e:
        show_error(f"Failed to delete: {e}")


def _export_backup(backup):
    """Export backup to a different location."""
    dest = text_input(
        title="Destination",
        message="Export to (full path):",
        default=f"/tmp/{backup['filename']}"
    )
    
    if not dest:
        return
    
    try:
        import shutil
        shutil.copy2(backup["filepath"], dest)
        show_success(f"Exported to: {dest}")
    except Exception as e:
        show_error(f"Failed to export: {e}")
