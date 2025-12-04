# MariaDB Enhancements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add comprehensive MariaDB management features including backup/restore, import/export, monitoring, configuration, and security management.

**Architecture:** Create `modules/database/mariadb/` folder structure with separate files for each feature group. Uses `mysql`, `mysqldump` commands.

**Tech Stack:** Python, MariaDB/MySQL, mysqldump, mysql CLI

---

## Task 1: Create MariaDB Folder Structure

**Files:**
- Create: `modules/database/mariadb/__init__.py`
- Create: `modules/database/mariadb/utils.py`

**Step 1: Create modules/database/mariadb/utils.py**

```python
"""Shared utilities for MariaDB module."""

import os
import configparser

from utils.shell import run_command, is_installed, is_service_running

# Backup directory
MARIA_BACKUP_DIR = "/var/backups/mariadb"

# System databases
MARIA_SYSTEM_DBS = ["mysql", "information_schema", "performance_schema", "sys"]

# System users
MARIA_SYSTEM_USERS = ["root", "mysql.sys", "mysql.session", "mysql.infoschema", "debian-sys-maint"]


def is_mariadb_ready():
    """Check if MariaDB is installed and running."""
    return is_installed("mariadb-server") and is_service_running("mariadb")


def get_mysql_credentials():
    """Get MySQL credentials from debian-sys-maint or root."""
    # Try debian-sys-maint first
    debian_cnf = "/etc/mysql/debian.cnf"
    if os.path.exists(debian_cnf):
        config = configparser.ConfigParser()
        config.read(debian_cnf)
        if 'client' in config:
            return config['client'].get('user'), config['client'].get('password')
    return None, None


def run_mysql(sql, database="", silent=True):
    """Run SQL command via mysql."""
    user, password = get_mysql_credentials()
    
    if user and password:
        auth = f"-u{user} -p{password}"
    else:
        # Try socket auth as root
        auth = "-u root"
    
    db_opt = f"-D {database}" if database else ""
    cmd = f'mysql {auth} {db_opt} -N -e "{sql}"'
    return run_command(cmd, check=False, silent=silent)


def run_mysql_file(filepath, database=""):
    """Run SQL file via mysql."""
    user, password = get_mysql_credentials()
    
    if user and password:
        auth = f"-u{user} -p{password}"
    else:
        auth = "-u root"
    
    db_opt = f"-D {database}" if database else ""
    cmd = f'mysql {auth} {db_opt} < "{filepath}"'
    return run_command(cmd, check=False, silent=True)


def get_databases():
    """Get list of MariaDB databases."""
    result = run_mysql("SHOW DATABASES;")
    if result.returncode != 0:
        return []
    return [db.strip() for db in result.stdout.strip().split('\n') if db.strip()]


def get_user_databases():
    """Get non-system databases."""
    return [db for db in get_databases() if db not in MARIA_SYSTEM_DBS]


def get_users():
    """Get list of MariaDB users."""
    result = run_mysql("SELECT DISTINCT User FROM mysql.user;")
    if result.returncode != 0:
        return []
    return [u.strip() for u in result.stdout.strip().split('\n') if u.strip()]


def get_database_size(database):
    """Get database size in bytes."""
    sql = f"""
    SELECT SUM(data_length + index_length) 
    FROM information_schema.tables 
    WHERE table_schema = '{database}';
    """
    result = run_mysql(sql)
    if result.returncode == 0 and result.stdout.strip():
        try:
            size = result.stdout.strip()
            return int(float(size)) if size and size != 'NULL' else 0
        except ValueError:
            pass
    return 0


def format_size(size_bytes):
    """Format size in bytes to human readable."""
    if size_bytes >= 1024 ** 3:
        return f"{size_bytes / 1024 ** 3:.2f} GB"
    elif size_bytes >= 1024 ** 2:
        return f"{size_bytes / 1024 ** 2:.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes} B"


def get_mariadb_version():
    """Get MariaDB version."""
    result = run_mysql("SELECT VERSION();")
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def get_mariadb_datadir():
    """Get MariaDB data directory."""
    result = run_mysql("SELECT @@datadir;")
    if result.returncode == 0:
        return result.stdout.strip()
    return "/var/lib/mysql"
```

