"""MariaDB core functions - install, list, create, delete databases."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list
from utils.shell import run_command, is_installed, require_root
from utils.error_handler import handle_error
from utils.sanitize import (
    escape_mysql, escape_mysql_identifier, validate_identifier,
)
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
        handle_error("E4001", "Installation failed!")
    
    press_enter_to_continue()


def list_databases():
    """List all MariaDB databases."""
    clear_screen()
    show_header()
    show_panel("Database List", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        handle_error("E4001", "MariaDB is not running.")
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
        handle_error("E4001", "MariaDB is not running.")
        press_enter_to_continue()
        return
    
    db_name = text_input("Database name:")
    if not db_name:
        return
    
    # Validate database name (alphanumeric and underscore only)
    if not validate_identifier(db_name, max_length=64):
        handle_error("E4001", "Invalid database name. Use only letters, numbers, and underscore.")
        press_enter_to_continue()
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
        
        # Validate username
        if not validate_identifier(username, max_length=32):
            handle_error("E4001", "Invalid username. Use only letters, numbers, and underscore.")
            press_enter_to_continue()
            return
        
        from getpass import getpass
        try:
            password = getpass("Password: ")
        except Exception:
            password = text_input("Password:")
        
        if not password:
            return
    
    # Use safe identifier escaping for database name
    safe_db = escape_mysql_identifier(db_name)
    result = run_mysql(f"CREATE DATABASE {safe_db};")
    if result.returncode != 0:
        handle_error("E4001", "Failed to create database.")
        console.print(f"[dim]{result.stderr}[/dim]")
        press_enter_to_continue()
        return
    
    show_success(f"Database '{db_name}' created!")
    
    if create_user and username:
        # Escape username and password to prevent SQL injection
        safe_user = escape_mysql(username)
        safe_pass = escape_mysql(password)
        result = run_mysql(f"CREATE USER '{safe_user}'@'localhost' IDENTIFIED BY '{safe_pass}';")
        if result.returncode == 0:
            run_mysql(f"GRANT ALL PRIVILEGES ON {safe_db}.* TO '{safe_user}'@'localhost';")
            run_mysql("FLUSH PRIVILEGES;")
            show_success(f"User '{username}' created with access to {db_name}!")
        else:
            handle_error("E4001", "Failed to create user.")
    
    press_enter_to_continue()


def delete_database_interactive():
    """Delete a database."""
    clear_screen()
    show_header()
    show_panel("Delete Database", title="MariaDB", style="red")
    
    if not is_mariadb_ready():
        handle_error("E4001", "MariaDB is not running.")
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
        handle_error("E4001", "Name does not match.")
        press_enter_to_continue()
        return
    
    # Use safe identifier escaping
    safe_db = escape_mysql_identifier(db_name)
    result = run_mysql(f"DROP DATABASE {safe_db};")
    
    if result.returncode == 0:
        show_success(f"Database '{db_name}' deleted!")
    else:
        handle_error("E4001", "Failed to delete database.")
    
    press_enter_to_continue()
