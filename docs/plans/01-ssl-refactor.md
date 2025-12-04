# Phase 1: SSL Package Refactor + Certificate Dashboard

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor monolithic ssl.py into organized ssl/ package with comprehensive certificate dashboard showing status, expiry, and alerts.

**Architecture:** Split ssl.py into common utilities, dashboard display. Dashboard parses certbot certificates and custom certs, displays status table with color-coded expiry warnings.

**Tech Stack:** Python, Rich (tables, panels), OpenSSL CLI, Certbot CLI

---

## Task 1: Create Package Structure

**Files:**
- Create: `modules/ssl/__init__.py`
- Create: `modules/ssl/common.py`

**Step 1: Create common.py with shared utilities**

```python
"""Common utilities for SSL certificate module."""

import os
import re
import json
import subprocess
from datetime import datetime, timedelta
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
    
    # Get certificate details using openssl
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
            # Extract CN
            cn_match = re.search(r'CN\s*=\s*([^,]+)', line)
            if cn_match:
                info["domains"].append(cn_match.group(1).strip())
        
        elif line.startswith("issuer="):
            info["issuer"] = line.split("=", 1)[1].strip()
            # Extract issuer CN/O
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
            # Parse SAN domains
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
    # Sort by days_left (most urgent first)
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
```

**Step 2: Create package __init__.py**

```python
"""SSL Certificate management module for vexo."""

from ui.menu import run_menu_loop
from modules.ssl.common import is_certbot_installed, get_certbot_status_text


def show_menu():
    """Display the SSL Certificates main menu."""
    from modules.ssl.dashboard import show_dashboard
    from modules.ssl.issue import show_issue_menu
    from modules.ssl.import_cert import show_import_menu
    from modules.ssl.manage import show_manage_menu
    from modules.ssl.dns_providers import show_dns_menu
    from modules.ssl.security import show_security_menu
    from modules.ssl.backup import show_backup_menu
    from modules.ssl.settings import show_settings_menu
    
    def get_status():
        return f"Certbot: {get_certbot_status_text()}"
    
    def get_options():
        options = [
            ("dashboard", "1. Dashboard"),
            ("issue", "2. Issue Certificate"),
            ("import", "3. Import Certificate"),
            ("manage", "4. Manage Certificates"),
            ("dns", "5. DNS Providers"),
            ("security", "6. Security Audit"),
            ("backup", "7. Backup & Restore"),
            ("settings", "8. Settings"),
            ("back", "← Back to Main Menu"),
        ]
        return options
    
    handlers = {
        "dashboard": show_dashboard,
        "issue": show_issue_menu,
        "import": show_import_menu,
        "manage": show_manage_menu,
        "dns": show_dns_menu,
        "security": show_security_menu,
        "backup": show_backup_menu,
        "settings": show_settings_menu,
    }
    
    run_menu_loop("SSL Certificates", get_options, handlers, get_status)
```

**Step 3: Commit**

```bash
git add modules/ssl/__init__.py modules/ssl/common.py
git commit -m "feat(ssl): create package structure with common utilities"
```

---

## Task 2: Create Certificate Dashboard

**Files:**
- Create: `modules/ssl/dashboard.py`

**Step 1: Create dashboard.py**

