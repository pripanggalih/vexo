"""DNS provider configuration for DNS-01 challenge."""

from ui.components import (
    clear_screen, show_header, show_panel, show_info, press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.ssl.common import get_certbot_status_text


def show_dns_menu():
    """Display DNS providers submenu."""
    def get_status():
        return f"Certbot: {get_certbot_status_text()}"
    
    options = [
        ("cloudflare", "1. Configure Cloudflare"),
        ("digitalocean", "2. Configure DigitalOcean"),
        ("route53", "3. Configure Route53"),
        ("manual", "4. Manual DNS"),
        ("test", "5. Test DNS API"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "cloudflare": _placeholder,
        "digitalocean": _placeholder,
        "route53": _placeholder,
        "manual": _placeholder,
        "test": _placeholder,
    }
    
    run_menu_loop("DNS Providers", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="DNS Providers", style="cyan")
    show_info("This feature will be implemented in Phase 5.")
    press_enter_to_continue()
