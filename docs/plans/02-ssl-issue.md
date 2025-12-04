# Phase 2: Issue Certificate (Single/SAN/Wildcard)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement certificate issuance for single domain, SAN (multiple domains), and wildcard certificates with multiple CA support.

**Architecture:** Wizard-based flow for each certificate type. Pre-flight checks before issuance. Support Let's Encrypt, ZeroSSL, Buypass CAs via certbot or acme.sh.

**Tech Stack:** Python, Rich, Certbot CLI, ACME protocol

---

## Task 1: Add CA Configuration to Common

**Files:**
- Modify: `modules/ssl/common.py`

**Step 1: Add CA definitions**

Add to common.py:

```python
# Certificate Authorities
CERTIFICATE_AUTHORITIES = {
    "letsencrypt": {
        "name": "Let's Encrypt",
        "server": None,  # Default certbot server
        "validity": 90,
        "description": "Free, 90 days, widely trusted"
    },
    "letsencrypt_staging": {
        "name": "Let's Encrypt (Staging)",
        "server": "https://acme-staging-v02.api.letsencrypt.org/directory",
        "validity": 90,
        "description": "Testing only, not trusted"
    },
    "zerossl": {
        "name": "ZeroSSL",
        "server": "https://acme.zerossl.com/v2/DV90",
        "validity": 90,
        "description": "Free, 90 days, alternative to LE"
    },
    "buypass": {
        "name": "Buypass",
        "server": "https://api.buypass.com/acme/directory",
        "validity": 180,
        "description": "Free, 180 days, longer validity"
    }
}


def get_default_ca():
    """Get default CA from settings."""
    settings = load_settings()
    return settings.get("default_ca", "letsencrypt")


def load_settings():
    """Load SSL settings."""
    if not os.path.exists(SETTINGS_FILE):
        return {"default_ca": "letsencrypt"}
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"default_ca": "letsencrypt"}


def save_settings(settings):
    """Save SSL settings."""
    ensure_config_dir()
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)


def run_preflight_checks(domains):
    """
    Run pre-flight checks before issuing certificate.
    
    Returns:
        tuple: (success: bool, messages: list)
    """
    messages = []
    success = True
    
    # Check nginx installed
    if not is_installed("nginx"):
        messages.append(("[red]✗[/red]", "Nginx is not installed"))
        success = False
    else:
        messages.append(("[green]✓[/green]", "Nginx is installed"))
    
    # Check nginx running
    result = run_command("systemctl is-active nginx", check=False, silent=True)
    if result.returncode == 0:
        messages.append(("[green]✓[/green]", "Nginx is running"))
    else:
        messages.append(("[yellow]![/yellow]", "Nginx is not running"))
    
    # Check port 80
    result = run_command("ss -tlnp | grep ':80 '", check=False, silent=True)
    if result.returncode == 0:
        messages.append(("[green]✓[/green]", "Port 80 is listening"))
    else:
        messages.append(("[red]✗[/red]", "Port 80 is not listening"))
        success = False
    
    # Check DNS for each domain
    import socket
    server_ip = _get_server_ip()
    
    for domain in domains:
        try:
            resolved_ip = socket.gethostbyname(domain)
            if resolved_ip == server_ip:
                messages.append(("[green]✓[/green]", f"DNS {domain} → {resolved_ip} (correct)"))
            else:
                messages.append(("[yellow]![/yellow]", f"DNS {domain} → {resolved_ip} (expected {server_ip})"))
        except socket.gaierror:
            messages.append(("[red]✗[/red]", f"DNS {domain} - cannot resolve"))
            success = False
    
    return success, messages


def _get_server_ip():
    """Get server's public IP."""
    result = run_command("curl -s ifconfig.me", check=False, silent=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return "unknown"
```

**Step 2: Commit**

```bash
git add modules/ssl/common.py
git commit -m "feat(ssl): add CA definitions and preflight checks"
```

---

## Task 2: Implement Issue Certificate Module

**Files:**
- Modify: `modules/ssl/issue.py`

**Step 1: Replace issue.py with full implementation**

```python
"""Issue SSL certificates."""

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
            continue  # Hide staging by default
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
    
    # Map choice back to key
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
    
    if not email or "@" not in email:
        show_error("Valid email is required.")
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
    
    # Build certbot command
    domain_args = " ".join(f"-d {d}" for d in domains)
    
    cmd = f"certbot --nginx {domain_args} --non-interactive --agree-tos -m {email}"
    
    # Add CA server if not default Let's Encrypt
    if ca.get("server"):
        cmd += f" --server {ca['server']}"
    
    # For ZeroSSL, need EAB credentials (simplified - would need config)
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
    
    # Get domain
    domain = text_input(
        title="Domain",
        message="Enter domain name (e.g., example.com):"
    )
    
    if not domain:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Clean domain
    domain = domain.strip().lower()
    if domain.startswith("http"):
        domain = domain.split("//")[-1].split("/")[0]
    
    # Pre-flight checks
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
    
    # Select CA
    ca_key = _select_ca()
    if not ca_key:
        press_enter_to_continue()
        return
    
    # Get email
    email = _get_email()
    if not email:
        press_enter_to_continue()
        return
    
    # Confirm
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
    
    # Issue certificate
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
    
    # Get primary domain
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
    
    # Get additional domains
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
    
    # Pre-flight checks
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
    
    # Select CA
    ca_key = _select_ca()
    if not ca_key:
        press_enter_to_continue()
        return
    
    # Get email
    email = _get_email()
    if not email:
        press_enter_to_continue()
        return
    
    # Confirm
    console.print()
    console.print("[bold]Domains:[/bold]")
    for d in domains:
        console.print(f"  • {d}")
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
    
    # Issue certificate
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
    
    console.print("[yellow]⚠ Wildcard certificates require DNS-01 challenge.[/yellow]")
    console.print("[dim]You need to configure a DNS provider or use manual mode.[/dim]")
    console.print()
    
    # Get base domain
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
    
    # Include root domain?
    include_root = confirm_action(f"Include root domain ({domain}) in certificate?")
    
    domains = [wildcard]
    if include_root:
        domains.append(domain)
    
    # Check DNS provider configuration
    from modules.ssl.dns_providers import get_configured_provider
    
    provider = get_configured_provider(domain)
    
    if provider:
        console.print(f"[green]✓[/green] DNS Provider: {provider['name']} configured")
        use_api = confirm_action("Use automatic DNS verification?")
    else:
        console.print("[yellow]![/yellow] No DNS provider configured for this domain")
        use_api = False
    
    if not use_api:
        # Manual DNS mode
        _issue_wildcard_manual(domains, domain)
    else:
        # Automatic DNS mode
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
    
    # Run interactively for manual DNS
    import subprocess
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
    
    # Build certbot command with DNS plugin
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
```

**Step 2: Commit**

```bash
git add modules/ssl/issue.py
git commit -m "feat(ssl): implement certificate issuance for single/SAN/wildcard"
```

---

## Verification

After completing all tasks:

1. **Single Domain works:**
   - Pre-flight checks run
   - CA selection works
   - Certificate issued via certbot

2. **SAN Certificate works:**
   - Multiple domains can be added
   - All domains in single certificate

3. **Wildcard works:**
   - DNS challenge required
   - Manual mode shows TXT record instructions
   - Auto mode uses configured DNS provider
