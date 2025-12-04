"""System dashboard for vexo."""

import datetime
import psutil

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    press_enter_to_continue,
)
from modules.monitor.common import get_status_color, format_bytes
from modules.monitor.cpu import get_cpu_usage
from modules.monitor.memory import get_ram_usage
from modules.monitor.disk import get_disk_usage


def show_dashboard():
    """Display system status overview with all metrics."""
    clear_screen()
    show_header()
    show_panel("System Dashboard", title="Monitoring", style="cyan")
    
    cpu_percent = get_cpu_usage()
    ram = get_ram_usage()
    disk = get_disk_usage("/")
    
    columns = [
        {"name": "Resource", "style": "cyan"},
        {"name": "Usage", "justify": "right"},
        {"name": "Details", "justify": "right"},
        {"name": "Status", "justify": "center"},
    ]
    
    cpu_color = get_status_color(cpu_percent)
    ram_color = get_status_color(ram['percent'])
    disk_color = get_status_color(disk['percent'])
    
    rows = [
        [
            "CPU",
            f"[{cpu_color}]{cpu_percent:.1f}%[/{cpu_color}]",
            f"{psutil.cpu_count()} cores",
            f"[{cpu_color}]●[/{cpu_color}]"
        ],
        [
            "Memory",
            f"[{ram_color}]{ram['percent']:.1f}%[/{ram_color}]",
            f"{format_bytes(ram['used'])} / {format_bytes(ram['total'])}",
            f"[{ram_color}]●[/{ram_color}]"
        ],
        [
            "Disk (/)",
            f"[{disk_color}]{disk['percent']:.1f}%[/{disk_color}]",
            f"{format_bytes(disk['used'])} / {format_bytes(disk['total'])}",
            f"[{disk_color}]●[/{disk_color}]"
        ],
    ]
    
    show_table("System Resources", columns, rows)
    
    console.print()
    console.print("[dim]Status: [green]● Good (<70%)[/green] | [yellow]● Warning (70-85%)[/yellow] | [red]● Critical (>85%)[/red][/dim]")
    
    console.print()
    try:
        boot_time = psutil.boot_time()
        uptime_seconds = datetime.datetime.now().timestamp() - boot_time
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        uptime_str = ""
        if days > 0:
            uptime_str += f"{days}d "
        uptime_str += f"{hours}h {minutes}m"
        
        console.print(f"[bold]Uptime:[/bold] {uptime_str}")
    except Exception:
        pass
    
    press_enter_to_continue()
