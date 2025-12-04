# Phase 3: Process Manager

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add full-featured process manager with view, search, kill, signal, and priority control capabilities.

**Architecture:** Create process.py module with process listing (sortable by CPU/Memory), search functionality, and process actions (kill, signal, nice). Include safety guards for critical system processes.

**Tech Stack:** Python, psutil (existing), os (stdlib)

**Prerequisite:** Complete Phase 1 (monitor package structure)

---

## Task 1: Create Process Module Base

**Files:**
- Create: `modules/monitor/process.py`

**Step 1: Create process.py with process listing**

```python
"""Process management for vexo."""

import os
import signal
import psutil
from datetime import datetime

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_info,
    show_warning,
    show_error,
    show_success,
    press_enter_to_continue,
)
from ui.menu import run_menu_loop, confirm_action, text_input, select_from_list
from modules.monitor.common import format_bytes


# Critical processes that should not be killed
PROTECTED_PIDS = [0, 1]
PROTECTED_NAMES = ['systemd', 'init', 'kernel', 'kthreadd']


def show_menu():
    """Display the Process Manager submenu."""
    options = [
        ("top_cpu", "1. Top Processes (CPU)"),
        ("top_mem", "2. Top Processes (Memory)"),
        ("search", "3. Search Process"),
        ("all", "4. All Processes"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "top_cpu": lambda: show_top_processes("cpu"),
        "top_mem": lambda: show_top_processes("memory"),
        "search": search_process,
        "all": show_all_processes,
    }
    
    run_menu_loop("Process Manager", options, handlers)


def get_processes(sort_by="cpu", limit=20):
    """
    Get list of processes sorted by specified criteria.
    
    Args:
        sort_by: 'cpu', 'memory', 'pid', 'name'
        limit: Maximum number of processes to return
    
    Returns:
        list: List of process dicts
    """
    processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 
                                      'memory_percent', 'status', 'create_time',
                                      'num_threads', 'cmdline']):
        try:
            pinfo = proc.info
            
            # Calculate runtime
            create_time = pinfo.get('create_time', 0)
            if create_time:
                runtime = datetime.now() - datetime.fromtimestamp(create_time)
                runtime_str = _format_runtime(runtime.total_seconds())
            else:
                runtime_str = "-"
            
            processes.append({
                'pid': pinfo['pid'],
                'name': pinfo['name'] or '-',
                'user': pinfo['username'] or '-',
                'cpu': pinfo['cpu_percent'] or 0,
                'memory': pinfo['memory_percent'] or 0,
                'status': pinfo['status'] or '-',
                'runtime': runtime_str,
                'threads': pinfo['num_threads'] or 0,
                'cmdline': ' '.join(pinfo['cmdline'] or [])[:50],
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    # Sort
    if sort_by == "cpu":
        processes.sort(key=lambda x: x['cpu'], reverse=True)
    elif sort_by == "memory":
        processes.sort(key=lambda x: x['memory'], reverse=True)
    elif sort_by == "pid":
        processes.sort(key=lambda x: x['pid'])
    elif sort_by == "name":
        processes.sort(key=lambda x: x['name'].lower())
    
    return processes[:limit] if limit else processes


def _format_runtime(seconds):
    """Format seconds to human-readable runtime."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h{mins}m"
    else:
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        return f"{days}d{hours}h"


def show_top_processes(sort_by="cpu"):
    """Display top processes sorted by CPU or Memory."""
    clear_screen()
    show_header()
    
    title = "Top Processes by CPU" if sort_by == "cpu" else "Top Processes by Memory"
    show_panel(title, title="Process Manager", style="cyan")
    
    processes = get_processes(sort_by=sort_by, limit=20)
    
    columns = [
        {"name": "PID", "style": "cyan", "justify": "right"},
        {"name": "Name"},
        {"name": "User"},
        {"name": "CPU%", "justify": "right"},
        {"name": "MEM%", "justify": "right"},
        {"name": "Status"},
        {"name": "Time"},
    ]
    
    rows = []
    for proc in processes:
        cpu_color = "red" if proc['cpu'] > 80 else "yellow" if proc['cpu'] > 50 else "white"
        mem_color = "red" if proc['memory'] > 80 else "yellow" if proc['memory'] > 50 else "white"
        
        rows.append([
            str(proc['pid']),
            proc['name'][:20],
            proc['user'][:10],
            f"[{cpu_color}]{proc['cpu']:.1f}[/{cpu_color}]",
            f"[{mem_color}]{proc['memory']:.1f}[/{mem_color}]",
            proc['status'][:8],
            proc['runtime'],
        ])
    
    show_table(f"Top {len(rows)} processes", columns, rows)
    
    console.print()
    console.print("[dim]Enter PID to manage process, or press Enter to go back[/dim]")
    
    pid_input = text_input("PID (or Enter to skip):", default="")
    if pid_input and pid_input.isdigit():
        show_process_actions(int(pid_input))
    
    # Don't call press_enter_to_continue here, handled by menu loop
```

