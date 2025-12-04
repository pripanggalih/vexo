# Task 12.0: Firewall Module Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create UFW firewall management module with default rules, custom ports, and email ports support.

**Architecture:** Single `modules/firewall.py` with UFW wrapper functions. Default deny incoming, allow outgoing. Pre-configured rules for SSH/HTTP/HTTPS with option to add email ports (25/587/465).

**Tech Stack:** UFW (Uncomplicated Firewall), existing shell.py utilities, Rich UI components

---

## Sub-tasks Overview

| Sub-task | Description | Commit |
|----------|-------------|--------|
| 12.1 | Create firewall.py with show_menu() | Yes |
| 12.2 | Add install_ufw() | Yes |
| 12.3 | Add enable_firewall() with default rules | Yes |
| 12.4 | Add disable_firewall() | Yes |
| 12.5 | Add add_port() and add_email_ports() | Yes |
| 12.6 | Add remove_port() and list_rules() | Yes |
| 12.7 | Add show_status() and update __init__.py | Yes |

**Total: 7 sub-tasks, 7 commits**

---

## Task 12.1: Create firewall.py with show_menu()

**Files:**
- Create: `modules/firewall.py`

**Step 1: Create firewall module with menu**

```python
"""Firewall (UFW) management module for vexo."""

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
from ui.menu import show_submenu, confirm_action, text_input, select_from_list
from utils.shell import (
    run_command,
    run_command_with_progress,
    is_installed,
    is_service_running,
    require_root,
)


def show_menu():
    """
    Display the Firewall (UFW) submenu and handle user selection.
    """
    while True:
        clear_screen()
        show_header()
        
        # Show UFW status
        status = _get_ufw_status()
        console.print(f"[dim]UFW Status: {status}[/dim]")
        console.print()
        
        choice = show_submenu(
            title="Firewall (UFW)",
            options=[
                ("status", "1. Show Status"),
                ("enable", "2. Enable Firewall"),
                ("disable", "3. Disable Firewall"),
                ("add_port", "4. Add Custom Port"),
                ("add_email", "5. Add Email Ports"),
                ("remove_port", "6. Remove Port"),
                ("list_rules", "7. List Rules"),
                ("back", "← Back to Main Menu"),
            ],
        )
        
        if choice == "status":
            show_status()
        elif choice == "enable":
            enable_firewall()
        elif choice == "disable":
            disable_firewall()
        elif choice == "add_port":
            add_port_interactive()
        elif choice == "add_email":
            add_email_ports()
        elif choice == "remove_port":
            remove_port_interactive()
        elif choice == "list_rules":
            list_rules()
        elif choice == "back" or choice is None:
            break


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
```

**Step 2: Commit**

```bash
git add modules/firewall.py
git commit -m "feat(firewall): add firewall.py with menu structure"
```

---

## Task 12.2: Add install_ufw()

**Files:**
- Modify: `modules/firewall.py`

**Step 1: Add UFW installation function**

Append to `modules/firewall.py`:

```python
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
```

**Step 2: Commit**

```bash
git add modules/firewall.py
git commit -m "feat(firewall): add install_ufw()"
```

---

## Task 12.3: Add enable_firewall() with default rules

**Files:**
- Modify: `modules/firewall.py`

**Step 1: Add enable firewall function with defaults**

Append to `modules/firewall.py`:

```python
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
```

**Step 2: Commit**

```bash
git add modules/firewall.py
git commit -m "feat(firewall): add enable_firewall() with default rules"
```

---

## Task 12.4: Add disable_firewall()

**Files:**
- Modify: `modules/firewall.py`

**Step 1: Add disable firewall function**

Append to `modules/firewall.py`:

```python
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
```

**Step 2: Commit**

```bash
git add modules/firewall.py
git commit -m "feat(firewall): add disable_firewall() with warning"
```

---

## Task 12.5: Add add_port() and add_email_ports()

**Files:**
- Modify: `modules/firewall.py`

**Step 1: Add port management functions**

Append to `modules/firewall.py`:

```python
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
```

**Step 2: Commit**

```bash
git add modules/firewall.py
git commit -m "feat(firewall): add add_port() and add_email_ports()"
```

---

## Task 12.6: Add remove_port() and list_rules()

**Files:**
- Modify: `modules/firewall.py`

**Step 1: Add remove and list functions**

Append to `modules/firewall.py`:

```python
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
```

**Step 2: Commit**

```bash
git add modules/firewall.py
git commit -m "feat(firewall): add remove_port() and list_rules()"
```

---

## Task 12.7: Add show_status() and update __init__.py

**Files:**
- Modify: `modules/firewall.py`
- Modify: `modules/__init__.py`

**Step 1: Add show_status function**

Append to `modules/firewall.py`:

```python
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
```

**Step 2: Update modules/__init__.py**

```python
"""Business logic modules for vexo - system, webserver, runtime, database, email."""

from modules import system
from modules import webserver
from modules import runtime
from modules import database
from modules import email
from modules import monitor
from modules import firewall
```

**Step 3: Commit**

```bash
git add modules/firewall.py modules/__init__.py
git commit -m "feat(firewall): add show_status() and export module"
```

---

## Summary

After completion, `modules/firewall.py` will have:

**Menu Function:**
- `show_menu()` - 7-option firewall submenu

**Core Functions:**
- `install_ufw()` - Install UFW package
- `enable_firewall()` - Setup defaults + enable
- `disable_firewall()` - Disable with warning
- `add_port()` - Add custom port rule
- `add_email_ports()` - Batch add 25/587/465
- `remove_port_interactive()` - Remove rule by number
- `list_rules()` - Show numbered rules
- `show_status()` - Verbose status display

**Helper Functions:**
- `_get_ufw_status()` - Status string for menu
- `_get_ufw_rules()` - Parse numbered rules

**Default Rules:**
- `ufw default deny incoming`
- `ufw default allow outgoing`
- `ufw allow 22/tcp` (SSH)
- `ufw allow 80/tcp` (HTTP)
- `ufw allow 443/tcp` (HTTPS)
