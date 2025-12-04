"""Ban management for fail2ban module."""

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
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, require_root

from .common import (
    is_fail2ban_installed,
    is_fail2ban_running,
    get_active_jails,
    get_jail_stats,
    get_banned_ips,
    get_all_banned_ips,
    is_valid_ip,
    is_valid_cidr,
    VEXO_FAIL2BAN_DIR,
    ensure_data_dir,
)


PERMANENT_BANS_FILE = VEXO_FAIL2BAN_DIR / "permanent_bans.json"


def show_menu():
    """Display ban management menu."""
    def get_status():
        total = sum(
            get_jail_stats(j).get('currently_banned', 0)
            for j in get_active_jails()
        )
        return f"{total} IPs currently banned"
    
    def get_options():
        return [
            ("list", "1. List Banned IPs"),
            ("ban", "2. Ban IP"),
            ("unban", "3. Unban IP"),
            ("permanent", "4. Permanent Ban List"),
            ("search", "5. Search IP"),
            ("back", "← Back"),
        ]
    
    handlers = {
        "list": list_banned_ips_menu,
        "ban": ban_ip_menu,
        "unban": unban_ip_menu,
        "permanent": permanent_ban_menu,
        "search": search_ip,
    }
    
    run_menu_loop("Ban Management", get_options, handlers, get_status)


def list_banned_ips_menu():
    """List banned IPs with options."""
    clear_screen()
    show_header()
    show_panel("Banned IPs", title="Ban Management", style="cyan")
    
    jails = get_active_jails()
    
    if not jails:
        show_info("No active jails found.")
        press_enter_to_continue()
        return
    
    options = ["(all jails)"] + jails
    
    jail = select_from_list(
        title="Select Jail",
        message="View banned IPs for:",
        options=options
    )
    
    if not jail:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if jail == "(all jails)":
        _list_all_banned()
    else:
        _list_banned_for_jail(jail)
    
    press_enter_to_continue()


def _list_all_banned():
    """List all banned IPs across all jails."""
    all_banned = get_all_banned_ips()
    
    if not any(all_banned.values()):
        show_info("No IPs currently banned.")
        return
    
    columns = [
        {"name": "IP Address", "style": "cyan"},
        {"name": "Jail"},
    ]
    
    rows = []
    for jail, ips in all_banned.items():
        for ip in ips:
            rows.append([ip, jail])
    
    show_table(f"All Banned IPs ({len(rows)} total)", columns, rows)


def _list_banned_for_jail(jail):
    """List banned IPs for a specific jail."""
    ips = get_banned_ips(jail)
    
    if not ips:
        show_info(f"No IPs currently banned in {jail}.")
        return
    
    columns = [
        {"name": "#", "style": "dim", "width": 4},
        {"name": "IP Address", "style": "cyan"},
    ]
    
    rows = [[str(i), ip] for i, ip in enumerate(ips, 1)]
    
    show_table(f"Banned IPs in {jail} ({len(ips)} total)", columns, rows)


