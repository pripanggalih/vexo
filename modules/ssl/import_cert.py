"""Import custom SSL certificates."""

import os
import re
import shutil
import json
from datetime import datetime

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
from utils.shell import run_command, require_root
from modules.ssl.common import (
    get_certbot_status_text,
    parse_certificate,
    ensure_config_dir,
    VEXO_SSL_CERTS,
    log_event,
    format_status,
    format_days_left,
)


def show_import_menu():
    """Display import certificate submenu."""
    def get_status():
        return f"Certbot: {get_certbot_status_text()}"
    
    options = [
        ("pem", "1. Upload PEM Files"),
        ("pfx", "2. Upload PFX/PKCS12"),
        ("paste", "3. Paste Certificate"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "pem": import_pem_files,
        "pfx": import_pfx_file,
        "paste": paste_certificate,
    }
    
    run_menu_loop("Import Certificate", options, handlers, get_status)


def import_pem_files():
    """Import certificate from PEM files."""
    clear_screen()
    show_header()
    show_panel("Import PEM Certificate", title="Import Certificate", style="cyan")
    
    console.print("Import certificate and private key from PEM files.")
    console.print()
    
    cert_path = text_input(
        title="Certificate",
        message="Path to certificate file (.pem, .crt):"
    )
    
    if not cert_path or not os.path.exists(cert_path):
        show_error("Certificate file not found.")
        press_enter_to_continue()
        return
    
    cert_info = parse_certificate(cert_path)
    if not cert_info:
        show_error("Invalid certificate file.")
        press_enter_to_continue()
        return
    
    console.print(f"  [green]✓[/green] Valid certificate found")
    console.print(f"    Domains: {', '.join(cert_info['domains'][:3])}")
    
    key_path = text_input(
        title="Private Key",
        message="Path to private key file (.key, .pem):"
    )
    
    if not key_path or not os.path.exists(key_path):
        show_error("Private key file not found.")
        press_enter_to_continue()
        return
    
    if not _validate_private_key(key_path):
        show_error("Invalid private key file.")
        press_enter_to_continue()
        return
    
    console.print(f"  [green]✓[/green] Valid private key")
    
    if not _verify_cert_key_match(cert_path, key_path):
        show_error("Certificate and private key do not match!")
        press_enter_to_continue()
        return
    
    console.print(f"  [green]✓[/green] Certificate and key match")
    
    chain_path = text_input(
        title="Chain",
        message="Path to chain/intermediate certificate (optional, leave empty to skip):",
        default=""
    )
    
    if chain_path and not os.path.exists(chain_path):
        show_warning("Chain file not found, skipping.")
        chain_path = None
    elif chain_path:
        console.print(f"  [green]✓[/green] Chain certificate found")
    
    console.print()
    _show_cert_details(cert_info)
    
    domain = cert_info['domains'][0] if cert_info['domains'] else None
    if not domain:
        domain = text_input(
            title="Domain",
            message="Enter domain name for this certificate:"
        )
    
    if not domain:
        show_error("Domain name required.")
        press_enter_to_continue()
        return
    
    console.print()
    if not confirm_action(f"Import certificate for {domain}?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = _save_certificate(domain, cert_path, key_path, chain_path)
    
    if success:
        show_success(f"Certificate imported for {domain}!")
        
        if confirm_action("Configure Nginx to use this certificate?"):
            _configure_nginx(domain)
        
        log_event(domain, "imported", "PEM files")
    else:
        show_error("Failed to import certificate.")
    
    press_enter_to_continue()


def import_pfx_file():
    """Import certificate from PFX/PKCS12 file."""
    clear_screen()
    show_header()
    show_panel("Import PFX/PKCS12 Certificate", title="Import Certificate", style="cyan")
    
    console.print("Import certificate from PFX/PKCS12 file.")
    console.print("[dim]The certificate, key, and chain will be extracted.[/dim]")
    console.print()
    
    pfx_path = text_input(
        title="PFX File",
        message="Path to PFX/P12 file:"
    )
    
    if not pfx_path or not os.path.exists(pfx_path):
        show_error("PFX file not found.")
        press_enter_to_continue()
        return
    
    password = text_input(
        title="Password",
        message="PFX password (leave empty if none):",
        default=""
    )
    
    show_info("Extracting certificate...")
    
    temp_dir = "/tmp/vexo-ssl-import"
    os.makedirs(temp_dir, exist_ok=True)
    
    cert_path = f"{temp_dir}/cert.pem"
    key_path = f"{temp_dir}/key.pem"
    chain_path = f"{temp_dir}/chain.pem"
    
    pass_arg = f"-passin pass:{password}" if password else "-passin pass:"
    
    result = run_command(
        f"openssl pkcs12 -in {pfx_path} -clcerts -nokeys -out {cert_path} {pass_arg}",
        check=False,
        silent=True
    )
    
    if result.returncode != 0:
        show_error("Failed to extract certificate. Check password.")
        shutil.rmtree(temp_dir, ignore_errors=True)
        press_enter_to_continue()
        return
    
    console.print(f"  [green]✓[/green] Certificate extracted")
    
    result = run_command(
        f"openssl pkcs12 -in {pfx_path} -nocerts -nodes -out {key_path} {pass_arg}",
        check=False,
        silent=True
    )
    
    if result.returncode != 0:
        show_error("Failed to extract private key.")
        shutil.rmtree(temp_dir, ignore_errors=True)
        press_enter_to_continue()
        return
    
    console.print(f"  [green]✓[/green] Private key extracted")
    
    result = run_command(
        f"openssl pkcs12 -in {pfx_path} -cacerts -nokeys -out {chain_path} {pass_arg}",
        check=False,
        silent=True
    )
    
    if result.returncode == 0 and os.path.exists(chain_path) and os.path.getsize(chain_path) > 0:
        console.print(f"  [green]✓[/green] Chain certificates extracted")
    else:
        chain_path = None
        console.print(f"  [dim]-[/dim] No chain certificates in PFX")
    
    cert_info = parse_certificate(cert_path)
    if not cert_info:
        show_error("Failed to parse extracted certificate.")
        shutil.rmtree(temp_dir, ignore_errors=True)
        press_enter_to_continue()
        return
    
    console.print()
    _show_cert_details(cert_info)
    
    domain = cert_info['domains'][0] if cert_info['domains'] else None
    if not domain:
        domain = text_input(
            title="Domain",
            message="Enter domain name:"
        )
    
    if not domain:
        shutil.rmtree(temp_dir, ignore_errors=True)
        press_enter_to_continue()
        return
    
    console.print()
    if not confirm_action(f"Import certificate for {domain}?"):
        shutil.rmtree(temp_dir, ignore_errors=True)
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        shutil.rmtree(temp_dir, ignore_errors=True)
        press_enter_to_continue()
        return
    
    success = _save_certificate(domain, cert_path, key_path, chain_path)
    
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    if success:
        show_success(f"Certificate imported for {domain}!")
        
        if confirm_action("Configure Nginx?"):
            _configure_nginx(domain)
        
        log_event(domain, "imported", "PFX/PKCS12")
    else:
        show_error("Failed to import certificate.")
    
    press_enter_to_continue()


def paste_certificate():
    """Paste certificate content directly."""
    clear_screen()
    show_header()
    show_panel("Paste Certificate", title="Import Certificate", style="cyan")
    
    console.print("Paste your certificate in PEM format.")
    console.print("[dim]Include -----BEGIN CERTIFICATE----- and -----END CERTIFICATE-----[/dim]")
    console.print()
    
    console.print("[bold]Certificate:[/bold]")
    console.print("[dim](Paste and press Enter twice when done)[/dim]")
    
    cert_lines = []
    empty_count = 0
    
    while empty_count < 2:
        line = input()
        if line == "":
            empty_count += 1
        else:
            empty_count = 0
            cert_lines.append(line)
    
    cert_content = "\n".join(cert_lines)
    
    if "-----BEGIN CERTIFICATE-----" not in cert_content:
        show_error("Invalid certificate format.")
        press_enter_to_continue()
        return
    
    temp_cert = "/tmp/vexo-paste-cert.pem"
    with open(temp_cert, "w") as f:
        f.write(cert_content)
    
    cert_info = parse_certificate(temp_cert)
    if not cert_info:
        os.remove(temp_cert)
        show_error("Invalid certificate.")
        press_enter_to_continue()
        return
    
    console.print(f"  [green]✓[/green] Valid certificate")
    
    console.print()
    console.print("[bold]Private Key:[/bold]")
    
    key_lines = []
    empty_count = 0
    
    while empty_count < 2:
        line = input()
        if line == "":
            empty_count += 1
        else:
            empty_count = 0
            key_lines.append(line)
    
    key_content = "\n".join(key_lines)
    
    if "-----BEGIN" not in key_content or "KEY-----" not in key_content:
        show_error("Invalid key format.")
        os.remove(temp_cert)
        press_enter_to_continue()
        return
    
    temp_key = "/tmp/vexo-paste-key.pem"
    with open(temp_key, "w") as f:
        f.write(key_content)
    
    if not _verify_cert_key_match(temp_cert, temp_key):
        show_error("Certificate and key do not match!")
        os.remove(temp_cert)
        os.remove(temp_key)
        press_enter_to_continue()
        return
    
    console.print(f"  [green]✓[/green] Certificate and key match")
    
    _show_cert_details(cert_info)
    
    domain = cert_info['domains'][0] if cert_info['domains'] else text_input(
        title="Domain",
        message="Enter domain name:"
    )
    
    if not domain:
        os.remove(temp_cert)
        os.remove(temp_key)
        press_enter_to_continue()
        return
    
    if not confirm_action(f"Import certificate for {domain}?"):
        os.remove(temp_cert)
        os.remove(temp_key)
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        os.remove(temp_cert)
        os.remove(temp_key)
        press_enter_to_continue()
        return
    
    success = _save_certificate(domain, temp_cert, temp_key, None)
    
    os.remove(temp_cert)
    os.remove(temp_key)
    
    if success:
        show_success(f"Certificate imported for {domain}!")
        log_event(domain, "imported", "Pasted PEM")
    else:
        show_error("Failed to import certificate.")
    
    press_enter_to_continue()


def _validate_private_key(key_path):
    """Validate private key file."""
    result = run_command(
        f"openssl rsa -in {key_path} -check -noout 2>/dev/null",
        check=False,
        silent=True
    )
    return result.returncode == 0


def _verify_cert_key_match(cert_path, key_path):
    """Verify certificate and key match."""
    cert_mod = run_command(
        f"openssl x509 -in {cert_path} -noout -modulus 2>/dev/null | md5sum",
        check=False,
        silent=True
    )
    
    key_mod = run_command(
        f"openssl rsa -in {key_path} -noout -modulus 2>/dev/null | md5sum",
        check=False,
        silent=True
    )
    
    if cert_mod.returncode != 0 or key_mod.returncode != 0:
        return False
    
    return cert_mod.stdout.strip() == key_mod.stdout.strip()


def _show_cert_details(cert_info):
    """Show certificate details."""
    console.print("[bold]Certificate Details:[/bold]")
    console.print(f"  Domains: {', '.join(cert_info.get('domains', []))}")
    console.print(f"  Issuer: {cert_info.get('issuer', 'unknown')}")
    console.print(f"  Status: {format_status(cert_info.get('status', 'unknown'))}")
    console.print(f"  Days Left: {format_days_left(cert_info.get('days_left', 0))}")
    
    if cert_info.get('not_after'):
        console.print(f"  Expires: {cert_info['not_after'].strftime('%Y-%m-%d')}")


def _save_certificate(domain, cert_path, key_path, chain_path=None):
    """Save certificate files to vexo directory."""
    ensure_config_dir()
    
    domain_dir = os.path.join(VEXO_SSL_CERTS, domain)
    os.makedirs(domain_dir, exist_ok=True)
    
    try:
        shutil.copy2(cert_path, os.path.join(domain_dir, "cert.pem"))
        
        key_dest = os.path.join(domain_dir, "privkey.pem")
        shutil.copy2(key_path, key_dest)
        os.chmod(key_dest, 0o600)
        
        fullchain_path = os.path.join(domain_dir, "fullchain.pem")
        with open(fullchain_path, "w") as f:
            with open(cert_path, "r") as cert_f:
                f.write(cert_f.read())
            if chain_path and os.path.exists(chain_path):
                f.write("\n")
                with open(chain_path, "r") as chain_f:
                    f.write(chain_f.read())
        
        if chain_path and os.path.exists(chain_path):
            shutil.copy2(chain_path, os.path.join(domain_dir, "chain.pem"))
        
        metadata = {
            "domain": domain,
            "imported": datetime.now().isoformat(),
            "source": "custom"
        }
        with open(os.path.join(domain_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)
        
        return True
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False


def _configure_nginx(domain):
    """Configure Nginx to use the imported certificate."""
    cert_dir = os.path.join(VEXO_SSL_CERTS, domain)
    fullchain = os.path.join(cert_dir, "fullchain.pem")
    privkey = os.path.join(cert_dir, "privkey.pem")
    
    nginx_conf = f"/etc/nginx/sites-available/{domain}"
    
    if not os.path.exists(nginx_conf):
        show_warning(f"Nginx config not found: {nginx_conf}")
        show_info("You'll need to manually configure Nginx.")
        return
    
    with open(nginx_conf, "r") as f:
        content = f.read()
    
    if "ssl_certificate" in content:
        show_info("SSL already configured in Nginx. Updating paths...")
        content = re.sub(
            r'ssl_certificate\s+[^;]+;',
            f'ssl_certificate {fullchain};',
            content
        )
        content = re.sub(
            r'ssl_certificate_key\s+[^;]+;',
            f'ssl_certificate_key {privkey};',
            content
        )
    else:
        show_info("Adding SSL configuration to Nginx...")
        show_warning("Manual SSL configuration recommended.")
        console.print(f"""
[dim]Add to your Nginx server block:

    listen 443 ssl;
    ssl_certificate {fullchain};
    ssl_certificate_key {privkey};
[/dim]
""")
        return
    
    with open(nginx_conf, "w") as f:
        f.write(content)
    
    result = run_command("nginx -t", check=False, silent=True)
    if result.returncode == 0:
        run_command("systemctl reload nginx", check=False, silent=True)
        show_success("Nginx configuration updated!")
    else:
        show_error("Nginx config test failed. Please check manually.")
