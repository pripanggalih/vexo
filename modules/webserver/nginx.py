"""Nginx installation and service management."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action
from utils.shell import (
    run_command, run_command_with_progress, is_installed,
    is_service_running, service_control, require_root,
)
from modules.webserver.utils import get_configured_domains


def install_nginx():
    """Install Nginx web server."""
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
    
    result = run_command_with_progress("apt install -y nginx", "Installing Nginx...")
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
        show_warning("Nginx installed but may not be running.")
    
    press_enter_to_continue()


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
    
    domains = get_configured_domains()
    rows.append(["Domains Configured", str(len(domains))])
    
    show_table("", columns, rows, show_header=False)
    
    if not config_ok:
        console.print()
        show_error("Configuration test failed:")
        console.print(f"[dim]{result.stderr}[/dim]")
    
    press_enter_to_continue()


def test_and_reload():
    """Test nginx config and reload if valid."""
    clear_screen()
    show_header()
    show_panel("Test & Reload Nginx", title="Domain & Nginx", style="cyan")
    
    show_info("Testing Nginx configuration...")
    console.print()
    
    result = run_command("nginx -t 2>&1", check=False, silent=True)
    
    if result.returncode != 0:
        show_error("Configuration test FAILED!")
        console.print()
        console.print(f"[red]{result.stderr}[/red]")
        press_enter_to_continue()
        return False
    
    show_success("Configuration test passed!")
    console.print()
    
    if not confirm_action("Reload Nginx now?"):
        press_enter_to_continue()
        return True
    
    success = service_control("nginx", "reload")
    
    if success:
        show_success("Nginx reloaded successfully!")
    else:
        show_error("Failed to reload Nginx.")
    
    press_enter_to_continue()
    return success


def reload_nginx(silent=False):
    """Reload Nginx configuration."""
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
