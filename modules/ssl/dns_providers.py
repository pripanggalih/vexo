"""DNS provider configuration for DNS-01 challenge."""

import os
import json
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
from utils.shell import run_command, require_root, is_installed
from utils.sanitize import escape_shell
from modules.ssl.common import (
    get_certbot_status_text,
    ensure_config_dir,
    VEXO_SSL_DNS,
)


# DNS Provider configurations
DNS_PROVIDERS = {
    "cloudflare": {
        "name": "Cloudflare",
        "certbot_plugin": "dns-cloudflare",
        "package": "python3-certbot-dns-cloudflare",
        "credentials_file": f"{VEXO_SSL_DNS}/cloudflare.ini",
        "credentials_template": """# Cloudflare API credentials
# Use API Token (recommended) or Global API Key

# Option 1: API Token (recommended - scoped permissions)
dns_cloudflare_api_token = {api_token}

# Option 2: Global API Key (full account access)
# dns_cloudflare_email = {email}
# dns_cloudflare_api_key = {api_key}
""",
        "required_fields": ["api_token"],
        "test_command": "curl -s -X GET 'https://api.cloudflare.com/client/v4/user/tokens/verify' -H 'Authorization: Bearer {api_token}'"
    },
    "digitalocean": {
        "name": "DigitalOcean",
        "certbot_plugin": "dns-digitalocean",
        "package": "python3-certbot-dns-digitalocean",
        "credentials_file": f"{VEXO_SSL_DNS}/digitalocean.ini",
        "credentials_template": """# DigitalOcean API credentials
dns_digitalocean_token = {api_token}
""",
        "required_fields": ["api_token"],
        "test_command": "curl -s -X GET 'https://api.digitalocean.com/v2/account' -H 'Authorization: Bearer {api_token}'"
    },
    "route53": {
        "name": "AWS Route53",
        "certbot_plugin": "dns-route53",
        "package": "python3-certbot-dns-route53",
        "credentials_file": f"{VEXO_SSL_DNS}/route53.ini",
        "credentials_template": """# AWS Route53 credentials
[default]
aws_access_key_id = {access_key}
aws_secret_access_key = {secret_key}
""",
        "required_fields": ["access_key", "secret_key"],
        "env_vars": {
            "AWS_ACCESS_KEY_ID": "{access_key}",
            "AWS_SECRET_ACCESS_KEY": "{secret_key}"
        }
    },
    "google": {
        "name": "Google Cloud DNS",
        "certbot_plugin": "dns-google",
        "package": "python3-certbot-dns-google",
        "credentials_file": f"{VEXO_SSL_DNS}/google.json",
        "is_json": True,
        "required_fields": ["service_account_json"],
    }
}


