"""Node.js Runtime management module."""

from ui.menu import run_menu_loop
from modules.runtime.nodejs.utils import (
    is_nvm_installed, get_current_nodejs_version, is_pm2_installed,
)


def show_menu():
    """Display the Node.js Runtime submenu."""
    def get_status():
        current_node = get_current_nodejs_version()
        if current_node:
            return f"Node.js: {current_node}"
        return "Node.js: Not installed"
    
    def get_options():
        options = []
        if is_nvm_installed() or get_current_nodejs_version():
            options.extend([
                ("list", "1. List Node.js Versions"),
                ("install", "2. Install Node.js Version"),
                ("switch", "3. Switch Node.js Version"),
                ("pm2", "4. PM2 Process Manager"),
                ("packages", "5. Global Packages"),
                ("deploy", "6. App Deployment"),
                ("monitor", "7. Monitoring"),
                ("projects", "8. Project Management"),
                ("info", "9. Node.js Info"),
                ("nvm", "10. Install/Update NVM"),
            ])
        else:
            options.append(("nvm", "1. Install NVM"))
        options.append(("back", "← Back to Main Menu"))
        return options
    
    def get_handlers():
        from modules.runtime.nodejs.install import (
            list_nodejs_versions, install_nodejs_interactive,
            switch_nodejs_interactive, show_nodejs_info, install_nvm_interactive,
        )
        from modules.runtime.nodejs.pm2 import show_pm2_menu
        from modules.runtime.nodejs.packages import show_packages_menu
        from modules.runtime.nodejs.deploy import show_deploy_menu
        from modules.runtime.nodejs.monitor import show_monitor_menu
        from modules.runtime.nodejs.projects import show_projects_menu
        
        return {
            "list": list_nodejs_versions,
            "install": install_nodejs_interactive,
            "switch": switch_nodejs_interactive,
            "pm2": show_pm2_menu,
            "packages": show_packages_menu,
            "deploy": show_deploy_menu,
            "monitor": show_monitor_menu,
            "projects": show_projects_menu,
            "info": show_nodejs_info,
            "nvm": install_nvm_interactive,
        }
    
    run_menu_loop("Node.js Runtime Management", get_options, get_handlers(), get_status)
