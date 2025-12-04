"""Supervisor module for vexo-cli (Queue Workers)."""

from ui.menu import run_menu_loop
from utils.shell import is_installed, is_service_running

from modules.supervisor.install import install_supervisor
from modules.supervisor.add_worker import show_menu as show_add_worker_menu
from modules.supervisor.worker import remove_worker_interactive, list_workers
from modules.supervisor.edit import edit_worker_menu, clone_worker_menu
from modules.supervisor.control import show_menu as show_control_menu
from modules.supervisor.monitor import show_menu as show_monitor_menu
from modules.supervisor.logs import show_menu as show_logs_menu
from modules.supervisor.env import show_menu as show_env_menu
from modules.supervisor.status import show_status


def show_menu():
    """Display the Supervisor Management submenu."""
    def get_status():
        if is_service_running("supervisor"):
            return "Supervisor: [green]Running[/green]"
        elif is_installed("supervisor"):
            return "Supervisor: [red]Stopped[/red]"
        return "Supervisor: [dim]Not installed[/dim]"
    
    def get_options():
        options = []
        if is_installed("supervisor"):
            options.extend([
                ("manage", "1. Worker Management"),
                ("control", "2. Worker Control"),
                ("monitor", "3. Monitoring"),
                ("logs", "4. Logs"),
                ("env", "5. Environment Variables"),
                ("status", "6. Show Status"),
            ])
        else:
            options.append(("install", "1. Install Supervisor"))
        options.append(("back", "← Back to Main Menu"))
        return options
    
    handlers = {
        "install": install_supervisor,
        "manage": worker_management_menu,
        "control": show_control_menu,
        "monitor": show_monitor_menu,
        "logs": show_logs_menu,
        "env": show_env_menu,
        "status": show_status,
    }
    
    run_menu_loop("Supervisor (Queue Workers)", get_options, handlers, get_status)


def worker_management_menu():
    """Submenu for worker management operations."""
    options = [
        ("add", "1. Add Worker"),
        ("edit", "2. Edit Worker"),
        ("clone", "3. Clone Worker"),
        ("remove", "4. Remove Worker"),
        ("list", "5. List Workers"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "add": show_add_worker_menu,
        "edit": edit_worker_menu,
        "clone": clone_worker_menu,
        "remove": remove_worker_interactive,
        "list": list_workers,
    }
    
    run_menu_loop("Worker Management", options, handlers)
