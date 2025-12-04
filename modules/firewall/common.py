"""Common utilities for firewall module."""

import os
import re
from utils.shell import run_command, is_installed


# Config paths
VEXO_FIREWALL_DIR = "/etc/vexo/firewall"
VEXO_FIREWALL_BACKUPS = f"{VEXO_FIREWALL_DIR}/backups"
IP_GROUPS_FILE = f"{VEXO_FIREWALL_DIR}/ip-groups.json"
RATE_LIMITS_FILE = f"{VEXO_FIREWALL_DIR}/rate-limits.json"
SETTINGS_FILE = f"{VEXO_FIREWALL_DIR}/settings.json"


def is_ufw_installed():
    """Check if UFW is installed."""
    return is_installed("ufw")


def is_ufw_active():
    """Check if UFW is active."""
    if not is_ufw_installed():
        return False
    result = run_command("ufw status", check=False, silent=True)
    if result.returncode == 0:
        return "active" in result.stdout.lower() and "inactive" not in result.stdout.lower()
    return False


def get_ufw_status_text():
    """Get UFW status as formatted text."""
    if not is_ufw_installed():
        return "[dim]Not installed[/dim]"
    
    result = run_command("ufw status", check=False, silent=True)
    if result.returncode == 0:
        if "inactive" in result.stdout.lower():
            return "[yellow]Inactive[/yellow]"
        elif "active" in result.stdout.lower():
            return "[green]Active[/green]"
    return "[dim]Unknown[/dim]"


def get_ufw_rules():
    """Get list of UFW rules as list of dicts."""
    result = run_command("ufw status numbered", check=False, silent=True)
    if result.returncode != 0:
        return []
    
    rules = []
    for line in result.stdout.strip().split('\n'):
        if line.strip().startswith('['):
            match = re.match(r'\[\s*(\d+)\]\s+(.+)', line)
            if match:
                rules.append({
                    "number": int(match.group(1)),
                    "rule": match.group(2).strip()
                })
    return rules


def get_ufw_defaults():
    """Get UFW default policies."""
    result = run_command("ufw status verbose", check=False, silent=True)
    if result.returncode != 0:
        return {"incoming": "unknown", "outgoing": "unknown", "routed": "unknown"}
    
    defaults = {"incoming": "unknown", "outgoing": "unknown", "routed": "unknown"}
    
    for line in result.stdout.split('\n'):
        line_lower = line.lower()
        if "default:" in line_lower:
            if "deny (incoming)" in line_lower:
                defaults["incoming"] = "deny"
            elif "allow (incoming)" in line_lower:
                defaults["incoming"] = "allow"
            if "allow (outgoing)" in line_lower:
                defaults["outgoing"] = "allow"
            elif "deny (outgoing)" in line_lower:
                defaults["outgoing"] = "deny"
            if "disabled (routed)" in line_lower:
                defaults["routed"] = "disabled"
            elif "deny (routed)" in line_lower:
                defaults["routed"] = "deny"
    
    return defaults


def get_rule_count():
    """Get total number of UFW rules."""
    return len(get_ufw_rules())


def ensure_config_dir():
    """Ensure vexo firewall config directory exists."""
    os.makedirs(VEXO_FIREWALL_DIR, exist_ok=True)
    os.makedirs(VEXO_FIREWALL_BACKUPS, exist_ok=True)
