"""Email deliverability configuration (DKIM, SPF, DMARC)."""

import os
import re

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, run_command_realtime, is_installed, require_root
from modules.email.postfix.utils import (
    is_postfix_ready, get_postfix_setting, set_postfix_settings, 
    reload_postfix, get_configured_domains,
)


# OpenDKIM paths
OPENDKIM_CONF = "/etc/opendkim.conf"
OPENDKIM_KEYS_DIR = "/etc/opendkim/keys"
OPENDKIM_KEY_TABLE = "/etc/opendkim/key.table"
OPENDKIM_SIGNING_TABLE = "/etc/opendkim/signing.table"
OPENDKIM_TRUSTED_HOSTS = "/etc/opendkim/trusted.hosts"


def show_deliverability_menu():
    """Display deliverability menu."""
    def get_status():
        dkim = "[green]✓[/green]" if is_installed("opendkim") else "[dim]○[/dim]"
        return f"DKIM:{dkim}"
    
    options = [
        ("status", "1. View Status"),
        ("dkim", "2. Setup DKIM"),
        ("spf", "3. Generate SPF Record"),
        ("dmarc", "4. Generate DMARC Record"),
        ("test", "5. Test Deliverability"),
        ("dns", "6. View DNS Records"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "status": view_status,
        "dkim": setup_dkim_menu,
        "spf": generate_spf_record,
        "dmarc": generate_dmarc_record,
        "test": test_deliverability,
        "dns": view_dns_records,
    }
    
    run_menu_loop("Deliverability", options, handlers, get_status)


def view_status():
    """View current deliverability status."""
    clear_screen()
    show_header()
    show_panel("Deliverability Status", title="Email", style="cyan")
    
    columns = [
        {"name": "Component", "style": "cyan"},
        {"name": "Status"},
        {"name": "Details"},
    ]
    
    rows = []
    
    # DKIM
    if is_installed("opendkim"):
        from utils.shell import is_service_running
        running = is_service_running("opendkim")
        status = "[green]Running[/green]" if running else "[red]Stopped[/red]"
        
        # Count configured domains
        if os.path.exists(OPENDKIM_SIGNING_TABLE):
            with open(OPENDKIM_SIGNING_TABLE) as f:
                domains = len([l for l in f if l.strip() and not l.startswith('#')])
        else:
            domains = 0
        
        rows.append(["DKIM (OpenDKIM)", status, f"{domains} domain(s)"])
    else:
        rows.append(["DKIM (OpenDKIM)", "[dim]Not Installed[/dim]", ""])
    
    # TLS
    tls = get_postfix_setting("smtpd_tls_security_level")
    if tls in ["may", "encrypt"]:
        rows.append(["TLS", "[green]Enabled[/green]", tls])
    else:
        rows.append(["TLS", "[yellow]Disabled[/yellow]", "Consider enabling"])
    
    # Hostname
    hostname = get_postfix_setting("myhostname")
    rows.append(["Mail Hostname", "[green]Set[/green]" if hostname else "[yellow]Not Set[/yellow]", hostname or ""])
    
    show_table("", columns, rows, show_header=True)
    
    console.print()
    console.print("[bold]DNS Records to Add:[/bold]")
    console.print("[dim]Use the menu options to generate SPF, DKIM, and DMARC records.[/dim]")
    
    press_enter_to_continue()


def setup_dkim_menu():
    """DKIM setup menu."""
    def get_status():
        if is_installed("opendkim"):
            return "OpenDKIM: [green]Installed[/green]"
        return "OpenDKIM: [dim]Not Installed[/dim]"
    
    options = [
        ("install", "1. Install OpenDKIM"),
        ("add", "2. Add Domain"),
        ("remove", "3. Remove Domain"),
        ("list", "4. List DKIM Domains"),
        ("keys", "5. View DNS Records"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "install": install_opendkim,
        "add": add_dkim_domain,
        "remove": remove_dkim_domain,
        "list": list_dkim_domains,
        "keys": view_dkim_keys,
    }
    
    run_menu_loop("DKIM Setup", options, handlers, get_status)


def install_opendkim():
    """Install and configure OpenDKIM."""
    clear_screen()
    show_header()
    show_panel("Install OpenDKIM", title="DKIM", style="cyan")
    
    if is_installed("opendkim"):
        show_info("OpenDKIM is already installed.")
        press_enter_to_continue()
        return
    
    console.print("[bold]OpenDKIM will be installed to sign outgoing emails.[/bold]")
    console.print()
    console.print("This helps prevent your emails from being marked as spam.")
    console.print()
    
    if not confirm_action("Install OpenDKIM?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Install packages
    show_info("Installing OpenDKIM...")
    
    returncode = run_command_realtime(
        "apt install -y opendkim opendkim-tools",
        "Installing OpenDKIM..."
    )
    
    if returncode != 0:
        show_error("Failed to install OpenDKIM.")
        press_enter_to_continue()
        return
    
    # Create directories
    os.makedirs(OPENDKIM_KEYS_DIR, mode=0o700, exist_ok=True)
    
    # Configure OpenDKIM
    config_content = """# OpenDKIM configuration - managed by vexo
AutoRestart             Yes
AutoRestartRate         10/1h
Canonicalization        relaxed/simple
ExternalIgnoreList      refile:/etc/opendkim/trusted.hosts
InternalHosts           refile:/etc/opendkim/trusted.hosts
KeyTable                refile:/etc/opendkim/key.table
SigningTable            refile:/etc/opendkim/signing.table
Mode                    sv
PidFile                 /run/opendkim/opendkim.pid
SignatureAlgorithm      rsa-sha256
Socket                  inet:8891@localhost
Syslog                  Yes
SyslogSuccess           Yes
TemporaryDirectory      /var/tmp
UMask                   002
UserID                  opendkim:opendkim
"""
    
    with open(OPENDKIM_CONF, 'w') as f:
        f.write(config_content)
    
    # Create trusted hosts
    with open(OPENDKIM_TRUSTED_HOSTS, 'w') as f:
        f.write("127.0.0.1\nlocalhost\n")
    
    # Create empty key and signing tables
    open(OPENDKIM_KEY_TABLE, 'w').close()
    open(OPENDKIM_SIGNING_TABLE, 'w').close()
    
    # Configure Postfix to use OpenDKIM
    postfix_settings = {
        "milter_protocol": "6",
        "milter_default_action": "accept",
        "smtpd_milters": "inet:localhost:8891",
        "non_smtpd_milters": "inet:localhost:8891",
    }
    set_postfix_settings(postfix_settings)
    
    # Start services
    from utils.shell import service_control
    service_control("opendkim", "restart")
    service_control("opendkim", "enable")
    reload_postfix()
    
    show_success("OpenDKIM installed and configured!")
    console.print()
    console.print("[yellow]Next: Add domains using 'Add Domain' option.[/yellow]")
    
    press_enter_to_continue()


def add_dkim_domain():
    """Add DKIM signing for a domain."""
    clear_screen()
    show_header()
    show_panel("Add DKIM Domain", title="DKIM", style="cyan")
    
    if not is_installed("opendkim"):
        show_error("OpenDKIM is not installed.")
        press_enter_to_continue()
        return
    
    # Get domain
    configured = get_configured_domains()
    
    if configured:
        console.print("[bold]Configured email domains:[/bold]")
        for d in configured:
            console.print(f"  • {d}")
        console.print()
    
    domain = text_input("Domain to add DKIM for:")
    if not domain:
        return
    
    domain = domain.lower().strip()
    
    # Check if already configured
    if os.path.exists(os.path.join(OPENDKIM_KEYS_DIR, domain)):
        show_warning(f"DKIM already configured for {domain}.")
        if not confirm_action("Regenerate keys?"):
            press_enter_to_continue()
            return
    
    selector = text_input("DKIM selector:", default="default")
    if not selector:
        selector = "default"
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    show_info(f"Generating DKIM keys for {domain}...")
    
    # Create domain key directory
    domain_key_dir = os.path.join(OPENDKIM_KEYS_DIR, domain)
    os.makedirs(domain_key_dir, mode=0o700, exist_ok=True)
    
    # Generate keys
    result = run_command(
        f"opendkim-genkey -b 2048 -d {domain} -D {domain_key_dir} -s {selector} -v",
        check=False, silent=True
    )
    
    if result.returncode != 0:
        show_error("Failed to generate DKIM keys.")
        press_enter_to_continue()
        return
    
    # Set permissions
    run_command(f"chown -R opendkim:opendkim {domain_key_dir}", check=False, silent=True)
    
    # Update key table
    key_entry = f"{selector}._domainkey.{domain} {domain}:{selector}:{domain_key_dir}/{selector}.private\n"
    
    with open(OPENDKIM_KEY_TABLE, 'a') as f:
        f.write(key_entry)
    
    # Update signing table
    signing_entry = f"*@{domain} {selector}._domainkey.{domain}\n"
    
    with open(OPENDKIM_SIGNING_TABLE, 'a') as f:
        f.write(signing_entry)
    
    # Add to trusted hosts
    with open(OPENDKIM_TRUSTED_HOSTS, 'a') as f:
        f.write(f"*.{domain}\n")
    
    # Restart OpenDKIM
    from utils.shell import service_control
    service_control("opendkim", "restart")
    
    # Read public key
    txt_file = os.path.join(domain_key_dir, f"{selector}.txt")
    if os.path.exists(txt_file):
        with open(txt_file) as f:
            dns_record = f.read()
        
        show_success(f"DKIM configured for {domain}!")
        console.print()
        console.print("[bold yellow]Add this DNS TXT record:[/bold yellow]")
        console.print()
        console.print(f"[cyan]Name:[/cyan] {selector}._domainkey.{domain}")
        console.print()
        console.print("[cyan]Value:[/cyan]")
        # Clean up the record for display
        record_value = _extract_dkim_value(dns_record)
        console.print(f"  {record_value}")
    else:
        show_success(f"DKIM configured for {domain}!")
        console.print("[dim]Use 'View DNS Records' to see the record to add.[/dim]")
    
    press_enter_to_continue()


def _extract_dkim_value(dns_record):
    """Extract clean DKIM value from opendkim-genkey output."""
    # Remove comments and formatting
    lines = dns_record.split('\n')
    value_parts = []
    
    for line in lines:
        # Find quoted parts
        matches = re.findall(r'"([^"]*)"', line)
        value_parts.extend(matches)
    
    return ''.join(value_parts)


def remove_dkim_domain():
    """Remove DKIM signing for a domain."""
    clear_screen()
    show_header()
    show_panel("Remove DKIM Domain", title="DKIM", style="red")
    
    if not is_installed("opendkim"):
        show_error("OpenDKIM is not installed.")
        press_enter_to_continue()
        return
    
    # List configured domains
    domains = []
    if os.path.exists(OPENDKIM_KEYS_DIR):
        domains = [d for d in os.listdir(OPENDKIM_KEYS_DIR) 
                   if os.path.isdir(os.path.join(OPENDKIM_KEYS_DIR, d))]
    
    if not domains:
        show_info("No DKIM domains configured.")
        press_enter_to_continue()
        return
    
    domain = select_from_list("Select Domain", "Remove DKIM for:", domains)
    if not domain:
        return
    
    if not confirm_action(f"Remove DKIM for {domain}?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Remove key directory
    import shutil
    domain_key_dir = os.path.join(OPENDKIM_KEYS_DIR, domain)
    if os.path.exists(domain_key_dir):
        shutil.rmtree(domain_key_dir)
    
    # Remove from key table
    if os.path.exists(OPENDKIM_KEY_TABLE):
        with open(OPENDKIM_KEY_TABLE, 'r') as f:
            lines = f.readlines()
        with open(OPENDKIM_KEY_TABLE, 'w') as f:
            for line in lines:
                if domain not in line:
                    f.write(line)
    
    # Remove from signing table
    if os.path.exists(OPENDKIM_SIGNING_TABLE):
        with open(OPENDKIM_SIGNING_TABLE, 'r') as f:
            lines = f.readlines()
        with open(OPENDKIM_SIGNING_TABLE, 'w') as f:
            for line in lines:
                if domain not in line:
                    f.write(line)
    
    # Restart OpenDKIM
    from utils.shell import service_control
    service_control("opendkim", "restart")
    
    show_success(f"DKIM removed for {domain}!")
    console.print("[dim]Remember to remove the DNS TXT record.[/dim]")
    
    press_enter_to_continue()


def list_dkim_domains():
    """List domains with DKIM configured."""
    clear_screen()
    show_header()
    show_panel("DKIM Domains", title="DKIM", style="cyan")
    
    if not is_installed("opendkim"):
        show_error("OpenDKIM is not installed.")
        press_enter_to_continue()
        return
    
    domains = []
    if os.path.exists(OPENDKIM_KEYS_DIR):
        domains = [d for d in os.listdir(OPENDKIM_KEYS_DIR) 
                   if os.path.isdir(os.path.join(OPENDKIM_KEYS_DIR, d))]
    
    if not domains:
        show_info("No DKIM domains configured.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Domain", "style": "cyan"},
        {"name": "Selector"},
        {"name": "Key File"},
    ]
    
    rows = []
    for domain in domains:
        domain_dir = os.path.join(OPENDKIM_KEYS_DIR, domain)
        # Find selector from key files
        for f in os.listdir(domain_dir):
            if f.endswith('.private'):
                selector = f.replace('.private', '')
                rows.append([domain, selector, f"{domain_dir}/{f}"])
                break
    
    show_table(f"{len(domains)} domain(s)", columns, rows, show_header=True)
    press_enter_to_continue()


def view_dkim_keys():
    """View DKIM DNS records to add."""
    clear_screen()
    show_header()
    show_panel("DKIM DNS Records", title="DKIM", style="cyan")
    
    if not is_installed("opendkim"):
        show_error("OpenDKIM is not installed.")
        press_enter_to_continue()
        return
    
    domains = []
    if os.path.exists(OPENDKIM_KEYS_DIR):
        domains = [d for d in os.listdir(OPENDKIM_KEYS_DIR) 
                   if os.path.isdir(os.path.join(OPENDKIM_KEYS_DIR, d))]
    
    if not domains:
        show_info("No DKIM domains configured.")
        press_enter_to_continue()
        return
    
    for domain in domains:
        domain_dir = os.path.join(OPENDKIM_KEYS_DIR, domain)
        
        for f in os.listdir(domain_dir):
            if f.endswith('.txt'):
                selector = f.replace('.txt', '')
                txt_path = os.path.join(domain_dir, f)
                
                console.print(f"[bold cyan]{domain}[/bold cyan]")
                console.print(f"[bold]Name:[/bold] {selector}._domainkey.{domain}")
                console.print("[bold]Type:[/bold] TXT")
                console.print("[bold]Value:[/bold]")
                
                with open(txt_path) as tf:
                    content = tf.read()
                    value = _extract_dkim_value(content)
                    console.print(f"  {value}")
                
                console.print()
    
    press_enter_to_continue()


def generate_spf_record():
    """Generate SPF DNS record."""
    clear_screen()
    show_header()
    show_panel("Generate SPF Record", title="Deliverability", style="cyan")
    
    console.print("[bold]SPF (Sender Policy Framework)[/bold]")
    console.print("Specifies which servers are allowed to send email for your domain.")
    console.print()
    
    # Get server IP
    result = run_command("curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com", check=False, silent=True)
    server_ip = result.stdout.strip() if result.returncode == 0 else ""
    
    console.print(f"[dim]Detected server IP: {server_ip}[/dim]")
    console.print()
    
    # Build SPF record
    spf_parts = ["v=spf1"]
    
    # Server IP
    if server_ip:
        if confirm_action(f"Include server IP ({server_ip})?"):
            spf_parts.append(f"ip4:{server_ip}")
    
    # MX records
    if confirm_action("Include MX servers (mx)?"):
        spf_parts.append("mx")
    
    # A record
    if confirm_action("Include A record servers (a)?"):
        spf_parts.append("a")
    
    # External providers
    providers = [
        ("SendGrid", "include:sendgrid.net"),
        ("Amazon SES", "include:amazonses.com"),
        ("Mailgun", "include:mailgun.org"),
        ("Mailjet", "include:spf.mailjet.com"),
        ("Google Workspace", "include:_spf.google.com"),
        ("Microsoft 365", "include:spf.protection.outlook.com"),
    ]
    
    console.print()
    console.print("[bold]External email providers:[/bold]")
    
    for name, include in providers:
        if confirm_action(f"Include {name}?"):
            spf_parts.append(include)
    
    # Policy
    console.print()
    policies = [
        "-all (strict - reject unauthorized)",
        "~all (soft fail - mark as spam)",
        "?all (neutral - no action)",
    ]
    
    policy = select_from_list("SPF Policy", "How to handle unauthorized senders:", policies)
    if policy:
        spf_parts.append(policy.split(" ")[0])
    else:
        spf_parts.append("~all")
    
    # Generate record
    spf_record = " ".join(spf_parts)
    
    console.print()
    console.print("[bold green]═══ SPF Record ═══[/bold green]")
    console.print()
    
    domain = text_input("Domain (for display):", default="example.com")
    
    console.print(f"[bold]Name:[/bold] {domain} (or @)")
    console.print("[bold]Type:[/bold] TXT")
    console.print(f"[bold]Value:[/bold] {spf_record}")
    console.print()
    console.print("[dim]Add this record to your DNS settings.[/dim]")
    
    press_enter_to_continue()


def generate_dmarc_record():
    """Generate DMARC DNS record."""
    clear_screen()
    show_header()
    show_panel("Generate DMARC Record", title="Deliverability", style="cyan")
    
    console.print("[bold]DMARC (Domain-based Message Authentication)[/bold]")
    console.print("Tells receivers what to do when SPF/DKIM checks fail.")
    console.print()
    
    domain = text_input("Domain:", default="example.com")
    if not domain:
        return
    
    # Policy
    policies = [
        "none (monitor only, no action)",
        "quarantine (send to spam)",
        "reject (block the email)",
    ]
    
    policy = select_from_list("DMARC Policy", "What to do with failed emails:", policies)
    if not policy:
        return
    
    policy_value = policy.split(" ")[0]
    
    # Reporting email
    report_email = text_input("Email for reports (optional):", default=f"postmaster@{domain}")
    
    # Build DMARC record
    dmarc_parts = [f"v=DMARC1", f"p={policy_value}"]
    
    if report_email:
        dmarc_parts.append(f"rua=mailto:{report_email}")
        if confirm_action("Also receive forensic reports?"):
            dmarc_parts.append(f"ruf=mailto:{report_email}")
    
    # Percentage
    if policy_value != "none":
        pct = text_input("Percentage to apply policy (0-100):", default="100")
        if pct and pct != "100":
            dmarc_parts.append(f"pct={pct}")
    
    dmarc_record = "; ".join(dmarc_parts)
    
    console.print()
    console.print("[bold green]═══ DMARC Record ═══[/bold green]")
    console.print()
    console.print(f"[bold]Name:[/bold] _dmarc.{domain}")
    console.print("[bold]Type:[/bold] TXT")
    console.print(f"[bold]Value:[/bold] {dmarc_record}")
    console.print()
    console.print("[dim]Add this record to your DNS settings.[/dim]")
    
    press_enter_to_continue()


def test_deliverability():
    """Test email deliverability."""
    clear_screen()
    show_header()
    show_panel("Test Deliverability", title="Deliverability", style="cyan")
    
    if not is_postfix_ready():
        show_error("Postfix is not running.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Options:[/bold]")
    console.print()
    console.print("1. Send test to mail-tester.com (get a score)")
    console.print("2. Send test to your email")
    console.print("3. Check DKIM signature locally")
    console.print()
    
    options = [
        "Send to custom email",
        "Check DKIM configuration",
    ]
    
    choice = select_from_list("Test", "Select:", options)
    if not choice:
        return
    
    if "custom" in choice:
        recipient = text_input("Recipient email:")
        if not recipient or "@" not in recipient:
            return
        
        from utils.shell import get_hostname
        hostname = get_hostname()
        subject = f"Deliverability Test from {hostname}"
        body = f"""This is a deliverability test email from vexo.

Server: {hostname}

Check the email headers for:
- DKIM-Signature header (if DKIM configured)
- Received-SPF header
- Authentication-Results header

If you received this in your inbox (not spam), deliverability is working!
"""
        
        result = run_command(
            f'echo "{body}" | mail -s "{subject}" {recipient}',
            check=False, silent=True
        )
        
        if result.returncode == 0:
            show_success("Test email sent!")
            console.print(f"[dim]Check {recipient} inbox (and spam folder).[/dim]")
        else:
            show_error("Failed to send test email.")
    
    else:
        # Check DKIM
        if not is_installed("opendkim"):
            show_warning("OpenDKIM is not installed.")
            press_enter_to_continue()
            return
        
        result = run_command("opendkim-testkey -vvv -d example.com -s default 2>&1 | head -20", check=False, silent=True)
        console.print("[bold]DKIM Test Output:[/bold]")
        console.print(result.stdout if result.stdout else "[dim]No output[/dim]")
    
    press_enter_to_continue()


def view_dns_records():
    """View all DNS records needed for email."""
    clear_screen()
    show_header()
    show_panel("DNS Records Summary", title="Deliverability", style="cyan")
    
    domain = text_input("Domain to check:", default="example.com")
    if not domain:
        return
    
    console.print()
    console.print(f"[bold]Required DNS records for {domain}:[/bold]")
    console.print()
    
    # MX Record
    console.print("[cyan]1. MX Record[/cyan]")
    hostname = get_postfix_setting("myhostname") or "mail.example.com"
    console.print(f"   Name: {domain}")
    console.print(f"   Type: MX")
    console.print(f"   Priority: 10")
    console.print(f"   Value: {hostname}")
    console.print()
    
    # SPF Record
    result = run_command("curl -s ifconfig.me 2>/dev/null", check=False, silent=True)
    server_ip = result.stdout.strip() if result.returncode == 0 else "YOUR_SERVER_IP"
    
    console.print("[cyan]2. SPF Record[/cyan]")
    console.print(f"   Name: {domain}")
    console.print(f"   Type: TXT")
    console.print(f"   Value: v=spf1 ip4:{server_ip} mx -all")
    console.print()
    
    # DKIM Record
    if is_installed("opendkim"):
        domain_dir = os.path.join(OPENDKIM_KEYS_DIR, domain)
        if os.path.exists(domain_dir):
            for f in os.listdir(domain_dir):
                if f.endswith('.txt'):
                    selector = f.replace('.txt', '')
                    console.print("[cyan]3. DKIM Record[/cyan]")
                    console.print(f"   Name: {selector}._domainkey.{domain}")
                    console.print(f"   Type: TXT")
                    with open(os.path.join(domain_dir, f)) as tf:
                        value = _extract_dkim_value(tf.read())
                        console.print(f"   Value: {value[:50]}...")
                    console.print()
                    break
        else:
            console.print("[cyan]3. DKIM Record[/cyan]")
            console.print("   [dim]Not configured for this domain[/dim]")
            console.print()
    
    # DMARC Record
    console.print("[cyan]4. DMARC Record[/cyan]")
    console.print(f"   Name: _dmarc.{domain}")
    console.print(f"   Type: TXT")
    console.print(f"   Value: v=DMARC1; p=quarantine; rua=mailto:postmaster@{domain}")
    console.print()
    
    press_enter_to_continue()
