# Task 6.0: Implement PHP Runtime Module - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the PHP Runtime module for installing multiple PHP versions, Composer, Laravel-compatible extensions, and per-site PHP isolation.

**Architecture:** File `modules/runtime.py` will contain both PHP and Node.js functions (Task 7). PHP versions are installed from ondrej/php PPA. Each version runs its own FPM service. The module supports PHP 8.3, 8.4, and 8.5. Per-site PHP isolation is achieved by configuring each Nginx vhost to use a specific PHP-FPM socket.

**Tech Stack:** PHP 8.3/8.4/8.5, PHP-FPM, ondrej/php PPA, Composer, update-alternatives for CLI switching

**Note:** Development only - no testing/running. Code will be tested by user on target environment.

---

## Task 6.1: Create modules/runtime.py with PHP menu

**Files:**
- Create: `modules/runtime.py`

**Step 1: Create runtime.py with imports and PHP menu**

```python
"""PHP & Node.js Runtime management module for vexo."""

import os

from config import PHP_VERSIONS, PHP_FPM_PATH, NVM_DIR, NVM_INSTALL_URL
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
from ui.menu import show_submenu, confirm_action, select_from_list
from utils.shell import (
    run_command,
    run_command_with_progress,
    run_command_realtime,
    is_installed,
    is_service_running,
    service_control,
    require_root,
)


# PHP versions to support
PHP_VERSIONS = ["8.3", "8.4", "8.5"]

# Laravel-compatible PHP extensions
PHP_EXTENSIONS = [
    "cli",
    "fpm",
    "common",
    # Laravel required
    "bcmath",
    "ctype",
    "curl",
    "dom",
    "fileinfo",
    "mbstring",
    "pdo",
    "tokenizer",
    "xml",
    # Database
    "mysql",
    "pgsql",
    "sqlite3",
    # Common/recommended
    "zip",
    "gd",
    "intl",
    "opcache",
    "redis",
    "imagick",
    "soap",
    "imap",
    "exif",
    "pcntl",
]


def show_php_menu():
    """
    Display the PHP Runtime submenu and handle user selection.
    
    Returns when user selects 'back' or cancels.
    """
    while True:
        clear_screen()
        show_header()
        
        # Show current default PHP version
        default_php = _get_default_php_version()
        if default_php:
            console.print(f"[dim]Default PHP: {default_php}[/dim]")
        else:
            console.print("[dim]Default PHP: Not installed[/dim]")
        console.print()
        
        choice = show_submenu(
            title="PHP Runtime Management",
            options=[
                ("list", "1. List PHP Versions"),
                ("install", "2. Install PHP Version"),
                ("switch", "3. Switch Default PHP"),
                ("extensions", "4. Install Extensions"),
                ("composer", "5. Install/Update Composer"),
                ("site_php", "6. Set PHP Version for Site"),
                ("info", "7. PHP Info"),
                ("back", "← Back to Main Menu"),
            ],
        )
        
        if choice == "list":
            list_php_versions()
        elif choice == "install":
            install_php_interactive()
        elif choice == "switch":
            switch_php_interactive()
        elif choice == "extensions":
            install_extensions_interactive()
        elif choice == "composer":
            install_composer()
        elif choice == "site_php":
            set_site_php_interactive()
        elif choice == "info":
            show_php_info_interactive()
        elif choice == "back" or choice is None:
            break
```

**Step 2: Commit**

```bash
git add modules/runtime.py && git commit -m "feat(modules): add runtime.py with PHP menu structure"
```

---

## Task 6.2: Add add_php_ppa() function

**Files:**
- Modify: `modules/runtime.py`

**Step 1: Add PPA management function**

Append to `modules/runtime.py`:

