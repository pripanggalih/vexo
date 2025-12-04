# Phase 1: Refactor Monitor Module

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor monolithic `modules/monitor.py` into organized `modules/monitor/` folder structure.

**Architecture:** Split existing monitor.py into separate files by concern (dashboard, cpu, memory, disk) while maintaining all existing functionality. Add new menu structure to support future features.

**Tech Stack:** Python, psutil (existing), Rich (existing)

---

## Task 1: Create Monitor Package Structure

**Files:**
- Create: `modules/monitor/__init__.py`
- Create: `modules/monitor/common.py`

**Step 1: Create monitor directory**

```bash
mkdir -p modules/monitor
```

**Step 2: Create common.py with shared utilities**

```python
"""Common utilities for monitor module."""

from config import THRESHOLDS


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


def format_bytes(bytes_value):
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024
    return f"{bytes_value:.1f} PB"
```

**Step 3: Commit**

```bash
git add modules/monitor/
git commit -m "feat(monitor): create monitor package with common utilities"
```

---

## Task 2: Create CPU Module

**Files:**
- Create: `modules/monitor/cpu.py`

**Step 1: Create cpu.py**

```python
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
```

**Step 2: Commit**

```bash
git add modules/monitor/cpu.py
git commit -m "feat(monitor): add CPU monitoring module"
```

---

## Task 3: Create Memory Module

**Files:**
- Create: `modules/monitor/memory.py`

**Step 1: Create memory.py**

```python
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
```

**Step 2: Commit**

```bash
git add modules/monitor/memory.py
git commit -m "feat(monitor): add memory monitoring module"
```

---

## Task 4: Create Disk Module

**Files:**
- Create: `modules/monitor/disk.py`

**Step 1: Create disk.py**

```python
"""Disk monitoring for vexo."""

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
```

**Step 2: Commit**

```bash
git add modules/monitor/disk.py
git commit -m "feat(monitor): add disk monitoring module"
```

---

## Task 5: Create Dashboard Module

**Files:**
- Create: `modules/monitor/dashboard.py`

**Step 1: Create dashboard.py**

```python
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
```

**Step 2: Commit**

```bash
git add modules/monitor/dashboard.py
git commit -m "feat(monitor): add system dashboard module"
```

---

## Task 6: Create Package Init with Menu

**Files:**
- Modify: `modules/monitor/__init__.py`

**Step 1: Create __init__.py with menu**

```python
"""System monitoring module for vexo."""

from ui.menu import run_menu_loop

from modules.monitor.dashboard import show_dashboard
from modules.monitor.cpu import show_cpu_details
from modules.monitor.memory import show_ram_details
from modules.monitor.disk import show_disk_details


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
        # Phase 2-6 handlers will be added later
        "network": _coming_soon,
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
```

**Step 2: Commit**

```bash
git add modules/monitor/__init__.py
git commit -m "feat(monitor): add monitor package init with menu structure"
```

---

## Task 7: Delete Old Monitor File

**Files:**
- Delete: `modules/monitor.py`

**Step 1: Remove old monitor.py**

```bash
rm modules/monitor.py
```

**Step 2: Commit**

```bash
git add modules/monitor.py
git commit -m "refactor(monitor): remove old monolithic monitor.py"
```

---

## Task 8: Verify Import Works

**Files:**
- Check: `main.py` (no changes needed if import path unchanged)

**Step 1: Verify main.py imports**

Main.py should already import from `modules.monitor` which will now resolve to `modules/monitor/__init__.py`. No changes needed.

**Step 2: Final commit**

```bash
git add -A
git commit -m "refactor(monitor): complete migration to monitor package"
```

---

## Summary

After Phase 1, the structure will be:

```
modules/
├── monitor/
│   ├── __init__.py      # Menu and exports
│   ├── common.py        # Shared utilities
│   ├── cpu.py           # CPU monitoring
│   ├── memory.py        # Memory monitoring
│   ├── disk.py          # Disk monitoring
│   └── dashboard.py     # System overview
```

All existing functionality preserved, ready for Phase 2-6 additions.