```python
"""SSL Certificate dashboard."""

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_success,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import select_from_list, confirm_action
from modules.ssl.common import (
    list_all_certificates,
    format_status,
    format_days_left,
    ALERT_WARNING,
    ALERT_CRITICAL,
)
from utils.shell import run_command


def show_dashboard():
    """Display SSL certificate dashboard."""
    clear_screen()
    show_header()
    
    certificates = list_all_certificates()
    
    # Calculate stats
    total = len(certificates)
    valid = sum(1 for c in certificates if c["status"] == "valid" or c["status"] == "notice")
    expiring = sum(1 for c in certificates if c["status"] in ("warning", "critical"))
    expired = sum(1 for c in certificates if c["status"] == "expired")
    
    # Summary panel
    summary = f"""[bold]Total:[/bold] {total}  │  [green]Valid:[/green] {valid}  │  [yellow]Expiring:[/yellow] {expiring}  │  [red]Expired:[/red] {expired}"""
    
    show_panel(summary, title="SSL Certificate Dashboard", style="cyan")
    
    if not certificates:
        console.print()
        show_info("No SSL certificates found.")
        console.print("[dim]Use 'Issue Certificate' to generate a new certificate.[/dim]")
        press_enter_to_continue()
        return
    
    # Certificate table
    console.print()
    
    columns = [
        {"name": "Domain", "style": "cyan"},
        {"name": "Status", "justify": "center"},
        {"name": "Days Left", "justify": "right"},
        {"name": "CA"},
        {"name": "Type"},
    ]
    
    rows = []
    for cert in certificates:
        rows.append([
            cert.get("name", "unknown")[:25],
            format_status(cert.get("status", "unknown")),
            format_days_left(cert.get("days_left", 0)),
            cert.get("ca", "unknown")[:15],
            cert.get("type", "unknown"),
        ])
    
    show_table("Certificates", columns, rows)
    
    # Alerts section
    alerts = _get_alerts(certificates)
    if alerts:
        console.print()
        console.print("[bold yellow]⚠ Alerts:[/bold yellow]")
        for alert in alerts[:5]:
            console.print(f"  {alert}")
        if len(alerts) > 5:
            console.print(f"  [dim]... and {len(alerts) - 5} more alerts[/dim]")
    
    # Next renewal check
    console.print()
    _show_renewal_info()
    
    # Actions
    console.print()
    action = select_from_list(
        title="Action",
        message="Quick actions:",
        options=[
            "Refresh",
            "Renew Expiring Certificates",
            "View Certificate Details",
            "Back to Menu"
        ]
    )
    
    if action == "Refresh":
        show_dashboard()
    elif action == "Renew Expiring Certificates":
        _renew_expiring(certificates)
    elif action == "View Certificate Details":
        _view_details(certificates)
    # else back to menu


def _get_alerts(certificates):
    """Generate alert messages for certificates."""
    alerts = []
    
    for cert in certificates:
        status = cert.get("status", "")
        name = cert.get("name", "unknown")
        days = cert.get("days_left", 0)
        
        if status == "expired":
            alerts.append(f"[red]• {name} has EXPIRED - immediate action required![/red]")
        elif status == "critical":
            alerts.append(f"[red]• {name} expires in {days} days - renew now![/red]")
        elif status == "warning":
            alerts.append(f"[yellow]• {name} expires in {days} days - renew soon[/yellow]")
    
    return alerts


def _show_renewal_info():
    """Show auto-renewal timer information."""
    result = run_command(
        "systemctl list-timers certbot.timer --no-pager 2>/dev/null | grep certbot",
        check=False,
        silent=True
    )
    
    if result.returncode == 0 and result.stdout.strip():
        # Parse next run time from output
        console.print(f"[dim]Auto-renewal: Active (via certbot.timer)[/dim]")
    else:
        console.print("[dim]Auto-renewal: Check certbot.timer or cron[/dim]")


def _renew_expiring(certificates):
    """Renew certificates that are expiring soon."""
    expiring = [c for c in certificates if c["status"] in ("warning", "critical") and c["source"] == "certbot"]
    
    if not expiring:
        show_info("No certbot certificates need renewal.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print("[bold]Certificates to renew:[/bold]")
    for cert in expiring:
        console.print(f"  • {cert['name']} ({cert['days_left']} days left)")
    console.print()
    
    if not confirm_action(f"Renew {len(expiring)} certificate(s)?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    from utils.shell import run_command_realtime, require_root
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    run_command_realtime("certbot renew", "Renewing certificates...")
    
    press_enter_to_continue()
    show_dashboard()


def _view_details(certificates):
    """View detailed info about a certificate."""
    if not certificates:
        return
    
    options = [f"{c['name']} ({c['status']})" for c in certificates]
    
    choice = select_from_list(
        title="Certificate",
        message="Select certificate:",
        options=options
    )
    
    if not choice:
        return
    
    # Find selected certificate
    idx = options.index(choice)
    cert = certificates[idx]
    
    clear_screen()
    show_header()
    
    show_panel(f"Certificate Details: {cert['name']}", title="SSL Certificate", style="cyan")
    
    console.print()
    console.print(f"[bold]Domain(s):[/bold]")
    for domain in cert.get("domains", []):
        console.print(f"  • {domain}")
    
    console.print()
    console.print(f"[bold]Status:[/bold] {format_status(cert.get('status', 'unknown'))}")
    console.print(f"[bold]Days Left:[/bold] {format_days_left(cert.get('days_left', 0))}")
    console.print(f"[bold]CA:[/bold] {cert.get('ca', 'unknown')}")
    console.print(f"[bold]Type:[/bold] {cert.get('type', 'unknown')}")
    console.print(f"[bold]Source:[/bold] {cert.get('source', 'unknown')}")
    
    if cert.get("not_before"):
        console.print(f"[bold]Valid From:[/bold] {cert['not_before'].strftime('%Y-%m-%d %H:%M')}")
    if cert.get("not_after"):
        console.print(f"[bold]Valid Until:[/bold] {cert['not_after'].strftime('%Y-%m-%d %H:%M')}")
    
    console.print(f"[bold]Path:[/bold] {cert.get('path', 'unknown')}")
    
    press_enter_to_continue()
    show_dashboard()
```

