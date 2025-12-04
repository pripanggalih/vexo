# Phase 3: Edit Job & Clone Job

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add ability to edit existing cron job configurations (schedule and command) and clone jobs with new names.

**Architecture:** Create edit.py module with functions to view and modify job settings. Parse existing cron lines to display current values and generate updated entries.

**Tech Stack:** Python, subprocess (existing)

**Prerequisite:** Complete Phase 2 (job templates)

---

## Task 1: Create Edit Job Module

**Files:**
- Create: `modules/cron/edit.py`

**Step 1: Create edit.py with edit and clone functions**

```python
"""Edit and clone jobs for vexo-cli cron."""

import os

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
from ui.menu import show_submenu, confirm_action, text_input, select_from_list
from utils.shell import require_root

from modules.cron.common import (
    CRON_PRESETS,
    CRON_LOG_DIR,
    get_vexo_jobs,
    get_crontab_lines,
    save_crontab,
    parse_cron_line,
    job_exists,
)


def edit_job_menu():
    """Display edit job selection and options."""
    clear_screen()
    show_header()
    show_panel("Edit Job", title="Cron Jobs", style="cyan")
    
    jobs = get_vexo_jobs()
    
    if not jobs:
        show_info("No vexo-managed cron jobs found.")
        press_enter_to_continue()
        return
    
    job_names = [job["name"] for job in jobs]
    
    selection = select_from_list(
        title="Edit Job",
        message="Select job to edit:",
        options=job_names
    )
    
    if not selection:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    _show_edit_options(selection)


def _show_edit_options(job_name):
    """Show edit options for a specific job."""
    jobs = get_vexo_jobs()
    job = next((j for j in jobs if j["name"] == job_name), None)
    
    if not job:
        show_error("Job not found.")
        press_enter_to_continue()
        return
    
    while True:
        clear_screen()
        show_header()
        show_panel(f"Edit: {job_name}", title="Cron Jobs", style="cyan")
        
        # Parse current config
        schedule, command = parse_cron_line(job["line"])
        if not schedule:
            schedule = "Unknown"
            command = job["line"]
        
        # Display current config
        console.print(f"[bold]Job Name:[/bold] {job_name}")
        console.print(f"[bold]Schedule:[/bold] {schedule}")
        console.print(f"[bold]Command:[/bold] {command[:60]}..." if len(command or "") > 60 else f"[bold]Command:[/bold] {command}")
        console.print(f"[bold]Status:[/bold] {'[green]Enabled[/green]' if job['enabled'] else '[red]Disabled[/red]'}")
        console.print()
        
        choice = show_submenu(
            title=f"Edit {job_name}",
            options=[
                ("schedule", "1. Change Schedule"),
                ("command", "2. Change Command"),
                ("name", "3. Change Job Name"),
                ("view", "4. View Full Command"),
                ("back", "← Back"),
            ]
        )
        
        if choice == "schedule":
            _edit_schedule(job_name, job)
            # Refresh job data
            jobs = get_vexo_jobs()
            job = next((j for j in jobs if j["name"] == job_name), None)
            if not job:
                break
        elif choice == "command":
            _edit_command(job_name, job)
            jobs = get_vexo_jobs()
            job = next((j for j in jobs if j["name"] == job_name), None)
            if not job:
                break
        elif choice == "name":
            new_name = _edit_job_name(job_name, job)
            if new_name:
                job_name = new_name
                jobs = get_vexo_jobs()
                job = next((j for j in jobs if j["name"] == job_name), None)
                if not job:
                    break
        elif choice == "view":
            _view_full_command(job_name, job)
        elif choice == "back" or choice is None:
            break


def _edit_schedule(job_name, job):
    """Edit job schedule."""
    schedule, command = parse_cron_line(job["line"])
    
    console.print(f"\n[dim]Current schedule: {schedule}[/dim]")
    console.print()
    
    # Show preset options
    preset_options = [f"{s} ({d})" for s, d in CRON_PRESETS]
    preset_options.append("Custom (enter manually)")
    
    selection = select_from_list(
        title="New Schedule",
        message="Select new schedule:",
        options=preset_options
    )
    
    if not selection:
        return
    
    if selection == "Custom (enter manually)":
        new_schedule = text_input(
            title="Cron Expression",
            message="Enter cron expression:",
            default=schedule
        )
        if not new_schedule:
            return
    else:
        new_schedule = selection.split(" (")[0]
    
    if new_schedule == schedule:
        show_info("No changes made.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Update crontab
    new_cron_line = f"{new_schedule} {command}"
    if not job["enabled"]:
        new_cron_line = f"# {new_cron_line}"
    
    success = _update_job_line(job_name, new_cron_line)
    
    if success:
        show_success(f"Schedule updated to: {new_schedule}")
    else:
        show_error("Failed to update schedule.")
    
    press_enter_to_continue()


def _edit_command(job_name, job):
    """Edit job command."""
    schedule, command = parse_cron_line(job["line"])
    
    console.print(f"\n[dim]Current command:[/dim]")
    console.print(f"[dim]{command}[/dim]")
    console.print()
    
    new_command = text_input(
        title="New Command",
        message="Enter new command:",
        default=command
    )
    
    if not new_command:
        return
    
    if new_command == command:
        show_info("No changes made.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Update crontab
    new_cron_line = f"{schedule} {new_command}"
    if not job["enabled"]:
        new_cron_line = f"# {new_cron_line}"
    
    success = _update_job_line(job_name, new_cron_line)
    
    if success:
        show_success("Command updated!")
    else:
        show_error("Failed to update command.")
    
    press_enter_to_continue()


def _edit_job_name(job_name, job):
    """Edit job name."""
    console.print(f"\n[dim]Current name: {job_name}[/dim]")
    
    new_name = text_input(
        title="New Name",
        message="Enter new job name:",
        default=job_name
    )
    
    if not new_name:
        return None
    
    new_name = new_name.lower().strip().replace(" ", "-")
    
    if new_name == job_name:
        show_info("No changes made.")
        press_enter_to_continue()
        return None
    
    if job_exists(new_name):
        show_error(f"Job '{new_name}' already exists.")
        press_enter_to_continue()
        return None
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return None
    
    # Update crontab - change marker line
    lines = get_crontab_lines()
    new_lines = []
    
    for line in lines:
        if f"# vexo: {job_name}" in line:
            new_lines.append(f"# vexo: {new_name}")
        else:
            # Also update log path in command if present
            new_lines.append(line.replace(f"/{job_name}.log", f"/{new_name}.log"))
    
    success = save_crontab(new_lines)
    
    if success:
        show_success(f"Job renamed to: {new_name}")
        press_enter_to_continue()
        return new_name
    else:
        show_error("Failed to rename job.")
        press_enter_to_continue()
        return None


def _view_full_command(job_name, job):
    """View full command."""
    clear_screen()
    show_header()
    show_panel(f"Full Command: {job_name}", title="Cron Jobs", style="cyan")
    
    schedule, command = parse_cron_line(job["line"])
    
    console.print(f"[bold]Schedule:[/bold] {schedule}")
    console.print()
    console.print(f"[bold]Command:[/bold]")
    console.print(f"[cyan]{command}[/cyan]")
    console.print()
    console.print(f"[bold]Full cron line:[/bold]")
    console.print(f"[dim]{job['line']}[/dim]")
    
    press_enter_to_continue()


def _update_job_line(job_name, new_cron_line):
    """Update a job's cron line in crontab."""
    lines = get_crontab_lines()
    new_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        if f"# vexo: {job_name}" in line:
            new_lines.append(line)  # Keep marker
            if i + 1 < len(lines):
                new_lines.append(new_cron_line)  # Replace cron line
                i += 2
            else:
                i += 1
        else:
            new_lines.append(line)
            i += 1
    
    return save_crontab(new_lines)


# =============================================================================
# Clone Job
# =============================================================================

def clone_job_menu():
    """Clone an existing job with a new name."""
    clear_screen()
    show_header()
    show_panel("Clone Job", title="Cron Jobs", style="cyan")
    
    jobs = get_vexo_jobs()
    
    if not jobs:
        show_info("No vexo-managed cron jobs found.")
        press_enter_to_continue()
        return
    
    job_names = [job["name"] for job in jobs]
    
    source = select_from_list(
        title="Clone Job",
        message="Select job to clone:",
        options=job_names
    )
    
    if not source:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Get source job
    job = next((j for j in jobs if j["name"] == source), None)
    if not job:
        show_error("Job not found.")
        press_enter_to_continue()
        return
    
    console.print(f"\n[dim]Cloning: {source}[/dim]")
    
    new_name = text_input(
        title="New Job Name",
        message="Enter name for the new job:",
        default=f"{source}-copy"
    )
    
    if not new_name:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    new_name = new_name.lower().strip().replace(" ", "-")
    
    if job_exists(new_name):
        show_error(f"Job '{new_name}' already exists.")
        press_enter_to_continue()
        return
    
    if not confirm_action(f"Clone '{source}' to '{new_name}'?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Create new cron line with updated log path
    new_cron_line = job["line"].replace(f"/{source}.log", f"/{new_name}.log")
    
    # Add to crontab
    lines = get_crontab_lines()
    lines.append(f"# vexo: {new_name}")
    lines.append(new_cron_line)
    
    success = save_crontab(lines)
    
    if success:
        show_success(f"Job '{new_name}' created!")
        console.print()
        console.print(f"[dim]Log: {CRON_LOG_DIR}/{new_name}.log[/dim]")
        console.print()
        
        if confirm_action(f"Edit '{new_name}' now?"):
            jobs = get_vexo_jobs()
            new_job = next((j for j in jobs if j["name"] == new_name), None)
            if new_job:
                _show_edit_options(new_name)
    else:
        show_error("Failed to clone job.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/cron/edit.py
git commit -m "feat(cron): add edit and clone job functionality"
```

