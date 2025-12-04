"""Reusable UI components for vexo."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from config import APP_NAME, APP_VERSION, APP_TAGLINE, APP_DESCRIPTION
from ui.styles import PRIMARY, SUCCESS, WARNING, ERROR

# Global console instance
console = Console()


def clear_screen():
    """Clear the terminal screen."""
    console.clear()


def show_header():
    """Display the application header/branding with ASCII art."""
    # Cyan gradient colors (light to dark)
    c1 = "#00ffff"  # Bright cyan
    c2 = "#00e5e5"
    c3 = "#00cccc"
    c4 = "#00b3b3"
    c5 = "#009999"
    c6 = "#008080"  # Dark cyan
    
    console.print()
    console.print(f"[{c1}] ██╗   ██╗███████╗██╗  ██╗ ██████╗ [/{c1}]")
    console.print(f"[{c2}] ██║   ██║██╔════╝╚██╗██╔╝██╔═══██╗[/{c2}]")
    console.print(f"[{c3}] ██║   ██║█████╗   ╚███╔╝ ██║   ██║[/{c3}]")
    console.print(f"[{c4}] ╚██╗ ██╔╝██╔══╝   ██╔██╗ ██║   ██║[/{c4}]")
    console.print(f"[{c5}]  ╚████╔╝ ███████╗██╔╝ ██╗╚██████╔╝[/{c5}]")
    console.print(f"[{c6}]   ╚═══╝  ╚══════╝╚═╝  ╚═╝ ╚═════╝ [/{c6}]")
    console.print(f"  [bold cyan]{APP_TAGLINE}[/bold cyan]  [dim]v{APP_VERSION}[/dim]")
    console.print(f"  [dim]{APP_DESCRIPTION}[/dim]")
    console.print()


def show_system_bar():
    """Display system info bar (IP, uptime, RAM, disk, swap)."""
    import socket
    import psutil
    from datetime import datetime
    
    # Hostname & IP
    hostname = socket.gethostname()
    try:
        from utils.shell import get_ip_address
        ip = get_ip_address()
    except Exception:
        ip = "unknown"
    
    # Uptime
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime_delta = datetime.now() - boot_time
    days = uptime_delta.days
    hours = uptime_delta.seconds // 3600
    if days > 0:
        uptime_str = f"{days}d {hours}h"
    else:
        minutes = (uptime_delta.seconds % 3600) // 60
        uptime_str = f"{hours}h {minutes}m"
    
    # RAM
    mem = psutil.virtual_memory()
    ram_used = mem.used / (1024 ** 3)
    ram_total = mem.total / (1024 ** 3)
    ram_pct = mem.percent
    
    # Disk
    disk = psutil.disk_usage('/')
    disk_used = disk.used / (1024 ** 3)
    disk_total = disk.total / (1024 ** 3)
    disk_pct = disk.percent
    
    # Swap
    swap = psutil.swap_memory()
    swap_used = swap.used / (1024 ** 3)
    swap_total = swap.total / (1024 ** 3)
    
    # Line 1: Host & Uptime
    console.print(
        f"[dim]Host:[/dim] [cyan]{hostname}[/cyan] [dim]([/dim][cyan]{ip}[/cyan][dim])[/dim] "
        f"[dim]|[/dim] [dim]Uptime:[/dim] [cyan]{uptime_str}[/cyan]"
    )
    
    # Line 2: RAM, Disk, Swap
    console.print(
        f"[dim]RAM:[/dim] [cyan]{ram_used:.1f}/{ram_total:.1f}GB[/cyan] [dim]({ram_pct:.0f}%)[/dim] "
        f"[dim]|[/dim] [dim]Disk:[/dim] [cyan]{disk_used:.0f}/{disk_total:.0f}GB[/cyan] [dim]({disk_pct:.0f}%)[/dim] "
        f"[dim]|[/dim] [dim]Swap:[/dim] [cyan]{swap_used:.1f}/{swap_total:.1f}GB[/cyan]"
    )
    console.print()


def show_panel(content, title="", style="cyan", padding=(1, 2)):
    """
    Display content in a styled panel.
    
    Args:
        content: Text or Rich renderable to display
        title: Optional panel title
        style: Border style color
        padding: Tuple of (vertical, horizontal) padding
    """
    panel = Panel(
        content,
        title=title if title else None,
        border_style=style,
        padding=padding,
    )
    console.print(panel)


def show_table(title, columns, rows, show_header=True):
    """
    Display data in a formatted table.
    
    Args:
        title: Table title
        columns: List of column definitions, each is dict with 'name' and optional 'style', 'justify'
        rows: List of row data (list of values matching column order)
        show_header: Whether to show column headers
    
    Example:
        columns = [
            {"name": "Domain", "style": "cyan"},
            {"name": "Status", "justify": "center"},
        ]
        rows = [
            ["example.com", "Active"],
            ["test.com", "Inactive"],
        ]
        show_table("Domains", columns, rows)
    """
    table = Table(title=title, show_header=show_header, border_style="dim")
    
    for col in columns:
        table.add_column(
            col.get("name", ""),
            style=col.get("style", None),
            justify=col.get("justify", "left"),
        )
    
    for row in rows:
        table.add_row(*[str(cell) for cell in row])
    
    console.print(table)
    console.print()


def show_success(message):
    """Display a success message."""
    console.print(f"[{SUCCESS}]✓[/{SUCCESS}] {message}")


def show_error(message):
    """Display an error message."""
    console.print(f"[{ERROR}]✗[/{ERROR}] {message}")


def show_warning(message):
    """Display a warning message."""
    console.print(f"[{WARNING}]![/{WARNING}] {message}")


def show_info(message):
    """Display an info message."""
    console.print(f"[{PRIMARY}]→[/{PRIMARY}] {message}")


def show_spinner(message):
    """
    Return a spinner context manager for long operations.
    
    Usage:
        with show_spinner("Installing..."):
            run_command("apt install nginx")
    """
    return console.status(message, spinner="dots")


def press_enter_to_continue():
    """Wait for user to press Enter."""
    console.print()
    console.input("[dim]Press Enter to continue...[/dim]")