**Step 2: Create modules/database/mariadb/__init__.py**

```python
"""MariaDB management module."""

from ui.menu import run_menu_loop
from utils.shell import is_installed, is_service_running


def show_menu():
    """Display MariaDB Management submenu."""
    def get_status():
        if not is_installed("mariadb-server"):
            return "MariaDB: [yellow]Not installed[/yellow]"
        if is_service_running("mariadb"):
            return "MariaDB: [green]Running[/green]"
        return "MariaDB: [red]Stopped[/red]"
    
    def get_options():
        options = []
        if is_installed("mariadb-server"):
            options.extend([
                ("list", "1. List Databases"),
                ("create", "2. Create Database"),
                ("delete", "3. Delete Database"),
                ("users", "4. User Management"),
                ("backup", "5. Backup & Restore"),
                ("import", "6. Import/Export"),
                ("monitor", "7. Monitoring"),
                ("config", "8. Configuration"),
                ("security", "9. Security"),
            ])
        else:
            options.append(("install", "1. Install MariaDB"))
        options.append(("back", "← Back"))
        return options
    
    def get_handlers():
        from modules.database.mariadb.core import (
            list_databases, create_database_interactive,
            delete_database_interactive, install_mariadb,
        )
        from modules.database.mariadb.users import show_users_menu
        from modules.database.mariadb.backup import show_backup_menu
        from modules.database.mariadb.importexport import show_import_menu
        from modules.database.mariadb.monitor import show_monitor_menu
        from modules.database.mariadb.config import show_config_menu
        from modules.database.mariadb.security import show_security_menu
        
        return {
            "install": install_mariadb,
            "list": list_databases,
            "create": create_database_interactive,
            "delete": delete_database_interactive,
            "users": show_users_menu,
            "backup": show_backup_menu,
            "import": show_import_menu,
            "monitor": show_monitor_menu,
            "config": show_config_menu,
            "security": show_security_menu,
        }
    
    run_menu_loop("MariaDB Management", get_options, get_handlers(), get_status)
```

**Step 3: Commit**

```bash
git add modules/database/mariadb/
git commit -m "refactor(database): create MariaDB folder structure"
```

---

## Task 2: Create MariaDB Backup Module

**Files:**
- Create: `modules/database/mariadb/backup.py`

**Step 1: Create backup.py**

