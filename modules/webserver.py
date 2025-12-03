"""Domain & Nginx management module for vexo-cli."""

import os
import re

from config import (
    NGINX_SITES_AVAILABLE,
    NGINX_SITES_ENABLED,
    DEFAULT_WEB_ROOT,
    TEMPLATES_DIR,
)
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
from ui.menu import show_submenu, confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import (
    run_command,
    run_command_with_progress,
    is_installed,
    is_service_running,
    service_control,
    require_root,
)


# Site type presets
SITE_TYPES = [
    ("laravel", "Laravel/PHP Application"),
    ("wordpress", "WordPress"),
    ("static", "Static HTML"),
    ("spa", "SPA (React/Vue/Angular)"),
    ("nodejs", "Node.js/Proxy"),
    ("custom", "Custom Configuration"),
]

# Default site configuration
DEFAULT_SITE_CONFIG = {
    "site_type": "laravel",
    "php_version": "8.3",
    "ssl_enabled": False,
    "www_redirect": "none",  # none, www_to_non, non_to_www
    "gzip_enabled": True,
    "cache_static": True,
    "security_headers": True,
    "rate_limit_enabled": False,
    "rate_limit_requests": 10,
    "ip_whitelist": [],
    "ip_blacklist": [],
    "proxy_port": 3000,
}


def _get_site_config(domain):
    """
    Read site configuration from Nginx config file comments.
    Returns DEFAULT_SITE_CONFIG merged with saved values.
    """
    import json
    config = DEFAULT_SITE_CONFIG.copy()
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    
    if not os.path.exists(config_path):
        return config
    
    try:
        with open(config_path, "r") as f:
            content = f.read()
        
        # Parse config from header comment: # VEXO_CONFIG: {"key": "value", ...}
        match = re.search(r'# VEXO_CONFIG: ({.*})', content)
        if match:
            saved = json.loads(match.group(1))
            config.update(saved)
    except Exception:
        pass
    
    return config


def _domain_to_safe_name(domain):
    """Convert domain to safe variable name for nginx."""
    return domain.replace(".", "_").replace("-", "_")


