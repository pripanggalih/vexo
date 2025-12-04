"""Global configuration for vexo."""

import os

# Application Info
APP_NAME = "vexo"
APP_VERSION = "1.0.0"
APP_TAGLINE = "VPS Easy eXecution Orchestrator"
APP_DESCRIPTION = "Management CLI for Ubuntu/Debian"

# Paths - Nginx
NGINX_SITES_AVAILABLE = "/etc/nginx/sites-available"
NGINX_SITES_ENABLED = "/etc/nginx/sites-enabled"
NGINX_CONFIG_PATH = "/etc/nginx/nginx.conf"

# Paths - PHP
PHP_FPM_PATH = "/etc/php"
PHP_VERSIONS = ["8.3", "8.4", "8.5"]

# Paths - Application
APP_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(APP_DIR, "templates")

# Default web root
DEFAULT_WEB_ROOT = "/var/www"

# NVM
NVM_DIR = os.path.expanduser("~/.nvm")
NVM_INSTALL_URL = "https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh"

# Database
MYSQL_CONFIG_PATH = "/etc/mysql/mysql.conf.d/mysqld.cnf"

# Postfix
POSTFIX_CONFIG_PATH = "/etc/postfix/main.cf"

# UI Colors (for reference, actual styling in ui/styles.py)
COLORS = {
    "primary": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "info": "blue",
}

# Thresholds for monitoring (percentage)
THRESHOLDS = {
    "good": 70,      # < 70% = green
    "warning": 85,   # 70-85% = yellow
                     # > 85% = red
}

# Alert Thresholds (percentage, can be overridden by user config)
ALERT_THRESHOLDS = {
    "cpu": {"warning": 70, "critical": 90},
    "memory": {"warning": 80, "critical": 95},
    "disk": {"warning": 80, "critical": 90},
    "swap": {"warning": 50, "critical": 80},
    "load_avg": {"warning": 2.0, "critical": 5.0},  # multiplier of CPU cores
}

# Logging Configuration
LOG_CONFIG = {
    "log_dir": "/var/log/vexo",
    "log_file": "monitor.log",
    "retention_days": 7,
    "log_interval": 60,  # seconds between log entries
    "max_log_size_mb": 50,
}

# User config file path
USER_CONFIG_PATH = os.path.expanduser("~/.vexo/config.json")
