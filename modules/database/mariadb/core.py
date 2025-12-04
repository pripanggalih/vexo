"""MariaDB core functions - install, list, create, delete databases."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list
from utils.shell import run_command, is_installed, require_root
from modules.database.mariadb.utils import (
    is_mariadb_ready, run_mysql, get_databases, get_user_databases,
    get_database_size, format_size, MARIA_SYSTEM_DBS,
)


def install_mariadb():
    """Install MariaDB."""
    clear_screen()
    show_header()
    show_panel("Install MariaDB", title="Database", style="cyan")
    
    if is_installed("mariadb-server"):
        show_info("MariaDB is already installed.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print("Installing MariaDB...")
    result = run_command("apt update && apt install -y mariadb-server", check=False)
    
    if result.returncode == 0:
        show_success("MariaDB installed successfully!")
        console.print()
        console.print("[dim]Run 'mysql_secure_installation' to secure your installation.[/dim]")
    else:
        show_error("Installation failed!")
    
    press_enter_to_continue()


def list_databases():
    """List all MariaDB databases."""
    clear_screen()
    show_header()
    show_panel("Database List", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
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
        db_type = "[dim]system[/dim]" if db in MARIA_SYSTEM_DBS else "user"
        rows.append([db, size, db_type])
    
    show_table(f"Total: {len(databases)} database(s)", columns, rows, show_header=True)
    press_enter_to_continue()


def create_database_interactive():
    """Create a new database with optional user."""
    clear_screen()
    show_header()
    show_panel("Create Database", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    db_name = text_input("Database name:")
    if not db_name:
        return
    
    if db_name in get_databases():
        show_error(f"Database '{db_name}' already exists.")
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
    
    result = run_mysql(f"CREATE DATABASE `{db_name}`;")
    if result.returncode != 0:
        show_error("Failed to create database.")
        console.print(f"[dim]{result.stderr}[/dim]")
        press_enter_to_continue()
        return
    
    show_success(f"Database '{db_name}' created!")
    
    if create_user and username:
        result = run_mysql(f"CREATE USER '{username}'@'localhost' IDENTIFIED BY '{password}';")
        if result.returncode == 0:
            run_mysql(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{username}'@'localhost';")
            run_mysql("FLUSH PRIVILEGES;")
            show_success(f"User '{username}' created with access to {db_name}!")
        else:
            show_error("Failed to create user.")
    
    press_enter_to_continue()


def delete_database_interactive():
    """Delete a database."""
    clear_screen()
    show_header()
    show_panel("Delete Database", title="MariaDB", style="red")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
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
    
    if not confirm_action("Type database name to confirm deletion"):
        return
    
    confirm_name = text_input("Database name:")
    if confirm_name != db_name:
        show_error("Name does not match.")
        press_enter_to_continue()
        return
    
    result = run_mysql(f"DROP DATABASE `{db_name}`;")
    
    if result.returncode == 0:
        show_success(f"Database '{db_name}' deleted!")
    else:
        show_error("Failed to delete database.")
    
    press_enter_to_continue()
