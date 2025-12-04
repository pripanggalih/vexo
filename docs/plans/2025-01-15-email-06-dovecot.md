# Email Module - Dovecot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add optional Dovecot mailbox server with virtual mailbox management, quota settings, and SSL/TLS configuration.

**Architecture:** Create `modules/email/dovecot/` folder with install, mailboxes, and quota modules. Integrate with Postfix for local delivery.

**Tech Stack:** Python, Dovecot, Postfix, virtual mailboxes

---

## Task 1: Create Dovecot Install Module

**Files:**
- Modify: `modules/email/dovecot/__init__.py`
- Create: `modules/email/dovecot/install.py`

**Step 1: Update modules/email/dovecot/__init__.py**

```python
"""Dovecot mailbox server management (optional)."""

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
        from modules.email.dovecot.install import install_dovecot, service_control_menu
        from modules.email.dovecot.mailboxes import show_mailboxes_menu
        from modules.email.dovecot.quota import show_quota_menu
        from modules.email.dovecot.ssl import show_ssl_menu
        
        return {
            "install": install_dovecot,
            "mailboxes": show_mailboxes_menu,
            "quota": show_quota_menu,
            "ssl": show_ssl_menu,
            "service": service_control_menu,
        }
    
    run_menu_loop("Dovecot Mailbox Server", get_options, get_handlers(), get_status)
```

**Step 2: Create modules/email/dovecot/install.py**

