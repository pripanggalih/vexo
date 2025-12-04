"""Redis core functions - install, info, service control."""

from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_success, show_info, press_enter_to_continue,
)
from ui.menu import select_from_list
from utils.shell import run_command, is_installed, require_root, service_control
from utils.error_handler import handle_error
from modules.database.redis.utils import (
    is_redis_ready, redis_info, get_db_keys_count,
)


def install_redis():
    """Install Redis."""
    clear_screen()
    show_header()
    show_panel("Install Redis", title="Database", style="cyan")
    
    if is_installed("redis-server"):
        show_info("Redis is already installed.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print("Installing Redis...")
    result = run_command("apt update && apt install -y redis-server", check=False)
    
    if result.returncode == 0:
        show_success("Redis installed successfully!")
    else:
        handle_error("E4001", "Installation failed!")
    
    press_enter_to_continue()


def server_info():
    """Show Redis server info."""
    clear_screen()
    show_header()
    show_panel("Server Info", title="Redis", style="cyan")
    
    if not is_redis_ready():
        handle_error("E4001", "Redis is not running.")
        press_enter_to_continue()
        return
    
    server = redis_info("server")
    memory = redis_info("memory")
    clients = redis_info("clients")
    stats = redis_info("stats")
    
    console.print(f"[bold]Version:[/bold] {server.get('redis_version', 'N/A')}")
    console.print(f"[bold]Mode:[/bold] {server.get('redis_mode', 'standalone')}")
    console.print(f"[bold]OS:[/bold] {server.get('os', 'N/A')}")
    console.print(f"[bold]Uptime:[/bold] {int(server.get('uptime_in_seconds', 0)) // 3600} hours")
    console.print()
    
    console.print(f"[bold]Used Memory:[/bold] {memory.get('used_memory_human', 'N/A')}")
    console.print(f"[bold]Peak Memory:[/bold] {memory.get('used_memory_peak_human', 'N/A')}")
    console.print(f"[bold]Max Memory:[/bold] {memory.get('maxmemory_human', 'unlimited')}")
    console.print()
    
    console.print(f"[bold]Connected Clients:[/bold] {clients.get('connected_clients', 'N/A')}")
    console.print(f"[bold]Blocked Clients:[/bold] {clients.get('blocked_clients', 'N/A')}")
    console.print()
    
    console.print(f"[bold]Total Commands:[/bold] {stats.get('total_commands_processed', 'N/A')}")
    console.print(f"[bold]Total Connections:[/bold] {stats.get('total_connections_received', 'N/A')}")
    console.print()
    
    db_keys = get_db_keys_count()
    if db_keys:
        console.print("[bold]Keys per Database:[/bold]")
        for db, count in db_keys.items():
            console.print(f"  {db}: {count} keys")
    else:
        console.print("[dim]No keys in any database[/dim]")
    
    press_enter_to_continue()


def service_control_menu():
    """Service control menu."""
    clear_screen()
    show_header()
    show_panel("Service Control", title="Redis", style="cyan")
    
    from utils.shell import is_service_running
    running = is_service_running("redis-server")
    
    console.print(f"[bold]Status:[/bold] {'[green]Running[/green]' if running else '[red]Stopped[/red]'}")
    console.print()
    
    options = ["Start", "Stop", "Restart", "Enable (start on boot)", "Disable (don't start on boot)"]
    action = select_from_list("Action", "Select:", options)
    
    if not action:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    action_map = {
        "Start": "start",
        "Stop": "stop",
        "Restart": "restart",
        "Enable": "enable",
        "Disable": "disable",
    }
    
    for key, value in action_map.items():
        if action.startswith(key):
            service_control("redis-server", value)
            show_success(f"Redis {value}d!")
            break
    
    press_enter_to_continue()
