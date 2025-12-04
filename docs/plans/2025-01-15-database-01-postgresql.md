# PostgreSQL Enhancements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add comprehensive PostgreSQL management features including backup/restore, import/export, monitoring, configuration, and security management.

**Architecture:** Create `modules/database/postgresql/` folder structure with separate files for each feature group. Uses `psql`, `pg_dump`, `pg_restore` commands via sudo postgres user.

**Tech Stack:** Python, PostgreSQL, pg_dump/pg_restore, psql

---

## Task 1: Create Database Folder Structure

**Files:**
- Create: `modules/database/__init__.py`
- Create: `modules/database/postgresql/__init__.py`
- Create: `modules/database/postgresql/utils.py`
- Create: `modules/database/mariadb/__init__.py`
- Create: `modules/database/redis/__init__.py`

**Step 1: Create directory structure**

```bash
mkdir -p modules/database/postgresql
mkdir -p modules/database/mariadb
mkdir -p modules/database/redis
```

**Step 2: Create modules/database/postgresql/utils.py**

```python
"""Shared utilities for PostgreSQL module."""

import os

from utils.shell import run_command, is_installed, is_service_running

# Backup directory
PG_BACKUP_DIR = "/var/backups/postgresql"

# System databases
PG_SYSTEM_DBS = ["postgres", "template0", "template1"]

# System users
PG_SYSTEM_USERS = ["postgres"]


def is_postgresql_ready():
    """Check if PostgreSQL is installed and running."""
    return is_installed("postgresql") and is_service_running("postgresql")


def run_psql(sql, database="postgres", silent=True):
    """Run SQL command via psql as postgres user."""
    cmd = f'sudo -u postgres psql -d {database} -t -c "{sql}"'
    return run_command(cmd, check=False, silent=silent)


def run_psql_file(filepath, database="postgres"):
    """Run SQL file via psql."""
    cmd = f'sudo -u postgres psql -d {database} -f "{filepath}"'
    return run_command(cmd, check=False, silent=True)


def get_databases():
    """Get list of PostgreSQL databases."""
    result = run_psql("SELECT datname FROM pg_database WHERE datistemplate = false;")
    if result.returncode != 0:
        return []
    return [db.strip() for db in result.stdout.strip().split('\n') if db.strip()]


def get_user_databases():
    """Get non-system databases."""
    return [db for db in get_databases() if db not in PG_SYSTEM_DBS]


def get_users():
    """Get list of PostgreSQL users."""
    result = run_psql("SELECT usename FROM pg_catalog.pg_user;")
    if result.returncode != 0:
        return []
    return [u.strip() for u in result.stdout.strip().split('\n') if u.strip()]


def get_database_size(database):
    """Get database size in bytes."""
    result = run_psql(f"SELECT pg_database_size('{database}');")
    if result.returncode == 0 and result.stdout.strip():
        try:
            return int(result.stdout.strip())
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


def get_pg_version():
    """Get PostgreSQL version."""
    result = run_psql("SHOW server_version;")
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def get_pg_config_file():
    """Get path to postgresql.conf."""
    result = run_psql("SHOW config_file;")
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def get_pg_hba_file():
    """Get path to pg_hba.conf."""
    result = run_psql("SHOW hba_file;")
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def get_pg_data_dir():
    """Get PostgreSQL data directory."""
    result = run_psql("SHOW data_directory;")
    if result.returncode == 0:
        return result.stdout.strip()
    return None
```

**Step 3: Create modules/database/postgresql/__init__.py**

```python
"""PostgreSQL management module."""

from ui.menu import run_menu_loop
from utils.shell import is_installed, is_service_running


def show_menu():
    """Display PostgreSQL Management submenu."""
    def get_status():
        if not is_installed("postgresql"):
            return "PostgreSQL: [yellow]Not installed[/yellow]"
        if is_service_running("postgresql"):
            return "PostgreSQL: [green]Running[/green]"
        return "PostgreSQL: [red]Stopped[/red]"
    
    def get_options():
        options = []
        if is_installed("postgresql"):
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
            options.append(("install", "1. Install PostgreSQL"))
        options.append(("back", "← Back"))
        return options
    
    def get_handlers():
        from modules.database.postgresql.core import (
            list_databases, create_database_interactive,
            delete_database_interactive, install_postgresql,
        )
        from modules.database.postgresql.users import show_users_menu
        from modules.database.postgresql.backup import show_backup_menu
        from modules.database.postgresql.importexport import show_import_menu
        from modules.database.postgresql.monitor import show_monitor_menu
        from modules.database.postgresql.config import show_config_menu
        from modules.database.postgresql.security import show_security_menu
        
        return {
            "install": install_postgresql,
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
    
    run_menu_loop("PostgreSQL Management", get_options, get_handlers(), get_status)
```

**Step 4: Create modules/database/__init__.py**

```python
"""Database management module for vexo-cli."""

from ui.menu import run_menu_loop
from utils.shell import is_installed


def show_menu():
    """Display Database Management submenu."""
    def get_status():
        pg = "[green]✓[/green]" if is_installed("postgresql") else "[dim]○[/dim]"
        maria = "[green]✓[/green]" if is_installed("mariadb-server") else "[dim]○[/dim]"
        redis = "[green]✓[/green]" if is_installed("redis-server") else "[dim]○[/dim]"
        return f"PG:{pg} Maria:{maria} Redis:{redis}"
    
    options = [
        ("pgsql", "1. PostgreSQL Management"),
        ("mariadb", "2. MariaDB Management"),
        ("redis", "3. Redis Management"),
        ("back", "← Back to Main Menu"),
    ]
    
    def get_handlers():
        from modules.database.postgresql import show_menu as pg_menu
        from modules.database.mariadb import show_menu as maria_menu
        from modules.database.redis import show_menu as redis_menu
        
        return {
            "pgsql": pg_menu,
            "mariadb": maria_menu,
            "redis": redis_menu,
        }
    
    run_menu_loop("Database Management", options, get_handlers(), get_status)
```

