"""Whitelist management for fail2ban module."""

import json
import os
from datetime import datetime

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_success,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, require_root, service_control
from utils.error_handler import handle_error

from .common import (
    is_valid_ip,
    is_valid_cidr,
    get_active_jails,
    VEXO_FAIL2BAN_DIR,
    JAIL_LOCAL,
    JAIL_D_DIR,
    ensure_data_dir,
)


WHITELIST_FILE = VEXO_FAIL2BAN_DIR / "whitelist.json"
TRUSTED_SOURCES_FILE = VEXO_FAIL2BAN_DIR / "trusted_sources.json"


TRUSTED_SOURCES = {
    "cloudflare_ipv4": {
        "name": "Cloudflare IPv4",
        "url": "https://www.cloudflare.com/ips-v4",
        "description": "Cloudflare CDN IPv4 ranges",
    },
    "cloudflare_ipv6": {
        "name": "Cloudflare IPv6",
        "url": "https://www.cloudflare.com/ips-v6",
        "description": "Cloudflare CDN IPv6 ranges",
    },
}


def show_menu():
    """Display whitelist management menu."""
    def get_status():
        whitelist = _load_whitelist()
        count = len(whitelist.get('global', {}).get('ips', []))
        count += len(whitelist.get('global', {}).get('ranges', []))
        return f"{count} whitelisted IPs/ranges"
    
    def get_options():
        return [
            ("global", "1. Global Whitelist"),
            ("perjail", "2. Per-Jail Whitelist"),
            ("groups", "3. IP Groups"),
            ("trusted", "4. Trusted Sources"),
            ("import", "5. Import/Export"),
            ("apply", "6. Apply to Fail2ban"),
            ("back", "← Back"),
        ]
    
    handlers = {
        "global": global_whitelist_menu,
        "perjail": perjail_whitelist_menu,
        "groups": ip_groups_menu,
        "trusted": trusted_sources_menu,
        "import": import_export_menu,
        "apply": apply_whitelist,
    }
    
    run_menu_loop("Whitelist Management", get_options, handlers, get_status)


def global_whitelist_menu():
    """Manage global whitelist."""
    def get_options():
        return [
            ("view", "1. View Whitelist"),
            ("add_ip", "2. Add IP"),
            ("add_range", "3. Add CIDR Range"),
            ("remove", "4. Remove Entry"),
            ("back", "← Back"),
        ]
    
    handlers = {
        "view": _view_global_whitelist,
        "add_ip": _add_global_ip,
        "add_range": _add_global_range,
        "remove": _remove_global_entry,
    }
    
    run_menu_loop("Global Whitelist", get_options, handlers)


def _view_global_whitelist():
    """View global whitelist entries."""
    clear_screen()
    show_header()
    show_panel("Global Whitelist", title="Whitelist", style="cyan")
    
    whitelist = _load_whitelist()
    global_wl = whitelist.get('global', {})
    
    ips = global_wl.get('ips', [])
    ranges = global_wl.get('ranges', [])
    groups = global_wl.get('groups', [])
    
    if not ips and not ranges and not groups:
        show_info("Global whitelist is empty.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Type", "style": "dim"},
        {"name": "Value", "style": "cyan"},
        {"name": "Description"},
    ]
    
    rows = []
    for ip in ips:
        if isinstance(ip, dict):
            rows.append(["IP", ip.get('value', ''), ip.get('description', '')])
        else:
            rows.append(["IP", ip, ""])
    
    for r in ranges:
        if isinstance(r, dict):
            rows.append(["Range", r.get('value', ''), r.get('description', '')])
        else:
            rows.append(["Range", r, ""])
    
    for g in groups:
        rows.append(["Group", g, "(see IP Groups)"])
    
    show_table(f"Global Whitelist ({len(rows)} entries)", columns, rows)
    press_enter_to_continue()


