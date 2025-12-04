# Webserver Enhancements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor webserver module to folder structure and add 7 new features: Backup/Restore, Clone Domain, Bulk Operations, Log Viewer, SSL Management, Traffic Stats, and enhanced Test/Reload.

**Architecture:** Split monolithic webserver.py (~1200 lines) into modules/webserver/ folder with separate files per feature group. Maintain backward compatibility via `__init__.py` exports.

**Tech Stack:** Python, Nginx, Certbot, standard Unix tools (tail, grep, awk)

---

## Task 1: Create Folder Structure and Move Core Functions

**Files:**
- Create: `modules/webserver/__init__.py`
- Create: `modules/webserver/nginx.py`
- Create: `modules/webserver/domains.py`
- Create: `modules/webserver/configure.py`
- Create: `modules/webserver/utils.py`
- Delete: `modules/webserver.py`

**Step 1: Create modules/webserver/ directory**

```bash
mkdir -p modules/webserver
```

**Step 2: Create utils.py with shared helpers**

```python
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
```

**Step 3: Create nginx.py with install/status/reload**

```python
"""Nginx installation and service management."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action
from utils.shell import (
    run_command, run_command_with_progress, is_installed,
    is_service_running, service_control, require_root,
)
from modules.webserver.utils import get_configured_domains


def install_nginx():
    """Install Nginx web server."""
    clear_screen()
    show_header()
    show_panel("Install Nginx", title="Domain & Nginx", style="cyan")
    
    if is_installed("nginx"):
        show_info("Nginx is already installed.")
        if not confirm_action("Do you want to reinstall Nginx?"):
            press_enter_to_continue()
            return
    
    if not confirm_action("Install Nginx web server?"):
        show_warning("Installation cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print()
    show_info("Installing Nginx...")
    
    result = run_command_with_progress("apt update", "Updating package lists...")
    if result.returncode != 0:
        show_error("Failed to update package lists.")
        press_enter_to_continue()
        return
    
    result = run_command_with_progress("apt install -y nginx", "Installing Nginx...")
    if result.returncode != 0:
        show_error("Failed to install Nginx.")
        press_enter_to_continue()
        return
    
    service_control("nginx", "start")
    service_control("nginx", "enable")
    
    console.print()
    if is_service_running("nginx"):
        show_success("Nginx installed and running!")
    else:
        show_warning("Nginx installed but may not be running.")
    
    press_enter_to_continue()


def show_nginx_status():
    """Display Nginx service status."""
    clear_screen()
    show_header()
    show_panel("Nginx Status", title="Domain & Nginx", style="cyan")
    
    if not is_installed("nginx"):
        show_warning("Nginx is not installed.")
        press_enter_to_continue()
        return
    
    running = is_service_running("nginx")
    
    columns = [
        {"name": "Property", "style": "cyan"},
        {"name": "Value"},
    ]
    
    rows = [
        ["Installed", "[green]Yes[/green]"],
        ["Running", "[green]Yes[/green]" if running else "[red]No[/red]"],
    ]
    
    result = run_command("nginx -v 2>&1", check=False, silent=True)
    if result.returncode == 0:
        version = result.stderr.strip() if result.stderr else result.stdout.strip()
        rows.append(["Version", version.replace("nginx version: ", "")])
    
    result = run_command("nginx -t 2>&1", check=False, silent=True)
    config_ok = result.returncode == 0
    rows.append(["Config Valid", "[green]Yes[/green]" if config_ok else "[red]No[/red]"])
    
    domains = get_configured_domains()
    rows.append(["Domains Configured", str(len(domains))])
    
    show_table("", columns, rows, show_header=False)
    
    if not config_ok:
        console.print()
        show_error("Configuration test failed:")
        console.print(f"[dim]{result.stderr}[/dim]")
    
    press_enter_to_continue()


def test_and_reload():
    """Test nginx config and reload if valid."""
    clear_screen()
    show_header()
    show_panel("Test & Reload Nginx", title="Domain & Nginx", style="cyan")
    
    show_info("Testing Nginx configuration...")
    console.print()
    
    result = run_command("nginx -t 2>&1", check=False, silent=True)
    
    if result.returncode != 0:
        show_error("Configuration test FAILED!")
        console.print()
        console.print(f"[red]{result.stderr}[/red]")
        press_enter_to_continue()
        return False
    
    show_success("Configuration test passed!")
    console.print()
    
    if not confirm_action("Reload Nginx now?"):
        press_enter_to_continue()
        return True
    
    success = service_control("nginx", "reload")
    
    if success:
        show_success("Nginx reloaded successfully!")
    else:
        show_error("Failed to reload Nginx.")
    
    press_enter_to_continue()
    return success


def reload_nginx(silent=False):
    """Reload Nginx configuration."""
    try:
        result = run_command("nginx -t", check=False, silent=True)
        if result.returncode != 0:
            if not silent:
                show_error("Nginx configuration test failed!")
                console.print(f"[dim]{result.stderr}[/dim]")
            return False
        
        success = service_control("nginx", "reload")
        
        if not silent:
            if success:
                show_success("Nginx reloaded successfully!")
            else:
                show_error("Failed to reload Nginx.")
            press_enter_to_continue()
        
        return success
    except Exception as e:
        if not silent:
            show_error(f"Error reloading Nginx: {e}")
            press_enter_to_continue()
        return False
```

