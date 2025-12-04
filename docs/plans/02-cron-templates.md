# Phase 2: Job Templates

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add job templates for Database Backup, System Cleanup, SSL Certificate Renewal, and Custom Script Runner.

**Architecture:** Create templates.py module with template generators and add_job.py with template selection menu. Each template produces a ready-to-use cron line with logging to per-job log files.

**Tech Stack:** Python, subprocess (existing)

**Prerequisite:** Complete Phase 1 (cron package structure)

---

## Task 1: Create Templates Module

**Files:**
- Create: `modules/cron/templates.py`

**Step 1: Create templates.py with all template generators**

```python
"""Job templates for vexo cron."""

import os

from modules.cron.common import CRON_LOG_DIR


def generate_laravel_scheduler(laravel_path, job_name):
    """
    Generate Laravel scheduler cron line.
    
    Args:
        laravel_path: Path to Laravel project
        job_name: Job name for logging
    
    Returns:
        tuple: (schedule, cron_line)
    """
    log_path = os.path.join(CRON_LOG_DIR, f"{job_name}.log")
    schedule = "* * * * *"
    command = f"cd {laravel_path} && php artisan schedule:run >> {log_path} 2>&1"
    return schedule, f"{schedule} {command}"


def generate_mysql_backup(database, user, password, backup_path, job_name, schedule="0 2 * * *"):
    """
    Generate MySQL/MariaDB backup cron line.
    
    Args:
        database: Database name
        user: MySQL user
        password: MySQL password
        backup_path: Directory to store backups
        job_name: Job name for logging
        schedule: Cron schedule (default: daily at 2am)
    
    Returns:
        tuple: (schedule, cron_line)
    """
    log_path = os.path.join(CRON_LOG_DIR, f"{job_name}.log")
    
    # Create backup command with date in filename
    command = (
        f"mysqldump -u{user} -p'{password}' {database} 2>> {log_path} | "
        f"gzip > {backup_path}/{database}-$(date +\\%Y\\%m\\%d-\\%H\\%M\\%S).sql.gz && "
        f"echo \"Backup completed: {database}\" >> {log_path}"
    )
    
    return schedule, f"{schedule} {command}"


def generate_postgresql_backup(database, user, password, backup_path, job_name, schedule="0 2 * * *"):
    """
    Generate PostgreSQL backup cron line.
    
    Args:
        database: Database name
        user: PostgreSQL user
        password: PostgreSQL password
        backup_path: Directory to store backups
        job_name: Job name for logging
        schedule: Cron schedule (default: daily at 2am)
    
    Returns:
        tuple: (schedule, cron_line)
    """
    log_path = os.path.join(CRON_LOG_DIR, f"{job_name}.log")
    
    command = (
        f"PGPASSWORD='{password}' pg_dump -U {user} {database} 2>> {log_path} | "
        f"gzip > {backup_path}/{database}-$(date +\\%Y\\%m\\%d-\\%H\\%M\\%S).sql.gz && "
        f"echo \"Backup completed: {database}\" >> {log_path}"
    )
    
    return schedule, f"{schedule} {command}"


def generate_backup_cleanup(backup_path, days, job_name, schedule="0 3 * * *"):
    """
    Generate backup cleanup cron line (delete old backups).
    
    Args:
        backup_path: Directory containing backups
        days: Delete files older than this many days
        job_name: Job name for logging
        schedule: Cron schedule (default: daily at 3am)
    
    Returns:
        tuple: (schedule, cron_line)
    """
    log_path = os.path.join(CRON_LOG_DIR, f"{job_name}.log")
    
    command = (
        f"find {backup_path} -name '*.sql.gz' -mtime +{days} -delete && "
        f"echo \"Cleanup completed: removed files older than {days} days\" >> {log_path}"
    )
    
    return schedule, f"{schedule} {command}"


def generate_laravel_cache_clear(laravel_path, job_name, schedule="0 4 * * *"):
    """
    Generate Laravel cache clear cron line.
    
    Args:
        laravel_path: Path to Laravel project
        job_name: Job name for logging
        schedule: Cron schedule (default: daily at 4am)
    
    Returns:
        tuple: (schedule, cron_line)
    """
    log_path = os.path.join(CRON_LOG_DIR, f"{job_name}.log")
    
    command = (
        f"cd {laravel_path} && "
        f"php artisan cache:clear && "
        f"php artisan config:clear && "
        f"php artisan view:clear && "
        f"echo \"Laravel cache cleared\" >> {log_path} 2>&1"
    )
    
    return schedule, f"{schedule} {command}"


def generate_temp_cleanup(path, days, job_name, schedule="0 5 * * *"):
    """
    Generate temp files cleanup cron line.
    
    Args:
        path: Directory to clean
        days: Delete files older than this many days
        job_name: Job name for logging
        schedule: Cron schedule (default: daily at 5am)
    
    Returns:
        tuple: (schedule, cron_line)
    """
    log_path = os.path.join(CRON_LOG_DIR, f"{job_name}.log")
    
    command = (
        f"find {path} -type f -mtime +{days} -delete 2>> {log_path} && "
        f"echo \"Temp cleanup completed\" >> {log_path}"
    )
    
    return schedule, f"{schedule} {command}"


def generate_log_rotation(log_path, max_size_mb, job_name, schedule="0 0 * * 0"):
    """
    Generate log rotation cron line.
    
    Args:
        log_path: Path pattern for logs (e.g., /var/log/myapp/*.log)
        max_size_mb: Truncate logs larger than this size
        job_name: Job name for logging
        schedule: Cron schedule (default: weekly on Sunday)
    
    Returns:
        tuple: (schedule, cron_line)
    """
    vexo_log_path = os.path.join(CRON_LOG_DIR, f"{job_name}.log")
    
    command = (
        f"find {os.path.dirname(log_path)} -name '{os.path.basename(log_path)}' "
        f"-size +{max_size_mb}M -exec truncate -s 0 {{}} \\; 2>> {vexo_log_path} && "
        f"echo \"Log rotation completed\" >> {vexo_log_path}"
    )
    
    return schedule, f"{schedule} {command}"


def generate_certbot_renew(job_name, schedule="0 3 * * *"):
    """
    Generate certbot renewal cron line.
    
    Args:
        job_name: Job name for logging
        schedule: Cron schedule (default: daily at 3am)
    
    Returns:
        tuple: (schedule, cron_line)
    """
    log_path = os.path.join(CRON_LOG_DIR, f"{job_name}.log")
    
    command = f"certbot renew --quiet >> {log_path} 2>&1"
    
    return schedule, f"{schedule} {command}"


def generate_custom_script(script_path, interpreter, job_name, schedule, working_dir=None):
    """
    Generate custom script runner cron line.
    
    Args:
        script_path: Path to script file
        interpreter: Script interpreter (php, python3, bash, node)
        job_name: Job name for logging
        schedule: Cron schedule
        working_dir: Optional working directory
    
    Returns:
        tuple: (schedule, cron_line)
    """
    log_path = os.path.join(CRON_LOG_DIR, f"{job_name}.log")
    
    if working_dir:
        command = f"cd {working_dir} && {interpreter} {script_path} >> {log_path} 2>&1"
    else:
        command = f"{interpreter} {script_path} >> {log_path} 2>&1"
    
    return schedule, f"{schedule} {command}"


def generate_custom_command(command, job_name, schedule):
    """
    Generate custom command cron line.
    
    Args:
        command: Full command to run
        job_name: Job name for logging
        schedule: Cron schedule
    
    Returns:
        tuple: (schedule, cron_line)
    """
    log_path = os.path.join(CRON_LOG_DIR, f"{job_name}.log")
    
    full_command = f"{command} >> {log_path} 2>&1"
    
    return schedule, f"{schedule} {full_command}"


# Template metadata for UI
TEMPLATE_INFO = {
    'laravel-scheduler': {
        'name': 'Laravel Scheduler',
        'description': 'Run artisan schedule:run every minute',
        'category': 'Laravel',
    },
    'mysql-backup': {
        'name': 'MySQL/MariaDB Backup',
        'description': 'Daily database dump with gzip compression',
        'category': 'Database',
    },
    'postgresql-backup': {
        'name': 'PostgreSQL Backup',
        'description': 'Daily database dump with gzip compression',
        'category': 'Database',
    },
    'backup-cleanup': {
        'name': 'Backup Cleanup',
        'description': 'Delete old backup files',
        'category': 'Database',
    },
    'laravel-cache': {
        'name': 'Laravel Cache Clear',
        'description': 'Clear cache, config, and view cache',
        'category': 'System',
    },
    'temp-cleanup': {
        'name': 'Temp Files Cleanup',
        'description': 'Delete old temporary files',
        'category': 'System',
    },
    'log-rotation': {
        'name': 'Log Rotation',
        'description': 'Truncate large log files',
        'category': 'System',
    },
    'certbot-renew': {
        'name': 'SSL Certificate Renewal',
        'description': 'Renew Let\'s Encrypt certificates',
        'category': 'SSL',
    },
    'custom-script': {
        'name': 'Custom Script',
        'description': 'Run PHP, Python, Bash, or Node script',
        'category': 'Custom',
    },
    'custom-command': {
        'name': 'Custom Command',
        'description': 'Run any shell command',
        'category': 'Custom',
    },
}
```

