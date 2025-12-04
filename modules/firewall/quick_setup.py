"""Quick setup functions for firewall."""

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_success,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import confirm_action
from utils.shell import (
from utils.error_handler import handle_error
    run_command,
    run_command_with_progress,
    is_installed,
    require_root,
)
from modules.firewall.common import is_ufw_installed, is_ufw_active


def install_ufw():
    """Install UFW if not already installed."""
    clear_screen()
    show_header()
    show_panel("Install UFW", title="Firewall (UFW)", style="cyan")
    
    if is_installed("ufw"):
        show_info("UFW is already installed.")
        press_enter_to_continue()
        return True
    
    if not confirm_action("Install UFW firewall?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return False
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return False
    
    show_info("Installing UFW...")
    
    result = run_command_with_progress(
        "apt install -y ufw",
        "Installing UFW..."
    )
    
    if result.returncode != 0:
        handle_error("E6001", "Failed to install UFW.")
        press_enter_to_continue()
        return False
    
    show_success("UFW installed successfully!")
    press_enter_to_continue()
    return True


def enable_firewall():
    """Enable UFW with default security rules."""
    clear_screen()
    show_header()
    show_panel("Enable Firewall", title="Firewall (UFW)", style="cyan")
    
    console.print("[bold]This will configure UFW with:[/bold]")
    console.print("  - Default: deny incoming, allow outgoing")
    console.print("  - Allow SSH (port 22)")
    console.print("  - Allow HTTP (port 80)")
    console.print("  - Allow HTTPS (port 443)")
    console.print()
    
    if is_ufw_active():
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
    
    if not is_ufw_installed():
        if not install_ufw():
            return
    
    show_info("Configuring firewall rules...")
    
    run_command("ufw --force reset", check=False, silent=True)
    run_command("ufw default deny incoming", check=False, silent=True)
    run_command("ufw default allow outgoing", check=False, silent=True)
    
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
    
    console.print()
    show_info("Enabling UFW...")
    
    result = run_command("ufw --force enable", check=False, silent=True)
    
    if result.returncode == 0:
        show_success("Firewall enabled successfully!")
    else:
        handle_error("E6001", "Failed to enable UFW.")
    
    press_enter_to_continue()


def disable_firewall():
    """Disable UFW firewall."""
    clear_screen()
    show_header()
    show_panel("Disable Firewall", title="Firewall (UFW)", style="cyan")
    
    if not is_ufw_installed():
        handle_error("E6001", "UFW is not installed.")
        press_enter_to_continue()
        return
    
    if not is_ufw_active():
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
        handle_error("E6001", "Failed to disable UFW.")
    
    press_enter_to_continue()
