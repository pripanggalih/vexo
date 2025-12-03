"""Shared utilities for webserver module."""

import os
import re
import json

from config import NGINX_SITES_AVAILABLE, NGINX_SITES_ENABLED, DEFAULT_WEB_ROOT, TEMPLATES_DIR

# Site type presets
SITE_TYPES = [
    ("laravel", "Laravel/PHP Application"),
    ("wordpress", "WordPress"),
    ("static", "Static HTML"),
    ("spa", "SPA (React/Vue/Angular)"),
    ("nodejs", "Node.js/Proxy"),
    ("custom", "Custom Configuration"),
]

# Default site configuration
DEFAULT_SITE_CONFIG = {
    "site_type": "laravel",
    "php_version": "8.3",
    "ssl_enabled": False,
    "www_redirect": "none",
    "gzip_enabled": True,
    "cache_static": True,
    "security_headers": True,
    "rate_limit_enabled": False,
    "rate_limit_requests": 10,
    "ip_whitelist": [],
    "ip_blacklist": [],
    "proxy_port": 3000,
}

# Backup directory
NGINX_BACKUP_DIR = "/etc/vexo/nginx-backups"


def get_site_config(domain):
    """Read site configuration from Nginx config file comments."""
    config = DEFAULT_SITE_CONFIG.copy()
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    
    if not os.path.exists(config_path):
        return config
    
    try:
        with open(config_path, "r") as f:
            content = f.read()
        match = re.search(r'# VEXO_CONFIG: ({.*})', content)
        if match:
            saved = json.loads(match.group(1))
            config.update(saved)
    except Exception:
        pass
    
    return config


def domain_to_safe_name(domain):
    """Convert domain to safe variable name for nginx."""
    return domain.replace(".", "_").replace("-", "_")


def is_valid_domain(domain):
    """Check if domain name is valid."""
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$'
    return bool(re.match(pattern, domain))


def get_configured_domains():
    """Get list of configured domains from sites-available."""
    try:
        if not os.path.exists(NGINX_SITES_AVAILABLE):
            return []
        
        domains = []
        for name in os.listdir(NGINX_SITES_AVAILABLE):
            if name in ["default", "default.conf", ".DS_Store"]:
                continue
            path = os.path.join(NGINX_SITES_AVAILABLE, name)
            if os.path.isfile(path):
                domains.append(name)
        
        return sorted(domains)
    except Exception:
        return []


def is_domain_enabled(domain):
    """Check if domain is enabled (has symlink in sites-enabled)."""
    enabled_path = os.path.join(NGINX_SITES_ENABLED, domain)
    return os.path.islink(enabled_path)


def get_domain_root(domain):
    """Get document root from domain config."""
    try:
        config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
        with open(config_path, "r") as f:
            for line in f:
                if "root " in line:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        return parts[1].rstrip(";")
        return None
    except Exception:
        return None
