# DRY Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce code repetition across modules with simple helper functions (no complex OOP).

**Architecture:** Add helper functions to `ui/menu.py` and `utils/shell.py` that encapsulate repeated patterns. Modules will use these helpers instead of copy-pasting boilerplate.

**Tech Stack:** Python 3.8+, existing InquirerPy/Rich stack

---

## Task 1: Create Menu Loop Helper

**Files:**
- Modify: `ui/menu.py` (add function at end)

**Step 1: Add `run_menu_loop` helper function**

Add this function to `ui/menu.py`:

```python
def run_menu_loop(title, get_options, handlers, get_status=None):
    """
    Run a standard menu loop with automatic screen clearing and header.
    
    Args:
        title: Menu title string
        get_options: Callable that returns list of (key, label) tuples
        handlers: Dict mapping choice keys to handler functions
        get_status: Optional callable that returns status string to display
    
    Example:
        def get_options():
            opts = [("list", "1. List Items")]
            opts.append(("back", "← Back"))
            return opts
        
        handlers = {
            "list": list_items,
        }
        
        run_menu_loop("My Menu", get_options, handlers)
    """
    from ui.components import clear_screen, show_header, console
    
    while True:
        clear_screen()
        show_header()
        
        if get_status:
            status = get_status()
            if status:
                console.print(f"[dim]{status}[/dim]")
                console.print()
        
        options = get_options() if callable(get_options) else get_options
        
        choice = show_submenu(title=title, options=options)
        
        if choice == "back" or choice is None:
            break
        
        handler = handlers.get(choice)
        if handler:
            handler()
```

**Step 2: Verify syntax**

Run: `python3 -m py_compile ui/menu.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add ui/menu.py
git commit -m "feat(ui): add run_menu_loop helper for DRY menus"
```

---

## Task 2: Create Service Status Helper

**Files:**
- Modify: `utils/shell.py` (add function at end)

**Step 1: Add `get_service_status` helper function**

Add this function to `utils/shell.py`:

```python
def get_service_status(package_name, service_name=None):
    """
    Get formatted status string for a service.
    
    Args:
        package_name: Package name to check installation
        service_name: Service name to check running state (defaults to package_name)
    
    Returns:
        tuple: (status_string, is_installed, is_running)
        
    Example:
        status, installed, running = get_service_status("nginx")
        # status = "[green]Running[/green]" or "[red]Stopped[/red]" or "[dim]Not installed[/dim]"
    """
    if service_name is None:
        service_name = package_name
    
    if not is_installed(package_name):
        return "[dim]Not installed[/dim]", False, False
    
    if is_service_running(service_name):
        return "[green]Running[/green]", True, True
    else:
        return "[red]Stopped[/red]", True, False
```

**Step 2: Export in `utils/__init__.py`**

Add `get_service_status` to the imports in `utils/__init__.py` if needed.

**Step 3: Verify syntax**

Run: `python3 -m py_compile utils/shell.py`
Expected: No output (success)

**Step 4: Commit**

```bash
git add utils/shell.py utils/__init__.py
git commit -m "feat(utils): add get_service_status helper"
```

---

## Task 3: Refactor `modules/monitor.py` (Simplest Module)

**Files:**
- Modify: `modules/monitor.py`

**Step 1: Refactor show_menu using run_menu_loop**

Replace the current `show_menu()` function:

```python
from ui.menu import show_submenu, run_menu_loop


def show_menu():
    """Display the System Monitoring submenu."""
    options = [
        ("status", "1. Show System Status"),
        ("cpu", "2. CPU Details"),
        ("ram", "3. Memory Details"),
        ("disk", "4. Disk Details"),
        ("back", "← Back to Main Menu"),
    ]
    
    handlers = {
        "status": show_status,
        "cpu": show_cpu_details,
        "ram": show_ram_details,
        "disk": show_disk_details,
    }
    
    run_menu_loop("System Monitoring", options, handlers)
```

**Step 2: Verify syntax**

Run: `python3 -m py_compile modules/monitor.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add modules/monitor.py
git commit -m "refactor(monitor): use run_menu_loop helper"
```

---

## Task 4: Refactor `modules/system.py`

**Files:**
- Modify: `modules/system.py`

**Step 1: Refactor show_menu using run_menu_loop**

Replace the current `show_menu()` function:

