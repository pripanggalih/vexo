"""Advanced log viewing for vexo supervisor."""

import os
import re
import subprocess
import time

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
from ui.menu import run_menu_loop, select_from_list, text_input, confirm_action
from utils.shell import run_command, is_installed

from modules.supervisor.common import (
    SUPERVISOR_LOG_DIR,
    get_vexo_workers,
    get_log_path,
    get_config_path,
    parse_worker_config,
)


def show_menu():
    """Display the logs submenu."""
    options = [
        ("view", "1. View Logs"),
        ("tail", "2. Tail Realtime"),
        ("filter", "3. Filter by Level"),
        ("search", "4. Search Logs"),
        ("settings", "5. Log Settings"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "view": view_logs,
        "tail": tail_logs,
        "filter": filter_logs,
        "search": search_logs,
        "settings": log_settings,
    }
    
    run_menu_loop("Logs", options, handlers)


def _select_log_file():
    """Helper to select a log file."""
    workers = get_vexo_workers()
    options = ["supervisord (main)"] + workers
    
    selection = select_from_list(
        title="Select Log",
        message="Select log to view:",
        options=options
    )
    
    if not selection:
        return None
    
    if selection == "supervisord (main)":
        return "/var/log/supervisor/supervisord.log"
    else:
        return get_log_path(selection)


def view_logs():
    """View worker logs with pagination."""
    clear_screen()
    show_header()
    show_panel("View Logs", title="Logs", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    log_path = _select_log_file()
    if not log_path:
        return
    
    if not os.path.exists(log_path):
        show_error(f"Log file not found: {log_path}")
        press_enter_to_continue()
        return
    
    # Ask for number of lines
    lines = text_input(
        title="Lines",
        message="Number of lines to show:",
        default="100"
    )
    
    try:
        lines = int(lines)
        if lines < 1:
            lines = 100
    except ValueError:
        lines = 100
    
    clear_screen()
    show_header()
    show_panel(f"Log: {os.path.basename(log_path)}", title="Logs", style="cyan")
    
    console.print(f"[dim]Showing last {lines} lines of {log_path}[/dim]")
    console.print()
    
    result = run_command(f"tail -{lines} {log_path}", check=False, silent=True)
    
    if result.returncode == 0 and result.stdout:
        # Color code log lines
        for line in result.stdout.strip().split('\n'):
            _print_colored_log_line(line)
    else:
        console.print("[dim]Log is empty or unreadable.[/dim]")
    
    press_enter_to_continue()


def _print_colored_log_line(line):
    """Print a log line with color coding based on content."""
    line_lower = line.lower()
    
    if 'error' in line_lower or 'exception' in line_lower or 'failed' in line_lower:
        console.print(f"[red]{line}[/red]")
    elif 'warning' in line_lower or 'warn' in line_lower:
        console.print(f"[yellow]{line}[/yellow]")
    elif 'success' in line_lower or 'processed' in line_lower or 'completed' in line_lower:
        console.print(f"[green]{line}[/green]")
    elif 'info' in line_lower or 'processing' in line_lower:
        console.print(f"[dim]{line}[/dim]")
    else:
        console.print(line)


def tail_logs():
    """Tail logs in realtime."""
    clear_screen()
    show_header()
    show_panel("Tail Realtime", title="Logs", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    log_path = _select_log_file()
    if not log_path:
        return
    
    if not os.path.exists(log_path):
        show_error(f"Log file not found: {log_path}")
        press_enter_to_continue()
        return
    
    clear_screen()
    console.print(f"[bold cyan]Tailing: {log_path}[/bold cyan]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    console.print()
    
    process = None
    try:
        process = subprocess.Popen(
            ["tail", "-f", log_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        
        for line in process.stdout:
            _print_colored_log_line(line.rstrip())
    
    except KeyboardInterrupt:
        if process:
            process.terminate()
        console.print("\n[dim]Tail stopped.[/dim]")
        time.sleep(1)
    except Exception as e:
        show_error(f"Failed to tail log: {e}")
        press_enter_to_continue()


def filter_logs():
    """Filter logs by level."""
    clear_screen()
    show_header()
    show_panel("Filter by Level", title="Logs", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    log_path = _select_log_file()
    if not log_path:
        return
    
    if not os.path.exists(log_path):
        show_error(f"Log file not found: {log_path}")
        press_enter_to_continue()
        return
    
    # Select filter level
    level = select_from_list(
        title="Filter Level",
        message="Show logs containing:",
        options=[
            "ERROR / Exception / Failed",
            "WARNING / Warn",
            "INFO / Processing",
            "All levels",
        ]
    )
    
    if not level:
        return
    
    # Build grep pattern
    if "ERROR" in level:
        pattern = r"error|exception|failed|fatal"
    elif "WARNING" in level:
        pattern = r"warning|warn"
    elif "INFO" in level:
        pattern = r"info|processing|processed"
    else:
        pattern = None
    
    clear_screen()
    show_header()
    show_panel(f"Filtered: {level}", title="Logs", style="cyan")
    
    if pattern:
        result = run_command(
            f"grep -iE '{pattern}' {log_path} | tail -100",
            check=False,
            silent=True
        )
    else:
        result = run_command(f"tail -100 {log_path}", check=False, silent=True)
    
    if result.returncode == 0 and result.stdout:
        lines = result.stdout.strip().split('\n')
        console.print(f"[dim]Found {len(lines)} matching lines (showing last 100)[/dim]")
        console.print()
        
        for line in lines:
            _print_colored_log_line(line)
    else:
        console.print("[dim]No matching log entries found.[/dim]")
    
    press_enter_to_continue()


def search_logs():
    """Search logs by keyword."""
    clear_screen()
    show_header()
    show_panel("Search Logs", title="Logs", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    log_path = _select_log_file()
    if not log_path:
        return
    
    if not os.path.exists(log_path):
        show_error(f"Log file not found: {log_path}")
        press_enter_to_continue()
        return
    
    # Get search query
    query = text_input(
        title="Search",
        message="Enter search term:"
    )
    
    if not query:
        return
    
    clear_screen()
    show_header()
    show_panel(f"Search: '{query}'", title="Logs", style="cyan")
    
    # Search with grep (case insensitive)
    result = run_command(
        f"grep -i '{query}' {log_path} | tail -100",
        check=False,
        silent=True
    )
    
    if result.returncode == 0 and result.stdout:
        lines = result.stdout.strip().split('\n')
        console.print(f"[dim]Found {len(lines)} matches (showing last 100)[/dim]")
        console.print()
        
        for line in lines:
            # Highlight search term
            highlighted = re.sub(
                f'({re.escape(query)})',
                r'[bold yellow]\1[/bold yellow]',
                line,
                flags=re.IGNORECASE
            )
            console.print(highlighted)
    else:
        console.print(f"[dim]No matches found for '{query}'.[/dim]")
    
    press_enter_to_continue()


def log_settings():
    """Configure log settings for workers."""
    clear_screen()
    show_header()
    show_panel("Log Settings", title="Logs", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    workers = get_vexo_workers()
    
    if not workers:
        show_info("No workers configured.")
        press_enter_to_continue()
        return
    
    worker = select_from_list(
        title="Log Settings",
        message="Select worker:",
        options=workers
    )
    
    if not worker:
        return
    
    _show_log_settings(worker)


def _show_log_settings(worker_name):
    """Show and edit log settings for a worker."""
    clear_screen()
    show_header()
    show_panel(f"Log Settings: {worker_name}", title="Logs", style="cyan")
    
    config = parse_worker_config(worker_name)
    if not config:
        show_error("Failed to parse worker config.")
        press_enter_to_continue()
        return
    
    log_path = get_log_path(worker_name)
    
    # Get current log size
    log_size = 0
    if os.path.exists(log_path):
        log_size = os.path.getsize(log_path) / (1024 * 1024)  # MB
    
    # Display current settings
    console.print(f"[bold]Log File:[/bold] {log_path}")
    console.print(f"[bold]Current Size:[/bold] {log_size:.2f} MB")
    console.print(f"[bold]Max Size:[/bold] {config.get('stdout_logfile_maxbytes', '50MB')}")
    console.print(f"[bold]Backups:[/bold] {config.get('stdout_logfile_backups', 5)}")
    console.print()
    
    options = [
        ("maxsize", "1. Change Max Size"),
        ("backups", "2. Change Backups"),
        ("clear", "3. Clear Log"),
        ("back", "← Back"),
    ]
    
    choice = select_from_list(
        title="Log Settings",
        message="Select option:",
        options=[label for _, label in options]
    )
    
    if not choice or choice == "← Back":
        return
    
    if choice == "1. Change Max Size":
        _change_log_maxsize(worker_name)
    elif choice == "2. Change Backups":
        _change_log_backups(worker_name)
    elif choice == "3. Clear Log":
        _clear_log(worker_name)


def _change_log_maxsize(worker_name):
    """Change log max size setting."""
    new_size = text_input(
        title="Max Size",
        message="Enter max log size (e.g., 50MB, 100MB):",
        default="50MB"
    )
    
    if not new_size:
        return
    
    # Validate format
    if not re.match(r'^\d+[MK]B$', new_size.upper()):
        show_error("Invalid format. Use format like 50MB or 100MB.")
        press_enter_to_continue()
        return
    
    _update_config_setting(worker_name, 'stdout_logfile_maxbytes', new_size.upper())


def _change_log_backups(worker_name):
    """Change number of log backups."""
    new_backups = text_input(
        title="Backups",
        message="Enter number of backup files to keep:",
        default="5"
    )
    
    if not new_backups:
        return
    
    try:
        backups = int(new_backups)
        if backups < 0:
            raise ValueError()
    except ValueError:
        show_error("Invalid number.")
        press_enter_to_continue()
        return
    
    _update_config_setting(worker_name, 'stdout_logfile_backups', str(backups))


def _update_config_setting(worker_name, key, value):
    """Update a config setting and reload."""
    from utils.shell import require_root
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    config_path = get_config_path(worker_name)
    
    try:
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Update or add setting
        if f'{key}=' in content:
            content = re.sub(f'{key}=.*', f'{key}={value}', content)
        else:
            # Add before last line
            content = content.rstrip() + f'\n{key}={value}\n'
        
        with open(config_path, 'w') as f:
            f.write(content)
        
        # Reload
        run_command("supervisorctl reread", check=False, silent=True)
        run_command(f"supervisorctl update {worker_name}", check=False, silent=True)
        
        show_success(f"Setting {key} updated to {value}")
    
    except IOError as e:
        show_error(f"Failed to update config: {e}")
    
    press_enter_to_continue()


def _clear_log(worker_name):
    """Clear worker log file."""
    log_path = get_log_path(worker_name)
    
    if not os.path.exists(log_path):
        show_info("Log file does not exist.")
        press_enter_to_continue()
        return
    
    log_size = os.path.getsize(log_path) / (1024 * 1024)
    
    console.print(f"[yellow]This will delete {log_size:.2f} MB of logs.[/yellow]")
    
    if not confirm_action(f"Clear log for '{worker_name}'?"):
        show_info("Cancelled.")
        press_enter_to_continue()
        return
    
    from utils.shell import require_root
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    try:
        # Truncate log file
        with open(log_path, 'w') as f:
            f.write('')
        show_success("Log cleared!")
    except IOError as e:
        show_error(f"Failed to clear log: {e}")
    
    press_enter_to_continue()
