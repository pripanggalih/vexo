"""Cron module for vexo-cli (Scheduled Tasks)."""

from ui.menu import run_menu_loop, show_submenu

from modules.cron.add_job import add_job_menu
from modules.cron.jobs import (
    remove_cron_job_interactive,
    list_cron_jobs,
    toggle_cron_job,
)
from modules.cron.edit import edit_job_menu, clone_job_menu
from modules.cron.logs import logs_menu
from modules.cron.history import history_menu
from modules.cron.backup import backup_crontab, restore_crontab
from modules.cron.status import show_status


def show_menu():
    """Display the Cron Management submenu."""
    options = [
        ("manage", "1. Job Management"),
        ("toggle", "2. Enable/Disable Job"),
        ("logs", "3. Logs & History"),
        ("backup", "4. Backup & Restore"),
        ("status", "5. Show Status"),
        ("back", "← Back to Main Menu"),
    ]
    
    handlers = {
        "manage": job_management_menu,
        "toggle": toggle_cron_job,
        "logs": logs_history_menu,
        "backup": backup_restore_menu,
        "status": show_status,
    }
    
    run_menu_loop("Cron Jobs", options, handlers, lambda: "Cron Jobs Manager")


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
