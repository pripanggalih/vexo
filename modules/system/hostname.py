"""Hostname and timezone management."""

import re
from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_success,
    show_error,
    show_warning,
    press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, require_root, get_hostname


POPULAR_TIMEZONES = [
    ("Asia/Jakarta", "Asia/Jakarta (WIB)"),
    ("Asia/Makassar", "Asia/Makassar (WITA)"),
    ("Asia/Jayapura", "Asia/Jayapura (WIT)"),
    ("Asia/Singapore", "Asia/Singapore"),
    ("Asia/Tokyo", "Asia/Tokyo"),
    ("UTC", "UTC"),
]


def show_hostname_menu():
    """Display Hostname & Timezone submenu."""
    options = [
        ("change_hostname", "1. Change Hostname"),
        ("set_timezone", "2. Set Timezone"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "change_hostname": change_hostname,
        "set_timezone": set_timezone,
    }
    
    run_menu_loop("Hostname & Timezone", options, handlers)


def change_hostname():
    """Change system hostname."""
    clear_screen()
    show_header()
    show_panel("Change Hostname", title="System Setup", style="cyan")
    
    current = get_hostname()
    console.print(f"Current hostname: [cyan]{current}[/cyan]")
    console.print()
    
    new_hostname = text_input("Enter new hostname:")
    if not new_hostname:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', new_hostname):
        show_error("Invalid hostname. Use alphanumeric and hyphens only.")
        show_error("Must start and end with alphanumeric character.")
        press_enter_to_continue()
        return
    
    if not confirm_action(f"Change hostname from '{current}' to '{new_hostname}'?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    result = run_command(f"hostnamectl set-hostname {new_hostname}", check=False, silent=True)
    if result.returncode != 0:
        show_error("Failed to set hostname.")
        press_enter_to_continue()
        return
    
    run_command(f"sed -i 's/{current}/{new_hostname}/g' /etc/hosts", check=False, silent=True)
    
    show_success(f"Hostname changed to '{new_hostname}'")
    show_warning("A reboot may be required for full effect.")
    press_enter_to_continue()


def set_timezone():
    """Set system timezone."""
    clear_screen()
    show_header()
    show_panel("Set Timezone", title="System Setup", style="cyan")
    
    result = run_command("timedatectl show --property=Timezone --value", check=False, silent=True)
    current_tz = result.stdout.strip() if result.returncode == 0 else "Unknown"
    console.print(f"Current timezone: [cyan]{current_tz}[/cyan]")
    console.print()
    
    tz_options = [label for _, label in POPULAR_TIMEZONES]
    tz_options.append("Other (search)...")
    
    choice = select_from_list("Select Timezone", "Choose timezone:", tz_options)
    if not choice:
        return
    
    if choice == "Other (search)...":
        result = run_command("timedatectl list-timezones", check=False, silent=True)
        if result.returncode != 0:
            show_error("Failed to list timezones.")
            press_enter_to_continue()
            return
        
        all_tz = result.stdout.strip().split('\n')
        timezone = select_from_list("All Timezones", "Search and select:", all_tz)
        if not timezone:
            return
    else:
        timezone = None
        for tz_val, tz_label in POPULAR_TIMEZONES:
            if tz_label == choice:
                timezone = tz_val
                break
    
    if not timezone:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    result = run_command(f"timedatectl set-timezone {timezone}", check=False, silent=True)
    if result.returncode == 0:
        show_success(f"Timezone set to {timezone}")
    else:
        show_error("Failed to set timezone.")
    
    press_enter_to_continue()
