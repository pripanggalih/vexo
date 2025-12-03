"""Database management module for vexo-cli (PostgreSQL & MariaDB)."""

from ui.components import (
    console,
    show_panel,
    show_table,
    show_success,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import (
    run_command,
    run_command_with_progress,
    run_command_realtime,
    is_installed,
    is_service_running,
    service_control,
    require_root,
)


def show_menu():
    """Display the Database Management submenu."""
    def get_status():
        pg = "[green]Installed[/green]" if is_installed("postgresql") else "[dim]Not installed[/dim]"
        maria = "[green]Installed[/green]" if is_installed("mariadb-server") else "[dim]Not installed[/dim]"
        redis = "[green]Installed[/green]" if is_installed("redis-server") else "[dim]Not installed[/dim]"
        return f"PostgreSQL: {pg} | MariaDB: {maria} | Redis: {redis}"
    
    options = [
        ("pgsql", "1. PostgreSQL Management"),
        ("mariadb", "2. MariaDB Management"),
        ("redis", "3. Redis Management"),
        ("back", "← Back to Main Menu"),
    ]
    
    handlers = {
        "pgsql": show_postgresql_menu,
        "mariadb": show_mariadb_menu,
        "redis": show_redis_menu,
    }
    
    run_menu_loop("Database Management", options, handlers, get_status)


def show_postgresql_menu():
    """Display PostgreSQL submenu."""
    while True:
        clear_screen()
        show_header()
        
        if is_service_running("postgresql"):
            status = "[green]Running[/green]"
        elif is_installed("postgresql"):
            status = "[red]Stopped[/red]"
        else:
            status = "[dim]Not installed[/dim]"
        
        console.print(f"[dim]PostgreSQL Status: {status}[/dim]")
        console.print()
        
        # Build dynamic options based on install status
        options = []
        
        if is_installed("postgresql"):
            options.extend([
                ("list_db", "1. List Databases"),
                ("create_db", "2. Create Database"),
                ("delete_db", "3. Delete Database"),
                ("create_user", "4. Create User"),
                ("delete_user", "5. Delete User"),
            ])
        else:
            options.append(("install", "1. Install PostgreSQL"))
        
        options.append(("back", "← Back"))
        
        choice = show_submenu(
            title="PostgreSQL Management",
            options=options,
        )
        
        if choice == "install":
            install_postgresql()
        elif choice == "list_db":
            list_databases("postgresql")
        elif choice == "create_db":
            create_database_interactive("postgresql")
        elif choice == "delete_db":
            delete_database_interactive("postgresql")
        elif choice == "create_user":
            create_user_interactive("postgresql")
        elif choice == "delete_user":
            delete_user_interactive("postgresql")
        elif choice == "back" or choice is None:
            break


def show_mariadb_menu():
    """Display MariaDB submenu."""
    while True:
        clear_screen()
        show_header()
        
        if is_service_running("mariadb"):
            status = "[green]Running[/green]"
        elif is_installed("mariadb-server"):
            status = "[red]Stopped[/red]"
        else:
            status = "[dim]Not installed[/dim]"
        
        console.print(f"[dim]MariaDB Status: {status}[/dim]")
        console.print()
        
        # Build dynamic options based on install status
        options = []
        
        if is_installed("mariadb-server"):
            options.extend([
                ("secure", "1. Secure Installation"),
                ("list_db", "2. List Databases"),
                ("create_db", "3. Create Database"),
                ("delete_db", "4. Delete Database"),
                ("create_user", "5. Create User"),
                ("delete_user", "6. Delete User"),
            ])
        else:
            options.append(("install", "1. Install MariaDB"))
        
        options.append(("back", "← Back"))
        
        choice = show_submenu(
            title="MariaDB Management",
            options=options,
        )
        
        if choice == "install":
            install_mariadb()
        elif choice == "secure":
            secure_mariadb_installation()
        elif choice == "list_db":
            list_databases("mariadb")
        elif choice == "create_db":
            create_database_interactive("mariadb")
        elif choice == "delete_db":
            delete_database_interactive("mariadb")
        elif choice == "create_user":
            create_user_interactive("mariadb")
        elif choice == "delete_user":
            delete_user_interactive("mariadb")
        elif choice == "back" or choice is None:
            break


# =============================================================================
# PostgreSQL Functions
# =============================================================================

def install_postgresql():
    """Install PostgreSQL server."""
    clear_screen()
    show_header()
    show_panel("Install PostgreSQL", title="Database", style="cyan")
    
    if is_installed("postgresql"):
        show_info("PostgreSQL is already installed.")
        
        if is_service_running("postgresql"):
            console.print("[dim]Service is running.[/dim]")
        else:
            if confirm_action("Start PostgreSQL service?"):
                service_control("postgresql", "start")
                show_success("PostgreSQL started!")
        
        press_enter_to_continue()
        return
    
    if not confirm_action("Install PostgreSQL server?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    show_info("Installing PostgreSQL...")
    
    returncode = run_command_realtime(
        "apt install -y postgresql postgresql-contrib",
        "Installing PostgreSQL..."
    )
    
    if returncode != 0:
        show_error("Failed to install PostgreSQL.")
        press_enter_to_continue()
        return
    
    service_control("postgresql", "start")
    service_control("postgresql", "enable")
    
    if is_service_running("postgresql"):
        show_success("PostgreSQL installed and running!")
        
        console.print()
        console.print("[bold]Connection Info:[/bold]")
        console.print("  Host: localhost")
        console.print("  Port: 5432")
        console.print("  Default user: postgres")
        console.print()
        console.print("[dim]To access: sudo -u postgres psql[/dim]")
    else:
        show_warning("PostgreSQL installed but service may not be running.")
    
    press_enter_to_continue()


# =============================================================================
# MariaDB Functions
# =============================================================================

def install_mariadb():
    """Install MariaDB server."""
    clear_screen()
    show_header()
    show_panel("Install MariaDB", title="Database", style="cyan")
    
    if is_installed("mariadb-server"):
        show_info("MariaDB is already installed.")
        
        if is_service_running("mariadb"):
            console.print("[dim]Service is running.[/dim]")
        else:
            if confirm_action("Start MariaDB service?"):
                service_control("mariadb", "start")
                show_success("MariaDB started!")
        
        press_enter_to_continue()
        return
    
    if not confirm_action("Install MariaDB server?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    show_info("Installing MariaDB...")
    
    returncode = run_command_realtime(
        "apt install -y mariadb-server mariadb-client",
        "Installing MariaDB..."
    )
    
    if returncode != 0:
        show_error("Failed to install MariaDB.")
        press_enter_to_continue()
        return
    
    service_control("mariadb", "start")
    service_control("mariadb", "enable")
    
    if is_service_running("mariadb"):
        show_success("MariaDB installed and running!")
        
        console.print()
        console.print("[bold]Connection Info:[/bold]")
        console.print("  Host: localhost")
        console.print("  Port: 3306")
        console.print("  Default user: root (no password)")
        console.print()
        console.print("[yellow]IMPORTANT: Run 'Secure Installation' next![/yellow]")
    else:
        show_warning("MariaDB installed but service may not be running.")
    
    press_enter_to_continue()


def secure_mariadb_installation():
    """Run automated mysql_secure_installation for MariaDB."""
    clear_screen()
    show_header()
    show_panel("Secure MariaDB Installation", title="Database", style="cyan")
    
    if not is_installed("mariadb-server"):
        show_error("MariaDB is not installed.")
        press_enter_to_continue()
        return
    
    if not is_service_running("mariadb"):
        show_error("MariaDB service is not running.")
        press_enter_to_continue()
        return
    
    console.print("[bold]This will:[/bold]")
    console.print("  • Set root password")
    console.print("  • Remove anonymous users")
    console.print("  • Disable remote root login")
    console.print("  • Remove test database")
    console.print("  • Reload privilege tables")
    console.print()
    
    root_password = text_input(
        title="Root Password",
        message="Enter new root password for MariaDB:",
        password=True
    )
    
    if not root_password:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    confirm_password = text_input(
        title="Confirm Password",
        message="Confirm root password:",
        password=True
    )
    
    if root_password != confirm_password:
        show_error("Passwords do not match!")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    show_info("Securing MariaDB installation...")
    
    # Create secure installation SQL
    secure_sql = f"""
ALTER USER 'root'@'localhost' IDENTIFIED BY '{root_password}';
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
"""
    
    result = run_command(
        f'mysql -u root -e "{secure_sql}"',
        check=False,
        silent=True
    )
    
    if result.returncode == 0:
        show_success("MariaDB secured successfully!")
        console.print()
        console.print("[dim]Root password has been set.[/dim]")
        console.print("[dim]To connect: mysql -u root -p[/dim]")
    else:
        show_error("Failed to secure MariaDB. May already be secured.")
        console.print(f"[dim]{result.stderr}[/dim]")
    
    press_enter_to_continue()


# =============================================================================
# Database CRUD Functions (Both Engines)
# =============================================================================

def create_database_interactive(engine):
    """Interactive prompt to create a database."""
    clear_screen()
    show_header()
    show_panel(f"Create Database ({engine.upper()})", title="Database", style="cyan")
    
    if not _check_engine_installed(engine):
        press_enter_to_continue()
        return
    
    db_name = text_input(
        title="Create Database",
        message="Enter database name:"
    )
    
    if not db_name:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not db_name.replace("_", "").isalnum():
        show_error("Database name can only contain letters, numbers, and underscores.")
        press_enter_to_continue()
        return
    
    success = create_database(engine, db_name)
    
    if success:
        show_success(f"Database '{db_name}' created successfully!")
    else:
        show_error(f"Failed to create database '{db_name}'")
    
    press_enter_to_continue()


def create_database(engine, db_name):
    """
    Create a new database.
    
    Args:
        engine: "postgresql" or "mariadb"
        db_name: Database name
    
    Returns:
        bool: True if successful
    """
    if engine == "postgresql":
        result = run_command(
            f'sudo -u postgres psql -c "CREATE DATABASE {db_name};"',
            check=False,
            silent=True
        )
    else:  # mariadb
        result = run_command(
            f'mysql -u root -e "CREATE DATABASE {db_name};"',
            check=False,
            silent=True
        )
    
    return result.returncode == 0


def create_user_interactive(engine):
    """Interactive prompt to create a database user."""
    clear_screen()
    show_header()
    show_panel(f"Create User ({engine.upper()})", title="Database", style="cyan")
    
    if not _check_engine_installed(engine):
        press_enter_to_continue()
        return
    
    username = text_input(
        title="Create User",
        message="Enter username:"
    )
    
    if not username:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not username.replace("_", "").isalnum():
        show_error("Username can only contain letters, numbers, and underscores.")
        press_enter_to_continue()
        return
    
    password = text_input(
        title="Password",
        message=f"Enter password for '{username}':",
        password=True
    )
    
    if not password:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Ask for database to grant access
    databases = _get_databases(engine)
    db_name = None
    if databases:
        user_dbs = [db for db in databases if db not in _get_system_databases(engine)]
        if user_dbs:
            console.print()
            console.print("[bold]Grant access to database (optional):[/bold]")
            db_name = select_from_list(
                title="Select Database",
                message="Grant all privileges on which database?",
                options=["(skip)"] + user_dbs
            )
            if db_name == "(skip)":
                db_name = None
    
    success = create_user(engine, username, password, db_name)
    
    if success:
        show_success(f"User '{username}' created successfully!")
        if db_name:
            console.print(f"[dim]Granted all privileges on '{db_name}'[/dim]")
    else:
        show_error(f"Failed to create user '{username}'")
    
    press_enter_to_continue()


def create_user(engine, username, password, db_name=None):
    """
    Create a database user with optional database privileges.
    
    Args:
        engine: "postgresql" or "mariadb"
        username: Username
        password: Password
        db_name: Optional database to grant privileges on
    
    Returns:
        bool: True if successful
    """
    if engine == "postgresql":
        result = run_command(
            f"sudo -u postgres psql -c \"CREATE USER {username} WITH PASSWORD '{password}';\"",
            check=False,
            silent=True
        )
        
        if result.returncode != 0:
            return False
        
        if db_name:
            run_command(
                f'sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {username};"',
                check=False,
                silent=True
            )
    else:  # mariadb
        result = run_command(
            f"mysql -u root -e \"CREATE USER '{username}'@'localhost' IDENTIFIED BY '{password}';\"",
            check=False,
            silent=True
        )
        
        if result.returncode != 0:
            return False
        
        if db_name:
            run_command(
                f"mysql -u root -e \"GRANT ALL PRIVILEGES ON {db_name}.* TO '{username}'@'localhost';\"",
                check=False,
                silent=True
            )
        
        run_command("mysql -u root -e 'FLUSH PRIVILEGES;'", check=False, silent=True)
    
    return True


def list_databases(engine):
    """Display a table of databases."""
    clear_screen()
    show_header()
    show_panel(f"Databases ({engine.upper()})", title="Database", style="cyan")
    
    if not _check_engine_installed(engine):
        press_enter_to_continue()
        return
    
    databases = _get_databases(engine)
    
    if not databases:
        show_info("No databases found (or unable to list).")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Database Name", "style": "cyan"},
        {"name": "Type"},
    ]
    
    rows = []
    system_dbs = _get_system_databases(engine)
    
    for db in databases:
        db_type = "[dim]System[/dim]" if db in system_dbs else "User"
        rows.append([db, db_type])
    
    show_table(f"Total: {len(databases)} database(s)", columns, rows)
    
    press_enter_to_continue()


def delete_database_interactive(engine):
    """Interactive prompt to delete a database."""
    clear_screen()
    show_header()
    show_panel(f"Delete Database ({engine.upper()})", title="Database", style="cyan")
    
    if not _check_engine_installed(engine):
        press_enter_to_continue()
        return
    
    databases = _get_databases(engine)
    system_dbs = _get_system_databases(engine)
    
    user_databases = [db for db in databases if db not in system_dbs]
    
    if not user_databases:
        show_info("No user databases to delete.")
        press_enter_to_continue()
        return
    
    db_name = select_from_list(
        title="Delete Database",
        message="Select database to delete:",
        options=user_databases
    )
    
    if not db_name:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print(f"[red bold]WARNING: This will permanently delete database '{db_name}'![/red bold]")
    console.print()
    
    if not confirm_action(f"Are you sure you want to delete '{db_name}'?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = delete_database(engine, db_name)
    
    if success:
        show_success(f"Database '{db_name}' deleted successfully!")
    else:
        show_error(f"Failed to delete database '{db_name}'")
    
    press_enter_to_continue()


def delete_database(engine, db_name):
    """
    Delete a database.
    
    Args:
        engine: "postgresql" or "mariadb"
        db_name: Database name
    
    Returns:
        bool: True if successful
    """
    if engine == "postgresql":
        result = run_command(
            f'sudo -u postgres psql -c "DROP DATABASE {db_name};"',
            check=False,
            silent=True
        )
    else:  # mariadb
        result = run_command(
            f'mysql -u root -e "DROP DATABASE {db_name};"',
            check=False,
            silent=True
        )
    
    return result.returncode == 0


def delete_user_interactive(engine):
    """Interactive prompt to delete a database user."""
    clear_screen()
    show_header()
    show_panel(f"Delete User ({engine.upper()})", title="Database", style="cyan")
    
    if not _check_engine_installed(engine):
        press_enter_to_continue()
        return
    
    users = _get_users(engine)
    system_users = _get_system_users(engine)
    
    user_list = [u for u in users if u not in system_users]
    
    if not user_list:
        show_info("No user accounts to delete.")
        press_enter_to_continue()
        return
    
    username = select_from_list(
        title="Delete User",
        message="Select user to delete:",
        options=user_list
    )
    
    if not username:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print(f"[red bold]WARNING: This will permanently delete user '{username}'![/red bold]")
    console.print()
    
    if not confirm_action(f"Are you sure you want to delete '{username}'?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = delete_user(engine, username)
    
    if success:
        show_success(f"User '{username}' deleted successfully!")
    else:
        show_error(f"Failed to delete user '{username}'")
    
    press_enter_to_continue()


def delete_user(engine, username):
    """
    Delete a database user.
    
    Args:
        engine: "postgresql" or "mariadb"
        username: Username
    
    Returns:
        bool: True if successful
    """
    if engine == "postgresql":
        result = run_command(
            f'sudo -u postgres psql -c "DROP USER {username};"',
            check=False,
            silent=True
        )
    else:  # mariadb
        result = run_command(
            f"mysql -u root -e \"DROP USER '{username}'@'localhost';\"",
            check=False,
            silent=True
        )
        run_command("mysql -u root -e 'FLUSH PRIVILEGES;'", check=False, silent=True)
    
    return result.returncode == 0


# =============================================================================
# Helper Functions
# =============================================================================

def _check_engine_installed(engine):
    """Check if database engine is installed and running."""
    if engine == "postgresql":
        if not is_installed("postgresql"):
            show_error("PostgreSQL is not installed.")
            return False
        if not is_service_running("postgresql"):
            show_error("PostgreSQL service is not running.")
            return False
    else:  # mariadb
        if not is_installed("mariadb-server"):
            show_error("MariaDB is not installed.")
            return False
        if not is_service_running("mariadb"):
            show_error("MariaDB service is not running.")
            return False
    return True


def _get_databases(engine):
    """Get list of databases."""
    if engine == "postgresql":
        result = run_command(
            "sudo -u postgres psql -t -c \"SELECT datname FROM pg_database WHERE datistemplate = false;\"",
            check=False,
            silent=True
        )
        if result.returncode != 0:
            return []
        return [db.strip() for db in result.stdout.strip().split('\n') if db.strip()]
    
    else:  # mariadb
        result = run_command(
            "mysql -u root -N -e 'SHOW DATABASES;'",
            check=False,
            silent=True
        )
        if result.returncode != 0:
            return []
        return [db.strip() for db in result.stdout.strip().split('\n') if db.strip()]


def _get_users(engine):
    """Get list of database users."""
    if engine == "postgresql":
        result = run_command(
            "sudo -u postgres psql -t -c \"SELECT usename FROM pg_catalog.pg_user;\"",
            check=False,
            silent=True
        )
        if result.returncode != 0:
            return []
        return [u.strip() for u in result.stdout.strip().split('\n') if u.strip()]
    
    else:  # mariadb
        result = run_command(
            "mysql -u root -N -e \"SELECT User FROM mysql.user WHERE Host='localhost';\"",
            check=False,
            silent=True
        )
        if result.returncode != 0:
            return []
        return [u.strip() for u in result.stdout.strip().split('\n') if u.strip()]


def _get_system_databases(engine):
    """Get list of system databases that shouldn't be modified."""
    if engine == "postgresql":
        return ["postgres", "template0", "template1"]
    else:  # mariadb
        return ["information_schema", "mysql", "performance_schema", "sys"]


def _get_system_users(engine):
    """Get list of system users that shouldn't be deleted."""
    if engine == "postgresql":
        return ["postgres"]
    else:  # mariadb
        return ["root", "mysql", "mariadb.sys"]


# =============================================================================
# Redis Functions
# =============================================================================

def show_redis_menu():
    """Display Redis submenu."""
    while True:
        clear_screen()
        show_header()
        
        if is_service_running("redis-server"):
            status = "[green]Running[/green]"
        elif is_installed("redis-server"):
            status = "[red]Stopped[/red]"
        else:
            status = "[dim]Not installed[/dim]"
        
        console.print(f"[dim]Redis Status: {status}[/dim]")
        console.print()
        
        # Build dynamic options based on install status
        options = []
        
        if is_installed("redis-server"):
            options.extend([
                ("status", "1. Show Status"),
                ("info", "2. Redis Info"),
                ("service", "3. Service Control"),
                ("test", "4. Test Connection"),
                ("flush", "5. Flush Cache"),
            ])
        else:
            options.append(("install", "1. Install Redis"))
        
        options.append(("back", "← Back"))
        
        choice = show_submenu(
            title="Redis Management",
            options=options,
        )
        
        if choice == "install":
            install_redis()
        elif choice == "status":
            show_redis_status()
        elif choice == "info":
            show_redis_info()
        elif choice == "service":
            redis_service_control()
        elif choice == "test":
            test_redis_connection()
        elif choice == "flush":
            flush_redis_cache()
        elif choice == "back" or choice is None:
            break


def install_redis():
    """Install Redis server."""
    clear_screen()
    show_header()
    show_panel("Install Redis Server", title="Redis", style="cyan")
    
    if is_installed("redis-server"):
        show_info("Redis is already installed.")
        press_enter_to_continue()
        return
    
    if not confirm_action("Install Redis server?"):
        return
    
    show_info("Installing Redis...")
    
    result = run_command_with_progress(
        "apt update && apt install -y redis-server",
        description="Installing Redis server",
    )
    
    if result.returncode != 0:
        show_error("Failed to install Redis.")
        press_enter_to_continue()
        return
    
    # Enable and start Redis
    run_command("systemctl enable redis-server", check=False, silent=True)
    service_control("redis-server", "start")
    
    show_success("Redis installed and started successfully!")
    press_enter_to_continue()


def show_redis_status():
    """Show Redis service status."""
    clear_screen()
    show_header()
    show_panel("Redis Status", title="Redis", style="cyan")
    
    if not is_installed("redis-server"):
        show_warning("Redis is not installed.")
        press_enter_to_continue()
        return
    
    # Get service status
    result = run_command("systemctl status redis-server", check=False, silent=True)
    
    if is_service_running("redis-server"):
        show_success("Redis is running")
    else:
        show_error("Redis is stopped")
    
    console.print()
    console.print("[bold]Service Status:[/bold]")
    console.print(result.stdout if result.stdout else result.stderr)
    
    press_enter_to_continue()


def show_redis_info():
    """Show Redis server info and stats."""
    clear_screen()
    show_header()
    show_panel("Redis Info", title="Redis", style="cyan")
    
    if not is_service_running("redis-server"):
        show_warning("Redis is not running.")
        press_enter_to_continue()
        return
    
    # Get Redis info
    result = run_command("redis-cli INFO", check=False, silent=True)
    
    if result.returncode != 0:
        show_error("Failed to get Redis info.")
        press_enter_to_continue()
        return
    
    # Parse and display key info
    info = result.stdout
    
    # Extract key metrics
    metrics = []
    for line in info.split('\n'):
        if ':' in line and not line.startswith('#'):
            key, value = line.strip().split(':', 1)
            if key in ['redis_version', 'uptime_in_seconds', 'connected_clients', 
                       'used_memory_human', 'total_connections_received', 
                       'total_commands_processed', 'keyspace_hits', 'keyspace_misses']:
                metrics.append((key, value))
    
    if metrics:
        columns = [
            {"name": "Metric", "style": "cyan"},
            {"name": "Value", "style": "white"},
        ]
        show_table("Redis Statistics", columns, metrics)
    
    # Show keyspace info
    console.print()
    console.print("[bold]Keyspace:[/bold]")
    result = run_command("redis-cli INFO keyspace", check=False, silent=True)
    if result.stdout:
        for line in result.stdout.split('\n'):
            if line.startswith('db'):
                console.print(f"  {line}")
    else:
        console.print("  [dim]No databases with keys[/dim]")
    
    press_enter_to_continue()


def redis_service_control():
    """Control Redis service (start/stop/restart)."""
    clear_screen()
    show_header()
    show_panel("Redis Service Control", title="Redis", style="cyan")
    
    if not is_installed("redis-server"):
        show_warning("Redis is not installed.")
        press_enter_to_continue()
        return
    
    current_status = "Running" if is_service_running("redis-server") else "Stopped"
    console.print(f"[dim]Current status: {current_status}[/dim]")
    console.print()
    
    actions = ["start", "stop", "restart"]
    action = select_from_list(
        title="Service Control",
        message="Select action",
        options=actions,
    )
    
    if not action:
        return
    
    if not confirm_action(f"{action.capitalize()} Redis service?"):
        return
    
    result = service_control("redis-server", action)
    
    if result:
        show_success(f"Redis service {action}ed successfully!")
    else:
        show_error(f"Failed to {action} Redis service.")
    
    press_enter_to_continue()


def test_redis_connection():
    """Test Redis connection with PING."""
    clear_screen()
    show_header()
    show_panel("Test Redis Connection", title="Redis", style="cyan")
    
    if not is_service_running("redis-server"):
        show_warning("Redis is not running.")
        press_enter_to_continue()
        return
    
    show_info("Testing connection with PING...")
    
    result = run_command("redis-cli PING", check=False, silent=True)
    
    if result.returncode == 0 and "PONG" in result.stdout:
        show_success("Connection successful! Redis responded with PONG")
    else:
        show_error("Connection failed!")
        if result.stderr:
            console.print(f"[red]{result.stderr}[/red]")
    
    press_enter_to_continue()


def flush_redis_cache():
    """Flush Redis cache (FLUSHALL or FLUSHDB)."""
    clear_screen()
    show_header()
    show_panel("Flush Redis Cache", title="Redis", style="cyan")
    
    if not is_service_running("redis-server"):
        show_warning("Redis is not running.")
        press_enter_to_continue()
        return
    
    show_warning("This will delete cached data!")
    console.print()
    
    flush_options = [
        "FLUSHDB - Flush current database (db0)",
        "FLUSHALL - Flush ALL databases",
    ]
    
    choice = select_from_list(
        title="Flush Cache",
        message="Select flush option",
        options=flush_options,
    )
    
    if not choice:
        return
    
    cmd = "FLUSHDB" if "FLUSHDB" in choice else "FLUSHALL"
    
    if not confirm_action(f"Execute {cmd}? This cannot be undone!"):
        return
    
    result = run_command(f"redis-cli {cmd}", check=False, silent=True)
    
    if result.returncode == 0 and "OK" in result.stdout:
        show_success(f"{cmd} executed successfully!")
    else:
        show_error(f"Failed to execute {cmd}.")
        if result.stderr:
            console.print(f"[red]{result.stderr}[/red]")
    
    press_enter_to_continue()
