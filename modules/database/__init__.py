"""Database management module for vexo-cli."""

from ui.menu import run_menu_loop
from utils.shell import is_installed


def show_menu():
    """Display Database Management submenu."""
    def get_status():
        pg = "[green]✓[/green]" if is_installed("postgresql") else "[dim]○[/dim]"
        maria = "[green]✓[/green]" if is_installed("mariadb-server") else "[dim]○[/dim]"
        redis = "[green]✓[/green]" if is_installed("redis-server") else "[dim]○[/dim]"
        return f"PG:{pg} Maria:{maria} Redis:{redis}"
    
    options = [
        ("pgsql", "1. PostgreSQL Management"),
        ("mariadb", "2. MariaDB Management"),
        ("redis", "3. Redis Management"),
        ("back", "← Back to Main Menu"),
    ]
    
    def get_handlers():
        from modules.database.postgresql import show_menu as pg_menu
        from modules.database.mariadb import show_menu as maria_menu
        from modules.database.redis import show_menu as redis_menu
        
        return {
            "pgsql": pg_menu,
            "mariadb": maria_menu,
            "redis": redis_menu,
        }
    
    run_menu_loop("Database Management", options, get_handlers(), get_status)
