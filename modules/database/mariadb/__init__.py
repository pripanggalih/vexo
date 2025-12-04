"""MariaDB management module."""

from ui.menu import run_menu_loop
from utils.shell import is_installed, is_service_running


def show_menu():
    """Display MariaDB Management submenu."""
    def get_status():
        if not is_installed("mariadb-server"):
            return "MariaDB: [yellow]Not installed[/yellow]"
        if is_service_running("mariadb"):
            return "MariaDB: [green]Running[/green]"
        return "MariaDB: [red]Stopped[/red]"
    
    def get_options():
        options = []
        if is_installed("mariadb-server"):
            options.extend([
                ("list", "1. List Databases"),
                ("create", "2. Create Database"),
                ("delete", "3. Delete Database"),
                ("users", "4. User Management"),
                ("backup", "5. Backup & Restore"),
                ("import", "6. Import/Export"),
                ("monitor", "7. Monitoring"),
                ("config", "8. Configuration"),
                ("security", "9. Security"),
            ])
        else:
            options.append(("install", "1. Install MariaDB"))
        options.append(("back", "← Back"))
        return options
    
    def get_handlers():
        from modules.database.mariadb.core import (
            list_databases, create_database_interactive,
            delete_database_interactive, install_mariadb,
        )
        from modules.database.mariadb.users import show_users_menu
        from modules.database.mariadb.backup import show_backup_menu
        from modules.database.mariadb.importexport import show_import_menu
        from modules.database.mariadb.monitor import show_monitor_menu
        from modules.database.mariadb.config import show_config_menu
        from modules.database.mariadb.security import show_security_menu
        
        return {
            "install": install_mariadb,
            "list": list_databases,
            "create": create_database_interactive,
            "delete": delete_database_interactive,
            "users": show_users_menu,
            "backup": show_backup_menu,
            "import": show_import_menu,
            "monitor": show_monitor_menu,
            "config": show_config_menu,
            "security": show_security_menu,
        }
    
    run_menu_loop("MariaDB Management", get_options, get_handlers(), get_status)
