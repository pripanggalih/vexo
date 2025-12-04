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