def _add_global_ip():
    """Add IP to global whitelist."""
    clear_screen()
    show_header()
    show_panel("Add IP to Global Whitelist", title="Whitelist", style="cyan")
    
    ip = text_input(
        title="IP Address",
        message="Enter IP address to whitelist:"
    )
    
    if not ip:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not is_valid_ip(ip):
        handle_error("E6003", "Invalid IP address format.")
        press_enter_to_continue()
        return
    
    description = text_input(
        title="Description",
        message="Description (optional):",
        default=""
    )
    
    whitelist = _load_whitelist()
    if 'global' not in whitelist:
        whitelist['global'] = {'ips': [], 'ranges': [], 'groups': []}
    
    existing = [x.get('value') if isinstance(x, dict) else x for x in whitelist['global'].get('ips', [])]
    if ip in existing:
        show_warning(f"IP {ip} is already in whitelist.")
        press_enter_to_continue()
        return
    
    whitelist['global']['ips'].append({
        'value': ip,
        'description': description,
        'added': datetime.now().isoformat()
    })
    
    _save_whitelist(whitelist)
    show_success(f"IP {ip} added to global whitelist!")
    
    if confirm_action("Apply changes to fail2ban now?"):
        _apply_whitelist_to_fail2ban()
    
    press_enter_to_continue()


def _add_global_range():
    """Add CIDR range to global whitelist."""
    clear_screen()
    show_header()
    show_panel("Add CIDR Range to Global Whitelist", title="Whitelist", style="cyan")
    
    console.print("[dim]Enter CIDR notation, e.g., 192.168.0.0/24[/dim]")
    console.print()
    
    cidr = text_input(
        title="CIDR Range",
        message="Enter CIDR range:"
    )
    
    if not cidr:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not is_valid_cidr(cidr):
        handle_error("E6003", "Invalid CIDR format. Use format like 192.168.0.0/24")
        press_enter_to_continue()
        return
    
    description = text_input(
        title="Description",
        message="Description (optional):",
        default=""
    )
    
    whitelist = _load_whitelist()
    if 'global' not in whitelist:
        whitelist['global'] = {'ips': [], 'ranges': [], 'groups': []}
    
    whitelist['global']['ranges'].append({
        'value': cidr,
        'description': description,
        'added': datetime.now().isoformat()
    })
    
    _save_whitelist(whitelist)
    show_success(f"Range {cidr} added to global whitelist!")
    
    if confirm_action("Apply changes to fail2ban now?"):
        _apply_whitelist_to_fail2ban()
    
    press_enter_to_continue()


