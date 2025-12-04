"""Postfix mail server management."""

from ui.menu import run_menu_loop
from utils.shell import is_installed, is_service_running
from modules.email.postfix.utils import get_postfix_mode, get_postfix_setting


def show_menu():
    """Display Postfix Management submenu."""
    def get_status():
        if not is_installed("postfix"):
            return "Postfix: [yellow]Not installed[/yellow]"
        
        if not is_service_running("postfix"):
            return "Postfix: [red]Stopped[/red]"
        
        mode = get_postfix_mode()
        mode_display = {
            "send-only": "[cyan]Send-Only[/cyan]",
            "receive": "[yellow]Receive[/yellow]",
        }.get(mode, f"[dim]{mode}[/dim]")
        
        return f"Postfix: [green]Running[/green] ({mode_display})"
    
    def get_options():
        options = []
        if is_installed("postfix"):
            options.extend([
                ("mode", "1. Configure Mode"),
                ("domains", "2. Domain Management"),
                ("deliver", "3. Deliverability (DKIM/SPF/DMARC)"),
                ("relay", "4. SMTP Relay"),
                ("routing", "5. Routing (Aliases/Forward/Spam)"),
                ("monitor", "6. Monitoring & Stats"),
                ("queue", "7. Queue Management"),
                ("service", "8. Service Control"),
            ])
        else:
            options.append(("install", "1. Install Postfix"))
        options.append(("back", "← Back"))
        return options
    
    def get_handlers():
        from modules.email.postfix.install import install_postfix, service_control_menu
        from modules.email.postfix.modes import show_modes_menu
        from modules.email.postfix.domains import show_domains_menu
        from modules.email.postfix.deliverability import show_deliverability_menu
        from modules.email.postfix.relay import show_relay_menu
        from modules.email.postfix.routing import show_routing_menu
        from modules.email.postfix.monitor import show_monitor_menu
        from modules.email.postfix.queue import show_queue_menu
        
        return {
            "install": install_postfix,
            "mode": show_modes_menu,
            "domains": show_domains_menu,
            "deliver": show_deliverability_menu,
            "relay": show_relay_menu,
            "routing": show_routing_menu,
            "monitor": show_monitor_menu,
            "queue": show_queue_menu,
            "service": service_control_menu,
        }
    
    run_menu_loop("Postfix Mail Server", get_options, get_handlers(), get_status)