---

## Task 2: Update Package Init with Edit/Clone

**Files:**
- Modify: `modules/cron/__init__.py`

**Step 1: Update __init__.py to include edit and clone options**

```python
"""Cron module for vexo-cli (Scheduled Tasks)."""

from ui.menu import run_menu_loop, show_submenu

from modules.cron.add_job import add_job_menu
from modules.cron.jobs import (
    remove_cron_job_interactive,
    list_cron_jobs,
    toggle_cron_job,
)
from modules.cron.edit import edit_job_menu, clone_job_menu
from modules.cron.backup import backup_crontab, restore_crontab
from modules.cron.status import show_status


def show_menu():
    """Display the Cron Management submenu."""
    options = [
        ("manage", "1. Job Management"),
        ("toggle", "2. Enable/Disable Job"),
        ("backup", "3. Backup & Restore"),
        ("status", "4. Show Status"),
        ("back", "← Back to Main Menu"),
    ]
    
    handlers = {
        "manage": job_management_menu,
        "toggle": toggle_cron_job,
        "backup": backup_restore_menu,
        "status": show_status,
    }
    
    run_menu_loop("Cron Jobs", options, handlers, lambda: "Cron Jobs Manager")


def job_management_menu():
    """Submenu for job management operations."""
    from ui.components import clear_screen, show_header
    
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

**Step 2: Commit**

```bash
git add modules/cron/__init__.py
git commit -m "feat(cron): add job management submenu with edit/clone"
```

---

## Summary

After Phase 3, the cron module will have:

**Edit Job:**
- Change schedule (from preset or custom)
- Change command
- Change job name (with log path update)
- View full command

**Clone Job:**
- Select source job
- Enter new name
- Auto-update log path
- Optional immediate edit after clone

Files added/modified:
- `modules/cron/edit.py` (new)
- `modules/cron/__init__.py` (updated)