def generate_site_config(domain, root_path, config):
    """
    Generate Nginx config from template and options.
    
    Args:
        domain: Domain name
        root_path: Document root path
        config: Site configuration dict
    
    Returns:
        str: Generated Nginx configuration
    """
    import json
    
    site_type = config.get("site_type", "laravel")
    template_path = os.path.join(TEMPLATES_DIR, "nginx", f"{site_type}.conf")
    
    # Fallback to laravel if template not found
    if not os.path.exists(template_path):
        template_path = os.path.join(TEMPLATES_DIR, "nginx", "laravel.conf")
    
    with open(template_path, "r") as f:
        template = f.read()
    
    snippets_dir = os.path.join(TEMPLATES_DIR, "nginx", "snippets")
    
    # Basic replacements
    output = template.replace("{{domain}}", domain)
    output = output.replace("{{root_path}}", root_path)
    output = output.replace("{{domain_safe}}", _domain_to_safe_name(domain))
    
    # WWW alias
    www_redirect = config.get("www_redirect", "none")
    if www_redirect == "none":
        output = output.replace("{{www_alias}}", f" www.{domain}")
    else:
        output = output.replace("{{www_alias}}", "")
    
    # SSL config
    if config.get("ssl_enabled", False):
        ssl_path = os.path.join(snippets_dir, "ssl.conf")
        if os.path.exists(ssl_path):
            with open(ssl_path, "r") as f:
                ssl_snippet = f.read().replace("{{domain}}", domain)
            output = output.replace("{{ssl_listen}}", "")
            output = output.replace("{{ssl_config}}", ssl_snippet)
        else:
            output = output.replace("{{ssl_listen}}", "")
            output = output.replace("{{ssl_config}}", "")
    else:
        output = output.replace("{{ssl_listen}}", "")
        output = output.replace("{{ssl_config}}", "")
    
    # Redirect config
    redirect_config = ""
    if www_redirect == "www_to_non":
        redirect_config = f"""
    if ($host = www.{domain}) {{
        return 301 $scheme://{domain}$request_uri;
    }}"""
    elif www_redirect == "non_to_www":
        redirect_config = f"""
    if ($host = {domain}) {{
        return 301 $scheme://www.{domain}$request_uri;
    }}"""
    output = output.replace("{{redirect_config}}", redirect_config)
    
    # Gzip
    if config.get("gzip_enabled", True):
        gzip_path = os.path.join(snippets_dir, "gzip.conf")
        if os.path.exists(gzip_path):
            with open(gzip_path, "r") as f:
                output = output.replace("{{gzip_config}}", f.read())
        else:
            output = output.replace("{{gzip_config}}", "")
    else:
        output = output.replace("{{gzip_config}}", "")
    
    # Security headers
    if config.get("security_headers", True):
        sec_path = os.path.join(snippets_dir, "security-headers.conf")
        if os.path.exists(sec_path):
            with open(sec_path, "r") as f:
                output = output.replace("{{security_headers}}", f.read())
        else:
            output = output.replace("{{security_headers}}", "")
    else:
        output = output.replace("{{security_headers}}", "")
    
    # Rate limiting
    if config.get("rate_limit_enabled", False):
        rate_path = os.path.join(snippets_dir, "rate-limit.conf")
        if os.path.exists(rate_path):
            with open(rate_path, "r") as f:
                rate_limit = f.read()
                rate_limit = rate_limit.replace("{{domain_safe}}", _domain_to_safe_name(domain))
            output = output.replace("{{rate_limit_config}}", rate_limit)
        else:
            output = output.replace("{{rate_limit_config}}", "")
    else:
        output = output.replace("{{rate_limit_config}}", "")
    
    # IP rules
    ip_rules = ""
    for ip in config.get("ip_whitelist", []):
        ip_rules += f"    allow {ip};\n"
    if config.get("ip_whitelist"):
        ip_rules += "    deny all;\n"
    for ip in config.get("ip_blacklist", []):
        ip_rules += f"    deny {ip};\n"
    output = output.replace("{{ip_rules}}", ip_rules)
    
    # PHP-FPM config
    php_version = config.get("php_version", "8.3")
    if site_type in ["laravel", "wordpress"]:
        php_path = os.path.join(snippets_dir, "php-fpm.conf")
        if os.path.exists(php_path):
            with open(php_path, "r") as f:
                php_config = f.read().replace("{{php_version}}", php_version)
            output = output.replace("{{php_fpm_config}}", php_config)
        else:
            output = output.replace("{{php_fpm_config}}", "")
    else:
        output = output.replace("{{php_fpm_config}}", "")
    
    # Static cache
    if config.get("cache_static", True):
        cache_path = os.path.join(snippets_dir, "cache-static.conf")
        if os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                output = output.replace("{{cache_static_config}}", f.read())
        else:
            output = output.replace("{{cache_static_config}}", "")
    else:
        output = output.replace("{{cache_static_config}}", "")
    
    # Proxy port for Node.js
    proxy_port = config.get("proxy_port", 3000)
    output = output.replace("{{proxy_port}}", str(proxy_port))
    
    # Add config header for future reads
    config_json = json.dumps(config)
    header = f"# VEXO_CONFIG: {config_json}\n"
    output = header + output
    
    return output


def show_menu():
    """Display the Domain & Nginx submenu."""
    def get_status():
        if not is_installed("nginx"):
            return "Nginx Status: [yellow]Not installed[/yellow]"
        if is_service_running("nginx"):
            return "Nginx Status: [green]Running[/green]"
        return "Nginx Status: [red]Not running[/red]"
    
    def get_options():
        options = []
        if is_installed("nginx"):
            options.extend([
                ("list", "1. List Domains"),
                ("add", "2. Add New Domain"),
                ("configure", "3. Configure Site"),
                ("remove", "4. Remove Domain"),
                ("reload", "5. Reload Nginx"),
                ("status", "6. Nginx Status"),
            ])
        else:
            options.append(("install", "1. Install Nginx"))
        options.append(("back", "← Back to Main Menu"))
        return options
    
    handlers = {
        "list": list_domains,
        "add": add_domain_interactive,
        "configure": configure_site_menu,
        "remove": remove_domain_interactive,
        "install": install_nginx,
        "reload": reload_nginx,
        "status": show_nginx_status,
    }
    
    run_menu_loop("Domain & Nginx Management", get_options, handlers, get_status)


