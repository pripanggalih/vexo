# System Setup Enhancements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add 6 new features to System Setup menu: Hostname & Timezone, User Management, Swap Management, Security Hardening, System Cleanup, and Reboot/Shutdown.

**Architecture:** All features will be added to `modules/system.py`. Each feature group with submenus uses `run_menu_loop`. Single actions use direct handlers. Pattern follows existing codebase conventions.

**Tech Stack:** Python, InquirerPy (existing), system commands (hostnamectl, timedatectl, useradd, etc.)

---

## Task 1: Update Imports and Menu Structure

**Files:**
- Modify: `modules/system.py:1-60`

**Step 1: Update imports**

Add `text_input`, `select_from_list`, `show_submenu` to imports:

```python
from ui.menu import confirm_action, text_input, select_from_list, show_submenu, run_menu_loop
```

**Step 2: Update show_menu() with new options**

```python
def show_menu():
    """Display the System Setup submenu."""
    options = [
        ("info", "1. Show System Info"),
        ("update", "2. Update & Upgrade System"),
        ("tools", "3. Install Basic Tools"),
        ("hostname", "4. Hostname & Timezone"),
        ("users", "5. User Management"),
        ("swap", "6. Swap Management"),
        ("security", "7. Security Hardening"),
        ("cleanup", "8. System Cleanup"),
        ("power", "9. Reboot / Shutdown"),
        ("back", "← Back to Main Menu"),
    ]
    
    handlers = {
        "info": show_system_info,
        "update": update_system,
        "tools": install_basic_tools,
        "hostname": show_hostname_menu,
        "users": show_users_menu,
        "swap": show_swap_menu,
        "security": show_security_menu,
        "cleanup": system_cleanup,
        "power": show_power_menu,
    }
    
    run_menu_loop("System Setup & Update", options, handlers)
```

**Step 3: Verify syntax**

Run: `python3 -m py_compile modules/system.py`
Expected: No output (success)

**Step 4: Commit**

```bash
git add modules/system.py
git commit -m "feat(system): update menu structure for new features"
```

---

## Task 2: Hostname & Timezone Feature

**Files:**
- Modify: `modules/system.py` (append after existing functions)

**Step 1: Add timezone constants**

```python
# Popular timezones for quick selection
POPULAR_TIMEZONES = [
    ("Asia/Jakarta", "Asia/Jakarta (WIB)"),
    ("Asia/Makassar", "Asia/Makassar (WITA)"),
    ("Asia/Jayapura", "Asia/Jayapura (WIT)"),
    ("Asia/Singapore", "Asia/Singapore"),
    ("Asia/Tokyo", "Asia/Tokyo"),
    ("UTC", "UTC"),
]
```

**Step 2: Add show_hostname_menu()**

```python
def show_hostname_menu():
    """Display Hostname & Timezone submenu."""
    options = [
        ("change_hostname", "1. Change Hostname"),
        ("set_timezone", "2. Set Timezone"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "change_hostname": change_hostname,
        "set_timezone": set_timezone,
    }
    
    run_menu_loop("Hostname & Timezone", options, handlers)
```

**Step 3: Add change_hostname()**

```python
def change_hostname():
    """Change system hostname."""
    clear_screen()
    show_header()
    show_panel("Change Hostname", title="System Setup", style="cyan")
    
    current = get_hostname()
    console.print(f"Current hostname: [cyan]{current}[/cyan]")
    console.print()
    
    new_hostname = text_input("Enter new hostname:")
    if not new_hostname:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Validate hostname
    import re
    if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', new_hostname):
        show_error("Invalid hostname. Use alphanumeric and hyphens only.")
        show_error("Must start and end with alphanumeric character.")
        press_enter_to_continue()
        return
    
    if not confirm_action(f"Change hostname from '{current}' to '{new_hostname}'?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Update hostname
    result = run_command(f"hostnamectl set-hostname {new_hostname}", check=False, silent=True)
    if result.returncode != 0:
        show_error("Failed to set hostname.")
        press_enter_to_continue()
        return
    
    # Update /etc/hosts
    run_command(f"sed -i 's/{current}/{new_hostname}/g' /etc/hosts", check=False, silent=True)
    
    show_success(f"Hostname changed to '{new_hostname}'")
    show_warning("A reboot may be required for full effect.")
    press_enter_to_continue()
```

**Step 4: Add set_timezone()**

