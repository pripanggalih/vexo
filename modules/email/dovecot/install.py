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
    main_conf = """# Dovecot configuration - managed by vexo-cli
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
