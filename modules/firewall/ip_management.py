"""IP management for firewall."""

from ui.components import (
    clear_screen,
    show_header,
    show_panel,
    show_info,
    press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.firewall.common import get_ufw_status_text


def show_ip_menu():
    """Display IP management submenu."""
    def get_status():
        return f"UFW: {get_ufw_status_text()}"
    
    options = [
        ("allow", "1. Allow IP"),
        ("deny", "2. Deny/Block IP"),
        ("whitelist", "3. IP Whitelist"),
        ("groups", "4. IP Groups"),
        ("list", "5. List IP Rules"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "allow": _placeholder,
        "deny": _placeholder,
        "whitelist": _placeholder,
        "groups": _placeholder,
        "list": _placeholder,
    }
    
    run_menu_loop("IP Management", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="IP Management", style="cyan")
    show_info("This feature will be implemented in Phase 3.")
    press_enter_to_continue()