**Step 2: Commit**

```bash
git add modules/monitor/process.py
git commit -m "feat(monitor): add process listing with CPU/memory sorting"
```

---

## Task 2: Add Search Process Function

**Files:**
- Modify: `modules/monitor/process.py`

**Step 1: Add search function**

Add after `show_top_processes()`:

```python
def search_process():
    """Search for processes by name or PID."""
    clear_screen()
    show_header()
    show_panel("Search Process", title="Process Manager", style="cyan")
    
    query = text_input("Enter process name or PID:")
    if not query:
        return
    
    processes = get_processes(sort_by="cpu", limit=None)
    
    # Search by PID or name
    results = []
    for proc in processes:
        if query.isdigit() and str(proc['pid']) == query:
            results.append(proc)
        elif query.lower() in proc['name'].lower():
            results.append(proc)
        elif query.lower() in proc['cmdline'].lower():
            results.append(proc)
    
    if not results:
        show_info(f"No processes found matching '{query}'")
        press_enter_to_continue()
        return
    
    console.print(f"\n[bold]Found {len(results)} process(es):[/bold]\n")
    
    columns = [
        {"name": "PID", "style": "cyan", "justify": "right"},
        {"name": "Name"},
        {"name": "User"},
        {"name": "CPU%", "justify": "right"},
        {"name": "MEM%", "justify": "right"},
        {"name": "Command"},
    ]
    
    rows = []
    for proc in results[:20]:
        rows.append([
            str(proc['pid']),
            proc['name'][:15],
            proc['user'][:10],
            f"{proc['cpu']:.1f}",
            f"{proc['memory']:.1f}",
            proc['cmdline'][:30],
        ])
    
    show_table(f"{len(results)} result(s)", columns, rows)
    
    if len(results) > 20:
        console.print(f"[dim]... and {len(results) - 20} more[/dim]")
    
    console.print()
    pid_input = text_input("Enter PID to manage (or Enter to skip):", default="")
    if pid_input and pid_input.isdigit():
        show_process_actions(int(pid_input))


def show_all_processes():
    """Display all processes."""
    clear_screen()
    show_header()
    show_panel("All Processes", title="Process Manager", style="cyan")
    
    processes = get_processes(sort_by="pid", limit=None)
    
    console.print(f"[bold]Total:[/bold] {len(processes)} processes\n")
    
    columns = [
        {"name": "PID", "style": "cyan", "justify": "right"},
        {"name": "Name"},
        {"name": "User"},
        {"name": "CPU%", "justify": "right"},
        {"name": "MEM%", "justify": "right"},
        {"name": "Threads", "justify": "right"},
        {"name": "Status"},
    ]
    
    rows = []
    for proc in processes[:50]:
        rows.append([
            str(proc['pid']),
            proc['name'][:20],
            proc['user'][:10],
            f"{proc['cpu']:.1f}",
            f"{proc['memory']:.1f}",
            str(proc['threads']),
            proc['status'][:10],
        ])
    
    show_table(f"Showing {len(rows)} of {len(processes)}", columns, rows)
    
    if len(processes) > 50:
        console.print(f"[dim]... and {len(processes) - 50} more. Use Search for specific process.[/dim]")
    
    console.print()
    pid_input = text_input("Enter PID to manage (or Enter to skip):", default="")
    if pid_input and pid_input.isdigit():
        show_process_actions(int(pid_input))
```

