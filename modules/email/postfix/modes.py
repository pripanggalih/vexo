"""Postfix mode configuration (send-only, receive)."""

from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, run_menu_loop
from utils.shell import is_installed, is_service_running, require_root
from modules.email.postfix.utils import (
    get_postfix_mode, set_postfix_settings, restart_postfix,
)


def show_modes_menu():
    """Display mode configuration menu."""
    def get_status():
        mode = get_postfix_mode()
        if mode == "send-only":
            return "Current: [cyan]Send-Only[/cyan]"
        elif mode == "receive":
            return "Current: [yellow]Receive[/yellow]"
        return f"Current: [dim]{mode}[/dim]"
    
    options = [
        ("send", "1. Send-Only Mode"),
        ("receive", "2. Receive Mode"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "send": setup_send_only,
        "receive": setup_receive_mode,
    }
    
    run_menu_loop("Configure Mode", options, handlers, get_status)


def setup_send_only():
    """Configure Postfix for send-only mode."""
    clear_screen()
    show_header()
    show_panel("Send-Only Mode", title="Postfix", style="cyan")
    
    if not is_installed("postfix"):
        show_error("Postfix is not installed.")
        press_enter_to_continue()
        return
    
    current_mode = get_postfix_mode()
    if current_mode == "send-only":
        show_info("Already in send-only mode.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Send-Only Mode will:[/bold]")
    console.print("  • Listen on localhost only (127.0.0.1)")
    console.print("  • Disable incoming mail from outside")
    console.print("  • Allow sending outgoing emails")
    console.print("  • Disable local mailbox delivery")
    console.print()
    console.print("[dim]Ideal for application servers that only need to")
    console.print("send notifications and transactional emails.[/dim]")
    console.print()
    
    if not confirm_action("Switch to send-only mode?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    show_info("Configuring send-only mode...")
    
    settings = {
        "inet_interfaces": "loopback-only",
        "mydestination": "$myhostname, localhost.$mydomain, localhost",
        "local_transport": "error:local delivery disabled",
    }
    
    if set_postfix_settings(settings):
        restart_postfix()
        
        if is_service_running("postfix"):
            show_success("Send-only mode configured!")
            console.print()
            console.print("[dim]Postfix now only listens on localhost.[/dim]")
        else:
            show_warning("Configuration applied but Postfix may not be running.")
    else:
        show_error("Failed to configure send-only mode.")
    
    press_enter_to_continue()


def setup_receive_mode():
    """Configure Postfix for receive mode."""
    clear_screen()
    show_header()
    show_panel("Receive Mode", title="Postfix", style="cyan")
    
    if not is_installed("postfix"):
        show_error("Postfix is not installed.")
        press_enter_to_continue()
        return
    
    current_mode = get_postfix_mode()
    if current_mode == "receive":
        show_info("Already in receive mode.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Receive Mode will:[/bold]")
    console.print("  • Listen on all interfaces (port 25)")
    console.print("  • Accept incoming email for configured domains")
    console.print("  • Can pipe emails to applications")
    console.print()
    console.print("[yellow]Prerequisites:[/yellow]")
    console.print("  • DNS MX record pointing to this server")
    console.print("  • Port 25 open in firewall")
    console.print("  • Domain(s) configured in Domain Management")
    console.print()
    
    if not confirm_action("Switch to receive mode?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    show_info("Configuring receive mode...")
    
    settings = {
        "inet_interfaces": "all",
        "mydestination": "$myhostname, localhost.$mydomain, localhost",
    }
    
    # Remove local_transport restriction
    from utils.shell import run_command
    run_command("postconf -X local_transport 2>/dev/null", check=False, silent=True)
    
    if set_postfix_settings(settings):
        restart_postfix()
        
        if is_service_running("postfix"):
            show_success("Receive mode configured!")
            console.print()
            console.print("[yellow]Remember to:[/yellow]")
            console.print("  • Configure domains in Domain Management")
            console.print("  • Setup MX DNS record")
            console.print("  • Open port 25 in firewall")
        else:
            show_warning("Configuration applied but Postfix may not be running.")
    else:
        show_error("Failed to configure receive mode.")
    
    press_enter_to_continue()
