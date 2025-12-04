# Email Module - Postfix Core Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor email module to folder structure and enhance Postfix core functionality with install wizard, mode configuration, and domain management.

**Architecture:** Create `modules/email/` folder structure with `postfix/` subfolder. Migrate existing email.py functions to appropriate files. Add shared utilities.

**Tech Stack:** Python, Postfix, Rich UI, Prompt Toolkit

---

## Task 1: Create Email Folder Structure

**Files:**
- Create: `modules/email/__init__.py`
- Create: `modules/email/utils.py`
- Create: `modules/email/postfix/__init__.py`
- Create: `modules/email/postfix/utils.py`

**Step 1: Create directory structure**

```bash
mkdir -p modules/email/postfix
mkdir -p modules/email/dovecot
mkdir -p modules/email/webmail
```

**Step 2: Create modules/email/utils.py**

```python
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
```

**Step 3: Create modules/email/__init__.py**

```python
"""Email server management module for vexo."""

from ui.menu import run_menu_loop
from modules.email.utils import get_email_status, format_service_status


def show_menu():
    """Display the main Email Management menu."""
    def get_status():
        status = get_email_status()
        parts = []
        
        # Postfix status
        pf = status["postfix"]
        if pf["installed"]:
            parts.append(f"Postfix:[{'green' if pf['running'] else 'red'}]{'●' if pf['running'] else '○'}[/]")
        
        # Dovecot status
        dv = status["dovecot"]
        if dv["installed"]:
            parts.append(f"Dovecot:[{'green' if dv['running'] else 'red'}]{'●' if dv['running'] else '○'}[/]")
        
        # Roundcube status
        rc = status["roundcube"]
        if rc["installed"]:
            parts.append("Webmail:[green]●[/]")
        
        return " | ".join(parts) if parts else "[dim]Not configured[/dim]"
    
    options = [
        ("postfix", "1. Postfix (Core Mail Server)"),
        ("dovecot", "2. Dovecot (Mailbox Server) [Optional]"),
        ("webmail", "3. Webmail (Roundcube) [Optional]"),
        ("back", "← Back to Main Menu"),
    ]
    
    def get_handlers():
        from modules.email.postfix import show_menu as postfix_menu
        from modules.email.dovecot import show_menu as dovecot_menu
        from modules.email.webmail import show_menu as webmail_menu
        
        return {
            "postfix": postfix_menu,
            "dovecot": dovecot_menu,
            "webmail": webmail_menu,
        }
    
    run_menu_loop("Email Server Management", options, get_handlers(), get_status)
```

**Step 4: Create modules/email/postfix/utils.py**

```python
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
```

**Step 5: Create modules/email/postfix/__init__.py**

```python
"""Postfix mail server management."""

from ui.menu import run_menu_loop
from utils.shell import is_installed, is_service_running
from modules.email.postfix.utils import get_postfix_mode, get_postfix_setting


def show_menu():
    """Display Postfix Management submenu."""
    def get_status():
        if not is_installed("postfix"):
            return "Postfix: [yellow]Not installed[/yellow]"
        
        if not is_service_running("postfix"):
            return "Postfix: [red]Stopped[/red]"
        
        mode = get_postfix_mode()
        mode_display = {
            "send-only": "[cyan]Send-Only[/cyan]",
            "receive": "[yellow]Receive[/yellow]",
        }.get(mode, f"[dim]{mode}[/dim]")
        
        return f"Postfix: [green]Running[/green] ({mode_display})"
    
    def get_options():
        options = []
        if is_installed("postfix"):
            options.extend([
                ("mode", "1. Configure Mode"),
                ("domains", "2. Domain Management"),
                ("deliver", "3. Deliverability (DKIM/SPF/DMARC)"),
                ("relay", "4. SMTP Relay"),
                ("routing", "5. Routing (Aliases/Forward/Spam)"),
                ("monitor", "6. Monitoring & Stats"),
                ("queue", "7. Queue Management"),
                ("service", "8. Service Control"),
            ])
        else:
            options.append(("install", "1. Install Postfix"))
        options.append(("back", "← Back"))
        return options
    
    def get_handlers():
        from modules.email.postfix.install import install_postfix, service_control_menu
        from modules.email.postfix.modes import show_modes_menu
        from modules.email.postfix.domains import show_domains_menu
        from modules.email.postfix.deliverability import show_deliverability_menu
        from modules.email.postfix.relay import show_relay_menu
        from modules.email.postfix.routing import show_routing_menu
        from modules.email.postfix.monitor import show_monitor_menu
        from modules.email.postfix.queue import show_queue_menu
        
        return {
            "install": install_postfix,
            "mode": show_modes_menu,
            "domains": show_domains_menu,
            "deliver": show_deliverability_menu,
            "relay": show_relay_menu,
            "routing": show_routing_menu,
            "monitor": show_monitor_menu,
            "queue": show_queue_menu,
            "service": service_control_menu,
        }
    
    run_menu_loop("Postfix Mail Server", get_options, get_handlers(), get_status)
```