def install_nginx():
    """
    Install Nginx web server.
    
    Idempotent - checks if already installed.
    """
    clear_screen()
    show_header()
    show_panel("Install Nginx", title="Domain & Nginx", style="cyan")
    
    if is_installed("nginx"):
        show_info("Nginx is already installed.")
        
        if not confirm_action("Do you want to reinstall Nginx?"):
            press_enter_to_continue()
            return
    
    if not confirm_action("Install Nginx web server?"):
        show_warning("Installation cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print()
    show_info("Installing Nginx...")
    
    result = run_command_with_progress("apt update", "Updating package lists...")
    if result.returncode != 0:
        show_error("Failed to update package lists.")
        press_enter_to_continue()
        return
    
    result = run_command_with_progress(
        "apt install -y nginx",
        "Installing Nginx..."
    )
    
    if result.returncode != 0:
        show_error("Failed to install Nginx.")
        press_enter_to_continue()
        return
    
    service_control("nginx", "start")
    service_control("nginx", "enable")
    
    console.print()
    if is_service_running("nginx"):
        show_success("Nginx installed and running!")
    else:
        show_warning("Nginx installed but may not be running. Check status.")
    
    press_enter_to_continue()


def add_domain_interactive():
    """Interactive wizard to add a new domain with site type selection."""
    clear_screen()
    show_header()
    show_panel("Add New Domain", title="Domain & Nginx", style="cyan")
    
    if not is_installed("nginx"):
        show_error("Nginx is not installed. Please install it first.")
        press_enter_to_continue()
        return
    
    # Step 1: Domain name
    domain = text_input(
        "Enter domain name (e.g., example.com):",
        title="Add Domain"
    )
    
    if not domain:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    domain = domain.strip().lower()
    if not _is_valid_domain(domain):
        show_error(f"Invalid domain name: {domain}")
        press_enter_to_continue()
        return
    
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    if os.path.exists(config_path):
        show_error(f"Domain {domain} already exists.")
        press_enter_to_continue()
        return
    
    # Step 2: Site type
    console.print()
    site_type = select_from_list(
        title="Site Type",
        message="Select site type",
        options=[label for _, label in SITE_TYPES if _ != "custom"]
    )
    
    if not site_type:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Map label back to key
    site_type_key = next((k for k, v in SITE_TYPES if v == site_type), "laravel")
    
    # Step 3: Root path or proxy port
    if site_type_key == "nodejs":
        root_path = ""
        proxy_port = text_input(
            "Enter application port:",
            title="Proxy Port",
            default="3000"
        )
        if not proxy_port:
            show_warning("Cancelled.")
            press_enter_to_continue()
            return
        try:
            proxy_port = int(proxy_port)
        except ValueError:
            show_error("Invalid port number.")
            press_enter_to_continue()
            return
    else:
        default_root = os.path.join(DEFAULT_WEB_ROOT, domain, "public")
        if site_type_key in ["static", "spa"]:
            default_root = os.path.join(DEFAULT_WEB_ROOT, domain, "dist")
        
        root_path = text_input(
            "Enter document root path:",
            title="Document Root",
            default=default_root
        )
        
        if not root_path:
            show_warning("Cancelled.")
            press_enter_to_continue()
            return
        proxy_port = 3000
    
    # Step 4: PHP version (only for PHP sites)
    php_version = "8.3"
    if site_type_key in ["laravel", "wordpress"]:
        from modules.runtime import _get_installed_php_versions
        installed_php = _get_installed_php_versions()
        if installed_php:
            console.print()
            php_choice = select_from_list(
                title="PHP Version",
                message="Select PHP version",
                options=[f"PHP {v}" for v in installed_php]
            )
            if php_choice:
                php_version = php_choice.replace("PHP ", "")
    
    # Step 5: Quick options
    console.print()
    ssl_enabled = confirm_action("Enable SSL? (requires existing certificate)")
    
    www_options = ["No redirect", "www → non-www", "non-www → www"]
    www_choice = select_from_list(
        title="WWW Redirect",
        message="Configure www redirect",
        options=www_options
    )
    www_redirect = "none"
    if www_choice == "www → non-www":
        www_redirect = "www_to_non"
    elif www_choice == "non-www → www":
        www_redirect = "non_to_www"
    
    # Step 6: Advanced options (optional)
    gzip_enabled = True
    cache_static = True
    security_headers = True
    rate_limit_enabled = False
    
    console.print()
    if confirm_action("Configure advanced options?"):
        gzip_enabled = confirm_action("Enable Gzip compression?")
        cache_static = confirm_action("Enable browser caching for static files?")
        security_headers = confirm_action("Enable security headers?")
        rate_limit_enabled = confirm_action("Enable rate limiting?")
    
    # Build config
    config = {
        "site_type": site_type_key,
        "php_version": php_version,
        "ssl_enabled": ssl_enabled,
        "www_redirect": www_redirect,
        "gzip_enabled": gzip_enabled,
        "cache_static": cache_static,
        "security_headers": security_headers,
        "rate_limit_enabled": rate_limit_enabled,
        "proxy_port": proxy_port,
        "ip_whitelist": [],
        "ip_blacklist": [],
    }
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Create document root if needed
    if root_path and not os.path.exists(root_path):
        os.makedirs(root_path, exist_ok=True)
        if site_type_key in ["static", "spa"]:
            index_path = os.path.join(root_path, "index.html")
            with open(index_path, "w") as f:
                f.write(f"<!DOCTYPE html>\n<html><body><h1>Welcome to {domain}</h1></body></html>\n")
    
    # Generate and save config
    nginx_config = generate_site_config(domain, root_path, config)
    
    try:
        with open(config_path, "w") as f:
            f.write(nginx_config)
        
        if enable_domain(domain):
            show_success(f"Domain {domain} added successfully!")
            console.print()
            console.print(f"[dim]Type: {site_type}[/dim]")
            console.print(f"[dim]Config: {config_path}[/dim]")
            if root_path:
                console.print(f"[dim]Root: {root_path}[/dim]")
        else:
            show_error(f"Failed to enable domain {domain}")
    except Exception as e:
        show_error(f"Error: {e}")
    
    press_enter_to_continue()


def add_domain(domain, root_path):
    """
    Add a new domain configuration.
    
    Args:
        domain: Domain name (e.g., example.com)
        root_path: Document root path
    
    Returns:
        bool: True if successful
    """
    try:
        template_path = os.path.join(TEMPLATES_DIR, "nginx_vhost.conf")
        with open(template_path, "r") as f:
            template = f.read()
        
        config = template.replace("{{domain}}", domain)
        config = config.replace("{{root_path}}", root_path)
        
        if not os.path.exists(root_path):
            os.makedirs(root_path, exist_ok=True)
            index_path = os.path.join(root_path, "index.html")
            with open(index_path, "w") as f:
                f.write(f"<html><body><h1>Welcome to {domain}</h1></body></html>\n")
        
        config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
        with open(config_path, "w") as f:
            f.write(config)
        
        return enable_domain(domain)
    
    except Exception as e:
        show_error(f"Error adding domain: {e}")
        return False


def enable_domain(domain):
    """
    Enable a domain by creating symlink and reloading Nginx.
    
    Args:
        domain: Domain name
    
    Returns:
        bool: True if successful
    """
    try:
        source = os.path.join(NGINX_SITES_AVAILABLE, domain)
        target = os.path.join(NGINX_SITES_ENABLED, domain)
        
        if not os.path.exists(source):
            show_error(f"Config not found: {source}")
            return False
        
        if os.path.islink(target):
            os.remove(target)
        
        os.symlink(source, target)
        
        result = run_command("nginx -t", check=False, silent=True)
        if result.returncode != 0:
            show_error("Nginx configuration test failed!")
            console.print(f"[dim]{result.stderr}[/dim]")
            os.remove(target)
            return False
        
        return reload_nginx(silent=True)
    
    except Exception as e:
        show_error(f"Error enabling domain: {e}")
        return False


def list_domains():
    """Display a table of configured domains."""
    clear_screen()
    show_header()
    show_panel("Configured Domains", title="Domain & Nginx", style="cyan")
    
    domains = _get_configured_domains()
    
    if not domains:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Domain", "style": "cyan"},
        {"name": "Type", "style": "white"},
        {"name": "Enabled", "justify": "center"},
        {"name": "SSL", "justify": "center"},
    ]
    
    rows = []
    for domain in domains:
        enabled = _is_domain_enabled(domain)
        enabled_str = "[green]✓[/green]" if enabled else "[red]✗[/red]"
        
        config = _get_site_config(domain)
        site_type = config.get("site_type", "unknown")
        site_type_label = next((v for k, v in SITE_TYPES if k == site_type), site_type)
        ssl = "[green]✓[/green]" if config.get("ssl_enabled") else "[dim]-[/dim]"
        
        rows.append([domain, site_type_label, enabled_str, ssl])
    
    show_table(f"Total: {len(domains)} domain(s)", columns, rows)
    
    press_enter_to_continue()


