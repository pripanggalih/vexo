"""Firewall (UFW) management module for vexo-cli."""

from ui.menu import run_menu_loop
from modules.firewall.common import is_ufw_installed, get_ufw_status_text


def show_menu():
    """Display the Firewall (UFW) main menu."""
    from modules.firewall.status import show_status_dashboard
    from modules.firewall.quick_setup import (
        install_ufw,
        enable_firewall,
        disable_firewall,
    )
    from modules.firewall.ports import show_ports_menu
    from modules.firewall.ip_management import show_ip_menu
    from modules.firewall.rate_limiting import show_rate_limit_menu
    from modules.firewall.profiles import show_profiles_menu
    from modules.firewall.logs import show_logs_menu
    from modules.firewall.backup import show_backup_menu
    
    def get_status():
        return f"UFW Status: {get_ufw_status_text()}"
    
    def get_options():
        options = []
        if is_ufw_installed():
            options.extend([
                ("status", "1. Status Dashboard"),
                ("enable", "2. Enable Firewall"),
                ("disable", "3. Disable Firewall"),
                ("ports", "4. Port Management"),
                ("ip", "5. IP Management"),
                ("rate", "6. Rate Limiting"),
                ("profiles", "7. Application Profiles"),
                ("logs", "8. Logs & Monitoring"),
                ("backup", "9. Backup & Restore"),
            ])
        else:
            options.append(("install", "1. Install UFW"))
        options.append(("back", "← Back to Main Menu"))
        return options
    
    handlers = {
        "install": install_ufw,
        "status": show_status_dashboard,
        "enable": enable_firewall,
        "disable": disable_firewall,
        "ports": show_ports_menu,
        "ip": show_ip_menu,
        "rate": show_rate_limit_menu,
        "profiles": show_profiles_menu,
        "logs": show_logs_menu,
        "backup": show_backup_menu,
    }
    
    run_menu_loop("Firewall (UFW)", get_options, handlers, get_status)
