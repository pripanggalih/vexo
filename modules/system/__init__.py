"""System Setup module for vexo-cli."""

from ui.menu import run_menu_loop

# Import handlers from submodules
from modules.system.info import show_system_info, update_system, install_basic_tools
from modules.system.hostname import show_hostname_menu
from modules.system.users import show_users_menu
from modules.system.swap import show_swap_menu
from modules.system.security import show_security_menu
from modules.system.cleanup import system_cleanup
from modules.system.power import show_power_menu


def show_menu():
    """Display the System Setup submenu."""
    options = [
        ("info", "1. Show System Info"),
        ("update", "2. Update & Upgrade System"),
        ("tools", "3. Install Basic Tools"),
        ("hostname", "4. Hostname & Timezone"),
        ("users", "5. User Management"),
        ("swap", "6. Swap Management"),
        ("security", "7. Security Hardening"),
        ("cleanup", "8. System Cleanup"),
        ("power", "9. Reboot / Shutdown"),
        ("back", "← Back to Main Menu"),
    ]
    
    handlers = {
        "info": show_system_info,
        "update": update_system,
        "tools": install_basic_tools,
        "hostname": show_hostname_menu,
        "users": show_users_menu,
        "swap": show_swap_menu,
        "security": show_security_menu,
        "cleanup": system_cleanup,
        "power": show_power_menu,
    }
    
    run_menu_loop("System Setup & Update", options, handlers)