**Step 4: Create domains.py** (add_domain, list_domains, remove_domain, enable_domain, generate_site_config - copy from original)

**Step 5: Create configure.py** (configure_site_menu and all configure_* functions - copy from original)

**Step 6: Create __init__.py with main menu**

```python
"""Domain & Nginx management module for vexo."""

from ui.menu import run_menu_loop
from utils.shell import is_installed

from modules.webserver.nginx import install_nginx, show_nginx_status, test_and_reload
from modules.webserver.domains import list_domains, add_domain_interactive, remove_domain_interactive
from modules.webserver.configure import configure_site_menu
from modules.webserver.backup import show_backup_menu
from modules.webserver.bulk import show_bulk_menu
from modules.webserver.logs import show_logs_menu
from modules.webserver.ssl import show_ssl_menu
from modules.webserver.stats import show_traffic_stats
from modules.webserver.clone import clone_domain


def show_menu():
    """Display the Domain & Nginx submenu."""
    def get_status():
        from utils.shell import is_service_running
        if not is_installed("nginx"):
            return "Nginx: [yellow]Not installed[/yellow]"
        if is_service_running("nginx"):
            return "Nginx: [green]Running[/green]"
        return "Nginx: [red]Stopped[/red]"
    
    def get_options():
        options = []
        if is_installed("nginx"):
            options.extend([
                ("list", "1. List Domains"),
                ("add", "2. Add Domain"),
                ("configure", "3. Configure Site"),
                ("remove", "4. Remove Domain"),
                ("backup", "5. Backup & Restore"),
                ("clone", "6. Clone Domain"),
                ("bulk", "7. Bulk Operations"),
                ("logs", "8. Log Viewer"),
                ("ssl", "9. SSL Management"),
                ("stats", "10. Traffic Stats"),
                ("reload", "11. Test & Reload"),
                ("status", "12. Nginx Status"),
            ])
        else:
            options.append(("install", "1. Install Nginx"))
        options.append(("back", "← Back to Main Menu"))
        return options
    
    handlers = {
        "install": install_nginx,
        "list": list_domains,
        "add": add_domain_interactive,
        "configure": configure_site_menu,
        "remove": remove_domain_interactive,
        "backup": show_backup_menu,
        "clone": clone_domain,
        "bulk": show_bulk_menu,
        "logs": show_logs_menu,
        "ssl": show_ssl_menu,
        "stats": show_traffic_stats,
        "reload": test_and_reload,
        "status": show_nginx_status,
    }
    
    run_menu_loop("Domain & Nginx Management", get_options, handlers, get_status)
```

**Step 7: Delete old webserver.py and commit**

```bash
rm modules/webserver.py
git add modules/webserver/
git commit -m "refactor(webserver): split into folder structure"
```

---

## Task 2: Implement Backup & Restore

**Files:**
- Create: `modules/webserver/backup.py`

**Step 1: Create backup.py**

