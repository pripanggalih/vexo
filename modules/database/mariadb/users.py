"""MariaDB user management."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.sanitize import escape_mysql, validate_identifier
from modules.database.mariadb.utils import (
    is_mariadb_ready, run_mysql, get_users, MARIA_SYSTEM_USERS,
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
    """List all MariaDB users."""
    clear_screen()
    show_header()
    show_panel("User List", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    sql = "SELECT User, Host FROM mysql.user ORDER BY User;"
    result = run_mysql(sql)
    
    columns = [
        {"name": "Username", "style": "cyan"},
        {"name": "Host"},
    ]
    
    rows = []
    for line in result.stdout.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) >= 2:
            rows.append([parts[0], parts[1]])
    
    if rows:
        show_table("", columns, rows, show_header=True)
    
    press_enter_to_continue()


def create_user():
    """Create a new MariaDB user."""
    clear_screen()
    show_header()
    show_panel("Create User", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    username = text_input("Username:")
    if not username:
        return
    
    # Validate username
    if not validate_identifier(username, max_length=32):
        show_error("Invalid username. Use only letters, numbers, and underscore.")
        press_enter_to_continue()
        return
    
    from getpass import getpass
    try:
        password = getpass("Password: ")
    except Exception:
        password = text_input("Password:")
    
    if not password:
        return
    
    host_options = ["localhost", "%", "Custom"]
    host = select_from_list("Host", "Allow from:", host_options)
    if not host:
        return
    
    if host == "Custom":
        host = text_input("Host/IP:")
        if not host:
            return
    
    # Escape values to prevent SQL injection
    safe_user = escape_mysql(username)
    safe_host = escape_mysql(host)
    safe_pass = escape_mysql(password)
    result = run_mysql(f"CREATE USER '{safe_user}'@'{safe_host}' IDENTIFIED BY '{safe_pass}';")
    
    if result.returncode == 0:
        run_mysql("FLUSH PRIVILEGES;")
        show_success(f"User '{username}'@'{host}' created!")
    else:
        show_error("Failed to create user.")
        console.print(f"[dim]{result.stderr}[/dim]")
    
    press_enter_to_continue()


def delete_user():
    """Delete a MariaDB user."""
    clear_screen()
    show_header()
    show_panel("Delete User", title="MariaDB", style="red")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    users = [u for u in get_users() if u not in MARIA_SYSTEM_USERS]
    if not users:
        show_info("No user-created accounts found.")
        press_enter_to_continue()
        return
    
    username = select_from_list("Select User", "Delete:", users)
    if not username:
        return
    
    # Escape username for query
    safe_user = escape_mysql(username)
    result = run_mysql(f"SELECT Host FROM mysql.user WHERE User = '{safe_user}';")
    hosts = [h.strip() for h in result.stdout.strip().split('\n') if h.strip()]
    
    if len(hosts) > 1:
        host = select_from_list("Select Host", f"Delete {username}@:", hosts)
        if not host:
            return
    else:
        host = hosts[0] if hosts else "localhost"
    
    if not confirm_action(f"Delete user '{username}'@'{host}'?"):
        return
    
    # Escape values for DROP USER
    safe_host = escape_mysql(host)
    result = run_mysql(f"DROP USER '{safe_user}'@'{safe_host}';")
    
    if result.returncode == 0:
        run_mysql("FLUSH PRIVILEGES;")
        show_success(f"User '{username}'@'{host}' deleted!")
    else:
        show_error("Failed to delete user.")
    
    press_enter_to_continue()
