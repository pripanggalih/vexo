"""PHP & Node.js Runtime management module for vexo-cli."""

import os
import re

from config import PHP_FPM_PATH, NVM_DIR, NVM_INSTALL_URL
from ui.components import (
    console,
    show_panel,
    show_table,
    show_success,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import confirm_action, select_from_list, run_menu_loop
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
]


def show_php_menu():
    """Display the PHP Runtime submenu."""
    def get_status():
        default_php = _get_default_php_version()
        if default_php:
            return f"Default PHP: {default_php}"
        return "Default PHP: Not installed"
    
    def get_options():
        options = []
        installed_php = _get_installed_php_versions()
        if installed_php:
            options.extend([
                ("list", "1. List PHP Versions"),
                ("install", "2. Install PHP Version"),
                ("switch", "3. Switch Default PHP"),
                ("extensions", "4. Install Extensions"),
                ("composer", "5. Install/Update Composer"),
                ("site_php", "6. Set PHP Version for Site"),
                ("info", "7. PHP Info"),
            ])
        else:
            options.append(("install", "1. Install PHP"))
        options.append(("back", "← Back to Main Menu"))
        return options
    
    handlers = {
        "list": list_php_versions,
        "install": install_php_interactive,
        "switch": switch_php_interactive,
        "extensions": install_extensions_interactive,
        "composer": install_composer,
        "site_php": set_site_php_interactive,
        "info": show_php_info_interactive,
    }
    
    run_menu_loop("PHP Runtime Management", get_options, handlers, get_status)


def add_php_ppa():
    """
    Add ondrej/php PPA for multiple PHP versions.
    
    Returns:
        bool: True if successful or already added
    """
    result = run_command(
        "grep -r 'ondrej/php' /etc/apt/sources.list.d/ 2>/dev/null",
        check=False,
        silent=True
    )
    
    if result.returncode == 0:
        show_info("PHP PPA already added.")
        return True
    
    show_info("Adding ondrej/php PPA...")
    
    if not is_installed("software-properties-common"):
        result = run_command_with_progress(
            "apt install -y software-properties-common",
            "Installing software-properties-common..."
        )
        if result.returncode != 0:
            show_error("Failed to install software-properties-common")
            return False
    
    result = run_command_with_progress(
        "add-apt-repository -y ppa:ondrej/php",
        "Adding PHP PPA..."
    )
    
    if result.returncode != 0:
        show_error("Failed to add PHP PPA")
        return False
    
    result = run_command_with_progress(
        "apt update",
        "Updating package lists..."
    )
    
    if result.returncode != 0:
        show_warning("PPA added but failed to update package lists")
        return False
    
    show_success("PHP PPA added successfully!")
    return True


