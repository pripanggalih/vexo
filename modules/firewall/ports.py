"""Port management for firewall."""

from ui.components import (
    clear_screen,
    show_header,
    show_panel,
    show_info,
    press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.firewall.common import get_ufw_status_text


def show_ports_menu():
    """Display port management submenu."""
    def get_status():
        return f"UFW: {get_ufw_status_text()}"
    
    options = [
        ("add", "1. Add Custom Port"),
        ("presets", "2. Port Presets"),
        ("remove", "3. Remove Port"),
        ("list", "4. List Open Ports"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "add": _placeholder,
        "presets": _placeholder,
        "remove": _placeholder,
        "list": _placeholder,
    }
    
    run_menu_loop("Port Management", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Port Management", style="cyan")
    show_info("This feature will be implemented in Phase 2.")
    press_enter_to_continue()