**Step 2: Commit**

```bash
git add modules/monitor/process.py
git commit -m "feat(monitor): add process search functionality"
```

---

## Task 3: Add Process Actions (Kill, Signal, Nice)

**Files:**
- Modify: `modules/monitor/process.py`

**Step 1: Add process actions function**

Add after `show_all_processes()`:

```python
def is_protected_process(pid, name):
    """Check if process is protected from being killed."""
    if pid in PROTECTED_PIDS:
        return True
    if name.lower() in [p.lower() for p in PROTECTED_NAMES]:
        return True
    return False


def get_process_details(pid):
    """
    Get detailed information about a process.
    
    Args:
        pid: Process ID
    
    Returns:
        dict: Process details or None if not found
    """
    try:
        proc = psutil.Process(pid)
        
        with proc.oneshot():
            return {
                'pid': pid,
                'name': proc.name(),
                'user': proc.username(),
                'status': proc.status(),
                'cpu': proc.cpu_percent(interval=0.1),
                'memory': proc.memory_percent(),
                'memory_bytes': proc.memory_info().rss,
                'threads': proc.num_threads(),
                'nice': proc.nice(),
                'create_time': datetime.fromtimestamp(proc.create_time()),
                'cmdline': ' '.join(proc.cmdline()),
                'cwd': proc.cwd() if hasattr(proc, 'cwd') else '-',
            }
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
        return None


def show_process_actions(pid):
    """Display process details and action menu."""
    clear_screen()
    show_header()
    
    proc = get_process_details(pid)
    if not proc:
        show_error(f"Process {pid} not found or access denied.")
        press_enter_to_continue()
        return
    
    show_panel(f"Process: {proc['name']} (PID: {pid})", title="Process Manager", style="cyan")
    
    # Show details
    console.print(f"[bold]User:[/bold] {proc['user']}")
    console.print(f"[bold]Status:[/bold] {proc['status']}")
    console.print(f"[bold]CPU:[/bold] {proc['cpu']:.1f}%")
    console.print(f"[bold]Memory:[/bold] {proc['memory']:.1f}% ({format_bytes(proc['memory_bytes'])})")
    console.print(f"[bold]Threads:[/bold] {proc['threads']}")
    console.print(f"[bold]Nice:[/bold] {proc['nice']}")
    console.print(f"[bold]Started:[/bold] {proc['create_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    console.print(f"[bold]Command:[/bold] {proc['cmdline'][:60]}")
    console.print()
    
    # Check if protected
    if is_protected_process(pid, proc['name']):
        show_warning("This is a critical system process. Actions are restricted.")
        press_enter_to_continue()
        return
    
    # Action menu
    actions = [
        ("term", "1. Kill (SIGTERM) - graceful shutdown"),
        ("kill", "2. Force Kill (SIGKILL) - immediate termination"),
        ("hup", "3. Reload (SIGHUP) - reload configuration"),
        ("nice", "4. Change Priority (nice)"),
        ("back", "← Back"),
    ]
    
    action_labels = [label for _, label in actions]
    action_keys = [key for key, _ in actions]
    
    choice = select_from_list(
        "Process Actions",
        "Select action:",
        action_labels,
        allow_cancel=False
    )
    
    if not choice or choice == "← Back":
        return
    
    # Map label back to key
    action_idx = action_labels.index(choice)
    action = action_keys[action_idx]
    
    if action == "term":
        _send_signal(pid, proc['name'], signal.SIGTERM, "SIGTERM")
    elif action == "kill":
        _send_signal(pid, proc['name'], signal.SIGKILL, "SIGKILL")
    elif action == "hup":
        _send_signal(pid, proc['name'], signal.SIGHUP, "SIGHUP")
    elif action == "nice":
        _change_priority(pid, proc['name'], proc['nice'])


def _send_signal(pid, name, sig, sig_name):
    """Send a signal to a process with confirmation."""
    if not confirm_action(f"Send {sig_name} to {name} (PID: {pid})?"):
        show_info("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        os.kill(pid, sig)
        show_success(f"Sent {sig_name} to process {pid}")
    except ProcessLookupError:
        show_error(f"Process {pid} not found.")
    except PermissionError:
        show_error(f"Permission denied. Try running as root.")
    except Exception as e:
        show_error(f"Failed to send signal: {e}")
    
    press_enter_to_continue()


def _change_priority(pid, name, current_nice):
    """Change process priority (nice value)."""
    console.print(f"\n[bold]Current nice value:[/bold] {current_nice}")
    console.print("[dim]Nice values: -20 (highest priority) to 19 (lowest priority)[/dim]")
    console.print("[dim]Only root can set negative nice values.[/dim]\n")
    
    new_nice = text_input("Enter new nice value (-20 to 19):", default=str(current_nice))
    
    if not new_nice:
        return
    
    try:
        new_nice = int(new_nice)
        if new_nice < -20 or new_nice > 19:
            show_error("Nice value must be between -20 and 19.")
            press_enter_to_continue()
            return
    except ValueError:
        show_error("Invalid nice value.")
        press_enter_to_continue()
        return
    
    if not confirm_action(f"Change {name} (PID: {pid}) nice value to {new_nice}?"):
        show_info("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        proc = psutil.Process(pid)
        proc.nice(new_nice)
        show_success(f"Changed nice value to {new_nice}")
    except psutil.NoSuchProcess:
        show_error(f"Process {pid} not found.")
    except psutil.AccessDenied:
        show_error("Permission denied. Try running as root for negative nice values.")
    except Exception as e:
        show_error(f"Failed to change priority: {e}")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/monitor/process.py
git commit -m "feat(monitor): add process actions (kill, signal, nice)"
```

