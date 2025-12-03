"""Cron module for vexo-cli (Scheduled Tasks)."""

import os
import tempfile
from datetime import datetime

from ui.components import (
    console,
    show_panel,
    show_table,
    show_success,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, require_root


# Constants
VEXO_CONFIG_DIR = "/etc/vexo"
CRON_BACKUP_DIR = "/etc/vexo/cron-backups"
CRON_USER = "www-data"

# Cron presets
CRON_PRESETS = [
    ("* * * * *", "Every minute"),
    ("*/5 * * * *", "Every 5 minutes"),
    ("*/15 * * * *", "Every 15 minutes"),
    ("*/30 * * * *", "Every 30 minutes"),
    ("0 * * * *", "Every hour"),
    ("0 */6 * * *", "Every 6 hours"),
    ("0 0 * * *", "Every day at midnight"),
    ("0 0 * * 0", "Every Sunday at midnight"),
    ("0 0 1 * *", "First day of month"),
]


def show_menu():
    """Display the Cron Management submenu."""
    options = [
        ("laravel", "1. Setup Laravel Scheduler"),
        ("add", "2. Add Cron Job"),
        ("remove", "3. Remove Cron Job"),
        ("list", "4. List Cron Jobs"),
        ("toggle", "5. Enable/Disable Job"),
        ("backup", "6. Backup Crontab"),
        ("restore", "7. Restore Crontab"),
        ("status", "8. Show Status"),
        ("back", "← Back to Main Menu"),
    ]
    
    handlers = {
        "laravel": setup_laravel_scheduler,
        "add": add_cron_job_interactive,
        "remove": remove_cron_job_interactive,
        "list": list_cron_jobs,
        "toggle": toggle_cron_job,
        "backup": backup_crontab,
        "restore": restore_crontab,
        "status": show_status,
    }
    
    run_menu_loop("Cron Jobs", options, handlers, lambda: "Cron Jobs Manager")


# =============================================================================
# Crontab Helpers
# =============================================================================

def _get_crontab_lines():
    """Get current crontab lines for www-data user."""
    result = run_command(f"crontab -u {CRON_USER} -l 2>/dev/null", check=False, silent=True)
    if result.returncode == 0 and result.stdout:
        return result.stdout.strip().split('\n')
    return []


def _save_crontab(lines):
    """Save crontab for www-data user."""
    content = '\n'.join(lines) + '\n'
    
    # Write to temp file and install (use tempfile to avoid race conditions)
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, prefix='vexo-crontab-') as f:
            f.write(content)
            tmp_file = f.name
        
        result = run_command(f"crontab -u {CRON_USER} {tmp_file}", check=False, silent=True)
        
        os.unlink(tmp_file)
        return result.returncode == 0
    except IOError:
        return False


def _add_cron_entry(job_name, cron_line):
    """Add a new cron entry with vexo marker."""
    lines = _get_crontab_lines()
    
    # Remove empty lines at start
    while lines and not lines[0].strip():
        lines.pop(0)
    
    # Add the new entry with marker
    lines.append(f"# vexo: {job_name}")
    lines.append(cron_line)
    
    return _save_crontab(lines)


def _remove_cron_entry(job_name):
    """Remove a cron entry by job name."""
    lines = _get_crontab_lines()
    new_lines = []
    skip_next = False
    
    for line in lines:
        if f"# vexo: {job_name}" in line:
            skip_next = True
            continue
        if skip_next:
            skip_next = False
            continue
        new_lines.append(line)
    
    return _save_crontab(new_lines)


def _get_vexo_jobs():
    """Get list of vexo-managed cron jobs."""
    lines = _get_crontab_lines()
    jobs = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("# vexo:"):
            job_name = line.replace("# vexo:", "").strip()
            if i + 1 < len(lines):
                cron_line = lines[i + 1]
                enabled = not cron_line.startswith("#")
                jobs.append({
                    "name": job_name,
                    "line": cron_line.lstrip("# "),
                    "enabled": enabled,
                    "index": i
                })
            i += 2
        else:
            i += 1
    
    return jobs


# =============================================================================
# Laravel Scheduler
# =============================================================================

