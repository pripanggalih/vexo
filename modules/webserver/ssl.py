"""SSL certificate management."""

import os
from datetime import datetime

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, select_from_list, run_menu_loop
from utils.shell import run_command, run_command_realtime, is_installed, require_root
from utils.error_handler import handle_error
from modules.webserver.utils import get_configured_domains


def show_ssl_menu():
    """Display SSL Management submenu."""
    def get_status():
        if is_installed("certbot"):
            return "Certbot: [green]Installed[/green]"
        return "Certbot: [yellow]Not installed[/yellow]"
    
    options = [
        ("view", "1. View Certificate Info"),
        ("status", "2. Check Auto-Renew Status"),
        ("renew", "3. Manual Renew"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "view": view_certificate,
        "status": check_autorenew,
        "renew": manual_renew,
    }
    
    run_menu_loop("SSL Management", options, handlers, get_status)


def view_certificate():
    """View SSL certificate details for a domain."""
    clear_screen()
    show_header()
    show_panel("Certificate Info", title="SSL Management", style="cyan")
    
    domains = get_configured_domains()
    if not domains:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    domain = select_from_list("Select Domain", "Choose domain:", domains)
    if not domain:
        return
    
    cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
    
    if not os.path.exists(cert_path):
        show_warning(f"No SSL certificate found for {domain}")
        press_enter_to_continue()
        return
    
    # Get certificate info using openssl
    result = run_command(
        f"openssl x509 -in {cert_path} -noout -subject -issuer -dates",
        check=False, silent=True
    )
    
    if result.returncode != 0:
        handle_error("E2002", "Failed to read certificate.")
        press_enter_to_continue()
        return
    
    console.print(f"[bold cyan]Certificate for: {domain}[/bold cyan]")
    console.print()
    
    columns = [
        {"name": "Property", "style": "cyan"},
        {"name": "Value", "style": "white"},
    ]
    
    rows = []
    for line in result.stdout.strip().split('\n'):
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Parse dates
            if 'notBefore' in key or 'notAfter' in key:
                try:
                    dt = datetime.strptime(value, "%b %d %H:%M:%S %Y %Z")
                    value = dt.strftime("%Y-%m-%d %H:%M")
                    
                    if 'notAfter' in key:
                        days_left = (dt - datetime.now()).days
                        if days_left < 0:
                            value += f" [red](EXPIRED)[/red]"
                        elif days_left < 30:
                            value += f" [yellow]({days_left} days left)[/yellow]"
                        else:
                            value += f" [green]({days_left} days left)[/green]"
                except ValueError:
                    pass
            
            rows.append([key, value])
    
    show_table("", columns, rows, show_header=False)
    press_enter_to_continue()


def check_autorenew():
    """Check certbot auto-renew timer status."""
    clear_screen()
    show_header()
    show_panel("Auto-Renew Status", title="SSL Management", style="cyan")
    
    if not is_installed("certbot"):
        show_warning("Certbot is not installed.")
        press_enter_to_continue()
        return
    
    # Check timer status
    result = run_command("systemctl status certbot.timer", check=False, silent=True)
    
    if result.returncode == 0:
        show_success("Auto-renew timer is active!")
        console.print()
        console.print(result.stdout)
    else:
        show_warning("Auto-renew timer may not be running.")
        console.print()
        console.print(result.stdout if result.stdout else result.stderr)
    
    console.print()
    
    # List certificates
    result = run_command("certbot certificates 2>/dev/null", check=False, silent=True)
    if result.returncode == 0 and result.stdout.strip():
        console.print("[bold]Managed Certificates:[/bold]")
        console.print(result.stdout)
    
    press_enter_to_continue()


def manual_renew():
    """Manually renew SSL certificates."""
    clear_screen()
    show_header()
    show_panel("Manual Renew", title="SSL Management", style="cyan")
    
    if not is_installed("certbot"):
        handle_error("E2002", "Certbot is not installed.")
        press_enter_to_continue()
        return
    
    # Get list of certificates
    result = run_command("certbot certificates 2>/dev/null | grep 'Certificate Name' | awk '{print $3}'", check=False, silent=True)
    
    certs = [c.strip() for c in result.stdout.strip().split('\n') if c.strip()]
    
    if not certs:
        show_info("No certificates found.")
        press_enter_to_continue()
        return
    
    certs.insert(0, "(Renew All)")
    
    choice = select_from_list("Select Certificate", "Choose certificate to renew:", certs)
    if not choice:
        return
    
    if not confirm_action(f"Renew {'all certificates' if choice == '(Renew All)' else choice}?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print()
    
    if choice == "(Renew All)":
        run_command_realtime("certbot renew", "Renewing certificates...")
    else:
        run_command_realtime(f"certbot renew --cert-name {choice}", "Renewing certificate...")
    
    press_enter_to_continue()
