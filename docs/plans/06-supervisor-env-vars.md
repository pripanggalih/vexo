# Phase 6: Environment Variables Management

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add environment variables management for workers with view, add, edit, remove, and import from .env file.

**Architecture:** Create env.py module that manages the `environment=` directive in supervisor configs. Parse and format environment strings, and import from Laravel .env files.

**Tech Stack:** Python, re (stdlib)

**Prerequisite:** Complete Phase 1 (supervisor package structure)

---

## Task 1: Create Environment Variables Module

**Files:**
- Create: `modules/supervisor/env.py`

**Step 1: Create env.py with environment management functions**

```python
"""Environment variables management for vexo-cli supervisor."""

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
from ui.menu import show_submenu, select_from_list, text_input, confirm_action
from utils.shell import run_command, is_installed, require_root

from modules.supervisor.common import (
    get_vexo_workers,
    get_config_path,
    parse_worker_config,
    format_env_string,
)


def env_menu():
    """Display the environment variables submenu."""
    while True:
        clear_screen()
        show_header()
        
        choice = show_submenu(
            title="Environment Variables",
            options=[
                ("view", "1. View Env Vars"),
                ("add", "2. Add Variable"),
                ("edit", "3. Edit Variable"),
                ("remove", "4. Remove Variable"),
                ("import", "5. Import from .env"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "view":
            view_env_vars()
        elif choice == "add":
            add_env_var()
        elif choice == "edit":
            edit_env_var()
        elif choice == "remove":
            remove_env_var()
        elif choice == "import":
            import_from_dotenv()
        elif choice == "back" or choice is None:
            break


def _select_worker():
    """Helper to select a worker."""
    workers = get_vexo_workers()
    
    if not workers:
        show_info("No workers configured.")
        press_enter_to_continue()
        return None
    
    return select_from_list(
        title="Select Worker",
        message="Select worker:",
        options=workers
    )


def _get_env_vars(worker_name):
    """Get environment variables from worker config."""
    config_path = get_config_path(worker_name)
    
    if not os.path.exists(config_path):
        return {}
    
    try:
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Find environment= line
        match = re.search(r'environment=(.+)', content)
        if not match:
            return {}
        
        env_str = match.group(1).strip()
        
        # Parse KEY="value",KEY2="value2" format
        env_vars = {}
        pairs = re.findall(r'(\w+)="([^"]*)"', env_str)
        for key, value in pairs:
            env_vars[key] = value
        
        return env_vars
    
    except IOError:
        return {}


def _save_env_vars(worker_name, env_vars):
    """Save environment variables to worker config."""
    config_path = get_config_path(worker_name)
    
    try:
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Format env vars
        if env_vars:
            env_str = format_env_string(env_vars)
            env_line = f'environment={env_str}'
        else:
            env_line = ''
        
        # Check if environment= line exists
        if 'environment=' in content:
            if env_vars:
                content = re.sub(r'environment=.+', env_line, content)
            else:
                # Remove environment line
                content = re.sub(r'environment=.+\n?', '', content)
        else:
            if env_vars:
                # Add before last line (or at end of [program] section)
                content = content.rstrip() + f'\n{env_line}\n'
        
        with open(config_path, 'w') as f:
            f.write(content)
        
        # Reload supervisor
        run_command("supervisorctl reread", check=False, silent=True)
        run_command(f"supervisorctl update {worker_name}", check=False, silent=True)
        
        return True
    
    except IOError as e:
        show_error(f"Failed to save config: {e}")
        return False


def view_env_vars():
    """View environment variables for a worker."""
    clear_screen()
    show_header()
    show_panel("View Environment Variables", title="Env Vars", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    worker = _select_worker()
    if not worker:
        return
    
    env_vars = _get_env_vars(worker)
    
    clear_screen()
    show_header()
    show_panel(f"Env Vars: {worker}", title="Environment Variables", style="cyan")
    
    if not env_vars:
        show_info("No environment variables configured.")
        console.print()
        console.print("[dim]Use 'Add Variable' or 'Import from .env' to add variables.[/dim]")
    else:
        columns = [
            {"name": "Variable", "style": "cyan"},
            {"name": "Value"},
        ]
        
        rows = []
        for key, value in sorted(env_vars.items()):
            # Mask sensitive values
            if any(s in key.lower() for s in ['password', 'secret', 'key', 'token']):
                display_value = '*' * min(len(value), 8) if value else '(empty)'
            else:
                display_value = value if len(value) <= 40 else value[:37] + '...'
            
            rows.append([key, display_value])
        
        show_table(f"{len(env_vars)} variable(s)", columns, rows)
    
    press_enter_to_continue()


def add_env_var():
    """Add a new environment variable."""
    clear_screen()
    show_header()
    show_panel("Add Environment Variable", title="Env Vars", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    worker = _select_worker()
    if not worker:
        return
    
    # Get variable name
    var_name = text_input(
        title="Variable Name",
        message="Enter variable name (e.g., APP_ENV):"
    )
    
    if not var_name:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    var_name = var_name.upper().strip()
    
    # Validate name
    if not re.match(r'^[A-Z][A-Z0-9_]*$', var_name):
        show_error("Invalid variable name. Use uppercase letters, numbers, and underscores.")
        press_enter_to_continue()
        return
    
    # Check if exists
    env_vars = _get_env_vars(worker)
    if var_name in env_vars:
        show_warning(f"Variable '{var_name}' already exists. Use 'Edit Variable' to change it.")
        press_enter_to_continue()
        return
    
    # Get value
    var_value = text_input(
        title="Variable Value",
        message=f"Enter value for {var_name}:"
    )
    
    if var_value is None:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Confirm
    console.print()
    console.print(f"[bold]Add variable:[/bold] {var_name}={var_value}")
    
    if not confirm_action("Add this variable?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    env_vars[var_name] = var_value
    
    if _save_env_vars(worker, env_vars):
        show_success(f"Variable '{var_name}' added!")
        console.print("[dim]Note: Restart worker for changes to take effect.[/dim]")
    
    press_enter_to_continue()


def edit_env_var():
    """Edit an existing environment variable."""
    clear_screen()
    show_header()
    show_panel("Edit Environment Variable", title="Env Vars", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    worker = _select_worker()
    if not worker:
        return
    
    env_vars = _get_env_vars(worker)
    
    if not env_vars:
        show_info("No environment variables to edit.")
        press_enter_to_continue()
        return
    
    # Select variable
    var_name = select_from_list(
        title="Edit Variable",
        message="Select variable to edit:",
        options=list(sorted(env_vars.keys()))
    )
    
    if not var_name:
        return
    
    current_value = env_vars[var_name]
    
    console.print(f"\n[dim]Current value: {current_value}[/dim]")
    
    # Get new value
    new_value = text_input(
        title="New Value",
        message=f"Enter new value for {var_name}:",
        default=current_value
    )
    
    if new_value is None:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if new_value == current_value:
        show_info("No changes made.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    env_vars[var_name] = new_value
    
    if _save_env_vars(worker, env_vars):
        show_success(f"Variable '{var_name}' updated!")
        console.print("[dim]Note: Restart worker for changes to take effect.[/dim]")
    
    press_enter_to_continue()


def remove_env_var():
    """Remove an environment variable."""
    clear_screen()
    show_header()
    show_panel("Remove Environment Variable", title="Env Vars", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    worker = _select_worker()
    if not worker:
        return
    
    env_vars = _get_env_vars(worker)
    
    if not env_vars:
        show_info("No environment variables to remove.")
        press_enter_to_continue()
        return
    
    # Select variable
    var_name = select_from_list(
        title="Remove Variable",
        message="Select variable to remove:",
        options=list(sorted(env_vars.keys()))
    )
    
    if not var_name:
        return
    
    if not confirm_action(f"Remove variable '{var_name}'?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    del env_vars[var_name]
    
    if _save_env_vars(worker, env_vars):
        show_success(f"Variable '{var_name}' removed!")
        console.print("[dim]Note: Restart worker for changes to take effect.[/dim]")
    
    press_enter_to_continue()


def import_from_dotenv():
    """Import environment variables from a .env file."""
    clear_screen()
    show_header()
    show_panel("Import from .env", title="Env Vars", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    worker = _select_worker()
    if not worker:
        return
    
    # Get Laravel path from worker config
    config = parse_worker_config(worker)
    default_path = "/var/www/html/.env"
    
    if config and config.get('command'):
        # Try to extract path from command
        match = re.search(r'(/\S+)/artisan', config['command'])
        if match:
            default_path = f"{match.group(1)}/.env"
    
    # Get .env path
    env_path = text_input(
        title=".env Path",
        message="Enter path to .env file:",
        default=default_path
    )
    
    if not env_path:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not os.path.exists(env_path):
        show_error(f"File not found: {env_path}")
        press_enter_to_continue()
        return
    
    # Parse .env file
    dotenv_vars = _parse_dotenv(env_path)
    
    if not dotenv_vars:
        show_info("No variables found in .env file.")
        press_enter_to_continue()
        return
    
    # Show variables for selection
    clear_screen()
    show_header()
    show_panel("Select Variables to Import", title="Import from .env", style="cyan")
    
    console.print(f"[dim]Found {len(dotenv_vars)} variables in {env_path}[/dim]")
    console.print()
    
    # Get current env vars
    current_vars = _get_env_vars(worker)
    
    # Common variables to suggest
    common_vars = [
        'APP_ENV', 'APP_DEBUG', 'APP_URL',
        'DB_CONNECTION', 'DB_HOST', 'DB_DATABASE',
        'REDIS_HOST', 'REDIS_PORT',
        'QUEUE_CONNECTION', 'QUEUE_DRIVER',
        'MAIL_MAILER', 'MAIL_HOST',
    ]
    
    # Filter to available vars
    available_common = [v for v in common_vars if v in dotenv_vars]
    
    if available_common:
        console.print("[bold]Suggested variables:[/bold]")
        for var in available_common:
            exists = " [dim](exists)[/dim]" if var in current_vars else ""
            console.print(f"  • {var}{exists}")
        console.print()
    
    # Import options
    choice = show_submenu(
        title="Import Options",
        options=[
            ("common", "1. Import suggested variables only"),
            ("select", "2. Select variables manually"),
            ("all", "3. Import all variables"),
            ("back", "← Cancel"),
        ]
    )
    
    if choice == "back" or choice is None:
        return
    
    vars_to_import = {}
    
    if choice == "common":
        vars_to_import = {k: dotenv_vars[k] for k in available_common if k in dotenv_vars}
    elif choice == "all":
        vars_to_import = dotenv_vars.copy()
    elif choice == "select":
        vars_to_import = _select_vars_to_import(dotenv_vars, current_vars)
    
    if not vars_to_import:
        show_info("No variables selected.")
        press_enter_to_continue()
        return
    
    # Confirm
    console.print()
    console.print(f"[bold]Import {len(vars_to_import)} variable(s):[/bold]")
    for var in sorted(vars_to_import.keys())[:10]:
        console.print(f"  • {var}")
    if len(vars_to_import) > 10:
        console.print(f"  ... and {len(vars_to_import) - 10} more")
    console.print()
    
    if not confirm_action("Import these variables?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Merge with existing
    current_vars.update(vars_to_import)
    
    if _save_env_vars(worker, current_vars):
        show_success(f"Imported {len(vars_to_import)} variable(s)!")
        console.print("[dim]Note: Restart worker for changes to take effect.[/dim]")
    
    press_enter_to_continue()


def _parse_dotenv(filepath):
    """Parse a .env file and return dict of variables."""
    env_vars = {}
    
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse KEY=value
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # Skip empty keys
                    if key:
                        env_vars[key] = value
    
    except IOError:
        pass
    
    return env_vars


def _select_vars_to_import(dotenv_vars, current_vars):
    """Interactive selection of variables to import."""
    selected = {}
    
    console.print("[dim]Enter variable names to import (comma-separated), or 'list' to see all:[/dim]")
    
    user_input = text_input(
        title="Variables",
        message="Enter variable names:",
        default=""
    )
    
    if not user_input:
        return {}
    
    if user_input.lower() == 'list':
        console.print("\n[bold]Available variables:[/bold]")
        for var in sorted(dotenv_vars.keys()):
            exists = " [dim](exists)[/dim]" if var in current_vars else ""
            console.print(f"  {var}{exists}")
        
        user_input = text_input(
            title="Variables",
            message="Enter variable names to import:",
            default=""
        )
        
        if not user_input:
            return {}
    
    # Parse comma-separated names
    names = [n.strip().upper() for n in user_input.split(',')]
    
    for name in names:
        if name in dotenv_vars:
            selected[name] = dotenv_vars[name]
        else:
            console.print(f"[yellow]Variable '{name}' not found in .env[/yellow]")
    
    return selected
```

