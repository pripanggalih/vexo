"""Manage SSL certificates."""

import os
import shutil

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
from ui.menu import run_menu_loop, text_input, select_from_list, confirm_action
from utils.shell import run_command, run_command_realtime, require_root
from modules.ssl.common import (
    get_certbot_status_text,
    list_all_certificates,
    list_certbot_certificates,
    list_custom_certificates,
    parse_certificate,
    format_status,
    format_days_left,
    log_event,
    VEXO_SSL_CERTS,
    LETSENCRYPT_LIVE,
)


def show_manage_menu():
    """Display manage certificates submenu."""
    def get_status():
        certs = list_all_certificates()
        return f"Certificates: {len(certs)}"
    
    options = [
        ("details", "1. View Details"),
        ("renew", "2. Renew Certificate"),
        ("revoke", "3. Revoke Certificate"),
        ("delete", "4. Delete Certificate"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "details": view_certificate_details,
        "renew": renew_certificate,
        "revoke": revoke_certificate,
        "delete": delete_certificate,
    }
    
    run_menu_loop("Manage Certificates", options, handlers, get_status)


def _select_certificate(message="Select certificate:"):
    """Helper to select a certificate."""
    certificates = list_all_certificates()
    
    if not certificates:
        show_info("No certificates found.")
        return None
    
    options = []
    for cert in certificates:
        status = format_status(cert.get('status', 'unknown'))
        source = f"[dim]({cert.get('source', 'unknown')})[/dim]"
        options.append(f"{cert['name']} - {status} {source}")
    
    choice = select_from_list(
        title="Certificate",
        message=message,
        options=options
    )
    
    if not choice:
        return None
    
    idx = options.index(choice)
    return certificates[idx]


def view_certificate_details():
    """View detailed information about a certificate."""
    clear_screen()
    show_header()
    show_panel("View Certificate Details", title="Manage Certificates", style="cyan")
    
    cert = _select_certificate()
    if not cert:
        press_enter_to_continue()
        return
    
    clear_screen()
    show_header()
    show_panel(f"Certificate: {cert['name']}", title="Certificate Details", style="cyan")
    
    console.print()
    
    console.print("[bold]General Information:[/bold]")
    console.print(f"  Name: {cert.get('name', 'unknown')}")
    console.print(f"  Source: {cert.get('source', 'unknown')}")
    console.print(f"  Type: {cert.get('type', 'unknown')}")
    console.print(f"  CA: {cert.get('ca', 'unknown')}")
    console.print()
    
    console.print("[bold]Domains:[/bold]")
    for domain in cert.get('domains', []):
        console.print(f"  * {domain}")
    console.print()
    
    console.print("[bold]Validity:[/bold]")
    console.print(f"  Status: {format_status(cert.get('status', 'unknown'))}")
    console.print(f"  Days Left: {format_days_left(cert.get('days_left', 0))}")
    if cert.get('not_before'):
        console.print(f"  Valid From: {cert['not_before'].strftime('%Y-%m-%d %H:%M:%S')}")
    if cert.get('not_after'):
        console.print(f"  Valid Until: {cert['not_after'].strftime('%Y-%m-%d %H:%M:%S')}")
    console.print()
    
    console.print("[bold]File Locations:[/bold]")
    console.print(f"  Certificate: {cert.get('path', 'unknown')}")
    
    if cert.get('source') == 'certbot':
        live_dir = os.path.join(LETSENCRYPT_LIVE, cert['name'])
        console.print(f"  Private Key: {os.path.join(live_dir, 'privkey.pem')}")
        console.print(f"  Full Chain: {os.path.join(live_dir, 'fullchain.pem')}")
    else:
        cert_dir = os.path.join(VEXO_SSL_CERTS, cert['name'])
        console.print(f"  Private Key: {os.path.join(cert_dir, 'privkey.pem')}")
        console.print(f"  Full Chain: {os.path.join(cert_dir, 'fullchain.pem')}")
    
    console.print()
    
    action = select_from_list(
        title="Action",
        message="Additional actions:",
        options=[
            "View Certificate Chain",
            "View Fingerprint",
            "Test HTTPS Connection",
            "Back"
        ]
    )
    
    if action == "View Certificate Chain":
        _show_certificate_chain(cert)
    elif action == "View Fingerprint":
        _show_fingerprint(cert)
    elif action == "Test HTTPS Connection":
        _test_https(cert)
    
    press_enter_to_continue()


def _show_certificate_chain(cert):
    """Show certificate chain information."""
    console.print()
    console.print("[bold]Certificate Chain:[/bold]")
    
    result = run_command(
        f"openssl crl2pkcs7 -nocrl -certfile {cert['path']} | "
        f"openssl pkcs7 -print_certs -noout",
        check=False,
        silent=True
    )
    
    if result.returncode == 0:
        console.print(result.stdout)
    else:
        console.print("[dim]Could not retrieve chain information.[/dim]")


def _show_fingerprint(cert):
    """Show certificate fingerprint."""
    console.print()
    console.print("[bold]Certificate Fingerprints:[/bold]")
    
    for algo in ['sha256', 'sha1']:
        result = run_command(
            f"openssl x509 -in {cert['path']} -noout -fingerprint -{algo}",
            check=False,
            silent=True
        )
        if result.returncode == 0:
            console.print(f"  {result.stdout.strip()}")


def _test_https(cert):
    """Test HTTPS connection to the domain."""
    domain = cert.get('domains', [cert.get('name')])[0]
    
    if domain.startswith('*.'):
        domain = domain[2:]
    
    console.print()
    console.print(f"[bold]Testing HTTPS connection to {domain}...[/bold]")
    
    result = run_command(
        f"curl -sI -o /dev/null -w '%{{http_code}}' https://{domain} --connect-timeout 5",
        check=False,
        silent=True
    )
    
    if result.returncode == 0:
        status_code = result.stdout.strip()
        if status_code.startswith('2') or status_code.startswith('3'):
            console.print(f"  [green]✓[/green] HTTPS working (HTTP {status_code})")
        else:
            console.print(f"  [yellow]![/yellow] HTTPS responded with HTTP {status_code}")
    else:
        console.print(f"  [red]✗[/red] Could not connect to https://{domain}")


def renew_certificate():
    """Manually renew a certificate."""
    clear_screen()
    show_header()
    show_panel("Renew Certificate", title="Manage Certificates", style="cyan")
    
    cert = _select_certificate("Select certificate to renew:")
    if not cert:
        press_enter_to_continue()
        return
    
    source = cert.get('source', 'unknown')
    
    if source == 'custom':
        show_warning("Custom certificates cannot be auto-renewed.")
        console.print("[dim]You need to obtain a new certificate from your CA and import it.[/dim]")
        press_enter_to_continue()
        return
    
    console.print()
    console.print(f"[bold]Certificate:[/bold] {cert['name']}")
    console.print(f"[bold]Days Left:[/bold] {format_days_left(cert.get('days_left', 0))}")
    console.print()
    
    if cert.get('days_left', 0) > 30:
        show_info("Certificate is not due for renewal yet.")
        if not confirm_action("Force renewal anyway?"):
            press_enter_to_continue()
            return
    
    if not confirm_action(f"Renew certificate for {cert['name']}?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    show_info("Renewing certificate...")
    
    returncode = run_command_realtime(
        f"certbot renew --cert-name {cert['name']} --force-renewal",
        "Renewing certificate..."
    )
    
    if returncode == 0:
        show_success(f"Certificate {cert['name']} renewed!")
        log_event(cert['name'], "renewed", "Manual renewal")
    else:
        show_error("Renewal failed. Check certbot output above.")
    
    press_enter_to_continue()


def revoke_certificate():
    """Revoke a certificate."""
    clear_screen()
    show_header()
    show_panel("Revoke Certificate", title="Manage Certificates", style="cyan")
    
    cert = _select_certificate("Select certificate to revoke:")
    if not cert:
        press_enter_to_continue()
        return
    
    source = cert.get('source', 'unknown')
    
    if source == 'custom':
        show_warning("Custom certificates must be revoked through your CA.")
        console.print("[dim]Contact your certificate authority to revoke.[/dim]")
        press_enter_to_continue()
        return
    
    console.print()
    console.print(f"[red bold]WARNING: This will revoke the certificate![/red bold]")
    console.print(f"[bold]Certificate:[/bold] {cert['name']}")
    console.print()
    console.print("[yellow]The certificate will be marked as invalid and cannot be used.[/yellow]")
    console.print("[yellow]You will need to issue a new certificate.[/yellow]")
    console.print()
    
    if not confirm_action(f"Revoke certificate for {cert['name']}?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    confirm_text = text_input(
        title="Confirm",
        message=f"Type '{cert['name']}' to confirm revocation:"
    )
    
    if confirm_text != cert['name']:
        show_warning("Confirmation did not match. Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    show_info("Revoking certificate...")
    
    result = run_command(
        f"certbot revoke --cert-name {cert['name']} --non-interactive",
        check=False,
        silent=True
    )
    
    if result.returncode == 0:
        show_success(f"Certificate {cert['name']} revoked!")
        log_event(cert['name'], "revoked", "Manual revocation")
        
        if confirm_action("Also delete the certificate files?"):
            run_command(
                f"certbot delete --cert-name {cert['name']} --non-interactive",
                check=False,
                silent=True
            )
            show_info("Certificate files deleted.")
    else:
        show_error("Revocation failed.")
        console.print(f"[dim]{result.stderr}[/dim]")
    
    press_enter_to_continue()


def delete_certificate():
    """Delete a certificate (without revoking)."""
    clear_screen()
    show_header()
    show_panel("Delete Certificate", title="Manage Certificates", style="cyan")
    
    cert = _select_certificate("Select certificate to delete:")
    if not cert:
        press_enter_to_continue()
        return
    
    source = cert.get('source', 'unknown')
    
    console.print()
    console.print(f"[yellow bold]WARNING: This will delete the certificate files![/yellow bold]")
    console.print(f"[bold]Certificate:[/bold] {cert['name']}")
    console.print(f"[bold]Source:[/bold] {source}")
    console.print()
    
    if source == 'certbot':
        console.print("[dim]Note: This does NOT revoke the certificate.[/dim]")
        console.print("[dim]The certificate will still be valid until it expires.[/dim]")
    
    console.print()
    
    if not confirm_action(f"Delete certificate {cert['name']}?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if source == 'certbot':
        result = run_command(
            f"certbot delete --cert-name {cert['name']} --non-interactive",
            check=False,
            silent=True
        )
        
        if result.returncode == 0:
            show_success(f"Certificate {cert['name']} deleted!")
            log_event(cert['name'], "deleted", "Certbot certificate")
        else:
            show_error("Failed to delete certificate.")
            console.print(f"[dim]{result.stderr}[/dim]")
    else:
        cert_dir = os.path.join(VEXO_SSL_CERTS, cert['name'])
        
        if os.path.exists(cert_dir):
            shutil.rmtree(cert_dir)
            show_success(f"Certificate {cert['name']} deleted!")
            log_event(cert['name'], "deleted", "Custom certificate")
        else:
            show_error("Certificate directory not found.")
    
    press_enter_to_continue()
