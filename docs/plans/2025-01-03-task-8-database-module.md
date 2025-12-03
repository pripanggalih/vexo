# Task 8.0: Database Module Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create database management module supporting PostgreSQL and MariaDB with database/user CRUD operations.

**Architecture:** Single `modules/database.py` with two database engines (PostgreSQL, MariaDB). Each engine has install, secure, and CRUD operations. Menu system allows selecting which database engine to manage.

**Tech Stack:** PostgreSQL (psql CLI), MariaDB (mysql CLI), existing shell.py utilities, Rich UI components

---

## Sub-tasks Overview

| Sub-task | Description | Commit |
|----------|-------------|--------|
| 8.1 | Create database.py with show_menu() | Yes |
| 8.2 | Add install_postgresql() | Yes |
| 8.3 | Add install_mariadb() | Yes |
| 8.4 | Add secure_mariadb_installation() | Yes |
| 8.5 | Add create_database() for both engines | Yes |
| 8.6 | Add create_user() for both engines | Yes |
| 8.7 | Add list_databases() for both engines | Yes |
| 8.8 | Add delete_database() for both engines | Yes |
| 8.9 | Add delete_user() for both engines | Yes |
| 8.10 | Update modules/__init__.py and task list | Yes |

**Total: 10 sub-tasks, 10 commits**

---

## Task 8.1: Create database.py with show_menu()

**Files:**
- Create: `modules/database.py`

**Step 1: Create database module with menu**

```python
"""Database management module for vexo-cli (PostgreSQL & MariaDB)."""

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_success,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import show_submenu, confirm_action, text_input, select_from_list
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
    """
    Display the Database Management submenu and handle user selection.
    """
    while True:
        clear_screen()
        show_header()
        
        # Show installed status
        pg_status = "[green]Installed[/green]" if is_installed("postgresql") else "[dim]Not installed[/dim]"
        maria_status = "[green]Installed[/green]" if is_installed("mariadb-server") else "[dim]Not installed[/dim]"
        
        console.print(f"[dim]PostgreSQL: {pg_status} | MariaDB: {maria_status}[/dim]")
        console.print()
        
        choice = show_submenu(
            title="Database Management",
            options=[
                ("pgsql", "1. PostgreSQL Management"),
                ("mariadb", "2. MariaDB Management"),
                ("back", "← Back to Main Menu"),
            ],
        )
        
        if choice == "pgsql":
            show_postgresql_menu()
        elif choice == "mariadb":
            show_mariadb_menu()
        elif choice == "back" or choice is None:
            break


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
        
        choice = show_submenu(
            title="PostgreSQL Management",
            options=[
                ("install", "1. Install PostgreSQL"),
                ("list_db", "2. List Databases"),
                ("create_db", "3. Create Database"),
                ("delete_db", "4. Delete Database"),
                ("create_user", "5. Create User"),
                ("delete_user", "6. Delete User"),
                ("back", "← Back"),
            ],
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
        
        choice = show_submenu(
            title="MariaDB Management",
            options=[
                ("install", "1. Install MariaDB"),
                ("secure", "2. Secure Installation"),
                ("list_db", "3. List Databases"),
                ("create_db", "4. Create Database"),
                ("delete_db", "5. Delete Database"),
                ("create_user", "6. Create User"),
                ("delete_user", "7. Delete User"),
                ("back", "← Back"),
            ],
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
```

**Step 2: Commit**

```bash
git add modules/database.py
git commit -m "feat(database): add database.py with menu structure"
```

---

## Task 8.2: Add install_postgresql()

**Files:**
- Modify: `modules/database.py`

**Step 1: Add PostgreSQL installation function**

Append to `modules/database.py`:

```python
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
        
        # Show connection info
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
```

**Step 2: Commit**

```bash
git add modules/database.py
git commit -m "feat(database): add install_postgresql()"
```

---

## Task 8.3: Add install_mariadb()

**Files:**
- Modify: `modules/database.py`

**Step 1: Add MariaDB installation function**

Append to `modules/database.py`:

```python
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
```

**Step 2: Commit**

```bash
git add modules/database.py
git commit -m "feat(database): add install_mariadb()"
```

---

## Task 8.4: Add secure_mariadb_installation()

**Files:**
- Modify: `modules/database.py`

**Step 1: Add MariaDB secure installation function**

Append to `modules/database.py`:

```python
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
-- Set root password
ALTER USER 'root'@'localhost' IDENTIFIED BY '{root_password}';

-- Remove anonymous users
DELETE FROM mysql.user WHERE User='';

-- Disallow root login remotely
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');

-- Remove test database
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';

-- Reload privileges
FLUSH PRIVILEGES;
"""
    
    result = run_command(
        f'mysql -u root -e "{secure_sql}"',
        check=False,
        silent=True
    )
    
    if result.returncode != 0:
        # Try without password (fresh install)
        result = run_command(
            f"mysql -u root <<EOF\n{secure_sql}\nEOF",
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
```

**Step 2: Commit**

```bash
git add modules/database.py
git commit -m "feat(database): add secure_mariadb_installation()"
```

---

## Task 8.5: Add create_database()