```python
"""Backup and restore domain configurations."""

import os
import shutil
from datetime import datetime

from config import NGINX_SITES_AVAILABLE
from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, select_from_list, run_menu_loop
from utils.shell import run_command, require_root
from modules.webserver.utils import get_configured_domains, NGINX_BACKUP_DIR


def show_backup_menu():
    """Display Backup & Restore submenu."""
    options = [
        ("backup", "1. Backup Domain Config"),
        ("restore", "2. Restore Domain Config"),
        ("list", "3. List Backups"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "backup": backup_domain,
        "restore": restore_domain,
        "list": list_backups,
    }
    
    run_menu_loop("Backup & Restore", options, handlers)


def backup_domain():
    """Backup a domain configuration."""
    clear_screen()
    show_header()
    show_panel("Backup Domain Config", title="Backup & Restore", style="cyan")
    
    domains = get_configured_domains()
    if not domains:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    domain = select_from_list("Select Domain", "Choose domain to backup:", domains)
    if not domain:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    if not os.path.exists(config_path):
        show_error("Config file not found.")
        press_enter_to_continue()
        return
    
    # Create backup directory
    backup_dir = os.path.join(NGINX_BACKUP_DIR, domain)
    os.makedirs(backup_dir, exist_ok=True)
    
    # Create timestamped backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"{timestamp}.conf")
    
    shutil.copy2(config_path, backup_path)
    
    # Keep only last 5 backups
    backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.conf')], reverse=True)
    for old_backup in backups[5:]:
        os.remove(os.path.join(backup_dir, old_backup))
    
    show_success(f"Backup created: {backup_path}")
    press_enter_to_continue()


def restore_domain():
    """Restore a domain configuration from backup."""
    clear_screen()
    show_header()
    show_panel("Restore Domain Config", title="Backup & Restore", style="cyan")
    
    # Get domains with backups
    if not os.path.exists(NGINX_BACKUP_DIR):
        show_info("No backups found.")
        press_enter_to_continue()
        return
    
    domains_with_backups = [d for d in os.listdir(NGINX_BACKUP_DIR) 
                           if os.path.isdir(os.path.join(NGINX_BACKUP_DIR, d))]
    
    if not domains_with_backups:
        show_info("No backups found.")
        press_enter_to_continue()
        return
    
    domain = select_from_list("Select Domain", "Choose domain:", domains_with_backups)
    if not domain:
        return
    
    # List backups for domain
    backup_dir = os.path.join(NGINX_BACKUP_DIR, domain)
    backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.conf')], reverse=True)
    
    if not backups:
        show_info("No backups found for this domain.")
        press_enter_to_continue()
        return
    
    # Format backup options with timestamps
    backup_options = []
    for b in backups:
        ts = b.replace(".conf", "")
        try:
            dt = datetime.strptime(ts, "%Y%m%d_%H%M%S")
            formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            formatted = ts
        size = os.path.getsize(os.path.join(backup_dir, b))
        backup_options.append(f"{formatted} ({size/1024:.1f} KB)")
    
    choice = select_from_list("Select Backup", "Choose backup to restore:", backup_options)
    if not choice:
        return
    
    # Map choice back to filename
    idx = backup_options.index(choice)
    backup_file = backups[idx]
    backup_path = os.path.join(backup_dir, backup_file)
    
    if not confirm_action(f"Restore {domain} from {choice}?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    
    # Backup current before restore
    if os.path.exists(config_path):
        pre_restore = os.path.join(backup_dir, f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.conf")
        shutil.copy2(config_path, pre_restore)
    
    shutil.copy2(backup_path, config_path)
    
    # Test nginx config
    result = run_command("nginx -t", check=False, silent=True)
    if result.returncode != 0:
        show_error("Nginx config test failed after restore!")
        console.print(f"[dim]{result.stderr}[/dim]")
        press_enter_to_continue()
        return
    
    from modules.webserver.nginx import reload_nginx
    reload_nginx(silent=True)
    
    show_success(f"Config restored for {domain}!")
    press_enter_to_continue()


def list_backups():
    """List all backups."""
    clear_screen()
    show_header()
    show_panel("Backup List", title="Backup & Restore", style="cyan")
    
    if not os.path.exists(NGINX_BACKUP_DIR):
        show_info("No backups found.")
        press_enter_to_continue()
        return
    
    domains = [d for d in os.listdir(NGINX_BACKUP_DIR) 
               if os.path.isdir(os.path.join(NGINX_BACKUP_DIR, d))]
    
    if not domains:
        show_info("No backups found.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Domain", "style": "cyan"},
        {"name": "Backups", "justify": "center"},
        {"name": "Latest", "style": "white"},
        {"name": "Size", "justify": "right"},
    ]
    
    rows = []
    for domain in sorted(domains):
        backup_dir = os.path.join(NGINX_BACKUP_DIR, domain)
        backups = [f for f in os.listdir(backup_dir) if f.endswith('.conf')]
        
        if not backups:
            continue
        
        latest = sorted(backups, reverse=True)[0]
        try:
            ts = latest.replace(".conf", "")
            dt = datetime.strptime(ts, "%Y%m%d_%H%M%S")
            latest_str = dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            latest_str = latest
        
        total_size = sum(os.path.getsize(os.path.join(backup_dir, f)) for f in backups)
        
        rows.append([domain, str(len(backups)), latest_str, f"{total_size/1024:.1f} KB"])
    
    if rows:
        show_table("", columns, rows, show_header=True)
    else:
        show_info("No backups found.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/webserver/backup.py
git commit -m "feat(webserver): add backup and restore functionality"
```

---

## Task 3: Implement Clone Domain

**Files:**
- Create: `modules/webserver/clone.py`

**Step 1: Create clone.py**

