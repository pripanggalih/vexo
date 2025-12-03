"""Clone domain configuration."""

import os

from config import NGINX_SITES_AVAILABLE, DEFAULT_WEB_ROOT
from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list
from utils.shell import require_root
from modules.webserver.utils import get_configured_domains, is_valid_domain, get_site_config
from modules.webserver.domains import enable_domain


def clone_domain():
    """Clone a domain configuration to a new domain."""
    clear_screen()
    show_header()
    show_panel("Clone Domain", title="Domain & Nginx", style="cyan")
    
    domains = get_configured_domains()
    if not domains:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    # Select source domain
    source = select_from_list("Source Domain", "Choose domain to clone:", domains)
    if not source:
        return
    
    # Enter new domain name
    console.print()
    new_domain = text_input("Enter new domain name:")
    if not new_domain:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    new_domain = new_domain.strip().lower()
    
    if not is_valid_domain(new_domain):
        show_error(f"Invalid domain name: {new_domain}")
        press_enter_to_continue()
        return
    
    if new_domain in domains:
        show_error(f"Domain {new_domain} already exists.")
        press_enter_to_continue()
        return
    
    # Options
    console.print()
    create_dir = confirm_action("Create directory structure?")
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Read source config
    source_path = os.path.join(NGINX_SITES_AVAILABLE, source)
    try:
        with open(source_path, "r") as f:
            config_content = f.read()
    except Exception as e:
        show_error(f"Failed to read source config: {e}")
        press_enter_to_continue()
        return
    
    # Replace domain name in config
    new_config = config_content.replace(source, new_domain)
    
    # Update root path if present
    old_root = os.path.join(DEFAULT_WEB_ROOT, source)
    new_root = os.path.join(DEFAULT_WEB_ROOT, new_domain)
    new_config = new_config.replace(old_root, new_root)
    
    # Write new config
    new_path = os.path.join(NGINX_SITES_AVAILABLE, new_domain)
    try:
        with open(new_path, "w") as f:
            f.write(new_config)
    except Exception as e:
        show_error(f"Failed to write config: {e}")
        press_enter_to_continue()
        return
    
    # Create directory if requested
    if create_dir:
        config = get_site_config(source)
        if config.get("site_type") in ["static", "spa"]:
            new_doc_root = os.path.join(new_root, "dist")
        else:
            new_doc_root = os.path.join(new_root, "public")
        
        os.makedirs(new_doc_root, exist_ok=True)
        
        # Create placeholder index
        index_path = os.path.join(new_doc_root, "index.html")
        try:
            with open(index_path, "w") as f:
                f.write(f"<!DOCTYPE html>\n<html><body><h1>Welcome to {new_domain}</h1></body></html>\n")
        except Exception as e:
            show_warning(f"Could not create index file: {e}")
        
        show_success(f"Created: {new_doc_root}")
    
    # Enable domain
    if enable_domain(new_domain):
        show_success(f"Domain {new_domain} cloned from {source}!")
        console.print()
        show_warning("SSL certificate not copied - run certbot for new domain.")
    else:
        show_error("Failed to enable domain.")
    
    press_enter_to_continue()
