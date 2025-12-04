"""PostgreSQL security management."""

import os

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, service_control, require_root
from modules.database.postgresql.utils import (
    is_postgresql_ready, run_psql, get_pg_hba_file, get_users,
    get_user_databases, PG_SYSTEM_USERS,
)


def show_security_menu():
    """Display Security submenu."""
    options = [
        ("users", "1. List Users & Privileges"),
        ("privileges", "2. Manage Privileges"),
        ("password", "3. Change User Password"),
        ("remote", "4. Remote Access"),
        ("reset", "5. Reset postgres Password"),
        ("audit", "6. Security Audit"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "users": list_users_privileges,
        "privileges": manage_privileges,
        "password": change_user_password,
        "remote": remote_access,
        "reset": reset_postgres_password,
        "audit": security_audit,
    }
    
    run_menu_loop("Security", options, handlers)


def list_users_privileges():
    """List all users and their privileges."""
    clear_screen()
    show_header()
    show_panel("Users & Privileges", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    sql = """
    SELECT 
        r.rolname as username,
        r.rolsuper as superuser,
        r.rolcreatedb as createdb,
        r.rolcanlogin as canlogin
    FROM pg_roles r
    WHERE r.rolcanlogin = true
    ORDER BY r.rolname;
    """
    
    result = run_psql(sql)
    
    columns = [
        {"name": "Username", "style": "cyan"},
        {"name": "Superuser", "justify": "center"},
        {"name": "Create DB", "justify": "center"},
        {"name": "Can Login", "justify": "center"},
    ]
    
    rows = []
    for line in result.stdout.strip().split('\n'):
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 4:
            superuser = "[green]Yes[/green]" if parts[1] == 't' else "No"
            createdb = "[green]Yes[/green]" if parts[2] == 't' else "No"
            canlogin = "[green]Yes[/green]" if parts[3] == 't' else "No"
            rows.append([parts[0], superuser, createdb, canlogin])
    
    if rows:
        show_table("", columns, rows, show_header=True)
    else:
        show_info("No users found.")
    
    press_enter_to_continue()


def manage_privileges():
    """Grant or revoke privileges."""
    clear_screen()
    show_header()
    show_panel("Manage Privileges", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    users = [u for u in get_users() if u not in PG_SYSTEM_USERS]
    if not users:
        show_info("No user-created accounts found.")
        press_enter_to_continue()
        return
    
    user = select_from_list("Select User", "Manage:", users)
    if not user:
        return
    
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
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if "Grant ALL" in action:
        run_psql(f"GRANT ALL PRIVILEGES ON DATABASE {database} TO {user};")
        run_psql(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {user};", database=database)
        show_success(f"Granted ALL privileges on {database} to {user}")
    elif "SELECT only" in action:
        run_psql(f"GRANT CONNECT ON DATABASE {database} TO {user};")
        run_psql(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {user};", database=database)
        show_success(f"Granted SELECT on {database} to {user}")
    elif "INSERT" in action:
        run_psql(f"GRANT CONNECT ON DATABASE {database} TO {user};")
        run_psql(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {user};", database=database)
        show_success(f"Granted CRUD on {database} to {user}")
    elif "Revoke" in action:
        run_psql(f"REVOKE ALL PRIVILEGES ON DATABASE {database} FROM {user};")
        run_psql(f"REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM {user};", database=database)
        show_success(f"Revoked all privileges on {database} from {user}")
    
    press_enter_to_continue()


def change_user_password():
    """Change user password."""
    clear_screen()
    show_header()
    show_panel("Change Password", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
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
    
    result = run_psql(f"ALTER USER {user} WITH PASSWORD '{password}';")
    
    if result.returncode == 0:
        show_success(f"Password changed for {user}!")
    else:
        show_error("Failed to change password.")
    
    press_enter_to_continue()


def remote_access():
    """Configure remote access."""
    clear_screen()
    show_header()
    show_panel("Remote Access", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    result = run_psql("SHOW listen_addresses;")
    current = result.stdout.strip() if result.returncode == 0 else "localhost"
    
    console.print(f"[bold]Current listen_addresses:[/bold] {current}")
    console.print()
    
    if current == "localhost" or current == "127.0.0.1":
        console.print("[yellow]Remote access is currently DISABLED[/yellow]")
    else:
        console.print("[green]Remote access is currently ENABLED[/green]")
    
    console.print()
    
    hba_file = get_pg_hba_file()
    if hba_file and os.path.exists(hba_file):
        console.print("[bold]Current pg_hba.conf rules:[/bold]")
        result = run_command(f"grep -v '^#' {hba_file} | grep -v '^$' | head -10", check=False, silent=True)
        if result.stdout:
            console.print(result.stdout)
    console.print()
    
    options = [
        "Enable remote access (listen on all interfaces)",
        "Disable remote access (localhost only)",
        "Allow specific IP range",
    ]
    
    choice = select_from_list("Action", "Configure:", options)
    if not choice:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if "Enable" in choice:
        run_psql("ALTER SYSTEM SET listen_addresses = '*';")
        
        if hba_file:
            rule = "host    all             all             0.0.0.0/0               md5"
            with open(hba_file, 'a') as f:
                f.write(f"\n# Added by vexo - allow remote\n{rule}\n")
        
        show_success("Remote access enabled!")
        show_warning("Restart PostgreSQL to apply changes.")
        show_warning("Make sure firewall allows port 5432!")
        
    elif "Disable" in choice:
        run_psql("ALTER SYSTEM SET listen_addresses = 'localhost';")
        show_success("Remote access disabled!")
        show_warning("Restart PostgreSQL to apply changes.")
        
    elif "specific IP" in choice:
        ip_range = text_input("IP range (e.g., 192.168.1.0/24):")
        if not ip_range:
            return
        
        if hba_file:
            rule = f"host    all             all             {ip_range}               md5"
            with open(hba_file, 'a') as f:
                f.write(f"\n# Added by vexo - allow {ip_range}\n{rule}\n")
        
        show_success(f"Added rule for {ip_range}!")
        show_warning("Restart PostgreSQL to apply changes.")
    
    if confirm_action("Restart PostgreSQL now?"):
        service_control("postgresql", "restart")
        show_success("PostgreSQL restarted!")
    
    press_enter_to_continue()


def reset_postgres_password():
    """Reset postgres superuser password."""
    clear_screen()
    show_header()
    show_panel("Reset postgres Password", title="PostgreSQL", style="yellow")
    
    show_warning("This will reset the postgres superuser password!")
    console.print()
    
    if not confirm_action("Continue?"):
        return
    
    from getpass import getpass
    try:
        password = getpass("New password for postgres: ")
        confirm = getpass("Confirm password: ")
    except Exception:
        password = text_input("New password:")
        confirm = text_input("Confirm password:")
    
    if not password or password != confirm:
        show_error("Passwords do not match.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    result = run_psql(f"ALTER USER postgres WITH PASSWORD '{password}';")
    
    if result.returncode == 0:
        show_success("postgres password has been reset!")
    else:
        show_error("Failed to reset password.")
    
    press_enter_to_continue()


def security_audit():
    """Run security audit."""
    clear_screen()
    show_header()
    show_panel("Security Audit", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    checks = []
    recommendations = []
    
    result = run_psql(
        "SELECT passwd IS NOT NULL as has_password FROM pg_shadow WHERE usename = 'postgres';"
    )
    has_pw = 't' in result.stdout if result.returncode == 0 else False
    checks.append(("postgres has password", has_pw, "Yes" if has_pw else "No"))
    if not has_pw:
        recommendations.append("Set password for postgres user")
    
    result = run_psql(
        "SELECT count(*) FROM pg_shadow WHERE passwd IS NULL AND usename != 'postgres';"
    )
    no_pw_count = int(result.stdout.strip()) if result.returncode == 0 else 0
    checks.append(("Users without password", no_pw_count == 0, str(no_pw_count)))
    if no_pw_count > 0:
        recommendations.append(f"{no_pw_count} user(s) have no password set")
    
    result = run_psql("SHOW listen_addresses;")
    listen = result.stdout.strip() if result.returncode == 0 else "localhost"
    is_local = listen in ["localhost", "127.0.0.1"]
    checks.append(("Listen localhost only", is_local, listen))
    if not is_local:
        recommendations.append("PostgreSQL accepts remote connections - ensure pg_hba.conf is restrictive")
    
    result = run_psql("SHOW ssl;")
    ssl_on = result.stdout.strip() == "on" if result.returncode == 0 else False
    checks.append(("SSL enabled", ssl_on, "Yes" if ssl_on else "No"))
    if not ssl_on:
        recommendations.append("Consider enabling SSL for encrypted connections")
    
    result = run_psql("SELECT count(*) FROM pg_roles WHERE rolsuper = true;")
    su_count = int(result.stdout.strip()) if result.returncode == 0 else 0
    checks.append(("Superuser count", su_count <= 2, str(su_count)))
    if su_count > 2:
        recommendations.append("Multiple superusers - review if all are necessary")
    
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
