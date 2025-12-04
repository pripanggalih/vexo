# Task 4.0: Implement System Setup Module - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the System Setup module for updating the system, installing basic tools, and displaying system information.

**Architecture:** Single file `modules/system.py` containing all system setup functions. Uses utilities from `utils/shell.py` for command execution and `ui/` for display. All operations are idempotent - they check current state before making changes.

**Tech Stack:** Python subprocess (via utils/shell.py), apt package manager, Rich UI components

**Note:** Development only - no testing/running. Code will be tested by user on target environment.

---

## Task 4.1: Create modules/system.py with show_menu()

**Files:**
- Create: `modules/system.py`

**Step 1: Create system.py with menu and basic structure**

```python
"""System Setup module for vexo."""

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
from ui.menu import show_submenu, confirm_action
from utils.shell import (
    run_command,
    run_command_with_progress,
    run_command_realtime,
    is_installed,
    is_command_available,
    require_root,
    get_os_info,
    get_hostname,
    get_ip_address,
)


def show_menu():
    """
    Display the System Setup submenu and handle user selection.
    
    Returns when user selects 'back' or cancels.
    """
    while True:
        clear_screen()
        show_header()
        
        choice = show_submenu(
            title="System Setup & Update",
            options=[
                ("info", "1. Show System Info"),
                ("update", "2. Update & Upgrade System"),
                ("tools", "3. Install Basic Tools"),
                ("back", "← Back to Main Menu"),
            ],
        )
        
        if choice == "info":
            show_system_info()
        elif choice == "update":
            update_system()
        elif choice == "tools":
            install_basic_tools()
        elif choice == "back" or choice is None:
            break
```

**Step 2: Commit**

```bash
git add modules/system.py && git commit -m "feat(modules): add system.py with show_menu() structure"
```

---

## Task 4.2: Add update_system() function

**Files:**
- Modify: `modules/system.py`

**Step 1: Add update_system() function**

Append to `modules/system.py`:

```python


def update_system():
    """
    Update package lists and upgrade all packages.
    
    Runs: apt update && apt upgrade -y
    """
    clear_screen()
    show_header()
    show_panel("System Update & Upgrade", title="System Setup", style="cyan")
    
    if not confirm_action("This will update and upgrade all system packages. Continue?"):
        show_warning("Update cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print()
    show_info("Updating package lists...")
    
    # Run apt update
    result = run_command_with_progress(
        "apt update",
        "Updating package lists..."
    )
    
    if result.returncode != 0:
        show_error("Failed to update package lists.")
        if result.stderr:
            console.print(f"[dim]{result.stderr}[/dim]")
        press_enter_to_continue()
        return
    
    show_success("Package lists updated.")
    console.print()
    
    # Run apt upgrade
    show_info("Upgrading packages (this may take a while)...")
    console.print()
    
    returncode = run_command_realtime(
        "apt upgrade -y",
        "Upgrading packages..."
    )
    
    console.print()
    if returncode == 0:
        show_success("System upgraded successfully!")
    else:
        show_error("Some packages may have failed to upgrade.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/system.py && git commit -m "feat(modules): add update_system() for apt update/upgrade"
```

---

## Task 4.3: Add install_basic_tools() function

**Files:**
- Modify: `modules/system.py`

**Step 1: Add install_basic_tools() function with idempotency**

Append to `modules/system.py`:

```python


# List of basic tools to install
BASIC_TOOLS = [
    "curl",
    "wget",
    "git",
    "unzip",
    "zip",
    "htop",
    "vim",
    "software-properties-common",
    "apt-transport-https",
    "ca-certificates",
    "gnupg",
    "lsb-release",
]


def install_basic_tools():
    """
    Install essential tools for server management.
    
    Checks each tool before installing (idempotent).
    """
    clear_screen()
    show_header()
    show_panel("Install Basic Tools", title="System Setup", style="cyan")
    
    # Show what will be installed
    console.print("[bold]The following tools will be checked/installed:[/bold]")
    console.print()
    for tool in BASIC_TOOLS:
        console.print(f"  • {tool}")
    console.print()
    
    if not confirm_action("Proceed with installation?"):
        show_warning("Installation cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print()
    
    # Check which tools need to be installed
    to_install = []
    already_installed = []
    
    for tool in BASIC_TOOLS:
        if is_installed(tool):
            already_installed.append(tool)
        else:
            to_install.append(tool)
    
    # Show already installed
    if already_installed:
        show_info(f"Already installed: {', '.join(already_installed)}")
        console.print()
    
    # Install missing tools
    if not to_install:
        show_success("All basic tools are already installed!")
        press_enter_to_continue()
        return
    
    show_info(f"Installing: {', '.join(to_install)}")
    console.print()
    
    # Update package lists first
    result = run_command_with_progress("apt update", "Updating package lists...")
    if result.returncode != 0:
        show_error("Failed to update package lists.")
        press_enter_to_continue()
        return
    
    # Install all missing tools at once
    packages = " ".join(to_install)
    returncode = run_command_realtime(
        f"apt install -y {packages}",
        f"Installing {len(to_install)} packages..."
    )
    
    console.print()
    if returncode == 0:
        show_success(f"Successfully installed {len(to_install)} tools!")
    else:
        show_warning("Some tools may have failed to install. Check the output above.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/system.py && git commit -m "feat(modules): add install_basic_tools() with idempotency check"
```

