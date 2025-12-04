# PHP-FPM Management Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add comprehensive PHP-FPM pool management including status monitoring, configuration editing, service control, custom pools, and memory calculator.

**Architecture:** Create `modules/runtime/php/fpm.py` as part of runtime module refactor. Each feature is a menu handler function. Pool configs are edited via `/etc/php/{version}/fpm/pool.d/www.conf`.

**Tech Stack:** Python, PHP-FPM, systemd service control

---

## Task 1: Create Runtime Folder Structure

**Files:**
- Create: `modules/runtime/__init__.py`
- Create: `modules/runtime/php/__init__.py`
- Create: `modules/runtime/php/utils.py`
- Create: `modules/runtime/nodejs.py`

**Step 1: Create directory structure**

```bash
mkdir -p modules/runtime/php
```

**Step 2: Create modules/runtime/php/utils.py**

```python
"""Shared utilities for PHP runtime module."""

import os
import re

from utils.shell import run_command, is_installed, is_service_running

# PHP versions to support
PHP_VERSIONS = ["8.3", "8.4", "8.5"]

# Laravel-compatible PHP extensions
PHP_EXTENSIONS = [
    "cli", "fpm", "common",
    "bcmath", "ctype", "curl", "dom", "fileinfo", "mbstring", "pdo", "tokenizer", "xml",
    "mysql", "pgsql", "sqlite3",
    "zip", "gd", "intl", "opcache", "redis", "imagick", "soap", "imap", "exif",
]

# FPM config paths
PHP_FPM_POOL_DIR = "/etc/php/{version}/fpm/pool.d"
PHP_FPM_CONF = "/etc/php/{version}/fpm/php-fpm.conf"
PHP_INI_FPM = "/etc/php/{version}/fpm/php.ini"
PHP_INI_CLI = "/etc/php/{version}/cli/php.ini"


def get_installed_php_versions():
    """Get list of installed PHP versions."""
    installed = []
    for version in PHP_VERSIONS:
        if is_installed(f"php{version}") or is_installed(f"php{version}-cli"):
            installed.append(version)
    return installed


def get_default_php_version():
    """Get the current default PHP CLI version."""
    result = run_command("php -v 2>/dev/null | head -1", check=False, silent=True)
    if result.returncode != 0:
        return None
    
    output = result.stdout.strip()
    if "PHP" in output:
        parts = output.split()
        if len(parts) >= 2:
            version = parts[1]
            return ".".join(version.split(".")[:2])
    return None


def get_fpm_pool_path(version, pool_name="www"):
    """Get path to FPM pool config file."""
    return f"/etc/php/{version}/fpm/pool.d/{pool_name}.conf"


def get_fpm_service_name(version):
    """Get FPM service name for a PHP version."""
    return f"php{version}-fpm"


def is_fpm_running(version):
    """Check if PHP-FPM is running for a version."""
    return is_service_running(get_fpm_service_name(version))


def parse_fpm_pool_config(version, pool_name="www"):
    """Parse FPM pool configuration file."""
    config_path = get_fpm_pool_path(version, pool_name)
    config = {}
    
    if not os.path.exists(config_path):
        return config
    
    try:
        with open(config_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(";") or line.startswith("["):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
    except Exception:
        pass
    
    return config


def get_server_memory_mb():
    """Get total server memory in MB."""
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return kb // 1024
    except Exception:
        pass
    return 2048  # Default 2GB
```

**Step 3: Create modules/runtime/nodejs.py**

Copy all Node.js functions from original `runtime.py`:
- `show_nodejs_menu()`
- `install_nvm_interactive()`, `install_nvm()`
- `install_nodejs_interactive()`, `install_nodejs()`
- `switch_nodejs_interactive()`, `switch_nodejs_version()`
- `list_nodejs_versions()`
- `show_nodejs_info()`
- All `_get_*` and `_run_with_nvm()` helpers

Update imports to use local paths.

**Step 4: Create modules/runtime/php/__init__.py**

