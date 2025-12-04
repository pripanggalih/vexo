# Task 5.0: Implement Domain & Nginx Module - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the Domain & Nginx module for installing Nginx, managing virtual hosts, and domain configuration.

**Architecture:** Two files - `modules/webserver.py` for all Nginx/domain functions, and `templates/nginx_vhost.conf` for the virtual host template. Domains are managed via `/etc/nginx/sites-available` and symlinked to `sites-enabled`. All operations are idempotent and require root.

**Tech Stack:** Nginx, Python string templating, systemctl for service management

**Note:** Development only - no testing/running. Code will be tested by user on target environment.

---

## Task 5.1: Create templates/nginx_vhost.conf

**Files:**
- Create: `templates/nginx_vhost.conf`

**Step 1: Create Nginx virtual host template**

```nginx
server {
    listen 80;
    listen [::]:80;
    
    server_name {{domain}} www.{{domain}};
    root {{root_path}};
    
    index index.php index.html index.htm;
    
    # Logging
    access_log /var/log/nginx/{{domain}}.access.log;
    error_log /var/log/nginx/{{domain}}.error.log;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }
    
    # PHP-FPM configuration (uncomment and adjust version as needed)
    # location ~ \.php$ {
    #     fastcgi_pass unix:/var/run/php/php8.2-fpm.sock;
    #     fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
    #     include fastcgi_params;
    # }
    
    # Deny access to hidden files
    location ~ /\. {
        deny all;
    }
    
    # Deny access to sensitive files
    location ~* \.(engine|inc|info|install|make|module|profile|test|po|sh|.*sql|theme|tpl(\.php)?|xtmpl)$|^(\..*|Entries.*|Repository|Root|Tag|Template)$ {
        deny all;
    }
}
```

**Step 2: Commit**

```bash
git add templates/nginx_vhost.conf && git commit -m "feat(templates): add nginx virtual host template"
```

---

## Task 5.2: Create modules/webserver.py with show_menu()

**Files:**
- Create: `modules/webserver.py`

**Step 1: Create webserver.py with imports and menu**

```python
"""Domain & Nginx management module for vexo."""

import os

from config import (
    NGINX_SITES_AVAILABLE,
    NGINX_SITES_ENABLED,
    DEFAULT_WEB_ROOT,
    TEMPLATES_DIR,
)
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
    service_control,
    require_root,
)


def show_menu():
    """
    Display the Domain & Nginx submenu and handle user selection.
    
    Returns when user selects 'back' or cancels.
    """
    while True:
        clear_screen()
        show_header()
        
        # Show Nginx status in menu
        nginx_status = "[green]Running[/green]" if is_service_running("nginx") else "[red]Not running[/red]"
        if not is_installed("nginx"):
            nginx_status = "[yellow]Not installed[/yellow]"
        
        console.print(f"[dim]Nginx Status: {nginx_status}[/dim]")
        console.print()
        
        choice = show_submenu(
            title="Domain & Nginx Management",
            options=[
                ("list", "1. List Domains"),
                ("add", "2. Add New Domain"),
                ("remove", "3. Remove Domain"),
                ("install", "4. Install/Reinstall Nginx"),
                ("reload", "5. Reload Nginx"),
                ("status", "6. Nginx Status"),
                ("back", "← Back to Main Menu"),
            ],
        )
        
        if choice == "list":
            list_domains()
        elif choice == "add":
            add_domain_interactive()
        elif choice == "remove":
            remove_domain_interactive()
        elif choice == "install":
            install_nginx()
        elif choice == "reload":
            reload_nginx()
        elif choice == "status":
            show_nginx_status()
        elif choice == "back" or choice is None:
            break
```

**Step 2: Commit**

```bash
git add modules/webserver.py && git commit -m "feat(modules): add webserver.py with show_menu() structure"
```

---

## Task 5.3: Add install_nginx() function

**Files:**
- Modify: `modules/webserver.py`

**Step 1: Add install_nginx() function**

Append to `modules/webserver.py`:

