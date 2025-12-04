# Phase 2: Network Monitor

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add comprehensive network monitoring with interface stats, active connections, listening ports, and traffic by process.

**Architecture:** Create network.py module with four main views: interface statistics, active connections list, listening ports, and bandwidth by process. Use psutil for network data and socket for connection details.

**Tech Stack:** Python, psutil (existing), socket (stdlib)

**Prerequisite:** Complete Phase 1 (monitor package structure)

---

## Task 1: Create Network Module Base

**Files:**
- Create: `modules/monitor/network.py`

**Step 1: Create network.py with interface stats**

```python
"""Network monitoring for vexo-cli."""

import psutil
import socket
from collections import defaultdict

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_info,
    press_enter_to_continue,
)
from ui.menu import run_menu_loop
from modules.monitor.common import format_bytes


def show_menu():
    """Display the Network Monitor submenu."""
    options = [
        ("interfaces", "1. Interface Statistics"),
        ("connections", "2. Active Connections"),
        ("ports", "3. Listening Ports"),
        ("traffic", "4. Traffic by Process"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "interfaces": show_interface_stats,
        "connections": show_active_connections,
        "ports": show_listening_ports,
        "traffic": show_traffic_by_process,
    }
    
    run_menu_loop("Network Monitor", options, handlers)


def get_interface_stats():
    """
    Get network interface statistics.
    
    Returns:
        list: List of dicts with interface info
    """
    stats = []
    
    net_if_addrs = psutil.net_if_addrs()
    net_if_stats = psutil.net_if_stats()
    net_io = psutil.net_io_counters(pernic=True)
    
    for iface, addrs in net_if_addrs.items():
        info = {
            "name": iface,
            "ip": "-",
            "status": "DOWN",
            "rx_bytes": 0,
            "tx_bytes": 0,
            "rx_packets": 0,
            "tx_packets": 0,
        }
        
        for addr in addrs:
            if addr.family == socket.AF_INET:
                info["ip"] = addr.address
                break
        
        if iface in net_if_stats:
            info["status"] = "UP" if net_if_stats[iface].isup else "DOWN"
        
        if iface in net_io:
            io = net_io[iface]
            info["rx_bytes"] = io.bytes_recv
            info["tx_bytes"] = io.bytes_sent
            info["rx_packets"] = io.packets_recv
            info["tx_packets"] = io.packets_sent
        
        stats.append(info)
    
    return stats


def show_interface_stats():
    """Display network interface statistics."""
    clear_screen()
    show_header()
    show_panel("Network Interfaces", title="Network Monitor", style="cyan")
    
    interfaces = get_interface_stats()
    
    columns = [
        {"name": "Interface", "style": "cyan"},
        {"name": "Status", "justify": "center"},
        {"name": "IP Address"},
        {"name": "RX", "justify": "right"},
        {"name": "TX", "justify": "right"},
        {"name": "Packets", "justify": "right"},
    ]
    
    rows = []
    for iface in interfaces:
        status_color = "green" if iface["status"] == "UP" else "red"
        rows.append([
            iface["name"],
            f"[{status_color}]● {iface['status']}[/{status_color}]",
            iface["ip"],
            format_bytes(iface["rx_bytes"]),
            format_bytes(iface["tx_bytes"]),
            f"↓{iface['rx_packets']:,} ↑{iface['tx_packets']:,}",
        ])
    
    show_table(f"{len(interfaces)} interface(s)", columns, rows)
    
    # Show current bandwidth
    console.print()
    console.print("[bold]Current Bandwidth:[/bold]")
    console.print("[dim]Measuring... (1 second)[/dim]")
    
    io_before = psutil.net_io_counters()
    import time
    time.sleep(1)
    io_after = psutil.net_io_counters()
    
    rx_speed = io_after.bytes_recv - io_before.bytes_recv
    tx_speed = io_after.bytes_sent - io_before.bytes_sent
    
    console.print(f"  Download: [cyan]{format_bytes(rx_speed)}/s[/cyan]")
    console.print(f"  Upload: [cyan]{format_bytes(tx_speed)}/s[/cyan]")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/monitor/network.py
git commit -m "feat(monitor): add network interface statistics"
```

---

## Task 2: Add Active Connections View

