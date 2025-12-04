"""Logging and monitoring for firewall."""

from ui.components import (
    clear_screen,
    show_header,
    show_panel,
    show_info,
    press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.firewall.common import get_ufw_status_text


def show_logs_menu():
    """Display logs and monitoring submenu."""
    def get_status():
        return f"UFW: {get_ufw_status_text()}"
    
    options = [
        ("view", "1. View Firewall Logs"),
        ("stats", "2. Blocked Attempts Stats"),
        ("settings", "3. Log Settings"),
        ("live", "4. Live Monitor"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "view": _placeholder,
        "stats": _placeholder,
        "settings": _placeholder,
        "live": _placeholder,
    }
    
    run_menu_loop("Logs & Monitoring", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Logs & Monitoring", style="cyan")
    show_info("This feature will be implemented in Phase 6.")
    press_enter_to_continue()