**Step 6: Commit**

```bash
git add modules/email/
git commit -m "refactor(email): create folder structure with postfix subfolder"
```

---

## Task 2: Create Postfix Install Module

**Files:**
- Create: `modules/email/postfix/install.py`

**Step 1: Create install.py**

```python
"""Postfix installation and service control."""

from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list
from utils.shell import (
    run_command, run_command_realtime, is_installed, is_service_running,
    service_control, require_root, get_hostname,
)


def install_postfix():
    """Install Postfix mail server."""
    clear_screen()
    show_header()
    show_panel("Install Postfix", title="Email Server", style="cyan")
    
    if is_installed("postfix"):
        show_info("Postfix is already installed.")
        
        if not is_service_running("postfix"):
            if confirm_action("Start Postfix service?"):
                service_control("postfix", "start")
                show_success("Postfix started!")
        
        press_enter_to_continue()
        return
    
    console.print("[bold]Postfix Installation Wizard[/bold]")
    console.print()
    console.print("This will install:")
    console.print("  • Postfix MTA (Mail Transfer Agent)")
    console.print("  • mailutils (mail command)")
    console.print()
    
    # Get hostname
    hostname = get_hostname()
    
    mail_hostname = text_input("Mail hostname:", default=hostname)
    if not mail_hostname:
        return
    
    # Extract domain from hostname
    parts = mail_hostname.split('.')
    if len(parts) >= 2:
        default_domain = '.'.join(parts[-2:])
    else:
        default_domain = mail_hostname
    
    mail_domain = text_input("Mail domain:", default=default_domain)
    if not mail_domain:
        return
    
    # Mode selection
    modes = [
        "Send-Only (recommended for app servers)",
        "Receive (accept incoming email)",
    ]
    mode = select_from_list("Initial Mode", "Select mode:", modes)
    if not mode:
        return
    
    console.print()
    console.print("[bold]Configuration Summary:[/bold]")
    console.print(f"  Hostname: {mail_hostname}")
    console.print(f"  Domain: {mail_domain}")
    console.print(f"  Mode: {mode.split(' ')[0]}")
    console.print()
    
    if not confirm_action("Install Postfix with these settings?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Pre-configure debconf
    show_info("Pre-configuring Postfix...")
    
    debconf_settings = f"""postfix postfix/main_mailer_type select Internet Site
postfix postfix/mailname string {mail_hostname}
"""
    run_command(
        f'echo "{debconf_settings}" | debconf-set-selections',
        check=False, silent=True
    )
    
    # Install
    show_info("Installing Postfix...")
    
    returncode = run_command_realtime(
        "DEBIAN_FRONTEND=noninteractive apt install -y postfix mailutils",
        "Installing Postfix..."
    )
    
    if returncode != 0:
        show_error("Failed to install Postfix.")
        press_enter_to_continue()
        return
    
    # Configure based on mode
    from modules.email.postfix.utils import set_postfix_settings
    
    base_settings = {
        "myhostname": mail_hostname,
        "mydomain": mail_domain,
        "myorigin": "$mydomain",
    }
    
    if "Send-Only" in mode:
        base_settings.update({
            "inet_interfaces": "loopback-only",
            "mydestination": "$myhostname, localhost.$mydomain, localhost",
            "local_transport": "error:local delivery disabled",
        })
    else:
        base_settings.update({
            "inet_interfaces": "all",
            "mydestination": "$myhostname, localhost.$mydomain, localhost",
        })
    
    set_postfix_settings(base_settings)
    
    # Start and enable
    service_control("postfix", "restart")
    service_control("postfix", "enable")
    
    if is_service_running("postfix"):
        show_success("Postfix installed and running!")
        console.print()
        console.print(f"[dim]Mode: {mode.split(' ')[0]}[/dim]")
        console.print(f"[dim]Hostname: {mail_hostname}[/dim]")
    else:
        show_warning("Postfix installed but may not be running.")
    
    press_enter_to_continue()


def service_control_menu():
    """Service control menu for Postfix."""
    clear_screen()
    show_header()
    show_panel("Service Control", title="Postfix", style="cyan")
    
    running = is_service_running("postfix")
    console.print(f"[bold]Status:[/bold] {'[green]Running[/green]' if running else '[red]Stopped[/red]'}")
    console.print()
    
    options = [
        "Start",
        "Stop",
        "Restart",
        "Reload (graceful)",
        "Enable (start on boot)",
        "Disable (don't start on boot)",
    ]
    
    action = select_from_list("Action", "Select:", options)
    if not action:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    action_map = {
        "Start": "start",
        "Stop": "stop",
        "Restart": "restart",
        "Reload": "reload",
        "Enable": "enable",
        "Disable": "disable",
    }
    
    for key, value in action_map.items():
        if action.startswith(key):
            service_control("postfix", value)
            show_success(f"Postfix {value}ed!")
            break
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/email/postfix/install.py
git commit -m "feat(email): add Postfix installation wizard"
```