**Step 2: Commit**

```bash
git add modules/ssl/dashboard.py
git commit -m "feat(ssl): add certificate dashboard with status overview"
```

---

## Task 3: Create Placeholder Submodules

**Files:**
- Create: `modules/ssl/issue.py`
- Create: `modules/ssl/import_cert.py`
- Create: `modules/ssl/manage.py`
- Create: `modules/ssl/dns_providers.py`
- Create: `modules/ssl/security.py`
- Create: `modules/ssl/backup.py`
- Create: `modules/ssl/settings.py`

**Step 1: Create issue.py placeholder**

```python
"""Issue SSL certificates."""

from ui.components import (
    clear_screen, show_header, show_panel, show_info, press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.ssl.common import get_certbot_status_text


def show_issue_menu():
    """Display issue certificate submenu."""
    def get_status():
        return f"Certbot: {get_certbot_status_text()}"
    
    options = [
        ("single", "1. Single Domain"),
        ("san", "2. Multiple Domains (SAN)"),
        ("wildcard", "3. Wildcard Certificate"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "single": _placeholder,
        "san": _placeholder,
        "wildcard": _placeholder,
    }
    
    run_menu_loop("Issue Certificate", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Issue Certificate", style="cyan")
    show_info("This feature will be implemented in Phase 2.")
    press_enter_to_continue()
```

**Step 2: Create import_cert.py placeholder**

```python
"""Import custom SSL certificates."""

from ui.components import (
    clear_screen, show_header, show_panel, show_info, press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.ssl.common import get_certbot_status_text


def show_import_menu():
    """Display import certificate submenu."""
    def get_status():
        return f"Certbot: {get_certbot_status_text()}"
    
    options = [
        ("pem", "1. Upload PEM Files"),
        ("pfx", "2. Upload PFX/PKCS12"),
        ("paste", "3. Paste Certificate"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "pem": _placeholder,
        "pfx": _placeholder,
        "paste": _placeholder,
    }
    
    run_menu_loop("Import Certificate", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Import Certificate", style="cyan")
    show_info("This feature will be implemented in Phase 3.")
    press_enter_to_continue()
```

**Step 3: Create manage.py placeholder**

```python
"""Manage SSL certificates."""

from ui.components import (
    clear_screen, show_header, show_panel, show_info, press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.ssl.common import get_certbot_status_text


def show_manage_menu():
    """Display manage certificates submenu."""
    def get_status():
        return f"Certbot: {get_certbot_status_text()}"
    
    options = [
        ("details", "1. View Details"),
        ("renew", "2. Renew Certificate"),
        ("revoke", "3. Revoke Certificate"),
        ("delete", "4. Delete Certificate"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "details": _placeholder,
        "renew": _placeholder,
        "revoke": _placeholder,
        "delete": _placeholder,
    }
    
    run_menu_loop("Manage Certificates", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Manage Certificates", style="cyan")
    show_info("This feature will be implemented in Phase 4.")
    press_enter_to_continue()
```

**Step 4: Create dns_providers.py placeholder**

```python
"""DNS provider configuration for DNS-01 challenge."""

from ui.components import (
    clear_screen, show_header, show_panel, show_info, press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.ssl.common import get_certbot_status_text


def show_dns_menu():
    """Display DNS providers submenu."""
    def get_status():
        return f"Certbot: {get_certbot_status_text()}"
    
    options = [
        ("cloudflare", "1. Configure Cloudflare"),
        ("digitalocean", "2. Configure DigitalOcean"),
        ("route53", "3. Configure Route53"),
        ("manual", "4. Manual DNS"),
        ("test", "5. Test DNS API"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "cloudflare": _placeholder,
        "digitalocean": _placeholder,
        "route53": _placeholder,
        "manual": _placeholder,
        "test": _placeholder,
    }
    
    run_menu_loop("DNS Providers", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="DNS Providers", style="cyan")
    show_info("This feature will be implemented in Phase 5.")
    press_enter_to_continue()
```

