"""Site configuration functions for webserver module."""

import os

from config import NGINX_SITES_AVAILABLE
from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_success, show_error, show_info, press_enter_to_continue,
)
from ui.menu import show_submenu, confirm_action, text_input, select_from_list
from utils.shell import run_command
from modules.webserver.utils import (
    SITE_TYPES, get_site_config, get_configured_domains, get_domain_root,
)
from modules.webserver.domains import generate_site_config
from modules.webserver.nginx import reload_nginx


def _save_site_config(domain, config):
    """Regenerate and save site config."""
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    
    root_path = get_domain_root(domain)
    if root_path is None:
        root_path = ""
    
    nginx_config = generate_site_config(domain, root_path, config)
    
    try:
        with open(config_path, "w") as f:
            f.write(nginx_config)
        
        result = run_command("nginx -t", check=False, silent=True)
        if result.returncode != 0:
            show_error("Nginx config test failed!")
            console.print(f"[dim]{result.stderr}[/dim]")
            return False
        
        reload_nginx(silent=True)
        return True
    except Exception as e:
        show_error(f"Error saving config: {e}")
        return False


def configure_site_menu():
    """Menu to configure an existing site."""
    clear_screen()
    show_header()
    show_panel("Configure Site", title="Domain & Nginx", style="cyan")
    
    domains = get_configured_domains()
    if not domains:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    domain = select_from_list(
        title="Select Domain",
        message="Choose site to configure",
        options=domains
    )
    
    if not domain:
        return
    
    while True:
        clear_screen()
        show_header()
        
        config = get_site_config(domain)
        site_type_label = next((v for k, v in SITE_TYPES if k == config.get("site_type")), "Unknown")
        
        console.print(f"[bold cyan]Configuring: {domain}[/bold cyan]")
        console.print(f"[dim]Type: {site_type_label} | PHP: {config.get('php_version', 'N/A')} | SSL: {'Yes' if config.get('ssl_enabled') else 'No'}[/dim]")
        console.print()
        
        choice = show_submenu(
            title=f"Configure: {domain}",
            options=[
                ("type", "1. Change Site Type"),
                ("php", "2. Change PHP Version"),
                ("ssl", "3. SSL Settings"),
                ("redirect", "4. WWW Redirect"),
                ("performance", "5. Performance (Gzip, Cache)"),
                ("security", "6. Security (Headers, Rate Limit)"),
                ("ip", "7. IP Rules (Whitelist/Blacklist)"),
                ("view", "8. View Current Config"),
                ("edit", "9. Edit Raw Config"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "type":
            configure_site_type(domain, config)
        elif choice == "php":
            configure_php_version(domain, config)
        elif choice == "ssl":
            configure_ssl(domain, config)
        elif choice == "redirect":
            configure_redirect(domain, config)
        elif choice == "performance":
            configure_performance(domain, config)
        elif choice == "security":
            configure_security(domain, config)
        elif choice == "ip":
            configure_ip_rules(domain, config)
        elif choice == "view":
            view_site_config(domain)
        elif choice == "edit":
            edit_raw_config(domain)
        elif choice == "back" or choice is None:
            break


def configure_site_type(domain, config):
    """Change site type."""
    clear_screen()
    show_header()
    
    current = next((v for k, v in SITE_TYPES if k == config.get("site_type")), "Unknown")
    console.print(f"[dim]Current type: {current}[/dim]")
    console.print()
    
    new_type = select_from_list(
        title="Site Type",
        message="Select new site type",
        options=[label for key, label in SITE_TYPES if key != "custom"]
    )
    
    if not new_type:
        return
    
    new_type_key = next((k for k, v in SITE_TYPES if v == new_type), config.get("site_type"))
    
    if new_type_key == config.get("site_type"):
        show_info("Site type unchanged.")
        press_enter_to_continue()
        return
    
    config["site_type"] = new_type_key
    
    if _save_site_config(domain, config):
        show_success(f"Site type changed to {new_type}!")
    
    press_enter_to_continue()


def configure_php_version(domain, config):
    """Change PHP version for site."""
    clear_screen()
    show_header()
    
    if config.get("site_type") not in ["laravel", "wordpress"]:
        show_info("PHP version only applies to Laravel/WordPress sites.")
        press_enter_to_continue()
        return
    
    from modules.runtime import _get_installed_php_versions
    installed = _get_installed_php_versions()
    
    if not installed:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    console.print(f"[dim]Current: PHP {config.get('php_version', '8.3')}[/dim]")
    console.print()
    
    choice = select_from_list(
        title="PHP Version",
        message="Select PHP version",
        options=[f"PHP {v}" for v in installed]
    )
    
    if not choice:
        return
    
    new_version = choice.replace("PHP ", "")
    config["php_version"] = new_version
    
    if _save_site_config(domain, config):
        show_success(f"PHP version changed to {new_version}!")
    
    press_enter_to_continue()


def configure_ssl(domain, config):
    """Configure SSL settings."""
    clear_screen()
    show_header()
    
    current = "Enabled" if config.get("ssl_enabled") else "Disabled"
    console.print(f"[dim]SSL currently: {current}[/dim]")
    console.print()
    
    ssl_enabled = confirm_action("Enable SSL?")
    config["ssl_enabled"] = ssl_enabled
    
    if _save_site_config(domain, config):
        status = "enabled" if ssl_enabled else "disabled"
        show_success(f"SSL {status}!")
    
    press_enter_to_continue()


def configure_redirect(domain, config):
    """Configure www redirect."""
    clear_screen()
    show_header()
    
    current = config.get("www_redirect", "none")
    labels = {"none": "No redirect", "www_to_non": "www → non-www", "non_to_www": "non-www → www"}
    console.print(f"[dim]Current redirect: {labels.get(current, current)}[/dim]")
    console.print()
    
    options = ["No redirect", "www → non-www", "non-www → www"]
    choice = select_from_list(
        title="WWW Redirect",
        message="Select redirect option",
        options=options
    )
    
    if not choice:
        return
    
    if choice == "www → non-www":
        config["www_redirect"] = "www_to_non"
    elif choice == "non-www → www":
        config["www_redirect"] = "non_to_www"
    else:
        config["www_redirect"] = "none"
    
    if _save_site_config(domain, config):
        show_success("Redirect settings updated!")
    
    press_enter_to_continue()


def configure_performance(domain, config):
    """Configure performance options."""
    clear_screen()
    show_header()
    show_panel("Performance Settings", title=domain, style="cyan")
    
    console.print(f"[dim]Gzip: {'On' if config.get('gzip_enabled', True) else 'Off'}[/dim]")
    console.print(f"[dim]Static Cache: {'On' if config.get('cache_static', True) else 'Off'}[/dim]")
    console.print()
    
    config["gzip_enabled"] = confirm_action("Enable Gzip compression?")
    config["cache_static"] = confirm_action("Enable browser caching for static files?")
    
    if _save_site_config(domain, config):
        show_success("Performance settings updated!")
    
    press_enter_to_continue()


def configure_security(domain, config):
    """Configure security options."""
    clear_screen()
    show_header()
    show_panel("Security Settings", title=domain, style="cyan")
    
    console.print(f"[dim]Security Headers: {'On' if config.get('security_headers', True) else 'Off'}[/dim]")
    console.print(f"[dim]Rate Limiting: {'On' if config.get('rate_limit_enabled', False) else 'Off'}[/dim]")
    console.print()
    
    config["security_headers"] = confirm_action("Enable security headers?")
    config["rate_limit_enabled"] = confirm_action("Enable rate limiting?")
    
    if _save_site_config(domain, config):
        show_success("Security settings updated!")
    
    press_enter_to_continue()


def configure_ip_rules(domain, config):
    """Configure IP whitelist/blacklist."""
    clear_screen()
    show_header()
    show_panel("IP Rules", title=domain, style="cyan")
    
    whitelist = config.get("ip_whitelist", [])
    blacklist = config.get("ip_blacklist", [])
    
    console.print(f"[dim]Whitelist: {', '.join(whitelist) if whitelist else 'None'}[/dim]")
    console.print(f"[dim]Blacklist: {', '.join(blacklist) if blacklist else 'None'}[/dim]")
    console.print()
    
    choice = show_submenu(
        title="IP Rules",
        options=[
            ("add_white", "1. Add IP to Whitelist"),
            ("add_black", "2. Add IP to Blacklist"),
            ("clear_white", "3. Clear Whitelist"),
            ("clear_black", "4. Clear Blacklist"),
            ("back", "← Back"),
        ],
    )
    
    if choice == "add_white":
        ip = text_input("Enter IP address:", title="Whitelist")
        if ip:
            config["ip_whitelist"] = whitelist + [ip.strip()]
            if _save_site_config(domain, config):
                show_success(f"Added {ip} to whitelist!")
    elif choice == "add_black":
        ip = text_input("Enter IP address:", title="Blacklist")
        if ip:
            config["ip_blacklist"] = blacklist + [ip.strip()]
            if _save_site_config(domain, config):
                show_success(f"Added {ip} to blacklist!")
    elif choice == "clear_white":
        if confirm_action("Clear whitelist?"):
            config["ip_whitelist"] = []
            if _save_site_config(domain, config):
                show_success("Whitelist cleared!")
    elif choice == "clear_black":
        if confirm_action("Clear blacklist?"):
            config["ip_blacklist"] = []
            if _save_site_config(domain, config):
                show_success("Blacklist cleared!")
    
    if choice and choice != "back":
        press_enter_to_continue()


def view_site_config(domain):
    """View current Nginx config."""
    clear_screen()
    show_header()
    
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    
    if not os.path.exists(config_path):
        show_error("Config file not found.")
        press_enter_to_continue()
        return
    
    with open(config_path, "r") as f:
        content = f.read()
    
    console.print(f"[bold]Config: {config_path}[/bold]")
    console.print()
    console.print(content)
    
    press_enter_to_continue()


def edit_raw_config(domain):
    """Open config in editor."""
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    
    if not os.path.exists(config_path):
        show_error("Config file not found.")
        press_enter_to_continue()
        return
    
    editor = os.environ.get("EDITOR", "nano")
    os.system(f"{editor} {config_path}")
    
    # Test and reload after edit
    result = run_command("nginx -t", check=False, silent=True)
    if result.returncode == 0:
        reload_nginx(silent=True)
        show_success("Config saved and Nginx reloaded!")
    else:
        show_error("Nginx config test failed!")
        console.print(f"[dim]{result.stderr}[/dim]")
    
    press_enter_to_continue()