---

## Task 4: Wire Up Process Manager Menu

**Files:**
- Modify: `modules/monitor/__init__.py`

**Step 1: Update __init__.py to import process module**

Update the imports and handlers:

```python
"""System monitoring module for vexo."""

from ui.menu import run_menu_loop

from modules.monitor.dashboard import show_dashboard
from modules.monitor.cpu import show_cpu_details
from modules.monitor.memory import show_ram_details
from modules.monitor.disk import show_disk_details
from modules.monitor.network import show_menu as show_network_menu
from modules.monitor.process import show_menu as show_process_menu


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
        # Phase 4-6 handlers will be added later
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
git commit -m "feat(monitor): wire up process manager menu"
```

---

## Summary

After Phase 3, the process manager will have:

- **Top Processes (CPU):** Top 20 processes sorted by CPU usage
- **Top Processes (Memory):** Top 20 processes sorted by memory usage
- **Search Process:** Find process by name, PID, or command
- **All Processes:** View all running processes
- **Process Actions:**
  - Kill (SIGTERM) - graceful shutdown
  - Force Kill (SIGKILL) - immediate termination
  - Reload (SIGHUP) - reload configuration
  - Change Priority (nice)
- **Safety:** Protected critical system processes (PID 0, 1, systemd, init)

Files added/modified:
- `modules/monitor/process.py` (new)
- `modules/monitor/__init__.py` (updated)
