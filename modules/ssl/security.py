"""SSL security audit."""

from ui.components import (
    clear_screen, show_header, show_panel, show_info, press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.ssl.common import get_certbot_status_text


def show_security_menu():
    """Display security audit submenu."""
    def get_status():
        return f"Certbot: {get_certbot_status_text()}"
    
    options = [
        ("quick", "1. Quick Check"),
        ("full", "2. Full SSL Audit"),
        ("headers", "3. Security Headers"),
        ("recommend", "4. Get Recommendations"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "quick": _placeholder,
        "full": _placeholder,
        "headers": _placeholder,
        "recommend": _placeholder,
    }
    
    run_menu_loop("Security Audit", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Security Audit", style="cyan")
    show_info("This feature will be implemented in Phase 6.")
    press_enter_to_continue()