```python


def add_php_ppa():
    """
    Add ondrej/php PPA for multiple PHP versions.
    
    Returns:
        bool: True if successful or already added
    """
    # Check if PPA is already added
    result = run_command(
        "grep -r 'ondrej/php' /etc/apt/sources.list.d/ 2>/dev/null",
        check=False,
        silent=True
    )
    
    if result.returncode == 0:
        show_info("PHP PPA already added.")
        return True
    
    show_info("Adding ondrej/php PPA...")
    
    # Install software-properties-common if not present
    if not is_installed("software-properties-common"):
        result = run_command_with_progress(
            "apt install -y software-properties-common",
            "Installing software-properties-common..."
        )
        if result.returncode != 0:
            show_error("Failed to install software-properties-common")
            return False
    
    # Add PPA
    result = run_command_with_progress(
        "add-apt-repository -y ppa:ondrej/php",
        "Adding PHP PPA..."
    )
    
    if result.returncode != 0:
        show_error("Failed to add PHP PPA")
        return False
    
    # Update package lists
    result = run_command_with_progress(
        "apt update",
        "Updating package lists..."
    )
    
    if result.returncode != 0:
        show_warning("PPA added but failed to update package lists")
        return False
    
    show_success("PHP PPA added successfully!")
    return True
```

**Step 2: Commit**

```bash
git add modules/runtime.py && git commit -m "feat(modules): add add_php_ppa() function"
```

---

## Task 6.3: Add install_php() function

**Files:**
- Modify: `modules/runtime.py`

**Step 1: Add PHP installation functions**

Append to `modules/runtime.py`:

```python


def install_php_interactive():
    """Interactive prompt to install a PHP version."""
    clear_screen()
    show_header()
    show_panel("Install PHP Version", title="PHP Runtime", style="cyan")
    
    # Show available versions
    console.print("[bold]Available PHP versions:[/bold]")
    console.print()
    for version in PHP_VERSIONS:
        installed = is_installed(f"php{version}-fpm")
        status = "[green]Installed[/green]" if installed else "[dim]Not installed[/dim]"
        console.print(f"  • PHP {version} - {status}")
    console.print()
    
    # Let user select version
    version = select_from_list(
        title="Install PHP",
        message="Select PHP version to install:",
        options=PHP_VERSIONS
    )
    
    if not version:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Check if already installed
    if is_installed(f"php{version}-fpm"):
        show_info(f"PHP {version} is already installed.")
        if not confirm_action(f"Reinstall PHP {version}?"):
            press_enter_to_continue()
            return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = install_php(version)
    
    if success:
        show_success(f"PHP {version} installed successfully!")
    else:
        show_error(f"Failed to install PHP {version}")
    
    press_enter_to_continue()


def install_php(version, with_extensions=True):
    """
    Install a specific PHP version with FPM.
    
    Args:
        version: PHP version (e.g., "8.2")
        with_extensions: If True, install common extensions
    
    Returns:
        bool: True if successful
    """
    # Add PPA first
    if not add_php_ppa():
        return False
    
    console.print()
    show_info(f"Installing PHP {version}...")
    
    # Base packages
    packages = [f"php{version}", f"php{version}-fpm"]
    
    # Add common extensions if requested
    if with_extensions:
        for ext in PHP_EXTENSIONS:
            if ext not in ["cli", "fpm"]:  # These are already included
                packages.append(f"php{version}-{ext}")
    
    # Install packages
    packages_str = " ".join(packages)
    returncode = run_command_realtime(
        f"apt install -y {packages_str}",
        f"Installing PHP {version} packages..."
    )
    
    if returncode != 0:
        show_error(f"Failed to install PHP {version}")
        return False
    
    # Start and enable FPM service
    fpm_service = f"php{version}-fpm"
    service_control(fpm_service, "start")
    service_control(fpm_service, "enable")
    
    console.print()
    if is_service_running(fpm_service):
        show_success(f"PHP {version} FPM is running!")
    else:
        show_warning(f"PHP {version} installed but FPM may not be running")
    
    return True
```

**Step 2: Commit**