def remove_domain_interactive():
    """Interactive prompt to remove a domain."""
    clear_screen()
    show_header()
    show_panel("Remove Domain", title="Domain & Nginx", style="cyan")
    
    domains = _get_configured_domains()
    
    if not domains:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    domain = select_from_list(
        title="Remove Domain",
        message="Select domain to remove:",
        options=domains
    )
    
    if not domain:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not confirm_action(f"Are you sure you want to remove {domain}?\nThis will delete the Nginx config but NOT the files."):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = remove_domain(domain)
    
    if success:
        show_success(f"Domain {domain} removed successfully!")
    else:
        show_error(f"Failed to remove domain {domain}")
    
    press_enter_to_continue()


def remove_domain(domain):
    """
    Remove a domain configuration.
    
    Args:
        domain: Domain name
    
    Returns:
        bool: True if successful
    """
    try:
        enabled_path = os.path.join(NGINX_SITES_ENABLED, domain)
        if os.path.islink(enabled_path):
            os.remove(enabled_path)
        
        available_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
        if os.path.exists(available_path):
            os.remove(available_path)
        
        return reload_nginx(silent=True)
    
    except Exception as e:
        show_error(f"Error removing domain: {e}")
        return False


def reload_nginx(silent=False):
    """
    Reload Nginx configuration.
    
    Args:
        silent: If True, don't show messages
    
    Returns:
        bool: True if successful
    """
    try:
        result = run_command("nginx -t", check=False, silent=True)
        if result.returncode != 0:
            if not silent:
                show_error("Nginx configuration test failed!")
                console.print(f"[dim]{result.stderr}[/dim]")
            return False
        
        success = service_control("nginx", "reload")
        
        if not silent:
            if success:
                show_success("Nginx reloaded successfully!")
            else:
                show_error("Failed to reload Nginx.")
            press_enter_to_continue()
        
        return success
    
    except Exception as e:
        if not silent:
            show_error(f"Error reloading Nginx: {e}")
            press_enter_to_continue()
        return False


