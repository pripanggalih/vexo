"""Execution history for vexo cron."""

import os
import json
from datetime import datetime

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
from ui.menu import show_submenu, select_from_list, confirm_action
from utils.shell import require_root

from modules.cron.common import (
    CRON_LOG_DIR,
    get_vexo_jobs,
)


HISTORY_FILE = os.path.join(CRON_LOG_DIR, "history.json")
MAX_HISTORY_PER_JOB = 100


def get_history():
    """Load execution history from file."""
    if not os.path.exists(HISTORY_FILE):
        return {}
    
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_history(history):
    """Save execution history to file."""
    os.makedirs(CRON_LOG_DIR, mode=0o755, exist_ok=True)
    
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
        return True
    except IOError:
        return False


def record_execution(job_name, exit_code, duration_seconds, output_snippet=""):
    """
    Record a job execution in history.
    
    Args:
        job_name: Name of the job
        exit_code: Exit code from command
        duration_seconds: How long the job took
        output_snippet: Last few lines of output
    """
    history = get_history()
    
    if job_name not in history:
        history[job_name] = []
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "exit_code": exit_code,
        "duration_seconds": duration_seconds,
        "output_snippet": output_snippet[:500],  # Limit snippet size
        "status": "success" if exit_code == 0 else "failed",
    }
    
    history[job_name].insert(0, entry)  # Newest first
    
    # Trim old entries
    history[job_name] = history[job_name][:MAX_HISTORY_PER_JOB]
    
    save_history(history)


