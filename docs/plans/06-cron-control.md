# Phase 6: Job Control

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add job control features including run job now (manual trigger), test job (dry run), and enhanced enable/disable functionality.

**Architecture:** Create control.py module with functions to manually trigger jobs, test jobs before scheduling, and improved toggle functionality with status display.

**Tech Stack:** Python, subprocess

**Prerequisite:** Complete Phase 5 (logs & history)

---

## Task 1: Create Control Module

**Files:**
- Create: `modules/cron/control.py`

**Step 1: Create control.py with job control functions**

```python
"""Job control for vexo-cli cron."""

import os
import subprocess
import time
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
    show_spinner,
    press_enter_to_continue,
)
from ui.menu import show_submenu, confirm_action, select_from_list
from utils.shell import run_command, require_root

from modules.cron.common import (
    get_vexo_jobs,
    toggle_cron_entry,
    parse_cron_line,
    get_job_log_path,
    CRON_LOG_DIR,
)
from modules.cron.history import record_execution


def control_menu():
    """Display the job control submenu."""
    while True:
        clear_screen()
        show_header()
        
        choice = show_submenu(
            title="Job Control",
            options=[
                ("toggle", "1. Enable/Disable Job"),
                ("run", "2. Run Job Now"),
                ("test", "3. Test Job (Dry Run)"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "toggle":
            toggle_job()
        elif choice == "run":
            run_job_now()
        elif choice == "test":
            test_job()
        elif choice == "back" or choice is None:
            break


def toggle_job():
    """Enable or disable a cron job with status display."""
    clear_screen()
    show_header()
    show_panel("Enable/Disable Job", title="Job Control", style="cyan")
    
    jobs = get_vexo_jobs()
    
    if not jobs:
        show_info("No vexo-managed cron jobs found.")
        press_enter_to_continue()
        return
    
    # Display current status
    columns = [
        {"name": "Job", "style": "cyan"},
        {"name": "Schedule"},
        {"name": "Status", "justify": "center"},
    ]
    
    rows = []
    for job in jobs:
        schedule, _ = parse_cron_line(job["line"])
        status = "[green]● Enabled[/green]" if job["enabled"] else "[red]○ Disabled[/red]"
        rows.append([job["name"], schedule or "-", status])
    
    show_table("Current Status", columns, rows)
    console.print()
    
    # Select job to toggle
    options = []
    for job in jobs:
        action = "Disable" if job["enabled"] else "Enable"
        status = "[green]enabled[/green]" if job["enabled"] else "[red]disabled[/red]"
        options.append(f"{action} {job['name']} (currently {status})")
    
    selection = select_from_list(
        title="Toggle Job",
        message="Select job to toggle:",
        options=options
    )
    
    if not selection:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Parse selection
    parts = selection.split(" ", 2)
    action = parts[0].lower()
    job_name = parts[1]
    
    job = next((j for j in jobs if j["name"] == job_name), None)
    if not job:
        show_error("Job not found.")
        press_enter_to_continue()
        return
    
    if not confirm_action(f"{action.capitalize()} job '{job_name}'?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    enable = action == "enable"
    success = toggle_cron_entry(job_name, enable)
    
    if success:
        show_success(f"Job '{job_name}' {action}d!")
    else:
        show_error(f"Failed to {action} job.")
    
    press_enter_to_continue()


def run_job_now():
    """Manually trigger a job to run immediately."""
    clear_screen()
    show_header()
    show_panel("Run Job Now", title="Job Control", style="cyan")
    
    jobs = get_vexo_jobs()
    
    if not jobs:
        show_info("No vexo-managed cron jobs found.")
        press_enter_to_continue()
        return
    
    job_names = [job["name"] for job in jobs]
    
    selection = select_from_list(
        title="Run Job",
        message="Select job to run:",
        options=job_names
    )
    
    if not selection:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    job = next((j for j in jobs if j["name"] == selection), None)
    if not job:
        show_error("Job not found.")
        press_enter_to_continue()
        return
    
    schedule, command = parse_cron_line(job["line"])
    
    if not command:
        show_error("Could not parse job command.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print(f"[bold]Job:[/bold] {selection}")
    console.print(f"[bold]Command:[/bold]")
    console.print(f"[dim]{command}[/dim]")
    console.print()
    
    console.print("[yellow]This will execute the job immediately.[/yellow]")
    
    if not confirm_action("Run this job now?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    clear_screen()
    show_header()
    show_panel(f"Running: {selection}", title="Job Control", style="cyan")
    
    console.print("[dim]Executing...[/dim]")
    console.print()
    
    # Execute the command
    start_time = time.time()
    
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        
        output_lines = []
        for line in process.stdout:
            console.print(f"[dim]{line.rstrip()}[/dim]")
            output_lines.append(line.rstrip())
        
        process.wait()
        exit_code = process.returncode
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        exit_code = 1
        output_lines = [str(e)]
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Record execution
    output_snippet = "\n".join(output_lines[-10:])  # Last 10 lines
    record_execution(selection, exit_code, duration, output_snippet)
    
    console.print()
    console.print("─" * 50)
    
    if exit_code == 0:
        console.print(f"[bold green]✓ Job completed successfully[/bold green]")
    else:
        console.print(f"[bold red]✗ Job failed (exit code: {exit_code})[/bold red]")
    
    console.print(f"[bold]Duration:[/bold] {duration:.2f} seconds")
    
    # Also write to log file
    log_path = get_job_log_path(selection)
    os.makedirs(CRON_LOG_DIR, mode=0o755, exist_ok=True)
    
    try:
        with open(log_path, 'a') as f:
            f.write(f"\n[Manual Run - {datetime.now().isoformat()}]\n")
            f.write("\n".join(output_lines))
            f.write(f"\nExit code: {exit_code}, Duration: {duration:.2f}s\n")
    except IOError:
        pass
    
    press_enter_to_continue()


def test_job():
    """Test a job without actually executing (dry run / preview)."""
    clear_screen()
    show_header()
    show_panel("Test Job (Dry Run)", title="Job Control", style="cyan")
    
    jobs = get_vexo_jobs()
    
    if not jobs:
        show_info("No vexo-managed cron jobs found.")
        press_enter_to_continue()
        return
    
    job_names = [job["name"] for job in jobs]
    
    selection = select_from_list(
        title="Test Job",
        message="Select job to test:",
        options=job_names
    )
    
    if not selection:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    job = next((j for j in jobs if j["name"] == selection), None)
    if not job:
        show_error("Job not found.")
        press_enter_to_continue()
        return
    
    schedule, command = parse_cron_line(job["line"])
    
    if not command:
        show_error("Could not parse job command.")
        press_enter_to_continue()
        return
    
    clear_screen()
    show_header()
    show_panel(f"Test: {selection}", title="Job Control", style="cyan")
    
    console.print("[bold]Job Analysis:[/bold]")
    console.print()
    console.print(f"[bold]Name:[/bold] {selection}")
    console.print(f"[bold]Schedule:[/bold] {schedule}")
    console.print(f"[bold]Status:[/bold] {'Enabled' if job['enabled'] else 'Disabled'}")
    console.print()
    console.print(f"[bold]Full Command:[/bold]")
    console.print(f"[cyan]{command}[/cyan]")
    console.print()
    
    # Analyze command
    _analyze_command(command)
    
    console.print()
    
    # Offer to do specific tests
    test_options = [
        "Check if paths exist",
        "Check if executables are available",
        "Run command (actual execution)",
        "Cancel",
    ]
    
    test_choice = select_from_list(
        title="Test Options",
        message="Select test to perform:",
        options=test_options
    )
    
    if test_choice == "Check if paths exist":
        _check_paths(command)
    elif test_choice == "Check if executables are available":
        _check_executables(command)
    elif test_choice == "Run command (actual execution)":
        if confirm_action("This will actually run the command. Continue?"):
            # Use run_job_now logic
            _execute_test_run(selection, command)
    
    press_enter_to_continue()


def _analyze_command(command):
    """Analyze a command and display information."""
    console.print("[bold]Command Analysis:[/bold]")
    
    # Check for common patterns
    checks = []
    
    if "php artisan" in command:
        checks.append(("Laravel Artisan", "Detected Laravel artisan command"))
    
    if "mysqldump" in command or "pg_dump" in command:
        checks.append(("Database Backup", "Detected database backup command"))
    
    if "certbot" in command:
        checks.append(("SSL/Certbot", "Detected certificate management"))
    
    if "find" in command and "-delete" in command:
        checks.append(("File Cleanup", "Detected file deletion command"))
    
    if ">> " in command or "2>&1" in command:
        checks.append(("Output Redirect", "Output is being logged"))
    
    if "/var/log/vexo/cron/" in command:
        checks.append(("Vexo Logging", "Using vexo log directory"))
    
    if checks:
        for name, desc in checks:
            console.print(f"  [green]✓[/green] {name}: {desc}")
    else:
        console.print("  [dim]No specific patterns detected[/dim]")


def _check_paths(command):
    """Check if paths in command exist."""
    console.print()
    console.print("[bold]Path Check:[/bold]")
    
    import re
    
    # Find paths (starting with /)
    paths = re.findall(r'(/[^\s"\'><|&;]+)', command)
    
    if not paths:
        console.print("  [dim]No paths detected in command[/dim]")
        return
    
    for path in set(paths):
        # Skip log file paths (they're created on demand)
        if path.endswith('.log'):
            console.print(f"  [dim]○[/dim] {path} (log file, created on write)")
            continue
        
        if os.path.exists(path):
            if os.path.isdir(path):
                console.print(f"  [green]✓[/green] {path} (directory exists)")
            else:
                console.print(f"  [green]✓[/green] {path} (file exists)")
        else:
            # Check if parent directory exists
            parent = os.path.dirname(path)
            if os.path.exists(parent):
                console.print(f"  [yellow]?[/yellow] {path} (not found, but parent exists)")
            else:
                console.print(f"  [red]✗[/red] {path} (not found)")


def _check_executables(command):
    """Check if executables in command are available."""
    console.print()
    console.print("[bold]Executable Check:[/bold]")
    
    # Common executables to check for
    executables = ['php', 'python3', 'python', 'node', 'bash', 'sh',
                   'mysqldump', 'pg_dump', 'certbot', 'find', 'gzip',
                   'tar', 'rsync', 'curl', 'wget']
    
    found = []
    for exe in executables:
        if exe in command:
            found.append(exe)
    
    if not found:
        console.print("  [dim]No common executables detected[/dim]")
        return
    
    for exe in found:
        result = run_command(f"which {exe}", check=False, silent=True)
        if result.returncode == 0:
            path = result.stdout.strip()
            console.print(f"  [green]✓[/green] {exe}: {path}")
        else:
            console.print(f"  [red]✗[/red] {exe}: not found in PATH")


def _execute_test_run(job_name, command):
    """Execute a test run of the command."""
    console.print()
    console.print("[bold]Test Execution:[/bold]")
    console.print()
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout for test
        )
        
        duration = time.time() - start_time
        
        if result.stdout:
            console.print("[bold]Output:[/bold]")
            for line in result.stdout.strip().split('\n')[:20]:
                console.print(f"  [dim]{line}[/dim]")
            if len(result.stdout.strip().split('\n')) > 20:
                console.print("  [dim]... (truncated)[/dim]")
        
        if result.stderr:
            console.print("[bold]Errors:[/bold]")
            for line in result.stderr.strip().split('\n')[:10]:
                console.print(f"  [red]{line}[/red]")
        
        console.print()
        if result.returncode == 0:
            console.print(f"[green]✓ Test passed[/green] (exit code: 0, duration: {duration:.2f}s)")
        else:
            console.print(f"[red]✗ Test failed[/red] (exit code: {result.returncode}, duration: {duration:.2f}s)")
        
        # Record in history
        output_snippet = result.stdout[-500:] if result.stdout else ""
        record_execution(job_name + "-test", result.returncode, duration, output_snippet)
        
    except subprocess.TimeoutExpired:
        console.print("[red]✗ Test timed out (60 seconds)[/red]")
    except Exception as e:
        console.print(f"[red]✗ Test error: {e}[/red]")
```

