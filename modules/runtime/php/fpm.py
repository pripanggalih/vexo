"""PHP-FPM pool management."""

import os
import re

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, service_control, require_root
from utils.error_handler import handle_error
from modules.runtime.php.utils import (
    get_installed_php_versions, get_fpm_pool_path, get_fpm_service_name,
    is_fpm_running, parse_fpm_pool_config, get_server_memory_mb,
)


def show_fpm_menu():
    """Display FPM Management submenu."""
    def get_status():
        versions = get_installed_php_versions()
        running = sum(1 for v in versions if is_fpm_running(v))
        return f"FPM Running: {running}/{len(versions)}"
    
    options = [
        ("status", "1. Pool Status"),
        ("config", "2. Configure Pool"),
        ("service", "3. Service Control"),
        ("create", "4. Create Custom Pool"),
        ("calculator", "5. Memory Calculator"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "status": show_pool_status,
        "config": configure_pool,
        "service": fpm_service_control,
        "create": create_custom_pool,
        "calculator": memory_calculator,
    }
    
    run_menu_loop("FPM Management", options, handlers, get_status)


def show_pool_status():
    """Show status of all PHP-FPM pools."""
    clear_screen()
    show_header()
    show_panel("PHP-FPM Pool Status", title="FPM Management", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_info("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "PHP", "style": "cyan"},
        {"name": "Status", "justify": "center"},
        {"name": "PM Mode", "justify": "center"},
        {"name": "Workers", "justify": "center"},
        {"name": "Max Children", "justify": "right"},
    ]
    
    rows = []
    for version in versions:
        service = get_fpm_service_name(version)
        running = is_fpm_running(version)
        status = "[green]Running[/green]" if running else "[red]Stopped[/red]"
        
        config = parse_fpm_pool_config(version)
        pm_mode = config.get("pm", "dynamic")
        max_children = config.get("pm.max_children", "5")
        
        workers = "-"
        if running:
            result = run_command(
                f"pgrep -c -f 'php-fpm: pool www.*{version}'",
                check=False, silent=True
            )
            if result.returncode == 0:
                workers = result.stdout.strip()
        
        rows.append([f"PHP {version}", status, pm_mode, workers, max_children])
    
    show_table("", columns, rows, show_header=True)
    press_enter_to_continue()


def configure_pool():
    """Configure PHP-FPM pool settings."""
    clear_screen()
    show_header()
    show_panel("Configure FPM Pool", title="FPM Management", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        handle_error("E3001", "No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "Configure pool for:", versions)
    if not version:
        return
    
    config = parse_fpm_pool_config(version)
    
    console.print(f"[bold]Current Pool Settings (PHP {version}):[/bold]")
    console.print()
    console.print(f"  pm = {config.get('pm', 'dynamic')}")
    console.print(f"  pm.max_children = {config.get('pm.max_children', '5')}")
    console.print(f"  pm.start_servers = {config.get('pm.start_servers', '2')}")
    console.print(f"  pm.min_spare_servers = {config.get('pm.min_spare_servers', '1')}")
    console.print(f"  pm.max_spare_servers = {config.get('pm.max_spare_servers', '3')}")
    console.print(f"  pm.max_requests = {config.get('pm.max_requests', '500')}")
    console.print()
    
    settings = [
        "pm (process manager mode)",
        "pm.max_children",
        "pm.start_servers",
        "pm.min_spare_servers",
        "pm.max_spare_servers",
        "pm.max_requests",
    ]
    
    setting = select_from_list("Select Setting", "Which setting to change?", settings)
    if not setting:
        return
    
    setting_key = setting.split(" ")[0]
    
    if setting_key == "pm":
        new_value = select_from_list(
            "PM Mode", "Select process manager mode:",
            ["dynamic", "static", "ondemand"]
        )
    else:
        current = config.get(setting_key, "")
        new_value = text_input(f"Enter new value for {setting_key}:", default=current)
    
    if not new_value:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    config_path = get_fpm_pool_path(version)
    success = _update_pool_config(config_path, setting_key, new_value)
    
    if success:
        show_success(f"Updated {setting_key} = {new_value}")
        console.print()
        if confirm_action("Restart PHP-FPM to apply changes?"):
            service_control(get_fpm_service_name(version), "restart")
            show_success("PHP-FPM restarted!")
    else:
        handle_error("E3001", "Failed to update configuration.")
    
    press_enter_to_continue()


def _update_pool_config(config_path, key, value):
    """Update a single value in pool config file."""
    try:
        with open(config_path, "r") as f:
            lines = f.readlines()
        
        updated = False
        new_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(f"{key} =") or stripped.startswith(f";{key} ="):
                new_lines.append(f"{key} = {value}\n")
                updated = True
            else:
                new_lines.append(line)
        
        if not updated:
            for i, line in enumerate(new_lines):
                if line.strip() == "[www]":
                    new_lines.insert(i + 1, f"{key} = {value}\n")
                    updated = True
                    break
        
        with open(config_path, "w") as f:
            f.writelines(new_lines)
        
        return True
    except Exception as e:
        handle_error("E3001", f"Error updating config: {e}")
        return False


def fpm_service_control():
    """Start/Stop/Restart PHP-FPM services."""
    clear_screen()
    show_header()
    show_panel("FPM Service Control", title="FPM Management", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        handle_error("E3001", "No PHP versions installed.")
        press_enter_to_continue()
        return
    
    for version in versions:
        status = "[green]Running[/green]" if is_fpm_running(version) else "[red]Stopped[/red]"
        console.print(f"  PHP {version} FPM: {status}")
    console.print()
    
    version = select_from_list("Select PHP Version", "Control FPM for:", versions)
    if not version:
        return
    
    action = select_from_list(
        "Select Action", "What to do?",
        ["start", "stop", "restart", "reload"]
    )
    if not action:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    service = get_fpm_service_name(version)
    success = service_control(service, action)
    
    if success:
        show_success(f"PHP {version} FPM {action}ed successfully!")
    else:
        handle_error("E3001", f"Failed to {action} PHP {version} FPM.")
    
    press_enter_to_continue()


def create_custom_pool():
    """Create a custom FPM pool for a specific site."""
    clear_screen()
    show_header()
    show_panel("Create Custom Pool", title="FPM Management", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        handle_error("E3001", "No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "Create pool for:", versions)
    if not version:
        return
    
    pool_name = text_input("Enter pool name (e.g., mysite):")
    if not pool_name:
        return
    
    pool_name = pool_name.strip().lower().replace(" ", "_")
    
    pool_path = get_fpm_pool_path(version, pool_name)
    if os.path.exists(pool_path):
        handle_error("E3001", f"Pool '{pool_name}' already exists.")
        press_enter_to_continue()
        return
    
    user = text_input("Run as user:", default="www-data")
    if not user:
        return
    
    max_children = text_input("Max children (workers):", default="5")
    if not max_children:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    pool_config = f"""[{pool_name}]
user = {user}
group = {user}
listen = /run/php/php{version}-fpm-{pool_name}.sock
listen.owner = www-data
listen.group = www-data
listen.mode = 0660

pm = dynamic
pm.max_children = {max_children}
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
pm.max_requests = 500

; Logging
access.log = /var/log/php{version}-fpm-{pool_name}.access.log
slowlog = /var/log/php{version}-fpm-{pool_name}.slow.log
request_slowlog_timeout = 5s
"""
    
    try:
        with open(pool_path, "w") as f:
            f.write(pool_config)
        
        show_success(f"Pool '{pool_name}' created!")
        console.print(f"[dim]Config: {pool_path}[/dim]")
        console.print(f"[dim]Socket: /run/php/php{version}-fpm-{pool_name}.sock[/dim]")
        console.print()
        
        if confirm_action("Restart PHP-FPM to activate pool?"):
            service_control(get_fpm_service_name(version), "restart")
            show_success("PHP-FPM restarted!")
    except Exception as e:
        handle_error("E3001", f"Failed to create pool: {e}")
    
    press_enter_to_continue()


def memory_calculator():
    """Calculate optimal FPM settings based on server memory."""
    clear_screen()
    show_header()
    show_panel("FPM Memory Calculator", title="FPM Management", style="cyan")
    
    total_mb = get_server_memory_mb()
    console.print(f"[bold]Server Memory:[/bold] {total_mb} MB")
    console.print()
    
    avg_process_mb = 40
    
    reserved_mb = min(512, total_mb * 0.2)
    available_mb = total_mb - reserved_mb
    
    recommended_max = max(2, int(available_mb / avg_process_mb))
    
    console.print("[bold]Recommendations:[/bold]")
    console.print()
    console.print(f"  Reserved for OS/services: {int(reserved_mb)} MB")
    console.print(f"  Available for PHP-FPM: {int(available_mb)} MB")
    console.print(f"  Avg memory per process: ~{avg_process_mb} MB")
    console.print()
    
    columns = [
        {"name": "Setting", "style": "cyan"},
        {"name": "Conservative", "justify": "center"},
        {"name": "Balanced", "justify": "center"},
        {"name": "Aggressive", "justify": "center"},
    ]
    
    conservative = max(2, int(recommended_max * 0.5))
    balanced = recommended_max
    aggressive = int(recommended_max * 1.5)
    
    rows = [
        ["pm.max_children", str(conservative), str(balanced), str(aggressive)],
        ["pm.start_servers", str(max(1, conservative // 4)), str(max(2, balanced // 4)), str(max(2, aggressive // 4))],
        ["pm.min_spare_servers", str(max(1, conservative // 5)), str(max(1, balanced // 5)), str(max(1, aggressive // 5))],
        ["pm.max_spare_servers", str(max(2, conservative // 3)), str(max(3, balanced // 3)), str(max(3, aggressive // 3))],
    ]
    
    show_table("", columns, rows, show_header=True)
    
    console.print()
    console.print("[dim]Conservative: Safe for shared servers, low memory usage[/dim]")
    console.print("[dim]Balanced: Good for most VPS, recommended starting point[/dim]")
    console.print("[dim]Aggressive: High traffic sites, monitor memory usage[/dim]")
    
    press_enter_to_continue()
