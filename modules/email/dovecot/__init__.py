"""Dovecot mailbox server management (optional)."""

from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_info, press_enter_to_continue,
)
from ui.menu import run_menu_loop
from utils.shell import is_installed, is_service_running


def show_menu():
    """Display Dovecot Management submenu."""
    def get_status():
        if not is_installed("dovecot-core"):
            return "Dovecot: [dim]Not Installed[/dim]"
        if is_service_running("dovecot"):
            return "Dovecot: [green]Running[/green]"
        return "Dovecot: [red]Stopped[/red]"
    
    def get_options():
        if is_installed("dovecot-core"):
            return [
                ("mailboxes", "1. Mailbox Management"),
                ("quota", "2. Quota Settings"),
                ("ssl", "3. SSL/TLS Certificates"),
                ("service", "4. Service Control"),
                ("back", "← Back"),
            ]
        return [
            ("install", "1. Install Dovecot"),
            ("back", "← Back"),
        ]
    
    def get_handlers():
        return {
            "install": _coming_soon,
            "mailboxes": _coming_soon,
            "quota": _coming_soon,
            "ssl": _coming_soon,
            "service": _coming_soon,
        }
    
    run_menu_loop("Dovecot Mailbox Server", get_options, get_handlers(), get_status)


def _coming_soon():
    """Placeholder for features to be implemented."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Dovecot", style="yellow")
    show_info("This feature will be implemented in a future update.")
    press_enter_to_continue()