```python
"""MariaDB backup and restore functions."""

import os
from datetime import datetime

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, require_root
from modules.database.mariadb.utils import (
    is_mariadb_ready, get_user_databases, get_database_size,
    format_size, MARIA_BACKUP_DIR, get_mysql_credentials,
)


def show_backup_menu():
    """Display Backup & Restore submenu."""
    options = [
        ("backup", "1. Backup Database"),
        ("backup_all", "2. Backup All Databases"),
        ("restore", "3. Restore Database"),
        ("list", "4. List Backups"),
        ("schedule", "5. Scheduled Backups"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "backup": backup_database,
        "backup_all": backup_all_databases,
        "restore": restore_database,
        "list": list_backups,
        "schedule": scheduled_backups,
    }
    
    run_menu_loop("Backup & Restore", options, handlers)


def backup_database():
    """Backup a single database."""
    clear_screen()
    show_header()
    show_panel("Backup Database", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    databases = get_user_databases()
    if not databases:
        show_info("No user databases found.")
        press_enter_to_continue()
        return
    
    # Show databases with sizes
    console.print("[bold]Available Databases:[/bold]")
    for db in databases:
        size = format_size(get_database_size(db))
        console.print(f"  • {db} ({size})")
    console.print()
    
    database = select_from_list("Select Database", "Backup:", databases)
    if not database:
        return
    
    compress = confirm_action("Compress backup (gzip)?")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = ".sql.gz" if compress else ".sql"
    default_path = os.path.join(MARIA_BACKUP_DIR, f"{database}_{timestamp}{ext}")
    
    backup_path = text_input("Backup path:", default=default_path)
    if not backup_path:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    
    user, password = get_mysql_credentials()
    if user and password:
        auth = f"-u{user} -p{password}"
    else:
        auth = "-u root"
    
    if compress:
        cmd = f"mysqldump {auth} {database} | gzip > {backup_path}"
    else:
        cmd = f"mysqldump {auth} {database} > {backup_path}"
    
    console.print()
    show_info(f"Backing up {database}...")
    
    result = run_command(cmd, check=False, silent=False)
    
    if result.returncode == 0 and os.path.exists(backup_path):
        size = format_size(os.path.getsize(backup_path))
        show_success(f"Backup created: {backup_path} ({size})")
    else:
        show_error("Backup failed!")
        if result.stderr:
            console.print(f"[dim]{result.stderr}[/dim]")
    
    press_enter_to_continue()


def backup_all_databases():
    """Backup all databases."""
    clear_screen()
    show_header()
    show_panel("Backup All Databases", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    compress = confirm_action("Compress backup (gzip)?")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = ".sql.gz" if compress else ".sql"
    default_path = os.path.join(MARIA_BACKUP_DIR, f"all_databases_{timestamp}{ext}")
    
    backup_path = text_input("Backup path:", default=default_path)
    if not backup_path:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    
    user, password = get_mysql_credentials()
    if user and password:
        auth = f"-u{user} -p{password}"
    else:
        auth = "-u root"
    
    if compress:
        cmd = f"mysqldump {auth} --all-databases | gzip > {backup_path}"
    else:
        cmd = f"mysqldump {auth} --all-databases > {backup_path}"
    
    console.print()
    show_info("Backing up all databases...")
    
    result = run_command(cmd, check=False, silent=False)
    
    if result.returncode == 0 and os.path.exists(backup_path):
        size = format_size(os.path.getsize(backup_path))
        show_success(f"Backup created: {backup_path} ({size})")
    else:
        show_error("Backup failed!")
    
    press_enter_to_continue()


def restore_database():
    """Restore database from backup."""
    clear_screen()
    show_header()
    show_panel("Restore Database", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    backup_path = text_input("Backup file path:")
    if not backup_path:
        return
    
    if not os.path.exists(backup_path):
        show_error("File not found.")
        press_enter_to_continue()
        return
    
    database = text_input("Target database name:")
    if not database:
        return
    
    databases = get_user_databases()
    db_exists = database in databases
    
    if db_exists:
        show_warning(f"Database '{database}' already exists!")
        if confirm_action("Drop and recreate database?"):
            from modules.database.mariadb.utils import run_mysql
            run_mysql(f"DROP DATABASE {database};")
        else:
            press_enter_to_continue()
            return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Create database
    from modules.database.mariadb.utils import run_mysql
    run_mysql(f"CREATE DATABASE {database};")
    
    is_gzip = backup_path.endswith('.gz')
    
    user, password = get_mysql_credentials()
    if user and password:
        auth = f"-u{user} -p{password}"
    else:
        auth = "-u root"
    
    if is_gzip:
        cmd = f"gunzip -c {backup_path} | mysql {auth} {database}"
    else:
        cmd = f"mysql {auth} {database} < {backup_path}"
    
    console.print()
    show_info(f"Restoring to {database}...")
    
    result = run_command(cmd, check=False, silent=False)
    
    if result.returncode == 0:
        show_success(f"Database '{database}' restored successfully!")
    else:
        show_error("Restore failed!")
        if result.stderr:
            console.print(f"[dim]{result.stderr}[/dim]")
    
    press_enter_to_continue()


def list_backups():
    """List existing backups."""
    clear_screen()
    show_header()
    show_panel("Backup List", title="MariaDB", style="cyan")
    
    if not os.path.exists(MARIA_BACKUP_DIR):
        show_info("No backups found.")
        console.print(f"[dim]Backup directory: {MARIA_BACKUP_DIR}[/dim]")
        press_enter_to_continue()
        return
    
    backups = []
    for f in os.listdir(MARIA_BACKUP_DIR):
        if f.endswith('.sql') or f.endswith('.sql.gz'):
            path = os.path.join(MARIA_BACKUP_DIR, f)
            size = os.path.getsize(path)
            mtime = os.path.getmtime(path)
            backups.append((f, size, mtime))
    
    if not backups:
        show_info("No backups found.")
        press_enter_to_continue()
        return
    
    backups.sort(key=lambda x: x[2], reverse=True)
    
    columns = [
        {"name": "Filename", "style": "cyan"},
        {"name": "Size", "justify": "right"},
        {"name": "Date"},
    ]
    
    rows = []
    import time
    for name, size, mtime in backups:
        date_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))
        rows.append([name, format_size(size), date_str])
    
    show_table(f"Total: {len(backups)} backup(s)", columns, rows, show_header=True)
    console.print()
    console.print(f"[dim]Location: {MARIA_BACKUP_DIR}[/dim]")
    
    press_enter_to_continue()


def scheduled_backups():
    """Setup scheduled backups via cron."""
    clear_screen()
    show_header()
    show_panel("Scheduled Backups", title="MariaDB", style="cyan")
    
    result = run_command("crontab -l 2>/dev/null | grep mysqldump", check=False, silent=True)
    
    if result.returncode == 0 and result.stdout.strip():
        console.print("[bold]Current Backup Schedule:[/bold]")
        console.print(result.stdout)
        console.print()
        
        if confirm_action("Remove scheduled backup?"):
            run_command(
                "crontab -l 2>/dev/null | grep -v mysqldump | crontab -",
                check=False, silent=True
            )
            show_success("Scheduled backup removed.")
            press_enter_to_continue()
            return
    
    if not confirm_action("Setup daily backup?"):
        press_enter_to_continue()
        return
    
    databases = get_user_databases()
    if databases:
        db_options = ["(All databases)"] + databases
        target = select_from_list("Backup Target", "What to backup:", db_options)
        if not target:
            return
    else:
        target = "(All databases)"
    
    retention = text_input("Keep backups for (days):", default="7")
    if not retention:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    os.makedirs(MARIA_BACKUP_DIR, exist_ok=True)
    
    user, password = get_mysql_credentials()
    if user and password:
        auth = f"-u{user} -p{password}"
    else:
        auth = "-u root"
    
    if target == "(All databases)":
        dump_cmd = f"mysqldump {auth} --all-databases"
        prefix = "all_databases"
    else:
        dump_cmd = f"mysqldump {auth} {target}"
        prefix = target
    
    script_content = f'''#!/bin/bash
# MariaDB backup script - managed by vexo
BACKUP_DIR="{MARIA_BACKUP_DIR}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/{prefix}_$TIMESTAMP.sql.gz"

# Create backup
{dump_cmd} | gzip > "$BACKUP_FILE"

# Remove old backups (older than {retention} days)
find "$BACKUP_DIR" -name "{prefix}_*.sql.gz" -mtime +{retention} -delete
'''
    
    script_path = "/etc/vexo/scripts/maria_backup.sh"
    os.makedirs(os.path.dirname(script_path), exist_ok=True)
    
    try:
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
    except Exception as e:
        show_error(f"Failed to create script: {e}")
        press_enter_to_continue()
        return
    
    cron_line = f"0 2 * * * {script_path}"
    run_command(
        f'(crontab -l 2>/dev/null | grep -v maria_backup; echo "{cron_line}") | crontab -',
        check=False, silent=True
    )
    
    show_success("Daily backup scheduled at 2:00 AM!")
    console.print(f"[dim]Script: {script_path}[/dim]")
    console.print(f"[dim]Retention: {retention} days[/dim]")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/database/mariadb/backup.py
git commit -m "feat(database): add MariaDB backup and restore"
```

