"""Postfix-specific utilities."""

import os
import json

from utils.shell import run_command, is_installed, is_service_running, get_hostname

# Postfix paths
POSTFIX_MAIN_CF = "/etc/postfix/main.cf"
POSTFIX_MASTER_CF = "/etc/postfix/master.cf"
POSTFIX_VIRTUAL = "/etc/postfix/virtual"
POSTFIX_TRANSPORT = "/etc/postfix/transport"
POSTFIX_SENDER_RELAY = "/etc/postfix/sender_relay"

# Config
EMAIL_DOMAINS_CONFIG = "/etc/vexo/email-domains.json"


def is_postfix_ready():
    """Check if Postfix is installed and running."""
    return is_installed("postfix") and is_service_running("postfix")


def get_postfix_setting(key):
    """Get a Postfix configuration value."""
    result = run_command(f"postconf -h {key} 2>/dev/null", check=False, silent=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def set_postfix_setting(key, value):
    """Set a Postfix configuration value."""
    result = run_command(f'postconf -e "{key}={value}"', check=False, silent=True)
    return result.returncode == 0


def set_postfix_settings(settings):
    """Set multiple Postfix settings."""
    for key, value in settings.items():
        if not set_postfix_setting(key, value):
            return False
    return True


def get_postfix_mode():
    """Get current Postfix mode."""
    inet_interfaces = get_postfix_setting("inet_interfaces")
    if inet_interfaces == "loopback-only":
        return "send-only"
    elif inet_interfaces == "all":
        return "receive"
    return "unknown"


def reload_postfix():
    """Reload Postfix configuration."""
    from utils.shell import service_control
    return service_control("postfix", "reload")


def restart_postfix():
    """Restart Postfix service."""
    from utils.shell import service_control
    return service_control("postfix", "restart")


def load_domains_config():
    """Load email domains configuration."""
    if not os.path.exists(EMAIL_DOMAINS_CONFIG):
        return {}
    try:
        with open(EMAIL_DOMAINS_CONFIG, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_domains_config(config):
    """Save email domains configuration."""
    from modules.email.utils import ensure_config_dir
    ensure_config_dir()
    try:
        with open(EMAIL_DOMAINS_CONFIG, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except IOError:
        return False


def get_configured_domains():
    """Get list of configured email domains."""
    config = load_domains_config()
    return list(config.keys())


def validate_domain(domain):
    """Validate domain format."""
    if not domain or '.' not in domain:
        return False
    if domain.startswith('.') or domain.endswith('.'):
        return False
    return True
