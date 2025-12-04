"""Cron module for vexo-cli (Scheduled Tasks)."""

from ui.menu import run_menu_loop

from modules.cron.add_job import add_job_menu
from modules.cron.jobs import (
    remove_cron_job_interactive,
    list_cron_jobs,
    toggle_cron_job,
)
from modules.cron.backup import backup_crontab, restore_crontab
from modules.cron.status import show_status


def show_menu():
    """Display the Cron Management submenu."""
    options = [
        ("add", "1. Add Cron Job"),
        ("remove", "2. Remove Cron Job"),
        ("list", "3. List Cron Jobs"),
        ("toggle", "4. Enable/Disable Job"),
        ("backup", "5. Backup Crontab"),
        ("restore", "6. Restore Crontab"),
        ("status", "7. Show Status"),
        ("back", "← Back to Main Menu"),
    ]
    
    handlers = {
        "add": add_job_menu,
        "remove": remove_cron_job_interactive,
        "list": list_cron_jobs,
        "toggle": toggle_cron_job,
        "backup": backup_crontab,
        "restore": restore_crontab,
        "status": show_status,
    }
    
    run_menu_loop("Cron Jobs", options, handlers, lambda: "Cron Jobs Manager")
