"""Worker management for vexo-cli supervisor."""

import os

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
from ui.menu import confirm_action, text_input, select_from_list
from utils.shell import run_command, is_installed, require_root

from modules.supervisor.common import (
    SUPERVISOR_CONF_DIR,
    SUPERVISOR_LOG_DIR,
    validate_worker_name,
    get_config_path,
    get_log_path,
    worker_exists,
    get_vexo_workers,
    format_env_string,
)


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
    
    if not validate_worker_name(worker_name):
        show_error("Invalid worker name. Use only letters, numbers, and hyphens.")
        press_enter_to_continue()
        return
    
    if worker_exists(worker_name):
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
    
    success = add_laravel_worker(worker_name, laravel_path, connection, queues, numprocs)
    
    if success:
        show_success(f"Worker '{worker_name}' created!")
        console.print()
        console.print(f"[dim]Config: {get_config_path(worker_name)}[/dim]")
        console.print(f"[dim]Log: {get_log_path(worker_name)}[/dim]")
    else:
        show_error("Failed to create worker.")
    
    press_enter_to_continue()


def add_laravel_worker(name, laravel_path, connection, queues, numprocs, user="www-data", env_vars=None):
    """
    Create a new Laravel queue worker config.
    
    Args:
        name: Worker name
        laravel_path: Path to Laravel project
        connection: Queue connection
        queues: Queue names (comma-separated)
        numprocs: Number of processes
        user: System user to run as
        env_vars: Optional environment variables dict
    
    Returns:
        bool: True if successful
    """
    env_line = ""
    if env_vars:
        env_line = f"environment={format_env_string(env_vars)}\n"
    
    config_content = f"""# vexo-managed
[program:{name}]
process_name=%(program_name)s_%(process_num)02d
command=php {laravel_path}/artisan queue:work {connection} --queue={queues} --sleep=3 --tries=3 --max-time=3600
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
user={user}
numprocs={numprocs}
redirect_stderr=true
stdout_logfile={SUPERVISOR_LOG_DIR}/{name}.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=5
stopwaitsecs=3600
{env_line}"""
    
    config_path = get_config_path(name)
    
    try:
        with open(config_path, 'w') as f:
            f.write(config_content)
    except IOError as e:
        show_error(f"Failed to write config: {e}")
        return False
    
    return _reload_supervisor()


def remove_worker_interactive():
    """Interactive prompt to remove a worker."""
    clear_screen()
    show_header()
    show_panel("Remove Worker", title="Queue Workers", style="cyan")
    
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
    run_command(f"supervisorctl stop {name}:*", check=False, silent=True)
    
    config_path = get_config_path(name)
    
    try:
        if os.path.exists(config_path):
            os.remove(config_path)
    except IOError as e:
        show_error(f"Failed to remove config: {e}")
        return False
    
    return _reload_supervisor()


def list_workers():
    """Display all configured workers."""
    clear_screen()
    show_header()
    show_panel("Queue Workers", title="Supervisor", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    workers = get_vexo_workers()
    
    if not workers:
        show_info("No workers configured.")
        console.print()
        console.print("[dim]Use 'Add Worker' to create one.[/dim]")
        press_enter_to_continue()
        return
    
    result = run_command("supervisorctl status", check=False, silent=True)
    status_lines = result.stdout.strip().split('\n') if result.stdout else []
    
    status_map = {}
    for line in status_lines:
        parts = line.split()
        if len(parts) >= 2:
            status_map[parts[0]] = parts[1]
    
    columns = [
        {"name": "Worker", "style": "cyan"},
        {"name": "Processes"},
        {"name": "Status"},
    ]
    
    rows = []
    for worker in workers:
        proc_statuses = [state for key, state in status_map.items() 
                        if key.startswith(f"{worker}:") or key == worker]
        
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


def _reload_supervisor():
    """Reload supervisor configuration."""
    result = run_command("supervisorctl reread", check=False, silent=True)
    if result.returncode != 0:
        return False
    
    result = run_command("supervisorctl update", check=False, silent=True)
    return result.returncode == 0