**Step 5: Commit**

```bash
git add modules/database/
git commit -m "refactor(database): create folder structure"
```

---

## Task 2: Create PostgreSQL Backup Module

**Files:**
- Create: `modules/database/postgresql/backup.py`

**Step 1: Create backup.py**

```python
"""PostgreSQL backup and restore functions."""

import os
from datetime import datetime

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, run_command_realtime, require_root
from modules.database.postgresql.utils import (
    is_postgresql_ready, get_user_databases, get_database_size,
    format_size, PG_BACKUP_DIR,
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
    show_panel("Backup Database", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
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
    
    # Backup options
    compress = confirm_action("Compress backup (gzip)?")
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = ".sql.gz" if compress else ".sql"
    default_path = os.path.join(PG_BACKUP_DIR, f"{database}_{timestamp}{ext}")
    
    backup_path = text_input("Backup path:", default=default_path)
    if not backup_path:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Create backup directory
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    
    # Build command
    if compress:
        cmd = f"sudo -u postgres pg_dump {database} | gzip > {backup_path}"
    else:
        cmd = f"sudo -u postgres pg_dump {database} > {backup_path}"
    
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
    show_panel("Backup All Databases", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    compress = confirm_action("Compress backup (gzip)?")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = ".sql.gz" if compress else ".sql"
    default_path = os.path.join(PG_BACKUP_DIR, f"all_databases_{timestamp}{ext}")
    
    backup_path = text_input("Backup path:", default=default_path)
    if not backup_path:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    
    if compress:
        cmd = f"sudo -u postgres pg_dumpall | gzip > {backup_path}"
    else:
        cmd = f"sudo -u postgres pg_dumpall > {backup_path}"
    
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
    show_panel("Restore Database", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    # Get backup file
    backup_path = text_input("Backup file path:")
    if not backup_path:
        return
    
    if not os.path.exists(backup_path):
        show_error("File not found.")
        press_enter_to_continue()
        return
    
    # Target database
    database = text_input("Target database name:")
    if not database:
        return
    
    # Check if database exists
    databases = get_user_databases()
    db_exists = database in databases
    
    if db_exists:
        show_warning(f"Database '{database}' already exists!")
        if confirm_action("Drop and recreate database?"):
            run_command(
                f'sudo -u postgres psql -c "DROP DATABASE {database};"',
                check=False, silent=True
            )
        else:
            press_enter_to_continue()
            return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Create database
    run_command(
        f'sudo -u postgres psql -c "CREATE DATABASE {database};"',
        check=False, silent=True
    )
    
    # Detect compression
    is_gzip = backup_path.endswith('.gz')
    
    if is_gzip:
        cmd = f"gunzip -c {backup_path} | sudo -u postgres psql {database}"
    else:
        cmd = f"sudo -u postgres psql {database} < {backup_path}"
    
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
    show_panel("Backup List", title="PostgreSQL", style="cyan")
    
    if not os.path.exists(PG_BACKUP_DIR):
        show_info("No backups found.")
        console.print(f"[dim]Backup directory: {PG_BACKUP_DIR}[/dim]")
        press_enter_to_continue()
        return
    
    backups = []
    for f in os.listdir(PG_BACKUP_DIR):
        if f.endswith('.sql') or f.endswith('.sql.gz'):
            path = os.path.join(PG_BACKUP_DIR, f)
            size = os.path.getsize(path)
            mtime = os.path.getmtime(path)
            backups.append((f, size, mtime))
    
    if not backups:
        show_info("No backups found.")
        press_enter_to_continue()
        return
    
    # Sort by date descending
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
    console.print(f"[dim]Location: {PG_BACKUP_DIR}[/dim]")
    
    press_enter_to_continue()


def scheduled_backups():
    """Setup scheduled backups via cron."""
    clear_screen()
    show_header()
    show_panel("Scheduled Backups", title="PostgreSQL", style="cyan")
    
    # Check existing cron
    result = run_command("crontab -l 2>/dev/null | grep pg_dump", check=False, silent=True)
    
    if result.returncode == 0 and result.stdout.strip():
        console.print("[bold]Current Backup Schedule:[/bold]")
        console.print(result.stdout)
        console.print()
        
        if confirm_action("Remove scheduled backup?"):
            run_command(
                "crontab -l 2>/dev/null | grep -v pg_dump | crontab -",
                check=False, silent=True
            )
            show_success("Scheduled backup removed.")
            press_enter_to_continue()
            return
    
    if not confirm_action("Setup daily backup?"):
        press_enter_to_continue()
        return
    
    # Backup settings
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
    
    # Create backup script
    os.makedirs(PG_BACKUP_DIR, exist_ok=True)
    
    if target == "(All databases)":
        dump_cmd = "pg_dumpall"
        prefix = "all_databases"
    else:
        dump_cmd = f"pg_dump {target}"
        prefix = target
    
    script_content = f'''#!/bin/bash
# PostgreSQL backup script - managed by vexo-cli
BACKUP_DIR="{PG_BACKUP_DIR}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/{prefix}_$TIMESTAMP.sql.gz"

# Create backup
sudo -u postgres {dump_cmd} | gzip > "$BACKUP_FILE"

# Remove old backups (older than {retention} days)
find "$BACKUP_DIR" -name "{prefix}_*.sql.gz" -mtime +{retention} -delete
'''
    
    script_path = "/etc/vexo/scripts/pg_backup.sh"
    os.makedirs(os.path.dirname(script_path), exist_ok=True)
    
    try:
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
    except Exception as e:
        show_error(f"Failed to create script: {e}")
        press_enter_to_continue()
        return
    
    # Add to cron (daily at 2 AM)
    cron_line = f"0 2 * * * {script_path}"
    run_command(
        f'(crontab -l 2>/dev/null | grep -v pg_backup; echo "{cron_line}") | crontab -',
        check=False, silent=True
    )
    
    show_success("Daily backup scheduled at 2:00 AM!")
    console.print(f"[dim]Script: {script_path}[/dim]")
    console.print(f"[dim]Retention: {retention} days[/dim]")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/database/postgresql/backup.py
git commit -m "feat(database): add PostgreSQL backup and restore"
```

