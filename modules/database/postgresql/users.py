"""PostgreSQL user management."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.sanitize import (
    escape_postgresql, escape_postgresql_identifier, validate_identifier,
)
from modules.database.postgresql.utils import (
    is_postgresql_ready, run_psql, get_users, PG_SYSTEM_USERS,
)


def show_users_menu():
    """Display Users submenu."""
    options = [
        ("list", "1. List Users"),
        ("create", "2. Create User"),
        ("delete", "3. Delete User"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "list": list_users,
        "create": create_user,
        "delete": delete_user,
    }
    
    run_menu_loop("User Management", options, handlers)


def list_users():
    """List all PostgreSQL users."""
    clear_screen()
    show_header()
    show_panel("User List", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    sql = """
    SELECT usename, usecreatedb, usesuper
    FROM pg_catalog.pg_user
    ORDER BY usename;
    """
    
    result = run_psql(sql)
    
    columns = [
        {"name": "Username", "style": "cyan"},
        {"name": "Create DB", "justify": "center"},
        {"name": "Superuser", "justify": "center"},
    ]
    
    rows = []
    for line in result.stdout.strip().split('\n'):
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 3:
            createdb = "[green]Yes[/green]" if parts[1] == 't' else "No"
            superuser = "[green]Yes[/green]" if parts[2] == 't' else "No"
            rows.append([parts[0], createdb, superuser])
    
    if rows:
        show_table("", columns, rows, show_header=True)
    
    press_enter_to_continue()


def create_user():
    """Create a new PostgreSQL user."""
    clear_screen()
    show_header()
    show_panel("Create User", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    username = text_input("Username:")
    if not username:
        return
    
    # Validate username (PostgreSQL allows lowercase + underscore + digits)
    if not validate_identifier(username, max_length=63, allow_chars="a-z0-9_"):
        show_error("Invalid username. Use only lowercase letters, numbers, and underscore.")
        press_enter_to_continue()
        return
    
    if username in get_users():
        show_error(f"User '{username}' already exists.")
        press_enter_to_continue()
        return
    
    from getpass import getpass
    try:
        password = getpass("Password: ")
    except Exception:
        password = text_input("Password:")
    
    if not password:
        return
    
    can_createdb = confirm_action("Allow user to create databases?")
    
    options = ""
    if can_createdb:
        options = "CREATEDB"
    
    # Use safe escaping for username and password
    safe_user = escape_postgresql_identifier(username)
    safe_pass = escape_postgresql(password)
    result = run_psql(f"CREATE USER {safe_user} WITH PASSWORD '{safe_pass}' {options};")
    
    if result.returncode == 0:
        show_success(f"User '{username}' created!")
    else:
        show_error("Failed to create user.")
    
    press_enter_to_continue()


def delete_user():
    """Delete a PostgreSQL user."""
    clear_screen()
    show_header()
    show_panel("Delete User", title="PostgreSQL", style="red")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    users = [u for u in get_users() if u not in PG_SYSTEM_USERS]
    if not users:
        show_info("No user-created accounts found.")
        press_enter_to_continue()
        return
    
    username = select_from_list("Select User", "Delete:", users)
    if not username:
        return
    
    if not confirm_action(f"Delete user '{username}'?"):
        return
    
    # Use safe identifier escaping
    safe_user = escape_postgresql_identifier(username)
    result = run_psql(f"DROP USER {safe_user};")
    
    if result.returncode == 0:
        show_success(f"User '{username}' deleted!")
    else:
        show_error("Failed to delete user. User may own objects.")
        console.print("[dim]Drop owned objects first: DROP OWNED BY username;[/dim]")
    
    press_enter_to_continue()