```python
"""PHP Runtime management module."""

from ui.menu import run_menu_loop
from modules.runtime.php.utils import get_installed_php_versions, get_default_php_version


def show_menu():
    """Display the PHP Runtime submenu."""
    def get_status():
        default_php = get_default_php_version()
        if default_php:
            return f"Default PHP: {default_php}"
        return "Default PHP: Not installed"
    
    def get_options():
        from modules.runtime.php.install import (
            list_php_versions, install_php_interactive, switch_php_interactive,
            install_composer, set_site_php_interactive, show_php_info_interactive,
        )
        
        options = []
        installed = get_installed_php_versions()
        if installed:
            options.extend([
                ("list", "1. List PHP Versions"),
                ("install", "2. Install PHP Version"),
                ("switch", "3. Switch Default PHP"),
                ("fpm", "4. FPM Management"),
                ("config", "5. PHP Configuration"),
                ("extensions", "6. Extension Management"),
                ("monitor", "7. Monitoring & Logs"),
                ("security", "8. Security Hardening"),
                ("composer", "9. Install/Update Composer"),
                ("site_php", "10. Set PHP for Site"),
                ("info", "11. PHP Info"),
            ])
        else:
            options.append(("install", "1. Install PHP"))
        options.append(("back", "← Back to Main Menu"))
        return options
    
    def get_handlers():
        from modules.runtime.php.install import (
            list_php_versions, install_php_interactive, switch_php_interactive,
            install_composer, set_site_php_interactive, show_php_info_interactive,
        )
        from modules.runtime.php.fpm import show_fpm_menu
        from modules.runtime.php.config import show_config_menu
        from modules.runtime.php.extensions import show_extensions_menu
        from modules.runtime.php.monitor import show_monitor_menu
        from modules.runtime.php.security import show_security_menu
        
        return {
            "list": list_php_versions,
            "install": install_php_interactive,
            "switch": switch_php_interactive,
            "fpm": show_fpm_menu,
            "config": show_config_menu,
            "extensions": show_extensions_menu,
            "monitor": show_monitor_menu,
            "security": show_security_menu,
            "composer": install_composer,
            "site_php": set_site_php_interactive,
            "info": show_php_info_interactive,
        }
    
    run_menu_loop("PHP Runtime Management", get_options, get_handlers(), get_status)
```

**Step 5: Create modules/runtime/__init__.py**

```python
"""Runtime management module for vexo-cli (PHP & Node.js)."""

from modules.runtime.php import show_menu as show_php_menu
from modules.runtime.nodejs import show_nodejs_menu

__all__ = ["show_php_menu", "show_nodejs_menu"]
```

**Step 6: Commit structure**

```bash
git add modules/runtime/
git commit -m "refactor(runtime): create folder structure for PHP enhancements"
```

---

## Task 2: Create FPM Management Module

**Files:**
- Create: `modules/runtime/php/fpm.py`

**Step 1: Create fpm.py with menu and status functions**