def install_php_interactive():
    """Interactive prompt to install a PHP version."""
    clear_screen()
    show_header()
    show_panel("Install PHP Version", title="PHP Runtime", style="cyan")
    
    console.print("[bold]Available PHP versions:[/bold]")
    console.print()
    for version in PHP_VERSIONS:
        installed = is_installed(f"php{version}-fpm")
        status = "[green]Installed[/green]" if installed else "[dim]Not installed[/dim]"
        console.print(f"  • PHP {version} - {status}")
    console.print()
    
    version = select_from_list(
        title="Install PHP",
        message="Select PHP version to install:",
        options=PHP_VERSIONS
    )
    
    if not version:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
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
        version: PHP version (e.g., "8.4")
        with_extensions: If True, install common extensions
    
    Returns:
        bool: True if successful
    """
    if not add_php_ppa():
        return False
    
    console.print()
    show_info(f"Installing PHP {version}...")
    
    packages = [f"php{version}", f"php{version}-fpm"]
    
    if with_extensions:
        for ext in PHP_EXTENSIONS:
            if ext not in ["cli", "fpm"]:
                packages.append(f"php{version}-{ext}")
    
    packages_str = " ".join(packages)
    returncode = run_command_realtime(
        f"apt install -y {packages_str}",
        f"Installing PHP {version} packages..."
    )
    
    if returncode != 0:
        show_error(f"Failed to install PHP {version}")
        return False
    
    fpm_service = f"php{version}-fpm"
    service_control(fpm_service, "start")
    service_control(fpm_service, "enable")
    
    console.print()
    if is_service_running(fpm_service):
        show_success(f"PHP {version} FPM is running!")
    else:
        show_warning(f"PHP {version} installed but FPM may not be running")
    
    return True


def install_extensions_interactive():
    """Interactive prompt to install PHP extensions."""
    clear_screen()
    show_header()
    show_panel("Install PHP Extensions", title="PHP Runtime", style="cyan")
    
    installed_versions = _get_installed_php_versions()
    
    if not installed_versions:
        show_error("No PHP versions installed. Please install PHP first.")
        press_enter_to_continue()
        return
    
    version = select_from_list(
        title="Select PHP Version",
        message="Install extensions for which PHP version?",
        options=installed_versions
    )
    
    if not version:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
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
        version: PHP version (e.g., "8.4")
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
    
    fpm_service = f"php{version}-fpm"
    if is_service_running(fpm_service):
        service_control(fpm_service, "restart")
    
    return returncode == 0


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
        version: PHP version (e.g., "8.4")
    
    Returns:
        bool: True if successful
    """
    php_bin = f"/usr/bin/php{version}"
    
    if not os.path.exists(php_bin):
        show_error(f"PHP {version} not found at {php_bin}")
        return False
    
    show_info(f"Switching to PHP {version}...")
    
    result = run_command(
        f"update-alternatives --set php {php_bin}",
        check=False,
        silent=True
    )
    
    if result.returncode != 0:
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
        version: PHP version (e.g., "8.4")
    """
    clear_screen()
    show_header()
    show_panel(f"PHP {version} Information", title="PHP Runtime", style="cyan")
    
    php_bin = f"/usr/bin/php{version}"
    result = run_command(f"{php_bin} -v | head -1", check=False, silent=True)
    if result.returncode == 0:
        console.print(f"[bold]Version:[/bold] {result.stdout.strip()}")
    
    result = run_command(f"{php_bin} --ini | grep 'Loaded Configuration'", check=False, silent=True)
    if result.returncode == 0:
        console.print(f"[bold]Config:[/bold] {result.stdout.strip().split(':')[-1].strip()}")
    
    console.print()
    console.print("[bold]Installed Extensions:[/bold]")
    console.print()
    
    result = run_command(f"{php_bin} -m", check=False, silent=True)
    if result.returncode == 0:
        extensions = [ext.strip() for ext in result.stdout.strip().split('\n') if ext.strip() and not ext.startswith('[')]
        
        cols = 4
        for i in range(0, len(extensions), cols):
            row = extensions[i:i+cols]
            console.print("  " + "  ".join(f"[dim]{ext:20}[/dim]" for ext in row))
    
    console.print()
    
    fpm_service = f"php{version}-fpm"
    if is_service_running(fpm_service):
        console.print(f"[bold]FPM Status:[/bold] [green]Running[/green]")
    else:
        console.print(f"[bold]FPM Status:[/bold] [red]Not running[/red]")


def install_composer():
    """Install or update Composer globally."""
    clear_screen()
    show_header()
    show_panel("Install/Update Composer", title="PHP Runtime", style="cyan")
    
    if not _get_installed_php_versions():
        show_error("No PHP versions installed. Please install PHP first.")
        press_enter_to_continue()
        return
    
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
    
    result = run_command_with_progress(
        "curl -sS https://getcomposer.org/installer -o /tmp/composer-setup.php",
        "Downloading Composer..."
    )
    
    if result.returncode != 0:
        show_error("Failed to download Composer installer.")
        press_enter_to_continue()
        return
    
    show_info("Installing Composer globally...")
    
    result = run_command_with_progress(
        "php /tmp/composer-setup.php --install-dir=/usr/local/bin --filename=composer",
        "Installing Composer..."
    )
    
    run_command("rm -f /tmp/composer-setup.php", check=False, silent=True)
    
    if result.returncode != 0:
        show_error("Failed to install Composer.")
        press_enter_to_continue()
        return
    
    result = run_command("composer --version", check=False, silent=True)
    if result.returncode == 0:
        show_success("Composer installed successfully!")
        console.print(f"[dim]{result.stdout.strip()}[/dim]")
    else:
        show_warning("Composer installed but verification failed.")
    
    press_enter_to_continue()


def set_site_php_interactive():
    """Interactive prompt to set PHP version for a specific site."""
    clear_screen()
    show_header()
    show_panel("Set PHP Version for Site", title="PHP Runtime", style="cyan")
    
    installed_php = _get_installed_php_versions()
    if not installed_php:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    from modules.webserver import _get_configured_domains
    domains = _get_configured_domains()
    
    if not domains:
        show_error("No domains configured. Add a domain first.")
        press_enter_to_continue()
        return
    
    domain = select_from_list(
        title="Select Site",
        message="Configure PHP for which site?",
        options=domains
    )
    
    if not domain:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    current_php = _get_site_php_version(domain)
    if current_php:
        console.print(f"[dim]Current PHP for {domain}: {current_php}[/dim]")
    else:
        console.print(f"[dim]PHP not configured for {domain}[/dim]")
    console.print()
    
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
        with open(config_path, "r") as f:
            config = f.read()
        
        php_block = f'''    location ~ \\.php$ {{
        fastcgi_pass unix:/run/php/php{version}-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
        include fastcgi_params;
        fastcgi_hide_header X-Powered-By;
    }}'''
        
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
        
        last_brace = config.rfind('}')
        if last_brace > 0:
            config = config[:last_brace] + "\n" + php_block + "\n" + config[last_brace:]
        
        with open(config_path, "w") as f:
            f.write(config)
        
        result = run_command("nginx -t", check=False, silent=True)
        if result.returncode != 0:
            show_error("Nginx configuration test failed!")
            console.print(f"[dim]{result.stderr}[/dim]")
            return False
        
        return service_control("nginx", "reload")
    
    except Exception as e:
        show_error(f"Error configuring PHP: {e}")
        return False


def _get_site_php_version(domain):
    """Get the PHP version configured for a site."""
    from config import NGINX_SITES_AVAILABLE
    
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    
    try:
        with open(config_path, "r") as f:
            config = f.read()
        
        match = re.search(r'fastcgi_pass\s+unix:/run/php/php(\d+\.\d+)-fpm\.sock', config)
        if match:
            return match.group(1)
        return None
    except Exception:
        return None


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
    
    output = result.stdout.strip()
    if "PHP" in output:
        parts = output.split()
        if len(parts) >= 2:
            version = parts[1]
            return ".".join(version.split(".")[:2])
    return None


# =============================================================================
# Node.js Runtime Functions
# =============================================================================

def show_nodejs_menu():
    """Display the Node.js Runtime submenu."""
    def get_status():
        current_node = _get_current_nodejs_version()
        if current_node:
            return f"Current Node.js: {current_node}"
        return "Node.js: Not installed"
    
    def get_options():
        options = []
        current_node = _get_current_nodejs_version()
        if _is_nvm_installed() or current_node:
            options.extend([
                ("list", "1. List Node.js Versions"),
                ("install", "2. Install Node.js Version"),
                ("switch", "3. Switch Node.js Version"),
                ("info", "4. Node.js Info"),
                ("nvm", "5. Install/Update NVM"),
            ])
        else:
            options.append(("nvm", "1. Install NVM"))
        options.append(("back", "← Back to Main Menu"))
        return options
    
    handlers = {
        "list": list_nodejs_versions,
        "install": install_nodejs_interactive,
        "switch": switch_nodejs_interactive,
        "info": show_nodejs_info,
        "nvm": install_nvm_interactive,
    }
    
    run_menu_loop("Node.js Runtime Management", get_options, handlers, get_status)


def install_nvm_interactive():
    """Interactive prompt to install or update NVM."""
    clear_screen()
    show_header()
    show_panel("Install/Update NVM", title="Node.js Runtime", style="cyan")
    
    if _is_nvm_installed():
        nvm_version = _get_nvm_version()
        console.print(f"[dim]Current NVM: {nvm_version}[/dim]")
        console.print()
        if not confirm_action("NVM is already installed. Reinstall/update?"):
            press_enter_to_continue()
            return
    
    success = install_nvm()
    
    if success:
        show_success("NVM installed successfully!")
        console.print()
        console.print("[dim]Note: You may need to restart your terminal or run:[/dim]")
        console.print("[dim]  source ~/.bashrc[/dim]")
    else:
        show_error("Failed to install NVM.")
    
    press_enter_to_continue()


def install_nvm():
    """
    Install NVM (Node Version Manager) via curl script.
    
    Returns:
        bool: True if successful
    """
    from config import NVM_INSTALL_URL
    
    show_info("Installing NVM...")
    
    result = run_command_with_progress(
        f"curl -o- {NVM_INSTALL_URL} | bash",
        "Downloading and installing NVM..."
    )
    
    if result.returncode != 0:
        show_error("Failed to download/install NVM")
        return False
    
    if _is_nvm_installed():
        show_success("NVM installed!")
        return True
    else:
        show_warning("NVM script ran but installation could not be verified")
        return True


def _is_nvm_installed():
    """Check if NVM is installed."""
    from config import NVM_DIR
    nvm_script = os.path.join(NVM_DIR, "nvm.sh")
    return os.path.exists(nvm_script)


def _get_nvm_version():
    """Get installed NVM version."""
    result = _run_with_nvm("nvm --version")
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None


def _run_with_nvm(command):
    """
    Run a command with NVM sourced.
    
    Args:
        command: Command to run after sourcing NVM
    
    Returns:
        CompletedProcess or None if NVM not installed
    """
    from config import NVM_DIR
    
    nvm_script = os.path.join(NVM_DIR, "nvm.sh")
    if not os.path.exists(nvm_script):
        return None
    
    full_command = f'bash -c "source {nvm_script} && {command}"'
    return run_command(full_command, check=False, silent=True)


def install_nodejs_interactive():
    """Interactive prompt to install a Node.js version."""
    clear_screen()
    show_header()
    show_panel("Install Node.js", title="Node.js Runtime", style="cyan")
    
    if not _is_nvm_installed():
        show_error("NVM is not installed. Please install NVM first.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Common options:[/bold]")
    console.print()
    console.print("  • [cyan]lts[/cyan]     - Latest LTS version (recommended)")
    console.print("  • [cyan]latest[/cyan]  - Latest current version")
    console.print("  • [cyan]20[/cyan]      - Latest Node.js 20.x")
    console.print("  • [cyan]18[/cyan]      - Latest Node.js 18.x")
    console.print("  • [cyan]20.10.0[/cyan] - Specific version")
    console.print()
    
    from ui.menu import text_input
    version = text_input(
        title="Install Node.js",
        message="Enter version to install (e.g., lts, 20, 18.19.0):",
        default="lts"
    )
    
    if not version:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    version = version.strip().lower()
    
    if version == "lts":
        version = "--lts"
    elif version == "latest":
        version = "node"
    
    success = install_nodejs(version)
    
    if success:
        show_success("Node.js installed successfully!")
        node_ver = _get_current_nodejs_version()
        if node_ver:
            console.print(f"[dim]Installed: {node_ver}[/dim]")
    else:
        show_error("Failed to install Node.js")
    
    press_enter_to_continue()


def install_nodejs(version):
    """
    Install a specific Node.js version via NVM.
    
    Args:
        version: Version string (e.g., "20", "18.19.0", "--lts", "node")
    
    Returns:
        bool: True if successful
    """
    if not _is_nvm_installed():
        show_error("NVM is not installed")
        return False
    
    show_info(f"Installing Node.js {version}...")
    
    from config import NVM_DIR
    nvm_script = os.path.join(NVM_DIR, "nvm.sh")
    
    returncode = run_command_realtime(
        f'bash -c "source {nvm_script} && nvm install {version}"',
        f"Installing Node.js {version}..."
    )
    
    return returncode == 0


def switch_nodejs_interactive():
    """Interactive prompt to switch Node.js version."""
    clear_screen()
    show_header()
    show_panel("Switch Node.js Version", title="Node.js Runtime", style="cyan")
    
    if not _is_nvm_installed():
        show_error("NVM is not installed.")
        press_enter_to_continue()
        return
    
    installed = _get_installed_nodejs_versions()
    
    if not installed:
        show_error("No Node.js versions installed.")
        press_enter_to_continue()
        return
    
    if len(installed) < 2:
        show_info("Only one Node.js version installed. Nothing to switch.")
        press_enter_to_continue()
        return
    
    current = _get_current_nodejs_version()
    console.print(f"[dim]Current: {current}[/dim]")
    console.print()
    
    version = select_from_list(
        title="Switch Node.js",
        message="Select Node.js version to use:",
        options=installed
    )
    
    if not version:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    success = switch_nodejs_version(version)
    
    if success:
        show_success(f"Switched to Node.js {version}!")
        
        new_ver = _get_current_nodejs_version()
        if new_ver:
            console.print(f"[dim]Now using: {new_ver}[/dim]")
    else:
        show_error(f"Failed to switch to Node.js {version}")
    
    press_enter_to_continue()


def switch_nodejs_version(version):
    """
    Switch to a specific Node.js version and set as default.
    
    Args:
        version: Version string (e.g., "v20.10.0", "20.10.0")
    
    Returns:
        bool: True if successful
    """
    if not _is_nvm_installed():
        return False
    
    version_clean = version.lstrip('v')
    
    show_info(f"Switching to Node.js {version}...")
    
    result = _run_with_nvm(f"nvm use {version_clean}")
    if result is None or result.returncode != 0:
        return False
    
    result = _run_with_nvm(f"nvm alias default {version_clean}")
    if result is None or result.returncode != 0:
        show_warning("Switched version but failed to set as default")
    
    return True


def list_nodejs_versions():
    """Display a table of installed Node.js versions."""
    clear_screen()
    show_header()
    show_panel("Installed Node.js Versions", title="Node.js Runtime", style="cyan")
    
    if not _is_nvm_installed():
        show_error("NVM is not installed.")
        console.print()
        console.print("[dim]Use 'Install/Update NVM' first.[/dim]")
        press_enter_to_continue()
        return
    
    installed = _get_installed_nodejs_versions()
    
    if not installed:
        show_info("No Node.js versions installed.")
        console.print()
        console.print("[dim]Use 'Install Node.js Version' to install.[/dim]")
        press_enter_to_continue()
        return
    
    current = _get_current_nodejs_version()
    default = _get_default_nodejs_version()
    
    columns = [
        {"name": "Version", "style": "cyan"},
        {"name": "Current", "justify": "center"},
        {"name": "Default", "justify": "center"},
        {"name": "npm Version"},
    ]
    
    rows = []
    for version in installed:
        is_current = "[green]✓[/green]" if version == current else ""
        is_default = "[green]✓[/green]" if version == default else ""
        
        npm_ver = _get_npm_version_for_node(version)
        npm_display = npm_ver if npm_ver else "[dim]N/A[/dim]"
        
        rows.append([version, is_current, is_default, npm_display])
    
    show_table(f"Total: {len(installed)} version(s)", columns, rows)
    
    press_enter_to_continue()


def _get_installed_nodejs_versions():
    """Get list of installed Node.js versions via NVM."""
    result = _run_with_nvm("nvm ls --no-colors")
    if result is None or result.returncode != 0:
        return []
    
    versions = []
    for line in result.stdout.strip().split('\n'):
        line = line.strip()
        line = line.replace('->', '').replace('*', '').strip()
        
        if line.startswith('v') and '.' in line:
            version = line.split()[0] if ' ' in line else line
            version = version.strip()
            if version and version not in versions:
                versions.append(version)
    
    return sorted(versions, key=lambda v: [int(x) for x in v.lstrip('v').split('.')], reverse=True)


def _get_current_nodejs_version():
    """Get the current active Node.js version."""
    result = _run_with_nvm("node --version")
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None


def _get_default_nodejs_version():
    """Get the default Node.js version set in NVM."""
    result = _run_with_nvm("nvm alias default")
    if result and result.returncode == 0:
        output = result.stdout.strip()
        if '->' in output:
            version = output.split('->')[-1].strip()
            version = version.replace('*', '').strip()
            if version.startswith('v'):
                return version
    return None


def _get_npm_version_for_node(node_version):
    """Get npm version for a specific Node.js version."""
    version_clean = node_version.lstrip('v')
    result = _run_with_nvm(f"nvm exec {version_clean} npm --version")
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None


def show_nodejs_info():
    """Display current Node.js and npm information."""
    clear_screen()
    show_header()
    show_panel("Node.js Information", title="Node.js Runtime", style="cyan")
    
    if not _is_nvm_installed():
        show_error("NVM is not installed.")
        press_enter_to_continue()
        return
    
    nvm_version = _get_nvm_version()
    console.print(f"[bold]NVM Version:[/bold] {nvm_version or 'Unknown'}")
    console.print()
    
    node_version = _get_current_nodejs_version()
    if node_version:
        console.print(f"[bold]Node.js Version:[/bold] {node_version}")
        
        npm_version = _run_with_nvm("npm --version")
        if npm_version and npm_version.returncode == 0:
            console.print(f"[bold]npm Version:[/bold] {npm_version.stdout.strip()}")
        
        npx_version = _run_with_nvm("npx --version")
        if npx_version and npx_version.returncode == 0:
            console.print(f"[bold]npx Version:[/bold] {npx_version.stdout.strip()}")
        
        console.print()
        
        node_path = _run_with_nvm("which node")
        if node_path and node_path.returncode == 0:
            console.print(f"[bold]Node Path:[/bold] {node_path.stdout.strip()}")
        
        npm_path = _run_with_nvm("which npm")
        if npm_path and npm_path.returncode == 0:
            console.print(f"[bold]npm Path:[/bold] {npm_path.stdout.strip()}")
        
        console.print()
        
        default = _get_default_nodejs_version()
        if default:
            console.print(f"[bold]Default Version:[/bold] {default}")
        
        console.print()
        
        result = _run_with_nvm("npm config get prefix")
        if result and result.returncode == 0:
            console.print(f"[bold]npm Prefix:[/bold] {result.stdout.strip()}")
        
        result = _run_with_nvm("npm root -g")
        if result and result.returncode == 0:
            console.print(f"[bold]Global Modules:[/bold] {result.stdout.strip()}")
    else:
        show_warning("No Node.js version is currently active.")
        console.print()
        console.print("[dim]Install Node.js first with 'Install Node.js Version'[/dim]")
    
    press_enter_to_continue()