**Step 2: Commit**

```bash
git add modules/cron/control.py
git commit -m "feat(cron): add job control with run now and test features"
```

---

## Task 2: Update Package Init with Control Menu

**Files:**
- Modify: `modules/cron/__init__.py`

**Step 1: Final update to __init__.py**

```python
"""Cron module for vexo-cli (Scheduled Tasks)."""

from ui.menu import run_menu_loop, show_submenu

from modules.cron.add_job import add_job_menu
from modules.cron.jobs import (
    remove_cron_job_interactive,
    list_cron_jobs,
)
from modules.cron.edit import edit_job_menu, clone_job_menu
from modules.cron.control import control_menu
from modules.cron.logs import logs_menu
from modules.cron.history import history_menu
from modules.cron.backup import backup_crontab, restore_crontab
from modules.cron.status import show_status


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
        "control": control_menu,
        "logs": logs_history_menu,
        "backup": backup_restore_menu,
        "status": show_status,
    }
    
    run_menu_loop("Cron Jobs", options, handlers, lambda: "Cron Jobs Manager")


def job_management_menu():
    """Submenu for job management operations."""
    from ui.components import clear_screen, show_header
    from modules.cron.builder import schedule_builder
    
    while True:
        clear_screen()
        show_header()
        
        choice = show_submenu(
            title="Job Management",
            options=[
                ("add", "1. Add Job"),
                ("edit", "2. Edit Job"),
                ("clone", "3. Clone Job"),
                ("remove", "4. Remove Job"),
                ("list", "5. List Jobs"),
                ("builder", "6. Schedule Builder"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "add":
            add_job_menu()
        elif choice == "edit":
            edit_job_menu()
        elif choice == "clone":
            clone_job_menu()
        elif choice == "remove":
            remove_cron_job_interactive()
        elif choice == "list":
            list_cron_jobs()
        elif choice == "builder":
            _show_builder_standalone()
        elif choice == "back" or choice is None:
            break


def _show_builder_standalone():
    """Show schedule builder as standalone tool."""
    from modules.cron.builder import schedule_builder
    from ui.components import console, press_enter_to_continue
    
    result = schedule_builder()
    if result:
        console.print()
        console.print(f"[bold green]Generated schedule:[/bold green] {result}")
        console.print()
        console.print("[dim]You can use this schedule when adding a new job.[/dim]")
        press_enter_to_continue()


def logs_history_menu():
    """Submenu for logs and history."""
    from ui.components import clear_screen, show_header
    
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


def backup_restore_menu():
    """Submenu for backup and restore operations."""
    from ui.components import clear_screen, show_header
    
    while True:
        clear_screen()
        show_header()
        
        choice = show_submenu(
            title="Backup & Restore",
            options=[
                ("backup", "1. Backup Crontab"),
                ("restore", "2. Restore Crontab"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "backup":
            backup_crontab()
        elif choice == "restore":
            restore_crontab()
        elif choice == "back" or choice is None:
            break
```