```python
"""PHP-FPM pool management."""

import os
import re

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, service_control, require_root
from modules.runtime.php.utils import (
    get_installed_php_versions, get_fpm_pool_path, get_fpm_service_name,
    is_fpm_running, parse_fpm_pool_config, get_server_memory_mb,
)


def show_fpm_menu():
    """Display FPM Management submenu."""
    def get_status():
        versions = get_installed_php_versions()
        running = sum(1 for v in versions if is_fpm_running(v))
        return f"FPM Running: {running}/{len(versions)}"
    
    options = [
        ("status", "1. Pool Status"),
        ("config", "2. Configure Pool"),
        ("service", "3. Service Control"),
        ("create", "4. Create Custom Pool"),
        ("calculator", "5. Memory Calculator"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "status": show_pool_status,
        "config": configure_pool,
        "service": fpm_service_control,
        "create": create_custom_pool,
        "calculator": memory_calculator,
    }
    
    run_menu_loop("FPM Management", options, handlers, get_status)


def show_pool_status():
    """Show status of all PHP-FPM pools."""
    clear_screen()
    show_header()
    show_panel("PHP-FPM Pool Status", title="FPM Management", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_info("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "PHP", "style": "cyan"},
        {"name": "Status", "justify": "center"},
        {"name": "PM Mode", "justify": "center"},
        {"name": "Workers", "justify": "center"},
        {"name": "Max Children", "justify": "right"},
    ]
    
    rows = []
    for version in versions:
        service = get_fpm_service_name(version)
        running = is_fpm_running(version)
        status = "[green]Running[/green]" if running else "[red]Stopped[/red]"
        
        config = parse_fpm_pool_config(version)
        pm_mode = config.get("pm", "dynamic")
        max_children = config.get("pm.max_children", "5")
        
        # Get active workers
        workers = "-"
        if running:
            result = run_command(
                f"pgrep -c -f 'php-fpm: pool www.*{version}'",
                check=False, silent=True
            )
            if result.returncode == 0:
                workers = result.stdout.strip()
        
        rows.append([f"PHP {version}", status, pm_mode, workers, max_children])
    
    show_table("", columns, rows, show_header=True)
    press_enter_to_continue()


def configure_pool():
    """Configure PHP-FPM pool settings."""
    clear_screen()
    show_header()
    show_panel("Configure FPM Pool", title="FPM Management", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "Configure pool for:", versions)
    if not version:
        return
    
    config = parse_fpm_pool_config(version)
    
    console.print(f"[bold]Current Pool Settings (PHP {version}):[/bold]")
    console.print()
    console.print(f"  pm = {config.get('pm', 'dynamic')}")
    console.print(f"  pm.max_children = {config.get('pm.max_children', '5')}")
    console.print(f"  pm.start_servers = {config.get('pm.start_servers', '2')}")
    console.print(f"  pm.min_spare_servers = {config.get('pm.min_spare_servers', '1')}")
    console.print(f"  pm.max_spare_servers = {config.get('pm.max_spare_servers', '3')}")
    console.print(f"  pm.max_requests = {config.get('pm.max_requests', '500')}")
    console.print()
    
    # Select setting to change
    settings = [
        "pm (process manager mode)",
        "pm.max_children",
        "pm.start_servers",
        "pm.min_spare_servers",
        "pm.max_spare_servers",
        "pm.max_requests",
    ]
    
    setting = select_from_list("Select Setting", "Which setting to change?", settings)
    if not setting:
        return
    
    setting_key = setting.split(" ")[0]
    
    # Get new value
    if setting_key == "pm":
        new_value = select_from_list(
            "PM Mode", "Select process manager mode:",
            ["dynamic", "static", "ondemand"]
        )
    else:
        current = config.get(setting_key, "")
        new_value = text_input(f"Enter new value for {setting_key}:", default=current)
    
    if not new_value:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Update config file
    config_path = get_fpm_pool_path(version)
    success = _update_pool_config(config_path, setting_key, new_value)
    
    if success:
        show_success(f"Updated {setting_key} = {new_value}")
        console.print()
        if confirm_action("Restart PHP-FPM to apply changes?"):
            service_control(get_fpm_service_name(version), "restart")
            show_success("PHP-FPM restarted!")
    else:
        show_error("Failed to update configuration.")
    
    press_enter_to_continue()


def _update_pool_config(config_path, key, value):
    """Update a single value in pool config file."""
    try:
        with open(config_path, "r") as f:
            lines = f.readlines()
        
        updated = False
        new_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Match both active and commented versions
            if stripped.startswith(f"{key} =") or stripped.startswith(f";{key} ="):
                new_lines.append(f"{key} = {value}\n")
                updated = True
            else:
                new_lines.append(line)
        
        # Add if not found
        if not updated:
            # Find [www] section and add after it
            for i, line in enumerate(new_lines):
                if line.strip() == "[www]":
                    new_lines.insert(i + 1, f"{key} = {value}\n")
                    updated = True
                    break
        
        with open(config_path, "w") as f:
            f.writelines(new_lines)
        
        return True
    except Exception as e:
        show_error(f"Error updating config: {e}")
        return False


def fpm_service_control():
    """Start/Stop/Restart PHP-FPM services."""
    clear_screen()
    show_header()
    show_panel("FPM Service Control", title="FPM Management", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    # Show current status
    for version in versions:
        status = "[green]Running[/green]" if is_fpm_running(version) else "[red]Stopped[/red]"
        console.print(f"  PHP {version} FPM: {status}")
    console.print()
    
    version = select_from_list("Select PHP Version", "Control FPM for:", versions)
    if not version:
        return
    
    action = select_from_list(
        "Select Action", "What to do?",
        ["start", "stop", "restart", "reload"]
    )
    if not action:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    service = get_fpm_service_name(version)
    success = service_control(service, action)
    
    if success:
        show_success(f"PHP {version} FPM {action}ed successfully!")
    else:
        show_error(f"Failed to {action} PHP {version} FPM.")
    
    press_enter_to_continue()


def create_custom_pool():
    """Create a custom FPM pool for a specific site."""
    clear_screen()
    show_header()
    show_panel("Create Custom Pool", title="FPM Management", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "Create pool for:", versions)
    if not version:
        return
    
    pool_name = text_input("Enter pool name (e.g., mysite):")
    if not pool_name:
        return
    
    pool_name = pool_name.strip().lower().replace(" ", "_")
    
    # Check if pool exists
    pool_path = get_fpm_pool_path(version, pool_name)
    if os.path.exists(pool_path):
        show_error(f"Pool '{pool_name}' already exists.")
        press_enter_to_continue()
        return
    
    # Get user for pool
    user = text_input("Run as user:", default="www-data")
    if not user:
        return
    
    # Get max_children
    max_children = text_input("Max children (workers):", default="5")
    if not max_children:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Create pool config
    pool_config = f"""[{pool_name}]
user = {user}
group = {user}
listen = /run/php/php{version}-fpm-{pool_name}.sock
listen.owner = www-data
listen.group = www-data
listen.mode = 0660

pm = dynamic
pm.max_children = {max_children}
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
pm.max_requests = 500

; Logging
access.log = /var/log/php{version}-fpm-{pool_name}.access.log
slowlog = /var/log/php{version}-fpm-{pool_name}.slow.log
request_slowlog_timeout = 5s
"""
    
    try:
        with open(pool_path, "w") as f:
            f.write(pool_config)
        
        show_success(f"Pool '{pool_name}' created!")
        console.print(f"[dim]Config: {pool_path}[/dim]")
        console.print(f"[dim]Socket: /run/php/php{version}-fpm-{pool_name}.sock[/dim]")
        console.print()
        
        if confirm_action("Restart PHP-FPM to activate pool?"):
            service_control(get_fpm_service_name(version), "restart")
            show_success("PHP-FPM restarted!")
    except Exception as e:
        show_error(f"Failed to create pool: {e}")
    
    press_enter_to_continue()


def memory_calculator():
    """Calculate optimal FPM settings based on server memory."""
    clear_screen()
    show_header()
    show_panel("FPM Memory Calculator", title="FPM Management", style="cyan")
    
    total_mb = get_server_memory_mb()
    console.print(f"[bold]Server Memory:[/bold] {total_mb} MB")
    console.print()
    
    # Estimate memory per PHP process (average 30-50MB)
    avg_process_mb = 40
    
    # Reserve memory for OS and other services
    reserved_mb = min(512, total_mb * 0.2)  # 20% or 512MB, whichever is smaller
    available_mb = total_mb - reserved_mb
    
    # Calculate max_children
    recommended_max = max(2, int(available_mb / avg_process_mb))
    
    console.print("[bold]Recommendations:[/bold]")
    console.print()
    console.print(f"  Reserved for OS/services: {int(reserved_mb)} MB")
    console.print(f"  Available for PHP-FPM: {int(available_mb)} MB")
    console.print(f"  Avg memory per process: ~{avg_process_mb} MB")
    console.print()
    
    columns = [
        {"name": "Setting", "style": "cyan"},
        {"name": "Conservative", "justify": "center"},
        {"name": "Balanced", "justify": "center"},
        {"name": "Aggressive", "justify": "center"},
    ]
    
    conservative = max(2, int(recommended_max * 0.5))
    balanced = recommended_max
    aggressive = int(recommended_max * 1.5)
    
    rows = [
        ["pm.max_children", str(conservative), str(balanced), str(aggressive)],
        ["pm.start_servers", str(max(1, conservative // 4)), str(max(2, balanced // 4)), str(max(2, aggressive // 4))],
        ["pm.min_spare_servers", str(max(1, conservative // 5)), str(max(1, balanced // 5)), str(max(1, aggressive // 5))],
        ["pm.max_spare_servers", str(max(2, conservative // 3)), str(max(3, balanced // 3)), str(max(3, aggressive // 3))],
    ]
    
    show_table("", columns, rows, show_header=True)
    
    console.print()
    console.print("[dim]Conservative: Safe for shared servers, low memory usage[/dim]")
    console.print("[dim]Balanced: Good for most VPS, recommended starting point[/dim]")
    console.print("[dim]Aggressive: High traffic sites, monitor memory usage[/dim]")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/runtime/php/fpm.py
git commit -m "feat(runtime): add PHP-FPM management module"
```

---

## Execution Handoff

**Plan saved to:** `docs/plans/2025-01-15-php-fpm-management.md`

This plan covers:
- Task 1: Folder structure setup (runtime → php subfolder)
- Task 2: FPM Management module with 5 features

**Dependencies:** This plan should be executed first as it creates the folder structure needed by other plans.
