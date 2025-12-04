"""Supervisor module for vexo-cli (Queue Workers)."""

from ui.menu import run_menu_loop
from utils.shell import is_installed, is_service_running

from modules.supervisor.install import install_supervisor
from modules.supervisor.worker import add_worker_interactive, remove_worker_interactive, list_workers
from modules.supervisor.control import show_menu as show_control_menu
from modules.supervisor.logs import view_logs
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
                ("add", "1. Add Worker"),
                ("remove", "2. Remove Worker"),
                ("list", "3. List Workers"),
                ("control", "4. Worker Control"),
                ("logs", "5. View Logs"),
                ("status", "6. Show Status"),
            ])
        else:
            options.append(("install", "1. Install Supervisor"))
        options.append(("back", "← Back to Main Menu"))
        return options
    
    handlers = {
        "install": install_supervisor,
        "add": add_worker_interactive,
        "remove": remove_worker_interactive,
        "list": list_workers,
        "control": show_control_menu,
        "logs": view_logs,
        "status": show_status,
    }
    
    run_menu_loop("Supervisor (Queue Workers)", get_options, handlers, get_status)
