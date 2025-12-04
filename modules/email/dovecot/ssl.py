"""Dovecot SSL/TLS certificate management."""

import os

from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_success, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, is_installed, is_service_running, service_control, require_root
from utils.error_handler import handle_error


# Paths
DOVECOT_SSL_CONF = "/etc/dovecot/conf.d/10-ssl.conf"
DOVECOT_CONF = "/etc/dovecot/dovecot.conf"


def show_ssl_menu():
    """Display SSL settings menu."""
    def get_status():
        ssl_status = _get_ssl_status()
        return f"SSL: {ssl_status}"
    
    options = [
        ("status", "1. View SSL Status"),
        ("letsencrypt", "2. Use Let's Encrypt"),
        ("self", "3. Generate Self-Signed"),
        ("custom", "4. Use Custom Certificate"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "status": view_ssl_status,
        "letsencrypt": use_letsencrypt,
        "self": generate_self_signed,
        "custom": use_custom_cert,
    }
    
    run_menu_loop("SSL/TLS Certificates", options, handlers, get_status)


def _get_ssl_status():
    """Get current SSL status."""
    if not is_installed("dovecot-core"):
        return "[dim]Not Installed[/dim]"
    
    # Check if SSL is enabled
    result = run_command("grep -E '^ssl\\s*=' /etc/dovecot/dovecot.conf 2>/dev/null", check=False, silent=True)
    if result.returncode == 0:
        if "required" in result.stdout:
            return "[green]Required[/green]"
        elif "yes" in result.stdout:
            return "[green]Enabled[/green]"
    
    return "[yellow]Optional[/yellow]"


def view_ssl_status():
    """View current SSL configuration."""
    clear_screen()
    show_header()
    show_panel("SSL Status", title="SSL/TLS", style="cyan")
    
    if not is_installed("dovecot-core"):
        handle_error("E5002", "Dovecot is not installed.")
        press_enter_to_continue()
        return
    
    # Check SSL setting
    result = run_command("doveconf ssl ssl_cert ssl_key 2>/dev/null", check=False, silent=True)
    
    if result.returncode == 0:
        console.print("[bold]Current Configuration:[/bold]")
        console.print()
        for line in result.stdout.strip().split('\n'):
            console.print(f"  {line}")
    else:
        show_info("Could not read SSL configuration.")
    
    # Check certificate validity
    console.print()
    cert_path = "/etc/dovecot/private/dovecot.pem"
    
    # Try to find cert path from config
    cert_result = run_command("doveconf ssl_cert 2>/dev/null | cut -d'<' -f2", check=False, silent=True)
    if cert_result.returncode == 0 and cert_result.stdout.strip():
        cert_path = cert_result.stdout.strip()
    
    if os.path.exists(cert_path):
        console.print(f"[bold]Certificate:[/bold] {cert_path}")
        
        # Check expiry
        result = run_command(
            f"openssl x509 -enddate -noout -in {cert_path} 2>/dev/null",
            check=False, silent=True
        )
        if result.returncode == 0:
            console.print(f"[bold]Expiry:[/bold] {result.stdout.strip().replace('notAfter=', '')}")
        
        # Check issuer
        result = run_command(
            f"openssl x509 -issuer -noout -in {cert_path} 2>/dev/null",
            check=False, silent=True
        )
        if result.returncode == 0:
            issuer = result.stdout.strip().replace('issuer=', '')
            if "Let's Encrypt" in issuer:
                console.print("[bold]Type:[/bold] [green]Let's Encrypt[/green]")
            elif "O = vexo" in issuer or "Self" in issuer:
                console.print("[bold]Type:[/bold] [yellow]Self-Signed[/yellow]")
            else:
                console.print(f"[bold]Issuer:[/bold] {issuer[:50]}")
    else:
        console.print("[yellow]No certificate found.[/yellow]")
    
    press_enter_to_continue()


def use_letsencrypt():
    """Configure Dovecot to use Let's Encrypt certificate."""
    clear_screen()
    show_header()
    show_panel("Let's Encrypt", title="SSL/TLS", style="cyan")
    
    if not is_installed("dovecot-core"):
        handle_error("E5002", "Dovecot is not installed.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Use Let's Encrypt Certificate[/bold]")
    console.print()
    console.print("[dim]This will configure Dovecot to use an existing Let's Encrypt certificate.[/dim]")
    console.print()
    
    domain = text_input("Mail domain (e.g., mail.example.com):")
    if not domain:
        return
    
    # Check if certificate exists
    cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
    key_path = f"/etc/letsencrypt/live/{domain}/privkey.pem"
    
    if not os.path.exists(cert_path):
        handle_error("E5002", f"Certificate not found at {cert_path}")
        console.print()
        console.print("[dim]Run certbot first to obtain a certificate:[/dim]")
        console.print(f"  certbot certonly --standalone -d {domain}")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Update Dovecot config
    _update_ssl_config(cert_path, key_path)
    
    # Restart Dovecot
    service_control("dovecot", "restart")
    
    show_success(f"Dovecot configured to use Let's Encrypt certificate for {domain}!")
    press_enter_to_continue()


def generate_self_signed():
    """Generate a self-signed certificate."""
    clear_screen()
    show_header()
    show_panel("Self-Signed Certificate", title="SSL/TLS", style="cyan")
    
    if not is_installed("dovecot-core"):
        handle_error("E5002", "Dovecot is not installed.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Generate Self-Signed Certificate[/bold]")
    console.print()
    console.print("[yellow]Warning: Self-signed certificates will show security warnings in email clients.[/yellow]")
    console.print("[dim]Recommended for testing only.[/dim]")
    console.print()
    
    domain = text_input("Mail domain (e.g., mail.example.com):")
    if not domain:
        return
    
    if not confirm_action("Generate self-signed certificate?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Create directory
    cert_dir = "/etc/dovecot/private"
    os.makedirs(cert_dir, mode=0o700, exist_ok=True)
    
    cert_path = f"{cert_dir}/dovecot.pem"
    key_path = f"{cert_dir}/dovecot.key"
    
    show_info("Generating certificate...")
    
    result = run_command(
        f'openssl req -new -x509 -days 365 -nodes '
        f'-out {cert_path} -keyout {key_path} '
        f'-subj "/O=vexo/CN={domain}"',
        check=False, silent=True
    )
    
    if result.returncode != 0:
        handle_error("E5002", "Failed to generate certificate.")
        press_enter_to_continue()
        return
    
    # Set permissions
    os.chmod(key_path, 0o600)
    
    # Update config
    _update_ssl_config(cert_path, key_path)
    
    # Restart Dovecot
    service_control("dovecot", "restart")
    
    show_success("Self-signed certificate generated and configured!")
    console.print()
    console.print(f"[dim]Certificate: {cert_path}[/dim]")
    console.print(f"[dim]Key: {key_path}[/dim]")
    
    press_enter_to_continue()


def use_custom_cert():
    """Configure Dovecot to use custom certificate."""
    clear_screen()
    show_header()
    show_panel("Custom Certificate", title="SSL/TLS", style="cyan")
    
    if not is_installed("dovecot-core"):
        handle_error("E5002", "Dovecot is not installed.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Use Custom Certificate[/bold]")
    console.print()
    
    cert_path = text_input("Certificate file path:")
    if not cert_path or not os.path.exists(cert_path):
        handle_error("E5002", "Certificate file not found.")
        press_enter_to_continue()
        return
    
    key_path = text_input("Private key file path:")
    if not key_path or not os.path.exists(key_path):
        handle_error("E5002", "Key file not found.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Update config
    _update_ssl_config(cert_path, key_path)
    
    # Restart Dovecot
    service_control("dovecot", "restart")
    
    show_success("Custom certificate configured!")
    press_enter_to_continue()


def _update_ssl_config(cert_path, key_path):
    """Update Dovecot SSL configuration."""
    # Update main config file
    if os.path.exists(DOVECOT_CONF):
        with open(DOVECOT_CONF, 'r') as f:
            content = f.read()
        
        # Update ssl_cert line
        import re
        content = re.sub(
            r'ssl_cert\s*=.*',
            f'ssl_cert = <{cert_path}',
            content
        )
        content = re.sub(
            r'ssl_key\s*=.*',
            f'ssl_key = <{key_path}',
            content
        )
        
        # Add if not present
        if 'ssl_cert' not in content:
            content += f'\nssl_cert = <{cert_path}\n'
        if 'ssl_key' not in content:
            content += f'ssl_key = <{key_path}\n'
        
        with open(DOVECOT_CONF, 'w') as f:
            f.write(content)