```python


def install_nginx():
    """
    Install Nginx web server.
    
    Idempotent - checks if already installed.
    """
    clear_screen()
    show_header()
    show_panel("Install Nginx", title="Domain & Nginx", style="cyan")
    
    if is_installed("nginx"):
        show_info("Nginx is already installed.")
        
        if not confirm_action("Do you want to reinstall Nginx?"):
            press_enter_to_continue()
            return
    
    if not confirm_action("Install Nginx web server?"):
        show_warning("Installation cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print()
    show_info("Installing Nginx...")
    
    # Update package lists
    result = run_command_with_progress("apt update", "Updating package lists...")
    if result.returncode != 0:
        show_error("Failed to update package lists.")
        press_enter_to_continue()
        return
    
    # Install Nginx
    result = run_command_with_progress(
        "apt install -y nginx",
        "Installing Nginx..."
    )
    
    if result.returncode != 0:
        show_error("Failed to install Nginx.")
        press_enter_to_continue()
        return
    
    # Start and enable Nginx
    service_control("nginx", "start")
    service_control("nginx", "enable")
    
    console.print()
    if is_service_running("nginx"):
        show_success("Nginx installed and running!")
    else:
        show_warning("Nginx installed but may not be running. Check status.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/webserver.py && git commit -m "feat(modules): add install_nginx() function"
```

---

## Task 5.4: Add domain management functions

**Files:**
- Modify: `modules/webserver.py`

**Step 1: Add add_domain(), enable_domain(), and helper functions**

Append to `modules/webserver.py`:

```python


def add_domain_interactive():
    """Interactive prompt to add a new domain."""
    clear_screen()
    show_header()
    show_panel("Add New Domain", title="Domain & Nginx", style="cyan")
    
    # Check Nginx is installed
    if not is_installed("nginx"):
        show_error("Nginx is not installed. Please install it first.")
        press_enter_to_continue()
        return
    
    # Get domain name
    domain = text_input(
        "Enter domain name (e.g., example.com):",
        title="Add Domain"
    )
    
    if not domain:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Validate domain
    domain = domain.strip().lower()
    if not _is_valid_domain(domain):
        show_error(f"Invalid domain name: {domain}")
        press_enter_to_continue()
        return
    
    # Check if domain already exists
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    if os.path.exists(config_path):
        show_error(f"Domain {domain} already exists.")
        press_enter_to_continue()
        return
    
    # Get root path
    default_root = os.path.join(DEFAULT_WEB_ROOT, domain, "public")
    root_path = text_input(
        f"Enter document root path:",
        title="Document Root",
        default=default_root
    )
    
    if not root_path:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Add the domain
    success = add_domain(domain, root_path)
    
    if success:
        show_success(f"Domain {domain} added successfully!")
        console.print()
        console.print(f"[dim]Config: {NGINX_SITES_AVAILABLE}/{domain}[/dim]")
        console.print(f"[dim]Root: {root_path}[/dim]")
    else:
        show_error(f"Failed to add domain {domain}")
    
    press_enter_to_continue()


def add_domain(domain, root_path):
    """
    Add a new domain configuration.
    
    Args:
        domain: Domain name (e.g., example.com)
        root_path: Document root path
    
    Returns:
        bool: True if successful
    """
    try:
        # Read template
        template_path = os.path.join(TEMPLATES_DIR, "nginx_vhost.conf")
        with open(template_path, "r") as f:
            template = f.read()
        
        # Replace placeholders
        config = template.replace("{{domain}}", domain)
        config = config.replace("{{root_path}}", root_path)
        
        # Create document root if it doesn't exist
        if not os.path.exists(root_path):
            os.makedirs(root_path, exist_ok=True)
            # Create a default index.html
            index_path = os.path.join(root_path, "index.html")
            with open(index_path, "w") as f:
                f.write(f"<html><body><h1>Welcome to {domain}</h1></body></html>\n")
        
        # Write config file
        config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
        with open(config_path, "w") as f:
            f.write(config)
        
        # Enable the domain
        return enable_domain(domain)
    
    except Exception as e:
        show_error(f"Error adding domain: {e}")
        return False


def enable_domain(domain):
    """
    Enable a domain by creating symlink and reloading Nginx.
    
    Args:
        domain: Domain name
    
    Returns:
        bool: True if successful
    """
    try:
        source = os.path.join(NGINX_SITES_AVAILABLE, domain)
        target = os.path.join(NGINX_SITES_ENABLED, domain)
        
        # Check source exists
        if not os.path.exists(source):
            show_error(f"Config not found: {source}")
            return False
        
        # Remove existing symlink if exists
        if os.path.islink(target):
            os.remove(target)
        
        # Create symlink
        os.symlink(source, target)
        
        # Test Nginx config
        result = run_command("nginx -t", check=False, silent=True)
        if result.returncode != 0:
            show_error("Nginx configuration test failed!")
            console.print(f"[dim]{result.stderr}[/dim]")
            # Remove the symlink if config is invalid
            os.remove(target)
            return False
        
        # Reload Nginx
        return reload_nginx(silent=True)
    
    except Exception as e:
        show_error(f"Error enabling domain: {e}")
        return False


def _is_valid_domain(domain):
    """Check if domain name is valid."""
    import re
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$'
    return bool(re.match(pattern, domain))
```

