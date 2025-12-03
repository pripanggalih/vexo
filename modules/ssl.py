"""SSL Certificate (Let's Encrypt) management module for vexo-cli."""

import os

from config import NGINX_SITES_AVAILABLE
from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_success,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import (
    run_command,
    run_command_with_progress,
    run_command_realtime,
    is_installed,
    is_service_running,
    require_root,
)


def show_menu():
    """Display the SSL Certificates submenu."""
    def get_status():
        if is_installed("certbot"):
            return "Certbot: [green]Installed[/green]"
        return "Certbot: [dim]Not installed[/dim]"
    
    options = [
        ("install", "1. Install Certbot"),
        ("enable", "2. Enable SSL for Domain"),
        ("list", "3. List Certificates"),
        ("renew", "4. Renew All Certificates"),
        ("revoke", "5. Revoke Certificate"),
        ("status", "6. Auto-Renewal Status"),
        ("back", "← Back to Main Menu"),
    ]
    
    handlers = {
        "install": install_certbot,
        "enable": enable_ssl_interactive,
        "list": list_certificates,
        "renew": renew_certificates,
        "revoke": revoke_certificate_interactive,
        "status": show_renewal_status,
    }
    
    run_menu_loop("SSL Certificates (Let's Encrypt)", options, handlers, get_status)