**Step 2: Final commit**

```bash
git add modules/cron/__init__.py
git commit -m "feat(cron): complete cron enhancement with job control - all phases done"
```

---

## Summary

After Phase 6, the cron module will have:

**Job Control:**
- **Enable/Disable Job:** Toggle with status table display
- **Run Job Now:** Manual execution with live output and history recording
- **Test Job (Dry Run):**
  - Command analysis
  - Path existence check
  - Executable availability check
  - Optional actual execution with 60s timeout

Files added/modified:
- `modules/cron/control.py` (new)
- `modules/cron/__init__.py` (updated)

---

## Final Project Structure

After completing all 6 phases:

```
modules/
├── cron/
│   ├── __init__.py       # Main menu & submenus
│   ├── common.py         # Shared utilities
│   ├── laravel.py        # Laravel scheduler (legacy, kept for compatibility)
│   ├── jobs.py           # List/remove jobs
│   ├── add_job.py        # Add job wizards with templates
│   ├── templates.py      # Job templates
│   ├── edit.py           # Edit/clone jobs
│   ├── builder.py        # Interactive schedule builder
│   ├── control.py        # Enable/disable, run now, test
│   ├── logs.py           # Log viewing
│   ├── history.py        # Execution history
│   ├── backup.py         # Backup & restore
│   └── status.py         # Status display
scripts/
└── vexo-cron-wrapper     # Execution tracking wrapper
```

**Full Menu Structure:**
```
Cron Jobs
├── 1. Job Management
│      ├── Add Job (templates for DB backup, cleanup, SSL, custom)
│      ├── Edit Job
│      ├── Clone Job
│      ├── Remove Job
│      ├── List Jobs
│      └── Schedule Builder
├── 2. Job Control
│      ├── Enable/Disable Job
│      ├── Run Job Now
│      └── Test Job (Dry Run)
├── 3. Logs & History
│      ├── View Logs (tail, search, clear)
│      └── Execution History (per-job, summary)
├── 4. Backup & Restore
│      ├── Backup Crontab
│      └── Restore Crontab
├── 5. Show Status
└── ← Back
```
