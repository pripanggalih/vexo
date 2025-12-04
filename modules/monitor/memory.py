"""Memory monitoring for vexo."""

import psutil

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    press_enter_to_continue,
)
from modules.monitor.common import get_status_color, format_bytes


def get_ram_usage():
    """
    Get RAM usage information.
    
    Returns:
        dict: {
            'percent': float (0-100),
            'total': int (bytes),
            'used': int (bytes),
            'available': int (bytes)
        }
    """
    mem = psutil.virtual_memory()
    return {
        'percent': mem.percent,
        'total': mem.total,
        'used': mem.used,
        'available': mem.available,
    }


def show_ram_details():
    """Display detailed RAM information."""
    clear_screen()
    show_header()
    show_panel("Memory Details", title="Monitoring", style="cyan")
    
    ram = get_ram_usage()
    color = get_status_color(ram['percent'])
    
    console.print(f"[bold]Usage:[/bold] [{color}]{ram['percent']:.1f}%[/{color}]")
    console.print()
    console.print(f"[bold]Total:[/bold] {format_bytes(ram['total'])}")
    console.print(f"[bold]Used:[/bold] {format_bytes(ram['used'])}")
    console.print(f"[bold]Available:[/bold] {format_bytes(ram['available'])}")
    console.print()
    
    swap = psutil.swap_memory()
    if swap.total > 0:
        swap_color = get_status_color(swap.percent)
        console.print("[bold]Swap:[/bold]")
        console.print(f"  Usage: [{swap_color}]{swap.percent:.1f}%[/{swap_color}]")
        console.print(f"  Total: {format_bytes(swap.total)}")
        console.print(f"  Used: {format_bytes(swap.used)}")
        console.print(f"  Free: {format_bytes(swap.free)}")
    else:
        console.print("[dim]Swap: Not configured[/dim]")
    
    press_enter_to_continue()