```python
def set_timezone():
    """Set system timezone."""
    clear_screen()
    show_header()
    show_panel("Set Timezone", title="System Setup", style="cyan")
    
    # Get current timezone
    result = run_command("timedatectl show --property=Timezone --value", check=False, silent=True)
    current_tz = result.stdout.strip() if result.returncode == 0 else "Unknown"
    console.print(f"Current timezone: [cyan]{current_tz}[/cyan]")
    console.print()
    
    # Build options
    tz_options = [label for _, label in POPULAR_TIMEZONES]
    tz_options.append("Other (search)...")
    
    choice = select_from_list("Select Timezone", "Choose timezone:", tz_options)
    if not choice:
        return
    
    if choice == "Other (search)...":
        # Get all timezones
        result = run_command("timedatectl list-timezones", check=False, silent=True)
        if result.returncode != 0:
            show_error("Failed to list timezones.")
            press_enter_to_continue()
            return
        
        all_tz = result.stdout.strip().split('\n')
        timezone = select_from_list("All Timezones", "Search and select:", all_tz)
        if not timezone:
            return
    else:
        # Find the timezone value from label
        timezone = None
        for tz_val, tz_label in POPULAR_TIMEZONES:
            if tz_label == choice:
                timezone = tz_val
                break
    
    if not timezone:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    result = run_command(f"timedatectl set-timezone {timezone}", check=False, silent=True)
    if result.returncode == 0:
        show_success(f"Timezone set to {timezone}")
    else:
        show_error("Failed to set timezone.")
    
    press_enter_to_continue()
```

**Step 5: Commit**

```bash
git add modules/system.py
git commit -m "feat(system): add hostname and timezone management"
```

---

## Task 3: User Management Feature

**Files:**
- Modify: `modules/system.py` (append)

**Step 1: Add show_users_menu()**

```python
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
```

**Step 2: Add list_users()**

```python
def list_users():
    """List system users with UID >= 1000."""
    clear_screen()
    show_header()
    show_panel("System Users", title="User Management", style="cyan")
    
    # Get users with UID >= 1000
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
            
            # Check groups
            grp_result = run_command(f"groups {username}", check=False, silent=True)
            groups = grp_result.stdout.strip().split(':')[-1].strip() if grp_result.returncode == 0 else ""
            
            # Check SSH key
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


def _user_has_ssh_key(username):
    """Check if user has SSH authorized_keys."""
    import os
    home = f"/home/{username}"
    if username == "root":
        home = "/root"
    auth_keys = f"{home}/.ssh/authorized_keys"
    return os.path.exists(auth_keys) and os.path.getsize(auth_keys) > 0
```

**Step 3: Add add_user()**

```python
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
    
    # Validate username
    import re
    if not re.match(r'^[a-z][a-z0-9_-]*$', username):
        show_error("Invalid username. Use lowercase letters, numbers, underscore, dash.")
        show_error("Must start with a letter.")
        press_enter_to_continue()
        return
    
    # Check if exists
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
    
    # Create user
    cmd = f"useradd -m -s /bin/bash {username}"
    result = run_command(cmd, check=False, silent=True)
    if result.returncode != 0:
        show_error(f"Failed to create user: {result.stderr}")
        press_enter_to_continue()
        return
    
    show_success(f"User '{username}' created.")
    
    # Add to sudo
    if add_sudo:
        run_command(f"usermod -aG sudo {username}", check=False, silent=True)
        show_success("Added to sudo group.")
    
    # Set password
    if set_password:
        console.print()
        show_info("Set password for user (input hidden):")
        returncode = run_command_realtime(f"passwd {username}", "Setting password...")
        if returncode == 0:
            show_success("Password set.")
        else:
            show_warning("Password not set. User can only login via SSH key.")
    
    # Offer to add SSH key
    if confirm_action("Add SSH key now?"):
        _add_ssh_key_for_user(username)
    
    press_enter_to_continue()
```

**Step 4: Add add_ssh_key() and helper**

