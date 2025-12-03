"""User management - list, add, delete users, SSH keys."""

import os
import re
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
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, run_command_realtime, require_root


def show_users_menu():
    """Display User Management submenu."""
    options = [
        ("list", "1. List Users"),
        ("add", "2. Add New User"),
        ("ssh_key", "3. Add SSH Key to User"),
        ("delete", "4. Delete User"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "list": list_users,
        "add": add_user,
        "ssh_key": add_ssh_key,
        "delete": delete_user,
    }
    
    run_menu_loop("User Management", options, handlers)


def _user_has_ssh_key(username):
    """Check if user has SSH authorized_keys."""
    home = f"/home/{username}"
    if username == "root":
        home = "/root"
    auth_keys = f"{home}/.ssh/authorized_keys"
    return os.path.exists(auth_keys) and os.path.getsize(auth_keys) > 0


def list_users():
    """List system users with UID >= 1000."""
    clear_screen()
    show_header()
    show_panel("System Users", title="User Management", style="cyan")
    
    result = run_command("awk -F: '$3 >= 1000 && $3 < 65534 {print $1\":\"$3\":\"$7}' /etc/passwd", check=False, silent=True)
    if result.returncode != 0:
        show_error("Failed to list users.")
        press_enter_to_continue()
        return
    
    users = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        parts = line.split(':')
        if len(parts) >= 3:
            username, uid, shell = parts[0], parts[1], parts[2]
            
            grp_result = run_command(f"groups {username}", check=False, silent=True)
            groups = grp_result.stdout.strip().split(':')[-1].strip() if grp_result.returncode == 0 else ""
            
            ssh_key = "Yes" if _user_has_ssh_key(username) else "No"
            
            users.append([username, uid, groups, ssh_key])
    
    if not users:
        show_info("No regular users found (UID >= 1000).")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Username", "style": "cyan"},
        {"name": "UID", "style": "white"},
        {"name": "Groups", "style": "white"},
        {"name": "SSH Key", "style": "white"},
    ]
    
    show_table("", columns, users, show_header=True)
    press_enter_to_continue()


def add_user():
    """Add a new system user."""
    clear_screen()
    show_header()
    show_panel("Add New User", title="User Management", style="cyan")
    
    username = text_input("Enter username (lowercase, alphanumeric):")
    if not username:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if not re.match(r'^[a-z][a-z0-9_-]*$', username):
        show_error("Invalid username. Use lowercase letters, numbers, underscore, dash.")
        show_error("Must start with a letter.")
        press_enter_to_continue()
        return
    
    result = run_command(f"id {username}", check=False, silent=True)
    if result.returncode == 0:
        show_error(f"User '{username}' already exists.")
        press_enter_to_continue()
        return
    
    add_sudo = confirm_action("Add to sudo group?")
    set_password = confirm_action("Set password now? (No = SSH key only)")
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    cmd = f"useradd -m -s /bin/bash {username}"
    result = run_command(cmd, check=False, silent=True)
    if result.returncode != 0:
        show_error(f"Failed to create user: {result.stderr}")
        press_enter_to_continue()
        return
    
    show_success(f"User '{username}' created.")
    
    if add_sudo:
        run_command(f"usermod -aG sudo {username}", check=False, silent=True)
        show_success("Added to sudo group.")
    
    if set_password:
        console.print()
        show_info("Set password for user (input hidden):")
        returncode = run_command_realtime(f"passwd {username}", "Setting password...")
        if returncode == 0:
            show_success("Password set.")
        else:
            show_warning("Password not set. User can only login via SSH key.")
    
    if confirm_action("Add SSH key now?"):
        _add_ssh_key_for_user(username)
    
    press_enter_to_continue()


def add_ssh_key():
    """Add SSH key to existing user."""
    clear_screen()
    show_header()
    show_panel("Add SSH Key", title="User Management", style="cyan")
    
    result = run_command("awk -F: '$3 >= 1000 && $3 < 65534 {print $1}' /etc/passwd", check=False, silent=True)
    if result.returncode != 0:
        show_error("Failed to list users.")
        press_enter_to_continue()
        return
    
    users = [u.strip() for u in result.stdout.strip().split('\n') if u.strip()]
    if not users:
        show_error("No regular users found.")
        press_enter_to_continue()
        return
    
    username = select_from_list("Select User", "Choose user:", users)
    if not username:
        return
    
    _add_ssh_key_for_user(username)
    press_enter_to_continue()


def _add_ssh_key_for_user(username):
    """Helper to add SSH key for a user."""
    console.print()
    console.print("[bold]Paste the public SSH key (ssh-rsa or ssh-ed25519):[/bold]")
    ssh_key = text_input("SSH public key:")
    
    if not ssh_key:
        show_warning("No key provided.")
        return
    
    if not (ssh_key.startswith("ssh-rsa ") or ssh_key.startswith("ssh-ed25519 ")):
        show_error("Invalid SSH key format. Must start with 'ssh-rsa' or 'ssh-ed25519'.")
        return
    
    try:
        require_root()
    except PermissionError:
        return
    
    home = f"/home/{username}"
    ssh_dir = f"{home}/.ssh"
    auth_keys = f"{ssh_dir}/authorized_keys"
    
    run_command(f"mkdir -p {ssh_dir}", check=False, silent=True)
    run_command(f"chmod 700 {ssh_dir}", check=False, silent=True)
    run_command(f"chown {username}:{username} {ssh_dir}", check=False, silent=True)
    
    try:
        with open(auth_keys, "a") as f:
            f.write(ssh_key.strip() + "\n")
    except (PermissionError, IOError) as e:
        show_error(f"Failed to write SSH key: {e}")
        return
    
    run_command(f"chmod 600 {auth_keys}", check=False, silent=True)
    run_command(f"chown {username}:{username} {auth_keys}", check=False, silent=True)
    
    show_success(f"SSH key added for {username}.")


def delete_user():
    """Delete a system user."""
    clear_screen()
    show_header()
    show_panel("Delete User", title="User Management", style="cyan")
    
    show_warning("⚠️  This action cannot be undone!")
    console.print()
    
    current_user = os.environ.get("SUDO_USER", os.environ.get("USER", ""))
    
    result = run_command("awk -F: '$3 >= 1000 && $3 < 65534 {print $1}' /etc/passwd", check=False, silent=True)
    if result.returncode != 0:
        show_error("Failed to list users.")
        press_enter_to_continue()
        return
    
    users = [u.strip() for u in result.stdout.strip().split('\n') if u.strip() and u.strip() != current_user]
    if not users:
        show_info("No deletable users found.")
        press_enter_to_continue()
        return
    
    username = select_from_list("Select User", "Choose user to delete:", users)
    if not username:
        return
    
    delete_home = confirm_action(f"Delete home directory (/home/{username})?")
    
    console.print()
    console.print(f"[bold red]Type '{username}' to confirm deletion:[/bold red]")
    confirm_text = text_input("Confirm username:")
    
    if confirm_text != username:
        show_warning("Username mismatch. Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    cmd = f"userdel {'-r ' if delete_home else ''}{username}"
    result = run_command(cmd, check=False, silent=True)
    
    if result.returncode == 0:
        show_success(f"User '{username}' deleted.")
    else:
        show_error(f"Failed to delete user: {result.stderr}")
    
    press_enter_to_continue()
