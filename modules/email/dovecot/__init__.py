"""Dovecot mailbox server management (optional)."""

from ui.menu import run_menu_loop
from utils.shell import is_installed, is_service_running


def show_menu():
    """Display Dovecot Management submenu."""
    def get_status():
        if not is_installed("dovecot-core"):
            return "Dovecot: [dim]Not Installed[/dim]"
        if is_service_running("dovecot"):
            return "Dovecot: [green]Running[/green]"
        return "Dovecot: [red]Stopped[/red]"
    
    def get_options():
        if is_installed("dovecot-core"):
            return [
                ("mailboxes", "1. Mailbox Management"),
                ("quota", "2. Quota Settings"),
                ("ssl", "3. SSL/TLS Certificates"),
                ("service", "4. Service Control"),
                ("back", "← Back"),
            ]
        return [
            ("install", "1. Install Dovecot"),
            ("back", "← Back"),
        ]
    
    def get_handlers():
        from modules.email.dovecot.install import install_dovecot, service_control_menu
        from modules.email.dovecot.mailboxes import show_mailboxes_menu
        from modules.email.dovecot.quota import show_quota_menu
        from modules.email.dovecot.ssl import show_ssl_menu
        
        return {
            "install": install_dovecot,
            "mailboxes": show_mailboxes_menu,
            "quota": show_quota_menu,
            "ssl": show_ssl_menu,
            "service": service_control_menu,
        }
    
    run_menu_loop("Dovecot Mailbox Server", get_options, get_handlers(), get_status)
