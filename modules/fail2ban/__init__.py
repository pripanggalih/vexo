"""Fail2ban (brute force protection) module for vexo-cli."""

from ui.menu import run_menu_loop
from utils.shell import is_installed, is_service_running

from .common import is_fail2ban_installed, is_fail2ban_running


def show_menu():
    """Display the Fail2ban main menu."""
    def get_status():
        if is_fail2ban_running():
            return "Fail2ban: [green]Running[/green]"
        elif is_fail2ban_installed():
            return "Fail2ban: [red]Stopped[/red]"
        return "Fail2ban: [dim]Not installed[/dim]"
    
    def get_options():
        options = []
        if is_fail2ban_installed():
            options.extend([
                ("dashboard", "1. Dashboard"),
                ("jails", "2. Jail Management"),
                ("bans", "3. Ban Management"),
                ("whitelist", "4. Whitelist"),
                ("filters", "5. Filters"),
                ("history", "6. History & Logs"),
                ("notifications", "7. Notifications"),
                ("backup", "8. Backup & Restore"),
                ("settings", "9. Settings"),
            ])
        else:
            options.append(("install", "1. Install Fail2ban"))
        options.append(("back", "← Back to Main Menu"))
        return options
    
    handlers = {
        "install": _install_handler,
        "dashboard": _dashboard_handler,
        "jails": _jails_handler,
        "bans": _bans_handler,
        "whitelist": _whitelist_handler,
        "filters": _filters_handler,
        "history": _history_handler,
        "notifications": _notifications_handler,
        "backup": _backup_handler,
        "settings": _settings_handler,
    }
    
    run_menu_loop("Fail2ban (Brute Force Protection)", get_options, handlers, get_status)


def _install_handler():
    """Handle install menu option."""
    from .settings import install_fail2ban
    install_fail2ban()


def _dashboard_handler():
    """Handle dashboard menu option."""
    from .dashboard import show_dashboard
    show_dashboard()


def _jails_handler():
    """Handle jails menu option."""
    from .jails import show_menu as show_jails_menu
    show_jails_menu()


def _bans_handler():
    """Handle bans menu option."""
    from .bans import show_menu as show_bans_menu
    show_bans_menu()


def _whitelist_handler():
    """Handle whitelist menu option."""
    from .whitelist import show_menu as show_whitelist_menu
    show_whitelist_menu()


def _filters_handler():
    """Handle filters menu option."""
    from .filters import show_menu as show_filters_menu
    show_filters_menu()


def _history_handler():
    """Handle history menu option."""
    from .history import show_menu as show_history_menu
    show_history_menu()


def _notifications_handler():
    """Handle notifications menu option."""
    from .notifications import show_menu as show_notifications_menu
    show_notifications_menu()


def _backup_handler():
    """Handle backup menu option."""
    from .backup import show_menu as show_backup_menu
    show_backup_menu()


def _settings_handler():
    """Handle settings menu option."""
    from .settings import show_menu as show_settings_menu
    show_settings_menu()
