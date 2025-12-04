"""Common utilities for supervisor module."""

import os
import re

# Constants
SUPERVISOR_CONF_DIR = "/etc/supervisor/conf.d"
SUPERVISOR_LOG_DIR = "/var/log/supervisor"


def validate_worker_name(name):
    """
    Validate worker name (alphanumeric and hyphens only).
    
    Args:
        name: Worker name to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not name:
        return False
    if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$', name):
        return False
    if '--' in name:
        return False
    return True


def get_config_path(worker_name):
    """Get config file path for a worker."""
    return os.path.join(SUPERVISOR_CONF_DIR, f"{worker_name}.conf")


def get_log_path(worker_name):
    """Get log file path for a worker."""
    return os.path.join(SUPERVISOR_LOG_DIR, f"{worker_name}.log")


def worker_exists(worker_name):
    """Check if a worker config already exists."""
    return os.path.exists(get_config_path(worker_name))


def get_all_workers():
    """
    Get list of all supervisor workers (not just vexo-managed).
    
    Returns:
        list: List of worker names
    """
    workers = []
    
    if not os.path.exists(SUPERVISOR_CONF_DIR):
        return workers
    
    for filename in os.listdir(SUPERVISOR_CONF_DIR):
        if filename.endswith('.conf'):
            workers.append(filename[:-5])
    
    return sorted(workers)


def get_vexo_workers():
    """
    Get list of vexo-managed queue workers.
    
    Returns:
        list: List of worker names managed by vexo
    """
    workers = []
    
    if not os.path.exists(SUPERVISOR_CONF_DIR):
        return workers
    
    for filename in os.listdir(SUPERVISOR_CONF_DIR):
        if filename.endswith('.conf'):
            config_path = os.path.join(SUPERVISOR_CONF_DIR, filename)
            try:
                with open(config_path, 'r') as f:
                    content = f.read()
                    # Check for vexo marker or artisan queue:work
                    if '# vexo-managed' in content or 'artisan queue:work' in content or 'artisan horizon' in content:
                        workers.append(filename[:-5])
            except IOError:
                continue
    
    return sorted(workers)


def parse_worker_config(worker_name):
    """
    Parse a worker config file and return its settings.
    
    Args:
        worker_name: Name of the worker
    
    Returns:
        dict: Parsed configuration or None if not found
    """
    config_path = get_config_path(worker_name)
    
    if not os.path.exists(config_path):
        return None
    
    config = {
        'name': worker_name,
        'command': '',
        'user': 'www-data',
        'numprocs': 1,
        'autostart': True,
        'autorestart': True,
        'environment': {},
        'stdout_logfile': '',
        'stdout_logfile_maxbytes': '50MB',
        'stdout_logfile_backups': 5,
    }
    
    try:
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('[') and not line.startswith(';'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key == 'command':
                        config['command'] = value
                    elif key == 'user':
                        config['user'] = value
                    elif key == 'numprocs':
                        config['numprocs'] = int(value)
                    elif key == 'autostart':
                        config['autostart'] = value.lower() == 'true'
                    elif key == 'autorestart':
                        config['autorestart'] = value.lower() == 'true'
                    elif key == 'stdout_logfile':
                        config['stdout_logfile'] = value
                    elif key == 'stdout_logfile_maxbytes':
                        config['stdout_logfile_maxbytes'] = value
                    elif key == 'stdout_logfile_backups':
                        config['stdout_logfile_backups'] = int(value)
                    elif key == 'environment':
                        config['environment'] = _parse_env_string(value)
    except (IOError, ValueError):
        pass
    
    return config


def _parse_env_string(env_string):
    """Parse supervisor environment string to dict."""
    env = {}
    if not env_string:
        return env
    
    # Format: KEY="value",KEY2="value2"
    pairs = re.findall(r'(\w+)="([^"]*)"', env_string)
    for key, value in pairs:
        env[key] = value
    
    return env


def format_env_string(env_dict):
    """Format dict to supervisor environment string."""
    if not env_dict:
        return ''
    
    pairs = [f'{key}="{value}"' for key, value in env_dict.items()]
    return ','.join(pairs)
