"""History and logs viewer for vexo."""

import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_info,
    show_warning,
    press_enter_to_continue,
)
from utils.error_handler import handle_error
from ui.menu import run_menu_loop, select_from_list, text_input
from utils.monitor_logger import load_log_config
from modules.monitor.common import format_bytes


# Log entry regex pattern
LOG_PATTERN = re.compile(
    r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(\w+)\] (.+)$'
)


def show_menu():
    """Display the History & Logs submenu."""
    options = [
        ("recent", "1. View Recent Logs"),
        ("filter", "2. Filter by Level"),
        ("search", "3. Search Logs"),
        ("summary", "4. Today's Summary"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "recent": show_recent_logs,
        "filter": filter_logs_by_level,
        "search": search_logs,
        "summary": show_summary,
    }
    
    run_menu_loop("History & Logs", options, handlers)


def get_log_file_path():
    """Get the main log file path."""
    log_config = load_log_config()
    return os.path.join(log_config['log_dir'], log_config['log_file'])


def parse_log_entry(line):
    """
    Parse a single log line.
    
    Args:
        line: Raw log line string
    
    Returns:
        dict: Parsed log entry or None if invalid
    """
    match = LOG_PATTERN.match(line.strip())
    if not match:
        return None
    
    timestamp_str, level, message = match.groups()
    
    try:
        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return None
    
    return {
        'timestamp': timestamp,
        'level': level,
        'message': message,
    }


def read_log_entries(limit=None, level_filter=None, search_filter=None, date_filter=None):
    """
    Read and parse log entries from file.
    
    Args:
        limit: Maximum number of entries to return
        level_filter: Filter by level (INFO, WARNING, CRITICAL)
        search_filter: Filter by text in message
        date_filter: Filter by date ('today', 'yesterday', 'week')
    
    Returns:
        list: List of parsed log entries (newest first)
    """
    log_file = get_log_file_path()
    entries = []
    
    if not os.path.exists(log_file):
        return entries
    
    # Determine date range
    date_start = None
    if date_filter == 'today':
        date_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_filter == 'yesterday':
        date_start = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_filter == 'week':
        date_start = datetime.now() - timedelta(days=7)
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Process in reverse (newest first)
        for line in reversed(lines):
            entry = parse_log_entry(line)
            if not entry:
                continue
            
            # Apply filters
            if level_filter and entry['level'] != level_filter:
                continue
            
            if search_filter and search_filter.lower() not in entry['message'].lower():
                continue
            
            if date_start and entry['timestamp'] < date_start:
                continue
            
            entries.append(entry)
            
            if limit and len(entries) >= limit:
                break
    
    except Exception:
        pass
    
    return entries


def format_log_entry(entry):
    """Format a log entry for display."""
    time_str = entry['timestamp'].strftime('%H:%M:%S')
    level = entry['level']
    message = entry['message']
    
    # Color based on level
    if level == 'CRITICAL':
        return f"[red]{time_str} [CRITICAL] {message}[/red]"
    elif level == 'WARNING':
        return f"[yellow]{time_str} [WARNING] {message}[/yellow]"
    elif level == 'ERROR':
        return f"[red]{time_str} [ERROR] {message}[/red]"
    else:
        return f"[dim]{time_str} [INFO] {message}[/dim]"


# =============================================================================
# Log View Functions
# =============================================================================

def show_recent_logs():
    """Display recent log entries."""
    clear_screen()
    show_header()
    show_panel("Recent Logs", title="History & Logs", style="cyan")
    
    log_file = get_log_file_path()
    
    if not os.path.exists(log_file):
        show_info(f"No log file found at {log_file}")
        show_info("Run 'Alert Settings > Test Logging' to create logs.")
        press_enter_to_continue()
        return
    
    entries = read_log_entries(limit=50)
    
    if not entries:
        show_info("No log entries found.")
        press_enter_to_continue()
        return
    
    console.print(f"[bold]Log file:[/bold] {log_file}")
    console.print(f"[bold]Showing:[/bold] Last {len(entries)} entries")
    console.print()
    
    # Display entries
    current_date = None
    for entry in entries:
        entry_date = entry['timestamp'].date()
        
        # Print date header when date changes
        if entry_date != current_date:
            current_date = entry_date
            date_str = entry_date.strftime('%Y-%m-%d')
            if entry_date == datetime.now().date():
                date_str += " (Today)"
            elif entry_date == (datetime.now() - timedelta(days=1)).date():
                date_str += " (Yesterday)"
            console.print(f"\n[bold cyan]── {date_str} ──[/bold cyan]")
        
        console.print(format_log_entry(entry))
    
    console.print()
    press_enter_to_continue()


def filter_logs_by_level():
    """Filter logs by severity level."""
    clear_screen()
    show_header()
    show_panel("Filter by Level", title="History & Logs", style="cyan")
    
    options = [
        "All levels",
        "CRITICAL only",
        "WARNING and above",
        "INFO only",
        "← Back",
    ]
    
    choice = select_from_list("Filter", "Select level filter:", options, allow_cancel=False)
    
    if not choice or choice == "← Back":
        return
    
    # Determine filter
    if choice == "CRITICAL only":
        entries = read_log_entries(limit=100, level_filter="CRITICAL")
    elif choice == "WARNING and above":
        # Get both WARNING and CRITICAL
        entries = read_log_entries(limit=100, level_filter="WARNING")
        entries.extend(read_log_entries(limit=100, level_filter="CRITICAL"))
        # Sort by timestamp
        entries.sort(key=lambda x: x['timestamp'], reverse=True)
        entries = entries[:100]
    elif choice == "INFO only":
        entries = read_log_entries(limit=100, level_filter="INFO")
    else:
        entries = read_log_entries(limit=100)
    
    clear_screen()
    show_header()
    show_panel(f"Logs: {choice}", title="History & Logs", style="cyan")
    
    if not entries:
        show_info("No matching log entries found.")
        press_enter_to_continue()
        return
    
    console.print(f"[bold]Found:[/bold] {len(entries)} entries\n")
    
    for entry in entries[:50]:
        console.print(format_log_entry(entry))
    
    if len(entries) > 50:
        console.print(f"\n[dim]... and {len(entries) - 50} more entries[/dim]")
    
    console.print()
    press_enter_to_continue()


def search_logs():
    """Search logs by keyword."""
    clear_screen()
    show_header()
    show_panel("Search Logs", title="History & Logs", style="cyan")
    
    query = text_input("Enter search term:")
    if not query:
        return
    
    console.print(f"\n[dim]Searching for '{query}'...[/dim]\n")
    
    entries = read_log_entries(limit=100, search_filter=query)
    
    if not entries:
        show_info(f"No log entries found containing '{query}'")
        press_enter_to_continue()
        return
    
    console.print(f"[bold]Found:[/bold] {len(entries)} entries matching '{query}'\n")
    
    for entry in entries[:30]:
        # Highlight search term
        formatted = format_log_entry(entry)
        # Simple highlight by replacing
        highlighted = formatted.replace(
            query, f"[bold underline]{query}[/bold underline]"
        )
        console.print(highlighted)
    
    if len(entries) > 30:
        console.print(f"\n[dim]... and {len(entries) - 30} more matches[/dim]")
    
    console.print()
    press_enter_to_continue()


# =============================================================================
# Summary Statistics
# =============================================================================

def parse_metrics_from_message(message):
    """
    Extract CPU, MEM, DISK values from log message.
    
    Args:
        message: Log message string
    
    Returns:
        dict: {'cpu': float, 'memory': float, 'disk': float} or None
    """
    # Pattern: "CPU: 45.2% | MEM: 62.1% | DISK: 55.3%"
    metrics = {}
    
    cpu_match = re.search(r'CPU:\s*([\d.]+)%', message)
    if cpu_match:
        metrics['cpu'] = float(cpu_match.group(1))
    
    mem_match = re.search(r'MEM:\s*([\d.]+)%', message)
    if mem_match:
        metrics['memory'] = float(mem_match.group(1))
    
    disk_match = re.search(r'DISK:\s*([\d.]+)%', message)
    if disk_match:
        metrics['disk'] = float(disk_match.group(1))
    
    return metrics if metrics else None


def show_summary():
    """Display summary statistics for today."""
    clear_screen()
    show_header()
    show_panel("Today's Summary", title="History & Logs", style="cyan")
    
    # Get today's entries
    entries = read_log_entries(date_filter='today')
    
    if not entries:
        show_info("No log entries found for today.")
        show_info("Run 'Alert Settings > Test Logging' to create logs.")
        press_enter_to_continue()
        return
    
    # Count by level
    level_counts = defaultdict(int)
    for entry in entries:
        level_counts[entry['level']] += 1
    
    # Extract metrics
    cpu_values = []
    mem_values = []
    disk_values = []
    cpu_peaks = []
    mem_peaks = []
    disk_peaks = []
    
    for entry in entries:
        metrics = parse_metrics_from_message(entry['message'])
        if metrics:
            if 'cpu' in metrics:
                cpu_values.append(metrics['cpu'])
                cpu_peaks.append((metrics['cpu'], entry['timestamp']))
            if 'memory' in metrics:
                mem_values.append(metrics['memory'])
                mem_peaks.append((metrics['memory'], entry['timestamp']))
            if 'disk' in metrics:
                disk_values.append(metrics['disk'])
                disk_peaks.append((metrics['disk'], entry['timestamp']))
    
    # Display summary
    console.print(f"[bold]Date:[/bold] {datetime.now().strftime('%Y-%m-%d')}")
    console.print(f"[bold]Total Entries:[/bold] {len(entries)}")
    console.print()
    
    # Level breakdown
    columns = [
        {"name": "Level", "style": "cyan"},
        {"name": "Count", "justify": "right"},
        {"name": "Percentage", "justify": "right"},
    ]
    
    rows = []
    for level in ['INFO', 'WARNING', 'CRITICAL', 'ERROR']:
        count = level_counts.get(level, 0)
        if count > 0:
            pct = (count / len(entries)) * 100
            color = "green" if level == "INFO" else "yellow" if level == "WARNING" else "red"
            rows.append([
                f"[{color}]{level}[/{color}]",
                str(count),
                f"{pct:.1f}%"
            ])
    
    show_table("Alert Breakdown", columns, rows)
    
    # Resource statistics
    if cpu_values or mem_values or disk_values:
        console.print()
        console.print("[bold]Resource Statistics:[/bold]")
        console.print()
        
        stats_columns = [
            {"name": "Resource", "style": "cyan"},
            {"name": "Average", "justify": "right"},
            {"name": "Peak", "justify": "right"},
            {"name": "Peak Time", "justify": "right"},
        ]
        
        stats_rows = []
        
        if cpu_values:
            avg = sum(cpu_values) / len(cpu_values)
            peak_val, peak_time = max(cpu_peaks, key=lambda x: x[0])
            peak_color = "red" if peak_val > 85 else "yellow" if peak_val > 70 else "green"
            stats_rows.append([
                "CPU",
                f"{avg:.1f}%",
                f"[{peak_color}]{peak_val:.1f}%[/{peak_color}]",
                peak_time.strftime('%H:%M:%S')
            ])
        
        if mem_values:
            avg = sum(mem_values) / len(mem_values)
            peak_val, peak_time = max(mem_peaks, key=lambda x: x[0])
            peak_color = "red" if peak_val > 90 else "yellow" if peak_val > 80 else "green"
            stats_rows.append([
                "Memory",
                f"{avg:.1f}%",
                f"[{peak_color}]{peak_val:.1f}%[/{peak_color}]",
                peak_time.strftime('%H:%M:%S')
            ])
        
        if disk_values:
            avg = sum(disk_values) / len(disk_values)
            peak_val, peak_time = max(disk_peaks, key=lambda x: x[0])
            peak_color = "red" if peak_val > 90 else "yellow" if peak_val > 80 else "green"
            stats_rows.append([
                "Disk",
                f"{avg:.1f}%",
                f"[{peak_color}]{peak_val:.1f}%[/{peak_color}]",
                peak_time.strftime('%H:%M:%S')
            ])
        
        show_table("Today's Metrics", stats_columns, stats_rows)
    
    # Recent alerts
    alerts = [e for e in entries if e['level'] in ('WARNING', 'CRITICAL')]
    if alerts:
        console.print()
        console.print(f"[bold]Recent Alerts ({len(alerts)}):[/bold]")
        console.print()
        
        for alert in alerts[:10]:
            console.print(format_log_entry(alert))
        
        if len(alerts) > 10:
            console.print(f"[dim]... and {len(alerts) - 10} more alerts[/dim]")
    else:
        console.print()
        console.print("[green]No alerts recorded today![/green]")
    
    console.print()
    press_enter_to_continue()
