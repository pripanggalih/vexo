# Phase 4: Resource Monitoring

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add resource monitoring with worker status (CPU, Memory, Uptime), Laravel queue statistics, and live dashboard.

**Architecture:** Create monitor.py module that uses psutil to get per-process metrics, and optionally queries Laravel database for queue stats. Live dashboard with auto-refresh.

**Tech Stack:** Python, psutil (existing), subprocess

**Prerequisite:** Complete Phase 1 (supervisor package structure)

---

## Task 1: Create Monitor Module

**Files:**
- Create: `modules/supervisor/monitor.py`

**Step 1: Create monitor.py with worker status and monitoring functions**

```python
"""Resource monitoring for vexo-cli supervisor."""

import os
import time
import re
from datetime import datetime

import psutil

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
from ui.menu import show_submenu, select_from_list
from utils.shell import run_command, is_installed, is_service_running

from modules.supervisor.common import (
    get_vexo_workers,
    get_config_path,
    parse_worker_config,
)


def monitoring_menu():
    """Display the monitoring submenu."""
    while True:
        clear_screen()
        show_header()
        
        choice = show_submenu(
            title="Monitoring",
            options=[
                ("status", "1. Worker Status"),
                ("queue_stats", "2. Queue Statistics"),
                ("dashboard", "3. Live Dashboard"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "status":
            show_worker_status()
        elif choice == "queue_stats":
            show_queue_statistics()
        elif choice == "dashboard":
            show_live_dashboard()
        elif choice == "back" or choice is None:
            break


def get_process_info(pid):
    """
    Get process resource information.
    
    Args:
        pid: Process ID
    
    Returns:
        dict: Process info or None if not found
    """
    try:
        proc = psutil.Process(pid)
        with proc.oneshot():
            return {
                'pid': pid,
                'cpu_percent': proc.cpu_percent(interval=0.1),
                'memory_mb': proc.memory_info().rss / (1024 * 1024),
                'memory_percent': proc.memory_percent(),
                'create_time': proc.create_time(),
                'status': proc.status(),
                'num_threads': proc.num_threads(),
            }
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return None


def get_worker_processes():
    """
    Get all supervisor worker processes with their resource usage.
    
    Returns:
        dict: {worker_name: [process_info, ...]}
    """
    workers = {}
    
    # Get status from supervisorctl
    result = run_command("supervisorctl status", check=False, silent=True)
    if result.returncode != 0 or not result.stdout:
        return workers
    
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        
        parts = line.split()
        if len(parts) < 2:
            continue
        
        proc_name = parts[0]
        status = parts[1]
        
        # Extract worker name (before : or _ suffix)
        if ':' in proc_name:
            worker_name = proc_name.split(':')[0]
        elif '_' in proc_name:
            worker_name = '_'.join(proc_name.split('_')[:-1])
        else:
            worker_name = proc_name
        
        # Initialize worker entry
        if worker_name not in workers:
            workers[worker_name] = []
        
        # Get PID if running
        pid = None
        if status == "RUNNING" and "pid" in line.lower():
            pid_match = re.search(r'pid\s+(\d+)', line, re.IGNORECASE)
            if pid_match:
                pid = int(pid_match.group(1))
        
        proc_info = {
            'name': proc_name,
            'status': status,
            'pid': pid,
            'cpu_percent': 0,
            'memory_mb': 0,
            'uptime': '-',
        }
        
        # Get resource info if running
        if pid:
            resource_info = get_process_info(pid)
            if resource_info:
                proc_info['cpu_percent'] = resource_info['cpu_percent']
                proc_info['memory_mb'] = resource_info['memory_mb']
                proc_info['uptime'] = _format_uptime(resource_info['create_time'])
        
        workers[worker_name].append(proc_info)
    
    return workers


def _format_uptime(create_time):
    """Format process create time to uptime string."""
    try:
        delta = datetime.now() - datetime.fromtimestamp(create_time)
        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d {hours}h"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except Exception:
        return "-"


def show_worker_status():
    """Display detailed worker status with resource usage."""
    clear_screen()
    show_header()
    show_panel("Worker Status", title="Monitoring", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    if not is_service_running("supervisor"):
        show_warning("Supervisor service is not running.")
        press_enter_to_continue()
        return
    
    workers = get_worker_processes()
    
    if not workers:
        show_info("No workers found.")
        press_enter_to_continue()
        return
    
    # Summary
    total_procs = sum(len(procs) for procs in workers.values())
    running_procs = sum(
        1 for procs in workers.values() 
        for p in procs if p['status'] == 'RUNNING'
    )
    total_cpu = sum(
        p['cpu_percent'] for procs in workers.values() 
        for p in procs
    )
    total_mem = sum(
        p['memory_mb'] for procs in workers.values() 
        for p in procs
    )
    
    console.print(f"[bold]Workers:[/bold] {len(workers)} | [bold]Processes:[/bold] {running_procs}/{total_procs} running")
    console.print(f"[bold]Total CPU:[/bold] {total_cpu:.1f}% | [bold]Total Memory:[/bold] {total_mem:.1f} MB")
    console.print()
    
    # Worker table
    columns = [
        {"name": "Worker", "style": "cyan"},
        {"name": "Procs", "justify": "center"},
        {"name": "CPU%", "justify": "right"},
        {"name": "Memory", "justify": "right"},
        {"name": "Uptime", "justify": "right"},
        {"name": "Status", "justify": "center"},
    ]
    
    rows = []
    for worker_name, procs in sorted(workers.items()):
        running = sum(1 for p in procs if p['status'] == 'RUNNING')
        total = len(procs)
        cpu = sum(p['cpu_percent'] for p in procs)
        mem = sum(p['memory_mb'] for p in procs)
        
        # Get uptime from first running process
        uptime = "-"
        for p in procs:
            if p['status'] == 'RUNNING' and p['uptime'] != '-':
                uptime = p['uptime']
                break
        
        if running == total:
            status = "[green]● RUN[/green]"
        elif running > 0:
            status = "[yellow]● PARTIAL[/yellow]"
        else:
            status = "[red]● STOP[/red]"
        
        rows.append([
            worker_name,
            f"{running}/{total}",
            f"{cpu:.1f}",
            f"{mem:.1f} MB",
            uptime,
            status,
        ])
    
    show_table("Worker Status", columns, rows)
    
    # Ask to view details
    console.print()
    worker_names = list(workers.keys())
    worker = select_from_list(
        title="View Details",
        message="Select worker for process details (or cancel):",
        options=worker_names,
        allow_cancel=True
    )
    
    if worker:
        _show_worker_details(worker, workers[worker])
    else:
        press_enter_to_continue()


def _show_worker_details(worker_name, processes):
    """Show detailed process information for a worker."""
    clear_screen()
    show_header()
    show_panel(f"Worker: {worker_name}", title="Process Details", style="cyan")
    
    columns = [
        {"name": "Process", "style": "cyan"},
        {"name": "PID", "justify": "right"},
        {"name": "CPU%", "justify": "right"},
        {"name": "Memory", "justify": "right"},
        {"name": "Uptime"},
        {"name": "Status"},
    ]
    
    rows = []
    for proc in processes:
        if proc['status'] == 'RUNNING':
            status = "[green]RUNNING[/green]"
        elif proc['status'] == 'STOPPED':
            status = "[red]STOPPED[/red]"
        else:
            status = f"[yellow]{proc['status']}[/yellow]"
        
        rows.append([
            proc['name'],
            str(proc['pid']) if proc['pid'] else "-",
            f"{proc['cpu_percent']:.1f}",
            f"{proc['memory_mb']:.1f} MB",
            proc['uptime'],
            status,
        ])
    
    show_table(f"{len(processes)} process(es)", columns, rows)
    
    press_enter_to_continue()


def show_queue_statistics():
    """Display Laravel queue statistics."""
    clear_screen()
    show_header()
    show_panel("Queue Statistics", title="Monitoring", style="cyan")
    
    workers = get_vexo_workers()
    
    if not workers:
        show_info("No workers configured.")
        press_enter_to_continue()
        return
    
    # Filter Laravel workers only
    laravel_workers = []
    for worker in workers:
        config = parse_worker_config(worker)
        if config and 'artisan queue:work' in config.get('command', ''):
            laravel_workers.append(worker)
    
    if not laravel_workers:
        show_info("No Laravel queue workers found.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Laravel Queue Workers:[/bold]")
    console.print()
    
    for worker in laravel_workers:
        config = parse_worker_config(worker)
        command = config.get('command', '')
        
        # Extract queue info from command
        conn_match = re.search(r'queue:work\s+(\S+)', command)
        queue_match = re.search(r'--queue=([^\s]+)', command)
        
        connection = conn_match.group(1) if conn_match else "default"
        queues = queue_match.group(1) if queue_match else "default"
        
        console.print(f"[cyan]{worker}[/cyan]")
        console.print(f"  Connection: {connection}")
        console.print(f"  Queues: {queues}")
        console.print(f"  Processes: {config.get('numprocs', 1)}")
        console.print()
    
    console.print("[dim]Note: To see pending/failed job counts, check your Laravel application.[/dim]")
    console.print("[dim]Run: php artisan queue:failed to see failed jobs.[/dim]")
    
    press_enter_to_continue()


def show_live_dashboard():
    """Display live dashboard with auto-refresh."""
    console.print("[dim]Starting live dashboard... Press Ctrl+C to exit.[/dim]")
    time.sleep(1)
    
    try:
        while True:
            clear_screen()
            show_header()
            show_panel("Live Dashboard", title="Monitoring", style="cyan")
            
            if not is_service_running("supervisor"):
                console.print("[red]Supervisor service is not running.[/red]")
                console.print()
                console.print("[dim]Press Ctrl+C to exit[/dim]")
                time.sleep(5)
                continue
            
            workers = get_worker_processes()
            
            # Summary line
            total_procs = sum(len(procs) for procs in workers.values())
            running_procs = sum(
                1 for procs in workers.values() 
                for p in procs if p['status'] == 'RUNNING'
            )
            total_cpu = sum(
                p['cpu_percent'] for procs in workers.values() 
                for p in procs
            )
            total_mem = sum(
                p['memory_mb'] for procs in workers.values() 
                for p in procs
            )
            
            console.print(f"[bold]Workers:[/bold] {len(workers)} | [bold]Processes:[/bold] {running_procs}/{total_procs} | [bold]CPU:[/bold] {total_cpu:.1f}% | [bold]MEM:[/bold] {total_mem:.1f} MB")
            console.print()
            
            # Process list
            for worker_name, procs in sorted(workers.items()):
                for proc in procs:
                    if proc['status'] == 'RUNNING':
                        status_icon = "[green]●[/green]"
                        status_text = "RUNNING"
                    elif proc['status'] == 'STOPPED':
                        status_icon = "[red]●[/red]"
                        status_text = "STOPPED"
                    else:
                        status_icon = "[yellow]●[/yellow]"
                        status_text = proc['status']
                    
                    cpu_color = "red" if proc['cpu_percent'] > 80 else "yellow" if proc['cpu_percent'] > 50 else "white"
                    
                    console.print(
                        f"  {status_icon} {proc['name']:<30} "
                        f"[{cpu_color}]CPU: {proc['cpu_percent']:>5.1f}%[/{cpu_color}]  "
                        f"MEM: {proc['memory_mb']:>6.1f}MB  "
                        f"↑ {proc['uptime']}"
                    )
            
            console.print()
            console.print(f"[dim]Last updated: {datetime.now().strftime('%H:%M:%S')} | Refresh: 5s | Press Ctrl+C to exit[/dim]")
            
            time.sleep(5)
    
    except KeyboardInterrupt:
        console.print("\n[dim]Dashboard stopped.[/dim]")
        time.sleep(1)
```

