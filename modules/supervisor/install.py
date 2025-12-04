"""Supervisor installation for vexo."""

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
from ui.menu import confirm_action
from utils.shell import (
    run_command_realtime,
    is_installed,
    is_service_running,
    service_control,
    require_root,
)
from utils.error_handler import handle_error


def install_supervisor():
    """Install Supervisor."""
    clear_screen()
    show_header()
    show_panel("Install Supervisor", title="Queue Workers", style="cyan")
    
    if is_installed("supervisor"):
        show_info("Supervisor is already installed.")
        
        if is_service_running("supervisor"):
            console.print("[dim]Service is running.[/dim]")
        else:
            if confirm_action("Start Supervisor service?"):
                service_control("supervisor", "start")
                show_success("Supervisor started!")
        
        press_enter_to_continue()
        return
    
    console.print("[bold]Supervisor will be installed for:[/bold]")
    console.print("  - Managing queue workers (Laravel, Node.js, Python)")
    console.print("  - Auto-restart on failure")
    console.print("  - Process monitoring")
    console.print()
    
    if not confirm_action("Install Supervisor?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    show_info("Installing Supervisor...")
    
    returncode = run_command_realtime(
        "apt install -y supervisor",
        "Installing Supervisor..."
    )
    
    if returncode != 0:
        handle_error("E7001", "Failed to install Supervisor")
        press_enter_to_continue()
        return
    
    service_control("supervisor", "start")
    service_control("supervisor", "enable")
    
    if is_service_running("supervisor"):
        show_success("Supervisor installed and running!")
    else:
        show_warning("Supervisor installed but service may not be running.")
    
    press_enter_to_continue()