```python
"""Clone domain configuration."""

import os
import re

from config import NGINX_SITES_AVAILABLE, DEFAULT_WEB_ROOT
from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list
from utils.shell import run_command, require_root
from modules.webserver.utils import get_configured_domains, is_valid_domain, get_site_config
from modules.webserver.domains import enable_domain


def clone_domain():
    """Clone a domain configuration to a new domain."""
    clear_screen()
    show_header()
    show_panel("Clone Domain", title="Domain & Nginx", style="cyan")
    
    domains = get_configured_domains()
    if not domains:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    # Select source domain
    source = select_from_list("Source Domain", "Choose domain to clone:", domains)
    if not source:
        return
    
    # Enter new domain name
    console.print()
    new_domain = text_input("Enter new domain name:")
    if not new_domain:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    new_domain = new_domain.strip().lower()
    
    if not is_valid_domain(new_domain):
        show_error(f"Invalid domain name: {new_domain}")
        press_enter_to_continue()
        return
    
    if new_domain in domains:
        show_error(f"Domain {new_domain} already exists.")
        press_enter_to_continue()
        return
    
    # Options
    console.print()
    create_dir = confirm_action("Create directory structure?")
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Read source config
    source_path = os.path.join(NGINX_SITES_AVAILABLE, source)
    try:
        with open(source_path, "r") as f:
            config_content = f.read()
    except Exception as e:
        show_error(f"Failed to read source config: {e}")
        press_enter_to_continue()
        return
    
    # Replace domain name in config
    new_config = config_content.replace(source, new_domain)
    
    # Update root path if present
    old_root = os.path.join(DEFAULT_WEB_ROOT, source)
    new_root = os.path.join(DEFAULT_WEB_ROOT, new_domain)
    new_config = new_config.replace(old_root, new_root)
    
    # Write new config
    new_path = os.path.join(NGINX_SITES_AVAILABLE, new_domain)
    try:
        with open(new_path, "w") as f:
            f.write(new_config)
    except Exception as e:
        show_error(f"Failed to write config: {e}")
        press_enter_to_continue()
        return
    
    # Create directory if requested
    if create_dir:
        config = get_site_config(source)
        if config.get("site_type") in ["static", "spa"]:
            new_doc_root = os.path.join(new_root, "dist")
        else:
            new_doc_root = os.path.join(new_root, "public")
        
        os.makedirs(new_doc_root, exist_ok=True)
        
        # Create placeholder index
        index_path = os.path.join(new_doc_root, "index.html")
        with open(index_path, "w") as f:
            f.write(f"<!DOCTYPE html>\n<html><body><h1>Welcome to {new_domain}</h1></body></html>\n")
        
        show_success(f"Created: {new_doc_root}")
    
    # Enable domain
    if enable_domain(new_domain):
        show_success(f"Domain {new_domain} cloned from {source}!")
        console.print()
        show_warning("SSL certificate not copied - run certbot for new domain.")
    else:
        show_error("Failed to enable domain.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/webserver/clone.py
git commit -m "feat(webserver): add clone domain functionality"
```

---

## Task 4: Implement Bulk Operations

**Files:**
- Create: `modules/webserver/bulk.py`

**Step 1: Create bulk.py**

```python
"""Bulk operations for domains."""

import os

from config import NGINX_SITES_AVAILABLE, NGINX_SITES_ENABLED
from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, run_menu_loop
from utils.shell import run_command, require_root
from modules.webserver.utils import get_configured_domains, is_domain_enabled
from modules.webserver.nginx import reload_nginx

try:
    from InquirerPy import inquirer
    from InquirerPy.base.control import Choice
    HAS_INQUIRER = True
except ImportError:
    HAS_INQUIRER = False


def show_bulk_menu():
    """Display Bulk Operations submenu."""
    options = [
        ("enable", "1. Enable Multiple Domains"),
        ("disable", "2. Disable Multiple Domains"),
        ("remove", "3. Remove Multiple Domains"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "enable": bulk_enable,
        "disable": bulk_disable,
        "remove": bulk_remove,
    }
    
    run_menu_loop("Bulk Operations", options, handlers)


def _select_multiple(message, options):
    """Select multiple items using checkbox."""
    if not HAS_INQUIRER or not options:
        return []
    
    choices = [Choice(value=opt, name=opt) for opt in options]
    
    try:
        result = inquirer.checkbox(
            message=message,
            choices=choices,
            cycle=True,
        ).execute()
        return result or []
    except KeyboardInterrupt:
        return []


def bulk_enable():
    """Enable multiple disabled domains."""
    clear_screen()
    show_header()
    show_panel("Enable Multiple Domains", title="Bulk Operations", style="cyan")
    
    domains = get_configured_domains()
    disabled = [d for d in domains if not is_domain_enabled(d)]
    
    if not disabled:
        show_info("No disabled domains found.")
        press_enter_to_continue()
        return
    
    selected = _select_multiple("Select domains to enable:", disabled)
    
    if not selected:
        show_warning("No domains selected.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success_count = 0
    for domain in selected:
        source = os.path.join(NGINX_SITES_AVAILABLE, domain)
        target = os.path.join(NGINX_SITES_ENABLED, domain)
        
        try:
            if os.path.islink(target):
                os.remove(target)
            os.symlink(source, target)
            success_count += 1
            console.print(f"[green]✓[/green] Enabled: {domain}")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed: {domain} - {e}")
    
    # Test and reload
    result = run_command("nginx -t", check=False, silent=True)
    if result.returncode == 0:
        reload_nginx(silent=True)
        show_success(f"Enabled {success_count} domain(s)!")
    else:
        show_error("Nginx config test failed!")
        console.print(f"[dim]{result.stderr}[/dim]")
    
    press_enter_to_continue()


def bulk_disable():
    """Disable multiple enabled domains."""
    clear_screen()
    show_header()
    show_panel("Disable Multiple Domains", title="Bulk Operations", style="cyan")
    
    domains = get_configured_domains()
    enabled = [d for d in domains if is_domain_enabled(d)]
    
    if not enabled:
        show_info("No enabled domains found.")
        press_enter_to_continue()
        return
    
    show_warning("Disabled sites will be inaccessible!")
    console.print()
    
    selected = _select_multiple("Select domains to disable:", enabled)
    
    if not selected:
        show_warning("No domains selected.")
        press_enter_to_continue()
        return
    
    if not confirm_action(f"Disable {len(selected)} domain(s)?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success_count = 0
    for domain in selected:
        target = os.path.join(NGINX_SITES_ENABLED, domain)
        
        try:
            if os.path.islink(target):
                os.remove(target)
                success_count += 1
                console.print(f"[yellow]○[/yellow] Disabled: {domain}")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed: {domain} - {e}")
    
    reload_nginx(silent=True)
    show_success(f"Disabled {success_count} domain(s)!")
    press_enter_to_continue()


def bulk_remove():
    """Remove multiple domains."""
    clear_screen()
    show_header()
    show_panel("Remove Multiple Domains", title="Bulk Operations", style="red")
    
    domains = get_configured_domains()
    
    if not domains:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    show_warning("⚠️  This will DELETE domain configurations!")
    console.print()
    
    selected = _select_multiple("Select domains to REMOVE:", domains)
    
    if not selected:
        show_warning("No domains selected.")
        press_enter_to_continue()
        return
    
    # Double confirmation
    console.print()
    console.print(f"[bold red]Type 'DELETE' to confirm removal of {len(selected)} domain(s):[/bold red]")
    confirm_text = text_input("Confirm:")
    
    if confirm_text != "DELETE":
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success_count = 0
    for domain in selected:
        try:
            # Remove from sites-enabled
            enabled_path = os.path.join(NGINX_SITES_ENABLED, domain)
            if os.path.islink(enabled_path):
                os.remove(enabled_path)
            
            # Remove from sites-available
            available_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
            if os.path.exists(available_path):
                os.remove(available_path)
            
            success_count += 1
            console.print(f"[red]✗[/red] Removed: {domain}")
        except Exception as e:
            console.print(f"[red]![/red] Failed: {domain} - {e}")
    
    reload_nginx(silent=True)
    show_success(f"Removed {success_count} domain(s)!")
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/webserver/bulk.py
git commit -m "feat(webserver): add bulk operations"
```