```python
from ui.menu import show_submenu, confirm_action, run_menu_loop


def show_menu():
    """Display the System Setup submenu."""
    options = [
        ("info", "1. Show System Info"),
        ("update", "2. Update & Upgrade System"),
        ("tools", "3. Install Basic Tools"),
        ("back", "← Back to Main Menu"),
    ]
    
    handlers = {
        "info": show_system_info,
        "update": update_system,
        "tools": install_basic_tools,
    }
    
    run_menu_loop("System Setup & Update", options, handlers)
```

**Step 2: Verify syntax**

Run: `python3 -m py_compile modules/system.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add modules/system.py
git commit -m "refactor(system): use run_menu_loop helper"
```

---

## Task 5: Refactor `modules/ssl.py`

**Files:**
- Modify: `modules/ssl.py`

**Step 1: Refactor show_menu using run_menu_loop and get_service_status**

```python
from ui.menu import show_submenu, confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import (
    run_command,
    run_command_with_progress,
    run_command_realtime,
    is_installed,
    is_service_running,
    require_root,
    get_service_status,
)


def show_menu():
    """Display the SSL Certificates submenu."""
    def get_status():
        status, _, _ = get_service_status("certbot", "certbot")
        # Certbot is not a service, just check installed
        if is_installed("certbot"):
            return "Certbot: [green]Installed[/green]"
        return "Certbot: [dim]Not installed[/dim]"
    
    options = [
        ("install", "1. Install Certbot"),
        ("enable", "2. Enable SSL for Domain"),
        ("list", "3. List Certificates"),
        ("renew", "4. Renew All Certificates"),
        ("revoke", "5. Revoke Certificate"),
        ("status", "6. Auto-Renewal Status"),
        ("back", "← Back to Main Menu"),
    ]
    
    handlers = {
        "install": install_certbot,
        "enable": enable_ssl_interactive,
        "list": list_certificates,
        "renew": renew_certificates,
        "revoke": revoke_certificate_interactive,
        "status": show_renewal_status,
    }
    
    run_menu_loop("SSL Certificates (Let's Encrypt)", options, handlers, get_status)
```

**Step 2: Verify syntax**

Run: `python3 -m py_compile modules/ssl.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add modules/ssl.py
git commit -m "refactor(ssl): use run_menu_loop helper"
```

---

## Task 6: Refactor `modules/firewall.py` (Dynamic Options)

**Files:**
- Modify: `modules/firewall.py`

**Step 1: Refactor show_menu with dynamic options**

```python
from ui.menu import show_submenu, confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import (
    run_command,
    run_command_with_progress,
    is_installed,
    is_service_running,
    require_root,
    get_service_status,
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
```

**Step 2: Verify syntax**

Run: `python3 -m py_compile modules/firewall.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add modules/firewall.py
git commit -m "refactor(firewall): use run_menu_loop helper"
```

---

## Task 7: Refactor Remaining Modules

Apply the same pattern to remaining modules. Each module follows the same refactoring:

**Modules to refactor:**
- `modules/fail2ban.py`
- `modules/supervisor.py`
- `modules/cron.py`
- `modules/database.py` (has sub-menus)
- `modules/runtime.py` (has 2 menus: PHP and Node.js)
- `modules/email.py` (has sub-menus)
- `modules/webserver.py` (has sub-menus)

**Pattern for each:**

1. Import `run_menu_loop` from `ui.menu`
2. Import `get_service_status` from `utils.shell` if checking service status
3. Convert `show_menu()` to use `run_menu_loop(title, get_options, handlers, get_status)`
4. For modules with sub-menus, also refactor those using `run_menu_loop`
5. Verify syntax with `python3 -m py_compile modules/<name>.py`
6. Commit each module separately

**Step 1: Refactor fail2ban.py**
**Step 2: Refactor supervisor.py**
**Step 3: Refactor cron.py**
**Step 4: Refactor database.py** (main + 3 sub-menus)
**Step 5: Refactor runtime.py** (PHP + Node.js menus)
**Step 6: Refactor email.py** (main + sub-menus)
**Step 7: Refactor webserver.py** (main + configure site menu)

Each step: modify → verify syntax → commit

---

## Summary

**Before:** ~200 lines of repeated menu boilerplate across 13 modules

**After:** 
- 1 helper function `run_menu_loop()` (~30 lines)
- 1 helper function `get_service_status()` (~15 lines)
- Each module's `show_menu()` reduced from ~25 lines to ~15 lines

**Total reduction:** ~150+ lines of repetitive code

**Benefits:**
- Single place to change menu behavior
- Consistent look and feel
- Less copy-paste errors
- Easier to add new modules
