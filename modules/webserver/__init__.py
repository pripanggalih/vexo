"""Domain & Nginx management module for vexo-cli."""

from ui.menu import run_menu_loop
from utils.shell import is_installed

from modules.webserver.nginx import install_nginx, show_nginx_status, test_and_reload
from modules.webserver.domains import list_domains, add_domain_interactive, remove_domain_interactive
from modules.webserver.configure import configure_site_menu
from modules.webserver.backup import show_backup_menu
from modules.webserver.bulk import show_bulk_menu
from modules.webserver.logs import show_logs_menu
from modules.webserver.ssl import show_ssl_menu
from modules.webserver.stats import show_traffic_stats
from modules.webserver.clone import clone_domain


def show_menu():
    """Display the Domain & Nginx submenu."""
    def get_status():
        from utils.shell import is_service_running
        if not is_installed("nginx"):
            return "Nginx: [yellow]Not installed[/yellow]"
        if is_service_running("nginx"):
            return "Nginx: [green]Running[/green]"
        return "Nginx: [red]Stopped[/red]"
    
    def get_options():
        options = []
        if is_installed("nginx"):
            options.extend([
                ("list", "1. List Domains"),
                ("add", "2. Add Domain"),
                ("configure", "3. Configure Site"),
                ("remove", "4. Remove Domain"),
                ("backup", "5. Backup & Restore"),
                ("clone", "6. Clone Domain"),
                ("bulk", "7. Bulk Operations"),
                ("logs", "8. Log Viewer"),
                ("ssl", "9. SSL Management"),
                ("stats", "10. Traffic Stats"),
                ("reload", "11. Test & Reload"),
                ("status", "12. Nginx Status"),
            ])
        else:
            options.append(("install", "1. Install Nginx"))
        options.append(("back", "← Back to Main Menu"))
        return options
    
    handlers = {
        "install": install_nginx,
        "list": list_domains,
        "add": add_domain_interactive,
        "configure": configure_site_menu,
        "remove": remove_domain_interactive,
        "backup": show_backup_menu,
        "clone": clone_domain,
        "bulk": show_bulk_menu,
        "logs": show_logs_menu,
        "ssl": show_ssl_menu,
        "stats": show_traffic_stats,
        "reload": test_and_reload,
        "status": show_nginx_status,
    }
    
    run_menu_loop("Domain & Nginx Management", get_options, handlers, get_status)