---

## Task 3: Create Postfix Modes Module

**Files:**
- Create: `modules/email/postfix/modes.py`

**Step 1: Create modes.py**

```python
"""Postfix mode configuration (send-only, receive)."""

from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, run_menu_loop
from utils.shell import is_installed, is_service_running, require_root
from modules.email.postfix.utils import (
    get_postfix_mode, set_postfix_settings, restart_postfix,
)


def show_modes_menu():
    """Display mode configuration menu."""
    def get_status():
        mode = get_postfix_mode()
        if mode == "send-only":
            return "Current: [cyan]Send-Only[/cyan]"
        elif mode == "receive":
            return "Current: [yellow]Receive[/yellow]"
        return f"Current: [dim]{mode}[/dim]"
    
    options = [
        ("send", "1. Send-Only Mode"),
        ("receive", "2. Receive Mode"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "send": setup_send_only,
        "receive": setup_receive_mode,
    }
    
    run_menu_loop("Configure Mode", options, handlers, get_status)


def setup_send_only():
    """Configure Postfix for send-only mode."""
    clear_screen()
    show_header()
    show_panel("Send-Only Mode", title="Postfix", style="cyan")
    
    if not is_installed("postfix"):
        show_error("Postfix is not installed.")
        press_enter_to_continue()
        return
    
    current_mode = get_postfix_mode()
    if current_mode == "send-only":
        show_info("Already in send-only mode.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Send-Only Mode will:[/bold]")
    console.print("  • Listen on localhost only (127.0.0.1)")
    console.print("  • Disable incoming mail from outside")
    console.print("  • Allow sending outgoing emails")
    console.print("  • Disable local mailbox delivery")
    console.print()
    console.print("[dim]Ideal for application servers that only need to")
    console.print("send notifications and transactional emails.[/dim]")
    console.print()
    
    if not confirm_action("Switch to send-only mode?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    show_info("Configuring send-only mode...")
    
    settings = {
        "inet_interfaces": "loopback-only",
        "mydestination": "$myhostname, localhost.$mydomain, localhost",
        "local_transport": "error:local delivery disabled",
    }
    
    if set_postfix_settings(settings):
        restart_postfix()
        
        if is_service_running("postfix"):
            show_success("Send-only mode configured!")
            console.print()
            console.print("[dim]Postfix now only listens on localhost.[/dim]")
        else:
            show_warning("Configuration applied but Postfix may not be running.")
    else:
        show_error("Failed to configure send-only mode.")
    
    press_enter_to_continue()


def setup_receive_mode():
    """Configure Postfix for receive mode."""
    clear_screen()
    show_header()
    show_panel("Receive Mode", title="Postfix", style="cyan")
    
    if not is_installed("postfix"):
        show_error("Postfix is not installed.")
        press_enter_to_continue()
        return
    
    current_mode = get_postfix_mode()
    if current_mode == "receive":
        show_info("Already in receive mode.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Receive Mode will:[/bold]")
    console.print("  • Listen on all interfaces (port 25)")
    console.print("  • Accept incoming email for configured domains")
    console.print("  • Can pipe emails to applications")
    console.print()
    console.print("[yellow]Prerequisites:[/yellow]")
    console.print("  • DNS MX record pointing to this server")
    console.print("  • Port 25 open in firewall")
    console.print("  • Domain(s) configured in Domain Management")
    console.print()
    
    if not confirm_action("Switch to receive mode?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    show_info("Configuring receive mode...")
    
    settings = {
        "inet_interfaces": "all",
        "mydestination": "$myhostname, localhost.$mydomain, localhost",
    }
    
    # Remove local_transport restriction
    from utils.shell import run_command
    run_command("postconf -X local_transport 2>/dev/null", check=False, silent=True)
    
    if set_postfix_settings(settings):
        restart_postfix()
        
        if is_service_running("postfix"):
            show_success("Receive mode configured!")
            console.print()
            console.print("[yellow]Remember to:[/yellow]")
            console.print("  • Configure domains in Domain Management")
            console.print("  • Setup MX DNS record")
            console.print("  • Open port 25 in firewall")
        else:
            show_warning("Configuration applied but Postfix may not be running.")
    else:
        show_error("Failed to configure receive mode.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/email/postfix/modes.py
git commit -m "feat(email): add Postfix mode configuration"
```