```bash
git add modules/runtime.py && git commit -m "feat(modules): add install_php() and install_php_interactive()"
```

---

## Task 6.4: Add install_php_extensions() function

**Files:**
- Modify: `modules/runtime.py`

**Step 1: Add extension installation functions**

Append to `modules/runtime.py`:

```python


def install_extensions_interactive():
    """Interactive prompt to install PHP extensions."""
    clear_screen()
    show_header()
    show_panel("Install PHP Extensions", title="PHP Runtime", style="cyan")
    
    # Get installed PHP versions
    installed_versions = _get_installed_php_versions()
    
    if not installed_versions:
        show_error("No PHP versions installed. Please install PHP first.")
        press_enter_to_continue()
        return
    
    # Select version
    version = select_from_list(
        title="Select PHP Version",
        message="Install extensions for which PHP version?",
        options=installed_versions
    )
    
    if not version:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Show available extensions
    console.print()
    console.print("[bold]Extensions to install:[/bold]")
    console.print()
    for ext in PHP_EXTENSIONS:
        if ext not in ["cli", "fpm"]:
            pkg = f"php{version}-{ext}"
            installed = is_installed(pkg)
            status = "[green]✓[/green]" if installed else "[dim]○[/dim]"
            console.print(f"  {status} {ext}")
    console.print()
    
    if not confirm_action(f"Install all extensions for PHP {version}?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = install_php_extensions(version)
    
    if success:
        show_success(f"Extensions installed for PHP {version}!")
    else:
        show_error("Some extensions may have failed to install")
    
    press_enter_to_continue()


def install_php_extensions(version, extensions=None):
    """
    Install PHP extensions for a specific version.
    
    Args:
        version: PHP version (e.g., "8.2")
        extensions: List of extensions, or None for all common extensions
    
    Returns:
        bool: True if successful
    """
    if extensions is None:
        extensions = [ext for ext in PHP_EXTENSIONS if ext not in ["cli", "fpm"]]
    
    packages = [f"php{version}-{ext}" for ext in extensions]
    packages_str = " ".join(packages)
    
    show_info(f"Installing extensions for PHP {version}...")
    
    returncode = run_command_realtime(
        f"apt install -y {packages_str}",
        f"Installing {len(packages)} extensions..."
    )
    
    # Restart FPM to load new extensions
    fpm_service = f"php{version}-fpm"
    if is_service_running(fpm_service):
        service_control(fpm_service, "restart")
    
    return returncode == 0
```

**Step 2: Commit**

```bash
git add modules/runtime.py && git commit -m "feat(modules): add install_php_extensions() function"
```

---

## Task 6.5: Add switch_php_version() function

**Files:**
- Modify: `modules/runtime.py`

**Step 1: Add PHP version switching functions**

Append to `modules/runtime.py`:

```python


def switch_php_interactive():
    """Interactive prompt to switch default PHP version."""
    clear_screen()
    show_header()
    show_panel("Switch Default PHP Version", title="PHP Runtime", style="cyan")
    
    installed_versions = _get_installed_php_versions()
    
    if not installed_versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    if len(installed_versions) < 2:
        show_info("Only one PHP version installed. Nothing to switch.")
        press_enter_to_continue()
        return
    
    current = _get_default_php_version()
    console.print(f"[dim]Current default: PHP {current}[/dim]")
    console.print()
    
    version = select_from_list(
        title="Switch PHP Version",
        message="Select new default PHP version:",
        options=installed_versions
    )
    
    if not version:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    if version == current:
        show_info(f"PHP {version} is already the default.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = switch_php_version(version)
    
    if success:
        show_success(f"Switched to PHP {version}!")
        # Show new version
        result = run_command("php -v | head -1", check=False, silent=True)
        if result.returncode == 0:
            console.print(f"[dim]{result.stdout.strip()}[/dim]")
    else:
        show_error(f"Failed to switch to PHP {version}")
    
    press_enter_to_continue()


def switch_php_version(version):
    """
    Switch the default PHP CLI version using update-alternatives.
    
    Args:
        version: PHP version (e.g., "8.2")
    
    Returns:
        bool: True if successful
    """
    php_bin = f"/usr/bin/php{version}"
    
    # Check if the version exists
    if not os.path.exists(php_bin):
        show_error(f"PHP {version} not found at {php_bin}")
        return False
    
    show_info(f"Switching to PHP {version}...")
    
    # Update alternatives for php
    result = run_command(
        f"update-alternatives --set php {php_bin}",
        check=False,
        silent=True
    )
    
    if result.returncode != 0:
        # If update-alternatives fails, try to set it up first
        run_command(
            f"update-alternatives --install /usr/bin/php php {php_bin} 1",
            check=False,
            silent=True
        )
        result = run_command(
            f"update-alternatives --set php {php_bin}",
            check=False,
            silent=True
        )
    
    # Also update phpize and php-config if available
    phpize = f"/usr/bin/phpize{version}"
    if os.path.exists(phpize):
        run_command(
            f"update-alternatives --set phpize {phpize}",
            check=False,
            silent=True
        )
    
    php_config = f"/usr/bin/php-config{version}"
    if os.path.exists(php_config):
        run_command(
            f"update-alternatives --set php-config {php_config}",
            check=False,
            silent=True
        )
    
    return result.returncode == 0
```

**Step 2: Commit**

```bash
git add modules/runtime.py && git commit -m "feat(modules): add switch_php_version() function"
```

---

## Task 6.6: Add list_php_versions() function

**Files:**
- Modify: `modules/runtime.py`

**Step 1: Add PHP listing function**

Append to `modules/runtime.py`:

```python


def list_php_versions():
    """Display a table of installed PHP versions."""
    clear_screen()
    show_header()
    show_panel("Installed PHP Versions", title="PHP Runtime", style="cyan")
    
    installed = _get_installed_php_versions()
    
    if not installed:
        show_info("No PHP versions installed.")
        console.print()
        console.print("[dim]Use 'Install PHP Version' to install PHP.[/dim]")
        press_enter_to_continue()
        return
    
    default_version = _get_default_php_version()
    
    columns = [
        {"name": "Version", "style": "cyan"},
        {"name": "Default", "justify": "center"},
        {"name": "FPM Status", "justify": "center"},
        {"name": "FPM Socket"},
    ]
    
    rows = []
    for version in installed:
        is_default = "[green]✓[/green]" if version == default_version else ""
        
        fpm_service = f"php{version}-fpm"
        if is_service_running(fpm_service):
            fpm_status = "[green]Running[/green]"
        elif is_installed(f"php{version}-fpm"):
            fpm_status = "[red]Stopped[/red]"
        else:
            fpm_status = "[dim]Not installed[/dim]"
        
        socket = f"/run/php/php{version}-fpm.sock"
        
        rows.append([f"PHP {version}", is_default, fpm_status, socket])
    
    show_table(f"Total: {len(installed)} version(s)", columns, rows)
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/runtime.py && git commit -m "feat(modules): add list_php_versions() function"
```

---

## Task 6.7: Add show_php_info() and helper functions

**Files:**
- Modify: `modules/runtime.py`

**Step 1: Add PHP info and helper functions**

Append to `modules/runtime.py`:

```python


def show_php_info_interactive():
    """Interactive prompt to show PHP info."""
    clear_screen()
    show_header()
    show_panel("PHP Information", title="PHP Runtime", style="cyan")
    
    installed = _get_installed_php_versions()
    
    if not installed:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list(
        title="PHP Info",
        message="Select PHP version:",
        options=installed
    )
    
    if not version:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    show_php_info(version)
    press_enter_to_continue()


def show_php_info(version):
    """
    Display information about a specific PHP version.
    
    Args:
        version: PHP version (e.g., "8.2")
    """
    clear_screen()
    show_header()
    show_panel(f"PHP {version} Information", title="PHP Runtime", style="cyan")
    
    # Get PHP version info
    php_bin = f"/usr/bin/php{version}"
    result = run_command(f"{php_bin} -v | head -1", check=False, silent=True)
    if result.returncode == 0:
        console.print(f"[bold]Version:[/bold] {result.stdout.strip()}")
    
    # Get ini file location
    result = run_command(f"{php_bin} --ini | grep 'Loaded Configuration'", check=False, silent=True)
    if result.returncode == 0:
        console.print(f"[bold]Config:[/bold] {result.stdout.strip().split(':')[-1].strip()}")
    
    console.print()
    console.print("[bold]Installed Extensions:[/bold]")
    console.print()
    
    # Get loaded extensions
    result = run_command(f"{php_bin} -m", check=False, silent=True)
    if result.returncode == 0:
        extensions = [ext.strip() for ext in result.stdout.strip().split('\n') if ext.strip() and not ext.startswith('[')]
        
        # Display in columns
        cols = 4
        for i in range(0, len(extensions), cols):
            row = extensions[i:i+cols]
            console.print("  " + "  ".join(f"[dim]{ext:20}[/dim]" for ext in row))
    
    console.print()
    
    # FPM status
    fpm_service = f"php{version}-fpm"
    if is_service_running(fpm_service):
        console.print(f"[bold]FPM Status:[/bold] [green]Running[/green]")
    else:
        console.print(f"[bold]FPM Status:[/bold] [red]Not running[/red]")


def _get_installed_php_versions():
    """Get list of installed PHP versions."""
    installed = []
    for version in PHP_VERSIONS:
        if is_installed(f"php{version}") or is_installed(f"php{version}-cli"):
            installed.append(version)
    return installed


def _get_default_php_version():
    """Get the current default PHP CLI version."""
    result = run_command("php -v 2>/dev/null | head -1", check=False, silent=True)
    if result.returncode != 0:
        return None
    
    # Parse version from output like "PHP 8.2.0 (cli)..."
    output = result.stdout.strip()
    if "PHP" in output:
        parts = output.split()
        if len(parts) >= 2:
            version = parts[1]
            # Return just major.minor (e.g., "8.2" from "8.2.0")
            return ".".join(version.split(".")[:2])
    return None
```

**Step 2: Commit**

```bash
git add modules/runtime.py && git commit -m "feat(modules): add show_php_info() and helper functions"
```

---

## Task 6.8: Add install_composer() function

**Files:**
- Modify: `modules/runtime.py`

**Step 1: Add Composer installation function**

Append to `modules/runtime.py`:

```python


def install_composer():
    """Install or update Composer globally."""
    clear_screen()
    show_header()
    show_panel("Install/Update Composer", title="PHP Runtime", style="cyan")
    
    # Check if PHP is installed
    if not _get_installed_php_versions():
        show_error("No PHP versions installed. Please install PHP first.")
        press_enter_to_continue()
        return
    
    # Check if Composer is already installed
    result = run_command("composer --version 2>/dev/null", check=False, silent=True)
    if result.returncode == 0:
        console.print(f"[dim]Current: {result.stdout.strip()}[/dim]")
        console.print()
        if not confirm_action("Composer is already installed. Update to latest version?"):
            press_enter_to_continue()
            return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    show_info("Downloading Composer installer...")
    
    # Download installer
    result = run_command_with_progress(
        "curl -sS https://getcomposer.org/installer -o /tmp/composer-setup.php",
        "Downloading Composer..."
    )
    
    if result.returncode != 0:
        show_error("Failed to download Composer installer.")
        press_enter_to_continue()
        return
    
    # Verify installer (optional but recommended)
    show_info("Installing Composer globally...")
    
    # Install Composer
    result = run_command_with_progress(
        "php /tmp/composer-setup.php --install-dir=/usr/local/bin --filename=composer",
        "Installing Composer..."
    )
    
    # Cleanup
    run_command("rm -f /tmp/composer-setup.php", check=False, silent=True)
    
    if result.returncode != 0:
        show_error("Failed to install Composer.")
        press_enter_to_continue()
        return
    
    # Verify installation
    result = run_command("composer --version", check=False, silent=True)
    if result.returncode == 0:
        show_success("Composer installed successfully!")
        console.print(f"[dim]{result.stdout.strip()}[/dim]")
    else:
        show_warning("Composer installed but verification failed.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/runtime.py && git commit -m "feat(modules): add install_composer() function"
```