---

## Task 4.4: Add show_system_info() function

**Files:**
- Modify: `modules/system.py`

**Step 1: Add show_system_info() function**

Append to `modules/system.py`:

```python


def show_system_info():
    """
    Display system information including OS, hostname, and IP.
    """
    clear_screen()
    show_header()
    show_panel("System Information", title="System Setup", style="cyan")
    
    # Get system info
    os_info = get_os_info()
    hostname = get_hostname()
    ip_address = get_ip_address()
    
    # Get additional info
    kernel = _get_kernel_version()
    uptime = _get_uptime()
    
    # Display in table
    columns = [
        {"name": "Property", "style": "cyan"},
        {"name": "Value", "style": "white"},
    ]
    
    rows = [
        ["Operating System", f"{os_info['name']} {os_info['version']}"],
        ["Codename", os_info['codename']],
        ["Architecture", os_info['arch']],
        ["Kernel", kernel],
        ["Hostname", hostname],
        ["IP Address", ip_address],
        ["Uptime", uptime],
    ]
    
    show_table("", columns, rows, show_header=False)
    
    # Show installed status of basic tools
    console.print()
    console.print("[bold]Basic Tools Status:[/bold]")
    console.print()
    
    tool_columns = [
        {"name": "Tool", "style": "white"},
        {"name": "Status", "justify": "center"},
    ]
    
    tool_rows = []
    for tool in BASIC_TOOLS[:8]:  # Show first 8 tools
        status = "[green]✓ Installed[/green]" if is_installed(tool) else "[red]✗ Not installed[/red]"
        tool_rows.append([tool, status])
    
    show_table("", tool_columns, tool_rows, show_header=True)
    
    press_enter_to_continue()


def _get_kernel_version():
    """Get the Linux kernel version."""
    try:
        result = run_command("uname -r", check=False, silent=True)
        return result.stdout.strip() if result.returncode == 0 else "Unknown"
    except Exception:
        return "Unknown"


def _get_uptime():
    """Get system uptime in human-readable format."""
    try:
        result = run_command("uptime -p", check=False, silent=True)
        if result.returncode == 0:
            return result.stdout.strip().replace("up ", "")
        return "Unknown"
    except Exception:
        return "Unknown"
```

**Step 2: Commit**

```bash
git add modules/system.py && git commit -m "feat(modules): add show_system_info() with system details"
```

---

## Task 4.5: Update modules/__init__.py exports

**Files:**
- Modify: `modules/__init__.py`

**Step 1: Update __init__.py with system module export**

```python
"""Business logic modules for vexo - system, webserver, runtime, database, email."""

from modules import system
```

**Step 2: Commit**

```bash
git add modules/__init__.py && git commit -m "feat(modules): update __init__.py with system module"
```

---

## Task 4.6: Update task list

Mark Task 4.0 and all sub-tasks as completed in `tasks/tasks-vexo.md`

---

## Summary

After completing this plan:

```
modules/
├── __init__.py      ✅ Exports system module
└── system.py        ✅ System setup functions
```

**Functions available after Task 4:**

| Function | Description |
|----------|-------------|
| `show_menu()` | Display System Setup submenu |
| `update_system()` | Run apt update && apt upgrade -y |
| `install_basic_tools()` | Install curl, git, unzip, etc. (idempotent) |
| `show_system_info()` | Display OS, hostname, IP, tool status |

**Key Features:**
- All operations require root (checked with `require_root()`)
- Install operations are idempotent (check before install)
- Real-time output for long-running operations
- Confirmation dialogs before destructive actions