---

## Task 3: Create MariaDB Core Module

**Files:**
- Create: `modules/database/mariadb/core.py`

**Step 1: Create core.py**

```python
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
```

**Step 2: Commit**

```bash
git add modules/database/mariadb/core.py
git commit -m "feat(database): add MariaDB core module"
```

---

## Task 4: Create MariaDB Users Module

**Files:**
- Create: `modules/database/mariadb/users.py`

**Step 1: Create users.py**

```python
"""MariaDB user management."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
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
    
    result = run_mysql(f"CREATE USER '{username}'@'{host}' IDENTIFIED BY '{password}';")
    
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
    
    # Get hosts for this user
    result = run_mysql(f"SELECT Host FROM mysql.user WHERE User = '{username}';")
    hosts = [h.strip() for h in result.stdout.strip().split('\n') if h.strip()]
    
    if len(hosts) > 1:
        host = select_from_list("Select Host", f"Delete {username}@:", hosts)
        if not host:
            return
    else:
        host = hosts[0] if hosts else "localhost"
    
    if not confirm_action(f"Delete user '{username}'@'{host}'?"):
        return
    
    result = run_mysql(f"DROP USER '{username}'@'{host}';")
    
    if result.returncode == 0:
        run_mysql("FLUSH PRIVILEGES;")
        show_success(f"User '{username}'@'{host}' deleted!")
    else:
        show_error("Failed to delete user.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/database/mariadb/users.py
git commit -m "feat(database): add MariaDB users module"
```