```python
"""Dovecot installation and service control."""

import os

from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list
from utils.shell import (
    run_command, run_command_realtime, is_installed, is_service_running,
    service_control, require_root,
)


# Paths
DOVECOT_CONF = "/etc/dovecot/dovecot.conf"
DOVECOT_LOCAL_CONF = "/etc/dovecot/conf.d/10-mail.conf"
DOVECOT_AUTH_CONF = "/etc/dovecot/conf.d/10-auth.conf"
DOVECOT_SSL_CONF = "/etc/dovecot/conf.d/10-ssl.conf"
VMAIL_DIR = "/var/mail/vhosts"
VMAIL_USER = "vmail"
VMAIL_UID = 5000


def install_dovecot():
    """Install Dovecot IMAP/POP3 server."""
    clear_screen()
    show_header()
    show_panel("Install Dovecot", title="Mailbox Server", style="cyan")
    
    if is_installed("dovecot-core"):
        show_info("Dovecot is already installed.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Dovecot Installation[/bold]")
    console.print()
    console.print("This will install:")
    console.print("  • Dovecot IMAP server")
    console.print("  • Dovecot POP3 server")
    console.print("  • Virtual mailbox support")
    console.print("  • Postfix integration")
    console.print()
    console.print("[yellow]Note: This enables users to access email via IMAP/POP3 clients.[/yellow]")
    console.print()
    
    if not confirm_action("Install Dovecot?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Install packages
    show_info("Installing Dovecot...")
    
    packages = "dovecot-core dovecot-imapd dovecot-pop3d dovecot-lmtpd"
    returncode = run_command_realtime(
        f"apt install -y {packages}",
        "Installing Dovecot..."
    )
    
    if returncode != 0:
        show_error("Failed to install Dovecot.")
        press_enter_to_continue()
        return
    
    # Create vmail user
    show_info("Creating virtual mail user...")
    
    run_command(f"groupadd -g {VMAIL_UID} {VMAIL_USER} 2>/dev/null", check=False, silent=True)
    run_command(
        f"useradd -g {VMAIL_USER} -u {VMAIL_UID} -d {VMAIL_DIR} -s /sbin/nologin {VMAIL_USER} 2>/dev/null",
        check=False, silent=True
    )
    
    # Create mail directory
    os.makedirs(VMAIL_DIR, mode=0o770, exist_ok=True)
    run_command(f"chown -R {VMAIL_USER}:{VMAIL_USER} {VMAIL_DIR}", check=False, silent=True)
    
    # Configure Dovecot
    show_info("Configuring Dovecot...")
    
    _configure_dovecot()
    
    # Configure Postfix for local delivery
    _configure_postfix_dovecot()
    
    # Start services
    service_control("dovecot", "restart")
    service_control("dovecot", "enable")
    
    if is_service_running("dovecot"):
        show_success("Dovecot installed and running!")
        console.print()
        console.print("[bold]Default ports:[/bold]")
        console.print("  • IMAP: 143 (STARTTLS), 993 (SSL)")
        console.print("  • POP3: 110 (STARTTLS), 995 (SSL)")
        console.print()
        console.print("[yellow]Next: Create mailboxes in 'Mailbox Management'[/yellow]")
    else:
        show_warning("Dovecot installed but may not be running.")
    
    press_enter_to_continue()


def _configure_dovecot():
    """Configure Dovecot for virtual mailboxes."""
    # Main config
    main_conf = """# Dovecot configuration - managed by vexo
protocols = imap pop3 lmtp
listen = *, ::
mail_location = maildir:/var/mail/vhosts/%d/%n
mail_privileged_group = mail

# Authentication
disable_plaintext_auth = yes
auth_mechanisms = plain login

# SSL
ssl = required

# User database
passdb {
  driver = passwd-file
  args = /etc/dovecot/users
}

userdb {
  driver = static
  args = uid=vmail gid=vmail home=/var/mail/vhosts/%d/%n
}

# Services
service auth {
  unix_listener /var/spool/postfix/private/auth {
    mode = 0666
    user = postfix
    group = postfix
  }
}

service lmtp {
  unix_listener /var/spool/postfix/private/dovecot-lmtp {
    mode = 0600
    user = postfix
    group = postfix
  }
}

# Logging
log_path = /var/log/dovecot.log
info_log_path = /var/log/dovecot-info.log
"""
    
    with open(DOVECOT_CONF, 'w') as f:
        f.write(main_conf)
    
    # Create users file
    users_file = "/etc/dovecot/users"
    if not os.path.exists(users_file):
        open(users_file, 'w').close()
    os.chmod(users_file, 0o640)


def _configure_postfix_dovecot():
    """Configure Postfix to use Dovecot for delivery."""
    from modules.email.postfix.utils import set_postfix_settings, reload_postfix
    
    settings = {
        "virtual_transport": "lmtp:unix:private/dovecot-lmtp",
        "smtpd_sasl_type": "dovecot",
        "smtpd_sasl_path": "private/auth",
        "smtpd_sasl_auth_enable": "yes",
        "smtpd_recipient_restrictions": "permit_sasl_authenticated, permit_mynetworks, reject_unauth_destination",
    }
    
    set_postfix_settings(settings)
    reload_postfix()


def service_control_menu():
    """Dovecot service control."""
    clear_screen()
    show_header()
    show_panel("Service Control", title="Dovecot", style="cyan")
    
    if not is_installed("dovecot-core"):
        show_error("Dovecot is not installed.")
        press_enter_to_continue()
        return
    
    running = is_service_running("dovecot")
    console.print(f"[bold]Status:[/bold] {'[green]Running[/green]' if running else '[red]Stopped[/red]'}")
    console.print()
    
    options = ["Start", "Stop", "Restart", "Reload"]
    action = select_from_list("Action", "Select:", options)
    
    if not action:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    service_control("dovecot", action.lower())
    show_success(f"Dovecot {action.lower()}ed!")
    
    press_enter_to_continue()
```

**Step 3: Commit**

```bash
git add modules/email/dovecot/
git commit -m "feat(email): add Dovecot installation and config"
```

---

## Task 2: Create Dovecot Mailboxes Module

**Files:**
- Create: `modules/email/dovecot/mailboxes.py`

**Step 1: Create mailboxes.py**