---

## Task 6.9: Add set_site_php() function for per-site PHP isolation

**Files:**
- Modify: `modules/runtime.py`

**Step 1: Add per-site PHP configuration functions**

Append to `modules/runtime.py`:

```python


def set_site_php_interactive():
    """Interactive prompt to set PHP version for a specific site."""
    clear_screen()
    show_header()
    show_panel("Set PHP Version for Site", title="PHP Runtime", style="cyan")
    
    # Get installed PHP versions
    installed_php = _get_installed_php_versions()
    if not installed_php:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    # Get configured domains
    from modules.webserver import _get_configured_domains
    domains = _get_configured_domains()
    
    if not domains:
        show_error("No domains configured. Add a domain first.")
        press_enter_to_continue()
        return
    
    # Select domain
    domain = select_from_list(
        title="Select Site",
        message="Configure PHP for which site?",
        options=domains
    )
    
    if not domain:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Show current PHP version for site
    current_php = _get_site_php_version(domain)
    if current_php:
        console.print(f"[dim]Current PHP for {domain}: {current_php}[/dim]")
    else:
        console.print(f"[dim]PHP not configured for {domain}[/dim]")
    console.print()
    
    # Select PHP version
    version = select_from_list(
        title="Select PHP Version",
        message=f"Use which PHP version for {domain}?",
        options=installed_php
    )
    
    if not version:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = set_site_php(domain, version)
    
    if success:
        show_success(f"Site {domain} now uses PHP {version}!")
        console.print(f"[dim]FPM Socket: /run/php/php{version}-fpm.sock[/dim]")
    else:
        show_error(f"Failed to configure PHP for {domain}")
    
    press_enter_to_continue()


def set_site_php(domain, version):
    """
    Configure a site to use a specific PHP version.
    
    Updates the Nginx config to use the correct PHP-FPM socket.
    
    Args:
        domain: Domain name
        version: PHP version (e.g., "8.4")
    
    Returns:
        bool: True if successful
    """
    from config import NGINX_SITES_AVAILABLE
    
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    
    if not os.path.exists(config_path):
        show_error(f"Config not found: {config_path}")
        return False
    
    try:
        # Read current config
        with open(config_path, "r") as f:
            config = f.read()
        
        # Check if PHP block exists and is commented
        php_block = f'''    location ~ \\.php$ {{
        fastcgi_pass unix:/run/php/php{version}-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
        include fastcgi_params;
        fastcgi_hide_header X-Powered-By;
    }}'''
        
        # Remove existing PHP location block (commented or not)
        import re
        # Remove commented PHP block
        config = re.sub(
            r'\n\s*#\s*location\s*~\s*\\.php\$\s*\{[^}]*\}',
            '',
            config,
            flags=re.DOTALL
        )
        # Remove uncommented PHP block
        config = re.sub(
            r'\n\s*location\s*~\s*\\.php\$\s*\{[^}]*\}',
            '',
            config,
            flags=re.DOTALL
        )
        
        # Insert PHP block before the last closing brace
        # Find the position of the last }
        last_brace = config.rfind('}')
        if last_brace > 0:
            config = config[:last_brace] + "\n" + php_block + "\n" + config[last_brace:]
        
        # Write updated config
        with open(config_path, "w") as f:
            f.write(config)
        
        # Test and reload Nginx
        result = run_command("nginx -t", check=False, silent=True)
        if result.returncode != 0:
            show_error("Nginx configuration test failed!")
            console.print(f"[dim]{result.stderr}[/dim]")
            return False
        
        from utils.shell import service_control
        return service_control("nginx", "reload")
    
    except Exception as e:
        show_error(f"Error configuring PHP: {e}")
        return False


def _get_site_php_version(domain):
    """Get the PHP version configured for a site."""
    from config import NGINX_SITES_AVAILABLE
    import re
    
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    
    try:
        with open(config_path, "r") as f:
            config = f.read()
        
        # Look for fastcgi_pass unix:/run/php/phpX.X-fpm.sock
        match = re.search(r'fastcgi_pass\s+unix:/run/php/php(\d+\.\d+)-fpm\.sock', config)
        if match:
            return match.group(1)
        return None
    except Exception:
        return None
```