---

## Task 5: Implement Log Viewer

**Files:**
- Create: `modules/webserver/logs.py`

**Step 1: Create logs.py**

```python
"""Log viewer for nginx access and error logs."""

import os

from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import text_input, select_from_list, run_menu_loop
from utils.shell import run_command
from modules.webserver.utils import get_configured_domains


NGINX_LOG_DIR = "/var/log/nginx"


def show_logs_menu():
    """Display Log Viewer submenu."""
    options = [
        ("access", "1. View Access Log"),
        ("error", "2. View Error Log"),
        ("search", "3. Search Logs"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "access": view_access_log,
        "error": view_error_log,
        "search": search_logs,
    }
    
    run_menu_loop("Log Viewer", options, handlers)


def _get_log_path(domain, log_type="access"):
    """Get log file path for domain."""
    # Try domain-specific log first
    specific = os.path.join(NGINX_LOG_DIR, f"{domain}.{log_type}.log")
    if os.path.exists(specific):
        return specific
    
    # Fall back to default nginx logs
    default = os.path.join(NGINX_LOG_DIR, f"{log_type}.log")
    if os.path.exists(default):
        return default
    
    return None


def view_access_log():
    """View access log for a domain."""
    clear_screen()
    show_header()
    show_panel("Access Log", title="Log Viewer", style="cyan")
    
    domains = get_configured_domains()
    domains.insert(0, "(All - default nginx log)")
    
    domain = select_from_list("Select Domain", "Choose domain:", domains)
    if not domain:
        return
    
    if domain == "(All - default nginx log)":
        log_path = os.path.join(NGINX_LOG_DIR, "access.log")
    else:
        log_path = _get_log_path(domain, "access")
    
    if not log_path or not os.path.exists(log_path):
        show_error("Log file not found.")
        press_enter_to_continue()
        return
    
    console.print(f"[dim]Log: {log_path}[/dim]")
    console.print(f"[dim]Showing last 50 lines (Ctrl+C to exit)[/dim]")
    console.print()
    
    result = run_command(f"tail -n 50 {log_path}", check=False, silent=True)
    if result.returncode == 0:
        console.print(result.stdout)
    else:
        show_error("Failed to read log file.")
    
    press_enter_to_continue()


def view_error_log():
    """View error log for a domain."""
    clear_screen()
    show_header()
    show_panel("Error Log", title="Log Viewer", style="cyan")
    
    domains = get_configured_domains()
    domains.insert(0, "(All - default nginx log)")
    
    domain = select_from_list("Select Domain", "Choose domain:", domains)
    if not domain:
        return
    
    if domain == "(All - default nginx log)":
        log_path = os.path.join(NGINX_LOG_DIR, "error.log")
    else:
        log_path = _get_log_path(domain, "error")
    
    if not log_path or not os.path.exists(log_path):
        show_error("Log file not found.")
        press_enter_to_continue()
        return
    
    console.print(f"[dim]Log: {log_path}[/dim]")
    console.print(f"[dim]Showing last 50 lines[/dim]")
    console.print()
    
    result = run_command(f"tail -n 50 {log_path}", check=False, silent=True)
    if result.returncode == 0:
        # Highlight error levels
        for line in result.stdout.split('\n'):
            if 'error' in line.lower() or 'crit' in line.lower():
                console.print(f"[red]{line}[/red]")
            elif 'warn' in line.lower():
                console.print(f"[yellow]{line}[/yellow]")
            else:
                console.print(line)
    else:
        show_error("Failed to read log file.")
    
    press_enter_to_continue()


def search_logs():
    """Search logs for a pattern."""
    clear_screen()
    show_header()
    show_panel("Search Logs", title="Log Viewer", style="cyan")
    
    pattern = text_input("Enter search pattern (IP, URL, status code):")
    if not pattern:
        return
    
    domains = get_configured_domains()
    domains.insert(0, "(All - default nginx logs)")
    
    domain = select_from_list("Select Domain", "Choose domain:", domains)
    if not domain:
        return
    
    if domain == "(All - default nginx logs)":
        access_log = os.path.join(NGINX_LOG_DIR, "access.log")
        error_log = os.path.join(NGINX_LOG_DIR, "error.log")
    else:
        access_log = _get_log_path(domain, "access")
        error_log = _get_log_path(domain, "error")
    
    console.print()
    console.print(f"[bold]Searching for: {pattern}[/bold]")
    console.print()
    
    found = False
    
    if access_log and os.path.exists(access_log):
        result = run_command(f"grep -i '{pattern}' {access_log} | tail -n 20", check=False, silent=True)
        if result.returncode == 0 and result.stdout.strip():
            console.print("[cyan]Access Log:[/cyan]")
            console.print(result.stdout)
            found = True
    
    if error_log and os.path.exists(error_log):
        result = run_command(f"grep -i '{pattern}' {error_log} | tail -n 20", check=False, silent=True)
        if result.returncode == 0 and result.stdout.strip():
            console.print()
            console.print("[cyan]Error Log:[/cyan]")
            console.print(result.stdout)
            found = True
    
    if not found:
        show_info("No matches found.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/webserver/logs.py
git commit -m "feat(webserver): add log viewer"
```