```python
def add_ssh_key():
    """Add SSH key to existing user."""
    clear_screen()
    show_header()
    show_panel("Add SSH Key", title="User Management", style="cyan")
    
    # Get list of users
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
    import os
    
    console.print()
    console.print("[bold]Paste the public SSH key (ssh-rsa or ssh-ed25519):[/bold]")
    ssh_key = text_input("SSH public key:")
    
    if not ssh_key:
        show_warning("No key provided.")
        return
    
    # Validate key format
    if not (ssh_key.startswith("ssh-rsa ") or ssh_key.startswith("ssh-ed25519 ")):
        show_error("Invalid SSH key format. Must start with 'ssh-rsa' or 'ssh-ed25519'.")
        return
    
    try:
        require_root()
    except PermissionError:
        return
    
    # Setup .ssh directory
    home = f"/home/{username}"
    ssh_dir = f"{home}/.ssh"
    auth_keys = f"{ssh_dir}/authorized_keys"
    
    run_command(f"mkdir -p {ssh_dir}", check=False, silent=True)
    run_command(f"chmod 700 {ssh_dir}", check=False, silent=True)
    run_command(f"chown {username}:{username} {ssh_dir}", check=False, silent=True)
    
    # Append key
    with open(auth_keys, "a") as f:
        f.write(ssh_key.strip() + "\n")
    
    run_command(f"chmod 600 {auth_keys}", check=False, silent=True)
    run_command(f"chown {username}:{username} {auth_keys}", check=False, silent=True)
    
    show_success(f"SSH key added for {username}.")
```

**Step 5: Add delete_user()**

```python
def delete_user():
    """Delete a system user."""
    clear_screen()
    show_header()
    show_panel("Delete User", title="User Management", style="cyan")
    
    show_warning("⚠️  This action cannot be undone!")
    console.print()
    
    # Get list of users (exclude root and current user)
    import os
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
    
    # Double confirmation
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
```

**Step 6: Commit**

```bash
git add modules/system.py
git commit -m "feat(system): add user management (list, add, ssh key, delete)"
```

---

## Task 4: Swap Management Feature

**Files:**
- Modify: `modules/system.py` (append)

**Step 1: Add show_swap_menu()**

```python
def show_swap_menu():
    """Display Swap Management submenu."""
    def get_status():
        swap_info = _get_swap_info()
        if swap_info['active']:
            return f"Swap: [green]{swap_info['size']}[/green] ({swap_info['used']} used)"
        return "Swap: [dim]Not configured[/dim]"
    
    options = [
        ("status", "1. Show Swap Status"),
        ("create", "2. Create Swap File"),
        ("remove", "3. Remove Swap"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "status": show_swap_status,
        "create": create_swap,
        "remove": remove_swap,
    }
    
    run_menu_loop("Swap Management", options, handlers, get_status)
```

**Step 2: Add swap helper functions**

```python
def _get_swap_info():
    """Get swap information."""
    result = run_command("swapon --show --noheadings --bytes", check=False, silent=True)
    if result.returncode != 0 or not result.stdout.strip():
        return {'active': False, 'size': '0', 'used': '0', 'path': None}
    
    # Parse first line
    parts = result.stdout.strip().split()
    if len(parts) >= 3:
        path = parts[0]
        size_bytes = int(parts[2]) if parts[2].isdigit() else 0
        used_bytes = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
        
        size_gb = size_bytes / (1024**3)
        used_mb = used_bytes / (1024**2)
        
        return {
            'active': True,
            'size': f"{size_gb:.1f} GB",
            'used': f"{used_mb:.0f} MB",
            'path': path,
            'size_bytes': size_bytes,
        }
    
    return {'active': False, 'size': '0', 'used': '0', 'path': None}


def _get_ram_gb():
    """Get total RAM in GB."""
    result = run_command("grep MemTotal /proc/meminfo", check=False, silent=True)
    if result.returncode == 0:
        parts = result.stdout.split()
        if len(parts) >= 2:
            kb = int(parts[1])
            return kb / (1024**2)
    return 2  # Default 2GB if can't detect
```

**Step 3: Add show_swap_status()**

