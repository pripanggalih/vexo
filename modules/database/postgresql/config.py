"""PostgreSQL configuration management."""

import os

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, service_control, require_root
from modules.database.postgresql.utils import (
    is_postgresql_ready, run_psql, get_pg_config_file, format_size,
)


def show_config_menu():
    """Display Configuration submenu."""
    options = [
        ("view", "1. View Current Config"),
        ("quick", "2. Quick Settings"),
        ("memory", "3. Memory Tuning"),
        ("logs", "4. Log Configuration"),
        ("file", "5. View Config File"),
        ("restart", "6. Restart Service"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "view": view_current_config,
        "quick": quick_settings,
        "memory": memory_tuning,
        "logs": log_configuration,
        "file": view_config_file,
        "restart": restart_service,
    }
    
    run_menu_loop("Configuration", options, handlers)


def view_current_config():
    """View current PostgreSQL configuration."""
    clear_screen()
    show_header()
    show_panel("Current Configuration", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    settings = [
        "max_connections",
        "shared_buffers",
        "effective_cache_size",
        "work_mem",
        "maintenance_work_mem",
        "checkpoint_completion_target",
        "wal_buffers",
        "default_statistics_target",
        "random_page_cost",
        "effective_io_concurrency",
        "log_min_duration_statement",
        "log_destination",
    ]
    
    columns = [
        {"name": "Setting", "style": "cyan"},
        {"name": "Value"},
    ]
    
    rows = []
    for setting in settings:
        result = run_psql(f"SHOW {setting};")
        value = result.stdout.strip() if result.returncode == 0 else "N/A"
        rows.append([setting, value])
    
    show_table("", columns, rows, show_header=True)
    press_enter_to_continue()


def quick_settings():
    """Edit common PostgreSQL settings."""
    clear_screen()
    show_header()
    show_panel("Quick Settings", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    settings = [
        ("max_connections", "Maximum concurrent connections"),
        ("shared_buffers", "Shared memory buffers"),
        ("work_mem", "Memory for query operations"),
        ("maintenance_work_mem", "Memory for maintenance operations"),
    ]
    
    setting_options = [f"{s[0]} ({s[1]})" for s in settings]
    
    choice = select_from_list("Select Setting", "Configure:", setting_options)
    if not choice:
        return
    
    setting_name = choice.split(" (")[0]
    
    result = run_psql(f"SHOW {setting_name};")
    current = result.stdout.strip() if result.returncode == 0 else ""
    
    console.print(f"[dim]Current: {current}[/dim]")
    new_value = text_input(f"New value for {setting_name}:")
    if not new_value:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    result = run_psql(f"ALTER SYSTEM SET {setting_name} = '{new_value}';")
    
    if result.returncode == 0:
        show_success(f"Set {setting_name} = {new_value}")
        console.print()
        if confirm_action("Reload PostgreSQL to apply changes?"):
            run_psql("SELECT pg_reload_conf();")
            show_success("Configuration reloaded!")
    else:
        show_error("Failed to update setting.")
        console.print(f"[dim]{result.stderr}[/dim]")
    
    press_enter_to_continue()


def memory_tuning():
    """Memory tuning wizard."""
    clear_screen()
    show_header()
    show_panel("Memory Tuning", title="PostgreSQL", style="cyan")
    
    result = run_command("free -b | grep Mem | awk '{print $2}'", check=False, silent=True)
    total_ram = int(result.stdout.strip()) if result.returncode == 0 else 0
    
    if total_ram == 0:
        show_error("Could not detect server memory.")
        press_enter_to_continue()
        return
    
    total_ram_gb = total_ram / (1024 ** 3)
    console.print(f"[bold]Detected RAM:[/bold] {total_ram_gb:.1f} GB")
    console.print()
    
    shared_buffers = int(total_ram * 0.25)
    effective_cache_size = int(total_ram * 0.75)
    work_mem = int(total_ram / (100 * 4))
    maintenance_work_mem = min(int(total_ram * 0.05), 2 * 1024 ** 3)
    
    console.print("[bold]Recommended Settings:[/bold]")
    console.print()
    console.print(f"  shared_buffers = {format_size(shared_buffers)}")
    console.print(f"  effective_cache_size = {format_size(effective_cache_size)}")
    console.print(f"  work_mem = {format_size(work_mem)}")
    console.print(f"  maintenance_work_mem = {format_size(maintenance_work_mem)}")
    console.print()
    
    if not confirm_action("Apply these settings?"):
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    settings = {
        "shared_buffers": f"{shared_buffers // (1024 ** 2)}MB",
        "effective_cache_size": f"{effective_cache_size // (1024 ** 2)}MB",
        "work_mem": f"{work_mem // (1024 ** 2)}MB",
        "maintenance_work_mem": f"{maintenance_work_mem // (1024 ** 2)}MB",
    }
    
    for key, value in settings.items():
        run_psql(f"ALTER SYSTEM SET {key} = '{value}';")
    
    show_success("Settings applied!")
    console.print()
    show_warning("PostgreSQL restart required to apply shared_buffers change.")
    
    if confirm_action("Restart PostgreSQL now?"):
        service_control("postgresql", "restart")
        show_success("PostgreSQL restarted!")
    
    press_enter_to_continue()


def log_configuration():
    """Configure logging settings."""
    clear_screen()
    show_header()
    show_panel("Log Configuration", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    log_settings = [
        "log_destination",
        "logging_collector",
        "log_directory",
        "log_filename",
        "log_min_duration_statement",
        "log_statement",
    ]
    
    console.print("[bold]Current Log Settings:[/bold]")
    console.print()
    for setting in log_settings:
        result = run_psql(f"SHOW {setting};")
        value = result.stdout.strip() if result.returncode == 0 else "N/A"
        console.print(f"  {setting} = {value}")
    console.print()
    
    options = [
        "Enable statement logging (all)",
        "Enable DDL only logging",
        "Disable statement logging",
        "Set log rotation",
    ]
    
    choice = select_from_list("Action", "Configure:", options)
    if not choice:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if "all" in choice:
        run_psql("ALTER SYSTEM SET log_statement = 'all';")
        show_success("Logging all statements.")
    elif "DDL" in choice:
        run_psql("ALTER SYSTEM SET log_statement = 'ddl';")
        show_success("Logging DDL statements only.")
    elif "Disable" in choice:
        run_psql("ALTER SYSTEM SET log_statement = 'none';")
        show_success("Statement logging disabled.")
    elif "rotation" in choice:
        run_psql("ALTER SYSTEM SET log_rotation_age = '1d';")
        run_psql("ALTER SYSTEM SET log_rotation_size = '100MB';")
        show_success("Log rotation configured (daily or 100MB).")
    
    run_psql("SELECT pg_reload_conf();")
    console.print("[dim]Configuration reloaded.[/dim]")
    
    press_enter_to_continue()


def view_config_file():
    """View raw PostgreSQL config file."""
    clear_screen()
    show_header()
    show_panel("Config File", title="PostgreSQL", style="cyan")
    
    config_file = get_pg_config_file()
    if not config_file:
        show_error("Could not find config file.")
        press_enter_to_continue()
        return
    
    console.print(f"[bold]Config File:[/bold] {config_file}")
    console.print()
    
    if not os.path.exists(config_file):
        show_error("Config file not found.")
        press_enter_to_continue()
        return
    
    result = run_command(f"grep -v '^#' {config_file} | grep -v '^$' | head -50", check=False, silent=True)
    
    if result.returncode == 0:
        console.print(result.stdout)
    
    press_enter_to_continue()


def restart_service():
    """Restart PostgreSQL service."""
    clear_screen()
    show_header()
    show_panel("Restart Service", title="PostgreSQL", style="cyan")
    
    show_warning("This will briefly disconnect all clients!")
    console.print()
    
    options = ["Reload (graceful, limited changes)", "Restart (full restart)"]
    choice = select_from_list("Action", "Select:", options)
    if not choice:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if "Reload" in choice:
        run_psql("SELECT pg_reload_conf();")
        show_success("PostgreSQL configuration reloaded!")
    else:
        service_control("postgresql", "restart")
        show_success("PostgreSQL restarted!")
    
    press_enter_to_continue()