---

## Task 6: Implement SSL Management

**Files:**
- Create: `modules/webserver/ssl.py`

**Step 1: Create ssl.py**

```python
"""SSL certificate management."""

import os
from datetime import datetime

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, select_from_list, run_menu_loop
from utils.shell import run_command, run_command_realtime, is_installed, require_root
from modules.webserver.utils import get_configured_domains


def show_ssl_menu():
    """Display SSL Management submenu."""
    def get_status():
        if is_installed("certbot"):
            return "Certbot: [green]Installed[/green]"
        return "Certbot: [yellow]Not installed[/yellow]"
    
    options = [
        ("view", "1. View Certificate Info"),
        ("status", "2. Check Auto-Renew Status"),
        ("renew", "3. Manual Renew"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "view": view_certificate,
        "status": check_autorenew,
        "renew": manual_renew,
    }
    
    run_menu_loop("SSL Management", options, handlers, get_status)


def view_certificate():
    """View SSL certificate details for a domain."""
    clear_screen()
    show_header()
    show_panel("Certificate Info", title="SSL Management", style="cyan")
    
    domains = get_configured_domains()
    if not domains:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    domain = select_from_list("Select Domain", "Choose domain:", domains)
    if not domain:
        return
    
    cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
    
    if not os.path.exists(cert_path):
        show_warning(f"No SSL certificate found for {domain}")
        press_enter_to_continue()
        return
    
    # Get certificate info using openssl
    result = run_command(
        f"openssl x509 -in {cert_path} -noout -subject -issuer -dates",
        check=False, silent=True
    )
    
    if result.returncode != 0:
        show_error("Failed to read certificate.")
        press_enter_to_continue()
        return
    
    console.print(f"[bold cyan]Certificate for: {domain}[/bold cyan]")
    console.print()
    
    columns = [
        {"name": "Property", "style": "cyan"},
        {"name": "Value", "style": "white"},
    ]
    
    rows = []
    for line in result.stdout.strip().split('\n'):
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Parse dates
            if 'notBefore' in key or 'notAfter' in key:
                try:
                    dt = datetime.strptime(value, "%b %d %H:%M:%S %Y %Z")
                    value = dt.strftime("%Y-%m-%d %H:%M")
                    
                    if 'notAfter' in key:
                        days_left = (dt - datetime.now()).days
                        if days_left < 0:
                            value += f" [red](EXPIRED)[/red]"
                        elif days_left < 30:
                            value += f" [yellow]({days_left} days left)[/yellow]"
                        else:
                            value += f" [green]({days_left} days left)[/green]"
                except ValueError:
                    pass
            
            rows.append([key, value])
    
    show_table("", columns, rows, show_header=False)
    press_enter_to_continue()


def check_autorenew():
    """Check certbot auto-renew timer status."""
    clear_screen()
    show_header()
    show_panel("Auto-Renew Status", title="SSL Management", style="cyan")
    
    if not is_installed("certbot"):
        show_warning("Certbot is not installed.")
        press_enter_to_continue()
        return
    
    # Check timer status
    result = run_command("systemctl status certbot.timer", check=False, silent=True)
    
    if result.returncode == 0:
        show_success("Auto-renew timer is active!")
        console.print()
        console.print(result.stdout)
    else:
        show_warning("Auto-renew timer may not be running.")
        console.print()
        console.print(result.stdout if result.stdout else result.stderr)
    
    console.print()
    
    # List certificates
    result = run_command("certbot certificates 2>/dev/null", check=False, silent=True)
    if result.returncode == 0 and result.stdout.strip():
        console.print("[bold]Managed Certificates:[/bold]")
        console.print(result.stdout)
    
    press_enter_to_continue()


def manual_renew():
    """Manually renew SSL certificates."""
    clear_screen()
    show_header()
    show_panel("Manual Renew", title="SSL Management", style="cyan")
    
    if not is_installed("certbot"):
        show_error("Certbot is not installed.")
        press_enter_to_continue()
        return
    
    # Get list of certificates
    result = run_command("certbot certificates 2>/dev/null | grep 'Certificate Name' | awk '{print $3}'", check=False, silent=True)
    
    certs = [c.strip() for c in result.stdout.strip().split('\n') if c.strip()]
    
    if not certs:
        show_info("No certificates found.")
        press_enter_to_continue()
        return
    
    certs.insert(0, "(Renew All)")
    
    choice = select_from_list("Select Certificate", "Choose certificate to renew:", certs)
    if not choice:
        return
    
    if not confirm_action(f"Renew {'all certificates' if choice == '(Renew All)' else choice}?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print()
    
    if choice == "(Renew All)":
        run_command_realtime("certbot renew", "Renewing certificates...")
    else:
        run_command_realtime(f"certbot renew --cert-name {choice}", "Renewing certificate...")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/webserver/ssl.py
git commit -m "feat(webserver): add SSL management"
```

