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
