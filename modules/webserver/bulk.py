"""Bulk operations for domains."""

import os

from config import NGINX_SITES_AVAILABLE, NGINX_SITES_ENABLED
from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, run_menu_loop
from utils.shell import run_command, require_root
from modules.webserver.utils import get_configured_domains, is_domain_enabled
from modules.webserver.nginx import reload_nginx

try:
    from InquirerPy import inquirer
    from InquirerPy.base.control import Choice
    HAS_INQUIRER = True
except ImportError:
    HAS_INQUIRER = False


def show_bulk_menu():
    """Display Bulk Operations submenu."""
    options = [
        ("enable", "1. Enable Multiple Domains"),
        ("disable", "2. Disable Multiple Domains"),
        ("remove", "3. Remove Multiple Domains"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "enable": bulk_enable,
        "disable": bulk_disable,
        "remove": bulk_remove,
    }
    
    run_menu_loop("Bulk Operations", options, handlers)


def _select_multiple(message, options):
    """Select multiple items using checkbox."""
    if not HAS_INQUIRER or not options:
        return []
    
    choices = [Choice(value=opt, name=opt) for opt in options]
    
    try:
        result = inquirer.checkbox(
            message=message,
            choices=choices,
            cycle=True,
        ).execute()
        return result or []
    except KeyboardInterrupt:
        return []


def bulk_enable():
    """Enable multiple disabled domains."""
    clear_screen()
    show_header()
    show_panel("Enable Multiple Domains", title="Bulk Operations", style="cyan")
    
    domains = get_configured_domains()
    disabled = [d for d in domains if not is_domain_enabled(d)]
    
    if not disabled:
        show_info("No disabled domains found.")
        press_enter_to_continue()
        return
    
    selected = _select_multiple("Select domains to enable:", disabled)
    
    if not selected:
        show_warning("No domains selected.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success_count = 0
    for domain in selected:
        source = os.path.join(NGINX_SITES_AVAILABLE, domain)
        target = os.path.join(NGINX_SITES_ENABLED, domain)
        
        try:
            if os.path.islink(target):
                os.remove(target)
            os.symlink(source, target)
            success_count += 1
            console.print(f"[green]✓[/green] Enabled: {domain}")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed: {domain} - {e}")
    
    # Test and reload
    result = run_command("nginx -t", check=False, silent=True)
    if result.returncode == 0:
        reload_nginx(silent=True)
        show_success(f"Enabled {success_count} domain(s)!")
    else:
        show_error("Nginx config test failed!")
        console.print(f"[dim]{result.stderr}[/dim]")
    
    press_enter_to_continue()


def bulk_disable():
    """Disable multiple enabled domains."""
    clear_screen()
    show_header()
    show_panel("Disable Multiple Domains", title="Bulk Operations", style="cyan")
    
    domains = get_configured_domains()
    enabled = [d for d in domains if is_domain_enabled(d)]
    
    if not enabled:
        show_info("No enabled domains found.")
        press_enter_to_continue()
        return
    
    show_warning("Disabled sites will be inaccessible!")
    console.print()
    
    selected = _select_multiple("Select domains to disable:", enabled)
    
    if not selected:
        show_warning("No domains selected.")
        press_enter_to_continue()
        return
    
    if not confirm_action(f"Disable {len(selected)} domain(s)?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success_count = 0
    for domain in selected:
        target = os.path.join(NGINX_SITES_ENABLED, domain)
        
        try:
            if os.path.islink(target):
                os.remove(target)
                success_count += 1
                console.print(f"[yellow]○[/yellow] Disabled: {domain}")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed: {domain} - {e}")
    
    reload_nginx(silent=True)
    show_success(f"Disabled {success_count} domain(s)!")
    press_enter_to_continue()


def bulk_remove():
    """Remove multiple domains."""
    clear_screen()
    show_header()
    show_panel("Remove Multiple Domains", title="Bulk Operations", style="red")
    
    domains = get_configured_domains()
    
    if not domains:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    show_warning("This will DELETE domain configurations!")
    console.print()
    
    selected = _select_multiple("Select domains to REMOVE:", domains)
    
    if not selected:
        show_warning("No domains selected.")
        press_enter_to_continue()
        return
    
    # Double confirmation
    console.print()
    console.print(f"[bold red]Type 'DELETE' to confirm removal of {len(selected)} domain(s):[/bold red]")
    confirm_text = text_input("Confirm:")
    
    if confirm_text != "DELETE":
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success_count = 0
    for domain in selected:
        try:
            # Remove from sites-enabled
            enabled_path = os.path.join(NGINX_SITES_ENABLED, domain)
            if os.path.islink(enabled_path):
                os.remove(enabled_path)
            
            # Remove from sites-available
            available_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
            if os.path.exists(available_path):
                os.remove(available_path)
            
            success_count += 1
            console.print(f"[red]✗[/red] Removed: {domain}")
        except Exception as e:
            console.print(f"[red]![/red] Failed: {domain} - {e}")
    
    reload_nginx(silent=True)
    show_success(f"Removed {success_count} domain(s)!")
    press_enter_to_continue()
