# Phase 5: Logs & Execution History

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add per-job log viewing with tail/search capabilities and execution history tracking with wrapper script.

**Architecture:** Create logs.py module for log viewing and history.py for execution tracking. Create vexo-cron-wrapper script that wraps job commands to capture exit codes, duration, and output snippets into a JSON history file.

**Tech Stack:** Python, subprocess, json

**Prerequisite:** Complete Phase 1 (cron package structure)

---

## Task 1: Create Logs Module

**Files:**
- Create: `modules/cron/logs.py`

**Step 1: Create logs.py with log viewing functions**

```python
"""Log viewing for vexo cron."""

import os
import subprocess
import time

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
        
        import re
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
```

**Step 2: Commit**

```bash
git add modules/cron/logs.py
git commit -m "feat(cron): add log viewing with tail, search, clear"
```

---

## Task 2: Create History Module

**Files:**
- Create: `modules/cron/history.py`

**Step 1: Create history.py with execution tracking**

```python
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
from ui.menu import select_from_list, confirm_action
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
        
        from ui.menu import show_submenu
        
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
            status = "[green]● Success[/green]"
        else:
            status = "[red]● Failed[/red]"
        
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
```

**Step 2: Commit**

```bash
git add modules/cron/history.py
git commit -m "feat(cron): add execution history tracking"
```

---

## Task 3: Create Wrapper Script

**Files:**
- Create: `scripts/vexo-cron-wrapper`

**Step 1: Create wrapper script**

```bash
#!/bin/bash
# vexo-cron-wrapper - Wrapper script for tracking cron job execution
# Usage: vexo-cron-wrapper "job-name" "command to run"

JOB_NAME="$1"
COMMAND="$2"

LOG_DIR="/var/log/vexo/cron"
HISTORY_FILE="$LOG_DIR/history.json"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Record start time
START_TIME=$(date +%s)
START_ISO=$(date -Iseconds)

# Run the command and capture output
OUTPUT=$(eval "$COMMAND" 2>&1)
EXIT_CODE=$?

# Record end time
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Get last 500 chars of output for snippet
OUTPUT_SNIPPET=$(echo "$OUTPUT" | tail -c 500)

# Escape JSON special characters
OUTPUT_SNIPPET=$(echo "$OUTPUT_SNIPPET" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | tr '\n' ' ')

# Determine status
if [ $EXIT_CODE -eq 0 ]; then
    STATUS="success"
else
    STATUS="failed"
fi

# Create history entry
ENTRY=$(cat <<EOF
{
  "timestamp": "$START_ISO",
  "exit_code": $EXIT_CODE,
  "duration_seconds": $DURATION,
  "output_snippet": "$OUTPUT_SNIPPET",
  "status": "$STATUS"
}
EOF
)

# Update history file (using Python for JSON manipulation)
python3 << PYTHON
import json
import os

history_file = "$HISTORY_FILE"
job_name = "$JOB_NAME"
max_entries = 100

# Load existing history
history = {}
if os.path.exists(history_file):
    try:
        with open(history_file, 'r') as f:
            history = json.load(f)
    except:
        pass

# Add new entry
if job_name not in history:
    history[job_name] = []

entry = json.loads('''$ENTRY''')
history[job_name].insert(0, entry)
history[job_name] = history[job_name][:max_entries]

# Save
with open(history_file, 'w') as f:
    json.dump(history, f, indent=2)
PYTHON

exit $EXIT_CODE
```

**Step 2: Make executable**

```bash
chmod +x scripts/vexo-cron-wrapper
```

**Step 3: Commit**

```bash
git add scripts/vexo-cron-wrapper
git commit -m "feat(cron): add wrapper script for execution tracking"
```

---

## Task 4: Update Package Init with Logs/History Menu

**Files:**
- Modify: `modules/cron/__init__.py`

**Step 1: Add logs and history to menu**

Add imports:
```python
from modules.cron.logs import logs_menu
from modules.cron.history import history_menu
```

Update show_menu:
```python
def show_menu():
    """Display the Cron Management submenu."""
    options = [
        ("manage", "1. Job Management"),
        ("control", "2. Job Control"),
        ("logs", "3. Logs & History"),
        ("backup", "4. Backup & Restore"),
        ("status", "5. Show Status"),
        ("back", "← Back to Main Menu"),
    ]
    
    handlers = {
        "manage": job_management_menu,
        "control": job_control_menu,
        "logs": logs_history_menu,
        "backup": backup_restore_menu,
        "status": show_status,
    }
    
    run_menu_loop("Cron Jobs", options, handlers, lambda: "Cron Jobs Manager")


def logs_history_menu():
    """Submenu for logs and history."""
    from ui.components import clear_screen, show_header
    from ui.menu import show_submenu
    
    while True:
        clear_screen()
        show_header()
        
        choice = show_submenu(
            title="Logs & History",
            options=[
                ("logs", "1. View Logs"),
                ("history", "2. Execution History"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "logs":
            logs_menu()
        elif choice == "history":
            history_menu()
        elif choice == "back" or choice is None:
            break
```

**Step 2: Commit**

```bash
git add modules/cron/__init__.py
git commit -m "feat(cron): integrate logs and history menus"
```

---

## Summary

After Phase 5, the cron module will have:

**Log Viewing:**
- View job logs with line count option
- Tail realtime with color coding
- Search logs with highlighting
- Clear logs

**Execution History:**
- Per-job history tracking
- Success/failure status
- Duration tracking
- Output snippet capture
- Summary view for all jobs
- Clear history options

**Wrapper Script:**
- Captures exit code, duration, output
- Writes to JSON history file
- Installed at `/usr/local/bin/vexo-cron-wrapper`

Files added/modified:
- `modules/cron/logs.py` (new)
- `modules/cron/history.py` (new)
- `scripts/vexo-cron-wrapper` (new)
- `modules/cron/__init__.py` (updated)