**Step 2: Commit**

```bash
git add modules/webserver.py && git commit -m "feat(modules): add add_domain() and enable_domain() functions"
```

---

## Task 5.5: Add list_domains() and remove_domain() functions

**Files:**
- Modify: `modules/webserver.py`

**Step 1: Add list and remove domain functions**

Append to `modules/webserver.py`:

```python


def list_domains():
    """Display a table of configured domains."""
    clear_screen()
    show_header()
    show_panel("Configured Domains", title="Domain & Nginx", style="cyan")
    
    # Get domains from sites-available
    domains = _get_configured_domains()
    
    if not domains:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Domain", "style": "cyan"},
        {"name": "Enabled", "justify": "center"},
        {"name": "Root Path", "style": "dim"},
    ]
    
    rows = []
    for domain in domains:
        enabled = _is_domain_enabled(domain)
        enabled_str = "[green]✓[/green]" if enabled else "[red]✗[/red]"
        root_path = _get_domain_root(domain)
        rows.append([domain, enabled_str, root_path])
    
    show_table(f"Total: {len(domains)} domain(s)", columns, rows)
    
    press_enter_to_continue()


def remove_domain_interactive():
    """Interactive prompt to remove a domain."""
    clear_screen()
    show_header()
    show_panel("Remove Domain", title="Domain & Nginx", style="cyan")
    
    domains = _get_configured_domains()
    
    if not domains:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    # Let user select domain
    domain = select_from_list(
        title="Remove Domain",
        message="Select domain to remove:",
        options=domains
    )
    
    if not domain:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Confirm deletion
    if not confirm_action(f"Are you sure you want to remove {domain}?\nThis will delete the Nginx config but NOT the files."):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = remove_domain(domain)
    
    if success:
        show_success(f"Domain {domain} removed successfully!")
    else:
        show_error(f"Failed to remove domain {domain}")
    
    press_enter_to_continue()


def remove_domain(domain):
    """
    Remove a domain configuration.
    
    Args:
        domain: Domain name
    
    Returns:
        bool: True if successful
    """
    try:
        # Remove from sites-enabled first
        enabled_path = os.path.join(NGINX_SITES_ENABLED, domain)
        if os.path.islink(enabled_path):
            os.remove(enabled_path)
        
        # Remove from sites-available
        available_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
        if os.path.exists(available_path):
            os.remove(available_path)
        
        # Reload Nginx
        return reload_nginx(silent=True)
    
    except Exception as e:
        show_error(f"Error removing domain: {e}")
        return False


def _get_configured_domains():
    """Get list of configured domains from sites-available."""
    try:
        if not os.path.exists(NGINX_SITES_AVAILABLE):
            return []
        
        domains = []
        for name in os.listdir(NGINX_SITES_AVAILABLE):
            # Skip default and common non-domain files
            if name in ["default", "default.conf", ".DS_Store"]:
                continue
            path = os.path.join(NGINX_SITES_AVAILABLE, name)
            if os.path.isfile(path):
                domains.append(name)
        
        return sorted(domains)
    except Exception:
        return []


def _is_domain_enabled(domain):
    """Check if domain is enabled (has symlink in sites-enabled)."""
    enabled_path = os.path.join(NGINX_SITES_ENABLED, domain)
    return os.path.islink(enabled_path)


def _get_domain_root(domain):
    """Get document root from domain config."""
    try:
        config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
        with open(config_path, "r") as f:
            for line in f:
                if "root " in line:
                    # Extract path from "root /path/to/root;"
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        return parts[1].rstrip(";")
        return "Unknown"
    except Exception:
        return "Unknown"
```

