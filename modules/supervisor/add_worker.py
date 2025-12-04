"""Add worker wizards for vexo supervisor."""

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
from ui.menu import run_menu_loop, confirm_action, text_input, select_from_list
from utils.shell import run_command, is_installed, require_root
from utils.error_handler import handle_error

from modules.supervisor.common import (
    validate_worker_name,
    get_config_path,
    get_log_path,
    worker_exists,
)
from modules.supervisor.templates import (
    generate_laravel_queue_config,
    generate_laravel_horizon_config,
    generate_priority_queue_config,
    generate_custom_command_config,
    TEMPLATE_INFO,
)


def show_menu():
    """Display add worker type selection menu."""
    options = [
        ("laravel_queue", "1. Laravel Queue Worker"),
        ("laravel_horizon", "2. Laravel Horizon"),
        ("priority_queue", "3. Priority Queue Worker"),
        ("custom", "4. Custom Command"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "laravel_queue": add_laravel_queue_worker,
        "laravel_horizon": add_laravel_horizon_worker,
        "priority_queue": add_priority_queue_worker,
        "custom": add_custom_worker,
    }
    
    run_menu_loop("Add Worker", options, handlers)


def _get_worker_name(default_suffix="queue"):
    """Get and validate worker name from user."""
    worker_name = text_input(
        title="Worker Name",
        message=f"Enter worker name (e.g., myapp-{default_suffix}):"
    )
    
    if not worker_name:
        return None
    
    worker_name = worker_name.lower().strip().replace(" ", "-")
    
    if not validate_worker_name(worker_name):
        handle_error("E7002", "Invalid worker name. Use only letters, numbers, and hyphens.")
        press_enter_to_continue()
        return None
    
    if worker_exists(worker_name):
        handle_error("E7002", f"Worker '{worker_name}' already exists.")
        press_enter_to_continue()
        return None
    
    return worker_name


def _get_laravel_path():
    """Get and validate Laravel path from user."""
    laravel_path = text_input(
        title="Laravel Path",
        message="Enter Laravel project path:",
        default="/var/www/html"
    )
    
    if not laravel_path:
        return None
    
    artisan_path = os.path.join(laravel_path, "artisan")
    if not os.path.exists(artisan_path):
        handle_error("E7002", f"Laravel artisan not found at {laravel_path}")
        press_enter_to_continue()
        return None
    
    return laravel_path


def _save_worker_config(name, config_content):
    """Save worker config and reload supervisor."""
    config_path = get_config_path(name)
    
    try:
        with open(config_path, 'w') as f:
            f.write(config_content)
    except IOError as e:
        handle_error("E7002", f"Failed to write config: {e}")
        return False
    
    result = run_command("supervisorctl reread", check=False, silent=True)
    if result.returncode != 0:
        return False
    
    result = run_command("supervisorctl update", check=False, silent=True)
    return result.returncode == 0


def add_laravel_queue_worker():
    """Add a Laravel queue:work worker."""
    clear_screen()
    show_header()
    show_panel("Laravel Queue Worker", title="Add Worker", style="cyan")
    
    if not is_installed("supervisor"):
        handle_error("E7002", "Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    # Worker name
    worker_name = _get_worker_name("queue")
    if not worker_name:
        return
    
    # Laravel path
    laravel_path = _get_laravel_path()
    if not laravel_path:
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
    numprocs_str = text_input(
        title="Processes",
        message="Enter number of worker processes:",
        default="1"
    )
    if not numprocs_str:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        numprocs = int(numprocs_str)
        if numprocs < 1:
            raise ValueError()
    except ValueError:
        handle_error("E7002", "Invalid number of processes.")
        press_enter_to_continue()
        return
    
    # Memory limit
    memory_str = text_input(
        title="Memory Limit",
        message="Enter memory limit (MB):",
        default="128"
    )
    if not memory_str:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        memory = int(memory_str)
        if memory < 32:
            raise ValueError()
    except ValueError:
        handle_error("E7002", "Invalid memory limit (minimum 32 MB).")
        press_enter_to_continue()
        return
    
    # Summary
    console.print()
    console.print("[bold]Worker Configuration:[/bold]")
    console.print(f"  Type: Laravel Queue Worker")
    console.print(f"  Name: {worker_name}")
    console.print(f"  Laravel Path: {laravel_path}")
    console.print(f"  Connection: {connection}")
    console.print(f"  Queues: {queues}")
    console.print(f"  Processes: {numprocs}")
    console.print(f"  Memory: {memory} MB")
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
    
    config = generate_laravel_queue_config(
        name=worker_name,
        laravel_path=laravel_path,
        connection=connection,
        queues=queues,
        numprocs=numprocs,
        memory=memory,
    )
    
    if _save_worker_config(worker_name, config):
        show_success(f"Worker '{worker_name}' created!")
        console.print()
        console.print(f"[dim]Config: {get_config_path(worker_name)}[/dim]")
        console.print(f"[dim]Log: {get_log_path(worker_name)}[/dim]")
    else:
        handle_error("E7002", "Failed to create worker.")
    
    press_enter_to_continue()


def add_laravel_horizon_worker():
    """Add a Laravel Horizon worker."""
    clear_screen()
    show_header()
    show_panel("Laravel Horizon", title="Add Worker", style="cyan")
    
    if not is_installed("supervisor"):
        handle_error("E7002", "Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Laravel Horizon Requirements:[/bold]")
    console.print("  - Redis must be configured as queue driver")
    console.print("  - Horizon package must be installed")
    console.print("  - Only ONE Horizon process should run")
    console.print()
    
    # Worker name
    worker_name = _get_worker_name("horizon")
    if not worker_name:
        return
    
    # Laravel path
    laravel_path = _get_laravel_path()
    if not laravel_path:
        return
    
    # Check for Horizon
    horizon_config = os.path.join(laravel_path, "config", "horizon.php")
    if not os.path.exists(horizon_config):
        show_warning("Horizon config not found. Make sure Horizon is installed.")
        if not confirm_action("Continue anyway?"):
            return
    
    # Summary
    console.print()
    console.print("[bold]Worker Configuration:[/bold]")
    console.print(f"  Type: Laravel Horizon")
    console.print(f"  Name: {worker_name}")
    console.print(f"  Laravel Path: {laravel_path}")
    console.print(f"  Processes: 1 (Horizon manages workers internally)")
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
    
    config = generate_laravel_horizon_config(
        name=worker_name,
        laravel_path=laravel_path,
    )
    
    if _save_worker_config(worker_name, config):
        show_success(f"Worker '{worker_name}' created!")
        console.print()
        console.print(f"[dim]Config: {get_config_path(worker_name)}[/dim]")
        console.print(f"[dim]Log: {get_log_path(worker_name)}[/dim]")
        console.print()
        console.print("[cyan]Tip: Access Horizon dashboard at /horizon[/cyan]")
    else:
        handle_error("E7002", "Failed to create worker.")
    
    press_enter_to_continue()


def add_priority_queue_worker():
    """Add a priority queue worker (high/default/low)."""
    clear_screen()
    show_header()
    show_panel("Priority Queue Worker", title="Add Worker", style="cyan")
    
    if not is_installed("supervisor"):
        handle_error("E7002", "Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Priority Queue Info:[/bold]")
    console.print("  Jobs dispatched to 'high' queue process first,")
    console.print("  then 'default', then 'low'.")
    console.print()
    
    # Worker name
    worker_name = _get_worker_name("priority")
    if not worker_name:
        return
    
    # Laravel path
    laravel_path = _get_laravel_path()
    if not laravel_path:
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
    high_queue = text_input(title="High Priority Queue", message="High priority queue name:", default="high")
    if not high_queue:
        return
    
    default_queue = text_input(title="Default Queue", message="Default queue name:", default="default")
    if not default_queue:
        return
    
    low_queue = text_input(title="Low Priority Queue", message="Low priority queue name:", default="low")
    if not low_queue:
        return
    
    # Number of processes
    numprocs_str = text_input(title="Processes", message="Number of worker processes:", default="2")
    if not numprocs_str:
        return
    
    try:
        numprocs = int(numprocs_str)
        if numprocs < 1:
            raise ValueError()
    except ValueError:
        handle_error("E7002", "Invalid number of processes.")
        press_enter_to_continue()
        return
    
    # Summary
    console.print()
    console.print("[bold]Worker Configuration:[/bold]")
    console.print(f"  Type: Priority Queue Worker")
    console.print(f"  Name: {worker_name}")
    console.print(f"  Laravel Path: {laravel_path}")
    console.print(f"  Connection: {connection}")
    console.print(f"  Queues: {high_queue},{default_queue},{low_queue}")
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
    
    config = generate_priority_queue_config(
        name=worker_name,
        laravel_path=laravel_path,
        connection=connection,
        high_queue=high_queue,
        default_queue=default_queue,
        low_queue=low_queue,
        numprocs=numprocs,
    )
    
    if _save_worker_config(worker_name, config):
        show_success(f"Worker '{worker_name}' created!")
        console.print()
        console.print(f"[dim]Config: {get_config_path(worker_name)}[/dim]")
    else:
        handle_error("E7002", "Failed to create worker.")
    
    press_enter_to_continue()


def add_custom_worker():
    """Add a custom command worker."""
    clear_screen()
    show_header()
    show_panel("Custom Command Worker", title="Add Worker", style="cyan")
    
    if not is_installed("supervisor"):
        handle_error("E7002", "Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Custom Worker:[/bold]")
    console.print("  Run any command or script as a supervised process.")
    console.print()
    
    # Worker name
    worker_name = _get_worker_name("worker")
    if not worker_name:
        return
    
    # Command
    command = text_input(
        title="Command",
        message="Enter full command to run:",
        default=""
    )
    if not command:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Working directory
    working_dir = text_input(
        title="Working Directory",
        message="Enter working directory (optional):",
        default=""
    )
    
    # User
    user = text_input(
        title="User",
        message="Run as user:",
        default="www-data"
    )
    if not user:
        return
    
    # Number of processes
    numprocs_str = text_input(title="Processes", message="Number of processes:", default="1")
    if not numprocs_str:
        return
    
    try:
        numprocs = int(numprocs_str)
        if numprocs < 1:
            raise ValueError()
    except ValueError:
        handle_error("E7002", "Invalid number of processes.")
        press_enter_to_continue()
        return
    
    # Summary
    console.print()
    console.print("[bold]Worker Configuration:[/bold]")
    console.print(f"  Type: Custom Command")
    console.print(f"  Name: {worker_name}")
    console.print(f"  Command: {command}")
    if working_dir:
        console.print(f"  Working Dir: {working_dir}")
    console.print(f"  User: {user}")
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
    
    config = generate_custom_command_config(
        name=worker_name,
        command=command,
        working_dir=working_dir if working_dir else None,
        user=user,
        numprocs=numprocs,
    )
    
    if _save_worker_config(worker_name, config):
        show_success(f"Worker '{worker_name}' created!")
        console.print()
        console.print(f"[dim]Config: {get_config_path(worker_name)}[/dim]")
    else:
        handle_error("E7002", "Failed to create worker.")
    
    press_enter_to_continue()
