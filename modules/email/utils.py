"""Shared utilities for email module."""

import os
import json

from utils.shell import run_command, is_installed, is_service_running

# Config paths
VEXO_CONFIG_DIR = "/etc/vexo"
EMAIL_CONFIG_FILE = "/etc/vexo/email-config.json"
EMAIL_DOMAINS_CONFIG = "/etc/vexo/email-domains.json"


def ensure_config_dir():
    """Ensure /etc/vexo directory exists."""
    if not os.path.exists(VEXO_CONFIG_DIR):
        os.makedirs(VEXO_CONFIG_DIR, mode=0o755)


def load_email_config():
    """Load email configuration."""
    if not os.path.exists(EMAIL_CONFIG_FILE):
        return {}
    try:
        with open(EMAIL_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_email_config(config):
    """Save email configuration."""
    ensure_config_dir()
    try:
        with open(EMAIL_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except IOError:
        return False


def get_email_status():
    """Get overall email system status."""
    status = {
        "postfix": {
            "installed": is_installed("postfix"),
            "running": is_service_running("postfix"),
        },
        "dovecot": {
            "installed": is_installed("dovecot-core"),
            "running": is_service_running("dovecot"),
        },
        "roundcube": {
            "installed": os.path.exists("/var/www/roundcube") or is_installed("roundcube"),
        },
    }
    return status


def format_service_status(name, installed, running=None):
    """Format service status for display."""
    if not installed:
        return f"{name}: [dim]Not Installed[/dim]"
    if running is None:
        return f"{name}: [green]Installed[/green]"
    if running:
        return f"{name}: [green]Running[/green]"
    return f"{name}: [red]Stopped[/red]"
