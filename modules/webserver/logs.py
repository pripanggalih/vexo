"""Log viewer for nginx access and error logs."""

import os

from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_error, show_info, press_enter_to_continue,
)
from ui.menu import text_input, select_from_list, run_menu_loop
from utils.shell import run_command
from modules.webserver.utils import get_configured_domains


NGINX_LOG_DIR = "/var/log/nginx"


def show_logs_menu():
    """Display Log Viewer submenu."""
    options = [
        ("access", "1. View Access Log"),
        ("error", "2. View Error Log"),
        ("search", "3. Search Logs"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "access": view_access_log,
        "error": view_error_log,
        "search": search_logs,
    }
    
    run_menu_loop("Log Viewer", options, handlers)


def _get_log_path(domain, log_type="access"):
    """Get log file path for domain."""
    # Try domain-specific log first
    specific = os.path.join(NGINX_LOG_DIR, f"{domain}.{log_type}.log")
    if os.path.exists(specific):
        return specific
    
    # Fall back to default nginx logs
    default = os.path.join(NGINX_LOG_DIR, f"{log_type}.log")
    if os.path.exists(default):
        return default
    
    return None


def view_access_log():
    """View access log for a domain."""
    clear_screen()
    show_header()
    show_panel("Access Log", title="Log Viewer", style="cyan")
    
    domains = get_configured_domains()
    domains.insert(0, "(All - default nginx log)")
    
    domain = select_from_list("Select Domain", "Choose domain:", domains)
    if not domain:
        return
    
    if domain == "(All - default nginx log)":
        log_path = os.path.join(NGINX_LOG_DIR, "access.log")
    else:
        log_path = _get_log_path(domain, "access")
    
    if not log_path or not os.path.exists(log_path):
        show_error("Log file not found.")
        press_enter_to_continue()
        return
    
    console.print(f"[dim]Log: {log_path}[/dim]")
    console.print(f"[dim]Showing last 50 lines (Ctrl+C to exit)[/dim]")
    console.print()
    
    result = run_command(f"tail -n 50 {log_path}", check=False, silent=True)
    if result.returncode == 0:
        console.print(result.stdout)
    else:
        show_error("Failed to read log file.")
    
    press_enter_to_continue()


def view_error_log():
    """View error log for a domain."""
    clear_screen()
    show_header()
    show_panel("Error Log", title="Log Viewer", style="cyan")
    
    domains = get_configured_domains()
    domains.insert(0, "(All - default nginx log)")
    
    domain = select_from_list("Select Domain", "Choose domain:", domains)
    if not domain:
        return
    
    if domain == "(All - default nginx log)":
        log_path = os.path.join(NGINX_LOG_DIR, "error.log")
    else:
        log_path = _get_log_path(domain, "error")
    
    if not log_path or not os.path.exists(log_path):
        show_error("Log file not found.")
        press_enter_to_continue()
        return
    
    console.print(f"[dim]Log: {log_path}[/dim]")
    console.print(f"[dim]Showing last 50 lines[/dim]")
    console.print()
    
    result = run_command(f"tail -n 50 {log_path}", check=False, silent=True)
    if result.returncode == 0:
        # Highlight error levels
        for line in result.stdout.split('\n'):
            if 'error' in line.lower() or 'crit' in line.lower():
                console.print(f"[red]{line}[/red]")
            elif 'warn' in line.lower():
                console.print(f"[yellow]{line}[/yellow]")
            else:
                console.print(line)
    else:
        show_error("Failed to read log file.")
    
    press_enter_to_continue()


def search_logs():
    """Search logs for a pattern."""
    clear_screen()
    show_header()
    show_panel("Search Logs", title="Log Viewer", style="cyan")
    
    pattern = text_input("Enter search pattern (IP, URL, status code):")
    if not pattern:
        return
    
    domains = get_configured_domains()
    domains.insert(0, "(All - default nginx logs)")
    
    domain = select_from_list("Select Domain", "Choose domain:", domains)
    if not domain:
        return
    
    if domain == "(All - default nginx logs)":
        access_log = os.path.join(NGINX_LOG_DIR, "access.log")
        error_log = os.path.join(NGINX_LOG_DIR, "error.log")
    else:
        access_log = _get_log_path(domain, "access")
        error_log = _get_log_path(domain, "error")
    
    console.print()
    console.print(f"[bold]Searching for: {pattern}[/bold]")
    console.print()
    
    found = False
    
    if access_log and os.path.exists(access_log):
        result = run_command(f"grep -i '{pattern}' {access_log} | tail -n 20", check=False, silent=True)
        if result.returncode == 0 and result.stdout.strip():
            console.print("[cyan]Access Log:[/cyan]")
            console.print(result.stdout)
            found = True
    
    if error_log and os.path.exists(error_log):
        result = run_command(f"grep -i '{pattern}' {error_log} | tail -n 20", check=False, silent=True)
        if result.returncode == 0 and result.stdout.strip():
            console.print()
            console.print("[cyan]Error Log:[/cyan]")
            console.print(result.stdout)
            found = True
    
    if not found:
        show_info("No matches found.")
    
    press_enter_to_continue()
