# Phase 6: Logging & Monitoring

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement comprehensive firewall logging with log viewing, blocked attempts statistics, log level configuration, and live monitoring.

**Architecture:** Parse /var/log/ufw.log for statistics. Use Rich live display for real-time monitoring. Store stats cache in JSON for quick access.

**Tech Stack:** Python, Rich (Live, Table), UFW CLI, log parsing

---

## Task 1: Implement Logging & Monitoring Module

**Files:**
- Modify: `modules/firewall/logs.py`

**Step 1: Replace logs.py with full implementation**

```python
"""Logging and monitoring for firewall."""

import os
import re
from datetime import datetime, timedelta
from collections import Counter
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
from ui.menu import run_menu_loop, text_input, select_from_list, confirm_action
from utils.shell import run_command, require_root
from modules.firewall.common import is_ufw_installed, get_ufw_status_text


# Log file paths
UFW_LOG = "/var/log/ufw.log"
KERN_LOG = "/var/log/kern.log"  # Fallback


def show_logs_menu():
    """Display logs and monitoring submenu."""
    def get_status():
        level = _get_log_level()
        return f"UFW: {get_ufw_status_text()} | Logging: {level}"
    
    options = [
        ("view", "1. View Firewall Logs"),
        ("stats", "2. Blocked Attempts Stats"),
        ("settings", "3. Log Settings"),
        ("live", "4. Live Monitor"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "view": view_logs,
        "stats": show_blocked_stats,
        "settings": configure_logging,
        "live": live_monitor,
    }
    
    run_menu_loop("Logs & Monitoring", options, handlers, get_status)


def _get_log_level():
    """Get current UFW logging level."""
    result = run_command("ufw status verbose", check=False, silent=True)
    if result.returncode != 0:
        return "unknown"
    
    for line in result.stdout.split('\n'):
        if "Logging:" in line:
            parts = line.split(':')
            if len(parts) >= 2:
                return parts[1].strip().split()[0]
    
    return "unknown"


def _get_log_file():
    """Get the active log file path."""
    if os.path.exists(UFW_LOG):
        return UFW_LOG
    elif os.path.exists(KERN_LOG):
        return KERN_LOG
    return None


def _parse_ufw_log_line(line):
    """Parse a UFW log line into structured data."""
    # Example: Jan 15 10:30:45 server kernel: [UFW BLOCK] IN=eth0 ... SRC=1.2.3.4 ... DPT=22 ...
    
    entry = {
        "timestamp": None,
        "action": None,
        "src_ip": None,
        "dst_port": None,
        "protocol": None,
        "interface": None
    }
    
    # Skip non-UFW lines
    if "[UFW" not in line:
        return None
    
    # Extract action
    if "[UFW BLOCK]" in line:
        entry["action"] = "BLOCK"
    elif "[UFW ALLOW]" in line:
        entry["action"] = "ALLOW"
    elif "[UFW AUDIT]" in line:
        entry["action"] = "AUDIT"
    elif "[UFW LIMIT BLOCK]" in line:
        entry["action"] = "LIMIT"
    else:
        return None
    
    # Extract timestamp (first part of line)
    match = re.match(r'^(\w+\s+\d+\s+\d+:\d+:\d+)', line)
    if match:
        entry["timestamp"] = match.group(1)
    
    # Extract source IP
    match = re.search(r'SRC=(\d+\.\d+\.\d+\.\d+)', line)
    if match:
        entry["src_ip"] = match.group(1)
    
    # Extract destination port
    match = re.search(r'DPT=(\d+)', line)
    if match:
        entry["dst_port"] = match.group(1)
    
    # Extract protocol
    match = re.search(r'PROTO=(\w+)', line)
    if match:
        entry["protocol"] = match.group(1)
    
    # Extract interface
    match = re.search(r'IN=(\w+)', line)
    if match:
        entry["interface"] = match.group(1)
    
    return entry


def view_logs():
    """View firewall logs."""
    clear_screen()
    show_header()
    show_panel("Firewall Logs", title="Logs & Monitoring", style="cyan")
    
    log_file = _get_log_file()
    
    if not log_file:
        show_error("UFW log file not found.")
        show_info("Check if logging is enabled: ufw logging on")
        press_enter_to_continue()
        return
    
    # Filter options
    filter_opt = select_from_list(
        title="Filter",
        message="Filter logs by:",
        options=["All entries", "Blocked only", "Allowed only", "Rate limited only", "Last hour", "Last 24 hours"]
    )
    
    if not filter_opt:
        press_enter_to_continue()
        return
    
    # Read and parse logs
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
    except IOError as e:
        show_error(f"Cannot read log file: {e}")
        press_enter_to_continue()
        return
    
    # Parse entries
    entries = []
    for line in lines:
        entry = _parse_ufw_log_line(line)
        if entry:
            entries.append(entry)
    
    # Apply filters
    if "Blocked only" in filter_opt:
        entries = [e for e in entries if e["action"] == "BLOCK"]
    elif "Allowed only" in filter_opt:
        entries = [e for e in entries if e["action"] == "ALLOW"]
    elif "Rate limited" in filter_opt:
        entries = [e for e in entries if e["action"] == "LIMIT"]
    elif "Last hour" in filter_opt:
        entries = entries[-100:]  # Approximate
    elif "Last 24 hours" in filter_opt:
        entries = entries[-1000:]  # Approximate
    
    if not entries:
        show_info("No matching log entries found.")
        press_enter_to_continue()
        return
    
    # Display (last 50 entries)
    display_entries = entries[-50:]
    
    console.print(f"[bold]Showing {len(display_entries)} of {len(entries)} entries:[/bold]")
    console.print()
    
    columns = [
        {"name": "Time", "style": "dim"},
        {"name": "Action", "justify": "center"},
        {"name": "Source IP", "style": "cyan"},
        {"name": "Port"},
        {"name": "Proto"},
    ]
    
    rows = []
    for e in display_entries:
        action_colored = _format_action(e["action"])
        rows.append([
            e["timestamp"] or "-",
            action_colored,
            e["src_ip"] or "-",
            e["dst_port"] or "-",
            e["protocol"] or "-"
        ])
    
    show_table("", columns, rows)
    
    if len(entries) > 50:
        console.print(f"[dim]... and {len(entries) - 50} more entries[/dim]")
    
    press_enter_to_continue()


def _format_action(action):
    """Format action with color."""
    if action == "BLOCK":
        return "[red]BLOCK[/red]"
    elif action == "ALLOW":
        return "[green]ALLOW[/green]"
    elif action == "LIMIT":
        return "[yellow]LIMIT[/yellow]"
    return action


def show_blocked_stats():
    """Show statistics about blocked attempts."""
    clear_screen()
    show_header()
    show_panel("Blocked Attempts Statistics", title="Logs & Monitoring", style="cyan")
    
    log_file = _get_log_file()
    
    if not log_file:
        show_error("UFW log file not found.")
        press_enter_to_continue()
        return
    
    # Time period
    period = select_from_list(
        title="Period",
        message="Statistics for:",
        options=["Today", "Last 24 hours", "Last 7 days", "All time"]
    )
    
    if not period:
        press_enter_to_continue()
        return
    
    show_info("Analyzing logs...")
    
    # Read logs
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
    except IOError as e:
        show_error(f"Cannot read log file: {e}")
        press_enter_to_continue()
        return
    
    # Parse and collect stats
    blocked_ips = Counter()
    targeted_ports = Counter()
    actions = Counter()
    total_blocked = 0
    total_allowed = 0
    total_limited = 0
    
    for line in lines:
        entry = _parse_ufw_log_line(line)
        if not entry:
            continue
        
        actions[entry["action"]] += 1
        
        if entry["action"] in ("BLOCK", "LIMIT"):
            total_blocked += 1
            if entry["src_ip"]:
                blocked_ips[entry["src_ip"]] += 1
            if entry["dst_port"]:
                targeted_ports[entry["dst_port"]] += 1
        
        if entry["action"] == "ALLOW":
            total_allowed += 1
        
        if entry["action"] == "LIMIT":
            total_limited += 1
    
    # Display stats
    console.print()
    
    # Summary panel
    summary = f"""[bold]Summary ({period}):[/bold]
Total Blocked: [red]{total_blocked}[/red]
Total Allowed: [green]{total_allowed}[/green]
Rate Limited: [yellow]{total_limited}[/yellow]
Unique Blocked IPs: {len(blocked_ips)}"""
    
    show_panel(summary, title="Overview", style="cyan")
    
    # Top blocked IPs
    if blocked_ips:
        console.print()
        console.print("[bold]Top Blocked IPs:[/bold]")
        console.print()
        
        columns = [
            {"name": "#", "style": "dim", "justify": "right"},
            {"name": "IP Address", "style": "red"},
            {"name": "Count", "justify": "right"},
        ]
        
        rows = []
        for i, (ip, count) in enumerate(blocked_ips.most_common(10), 1):
            rows.append([str(i), ip, str(count)])
        
        show_table("", columns, rows)
        
        # Alert for suspicious IPs
        top_ip, top_count = blocked_ips.most_common(1)[0]
        if top_count > 100:
            console.print()
            console.print(f"[yellow]⚠ Alert: {top_ip} has {top_count} blocked attempts![/yellow]")
            console.print("[dim]Consider adding this IP to deny list.[/dim]")
    
    # Top targeted ports
    if targeted_ports:
        console.print()
        console.print("[bold]Most Targeted Ports:[/bold]")
        console.print()
        
        columns = [
            {"name": "#", "style": "dim", "justify": "right"},
            {"name": "Port", "style": "cyan"},
            {"name": "Attempts", "justify": "right"},
        ]
        
        rows = []
        for i, (port, count) in enumerate(targeted_ports.most_common(10), 1):
            port_name = _get_port_name(port)
            rows.append([str(i), f"{port} ({port_name})" if port_name else port, str(count)])
        
        show_table("", columns, rows)
    
    press_enter_to_continue()


def _get_port_name(port):
    """Get common port name."""
    port_names = {
        "22": "SSH",
        "23": "Telnet",
        "25": "SMTP",
        "80": "HTTP",
        "443": "HTTPS",
        "3306": "MySQL",
        "5432": "PostgreSQL",
        "6379": "Redis",
        "27017": "MongoDB"
    }
    return port_names.get(str(port), "")


def configure_logging():
    """Configure UFW logging settings."""
    clear_screen()
    show_header()
    show_panel("Log Settings", title="Logs & Monitoring", style="cyan")
    
    if not is_ufw_installed():
        show_error("UFW is not installed.")
        press_enter_to_continue()
        return
    
    current_level = _get_log_level()
    
    console.print(f"[bold]Current Log Level:[/bold] {current_level}")
    console.print()
    console.print("[bold]Available Levels:[/bold]")
    console.print("  • [cyan]off[/cyan]    - Disable logging")
    console.print("  • [cyan]low[/cyan]    - Log blocked packets not matching default policy")
    console.print("  • [cyan]medium[/cyan] - Log blocked + invalid packets")
    console.print("  • [cyan]high[/cyan]   - Log blocked + invalid + new connections")
    console.print("  • [cyan]full[/cyan]   - Log everything (very verbose)")
    console.print()
    
    new_level = select_from_list(
        title="Log Level",
        message="Select new log level:",
        options=["off", "low", "medium", "high", "full"]
    )
    
    if not new_level:
        press_enter_to_continue()
        return
    
    if new_level == current_level:
        show_info(f"Log level is already '{new_level}'.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    result = run_command(f"ufw logging {new_level}", check=False, silent=True)
    
    if result.returncode == 0:
        show_success(f"Log level changed to '{new_level}'!")
    else:
        show_error(f"Failed to change log level: {result.stderr}")
    
    press_enter_to_continue()


def live_monitor():
    """Live monitor firewall activity."""
    clear_screen()
    show_header()
    show_panel("Live Firewall Monitor", title="Logs & Monitoring", style="cyan")
    
    log_file = _get_log_file()
    
    if not log_file:
        show_error("UFW log file not found.")
        press_enter_to_continue()
        return
    
    # Filter selection
    filter_opt = select_from_list(
        title="Filter",
        message="Show events:",
        options=["All events", "Blocked only", "Allowed only", "Rate limited only"]
    )
    
    if not filter_opt:
        press_enter_to_continue()
        return
    
    console.print()
    console.print("[bold]Starting live monitor...[/bold]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    console.print()
    console.print("-" * 70)
    
    # Build filter for action types
    action_filter = None
    if "Blocked" in filter_opt:
        action_filter = ["BLOCK", "LIMIT"]
    elif "Allowed" in filter_opt:
        action_filter = ["ALLOW"]
    elif "Rate limited" in filter_opt:
        action_filter = ["LIMIT"]
    
    try:
        # Use tail -f approach
        import subprocess
        import select
        
        process = subprocess.Popen(
            ["tail", "-f", log_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        while True:
            # Check if there's data to read
            readable, _, _ = select.select([process.stdout], [], [], 1.0)
            
            if readable:
                line = process.stdout.readline()
                if line:
                    entry = _parse_ufw_log_line(line)
                    if entry:
                        # Apply filter
                        if action_filter and entry["action"] not in action_filter:
                            continue
                        
                        # Format and display
                        action_colored = _format_action(entry["action"])
                        console.print(
                            f"{entry['timestamp'] or '-':15} "
                            f"{action_colored:20} "
                            f"{entry['src_ip'] or '-':15} → "
                            f":{entry['dst_port'] or '-':5} "
                            f"{entry['protocol'] or ''}"
                        )
    
    except KeyboardInterrupt:
        if 'process' in locals():
            process.terminate()
        console.print()
        console.print("[dim]Monitor stopped.[/dim]")
    
    except Exception as e:
        show_error(f"Monitor error: {e}")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/firewall/logs.py
git commit -m "feat(firewall): implement logging with stats, settings, and live monitor"
```

---

## Verification

After completing all tasks, verify:

1. **View Logs works:**
   - Shows parsed log entries
   - Filter by action type works
   - Table format is readable

2. **Blocked Stats works:**
   - Shows summary statistics
   - Top blocked IPs listed
   - Most targeted ports listed
   - Alerts for suspicious activity

3. **Log Settings works:**
   - Shows current level
   - Can change log level

4. **Live Monitor works:**
   - Streams new log entries
   - Filter by action type
   - Ctrl+C stops cleanly
