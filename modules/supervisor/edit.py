"""Edit and clone workers for vexo supervisor."""

import os
import re

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_success,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import run_menu_loop, confirm_action, text_input, select_from_list
from utils.shell import run_command, is_installed, require_root
from utils.error_handler import handle_error

from modules.supervisor.common import (
    get_config_path,
    get_log_path,
    get_vexo_workers,
    parse_worker_config,
    worker_exists,
    validate_worker_name,
)
from modules.supervisor.templates import get_worker_type, TEMPLATE_INFO


def edit_worker_menu():
    """Display edit worker selection and options."""
    clear_screen()
    show_header()
    show_panel("Edit Worker", title="Worker Management", style="cyan")
    
    if not is_installed("supervisor"):
        handle_error("E7002", "Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    workers = get_vexo_workers()
    
    if not workers:
        show_info("No workers configured.")
        press_enter_to_continue()
        return
    
    worker = select_from_list(
        title="Edit Worker",
        message="Select worker to edit:",
        options=workers
    )
    
    if not worker:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    _show_edit_options(worker)


def _show_edit_options(worker_name):
    """Show edit options for a specific worker."""
    while True:
        clear_screen()
        show_header()
        show_panel(f"Edit: {worker_name}", title="Worker Management", style="cyan")
        
        # Load current config
        config = parse_worker_config(worker_name)
        if not config:
            handle_error("E7002", "Failed to parse worker config.")
            press_enter_to_continue()
            return
        
        # Get worker type
        config_path = get_config_path(worker_name)
        try:
            with open(config_path, 'r') as f:
                content = f.read()
        except IOError:
            handle_error("E7002", "Failed to read config file.")
            press_enter_to_continue()
            return
        
        worker_type = get_worker_type(content)
        type_info = TEMPLATE_INFO.get(worker_type, TEMPLATE_INFO['custom'])
        
        # Display current config
        console.print(f"[bold]Worker Type:[/bold] {type_info['name']}")
        cmd_display = config['command'][:60] + "..." if len(config['command']) > 60 else config['command']
        console.print(f"[bold]Command:[/bold] {cmd_display}")
        console.print(f"[bold]User:[/bold] {config['user']}")
        console.print(f"[bold]Processes:[/bold] {config['numprocs']}")
        console.print(f"[bold]Autostart:[/bold] {'Yes' if config['autostart'] else 'No'}")
        console.print(f"[bold]Autorestart:[/bold] {'Yes' if config['autorestart'] else 'No'}")
        console.print()
        
        # Build options based on worker type
        options = [
            ("numprocs", "1. Change Number of Processes"),
            ("user", "2. Change User"),
        ]
        
        if worker_type in ('laravel-queue', 'laravel-priority'):
            options.extend([
                ("queues", "3. Change Queue Names"),
                ("memory", "4. Change Memory Limit"),
                ("connection", "5. Change Connection"),
            ])
        
        options.extend([
            ("autostart", "6. Toggle Autostart"),
            ("autorestart", "7. Toggle Autorestart"),
            ("full", "8. Edit Full Config (Advanced)"),
            ("back", "← Back"),
        ])
        
        handlers = {
            "numprocs": lambda: _edit_numprocs(worker_name, config, content),
            "user": lambda: _edit_user(worker_name, config, content),
            "queues": lambda: _edit_queues(worker_name, config, content),
            "memory": lambda: _edit_memory(worker_name, config, content),
            "connection": lambda: _edit_connection(worker_name, config, content),
            "autostart": lambda: _toggle_autostart(worker_name, config, content),
            "autorestart": lambda: _toggle_autorestart(worker_name, config, content),
            "full": lambda: _edit_full_config(worker_name),
        }
        
        choice = select_from_list(
            title=f"Edit {worker_name}",
            message="Select option:",
            options=[label for _, label in options]
        )
        
        if not choice or choice == "← Back":
            break
        
        # Map label back to key
        for key, label in options:
            if label == choice:
                if key in handlers:
                    handlers[key]()
                break


def _edit_numprocs(worker_name, config, content):
    """Edit number of processes."""
    console.print(f"\n[dim]Current: {config['numprocs']} process(es)[/dim]")
    
    new_value = text_input(
        title="Number of Processes",
        message="Enter new number of processes:",
        default=str(config['numprocs'])
    )
    
    if not new_value:
        return
    
    try:
        numprocs = int(new_value)
        if numprocs < 1:
            raise ValueError()
    except ValueError:
        handle_error("E7002", "Invalid number (must be >= 1).")
        press_enter_to_continue()
        return
    
    # Update config
    new_content = re.sub(
        r'numprocs=\d+',
        f'numprocs={numprocs}',
        content
    )
    
    _save_and_reload(worker_name, new_content, f"Processes set to {numprocs}")


def _edit_user(worker_name, config, content):
    """Edit user."""
    console.print(f"\n[dim]Current: {config['user']}[/dim]")
    
    new_value = text_input(
        title="User",
        message="Enter user to run as:",
        default=config['user']
    )
    
    if not new_value:
        return
    
    new_content = re.sub(
        r'user=\S+',
        f'user={new_value}',
        content
    )
    
    _save_and_reload(worker_name, new_content, f"User set to {new_value}")


def _edit_queues(worker_name, config, content):
    """Edit queue names for Laravel workers."""
    # Extract current queues from command
    match = re.search(r'--queue=([^\s]+)', config['command'])
    current_queues = match.group(1) if match else "default"
    
    console.print(f"\n[dim]Current queues: {current_queues}[/dim]")
    
    new_value = text_input(
        title="Queue Names",
        message="Enter queue names (comma-separated):",
        default=current_queues
    )
    
    if not new_value:
        return
    
    new_content = re.sub(
        r'--queue=[^\s]+',
        f'--queue={new_value}',
        content
    )
    
    _save_and_reload(worker_name, new_content, f"Queues set to {new_value}")


def _edit_memory(worker_name, config, content):
    """Edit memory limit for Laravel workers."""
    # Extract current memory from command
    match = re.search(r'--memory=(\d+)', config['command'])
    current_memory = match.group(1) if match else "128"
    
    console.print(f"\n[dim]Current memory limit: {current_memory} MB[/dim]")
    
    new_value = text_input(
        title="Memory Limit",
        message="Enter memory limit (MB):",
        default=current_memory
    )
    
    if not new_value:
        return
    
    try:
        memory = int(new_value)
        if memory < 32:
            raise ValueError()
    except ValueError:
        handle_error("E7002", "Invalid memory (minimum 32 MB).")
        press_enter_to_continue()
        return
    
    # Check if --memory flag exists
    if '--memory=' in content:
        new_content = re.sub(
            r'--memory=\d+',
            f'--memory={memory}',
            content
        )
    else:
        # Add --memory flag after queue:work
        new_content = re.sub(
            r'(queue:work\s+\S+)',
            f'\\1 --memory={memory}',
            content
        )
    
    _save_and_reload(worker_name, new_content, f"Memory limit set to {memory} MB")


def _edit_connection(worker_name, config, content):
    """Edit queue connection for Laravel workers."""
    # Extract current connection from command
    match = re.search(r'queue:work\s+(\S+)', config['command'])
    current_conn = match.group(1) if match else "database"
    
    console.print(f"\n[dim]Current connection: {current_conn}[/dim]")
    
    new_value = text_input(
        title="Queue Connection",
        message="Enter queue connection:",
        default=current_conn
    )
    
    if not new_value:
        return
    
    new_content = re.sub(
        r'queue:work\s+\S+',
        f'queue:work {new_value}',
        content
    )
    
    _save_and_reload(worker_name, new_content, f"Connection set to {new_value}")


def _toggle_autostart(worker_name, config, content):
    """Toggle autostart setting."""
    new_value = not config['autostart']
    
    new_content = re.sub(
        r'autostart=(true|false)',
        f'autostart={"true" if new_value else "false"}',
        content
    )
    
    _save_and_reload(worker_name, new_content, f"Autostart {'enabled' if new_value else 'disabled'}")


def _toggle_autorestart(worker_name, config, content):
    """Toggle autorestart setting."""
    new_value = not config['autorestart']
    
    new_content = re.sub(
        r'autorestart=(true|false)',
        f'autorestart={"true" if new_value else "false"}',
        content
    )
    
    _save_and_reload(worker_name, new_content, f"Autorestart {'enabled' if new_value else 'disabled'}")


def _edit_full_config(worker_name):
    """Open full config for manual editing."""
    config_path = get_config_path(worker_name)
    
    console.print()
    console.print("[bold yellow]Advanced Edit Mode[/bold yellow]")
    console.print(f"[dim]Config file: {config_path}[/dim]")
    console.print()
    console.print("Use a text editor to modify the config file directly.")
    console.print("After editing, run 'Reload Configuration' from Worker Control menu.")
    console.print()
    
    # Show current content
    if confirm_action("View current config?"):
        with open(config_path, 'r') as f:
            content = f.read()
        console.print()
        console.print(content)
    
    press_enter_to_continue()


def _save_and_reload(worker_name, content, success_msg):
    """Save config and reload supervisor."""
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    config_path = get_config_path(worker_name)
    
    try:
        with open(config_path, 'w') as f:
            f.write(content)
    except IOError as e:
        handle_error("E7002", f"Failed to save config: {e}")
        press_enter_to_continue()
        return
    
    # Reload
    run_command("supervisorctl reread", check=False, silent=True)
    result = run_command(f"supervisorctl update {worker_name}", check=False, silent=True)
    
    if result.returncode == 0:
        show_success(success_msg)
    else:
        show_warning(f"{success_msg} (may need manual restart)")
    
    press_enter_to_continue()


# =============================================================================
# Clone Worker
# =============================================================================

def clone_worker_menu():
    """Clone an existing worker with a new name."""
    clear_screen()
    show_header()
    show_panel("Clone Worker", title="Worker Management", style="cyan")
    
    if not is_installed("supervisor"):
        handle_error("E7002", "Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    workers = get_vexo_workers()
    
    if not workers:
        show_info("No workers configured.")
        press_enter_to_continue()
        return
    
    # Select source worker
    source = select_from_list(
        title="Clone Worker",
        message="Select worker to clone:",
        options=workers
    )
    
    if not source:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Get new name
    console.print(f"\n[dim]Cloning: {source}[/dim]")
    
    new_name = text_input(
        title="New Worker Name",
        message="Enter name for the new worker:",
        default=f"{source}-copy"
    )
    
    if not new_name:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    new_name = new_name.lower().strip().replace(" ", "-")
    
    if not validate_worker_name(new_name):
        handle_error("E7002", "Invalid worker name.")
        press_enter_to_continue()
        return
    
    if worker_exists(new_name):
        handle_error("E7002", f"Worker '{new_name}' already exists.")
        press_enter_to_continue()
        return
    
    # Confirm
    if not confirm_action(f"Clone '{source}' to '{new_name}'?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Read source config
    source_path = get_config_path(source)
    try:
        with open(source_path, 'r') as f:
            content = f.read()
    except IOError as e:
        handle_error("E7002", f"Failed to read source config: {e}")
        press_enter_to_continue()
        return
    
    # Replace worker name in config
    new_content = content.replace(f"[program:{source}]", f"[program:{new_name}]")
    new_content = new_content.replace(f"/{source}.log", f"/{new_name}.log")
    
    # Save new config
    new_path = get_config_path(new_name)
    try:
        with open(new_path, 'w') as f:
            f.write(new_content)
    except IOError as e:
        handle_error("E7002", f"Failed to write new config: {e}")
        press_enter_to_continue()
        return
    
    # Reload
    run_command("supervisorctl reread", check=False, silent=True)
    run_command("supervisorctl update", check=False, silent=True)
    
    show_success(f"Worker '{new_name}' created!")
    console.print()
    console.print(f"[dim]Config: {new_path}[/dim]")
    console.print(f"[dim]Log: {get_log_path(new_name)}[/dim]")
    console.print()
    
    if confirm_action(f"Edit '{new_name}' now?"):
        _show_edit_options(new_name)
    else:
        press_enter_to_continue()