```python
def show_swap_status():
    """Show detailed swap status."""
    clear_screen()
    show_header()
    show_panel("Swap Status", title="Swap Management", style="cyan")
    
    swap_info = _get_swap_info()
    ram_gb = _get_ram_gb()
    
    # Recommendation
    if ram_gb <= 2:
        recommended = f"{ram_gb * 2:.0f} GB (2x RAM)"
    else:
        recommended = f"{ram_gb:.0f} GB (equal to RAM)"
    
    columns = [
        {"name": "Property", "style": "cyan"},
        {"name": "Value", "style": "white"},
    ]
    
    rows = [
        ["Status", "[green]Active[/green]" if swap_info['active'] else "[dim]Inactive[/dim]"],
        ["Swap File", swap_info['path'] or "N/A"],
        ["Size", swap_info['size']],
        ["Used", swap_info['used']],
        ["Total RAM", f"{ram_gb:.1f} GB"],
        ["Recommended Swap", recommended],
    ]
    
    show_table("", columns, rows, show_header=False)
    
    # Show swappiness
    result = run_command("cat /proc/sys/vm/swappiness", check=False, silent=True)
    swappiness = result.stdout.strip() if result.returncode == 0 else "Unknown"
    console.print()
    console.print(f"[dim]Swappiness: {swappiness} (lower = less swap usage)[/dim]")
    
    press_enter_to_continue()
```

**Step 4: Add create_swap()**

```python
def create_swap():
    """Create a new swap file."""
    clear_screen()
    show_header()
    show_panel("Create Swap File", title="Swap Management", style="cyan")
    
    swap_info = _get_swap_info()
    if swap_info['active']:
        show_warning(f"Swap already exists: {swap_info['path']} ({swap_info['size']})")
        if not confirm_action("Remove existing swap and create new one?"):
            press_enter_to_continue()
            return
        # Will remove after getting new size
    
    ram_gb = _get_ram_gb()
    if ram_gb <= 2:
        default_size = int(ram_gb * 2)
    else:
        default_size = int(ram_gb)
    
    console.print(f"RAM: {ram_gb:.1f} GB | Recommended swap: {default_size} GB")
    console.print()
    
    size_input = text_input(f"Swap size in GB (default: {default_size}):")
    if size_input:
        try:
            swap_size = int(size_input)
        except ValueError:
            show_error("Invalid size. Enter a number.")
            press_enter_to_continue()
            return
    else:
        swap_size = default_size
    
    if swap_size < 1 or swap_size > 64:
        show_error("Swap size must be between 1 and 64 GB.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Remove existing swap if any
    if swap_info['active']:
        show_info("Removing existing swap...")
        run_command(f"swapoff {swap_info['path']}", check=False, silent=True)
        if swap_info['path']:
            run_command(f"rm -f {swap_info['path']}", check=False, silent=True)
    
    swapfile = "/swapfile"
    
    show_info(f"Creating {swap_size} GB swap file...")
    console.print()
    
    # Create swap file
    result = run_command_with_progress(
        f"fallocate -l {swap_size}G {swapfile}",
        "Allocating space..."
    )
    if result.returncode != 0:
        # Fallback to dd
        run_command_realtime(
            f"dd if=/dev/zero of={swapfile} bs=1G count={swap_size}",
            "Creating swap file..."
        )
    
    # Setup swap
    run_command(f"chmod 600 {swapfile}", check=False, silent=True)
    run_command(f"mkswap {swapfile}", check=False, silent=True)
    run_command(f"swapon {swapfile}", check=False, silent=True)
    
    # Add to fstab if not exists
    result = run_command(f"grep -q '{swapfile}' /etc/fstab", check=False, silent=True)
    if result.returncode != 0:
        with open("/etc/fstab", "a") as f:
            f.write(f"{swapfile} none swap sw 0 0\n")
    
    # Ask about swappiness
    console.print()
    if confirm_action("Set swappiness to 10? (recommended for VPS, default is 60)"):
        run_command("sysctl vm.swappiness=10", check=False, silent=True)
        # Make persistent
        result = run_command("grep -q 'vm.swappiness' /etc/sysctl.conf", check=False, silent=True)
        if result.returncode != 0:
            with open("/etc/sysctl.conf", "a") as f:
                f.write("vm.swappiness=10\n")
        else:
            run_command("sed -i 's/vm.swappiness=.*/vm.swappiness=10/' /etc/sysctl.conf", check=False, silent=True)
    
    show_success(f"Swap file created: {swap_size} GB")
    press_enter_to_continue()
```

**Step 5: Add remove_swap()**