---

## Task 3: Create PostgreSQL Import/Export Module

**Files:**
- Create: `modules/database/postgresql/importexport.py`

**Step 1: Create importexport.py**

```python
"""PostgreSQL import/export functions."""

import os

from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, run_command_realtime, require_root
from modules.database.postgresql.utils import (
    is_postgresql_ready, get_user_databases, run_psql, format_size,
)


def show_import_menu():
    """Display Import/Export submenu."""
    options = [
        ("import", "1. Import SQL File"),
        ("export", "2. Export Database"),
        ("export_table", "3. Export Table"),
        ("clone", "4. Clone Database"),
        ("migrate", "5. Migration Helper"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "import": import_sql_file,
        "export": export_database,
        "export_table": export_table,
        "clone": clone_database,
        "migrate": migration_helper,
    }
    
    run_menu_loop("Import/Export", options, handlers)


def import_sql_file():
    """Import SQL file into database."""
    clear_screen()
    show_header()
    show_panel("Import SQL File", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    sql_file = text_input("SQL file path:")
    if not sql_file:
        return
    
    if not os.path.exists(sql_file):
        show_error("File not found.")
        press_enter_to_continue()
        return
    
    # Detect file type
    is_gzip = sql_file.endswith('.gz')
    is_zip = sql_file.endswith('.zip')
    
    # Select target database
    databases = get_user_databases()
    db_options = ["(Create new database)"] + databases
    
    target = select_from_list("Target Database", "Import to:", db_options)
    if not target:
        return
    
    if target == "(Create new database)":
        db_name = text_input("New database name:")
        if not db_name:
            return
        
        # Create database
        result = run_psql(f"CREATE DATABASE {db_name};")
        if result.returncode != 0:
            show_error(f"Failed to create database: {result.stderr}")
            press_enter_to_continue()
            return
        target = db_name
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print()
    show_info(f"Importing to {target}...")
    
    # Build command based on file type
    if is_gzip:
        cmd = f"gunzip -c {sql_file} | sudo -u postgres psql {target}"
    elif is_zip:
        # Extract and import
        import tempfile
        temp_dir = tempfile.mkdtemp()
        run_command(f"unzip -o {sql_file} -d {temp_dir}", check=False, silent=True)
        sql_files = [f for f in os.listdir(temp_dir) if f.endswith('.sql')]
        if sql_files:
            extracted = os.path.join(temp_dir, sql_files[0])
            cmd = f"sudo -u postgres psql {target} < {extracted}"
        else:
            show_error("No SQL file found in archive.")
            press_enter_to_continue()
            return
    else:
        cmd = f"sudo -u postgres psql {target} < {sql_file}"
    
    result = run_command(cmd, check=False, silent=False)
    
    if result.returncode == 0:
        show_success(f"Import completed to '{target}'!")
    else:
        show_error("Import failed!")
    
    press_enter_to_continue()


def export_database():
    """Export database with options."""
    clear_screen()
    show_header()
    show_panel("Export Database", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    databases = get_user_databases()
    if not databases:
        show_info("No user databases found.")
        press_enter_to_continue()
        return
    
    database = select_from_list("Select Database", "Export:", databases)
    if not database:
        return
    
    # Export options
    export_types = [
        "Structure + Data (full)",
        "Structure only (schema)",
        "Data only",
    ]
    
    export_type = select_from_list("Export Type", "What to export:", export_types)
    if not export_type:
        return
    
    compress = confirm_action("Compress output (gzip)?")
    
    # Build filename
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = ".sql.gz" if compress else ".sql"
    default_path = f"/tmp/{database}_{timestamp}{ext}"
    
    output_path = text_input("Output path:", default=default_path)
    if not output_path:
        return
    
    # Build pg_dump options
    options = ""
    if "Structure only" in export_type:
        options = "--schema-only"
    elif "Data only" in export_type:
        options = "--data-only"
    
    if compress:
        cmd = f"sudo -u postgres pg_dump {options} {database} | gzip > {output_path}"
    else:
        cmd = f"sudo -u postgres pg_dump {options} {database} > {output_path}"
    
    console.print()
    show_info("Exporting...")
    
    result = run_command(cmd, check=False, silent=True)
    
    if result.returncode == 0 and os.path.exists(output_path):
        size = format_size(os.path.getsize(output_path))
        show_success(f"Exported to: {output_path} ({size})")
    else:
        show_error("Export failed!")
    
    press_enter_to_continue()


def export_table():
    """Export a single table."""
    clear_screen()
    show_header()
    show_panel("Export Table", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    databases = get_user_databases()
    if not databases:
        show_info("No user databases found.")
        press_enter_to_continue()
        return
    
    database = select_from_list("Select Database", "From:", databases)
    if not database:
        return
    
    # Get tables
    result = run_psql(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public';",
        database=database
    )
    
    if result.returncode != 0 or not result.stdout.strip():
        show_info("No tables found.")
        press_enter_to_continue()
        return
    
    tables = [t.strip() for t in result.stdout.strip().split('\n') if t.strip()]
    
    table = select_from_list("Select Table", "Export:", tables)
    if not table:
        return
    
    # Format
    formats = ["SQL", "CSV"]
    fmt = select_from_list("Format", "Export as:", formats)
    if not fmt:
        return
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = ".csv" if fmt == "CSV" else ".sql"
    default_path = f"/tmp/{database}_{table}_{timestamp}{ext}"
    
    output_path = text_input("Output path:", default=default_path)
    if not output_path:
        return
    
    if fmt == "CSV":
        cmd = f"sudo -u postgres psql -d {database} -c \"COPY {table} TO STDOUT WITH CSV HEADER\" > {output_path}"
    else:
        cmd = f"sudo -u postgres pg_dump -t {table} {database} > {output_path}"
    
    result = run_command(cmd, check=False, silent=True)
    
    if result.returncode == 0:
        size = format_size(os.path.getsize(output_path))
        show_success(f"Table exported: {output_path} ({size})")
    else:
        show_error("Export failed!")
    
    press_enter_to_continue()


def clone_database():
    """Clone database to new name."""
    clear_screen()
    show_header()
    show_panel("Clone Database", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    databases = get_user_databases()
    if not databases:
        show_info("No user databases found.")
        press_enter_to_continue()
        return
    
    source = select_from_list("Source Database", "Clone from:", databases)
    if not source:
        return
    
    new_name = text_input("New database name:")
    if not new_name:
        return
    
    if new_name in databases:
        show_error(f"Database '{new_name}' already exists.")
        press_enter_to_continue()
        return
    
    console.print()
    show_info(f"Cloning {source} to {new_name}...")
    
    # Use CREATE DATABASE ... WITH TEMPLATE
    result = run_psql(f"CREATE DATABASE {new_name} WITH TEMPLATE {source};")
    
    if result.returncode == 0:
        show_success(f"Database cloned: {source} → {new_name}")
    else:
        show_error("Clone failed!")
        console.print(f"[dim]{result.stderr}[/dim]")
    
    press_enter_to_continue()


def migration_helper():
    """Generate migration commands for remote transfer."""
    clear_screen()
    show_header()
    show_panel("Migration Helper", title="PostgreSQL", style="cyan")
    
    databases = get_user_databases()
    if not databases:
        show_info("No user databases found.")
        press_enter_to_continue()
        return
    
    database = select_from_list("Select Database", "Migrate:", databases)
    if not database:
        return
    
    remote_host = text_input("Remote host (e.g., user@server.com):")
    if not remote_host:
        return
    
    console.print()
    console.print("[bold]Migration Commands:[/bold]")
    console.print()
    console.print("[cyan]Step 1: Export on this server[/cyan]")
    console.print(f"  sudo -u postgres pg_dump {database} | gzip > /tmp/{database}.sql.gz")
    console.print()
    console.print("[cyan]Step 2: Transfer to remote[/cyan]")
    console.print(f"  scp /tmp/{database}.sql.gz {remote_host}:/tmp/")
    console.print()
    console.print("[cyan]Step 3: Import on remote (run on remote server)[/cyan]")
    console.print(f"  sudo -u postgres createdb {database}")
    console.print(f"  gunzip -c /tmp/{database}.sql.gz | sudo -u postgres psql {database}")
    console.print()
    console.print("[cyan]One-liner (pipe over SSH):[/cyan]")
    console.print(f"  sudo -u postgres pg_dump {database} | ssh {remote_host} 'sudo -u postgres psql {database}'")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/database/postgresql/importexport.py
git commit -m "feat(database): add PostgreSQL import/export"
```

