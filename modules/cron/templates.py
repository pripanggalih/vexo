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
