# PHP Security Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add PHP security hardening features including disable dangerous functions, open_basedir configuration, session security, expose_php toggle, and security audit.

**Architecture:** Create `modules/runtime/php/security.py` with functions to modify php.ini security settings. Each feature modifies specific directives in `/etc/php/{version}/fpm/php.ini`.

**Tech Stack:** Python, PHP configuration, php.ini security directives

**Dependency:** Requires `2025-01-15-php-fpm-management.md` to be executed first (creates folder structure).

---

## Task 1: Create Security Module

**Files:**
- Create: `modules/runtime/php/security.py`

**Step 1: Create security.py**

```python
"""PHP security hardening."""

import os
import re

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, service_control, require_root
from modules.runtime.php.utils import (
    get_installed_php_versions, get_fpm_service_name,
    PHP_INI_FPM, PHP_INI_CLI,
)


# Dangerous functions to disable
DANGEROUS_FUNCTIONS = {
    "strict": [
        "exec", "shell_exec", "system", "passthru", "popen", "proc_open",
        "proc_close", "proc_get_status", "proc_nice", "proc_terminate",
        "pcntl_exec", "pcntl_fork", "pcntl_signal", "pcntl_alarm",
        "dl", "putenv", "ini_set", "ini_restore", "ini_alter",
        "show_source", "highlight_file", "phpinfo",
    ],
    "moderate": [
        "exec", "shell_exec", "system", "passthru", "popen", "proc_open",
        "pcntl_exec", "dl",
    ],
    "minimal": [
        "exec", "shell_exec", "system", "passthru",
    ],
}

# Session security settings
SESSION_SECURITY = {
    "session.cookie_httponly": ("1", "Prevent JavaScript access to session cookie"),
    "session.cookie_secure": ("1", "Only send cookie over HTTPS"),
    "session.use_strict_mode": ("1", "Reject uninitialized session IDs"),
    "session.cookie_samesite": ("Strict", "Prevent CSRF via cookie"),
    "session.use_only_cookies": ("1", "Disable session ID in URL"),
    "session.use_trans_sid": ("0", "Disable transparent session ID"),
}


def show_security_menu():
    """Display Security Hardening submenu."""
    options = [
        ("functions", "1. Disable Dangerous Functions"),
        ("basedir", "2. Open Basedir"),
        ("session", "3. Session Security"),
        ("expose", "4. Expose PHP"),
        ("audit", "5. Security Audit"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "functions": disable_dangerous_functions,
        "basedir": configure_open_basedir,
        "session": configure_session_security,
        "expose": toggle_expose_php,
        "audit": security_audit,
    }
    
    run_menu_loop("Security Hardening", options, handlers)


def disable_dangerous_functions():
    """Configure disabled functions."""
    clear_screen()
    show_header()
    show_panel("Disable Dangerous Functions", title="Security", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "Configure for:", versions)
    if not version:
        return
    
    # Get current disabled functions
    result = run_command(
        f"php{version} -r \"echo ini_get('disable_functions');\"",
        check=False, silent=True
    )
    current = result.stdout.strip() if result.returncode == 0 else ""
    current_list = [f.strip() for f in current.split(',') if f.strip()]
    
    console.print(f"[bold]Current Disabled Functions ({len(current_list)}):[/bold]")
    if current_list:
        console.print(f"[dim]{', '.join(current_list[:10])}{'...' if len(current_list) > 10 else ''}[/dim]")
    else:
        console.print("[yellow]None disabled[/yellow]")
    console.print()
    
    # Options
    options = [
        f"Apply Strict Preset ({len(DANGEROUS_FUNCTIONS['strict'])} functions)",
        f"Apply Moderate Preset ({len(DANGEROUS_FUNCTIONS['moderate'])} functions)",
        f"Apply Minimal Preset ({len(DANGEROUS_FUNCTIONS['minimal'])} functions)",
        "Custom List",
        "Clear All (enable all functions)",
    ]
    
    choice = select_from_list("Select Option", "How to configure?", options)
    if not choice:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if "Strict" in choice:
        functions = DANGEROUS_FUNCTIONS["strict"]
    elif "Moderate" in choice:
        functions = DANGEROUS_FUNCTIONS["moderate"]
    elif "Minimal" in choice:
        functions = DANGEROUS_FUNCTIONS["minimal"]
    elif "Custom" in choice:
        console.print()
        console.print("[dim]Available dangerous functions:[/dim]")
        console.print(f"[dim]{', '.join(DANGEROUS_FUNCTIONS['strict'])}[/dim]")
        console.print()
        custom = text_input("Enter functions to disable (comma-separated):")
        if not custom:
            return
        functions = [f.strip() for f in custom.split(',') if f.strip()]
    else:  # Clear all
        functions = []
    
    # Update php.ini
    ini_path = PHP_INI_FPM.format(version=version)
    value = ','.join(functions) if functions else ""
    
    success = _update_php_ini(ini_path, "disable_functions", value)
    
    if success:
        if functions:
            show_success(f"Disabled {len(functions)} functions!")
            console.print()
            console.print("[bold yellow]Warning:[/bold yellow]")
            console.print("  Some applications (like Laravel Horizon, Composer) may need")
            console.print("  exec/shell_exec. Test thoroughly after applying.")
        else:
            show_success("All functions enabled!")
        
        console.print()
        if confirm_action("Restart PHP-FPM to apply changes?"):
            service_control(get_fpm_service_name(version), "restart")
            show_success("PHP-FPM restarted!")
    else:
        show_error("Failed to update configuration.")
    
    press_enter_to_continue()


def configure_open_basedir():
    """Configure open_basedir restriction."""
    clear_screen()
    show_header()
    show_panel("Open Basedir", title="Security", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "Configure for:", versions)
    if not version:
        return
    
    # Get current value
    result = run_command(
        f"php{version} -r \"echo ini_get('open_basedir');\"",
        check=False, silent=True
    )
    current = result.stdout.strip() if result.returncode == 0 else ""
    
    console.print(f"[bold]Current open_basedir:[/bold]")
    if current:
        console.print(f"  {current}")
    else:
        console.print("  [yellow]Not set (PHP can access entire filesystem)[/yellow]")
    console.print()
    
    # Options
    options = [
        "Set common preset (/var/www:/tmp:/usr/share/php)",
        "Set for specific site",
        "Custom paths",
        "Disable (allow full access)",
    ]
    
    choice = select_from_list("Select Option", "Configure:", options)
    if not choice:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if "common preset" in choice:
        value = "/var/www:/tmp:/usr/share/php:/usr/share/phpmyadmin"
    elif "specific site" in choice:
        # Get domains
        from modules.webserver.utils import get_configured_domains
        domains = get_configured_domains()
        if not domains:
            show_error("No domains configured.")
            press_enter_to_continue()
            return
        
        domain = select_from_list("Select Site", "Configure for:", domains)
        if not domain:
            return
        
        value = f"/var/www/{domain}:/tmp:/usr/share/php"
        console.print(f"[dim]Will restrict PHP to: {value}[/dim]")
    elif "Custom" in choice:
        console.print("[dim]Separate paths with colon (:)[/dim]")
        console.print("[dim]Example: /var/www:/tmp:/usr/share/php[/dim]")
        value = text_input("Enter paths:")
        if not value:
            return
    else:  # Disable
        value = ""
    
    # Update php.ini
    ini_path = PHP_INI_FPM.format(version=version)
    
    if value:
        success = _update_php_ini(ini_path, "open_basedir", value)
    else:
        # Comment out the directive
        success = _comment_php_ini(ini_path, "open_basedir")
    
    if success:
        if value:
            show_success("open_basedir configured!")
            console.print(f"[dim]PHP restricted to: {value}[/dim]")
        else:
            show_success("open_basedir disabled!")
        
        console.print()
        if confirm_action("Restart PHP-FPM to apply changes?"):
            service_control(get_fpm_service_name(version), "restart")
            show_success("PHP-FPM restarted!")
    else:
        show_error("Failed to update configuration.")
    
    press_enter_to_continue()


def configure_session_security():
    """Configure session security settings."""
    clear_screen()
    show_header()
    show_panel("Session Security", title="Security", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "Configure for:", versions)
    if not version:
        return
    
    # Show current settings
    console.print(f"[bold]Session Security Settings (PHP {version}):[/bold]")
    console.print()
    
    current_settings = {}
    for key, (recommended, desc) in SESSION_SECURITY.items():
        result = run_command(
            f"php{version} -r \"echo ini_get('{key}');\"",
            check=False, silent=True
        )
        current = result.stdout.strip() if result.returncode == 0 else "?"
        current_settings[key] = current
        
        is_secure = current == recommended
        status = "[green]✓[/green]" if is_secure else "[yellow]○[/yellow]"
        console.print(f"  {status} {key} = {current} (recommended: {recommended})")
    
    console.print()
    
    # Options
    options = [
        "Apply all recommended settings",
        "Configure individual setting",
    ]
    
    choice = select_from_list("Action", "What to do?", options)
    if not choice:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    ini_path = PHP_INI_FPM.format(version=version)
    
    if "all recommended" in choice:
        show_warning("Note: session.cookie_secure=1 requires HTTPS!")
        if not confirm_action("Apply all recommended session settings?"):
            return
        
        success = True
        for key, (value, _) in SESSION_SECURITY.items():
            if not _update_php_ini(ini_path, key, value):
                success = False
        
        if success:
            show_success("Session security settings applied!")
        else:
            show_error("Some settings may have failed.")
    else:
        # Individual setting
        setting_options = [f"{k} ({v[1]})" for k, v in SESSION_SECURITY.items()]
        setting = select_from_list("Select Setting", "Configure:", setting_options)
        if not setting:
            return
        
        key = setting.split(" (")[0]
        recommended, desc = SESSION_SECURITY[key]
        current = current_settings.get(key, "")
        
        new_value = text_input(f"Enter value for {key}:", default=recommended)
        if not new_value:
            return
        
        if _update_php_ini(ini_path, key, new_value):
            show_success(f"Updated {key} = {new_value}")
        else:
            show_error("Failed to update setting.")
    
    console.print()
    if confirm_action("Restart PHP-FPM to apply changes?"):
        service_control(get_fpm_service_name(version), "restart")
        show_success("PHP-FPM restarted!")
    
    press_enter_to_continue()


def toggle_expose_php():
    """Toggle expose_php setting."""
    clear_screen()
    show_header()
    show_panel("Expose PHP", title="Security", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "Configure for:", versions)
    if not version:
        return
    
    # Get current value
    result = run_command(
        f"php{version} -r \"echo ini_get('expose_php');\"",
        check=False, silent=True
    )
    current = result.stdout.strip() if result.returncode == 0 else "1"
    exposed = current == "1"
    
    console.print(f"[bold]Current Status:[/bold]")
    if exposed:
        console.print("  expose_php = On [yellow](PHP version visible in headers)[/yellow]")
        console.print()
        console.print("[dim]The X-Powered-By header reveals PHP version to attackers.[/dim]")
    else:
        console.print("  expose_php = Off [green](PHP version hidden)[/green]")
    console.print()
    
    new_value = "Off" if exposed else "On"
    if not confirm_action(f"Set expose_php to {new_value}?"):
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    ini_path = PHP_INI_FPM.format(version=version)
    value = "0" if exposed else "1"
    
    if _update_php_ini(ini_path, "expose_php", value):
        show_success(f"expose_php set to {new_value}!")
        
        console.print()
        if confirm_action("Restart PHP-FPM to apply changes?"):
            service_control(get_fpm_service_name(version), "restart")
            show_success("PHP-FPM restarted!")
    else:
        show_error("Failed to update configuration.")
    
    press_enter_to_continue()


def security_audit():
    """Run security audit on PHP configuration."""
    clear_screen()
    show_header()
    show_panel("Security Audit", title="Security", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "Audit:", versions)
    if not version:
        return
    
    clear_screen()
    show_header()
    show_panel(f"PHP {version} Security Audit", title="Security", style="cyan")
    
    checks = []
    recommendations = []
    
    # Check 1: expose_php
    result = run_command(f"php{version} -r \"echo ini_get('expose_php');\"", check=False, silent=True)
    expose = result.stdout.strip() if result.returncode == 0 else "1"
    ok = expose == "0"
    checks.append(("expose_php", ok, "Off" if ok else "On"))
    if not ok:
        recommendations.append("Set expose_php = Off to hide PHP version")
    
    # Check 2: display_errors
    result = run_command(f"php{version} -r \"echo ini_get('display_errors');\"", check=False, silent=True)
    display = result.stdout.strip() if result.returncode == 0 else "1"
    ok = display in ["0", "", "Off"]
    checks.append(("display_errors", ok, "Off" if ok else "On"))
    if not ok:
        recommendations.append("Set display_errors = Off in production")
    
    # Check 3: disable_functions
    result = run_command(f"php{version} -r \"echo ini_get('disable_functions');\"", check=False, silent=True)
    disabled = result.stdout.strip() if result.returncode == 0 else ""
    disabled_count = len([f for f in disabled.split(',') if f.strip()])
    ok = disabled_count >= 4  # At least minimal protection
    checks.append(("disable_functions", ok, f"{disabled_count} disabled"))
    if not ok:
        recommendations.append("Disable dangerous functions (exec, shell_exec, etc.)")
    
    # Check 4: open_basedir
    result = run_command(f"php{version} -r \"echo ini_get('open_basedir');\"", check=False, silent=True)
    basedir = result.stdout.strip() if result.returncode == 0 else ""
    ok = bool(basedir)
    checks.append(("open_basedir", ok, basedir[:40] + "..." if len(basedir) > 40 else basedir or "Not set"))
    if not ok:
        recommendations.append("Set open_basedir to restrict file access")
    
    # Check 5: allow_url_fopen
    result = run_command(f"php{version} -r \"echo ini_get('allow_url_fopen');\"", check=False, silent=True)
    url_fopen = result.stdout.strip() if result.returncode == 0 else "1"
    ok = url_fopen in ["0", ""]  # Disabled is more secure but may break things
    checks.append(("allow_url_fopen", None, "On" if url_fopen == "1" else "Off"))  # Neutral
    
    # Check 6: allow_url_include
    result = run_command(f"php{version} -r \"echo ini_get('allow_url_include');\"", check=False, silent=True)
    url_include = result.stdout.strip() if result.returncode == 0 else "0"
    ok = url_include in ["0", "", "Off"]
    checks.append(("allow_url_include", ok, "Off" if ok else "On"))
    if not ok:
        recommendations.append("Set allow_url_include = Off (critical!)")
    
    # Check 7: Session security
    session_ok = True
    for key, (recommended, _) in list(SESSION_SECURITY.items())[:3]:
        result = run_command(f"php{version} -r \"echo ini_get('{key}');\"", check=False, silent=True)
        value = result.stdout.strip() if result.returncode == 0 else ""
        if value != recommended:
            session_ok = False
            break
    checks.append(("Session Security", session_ok, "Configured" if session_ok else "Weak"))
    if not session_ok:
        recommendations.append("Configure session security settings")
    
    # Display results
    columns = [
        {"name": "Setting", "style": "cyan"},
        {"name": "Status", "justify": "center"},
        {"name": "Value"},
    ]
    
    rows = []
    passed = 0
    total = 0
    
    for name, ok, value in checks:
        if ok is None:
            status = "[dim]○ INFO[/dim]"
        elif ok:
            status = "[green]✓ PASS[/green]"
            passed += 1
            total += 1
        else:
            status = "[red]✗ FAIL[/red]"
            total += 1
        rows.append([name, status, value])
    
    show_table(f"Score: {passed}/{total}", columns, rows, show_header=True)
    
    # Show recommendations
    if recommendations:
        console.print()
        console.print("[bold yellow]Recommendations:[/bold yellow]")
        for rec in recommendations:
            console.print(f"  • {rec}")
    else:
        console.print()
        console.print("[bold green]All security checks passed![/bold green]")
    
    press_enter_to_continue()


def _update_php_ini(ini_path, key, value):
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


def _comment_php_ini(ini_path, key):
    """Comment out a setting in php.ini file."""
    try:
        with open(ini_path, "r") as f:
            content = f.read()
        
        pattern = rf'^(\s*){re.escape(key)}\s*=(.*)$'
        replacement = rf';\1{key} =\2'
        
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        with open(ini_path, "w") as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        show_error(f"Error updating {ini_path}: {e}")
        return False
```

