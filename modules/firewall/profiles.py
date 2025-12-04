"""Application profiles for firewall."""

from ui.components import (
    clear_screen,
    show_header,
    show_panel,
    show_info,
    press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.firewall.common import get_ufw_status_text


def show_profiles_menu():
    """Display application profiles submenu."""
    def get_status():
        return f"UFW: {get_ufw_status_text()}"
    
    options = [
        ("list", "1. List Profiles"),
        ("apply", "2. Apply Profile"),
        ("create", "3. Create Custom Profile"),
        ("edit", "4. Edit/Delete Profile"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "list": _placeholder,
        "apply": _placeholder,
        "create": _placeholder,
        "edit": _placeholder,
    }
    
    run_menu_loop("Application Profiles", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Application Profiles", style="cyan")
    show_info("This feature will be implemented in Phase 5.")
    press_enter_to_continue()
