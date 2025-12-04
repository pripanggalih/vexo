"""Backup and restore for firewall."""

from ui.components import (
    clear_screen,
    show_header,
    show_panel,
    show_info,
    press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.firewall.common import get_ufw_status_text


def show_backup_menu():
    """Display backup and restore submenu."""
    def get_status():
        return f"UFW: {get_ufw_status_text()}"
    
    options = [
        ("create", "1. Create Backup"),
        ("restore", "2. Restore Backup"),
        ("compare", "3. Compare Configs"),
        ("auto", "4. Auto-Backup Settings"),
        ("manage", "5. Manage Backups"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "create": _placeholder,
        "restore": _placeholder,
        "compare": _placeholder,
        "auto": _placeholder,
        "manage": _placeholder,
    }
    
    run_menu_loop("Backup & Restore", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Backup & Restore", style="cyan")
    show_info("This feature will be implemented in Phase 7.")
    press_enter_to_continue()
