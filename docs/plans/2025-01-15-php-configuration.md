# PHP Configuration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add PHP configuration management including php.ini editor for common settings, OPcache tuning, view current settings, and restore defaults with backup.

**Architecture:** Create `modules/runtime/php/config.py` with menu-driven php.ini editing. Settings are modified in `/etc/php/{version}/fpm/php.ini` and `/etc/php/{version}/cli/php.ini`.

**Tech Stack:** Python, PHP configuration files, regex-based config editing

**Dependency:** Requires `2025-01-15-php-fpm-management.md` to be executed first (creates folder structure).

---

## Task 1: Create PHP Configuration Module

**Files:**
- Create: `modules/runtime/php/config.py`

**Step 1: Create config.py**

```python
"""PHP configuration management (php.ini editor)."""

import os
import re
import shutil
from datetime import datetime

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, service_control, require_root
from modules.runtime.php.utils import (
    get_installed_php_versions, get_fpm_service_name, is_fpm_running,
    PHP_INI_FPM, PHP_INI_CLI,
)


# Common php.ini settings with descriptions
PHP_SETTINGS = {
    "upload_max_filesize": {
        "description": "Maximum file upload size",
        "default": "2M",
        "examples": ["2M", "64M", "128M", "256M"],
    },
    "post_max_size": {
        "description": "Maximum POST data size (should be >= upload_max_filesize)",
        "default": "8M",
        "examples": ["8M", "64M", "128M", "256M"],
    },
    "memory_limit": {
        "description": "Maximum memory per script",
        "default": "128M",
        "examples": ["128M", "256M", "512M", "1G"],
    },
    "max_execution_time": {
        "description": "Maximum script execution time (seconds)",
        "default": "30",
        "examples": ["30", "60", "120", "300"],
    },
    "max_input_time": {
        "description": "Maximum input parsing time (seconds)",
        "default": "60",
        "examples": ["60", "120", "300"],
    },
    "date.timezone": {
        "description": "Default timezone",
        "default": "UTC",
        "examples": ["UTC", "Asia/Jakarta", "America/New_York", "Europe/London"],
    },
    "display_errors": {
        "description": "Show errors (Off for production)",
        "default": "Off",
        "examples": ["On", "Off"],
    },
    "error_reporting": {
        "description": "Error reporting level",
        "default": "E_ALL & ~E_DEPRECATED & ~E_STRICT",
        "examples": ["E_ALL", "E_ALL & ~E_DEPRECATED", "E_ALL & ~E_NOTICE"],
    },
}

# OPcache settings
OPCACHE_SETTINGS = {
    "opcache.enable": {
        "description": "Enable OPcache",
        "default": "1",
        "examples": ["0", "1"],
    },
    "opcache.memory_consumption": {
        "description": "OPcache memory (MB)",
        "default": "128",
        "examples": ["64", "128", "256", "512"],
    },
    "opcache.interned_strings_buffer": {
        "description": "Interned strings buffer (MB)",
        "default": "8",
        "examples": ["8", "16", "32"],
    },
    "opcache.max_accelerated_files": {
        "description": "Max cached files",
        "default": "10000",
        "examples": ["4000", "10000", "20000"],
    },
    "opcache.revalidate_freq": {
        "description": "Revalidate frequency (seconds, 0=always)",
        "default": "2",
        "examples": ["0", "2", "60"],
    },
    "opcache.validate_timestamps": {
        "description": "Check file timestamps (0=never, faster but needs restart)",
        "default": "1",
        "examples": ["0", "1"],
    },
}

# Backup directory
PHP_CONFIG_BACKUP_DIR = "/etc/vexo/php-config-backups"


def show_config_menu():
    """Display PHP Configuration submenu."""
    options = [
        ("quick", "1. Quick Settings"),
        ("opcache", "2. OPcache Tuning"),
        ("view", "3. View Current Settings"),
        ("restore", "4. Restore Defaults"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "quick": quick_settings,
        "opcache": opcache_tuning,
        "view": view_current_settings,
        "restore": restore_defaults,
    }
    
    run_menu_loop("PHP Configuration", options, handlers)


def quick_settings():
    """Edit common php.ini settings."""
    clear_screen()
    show_header()
    show_panel("Quick Settings", title="PHP Configuration", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "Configure:", versions)
    if not version:
        return
    
    # Show current values
    ini_path = PHP_INI_FPM.format(version=version)
    current = _parse_ini_settings(ini_path, PHP_SETTINGS.keys())
    
    console.print(f"[bold]Current Settings (PHP {version}):[/bold]")
    console.print()
    for key, info in PHP_SETTINGS.items():
        value = current.get(key, info["default"])
        console.print(f"  {key} = {value}")
    console.print()
    
    # Select setting to change
    setting_options = [f"{k} ({v['description']})" for k, v in PHP_SETTINGS.items()]
    choice = select_from_list("Select Setting", "Which setting to change?", setting_options)
    if not choice:
        return
    
    setting_key = choice.split(" (")[0]
    setting_info = PHP_SETTINGS[setting_key]
    
    # Get new value
    current_value = current.get(setting_key, setting_info["default"])
    
    if len(setting_info["examples"]) <= 5:
        new_value = select_from_list(
            f"Set {setting_key}",
            f"Current: {current_value}",
            setting_info["examples"]
        )
    else:
        console.print(f"[dim]Examples: {', '.join(setting_info['examples'])}[/dim]")
        new_value = text_input(f"Enter value for {setting_key}:", default=current_value)
    
    if not new_value:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Backup current config
    _backup_ini(version)
    
    # Update both FPM and CLI ini files
    fpm_success = _update_ini_setting(PHP_INI_FPM.format(version=version), setting_key, new_value)
    cli_success = _update_ini_setting(PHP_INI_CLI.format(version=version), setting_key, new_value)
    
    if fpm_success:
        show_success(f"Updated {setting_key} = {new_value}")
        
        # Handle related settings
        if setting_key == "upload_max_filesize":
            console.print()
            if confirm_action(f"Also set post_max_size to {new_value}?"):
                _update_ini_setting(PHP_INI_FPM.format(version=version), "post_max_size", new_value)
                _update_ini_setting(PHP_INI_CLI.format(version=version), "post_max_size", new_value)
                show_success(f"Updated post_max_size = {new_value}")
        
        console.print()
        if confirm_action("Restart PHP-FPM to apply changes?"):
            service_control(get_fpm_service_name(version), "restart")
            show_success("PHP-FPM restarted!")
    else:
        show_error("Failed to update configuration.")
    
    press_enter_to_continue()


def opcache_tuning():
    """Configure OPcache settings."""
    clear_screen()
    show_header()
    show_panel("OPcache Tuning", title="PHP Configuration", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "Configure OPcache for:", versions)
    if not version:
        return
    
    # Check if opcache is enabled
    ini_path = PHP_INI_FPM.format(version=version)
    current = _parse_ini_settings(ini_path, OPCACHE_SETTINGS.keys())
    
    # Show OPcache status
    console.print(f"[bold]OPcache Status (PHP {version}):[/bold]")
    console.print()
    
    opcache_enabled = current.get("opcache.enable", "0") == "1"
    if opcache_enabled:
        console.print("  Status: [green]Enabled[/green]")
        
        # Try to get hit rate
        result = run_command(
            f"php{version} -r \"if(function_exists('opcache_get_status')) {{ "
            f"$s = opcache_get_status(); "
            f"echo isset($s['opcache_statistics']) ? "
            f"round($s['opcache_statistics']['opcache_hit_rate'], 2) : 'N/A'; }}\"",
            check=False, silent=True
        )
        if result.returncode == 0 and result.stdout.strip():
            console.print(f"  Hit Rate: {result.stdout.strip()}%")
    else:
        console.print("  Status: [yellow]Disabled[/yellow]")
    
    console.print()
    console.print("[bold]Current Settings:[/bold]")
    for key, info in OPCACHE_SETTINGS.items():
        value = current.get(key, info["default"])
        console.print(f"  {key} = {value}")
    console.print()
    
    # Options
    options = ["Enable/Disable OPcache", "Configure Settings", "Apply Production Preset", "Apply Development Preset"]
    choice = select_from_list("Action", "What to do?", options)
    if not choice:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    _backup_ini(version)
    
    if choice == "Enable/Disable OPcache":
        new_value = "0" if opcache_enabled else "1"
        _update_ini_setting(ini_path, "opcache.enable", new_value)
        status = "enabled" if new_value == "1" else "disabled"
        show_success(f"OPcache {status}!")
    
    elif choice == "Configure Settings":
        setting_options = [f"{k} ({v['description']})" for k, v in OPCACHE_SETTINGS.items()]
        setting = select_from_list("Select Setting", "Configure:", setting_options)
        if setting:
            setting_key = setting.split(" (")[0]
            info = OPCACHE_SETTINGS[setting_key]
            new_value = select_from_list(f"Set {setting_key}", "Select value:", info["examples"])
            if new_value:
                _update_ini_setting(ini_path, setting_key, new_value)
                show_success(f"Updated {setting_key} = {new_value}")
    
    elif choice == "Apply Production Preset":
        _apply_opcache_preset(ini_path, "production")
        show_success("Production preset applied!")
    
    elif choice == "Apply Development Preset":
        _apply_opcache_preset(ini_path, "development")
        show_success("Development preset applied!")
    
    console.print()
    if confirm_action("Restart PHP-FPM to apply changes?"):
        service_control(get_fpm_service_name(version), "restart")
        show_success("PHP-FPM restarted!")
    
    press_enter_to_continue()


def _apply_opcache_preset(ini_path, preset):
    """Apply OPcache preset configuration."""
    if preset == "production":
        settings = {
            "opcache.enable": "1",
            "opcache.memory_consumption": "256",
            "opcache.interned_strings_buffer": "16",
            "opcache.max_accelerated_files": "20000",
            "opcache.revalidate_freq": "60",
            "opcache.validate_timestamps": "0",
        }
    else:  # development
        settings = {
            "opcache.enable": "1",
            "opcache.memory_consumption": "128",
            "opcache.interned_strings_buffer": "8",
            "opcache.max_accelerated_files": "10000",
            "opcache.revalidate_freq": "0",
            "opcache.validate_timestamps": "1",
        }
    
    for key, value in settings.items():
        _update_ini_setting(ini_path, key, value)


def view_current_settings():
    """View current PHP configuration."""
    clear_screen()
    show_header()
    show_panel("Current PHP Settings", title="PHP Configuration", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "View settings for:", versions)
    if not version:
        return
    
    clear_screen()
    show_header()
    show_panel(f"PHP {version} Configuration", title="PHP Configuration", style="cyan")
    
    # Get settings via php command (more accurate than parsing ini)
    all_settings = list(PHP_SETTINGS.keys()) + list(OPCACHE_SETTINGS.keys())
    
    columns = [
        {"name": "Setting", "style": "cyan"},
        {"name": "Value", "style": "white"},
    ]
    
    rows = []
    for setting in all_settings:
        result = run_command(
            f"php{version} -r \"echo ini_get('{setting}');\"",
            check=False, silent=True
        )
        value = result.stdout.strip() if result.returncode == 0 else "N/A"
        if value == "":
            value = "(empty)"
        rows.append([setting, value])
    
    show_table("", columns, rows, show_header=True)
    press_enter_to_continue()


def restore_defaults():
    """Restore php.ini to default values."""
    clear_screen()
    show_header()
    show_panel("Restore Defaults", title="PHP Configuration", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "Restore defaults for:", versions)
    if not version:
        return
    
    # Check for backups
    backup_dir = os.path.join(PHP_CONFIG_BACKUP_DIR, version)
    backups = []
    if os.path.exists(backup_dir):
        backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.ini')], reverse=True)
    
    if backups:
        console.print("[bold]Available Backups:[/bold]")
        for b in backups[:5]:
            console.print(f"  • {b}")
        console.print()
        
        if confirm_action("Restore from backup?"):
            backup_options = backups[:5]
            backup = select_from_list("Select Backup", "Restore from:", backup_options)
            if backup:
                _restore_from_backup(version, backup)
                show_success("Configuration restored from backup!")
                if confirm_action("Restart PHP-FPM?"):
                    service_control(get_fpm_service_name(version), "restart")
                press_enter_to_continue()
                return
    
    show_warning("This will reset php.ini to package defaults.")
    if not confirm_action("Reinstall PHP config package?"):
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Backup current first
    _backup_ini(version)
    
    # Reinstall config package
    result = run_command(
        f"apt-get install --reinstall -y php{version}-common",
        check=False, silent=True
    )
    
    if result.returncode == 0:
        show_success("Default configuration restored!")
        if confirm_action("Restart PHP-FPM?"):
            service_control(get_fpm_service_name(version), "restart")
    else:
        show_error("Failed to restore defaults.")
    
    press_enter_to_continue()


def _parse_ini_settings(ini_path, keys):
    """Parse specific settings from php.ini file."""
    settings = {}
    
    if not os.path.exists(ini_path):
        return settings
    
    try:
        with open(ini_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(";"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    if key in keys:
                        settings[key] = value.strip()
    except Exception:
        pass
    
    return settings


def _update_ini_setting(ini_path, key, value):
    """Update a setting in php.ini file."""
    try:
        with open(ini_path, "r") as f:
            content = f.read()
        
        # Pattern to match setting (with or without semicolon comment)
        pattern = rf'^[;\s]*{re.escape(key)}\s*=.*$'
        replacement = f"{key} = {value}"
        
        new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
        
        # If not found, add at end
        if count == 0:
            new_content = content.rstrip() + f"\n{key} = {value}\n"
        
        with open(ini_path, "w") as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        show_error(f"Error updating {ini_path}: {e}")
        return False


def _backup_ini(version):
    """Create backup of php.ini files."""
    backup_dir = os.path.join(PHP_CONFIG_BACKUP_DIR, version)
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    fpm_ini = PHP_INI_FPM.format(version=version)
    if os.path.exists(fpm_ini):
        shutil.copy2(fpm_ini, os.path.join(backup_dir, f"fpm_{timestamp}.ini"))
    
    cli_ini = PHP_INI_CLI.format(version=version)
    if os.path.exists(cli_ini):
        shutil.copy2(cli_ini, os.path.join(backup_dir, f"cli_{timestamp}.ini"))
    
    # Keep only last 5 backups per type
    for prefix in ["fpm_", "cli_"]:
        files = sorted([f for f in os.listdir(backup_dir) if f.startswith(prefix)], reverse=True)
        for old_file in files[5:]:
            os.remove(os.path.join(backup_dir, old_file))


def _restore_from_backup(version, backup_file):
    """Restore php.ini from backup."""
    backup_dir = os.path.join(PHP_CONFIG_BACKUP_DIR, version)
    backup_path = os.path.join(backup_dir, backup_file)
    
    if backup_file.startswith("fpm_"):
        target = PHP_INI_FPM.format(version=version)
    else:
        target = PHP_INI_CLI.format(version=version)
    
    shutil.copy2(backup_path, target)
```

**Step 2: Commit**

```bash
git add modules/runtime/php/config.py
git commit -m "feat(runtime): add PHP configuration management"
```

---

## Execution Handoff

**Plan saved to:** `docs/plans/2025-01-15-php-configuration.md`

This plan covers:
- Quick Settings (8 common php.ini values)
- OPcache Tuning (with production/development presets)
- View Current Settings
- Restore Defaults (with backup support)

**Dependency:** Execute after `2025-01-15-php-fpm-management.md`
