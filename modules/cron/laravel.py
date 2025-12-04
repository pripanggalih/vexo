"""Laravel scheduler setup for vexo cron."""

import os

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_success,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import confirm_action, text_input
from utils.shell import run_command, require_root
from utils.error_handler import handle_error

from modules.cron.common import (
    get_crontab_lines,
    add_cron_entry,
)


def setup_laravel_scheduler():
    """Setup Laravel scheduler cron job."""
    clear_screen()
    show_header()
    show_panel("Laravel Scheduler", title="Cron Jobs", style="cyan")
    
    console.print("[bold]Laravel Scheduler will:[/bold]")
    console.print("  - Run 'php artisan schedule:run' every minute")
    console.print("  - Execute scheduled tasks defined in app/Console/Kernel.php")
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
    
    artisan_path = os.path.join(laravel_path, "artisan")
    if not os.path.exists(artisan_path):
        handle_error("E7003", f"Laravel artisan not found at {laravel_path}")
        press_enter_to_continue()
        return
    
    cron_entry = f"cd {laravel_path} && php artisan schedule:run"
    existing_jobs = get_crontab_lines()
    
    for job in existing_jobs:
        if cron_entry in job and not job.strip().startswith('#'):
            show_info("Laravel scheduler already configured for this path.")
            console.print()
            console.print(f"[dim]{job}[/dim]")
            press_enter_to_continue()
            return
    
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
    
    job_name = f"laravel-scheduler-{os.path.basename(laravel_path)}"
    cron_line = f"* * * * * cd {laravel_path} && php artisan schedule:run >> /dev/null 2>&1"
    
    success = add_cron_entry(job_name, cron_line)
    
    if success:
        show_success("Laravel scheduler configured!")
        console.print()
        console.print(f"[dim]Job: {job_name}[/dim]")
        console.print(f"[dim]Schedule: Every minute[/dim]")
    else:
        handle_error("E7003", "Failed to add cron job.")
    
    press_enter_to_continue()