def install_certbot():
    """Install Certbot with Nginx plugin."""
    clear_screen()
    show_header()
    show_panel("Install Certbot", title="SSL Certificates", style="cyan")
    
    if is_installed("certbot"):
        show_info("Certbot is already installed.")
        
        # Check version
        result = run_command("certbot --version", check=False, silent=True)
        if result.returncode == 0:
            console.print(f"[dim]{result.stdout.strip()}[/dim]")
        
        press_enter_to_continue()
        return True
    
    console.print("[bold]This will install:[/bold]")
    console.print("  • certbot - Let's Encrypt client")
    console.print("  • python3-certbot-nginx - Nginx plugin")
    console.print()
    
    if not confirm_action("Install Certbot?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return False
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return False
    
    show_info("Installing Certbot...")
    
    returncode = run_command_realtime(
        "apt install -y certbot python3-certbot-nginx",
        "Installing Certbot..."
    )
    
    if returncode != 0:
        show_error("Failed to install Certbot.")
        press_enter_to_continue()
        return False
    
    show_success("Certbot installed successfully!")
    console.print()
    console.print("[dim]Auto-renewal is automatically configured via systemd timer.[/dim]")
    
    press_enter_to_continue()
    return True


def enable_ssl_interactive():
    """Interactive prompt to enable SSL for a domain."""
    clear_screen()
    show_header()
    show_panel("Enable SSL for Domain", title="SSL Certificates", style="cyan")
    
    if not is_installed("certbot"):
        show_error("Certbot is not installed.")
        if confirm_action("Install Certbot now?"):
            if not install_certbot():
                press_enter_to_continue()
                return
        else:
            press_enter_to_continue()
            return
    
    if not is_installed("nginx"):
        show_error("Nginx is not installed. SSL requires a web server.")
        press_enter_to_continue()
        return
    
    # Get domains without SSL
    domains = _get_domains_without_ssl()
    
    if not domains:
        show_info("No domains found without SSL.")
        console.print()
        console.print("[dim]All configured domains may already have SSL,")
        console.print("or no domains are configured in Nginx.[/dim]")
        press_enter_to_continue()
        return
    
    console.print("[bold]Domains without SSL:[/bold]")
    for domain in domains:
        console.print(f"  • {domain}")
    console.print()
    
    domain = select_from_list(
        title="Enable SSL",
        message="Select domain to enable SSL:",
        options=domains
    )
    
    if not domain:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Get email for Let's Encrypt
    email = text_input(
        title="Email Address",
        message="Enter email for Let's Encrypt notifications:",
    )
    
    if not email or "@" not in email:
        show_error("Valid email is required for Let's Encrypt.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print(f"[bold]Domain:[/bold] {domain}")
    console.print(f"[bold]Email:[/bold] {email}")
    console.print()
    console.print("[yellow]Note: Domain must be pointing to this server's IP.[/yellow]")
    console.print()
    
    if not confirm_action(f"Generate SSL certificate for {domain}?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = enable_ssl(domain, email)
    
    if success:
        show_success(f"SSL enabled for {domain}!")
        console.print()
        console.print("[dim]Certificate will auto-renew before expiry.[/dim]")
        console.print(f"[dim]Visit: https://{domain}[/dim]")
    else:
        show_error(f"Failed to enable SSL for {domain}")
        console.print()
        console.print("[dim]Check that:")
        console.print("  • Domain DNS points to this server")
        console.print("  • Port 80 is open in firewall")
        console.print("  • Nginx is running[/dim]")
    
    press_enter_to_continue()


def enable_ssl(domain, email):
    """
    Generate SSL certificate for a domain using Certbot.
    
    Args:
        domain: Domain name
        email: Email for Let's Encrypt notifications
    
    Returns:
        bool: True if successful
    """
    show_info(f"Generating SSL certificate for {domain}...")
    
    returncode = run_command_realtime(
        f'certbot --nginx -d {domain} --non-interactive --agree-tos -m {email}',
        f"Generating certificate for {domain}..."
    )
    
    return returncode == 0


def _get_domains_without_ssl():
    """Get list of configured domains without SSL."""
    domains = []
    
    if not os.path.exists(NGINX_SITES_AVAILABLE):
        return domains
    
    for filename in os.listdir(NGINX_SITES_AVAILABLE):
        if filename in ('default', 'default.conf'):
            continue
        
        filepath = os.path.join(NGINX_SITES_AVAILABLE, filename)
        if os.path.isfile(filepath):
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                
                # Check if already has SSL
                if 'ssl_certificate' not in content and '443' not in content:
                    domains.append(filename)
            except Exception:
                continue
    
    return sorted(domains)


def list_certificates():
    """Display all SSL certificates managed by Certbot."""
    clear_screen()
    show_header()
    show_panel("SSL Certificates", title="SSL Certificates", style="cyan")
    
    if not is_installed("certbot"):
        show_error("Certbot is not installed.")
        press_enter_to_continue()
        return
    
    result = run_command("certbot certificates", check=False, silent=True)
    
    if result.returncode != 0:
        show_error("Failed to list certificates.")
        press_enter_to_continue()
        return
    
    output = result.stdout.strip()
    
    if "No certificates found" in output or not output:
        show_info("No SSL certificates found.")
        console.print()
        console.print("[dim]Use 'Enable SSL for Domain' to generate certificates.[/dim]")
    else:
        console.print("[bold]Installed Certificates:[/bold]")
        console.print()
        console.print(output)
    
    press_enter_to_continue()


def renew_certificates():
    """Manually trigger certificate renewal."""
    clear_screen()
    show_header()
    show_panel("Renew Certificates", title="SSL Certificates", style="cyan")
    
    if not is_installed("certbot"):
        show_error("Certbot is not installed.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Certificate Renewal[/bold]")
    console.print()
    console.print("[dim]Certbot automatically renews certificates before expiry.")
    console.print("This manual renewal is usually not needed.[/dim]")
    console.print()
    
    if not confirm_action("Run renewal check now?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    show_info("Checking for certificate renewals...")
    
    returncode = run_command_realtime(
        "certbot renew",
        "Renewing certificates..."
    )
    
    if returncode == 0:
        show_success("Renewal check completed!")
    else:
        show_warning("Renewal completed with warnings. Check output above.")
    
    press_enter_to_continue()


def revoke_certificate_interactive():
    """Interactive prompt to revoke a certificate."""
    clear_screen()
    show_header()
    show_panel("Revoke Certificate", title="SSL Certificates", style="cyan")
    
    if not is_installed("certbot"):
        show_error("Certbot is not installed.")
        press_enter_to_continue()
        return
    
    # Get list of certificates
    certs = _get_certificate_domains()
    
    if not certs:
        show_info("No certificates found to revoke.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Installed certificates:[/bold]")
    for cert in certs:
        console.print(f"  • {cert}")
    console.print()
    
    domain = select_from_list(
        title="Revoke Certificate",
        message="Select certificate to revoke:",
        options=certs
    )
    
    if not domain:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print(f"[red bold]WARNING: This will revoke the certificate for {domain}![/red bold]")
    console.print("[yellow]The site will lose HTTPS until a new certificate is generated.[/yellow]")
    console.print()
    
    if not confirm_action(f"Revoke certificate for {domain}?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = revoke_certificate(domain)
    
    if success:
        show_success(f"Certificate for {domain} revoked!")
    else:
        show_error(f"Failed to revoke certificate for {domain}")
    
    press_enter_to_continue()


def revoke_certificate(domain):
    """
    Revoke and delete a certificate.
    
    Args:
        domain: Domain name
    
    Returns:
        bool: True if successful
    """
    # Revoke
    result = run_command(
        f"certbot revoke --cert-name {domain} --non-interactive",
        check=False,
        silent=True
    )
    
    if result.returncode != 0:
        return False
    
    # Delete
    run_command(
        f"certbot delete --cert-name {domain} --non-interactive",
        check=False,
        silent=True
    )
    
    return True


def _get_certificate_domains():
    """Get list of domains with certificates."""
    result = run_command("certbot certificates", check=False, silent=True)
    if result.returncode != 0:
        return []
    
    domains = []
    for line in result.stdout.split('\n'):
        if 'Certificate Name:' in line:
            domain = line.split(':')[-1].strip()
            if domain:
                domains.append(domain)
    
    return domains


def show_renewal_status():
    """Display auto-renewal timer status."""
    clear_screen()
    show_header()
    show_panel("Auto-Renewal Status", title="SSL Certificates", style="cyan")
    
    if not is_installed("certbot"):
        show_error("Certbot is not installed.")
        press_enter_to_continue()
        return
    
    # Check systemd timer
    result = run_command(
        "systemctl status certbot.timer",
        check=False,
        silent=True
    )
    
    if result.returncode == 0:
        console.print("[bold]Certbot Timer Status:[/bold]")
        console.print()
        console.print(result.stdout)
    else:
        # Try checking if timer exists
        result_list = run_command(
            "systemctl list-timers certbot.timer",
            check=False,
            silent=True
        )
        
        if result_list.returncode == 0 and 'certbot' in result_list.stdout:
            console.print("[bold]Certbot Timer:[/bold]")
            console.print()
            console.print(result_list.stdout)
        else:
            show_warning("Certbot timer not found.")
            console.print()
            console.print("[dim]Auto-renewal may be configured via cron instead.")
            console.print("Check: /etc/cron.d/certbot[/dim]")
    
    # Show next renewal check
    console.print()
    result_dry = run_command(
        "certbot renew --dry-run 2>&1 | head -20",
        check=False,
        silent=True
    )
    
    if result_dry.returncode == 0:
        console.print("[bold]Dry-run renewal test:[/bold]")
        console.print("[green]✓ Auto-renewal is working correctly[/green]")
    else:
        console.print("[yellow]! Dry-run test had issues. Check configuration.[/yellow]")
    
    press_enter_to_continue()
