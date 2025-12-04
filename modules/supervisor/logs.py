"""Log viewing for vexo-cli supervisor."""

import os

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_error,
    show_warning,
    press_enter_to_continue,
)
from ui.menu import select_from_list
from utils.shell import run_command, is_installed

from modules.supervisor.common import SUPERVISOR_LOG_DIR, get_vexo_workers, get_log_path


def view_logs():
    """View worker logs."""
    clear_screen()
    show_header()
    show_panel("View Logs", title="Queue Workers", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    workers = get_vexo_workers()
    
    options = ["supervisord (main)"] + workers
    
    selection = select_from_list(
        title="View Logs",
        message="Select log to view:",
        options=options
    )
    
    if not selection:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if selection == "supervisord (main)":
        log_path = "/var/log/supervisor/supervisord.log"
    else:
        log_path = get_log_path(selection)
    
    if not os.path.exists(log_path):
        show_error(f"Log file not found: {log_path}")
        press_enter_to_continue()
        return
    
    console.print(f"[bold]Last 50 lines of {log_path}:[/bold]")
    console.print()
    
    result = run_command(f"tail -50 {log_path}", check=False, silent=True)
    
    if result.returncode == 0:
        console.print(result.stdout or "[dim]Log is empty[/dim]")
    else:
        show_error("Failed to read log file.")
    
    press_enter_to_continue()
