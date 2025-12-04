"""Import custom SSL certificates."""

from ui.components import (
    clear_screen, show_header, show_panel, show_info, press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.ssl.common import get_certbot_status_text


def show_import_menu():
    """Display import certificate submenu."""
    def get_status():
        return f"Certbot: {get_certbot_status_text()}"
    
    options = [
        ("pem", "1. Upload PEM Files"),
        ("pfx", "2. Upload PFX/PKCS12"),
        ("paste", "3. Paste Certificate"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "pem": _placeholder,
        "pfx": _placeholder,
        "paste": _placeholder,
    }
    
    run_menu_loop("Import Certificate", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Import Certificate", style="cyan")
    show_info("This feature will be implemented in Phase 3.")
    press_enter_to_continue()