**Step 2: Commit**

```bash
git add modules/webserver.py && git commit -m "feat(modules): add list_domains() and remove_domain() functions"
```

---

## Task 5.6: Add reload_nginx() and show_nginx_status()

**Files:**
- Modify: `modules/webserver.py`

**Step 1: Add Nginx control functions**

Append to `modules/webserver.py`:

```python


def reload_nginx(silent=False):
    """
    Reload Nginx configuration.
    
    Args:
        silent: If True, don't show messages
    
    Returns:
        bool: True if successful
    """
    try:
        # Test config first
        result = run_command("nginx -t", check=False, silent=True)
        if result.returncode != 0:
            if not silent:
                show_error("Nginx configuration test failed!")
                console.print(f"[dim]{result.stderr}[/dim]")
            return False
        
        # Reload
        success = service_control("nginx", "reload")
        
        if not silent:
            if success:
                show_success("Nginx reloaded successfully!")
            else:
                show_error("Failed to reload Nginx.")
            press_enter_to_continue()
        
        return success
    
    except Exception as e:
        if not silent:
            show_error(f"Error reloading Nginx: {e}")
            press_enter_to_continue()
        return False


def show_nginx_status():
    """Display Nginx service status."""
    clear_screen()
    show_header()
    show_panel("Nginx Status", title="Domain & Nginx", style="cyan")
    
    # Check if installed
    if not is_installed("nginx"):
        show_warning("Nginx is not installed.")
        press_enter_to_continue()
        return
    
    # Get status info
    running = is_service_running("nginx")
    
    columns = [
        {"name": "Property", "style": "cyan"},
        {"name": "Value"},
    ]
    
    rows = [
        ["Installed", "[green]Yes[/green]"],
        ["Running", "[green]Yes[/green]" if running else "[red]No[/red]"],
    ]
    
    # Get version
    result = run_command("nginx -v 2>&1", check=False, silent=True)
    if result.returncode == 0:
        version = result.stderr.strip() if result.stderr else result.stdout.strip()
        rows.append(["Version", version.replace("nginx version: ", "")])
    
    # Config test
    result = run_command("nginx -t 2>&1", check=False, silent=True)
    config_ok = result.returncode == 0
    rows.append(["Config Valid", "[green]Yes[/green]" if config_ok else "[red]No[/red]"])
    
    # Domain count
    domains = _get_configured_domains()
    rows.append(["Domains Configured", str(len(domains))])
    
    show_table("", columns, rows, show_header=False)
    
    # Show config test output if failed
    if not config_ok:
        console.print()
        show_error("Configuration test failed:")
        console.print(f"[dim]{result.stderr}[/dim]")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/webserver.py && git commit -m "feat(modules): add reload_nginx() and show_nginx_status()"
```

---

## Task 5.7: Update modules/__init__.py

**Files:**
- Modify: `modules/__init__.py`

**Step 1: Add webserver module export**

```python
"""Business logic modules for vexo - system, webserver, runtime, database, email."""

from modules import system
from modules import webserver
```

**Step 2: Commit**

```bash
git add modules/__init__.py && git commit -m "feat(modules): add webserver module export"
```

---

## Task 5.8: Update task list

Mark Task 5.0 and all sub-tasks as completed in `tasks/tasks-vexo.md`

---

## Summary

After completing this plan:

```
modules/
├── __init__.py      ✅ Exports system, webserver
├── system.py        ✅ System setup
└── webserver.py     ✅ Nginx & domain management

templates/
└── nginx_vhost.conf ✅ Virtual host template
```

**Functions available after Task 5:**

| Function | Description |
|----------|-------------|
| `show_menu()` | Display Domain & Nginx submenu |
| `install_nginx()` | Install Nginx (idempotent) |
| `add_domain(domain, root_path)` | Add new domain config |
| `enable_domain(domain)` | Enable domain with symlink |
| `list_domains()` | Show all configured domains |
| `remove_domain(domain)` | Remove domain config |
| `reload_nginx()` | Test and reload Nginx |
| `show_nginx_status()` | Display Nginx status |

**Key Features:**
- Template-based virtual host generation
- Automatic document root creation with default index.html
- Config validation before reload
- Domain validation
- Interactive add/remove with selection dialogs
