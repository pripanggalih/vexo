"""Domain management functions for webserver module."""

import os
import json

from config import (
    NGINX_SITES_AVAILABLE,
    NGINX_SITES_ENABLED,
    DEFAULT_WEB_ROOT,
    TEMPLATES_DIR,
)
from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list
from utils.shell import (
from utils.error_handler import handle_error
    run_command, is_installed, service_control, require_root,
)
from modules.webserver.utils import (
    SITE_TYPES, DEFAULT_SITE_CONFIG, get_site_config, get_configured_domains,
    is_domain_enabled, domain_to_safe_name, is_valid_domain,
)


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
    output = output.replace("{{domain_safe}}", domain_to_safe_name(domain))
    
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
                rate_limit = rate_limit.replace("{{domain_safe}}", domain_to_safe_name(domain))
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


def add_domain_interactive():
    """Interactive wizard to add a new domain with site type selection."""
    clear_screen()
    show_header()
    show_panel("Add New Domain", title="Domain & Nginx", style="cyan")
    
    if not is_installed("nginx"):
        handle_error("E2002", "Nginx is not installed. Please install it first.")
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
    if not is_valid_domain(domain):
        handle_error("E2002", f"Invalid domain name: {domain}")
        press_enter_to_continue()
        return
    
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    if os.path.exists(config_path):
        handle_error("E2002", f"Domain {domain} already exists.")
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
            handle_error("E2002", "Invalid port number.")
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
        from modules.runtime.php.utils import get_installed_php_versions
        installed_php = get_installed_php_versions()
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
            handle_error("E2002", f"Failed to enable domain {domain}")
    except Exception as e:
        handle_error("E2002", f"Error: {e}")
    
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
        handle_error("E2002", f"Error adding domain: {e}")
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
            handle_error("E2002", f"Config not found: {source}")
            return False
        
        if os.path.islink(target):
            os.remove(target)
        
        os.symlink(source, target)
        
        result = run_command("nginx -t", check=False, silent=True)
        if result.returncode != 0:
            handle_error("E2002", "Nginx configuration test failed!")
            console.print(f"[dim]{result.stderr}[/dim]")
            os.remove(target)
            return False
        
        from modules.webserver.nginx import reload_nginx
        return reload_nginx(silent=True)
    
    except Exception as e:
        handle_error("E2002", f"Error enabling domain: {e}")
        return False


def disable_domain(domain):
    """
    Disable a domain by removing symlink.
    
    Args:
        domain: Domain name
    
    Returns:
        bool: True if successful
    """
    try:
        target = os.path.join(NGINX_SITES_ENABLED, domain)
        
        if os.path.islink(target):
            os.remove(target)
        
        from modules.webserver.nginx import reload_nginx
        return reload_nginx(silent=True)
    
    except Exception as e:
        handle_error("E2002", f"Error disabling domain: {e}")
        return False


def list_domains():
    """Display a table of configured domains."""
    clear_screen()
    show_header()
    show_panel("Configured Domains", title="Domain & Nginx", style="cyan")
    
    domains = get_configured_domains()
    
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
        enabled = is_domain_enabled(domain)
        enabled_str = "[green]✓[/green]" if enabled else "[red]✗[/red]"
        
        config = get_site_config(domain)
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
    
    domains = get_configured_domains()
    
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
        handle_error("E2002", f"Failed to remove domain {domain}")
    
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
        
        from modules.webserver.nginx import reload_nginx
        return reload_nginx(silent=True)
    
    except Exception as e:
        handle_error("E2002", f"Error removing domain: {e}")
        return False