**Step 2: Commit**

```bash
git add modules/supervisor/env.py
git commit -m "feat(supervisor): add environment variables management"
```

---

## Task 2: Update Package Init with Env Menu

**Files:**
- Modify: `modules/supervisor/__init__.py`

**Step 1: Update __init__.py to include env menu**

```python
"""Supervisor module for vexo-cli (Queue Workers)."""

from ui.menu import run_menu_loop, show_submenu
from utils.shell import is_installed, is_service_running

from modules.supervisor.install import install_supervisor
from modules.supervisor.add_worker import add_worker_menu
from modules.supervisor.worker import remove_worker_interactive, list_workers
from modules.supervisor.edit import edit_worker_menu, clone_worker_menu
from modules.supervisor.control import worker_control_menu
from modules.supervisor.monitor import monitoring_menu
from modules.supervisor.logs import logs_menu
from modules.supervisor.env import env_menu
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
        "control": worker_control_menu,
        "monitor": monitoring_menu,
        "logs": logs_menu,
        "env": env_menu,
        "status": show_status,
    }
    
    run_menu_loop("Supervisor (Queue Workers)", get_options, handlers, get_status)


def worker_management_menu():
    """Submenu for worker management operations."""
    from ui.components import clear_screen, show_header
    
    while True:
        clear_screen()
        show_header()
        
        choice = show_submenu(
            title="Worker Management",
            options=[
                ("add", "1. Add Worker"),
                ("edit", "2. Edit Worker"),
                ("clone", "3. Clone Worker"),
                ("remove", "4. Remove Worker"),
                ("list", "5. List Workers"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "add":
            add_worker_menu()
        elif choice == "edit":
            edit_worker_menu()
        elif choice == "clone":
            clone_worker_menu()
        elif choice == "remove":
            remove_worker_interactive()
        elif choice == "list":
            list_workers()
        elif choice == "back" or choice is None:
            break
```

