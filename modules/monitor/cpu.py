"""CPU monitoring for vexo."""

import psutil

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    press_enter_to_continue,
)
from modules.monitor.common import get_status_color


def get_cpu_usage():
    """
    Get CPU usage percentage.
    
    Returns:
        float: CPU usage percentage (0-100)
    """
    return psutil.cpu_percent(interval=1)


def show_cpu_details():
    """Display detailed CPU information."""
    clear_screen()
    show_header()
    show_panel("CPU Details", title="Monitoring", style="cyan")
    
    cpu_percent = get_cpu_usage()
    cpu_count = psutil.cpu_count(logical=False) or psutil.cpu_count()
    cpu_count_logical = psutil.cpu_count(logical=True)
    
    per_cpu = psutil.cpu_percent(interval=1, percpu=True)
    
    try:
        load_avg = psutil.getloadavg()
        load_1, load_5, load_15 = load_avg
    except (AttributeError, OSError):
        load_1 = load_5 = load_15 = 0
    
    color = get_status_color(cpu_percent)
    
    console.print(f"[bold]Overall Usage:[/bold] [{color}]{cpu_percent:.1f}%[/{color}]")
    console.print()
    console.print(f"[bold]Physical Cores:[/bold] {cpu_count}")
    console.print(f"[bold]Logical Cores:[/bold] {cpu_count_logical}")
    console.print()
    console.print(f"[bold]Load Average:[/bold] {load_1:.2f} (1m) / {load_5:.2f} (5m) / {load_15:.2f} (15m)")
    console.print()
    
    if len(per_cpu) > 1:
        console.print("[bold]Per-CPU Usage:[/bold]")
        columns = [
            {"name": "CPU", "style": "cyan"},
            {"name": "Usage", "justify": "right"},
            {"name": "Status", "justify": "center"},
        ]
        
        rows = []
        for i, usage in enumerate(per_cpu):
            c = get_status_color(usage)
            rows.append([
                f"CPU {i}",
                f"{usage:.1f}%",
                f"[{c}]●[/{c}]"
            ])
        
        show_table(f"{len(per_cpu)} cores", columns, rows)
    
    press_enter_to_continue()