**Step 2: Commit**

```bash
git add modules/runtime.py && git commit -m "feat(modules): add set_site_php() for per-site PHP isolation"
```

---

## Task 6.10: Update config.py with new PHP versions

**Files:**
- Modify: `config.py`

**Step 1: Update PHP_VERSIONS in config.py**

Change line in `config.py`:

```python
# Paths - PHP
PHP_FPM_PATH = "/etc/php"
PHP_VERSIONS = ["8.3", "8.4", "8.5"]
```

**Step 2: Commit**

```bash
git add config.py && git commit -m "chore(config): update PHP versions to 8.3, 8.4, 8.5"
```

---

## Task 6.11: Update modules/__init__.py

**Files:**
- Modify: `modules/__init__.py`

**Step 1: Add runtime module export**

```python
"""Business logic modules for vexo - system, webserver, runtime, database, email."""

from modules import system
from modules import webserver
from modules import runtime
```

**Step 2: Commit**

```bash
git add modules/__init__.py && git commit -m "feat(modules): add runtime module export"
```

---

## Task 6.12: Update task list

Mark Task 6.0 and all sub-tasks as completed in `tasks/tasks-vexo.md`

---

## Summary

After completing this plan:

```
modules/
├── __init__.py      ✅ Exports system, webserver, runtime
├── system.py        ✅ System setup
├── webserver.py     ✅ Nginx & domain
└── runtime.py       ✅ PHP runtime (Node.js will be added in Task 7)
```

**Functions available after Task 6:**

| Function | Description |
|----------|-------------|
| `show_php_menu()` | Display PHP submenu (7 options) |
| `add_php_ppa()` | Add ondrej/php PPA |
| `install_php(version)` | Install PHP with FPM & Laravel extensions |
| `install_php_extensions(version)` | Install additional extensions |
| `switch_php_version(version)` | Switch default PHP CLI |
| `list_php_versions()` | Show installed versions & FPM status |
| `install_composer()` | Install/update Composer globally |
| `set_site_php(domain, version)` | Configure per-site PHP version |
| `show_php_info(version)` | Show version details & extensions |

**PHP Versions:** 8.3, 8.4, 8.5

**Laravel Extensions (27):**
`cli`, `fpm`, `common`, `bcmath`, `ctype`, `curl`, `dom`, `fileinfo`, `mbstring`, `pdo`, `tokenizer`, `xml`, `mysql`, `pgsql`, `sqlite3`, `zip`, `gd`, `intl`, `opcache`, `redis`, `imagick`, `soap`, `imap`, `exif`, `pcntl`

**Key Features:**
- **Multi-version:** PHP 8.3, 8.4, 8.5 support
- **Laravel-ready:** All required + recommended extensions
- **Composer:** Global installation & updates
- **Per-site isolation:** Each domain can use different PHP-FPM socket
