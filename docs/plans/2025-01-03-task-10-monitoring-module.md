# Task 10.0: Monitoring Module Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create system monitoring module displaying CPU, RAM, and Disk usage with color-coded status indicators.

**Architecture:** Single `modules/monitor.py` using psutil library for metrics collection. Display metrics in Rich table with color-coded status (green < 70%, yellow 70-85%, red > 85%). Thresholds defined in config.py.

**Tech Stack:** psutil (already in requirements.txt), Rich tables, existing UI components

---

## Sub-tasks Overview

| Sub-task | Description | Commit |
|----------|-------------|--------|
| 10.1 | Create monitor.py with show_menu() | Yes |
| 10.2 | Add get_cpu_usage() | Yes |
| 10.3 | Add get_ram_usage() | Yes |
| 10.4 | Add get_disk_usage() | Yes |
| 10.5 | Add get_status_color() | Yes |
| 10.6 | Add show_status() with Rich table | Yes |
| 10.7 | Update modules/__init__.py and task list | Yes |

**Total: 7 sub-tasks, 7 commits**

---

## Task 10.1: Create monitor.py with show_menu()

**Files:**
- Create: `modules/monitor.py`

**Step 1: Create monitoring module with menu**

```python
"""System monitoring module for vexo."""

import psutil

from config import THRESHOLDS
from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_success,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import show_submenu, confirm_action


def show_menu():
    """
    Display the System Monitoring submenu and handle user selection.
    """
    while True:
        clear_screen()
        show_header()
        
        choice = show_submenu(
            title="System Monitoring",
            options=[
                ("status", "1. Show System Status"),
                ("cpu", "2. CPU Details"),
                ("ram", "3. Memory Details"),
                ("disk", "4. Disk Details"),
                ("back", "← Back to Main Menu"),
            ],
        )
        
        if choice == "status":
            show_status()
        elif choice == "cpu":
            show_cpu_details()
        elif choice == "ram":
            show_ram_details()
        elif choice == "disk":
            show_disk_details()
        elif choice == "back" or choice is None:
            break
```

**Step 2: Commit**

```bash
git add modules/monitor.py
git commit -m "feat(monitor): add monitor.py with menu structure"
```

---

## Task 10.2: Add get_cpu_usage()

**Files:**
- Modify: `modules/monitor.py`

**Step 1: Add CPU usage function**

Append to `modules/monitor.py`:

```python
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
    
    # Get CPU info
    cpu_percent = get_cpu_usage()
    cpu_count = psutil.cpu_count()
    cpu_count_logical = psutil.cpu_count(logical=True)
    
    # Get per-CPU usage
    per_cpu = psutil.cpu_percent(interval=1, percpu=True)
    
    # Get load average (Linux only)
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
    
    # Per-CPU table
    if len(per_cpu) > 1:
        console.print("[bold]Per-CPU Usage:[/bold]")
        columns = [
            {"name": "CPU", "style": "cyan"},
            {"name": "Usage", "justify": "right"},
            {"name": "Status", "justify": "center"},
        ]
        
        rows = []
        for i, usage in enumerate(per_cpu):
            color = get_status_color(usage)
            rows.append([
                f"CPU {i}",
                f"{usage:.1f}%",
                f"[{color}]●[/{color}]"
            ])
        
        show_table(f"{len(per_cpu)} cores", columns, rows)
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/monitor.py
git commit -m "feat(monitor): add get_cpu_usage() and show_cpu_details()"
```

---

## Task 10.3: Add get_ram_usage()

**Files:**
- Modify: `modules/monitor.py`

**Step 1: Add RAM usage function**

Append to `modules/monitor.py`:

```python
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


def _format_bytes(bytes_value):
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024
    return f"{bytes_value:.1f} PB"


def show_ram_details():
    """Display detailed RAM information."""
    clear_screen()
    show_header()
    show_panel("Memory Details", title="Monitoring", style="cyan")
    
    ram = get_ram_usage()
    color = get_status_color(ram['percent'])
    
    console.print(f"[bold]Usage:[/bold] [{color}]{ram['percent']:.1f}%[/{color}]")
    console.print()
    console.print(f"[bold]Total:[/bold] {_format_bytes(ram['total'])}")
    console.print(f"[bold]Used:[/bold] {_format_bytes(ram['used'])}")
    console.print(f"[bold]Available:[/bold] {_format_bytes(ram['available'])}")
    console.print()
    
    # Swap info
    swap = psutil.swap_memory()
    if swap.total > 0:
        swap_color = get_status_color(swap.percent)
        console.print("[bold]Swap:[/bold]")
        console.print(f"  Usage: [{swap_color}]{swap.percent:.1f}%[/{swap_color}]")
        console.print(f"  Total: {_format_bytes(swap.total)}")
        console.print(f"  Used: {_format_bytes(swap.used)}")
        console.print(f"  Free: {_format_bytes(swap.free)}")
    else:
        console.print("[dim]Swap: Not configured[/dim]")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/monitor.py
git commit -m "feat(monitor): add get_ram_usage() and show_ram_details()"
```