---

## Task 4: Create PostgreSQL Monitor Module

**Files:**
- Create: `modules/database/postgresql/monitor.py`

**Step 1: Create monitor.py**

```python
"""PostgreSQL monitoring functions."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, service_control
from modules.database.postgresql.utils import (
    is_postgresql_ready, run_psql, get_databases, get_database_size,
    format_size, get_pg_version, get_pg_data_dir,
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
    show_panel("Database Statistics", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    # Server info
    version = get_pg_version()
    data_dir = get_pg_data_dir()
    
    console.print(f"[bold]PostgreSQL Version:[/bold] {version}")
    console.print(f"[bold]Data Directory:[/bold] {data_dir}")
    console.print()
    
    # Get uptime
    result = run_psql("SELECT pg_postmaster_start_time();")
    if result.returncode == 0:
        console.print(f"[bold]Started:[/bold] {result.stdout.strip()}")
    
    # Connection stats
    result = run_psql("SELECT count(*) FROM pg_stat_activity;")
    if result.returncode == 0:
        console.print(f"[bold]Active Connections:[/bold] {result.stdout.strip()}")
    
    result = run_psql("SHOW max_connections;")
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
        
        # Get table count
        result = run_psql(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';",
            database=db
        )
        table_count = result.stdout.strip() if result.returncode == 0 else "?"
        
        rows.append([db, format_size(size), table_count])
    
    show_table(f"Total: {format_size(total_size)}", columns, rows, show_header=True)
    
    press_enter_to_continue()


def table_sizes():
    """Show table sizes for a database."""
    clear_screen()
    show_header()
    show_panel("Table Sizes", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    from modules.database.postgresql.utils import get_user_databases
    databases = get_user_databases()
    
    if not databases:
        show_info("No user databases found.")
        press_enter_to_continue()
        return
    
    database = select_from_list("Select Database", "Show tables for:", databases)
    if not database:
        return
    
    # Get table sizes
    sql = """
    SELECT 
        tablename,
        pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) as total_size,
        pg_size_pretty(pg_relation_size(schemaname || '.' || tablename)) as data_size,
        pg_size_pretty(pg_indexes_size(schemaname || '.' || tablename)) as index_size
    FROM pg_tables 
    WHERE schemaname = 'public'
    ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC
    LIMIT 20;
    """
    
    result = run_psql(sql, database=database)
    
    if result.returncode != 0 or not result.stdout.strip():
        show_info("No tables found.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Table", "style": "cyan"},
        {"name": "Total Size", "justify": "right"},
        {"name": "Data Size", "justify": "right"},
        {"name": "Index Size", "justify": "right"},
    ]
    
    rows = []
    for line in result.stdout.strip().split('\n'):
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 4:
            rows.append(parts[:4])
    
    if rows:
        show_table(f"Top tables in {database}", columns, rows, show_header=True)
    else:
        show_info("No tables found.")
    
    press_enter_to_continue()


def active_connections():
    """Show active database connections."""
    clear_screen()
    show_header()
    show_panel("Active Connections", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    sql = """
    SELECT 
        pid,
        usename,
        datname,
        client_addr,
        state,
        query_start::text,
        LEFT(query, 50) as query
    FROM pg_stat_activity
    WHERE state IS NOT NULL
    ORDER BY query_start DESC
    LIMIT 20;
    """
    
    result = run_psql(sql)
    
    if result.returncode != 0:
        show_error("Failed to get connections.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "PID", "style": "cyan"},
        {"name": "User"},
        {"name": "Database"},
        {"name": "Client"},
        {"name": "State"},
        {"name": "Query"},
    ]
    
    rows = []
    for line in result.stdout.strip().split('\n'):
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 6:
            # Color state
            state = parts[4]
            if state == "active":
                state = "[green]active[/green]"
            elif state == "idle":
                state = "[dim]idle[/dim]"
            parts[4] = state
            rows.append(parts[:6])
    
    if rows:
        show_table(f"{len(rows)} connection(s)", columns, rows, show_header=True)
        
        console.print()
        if confirm_action("Kill a connection?"):
            pid = text_input("Enter PID to kill:")
            if pid and pid.isdigit():
                result = run_psql(f"SELECT pg_terminate_backend({pid});")
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
    show_panel("Slow Query Log", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    # Check current setting
    result = run_psql("SHOW log_min_duration_statement;")
    current = result.stdout.strip() if result.returncode == 0 else "-1"
    
    console.print(f"[bold]Current slow query threshold:[/bold] {current}")
    console.print()
    
    if current == "-1":
        console.print("[yellow]Slow query logging is disabled.[/yellow]")
    else:
        console.print(f"[green]Logging queries slower than {current}[/green]")
    
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
        run_psql("ALTER SYSTEM SET log_min_duration_statement = '2s';")
        run_psql("SELECT pg_reload_conf();")
        show_success("Slow query log enabled (> 2s)")
    elif "5 seconds" in choice:
        run_psql("ALTER SYSTEM SET log_min_duration_statement = '5s';")
        run_psql("SELECT pg_reload_conf();")
        show_success("Slow query log enabled (> 5s)")
    elif "Disable" in choice:
        run_psql("ALTER SYSTEM SET log_min_duration_statement = '-1';")
        run_psql("SELECT pg_reload_conf();")
        show_success("Slow query log disabled.")
    else:
        # View logs
        console.print()
        console.print("[bold]Recent PostgreSQL log:[/bold]")
        result = run_command(
            "tail -50 /var/log/postgresql/*.log 2>/dev/null | grep -i duration",
            check=False, silent=True
        )
        if result.stdout.strip():
            console.print(result.stdout)
        else:
            show_info("No slow queries found in recent logs.")
    
    press_enter_to_continue()


def health_check():
    """Run PostgreSQL health check."""
    clear_screen()
    show_header()
    show_panel("Health Check", title="PostgreSQL", style="cyan")
    
    checks = []
    recommendations = []
    
    # Check 1: Service running
    from utils.shell import is_service_running
    running = is_service_running("postgresql")
    checks.append(("Service Running", running, "Yes" if running else "No"))
    if not running:
        recommendations.append("Start PostgreSQL: systemctl start postgresql")
        # Can't continue without service
        _show_health_results(checks, recommendations)
        return
    
    # Check 2: Accepting connections
    result = run_psql("SELECT 1;")
    accepting = result.returncode == 0
    checks.append(("Accepting Connections", accepting, "Yes" if accepting else "No"))
    
    # Check 3: Connection count
    result = run_psql("SELECT count(*) FROM pg_stat_activity;")
    conn_count = int(result.stdout.strip()) if result.returncode == 0 else 0
    result = run_psql("SHOW max_connections;")
    max_conn = int(result.stdout.strip()) if result.returncode == 0 else 100
    conn_pct = (conn_count / max_conn) * 100
    conn_ok = conn_pct < 80
    checks.append(("Connection Usage", conn_ok, f"{conn_count}/{max_conn} ({conn_pct:.0f}%)"))
    if not conn_ok:
        recommendations.append("Connection usage high - consider increasing max_connections")
    
    # Check 4: Disk space
    data_dir = get_pg_data_dir()
    if data_dir:
        result = run_command(f"df -h {data_dir} | tail -1", check=False, silent=True)
        if result.returncode == 0:
            parts = result.stdout.split()
            if len(parts) >= 5:
                usage = parts[4].replace('%', '')
                disk_ok = int(usage) < 85
                checks.append(("Disk Space", disk_ok, f"{parts[4]} used"))
                if not disk_ok:
                    recommendations.append("Disk space low - clean up or expand storage")
    
    # Check 5: Long-running queries
    result = run_psql(
        "SELECT count(*) FROM pg_stat_activity WHERE state = 'active' AND now() - query_start > interval '5 minutes';"
    )
    long_queries = int(result.stdout.strip()) if result.returncode == 0 else 0
    checks.append(("Long Queries (>5min)", long_queries == 0, str(long_queries)))
    if long_queries > 0:
        recommendations.append(f"{long_queries} query running > 5 minutes - check for locks")
    
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
git add modules/database/postgresql/monitor.py
git commit -m "feat(database): add PostgreSQL monitoring"
```

