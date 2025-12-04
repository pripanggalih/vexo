"""SMTP relay configuration for Postfix."""

import os
import json

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, is_installed, require_root
from modules.email.postfix.utils import (
    is_postfix_ready, get_postfix_setting, set_postfix_settings,
    reload_postfix, restart_postfix,
)
from modules.email.utils import load_email_config, save_email_config


# Postfix SASL files
POSTFIX_SASL_PASSWD = "/etc/postfix/sasl_passwd"
POSTFIX_SENDER_RELAY = "/etc/postfix/sender_relay"
POSTFIX_SENDER_RELAY_PASSWD = "/etc/postfix/sender_relay_passwd"


# Relay provider presets
RELAY_PROVIDERS = {
    "sendgrid": {
        "name": "SendGrid",
        "host": "smtp.sendgrid.net",
        "port": 587,
        "auth": True,
        "username_hint": "apikey",
        "password_hint": "Your SendGrid API Key",
    },
    "ses": {
        "name": "Amazon SES",
        "host": "email-smtp.{region}.amazonaws.com",
        "port": 587,
        "auth": True,
        "username_hint": "SMTP Username (from SES console)",
        "password_hint": "SMTP Password (from SES console)",
        "regions": ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
    },
    "mailgun": {
        "name": "Mailgun",
        "host": "smtp.mailgun.org",
        "port": 587,
        "auth": True,
        "username_hint": "Your Mailgun SMTP username",
        "password_hint": "Your Mailgun SMTP password",
    },
    "mailjet": {
        "name": "Mailjet",
        "host": "in-v3.mailjet.com",
        "port": 587,
        "auth": True,
        "username_hint": "API Key",
        "password_hint": "Secret Key",
    },
    "smtp2go": {
        "name": "SMTP2GO",
        "host": "mail.smtp2go.com",
        "port": 587,
        "auth": True,
        "username_hint": "Your SMTP2GO username",
        "password_hint": "Your SMTP2GO password",
    },
    "custom": {
        "name": "Custom SMTP",
        "host": "",
        "port": 587,
        "auth": True,
        "username_hint": "SMTP username",
        "password_hint": "SMTP password",
    },
}