---

## Task 4: Create Postfix Domains Module

**Files:**
- Create: `modules/email/postfix/domains.py`

**Step 1: Create domains.py** (migrate and enhance from existing email.py)

```python
"""Postfix domain management."""

import os

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, require_root
from modules.email.postfix.utils import (
    is_postfix_ready, get_postfix_mode, load_domains_config, save_domains_config,
    validate_domain, reload_postfix, POSTFIX_VIRTUAL, POSTFIX_MASTER_CF,
)


# Pipe script path
VEXO_PIPE_SCRIPT = "/usr/local/bin/vexo-pipe"
VEXO_EMAIL_LOG = "/var/log/vexo-email.log"


def show_domains_menu():
    """Display domain management menu."""
    def get_status():
        config = load_domains_config()
        count = len(config)
        return f"Domains: {count}"
    
    options = [
        ("list", "1. List Domains"),
        ("add", "2. Add Domain"),
        ("edit", "3. Edit Domain"),
        ("remove", "4. Remove Domain"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "list": list_domains,
        "add": add_domain_interactive,
        "edit": edit_domain_interactive,
        "remove": remove_domain_interactive,
    }
    
    run_menu_loop("Domain Management", options, handlers, get_status)


def list_domains():
    """Display all configured email domains."""
    clear_screen()
    show_header()
    show_panel("Email Domains", title="Domain Management", style="cyan")
    
    config = load_domains_config()
    
    if not config:
        show_info("No domains configured.")
        console.print()
        console.print("[dim]Use 'Add Domain' to configure one.[/dim]")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Domain", "style": "cyan"},
        {"name": "Type"},
        {"name": "Destination"},
        {"name": "Status"},
    ]
    
    rows = []
    for domain, cfg in config.items():
        domain_type = cfg.get("type", "catchall")
        
        if domain_type == "catchall":
            dest = f"→ {cfg.get('command', 'N/A')}"
        elif domain_type == "forward":
            dest = f"→ {cfg.get('forward_to', 'N/A')}"
        else:
            dest = cfg.get("path", "N/A")
        
        status = "[green]Active[/green]" if cfg.get("active", True) else "[red]Inactive[/red]"
        rows.append([domain, domain_type, dest, status])
    
    show_table("Configured Domains", columns, rows, show_header=True)
    press_enter_to_continue()


def add_domain_interactive():
    """Interactive prompt to add a new email domain."""
    clear_screen()
    show_header()
    show_panel("Add Domain", title="Domain Management", style="cyan")
    
    if not is_postfix_ready():
        show_error("Postfix is not running.")
        press_enter_to_continue()
        return
    
    mode = get_postfix_mode()
    if mode == "send-only":
        show_warning("Postfix is in send-only mode.")
        console.print("[dim]Switch to receive mode to accept incoming email.[/dim]")
        press_enter_to_continue()
        return
    
    domain = text_input("Domain name (e.g., example.com):")
    if not domain:
        return
    
    domain = domain.lower().strip()
    
    if not validate_domain(domain):
        show_error("Invalid domain format.")
        press_enter_to_continue()
        return
    
    config = load_domains_config()
    if domain in config:
        show_error(f"Domain '{domain}' already configured.")
        press_enter_to_continue()
        return
    
    # Domain type
    domain_types = [
        "Catch-all to Laravel (pipe to artisan)",
        "Forward to external email",
        "Local delivery (requires Dovecot)",
    ]
    
    domain_type = select_from_list("Domain Type", "How to handle email:", domain_types)
    if not domain_type:
        return
    
    domain_config = {"active": True}
    
    if "Laravel" in domain_type:
        domain_config["type"] = "catchall"
        
        laravel_path = text_input("Laravel project path:", default="/var/www/html")
        if not laravel_path:
            return
        
        if not _validate_laravel_path(laravel_path):
            show_error("Invalid Laravel path (artisan not found).")
            press_enter_to_continue()
            return
        
        artisan_cmd = text_input("Artisan command:", default="email:incoming")
        if not artisan_cmd:
            return
        
        domain_config["path"] = laravel_path
        domain_config["command"] = artisan_cmd
        
    elif "Forward" in domain_type:
        domain_config["type"] = "forward"
        
        forward_to = text_input("Forward all email to:")
        if not forward_to or "@" not in forward_to:
            show_error("Invalid email address.")
            press_enter_to_continue()
            return
        
        domain_config["forward_to"] = forward_to
        
    else:
        domain_config["type"] = "local"
        console.print("[yellow]Local delivery requires Dovecot to be installed.[/yellow]")
    
    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  Domain: {domain}")
    console.print(f"  Type: {domain_config['type']}")
    console.print()
    
    if not confirm_action(f"Add domain {domain}?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    config[domain] = domain_config
    
    if save_domains_config(config):
        _regenerate_postfix_files()
        reload_postfix()
        show_success(f"Domain '{domain}' added!")
    else:
        show_error("Failed to add domain.")
    
    press_enter_to_continue()


def edit_domain_interactive():
    """Edit domain configuration."""
    clear_screen()
    show_header()
    show_panel("Edit Domain", title="Domain Management", style="cyan")
    
    config = load_domains_config()
    if not config:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    domains = list(config.keys())
    domain = select_from_list("Select Domain", "Edit:", domains)
    if not domain:
        return
    
    current = config[domain]
    
    console.print(f"[bold]Current configuration for {domain}:[/bold]")
    console.print(f"  Type: {current.get('type', 'catchall')}")
    if current.get('path'):
        console.print(f"  Path: {current.get('path')}")
    if current.get('command'):
        console.print(f"  Command: {current.get('command')}")
    if current.get('forward_to'):
        console.print(f"  Forward to: {current.get('forward_to')}")
    console.print(f"  Active: {current.get('active', True)}")
    console.print()
    
    # Toggle active
    if confirm_action("Toggle active status?"):
        current["active"] = not current.get("active", True)
        config[domain] = current
        save_domains_config(config)
        _regenerate_postfix_files()
        reload_postfix()
        status = "activated" if current["active"] else "deactivated"
        show_success(f"Domain {domain} {status}!")
    
    press_enter_to_continue()


def remove_domain_interactive():
    """Remove a domain."""
    clear_screen()
    show_header()
    show_panel("Remove Domain", title="Domain Management", style="red")
    
    config = load_domains_config()
    if not config:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    domains = list(config.keys())
    domain = select_from_list("Select Domain", "Remove:", domains)
    if not domain:
        return
    
    console.print(f"[bold red]WARNING: This will stop receiving emails for {domain}![/bold red]")
    
    if not confirm_action(f"Remove domain {domain}?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    del config[domain]
    
    if save_domains_config(config):
        _regenerate_postfix_files()
        reload_postfix()
        show_success(f"Domain '{domain}' removed!")
    else:
        show_error("Failed to remove domain.")
    
    press_enter_to_continue()


def _validate_laravel_path(path):
    """Check if path contains Laravel artisan."""
    return os.path.exists(os.path.join(path, 'artisan'))


def _regenerate_postfix_files():
    """Regenerate Postfix virtual and master.cf files."""
    config = load_domains_config()
    
    # Generate virtual file
    lines = ["# Generated by vexo\n"]
    
    for domain, cfg in config.items():
        if not cfg.get("active", True):
            continue
        
        if cfg.get("type") == "catchall":
            transport_name = f"laravel-{domain.replace('.', '-')}"
            lines.append(f"@{domain}    {transport_name}\n")
        elif cfg.get("type") == "forward":
            forward_to = cfg.get("forward_to", "")
            lines.append(f"@{domain}    {forward_to}\n")
    
    try:
        with open(POSTFIX_VIRTUAL, 'w') as f:
            f.writelines(lines)
        run_command(f"postmap {POSTFIX_VIRTUAL}", check=False, silent=True)
    except IOError:
        return False
    
    # Generate master.cf entries for catchall domains
    _update_master_cf(config)
    
    # Update main.cf virtual settings
    _update_virtual_settings(config)
    
    # Install pipe script if needed
    catchall_domains = [d for d, c in config.items() if c.get("type") == "catchall" and c.get("active", True)]
    if catchall_domains:
        _install_vexo_pipe()
    
    return True


def _update_master_cf(config):
    """Update master.cf with pipe transports."""
    try:
        with open(POSTFIX_MASTER_CF, 'r') as f:
            content = f.read()
        
        # Remove existing vexo entries
        lines = content.split('\n')
        new_lines = []
        skip_next = False
        
        for line in lines:
            if '# vexo-start' in line:
                skip_next = True
                continue
            if '# vexo-end' in line:
                skip_next = False
                continue
            if skip_next:
                continue
            new_lines.append(line)
        
        # Add new entries
        new_lines.append("# vexo-start")
        
        for domain, cfg in config.items():
            if cfg.get("type") == "catchall" and cfg.get("active", True):
                transport_name = f"laravel-{domain.replace('.', '-')}"
                new_lines.append(f"{transport_name} unix - n n - - pipe")
                new_lines.append(f"  flags=F user=www-data argv={VEXO_PIPE_SCRIPT} {domain}")
        
        new_lines.append("# vexo-end")
        
        with open(POSTFIX_MASTER_CF, 'w') as f:
            f.write('\n'.join(new_lines))
        
        return True
    except IOError:
        return False


def _update_virtual_settings(config):
    """Update main.cf virtual alias settings."""
    from modules.email.postfix.utils import set_postfix_settings
    
    active_domains = [d for d, c in config.items() if c.get("active", True)]
    
    if active_domains:
        settings = {
            "virtual_alias_domains": ", ".join(active_domains),
            "virtual_alias_maps": f"hash:{POSTFIX_VIRTUAL}",
        }
    else:
        settings = {
            "virtual_alias_domains": "",
            "virtual_alias_maps": "",
        }
    
    set_postfix_settings(settings)


def _install_vexo_pipe():
    """Install the vexo-pipe script."""
    script_content = '''#!/bin/bash
DOMAIN="$1"
CONFIG_FILE="/etc/vexo/email-domains.json"
LOG_FILE="/var/log/vexo-email.log"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "$(date): ERROR - Config file not found" >> "$LOG_FILE"
    exit 75
fi

PATH_VALUE=$(jq -r ".\\\"$DOMAIN\\\".path" "$CONFIG_FILE")
CMD_VALUE=$(jq -r ".\\\"$DOMAIN\\\".command" "$CONFIG_FILE")

if [ "$PATH_VALUE" == "null" ] || [ -z "$PATH_VALUE" ]; then
    echo "$(date): ERROR - Domain $DOMAIN not configured" >> "$LOG_FILE"
    exit 75
fi

echo "$(date): Incoming email for $DOMAIN -> $CMD_VALUE" >> "$LOG_FILE"

cd "$PATH_VALUE" && /usr/bin/php artisan $CMD_VALUE 2>> "$LOG_FILE"
exit $?
'''
    
    try:
        # Install jq if needed
        from utils.shell import is_installed
        if not is_installed("jq"):
            run_command("apt install -y jq", check=False, silent=True)
        
        with open(VEXO_PIPE_SCRIPT, 'w') as f:
            f.write(script_content)
        os.chmod(VEXO_PIPE_SCRIPT, 0o755)
        
        if not os.path.exists(VEXO_EMAIL_LOG):
            with open(VEXO_EMAIL_LOG, 'w') as f:
                f.write("")
            os.chmod(VEXO_EMAIL_LOG, 0o666)
        
        return True
    except IOError:
        return False
```

