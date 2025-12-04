"""MariaDB configuration management."""

import os

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, service_control, require_root
from modules.database.mariadb.utils import (
    is_mariadb_ready, run_mysql, format_size,
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
    """View current MariaDB configuration."""
    clear_screen()
    show_header()
    show_panel("Current Configuration", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    settings = [
        "max_connections",
        "innodb_buffer_pool_size",
        "innodb_log_file_size",
        "query_cache_size",
        "tmp_table_size",
        "max_heap_table_size",
        "thread_cache_size",
        "table_open_cache",
        "slow_query_log",
        "long_query_time",
    ]
    
    columns = [
        {"name": "Setting", "style": "cyan"},
        {"name": "Value"},
    ]
    
    rows = []
    for setting in settings:
        result = run_mysql(f"SELECT @@{setting};")
        value = result.stdout.strip() if result.returncode == 0 else "N/A"
        if 'size' in setting and value.isdigit():
            value = format_size(int(value))
        rows.append([setting, value])
    
    show_table("", columns, rows, show_header=True)
    press_enter_to_continue()


def quick_settings():
    """Edit common MariaDB settings."""
    clear_screen()
    show_header()
    show_panel("Quick Settings", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    settings = [
        ("max_connections", "Maximum concurrent connections"),
        ("innodb_buffer_pool_size", "InnoDB buffer pool size"),
        ("query_cache_size", "Query cache size"),
        ("tmp_table_size", "Temporary table size"),
    ]
    
    setting_options = [f"{s[0]} ({s[1]})" for s in settings]
    
    choice = select_from_list("Select Setting", "Configure:", setting_options)
    if not choice:
        return
    
    setting_name = choice.split(" (")[0]
    
    result = run_mysql(f"SELECT @@{setting_name};")
    current = result.stdout.strip() if result.returncode == 0 else ""
    
    console.print(f"[dim]Current: {current}[/dim]")
    new_value = text_input(f"New value for {setting_name}:")
    if not new_value:
        return
    
    result = run_mysql(f"SET GLOBAL {setting_name} = {new_value};")
    
    if result.returncode == 0:
        show_success(f"Set {setting_name} = {new_value}")
        console.print()
        show_warning("This change is temporary. Add to my.cnf for persistence.")
    else:
        show_error("Failed to update setting.")
        console.print(f"[dim]{result.stderr}[/dim]")
    
    press_enter_to_continue()


def memory_tuning():
    """Memory tuning wizard."""
    clear_screen()
    show_header()
    show_panel("Memory Tuning", title="MariaDB", style="cyan")
    
    result = run_command("free -b | grep Mem | awk '{print $2}'", check=False, silent=True)
    total_ram = int(result.stdout.strip()) if result.returncode == 0 else 0
    
    if total_ram == 0:
        show_error("Could not detect server memory.")
        press_enter_to_continue()
        return
    
    total_ram_gb = total_ram / (1024 ** 3)
    console.print(f"[bold]Detected RAM:[/bold] {total_ram_gb:.1f} GB")
    console.print()
    
    # Calculate recommendations
    innodb_buffer = int(total_ram * 0.5)  # 50% for dedicated DB server
    query_cache = min(int(total_ram * 0.05), 256 * 1024 * 1024)  # 5% max 256MB
    tmp_table = min(int(total_ram * 0.05), 256 * 1024 * 1024)
    
    console.print("[bold]Recommended Settings:[/bold]")
    console.print()
    console.print(f"  innodb_buffer_pool_size = {format_size(innodb_buffer)}")
    console.print(f"  query_cache_size = {format_size(query_cache)}")
    console.print(f"  tmp_table_size = {format_size(tmp_table)}")
    console.print(f"  max_heap_table_size = {format_size(tmp_table)}")
    console.print()
    
    if not confirm_action("Apply these settings?"):
        press_enter_to_continue()
        return
    
    run_mysql(f"SET GLOBAL innodb_buffer_pool_size = {innodb_buffer};")
    run_mysql(f"SET GLOBAL query_cache_size = {query_cache};")
    run_mysql(f"SET GLOBAL tmp_table_size = {tmp_table};")
    run_mysql(f"SET GLOBAL max_heap_table_size = {tmp_table};")
    
    show_success("Settings applied!")
    console.print()
    show_warning("Changes are temporary. Add to my.cnf for persistence.")
    show_warning("Some settings require restart to take full effect.")
    
    press_enter_to_continue()


def log_configuration():
    """Configure logging settings."""
    clear_screen()
    show_header()
    show_panel("Log Configuration", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    log_settings = [
        "general_log",
        "general_log_file",
        "slow_query_log",
        "slow_query_log_file",
        "long_query_time",
        "log_error",
    ]
    
    console.print("[bold]Current Log Settings:[/bold]")
    console.print()
    for setting in log_settings:
        result = run_mysql(f"SELECT @@{setting};")
        value = result.stdout.strip() if result.returncode == 0 else "N/A"
        console.print(f"  {setting} = {value}")
    console.print()
    
    options = [
        "Enable general log (all queries)",
        "Disable general log",
        "Enable slow query log",
        "Disable slow query log",
    ]
    
    choice = select_from_list("Action", "Configure:", options)
    if not choice:
        return
    
    if "Enable general" in choice:
        run_mysql("SET GLOBAL general_log = 'ON';")
        show_success("General log enabled.")
    elif "Disable general" in choice:
        run_mysql("SET GLOBAL general_log = 'OFF';")
        show_success("General log disabled.")
    elif "Enable slow" in choice:
        run_mysql("SET GLOBAL slow_query_log = 'ON';")
        run_mysql("SET GLOBAL long_query_time = 2;")
        show_success("Slow query log enabled (> 2s).")
    elif "Disable slow" in choice:
        run_mysql("SET GLOBAL slow_query_log = 'OFF';")
        show_success("Slow query log disabled.")
    
    press_enter_to_continue()


def view_config_file():
    """View raw MariaDB config file."""
    clear_screen()
    show_header()
    show_panel("Config File", title="MariaDB", style="cyan")
    
    config_files = [
        "/etc/mysql/mariadb.conf.d/50-server.cnf",
        "/etc/mysql/my.cnf",
        "/etc/my.cnf",
    ]
    
    config_file = None
    for f in config_files:
        if os.path.exists(f):
            config_file = f
            break
    
    if not config_file:
        show_error("Could not find config file.")
        press_enter_to_continue()
        return
    
    console.print(f"[bold]Config File:[/bold] {config_file}")
    console.print()
    
    result = run_command(f"grep -v '^#' {config_file} | grep -v '^$' | head -50", check=False, silent=True)
    
    if result.returncode == 0:
        console.print(result.stdout)
    
    press_enter_to_continue()


def restart_service():
    """Restart MariaDB service."""
    clear_screen()
    show_header()
    show_panel("Restart Service", title="MariaDB", style="cyan")
    
    show_warning("This will briefly disconnect all clients!")
    console.print()
    
    options = ["Reload (graceful)", "Restart (full restart)"]
    choice = select_from_list("Action", "Select:", options)
    if not choice:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if "Reload" in choice:
        run_mysql("FLUSH PRIVILEGES;")
        show_success("MariaDB privileges reloaded!")
    else:
        service_control("mariadb", "restart")
        show_success("MariaDB restarted!")
    
    press_enter_to_continue()
