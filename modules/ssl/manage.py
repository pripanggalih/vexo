"""Manage SSL certificates."""

from ui.components import (
    clear_screen, show_header, show_panel, show_info, press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.ssl.common import get_certbot_status_text


def show_manage_menu():
    """Display manage certificates submenu."""
    def get_status():
        return f"Certbot: {get_certbot_status_text()}"
    
    options = [
        ("details", "1. View Details"),
        ("renew", "2. Renew Certificate"),
        ("revoke", "3. Revoke Certificate"),
        ("delete", "4. Delete Certificate"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "details": _placeholder,
        "renew": _placeholder,
        "revoke": _placeholder,
        "delete": _placeholder,
    }
    
    run_menu_loop("Manage Certificates", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Manage Certificates", style="cyan")
    show_info("This feature will be implemented in Phase 4.")
    press_enter_to_continue()