**Step 2: Commit**

```bash
git add modules/email/postfix/domains.py
git commit -m "feat(email): add Postfix domain management"
```

---

## Task 5: Create Postfix Queue Module

**Files:**
- Create: `modules/email/postfix/queue.py`

**Step 1: Create queue.py**

```python
"""Postfix queue management."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, require_root
from modules.email.postfix.utils import is_postfix_ready


def show_queue_menu():
    """Display queue management menu."""
    def get_status():
        result = run_command("postqueue -p 2>/dev/null | grep -c '^[A-F0-9]'", check=False, silent=True)
        try:
            count = int(result.stdout.strip())
        except ValueError:
            count = 0
        return f"Queue: {count} message(s)"
    
    options = [
        ("view", "1. View Queue"),
        ("flush", "2. Flush Queue"),
        ("hold", "3. Hold/Release Messages"),
        ("delete", "4. Delete Messages"),
        ("requeue", "5. Requeue All"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "view": view_queue,
        "flush": flush_queue,
        "hold": hold_release_menu,
        "delete": delete_messages,
        "requeue": requeue_all,
    }
    
    run_menu_loop("Queue Management", options, handlers, get_status)


def view_queue():
    """Display mail queue."""
    clear_screen()
    show_header()
    show_panel("Mail Queue", title="Queue Management", style="cyan")
    
    if not is_postfix_ready():
        show_error("Postfix is not running.")
        press_enter_to_continue()
        return
    
    result = run_command("postqueue -p", check=False, silent=True)
    
    if result.returncode == 0:
        output = result.stdout.strip()
        if "Mail queue is empty" in output or not output:
            show_info("Mail queue is empty.")
        else:
            console.print("[bold]Mail Queue:[/bold]")
            console.print()
            console.print(output)
    else:
        show_error("Failed to get queue status.")
    
    press_enter_to_continue()


def flush_queue():
    """Attempt to deliver all queued messages."""
    clear_screen()
    show_header()
    show_panel("Flush Queue", title="Queue Management", style="cyan")
    
    if not is_postfix_ready():
        show_error("Postfix is not running.")
        press_enter_to_continue()
        return
    
    console.print("[bold]This will attempt to deliver all queued messages immediately.[/bold]")
    console.print()
    
    if not confirm_action("Flush mail queue?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    result = run_command("postqueue -f", check=False, silent=True)
    
    if result.returncode == 0:
        show_success("Queue flush initiated!")
        console.print("[dim]Messages will be delivered in the background.[/dim]")
    else:
        show_error("Failed to flush queue.")
    
    press_enter_to_continue()


def hold_release_menu():
    """Hold or release messages."""
    clear_screen()
    show_header()
    show_panel("Hold/Release Messages", title="Queue Management", style="cyan")
    
    options = [
        "Hold all messages",
        "Release all held messages",
        "Hold specific message",
        "Release specific message",
    ]
    
    choice = select_from_list("Action", "Select:", options)
    if not choice:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if "Hold all" in choice:
        result = run_command("postsuper -h ALL", check=False, silent=True)
        if result.returncode == 0:
            show_success("All messages held!")
        else:
            show_error("Failed to hold messages.")
    elif "Release all" in choice:
        result = run_command("postsuper -H ALL", check=False, silent=True)
        if result.returncode == 0:
            show_success("All messages released!")
        else:
            show_error("Failed to release messages.")
    elif "Hold specific" in choice:
        queue_id = text_input("Queue ID:")
        if queue_id:
            result = run_command(f"postsuper -h {queue_id}", check=False, silent=True)
            if result.returncode == 0:
                show_success(f"Message {queue_id} held!")
            else:
                show_error("Failed to hold message.")
    else:
        queue_id = text_input("Queue ID:")
        if queue_id:
            result = run_command(f"postsuper -H {queue_id}", check=False, silent=True)
            if result.returncode == 0:
                show_success(f"Message {queue_id} released!")
            else:
                show_error("Failed to release message.")
    
    press_enter_to_continue()


def delete_messages():
    """Delete queued messages."""
    clear_screen()
    show_header()
    show_panel("Delete Messages", title="Queue Management", style="red")
    
    if not is_postfix_ready():
        show_error("Postfix is not running.")
        press_enter_to_continue()
        return
    
    options = [
        "Delete ALL messages",
        "Delete specific message",
        "Delete by recipient",
    ]
    
    choice = select_from_list("Action", "Select:", options)
    if not choice:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if "ALL" in choice:
        console.print("[bold red]WARNING: This will permanently delete ALL queued emails![/bold red]")
        if not confirm_action("Delete all queued messages?"):
            return
        
        result = run_command("postsuper -d ALL", check=False, silent=True)
        if result.returncode == 0:
            show_success("All queued messages deleted!")
        else:
            show_error("Failed to delete messages.")
    
    elif "specific" in choice:
        queue_id = text_input("Queue ID:")
        if queue_id:
            result = run_command(f"postsuper -d {queue_id}", check=False, silent=True)
            if result.returncode == 0:
                show_success(f"Message {queue_id} deleted!")
            else:
                show_error("Failed to delete message.")
    
    else:
        recipient = text_input("Recipient email:")
        if recipient:
            # Find and delete by recipient
            result = run_command(
                f"postqueue -p | grep -B2 '{recipient}' | grep '^[A-F0-9]' | cut -d' ' -f1 | cut -d'*' -f1",
                check=False, silent=True
            )
            
            if result.stdout.strip():
                queue_ids = result.stdout.strip().split('\n')
                console.print(f"Found {len(queue_ids)} message(s) for {recipient}")
                
                if confirm_action("Delete these messages?"):
                    for qid in queue_ids:
                        if qid.strip():
                            run_command(f"postsuper -d {qid.strip()}", check=False, silent=True)
                    show_success(f"Deleted {len(queue_ids)} message(s)!")
            else:
                show_info(f"No messages found for {recipient}")
    
    press_enter_to_continue()


def requeue_all():
    """Requeue all deferred messages."""
    clear_screen()
    show_header()
    show_panel("Requeue All", title="Queue Management", style="cyan")
    
    console.print("[bold]This will requeue all deferred messages for immediate retry.[/bold]")
    console.print()
    
    if not confirm_action("Requeue all deferred messages?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    result = run_command("postsuper -r ALL", check=False, silent=True)
    
    if result.returncode == 0:
        show_success("All messages requeued!")
    else:
        show_error("Failed to requeue messages.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/email/postfix/queue.py
git commit -m "feat(email): add Postfix queue management"
```