def show_dns_menu():
    """Display DNS providers submenu."""
    def get_status():
        configured = _count_configured_providers()
        return f"Configured: {configured} providers"
    
    options = [
        ("list", "1. List Configured Providers"),
        ("cloudflare", "2. Configure Cloudflare"),
        ("digitalocean", "3. Configure DigitalOcean"),
        ("route53", "4. Configure Route53"),
        ("google", "5. Configure Google Cloud DNS"),
        ("test", "6. Test DNS API"),
        ("remove", "7. Remove Provider"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "list": list_providers,
        "cloudflare": lambda: configure_provider("cloudflare"),
        "digitalocean": lambda: configure_provider("digitalocean"),
        "route53": lambda: configure_provider("route53"),
        "google": lambda: configure_provider("google"),
        "test": test_provider,
        "remove": remove_provider,
    }
    
    run_menu_loop("DNS Providers", options, handlers, get_status)


def _count_configured_providers():
    """Count how many providers are configured."""
    count = 0
    for provider_key, provider in DNS_PROVIDERS.items():
        if os.path.exists(provider["credentials_file"]):
            count += 1
    return count


def get_configured_provider(domain=None):
    """
    Get configured DNS provider for a domain.
    Returns provider config dict or None.
    """
    for provider_key, provider in DNS_PROVIDERS.items():
        if os.path.exists(provider["credentials_file"]):
            return {
                "key": provider_key,
                "name": provider["name"],
                "certbot_plugin": provider["certbot_plugin"],
                "credentials_file": provider["credentials_file"]
            }
    return None


def list_providers():
    """List all configured DNS providers."""
    clear_screen()
    show_header()
    show_panel("Configured DNS Providers", title="DNS Providers", style="cyan")
    
    columns = [
        {"name": "Provider", "style": "cyan"},
        {"name": "Status", "justify": "center"},
        {"name": "Plugin"},
    ]
    
    rows = []
    for provider_key, provider in DNS_PROVIDERS.items():
        if os.path.exists(provider["credentials_file"]):
            status = "[green]Configured[/green]"
        else:
            status = "[dim]Not configured[/dim]"
        
        plugin_installed = is_installed(provider["package"].replace("python3-", ""))
        plugin_status = provider["certbot_plugin"]
        if not plugin_installed:
            plugin_status += " [dim](not installed)[/dim]"
        
        rows.append([provider["name"], status, plugin_status])
    
    show_table("", columns, rows)
    
    press_enter_to_continue()


def configure_provider(provider_key):
    """Configure a DNS provider."""
    provider = DNS_PROVIDERS.get(provider_key)
    if not provider:
        show_error(f"Unknown provider: {provider_key}")
        press_enter_to_continue()
        return
    
    clear_screen()
    show_header()
    show_panel(f"Configure {provider['name']}", title="DNS Providers", style="cyan")
    
    if os.path.exists(provider["credentials_file"]):
        show_info(f"{provider['name']} is already configured.")
        if not confirm_action("Reconfigure?"):
            press_enter_to_continue()
            return
    
    if not _check_install_plugin(provider):
        press_enter_to_continue()
        return
    
    credentials = {}
    
    if provider_key == "cloudflare":
        console.print("[bold]Cloudflare API Credentials[/bold]")
        console.print()
        console.print("Get your API Token from: https://dash.cloudflare.com/profile/api-tokens")
        console.print("[dim]Required permissions: Zone:DNS:Edit, Zone:Zone:Read[/dim]")
        console.print()
        
        api_token = text_input(
            title="API Token",
            message="Enter Cloudflare API Token:"
        )
        
        if not api_token:
            show_warning("Cancelled.")
            press_enter_to_continue()
            return
        
        credentials["api_token"] = api_token
    
    elif provider_key == "digitalocean":
        console.print("[bold]DigitalOcean API Token[/bold]")
        console.print()
        console.print("Get your token from: https://cloud.digitalocean.com/api/tokens")
        console.print("[dim]Required scope: Read & Write[/dim]")
        console.print()
        
        api_token = text_input(
            title="API Token",
            message="Enter DigitalOcean API Token:"
        )
        
        if not api_token:
            show_warning("Cancelled.")
            press_enter_to_continue()
            return
        
        credentials["api_token"] = api_token
    
    elif provider_key == "route53":
        console.print("[bold]AWS Route53 Credentials[/bold]")
        console.print()
        console.print("Create IAM user with Route53 permissions.")
        console.print("[dim]Required: route53:GetChange, route53:ChangeResourceRecordSets, route53:ListHostedZones[/dim]")
        console.print()
        
        access_key = text_input(
            title="Access Key",
            message="AWS Access Key ID:"
        )
        
        if not access_key:
            show_warning("Cancelled.")
            press_enter_to_continue()
            return
        
        secret_key = text_input(
            title="Secret Key",
            message="AWS Secret Access Key:"
        )
        
        if not secret_key:
            show_warning("Cancelled.")
            press_enter_to_continue()
            return
        
        credentials["access_key"] = access_key
        credentials["secret_key"] = secret_key
    
    elif provider_key == "google":
        console.print("[bold]Google Cloud DNS Credentials[/bold]")
        console.print()
        console.print("Create a service account with DNS Admin role.")
        console.print("Download the JSON key file.")
        console.print()
        
        json_path = text_input(
            title="JSON Key",
            message="Path to service account JSON file:"
        )
        
        if not json_path or not os.path.exists(json_path):
            show_error("JSON file not found.")
            press_enter_to_continue()
            return
        
        credentials["service_account_json"] = json_path
    
    console.print()
    if confirm_action("Test API connection?"):
        if not _test_api(provider_key, credentials):
            if not confirm_action("Connection test failed. Save anyway?"):
                press_enter_to_continue()
                return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if _save_credentials(provider_key, credentials):
        show_success(f"{provider['name']} configured successfully!")
    else:
        show_error("Failed to save credentials.")
    
    press_enter_to_continue()


def _check_install_plugin(provider):
    """Check if certbot plugin is installed, offer to install."""
    package = provider["package"]
    
    result = run_command(f"dpkg -l | grep {package}", check=False, silent=True)
    
    if result.returncode != 0:
        show_warning(f"Certbot plugin not installed: {package}")
        
        if confirm_action(f"Install {package}?"):
            try:
                require_root()
            except PermissionError:
                return False
            
            from utils.shell import run_command_realtime
            returncode = run_command_realtime(
                f"apt install -y {package}",
                "Installing certbot plugin..."
            )
            
            if returncode != 0:
                show_error("Failed to install plugin.")
                return False
            
            show_success("Plugin installed!")
        else:
            return False
    
    return True


def _test_api(provider_key, credentials):
    """Test API connection for a provider."""
    provider = DNS_PROVIDERS[provider_key]
    
    show_info("Testing API connection...")
    
    if provider_key == "cloudflare":
        # Escape API token to prevent command injection
        safe_token = escape_shell(credentials.get("api_token", ""))
        # Build command manually with escaped token (don't use format with user input)
        cmd = f"curl -s -X GET 'https://api.cloudflare.com/client/v4/user/tokens/verify' -H 'Authorization: Bearer '{safe_token}"
        result = run_command(cmd, check=False, silent=True)
        
        if result.returncode == 0 and '"success":true' in result.stdout:
            console.print("[green]✓[/green] API connection successful!")
            return True
        else:
            console.print("[red]✗[/red] API connection failed")
            return False
    
    elif provider_key == "digitalocean":
        # Escape API token to prevent command injection
        safe_token = escape_shell(credentials.get("api_token", ""))
        cmd = f"curl -s -X GET 'https://api.digitalocean.com/v2/account' -H 'Authorization: Bearer '{safe_token}"
        result = run_command(cmd, check=False, silent=True)
        
        if result.returncode == 0 and '"account"' in result.stdout:
            console.print("[green]✓[/green] API connection successful!")
            return True
        else:
            console.print("[red]✗[/red] API connection failed")
            return False
    
    elif provider_key == "route53":
        console.print("[yellow]![/yellow] AWS API test requires AWS CLI. Skipping...")
        return True
    
    elif provider_key == "google":
        try:
            with open(credentials["service_account_json"], "r") as f:
                data = json.load(f)
                if "type" in data and data["type"] == "service_account":
                    console.print("[green]✓[/green] Valid service account JSON!")
                    return True
        except Exception:
            pass
        console.print("[red]✗[/red] Invalid service account JSON")
        return False
    
    return True


def _save_credentials(provider_key, credentials):
    """Save provider credentials to file."""
    provider = DNS_PROVIDERS[provider_key]
    ensure_config_dir()
    
    os.makedirs(VEXO_SSL_DNS, exist_ok=True)
    
    try:
        if provider_key == "google":
            shutil.copy2(
                credentials["service_account_json"],
                provider["credentials_file"]
            )
        else:
            template = provider["credentials_template"]
            content = template.format(**credentials)
            
            with open(provider["credentials_file"], "w") as f:
                f.write(content)
        
        os.chmod(provider["credentials_file"], 0o600)
        
        return True
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False


def test_provider():
    """Test a configured DNS provider."""
    clear_screen()
    show_header()
    show_panel("Test DNS Provider", title="DNS Providers", style="cyan")
    
    configured = []
    for provider_key, provider in DNS_PROVIDERS.items():
        if os.path.exists(provider["credentials_file"]):
            configured.append((provider_key, provider["name"]))
    
    if not configured:
        show_info("No DNS providers configured.")
        press_enter_to_continue()
        return
    
    options = [name for _, name in configured]
    
    choice = select_from_list(
        title="Provider",
        message="Select provider to test:",
        options=options
    )
    
    if not choice:
        press_enter_to_continue()
        return
    
    provider_key = None
    for key, name in configured:
        if name == choice:
            provider_key = key
            break
    
    if not provider_key:
        press_enter_to_continue()
        return
    
    provider = DNS_PROVIDERS[provider_key]
    
    show_info(f"Testing {provider['name']}...")
    
    result = run_command(
        f"certbot plugins --{provider['certbot_plugin']} 2>/dev/null | head -5",
        check=False,
        silent=True
    )
    
    if provider["certbot_plugin"] in result.stdout:
        console.print(f"[green]✓[/green] {provider['name']} plugin is available")
    else:
        console.print(f"[yellow]![/yellow] Plugin check inconclusive")
    
    console.print(f"[green]✓[/green] Credentials file exists: {provider['credentials_file']}")
    
    press_enter_to_continue()


def remove_provider():
    """Remove a configured DNS provider."""
    clear_screen()
    show_header()
    show_panel("Remove DNS Provider", title="DNS Providers", style="cyan")
    
    configured = []
    for provider_key, provider in DNS_PROVIDERS.items():
        if os.path.exists(provider["credentials_file"]):
            configured.append((provider_key, provider["name"]))
    
    if not configured:
        show_info("No DNS providers configured.")
        press_enter_to_continue()
        return
    
    options = [name for _, name in configured]
    
    choice = select_from_list(
        title="Provider",
        message="Select provider to remove:",
        options=options
    )
    
    if not choice:
        press_enter_to_continue()
        return
    
    provider_key = None
    for key, name in configured:
        if name == choice:
            provider_key = key
            break
    
    provider = DNS_PROVIDERS[provider_key]
    
    if not confirm_action(f"Remove {provider['name']} configuration?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    try:
        os.remove(provider["credentials_file"])
        show_success(f"{provider['name']} configuration removed!")
    except Exception as e:
        show_error(f"Failed to remove: {e}")
    
    press_enter_to_continue()