def show_relay_menu():
    """Display SMTP relay menu."""
    def get_status():
        relayhost = get_postfix_setting("relayhost")
        if relayhost:
            return f"Relay: [green]{relayhost}[/green]"
        return "Relay: [dim]Direct Send[/dim]"
    
    options = [
        ("status", "1. View Status"),
        ("config", "2. Configure Relay"),
        ("profiles", "3. Domain Profiles"),
        ("test", "4. Test Connection"),
        ("disable", "5. Disable Relay"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "status": view_relay_status,
        "config": configure_relay,
        "profiles": manage_profiles_menu,
        "test": test_relay_connection,
        "disable": disable_relay,
    }
    
    run_menu_loop("SMTP Relay", options, handlers, get_status)


def view_relay_status():
    """View current relay configuration."""
    clear_screen()
    show_header()
    show_panel("Relay Status", title="SMTP Relay", style="cyan")
    
    if not is_postfix_ready():
        show_error("Postfix is not running.")
        press_enter_to_continue()
        return
    
    relayhost = get_postfix_setting("relayhost")
    
    if not relayhost:
        console.print("[bold]Mode:[/bold] Direct Send (no relay)")
        console.print()
        console.print("[dim]Emails are sent directly to recipient mail servers.[/dim]")
        press_enter_to_continue()
        return
    
    console.print(f"[bold]Relay Host:[/bold] {relayhost}")
    
    # Check for SASL auth
    sasl_auth = get_postfix_setting("smtp_sasl_auth_enable")
    if sasl_auth == "yes":
        console.print("[bold]Authentication:[/bold] [green]Enabled[/green]")
    else:
        console.print("[bold]Authentication:[/bold] [dim]Disabled[/dim]")
    
    # Check TLS
    tls = get_postfix_setting("smtp_tls_security_level")
    console.print(f"[bold]TLS:[/bold] {tls or 'may'}")
    
    # Check for per-sender relay
    sender_relay = get_postfix_setting("sender_dependent_relayhost_maps")
    if sender_relay:
        console.print()
        console.print("[bold]Per-Domain Profiles:[/bold] [green]Enabled[/green]")
        
        # Load profiles
        config = load_email_config()
        profiles = config.get("relay_profiles", {})
        
        if profiles:
            console.print()
            for domain, profile in profiles.items():
                console.print(f"  • {domain} → {profile.get('provider', 'custom')}")
    
    press_enter_to_continue()


def configure_relay():
    """Configure SMTP relay provider."""
    clear_screen()
    show_header()
    show_panel("Configure Relay", title="SMTP Relay", style="cyan")
    
    if not is_postfix_ready():
        show_error("Postfix is not running.")
        press_enter_to_continue()
        return
    
    # Select provider
    provider_options = [
        f"{p['name']}" for p in RELAY_PROVIDERS.values()
    ]
    
    choice = select_from_list("Provider", "Select relay provider:", provider_options)
    if not choice:
        return
    
    # Find provider key
    provider_key = None
    for key, p in RELAY_PROVIDERS.items():
        if p["name"] == choice:
            provider_key = key
            break
    
    if not provider_key:
        return
    
    provider = RELAY_PROVIDERS[provider_key]
    
    console.print()
    console.print(f"[bold]Configuring {provider['name']}[/bold]")
    console.print()
    
    # Get host
    if provider_key == "custom":
        host = text_input("SMTP Host:")
        if not host:
            return
    elif provider_key == "ses":
        # Region selection for SES
        region = select_from_list("AWS Region", "Select region:", provider["regions"])
        if not region:
            return
        host = provider["host"].format(region=region)
    else:
        host = provider["host"]
    
    # Get port
    port = text_input("Port:", default=str(provider["port"]))
    if not port:
        port = str(provider["port"])
    
    # Get credentials if auth required
    username = None
    password = None
    
    if provider["auth"]:
        console.print()
        console.print(f"[dim]Username hint: {provider['username_hint']}[/dim]")
        username = text_input("Username:")
        if not username:
            return
        
        console.print(f"[dim]Password hint: {provider['password_hint']}[/dim]")
        
        from getpass import getpass
        try:
            password = getpass("Password: ")
        except Exception:
            password = text_input("Password:")
        
        if not password:
            return
    
    # Confirm
    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  Provider: {provider['name']}")
    console.print(f"  Host: {host}:{port}")
    console.print(f"  Auth: {'Yes' if username else 'No'}")
    console.print()
    
    if not confirm_action("Apply this relay configuration?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Install SASL if needed
    if provider["auth"] and not is_installed("libsasl2-modules"):
        show_info("Installing SASL modules...")
        run_command("apt install -y libsasl2-modules", check=False, silent=True)
    
    # Configure Postfix
    relayhost = f"[{host}]:{port}"
    
    settings = {
        "relayhost": relayhost,
        "smtp_tls_security_level": "encrypt",
        "smtp_tls_CAfile": "/etc/ssl/certs/ca-certificates.crt",
    }
    
    if username and password:
        settings.update({
            "smtp_sasl_auth_enable": "yes",
            "smtp_sasl_password_maps": f"hash:{POSTFIX_SASL_PASSWD}",
            "smtp_sasl_security_options": "noanonymous",
            "smtp_sasl_tls_security_options": "noanonymous",
        })
        
        # Write SASL password file
        with open(POSTFIX_SASL_PASSWD, 'w') as f:
            f.write(f"{relayhost} {username}:{password}\n")
        
        os.chmod(POSTFIX_SASL_PASSWD, 0o600)
        run_command(f"postmap {POSTFIX_SASL_PASSWD}", check=False, silent=True)
    
    set_postfix_settings(settings)
    
    # Save to config
    config = load_email_config()
    config["default_relay"] = {
        "provider": provider_key,
        "host": host,
        "port": port,
    }
    save_email_config(config)
    
    restart_postfix()
    
    show_success(f"Relay configured via {provider['name']}!")
    console.print()
    console.print("[dim]All outgoing email will now go through this relay.[/dim]")
    
    press_enter_to_continue()


def manage_profiles_menu():
    """Manage per-domain relay profiles."""
    def get_status():
        config = load_email_config()
        profiles = config.get("relay_profiles", {})
        return f"Profiles: {len(profiles)}"
    
    options = [
        ("list", "1. List Profiles"),
        ("add", "2. Add Profile"),
        ("remove", "3. Remove Profile"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "list": list_profiles,
        "add": add_profile,
        "remove": remove_profile,
    }
    
    run_menu_loop("Domain Profiles", options, handlers, get_status)


def list_profiles():
    """List per-domain relay profiles."""
    clear_screen()
    show_header()
    show_panel("Relay Profiles", title="Domain Profiles", style="cyan")
    
    config = load_email_config()
    profiles = config.get("relay_profiles", {})
    
    # Show default relay
    default = config.get("default_relay", {})
    if default:
        console.print("[bold]Default Relay:[/bold]")
        console.print(f"  Provider: {default.get('provider', 'custom')}")
        console.print(f"  Host: {default.get('host', 'N/A')}:{default.get('port', '587')}")
        console.print()
    
    if not profiles:
        show_info("No per-domain profiles configured.")
        console.print()
        console.print("[dim]All domains use the default relay.[/dim]")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Domain", "style": "cyan"},
        {"name": "Provider"},
        {"name": "Host"},
    ]
    
    rows = []
    for domain, profile in profiles.items():
        rows.append([
            domain,
            profile.get("provider", "custom"),
            f"{profile.get('host', 'N/A')}:{profile.get('port', '587')}",
        ])
    
    show_table(f"{len(profiles)} profile(s)", columns, rows, show_header=True)
    press_enter_to_continue()


def add_profile():
    """Add per-domain relay profile."""
    clear_screen()
    show_header()
    show_panel("Add Profile", title="Domain Profiles", style="cyan")
    
    domain = text_input("Sender domain (e.g., @example.com):")
    if not domain:
        return
    
    if not domain.startswith("@"):
        domain = f"@{domain}"
    
    # Select provider
    provider_options = [f"{p['name']}" for p in RELAY_PROVIDERS.values()]
    
    choice = select_from_list("Provider", "Select relay provider:", provider_options)
    if not choice:
        return
    
    # Find provider key
    provider_key = None
    for key, p in RELAY_PROVIDERS.items():
        if p["name"] == choice:
            provider_key = key
            break
    
    provider = RELAY_PROVIDERS[provider_key]
    
    # Get host
    if provider_key == "custom":
        host = text_input("SMTP Host:")
        if not host:
            return
    elif provider_key == "ses":
        region = select_from_list("AWS Region", "Select region:", provider["regions"])
        if not region:
            return
        host = provider["host"].format(region=region)
    else:
        host = provider["host"]
    
    port = text_input("Port:", default=str(provider["port"]))
    
    # Get credentials
    username = text_input("Username:")
    if not username:
        return
    
    from getpass import getpass
    try:
        password = getpass("Password: ")
    except Exception:
        password = text_input("Password:")
    
    if not password:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Save profile
    config = load_email_config()
    if "relay_profiles" not in config:
        config["relay_profiles"] = {}
    
    config["relay_profiles"][domain] = {
        "provider": provider_key,
        "host": host,
        "port": port,
    }
    save_email_config(config)
    
    # Update sender_relay map
    _update_sender_relay_maps(config)
    
    # Add credentials
    relayhost = f"[{host}]:{port}"
    
    with open(POSTFIX_SENDER_RELAY_PASSWD, 'a') as f:
        f.write(f"{relayhost} {username}:{password}\n")
    
    os.chmod(POSTFIX_SENDER_RELAY_PASSWD, 0o600)
    run_command(f"postmap {POSTFIX_SENDER_RELAY_PASSWD}", check=False, silent=True)
    
    # Enable sender-dependent relay
    settings = {
        "sender_dependent_relayhost_maps": f"hash:{POSTFIX_SENDER_RELAY}",
        "smtp_sender_dependent_authentication": "yes",
        "smtp_sasl_password_maps": f"hash:{POSTFIX_SASL_PASSWD}, hash:{POSTFIX_SENDER_RELAY_PASSWD}",
    }
    set_postfix_settings(settings)
    
    reload_postfix()
    
    show_success(f"Profile added for {domain}!")
    press_enter_to_continue()


def remove_profile():
    """Remove per-domain relay profile."""
    clear_screen()
    show_header()
    show_panel("Remove Profile", title="Domain Profiles", style="red")
    
    config = load_email_config()
    profiles = config.get("relay_profiles", {})
    
    if not profiles:
        show_info("No profiles configured.")
        press_enter_to_continue()
        return
    
    domains = list(profiles.keys())
    domain = select_from_list("Select Domain", "Remove profile for:", domains)
    if not domain:
        return
    
    if not confirm_action(f"Remove profile for {domain}?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    del config["relay_profiles"][domain]
    save_email_config(config)
    
    _update_sender_relay_maps(config)
    reload_postfix()
    
    show_success(f"Profile removed for {domain}!")
    press_enter_to_continue()


def _update_sender_relay_maps(config):
    """Update sender_relay map file."""
    profiles = config.get("relay_profiles", {})
    
    with open(POSTFIX_SENDER_RELAY, 'w') as f:
        for domain, profile in profiles.items():
            host = profile.get("host", "")
            port = profile.get("port", "587")
            f.write(f"{domain} [{host}]:{port}\n")
    
    run_command(f"postmap {POSTFIX_SENDER_RELAY}", check=False, silent=True)


def test_relay_connection():
    """Test SMTP relay connection."""
    clear_screen()
    show_header()
    show_panel("Test Connection", title="SMTP Relay", style="cyan")
    
    relayhost = get_postfix_setting("relayhost")
    
    if not relayhost:
        show_warning("No relay configured.")
        press_enter_to_continue()
        return
    
    console.print(f"[bold]Testing connection to:[/bold] {relayhost}")
    console.print()
    
    # Extract host and port
    import re
    match = re.match(r'\[([^\]]+)\]:(\d+)', relayhost)
    if match:
        host, port = match.groups()
    else:
        host = relayhost.replace('[', '').replace(']', '')
        port = "25"
    
    # Test TCP connection
    show_info(f"Connecting to {host}:{port}...")
    
    result = run_command(
        f"timeout 10 bash -c 'echo QUIT | openssl s_client -connect {host}:{port} -starttls smtp 2>&1 | head -20'",
        check=False, silent=True
    )
    
    if "CONNECTED" in result.stdout:
        show_success("Connection successful!")
        console.print()
        console.print("[dim]SMTP handshake output:[/dim]")
        console.print(result.stdout[:500])
    else:
        show_error("Connection failed!")
        console.print()
        if result.stderr:
            console.print(f"[dim]{result.stderr}[/dim]")
    
    # Offer to send test email
    console.print()
    if confirm_action("Send a test email?"):
        recipient = text_input("Recipient email:")
        if recipient and "@" in recipient:
            from utils.shell import get_hostname
            hostname = get_hostname()
            
            result = run_command(
                f'echo "Test email via relay {relayhost}" | mail -s "Relay Test from {hostname}" {recipient}',
                check=False, silent=True
            )
            
            if result.returncode == 0:
                show_success("Test email queued!")
            else:
                show_error("Failed to send test email.")
    
    press_enter_to_continue()


def disable_relay():
    """Disable SMTP relay and use direct send."""
    clear_screen()
    show_header()
    show_panel("Disable Relay", title="SMTP Relay", style="yellow")
    
    relayhost = get_postfix_setting("relayhost")
    
    if not relayhost:
        show_info("Relay is already disabled.")
        press_enter_to_continue()
        return
    
    console.print(f"[bold]Current relay:[/bold] {relayhost}")
    console.print()
    console.print("[yellow]Disabling relay will send emails directly to recipient servers.[/yellow]")
    console.print()
    
    if not confirm_action("Disable relay?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Clear relay settings
    run_command('postconf -e "relayhost="', check=False, silent=True)
    run_command('postconf -X smtp_sasl_auth_enable 2>/dev/null', check=False, silent=True)
    run_command('postconf -X smtp_sasl_password_maps 2>/dev/null', check=False, silent=True)
    run_command('postconf -X sender_dependent_relayhost_maps 2>/dev/null', check=False, silent=True)
    
    # Update config
    config = load_email_config()
    config.pop("default_relay", None)
    save_email_config(config)
    
    reload_postfix()
    
    show_success("Relay disabled!")
    console.print("[dim]Emails will now be sent directly.[/dim]")
    
    press_enter_to_continue()
