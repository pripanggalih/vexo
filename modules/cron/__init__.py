"""Cron module for vexo-cli (Scheduled Tasks)."""

from ui.menu import run_menu_loop

from modules.cron.laravel import setup_laravel_scheduler
from modules.cron.jobs import (
    add_cron_job_interactive,
    remove_cron_job_interactive,
    list_cron_jobs,
    toggle_cron_job,
)
from modules.cron.backup import backup_crontab, restore_crontab
from modules.cron.status import show_status


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
