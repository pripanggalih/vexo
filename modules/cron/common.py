"""Common utilities for cron module."""

import os
import tempfile
from datetime import datetime

from utils.shell import run_command

# Constants
VEXO_CONFIG_DIR = "/etc/vexo"
CRON_BACKUP_DIR = "/etc/vexo/cron-backups"
CRON_LOG_DIR = "/var/log/vexo/cron"
CRON_USER = "www-data"

# Cron presets
CRON_PRESETS = [
    ("* * * * *", "Every minute"),
    ("*/5 * * * *", "Every 5 minutes"),
    ("*/15 * * * *", "Every 15 minutes"),
    ("*/30 * * * *", "Every 30 minutes"),
    ("0 * * * *", "Every hour"),
    ("0 */6 * * *", "Every 6 hours"),
    ("0 0 * * *", "Every day at midnight"),
    ("0 0 * * 0", "Every Sunday at midnight"),
    ("0 0 1 * *", "First day of month"),
]


def get_crontab_lines():
    """Get current crontab lines for www-data user."""
    result = run_command(f"crontab -u {CRON_USER} -l 2>/dev/null", check=False, silent=True)
    if result.returncode == 0 and result.stdout:
        return result.stdout.strip().split('\n')
    return []


def save_crontab(lines):
    """Save crontab for www-data user."""
    content = '\n'.join(lines) + '\n'
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, prefix='vexo-crontab-') as f:
            f.write(content)
            tmp_file = f.name
        
        result = run_command(f"crontab -u {CRON_USER} {tmp_file}", check=False, silent=True)
        
        os.unlink(tmp_file)
        return result.returncode == 0
    except IOError:
        return False


def get_vexo_jobs():
    """Get list of vexo-managed cron jobs."""
    lines = get_crontab_lines()
    jobs = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("# vexo:"):
            job_name = line.replace("# vexo:", "").strip()
            if i + 1 < len(lines):
                cron_line = lines[i + 1]
                enabled = not cron_line.startswith("#")
                jobs.append({
                    "name": job_name,
                    "line": cron_line.lstrip("# "),
                    "enabled": enabled,
                    "index": i
                })
            i += 2
        else:
            i += 1
    
    return jobs


def add_cron_entry(job_name, cron_line):
    """Add a new cron entry with vexo marker."""
    lines = get_crontab_lines()
    
    while lines and not lines[0].strip():
        lines.pop(0)
    
    lines.append(f"# vexo: {job_name}")
    lines.append(cron_line)
    
    return save_crontab(lines)


def remove_cron_entry(job_name):
    """Remove a cron entry by job name."""
    lines = get_crontab_lines()
    new_lines = []
    skip_next = False
    
    for line in lines:
        if f"# vexo: {job_name}" in line:
            skip_next = True
            continue
        if skip_next:
            skip_next = False
            continue
        new_lines.append(line)
    
    return save_crontab(new_lines)


def toggle_cron_entry(job_name, enable):
    """Enable or disable a cron entry."""
    lines = get_crontab_lines()
    new_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        if f"# vexo: {job_name}" in line:
            new_lines.append(line)
            if i + 1 < len(lines):
                cron_line = lines[i + 1]
                if enable:
                    new_lines.append(cron_line.lstrip("# "))
                else:
                    if not cron_line.startswith("#"):
                        new_lines.append(f"# {cron_line}")
                    else:
                        new_lines.append(cron_line)
                i += 2
            else:
                i += 1
        else:
            new_lines.append(line)
            i += 1
    
    return save_crontab(new_lines)


def parse_cron_line(cron_line):
    """
    Parse a cron line into schedule and command.
    
    Returns:
        tuple: (schedule, command) or (None, None) if invalid
    """
    parts = cron_line.split(None, 5)
    if len(parts) >= 6:
        schedule = " ".join(parts[:5])
        command = parts[5]
        return schedule, command
    return None, None


def get_job_log_path(job_name):
    """Get log file path for a job."""
    return os.path.join(CRON_LOG_DIR, f"{job_name}.log")


def ensure_log_dir():
    """Ensure cron log directory exists."""
    os.makedirs(CRON_LOG_DIR, mode=0o755, exist_ok=True)


def job_exists(job_name):
    """Check if a job with given name already exists."""
    jobs = get_vexo_jobs()
    return any(job["name"] == job_name for job in jobs)
