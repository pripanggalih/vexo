"""MariaDB security management."""

import os

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, service_control, require_root
from modules.database.mariadb.utils import (
    is_mariadb_ready, run_mysql, get_users, get_user_databases,
    MARIA_SYSTEM_USERS,
)


def show_security_menu():
    """Display Security submenu."""
    options = [
        ("users", "1. List Users & Privileges"),
        ("privileges", "2. Manage Privileges"),
        ("password", "3. Change User Password"),
        ("remote", "4. Remote Access"),
        ("reset", "5. Reset root Password"),
        ("audit", "6. Security Audit"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "users": list_users_privileges,
        "privileges": manage_privileges,
        "password": change_user_password,
        "remote": remote_access,
        "reset": reset_root_password,
        "audit": security_audit,
    }
    
    run_menu_loop("Security", options, handlers)


def list_users_privileges():
    """List all users and their privileges."""
    clear_screen()
    show_header()
    show_panel("Users & Privileges", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    sql = """
    SELECT User, Host, 
           IF(Super_priv='Y','Yes','No') as superuser,
           IF(Grant_priv='Y','Yes','No') as grant_priv
    FROM mysql.user 
    ORDER BY User;
    """
    
    result = run_mysql(sql)
    
    columns = [
        {"name": "Username", "style": "cyan"},
        {"name": "Host"},
        {"name": "Superuser", "justify": "center"},
        {"name": "Grant", "justify": "center"},
    ]
    
    rows = []
    for line in result.stdout.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) >= 4:
            superuser = "[green]Yes[/green]" if parts[2] == "Yes" else "No"
            grant = "[green]Yes[/green]" if parts[3] == "Yes" else "No"
            rows.append([parts[0], parts[1], superuser, grant])
    
    if rows:
        show_table("", columns, rows, show_header=True)
    else:
        show_info("No users found.")
    
    press_enter_to_continue()


def manage_privileges():
    """Grant or revoke privileges."""
    clear_screen()
    show_header()
    show_panel("Manage Privileges", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    users = [u for u in get_users() if u not in MARIA_SYSTEM_USERS]
    if not users:
        show_info("No user-created accounts found.")
        press_enter_to_continue()
        return
    
    user = select_from_list("Select User", "Manage:", users)
    if not user:
        return
    
    result = run_mysql(f"SELECT Host FROM mysql.user WHERE User = '{user}';")
    hosts = [h.strip() for h in result.stdout.strip().split('\n') if h.strip()]
    host = hosts[0] if hosts else "localhost"
    
    databases = get_user_databases()
    if not databases:
        show_info("No user databases found.")
        press_enter_to_continue()
        return
    
    database = select_from_list("Select Database", "On database:", databases)
    if not database:
        return
    
    actions = [
        "Grant ALL privileges",
        "Grant SELECT only (read-only)",
        "Grant INSERT, UPDATE, DELETE",
        "Revoke ALL privileges",
    ]
    
    action = select_from_list("Action", "Privilege:", actions)
    if not action:
        return
    
    if "Grant ALL" in action:
        run_mysql(f"GRANT ALL PRIVILEGES ON `{database}`.* TO '{user}'@'{host}';")
        show_success(f"Granted ALL privileges on {database} to {user}")
    elif "SELECT only" in action:
        run_mysql(f"GRANT SELECT ON `{database}`.* TO '{user}'@'{host}';")
        show_success(f"Granted SELECT on {database} to {user}")
    elif "INSERT" in action:
        run_mysql(f"GRANT SELECT, INSERT, UPDATE, DELETE ON `{database}`.* TO '{user}'@'{host}';")
        show_success(f"Granted CRUD on {database} to {user}")
    elif "Revoke" in action:
        run_mysql(f"REVOKE ALL PRIVILEGES ON `{database}`.* FROM '{user}'@'{host}';")
        show_success(f"Revoked all privileges on {database} from {user}")
    
    run_mysql("FLUSH PRIVILEGES;")
    
    press_enter_to_continue()


def change_user_password():
    """Change user password."""
    clear_screen()
    show_header()
    show_panel("Change Password", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    users = get_users()
    if not users:
        show_info("No users found.")
        press_enter_to_continue()
        return
    
    user = select_from_list("Select User", "Change password for:", users)
    if not user:
        return
    
    result = run_mysql(f"SELECT Host FROM mysql.user WHERE User = '{user}';")
    hosts = [h.strip() for h in result.stdout.strip().split('\n') if h.strip()]
    
    if len(hosts) > 1:
        host = select_from_list("Select Host", f"For {user}@:", hosts)
        if not host:
            return
    else:
        host = hosts[0] if hosts else "localhost"
    
    from getpass import getpass
    try:
        password = getpass("New password: ")
        confirm = getpass("Confirm password: ")
    except Exception:
        password = text_input("New password:")
        confirm = text_input("Confirm password:")
    
    if not password or not confirm:
        return
    
    if password != confirm:
        show_error("Passwords do not match.")
        press_enter_to_continue()
        return
    
    if len(password) < 8:
        show_warning("Password should be at least 8 characters.")
        if not confirm_action("Continue anyway?"):
            return
    
    result = run_mysql(f"ALTER USER '{user}'@'{host}' IDENTIFIED BY '{password}';")
    
    if result.returncode == 0:
        run_mysql("FLUSH PRIVILEGES;")
        show_success(f"Password changed for {user}@{host}!")
    else:
        show_error("Failed to change password.")
    
    press_enter_to_continue()


def remote_access():
    """Configure remote access."""
    clear_screen()
    show_header()
    show_panel("Remote Access", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    result = run_mysql("SELECT @@bind_address;")
    current = result.stdout.strip() if result.returncode == 0 else "127.0.0.1"
    
    console.print(f"[bold]Current bind-address:[/bold] {current}")
    console.print()
    
    if current == "127.0.0.1" or current == "localhost":
        console.print("[yellow]Remote access is currently DISABLED[/yellow]")
    else:
        console.print("[green]Remote access is currently ENABLED[/green]")
    
    console.print()
    
    result = run_mysql("SELECT User, Host FROM mysql.user WHERE Host = '%';")
    if result.stdout.strip():
        console.print("[bold]Users with remote access (%):[/bold]")
        console.print(result.stdout)
    console.print()
    
    options = [
        "Allow user from any host (%)",
        "Allow user from specific IP",
        "Remove remote access for user",
    ]
    
    choice = select_from_list("Action", "Configure:", options)
    if not choice:
        return
    
    if "any host" in choice:
        users = [u for u in get_users() if u not in MARIA_SYSTEM_USERS]
        if not users:
            show_info("No users available.")
            press_enter_to_continue()
            return
        
        user = select_from_list("Select User", "Allow remote:", users)
        if not user:
            return
        
        from getpass import getpass
        try:
            password = getpass(f"Password for {user}@%: ")
        except Exception:
            password = text_input(f"Password for {user}@%:")
        
        if not password:
            return
        
        run_mysql(f"CREATE USER IF NOT EXISTS '{user}'@'%' IDENTIFIED BY '{password}';")
        run_mysql(f"GRANT ALL PRIVILEGES ON *.* TO '{user}'@'%';")
        run_mysql("FLUSH PRIVILEGES;")
        
        show_success(f"User {user}@% created!")
        show_warning("Edit /etc/mysql/mariadb.conf.d/50-server.cnf")
        show_warning("Change bind-address = 0.0.0.0 and restart MariaDB")
        
    elif "specific IP" in choice:
        users = [u for u in get_users() if u not in MARIA_SYSTEM_USERS]
        if not users:
            show_info("No users available.")
            press_enter_to_continue()
            return
        
        user = select_from_list("Select User", "Allow remote:", users)
        if not user:
            return
        
        ip = text_input("IP address:")
        if not ip:
            return
        
        from getpass import getpass
        try:
            password = getpass(f"Password for {user}@{ip}: ")
        except Exception:
            password = text_input(f"Password for {user}@{ip}:")
        
        if not password:
            return
        
        run_mysql(f"CREATE USER IF NOT EXISTS '{user}'@'{ip}' IDENTIFIED BY '{password}';")
        run_mysql(f"GRANT ALL PRIVILEGES ON *.* TO '{user}'@'{ip}';")
        run_mysql("FLUSH PRIVILEGES;")
        
        show_success(f"User {user}@{ip} created!")
        
    elif "Remove" in choice:
        result = run_mysql("SELECT CONCAT(User, '@', Host) FROM mysql.user WHERE Host != 'localhost';")
        remote_users = [u.strip() for u in result.stdout.strip().split('\n') if u.strip()]
        
        if not remote_users:
            show_info("No remote users found.")
            press_enter_to_continue()
            return
        
        user_host = select_from_list("Select User", "Remove:", remote_users)
        if not user_host:
            return
        
        if '@' in user_host:
            user, host = user_host.split('@', 1)
            run_mysql(f"DROP USER '{user}'@'{host}';")
            run_mysql("FLUSH PRIVILEGES;")
            show_success(f"Removed {user_host}")
    
    press_enter_to_continue()


def reset_root_password():
    """Reset root password."""
    clear_screen()
    show_header()
    show_panel("Reset root Password", title="MariaDB", style="yellow")
    
    show_warning("This will reset the root password!")
    console.print()
    
    if not confirm_action("Continue?"):
        return
    
    from getpass import getpass
    try:
        password = getpass("New password for root: ")
        confirm = getpass("Confirm password: ")
    except Exception:
        password = text_input("New password:")
        confirm = text_input("Confirm password:")
    
    if not password or password != confirm:
        show_error("Passwords do not match.")
        press_enter_to_continue()
        return
    
    result = run_mysql(f"ALTER USER 'root'@'localhost' IDENTIFIED BY '{password}';")
    
    if result.returncode == 0:
        run_mysql("FLUSH PRIVILEGES;")
        show_success("root password has been reset!")
    else:
        show_error("Failed to reset password.")
    
    press_enter_to_continue()


def security_audit():
    """Run security audit."""
    clear_screen()
    show_header()
    show_panel("Security Audit", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    checks = []
    recommendations = []
    
    # Check 1: Anonymous users
    result = run_mysql("SELECT COUNT(*) FROM mysql.user WHERE User = '';")
    anon_count = int(result.stdout.strip()) if result.returncode == 0 else 0
    checks.append(("No anonymous users", anon_count == 0, str(anon_count)))
    if anon_count > 0:
        recommendations.append("Remove anonymous users: DROP USER ''@'localhost';")
    
    # Check 2: Remote root
    result = run_mysql("SELECT COUNT(*) FROM mysql.user WHERE User = 'root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');")
    remote_root = int(result.stdout.strip()) if result.returncode == 0 else 0
    checks.append(("No remote root", remote_root == 0, str(remote_root)))
    if remote_root > 0:
        recommendations.append("Remove remote root access")
    
    # Check 3: Test database
    result = run_mysql("SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = 'test';")
    test_db = int(result.stdout.strip()) if result.returncode == 0 else 0
    checks.append(("No test database", test_db == 0, "Exists" if test_db else "Removed"))
    if test_db > 0:
        recommendations.append("Remove test database: DROP DATABASE test;")
    
    # Check 4: Users without password
    result = run_mysql("SELECT COUNT(*) FROM mysql.user WHERE authentication_string = '' OR authentication_string IS NULL;")
    no_pw = int(result.stdout.strip()) if result.returncode == 0 else 0
    checks.append(("All users have passwords", no_pw == 0, str(no_pw)))
    if no_pw > 0:
        recommendations.append(f"{no_pw} user(s) have no password")
    
    # Check 5: Bind address
    result = run_mysql("SELECT @@bind_address;")
    bind = result.stdout.strip() if result.returncode == 0 else ""
    is_local = bind in ["127.0.0.1", "localhost", ""]
    checks.append(("Bind localhost only", is_local, bind or "default"))
    if not is_local:
        recommendations.append("MariaDB accepts remote connections - ensure users are restricted")
    
    columns = [
        {"name": "Check", "style": "cyan"},
        {"name": "Status", "justify": "center"},
        {"name": "Value"},
    ]
    
    rows = []
    passed = 0
    for name, ok, value in checks:
        status = "[green]✓ PASS[/green]" if ok else "[yellow]⚠ WARN[/yellow]"
        if ok:
            passed += 1
        rows.append([name, status, value])
    
    show_table(f"Score: {passed}/{len(checks)}", columns, rows, show_header=True)
    
    if recommendations:
        console.print()
        console.print("[bold yellow]Recommendations:[/bold yellow]")
        for rec in recommendations:
            console.print(f"  • {rec}")
    
    press_enter_to_continue()
