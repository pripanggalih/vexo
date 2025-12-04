"""PostgreSQL core functions - install, list, create, delete databases."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list
from utils.shell import run_command, is_installed, require_root
from utils.error_handler import handle_error
from modules.database.postgresql.utils import (
    is_postgresql_ready, run_psql, get_databases, get_user_databases,
    get_database_size, format_size, PG_SYSTEM_DBS,
)


def install_postgresql():
    """Install PostgreSQL."""
    clear_screen()
    show_header()
    show_panel("Install PostgreSQL", title="Database", style="cyan")
    
    if is_installed("postgresql"):
        show_info("PostgreSQL is already installed.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print("Installing PostgreSQL...")
    result = run_command("apt update && apt install -y postgresql postgresql-contrib", check=False)
    
    if result.returncode == 0:
        show_success("PostgreSQL installed successfully!")
    else:
        handle_error("E4001", "Installation failed!")
    
    press_enter_to_continue()


def list_databases():
    """List all PostgreSQL databases."""
    clear_screen()
    show_header()
    show_panel("Database List", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        handle_error("E4001", "PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    databases = get_databases()
    
    columns = [
        {"name": "Database", "style": "cyan"},
        {"name": "Size", "justify": "right"},
        {"name": "Type"},
    ]
    
    rows = []
    for db in databases:
        size = format_size(get_database_size(db))
        db_type = "[dim]system[/dim]" if db in PG_SYSTEM_DBS else "user"
        rows.append([db, size, db_type])
    
    show_table(f"Total: {len(databases)} database(s)", columns, rows, show_header=True)
    press_enter_to_continue()


def create_database_interactive():
    """Create a new database with optional user."""
    clear_screen()
    show_header()
    show_panel("Create Database", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        handle_error("E4001", "PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    db_name = text_input("Database name:")
    if not db_name:
        return
    
    if db_name in get_databases():
        handle_error("E4001", f"Database '{db_name}' already exists.")
        press_enter_to_continue()
        return
    
    create_user = confirm_action("Create dedicated user for this database?")
    
    username = None
    password = None
    
    if create_user:
        username = text_input("Username:", default=db_name)
        if not username:
            return
        
        from getpass import getpass
        try:
            password = getpass("Password: ")
        except Exception:
            password = text_input("Password:")
        
        if not password:
            return
    
    result = run_psql(f"CREATE DATABASE {db_name};")
    if result.returncode != 0:
        handle_error("E4001", "Failed to create database.")
        console.print(f"[dim]{result.stderr}[/dim]")
        press_enter_to_continue()
        return
    
    show_success(f"Database '{db_name}' created!")
    
    if create_user and username:
        result = run_psql(f"CREATE USER {username} WITH PASSWORD '{password}';")
        if result.returncode == 0:
            run_psql(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {username};")
            show_success(f"User '{username}' created with access to {db_name}!")
        else:
            handle_error("E4001", "Failed to create user.")
    
    press_enter_to_continue()


def delete_database_interactive():
    """Delete a database."""
    clear_screen()
    show_header()
    show_panel("Delete Database", title="PostgreSQL", style="red")
    
    if not is_postgresql_ready():
        handle_error("E4001", "PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    databases = get_user_databases()
    if not databases:
        show_info("No user databases found.")
        press_enter_to_continue()
        return
    
    db_name = select_from_list("Select Database", "Delete:", databases)
    if not db_name:
        return
    
    size = format_size(get_database_size(db_name))
    console.print(f"[bold red]WARNING: This will permanently delete '{db_name}' ({size})[/bold red]")
    
    if not confirm_action(f"Type database name to confirm deletion"):
        return
    
    confirm_name = text_input("Database name:")
    if confirm_name != db_name:
        handle_error("E4001", "Name does not match.")
        press_enter_to_continue()
        return
    
    run_psql(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}';")
    
    result = run_psql(f"DROP DATABASE {db_name};")
    
    if result.returncode == 0:
        show_success(f"Database '{db_name}' deleted!")
    else:
        handle_error("E4001", "Failed to delete database.")
    
    press_enter_to_continue()