**Step 2: Commit**

```bash
git add modules/supervisor/monitor.py
git commit -m "feat(supervisor): add resource monitoring with live dashboard"
```

---

## Task 2: Update Package Init with Monitoring

**Files:**
- Modify: `modules/supervisor/__init__.py`

**Step 1: Update __init__.py to include monitoring menu**

```python
"""Supervisor module for vexo-cli (Queue Workers)."""

from ui.menu import run_menu_loop, show_submenu
from utils.shell import is_installed, is_service_running

from modules.supervisor.install import install_supervisor
from modules.supervisor.add_worker import add_worker_menu
from modules.supervisor.worker import remove_worker_interactive, list_workers
from modules.supervisor.edit import edit_worker_menu, clone_worker_menu
from modules.supervisor.control import worker_control_menu
from modules.supervisor.monitor import monitoring_menu
from modules.supervisor.logs import view_logs
from modules.supervisor.status import show_status


def show_menu():
    """Display the Supervisor Management submenu."""
    def get_status():
        if is_service_running("supervisor"):
            return "Supervisor: [green]Running[/green]"
        elif is_installed("supervisor"):
            return "Supervisor: [red]Stopped[/red]"
        return "Supervisor: [dim]Not installed[/dim]"
    
    def get_options():
        options = []
        if is_installed("supervisor"):
            options.extend([
                ("manage", "1. Worker Management"),
                ("control", "2. Worker Control"),
                ("monitor", "3. Monitoring"),
                ("logs", "4. View Logs"),
                ("status", "5. Show Status"),
            ])
        else:
            options.append(("install", "1. Install Supervisor"))
        options.append(("back", "← Back to Main Menu"))
        return options
    
    handlers = {
        "install": install_supervisor,
        "manage": worker_management_menu,
        "control": worker_control_menu,
        "monitor": monitoring_menu,
        "logs": view_logs,
        "status": show_status,
    }
    
    run_menu_loop("Supervisor (Queue Workers)", get_options, handlers, get_status)


def worker_management_menu():
    """Submenu for worker management operations."""
    from ui.components import clear_screen, show_header
    
    while True:
        clear_screen()
        show_header()
        
        choice = show_submenu(
            title="Worker Management",
            options=[
                ("add", "1. Add Worker"),
                ("edit", "2. Edit Worker"),
                ("clone", "3. Clone Worker"),
                ("remove", "4. Remove Worker"),
                ("list", "5. List Workers"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "add":
            add_worker_menu()
        elif choice == "edit":
            edit_worker_menu()
        elif choice == "clone":
            clone_worker_menu()
        elif choice == "remove":
            remove_worker_interactive()
        elif choice == "list":
            list_workers()
        elif choice == "back" or choice is None:
            break
```

**Step 2: Commit**

```bash
git add modules/supervisor/__init__.py
git commit -m "feat(supervisor): integrate monitoring menu"
```

---

## Summary

After Phase 4, the supervisor module will have:

**Worker Status:**
- Per-worker CPU and memory usage
- Process count (running/total)
- Uptime for each worker
- Drill-down to individual process details

**Queue Statistics:**
- List Laravel queue workers
- Show connection and queue names
- Process count per worker

**Live Dashboard:**
- Auto-refresh every 5 seconds
- Real-time CPU/memory per process
- Summary totals
- Color-coded CPU warnings
- Ctrl+C to exit

Files added/modified:
- `modules/supervisor/monitor.py` (new)
- `modules/supervisor/__init__.py` (updated)