---

## Task 5: Create PostgreSQL Config Module

**Files:**
- Create: `modules/database/postgresql/config.py`

*[Content continues with configuration and security modules...]*

**Step 1: Create config.py**

```python
"""PostgreSQL configuration management."""

import os
import re

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, service_control, require_root
from modules.database.postgresql.utils import (
    is_postgresql_ready, run_psql, get_pg_config_file, format_size,
)


def show_config_menu():
    """Display Configuration submenu."""
    options = [
        ("view", "1. View Current Config"),
        ("quick", "2. Quick Settings"),
        ("memory", "3. Memory Tuning"),
        ("logs", "4. Log Configuration"),
        ("file", "5. View Config File"),
        ("restart", "6. Restart Service"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "view": view_current_config,
        "quick": quick_settings,
        "memory": memory_tuning,
        "logs": log_configuration,
        "file": view_config_file,
        "restart": restart_service,
    }
    
    run_menu_loop("Configuration", options, handlers)


def view_current_config():
    """View current PostgreSQL configuration."""
    clear_screen()
    show_header()
    show_panel("Current Configuration", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    settings = [
        "max_connections",
        "shared_buffers",
        "effective_cache_size",
        "work_mem",
        "maintenance_work_mem",
        "checkpoint_completion_target",
        "wal_buffers",
        "default_statistics_target",
        "random_page_cost",
        "effective_io_concurrency",
        "log_min_duration_statement",
        "log_destination",
    ]
    
    columns = [
        {"name": "Setting", "style": "cyan"},
        {"name": "Value"},
    ]
    
    rows = []
    for setting in settings:
        result = run_psql(f"SHOW {setting};")
        value = result.stdout.strip() if result.returncode == 0 else "N/A"
        rows.append([setting, value])
    
    show_table("", columns, rows, show_header=True)
    press_enter_to_continue()


def quick_settings():
    """Edit common PostgreSQL settings."""
    clear_screen()
    show_header()
    show_panel("Quick Settings", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    settings = [
        ("max_connections", "Maximum concurrent connections"),
        ("shared_buffers", "Shared memory buffers"),
        ("work_mem", "Memory for query operations"),
        ("maintenance_work_mem", "Memory for maintenance operations"),
    ]
    
    setting_options = [f"{s[0]} ({s[1]})" for s in settings]
    
    choice = select_from_list("Select Setting", "Configure:", setting_options)
    if not choice:
        return
    
    setting_name = choice.split(" (")[0]
    
    # Get current value
    result = run_psql(f"SHOW {setting_name};")
    current = result.stdout.strip() if result.returncode == 0 else ""
    
    console.print(f"[dim]Current: {current}[/dim]")
    new_value = text_input(f"New value for {setting_name}:")
    if not new_value:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Use ALTER SYSTEM for persistent change
    result = run_psql(f"ALTER SYSTEM SET {setting_name} = '{new_value}';")
    
    if result.returncode == 0:
        show_success(f"Set {setting_name} = {new_value}")
        console.print()
        if confirm_action("Reload PostgreSQL to apply changes?"):
            run_psql("SELECT pg_reload_conf();")
            show_success("Configuration reloaded!")
    else:
        show_error("Failed to update setting.")
        console.print(f"[dim]{result.stderr}[/dim]")
    
    press_enter_to_continue()


def memory_tuning():
    """Memory tuning wizard."""
    clear_screen()
    show_header()
    show_panel("Memory Tuning", title="PostgreSQL", style="cyan")
    
    # Get server memory
    result = run_command("free -b | grep Mem | awk '{print $2}'", check=False, silent=True)
    total_ram = int(result.stdout.strip()) if result.returncode == 0 else 0
    
    if total_ram == 0:
        show_error("Could not detect server memory.")
        press_enter_to_continue()
        return
    
    total_ram_gb = total_ram / (1024 ** 3)
    console.print(f"[bold]Detected RAM:[/bold] {total_ram_gb:.1f} GB")
    console.print()
    
    # Calculate recommendations
    # shared_buffers: 25% of RAM
    shared_buffers = int(total_ram * 0.25)
    # effective_cache_size: 75% of RAM
    effective_cache_size = int(total_ram * 0.75)
    # work_mem: RAM / (max_connections * 4)
    work_mem = int(total_ram / (100 * 4))
    # maintenance_work_mem: 5% of RAM up to 2GB
    maintenance_work_mem = min(int(total_ram * 0.05), 2 * 1024 ** 3)
    
    console.print("[bold]Recommended Settings:[/bold]")
    console.print()
    console.print(f"  shared_buffers = {format_size(shared_buffers)}")
    console.print(f"  effective_cache_size = {format_size(effective_cache_size)}")
    console.print(f"  work_mem = {format_size(work_mem)}")
    console.print(f"  maintenance_work_mem = {format_size(maintenance_work_mem)}")
    console.print()
    
    if not confirm_action("Apply these settings?"):
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Apply settings
    settings = {
        "shared_buffers": f"{shared_buffers // (1024 ** 2)}MB",
        "effective_cache_size": f"{effective_cache_size // (1024 ** 2)}MB",
        "work_mem": f"{work_mem // (1024 ** 2)}MB",
        "maintenance_work_mem": f"{maintenance_work_mem // (1024 ** 2)}MB",
    }
    
    for key, value in settings.items():
        run_psql(f"ALTER SYSTEM SET {key} = '{value}';")
    
    show_success("Settings applied!")
    console.print()
    show_warning("PostgreSQL restart required to apply shared_buffers change.")
    
    if confirm_action("Restart PostgreSQL now?"):
        service_control("postgresql", "restart")
        show_success("PostgreSQL restarted!")
    
    press_enter_to_continue()


def log_configuration():
    """Configure logging settings."""
    clear_screen()
    show_header()
    show_panel("Log Configuration", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    # Show current log settings
    log_settings = [
        "log_destination",
        "logging_collector",
        "log_directory",
        "log_filename",
        "log_min_duration_statement",
        "log_statement",
    ]
    
    console.print("[bold]Current Log Settings:[/bold]")
    console.print()
    for setting in log_settings:
        result = run_psql(f"SHOW {setting};")
        value = result.stdout.strip() if result.returncode == 0 else "N/A"
        console.print(f"  {setting} = {value}")
    console.print()
    
    options = [
        "Enable statement logging (all)",
        "Enable DDL only logging",
        "Disable statement logging",
        "Set log rotation",
    ]
    
    choice = select_from_list("Action", "Configure:", options)
    if not choice:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if "all" in choice:
        run_psql("ALTER SYSTEM SET log_statement = 'all';")
        show_success("Logging all statements.")
    elif "DDL" in choice:
        run_psql("ALTER SYSTEM SET log_statement = 'ddl';")
        show_success("Logging DDL statements only.")
    elif "Disable" in choice:
        run_psql("ALTER SYSTEM SET log_statement = 'none';")
        show_success("Statement logging disabled.")
    elif "rotation" in choice:
        run_psql("ALTER SYSTEM SET log_rotation_age = '1d';")
        run_psql("ALTER SYSTEM SET log_rotation_size = '100MB';")
        show_success("Log rotation configured (daily or 100MB).")
    
    run_psql("SELECT pg_reload_conf();")
    console.print("[dim]Configuration reloaded.[/dim]")
    
    press_enter_to_continue()


def view_config_file():
    """View raw PostgreSQL config file."""
    clear_screen()
    show_header()
    show_panel("Config File", title="PostgreSQL", style="cyan")
    
    config_file = get_pg_config_file()
    if not config_file:
        show_error("Could not find config file.")
        press_enter_to_continue()
        return
    
    console.print(f"[bold]Config File:[/bold] {config_file}")
    console.print()
    
    if not os.path.exists(config_file):
        show_error("Config file not found.")
        press_enter_to_continue()
        return
    
    # Show non-comment lines
    result = run_command(f"grep -v '^#' {config_file} | grep -v '^$' | head -50", check=False, silent=True)
    
    if result.returncode == 0:
        console.print(result.stdout)
    
    press_enter_to_continue()


def restart_service():
    """Restart PostgreSQL service."""
    clear_screen()
    show_header()
    show_panel("Restart Service", title="PostgreSQL", style="cyan")
    
    show_warning("This will briefly disconnect all clients!")
    console.print()
    
    options = ["Reload (graceful, limited changes)", "Restart (full restart)"]
    choice = select_from_list("Action", "Select:", options)
    if not choice:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if "Reload" in choice:
        run_psql("SELECT pg_reload_conf();")
        show_success("PostgreSQL configuration reloaded!")
    else:
        service_control("postgresql", "restart")
        show_success("PostgreSQL restarted!")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/database/postgresql/config.py
git commit -m "feat(database): add PostgreSQL configuration"
```

