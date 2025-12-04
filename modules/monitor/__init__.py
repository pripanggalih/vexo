"""System monitoring module for vexo-cli."""

from ui.menu import run_menu_loop

from modules.monitor.dashboard import show_dashboard
from modules.monitor.cpu import show_cpu_details
from modules.monitor.memory import show_ram_details
from modules.monitor.disk import show_disk_details
from modules.monitor.network import show_menu as show_network_menu


def show_menu():
    """Display the System Monitoring submenu."""
    options = [
        ("dashboard", "1. Dashboard"),
        ("cpu", "2. CPU Details"),
        ("memory", "3. Memory Details"),
        ("disk", "4. Disk Details"),
        ("network", "5. Network Monitor"),
        ("process", "6. Process Manager"),
        ("service", "7. Service Status"),
        ("alert", "8. Alert Settings"),
        ("history", "9. History & Logs"),
        ("back", "← Back to Main Menu"),
    ]
    
    handlers = {
        "dashboard": show_dashboard,
        "cpu": show_cpu_details,
        "memory": show_ram_details,
        "disk": show_disk_details,
        "network": show_network_menu,
        # Phase 3-6 handlers will be added later
        "process": _coming_soon,
        "service": _coming_soon,
        "alert": _coming_soon,
        "history": _coming_soon,
    }
    
    run_menu_loop("System Monitoring", options, handlers)


def _coming_soon():
    """Placeholder for features under development."""
    from ui.components import (
        clear_screen,
        show_header,
        show_panel,
        show_info,
        press_enter_to_continue,
    )
    clear_screen()
    show_header()
    show_panel("Coming Soon", title="Monitoring", style="cyan")
    show_info("This feature is under development.")
    press_enter_to_continue()
