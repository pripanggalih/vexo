"""PHP installation and version management."""

import os
import re

from config import PHP_FPM_PATH
from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, select_from_list, run_menu_loop
from utils.shell import (
from utils.error_handler import handle_error
    run_command, run_command_with_progress, run_command_realtime,
    is_installed, is_service_running, service_control, require_root,
)
from modules.runtime.php.utils import (
    PHP_VERSIONS, PHP_EXTENSIONS,
    get_installed_php_versions, get_default_php_version, get_fpm_service_name,
)


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
            handle_error("E3001", "Failed to install software-properties-common")
            return False
    
    result = run_command_with_progress(
        "add-apt-repository -y ppa:ondrej/php",
        "Adding PHP PPA..."
    )
    
    if result.returncode != 0:
        handle_error("E3001", "Failed to add PHP PPA")
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
        handle_error("E3001", f"Failed to install PHP {version}")
    
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
        handle_error("E3001", f"Failed to install PHP {version}")
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


def switch_php_interactive():
    """Interactive prompt to switch default PHP version."""
    clear_screen()
    show_header()
    show_panel("Switch Default PHP Version", title="PHP Runtime", style="cyan")
    
    installed_versions = get_installed_php_versions()
    
    if not installed_versions:
        handle_error("E3001", "No PHP versions installed.")
        press_enter_to_continue()
        return
    
    if len(installed_versions) < 2:
        show_info("Only one PHP version installed. Nothing to switch.")
        press_enter_to_continue()
        return
    
    current = get_default_php_version()
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
        handle_error("E3001", f"Failed to switch to PHP {version}")
    
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
        handle_error("E3001", f"PHP {version} not found at {php_bin}")
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
    
    installed = get_installed_php_versions()
    
    if not installed:
        show_info("No PHP versions installed.")
        console.print()
        console.print("[dim]Use 'Install PHP Version' to install PHP.[/dim]")
        press_enter_to_continue()
        return
    
    default_version = get_default_php_version()
    
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
    
    installed = get_installed_php_versions()
    
    if not installed:
        handle_error("E3001", "No PHP versions installed.")
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
    
    if not get_installed_php_versions():
        handle_error("E3001", "No PHP versions installed. Please install PHP first.")
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
        handle_error("E3001", "Failed to download Composer installer.")
        press_enter_to_continue()
        return
    
    show_info("Installing Composer globally...")
    
    result = run_command_with_progress(
        "php /tmp/composer-setup.php --install-dir=/usr/local/bin --filename=composer",
        "Installing Composer..."
    )
    
    run_command("rm -f /tmp/composer-setup.php", check=False, silent=True)
    
    if result.returncode != 0:
        handle_error("E3001", "Failed to install Composer.")
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
    
    installed_php = get_installed_php_versions()
    if not installed_php:
        handle_error("E3001", "No PHP versions installed.")
        press_enter_to_continue()
        return
    
    from modules.webserver.utils import get_configured_domains
    domains = get_configured_domains()
    
    if not domains:
        handle_error("E3001", "No domains configured. Add a domain first.")
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
        handle_error("E3001", f"Failed to configure PHP for {domain}")
    
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
        handle_error("E3001", f"Config not found: {config_path}")
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
            handle_error("E3001", "Nginx configuration test failed!")
            console.print(f"[dim]{result.stderr}[/dim]")
            return False
        
        return service_control("nginx", "reload")
    
    except Exception as e:
        handle_error("E3001", f"Error configuring PHP: {e}")
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