**Step 2: Commit**

```bash
git add modules/cron/templates.py
git commit -m "feat(cron): add job templates for various tasks"
```

---

## Task 2: Create Add Job Menu with Templates

**Files:**
- Create: `modules/cron/add_job.py`

**Step 1: Create add_job.py with template selection wizards**

```python
"""Add job wizards for vexo cron."""

import os

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_success,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import show_submenu, confirm_action, text_input, select_from_list
from utils.shell import require_root

from modules.cron.common import (
    CRON_PRESETS,
    CRON_LOG_DIR,
    add_cron_entry,
    job_exists,
    ensure_log_dir,
)
from modules.cron.templates import (
    generate_laravel_scheduler,
    generate_mysql_backup,
    generate_postgresql_backup,
    generate_backup_cleanup,
    generate_laravel_cache_clear,
    generate_temp_cleanup,
    generate_log_rotation,
    generate_certbot_renew,
    generate_custom_script,
    generate_custom_command,
)


def add_job_menu():
    """Display add job template selection menu."""
    while True:
        clear_screen()
        show_header()
        
        choice = show_submenu(
            title="Add Cron Job",
            options=[
                ("laravel", "1. Laravel Scheduler"),
                ("db_backup", "2. Database Backup"),
                ("cleanup", "3. System Cleanup"),
                ("ssl", "4. SSL Certificate Renewal"),
                ("custom", "5. Custom Command/Script"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "laravel":
            add_laravel_scheduler()
        elif choice == "db_backup":
            add_database_backup_menu()
        elif choice == "cleanup":
            add_cleanup_menu()
        elif choice == "ssl":
            add_certbot_renew()
        elif choice == "custom":
            add_custom_menu()
        elif choice == "back" or choice is None:
            break


def _get_job_name(default_prefix):
    """Get and validate job name from user."""
    job_name = text_input(
        title="Job Name",
        message="Enter job name:",
        default=default_prefix
    )
    
    if not job_name:
        return None
    
    job_name = job_name.lower().strip().replace(" ", "-")
    
    if job_exists(job_name):
        show_error(f"Job '{job_name}' already exists.")
        press_enter_to_continue()
        return None
    
    return job_name


def _get_schedule(default="0 2 * * *"):
    """Get schedule from user with preset options."""
    preset_options = [f"{schedule} ({desc})" for schedule, desc in CRON_PRESETS]
    preset_options.append("Custom (enter manually)")
    
    selection = select_from_list(
        title="Schedule",
        message="Select schedule:",
        options=preset_options
    )
    
    if not selection:
        return None
    
    if selection == "Custom (enter manually)":
        schedule = text_input(
            title="Cron Expression",
            message="Enter cron expression:",
            default=default
        )
        return schedule
    else:
        return selection.split(" (")[0]


def _save_job(job_name, cron_line):
    """Save job and show result."""
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return False
    
    ensure_log_dir()
    
    success = add_cron_entry(job_name, cron_line)
    
    if success:
        show_success(f"Cron job '{job_name}' created!")
        console.print()
        console.print(f"[dim]Log: {CRON_LOG_DIR}/{job_name}.log[/dim]")
        return True
    else:
        show_error("Failed to add cron job.")
        return False


# =============================================================================
# Laravel
# =============================================================================

def add_laravel_scheduler():
    """Add Laravel scheduler job."""
    clear_screen()
    show_header()
    show_panel("Laravel Scheduler", title="Add Job", style="cyan")
    
    console.print("[bold]Laravel Scheduler:[/bold]")
    console.print("  Runs 'php artisan schedule:run' every minute")
    console.print()
    
    laravel_path = text_input(
        title="Laravel Path",
        message="Enter Laravel project path:",
        default="/var/www/html"
    )
    
    if not laravel_path:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not os.path.exists(os.path.join(laravel_path, "artisan")):
        show_error(f"Laravel artisan not found at {laravel_path}")
        press_enter_to_continue()
        return
    
    job_name = _get_job_name(f"laravel-scheduler-{os.path.basename(laravel_path)}")
    if not job_name:
        return
    
    schedule, cron_line = generate_laravel_scheduler(laravel_path, job_name)
    
    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  Job: {job_name}")
    console.print(f"  Schedule: {schedule} (every minute)")
    console.print(f"  Path: {laravel_path}")
    console.print()
    
    if not confirm_action("Create this job?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    _save_job(job_name, cron_line)
    press_enter_to_continue()


# =============================================================================
# Database Backup
# =============================================================================

def add_database_backup_menu():
    """Database backup submenu."""
    clear_screen()
    show_header()
    
    choice = show_submenu(
        title="Database Backup",
        options=[
            ("mysql", "1. MySQL/MariaDB Backup"),
            ("postgresql", "2. PostgreSQL Backup"),
            ("cleanup", "3. Backup Cleanup (delete old)"),
            ("back", "← Back"),
        ],
    )
    
    if choice == "mysql":
        add_mysql_backup()
    elif choice == "postgresql":
        add_postgresql_backup()
    elif choice == "cleanup":
        add_backup_cleanup()


def add_mysql_backup():
    """Add MySQL backup job."""
    clear_screen()
    show_header()
    show_panel("MySQL/MariaDB Backup", title="Add Job", style="cyan")
    
    database = text_input(title="Database", message="Database name:")
    if not database:
        return
    
    user = text_input(title="User", message="MySQL user:", default="root")
    if not user:
        return
    
    password = text_input(title="Password", message="MySQL password:", password=True)
    if password is None:
        return
    
    backup_path = text_input(title="Backup Path", message="Backup directory:", default="/var/backups/mysql")
    if not backup_path:
        return
    
    job_name = _get_job_name(f"mysql-backup-{database}")
    if not job_name:
        return
    
    schedule = _get_schedule("0 2 * * *")
    if not schedule:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    _, cron_line = generate_mysql_backup(database, user, password, backup_path, job_name, schedule)
    
    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  Job: {job_name}")
    console.print(f"  Database: {database}")
    console.print(f"  Schedule: {schedule}")
    console.print(f"  Backup to: {backup_path}")
    console.print()
    
    if not confirm_action("Create this job?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Create backup directory
    os.makedirs(backup_path, mode=0o750, exist_ok=True)
    
    _save_job(job_name, cron_line)
    press_enter_to_continue()


def add_postgresql_backup():
    """Add PostgreSQL backup job."""
    clear_screen()
    show_header()
    show_panel("PostgreSQL Backup", title="Add Job", style="cyan")
    
    database = text_input(title="Database", message="Database name:")
    if not database:
        return
    
    user = text_input(title="User", message="PostgreSQL user:", default="postgres")
    if not user:
        return
    
    password = text_input(title="Password", message="PostgreSQL password:", password=True)
    if password is None:
        return
    
    backup_path = text_input(title="Backup Path", message="Backup directory:", default="/var/backups/postgresql")
    if not backup_path:
        return
    
    job_name = _get_job_name(f"postgresql-backup-{database}")
    if not job_name:
        return
    
    schedule = _get_schedule("0 2 * * *")
    if not schedule:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    _, cron_line = generate_postgresql_backup(database, user, password, backup_path, job_name, schedule)
    
    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  Job: {job_name}")
    console.print(f"  Database: {database}")
    console.print(f"  Schedule: {schedule}")
    console.print(f"  Backup to: {backup_path}")
    console.print()
    
    if not confirm_action("Create this job?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    os.makedirs(backup_path, mode=0o750, exist_ok=True)
    
    _save_job(job_name, cron_line)
    press_enter_to_continue()


def add_backup_cleanup():
    """Add backup cleanup job."""
    clear_screen()
    show_header()
    show_panel("Backup Cleanup", title="Add Job", style="cyan")
    
    console.print("[bold]Backup Cleanup:[/bold]")
    console.print("  Deletes old .sql.gz backup files")
    console.print()
    
    backup_path = text_input(title="Backup Path", message="Backup directory:", default="/var/backups/mysql")
    if not backup_path:
        return
    
    days = text_input(title="Retention", message="Delete backups older than (days):", default="7")
    if not days:
        return
    
    try:
        days = int(days)
    except ValueError:
        show_error("Invalid number of days.")
        press_enter_to_continue()
        return
    
    job_name = _get_job_name(f"backup-cleanup-{os.path.basename(backup_path)}")
    if not job_name:
        return
    
    schedule = _get_schedule("0 3 * * *")
    if not schedule:
        return
    
    _, cron_line = generate_backup_cleanup(backup_path, days, job_name, schedule)
    
    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  Job: {job_name}")
    console.print(f"  Path: {backup_path}")
    console.print(f"  Delete files older than: {days} days")
    console.print(f"  Schedule: {schedule}")
    console.print()
    
    if not confirm_action("Create this job?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    _save_job(job_name, cron_line)
    press_enter_to_continue()


# =============================================================================
# System Cleanup
# =============================================================================

def add_cleanup_menu():
    """System cleanup submenu."""
    clear_screen()
    show_header()
    
    choice = show_submenu(
        title="System Cleanup",
        options=[
            ("laravel", "1. Laravel Cache Clear"),
            ("temp", "2. Temp Files Cleanup"),
            ("logs", "3. Log Rotation"),
            ("back", "← Back"),
        ],
    )
    
    if choice == "laravel":
        add_laravel_cache_clear()
    elif choice == "temp":
        add_temp_cleanup()
    elif choice == "logs":
        add_log_rotation()


def add_laravel_cache_clear():
    """Add Laravel cache clear job."""
    clear_screen()
    show_header()
    show_panel("Laravel Cache Clear", title="Add Job", style="cyan")
    
    laravel_path = text_input(
        title="Laravel Path",
        message="Enter Laravel project path:",
        default="/var/www/html"
    )
    
    if not laravel_path:
        return
    
    if not os.path.exists(os.path.join(laravel_path, "artisan")):
        show_error(f"Laravel artisan not found at {laravel_path}")
        press_enter_to_continue()
        return
    
    job_name = _get_job_name(f"laravel-cache-{os.path.basename(laravel_path)}")
    if not job_name:
        return
    
    schedule = _get_schedule("0 4 * * *")
    if not schedule:
        return
    
    _, cron_line = generate_laravel_cache_clear(laravel_path, job_name, schedule)
    
    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  Job: {job_name}")
    console.print(f"  Path: {laravel_path}")
    console.print(f"  Schedule: {schedule}")
    console.print("  Actions: cache:clear, config:clear, view:clear")
    console.print()
    
    if not confirm_action("Create this job?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    _save_job(job_name, cron_line)
    press_enter_to_continue()


def add_temp_cleanup():
    """Add temp files cleanup job."""
    clear_screen()
    show_header()
    show_panel("Temp Files Cleanup", title="Add Job", style="cyan")
    
    path = text_input(title="Path", message="Directory to clean:", default="/tmp")
    if not path:
        return
    
    days = text_input(title="Age", message="Delete files older than (days):", default="7")
    if not days:
        return
    
    try:
        days = int(days)
    except ValueError:
        show_error("Invalid number of days.")
        press_enter_to_continue()
        return
    
    job_name = _get_job_name("temp-cleanup")
    if not job_name:
        return
    
    schedule = _get_schedule("0 5 * * *")
    if not schedule:
        return
    
    _, cron_line = generate_temp_cleanup(path, days, job_name, schedule)
    
    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  Job: {job_name}")
    console.print(f"  Path: {path}")
    console.print(f"  Delete files older than: {days} days")
    console.print(f"  Schedule: {schedule}")
    console.print()
    
    if not confirm_action("Create this job?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    _save_job(job_name, cron_line)
    press_enter_to_continue()


def add_log_rotation():
    """Add log rotation job."""
    clear_screen()
    show_header()
    show_panel("Log Rotation", title="Add Job", style="cyan")
    
    log_path = text_input(title="Log Path", message="Log files pattern (e.g., /var/log/myapp/*.log):", default="/var/log/*.log")
    if not log_path:
        return
    
    max_size = text_input(title="Max Size", message="Truncate logs larger than (MB):", default="100")
    if not max_size:
        return
    
    try:
        max_size = int(max_size)
    except ValueError:
        show_error("Invalid size.")
        press_enter_to_continue()
        return
    
    job_name = _get_job_name("log-rotation")
    if not job_name:
        return
    
    schedule = _get_schedule("0 0 * * 0")
    if not schedule:
        return
    
    _, cron_line = generate_log_rotation(log_path, max_size, job_name, schedule)
    
    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  Job: {job_name}")
    console.print(f"  Path: {log_path}")
    console.print(f"  Max size: {max_size} MB")
    console.print(f"  Schedule: {schedule}")
    console.print()
    
    if not confirm_action("Create this job?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    _save_job(job_name, cron_line)
    press_enter_to_continue()


# =============================================================================
# SSL
# =============================================================================

def add_certbot_renew():
    """Add certbot renewal job."""
    clear_screen()
    show_header()
    show_panel("SSL Certificate Renewal", title="Add Job", style="cyan")
    
    console.print("[bold]Certbot Renewal:[/bold]")
    console.print("  Runs 'certbot renew' to renew Let's Encrypt certificates")
    console.print()
    
    job_name = _get_job_name("certbot-renew")
    if not job_name:
        return
    
    schedule = _get_schedule("0 3 * * *")
    if not schedule:
        return
    
    _, cron_line = generate_certbot_renew(job_name, schedule)
    
    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  Job: {job_name}")
    console.print(f"  Schedule: {schedule}")
    console.print()
    
    if not confirm_action("Create this job?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    _save_job(job_name, cron_line)
    press_enter_to_continue()


# =============================================================================
# Custom
# =============================================================================

def add_custom_menu():
    """Custom command/script submenu."""
    clear_screen()
    show_header()
    
    choice = show_submenu(
        title="Custom",
        options=[
            ("script", "1. Run Script (PHP/Python/Bash/Node)"),
            ("command", "2. Run Command"),
            ("back", "← Back"),
        ],
    )
    
    if choice == "script":
        add_custom_script()
    elif choice == "command":
        add_custom_command()


def add_custom_script():
    """Add custom script runner job."""
    clear_screen()
    show_header()
    show_panel("Custom Script", title="Add Job", style="cyan")
    
    script_path = text_input(title="Script Path", message="Full path to script:")
    if not script_path:
        return
    
    if not os.path.exists(script_path):
        show_warning(f"Script not found: {script_path}")
        if not confirm_action("Continue anyway?"):
            return
    
    interpreters = ["php", "python3", "bash", "node", "Other"]
    interpreter = select_from_list(
        title="Interpreter",
        message="Select interpreter:",
        options=interpreters
    )
    
    if not interpreter:
        return
    
    if interpreter == "Other":
        interpreter = text_input(title="Interpreter", message="Enter interpreter command:")
        if not interpreter:
            return
    
    working_dir = text_input(title="Working Directory", message="Working directory (optional):", default="")
    
    job_name = _get_job_name(f"script-{os.path.basename(script_path).split('.')[0]}")
    if not job_name:
        return
    
    schedule = _get_schedule("0 0 * * *")
    if not schedule:
        return
    
    _, cron_line = generate_custom_script(
        script_path, interpreter, job_name, schedule,
        working_dir if working_dir else None
    )
    
    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  Job: {job_name}")
    console.print(f"  Script: {script_path}")
    console.print(f"  Interpreter: {interpreter}")
    if working_dir:
        console.print(f"  Working Dir: {working_dir}")
    console.print(f"  Schedule: {schedule}")
    console.print()
    
    if not confirm_action("Create this job?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    _save_job(job_name, cron_line)
    press_enter_to_continue()


def add_custom_command():
    """Add custom command job."""
    clear_screen()
    show_header()
    show_panel("Custom Command", title="Add Job", style="cyan")
    
    command = text_input(title="Command", message="Enter full command to run:")
    if not command:
        return
    
    job_name = _get_job_name("custom-job")
    if not job_name:
        return
    
    schedule = _get_schedule("0 0 * * *")
    if not schedule:
        return
    
    _, cron_line = generate_custom_command(command, job_name, schedule)
    
    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  Job: {job_name}")
    console.print(f"  Command: {command}")
    console.print(f"  Schedule: {schedule}")
    console.print()
    
    if not confirm_action("Create this job?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    _save_job(job_name, cron_line)
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/cron/add_job.py
git commit -m "feat(cron): add job creation wizards for all templates"
```

