"""Supervisor module for vexo-cli (Queue Workers)."""

import os
import re

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_success,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import show_submenu, confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import (
    run_command,
    run_command_realtime,
    is_installed,
    is_service_running,
    service_control,
    require_root,
)


# Constants
SUPERVISOR_CONF_DIR = "/etc/supervisor/conf.d"
SUPERVISOR_LOG_DIR = "/var/log/supervisor"


def _validate_worker_name(name):
    """Validate worker name (alphanumeric and hyphens only)."""
    if not name:
        return False
    # Must start/end with alphanumeric, can contain hyphens in middle
    if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$', name):
        return False
    if '--' in name:  # No double hyphens
        return False
    return True


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
        "control": worker_control_menu,
        "logs": view_logs,
        "status": show_status,
    }
    
    run_menu_loop("Supervisor (Queue Workers)", get_options, handlers, get_status)


# =============================================================================
# Installation
# =============================================================================

def install_supervisor():
    """Install Supervisor."""
    clear_screen()
    show_header()
    show_panel("Install Supervisor", title="Queue Workers", style="cyan")
    
    if is_installed("supervisor"):
        show_info("Supervisor is already installed.")
        
        if is_service_running("supervisor"):
            console.print("[dim]Service is running.[/dim]")
        else:
            if confirm_action("Start Supervisor service?"):
                service_control("supervisor", "start")
                show_success("Supervisor started!")
        
        press_enter_to_continue()
        return
    
    console.print("[bold]Supervisor will be installed for:[/bold]")
    console.print("  • Managing Laravel queue workers")
    console.print("  • Auto-restart on failure")
    console.print("  • Process monitoring")
    console.print()
    
    if not confirm_action("Install Supervisor?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    show_info("Installing Supervisor...")
    
    returncode = run_command_realtime(
        "apt install -y supervisor",
        "Installing Supervisor..."
    )
    
    if returncode != 0:
        show_error("Failed to install Supervisor.")
        press_enter_to_continue()
        return
    
    service_control("supervisor", "start")
    service_control("supervisor", "enable")
    
    if is_service_running("supervisor"):
        show_success("Supervisor installed and running!")
    else:
        show_warning("Supervisor installed but service may not be running.")
    
    press_enter_to_continue()


# =============================================================================
# Worker Management
# =============================================================================

def add_worker_interactive():
    """Interactive prompt to add a new queue worker."""
    clear_screen()
    show_header()
    show_panel("Add Worker", title="Queue Workers", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    # Worker name
    worker_name = text_input(
        title="Worker Name",
        message="Enter worker name (e.g., myapp-queue):"
    )
    
    if not worker_name:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    worker_name = worker_name.lower().strip().replace(" ", "-")
    
    # Validate worker name format
    if not _validate_worker_name(worker_name):
        show_error("Invalid worker name. Use only letters, numbers, and hyphens (no double hyphens, must start/end with alphanumeric).")
        press_enter_to_continue()
        return
    
    # Check if worker already exists
    config_path = os.path.join(SUPERVISOR_CONF_DIR, f"{worker_name}.conf")
    if os.path.exists(config_path):
        show_error(f"Worker '{worker_name}' already exists.")
        press_enter_to_continue()
        return
    
    # Laravel path
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
    
    # Queue connection
    connection = text_input(
        title="Queue Connection",
        message="Enter queue connection:",
        default="database"
    )
    
    if not connection:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Queue names
    queues = text_input(
        title="Queue Names",
        message="Enter queue names (comma-separated):",
        default="default"
    )
    
    if not queues:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Number of processes
    numprocs = text_input(
        title="Processes",
        message="Enter number of worker processes:",
        default="1"
    )
    
    if not numprocs:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        numprocs = int(numprocs)
        if numprocs < 1:
            raise ValueError()
    except ValueError:
        show_error("Invalid number of processes.")
        press_enter_to_continue()
        return
    
    # Summary
    console.print()
    console.print("[bold]Worker Configuration:[/bold]")
    console.print(f"  Name: {worker_name}")
    console.print(f"  Laravel Path: {laravel_path}")
    console.print(f"  Connection: {connection}")
    console.print(f"  Queues: {queues}")
    console.print(f"  Processes: {numprocs}")
    console.print()
    
    if not confirm_action(f"Create worker '{worker_name}'?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = add_worker(worker_name, laravel_path, connection, queues, numprocs)
    
    if success:
        show_success(f"Worker '{worker_name}' created!")
        console.print()
        console.print(f"[dim]Config: {config_path}[/dim]")
        console.print(f"[dim]Log: {SUPERVISOR_LOG_DIR}/{worker_name}.log[/dim]")
    else:
        show_error("Failed to create worker.")
    
    press_enter_to_continue()


def add_worker(name, laravel_path, connection, queues, numprocs):
    """
    Create a new Supervisor worker config.
    
    Args:
        name: Worker name
        laravel_path: Path to Laravel project
        connection: Queue connection (database, redis, etc.)
        queues: Queue names (comma-separated)
        numprocs: Number of processes
    
    Returns:
        bool: True if successful
    """
    config_content = f"""[program:{name}]
process_name=%(program_name)s_%(process_num)02d
command=php {laravel_path}/artisan queue:work {connection} --queue={queues} --sleep=3 --tries=3 --max-time=3600
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
user=www-data
numprocs={numprocs}
redirect_stderr=true
stdout_logfile={SUPERVISOR_LOG_DIR}/{name}.log
stopwaitsecs=3600
"""
    
    config_path = os.path.join(SUPERVISOR_CONF_DIR, f"{name}.conf")
    
    try:
        with open(config_path, 'w') as f:
            f.write(config_content)
    except IOError as e:
        show_error(f"Failed to write config: {e}")
        return False
    
    # Reload Supervisor
    result = run_command("supervisorctl reread", check=False, silent=True)
    if result.returncode != 0:
        return False
    
    result = run_command("supervisorctl update", check=False, silent=True)
    if result.returncode != 0:
        return False
    
    return True


def remove_worker_interactive():
    """Interactive prompt to remove a worker."""
    clear_screen()
    show_header()
    show_panel("Remove Worker", title="Queue Workers", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    workers = _get_worker_list()
    
    if not workers:
        show_info("No workers configured.")
        press_enter_to_continue()
        return
    
    worker = select_from_list(
        title="Remove Worker",
        message="Select worker to remove:",
        options=workers
    )
    
    if not worker:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print(f"[red bold]WARNING: This will stop and remove worker '{worker}'![/red bold]")
    console.print()
    
    if not confirm_action(f"Remove worker '{worker}'?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = remove_worker(worker)
    
    if success:
        show_success(f"Worker '{worker}' removed!")
    else:
        show_error("Failed to remove worker.")
    
    press_enter_to_continue()


def remove_worker(name):
    """
    Remove a Supervisor worker.
    
    Args:
        name: Worker name
    
    Returns:
        bool: True if successful
    """
    # Stop the worker first
    run_command(f"supervisorctl stop {name}:*", check=False, silent=True)
    
    # Remove config file
    config_path = os.path.join(SUPERVISOR_CONF_DIR, f"{name}.conf")
    
    try:
        if os.path.exists(config_path):
            os.remove(config_path)
    except IOError as e:
        show_error(f"Failed to remove config: {e}")
        return False
    
    # Reload Supervisor
    result = run_command("supervisorctl reread", check=False, silent=True)
    if result.returncode != 0:
        return False
    
    result = run_command("supervisorctl update", check=False, silent=True)
    return result.returncode == 0


def _get_worker_list():
    """Get list of vexo-managed queue workers."""
    workers = []
    
    if not os.path.exists(SUPERVISOR_CONF_DIR):
        return workers
    
    for filename in os.listdir(SUPERVISOR_CONF_DIR):
        if filename.endswith('.conf'):
            config_path = os.path.join(SUPERVISOR_CONF_DIR, filename)
            # Only include vexo-managed workers (those with artisan queue:work)
            try:
                with open(config_path, 'r') as f:
                    content = f.read()
                    if 'artisan queue:work' in content:
                        workers.append(filename[:-5])  # Remove .conf extension
            except IOError:
                continue
    
    return sorted(workers)


def list_workers():
    """Display all configured workers."""
    clear_screen()
    show_header()
    show_panel("Queue Workers", title="Supervisor", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    workers = _get_worker_list()
    
    if not workers:
        show_info("No workers configured.")
        console.print()
        console.print("[dim]Use 'Add Worker' to create one.[/dim]")
        press_enter_to_continue()
        return
    
    # Get status from supervisorctl
    result = run_command("supervisorctl status", check=False, silent=True)
    status_lines = result.stdout.strip().split('\n') if result.stdout else []
    
    # Parse status
    status_map = {}
    for line in status_lines:
        parts = line.split()
        if len(parts) >= 2:
            name = parts[0]
            state = parts[1]
            status_map[name] = state
    
    columns = [
        {"name": "Worker", "style": "cyan"},
        {"name": "Processes"},
        {"name": "Status"},
    ]
    
    rows = []
    for worker in workers:
        # Count processes and get status
        proc_statuses = []
        for key, state in status_map.items():
            if key.startswith(f"{worker}:") or key == worker:
                proc_statuses.append(state)
        
        if proc_statuses:
            running = sum(1 for s in proc_statuses if s == "RUNNING")
            total = len(proc_statuses)
            proc_count = f"{running}/{total}"
            
            if running == total:
                status = "[green]Running[/green]"
            elif running > 0:
                status = "[yellow]Partial[/yellow]"
            else:
                status = "[red]Stopped[/red]"
        else:
            proc_count = "?"
            status = "[dim]Unknown[/dim]"
        
        rows.append([worker, proc_count, status])
    
    show_table("Configured Workers", columns, rows)
    
    press_enter_to_continue()


# =============================================================================
# Worker Control
# =============================================================================

def worker_control_menu():
    """Submenu for worker control operations."""
    while True:
        clear_screen()
        show_header()
        
        choice = show_submenu(
            title="Worker Control",
            options=[
                ("start", "1. Start Worker"),
                ("stop", "2. Stop Worker"),
                ("restart", "3. Restart Worker"),
                ("restart_all", "4. Restart All Workers"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "start":
            _control_worker("start")
        elif choice == "stop":
            _control_worker("stop")
        elif choice == "restart":
            _control_worker("restart")
        elif choice == "restart_all":
            _restart_all_workers()
        elif choice == "back" or choice is None:
            break


def _control_worker(action):
    """Control a specific worker."""
    clear_screen()
    show_header()
    show_panel(f"{action.capitalize()} Worker", title="Worker Control", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    workers = _get_worker_list()
    
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


def _restart_all_workers():
    """Restart all workers."""
    clear_screen()
    show_header()
    show_panel("Restart All Workers", title="Worker Control", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    workers = _get_worker_list()
    
    if not workers:
        show_info("No workers configured.")
        press_enter_to_continue()
        return
    
    console.print(f"[bold]This will restart {len(workers)} worker(s):[/bold]")
    for w in workers:
        console.print(f"  • {w}")
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


# =============================================================================
# Logs
# =============================================================================

def view_logs():
    """View worker logs."""
    clear_screen()
    show_header()
    show_panel("View Logs", title="Queue Workers", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    workers = _get_worker_list()
    
    if not workers:
        show_info("No workers configured.")
        press_enter_to_continue()
        return
    
    # Add "All logs" option
    options = ["supervisord (main)"] + workers
    
    selection = select_from_list(
        title="View Logs",
        message="Select log to view:",
        options=options
    )
    
    if not selection:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if selection == "supervisord (main)":
        log_path = "/var/log/supervisor/supervisord.log"
    else:
        log_path = f"{SUPERVISOR_LOG_DIR}/{selection}.log"
    
    if not os.path.exists(log_path):
        show_error(f"Log file not found: {log_path}")
        press_enter_to_continue()
        return
    
    console.print(f"[bold]Last 50 lines of {log_path}:[/bold]")
    console.print()
    
    result = run_command(f"tail -50 {log_path}", check=False, silent=True)
    
    if result.returncode == 0:
        console.print(result.stdout or "[dim]Log is empty[/dim]")
    else:
        show_error("Failed to read log file.")
    
    press_enter_to_continue()


# =============================================================================
# Status
# =============================================================================

def show_status():
    """Display Supervisor status."""
    clear_screen()
    show_header()
    show_panel("Supervisor Status", title="Queue Workers", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    # Service status
    if is_service_running("supervisor"):
        console.print("[bold]Service Status:[/bold] [green]Running[/green]")
    else:
        console.print("[bold]Service Status:[/bold] [red]Stopped[/red]")
    
    console.print()
    
    # Worker status
    result = run_command("supervisorctl status", check=False, silent=True)
    
    if result.returncode == 0 and result.stdout:
        console.print("[bold]Workers:[/bold]")
        console.print()
        
        for line in result.stdout.strip().split('\n'):
            if line:
                # Color code based on status
                if "RUNNING" in line:
                    console.print(f"  [green]●[/green] {line}")
                elif "STOPPED" in line:
                    console.print(f"  [red]●[/red] {line}")
                elif "STARTING" in line or "BACKOFF" in line:
                    console.print(f"  [yellow]●[/yellow] {line}")
                else:
                    console.print(f"  [dim]●[/dim] {line}")
    else:
        console.print("[dim]No workers running.[/dim]")
    
    press_enter_to_continue()