---

## Task 6: Create PostgreSQL Security Module

**Files:**
- Create: `modules/database/postgresql/security.py`

**Step 1: Create security.py**

```python
"""PostgreSQL security management."""

import os
import re

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, service_control, require_root
from modules.database.postgresql.utils import (
    is_postgresql_ready, run_psql, get_pg_hba_file, get_users,
    PG_SYSTEM_USERS,
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
            # Convert t/f to Yes/No
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
    
    from modules.database.postgresql.utils import get_user_databases
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
    
    # Validate password strength
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
    
    # Check current listen_addresses
    result = run_psql("SHOW listen_addresses;")
    current = result.stdout.strip() if result.returncode == 0 else "localhost"
    
    console.print(f"[bold]Current listen_addresses:[/bold] {current}")
    console.print()
    
    if current == "localhost" or current == "127.0.0.1":
        console.print("[yellow]Remote access is currently DISABLED[/yellow]")
    else:
        console.print("[green]Remote access is currently ENABLED[/green]")
    
    console.print()
    
    # Show pg_hba.conf relevant lines
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
        
        # Add rule to pg_hba.conf
        if hba_file:
            rule = "host    all             all             0.0.0.0/0               md5"
            with open(hba_file, 'a') as f:
                f.write(f"\n# Added by vexo-cli - allow remote\n{rule}\n")
        
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
                f.write(f"\n# Added by vexo-cli - allow {ip_range}\n{rule}\n")
        
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
    
    # Check 1: postgres has password
    result = run_psql(
        "SELECT passwd IS NOT NULL as has_password FROM pg_shadow WHERE usename = 'postgres';"
    )
    has_pw = 't' in result.stdout if result.returncode == 0 else False
    checks.append(("postgres has password", has_pw, "Yes" if has_pw else "No"))
    if not has_pw:
        recommendations.append("Set password for postgres user")
    
    # Check 2: Check for users without password
    result = run_psql(
        "SELECT count(*) FROM pg_shadow WHERE passwd IS NULL AND usename != 'postgres';"
    )
    no_pw_count = int(result.stdout.strip()) if result.returncode == 0 else 0
    checks.append(("Users without password", no_pw_count == 0, str(no_pw_count)))
    if no_pw_count > 0:
        recommendations.append(f"{no_pw_count} user(s) have no password set")
    
    # Check 3: Listen addresses
    result = run_psql("SHOW listen_addresses;")
    listen = result.stdout.strip() if result.returncode == 0 else "localhost"
    is_local = listen in ["localhost", "127.0.0.1"]
    checks.append(("Listen localhost only", is_local, listen))
    if not is_local:
        recommendations.append("PostgreSQL accepts remote connections - ensure pg_hba.conf is restrictive")
    
    # Check 4: SSL enabled
    result = run_psql("SHOW ssl;")
    ssl_on = result.stdout.strip() == "on" if result.returncode == 0 else False
    checks.append(("SSL enabled", ssl_on, "Yes" if ssl_on else "No"))
    if not ssl_on:
        recommendations.append("Consider enabling SSL for encrypted connections")
    
    # Check 5: Superuser count
    result = run_psql("SELECT count(*) FROM pg_roles WHERE rolsuper = true;")
    su_count = int(result.stdout.strip()) if result.returncode == 0 else 0
    checks.append(("Superuser count", su_count <= 2, str(su_count)))
    if su_count > 2:
        recommendations.append("Multiple superusers - review if all are necessary")
    
    # Display results
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
```

