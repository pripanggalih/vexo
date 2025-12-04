"""Shared utilities for Redis module."""

from utils.shell import run_command, is_installed, is_service_running


def is_redis_ready():
    """Check if Redis is installed and running."""
    return is_installed("redis-server") and is_service_running("redis-server")


def run_redis_cli(cmd, silent=True):
    """Run Redis CLI command."""
    return run_command(f'redis-cli {cmd}', check=False, silent=silent)


def redis_info(section=None):
    """Get Redis INFO output."""
    cmd = f"INFO {section}" if section else "INFO"
    result = run_redis_cli(cmd)
    if result.returncode != 0:
        return {}
    
    info = {}
    for line in result.stdout.strip().split('\n'):
        if ':' in line and not line.startswith('#'):
            key, value = line.split(':', 1)
            info[key.strip()] = value.strip()
    return info


def get_redis_config(key):
    """Get Redis configuration value."""
    result = run_redis_cli(f"CONFIG GET {key}")
    if result.returncode == 0 and result.stdout.strip():
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            return lines[1]
    return None


def set_redis_config(key, value):
    """Set Redis configuration value."""
    return run_redis_cli(f'CONFIG SET {key} "{value}"')


def format_size(size_bytes):
    """Format size in bytes to human readable."""
    try:
        size_bytes = int(size_bytes)
    except (ValueError, TypeError):
        return str(size_bytes)
    
    if size_bytes >= 1024 ** 3:
        return f"{size_bytes / 1024 ** 3:.2f} GB"
    elif size_bytes >= 1024 ** 2:
        return f"{size_bytes / 1024 ** 2:.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes} B"


def get_redis_version():
    """Get Redis version."""
    info = redis_info("server")
    return info.get("redis_version", "Unknown")


def get_db_keys_count():
    """Get key count per database."""
    info = redis_info("keyspace")
    dbs = {}
    for key, value in info.items():
        if key.startswith('db'):
            parts = dict(item.split('=') for item in value.split(','))
            dbs[key] = int(parts.get('keys', 0))
    return dbs
