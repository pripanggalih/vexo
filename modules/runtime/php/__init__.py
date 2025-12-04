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
