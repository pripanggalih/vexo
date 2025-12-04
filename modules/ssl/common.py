"""Common utilities for SSL certificate module."""

import os
import re
import json
from datetime import datetime
from typing import Optional, Dict, List, Any

from utils.shell import run_command, is_installed


# Config paths
VEXO_SSL_DIR = "/etc/vexo/ssl"
VEXO_SSL_CERTS = f"{VEXO_SSL_DIR}/certs"
VEXO_SSL_DNS = f"{VEXO_SSL_DIR}/dns"
VEXO_SSL_BACKUPS = f"{VEXO_SSL_DIR}/backups"
CERTIFICATES_FILE = f"{VEXO_SSL_DIR}/certificates.json"
SETTINGS_FILE = f"{VEXO_SSL_DIR}/settings.json"
ALERTS_FILE = f"{VEXO_SSL_DIR}/alerts.json"
HISTORY_LOG = f"{VEXO_SSL_DIR}/history.log"

# Let's Encrypt paths
LETSENCRYPT_LIVE = "/etc/letsencrypt/live"
LETSENCRYPT_RENEWAL = "/etc/letsencrypt/renewal"

# Alert thresholds (days)
ALERT_CRITICAL = 7
ALERT_WARNING = 14
ALERT_NOTICE = 30


def ensure_config_dir():
    """Ensure vexo SSL config directories exist."""
    for directory in [VEXO_SSL_DIR, VEXO_SSL_CERTS, VEXO_SSL_DNS, VEXO_SSL_BACKUPS]:
        os.makedirs(directory, exist_ok=True)


def is_certbot_installed():
    """Check if certbot is installed."""
    return is_installed("certbot")


def get_certbot_status_text():
    """Get certbot status for display."""
    if not is_certbot_installed():
        return "[dim]Not installed[/dim]"
    return "[green]Installed[/green]"


def parse_certificate(cert_path: str) -> Optional[Dict[str, Any]]:
    """
    Parse certificate file and extract information.
    
    Args:
        cert_path: Path to certificate file (PEM format)
    
    Returns:
        Dict with certificate info or None if failed
    """
    if not os.path.exists(cert_path):
        return None
    
    result = run_command(
        f"openssl x509 -in {cert_path} -noout -subject -issuer -dates -ext subjectAltName 2>/dev/null",
        check=False,
        silent=True
    )
    
    if result.returncode != 0:
        return None
    
    info = {
        "path": cert_path,
        "subject": "",
        "issuer": "",
        "not_before": None,
        "not_after": None,
        "domains": [],
        "days_left": 0,
        "status": "unknown"
    }
    
    for line in result.stdout.split('\n'):
        line = line.strip()
        
        if line.startswith("subject="):
            info["subject"] = line.split("=", 1)[1].strip()
            cn_match = re.search(r'CN\s*=\s*([^,]+)', line)
            if cn_match:
                info["domains"].append(cn_match.group(1).strip())
        
        elif line.startswith("issuer="):
            info["issuer"] = line.split("=", 1)[1].strip()
            org_match = re.search(r'O\s*=\s*([^,]+)', line)
            if org_match:
                info["issuer"] = org_match.group(1).strip()
        
        elif line.startswith("notBefore="):
            date_str = line.split("=", 1)[1].strip()
            try:
                info["not_before"] = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
            except ValueError:
                pass
        
        elif line.startswith("notAfter="):
            date_str = line.split("=", 1)[1].strip()
            try:
                info["not_after"] = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
            except ValueError:
                pass
        
        elif "DNS:" in line:
            dns_matches = re.findall(r'DNS:([^,\s]+)', line)
            for dns in dns_matches:
                if dns not in info["domains"]:
                    info["domains"].append(dns)
    
    # Calculate days left and status
    if info["not_after"]:
        delta = info["not_after"] - datetime.now()
        info["days_left"] = delta.days
        
        if info["days_left"] < 0:
            info["status"] = "expired"
        elif info["days_left"] <= ALERT_CRITICAL:
            info["status"] = "critical"
        elif info["days_left"] <= ALERT_WARNING:
            info["status"] = "warning"
        elif info["days_left"] <= ALERT_NOTICE:
            info["status"] = "notice"
        else:
            info["status"] = "valid"
    
    return info


def get_certificate_type(cert_info: Dict) -> str:
    """Determine certificate type (single, SAN, wildcard)."""
    domains = cert_info.get("domains", [])
    
    if not domains:
        return "unknown"
    
    has_wildcard = any(d.startswith("*.") for d in domains)
    
    if has_wildcard:
        return "wildcard"
    elif len(domains) > 1:
        return "SAN"
    else:
        return "single"


def get_ca_name(issuer: str) -> str:
    """Extract CA name from issuer string."""
    issuer_lower = issuer.lower()
    
    if "let's encrypt" in issuer_lower or "letsencrypt" in issuer_lower:
        return "Let's Encrypt"
    elif "zerossl" in issuer_lower:
        return "ZeroSSL"
    elif "buypass" in issuer_lower:
        return "Buypass"
    elif "digicert" in issuer_lower:
        return "DigiCert"
    elif "comodo" in issuer_lower or "sectigo" in issuer_lower:
        return "Sectigo"
    elif "globalsign" in issuer_lower:
        return "GlobalSign"
    else:
        return issuer[:20] if len(issuer) > 20 else issuer


