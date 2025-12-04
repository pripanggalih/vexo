"""Redis management module."""

from ui.menu import run_menu_loop
from utils.shell import is_installed, is_service_running


def show_menu():
    """Display Redis Management submenu."""
    def get_status():
        if not is_installed("redis-server"):
            return "Redis: [yellow]Not installed[/yellow]"
        if is_service_running("redis-server"):
            return "Redis: [green]Running[/green]"
        return "Redis: [red]Stopped[/red]"
    
    def get_options():
        options = []
        if is_installed("redis-server"):
            options.extend([
                ("info", "1. Server Info"),
                ("keys", "2. Key Browser"),
                ("databases", "3. Database Management"),
                ("memory", "4. Memory Management"),
                ("persist", "5. Persistence Config"),
                ("stats", "6. Performance Stats"),
                ("config", "7. Configuration"),
                ("service", "8. Service Control"),
            ])
        else:
            options.append(("install", "1. Install Redis"))
        options.append(("back", "← Back"))
        return options
    
    def get_handlers():
        from modules.database.redis.core import (
            server_info, install_redis, service_control_menu,
        )
        from modules.database.redis.keys import show_keys_menu
        from modules.database.redis.databases import show_databases_menu
        from modules.database.redis.memory import show_memory_menu
        from modules.database.redis.persistence import show_persistence_menu
        from modules.database.redis.stats import show_stats_menu
        from modules.database.redis.config import show_config_menu
        
        return {
            "install": install_redis,
            "info": server_info,
            "keys": show_keys_menu,
            "databases": show_databases_menu,
            "memory": show_memory_menu,
            "persist": show_persistence_menu,
            "stats": show_stats_menu,
            "config": show_config_menu,
            "service": service_control_menu,
        }
    
    run_menu_loop("Redis Management", get_options, get_handlers(), get_status)
