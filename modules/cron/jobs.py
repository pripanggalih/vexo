"""Job management for vexo cron."""

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_success,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list
from utils.shell import require_root
from utils.error_handler import handle_error

from modules.cron.common import (
    CRON_PRESETS,
    get_vexo_jobs,
    add_cron_entry,
    remove_cron_entry,
    toggle_cron_entry,
    parse_cron_line,
    get_crontab_lines,
    job_exists,
)


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
    
    if job_exists(job_name):
        handle_error("E7003", f"Job '{job_name}' already exists.")
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
    success = add_cron_entry(job_name, cron_line)
    
    if success:
        show_success(f"Cron job '{job_name}' created!")
    else:
        handle_error("E7003", "Failed to add cron job.")
    
    press_enter_to_continue()


def remove_cron_job_interactive():
    """Interactive prompt to remove a cron job."""
    clear_screen()
    show_header()
    show_panel("Remove Cron Job", title="Cron Jobs", style="cyan")
    
    jobs = get_vexo_jobs()
    
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
    
    success = remove_cron_entry(selection)
    
    if success:
        show_success(f"Cron job '{selection}' removed!")
    else:
        handle_error("E7003", "Failed to remove cron job.")
    
    press_enter_to_continue()


def list_cron_jobs():
    """Display all cron jobs."""
    clear_screen()
    show_header()
    show_panel("Cron Jobs", title="Scheduled Tasks", style="cyan")
    
    jobs = get_vexo_jobs()
    
    if jobs:
        columns = [
            {"name": "Name", "style": "cyan"},
            {"name": "Schedule"},
            {"name": "Command"},
            {"name": "Status"},
        ]
        
        rows = []
        for job in jobs:
            schedule, command = parse_cron_line(job["line"])
            if not schedule:
                schedule = job["line"]
                command = ""
            
            if command and len(command) > 40:
                command = command[:37] + "..."
            
            status = "[green]Enabled[/green]" if job["enabled"] else "[red]Disabled[/red]"
            rows.append([job["name"], schedule or "-", command or "-", status])
        
        show_table("Vexo-Managed Jobs", columns, rows)
    else:
        console.print("[dim]No vexo-managed jobs found.[/dim]")
    
    console.print()
    console.print(f"[bold]All crontab entries:[/bold]")
    console.print()
    
    lines = get_crontab_lines()
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
    
    jobs = get_vexo_jobs()
    
    if not jobs:
        show_info("No vexo-managed cron jobs found.")
        press_enter_to_continue()
        return
    
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
    
    job_name = selection.split(" (")[0]
    
    job = next((j for j in jobs if j["name"] == job_name), None)
    if not job:
        handle_error("E7003", "Job not found.")
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
    
    success = toggle_cron_entry(job_name, not job["enabled"])
    
    if success:
        show_success(f"Job '{job_name}' {action}d!")
    else:
        handle_error("E7003", f"Failed to {action} job.")
    
    press_enter_to_continue()
