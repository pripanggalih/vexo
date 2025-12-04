# Phase 1: Refactor Supervisor Module

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor monolithic `modules/supervisor.py` into organized `modules/supervisor/` folder structure while preserving all existing functionality.

**Architecture:** Split existing supervisor.py into separate files by concern (install, worker, control, logs, status) and add common utilities. This sets the foundation for new features in subsequent phases.

**Tech Stack:** Python, subprocess (existing)

---

## Task 1: Create Supervisor Package Structure

**Files:**
- Create: `modules/supervisor/__init__.py`
- Create: `modules/supervisor/common.py`

**Step 1: Create supervisor directory**

```bash
mkdir -p modules/supervisor
```

**Step 2: Create common.py with shared utilities and constants**

```python
"""Common utilities for supervisor module."""

import os
import re

# Constants
SUPERVISOR_CONF_DIR = "/etc/supervisor/conf.d"
SUPERVISOR_LOG_DIR = "/var/log/supervisor"


def validate_worker_name(name):
    """
    Validate worker name (alphanumeric and hyphens only).
    
    Args:
        name: Worker name to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not name:
        return False
    if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$', name):
        return False
    if '--' in name:
        return False
    return True


def get_config_path(worker_name):
    """Get config file path for a worker."""
    return os.path.join(SUPERVISOR_CONF_DIR, f"{worker_name}.conf")


def get_log_path(worker_name):
    """Get log file path for a worker."""
    return os.path.join(SUPERVISOR_LOG_DIR, f"{worker_name}.log")


def worker_exists(worker_name):
    """Check if a worker config already exists."""
    return os.path.exists(get_config_path(worker_name))


def get_all_workers():
    """
    Get list of all supervisor workers (not just vexo-managed).
    
    Returns:
        list: List of worker names
    """
    workers = []
    
    if not os.path.exists(SUPERVISOR_CONF_DIR):
        return workers
    
    for filename in os.listdir(SUPERVISOR_CONF_DIR):
        if filename.endswith('.conf'):
            workers.append(filename[:-5])
    
    return sorted(workers)


def get_vexo_workers():
    """
    Get list of vexo-managed queue workers.
    
    Returns:
        list: List of worker names managed by vexo
    """
    workers = []
    
    if not os.path.exists(SUPERVISOR_CONF_DIR):
        return workers
    
    for filename in os.listdir(SUPERVISOR_CONF_DIR):
        if filename.endswith('.conf'):
            config_path = os.path.join(SUPERVISOR_CONF_DIR, filename)
            try:
                with open(config_path, 'r') as f:
                    content = f.read()
                    # Check for vexo marker or artisan queue:work
                    if '# vexo-managed' in content or 'artisan queue:work' in content or 'artisan horizon' in content:
                        workers.append(filename[:-5])
            except IOError:
                continue
    
    return sorted(workers)


def parse_worker_config(worker_name):
    """
    Parse a worker config file and return its settings.
    
    Args:
        worker_name: Name of the worker
    
    Returns:
        dict: Parsed configuration or None if not found
    """
    config_path = get_config_path(worker_name)
    
    if not os.path.exists(config_path):
        return None
    
    config = {
        'name': worker_name,
        'command': '',
        'user': 'www-data',
        'numprocs': 1,
        'autostart': True,
        'autorestart': True,
        'environment': {},
        'stdout_logfile': '',
        'stdout_logfile_maxbytes': '50MB',
        'stdout_logfile_backups': 5,
    }
    
    try:
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('[') and not line.startswith(';'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key == 'command':
                        config['command'] = value
                    elif key == 'user':
                        config['user'] = value
                    elif key == 'numprocs':
                        config['numprocs'] = int(value)
                    elif key == 'autostart':
                        config['autostart'] = value.lower() == 'true'
                    elif key == 'autorestart':
                        config['autorestart'] = value.lower() == 'true'
                    elif key == 'stdout_logfile':
                        config['stdout_logfile'] = value
                    elif key == 'stdout_logfile_maxbytes':
                        config['stdout_logfile_maxbytes'] = value
                    elif key == 'stdout_logfile_backups':
                        config['stdout_logfile_backups'] = int(value)
                    elif key == 'environment':
                        # Parse environment variables
                        config['environment'] = _parse_env_string(value)
    except (IOError, ValueError):
        pass
    
    return config


def _parse_env_string(env_string):
    """Parse supervisor environment string to dict."""
    env = {}
    if not env_string:
        return env
    
    # Format: KEY="value",KEY2="value2"
    pairs = re.findall(r'(\w+)="([^"]*)"', env_string)
    for key, value in pairs:
        env[key] = value
    
    return env


def format_env_string(env_dict):
    """Format dict to supervisor environment string."""
    if not env_dict:
        return ''
    
    pairs = [f'{key}="{value}"' for key, value in env_dict.items()]
    return ','.join(pairs)
```

**Step 3: Commit**

```bash
git add modules/supervisor/
git commit -m "feat(supervisor): create supervisor package with common utilities"
```

---

