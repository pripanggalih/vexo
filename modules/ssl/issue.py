"""Issue SSL certificates."""

from ui.components import (
    clear_screen, show_header, show_panel, show_info, press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.ssl.common import get_certbot_status_text


def show_issue_menu():
    """Display issue certificate submenu."""
    def get_status():
        return f"Certbot: {get_certbot_status_text()}"
    
    options = [
        ("single", "1. Single Domain"),
        ("san", "2. Multiple Domains (SAN)"),
        ("wildcard", "3. Wildcard Certificate"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "single": _placeholder,
        "san": _placeholder,
        "wildcard": _placeholder,
    }
    
    run_menu_loop("Issue Certificate", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Issue Certificate", style="cyan")
    show_info("This feature will be implemented in Phase 2.")
    press_enter_to_continue()
