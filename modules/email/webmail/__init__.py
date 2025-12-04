"""Roundcube webmail management (optional)."""

import os

from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_info, press_enter_to_continue,
)
from ui.menu import run_menu_loop
from utils.shell import is_installed


def show_menu():
    """Display Webmail Management submenu."""
    def get_status():
        if os.path.exists("/var/www/roundcube") or is_installed("roundcube"):
            return "Roundcube: [green]Installed[/green]"
        return "Roundcube: [dim]Not Installed[/dim]"
    
    def get_options():
        installed = os.path.exists("/var/www/roundcube") or is_installed("roundcube")
        
        if installed:
            return [
                ("config", "1. Configure"),
                ("plugins", "2. Plugins"),
                ("update", "3. Update"),
                ("back", "← Back"),
            ]
        return [
            ("install", "1. Install Roundcube"),
            ("back", "← Back"),
        ]
    
    def get_handlers():
        return {
            "install": _coming_soon,
            "config": _coming_soon,
            "plugins": _coming_soon,
            "update": _coming_soon,
        }
    
    run_menu_loop("Webmail (Roundcube)", get_options, get_handlers(), get_status)


def _coming_soon():
    """Placeholder for features to be implemented."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Webmail", style="yellow")
    show_info("This feature will be implemented in a future update.")
    press_enter_to_continue()