**Step 5: Create security.py placeholder**

```python
"""SSL security audit."""

from ui.components import (
    clear_screen, show_header, show_panel, show_info, press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.ssl.common import get_certbot_status_text


def show_security_menu():
    """Display security audit submenu."""
    def get_status():
        return f"Certbot: {get_certbot_status_text()}"
    
    options = [
        ("quick", "1. Quick Check"),
        ("full", "2. Full SSL Audit"),
        ("headers", "3. Security Headers"),
        ("recommend", "4. Get Recommendations"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "quick": _placeholder,
        "full": _placeholder,
        "headers": _placeholder,
        "recommend": _placeholder,
    }
    
    run_menu_loop("Security Audit", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Security Audit", style="cyan")
    show_info("This feature will be implemented in Phase 6.")
    press_enter_to_continue()
```

**Step 6: Create backup.py placeholder**

```python
"""SSL certificate backup and restore."""

from ui.components import (
    clear_screen, show_header, show_panel, show_info, press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.ssl.common import get_certbot_status_text


def show_backup_menu():
    """Display backup and restore submenu."""
    def get_status():
        return f"Certbot: {get_certbot_status_text()}"
    
    options = [
        ("export_one", "1. Export Certificate"),
        ("export_all", "2. Export All"),
        ("restore", "3. Import/Restore"),
        ("schedule", "4. Scheduled Backups"),
        ("manage", "5. Manage Backups"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "export_one": _placeholder,
        "export_all": _placeholder,
        "restore": _placeholder,
        "schedule": _placeholder,
        "manage": _placeholder,
    }
    
    run_menu_loop("Backup & Restore", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Backup & Restore", style="cyan")
    show_info("This feature will be implemented in Phase 7.")
    press_enter_to_continue()
```

**Step 7: Create settings.py placeholder**

```python
"""SSL settings and alerts configuration."""

from ui.components import (
    clear_screen, show_header, show_panel, show_info, press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.ssl.common import get_certbot_status_text


def show_settings_menu():
    """Display settings submenu."""
    def get_status():
        return f"Certbot: {get_certbot_status_text()}"
    
    options = [
        ("ca", "1. Default CA"),
        ("alerts", "2. Alert Settings"),
        ("renewal", "3. Auto-Renewal Config"),
        ("monitor", "4. Monitoring Schedule"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "ca": _placeholder,
        "alerts": _placeholder,
        "renewal": _placeholder,
        "monitor": _placeholder,
    }
    
    run_menu_loop("Settings", options, handlers, get_status)


def _placeholder():
    """Placeholder for future implementation."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Settings", style="cyan")
    show_info("This feature will be implemented in Phase 8.")
    press_enter_to_continue()
```

**Step 8: Commit**

```bash
git add modules/ssl/issue.py modules/ssl/import_cert.py modules/ssl/manage.py modules/ssl/dns_providers.py modules/ssl/security.py modules/ssl/backup.py modules/ssl/settings.py
git commit -m "feat(ssl): add placeholder submodules for all features"
```

---

## Task 4: Update Main Module Import

**Files:**
- Modify: `main.py` (verify import works)

**Step 1: Verify import works**

The import `from modules import ssl` should now work since we have `modules/ssl/__init__.py`.

**Step 2: Remove old ssl.py**

```bash
rm modules/ssl.py
```

**Step 3: Commit**

```bash
git add -A
git commit -m "refactor(ssl): complete migration to package structure

- Remove old monolithic ssl.py
- Package provides dashboard and all submenus
- All features accessible from main menu"
```

---

## Verification

After completing all tasks, verify:

1. **Menu loads correctly:**
   - Main menu shows "SSL Certificates" option
   - SSL submenu shows all 8 options
   - Dashboard displays certificate overview

2. **Dashboard works:**
   - Shows certificate count stats
   - Lists all certbot certificates
   - Color-coded status and days left
   - Alerts for expiring certificates

3. **All submenus accessible:**
   - Issue Certificate → shows placeholder
   - Import Certificate → shows placeholder
   - Manage Certificates → shows placeholder
   - DNS Providers → shows placeholder
   - Security Audit → shows placeholder
   - Backup & Restore → shows placeholder
   - Settings → shows placeholder