**Files:**
- Modify: `modules/database.py`

**Step 1: Add database creation functions**

Append to `modules/database.py`:

```python
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
    
    # Validate name
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
```

**Step 2: Commit**

```bash
git add modules/database.py
git commit -m "feat(database): add create_database() for PostgreSQL and MariaDB"
```

---

## Task 8.6: Add create_user()

**Files:**
- Modify: `modules/database.py`

**Step 1: Add user creation functions**

Append to `modules/database.py`:

```python
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
    if databases:
        console.print()
        console.print("[bold]Grant access to database (optional):[/bold]")
        db_name = select_from_list(
            title="Select Database",
            message="Grant all privileges on which database? (optional)",
            options=["(none)"] + databases
        )
        if db_name == "(none)":
            db_name = None
    else:
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
        # Create user
        result = run_command(
            f"sudo -u postgres psql -c \"CREATE USER {username} WITH PASSWORD '{password}';\"",
            check=False,
            silent=True
        )
        
        if result.returncode != 0:
            return False
        
        # Grant privileges if database specified
        if db_name:
            run_command(
                f'sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {username};"',
                check=False,
                silent=True
            )
    else:  # mariadb
        # Create user
        result = run_command(
            f"mysql -u root -e \"CREATE USER '{username}'@'localhost' IDENTIFIED BY '{password}';\"",
            check=False,
            silent=True
        )
        
        if result.returncode != 0:
            return False
        
        # Grant privileges if database specified
        if db_name:
            run_command(
                f"mysql -u root -e \"GRANT ALL PRIVILEGES ON {db_name}.* TO '{username}'@'localhost';\"",
                check=False,
                silent=True
            )
        
        run_command("mysql -u root -e 'FLUSH PRIVILEGES;'", check=False, silent=True)
    
    return True
```

**Step 2: Commit**

```bash
git add modules/database.py
git commit -m "feat(database): add create_user() with privilege granting"
```

---

## Task 8.7: Add list_databases()

**Files:**
- Modify: `modules/database.py`

**Step 1: Add database listing function**

Append to `modules/database.py`:

```python
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


def _get_system_databases(engine):
    """Get list of system databases that shouldn't be modified."""
    if engine == "postgresql":
        return ["postgres", "template0", "template1"]
    else:  # mariadb
        return ["information_schema", "mysql", "performance_schema", "sys"]


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
```

**Step 2: Commit**

```bash
git add modules/database.py
git commit -m "feat(database): add list_databases() with system/user classification"
```

---

## Task 8.8: Add delete_database()

**Files:**
- Modify: `modules/database.py`

**Step 1: Add database deletion function**

Append to `modules/database.py`:

```python
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
    
    # Filter out system databases
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
```

**Step 2: Commit**

```bash
git add modules/database.py
git commit -m "feat(database): add delete_database() with safety checks"
```

---

## Task 8.9: Add delete_user()

**Files:**
- Modify: `modules/database.py`

**Step 1: Add user deletion function**

Append to `modules/database.py`:

```python
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
    
    # Filter out system users
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


def _get_system_users(engine):
    """Get list of system users that shouldn't be deleted."""
    if engine == "postgresql":
        return ["postgres"]
    else:  # mariadb
        return ["root", "mysql", "mariadb.sys"]
```

**Step 2: Commit**

```bash
git add modules/database.py
git commit -m "feat(database): add delete_user() with system user protection"
```

---

## Task 8.10: Update modules/__init__.py and task list

**Files:**
- Modify: `modules/__init__.py`
- Modify: `tasks/tasks-vexo-cli.md`

**Step 1: Update modules/__init__.py**

Add database import:

```python
"""Business logic modules for vexo-cli - system, webserver, runtime, database, email."""

from modules import system
from modules import webserver
from modules import runtime
from modules import database
```

**Step 2: Update task list**

Mark all Task 8.x items as `[x]` complete.

**Step 3: Commit**

```bash
git add modules/__init__.py tasks/tasks-vexo-cli.md
git commit -m "docs: mark Task 8.0 Database Module as complete"
```

---

## Summary

After completion, `modules/database.py` will have:

**Menu Functions:**
- `show_menu()` - Main database menu (PostgreSQL/MariaDB choice)
- `show_postgresql_menu()` - PostgreSQL submenu (7 options)
- `show_mariadb_menu()` - MariaDB submenu (8 options)

**PostgreSQL Functions:**
- `install_postgresql()` - Install postgresql + postgresql-contrib

**MariaDB Functions:**
- `install_mariadb()` - Install mariadb-server + mariadb-client
- `secure_mariadb_installation()` - Automated mysql_secure_installation

**CRUD Functions (both engines):**
- `create_database()` - Create database
- `create_user()` - Create user with optional privilege grant
- `list_databases()` - List databases with system/user classification
- `delete_database()` - Delete database with confirmation
- `delete_user()` - Delete user with system protection

**Helper Functions:**
- `_get_databases()` - Get database list
- `_get_users()` - Get user list
- `_get_system_databases()` - System databases to protect
- `_get_system_users()` - System users to protect
- `_check_engine_installed()` - Verify engine is ready