**Step 2: Final commit**

```bash
git add modules/supervisor/__init__.py
git commit -m "feat(supervisor): integrate environment variables menu - complete supervisor enhancement"
```

---

## Summary

After Phase 6, the environment variables system will have:

**View Env Vars:**
- List all variables for a worker
- Mask sensitive values (password, secret, key, token)

**Add Variable:**
- Validate variable name format
- Check for duplicates

**Edit Variable:**
- Select from existing variables
- Update value

**Remove Variable:**
- Select and confirm removal

**Import from .env:**
- Auto-detect Laravel project path
- Parse .env file
- Suggest common variables
- Select variables manually or import all
- Merge with existing variables

Files added/modified:
- `modules/supervisor/env.py` (new)
- `modules/supervisor/__init__.py` (updated)

---

## Final Project Structure

After completing all 6 phases:

```
modules/
├── supervisor/
│   ├── __init__.py       # Main menu & submenus
│   ├── common.py         # Shared utilities
│   ├── install.py        # Installation
│   ├── worker.py         # List/remove workers
│   ├── add_worker.py     # Add worker wizards
│   ├── templates.py      # Config templates
│   ├── edit.py           # Edit/clone workers
│   ├── control.py        # Start/stop/restart
│   ├── monitor.py        # Status/stats/dashboard
│   ├── logs.py           # Advanced logging
│   ├── env.py            # Environment variables
│   └── status.py         # Status display
```

**Full Menu Structure:**
```
Supervisor (Queue Workers)
├── 1. Worker Management
│      ├── Add Worker (Queue, Horizon, Priority, Custom)
│      ├── Edit Worker
│      ├── Clone Worker
│      ├── Remove Worker
│      └── List Workers
├── 2. Worker Control
│      ├── Start/Stop/Restart Worker
│      ├── Restart All Workers
│      └── Reload Configuration
├── 3. Monitoring
│      ├── Worker Status (CPU, Memory, Uptime)
│      ├── Queue Statistics
│      └── Live Dashboard
├── 4. Logs
│      ├── View Logs
│      ├── Tail Realtime
│      ├── Filter by Level
│      ├── Search Logs
│      └── Log Settings
├── 5. Environment Variables
│      ├── View Env Vars
│      ├── Add/Edit/Remove Variable
│      └── Import from .env
├── 6. Show Status
└── ← Back
```
