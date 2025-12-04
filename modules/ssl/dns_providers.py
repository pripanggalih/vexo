"""DNS provider configuration for DNS-01 challenge."""

import os
import json
from ui.components import (
    clear_screen, show_header, show_panel, show_info, press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.ssl.common import get_certbot_status_text, VEXO_SSL_DNS


def get_configured_provider(domain):
    """
    Get configured DNS provider for a domain.
    
    Returns:
        dict with provider info or None if not configured
    """
    config_file = os.path.join(VEXO_SSL_DNS, "providers.json")
    
    if not os.path.exists(config_file):
        return None
    
    try:
        with open(config_file, 'r') as f:
            providers = json.load(f)
        
        # Check for exact domain match or wildcard
        if domain in providers:
            return providers[domain]
        
        # Check for parent domain
        parts = domain.split('.')
        for i in range(len(parts) - 1):
            parent = '.'.join(parts[i:])
            if parent in providers:
                return providers[parent]
        
        # Check for default provider
        if "_default" in providers:
            return providers["_default"]
        
    except (json.JSONDecodeError, IOError):
        pass
    
    return None


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