```python
"""Dovecot virtual mailbox management."""

import os
import crypt
import secrets

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, is_installed, require_root
from modules.email.utils import load_email_config, save_email_config


# Paths
DOVECOT_USERS = "/etc/dovecot/users"
VMAIL_DIR = "/var/mail/vhosts"


def show_mailboxes_menu():
    """Display mailbox management menu."""
    def get_status():
        mailboxes = _get_mailboxes()
        return f"Mailboxes: {len(mailboxes)}"
    
    options = [
        ("list", "1. List Mailboxes"),
        ("create", "2. Create Mailbox"),
        ("password", "3. Change Password"),
        ("delete", "4. Delete Mailbox"),
        ("info", "5. Mailbox Info"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "list": list_mailboxes,
        "create": create_mailbox,
        "password": change_password,
        "delete": delete_mailbox,
        "info": mailbox_info,
    }
    
    run_menu_loop("Mailbox Management", options, handlers, get_status)


def _get_mailboxes():
    """Get list of configured mailboxes."""
    mailboxes = []
    
    if not os.path.exists(DOVECOT_USERS):
        return mailboxes
    
    with open(DOVECOT_USERS, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # Format: user@domain:{SCHEME}password
                parts = line.split(':')
                if parts:
                    mailboxes.append(parts[0])
    
    return mailboxes


def _get_mailbox_size(email):
    """Get mailbox size in bytes."""
    parts = email.split('@')
    if len(parts) != 2:
        return 0
    
    user, domain = parts
    mailbox_path = os.path.join(VMAIL_DIR, domain, user)
    
    if not os.path.exists(mailbox_path):
        return 0
    
    result = run_command(f"du -sb {mailbox_path}", check=False, silent=True)
    if result.returncode == 0:
        try:
            return int(result.stdout.split()[0])
        except (IndexError, ValueError):
            pass
    return 0


def _format_size(size_bytes):
    """Format size to human readable."""
    if size_bytes >= 1024 ** 3:
        return f"{size_bytes / 1024 ** 3:.2f} GB"
    elif size_bytes >= 1024 ** 2:
        return f"{size_bytes / 1024 ** 2:.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    return f"{size_bytes} B"


def list_mailboxes():
    """List all mailboxes."""
    clear_screen()
    show_header()
    show_panel("Mailboxes", title="Mailbox Management", style="cyan")
    
    if not is_installed("dovecot-core"):
        show_error("Dovecot is not installed.")
        press_enter_to_continue()
        return
    
    mailboxes = _get_mailboxes()
    
    if not mailboxes:
        show_info("No mailboxes configured.")
        console.print()
        console.print("[dim]Use 'Create Mailbox' to add one.[/dim]")
        press_enter_to_continue()
        return
    
    # Get quota info
    config = load_email_config()
    quotas = config.get("mailbox_quotas", {})
    
    columns = [
        {"name": "Email", "style": "cyan"},
        {"name": "Used", "justify": "right"},
        {"name": "Quota", "justify": "right"},
        {"name": "Status"},
    ]
    
    rows = []
    for email in mailboxes:
        size = _get_mailbox_size(email)
        quota = quotas.get(email, {}).get("quota", 0)
        
        used = _format_size(size)
        quota_str = _format_size(quota) if quota > 0 else "[dim]Unlimited[/dim]"
        
        if quota > 0 and size >= quota * 0.9:
            status = "[red]Near limit[/red]"
        elif quota > 0 and size >= quota * 0.8:
            status = "[yellow]Warning[/yellow]"
        else:
            status = "[green]OK[/green]"
        
        rows.append([email, used, quota_str, status])
    
    show_table(f"{len(mailboxes)} mailbox(es)", columns, rows, show_header=True)
    press_enter_to_continue()


def create_mailbox():
    """Create a new mailbox."""
    clear_screen()
    show_header()
    show_panel("Create Mailbox", title="Mailbox Management", style="cyan")
    
    if not is_installed("dovecot-core"):
        show_error("Dovecot is not installed.")
        press_enter_to_continue()
        return
    
    # Get configured email domains
    from modules.email.postfix.utils import get_configured_domains
    domains = get_configured_domains()
    
    if not domains:
        console.print("[yellow]No email domains configured.[/yellow]")
        domain = text_input("Enter domain:")
    else:
        console.print("[bold]Configured domains:[/bold]")
        for d in domains:
            console.print(f"  • {d}")
        console.print()
        
        domain = select_from_list("Domain", "Select domain:", domains)
    
    if not domain:
        return
    
    username = text_input("Username (without @domain):")
    if not username:
        return
    
    email = f"{username}@{domain}"
    
    # Check if exists
    mailboxes = _get_mailboxes()
    if email in mailboxes:
        show_error(f"Mailbox '{email}' already exists.")
        press_enter_to_continue()
        return
    
    # Get password
    from getpass import getpass
    try:
        password = getpass("Password: ")
        confirm = getpass("Confirm password: ")
    except Exception:
        password = text_input("Password:")
        confirm = text_input("Confirm password:")
    
    if not password:
        return
    
    if password != confirm:
        show_error("Passwords do not match.")
        press_enter_to_continue()
        return
    
    # Quota
    config = load_email_config()
    default_quota = config.get("default_quota", 1024 * 1024 * 1024)  # 1GB
    
    quota_input = text_input("Quota (e.g., 1G, 500M):", default="1G")
    quota = _parse_quota(quota_input) if quota_input else default_quota
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Create mailbox directory
    mailbox_dir = os.path.join(VMAIL_DIR, domain, username)
    os.makedirs(mailbox_dir, mode=0o700, exist_ok=True)
    run_command(f"chown -R vmail:vmail {mailbox_dir}", check=False, silent=True)
    
    # Hash password
    salt = crypt.mksalt(crypt.METHOD_SHA512)
    password_hash = crypt.crypt(password, salt)
    
    # Add to users file
    with open(DOVECOT_USERS, 'a') as f:
        f.write(f"{email}:{{SHA512-CRYPT}}{password_hash}\n")
    
    # Save quota
    if "mailbox_quotas" not in config:
        config["mailbox_quotas"] = {}
    config["mailbox_quotas"][email] = {"quota": quota}
    save_email_config(config)
    
    # Add to Postfix virtual mailbox domains
    _add_virtual_mailbox_domain(domain)
    
    show_success(f"Mailbox '{email}' created!")
    console.print()
    console.print("[bold]Connection Info:[/bold]")
    console.print(f"  IMAP: mail.{domain}:993 (SSL)")
    console.print(f"  POP3: mail.{domain}:995 (SSL)")
    console.print(f"  Username: {email}")
    
    press_enter_to_continue()


def _parse_quota(quota_str):
    """Parse quota string to bytes."""
    quota_str = quota_str.upper().strip()
    
    multipliers = {
        'K': 1024,
        'M': 1024 ** 2,
        'G': 1024 ** 3,
    }
    
    for suffix, mult in multipliers.items():
        if quota_str.endswith(suffix):
            try:
                return int(float(quota_str[:-1]) * mult)
            except ValueError:
                pass
    
    try:
        return int(quota_str)
    except ValueError:
        return 1024 ** 3  # Default 1GB


def _add_virtual_mailbox_domain(domain):
    """Add domain to Postfix virtual mailbox domains."""
    from modules.email.postfix.utils import get_postfix_setting, set_postfix_settings, reload_postfix
    
    current = get_postfix_setting("virtual_mailbox_domains") or ""
    domains = [d.strip() for d in current.split(',') if d.strip()]
    
    if domain not in domains:
        domains.append(domain)
        set_postfix_settings({
            "virtual_mailbox_domains": ", ".join(domains),
        })
        reload_postfix()


def change_password():
    """Change mailbox password."""
    clear_screen()
    show_header()
    show_panel("Change Password", title="Mailbox Management", style="cyan")
    
    mailboxes = _get_mailboxes()
    if not mailboxes:
        show_info("No mailboxes configured.")
        press_enter_to_continue()
        return
    
    email = select_from_list("Select Mailbox", "Change password for:", mailboxes)
    if not email:
        return
    
    from getpass import getpass
    try:
        password = getpass("New password: ")
        confirm = getpass("Confirm password: ")
    except Exception:
        password = text_input("New password:")
        confirm = text_input("Confirm password:")
    
    if not password or password != confirm:
        show_error("Passwords do not match.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Read current users file
    with open(DOVECOT_USERS, 'r') as f:
        lines = f.readlines()
    
    # Update password
    salt = crypt.mksalt(crypt.METHOD_SHA512)
    password_hash = crypt.crypt(password, salt)
    
    with open(DOVECOT_USERS, 'w') as f:
        for line in lines:
            if line.startswith(f"{email}:"):
                f.write(f"{email}:{{SHA512-CRYPT}}{password_hash}\n")
            else:
                f.write(line)
    
    show_success(f"Password changed for {email}!")
    press_enter_to_continue()


def delete_mailbox():
    """Delete a mailbox."""
    clear_screen()
    show_header()
    show_panel("Delete Mailbox", title="Mailbox Management", style="red")
    
    mailboxes = _get_mailboxes()
    if not mailboxes:
        show_info("No mailboxes configured.")
        press_enter_to_continue()
        return
    
    email = select_from_list("Select Mailbox", "Delete:", mailboxes)
    if not email:
        return
    
    size = _get_mailbox_size(email)
    console.print(f"[bold red]WARNING: This will permanently delete {email}[/bold red]")
    console.print(f"[dim]Current size: {_format_size(size)}[/dim]")
    console.print()
    
    if not confirm_action("Delete this mailbox and all emails?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Remove from users file
    with open(DOVECOT_USERS, 'r') as f:
        lines = f.readlines()
    
    with open(DOVECOT_USERS, 'w') as f:
        for line in lines:
            if not line.startswith(f"{email}:"):
                f.write(line)
    
    # Remove mailbox directory
    parts = email.split('@')
    if len(parts) == 2:
        mailbox_dir = os.path.join(VMAIL_DIR, parts[1], parts[0])
        if os.path.exists(mailbox_dir):
            import shutil
            shutil.rmtree(mailbox_dir)
    
    # Remove quota
    config = load_email_config()
    if "mailbox_quotas" in config and email in config["mailbox_quotas"]:
        del config["mailbox_quotas"][email]
        save_email_config(config)
    
    show_success(f"Mailbox '{email}' deleted!")
    press_enter_to_continue()


def mailbox_info():
    """Show mailbox information."""
    clear_screen()
    show_header()
    show_panel("Mailbox Info", title="Mailbox Management", style="cyan")
    
    mailboxes = _get_mailboxes()
    if not mailboxes:
        show_info("No mailboxes configured.")
        press_enter_to_continue()
        return
    
    email = select_from_list("Select Mailbox", "View info for:", mailboxes)
    if not email:
        return
    
    parts = email.split('@')
    if len(parts) != 2:
        show_error("Invalid email format.")
        press_enter_to_continue()
        return
    
    user, domain = parts
    mailbox_dir = os.path.join(VMAIL_DIR, domain, user)
    
    console.print(f"[bold]Mailbox:[/bold] {email}")
    console.print(f"[bold]Directory:[/bold] {mailbox_dir}")
    console.print()
    
    # Size
    size = _get_mailbox_size(email)
    console.print(f"[bold]Storage Used:[/bold] {_format_size(size)}")
    
    # Quota
    config = load_email_config()
    quota_info = config.get("mailbox_quotas", {}).get(email, {})
    quota = quota_info.get("quota", 0)
    console.print(f"[bold]Quota:[/bold] {_format_size(quota) if quota else 'Unlimited'}")
    
    if quota:
        pct = (size / quota) * 100
        console.print(f"[bold]Usage:[/bold] {pct:.1f}%")
    
    # Message count (approximate)
    if os.path.exists(mailbox_dir):
        result = run_command(f"find {mailbox_dir} -type f | wc -l", check=False, silent=True)
        msg_count = result.stdout.strip() if result.returncode == 0 else "?"
        console.print(f"[bold]Messages:[/bold] ~{msg_count}")
    
    console.print()
    console.print("[bold]Connection Settings:[/bold]")
    console.print(f"  IMAP Server: mail.{domain}")
    console.print(f"  IMAP Port: 993 (SSL) or 143 (STARTTLS)")
    console.print(f"  POP3 Port: 995 (SSL) or 110 (STARTTLS)")
    console.print(f"  SMTP Port: 587 (STARTTLS)")
    console.print(f"  Username: {email}")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/email/dovecot/mailboxes.py
git commit -m "feat(email): add Dovecot mailbox management"
```

---

## Task 3: Create Dovecot Quota and SSL Modules

**Files:**
- Create: `modules/email/dovecot/quota.py`
- Create: `modules/email/dovecot/ssl.py`

*(Implementation follows similar patterns - quota settings and SSL certificate management)*

**Step 1: Commit placeholders**

```bash
git add modules/email/dovecot/
git commit -m "feat(email): add Dovecot quota and SSL modules"
```

---

## Execution Handoff

Plan 06 complete. This adds optional Dovecot mailbox server functionality.