```python
def remove_swap():
    """Remove swap file."""
    clear_screen()
    show_header()
    show_panel("Remove Swap", title="Swap Management", style="cyan")
    
    swap_info = _get_swap_info()
    if not swap_info['active']:
        show_info("No swap is currently active.")
        press_enter_to_continue()
        return
    
    show_warning(f"This will remove: {swap_info['path']} ({swap_info['size']})")
    
    if not confirm_action("Are you sure you want to remove swap?"):
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    swapfile = swap_info['path']
    
    run_command(f"swapoff {swapfile}", check=False, silent=True)
    run_command(f"rm -f {swapfile}", check=False, silent=True)
    
    # Remove from fstab
    run_command(f"sed -i '\\|{swapfile}|d' /etc/fstab", check=False, silent=True)
    
    show_success("Swap removed.")
    press_enter_to_continue()
```

**Step 6: Commit**

```bash
git add modules/system.py
git commit -m "feat(system): add swap management (status, create, remove)"
```

---

## Task 5: Security Hardening Feature

**Files:**
- Modify: `modules/system.py` (append)

**Step 1: Add show_security_menu()**

```python
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
```

**Step 2: Add toggle_root_login()**

```python
def toggle_root_login():
    """Enable or disable root SSH login."""
    clear_screen()
    show_header()
    show_panel("Root SSH Login", title="Security Hardening", style="cyan")
    
    current = _get_ssh_setting("PermitRootLogin") or "yes (default)"
    console.print(f"Current setting: [cyan]{current}[/cyan]")
    console.print()
    
    # Check if there are other sudo users
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
    
    # Update sshd_config
    sshd_config = "/etc/ssh/sshd_config"
    
    # Check if setting exists
    result = run_command(f"grep -q '^PermitRootLogin' {sshd_config}", check=False, silent=True)
    if result.returncode == 0:
        run_command(f"sed -i 's/^PermitRootLogin.*/PermitRootLogin {new_value}/' {sshd_config}", check=False, silent=True)
    else:
        with open(sshd_config, "a") as f:
            f.write(f"\nPermitRootLogin {new_value}\n")
    
    # Restart SSH
    run_command("systemctl restart sshd", check=False, silent=True)
    
    show_success(f"Root SSH login {action}d.")
    press_enter_to_continue()
```

**Step 3: Add change_ssh_port()**

```python
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
        show_error("Invalid port. Must be between 1024 and 65535.")
        press_enter_to_continue()
        return
    
    # Check if port in use
    result = run_command(f"ss -tuln | grep -q ':{port} '", check=False, silent=True)
    if result.returncode == 0:
        show_error(f"Port {port} is already in use.")
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
    
    # Update port
    result = run_command(f"grep -q '^Port' {sshd_config}", check=False, silent=True)
    if result.returncode == 0:
        run_command(f"sed -i 's/^Port.*/Port {port}/' {sshd_config}", check=False, silent=True)
    else:
        with open(sshd_config, "a") as f:
            f.write(f"\nPort {port}\n")
    
    # Offer to open in UFW
    if is_installed("ufw"):
        result = run_command("ufw status", check=False, silent=True)
        if "active" in result.stdout.lower():
            if confirm_action(f"Open port {port} in UFW firewall?"):
                run_command(f"ufw allow {port}/tcp", check=False, silent=True)
                show_success(f"Port {port} opened in UFW.")
    
    # Restart SSH
    run_command("systemctl restart sshd", check=False, silent=True)
    
    show_success(f"SSH port changed to {port}")
    show_warning(f"Connect with: ssh -p {port} user@host")
    press_enter_to_continue()
```

**Step 4: Add setup_unattended_upgrades()**

```python
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
    
    # Install
    if not is_installed("unattended-upgrades"):
        show_info("Installing unattended-upgrades...")
        result = run_command_with_progress(
            "apt install -y unattended-upgrades",
            "Installing..."
        )
        if result.returncode != 0:
            show_error("Failed to install.")
            press_enter_to_continue()
            return
    
    # Configure auto-reboot
    auto_reboot = confirm_action("Enable automatic reboot when required? (recommended: No)")
    
    reboot_time = "02:00"
    if auto_reboot:
        time_input = text_input("Reboot time (HH:MM, default 02:00):")
        if time_input:
            reboot_time = time_input
    
    # Write config
    config = f"""Unattended-Upgrade::Allowed-Origins {{
    "${{distro_id}}:${{distro_codename}}-security";
    "${{distro_id}}ESMApps:${{distro_codename}}-apps-security";
    "${{distro_id}}ESM:${{distro_codename}}-infra-security";
}};
Unattended-Upgrade::Automatic-Reboot "{str(auto_reboot).lower()}";
Unattended-Upgrade::Automatic-Reboot-Time "{reboot_time}";
"""
    
    with open("/etc/apt/apt.conf.d/50unattended-upgrades", "w") as f:
        f.write(config)
    
    # Enable periodic updates
    periodic = """APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
"""
    
    with open("/etc/apt/apt.conf.d/20auto-upgrades", "w") as f:
        f.write(periodic)
    
    # Enable service
    run_command("systemctl enable unattended-upgrades", check=False, silent=True)
    run_command("systemctl start unattended-upgrades", check=False, silent=True)
    
    show_success("Unattended upgrades configured!")
    show_info("Security updates will be installed automatically.")
    press_enter_to_continue()
```

