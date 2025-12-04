"""SSL settings and alerts configuration."""

from ui.components import (
    clear_screen, show_header, show_panel, show_info, press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.ssl.common import get_certbot_status_text


def show_settings_menu():
    """Display settings submenu."""
    def get_status():
        return f"Certbot: {get_certbot_status_text()}"
    
    options = [
        ("ca", "1. Default CA"),
        ("alerts", "2. Alert Settings"),
        ("renewal", "3. Auto-Renewal Config"),
        ("monitor", "4. Monitoring Schedule"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "ca": _placeholder,
        "alerts": _placeholder,
        "renewal": _placeholder,
        "monitor": _placeholder,
    }
    
    run_menu_loop("Settings", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Settings", style="cyan")
    show_info("This feature will be implemented in Phase 8.")
    press_enter_to_continue()
