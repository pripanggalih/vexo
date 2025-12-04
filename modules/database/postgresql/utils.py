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