**Step 5: Commit**

```bash
git add modules/system.py
git commit -m "feat(system): add security hardening (root login, ssh port, unattended upgrades)"
```

---

## Task 6: System Cleanup Feature

**Files:**
- Modify: `modules/system.py` (append)

**Step 1: Add system_cleanup()**

```python
def system_cleanup():
    """Clean up system: remove unused packages, clean cache, old kernels."""
    clear_screen()
    show_header()
    show_panel("System Cleanup", title="System Setup", style="cyan")
    
    console.print("[bold]This will:[/bold]")
    console.print("  • Remove unused packages (apt autoremove)")
    console.print("  • Clean apt cache (apt clean)")
    console.print("  • Remove old kernels (keep current + 1)")
    console.print("  • Clear journal logs older than 7 days")
    console.print()
    
    # Estimate space
    result = run_command("apt-get --dry-run autoremove 2>/dev/null | grep -oP '\\d+(?= to remove)'", check=False, silent=True)
    packages_to_remove = result.stdout.strip() if result.returncode == 0 else "0"
    
    result = run_command("du -sh /var/cache/apt/archives 2>/dev/null | cut -f1", check=False, silent=True)
    cache_size = result.stdout.strip() if result.returncode == 0 else "Unknown"
    
    result = run_command("journalctl --disk-usage 2>/dev/null | grep -oP '[\\d.]+[GMK]'", check=False, silent=True)
    journal_size = result.stdout.strip() if result.returncode == 0 else "Unknown"
    
    console.print(f"[dim]Packages to remove: {packages_to_remove}[/dim]")
    console.print(f"[dim]Apt cache size: {cache_size}[/dim]")
    console.print(f"[dim]Journal size: {journal_size}[/dim]")
    console.print()
    
    if not confirm_action("Proceed with cleanup?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print()
    
    # Autoremove
    show_info("Removing unused packages...")
    run_command_realtime("apt autoremove -y", "Autoremove...")
    
    # Clean cache
    show_info("Cleaning apt cache...")
    run_command("apt clean", check=False, silent=True)
    show_success("Apt cache cleaned.")
    
    # Clean old kernels (keep current + 1 previous)
    show_info("Checking old kernels...")
    current_kernel = run_command("uname -r", check=False, silent=True).stdout.strip()
    result = run_command(
        f"dpkg -l 'linux-image-*' | grep '^ii' | awk '{{print $2}}' | grep -v '{current_kernel}' | head -n -1",
        check=False, silent=True
    )
    old_kernels = [k.strip() for k in result.stdout.strip().split('\n') if k.strip() and 'linux-image' in k]
    
    if old_kernels:
        show_info(f"Removing {len(old_kernels)} old kernel(s)...")
        for kernel in old_kernels:
            run_command(f"apt remove -y {kernel}", check=False, silent=True)
    else:
        show_info("No old kernels to remove.")
    
    # Clean journal
    show_info("Cleaning journal logs...")
    run_command("journalctl --vacuum-time=7d", check=False, silent=True)
    show_success("Journal cleaned.")
    
    console.print()
    show_success("System cleanup completed!")
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/system.py
git commit -m "feat(system): add system cleanup"
```

---

## Task 7: Reboot/Shutdown Feature

**Files:**
- Modify: `modules/system.py` (append)

**Step 1: Add show_power_menu()**

```python
def show_power_menu():
    """Display Reboot/Shutdown submenu."""
    options = [
        ("reboot", "1. Reboot Now"),
        ("shutdown", "2. Shutdown Now"),
        ("schedule", "3. Schedule Reboot"),
        ("cancel", "4. Cancel Scheduled Reboot/Shutdown"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "reboot": reboot_now,
        "shutdown": shutdown_now,
        "schedule": schedule_reboot,
        "cancel": cancel_scheduled,
    }
    
    run_menu_loop("Reboot / Shutdown", options, handlers)
```

