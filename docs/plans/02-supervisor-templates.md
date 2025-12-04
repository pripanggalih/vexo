# Phase 2: Worker Templates

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add worker templates for Laravel Queue Worker, Laravel Horizon, Priority Queue Worker, and Custom Command.

**Architecture:** Create templates.py module with config generators for each worker type. Update worker.py to use template selection menu instead of hardcoded Laravel queue config.

**Tech Stack:** Python, subprocess (existing)

**Prerequisite:** Complete Phase 1 (supervisor package structure)

---

## Task 1: Create Templates Module

**Files:**
- Create: `modules/supervisor/templates.py`

**Step 1: Create templates.py with all template generators**

```python
"""Worker config templates for vexo-cli supervisor."""

from modules.supervisor.common import SUPERVISOR_LOG_DIR, format_env_string


def generate_laravel_queue_config(name, laravel_path, connection="database", queues="default",
                                   numprocs=1, user="www-data", memory=128, 
                                   sleep=3, tries=3, max_time=3600, env_vars=None):
    """
    Generate Laravel queue:work worker config.
    
    Args:
        name: Worker name
        laravel_path: Path to Laravel project
        connection: Queue connection (database, redis, sqs, etc.)
        queues: Queue names (comma-separated)
        numprocs: Number of worker processes
        user: System user to run as
        memory: Memory limit in MB
        sleep: Sleep seconds when no jobs
        tries: Number of retry attempts
        max_time: Maximum job runtime in seconds
        env_vars: Optional environment variables dict
    
    Returns:
        str: Supervisor config content
    """
    env_line = ""
    if env_vars:
        env_line = f"environment={format_env_string(env_vars)}\n"
    
    return f"""# vexo-managed: laravel-queue
[program:{name}]
process_name=%(program_name)s_%(process_num)02d
command=php {laravel_path}/artisan queue:work {connection} --queue={queues} --sleep={sleep} --tries={tries} --max-time={max_time} --memory={memory}
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
stopwaitsecs={max_time}
{env_line}"""


def generate_laravel_horizon_config(name, laravel_path, user="www-data", env_vars=None):
    """
    Generate Laravel Horizon worker config.
    
    Args:
        name: Worker name
        laravel_path: Path to Laravel project
        user: System user to run as
        env_vars: Optional environment variables dict
    
    Returns:
        str: Supervisor config content
    """
    env_line = ""
    if env_vars:
        env_line = f"environment={format_env_string(env_vars)}\n"
    
    return f"""# vexo-managed: laravel-horizon
[program:{name}]
process_name=%(program_name)s
command=php {laravel_path}/artisan horizon
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
user={user}
numprocs=1
redirect_stderr=true
stdout_logfile={SUPERVISOR_LOG_DIR}/{name}.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=5
stopwaitsecs=3600
{env_line}"""


def generate_priority_queue_config(name, laravel_path, connection="database",
                                    high_queue="high", default_queue="default", 
                                    low_queue="low", numprocs=1, user="www-data",
                                    memory=128, env_vars=None):
    """
    Generate Laravel priority queue worker config.
    
    Args:
        name: Worker name
        laravel_path: Path to Laravel project
        connection: Queue connection
        high_queue: High priority queue name
        default_queue: Default priority queue name
        low_queue: Low priority queue name
        numprocs: Number of worker processes
        user: System user to run as
        memory: Memory limit in MB
        env_vars: Optional environment variables dict
    
    Returns:
        str: Supervisor config content
    """
    queues = f"{high_queue},{default_queue},{low_queue}"
    
    env_line = ""
    if env_vars:
        env_line = f"environment={format_env_string(env_vars)}\n"
    
    return f"""# vexo-managed: laravel-priority
[program:{name}]
process_name=%(program_name)s_%(process_num)02d
command=php {laravel_path}/artisan queue:work {connection} --queue={queues} --sleep=3 --tries=3 --max-time=3600 --memory={memory}
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


def generate_custom_command_config(name, command, working_dir=None, user="www-data",
                                    numprocs=1, autostart=True, autorestart=True,
                                    env_vars=None):
    """
    Generate custom command worker config.
    
    Args:
        name: Worker name
        command: Full command to execute
        working_dir: Working directory (optional)
        user: System user to run as
        numprocs: Number of processes
        autostart: Start on supervisor start
        autorestart: Restart on exit
        env_vars: Optional environment variables dict
    
    Returns:
        str: Supervisor config content
    """
    env_line = ""
    if env_vars:
        env_line = f"environment={format_env_string(env_vars)}\n"
    
    dir_line = ""
    if working_dir:
        dir_line = f"directory={working_dir}\n"
    
    process_name = "%(program_name)s_%(process_num)02d" if numprocs > 1 else "%(program_name)s"
    
    return f"""# vexo-managed: custom
[program:{name}]
process_name={process_name}
command={command}
{dir_line}autostart={'true' if autostart else 'false'}
autorestart={'true' if autorestart else 'false'}
stopasgroup=true
killasgroup=true
user={user}
numprocs={numprocs}
redirect_stderr=true
stdout_logfile={SUPERVISOR_LOG_DIR}/{name}.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=5
stopwaitsecs=60
{env_line}"""


def get_worker_type(config_content):
    """
    Detect worker type from config content.
    
    Args:
        config_content: Config file content
    
    Returns:
        str: Worker type ('laravel-queue', 'laravel-horizon', 'laravel-priority', 'custom')
    """
    if '# vexo-managed: laravel-horizon' in config_content:
        return 'laravel-horizon'
    elif '# vexo-managed: laravel-priority' in config_content:
        return 'laravel-priority'
    elif '# vexo-managed: laravel-queue' in config_content:
        return 'laravel-queue'
    elif '# vexo-managed: custom' in config_content:
        return 'custom'
    elif 'artisan horizon' in config_content:
        return 'laravel-horizon'
    elif 'artisan queue:work' in config_content:
        return 'laravel-queue'
    else:
        return 'custom'


TEMPLATE_INFO = {
    'laravel-queue': {
        'name': 'Laravel Queue Worker',
        'description': 'Standard queue:work for processing jobs',
        'icon': '📦',
    },
    'laravel-horizon': {
        'name': 'Laravel Horizon',
        'description': 'Horizon dashboard for Redis queues',
        'icon': '🌅',
    },
    'laravel-priority': {
        'name': 'Priority Queue Worker',
        'description': 'High/default/low priority queues',
        'icon': '⚡',
    },
    'custom': {
        'name': 'Custom Command',
        'description': 'Any shell command or script',
        'icon': '🔧',
    },
}
```

