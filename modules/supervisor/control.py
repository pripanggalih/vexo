"""Worker control operations for vexo supervisor."""

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
from ui.menu import run_menu_loop, confirm_action, select_from_list
from utils.shell import run_command, is_installed, require_root

from modules.supervisor.common import get_vexo_workers


def show_menu():
    """Display the Worker Control submenu."""
    options = [
        ("start", "1. Start Worker"),
        ("stop", "2. Stop Worker"),
        ("restart", "3. Restart Worker"),
        ("restart_all", "4. Restart All Workers"),
        ("reload", "5. Reload Configuration"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "start": lambda: control_worker("start"),
        "stop": lambda: control_worker("stop"),
        "restart": lambda: control_worker("restart"),
        "restart_all": restart_all_workers,
        "reload": reload_configuration,
    }
    
    run_menu_loop("Worker Control", options, handlers)


def control_worker(action):
    """Control a specific worker."""
    clear_screen()
    show_header()
    show_panel(f"{action.capitalize()} Worker", title="Worker Control", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    workers = get_vexo_workers()
    
    if not workers:
        show_info("No workers configured.")
        press_enter_to_continue()
        return
    
    worker = select_from_list(
        title=f"{action.capitalize()} Worker",
        message=f"Select worker to {action}:",
        options=workers
    )
    
    if not worker:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    show_info(f"{action.capitalize()}ing worker '{worker}'...")
    
    result = run_command(f"supervisorctl {action} {worker}:*", check=False, silent=True)
    
    if result.returncode == 0:
        show_success(f"Worker '{worker}' {action}ed!")
        if result.stdout:
            console.print(f"[dim]{result.stdout.strip()}[/dim]")
    else:
        show_error(f"Failed to {action} worker.")
        if result.stderr:
            console.print(f"[dim]{result.stderr.strip()}[/dim]")
    
    press_enter_to_continue()


def restart_all_workers():
    """Restart all workers."""
    clear_screen()
    show_header()
    show_panel("Restart All Workers", title="Worker Control", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    workers = get_vexo_workers()
    
    if not workers:
        show_info("No workers configured.")
        press_enter_to_continue()
        return
    
    console.print(f"[bold]This will restart {len(workers)} worker(s):[/bold]")
    for w in workers:
        console.print(f"  - {w}")
    console.print()
    
    if not confirm_action("Restart all workers?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    show_info("Restarting all workers...")
    
    result = run_command("supervisorctl restart all", check=False, silent=True)
    
    if result.returncode == 0:
        show_success("All workers restarted!")
    else:
        show_error("Failed to restart workers.")
    
    press_enter_to_continue()


def reload_configuration():
    """Reload supervisor configuration."""
    clear_screen()
    show_header()
    show_panel("Reload Configuration", title="Worker Control", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    show_info("Reloading supervisor configuration...")
    
    result = run_command("supervisorctl reread", check=False, silent=True)
    if result.returncode == 0:
        console.print("[dim]Configuration reread.[/dim]")
    
    result = run_command("supervisorctl update", check=False, silent=True)
    if result.returncode == 0:
        show_success("Configuration reloaded!")
    else:
        show_error("Failed to reload configuration.")
    
    press_enter_to_continue()