def history_menu():
    """Display the history submenu."""
    while True:
        clear_screen()
        show_header()
        
        choice = show_submenu(
            title="Execution History",
            options=[
                ("view", "1. View Job History"),
                ("summary", "2. Summary (All Jobs)"),
                ("clear", "3. Clear History"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "view":
            view_job_history()
        elif choice == "summary":
            show_history_summary()
        elif choice == "clear":
            clear_history()
        elif choice == "back" or choice is None:
            break


def view_job_history():
    """View execution history for a specific job."""
    clear_screen()
    show_header()
    show_panel("Job History", title="Execution History", style="cyan")
    
    jobs = get_vexo_jobs()
    
    if not jobs:
        show_info("No vexo-managed cron jobs found.")
        press_enter_to_continue()
        return
    
    history = get_history()
    
    # Show jobs with history count
    options = []
    for job in jobs:
        count = len(history.get(job["name"], []))
        options.append(f"{job['name']} ({count} runs)")
    
    selection = select_from_list(
        title="Select Job",
        message="Select job to view history:",
        options=options
    )
    
    if not selection:
        return
    
    job_name = selection.split(" (")[0]
    
    _show_job_history(job_name)


def _show_job_history(job_name):
    """Display history for a specific job."""
    clear_screen()
    show_header()
    show_panel(f"History: {job_name}", title="Execution History", style="cyan")
    
    history = get_history()
    job_history = history.get(job_name, [])
    
    if not job_history:
        show_info("No execution history for this job.")
        press_enter_to_continue()
        return
    
    # Calculate stats
    total = len(job_history)
    success_count = sum(1 for h in job_history if h["status"] == "success")
    failed_count = total - success_count
    success_rate = (success_count / total * 100) if total > 0 else 0
    
    avg_duration = sum(h["duration_seconds"] for h in job_history) / total if total > 0 else 0
    
    # Display stats
    console.print(f"[bold]Total Runs:[/bold] {total}")
    console.print(f"[bold]Success Rate:[/bold] {success_rate:.1f}% ({success_count}/{total})")
    console.print(f"[bold]Average Duration:[/bold] {avg_duration:.1f}s")
    
    if job_history:
        last_run = job_history[0]
        last_time = datetime.fromisoformat(last_run["timestamp"])
        console.print(f"[bold]Last Run:[/bold] {last_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    console.print()
    
    # Display table
    columns = [
        {"name": "Time", "style": "cyan"},
        {"name": "Duration", "justify": "right"},
        {"name": "Exit", "justify": "center"},
        {"name": "Status", "justify": "center"},
    ]
    
    rows = []
    for entry in job_history[:20]:  # Show last 20
        timestamp = datetime.fromisoformat(entry["timestamp"])
        time_str = timestamp.strftime("%m-%d %H:%M")
        
        duration = f"{entry['duration_seconds']:.1f}s"
        exit_code = str(entry["exit_code"])
        
        if entry["status"] == "success":
            status = "[green]Success[/green]"
        else:
            status = "[red]Failed[/red]"
        
        rows.append([time_str, duration, exit_code, status])
    
    show_table(f"Last {len(rows)} runs", columns, rows)
    
    if len(job_history) > 20:
        console.print(f"[dim]... and {len(job_history) - 20} more runs[/dim]")
    
    # Show last output if failed
    if job_history and job_history[0]["status"] == "failed":
        console.print()
        console.print("[bold red]Last failure output:[/bold red]")
        console.print(f"[dim]{job_history[0].get('output_snippet', 'No output captured')}[/dim]")
    
    press_enter_to_continue()


def show_history_summary():
    """Show summary of all job executions."""
    clear_screen()
    show_header()
    show_panel("History Summary", title="Execution History", style="cyan")
    
    history = get_history()
    jobs = get_vexo_jobs()
    
    if not history:
        show_info("No execution history recorded yet.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Job", "style": "cyan"},
        {"name": "Runs", "justify": "right"},
        {"name": "Success", "justify": "right"},
        {"name": "Failed", "justify": "right"},
        {"name": "Rate", "justify": "right"},
        {"name": "Last Run"},
    ]
    
    rows = []
    for job in jobs:
        job_history = history.get(job["name"], [])
        
        if not job_history:
            rows.append([job["name"], "0", "-", "-", "-", "-"])
            continue
        
        total = len(job_history)
        success = sum(1 for h in job_history if h["status"] == "success")
        failed = total - success
        rate = f"{(success / total * 100):.0f}%"
        
        last_run = datetime.fromisoformat(job_history[0]["timestamp"])
        last_str = last_run.strftime("%m-%d %H:%M")
        
        rate_color = "green" if success == total else "yellow" if success > failed else "red"
        
        rows.append([
            job["name"][:20],
            str(total),
            f"[green]{success}[/green]",
            f"[red]{failed}[/red]" if failed > 0 else "0",
            f"[{rate_color}]{rate}[/{rate_color}]",
            last_str,
        ])
    
    show_table("All Jobs", columns, rows)
    
    press_enter_to_continue()


def clear_history():
    """Clear execution history."""
    clear_screen()
    show_header()
    show_panel("Clear History", title="Execution History", style="cyan")
    
    history = get_history()
    
    if not history:
        show_info("No history to clear.")
        press_enter_to_continue()
        return
    
    total_entries = sum(len(h) for h in history.values())
    
    console.print(f"[yellow]This will delete {total_entries} history entries.[/yellow]")
    
    options = ["Clear all history", "Clear specific job", "Cancel"]
    
    choice = select_from_list(
        title="Clear History",
        message="Select option:",
        options=options
    )
    
    if not choice or choice == "Cancel":
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if choice == "Clear all history":
        if confirm_action("Clear ALL execution history?"):
            if save_history({}):
                show_success("History cleared!")
            else:
                show_error("Failed to clear history.")
    
    elif choice == "Clear specific job":
        jobs = list(history.keys())
        job_name = select_from_list(
            title="Select Job",
            message="Clear history for:",
            options=jobs
        )
        
        if job_name and confirm_action(f"Clear history for '{job_name}'?"):
            del history[job_name]
            if save_history(history):
                show_success(f"History for '{job_name}' cleared!")
            else:
                show_error("Failed to clear history.")
    
    press_enter_to_continue()