**Step 2: Commit**

```bash
git add modules/supervisor/templates.py
git commit -m "feat(supervisor): add worker config templates"
```

---

## Task 2: Create Add Worker Menu

**Files:**
- Create: `modules/supervisor/add_worker.py`

**Step 1: Create add_worker.py with template selection**

```python
"""Add worker wizards for vexo-cli supervisor."""

import os

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
from ui.menu import show_submenu, confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, is_installed, require_root

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


def add_worker_menu():
    """Display add worker type selection menu."""
    while True:
        clear_screen()
        show_header()
        
        choice = show_submenu(
            title="Add Worker",
            options=[
                ("laravel_queue", "1. Laravel Queue Worker"),
                ("laravel_horizon", "2. Laravel Horizon"),
                ("priority_queue", "3. Priority Queue Worker"),
                ("custom", "4. Custom Command"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "laravel_queue":
            add_laravel_queue_worker()
        elif choice == "laravel_horizon":
            add_laravel_horizon_worker()
        elif choice == "priority_queue":
            add_priority_queue_worker()
        elif choice == "custom":
            add_custom_worker()
        elif choice == "back" or choice is None:
            break


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
        show_error("Invalid worker name. Use only letters, numbers, and hyphens.")
        press_enter_to_continue()
        return None
    
    if worker_exists(worker_name):
        show_error(f"Worker '{worker_name}' already exists.")
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
        show_error(f"Laravel artisan not found at {laravel_path}")
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
        show_error(f"Failed to write config: {e}")
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
        show_error("Supervisor is not installed.")
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
        show_error("Invalid number of processes.")
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
        show_error("Invalid memory limit (minimum 32 MB).")
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
        show_error("Failed to create worker.")
    
    press_enter_to_continue()


def add_laravel_horizon_worker():
    """Add a Laravel Horizon worker."""
    clear_screen()
    show_header()
    show_panel("Laravel Horizon", title="Add Worker", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Laravel Horizon Requirements:[/bold]")
    console.print("  • Redis must be configured as queue driver")
    console.print("  • Horizon package must be installed")
    console.print("  • Only ONE Horizon process should run")
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
        show_error("Failed to create worker.")
    
    press_enter_to_continue()


def add_priority_queue_worker():
    """Add a priority queue worker (high/default/low)."""
    clear_screen()
    show_header()
    show_panel("Priority Queue Worker", title="Add Worker", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
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
        show_error("Invalid number of processes.")
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
        show_error("Failed to create worker.")
    
    press_enter_to_continue()


def add_custom_worker():
    """Add a custom command worker."""
    clear_screen()
    show_header()
    show_panel("Custom Command Worker", title="Add Worker", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
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
        show_error("Invalid number of processes.")
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
        show_error("Failed to create worker.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/supervisor/add_worker.py
git commit -m "feat(supervisor): add worker creation wizards for all templates"
```

---

## Task 3: Update Package Init

**Files:**
- Modify: `modules/supervisor/__init__.py`

**Step 1: Update __init__.py to use new add_worker menu**

```python
"""Supervisor module for vexo-cli (Queue Workers)."""

from ui.menu import run_menu_loop
from utils.shell import is_installed, is_service_running

from modules.supervisor.install import install_supervisor
from modules.supervisor.add_worker import add_worker_menu
from modules.supervisor.worker import remove_worker_interactive, list_workers
from modules.supervisor.control import worker_control_menu
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
        "add": add_worker_menu,
        "remove": remove_worker_interactive,
        "list": list_workers,
        "control": worker_control_menu,
        "logs": view_logs,
        "status": show_status,
    }
    
    run_menu_loop("Supervisor (Queue Workers)", get_options, handlers, get_status)
```

**Step 2: Commit**

```bash
git add modules/supervisor/__init__.py
git commit -m "feat(supervisor): integrate add worker menu with templates"
```

---

## Summary

After Phase 2, the supervisor module will have:

- **Laravel Queue Worker:** Standard queue:work with configurable memory, sleep, tries, max-time
- **Laravel Horizon:** Single process Horizon with Redis queue management
- **Priority Queue Worker:** High/default/low priority queue processing
- **Custom Command:** Any shell command as supervised process

Each template includes:
- `# vexo-managed: <type>` marker for identification
- Configurable log rotation (50MB, 5 backups)
- Proper stop wait times
- Environment variable support

Files added/modified:
- `modules/supervisor/templates.py` (new)
- `modules/supervisor/add_worker.py` (new)
- `modules/supervisor/__init__.py` (updated)
