"""SSL Certificate management module for vexo."""

from ui.menu import run_menu_loop
from modules.ssl.common import is_certbot_installed, get_certbot_status_text


def show_menu():
    """Display the SSL Certificates main menu."""
    from modules.ssl.dashboard import show_dashboard
    from modules.ssl.issue import show_issue_menu
    from modules.ssl.import_cert import show_import_menu
    from modules.ssl.manage import show_manage_menu
    from modules.ssl.dns_providers import show_dns_menu
    from modules.ssl.security import show_security_menu
    from modules.ssl.backup import show_backup_menu
    from modules.ssl.settings import show_settings_menu
    
    def get_status():
        return f"Certbot: {get_certbot_status_text()}"
    
    def get_options():
        options = [
            ("dashboard", "1. Dashboard"),
            ("issue", "2. Issue Certificate"),
            ("import", "3. Import Certificate"),
            ("manage", "4. Manage Certificates"),
            ("dns", "5. DNS Providers"),
            ("security", "6. Security Audit"),
            ("backup", "7. Backup & Restore"),
            ("settings", "8. Settings"),
            ("back", "← Back to Main Menu"),
        ]
        return options
    
    handlers = {
        "dashboard": show_dashboard,
        "issue": show_issue_menu,
        "import": show_import_menu,
        "manage": show_manage_menu,
        "dns": show_dns_menu,
        "security": show_security_menu,
        "backup": show_backup_menu,
        "settings": show_settings_menu,
    }
    
    run_menu_loop("SSL Certificates", get_options, handlers, get_status)
