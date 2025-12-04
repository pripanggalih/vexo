"""Roundcube webmail management (optional)."""

import os

from ui.menu import run_menu_loop
from utils.shell import is_installed


def _is_roundcube_installed():
    """Check if Roundcube is installed."""
    return os.path.exists("/var/www/roundcube") or os.path.exists("/usr/share/roundcube")


def show_menu():
    """Display Webmail Management submenu."""
    def get_status():
        if _is_roundcube_installed():
            return "Roundcube: [green]Installed[/green]"
        return "Roundcube: [dim]Not Installed[/dim]"
    
    def get_options():
        if _is_roundcube_installed():
            return [
                ("status", "1. View Status"),
                ("config", "2. Configure"),
                ("plugins", "3. Plugins"),
                ("update", "4. Update"),
                ("back", "← Back"),
            ]
        return [
            ("install", "1. Install Roundcube"),
            ("back", "← Back"),
        ]
    
    def get_handlers():
        from modules.email.webmail.roundcube import (
            install_roundcube, view_status, configure_roundcube,
            manage_plugins, update_roundcube,
        )
        
        return {
            "install": install_roundcube,
            "status": view_status,
            "config": configure_roundcube,
            "plugins": manage_plugins,
            "update": update_roundcube,
        }
    
    run_menu_loop("Webmail (Roundcube)", get_options, get_handlers(), get_status)