def setup_laravel_scheduler():
    """Setup Laravel scheduler cron job."""
    clear_screen()
    show_header()
    show_panel("Laravel Scheduler", title="Cron Jobs", style="cyan")
    
    console.print("[bold]Laravel Scheduler will:[/bold]")
    console.print("  • Run 'php artisan schedule:run' every minute")
    console.print("  • Execute scheduled tasks defined in app/Console/Kernel.php")
    console.print()
    
    laravel_path = text_input(
        title="Laravel Path",
        message="Enter Laravel project path:",
        default="/var/www/html"
    )
    
    if not laravel_path:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Validate Laravel path
    artisan_path = os.path.join(laravel_path, "artisan")
    if not os.path.exists(artisan_path):
        show_error(f"Laravel artisan not found at {laravel_path}")
        press_enter_to_continue()
        return
    
    # Check if already exists
    cron_entry = f"cd {laravel_path} && php artisan schedule:run"
    existing_jobs = _get_crontab_lines()
    
    for job in existing_jobs:
        if cron_entry in job and not job.strip().startswith('#'):
            show_info("Laravel scheduler already configured for this path.")
            console.print()
            console.print(f"[dim]{job}[/dim]")
            press_enter_to_continue()
            return
    
    # Show scheduled tasks
    console.print("[bold]Checking scheduled tasks...[/bold]")
    result = run_command(
        f"cd {laravel_path} && php artisan schedule:list 2>/dev/null",
        check=False,
        silent=True
    )
    
    if result.returncode == 0 and result.stdout:
        console.print()
        console.print(result.stdout)
    else:
        console.print("[dim]No scheduled tasks found or unable to list.[/dim]")
    
    console.print()
    
    if not confirm_action("Add Laravel scheduler to crontab?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Generate job name from path
    job_name = f"laravel-scheduler-{os.path.basename(laravel_path)}"
    cron_line = f"* * * * * cd {laravel_path} && php artisan schedule:run >> /dev/null 2>&1"
    
    success = _add_cron_entry(job_name, cron_line)
    
    if success:
        show_success("Laravel scheduler configured!")
        console.print()
        console.print(f"[dim]Job: {job_name}[/dim]")
        console.print(f"[dim]Schedule: Every minute[/dim]")
    else:
        show_error("Failed to add cron job.")
    
    press_enter_to_continue()


# =============================================================================
# Custom Cron Jobs
# =============================================================================

def add_cron_job_interactive():
    """Interactive prompt to add a custom cron job."""
    clear_screen()
    show_header()
    show_panel("Add Cron Job", title="Cron Jobs", style="cyan")
    
    # Job name
    job_name = text_input(
        title="Job Name",
        message="Enter job name (for identification):"
    )
    
    if not job_name:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    job_name = job_name.lower().strip().replace(" ", "-")
    
    # Check if job already exists
    existing_jobs = _get_vexo_jobs()
    for job in existing_jobs:
        if job["name"] == job_name:
            show_error(f"Job '{job_name}' already exists.")
            press_enter_to_continue()
            return
    
    # Schedule selection
    console.print("[bold]Select schedule:[/bold]")
    console.print()
    
    preset_options = [f"{schedule} ({desc})" for schedule, desc in CRON_PRESETS]
    preset_options.append("Custom (enter manually)")
    
    selection = select_from_list(
        title="Schedule",
        message="Select cron schedule:",
        options=preset_options
    )
    
    if not selection:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if selection == "Custom (enter manually)":
        schedule = text_input(
            title="Cron Expression",
            message="Enter cron expression (e.g., 0 * * * *):"
        )
        if not schedule:
            show_warning("Cancelled.")
            press_enter_to_continue()
            return
    else:
        # Extract schedule from selection
        schedule = selection.split(" (")[0]
    
    # Command
    command = text_input(
        title="Command",
        message="Enter command to execute:"
    )
    
    if not command:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Summary
    console.print()
    console.print("[bold]Cron Job Configuration:[/bold]")
    console.print(f"  Name: {job_name}")
    console.print(f"  Schedule: {schedule}")
    console.print(f"  Command: {command}")
    console.print()
    
    if not confirm_action(f"Create cron job '{job_name}'?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    cron_line = f"{schedule} {command}"
    success = _add_cron_entry(job_name, cron_line)
    
    if success:
        show_success(f"Cron job '{job_name}' created!")
    else:
        show_error("Failed to add cron job.")
    
    press_enter_to_continue()


def remove_cron_job_interactive():
    """Interactive prompt to remove a cron job."""
    clear_screen()
    show_header()
    show_panel("Remove Cron Job", title="Cron Jobs", style="cyan")
    
    jobs = _get_vexo_jobs()
    
    if not jobs:
        show_info("No vexo-managed cron jobs found.")
        press_enter_to_continue()
        return
    
    job_names = [job["name"] for job in jobs]
    
    selection = select_from_list(
        title="Remove Job",
        message="Select job to remove:",
        options=job_names
    )
    
    if not selection:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print(f"[red bold]WARNING: This will remove cron job '{selection}'![/red bold]")
    console.print()
    
    if not confirm_action(f"Remove job '{selection}'?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = _remove_cron_entry(selection)
    
    if success:
        show_success(f"Cron job '{selection}' removed!")
    else:
        show_error("Failed to remove cron job.")
    
    press_enter_to_continue()


def list_cron_jobs():
    """Display all cron jobs."""
    clear_screen()
    show_header()
    show_panel("Cron Jobs", title="Scheduled Tasks", style="cyan")
    
    # Vexo-managed jobs
    jobs = _get_vexo_jobs()
    
    if jobs:
        columns = [
            {"name": "Name", "style": "cyan"},
            {"name": "Schedule"},
            {"name": "Command"},
            {"name": "Status"},
        ]
        
        rows = []
        for job in jobs:
            parts = job["line"].split(None, 5)
            if len(parts) >= 6:
                schedule = " ".join(parts[:5])
                command = parts[5]
            else:
                schedule = job["line"]
                command = ""
            
            # Truncate long commands
            if len(command) > 40:
                command = command[:37] + "..."
            
            status = "[green]Enabled[/green]" if job["enabled"] else "[red]Disabled[/red]"
            rows.append([job["name"], schedule, command, status])
        
        show_table("Vexo-Managed Jobs", columns, rows)
    else:
        console.print("[dim]No vexo-managed jobs found.[/dim]")
    
    # Other jobs
    console.print()
    console.print(f"[bold]All crontab entries for {CRON_USER}:[/bold]")
    console.print()
    
    lines = _get_crontab_lines()
    if lines:
        for line in lines:
            if line.strip() and not line.startswith("# vexo:"):
                if line.startswith("#"):
                    console.print(f"[dim]{line}[/dim]")
                else:
                    console.print(f"  {line}")
    else:
        console.print("[dim]Crontab is empty.[/dim]")
    
    press_enter_to_continue()


def toggle_cron_job():
    """Enable or disable a cron job."""
    clear_screen()
    show_header()
    show_panel("Enable/Disable Job", title="Cron Jobs", style="cyan")
    
    jobs = _get_vexo_jobs()
    
    if not jobs:
        show_info("No vexo-managed cron jobs found.")
        press_enter_to_continue()
        return
    
    # Show jobs with status
    options = []
    for job in jobs:
        status = "[green]enabled[/green]" if job["enabled"] else "[red]disabled[/red]"
        options.append(f"{job['name']} ({status})")
    
    selection = select_from_list(
        title="Toggle Job",
        message="Select job to toggle:",
        options=options
    )
    
    if not selection:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Extract job name
    job_name = selection.split(" (")[0]
    
    # Find job
    job = next((j for j in jobs if j["name"] == job_name), None)
    if not job:
        show_error("Job not found.")
        press_enter_to_continue()
        return
    
    action = "disable" if job["enabled"] else "enable"
    
    if not confirm_action(f"{action.capitalize()} job '{job_name}'?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = _toggle_cron_entry(job_name, not job["enabled"])
    
    if success:
        show_success(f"Job '{job_name}' {action}d!")
    else:
        show_error(f"Failed to {action} job.")
    
    press_enter_to_continue()


def _toggle_cron_entry(job_name, enable):
    """Enable or disable a cron entry."""
    lines = _get_crontab_lines()
    new_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        if f"# vexo: {job_name}" in line:
            new_lines.append(line)
            if i + 1 < len(lines):
                cron_line = lines[i + 1]
                if enable:
                    # Remove comment prefix
                    new_lines.append(cron_line.lstrip("# "))
                else:
                    # Add comment prefix if not already commented
                    if not cron_line.startswith("#"):
                        new_lines.append(f"# {cron_line}")
                    else:
                        new_lines.append(cron_line)
                i += 2
            else:
                i += 1
        else:
            new_lines.append(line)
            i += 1
    
    return _save_crontab(new_lines)


# =============================================================================
# Backup & Restore
# =============================================================================

def backup_crontab():
    """Backup current crontab to file."""
    clear_screen()
    show_header()
    show_panel("Backup Crontab", title="Cron Jobs", style="cyan")
    
    lines = _get_crontab_lines()
    
    if not lines:
        show_info("Crontab is empty, nothing to backup.")
        press_enter_to_continue()
        return
    
    console.print(f"[bold]Current crontab ({len(lines)} lines):[/bold]")
    console.print()
    for line in lines[:10]:  # Show first 10 lines
        console.print(f"  {line}")
    if len(lines) > 10:
        console.print(f"  [dim]... and {len(lines) - 10} more lines[/dim]")
    console.print()
    
    if not confirm_action("Create backup?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Ensure backup directory exists (including parent /etc/vexo)
    os.makedirs(CRON_BACKUP_DIR, mode=0o755, exist_ok=True)
    
    # Generate backup filename
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_file = os.path.join(CRON_BACKUP_DIR, f"crontab-{timestamp}.txt")
    
    try:
        with open(backup_file, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        
        show_success("Crontab backed up!")
        console.print()
        console.print(f"[dim]File: {backup_file}[/dim]")
    except IOError as e:
        show_error(f"Failed to create backup: {e}")
    
    press_enter_to_continue()


def restore_crontab():
    """Restore crontab from backup file."""
    clear_screen()
    show_header()
    show_panel("Restore Crontab", title="Cron Jobs", style="cyan")
    
    if not os.path.exists(CRON_BACKUP_DIR):
        show_info("No backups found.")
        press_enter_to_continue()
        return
    
    # List backup files
    backups = []
    for filename in os.listdir(CRON_BACKUP_DIR):
        if filename.startswith("crontab-") and filename.endswith(".txt"):
            filepath = os.path.join(CRON_BACKUP_DIR, filename)
            mtime = os.path.getmtime(filepath)
            backups.append((filename, filepath, mtime))
    
    if not backups:
        show_info("No backups found.")
        press_enter_to_continue()
        return
    
    # Sort by date (newest first)
    backups.sort(key=lambda x: x[2], reverse=True)
    
    options = [b[0] for b in backups]
    
    selection = select_from_list(
        title="Restore Backup",
        message="Select backup to restore:",
        options=options
    )
    
    if not selection:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Find selected backup
    backup_path = next(b[1] for b in backups if b[0] == selection)
    
    # Show backup contents
    with open(backup_path, 'r') as f:
        content = f.read()
    
    console.print(f"[bold]Backup contents:[/bold]")
    console.print()
    console.print(content)
    console.print()
    
    console.print("[red bold]WARNING: This will replace the current crontab![/red bold]")
    console.print()
    
    if not confirm_action("Restore this backup?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    result = run_command(f"crontab -u {CRON_USER} {backup_path}", check=False, silent=True)
    
    if result.returncode == 0:
        show_success("Crontab restored!")
    else:
        show_error("Failed to restore crontab.")
    
    press_enter_to_continue()


# =============================================================================
# Status
# =============================================================================

def show_status():
    """Display cron status."""
    clear_screen()
    show_header()
    show_panel("Cron Status", title="Scheduled Tasks", style="cyan")
    
    # Cron service status
    result = run_command("systemctl is-active cron 2>/dev/null", check=False, silent=True)
    if result.returncode == 0 and "active" in result.stdout:
        console.print("[bold]Cron Service:[/bold] [green]Running[/green]")
    else:
        console.print("[bold]Cron Service:[/bold] [red]Not Running[/red]")
    
    console.print()
    
    # Job counts
    jobs = _get_vexo_jobs()
    all_lines = _get_crontab_lines()
    
    enabled_count = sum(1 for j in jobs if j["enabled"])
    disabled_count = sum(1 for j in jobs if not j["enabled"])
    
    console.print(f"[bold]Vexo-Managed Jobs:[/bold] {len(jobs)}")
    console.print(f"  [green]●[/green] Enabled: {enabled_count}")
    console.print(f"  [red]●[/red] Disabled: {disabled_count}")
    
    console.print()
    
    # Total crontab lines
    console.print(f"[bold]Total Crontab Lines:[/bold] {len(all_lines)}")
    
    # Backups
    if os.path.exists(CRON_BACKUP_DIR):
        backups = [f for f in os.listdir(CRON_BACKUP_DIR) if f.endswith(".txt")]
        console.print(f"[bold]Backups Available:[/bold] {len(backups)}")
    else:
        console.print("[bold]Backups Available:[/bold] 0")
    
    press_enter_to_continue()