def _remove_global_entry():
    """Remove entry from global whitelist."""
    clear_screen()
    show_header()
    show_panel("Remove from Global Whitelist", title="Whitelist", style="cyan")
    
    whitelist = _load_whitelist()
    global_wl = whitelist.get('global', {})
    
    all_entries = []
    for ip in global_wl.get('ips', []):
        val = ip.get('value') if isinstance(ip, dict) else ip
        all_entries.append(('ip', val))
    for r in global_wl.get('ranges', []):
        val = r.get('value') if isinstance(r, dict) else r
        all_entries.append(('range', val))
    
    if not all_entries:
        show_info("No entries to remove.")
        press_enter_to_continue()
        return
    
    options = [f"{t}: {v}" for t, v in all_entries]
    
    selected = select_from_list(
        title="Select Entry",
        message="Choose entry to remove:",
        options=options
    )
    
    if not selected:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    entry_type, value = selected.split(": ", 1)
    
    if not confirm_action(f"Remove {value}?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if entry_type == "ip":
        whitelist['global']['ips'] = [
            x for x in whitelist['global']['ips']
            if (x.get('value') if isinstance(x, dict) else x) != value
        ]
    else:
        whitelist['global']['ranges'] = [
            x for x in whitelist['global']['ranges']
            if (x.get('value') if isinstance(x, dict) else x) != value
        ]
    
    _save_whitelist(whitelist)
    show_success(f"Entry {value} removed!")
    
    if confirm_action("Apply changes to fail2ban now?"):
        _apply_whitelist_to_fail2ban()
    
    press_enter_to_continue()


def perjail_whitelist_menu():
    """Manage per-jail whitelist."""
    clear_screen()
    show_header()
    show_panel("Per-Jail Whitelist", title="Whitelist", style="cyan")
    
    jails = get_active_jails()
    
    if not jails:
        show_info("No active jails found.")
        press_enter_to_continue()
        return
    
    jail = select_from_list(
        title="Select Jail",
        message="Configure whitelist for:",
        options=jails
    )
    
    if not jail:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    _manage_jail_whitelist(jail)


def _manage_jail_whitelist(jail):
    """Manage whitelist for a specific jail."""
    def get_options():
        return [
            ("view", "1. View Whitelist"),
            ("add", "2. Add IP/Range"),
            ("remove", "3. Remove Entry"),
            ("back", "← Back"),
        ]
    
    def view():
        clear_screen()
        show_header()
        show_panel(f"Whitelist for {jail}", title="Whitelist", style="cyan")
        
        whitelist = _load_whitelist()
        jail_wl = whitelist.get('per_jail', {}).get(jail, {})
        
        entries = jail_wl.get('entries', [])
        
        if not entries:
            show_info(f"No per-jail whitelist for {jail}.")
            press_enter_to_continue()
            return
        
        for entry in entries:
            console.print(f"  • {entry}")
        
        press_enter_to_continue()
    
    def add():
        clear_screen()
        show_header()
        
        value = text_input(
            title="Add Entry",
            message="Enter IP or CIDR range:"
        )
        
        if not value:
            return
        
        if not is_valid_ip(value) and not is_valid_cidr(value):
            handle_error("E6003", "Invalid IP or CIDR format.")
            press_enter_to_continue()
            return
        
        whitelist = _load_whitelist()
        if 'per_jail' not in whitelist:
            whitelist['per_jail'] = {}
        if jail not in whitelist['per_jail']:
            whitelist['per_jail'][jail] = {'entries': []}
        
        whitelist['per_jail'][jail]['entries'].append(value)
        _save_whitelist(whitelist)
        show_success(f"Added {value} to {jail} whitelist!")
        
        if confirm_action("Apply to fail2ban?"):
            _apply_whitelist_to_fail2ban()
        
        press_enter_to_continue()
    
    def remove():
        clear_screen()
        show_header()
        
        whitelist = _load_whitelist()
        entries = whitelist.get('per_jail', {}).get(jail, {}).get('entries', [])
        
        if not entries:
            show_info("No entries to remove.")
            press_enter_to_continue()
            return
        
        entry = select_from_list(
            title="Remove Entry",
            message="Select entry to remove:",
            options=entries
        )
        
        if entry and confirm_action(f"Remove {entry}?"):
            whitelist['per_jail'][jail]['entries'].remove(entry)
            _save_whitelist(whitelist)
            show_success(f"Removed {entry}!")
        
        press_enter_to_continue()
    
    handlers = {"view": view, "add": add, "remove": remove}
    run_menu_loop(f"Whitelist: {jail}", get_options, handlers)


def ip_groups_menu():
    """Manage IP groups."""
    def get_options():
        return [
            ("view", "1. View Groups"),
            ("create", "2. Create Group"),
            ("edit", "3. Edit Group"),
            ("delete", "4. Delete Group"),
            ("back", "← Back"),
        ]
    
    handlers = {
        "view": _view_groups,
        "create": _create_group,
        "edit": _edit_group,
        "delete": _delete_group,
    }
    
    run_menu_loop("IP Groups", get_options, handlers)


def _view_groups():
    """View all IP groups."""
    clear_screen()
    show_header()
    show_panel("IP Groups", title="Whitelist", style="cyan")
    
    whitelist = _load_whitelist()
    groups = whitelist.get('groups', {})
    
    if not groups:
        show_info("No IP groups defined.")
        press_enter_to_continue()
        return
    
    for name, data in groups.items():
        console.print(f"[bold cyan]{name}[/bold cyan]")
        if data.get('description'):
            console.print(f"  [dim]{data['description']}[/dim]")
        for entry in data.get('entries', []):
            console.print(f"  • {entry}")
        console.print()
    
    press_enter_to_continue()


def _create_group():
    """Create a new IP group."""
    clear_screen()
    show_header()
    show_panel("Create IP Group", title="Whitelist", style="cyan")
    
    name = text_input(
        title="Group Name",
        message="Enter group name:"
    )
    
    if not name:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    description = text_input(
        title="Description",
        message="Group description (optional):",
        default=""
    )
    
    console.print()
    console.print("[dim]Enter IPs/ranges one per line. Empty line to finish.[/dim]")
    console.print()
    
    entries = []
    while True:
        entry = text_input(
            title="Add Entry",
            message=f"IP/Range #{len(entries)+1} (empty to finish):",
            default=""
        )
        
        if not entry:
            break
        
        if is_valid_ip(entry) or is_valid_cidr(entry):
            entries.append(entry)
        else:
            show_warning(f"Invalid format: {entry}")
    
    if not entries:
        show_warning("No entries added. Cancelled.")
        press_enter_to_continue()
        return
    
    whitelist = _load_whitelist()
    if 'groups' not in whitelist:
        whitelist['groups'] = {}
    
    whitelist['groups'][name] = {
        'description': description,
        'entries': entries,
        'created': datetime.now().isoformat()
    }
    
    _save_whitelist(whitelist)
    show_success(f"Group '{name}' created with {len(entries)} entries!")
    press_enter_to_continue()


def _edit_group():
    """Edit an existing group."""
    clear_screen()
    show_header()
    show_panel("Edit IP Group", title="Whitelist", style="cyan")
    
    whitelist = _load_whitelist()
    groups = whitelist.get('groups', {})
    
    if not groups:
        show_info("No groups to edit.")
        press_enter_to_continue()
        return
    
    name = select_from_list(
        title="Select Group",
        message="Choose group to edit:",
        options=list(groups.keys())
    )
    
    if not name:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    console.print(f"[bold]Current entries in {name}:[/bold]")
    for entry in groups[name].get('entries', []):
        console.print(f"  • {entry}")
    console.print()
    
    action = select_from_list(
        title="Action",
        message="What to do?",
        options=["Add entry", "Remove entry", "Cancel"]
    )
    
    if action == "Add entry":
        entry = text_input(
            title="New Entry",
            message="Enter IP/range to add:"
        )
        if entry and (is_valid_ip(entry) or is_valid_cidr(entry)):
            whitelist['groups'][name]['entries'].append(entry)
            _save_whitelist(whitelist)
            show_success(f"Added {entry} to group!")
    
    elif action == "Remove entry":
        entries = groups[name].get('entries', [])
        if entries:
            entry = select_from_list(
                title="Remove",
                message="Select entry to remove:",
                options=entries
            )
            if entry:
                whitelist['groups'][name]['entries'].remove(entry)
                _save_whitelist(whitelist)
                show_success(f"Removed {entry}!")
    
    press_enter_to_continue()


def _delete_group():
    """Delete an IP group."""
    clear_screen()
    show_header()
    
    whitelist = _load_whitelist()
    groups = whitelist.get('groups', {})
    
    if not groups:
        show_info("No groups to delete.")
        press_enter_to_continue()
        return
    
    name = select_from_list(
        title="Delete Group",
        message="Choose group to delete:",
        options=list(groups.keys())
    )
    
    if name and confirm_action(f"Delete group '{name}'?"):
        del whitelist['groups'][name]
        _save_whitelist(whitelist)
        show_success(f"Group '{name}' deleted!")
    
    press_enter_to_continue()


def trusted_sources_menu():
    """Manage trusted sources."""
    clear_screen()
    show_header()
    show_panel("Trusted Sources", title="Whitelist", style="cyan")
    
    console.print("[dim]Auto-whitelist IPs from trusted services:[/dim]")
    console.print()
    
    trusted = _load_trusted_sources()
    
    for key, source in TRUSTED_SOURCES.items():
        enabled = trusted.get(key, {}).get('enabled', False)
        status = "[green]enabled[/green]" if enabled else "[dim]disabled[/dim]"
        last_update = trusted.get(key, {}).get('last_update', 'never')
        
        console.print(f"[{'x' if enabled else ' '}] {source['name']} ({status})")
        console.print(f"    [dim]{source['description']}[/dim]")
        console.print(f"    [dim]Last update: {last_update}[/dim]")
        console.print()
    
    action = select_from_list(
        title="Action",
        message="Choose action:",
        options=["Toggle source", "Update all enabled", "Back"]
    )
    
    if action == "Toggle source":
        source = select_from_list(
            title="Toggle",
            message="Select source:",
            options=list(TRUSTED_SOURCES.keys())
        )
        if source:
            trusted[source] = trusted.get(source, {})
            trusted[source]['enabled'] = not trusted[source].get('enabled', False)
            _save_trusted_sources(trusted)
            show_success(f"Source '{source}' toggled!")
    
    elif action == "Update all enabled":
        _update_trusted_sources()
    
    press_enter_to_continue()


def _update_trusted_sources():
    """Update IPs from trusted sources."""
    import urllib.request
    
    trusted = _load_trusted_sources()
    whitelist = _load_whitelist()
    
    if 'trusted_ips' not in whitelist:
        whitelist['trusted_ips'] = {}
    
    for key, source in TRUSTED_SOURCES.items():
        if not trusted.get(key, {}).get('enabled', False):
            continue
        
        console.print(f"Updating {source['name']}...")
        
        try:
            with urllib.request.urlopen(source['url'], timeout=10) as response:
                content = response.read().decode('utf-8')
                ips = [line.strip() for line in content.split('\n') if line.strip()]
                
                whitelist['trusted_ips'][key] = {
                    'source': source['name'],
                    'entries': ips,
                    'updated': datetime.now().isoformat()
                }
                
                trusted[key]['last_update'] = datetime.now().isoformat()
                console.print(f"  [green]✓[/green] {len(ips)} entries")
        except Exception as e:
            console.print(f"  [red]✗[/red] Failed: {e}")
    
    _save_whitelist(whitelist)
    _save_trusted_sources(trusted)
    show_success("Trusted sources updated!")


def import_export_menu():
    """Import/export whitelist."""
    clear_screen()
    show_header()
    show_panel("Import/Export", title="Whitelist", style="cyan")
    
    action = select_from_list(
        title="Action",
        message="Choose action:",
        options=["Export to file", "Import from file", "Back"]
    )
    
    if action == "Export to file":
        path = text_input(
            title="Export Path",
            message="Enter file path:",
            default="/tmp/whitelist_export.txt"
        )
        if path:
            _export_whitelist(path)
    
    elif action == "Import from file":
        path = text_input(
            title="Import Path",
            message="Enter file path:"
        )
        if path:
            _import_whitelist(path)
    
    press_enter_to_continue()


def _export_whitelist(path):
    """Export whitelist to file."""
    whitelist = _load_whitelist()
    
    try:
        with open(path, 'w') as f:
            f.write("# Vexo Fail2ban Whitelist Export\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
            
            f.write("# Global IPs\n")
            for ip in whitelist.get('global', {}).get('ips', []):
                val = ip.get('value') if isinstance(ip, dict) else ip
                f.write(f"{val}\n")
            
            f.write("\n# Global Ranges\n")
            for r in whitelist.get('global', {}).get('ranges', []):
                val = r.get('value') if isinstance(r, dict) else r
                f.write(f"{val}\n")
        
        show_success(f"Exported to {path}")
    except Exception as e:
        handle_error("E6003", f"Export failed: {e}")


def _import_whitelist(path):
    """Import whitelist from file."""
    if not os.path.exists(path):
        handle_error("E6003", f"File not found: {path}")
        return
    
    whitelist = _load_whitelist()
    if 'global' not in whitelist:
        whitelist['global'] = {'ips': [], 'ranges': [], 'groups': []}
    
    imported = 0
    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if is_valid_ip(line):
                    whitelist['global']['ips'].append({
                        'value': line,
                        'description': 'Imported',
                        'added': datetime.now().isoformat()
                    })
                    imported += 1
                elif is_valid_cidr(line):
                    whitelist['global']['ranges'].append({
                        'value': line,
                        'description': 'Imported',
                        'added': datetime.now().isoformat()
                    })
                    imported += 1
        
        _save_whitelist(whitelist)
        show_success(f"Imported {imported} entries!")
    except Exception as e:
        handle_error("E6003", f"Import failed: {e}")


def apply_whitelist():
    """Apply whitelist to fail2ban configuration."""
    clear_screen()
    show_header()
    show_panel("Apply Whitelist", title="Whitelist", style="cyan")
    
    console.print("This will update fail2ban ignoreip configuration.")
    console.print()
    
    if not confirm_action("Apply whitelist to fail2ban?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = _apply_whitelist_to_fail2ban()
    
    if success:
        service_control("fail2ban", "reload")
        show_success("Whitelist applied to fail2ban!")
    else:
        handle_error("E6003", "Failed to apply whitelist.")
    
    press_enter_to_continue()


def _apply_whitelist_to_fail2ban():
    """Apply whitelist to fail2ban ignoreip directive."""
    whitelist = _load_whitelist()
    
    all_ips = set()
    
    for ip in whitelist.get('global', {}).get('ips', []):
        val = ip.get('value') if isinstance(ip, dict) else ip
        all_ips.add(val)
    
    for r in whitelist.get('global', {}).get('ranges', []):
        val = r.get('value') if isinstance(r, dict) else r
        all_ips.add(val)
    
    for group_name in whitelist.get('global', {}).get('groups', []):
        group = whitelist.get('groups', {}).get(group_name, {})
        for entry in group.get('entries', []):
            all_ips.add(entry)
    
    for source, data in whitelist.get('trusted_ips', {}).items():
        for entry in data.get('entries', []):
            all_ips.add(entry)
    
    all_ips.add("127.0.0.1")
    all_ips.add("::1")
    
    ignoreip_line = f"ignoreip = {' '.join(sorted(all_ips))}"
    
    try:
        if os.path.exists(JAIL_LOCAL):
            with open(JAIL_LOCAL, 'r') as f:
                lines = f.readlines()
        else:
            lines = ["[DEFAULT]\n"]
        
        new_lines = []
        ignoreip_updated = False
        in_default = False
        
        for line in lines:
            if line.strip() == '[DEFAULT]':
                in_default = True
                new_lines.append(line)
                continue
            elif line.strip().startswith('[') and line.strip() != '[DEFAULT]':
                if in_default and not ignoreip_updated:
                    new_lines.append(f"{ignoreip_line}\n")
                    ignoreip_updated = True
                in_default = False
            
            if in_default and line.strip().startswith('ignoreip'):
                new_lines.append(f"{ignoreip_line}\n")
                ignoreip_updated = True
            else:
                new_lines.append(line)
        
        if in_default and not ignoreip_updated:
            new_lines.append(f"{ignoreip_line}\n")
        
        with open(JAIL_LOCAL, 'w') as f:
            f.writelines(new_lines)
        
        return True
    except Exception as e:
        handle_error("E6003", f"Error: {e}")
        return False


def _load_whitelist():
    """Load whitelist from file."""
    ensure_data_dir()
    if not WHITELIST_FILE.exists():
        return {}
    try:
        with open(WHITELIST_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_whitelist(whitelist):
    """Save whitelist to file."""
    ensure_data_dir()
    try:
        with open(WHITELIST_FILE, 'w') as f:
            json.dump(whitelist, f, indent=2)
        return True
    except Exception:
        return False


def _load_trusted_sources():
    """Load trusted sources config."""
    ensure_data_dir()
    if not TRUSTED_SOURCES_FILE.exists():
        return {}
    try:
        with open(TRUSTED_SOURCES_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_trusted_sources(trusted):
    """Save trusted sources config."""
    ensure_data_dir()
    try:
        with open(TRUSTED_SOURCES_FILE, 'w') as f:
            json.dump(trusted, f, indent=2)
        return True
    except Exception:
        return False