def show_nginx_status():
    """Display Nginx service status."""
    clear_screen()
    show_header()
    show_panel("Nginx Status", title="Domain & Nginx", style="cyan")
    
    if not is_installed("nginx"):
        show_warning("Nginx is not installed.")
        press_enter_to_continue()
        return
    
    running = is_service_running("nginx")
    
    columns = [
        {"name": "Property", "style": "cyan"},
        {"name": "Value"},
    ]
    
    rows = [
        ["Installed", "[green]Yes[/green]"],
        ["Running", "[green]Yes[/green]" if running else "[red]No[/red]"],
    ]
    
    result = run_command("nginx -v 2>&1", check=False, silent=True)
    if result.returncode == 0:
        version = result.stderr.strip() if result.stderr else result.stdout.strip()
        rows.append(["Version", version.replace("nginx version: ", "")])
    
    result = run_command("nginx -t 2>&1", check=False, silent=True)
    config_ok = result.returncode == 0
    rows.append(["Config Valid", "[green]Yes[/green]" if config_ok else "[red]No[/red]"])
    
    domains = _get_configured_domains()
    rows.append(["Domains Configured", str(len(domains))])
    
    show_table("", columns, rows, show_header=False)
    
    if not config_ok:
        console.print()
        show_error("Configuration test failed:")
        console.print(f"[dim]{result.stderr}[/dim]")
    
    press_enter_to_continue()


def _is_valid_domain(domain):
    """Check if domain name is valid."""
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$'
    return bool(re.match(pattern, domain))


def _get_configured_domains():
    """Get list of configured domains from sites-available."""
    try:
        if not os.path.exists(NGINX_SITES_AVAILABLE):
            return []
        
        domains = []
        for name in os.listdir(NGINX_SITES_AVAILABLE):
            if name in ["default", "default.conf", ".DS_Store"]:
                continue
            path = os.path.join(NGINX_SITES_AVAILABLE, name)
            if os.path.isfile(path):
                domains.append(name)
        
        return sorted(domains)
    except Exception:
        return []


def _is_domain_enabled(domain):
    """Check if domain is enabled (has symlink in sites-enabled)."""
    enabled_path = os.path.join(NGINX_SITES_ENABLED, domain)
    return os.path.islink(enabled_path)


def _get_domain_root(domain):
    """Get document root from domain config."""
    try:
        config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
        with open(config_path, "r") as f:
            for line in f:
                if "root " in line:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        return parts[1].rstrip(";")
        return "Unknown"
    except Exception:
        return "Unknown"


# =============================================================================
# Configure Site Functions
# =============================================================================

def configure_site_menu():
    """Menu to configure an existing site."""
    clear_screen()
    show_header()
    show_panel("Configure Site", title="Domain & Nginx", style="cyan")
    
    domains = _get_configured_domains()
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
        
        config = _get_site_config(domain)
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


def _save_site_config(domain, config):
    """Regenerate and save site config."""
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    
    # Get root path from existing config
    root_path = _get_domain_root(domain)
    if root_path == "Unknown":
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