---

## Task 6: Create Placeholder Files for Other Modules

**Files:**
- Create: `modules/email/dovecot/__init__.py`
- Create: `modules/email/webmail/__init__.py`

**Step 1: Create placeholder modules**

```python
# modules/email/dovecot/__init__.py
"""Dovecot mailbox server management (optional)."""

from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_info, press_enter_to_continue,
)
from ui.menu import run_menu_loop
from utils.shell import is_installed, is_service_running


def show_menu():
    """Display Dovecot Management submenu."""
    def get_status():
        if not is_installed("dovecot-core"):
            return "Dovecot: [dim]Not Installed[/dim]"
        if is_service_running("dovecot"):
            return "Dovecot: [green]Running[/green]"
        return "Dovecot: [red]Stopped[/red]"
    
    def get_options():
        if is_installed("dovecot-core"):
            return [
                ("mailboxes", "1. Mailbox Management"),
                ("quota", "2. Quota Settings"),
                ("ssl", "3. SSL/TLS Certificates"),
                ("service", "4. Service Control"),
                ("back", "← Back"),
            ]
        return [
            ("install", "1. Install Dovecot"),
            ("back", "← Back"),
        ]
    
    def get_handlers():
        return {
            "install": _coming_soon,
            "mailboxes": _coming_soon,
            "quota": _coming_soon,
            "ssl": _coming_soon,
            "service": _coming_soon,
        }
    
    run_menu_loop("Dovecot Mailbox Server", get_options, get_handlers(), get_status)


def _coming_soon():
    """Placeholder for features to be implemented."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Dovecot", style="yellow")
    show_info("This feature will be implemented in a future update.")
    press_enter_to_continue()
```