**Files:**
- Modify: `modules/monitor/network.py`

**Step 1: Add connection functions to network.py**

Add after `show_interface_stats()`:

```python
def get_active_connections(kind="all"):
    """
    Get active network connections.
    
    Args:
        kind: Connection type filter ('all', 'tcp', 'udp', 'established', 'listen')
    
    Returns:
        list: List of connection dicts
    """
    connections = []
    
    try:
        if kind == "all":
            conns = psutil.net_connections(kind="inet")
        elif kind == "tcp":
            conns = psutil.net_connections(kind="tcp")
        elif kind == "udp":
            conns = psutil.net_connections(kind="udp")
        elif kind == "established":
            conns = [c for c in psutil.net_connections(kind="inet") 
                     if c.status == "ESTABLISHED"]
        elif kind == "listen":
            conns = [c for c in psutil.net_connections(kind="inet") 
                     if c.status == "LISTEN"]
        else:
            conns = psutil.net_connections(kind="inet")
    except psutil.AccessDenied:
        return []
    
    for conn in conns:
        local = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "-"
        remote = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "-"
        
        proto = "tcp" if conn.type == socket.SOCK_STREAM else "udp"
        
        pid = conn.pid or "-"
        try:
            proc_name = psutil.Process(conn.pid).name() if conn.pid else "-"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            proc_name = "-"
        
        connections.append({
            "proto": proto,
            "local": local,
            "remote": remote,
            "status": conn.status if hasattr(conn, 'status') else "-",
            "pid": pid,
            "process": proc_name,
        })
    
    return connections


def show_active_connections():
    """Display active network connections with filter."""
    clear_screen()
    show_header()
    show_panel("Active Connections", title="Network Monitor", style="cyan")
    
    # Get all connections
    connections = get_active_connections("all")
    
    if not connections:
        show_info("No connections found or access denied. Try running as root.")
        press_enter_to_continue()
        return
    
    # Count by status
    status_count = defaultdict(int)
    for conn in connections:
        status_count[conn["status"]] += 1
    
    console.print(f"[bold]Total:[/bold] {len(connections)} connections")
    status_str = " | ".join([f"{status}: {count}" for status, count in sorted(status_count.items())])
    console.print(f"[dim]{status_str}[/dim]")
    console.print()
    
    columns = [
        {"name": "Proto", "style": "cyan"},
        {"name": "Local Address"},
        {"name": "Remote Address"},
        {"name": "Status"},
        {"name": "PID", "justify": "right"},
        {"name": "Process"},
    ]
    
    # Show first 30 connections
    rows = []
    for conn in connections[:30]:
        status_color = "green" if conn["status"] == "ESTABLISHED" else \
                       "yellow" if conn["status"] == "LISTEN" else "dim"
        rows.append([
            conn["proto"],
            conn["local"],
            conn["remote"],
            f"[{status_color}]{conn['status']}[/{status_color}]",
            str(conn["pid"]),
            conn["process"][:15],
        ])
    
    show_table(f"Showing {len(rows)} of {len(connections)}", columns, rows)
    
    if len(connections) > 30:
        console.print(f"[dim]... and {len(connections) - 30} more connections[/dim]")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/monitor/network.py
git commit -m "feat(monitor): add active connections view"
```

---

## Task 3: Add Listening Ports View

**Files:**
- Modify: `modules/monitor/network.py`

**Step 1: Add listening ports function**

Add after `show_active_connections()`:

```python
def show_listening_ports():
    """Display all listening ports."""
    clear_screen()
    show_header()
    show_panel("Listening Ports", title="Network Monitor", style="cyan")
    
    connections = get_active_connections("listen")
    
    if not connections:
        show_info("No listening ports found or access denied. Try running as root.")
        press_enter_to_continue()
        return
    
    # Group by port
    ports = {}
    for conn in connections:
        port = conn["local"].split(":")[-1] if ":" in conn["local"] else conn["local"]
        if port not in ports:
            ports[port] = conn
    
    # Sort by port number
    sorted_ports = sorted(ports.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)
    
    columns = [
        {"name": "Port", "style": "cyan", "justify": "right"},
        {"name": "Proto"},
        {"name": "Address"},
        {"name": "PID", "justify": "right"},
        {"name": "Process"},
    ]
    
    rows = []
    for port, conn in sorted_ports:
        rows.append([
            port,
            conn["proto"],
            conn["local"],
            str(conn["pid"]),
            conn["process"],
        ])
    
    show_table(f"{len(rows)} listening port(s)", columns, rows)
    
    # Common ports reference
    console.print()
    console.print("[dim]Common ports: 22=SSH, 80=HTTP, 443=HTTPS, 3306=MySQL, 5432=PostgreSQL[/dim]")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/monitor/network.py
git commit -m "feat(monitor): add listening ports view"
```

