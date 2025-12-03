"""Firewall (UFW) management module for vexo-cli."""

from ui.components import (
    console,
    show_panel,
    show_table,
    show_success,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import (
    run_command,
    run_command_with_progress,
    is_installed,
    is_service_running,
    require_root,
)


def show_menu():
    """Display the Firewall (UFW) submenu."""
    def get_status():
        return f"UFW Status: {_get_ufw_status()}"
    
    def get_options():
        options = []
        if is_installed("ufw"):
            options.extend([
                ("status", "1. Show Status"),
                ("enable", "2. Enable Firewall"),
                ("disable", "3. Disable Firewall"),
                ("add_port", "4. Add Custom Port"),
                ("add_email", "5. Add Email Ports"),
                ("remove_port", "6. Remove Port"),
                ("list_rules", "7. List Rules"),
            ])
        else:
            options.append(("install", "1. Install UFW"))
        options.append(("back", "← Back to Main Menu"))
        return options
    
    handlers = {
        "install": install_ufw,
        "status": show_status,
        "enable": enable_firewall,
        "disable": disable_firewall,
        "add_port": add_port_interactive,
        "add_email": add_email_ports,
        "remove_port": remove_port_interactive,
        "list_rules": list_rules,
    }
    
    run_menu_loop("Firewall (UFW)", get_options, handlers, get_status)


def _get_ufw_status():
    """Get UFW status string for display."""
    if not is_installed("ufw"):
        return "[dim]Not installed[/dim]"
    
    result = run_command("ufw status", check=False, silent=True)
    if result.returncode == 0:
        if "inactive" in result.stdout.lower():
            return "[yellow]Inactive[/yellow]"
        elif "active" in result.stdout.lower():
            return "[green]Active[/green]"
    return "[dim]Unknown[/dim]"


def install_ufw():
    """Install UFW if not already installed."""
    if is_installed("ufw"):
        show_info("UFW is already installed.")
        return True
    
    show_info("Installing UFW...")
    
    result = run_command_with_progress(
        "apt install -y ufw",
        "Installing UFW..."
    )
    
    if result.returncode != 0:
        show_error("Failed to install UFW.")
        return False
    
    show_success("UFW installed successfully!")
    return True


def enable_firewall():
    """Enable UFW with default security rules."""
    clear_screen()
    show_header()
    show_panel("Enable Firewall", title="Firewall (UFW)", style="cyan")
    
    console.print("[bold]This will configure UFW with:[/bold]")
    console.print("  • Default: deny incoming, allow outgoing")
    console.print("  • Allow SSH (port 22)")
    console.print("  • Allow HTTP (port 80)")
    console.print("  • Allow HTTPS (port 443)")
    console.print()
    
    # Check if already active
    result = run_command("ufw status", check=False, silent=True)
    if result.returncode == 0 and "active" in result.stdout.lower() and "inactive" not in result.stdout.lower():
        show_info("UFW is already active.")
        if not confirm_action("Reconfigure with default rules?"):
            press_enter_to_continue()
            return
    
    if not confirm_action("Enable firewall with these rules?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Install if needed
    if not is_installed("ufw"):
        if not install_ufw():
            press_enter_to_continue()
            return
    
    show_info("Configuring firewall rules...")
    
    # Reset to defaults
    run_command("ufw --force reset", check=False, silent=True)
    
    # Set default policies
    run_command("ufw default deny incoming", check=False, silent=True)
    run_command("ufw default allow outgoing", check=False, silent=True)
    
    # Allow essential ports
    rules = [
        ("22/tcp", "SSH"),
        ("80/tcp", "HTTP"),
        ("443/tcp", "HTTPS"),
    ]
    
    for port, name in rules:
        result = run_command(f"ufw allow {port}", check=False, silent=True)
        if result.returncode == 0:
            console.print(f"  [green]✓[/green] Allowed {name} ({port})")
        else:
            console.print(f"  [red]✗[/red] Failed to allow {name}")
    
    # Enable UFW
    console.print()
    show_info("Enabling UFW...")
    
    result = run_command("ufw --force enable", check=False, silent=True)
    
    if result.returncode == 0:
        show_success("Firewall enabled successfully!")
        console.print()
        console.print("[dim]Run 'Show Status' to verify configuration.[/dim]")
    else:
        show_error("Failed to enable UFW.")
    
    press_enter_to_continue()


def disable_firewall():
    """Disable UFW firewall."""
    clear_screen()
    show_header()
    show_panel("Disable Firewall", title="Firewall (UFW)", style="cyan")
    
    if not is_installed("ufw"):
        show_error("UFW is not installed.")
        press_enter_to_continue()
        return
    
    result = run_command("ufw status", check=False, silent=True)
    if "inactive" in result.stdout.lower():
        show_info("UFW is already disabled.")
        press_enter_to_continue()
        return
    
    console.print("[red bold]WARNING: Disabling the firewall will expose all ports![/red bold]")
    console.print()
    console.print("[yellow]This is NOT recommended for production servers.[/yellow]")
    console.print()
    
    if not confirm_action("Are you sure you want to disable the firewall?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    result = run_command("ufw --force disable", check=False, silent=True)
    
    if result.returncode == 0:
        show_warning("Firewall disabled!")
        console.print("[dim]Your server is now unprotected.[/dim]")
    else:
        show_error("Failed to disable UFW.")
    
    press_enter_to_continue()


def add_port_interactive():
    """Interactive prompt to add a custom port."""
    clear_screen()
    show_header()
    show_panel("Add Custom Port", title="Firewall (UFW)", style="cyan")
    
    if not is_installed("ufw"):
        show_error("UFW is not installed. Enable firewall first.")
        press_enter_to_continue()
        return
    
    port = text_input(
        title="Add Port",
        message="Enter port number (e.g., 8080):"
    )
    
    if not port:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Validate port
    try:
        port_num = int(port)
        if port_num < 1 or port_num > 65535:
            raise ValueError()
    except ValueError:
        show_error("Invalid port number. Must be between 1 and 65535.")
        press_enter_to_continue()
        return
    
    # Ask for protocol
    protocol = select_from_list(
        title="Protocol",
        message="Select protocol:",
        options=["tcp", "udp", "both"]
    )
    
    if not protocol:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = add_port(port, protocol)
    
    if success:
        show_success(f"Port {port}/{protocol} added successfully!")
    else:
        show_error(f"Failed to add port {port}")
    
    press_enter_to_continue()


def add_port(port, protocol="tcp"):
    """
    Add a port to UFW rules.
    
    Args:
        port: Port number
        protocol: 'tcp', 'udp', or 'both'
    
    Returns:
        bool: True if successful
    """
    if protocol == "both":
        result1 = run_command(f"ufw allow {port}/tcp", check=False, silent=True)
        result2 = run_command(f"ufw allow {port}/udp", check=False, silent=True)
        return result1.returncode == 0 and result2.returncode == 0
    else:
        result = run_command(f"ufw allow {port}/{protocol}", check=False, silent=True)
        return result.returncode == 0


def add_email_ports():
    """Add email-related ports (25, 587, 465)."""
    clear_screen()
    show_header()
    show_panel("Add Email Ports", title="Firewall (UFW)", style="cyan")
    
    if not is_installed("ufw"):
        show_error("UFW is not installed. Enable firewall first.")
        press_enter_to_continue()
        return
    
    console.print("[bold]This will open the following ports:[/bold]")
    console.print("  • Port 25/tcp  - SMTP (mail transfer)")
    console.print("  • Port 587/tcp - SMTP Submission (sending mail)")
    console.print("  • Port 465/tcp - SMTPS (SMTP over SSL)")
    console.print()
    console.print("[dim]Only enable these if you're running a mail server[/dim]")
    console.print("[dim]that needs to receive mail from the internet.[/dim]")
    console.print()
    
    if not confirm_action("Add email ports?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    email_ports = [
        ("25", "SMTP"),
        ("587", "SMTP Submission"),
        ("465", "SMTPS"),
    ]
    
    all_success = True
    for port, name in email_ports:
        result = run_command(f"ufw allow {port}/tcp", check=False, silent=True)
        if result.returncode == 0:
            console.print(f"  [green]✓[/green] Allowed {name} (port {port})")
        else:
            console.print(f"  [red]✗[/red] Failed to add {name}")
            all_success = False
    
    console.print()
    if all_success:
        show_success("Email ports added successfully!")
    else:
        show_warning("Some ports may have failed to add.")
    
    press_enter_to_continue()


def remove_port_interactive():
    """Interactive prompt to remove a port rule."""
    clear_screen()
    show_header()
    show_panel("Remove Port", title="Firewall (UFW)", style="cyan")
    
    if not is_installed("ufw"):
        show_error("UFW is not installed.")
        press_enter_to_continue()
        return
    
    # Get current rules
    rules = _get_ufw_rules()
    
    if not rules:
        show_info("No rules to remove (or unable to list rules).")
        press_enter_to_continue()
        return
    
    # Display rules
    console.print("[bold]Current rules:[/bold]")
    for i, rule in enumerate(rules, 1):
        console.print(f"  {i}. {rule}")
    console.print()
    
    rule_num = text_input(
        title="Remove Rule",
        message="Enter rule number to remove:"
    )
    
    if not rule_num:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        num = int(rule_num)
        if num < 1 or num > len(rules):
            raise ValueError()
    except ValueError:
        show_error("Invalid rule number.")
        press_enter_to_continue()
        return
    
    selected_rule = rules[num - 1]
    
    if not confirm_action(f"Remove rule: {selected_rule}?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # UFW uses 'delete' with rule number
    result = run_command(f"ufw --force delete {num}", check=False, silent=True)
    
    if result.returncode == 0:
        show_success("Rule removed successfully!")
    else:
        show_error("Failed to remove rule.")
    
    press_enter_to_continue()


def _get_ufw_rules():
    """Get list of UFW rules."""
    result = run_command("ufw status numbered", check=False, silent=True)
    if result.returncode != 0:
        return []
    
    rules = []
    for line in result.stdout.strip().split('\n'):
        # Parse lines like "[ 1] 22/tcp                     ALLOW IN    Anywhere"
        if line.strip().startswith('['):
            # Extract rule part after the number
            parts = line.split(']', 1)
            if len(parts) > 1:
                rules.append(parts[1].strip())
    
    return rules


def list_rules():
    """Display all UFW rules."""
    clear_screen()
    show_header()
    show_panel("Firewall Rules", title="Firewall (UFW)", style="cyan")
    
    if not is_installed("ufw"):
        show_error("UFW is not installed.")
        press_enter_to_continue()
        return
    
    result = run_command("ufw status numbered", check=False, silent=True)
    
    if result.returncode != 0:
        show_error("Failed to get UFW rules.")
        press_enter_to_continue()
        return
    
    console.print("[bold]UFW Rules:[/bold]")
    console.print()
    console.print(result.stdout)
    
    press_enter_to_continue()


def show_status():
    """Display detailed UFW status."""
    clear_screen()
    show_header()
    show_panel("Firewall Status", title="Firewall (UFW)", style="cyan")
    
    if not is_installed("ufw"):
        show_error("UFW is not installed.")
        console.print()
        console.print("[dim]Use 'Enable Firewall' to install and configure UFW.[/dim]")
        press_enter_to_continue()
        return
    
    result = run_command("ufw status verbose", check=False, silent=True)
    
    if result.returncode != 0:
        show_error("Failed to get UFW status.")
        press_enter_to_continue()
        return
    
    console.print("[bold]UFW Status:[/bold]")
    console.print()
    console.print(result.stdout)
    
    # Show app profiles if any
    console.print()
    result_apps = run_command("ufw app list", check=False, silent=True)
    if result_apps.returncode == 0 and "Available applications" in result_apps.stdout:
        console.print("[bold]Available App Profiles:[/bold]")
        console.print(result_apps.stdout)
    
    press_enter_to_continue()