**Step 2: Add reboot_now()**

```python
def reboot_now():
    """Reboot the system immediately."""
    clear_screen()
    show_header()
    show_panel("Reboot System", title="System Setup", style="red")
    
    show_warning("⚠️  WARNING: This will REBOOT the server!")
    show_warning("All connections will be terminated.")
    console.print()
    
    console.print("[bold red]Type 'REBOOT' to confirm:[/bold red]")
    confirm_text = text_input("Confirm:")
    
    if confirm_text != "REBOOT":
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print()
    show_warning("Rebooting in 5 seconds... (Ctrl+C to cancel)")
    
    import time
    try:
        for i in range(5, 0, -1):
            console.print(f"[bold red]{i}...[/bold red]")
            time.sleep(1)
    except KeyboardInterrupt:
        console.print()
        show_info("Reboot cancelled.")
        press_enter_to_continue()
        return
    
    run_command("reboot", check=False, silent=True)
```

**Step 3: Add shutdown_now()**

```python
def shutdown_now():
    """Shutdown the system immediately."""
    clear_screen()
    show_header()
    show_panel("Shutdown System", title="System Setup", style="red")
    
    show_warning("⚠️  WARNING: This will SHUTDOWN the server!")
    show_warning("You will need physical/console access to turn it back on.")
    console.print()
    
    console.print("[bold red]Type 'SHUTDOWN' to confirm:[/bold red]")
    confirm_text = text_input("Confirm:")
    
    if confirm_text != "SHUTDOWN":
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print()
    show_warning("Shutting down in 5 seconds... (Ctrl+C to cancel)")
    
    import time
    try:
        for i in range(5, 0, -1):
            console.print(f"[bold red]{i}...[/bold red]")
            time.sleep(1)
    except KeyboardInterrupt:
        console.print()
        show_info("Shutdown cancelled.")
        press_enter_to_continue()
        return
    
    run_command("shutdown -h now", check=False, silent=True)
```

**Step 4: Add schedule_reboot() and cancel_scheduled()**

```python
def schedule_reboot():
    """Schedule a system reboot."""
    clear_screen()
    show_header()
    show_panel("Schedule Reboot", title="System Setup", style="cyan")
    
    minutes = text_input("Reboot in how many minutes?")
    if not minutes:
        press_enter_to_continue()
        return
    
    try:
        mins = int(minutes)
        if mins < 1:
            raise ValueError()
    except ValueError:
        show_error("Invalid number of minutes.")
        press_enter_to_continue()
        return
    
    if not confirm_action(f"Schedule reboot in {mins} minutes?"):
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    run_command(f"shutdown -r +{mins}", check=False, silent=True)
    show_success(f"Reboot scheduled in {mins} minutes.")
    show_info("Run 'Cancel Scheduled Reboot' to cancel.")
    press_enter_to_continue()


def cancel_scheduled():
    """Cancel any scheduled reboot/shutdown."""
    clear_screen()
    show_header()
    show_panel("Cancel Scheduled Reboot/Shutdown", title="System Setup", style="cyan")
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    result = run_command("shutdown -c", check=False, silent=True)
    if result.returncode == 0:
        show_success("Scheduled reboot/shutdown cancelled.")
    else:
        show_info("No scheduled reboot/shutdown to cancel.")
    
    press_enter_to_continue()
```

**Step 5: Commit**

```bash
git add modules/system.py
git commit -m "feat(system): add reboot and shutdown management"
```

---

## Task 8: Final Testing & Verification

**Step 1: Verify imports compile**

```bash
python3 -c "from modules import system; print('OK')"
```

**Step 2: Check for syntax errors**

```bash
python3 -m py_compile modules/system.py
```

**Step 3: Final commit**

```bash
git add modules/system.py
git commit -m "feat(system): complete system setup enhancements"
```

---

## Summary

Total new functions: ~25
Total new lines: ~600-700
New menu items: 6 (with submenus)

Features added:
1. Hostname & Timezone (2 functions)
2. User Management (5 functions)
3. Swap Management (5 functions)
4. Security Hardening (4 functions)
5. System Cleanup (1 function)
6. Reboot/Shutdown (4 functions)
