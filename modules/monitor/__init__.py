"""System monitoring module for vexo-cli."""

from ui.menu import run_menu_loop

from modules.monitor.dashboard import show_dashboard
from modules.monitor.cpu import show_cpu_details
from modules.monitor.memory import show_ram_details
from modules.monitor.disk import show_disk_details
from modules.monitor.network import show_menu as show_network_menu
from modules.monitor.process import show_menu as show_process_menu
from modules.monitor.service import show_menu as show_service_menu
from modules.monitor.alert import show_menu as show_alert_menu
from modules.monitor.history import show_menu as show_history_menu


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
        "process": show_process_menu,
        "service": show_service_menu,
        "alert": show_alert_menu,
        "history": show_history_menu,
    }
    
    run_menu_loop("System Monitoring", options, handlers)
