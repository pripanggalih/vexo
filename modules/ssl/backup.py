"""SSL certificate backup and restore."""

from ui.components import (
    clear_screen, show_header, show_panel, show_info, press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.ssl.common import get_certbot_status_text


def show_backup_menu():
    """Display backup and restore submenu."""
    def get_status():
        return f"Certbot: {get_certbot_status_text()}"
    
    options = [
        ("export_one", "1. Export Certificate"),
        ("export_all", "2. Export All"),
        ("restore", "3. Import/Restore"),
        ("schedule", "4. Scheduled Backups"),
        ("manage", "5. Manage Backups"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "export_one": _placeholder,
        "export_all": _placeholder,
        "restore": _placeholder,
        "schedule": _placeholder,
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
