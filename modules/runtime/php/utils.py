"""Shared utilities for PHP runtime module."""

import os
import re

from utils.shell import run_command, is_installed, is_service_running

# PHP versions to support
PHP_VERSIONS = ["8.3", "8.4", "8.5"]

# Laravel-compatible PHP extensions
PHP_EXTENSIONS = [
    "cli", "fpm", "common",
    "bcmath", "ctype", "curl", "dom", "fileinfo", "mbstring", "pdo", "tokenizer", "xml",
    "mysql", "pgsql", "sqlite3",
    "zip", "gd", "intl", "opcache", "redis", "imagick", "soap", "imap", "exif",
]

# FPM config paths
PHP_FPM_POOL_DIR = "/etc/php/{version}/fpm/pool.d"
PHP_FPM_CONF = "/etc/php/{version}/fpm/php-fpm.conf"
PHP_INI_FPM = "/etc/php/{version}/fpm/php.ini"
PHP_INI_CLI = "/etc/php/{version}/cli/php.ini"


def get_installed_php_versions():
    """Get list of installed PHP versions."""
    installed = []
    for version in PHP_VERSIONS:
        if is_installed(f"php{version}") or is_installed(f"php{version}-cli"):
            installed.append(version)
    return installed


def get_default_php_version():
    """Get the current default PHP CLI version."""
    result = run_command("php -v 2>/dev/null | head -1", check=False, silent=True)
    if result.returncode != 0:
        return None
    
    output = result.stdout.strip()
    if "PHP" in output:
        parts = output.split()
        if len(parts) >= 2:
            version = parts[1]
            return ".".join(version.split(".")[:2])
    return None


def get_fpm_pool_path(version, pool_name="www"):
    """Get path to FPM pool config file."""
    return f"/etc/php/{version}/fpm/pool.d/{pool_name}.conf"


def get_fpm_service_name(version):
    """Get FPM service name for a PHP version."""
    return f"php{version}-fpm"


def is_fpm_running(version):
    """Check if PHP-FPM is running for a version."""
    return is_service_running(get_fpm_service_name(version))


def parse_fpm_pool_config(version, pool_name="www"):
    """Parse FPM pool configuration file."""
    config_path = get_fpm_pool_path(version, pool_name)
    config = {}
    
    if not os.path.exists(config_path):
        return config
    
    try:
        with open(config_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(";") or line.startswith("["):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
    except Exception:
        pass
    
    return config


def get_server_memory_mb():
    """Get total server memory in MB."""
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return kb // 1024
    except Exception:
        pass
    return 2048  # Default 2GB