**Step 2: Commit**

```bash
git add modules/database/postgresql/security.py
git commit -m "feat(database): add PostgreSQL security management"
```

---

## Task 7: Create PostgreSQL Core & Users Modules

**Files:**
- Create: `modules/database/postgresql/core.py`
- Create: `modules/database/postgresql/users.py`

**Step 1: Create core.py**

```python
"""PostgreSQL core functions - install, list, create, delete databases."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list
from utils.shell import run_command, is_installed, require_root
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
        show_error("Installation failed!")
    
    press_enter_to_continue()


def list_databases():
    """List all PostgreSQL databases."""
    clear_screen()
    show_header()
    show_panel("Database List", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
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
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    db_name = text_input("Database name:")
    if not db_name:
        return
    
    # Check if exists
    if db_name in get_databases():
        show_error(f"Database '{db_name}' already exists.")
        press_enter_to_continue()
        return
    
    # Create user?
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
    
    # Create database
    result = run_psql(f"CREATE DATABASE {db_name};")
    if result.returncode != 0:
        show_error("Failed to create database.")
        console.print(f"[dim]{result.stderr}[/dim]")
        press_enter_to_continue()
        return
    
    show_success(f"Database '{db_name}' created!")
    
    # Create user
    if create_user and username:
        result = run_psql(f"CREATE USER {username} WITH PASSWORD '{password}';")
        if result.returncode == 0:
            run_psql(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {username};")
            show_success(f"User '{username}' created with access to {db_name}!")
        else:
            show_error("Failed to create user.")
    
    press_enter_to_continue()


def delete_database_interactive():
    """Delete a database."""
    clear_screen()
    show_header()
    show_panel("Delete Database", title="PostgreSQL", style="red")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
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
        show_error("Name does not match.")
        press_enter_to_continue()
        return
    
    # Terminate connections
    run_psql(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}';")
    
    result = run_psql(f"DROP DATABASE {db_name};")
    
    if result.returncode == 0:
        show_success(f"Database '{db_name}' deleted!")
    else:
        show_error("Failed to delete database.")
    
    press_enter_to_continue()
```

**Step 2: Create users.py**

```python
"""PostgreSQL user management."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import require_root
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
    
    result = run_psql(f"CREATE USER {username} WITH PASSWORD '{password}' {options};")
    
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
    
    result = run_psql(f"DROP USER {username};")
    
    if result.returncode == 0:
        show_success(f"User '{username}' deleted!")
    else:
        show_error("Failed to delete user. User may own objects.")
        console.print("[dim]Drop owned objects first: DROP OWNED BY username;[/dim]")
    
    press_enter_to_continue()
```

**Step 3: Commit**

```bash
git add modules/database/postgresql/core.py modules/database/postgresql/users.py
git commit -m "feat(database): add PostgreSQL core and users modules"
```

---

## Execution Handoff

Plan complete. Run all tasks sequentially to create the full PostgreSQL module.