---

## Task 7: Implement Traffic Stats

**Files:**
- Create: `modules/webserver/stats.py`

**Step 1: Create stats.py**

```python
"""Traffic statistics from nginx access logs."""

import os
from collections import Counter

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_error, show_info, press_enter_to_continue,
)
from ui.menu import select_from_list
from utils.shell import run_command
from modules.webserver.utils import get_configured_domains


NGINX_LOG_DIR = "/var/log/nginx"


def show_traffic_stats():
    """Show traffic statistics for a domain."""
    clear_screen()
    show_header()
    show_panel("Traffic Stats", title="Domain & Nginx", style="cyan")
    
    domains = get_configured_domains()
    domains.insert(0, "(All - default nginx log)")
    
    domain = select_from_list("Select Domain", "Choose domain:", domains)
    if not domain:
        return
    
    # Time range
    ranges = ["Today", "Last 7 days", "Last 30 days", "All time"]
    time_range = select_from_list("Time Range", "Select time range:", ranges)
    if not time_range:
        return
    
    # Get log file
    if domain == "(All - default nginx log)":
        log_path = os.path.join(NGINX_LOG_DIR, "access.log")
    else:
        log_path = os.path.join(NGINX_LOG_DIR, f"{domain}.access.log")
        if not os.path.exists(log_path):
            log_path = os.path.join(NGINX_LOG_DIR, "access.log")
    
    if not os.path.exists(log_path):
        show_error("Log file not found.")
        press_enter_to_continue()
        return
    
    clear_screen()
    show_header()
    show_panel(f"Traffic Stats: {domain}", title="Domain & Nginx", style="cyan")
    
    console.print(f"[dim]Analyzing: {log_path}[/dim]")
    console.print(f"[dim]Period: {time_range}[/dim]")
    console.print()
    
    # Parse log file
    stats = _parse_access_log(log_path, time_range)
    
    if not stats['total_requests']:
        show_info("No data found for selected period.")
        press_enter_to_continue()
        return
    
    # Summary
    columns = [
        {"name": "Metric", "style": "cyan"},
        {"name": "Value", "justify": "right"},
    ]
    
    rows = [
        ["Total Requests", f"{stats['total_requests']:,}"],
        ["Unique IPs", f"{stats['unique_ips']:,}"],
        ["Bandwidth (est.)", stats['bandwidth']],
    ]
    
    show_table("Summary", columns, rows, show_header=False)
    console.print()
    
    # Status codes
    if stats['status_codes']:
        console.print("[bold]Status Codes:[/bold]")
        for code, count in stats['status_codes'].most_common(5):
            pct = (count / stats['total_requests']) * 100
            color = "green" if code.startswith('2') else "yellow" if code.startswith('3') else "red"
            console.print(f"  [{color}]{code}[/{color}]: {count:,} ({pct:.1f}%)")
        console.print()
    
    # Top IPs
    if stats['top_ips']:
        console.print("[bold]Top 5 IPs:[/bold]")
        for ip, count in stats['top_ips'].most_common(5):
            console.print(f"  {ip}: {count:,} requests")
        console.print()
    
    # Top URLs
    if stats['top_urls']:
        console.print("[bold]Top 5 URLs:[/bold]")
        for url, count in stats['top_urls'].most_common(5):
            url_display = url[:50] + "..." if len(url) > 50 else url
            console.print(f"  {url_display}: {count:,} hits")
    
    press_enter_to_continue()


def _parse_access_log(log_path, time_range):
    """Parse nginx access log and return statistics."""
    stats = {
        'total_requests': 0,
        'unique_ips': 0,
        'bandwidth': '0 B',
        'status_codes': Counter(),
        'top_ips': Counter(),
        'top_urls': Counter(),
    }
    
    # Determine how many lines to process based on time range
    if time_range == "Today":
        cmd = f"grep \"$(date '+%d/%b/%Y')\" {log_path} 2>/dev/null"
    elif time_range == "Last 7 days":
        cmd = f"tail -n 100000 {log_path} 2>/dev/null"
    elif time_range == "Last 30 days":
        cmd = f"tail -n 500000 {log_path} 2>/dev/null"
    else:
        cmd = f"cat {log_path} 2>/dev/null"
    
    result = run_command(cmd, check=False, silent=True)
    if result.returncode != 0 or not result.stdout.strip():
        return stats
    
    lines = result.stdout.strip().split('\n')
    total_bytes = 0
    ips = set()
    
    for line in lines:
        if not line.strip():
            continue
        
        parts = line.split()
        if len(parts) < 10:
            continue
        
        try:
            ip = parts[0]
            url = parts[6] if len(parts) > 6 else "-"
            status = parts[8] if len(parts) > 8 else "0"
            size = parts[9] if len(parts) > 9 else "0"
            
            stats['total_requests'] += 1
            ips.add(ip)
            stats['top_ips'][ip] += 1
            stats['top_urls'][url] += 1
            stats['status_codes'][status] += 1
            
            if size.isdigit():
                total_bytes += int(size)
        except (IndexError, ValueError):
            continue
    
    stats['unique_ips'] = len(ips)
    
    # Format bandwidth
    if total_bytes > 1024**3:
        stats['bandwidth'] = f"{total_bytes / 1024**3:.2f} GB"
    elif total_bytes > 1024**2:
        stats['bandwidth'] = f"{total_bytes / 1024**2:.2f} MB"
    elif total_bytes > 1024:
        stats['bandwidth'] = f"{total_bytes / 1024:.2f} KB"
    else:
        stats['bandwidth'] = f"{total_bytes} B"
    
    return stats
```

