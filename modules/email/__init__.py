"""Email server management module for vexo."""

from ui.menu import run_menu_loop
from modules.email.utils import get_email_status, format_service_status


def show_menu():
    """Display the main Email Management menu."""
    def get_status():
        status = get_email_status()
        parts = []
        
        # Postfix status
        pf = status["postfix"]
        if pf["installed"]:
            parts.append(f"Postfix:[{'green' if pf['running'] else 'red'}]{'●' if pf['running'] else '○'}[/]")
        
        # Dovecot status
        dv = status["dovecot"]
        if dv["installed"]:
            parts.append(f"Dovecot:[{'green' if dv['running'] else 'red'}]{'●' if dv['running'] else '○'}[/]")
        
        # Roundcube status
        rc = status["roundcube"]
        if rc["installed"]:
            parts.append("Webmail:[green]●[/]")
        
        return " | ".join(parts) if parts else "[dim]Not configured[/dim]"
    
    options = [
        ("postfix", "1. Postfix (Core Mail Server)"),
        ("dovecot", "2. Dovecot (Mailbox Server) [Optional]"),
        ("webmail", "3. Webmail (Roundcube) [Optional]"),
        ("back", "← Back to Main Menu"),
    ]
    
    def get_handlers():
        from modules.email.postfix import show_menu as postfix_menu
        from modules.email.dovecot import show_menu as dovecot_menu
        from modules.email.webmail import show_menu as webmail_menu
        
        return {
            "postfix": postfix_menu,
            "dovecot": dovecot_menu,
            "webmail": webmail_menu,
        }
    
    run_menu_loop("Email Server Management", options, get_handlers(), get_status)