---

## Task 3: Update Package Init

**Files:**
- Modify: `modules/cron/__init__.py`

**Step 1: Update __init__.py to use new add_job menu**

```python
"""Cron module for vexo (Scheduled Tasks)."""

from ui.menu import run_menu_loop

from modules.cron.add_job import add_job_menu
from modules.cron.jobs import (
    remove_cron_job_interactive,
    list_cron_jobs,
    toggle_cron_job,
)
from modules.cron.backup import backup_crontab, restore_crontab
from modules.cron.status import show_status


def show_menu():
    """Display the Cron Management submenu."""
    options = [
        ("add", "1. Add Cron Job"),
        ("remove", "2. Remove Cron Job"),
        ("list", "3. List Cron Jobs"),
        ("toggle", "4. Enable/Disable Job"),
        ("backup", "5. Backup Crontab"),
        ("restore", "6. Restore Crontab"),
        ("status", "7. Show Status"),
        ("back", "← Back to Main Menu"),
    ]
    
    handlers = {
        "add": add_job_menu,
        "remove": remove_cron_job_interactive,
        "list": list_cron_jobs,
        "toggle": toggle_cron_job,
        "backup": backup_crontab,
        "restore": restore_crontab,
        "status": show_status,
    }
    
    run_menu_loop("Cron Jobs", options, handlers, lambda: "Cron Jobs Manager")
```

**Step 2: Commit**

```bash
git add modules/cron/__init__.py
git commit -m "feat(cron): integrate add job menu with templates"
```

---

## Summary

After Phase 2, the cron module will have templates for:

- **Laravel:** Scheduler
- **Database:** MySQL backup, PostgreSQL backup, Backup cleanup
- **System:** Laravel cache clear, Temp cleanup, Log rotation
- **SSL:** Certbot renewal
- **Custom:** Script runner (PHP/Python/Bash/Node), Custom command

Each template:
- Logs output to `/var/log/vexo/cron/{job-name}.log`
- Uses preset or custom schedule
- Creates necessary directories automatically

Files added/modified:
- `modules/cron/templates.py` (new)
- `modules/cron/add_job.py` (new)
- `modules/cron/__init__.py` (updated)