---

## Task 10.4: Add get_disk_usage()

**Files:**
- Modify: `modules/monitor.py`

**Step 1: Add disk usage function**

Append to `modules/monitor.py`:

```python
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
    
    # Get all partitions
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
                _format_bytes(usage.total),
                _format_bytes(usage.used),
                _format_bytes(usage.free),
                f"{usage.percent:.1f}%",
                f"[{color}]●[/{color}]"
            ])
        except (PermissionError, OSError):
            # Skip inaccessible partitions
            continue
    
    if rows:
        show_table(f"{len(rows)} partition(s)", columns, rows)
    else:
        show_info("No accessible partitions found.")
    
    # Disk I/O stats
    console.print()
    try:
        io_counters = psutil.disk_io_counters()
        if io_counters:
            console.print("[bold]Disk I/O (since boot):[/bold]")
            console.print(f"  Read: {_format_bytes(io_counters.read_bytes)}")
            console.print(f"  Written: {_format_bytes(io_counters.write_bytes)}")
    except Exception:
        pass
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/monitor.py
git commit -m "feat(monitor): add get_disk_usage() and show_disk_details()"
```

---

## Task 10.5: Add get_status_color()

**Files:**
- Modify: `modules/monitor.py`

**Step 1: Add status color function**

Add after imports (before show_menu):

```python
def get_status_color(percentage):
    """
    Get color based on usage percentage and thresholds.
    
    Args:
        percentage: Usage percentage (0-100)
    
    Returns:
        str: Color name ('green', 'yellow', or 'red')
    """
    if percentage < THRESHOLDS['good']:
        return 'green'
    elif percentage < THRESHOLDS['warning']:
        return 'yellow'
    else:
        return 'red'
```

**Step 2: Commit**

```bash
git add modules/monitor.py
git commit -m "feat(monitor): add get_status_color() with threshold-based coloring"
```

---

## Task 10.6: Add show_status() with Rich table

**Files:**
- Modify: `modules/monitor.py`

**Step 1: Add main status display function**

Append to `modules/monitor.py`:

```python
def show_status():
    """Display system status overview with all metrics."""
    clear_screen()
    show_header()
    show_panel("System Status", title="Monitoring", style="cyan")
    
    # Gather metrics
    cpu_percent = get_cpu_usage()
    ram = get_ram_usage()
    disk = get_disk_usage("/")
    
    # Main status table
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
            f"{_format_bytes(ram['used'])} / {_format_bytes(ram['total'])}",
            f"[{ram_color}]●[/{ram_color}]"
        ],
        [
            "Disk (/)",
            f"[{disk_color}]{disk['percent']:.1f}%[/{disk_color}]",
            f"{_format_bytes(disk['used'])} / {_format_bytes(disk['total'])}",
            f"[{disk_color}]●[/{disk_color}]"
        ],
    ]
    
    show_table("System Resources", columns, rows)
    
    # Legend
    console.print()
    console.print("[dim]Status: [green]● Good (<70%)[/green] | [yellow]● Warning (70-85%)[/yellow] | [red]● Critical (>85%)[/red][/dim]")
    
    # Uptime
    console.print()
    try:
        boot_time = psutil.boot_time()
        import datetime
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
```

**Step 2: Commit**

```bash
git add modules/monitor.py
git commit -m "feat(monitor): add show_status() with overview table and legend"
```

---

## Task 10.7: Update modules/__init__.py and task list

**Files:**
- Modify: `modules/__init__.py`
- Modify: `tasks/tasks-vexo.md`

**Step 1: Update modules/__init__.py**

Add monitor import:

```python
"""Business logic modules for vexo - system, webserver, runtime, database, email."""

from modules import system
from modules import webserver
from modules import runtime
from modules import database
from modules import email
from modules import monitor
```

**Step 2: Update task list**

Mark all Task 10.x items as `[x]` complete.

**Step 3: Commit**

```bash
git add modules/__init__.py tasks/tasks-vexo.md
git commit -m "docs: mark Task 10.0 Monitoring Module as complete"
```

---

## Summary

After completion, `modules/monitor.py` will have:

**Menu Function:**
- `show_menu()` - Monitoring submenu (4 options + back)

**Metric Functions:**
- `get_cpu_usage()` - CPU percentage via psutil
- `get_ram_usage()` - RAM dict (percent, total, used, available)
- `get_disk_usage()` - Disk dict (percent, total, used, free)

**Display Functions:**
- `show_status()` - Overview table with all metrics
- `show_cpu_details()` - Per-core usage, load average
- `show_ram_details()` - Memory + swap details
- `show_disk_details()` - All partitions table + I/O stats

**Helper Functions:**
- `get_status_color()` - Threshold-based color (green/yellow/red)
- `_format_bytes()` - Human-readable byte formatting

**Thresholds (from config.py):**
- Green: < 70%
- Yellow: 70-85%
- Red: > 85%
