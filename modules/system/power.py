"""Power management - reboot, shutdown, schedule."""

import time
from utils.error_handler import handle_error
from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_success,
    
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, run_menu_loop
from utils.shell import run_command, require_root


def show_power_menu():
    """Display Reboot/Shutdown submenu."""
    options = [
        ("reboot", "1. Reboot Now"),
        ("shutdown", "2. Shutdown Now"),
        ("schedule", "3. Schedule Reboot"),
        ("cancel", "4. Cancel Scheduled Reboot/Shutdown"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "reboot": reboot_now,
        "shutdown": shutdown_now,
        "schedule": schedule_reboot,
        "cancel": cancel_scheduled,
    }
    
    run_menu_loop("Reboot / Shutdown", options, handlers)


def reboot_now():
    """Reboot the system immediately."""
    clear_screen()
    show_header()
    show_panel("Reboot System", title="System Setup", style="red")
    
    show_warning("⚠️  WARNING: This will REBOOT the server!")
    show_warning("All connections will be terminated.")
    console.print()
    
    console.print("[bold red]Type 'REBOOT' to confirm:[/bold red]")
    confirm_text = text_input("Confirm:")
    
    if confirm_text != "REBOOT":
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print()
    show_warning("Rebooting in 5 seconds... (Ctrl+C to cancel)")
    
    try:
        for i in range(5, 0, -1):
            console.print(f"[bold red]{i}...[/bold red]")
            time.sleep(1)
    except KeyboardInterrupt:
        console.print()
        show_info("Reboot cancelled.")
        press_enter_to_continue()
        return
    
    run_command("reboot", check=False, silent=True)


def shutdown_now():
    """Shutdown the system immediately."""
    clear_screen()
    show_header()
    show_panel("Shutdown System", title="System Setup", style="red")
    
    show_warning("⚠️  WARNING: This will SHUTDOWN the server!")
    show_warning("You will need physical/console access to turn it back on.")
    console.print()
    
    console.print("[bold red]Type 'SHUTDOWN' to confirm:[/bold red]")
    confirm_text = text_input("Confirm:")
    
    if confirm_text != "SHUTDOWN":
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print()
    show_warning("Shutting down in 5 seconds... (Ctrl+C to cancel)")
    
    try:
        for i in range(5, 0, -1):
            console.print(f"[bold red]{i}...[/bold red]")
            time.sleep(1)
    except KeyboardInterrupt:
        console.print()
        show_info("Shutdown cancelled.")
        press_enter_to_continue()
        return
    
    run_command("shutdown -h now", check=False, silent=True)


def schedule_reboot():
    """Schedule a system reboot."""
    clear_screen()
    show_header()
    show_panel("Schedule Reboot", title="System Setup", style="cyan")
    
    minutes = text_input("Reboot in how many minutes?")
    if not minutes:
        press_enter_to_continue()
        return
    
    try:
        mins = int(minutes)
        if mins < 1:
            raise ValueError()
    except ValueError:
        handle_error("E1005", "Invalid number of minutes.")
        press_enter_to_continue()
        return
    
    if not confirm_action(f"Schedule reboot in {mins} minutes?"):
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    run_command(f"shutdown -r +{mins}", check=False, silent=True)
    show_success(f"Reboot scheduled in {mins} minutes.")
    show_info("Run 'Cancel Scheduled Reboot' to cancel.")
    press_enter_to_continue()


def cancel_scheduled():
    """Cancel any scheduled reboot/shutdown."""
    clear_screen()
    show_header()
    show_panel("Cancel Scheduled Reboot/Shutdown", title="System Setup", style="cyan")
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    result = run_command("shutdown -c", check=False, silent=True)
    if result.returncode == 0:
        show_success("Scheduled reboot/shutdown cancelled.")
    else:
        show_info("No scheduled reboot/shutdown to cancel.")
    
    press_enter_to_continue()