def ban_ip_menu():
    """Ban an IP address."""
    clear_screen()
    show_header()
    show_panel("Ban IP", title="Ban Management", style="cyan")
    
    jails = get_active_jails()
    
    if not jails:
        show_error("No active jails to ban IP in.")
        press_enter_to_continue()
        return
    
    ip = text_input(
        title="IP Address",
        message="Enter IP address to ban:"
    )
    
    if not ip:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not is_valid_ip(ip):
        show_error("Invalid IP address format.")
        press_enter_to_continue()
        return
    
    jail = select_from_list(
        title="Select Jail",
        message="Ban in which jail?",
        options=jails
    )
    
    if not jail:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    console.print()
    add_permanent = confirm_action("Add to permanent ban list?", default=False)
    
    reason = ""
    if add_permanent:
        reason = text_input(
            title="Reason",
            message="Reason for permanent ban (optional):",
            default=""
        )
    
    console.print()
    console.print(f"[yellow]This will ban {ip} in jail '{jail}'.[/yellow]")
    console.print()
    
    if not confirm_action(f"Ban {ip}?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = ban_ip(ip, jail)
    
    if success:
        show_success(f"IP {ip} banned in {jail}!")
        
        if add_permanent:
            _add_to_permanent_list(ip, jail, reason)
            show_info("Added to permanent ban list.")
    else:
        show_error(f"Failed to ban {ip}")
    
    press_enter_to_continue()


def ban_ip(ip, jail):
    """Ban an IP in a specific jail."""
    result = run_command(
        f"fail2ban-client set {jail} banip {ip}",
        check=False,
        silent=True
    )
    return result.returncode == 0


def unban_ip_menu():
    """Unban an IP address."""
    clear_screen()
    show_header()
    show_panel("Unban IP", title="Ban Management", style="cyan")
    
    ip = text_input(
        title="IP Address",
        message="Enter IP address to unban:"
    )
    
    if not ip:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not is_valid_ip(ip):
        show_error("Invalid IP address format.")
        press_enter_to_continue()
        return
    
    all_banned = get_all_banned_ips()
    found_in = [jail for jail, ips in all_banned.items() if ip in ips]
    
    if not found_in:
        show_warning(f"IP {ip} is not currently banned.")
        press_enter_to_continue()
        return
    
    console.print(f"[dim]IP found banned in: {', '.join(found_in)}[/dim]")
    console.print()
    
    options = ["(all jails)"] + found_in
    
    jail = select_from_list(
        title="Unban From",
        message="Unban from which jail?",
        options=options
    )
    
    if not jail:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if _is_in_permanent_list(ip):
        console.print()
        console.print("[yellow]This IP is in the permanent ban list.[/yellow]")
        if confirm_action("Remove from permanent list too?"):
            _remove_from_permanent_list(ip)
    
    if not confirm_action(f"Unban {ip}?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if jail == "(all jails)":
        success = unban_ip_all(ip)
    else:
        success = unban_ip(ip, jail)
    
    if success:
        show_success(f"IP {ip} unbanned!")
    else:
        show_error(f"Failed to unban {ip}")
    
    press_enter_to_continue()


def unban_ip(ip, jail):
    """Unban an IP from a specific jail."""
    result = run_command(
        f"fail2ban-client set {jail} unbanip {ip}",
        check=False,
        silent=True
    )
    return result.returncode == 0


def unban_ip_all(ip):
    """Unban an IP from all jails."""
    jails = get_active_jails()
    unbanned = False
    
    for jail in jails:
        result = run_command(
            f"fail2ban-client set {jail} unbanip {ip}",
            check=False,
            silent=True
        )
        if result.returncode == 0:
            unbanned = True
    
    return unbanned


def permanent_ban_menu():
    """Manage permanent ban list."""
    def get_status():
        bans = _load_permanent_bans()
        return f"{len(bans)} permanent bans"
    
    def get_options():
        return [
            ("list", "1. List Permanent Bans"),
            ("add", "2. Add to Permanent List"),
            ("remove", "3. Remove from List"),
            ("apply", "4. Apply All Permanent Bans"),
            ("back", "← Back"),
        ]
    
    handlers = {
        "list": _list_permanent_bans,
        "add": _add_permanent_ban,
        "remove": _remove_permanent_ban,
        "apply": _apply_permanent_bans,
    }
    
    run_menu_loop("Permanent Ban List", get_options, handlers, get_status)


def _list_permanent_bans():
    """List all permanent bans."""
    clear_screen()
    show_header()
    show_panel("Permanent Ban List", title="Ban Management", style="cyan")
    
    bans = _load_permanent_bans()
    
    if not bans:
        show_info("No permanent bans configured.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "IP Address", "style": "cyan"},
        {"name": "Jail"},
        {"name": "Reason"},
        {"name": "Added", "style": "dim"},
    ]
    
    rows = []
    for ip, data in bans.items():
        rows.append([
            ip,
            data.get('jail', 'all'),
            data.get('reason', '-'),
            data.get('added', '-')[:10],
        ])
    
    show_table(f"Permanent Bans ({len(bans)} total)", columns, rows)
    
    press_enter_to_continue()


def _add_permanent_ban():
    """Add IP to permanent ban list."""
    clear_screen()
    show_header()
    show_panel("Add Permanent Ban", title="Ban Management", style="cyan")
    
    ip = text_input(
        title="IP Address",
        message="Enter IP to permanently ban:"
    )
    
    if not ip:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not is_valid_ip(ip) and not is_valid_cidr(ip):
        show_error("Invalid IP address or CIDR format.")
        press_enter_to_continue()
        return
    
    if _is_in_permanent_list(ip):
        show_warning(f"IP {ip} is already in permanent list.")
        press_enter_to_continue()
        return
    
    jails = get_active_jails()
    jail = select_from_list(
        title="Apply to Jail",
        message="Apply permanent ban to which jail?",
        options=["(all jails)"] + jails
    )
    
    if not jail:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    jail = "all" if jail == "(all jails)" else jail
    
    reason = text_input(
        title="Reason",
        message="Reason for ban (optional):",
        default=""
    )
    
    _add_to_permanent_list(ip, jail, reason)
    show_success(f"IP {ip} added to permanent ban list!")
    
    if confirm_action("Ban IP now?"):
        try:
            require_root()
            if jail == "all":
                for j in jails:
                    ban_ip(ip, j)
            else:
                ban_ip(ip, jail)
            show_success("IP banned!")
        except PermissionError:
            pass
    
    press_enter_to_continue()


def _remove_permanent_ban():
    """Remove IP from permanent ban list."""
    clear_screen()
    show_header()
    show_panel("Remove Permanent Ban", title="Ban Management", style="cyan")
    
    bans = _load_permanent_bans()
    
    if not bans:
        show_info("No permanent bans to remove.")
        press_enter_to_continue()
        return
    
    ip = select_from_list(
        title="Select IP",
        message="Choose IP to remove:",
        options=list(bans.keys())
    )
    
    if not ip:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not confirm_action(f"Remove {ip} from permanent list?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    _remove_from_permanent_list(ip)
    show_success(f"IP {ip} removed from permanent list!")
    
    if confirm_action("Unban IP now?"):
        try:
            require_root()
            unban_ip_all(ip)
            show_success("IP unbanned!")
        except PermissionError:
            pass
    
    press_enter_to_continue()


def _apply_permanent_bans():
    """Apply all permanent bans."""
    clear_screen()
    show_header()
    show_panel("Apply Permanent Bans", title="Ban Management", style="cyan")
    
    bans = _load_permanent_bans()
    
    if not bans:
        show_info("No permanent bans to apply.")
        press_enter_to_continue()
        return
    
    console.print(f"This will ban {len(bans)} IP(s) across configured jails.")
    console.print()
    
    if not confirm_action("Apply all permanent bans?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    jails = get_active_jails()
    applied = 0
    
    for ip, data in bans.items():
        target_jail = data.get('jail', 'all')
        
        if target_jail == 'all':
            for jail in jails:
                if ban_ip(ip, jail):
                    applied += 1
        else:
            if ban_ip(ip, target_jail):
                applied += 1
    
    show_success(f"Applied {applied} ban(s)!")
    press_enter_to_continue()


def search_ip():
    """Search for an IP in banned lists and history."""
    clear_screen()
    show_header()
    show_panel("Search IP", title="Ban Management", style="cyan")
    
    ip = text_input(
        title="Search",
        message="Enter IP address to search:"
    )
    
    if not ip:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print(f"[bold]Results for {ip}:[/bold]")
    console.print()
    
    all_banned = get_all_banned_ips()
    found_in = [jail for jail, ips in all_banned.items() if ip in ips]
    
    if found_in:
        console.print(f"[green]Currently banned in:[/green] {', '.join(found_in)}")
    else:
        console.print("[dim]Not currently banned[/dim]")
    
    if _is_in_permanent_list(ip):
        bans = _load_permanent_bans()
        data = bans.get(ip, {})
        console.print(f"[yellow]In permanent list:[/yellow] jail={data.get('jail', 'all')}, reason={data.get('reason', '-')}")
    else:
        console.print("[dim]Not in permanent list[/dim]")
    
    console.print()
    press_enter_to_continue()


def _load_permanent_bans():
    """Load permanent bans from file."""
    ensure_data_dir()
    
    if not PERMANENT_BANS_FILE.exists():
        return {}
    
    try:
        with open(PERMANENT_BANS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_permanent_bans(bans):
    """Save permanent bans to file."""
    ensure_data_dir()
    
    try:
        with open(PERMANENT_BANS_FILE, 'w') as f:
            json.dump(bans, f, indent=2)
        return True
    except Exception:
        return False


def _add_to_permanent_list(ip, jail, reason=""):
    """Add IP to permanent ban list."""
    bans = _load_permanent_bans()
    bans[ip] = {
        'jail': jail,
        'reason': reason,
        'added': datetime.now().isoformat(),
    }
    _save_permanent_bans(bans)


def _remove_from_permanent_list(ip):
    """Remove IP from permanent ban list."""
    bans = _load_permanent_bans()
    if ip in bans:
        del bans[ip]
        _save_permanent_bans(bans)


def _is_in_permanent_list(ip):
    """Check if IP is in permanent ban list."""
    bans = _load_permanent_bans()
    return ip in bans