## Task 2: Create Install Module

**Files:**
- Create: `modules/supervisor/install.py`

**Step 1: Create install.py**

```python
"""Supervisor installation for vexo."""

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
from ui.menu import confirm_action
from utils.shell import (
    run_command_realtime,
    is_installed,
    is_service_running,
    service_control,
    require_root,
)


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
    console.print("  • Managing queue workers (Laravel, Node.js, Python)")
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
```

**Step 2: Commit**

```bash
git add modules/supervisor/install.py
git commit -m "feat(supervisor): add install module"
```

---

## Task 3: Create Worker Module

**Files:**
- Create: `modules/supervisor/worker.py`

**Step 1: Create worker.py with add/remove functions**

```python
"""Worker management for vexo supervisor."""

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
    from modules.supervisor.common import format_env_string
    
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
```

**Step 2: Commit**

```bash
git add modules/supervisor/worker.py
git commit -m "feat(supervisor): add worker management module"
```

---

## Task 4: Create Control Module

**Files:**
- Create: `modules/supervisor/control.py`

**Step 1: Create control.py**

```python
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
from ui.menu import show_submenu, confirm_action, select_from_list
from utils.shell import run_command, is_installed, require_root

from modules.supervisor.common import get_vexo_workers


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
                ("reload", "5. Reload Configuration"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "start":
            control_worker("start")
        elif choice == "stop":
            control_worker("stop")
        elif choice == "restart":
            control_worker("restart")
        elif choice == "restart_all":
            restart_all_workers()
        elif choice == "reload":
            reload_configuration()
        elif choice == "back" or choice is None:
            break


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
```

**Step 2: Commit**

```bash
git add modules/supervisor/control.py
git commit -m "feat(supervisor): add worker control module"
```

---

## Task 5: Create Logs Module

**Files:**
- Create: `modules/supervisor/logs.py`

**Step 1: Create logs.py**

```python
"""Log viewing for vexo supervisor."""

import os

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_error,
    show_warning,
    press_enter_to_continue,
)
from ui.menu import select_from_list
from utils.shell import run_command, is_installed

from modules.supervisor.common import SUPERVISOR_LOG_DIR, get_vexo_workers, get_log_path


def view_logs():
    """View worker logs."""
    clear_screen()
    show_header()
    show_panel("View Logs", title="Queue Workers", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    workers = get_vexo_workers()
    
    if not workers:
        # Still show supervisord log option
        pass
    
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
        log_path = get_log_path(selection)
    
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
```

**Step 2: Commit**

```bash
git add modules/supervisor/logs.py
git commit -m "feat(supervisor): add logs viewing module"
```

---

## Task 6: Create Status Module

**Files:**
- Create: `modules/supervisor/status.py`

**Step 1: Create status.py**

```python
"""Status display for vexo supervisor."""

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_error,
    press_enter_to_continue,
)
from utils.shell import run_command, is_installed, is_service_running


def show_status():
    """Display Supervisor status."""
    clear_screen()
    show_header()
    show_panel("Supervisor Status", title="Queue Workers", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    if is_service_running("supervisor"):
        console.print("[bold]Service Status:[/bold] [green]Running[/green]")
    else:
        console.print("[bold]Service Status:[/bold] [red]Stopped[/red]")
    
    console.print()
    
    result = run_command("supervisorctl status", check=False, silent=True)
    
    if result.returncode == 0 and result.stdout:
        console.print("[bold]Workers:[/bold]")
        console.print()
        
        for line in result.stdout.strip().split('\n'):
            if line:
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
```

**Step 2: Commit**

```bash
git add modules/supervisor/status.py
git commit -m "feat(supervisor): add status module"
```

---

## Task 7: Create Package Init with Menu

**Files:**
- Modify: `modules/supervisor/__init__.py`

**Step 1: Create __init__.py with menu**

```python
"""Supervisor module for vexo (Queue Workers)."""

from ui.menu import run_menu_loop
from utils.shell import is_installed, is_service_running

from modules.supervisor.install import install_supervisor
from modules.supervisor.worker import add_worker_interactive, remove_worker_interactive, list_workers
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
        "add": add_worker_interactive,
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
git commit -m "feat(supervisor): add package init with menu structure"
```

---

## Task 8: Delete Old Supervisor File

**Files:**
- Delete: `modules/supervisor.py`

**Step 1: Remove old supervisor.py**

```bash
rm modules/supervisor.py
```

**Step 2: Commit**

```bash
git add modules/supervisor.py
git commit -m "refactor(supervisor): remove old monolithic supervisor.py"
```

---

## Summary

After Phase 1, the structure will be:

```
modules/
├── supervisor/
│   ├── __init__.py      # Menu and exports
│   ├── common.py        # Shared utilities and constants
│   ├── install.py       # Installation
│   ├── worker.py        # Add/remove/list workers
│   ├── control.py       # Start/stop/restart
│   ├── logs.py          # Log viewing
│   └── status.py        # Status display
```

All existing functionality preserved, ready for Phase 2-6 additions.