---

## Task 4: Add Traffic by Process View

**Files:**
- Modify: `modules/monitor/network.py`

**Step 1: Add traffic by process function**

Add after `show_listening_ports()`:

```python
def get_process_connections():
    """
    Get connection count and basic info per process.
    
    Returns:
        dict: {pid: {'name': str, 'connections': int, 'established': int}}
    """
    processes = defaultdict(lambda: {
        'name': '-',
        'user': '-',
        'connections': 0,
        'established': 0,
        'listening': 0,
    })
    
    try:
        connections = psutil.net_connections(kind="inet")
    except psutil.AccessDenied:
        return {}
    
    for conn in connections:
        if not conn.pid:
            continue
        
        pid = conn.pid
        processes[pid]['connections'] += 1
        
        if conn.status == "ESTABLISHED":
            processes[pid]['established'] += 1
        elif conn.status == "LISTEN":
            processes[pid]['listening'] += 1
        
        try:
            proc = psutil.Process(pid)
            processes[pid]['name'] = proc.name()
            processes[pid]['user'] = proc.username()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    return dict(processes)


def show_traffic_by_process():
    """Display network usage by process."""
    clear_screen()
    show_header()
    show_panel("Traffic by Process", title="Network Monitor", style="cyan")
    
    console.print("[dim]Gathering process network data...[/dim]")
    console.print()
    
    proc_conns = get_process_connections()
    
    if not proc_conns:
        show_info("No process data available or access denied. Try running as root.")
        press_enter_to_continue()
        return
    
    # Sort by total connections
    sorted_procs = sorted(
        proc_conns.items(),
        key=lambda x: x[1]['connections'],
        reverse=True
    )
    
    columns = [
        {"name": "PID", "style": "cyan", "justify": "right"},
        {"name": "Process"},
        {"name": "User"},
        {"name": "Connections", "justify": "right"},
        {"name": "Established", "justify": "right"},
        {"name": "Listening", "justify": "right"},
    ]
    
    rows = []
    for pid, info in sorted_procs[:20]:
        rows.append([
            str(pid),
            info['name'][:20],
            info['user'][:10],
            str(info['connections']),
            f"[green]{info['established']}[/green]" if info['established'] else "0",
            f"[yellow]{info['listening']}[/yellow]" if info['listening'] else "0",
        ])
    
    show_table(f"Top {len(rows)} processes by connections", columns, rows)
    
    # Summary
    total_conns = sum(p['connections'] for p in proc_conns.values())
    total_est = sum(p['established'] for p in proc_conns.values())
    total_listen = sum(p['listening'] for p in proc_conns.values())
    
    console.print()
    console.print(f"[bold]Summary:[/bold] {total_conns} total connections ({total_est} established, {total_listen} listening)")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/monitor/network.py
git commit -m "feat(monitor): add traffic by process view"
```

---

## Task 5: Wire Up Network Menu

**Files:**
- Modify: `modules/monitor/__init__.py`

**Step 1: Update __init__.py to import network module**

Replace the `_coming_soon` handler for network:

```python
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
```

**Step 2: Commit**

```bash
git add modules/monitor/__init__.py
git commit -m "feat(monitor): wire up network monitor menu"
```

---

## Summary

After Phase 2, the network monitor will have:

- **Interface Statistics:** All network interfaces with IP, status, RX/TX bytes, current bandwidth
- **Active Connections:** All connections with filter, showing local/remote address, status, process
- **Listening Ports:** All open ports with associated process
- **Traffic by Process:** Top processes by connection count

Files added/modified:
- `modules/monitor/network.py` (new)
- `modules/monitor/__init__.py` (updated)
