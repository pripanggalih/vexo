# Email Module - Webmail (Roundcube) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add optional Roundcube webmail installation with automatic configuration for Dovecot integration.

**Architecture:** Create `modules/email/webmail/` folder with install module that handles Roundcube installation, Nginx configuration, and database setup.

**Tech Stack:** Python, Roundcube, Nginx, PHP, SQLite/MariaDB

---

## Task 1: Create Webmail Install Module

**Files:**
- Modify: `modules/email/webmail/__init__.py`
- Create: `modules/email/webmail/roundcube.py`

**Step 1: Update modules/email/webmail/__init__.py**

```python
"""Roundcube webmail management (optional)."""

import os

from ui.menu import run_menu_loop
from utils.shell import is_installed


def _is_roundcube_installed():
    """Check if Roundcube is installed."""
    return os.path.exists("/var/www/roundcube") or os.path.exists("/usr/share/roundcube")


def show_menu():
    """Display Webmail Management submenu."""
    def get_status():
        if _is_roundcube_installed():
            return "Roundcube: [green]Installed[/green]"
        return "Roundcube: [dim]Not Installed[/dim]"
    
    def get_options():
        if _is_roundcube_installed():
            return [
                ("status", "1. View Status"),
                ("config", "2. Configure"),
                ("plugins", "3. Plugins"),
                ("update", "4. Update"),
                ("back", "← Back"),
            ]
        return [
            ("install", "1. Install Roundcube"),
            ("back", "← Back"),
        ]
    
    def get_handlers():
        from modules.email.webmail.roundcube import (
            install_roundcube, view_status, configure_roundcube,
            manage_plugins, update_roundcube,
        )
        
        return {
            "install": install_roundcube,
            "status": view_status,
            "config": configure_roundcube,
            "plugins": manage_plugins,
            "update": update_roundcube,
        }
    
    run_menu_loop("Webmail (Roundcube)", get_options, get_handlers(), get_status)
```

**Step 2: Create modules/email/webmail/roundcube.py**

