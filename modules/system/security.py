"""Security hardening - SSH settings, unattended upgrades."""

from utils.error_handler import handle_error
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
from ui.menu import confirm_action, text_input, run_menu_loop
from utils.shell import run_command, run_command_with_progress, is_installed, require_root


def show_security_menu():
    """Display Security Hardening submenu."""
    def get_status():
        root_login = _get_ssh_setting("PermitRootLogin")
        ssh_port = _get_ssh_setting("Port") or "22"
        return f"SSH Port: {ssh_port} | Root Login: {root_login or 'default'}"
    
    options = [
        ("root_login", "1. Disable Root SSH Login"),
        ("ssh_port", "2. Change SSH Port"),
        ("unattended", "3. Enable Unattended Upgrades"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "root_login": toggle_root_login,
        "ssh_port": change_ssh_port,
        "unattended": setup_unattended_upgrades,
    }
    
    run_menu_loop("Security Hardening", options, handlers, get_status)


def _get_ssh_setting(key):
    """Get SSH config setting."""
    result = run_command(f"grep -E '^{key}' /etc/ssh/sshd_config", check=False, silent=True)
    if result.returncode == 0 and result.stdout.strip():
        parts = result.stdout.strip().split()
        if len(parts) >= 2:
            return parts[1]
    return None


def toggle_root_login():
    """Enable or disable root SSH login."""
    clear_screen()
    show_header()
    show_panel("Root SSH Login", title="Security Hardening", style="cyan")
    
    current = _get_ssh_setting("PermitRootLogin") or "yes (default)"
    console.print(f"Current setting: [cyan]{current}[/cyan]")
    console.print()
    
    result = run_command("grep -Po '^sudo.+:\\K.*$' /etc/group", check=False, silent=True)
    sudo_users = result.stdout.strip() if result.returncode == 0 else ""
    
    if sudo_users:
        console.print(f"[dim]Users with sudo access: {sudo_users}[/dim]")
    else:
        show_warning("⚠️  No other users have sudo access!")
        show_warning("Create a sudo user before disabling root login!")
        press_enter_to_continue()
        return
    
    console.print()
    
    if current in ["no", "prohibit-password"]:
        action = "enable"
        new_value = "yes"
        msg = "Enable root SSH login?"
    else:
        action = "disable"
        new_value = "no"
        msg = "Disable root SSH login?"
    
    if not confirm_action(msg):
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    sshd_config = "/etc/ssh/sshd_config"
    
    result = run_command(f"grep -q '^PermitRootLogin' {sshd_config}", check=False, silent=True)
    if result.returncode == 0:
        run_command(f"sed -i 's/^PermitRootLogin.*/PermitRootLogin {new_value}/' {sshd_config}", check=False, silent=True)
    else:
        try:
            with open(sshd_config, "a") as f:
                f.write(f"\nPermitRootLogin {new_value}\n")
        except (PermissionError, IOError) as e:
            handle_error("E1005", f"Failed to update sshd_config: {e}")
            press_enter_to_continue()
            return
    
    run_command("systemctl restart sshd", check=False, silent=True)
    
    show_success(f"Root SSH login {action}d.")
    press_enter_to_continue()


def change_ssh_port():
    """Change SSH port."""
    clear_screen()
    show_header()
    show_panel("Change SSH Port", title="Security Hardening", style="cyan")
    
    current_port = _get_ssh_setting("Port") or "22"
    console.print(f"Current SSH port: [cyan]{current_port}[/cyan]")
    console.print()
    
    show_warning("⚠️  IMPORTANT: Make sure the new port is open in firewall")
    show_warning("    before closing this SSH session!")
    console.print()
    
    new_port = text_input("Enter new SSH port (1024-65535):")
    if not new_port:
        press_enter_to_continue()
        return
    
    try:
        port = int(new_port)
        if port < 1024 or port > 65535:
            raise ValueError()
    except ValueError:
        handle_error("E1005", "Invalid port. Must be between 1024 and 65535.")
        press_enter_to_continue()
        return
    
    result = run_command(f"ss -tuln | grep -q ':{port} '", check=False, silent=True)
    if result.returncode == 0:
        handle_error("E1005", f"Port {port} is already in use.")
        press_enter_to_continue()
        return
    
    if not confirm_action(f"Change SSH port from {current_port} to {port}?"):
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    sshd_config = "/etc/ssh/sshd_config"
    
    result = run_command(f"grep -q '^Port' {sshd_config}", check=False, silent=True)
    if result.returncode == 0:
        run_command(f"sed -i 's/^Port.*/Port {port}/' {sshd_config}", check=False, silent=True)
    else:
        try:
            with open(sshd_config, "a") as f:
                f.write(f"\nPort {port}\n")
        except (PermissionError, IOError) as e:
            handle_error("E1005", f"Failed to update sshd_config: {e}")
            press_enter_to_continue()
            return
    
    if is_installed("ufw"):
        result = run_command("ufw status", check=False, silent=True)
        if "active" in result.stdout.lower():
            if confirm_action(f"Open port {port} in UFW firewall?"):
                run_command(f"ufw allow {port}/tcp", check=False, silent=True)
                show_success(f"Port {port} opened in UFW.")
    
    run_command("systemctl restart sshd", check=False, silent=True)
    
    show_success(f"SSH port changed to {port}")
    show_warning(f"Connect with: ssh -p {port} user@host")
    press_enter_to_continue()


def setup_unattended_upgrades():
    """Setup unattended security upgrades."""
    clear_screen()
    show_header()
    show_panel("Unattended Upgrades", title="Security Hardening", style="cyan")
    
    if is_installed("unattended-upgrades"):
        show_info("Unattended upgrades is already installed.")
        result = run_command("systemctl is-enabled unattended-upgrades", check=False, silent=True)
        status = "enabled" if result.returncode == 0 else "disabled"
        console.print(f"[dim]Status: {status}[/dim]")
        console.print()
        
        if not confirm_action("Reconfigure unattended upgrades?"):
            press_enter_to_continue()
            return
    else:
        if not confirm_action("Install and enable unattended security upgrades?"):
            press_enter_to_continue()
            return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if not is_installed("unattended-upgrades"):
        show_info("Installing unattended-upgrades...")
        result = run_command_with_progress(
            "apt install -y unattended-upgrades",
            "Installing..."
        )
        if result.returncode != 0:
            handle_error("E1005", "Failed to install.")
            press_enter_to_continue()
            return
    
    auto_reboot = confirm_action("Enable automatic reboot when required? (recommended: No)")
    
    reboot_time = "02:00"
    if auto_reboot:
        time_input = text_input("Reboot time (HH:MM, default 02:00):")
        if time_input:
            reboot_time = time_input
    
    config = f'''Unattended-Upgrade::Allowed-Origins {{
    "${{distro_id}}:${{distro_codename}}-security";
    "${{distro_id}}ESMApps:${{distro_codename}}-apps-security";
    "${{distro_id}}ESM:${{distro_codename}}-infra-security";
}};
Unattended-Upgrade::Automatic-Reboot "{str(auto_reboot).lower()}";
Unattended-Upgrade::Automatic-Reboot-Time "{reboot_time}";
'''
    
    try:
        with open("/etc/apt/apt.conf.d/50unattended-upgrades", "w") as f:
            f.write(config)
    except (PermissionError, IOError) as e:
        handle_error("E1005", f"Failed to write config: {e}")
        press_enter_to_continue()
        return
    
    periodic = '''APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
'''
    
    try:
        with open("/etc/apt/apt.conf.d/20auto-upgrades", "w") as f:
            f.write(periodic)
    except (PermissionError, IOError) as e:
        handle_error("E1005", f"Failed to write config: {e}")
        press_enter_to_continue()
        return
    
    run_command("systemctl enable unattended-upgrades", check=False, silent=True)
    run_command("systemctl start unattended-upgrades", check=False, silent=True)
    
    show_success("Unattended upgrades configured!")
    show_info("Security updates will be installed automatically.")
    press_enter_to_continue()
