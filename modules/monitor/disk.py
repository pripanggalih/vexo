"""Disk monitoring for vexo-cli."""

import psutil

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_info,
    press_enter_to_continue,
)
from modules.monitor.common import get_status_color, format_bytes


def get_disk_usage(path="/"):
    """
    Get disk usage for a specific path.
    
    Args:
        path: Filesystem path (default: root)
    
    Returns:
        dict: {
            'percent': float (0-100),
            'total': int (bytes),
            'used': int (bytes),
            'free': int (bytes)
        }
    """
    disk = psutil.disk_usage(path)
    return {
        'percent': disk.percent,
        'total': disk.total,
        'used': disk.used,
        'free': disk.free,
    }


def show_disk_details():
    """Display detailed disk information."""
    clear_screen()
    show_header()
    show_panel("Disk Details", title="Monitoring", style="cyan")
    
    partitions = psutil.disk_partitions()
    
    columns = [
        {"name": "Mount", "style": "cyan"},
        {"name": "Device"},
        {"name": "Type"},
        {"name": "Total", "justify": "right"},
        {"name": "Used", "justify": "right"},
        {"name": "Free", "justify": "right"},
        {"name": "Usage", "justify": "right"},
        {"name": "Status", "justify": "center"},
    ]
    
    rows = []
    for partition in partitions:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            color = get_status_color(usage.percent)
            
            rows.append([
                partition.mountpoint,
                partition.device,
                partition.fstype,
                format_bytes(usage.total),
                format_bytes(usage.used),
                format_bytes(usage.free),
                f"{usage.percent:.1f}%",
                f"[{color}]●[/{color}]"
            ])
        except (PermissionError, OSError):
            continue
    
    if rows:
        show_table(f"{len(rows)} partition(s)", columns, rows)
    else:
        show_info("No accessible partitions found.")
    
    console.print()
    try:
        io_counters = psutil.disk_io_counters()
        if io_counters:
            console.print("[bold]Disk I/O (since boot):[/bold]")
            console.print(f"  Read: {format_bytes(io_counters.read_bytes)}")
            console.print(f"  Written: {format_bytes(io_counters.write_bytes)}")
    except Exception:
        pass
    
    press_enter_to_continue()