```python
"""Roundcube webmail installation and management."""

import os
import secrets
import string

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list
from utils.shell import (
    run_command, run_command_realtime, is_installed, is_service_running,
    require_root,
)


# Paths
ROUNDCUBE_DIR = "/var/www/roundcube"
ROUNDCUBE_CONFIG = "/var/www/roundcube/config/config.inc.php"
ROUNDCUBE_VERSION = "1.6.5"
ROUNDCUBE_URL = f"https://github.com/roundcube/roundcubemail/releases/download/{ROUNDCUBE_VERSION}/roundcubemail-{ROUNDCUBE_VERSION}-complete.tar.gz"


def install_roundcube():
    """Install Roundcube webmail."""
    clear_screen()
    show_header()
    show_panel("Install Roundcube", title="Webmail", style="cyan")
    
    if os.path.exists(ROUNDCUBE_DIR):
        show_info("Roundcube appears to be already installed.")
        press_enter_to_continue()
        return
    
    # Prerequisites check
    console.print("[bold]Prerequisites Check:[/bold]")
    console.print()
    
    prereqs = [
        ("nginx", is_installed("nginx"), "Web server"),
        ("php-fpm", is_installed("php-fpm"), "PHP processor"),
        ("dovecot", is_installed("dovecot-core"), "IMAP server"),
    ]
    
    all_ok = True
    for name, installed, desc in prereqs:
        status = "[green]✓[/green]" if installed else "[red]✗[/red]"
        console.print(f"  {status} {desc} ({name})")
        if not installed:
            all_ok = False
    
    console.print()
    
    if not all_ok:
        show_warning("Some prerequisites are missing.")
        if not confirm_action("Continue anyway?"):
            press_enter_to_continue()
            return
    
    # Configuration
    console.print("[bold]Configuration:[/bold]")
    console.print()
    
    webmail_domain = text_input("Webmail domain (e.g., mail.example.com):")
    if not webmail_domain:
        return
    
    db_types = ["SQLite (simple, no setup)", "MariaDB (better for multiple users)"]
    db_type = select_from_list("Database", "Select database type:", db_types)
    if not db_type:
        return
    
    use_sqlite = "SQLite" in db_type
    
    if not use_sqlite:
        # MariaDB setup
        db_name = text_input("Database name:", default="roundcube")
        db_user = text_input("Database user:", default="roundcube")
        from getpass import getpass
        try:
            db_pass = getpass("Database password: ")
        except Exception:
            db_pass = text_input("Database password:")
        
        if not db_pass:
            return
    
    # SSL
    use_ssl = confirm_action("Setup SSL with Let's Encrypt?")
    
    console.print()
    console.print("[bold]Summary:[/bold]")
    console.print(f"  Domain: {webmail_domain}")
    console.print(f"  Database: {'SQLite' if use_sqlite else 'MariaDB'}")
    console.print(f"  SSL: {'Yes' if use_ssl else 'No'}")
    console.print()
    
    if not confirm_action("Install Roundcube?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Install PHP dependencies
    show_info("Installing PHP dependencies...")
    
    php_packages = "php-xml php-mbstring php-intl php-zip php-gd php-curl php-json"
    if not use_sqlite:
        php_packages += " php-mysql"
    else:
        php_packages += " php-sqlite3"
    
    run_command_realtime(f"apt install -y {php_packages}", "Installing PHP modules...")
    
    # Download Roundcube
    show_info("Downloading Roundcube...")
    
    os.makedirs("/tmp/roundcube_install", exist_ok=True)
    
    result = run_command(
        f"wget -O /tmp/roundcube.tar.gz {ROUNDCUBE_URL}",
        check=False, silent=True
    )
    
    if result.returncode != 0:
        # Fallback to apt install
        show_info("Downloading failed, trying apt install...")
        run_command_realtime("apt install -y roundcube roundcube-core", "Installing Roundcube...")
        
        if not os.path.exists("/usr/share/roundcube"):
            show_error("Failed to install Roundcube.")
            press_enter_to_continue()
            return
        
        # Symlink
        run_command(f"ln -sf /usr/share/roundcube {ROUNDCUBE_DIR}", check=False, silent=True)
    else:
        # Extract
        show_info("Extracting Roundcube...")
        run_command(f"tar -xzf /tmp/roundcube.tar.gz -C /tmp/roundcube_install", check=False, silent=True)
        run_command(f"mv /tmp/roundcube_install/roundcubemail-* {ROUNDCUBE_DIR}", check=False, silent=True)
    
    # Set permissions
    run_command(f"chown -R www-data:www-data {ROUNDCUBE_DIR}", check=False, silent=True)
    run_command(f"chmod -R 755 {ROUNDCUBE_DIR}", check=False, silent=True)
    
    # Configure database
    if use_sqlite:
        db_dsn = f"sqlite:///{ROUNDCUBE_DIR}/db/roundcube.db"
        os.makedirs(f"{ROUNDCUBE_DIR}/db", mode=0o750, exist_ok=True)
        run_command(f"chown www-data:www-data {ROUNDCUBE_DIR}/db", check=False, silent=True)
    else:
        # Create MariaDB database
        run_command(f'mysql -e "CREATE DATABASE IF NOT EXISTS {db_name};"', check=False, silent=True)
        run_command(
            f'mysql -e "GRANT ALL ON {db_name}.* TO \'{db_user}\'@\'localhost\' IDENTIFIED BY \'{db_pass}\';"',
            check=False, silent=True
        )
        run_command("mysql -e 'FLUSH PRIVILEGES;'", check=False, silent=True)
        db_dsn = f"mysql://{db_user}:{db_pass}@localhost/{db_name}"
    
    # Generate config
    show_info("Configuring Roundcube...")
    
    des_key = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(24))
    
    # Detect IMAP/SMTP settings
    imap_host = "localhost"
    smtp_host = "localhost"
    smtp_port = "587"
    
    config_content = f"""<?php
// Roundcube configuration - managed by vexo

$config['db_dsnw'] = '{db_dsn}';
$config['imap_host'] = 'ssl://{imap_host}:993';
$config['smtp_host'] = 'tls://{smtp_host}:{smtp_port}';
$config['smtp_user'] = '%u';
$config['smtp_pass'] = '%p';
$config['support_url'] = '';
$config['product_name'] = 'Webmail';
$config['des_key'] = '{des_key}';
$config['plugins'] = array('archive', 'zipdownload');
$config['skin'] = 'elastic';
$config['language'] = 'en_US';
$config['spellcheck_engine'] = 'pspell';
$config['upload_max_filesize'] = '25M';
$config['draft_autosave'] = 120;
$config['default_host'] = 'ssl://localhost';
$config['default_port'] = 993;
$config['smtp_port'] = {smtp_port};
$config['smtp_auth_type'] = 'LOGIN';

// Session
$config['session_lifetime'] = 30;
$config['session_domain'] = '';

// Enable installer for initial setup
$config['enable_installer'] = false;
"""
    
    os.makedirs(f"{ROUNDCUBE_DIR}/config", exist_ok=True)
    with open(ROUNDCUBE_CONFIG, 'w') as f:
        f.write(config_content)
    
    run_command(f"chown www-data:www-data {ROUNDCUBE_CONFIG}", check=False, silent=True)
    run_command(f"chmod 640 {ROUNDCUBE_CONFIG}", check=False, silent=True)
    
    # Initialize database
    if use_sqlite:
        run_command(
            f"sudo -u www-data php {ROUNDCUBE_DIR}/bin/initdb.sh --dir={ROUNDCUBE_DIR}/SQL",
            check=False, silent=True
        )
    else:
        run_command(
            f"mysql {db_name} < {ROUNDCUBE_DIR}/SQL/mysql.initial.sql",
            check=False, silent=True
        )
    
    # Create Nginx config
    show_info("Configuring Nginx...")
    
    nginx_config = f"""server {{
    listen 80;
    server_name {webmail_domain};
    root {ROUNDCUBE_DIR};
    index index.php;
    
    location / {{
        try_files $uri $uri/ /index.php?$args;
    }}
    
    location ~ \\.php$ {{
        include fastcgi_params;
        fastcgi_pass unix:/var/run/php/php-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_intercept_errors on;
    }}
    
    location ~ /\\. {{
        deny all;
    }}
    
    location ~ ^/(config|temp|logs)/ {{
        deny all;
    }}
}}
"""
    
    nginx_conf_path = f"/etc/nginx/sites-available/{webmail_domain}"
    with open(nginx_conf_path, 'w') as f:
        f.write(nginx_config)
    
    # Enable site
    enabled_path = f"/etc/nginx/sites-enabled/{webmail_domain}"
    if os.path.exists(enabled_path):
        os.remove(enabled_path)
    os.symlink(nginx_conf_path, enabled_path)
    
    # Test and reload Nginx
    result = run_command("nginx -t", check=False, silent=True)
    if result.returncode == 0:
        run_command("systemctl reload nginx", check=False, silent=True)
    else:
        show_warning("Nginx configuration test failed.")
    
    # SSL with Let's Encrypt
    if use_ssl:
        show_info("Setting up SSL...")
        
        if is_installed("certbot"):
            result = run_command(
                f"certbot --nginx -d {webmail_domain} --non-interactive --agree-tos --register-unsafely-without-email",
                check=False, silent=True
            )
            if result.returncode != 0:
                show_warning("SSL setup failed. You can run certbot manually later.")
        else:
            show_warning("Certbot not installed. Install with: apt install certbot python3-certbot-nginx")
    
    # Cleanup
    run_command("rm -rf /tmp/roundcube_install /tmp/roundcube.tar.gz", check=False, silent=True)
    
    show_success("Roundcube installed successfully!")
    console.print()
    console.print(f"[bold]Access webmail at:[/bold] http{'s' if use_ssl else ''}://{webmail_domain}")
    console.print()
    console.print("[dim]Users can login with their mailbox credentials.[/dim]")
    
    press_enter_to_continue()


def view_status():
    """View Roundcube status."""
    clear_screen()
    show_header()
    show_panel("Roundcube Status", title="Webmail", style="cyan")
    
    if not os.path.exists(ROUNDCUBE_DIR):
        show_error("Roundcube is not installed.")
        press_enter_to_continue()
        return
    
    console.print(f"[bold]Installation:[/bold] {ROUNDCUBE_DIR}")
    
    # Check config
    if os.path.exists(ROUNDCUBE_CONFIG):
        console.print("[bold]Configuration:[/bold] [green]Found[/green]")
    else:
        console.print("[bold]Configuration:[/bold] [red]Missing[/red]")
    
    # Check Nginx
    result = run_command("grep -l roundcube /etc/nginx/sites-enabled/* 2>/dev/null", check=False, silent=True)
    if result.stdout.strip():
        console.print(f"[bold]Nginx Config:[/bold] [green]Enabled[/green]")
        
        # Extract domain
        result = run_command(
            "grep server_name /etc/nginx/sites-enabled/*roundcube* 2>/dev/null | head -1",
            check=False, silent=True
        )
        if result.stdout:
            console.print(f"[bold]Domain:[/bold] {result.stdout.split()[-1].replace(';', '')}")
    else:
        console.print("[bold]Nginx Config:[/bold] [yellow]Not found[/yellow]")
    
    # PHP-FPM
    fpm_running = is_service_running("php8.1-fpm") or is_service_running("php-fpm")
    console.print(f"[bold]PHP-FPM:[/bold] {'[green]Running[/green]' if fpm_running else '[red]Stopped[/red]'}")
    
    press_enter_to_continue()


def configure_roundcube():
    """Configure Roundcube settings."""
    clear_screen()
    show_header()
    show_panel("Configure Roundcube", title="Webmail", style="cyan")
    
    if not os.path.exists(ROUNDCUBE_CONFIG):
        show_error("Roundcube configuration not found.")
        press_enter_to_continue()
        return
    
    options = [
        "Change IMAP server",
        "Change SMTP server",
        "Change product name",
        "View current config",
    ]
    
    choice = select_from_list("Configure", "Select option:", options)
    if not choice:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if "IMAP" in choice:
        host = text_input("IMAP server:", default="ssl://localhost:993")
        if host:
            _update_config("imap_host", f"'{host}'")
            show_success("IMAP server updated!")
    
    elif "SMTP" in choice:
        host = text_input("SMTP server:", default="tls://localhost:587")
        if host:
            _update_config("smtp_host", f"'{host}'")
            show_success("SMTP server updated!")
    
    elif "product" in choice:
        name = text_input("Product name:", default="Webmail")
        if name:
            _update_config("product_name", f"'{name}'")
            show_success("Product name updated!")
    
    else:
        # View config
        result = run_command(f"cat {ROUNDCUBE_CONFIG}", check=False, silent=True)
        console.print(result.stdout[:2000] if result.stdout else "[dim]Empty[/dim]")
    
    press_enter_to_continue()


def _update_config(key, value):
    """Update a Roundcube config value."""
    run_command(
        f"sed -i \"s|\\$config\\['{key}'\\].*|\\$config['{key}'] = {value};|\" {ROUNDCUBE_CONFIG}",
        check=False, silent=True
    )


def manage_plugins():
    """Manage Roundcube plugins."""
    clear_screen()
    show_header()
    show_panel("Plugins", title="Roundcube", style="cyan")
    
    if not os.path.exists(ROUNDCUBE_DIR):
        show_error("Roundcube is not installed.")
        press_enter_to_continue()
        return
    
    plugins_dir = f"{ROUNDCUBE_DIR}/plugins"
    if not os.path.exists(plugins_dir):
        show_info("Plugins directory not found.")
        press_enter_to_continue()
        return
    
    # List available plugins
    available = [d for d in os.listdir(plugins_dir) if os.path.isdir(os.path.join(plugins_dir, d))]
    
    # Get enabled plugins from config
    result = run_command(f"grep -o \"'[^']*'\" {ROUNDCUBE_CONFIG} | grep -A100 'plugins'", check=False, silent=True)
    enabled = []
    
    columns = [
        {"name": "Plugin", "style": "cyan"},
        {"name": "Status"},
        {"name": "Description"},
    ]
    
    plugin_descriptions = {
        "archive": "Archive messages to folder",
        "zipdownload": "Download attachments as ZIP",
        "managesieve": "Email filter rules",
        "password": "Change password",
        "markasjunk": "Mark messages as spam",
        "newmail_notifier": "New mail notifications",
    }
    
    rows = []
    for plugin in sorted(available)[:20]:
        status = "[green]Enabled[/green]" if plugin in str(result.stdout) else "[dim]Disabled[/dim]"
        desc = plugin_descriptions.get(plugin, "")
        rows.append([plugin, status, desc])
    
    show_table(f"{len(available)} plugin(s)", columns, rows, show_header=True)
    
    console.print()
    console.print("[dim]Edit plugins array in config.inc.php to enable/disable.[/dim]")
    
    press_enter_to_continue()


def update_roundcube():
    """Update Roundcube to latest version."""
    clear_screen()
    show_header()
    show_panel("Update Roundcube", title="Webmail", style="yellow")
    
    if not os.path.exists(ROUNDCUBE_DIR):
        show_error("Roundcube is not installed.")
        press_enter_to_continue()
        return
    
    show_warning("Update will download the latest version and replace files.")
    console.print("[dim]Your configuration will be preserved.[/dim]")
    console.print()
    
    if not confirm_action("Proceed with update?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Backup config
    show_info("Backing up configuration...")
    run_command(f"cp {ROUNDCUBE_CONFIG} /tmp/roundcube_config_backup.php", check=False, silent=True)
    
    # Download latest
    show_info("Downloading latest version...")
    
    result = run_command(f"wget -O /tmp/roundcube_new.tar.gz {ROUNDCUBE_URL}", check=False, silent=True)
    
    if result.returncode != 0:
        show_error("Download failed.")
        press_enter_to_continue()
        return
    
    # Extract to temp
    run_command("rm -rf /tmp/roundcube_update", check=False, silent=True)
    run_command("mkdir -p /tmp/roundcube_update", check=False, silent=True)
    run_command("tar -xzf /tmp/roundcube_new.tar.gz -C /tmp/roundcube_update", check=False, silent=True)
    
    # Update files
    show_info("Updating files...")
    run_command(f"rsync -a /tmp/roundcube_update/roundcubemail-*/ {ROUNDCUBE_DIR}/", check=False, silent=True)
    
    # Restore config
    run_command(f"cp /tmp/roundcube_config_backup.php {ROUNDCUBE_CONFIG}", check=False, silent=True)
    
    # Set permissions
    run_command(f"chown -R www-data:www-data {ROUNDCUBE_DIR}", check=False, silent=True)
    
    # Run update script
    run_command(f"php {ROUNDCUBE_DIR}/bin/update.sh --version=?", check=False, silent=True)
    
    # Cleanup
    run_command("rm -rf /tmp/roundcube_update /tmp/roundcube_new.tar.gz", check=False, silent=True)
    
    show_success("Roundcube updated!")
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/email/webmail/
git commit -m "feat(email): add Roundcube webmail installation"
```

---

## Execution Handoff

Plan 07 complete. This adds optional Roundcube webmail functionality.

---

## Summary - All Email Plans

| Plan | File | Features |
|------|------|----------|
| 01 | email-01-postfix-core.md | Folder structure, install, modes, domains, queue |
| 02 | email-02-deliverability.md | DKIM, SPF, DMARC, DNS records |
| 03 | email-03-relay.md | SMTP relay, multi-provider, profiles |
| 04 | email-04-routing.md | Aliases, forwarding, SpamAssassin, blacklist |
| 05 | email-05-monitoring.md | Statistics, delivery reports, logs, health check |
| 06 | email-06-dovecot.md | Mailbox server, virtual mailboxes, quota |
| 07 | email-07-webmail.md | Roundcube installation, configuration |

**Total: ~40+ features, ~5000+ lines of code**