**Step 2: Commit**

```bash
git add modules/webserver/stats.py
git commit -m "feat(webserver): add traffic statistics"
```

---

## Task 8: Create domains.py and configure.py

**Files:**
- Create: `modules/webserver/domains.py` (copy and adapt from original)
- Create: `modules/webserver/configure.py` (copy and adapt from original)

**Step 1: Create domains.py**

Copy functions from original webserver.py:
- `generate_site_config()`
- `add_domain_interactive()`
- `add_domain()`
- `list_domains()`
- `enable_domain()`
- `disable_domain()`
- `remove_domain_interactive()`

Update imports to use utils from `modules/webserver/utils.py`.

**Step 2: Create configure.py**

Copy functions from original webserver.py:
- `configure_site_menu()`
- All `configure_*` submenu handlers
- `_save_config()` helper

**Step 3: Verify and commit**

```bash
git add modules/webserver/domains.py modules/webserver/configure.py
git commit -m "feat(webserver): add domains and configure modules"
```

---

## Execution Handoff

**To execute this plan:**
1. Use skill: `superpowers:executing-plans`
2. Load this plan file
3. Execute tasks 1-8 in order
4. Each task is atomic - commit after each

**Estimated time:** 30-45 minutes

**Post-implementation verification:**
- [ ] `python3 -c "from modules.webserver import show_menu"` succeeds
- [ ] All 12 menu options visible when nginx installed
- [ ] Backup/Restore creates files in `/etc/vexo/nginx-backups/`
- [ ] Clone domain creates new config
- [ ] Bulk operations work with InquirerPy checkbox
- [ ] Log viewer shows last 50 lines
- [ ] SSL info shows certificate expiry
- [ ] Traffic stats parses access log correctly
