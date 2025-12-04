"""Log viewing for vexo cron."""

import os
import subprocess
import time
import re

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_success,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import show_submenu, select_from_list, text_input, confirm_action
from utils.shell import run_command, require_root

from modules.cron.common import (
    CRON_LOG_DIR,
    get_vexo_jobs,
    get_job_log_path,
)


def logs_menu():
    """Display the logs submenu."""
    while True:
        clear_screen()
        show_header()
        
        choice = show_submenu(
            title="Logs",
            options=[
                ("view", "1. View Job Logs"),
                ("tail", "2. Tail Realtime"),
                ("search", "3. Search Logs"),
                ("clear", "4. Clear Logs"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "view":
            view_logs()
        elif choice == "tail":
            tail_logs()
        elif choice == "search":
            search_logs()
        elif choice == "clear":
            clear_logs()
        elif choice == "back" or choice is None:
            break


def _select_job_log():
    """Select a job to view logs for."""
    jobs = get_vexo_jobs()
    
    if not jobs:
        show_info("No vexo-managed cron jobs found.")
        press_enter_to_continue()
        return None
    
    # Check which jobs have logs
    options = []
    for job in jobs:
        log_path = get_job_log_path(job["name"])
        if os.path.exists(log_path):
            size = os.path.getsize(log_path)
            size_str = _format_size(size)
            options.append(f"{job['name']} ({size_str})")
        else:
            options.append(f"{job['name']} (no log)")
    
    selection = select_from_list(
        title="Select Job",
        message="Select job to view logs:",
        options=options
    )
    
    if not selection:
        return None
    
    job_name = selection.split(" (")[0]
    return job_name


def _format_size(bytes_size):
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"


def view_logs():
    """View job logs."""
    clear_screen()
    show_header()
    show_panel("View Logs", title="Cron Logs", style="cyan")
    
    job_name = _select_job_log()
    if not job_name:
        return
    
    log_path = get_job_log_path(job_name)
    
    if not os.path.exists(log_path):
        show_info(f"No log file found for '{job_name}'")
        console.print(f"[dim]Expected: {log_path}[/dim]")
        press_enter_to_continue()
        return
    
    lines = text_input(
        title="Lines",
        message="Number of lines to show:",
        default="50"
    )
    
    try:
        lines = int(lines)
        if lines < 1:
            lines = 50
    except ValueError:
        lines = 50
    
    clear_screen()
    show_header()
    show_panel(f"Logs: {job_name}", title="Cron Logs", style="cyan")
    
    console.print(f"[dim]Showing last {lines} lines of {log_path}[/dim]")
    console.print()
    
    result = run_command(f"tail -{lines} {log_path}", check=False, silent=True)
    
    if result.returncode == 0 and result.stdout:
        for line in result.stdout.strip().split('\n'):
            _print_colored_log_line(line)
    else:
        console.print("[dim]Log is empty or unreadable.[/dim]")
    
    press_enter_to_continue()


def _print_colored_log_line(line):
    """Print log line with color coding."""
    line_lower = line.lower()
    
    if 'error' in line_lower or 'failed' in line_lower or 'exception' in line_lower:
        console.print(f"[red]{line}[/red]")
    elif 'warning' in line_lower or 'warn' in line_lower:
        console.print(f"[yellow]{line}[/yellow]")
    elif 'success' in line_lower or 'completed' in line_lower or 'done' in line_lower:
        console.print(f"[green]{line}[/green]")
    else:
        console.print(f"[dim]{line}[/dim]")


def tail_logs():
    """Tail logs in realtime."""
    clear_screen()
    show_header()
    show_panel("Tail Realtime", title="Cron Logs", style="cyan")
    
    job_name = _select_job_log()
    if not job_name:
        return
    
    log_path = get_job_log_path(job_name)
    
    if not os.path.exists(log_path):
        show_info(f"No log file found for '{job_name}'")
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


def search_logs():
    """Search in job logs."""
    clear_screen()
    show_header()
    show_panel("Search Logs", title="Cron Logs", style="cyan")
    
    job_name = _select_job_log()
    if not job_name:
        return
    
    log_path = get_job_log_path(job_name)
    
    if not os.path.exists(log_path):
        show_info(f"No log file found for '{job_name}'")
        press_enter_to_continue()
        return
    
    query = text_input(
        title="Search",
        message="Enter search term:"
    )
    
    if not query:
        return
    
    clear_screen()
    show_header()
    show_panel(f"Search: '{query}' in {job_name}", title="Cron Logs", style="cyan")
    
    result = run_command(
        f"grep -i '{query}' {log_path} | tail -50",
        check=False,
        silent=True
    )
    
    if result.returncode == 0 and result.stdout:
        lines = result.stdout.strip().split('\n')
        console.print(f"[dim]Found {len(lines)} matches (showing last 50)[/dim]")
        console.print()
        
        for line in lines:
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


def clear_logs():
    """Clear logs for a job."""
    clear_screen()
    show_header()
    show_panel("Clear Logs", title="Cron Logs", style="cyan")
    
    job_name = _select_job_log()
    if not job_name:
        return
    
    log_path = get_job_log_path(job_name)
    
    if not os.path.exists(log_path):
        show_info(f"No log file found for '{job_name}'")
        press_enter_to_continue()
        return
    
    size = os.path.getsize(log_path)
    console.print(f"[yellow]This will delete {_format_size(size)} of logs.[/yellow]")
    
    if not confirm_action(f"Clear logs for '{job_name}'?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    try:
        with open(log_path, 'w') as f:
            f.write('')
        show_success("Logs cleared!")
    except IOError as e:
        show_error(f"Failed to clear logs: {e}")
    
    press_enter_to_continue()