def list_certbot_certificates() -> List[Dict]:
    """List all certificates managed by certbot."""
    certificates = []
    
    if not os.path.exists(LETSENCRYPT_LIVE):
        return certificates
    
    for domain in os.listdir(LETSENCRYPT_LIVE):
        cert_path = os.path.join(LETSENCRYPT_LIVE, domain, "fullchain.pem")
        
        if os.path.exists(cert_path):
            cert_info = parse_certificate(cert_path)
            if cert_info:
                cert_info["name"] = domain
                cert_info["source"] = "certbot"
                cert_info["type"] = get_certificate_type(cert_info)
                cert_info["ca"] = get_ca_name(cert_info.get("issuer", ""))
                certificates.append(cert_info)
    
    return certificates


def list_custom_certificates() -> List[Dict]:
    """List all custom imported certificates."""
    certificates = []
    
    if not os.path.exists(VEXO_SSL_CERTS):
        return certificates
    
    for domain in os.listdir(VEXO_SSL_CERTS):
        domain_dir = os.path.join(VEXO_SSL_CERTS, domain)
        cert_path = os.path.join(domain_dir, "fullchain.pem")
        
        if os.path.isdir(domain_dir) and os.path.exists(cert_path):
            cert_info = parse_certificate(cert_path)
            if cert_info:
                cert_info["name"] = domain
                cert_info["source"] = "custom"
                cert_info["type"] = get_certificate_type(cert_info)
                cert_info["ca"] = get_ca_name(cert_info.get("issuer", ""))
                certificates.append(cert_info)
    
    return certificates


def list_all_certificates() -> List[Dict]:
    """List all certificates (certbot + custom)."""
    certs = list_certbot_certificates() + list_custom_certificates()
    return sorted(certs, key=lambda x: x.get("days_left", 999))


def format_status(status: str) -> str:
    """Format status with color."""
    status_colors = {
        "valid": "[green]Valid[/green]",
        "notice": "[cyan]Valid[/cyan]",
        "warning": "[yellow]Expiring[/yellow]",
        "critical": "[red]Critical[/red]",
        "expired": "[red bold]Expired[/red bold]",
        "unknown": "[dim]Unknown[/dim]"
    }
    return status_colors.get(status, status)


def format_days_left(days: int) -> str:
    """Format days left with color."""
    if days < 0:
        return f"[red bold]{days} days[/red bold]"
    elif days <= ALERT_CRITICAL:
        return f"[red]{days} days[/red]"
    elif days <= ALERT_WARNING:
        return f"[yellow]{days} days[/yellow]"
    elif days <= ALERT_NOTICE:
        return f"[cyan]{days} days[/cyan]"
    else:
        return f"[green]{days} days[/green]"


def log_event(domain: str, event: str, details: str = ""):
    """Log certificate event to history."""
    ensure_config_dir()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} | {domain} | {event} | {details}\n"
    
    with open(HISTORY_LOG, "a") as f:
        f.write(log_line)


# Certificate Authorities
CERTIFICATE_AUTHORITIES = {
    "letsencrypt": {
        "name": "Let's Encrypt",
        "server": None,
        "validity": 90,
        "description": "Free, 90 days, widely trusted"
    },
    "letsencrypt_staging": {
        "name": "Let's Encrypt (Staging)",
        "server": "https://acme-staging-v02.api.letsencrypt.org/directory",
        "validity": 90,
        "description": "Testing only, not trusted"
    },
    "zerossl": {
        "name": "ZeroSSL",
        "server": "https://acme.zerossl.com/v2/DV90",
        "validity": 90,
        "description": "Free, 90 days, alternative to LE"
    },
    "buypass": {
        "name": "Buypass",
        "server": "https://api.buypass.com/acme/directory",
        "validity": 180,
        "description": "Free, 180 days, longer validity"
    }
}


def get_default_ca():
    """Get default CA from settings."""
    settings = load_settings()
    return settings.get("default_ca", "letsencrypt")


def load_settings():
    """Load SSL settings."""
    if not os.path.exists(SETTINGS_FILE):
        return {"default_ca": "letsencrypt"}
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"default_ca": "letsencrypt"}


def save_settings(settings):
    """Save SSL settings."""
    ensure_config_dir()
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)


def run_preflight_checks(domains):
    """
    Run pre-flight checks before issuing certificate.
    
    Returns:
        tuple: (success: bool, messages: list)
    """
    messages = []
    success = True
    
    # Check nginx installed
    if not is_installed("nginx"):
        messages.append(("[red]✗[/red]", "Nginx is not installed"))
        success = False
    else:
        messages.append(("[green]✓[/green]", "Nginx is installed"))
    
    # Check nginx running
    result = run_command("systemctl is-active nginx", check=False, silent=True)
    if result.returncode == 0:
        messages.append(("[green]✓[/green]", "Nginx is running"))
    else:
        messages.append(("[yellow]![/yellow]", "Nginx is not running"))
    
    # Check port 80
    result = run_command("ss -tlnp | grep ':80 '", check=False, silent=True)
    if result.returncode == 0:
        messages.append(("[green]✓[/green]", "Port 80 is listening"))
    else:
        messages.append(("[red]✗[/red]", "Port 80 is not listening"))
        success = False
    
    # Check DNS for each domain
    import socket
    server_ip = _get_server_ip()
    
    for domain in domains:
        try:
            resolved_ip = socket.gethostbyname(domain)
            if resolved_ip == server_ip:
                messages.append(("[green]✓[/green]", f"DNS {domain} -> {resolved_ip} (correct)"))
            else:
                messages.append(("[yellow]![/yellow]", f"DNS {domain} -> {resolved_ip} (expected {server_ip})"))
        except socket.gaierror:
            messages.append(("[red]✗[/red]", f"DNS {domain} - cannot resolve"))
            success = False
    
    return success, messages


def _get_server_ip():
    """Get server's public IP."""
    result = run_command("curl -s ifconfig.me", check=False, silent=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return "unknown"
