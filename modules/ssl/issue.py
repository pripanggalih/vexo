"""Issue SSL certificates."""

import subprocess
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
from utils.shell import run_command, run_command_realtime, is_installed, require_root
from utils.sanitize import validate_email, validate_domain, escape_shell
from modules.ssl.common import (
    get_certbot_status_text,
    is_certbot_installed,
    CERTIFICATE_AUTHORITIES,
    get_default_ca,
    run_preflight_checks,
    log_event,
)


def show_issue_menu():
    """Display issue certificate submenu."""
    def get_status():
        return f"Certbot: {get_certbot_status_text()}"
    
    options = [
        ("single", "1. Single Domain"),
        ("san", "2. Multiple Domains (SAN)"),
        ("wildcard", "3. Wildcard Certificate"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "single": issue_single_domain,
        "san": issue_san_certificate,
        "wildcard": issue_wildcard_certificate,
    }
    
    run_menu_loop("Issue Certificate", options, handlers, get_status)


def _check_certbot():
    """Check if certbot is installed, offer to install."""
    if is_certbot_installed():
        return True
    
    show_error("Certbot is not installed.")
    if confirm_action("Install Certbot now?"):
        try:
            require_root()
        except PermissionError:
            return False
        
        returncode = run_command_realtime(
            "apt install -y certbot python3-certbot-nginx",
            "Installing Certbot..."
        )
        return returncode == 0
    return False


def _select_ca():
    """Let user select Certificate Authority."""
    default_ca = get_default_ca()
    
    options = []
    for key, ca in CERTIFICATE_AUTHORITIES.items():
        if key == "letsencrypt_staging":
            continue
        marker = " (default)" if key == default_ca else ""
        options.append(f"{ca['name']}{marker} - {ca['description']}")
    
    options.append("Let's Encrypt (Staging) - Testing only")
    
    choice = select_from_list(
        title="CA",
        message="Select Certificate Authority:",
        options=options
    )
    
    if not choice:
        return None
    
    for key, ca in CERTIFICATE_AUTHORITIES.items():
        if ca['name'] in choice:
            return key
    
    return "letsencrypt"


def _get_email():
    """Get email for certificate notifications."""
    email = text_input(
        title="Email",
        message="Enter email for certificate notifications:"
    )
    
    if not email or not validate_email(email):
        show_error("Valid email is required (e.g., user@example.com).")
        return None
    
    return email


def _run_certbot(domains, email, ca_key, challenge="http"):
    """
    Run certbot to issue certificate.
    
    Args:
        domains: List of domain names
        email: Email for notifications
        ca_key: CA key from CERTIFICATE_AUTHORITIES
        challenge: 'http' or 'dns'
    
    Returns:
        bool: Success status
    """
    ca = CERTIFICATE_AUTHORITIES.get(ca_key, CERTIFICATE_AUTHORITIES["letsencrypt"])
    
    domain_args = " ".join(f"-d {d}" for d in domains)
    
    cmd = f"certbot --nginx {domain_args} --non-interactive --agree-tos -m {email}"
    
    if ca.get("server"):
        cmd += f" --server {ca['server']}"
    
    if ca_key == "zerossl":
        show_warning("ZeroSSL requires EAB credentials. Using Let's Encrypt instead.")
        ca_key = "letsencrypt"
        cmd = f"certbot --nginx {domain_args} --non-interactive --agree-tos -m {email}"
    
    show_info(f"Issuing certificate via {ca['name']}...")
    
    returncode = run_command_realtime(cmd, f"Generating certificate...")
    
    if returncode == 0:
        log_event(domains[0], "issued", f"CA: {ca['name']}, Domains: {', '.join(domains)}")
        return True
    
    return False


def issue_single_domain():
    """Issue certificate for a single domain."""
    clear_screen()
    show_header()
    show_panel("Issue Single Domain Certificate", title="Issue Certificate", style="cyan")
    
    if not _check_certbot():
        press_enter_to_continue()
        return
    
    domain = text_input(
        title="Domain",
        message="Enter domain name (e.g., example.com):"
    )
    
    if not domain:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    domain = domain.strip().lower()
    if domain.startswith("http"):
        domain = domain.split("//")[-1].split("/")[0]
    
    # Validate domain format
    if not validate_domain(domain):
        show_error(f"Invalid domain format: {domain}")
        press_enter_to_continue()
        return
    
    console.print()
    console.print("[bold]Pre-flight checks:[/bold]")
    success, messages = run_preflight_checks([domain])
    for icon, msg in messages:
        console.print(f"  {icon} {msg}")
    console.print()
    
    if not success:
        show_warning("Some checks failed. Certificate may not be issued successfully.")
        if not confirm_action("Continue anyway?"):
            press_enter_to_continue()
            return
    
    ca_key = _select_ca()
    if not ca_key:
        press_enter_to_continue()
        return
    
    email = _get_email()
    if not email:
        press_enter_to_continue()
        return
    
    console.print()
    console.print(f"[bold]Domain:[/bold] {domain}")
    console.print(f"[bold]CA:[/bold] {CERTIFICATE_AUTHORITIES[ca_key]['name']}")
    console.print(f"[bold]Email:[/bold] {email}")
    console.print()
    
    if not confirm_action("Issue certificate?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if _run_certbot([domain], email, ca_key):
        show_success(f"Certificate issued for {domain}!")
        console.print()
        console.print(f"[dim]Visit: https://{domain}[/dim]")
    else:
        show_error("Failed to issue certificate.")
        console.print("[dim]Check domain DNS and firewall settings.[/dim]")
    
    press_enter_to_continue()


def issue_san_certificate():
    """Issue certificate for multiple domains (SAN)."""
    clear_screen()
    show_header()
    show_panel("Issue Multi-Domain (SAN) Certificate", title="Issue Certificate", style="cyan")
    
    if not _check_certbot():
        press_enter_to_continue()
        return
    
    console.print("Enter domains to include in the certificate.")
    console.print("[dim]Primary domain first, then additional domains.[/dim]")
    console.print()
    
    primary = text_input(
        title="Primary Domain",
        message="Primary domain (e.g., example.com):"
    )
    
    if not primary:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    primary = primary.strip().lower()
    domains = [primary]
    
    console.print()
    console.print("[dim]Enter additional domains (empty to finish):[/dim]")
    
    while True:
        additional = text_input(
            title="Domain",
            message=f"Additional domain {len(domains)}:",
            default=""
        )
        
        if not additional:
            break
        
        additional = additional.strip().lower()
        if additional not in domains:
            domains.append(additional)
            console.print(f"  [green]✓[/green] Added: {additional}")
        else:
            console.print(f"  [yellow]![/yellow] Already added: {additional}")
    
    if len(domains) < 2:
        show_info("Only one domain entered. Use 'Single Domain' instead.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print("[bold]Pre-flight checks:[/bold]")
    success, messages = run_preflight_checks(domains)
    for icon, msg in messages:
        console.print(f"  {icon} {msg}")
    console.print()
    
    if not success:
        show_warning("Some checks failed.")
        if not confirm_action("Continue anyway?"):
            press_enter_to_continue()
            return
    
    ca_key = _select_ca()
    if not ca_key:
        press_enter_to_continue()
        return
    
    email = _get_email()
    if not email:
        press_enter_to_continue()
        return
    
    console.print()
    console.print("[bold]Domains:[/bold]")
    for d in domains:
        console.print(f"  * {d}")
    console.print(f"[bold]CA:[/bold] {CERTIFICATE_AUTHORITIES[ca_key]['name']}")
    console.print()
    
    if not confirm_action(f"Issue certificate for {len(domains)} domains?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if _run_certbot(domains, email, ca_key):
        show_success(f"SAN Certificate issued for {len(domains)} domains!")
    else:
        show_error("Failed to issue certificate.")
    
    press_enter_to_continue()


def issue_wildcard_certificate():
    """Issue wildcard certificate (requires DNS challenge)."""
    clear_screen()
    show_header()
    show_panel("Issue Wildcard Certificate", title="Issue Certificate", style="cyan")
    
    if not _check_certbot():
        press_enter_to_continue()
        return
    
    console.print("[yellow]Wildcard certificates require DNS-01 challenge.[/yellow]")
    console.print("[dim]You need to configure a DNS provider or use manual mode.[/dim]")
    console.print()
    
    domain = text_input(
        title="Domain",
        message="Enter base domain (e.g., example.com):"
    )
    
    if not domain:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    domain = domain.strip().lower()
    wildcard = f"*.{domain}"
    
    include_root = confirm_action(f"Include root domain ({domain}) in certificate?")
    
    domains = [wildcard]
    if include_root:
        domains.append(domain)
    
    from modules.ssl.dns_providers import get_configured_provider
    
    provider = get_configured_provider(domain)
    
    if provider:
        console.print(f"[green]✓[/green] DNS Provider: {provider['name']} configured")
        use_api = confirm_action("Use automatic DNS verification?")
    else:
        console.print("[yellow]![/yellow] No DNS provider configured for this domain")
        use_api = False
    
    if not use_api:
        _issue_wildcard_manual(domains, domain)
    else:
        _issue_wildcard_auto(domains, domain, provider)


def _issue_wildcard_manual(domains, base_domain):
    """Issue wildcard with manual DNS verification."""
    email = _get_email()
    if not email:
        press_enter_to_continue()
        return
    
    console.print()
    console.print("[bold]Manual DNS Verification[/bold]")
    console.print()
    console.print("You will need to add a TXT record to your DNS.")
    console.print("The record details will be shown during the process.")
    console.print()
    
    if not confirm_action("Ready to proceed?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    domain_args = " ".join(f"-d {d}" for d in domains)
    
    cmd = f"certbot certonly --manual --preferred-challenges dns {domain_args} -m {email} --agree-tos"
    
    show_info("Starting certificate request...")
    console.print("[yellow]Follow the prompts to add DNS TXT record.[/yellow]")
    console.print()
    
    result = subprocess.run(cmd.split(), capture_output=False)
    
    if result.returncode == 0:
        show_success(f"Wildcard certificate issued for {domains[0]}!")
        log_event(base_domain, "issued", f"Wildcard, manual DNS")
    else:
        show_error("Failed to issue wildcard certificate.")
    
    press_enter_to_continue()


def _issue_wildcard_auto(domains, base_domain, provider):
    """Issue wildcard with automatic DNS verification."""
    email = _get_email()
    if not email:
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    domain_args = " ".join(f"-d {d}" for d in domains)
    
    plugin = provider.get("certbot_plugin", "")
    credentials = provider.get("credentials_file", "")
    
    if not plugin:
        show_error("DNS provider plugin not configured.")
        press_enter_to_continue()
        return
    
    cmd = (
        f"certbot certonly --{plugin} "
        f"--{plugin}-credentials {credentials} "
        f"{domain_args} -m {email} --agree-tos --non-interactive"
    )
    
    show_info(f"Issuing wildcard via {provider['name']}...")
    
    returncode = run_command_realtime(cmd, "Generating wildcard certificate...")
    
    if returncode == 0:
        show_success(f"Wildcard certificate issued for {domains[0]}!")
        log_event(base_domain, "issued", f"Wildcard, {provider['name']} DNS")
    else:
        show_error("Failed to issue wildcard certificate.")
    
    press_enter_to_continue()