---

## Task 5: Create MariaDB Monitor Module

**Files:**
- Create: `modules/database/mariadb/monitor.py`

**Step 1: Create monitor.py**

```python
"""MariaDB monitoring functions."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, service_control
from modules.database.mariadb.utils import (
    is_mariadb_ready, run_mysql, get_databases, get_database_size,
    format_size, get_mariadb_version, get_mariadb_datadir,
)


def show_monitor_menu():
    """Display Monitoring submenu."""
    options = [
        ("stats", "1. Database Stats"),
        ("tables", "2. Table Sizes"),
        ("connections", "3. Active Connections"),
        ("slow", "4. Slow Query Log"),
        ("health", "5. Health Check"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "stats": database_stats,
        "tables": table_sizes,
        "connections": active_connections,
        "slow": slow_query_log,
        "health": health_check,
    }
    
    run_menu_loop("Monitoring", options, handlers)


def database_stats():
    """Show database statistics."""
    clear_screen()
    show_header()
    show_panel("Database Statistics", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    version = get_mariadb_version()
    datadir = get_mariadb_datadir()
    
    console.print(f"[bold]MariaDB Version:[/bold] {version}")
    console.print(f"[bold]Data Directory:[/bold] {datadir}")
    console.print()
    
    # Uptime
    result = run_mysql("SHOW GLOBAL STATUS LIKE 'Uptime';")
    if result.returncode == 0:
        uptime = result.stdout.split('\t')[1].strip() if '\t' in result.stdout else "?"
        hours = int(uptime) // 3600 if uptime.isdigit() else 0
        console.print(f"[bold]Uptime:[/bold] {hours} hours")
    
    # Connections
    result = run_mysql("SHOW GLOBAL STATUS LIKE 'Threads_connected';")
    if result.returncode == 0 and '\t' in result.stdout:
        connections = result.stdout.split('\t')[1].strip()
        console.print(f"[bold]Active Connections:[/bold] {connections}")
    
    result = run_mysql("SELECT @@max_connections;")
    if result.returncode == 0:
        console.print(f"[bold]Max Connections:[/bold] {result.stdout.strip()}")
    
    console.print()
    
    # Database sizes
    databases = get_databases()
    
    columns = [
        {"name": "Database", "style": "cyan"},
        {"name": "Size", "justify": "right"},
        {"name": "Tables", "justify": "right"},
    ]
    
    rows = []
    total_size = 0
    
    for db in databases:
        size = get_database_size(db)
        total_size += size
        
        result = run_mysql(
            f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '{db}';"
        )
        table_count = result.stdout.strip() if result.returncode == 0 else "?"
        
        rows.append([db, format_size(size), table_count])
    
    show_table(f"Total: {format_size(total_size)}", columns, rows, show_header=True)
    
    press_enter_to_continue()


def table_sizes():
    """Show table sizes for a database."""
    clear_screen()
    show_header()
    show_panel("Table Sizes", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    from modules.database.mariadb.utils import get_user_databases
    databases = get_user_databases()
    
    if not databases:
        show_info("No user databases found.")
        press_enter_to_continue()
        return
    
    database = select_from_list("Select Database", "Show tables for:", databases)
    if not database:
        return
    
    sql = f"""
    SELECT 
        table_name,
        ROUND((data_length + index_length) / 1024 / 1024, 2) as total_mb,
        ROUND(data_length / 1024 / 1024, 2) as data_mb,
        ROUND(index_length / 1024 / 1024, 2) as index_mb,
        table_rows
    FROM information_schema.tables 
    WHERE table_schema = '{database}'
    ORDER BY (data_length + index_length) DESC
    LIMIT 20;
    """
    
    result = run_mysql(sql)
    
    if result.returncode != 0 or not result.stdout.strip():
        show_info("No tables found.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Table", "style": "cyan"},
        {"name": "Total MB", "justify": "right"},
        {"name": "Data MB", "justify": "right"},
        {"name": "Index MB", "justify": "right"},
        {"name": "Rows", "justify": "right"},
    ]
    
    rows = []
    for line in result.stdout.strip().split('\n'):
        parts = line.split('\t')
        if len(parts) >= 5:
            rows.append(parts[:5])
    
    if rows:
        show_table(f"Top tables in {database}", columns, rows, show_header=True)
    else:
        show_info("No tables found.")
    
    press_enter_to_continue()


def active_connections():
    """Show active database connections."""
    clear_screen()
    show_header()
    show_panel("Active Connections", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    result = run_mysql("SHOW FULL PROCESSLIST;")
    
    if result.returncode != 0:
        show_error("Failed to get connections.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "ID", "style": "cyan"},
        {"name": "User"},
        {"name": "Host"},
        {"name": "DB"},
        {"name": "Time"},
        {"name": "State"},
    ]
    
    rows = []
    for line in result.stdout.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) >= 6:
            rows.append(parts[:6])
    
    if rows:
        show_table(f"{len(rows)} connection(s)", columns, rows, show_header=True)
        
        console.print()
        if confirm_action("Kill a connection?"):
            pid = text_input("Enter ID to kill:")
            if pid and pid.isdigit():
                result = run_mysql(f"KILL {pid};")
                if result.returncode == 0:
                    show_success(f"Connection {pid} terminated.")
                else:
                    show_error("Failed to terminate connection.")
    else:
        show_info("No active connections.")
    
    press_enter_to_continue()


def slow_query_log():
    """Configure and view slow query log."""
    clear_screen()
    show_header()
    show_panel("Slow Query Log", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    result = run_mysql("SELECT @@slow_query_log;")
    enabled = result.stdout.strip() == "1" if result.returncode == 0 else False
    
    result = run_mysql("SELECT @@long_query_time;")
    threshold = result.stdout.strip() if result.returncode == 0 else "10"
    
    console.print(f"[bold]Slow Query Log:[/bold] {'Enabled' if enabled else 'Disabled'}")
    console.print(f"[bold]Threshold:[/bold] {threshold} seconds")
    console.print()
    
    options = [
        "Enable (log queries > 2 seconds)",
        "Enable (log queries > 5 seconds)",
        "Disable slow query logging",
        "View recent slow queries",
    ]
    
    choice = select_from_list("Action", "What to do?", options)
    if not choice:
        return
    
    if "2 seconds" in choice:
        run_mysql("SET GLOBAL slow_query_log = 'ON';")
        run_mysql("SET GLOBAL long_query_time = 2;")
        show_success("Slow query log enabled (> 2s)")
    elif "5 seconds" in choice:
        run_mysql("SET GLOBAL slow_query_log = 'ON';")
        run_mysql("SET GLOBAL long_query_time = 5;")
        show_success("Slow query log enabled (> 5s)")
    elif "Disable" in choice:
        run_mysql("SET GLOBAL slow_query_log = 'OFF';")
        show_success("Slow query log disabled.")
    else:
        result = run_mysql("SELECT @@slow_query_log_file;")
        log_file = result.stdout.strip() if result.returncode == 0 else "/var/log/mysql/mariadb-slow.log"
        
        console.print()
        console.print("[bold]Recent Slow Queries:[/bold]")
        result = run_command(f"tail -50 {log_file} 2>/dev/null", check=False, silent=True)
        if result.stdout.strip():
            console.print(result.stdout[:2000])
        else:
            show_info("No slow queries found or log file not accessible.")
    
    press_enter_to_continue()


def health_check():
    """Run MariaDB health check."""
    clear_screen()
    show_header()
    show_panel("Health Check", title="MariaDB", style="cyan")
    
    checks = []
    recommendations = []
    
    # Check 1: Service running
    from utils.shell import is_service_running
    running = is_service_running("mariadb")
    checks.append(("Service Running", running, "Yes" if running else "No"))
    if not running:
        recommendations.append("Start MariaDB: systemctl start mariadb")
        _show_health_results(checks, recommendations)
        return
    
    # Check 2: Accepting connections
    result = run_mysql("SELECT 1;")
    accepting = result.returncode == 0
    checks.append(("Accepting Connections", accepting, "Yes" if accepting else "No"))
    
    # Check 3: Connection usage
    result = run_mysql("SHOW GLOBAL STATUS LIKE 'Threads_connected';")
    conn_count = int(result.stdout.split('\t')[1]) if result.returncode == 0 and '\t' in result.stdout else 0
    result = run_mysql("SELECT @@max_connections;")
    max_conn = int(result.stdout.strip()) if result.returncode == 0 else 151
    conn_pct = (conn_count / max_conn) * 100
    conn_ok = conn_pct < 80
    checks.append(("Connection Usage", conn_ok, f"{conn_count}/{max_conn} ({conn_pct:.0f}%)"))
    if not conn_ok:
        recommendations.append("Connection usage high - consider increasing max_connections")
    
    # Check 4: Disk space
    datadir = get_mariadb_datadir()
    if datadir:
        result = run_command(f"df -h {datadir} | tail -1", check=False, silent=True)
        if result.returncode == 0:
            parts = result.stdout.split()
            if len(parts) >= 5:
                usage = parts[4].replace('%', '')
                disk_ok = int(usage) < 85
                checks.append(("Disk Space", disk_ok, f"{parts[4]} used"))
                if not disk_ok:
                    recommendations.append("Disk space low - clean up or expand storage")
    
    # Check 5: InnoDB buffer pool
    result = run_mysql("SELECT @@innodb_buffer_pool_size / 1024 / 1024 as mb;")
    buffer_mb = int(float(result.stdout.strip())) if result.returncode == 0 else 0
    buffer_ok = buffer_mb >= 128
    checks.append(("InnoDB Buffer Pool", buffer_ok, f"{buffer_mb} MB"))
    if not buffer_ok:
        recommendations.append("InnoDB buffer pool is small - consider increasing")
    
    _show_health_results(checks, recommendations)


def _show_health_results(checks, recommendations):
    """Display health check results."""
    columns = [
        {"name": "Check", "style": "cyan"},
        {"name": "Status", "justify": "center"},
        {"name": "Details"},
    ]
    
    rows = []
    passed = 0
    
    for name, ok, details in checks:
        status = "[green]✓ PASS[/green]" if ok else "[red]✗ FAIL[/red]"
        if ok:
            passed += 1
        rows.append([name, status, details])
    
    show_table(f"Score: {passed}/{len(checks)}", columns, rows, show_header=True)
    
    if recommendations:
        console.print()
        console.print("[bold yellow]Recommendations:[/bold yellow]")
        for rec in recommendations:
            console.print(f"  • {rec}")
    else:
        console.print()
        console.print("[bold green]All checks passed![/bold green]")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/database/mariadb/monitor.py
git commit -m "feat(database): add MariaDB monitoring"
```

---

## Task 6: Create Remaining MariaDB Modules

Create `importexport.py`, `config.py`, and `security.py` following the same pattern as PostgreSQL modules but with MariaDB-specific commands.

**Files:**
- Create: `modules/database/mariadb/importexport.py`
- Create: `modules/database/mariadb/config.py`
- Create: `modules/database/mariadb/security.py`

*(Follow PostgreSQL pattern, replace psql with mysql, pg_dump with mysqldump)*

---

## Execution Handoff

Plan complete. Run all tasks sequentially to create the full MariaDB module.
