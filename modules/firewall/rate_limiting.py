"""Rate limiting for firewall."""

from ui.components import (
    clear_screen,
    show_header,
    show_panel,
    show_info,
    press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.firewall.common import get_ufw_status_text


def show_rate_limit_menu():
    """Display rate limiting submenu."""
    def get_status():
        return f"UFW: {get_ufw_status_text()}"
    
    options = [
        ("enable", "1. Enable Rate Limit"),
        ("config", "2. Configure Limits"),
        ("list", "3. List Rate Limits"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "enable": _placeholder,
        "config": _placeholder,
        "list": _placeholder,
    }
    
    run_menu_loop("Rate Limiting", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Rate Limiting", style="cyan")
    show_info("This feature will be implemented in Phase 4.")
    press_enter_to_continue()
