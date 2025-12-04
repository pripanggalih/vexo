"""Common utilities and constants for fail2ban module."""

import os
import re
from pathlib import Path

from utils.shell import run_command, is_installed, is_service_running


# Paths
FAIL2BAN_CONFIG_DIR = "/etc/fail2ban"
JAIL_LOCAL = "/etc/fail2ban/jail.local"
JAIL_D_DIR = "/etc/fail2ban/jail.d"
FILTER_D_DIR = "/etc/fail2ban/filter.d"
FAIL2BAN_LOG = "/var/log/fail2ban.log"
FAIL2BAN_DB = "/var/lib/fail2ban/fail2ban.sqlite3"

# Vexo data directory
VEXO_FAIL2BAN_DIR = Path.home() / ".vexo" / "fail2ban"
HISTORY_DB = VEXO_FAIL2BAN_DIR / "history.db"
CONFIG_FILE = VEXO_FAIL2BAN_DIR / "config.json"
WHITELIST_FILE = VEXO_FAIL2BAN_DIR / "whitelist.json"
NOTIFICATIONS_FILE = VEXO_FAIL2BAN_DIR / "notifications.json"
BACKUPS_DIR = VEXO_FAIL2BAN_DIR / "backups"

# Defaults
DEFAULT_BANTIME = "1h"
DEFAULT_FINDTIME = "10m"
DEFAULT_MAXRETRY = "5"


def ensure_data_dir():
    """Ensure vexo fail2ban data directory exists."""
    VEXO_FAIL2BAN_DIR.mkdir(parents=True, exist_ok=True)
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


def is_fail2ban_installed():
    """Check if fail2ban is installed."""
    return is_installed("fail2ban")


def is_fail2ban_running():
    """Check if fail2ban service is running."""
    return is_service_running("fail2ban")


def get_fail2ban_version():
    """Get fail2ban version."""
    result = run_command("fail2ban-client --version", check=False, silent=True)
    if result.returncode == 0:
        match = re.search(r'v?(\d+\.\d+\.\d+)', result.stdout)
        if match:
            return match.group(1)
    return "unknown"


def get_active_jails():
    """Get list of active jails."""
    result = run_command("fail2ban-client status", check=False, silent=True)
    if result.returncode != 0:
        return []
    
    jails = []
    for line in result.stdout.split('\n'):
        if 'Jail list:' in line:
            jail_part = line.split(':')[-1].strip()
            jails = [j.strip() for j in jail_part.split(',') if j.strip()]
            break
    
    return jails


def get_jail_stats(jail):
    """Get statistics for a specific jail."""
    result = run_command(f"fail2ban-client status {jail}", check=False, silent=True)
    if result.returncode != 0:
        return {'currently_banned': 0, 'total_banned': 0, 'failed': 0}
    
    stats = {'currently_banned': 0, 'total_banned': 0, 'failed': 0}
    
    for line in result.stdout.split('\n'):
        if 'Currently banned:' in line:
            try:
                stats['currently_banned'] = int(line.split(':')[-1].strip())
            except ValueError:
                pass
        elif 'Total banned:' in line:
            try:
                stats['total_banned'] = int(line.split(':')[-1].strip())
            except ValueError:
                pass
        elif 'Currently failed:' in line:
            try:
                stats['failed'] = int(line.split(':')[-1].strip())
            except ValueError:
                pass
    
    return stats


def get_banned_ips(jail):
    """Get list of banned IPs for a jail."""
    result = run_command(f"fail2ban-client status {jail}", check=False, silent=True)
    if result.returncode != 0:
        return []
    
    for line in result.stdout.split('\n'):
        if 'Banned IP list:' in line:
            ip_part = line.split(':')[-1].strip()
            if ip_part:
                return [ip.strip() for ip in ip_part.split() if ip.strip()]
    
    return []


def get_all_banned_ips():
    """Get all banned IPs across all jails."""
    banned = {}
    for jail in get_active_jails():
        ips = get_banned_ips(jail)
        if ips:
            banned[jail] = ips
    return banned


def is_valid_ip(ip):
    """Validate IPv4 address."""
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    try:
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
    except ValueError:
        return False
    return True


def is_valid_cidr(cidr):
    """Validate CIDR notation (e.g., 192.168.0.0/24)."""
    if '/' not in cidr:
        return False
    ip_part, prefix = cidr.rsplit('/', 1)
    if not is_valid_ip(ip_part):
        return False
    try:
        prefix_int = int(prefix)
        return 0 <= prefix_int <= 32
    except ValueError:
        return False


def detect_services():
    """Detect installed services for jail configuration."""
    return {
        'ssh': is_installed("openssh-server") or os.path.exists("/etc/ssh/sshd_config"),
        'nginx': is_installed("nginx"),
        'apache': is_installed("apache2"),
        'postfix': is_installed("postfix"),
        'dovecot': is_installed("dovecot-core"),
        'mysql': is_installed("mysql-server") or is_installed("mariadb-server"),
        'postgresql': is_installed("postgresql"),
    }