**Step 2: Commit**

```bash
git add modules/runtime/php/security.py
git commit -m "feat(runtime): add PHP security hardening"
```

---

## Task 2: Create Install Module (move existing functions)

**Files:**
- Create: `modules/runtime/php/install.py`

**Step 1: Create install.py**

Copy functions from original `runtime.py`:
- `add_php_ppa()`
- `install_php_interactive()`, `install_php()`
- `install_extensions_interactive()`, `install_php_extensions()`
- `switch_php_interactive()`, `switch_php_version()`
- `list_php_versions()`
- `show_php_info_interactive()`, `show_php_info()`
- `install_composer()`
- `set_site_php_interactive()`, `set_site_php()`
- `_get_site_php_version()`

Update imports to use `modules.runtime.php.utils`.

**Step 2: Delete old runtime.py and commit**

```bash
rm modules/runtime.py
git add modules/runtime/
git commit -m "refactor(runtime): complete folder structure migration"
```

---

## Execution Handoff

**Plans saved to:**
1. `docs/plans/2025-01-15-php-fpm-management.md`
2. `docs/plans/2025-01-15-php-configuration.md`
3. `docs/plans/2025-01-15-php-extensions.md`
4. `docs/plans/2025-01-15-php-monitoring.md`
5. `docs/plans/2025-01-15-php-security.md`

**Execution Order:**
1. Execute `php-fpm-management.md` first (creates folder structure)
2. Execute remaining 4 plans in any order (all depend on folder structure)

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
