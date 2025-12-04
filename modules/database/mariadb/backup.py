"""MariaDB backup and restore functions."""

import os
from datetime import datetime

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, require_root
from utils.error_handler import handle_error
from modules.database.mariadb.utils import (
    is_mariadb_ready, get_user_databases, get_database_size,
    format_size, MARIA_BACKUP_DIR, get_mysql_credentials, run_mysql,
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
        handle_error("E4001", "MariaDB is not running.")
        press_enter_to_continue()
        return
    
    databases = get_user_databases()
    if not databases:
        show_info("No user databases found.")
        press_enter_to_continue()
        return
    
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
        handle_error("E4001", "Backup failed!")
        if result.stderr:
            console.print(f"[dim]{result.stderr}[/dim]")
    
    press_enter_to_continue()


def backup_all_databases():
    """Backup all databases."""
    clear_screen()
    show_header()
    show_panel("Backup All Databases", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        handle_error("E4001", "MariaDB is not running.")
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
        handle_error("E4001", "Backup failed!")
    
    press_enter_to_continue()


def restore_database():
    """Restore database from backup."""
    clear_screen()
    show_header()
    show_panel("Restore Database", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        handle_error("E4001", "MariaDB is not running.")
        press_enter_to_continue()
        return
    
    backup_path = text_input("Backup file path:")
    if not backup_path:
        return
    
    if not os.path.exists(backup_path):
        handle_error("E4001", "File not found.")
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
            run_mysql(f"DROP DATABASE `{database}`;")
        else:
            press_enter_to_continue()
            return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    run_mysql(f"CREATE DATABASE `{database}`;")
    
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
        handle_error("E4001", "Restore failed!")
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
        handle_error("E4001", f"Failed to create script: {e}")
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