```python
# modules/email/webmail/__init__.py
"""Roundcube webmail management (optional)."""

import os

from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_info, press_enter_to_continue,
)
from ui.menu import run_menu_loop
from utils.shell import is_installed


def show_menu():
    """Display Webmail Management submenu."""
    def get_status():
        if os.path.exists("/var/www/roundcube") or is_installed("roundcube"):
            return "Roundcube: [green]Installed[/green]"
        return "Roundcube: [dim]Not Installed[/dim]"
    
    def get_options():
        installed = os.path.exists("/var/www/roundcube") or is_installed("roundcube")
        
        if installed:
            return [
                ("config", "1. Configure"),
                ("plugins", "2. Plugins"),
                ("update", "3. Update"),
                ("back", "← Back"),
            ]
        return [
            ("install", "1. Install Roundcube"),
            ("back", "← Back"),
        ]
    
    def get_handlers():
        return {
            "install": _coming_soon,
            "config": _coming_soon,
            "plugins": _coming_soon,
            "update": _coming_soon,
        }
    
    run_menu_loop("Webmail (Roundcube)", get_options, get_handlers(), get_status)


def _coming_soon():
    """Placeholder for features to be implemented."""
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Webmail", style="yellow")
    show_info("This feature will be implemented in a future update.")
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/email/dovecot/__init__.py modules/email/webmail/__init__.py
git commit -m "feat(email): add placeholder modules for Dovecot and Webmail"
```

---

## Execution Handoff

Plan 01 complete. This creates the foundation for email module with Postfix core functionality.
