"""Traffic statistics from nginx access logs."""

import os
from collections import Counter

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_error, show_info, press_enter_to_continue,
)
from ui.menu import select_from_list
from utils.shell import run_command
from modules.webserver.utils import get_configured_domains


NGINX_LOG_DIR = "/var/log/nginx"


def show_traffic_stats():
    """Show traffic statistics for a domain."""
    clear_screen()
    show_header()
    show_panel("Traffic Stats", title="Domain & Nginx", style="cyan")
    
    domains = get_configured_domains()
    domains.insert(0, "(All - default nginx log)")
    
    domain = select_from_list("Select Domain", "Choose domain:", domains)
    if not domain:
        return
    
    # Time range
    ranges = ["Today", "Last 7 days", "Last 30 days", "All time"]
    time_range = select_from_list("Time Range", "Select time range:", ranges)
    if not time_range:
        return
    
    # Get log file
    if domain == "(All - default nginx log)":
        log_path = os.path.join(NGINX_LOG_DIR, "access.log")
    else:
        log_path = os.path.join(NGINX_LOG_DIR, f"{domain}.access.log")
        if not os.path.exists(log_path):
            log_path = os.path.join(NGINX_LOG_DIR, "access.log")
    
    if not os.path.exists(log_path):
        show_error("Log file not found.")
        press_enter_to_continue()
        return
    
    clear_screen()
    show_header()
    show_panel(f"Traffic Stats: {domain}", title="Domain & Nginx", style="cyan")
    
    console.print(f"[dim]Analyzing: {log_path}[/dim]")
    console.print(f"[dim]Period: {time_range}[/dim]")
    console.print()
    
    # Parse log file
    stats = _parse_access_log(log_path, time_range)
    
    if not stats['total_requests']:
        show_info("No data found for selected period.")
        press_enter_to_continue()
        return
    
    # Summary
    columns = [
        {"name": "Metric", "style": "cyan"},
        {"name": "Value", "justify": "right"},
    ]
    
    rows = [
        ["Total Requests", f"{stats['total_requests']:,}"],
        ["Unique IPs", f"{stats['unique_ips']:,}"],
        ["Bandwidth (est.)", stats['bandwidth']],
    ]
    
    show_table("Summary", columns, rows, show_header=False)
    console.print()
    
    # Status codes
    if stats['status_codes']:
        console.print("[bold]Status Codes:[/bold]")
        for code, count in stats['status_codes'].most_common(5):
            pct = (count / stats['total_requests']) * 100
            color = "green" if code.startswith('2') else "yellow" if code.startswith('3') else "red"
            console.print(f"  [{color}]{code}[/{color}]: {count:,} ({pct:.1f}%)")
        console.print()
    
    # Top IPs
    if stats['top_ips']:
        console.print("[bold]Top 5 IPs:[/bold]")
        for ip, count in stats['top_ips'].most_common(5):
            console.print(f"  {ip}: {count:,} requests")
        console.print()
    
    # Top URLs
    if stats['top_urls']:
        console.print("[bold]Top 5 URLs:[/bold]")
        for url, count in stats['top_urls'].most_common(5):
            url_display = url[:50] + "..." if len(url) > 50 else url
            console.print(f"  {url_display}: {count:,} hits")
    
    press_enter_to_continue()


def _parse_access_log(log_path, time_range):
    """Parse nginx access log and return statistics."""
    stats = {
        'total_requests': 0,
        'unique_ips': 0,
        'bandwidth': '0 B',
        'status_codes': Counter(),
        'top_ips': Counter(),
        'top_urls': Counter(),
    }
    
    # Determine how many lines to process based on time range
    if time_range == "Today":
        cmd = f"grep \"$(date '+%d/%b/%Y')\" {log_path} 2>/dev/null"
    elif time_range == "Last 7 days":
        cmd = f"tail -n 100000 {log_path} 2>/dev/null"
    elif time_range == "Last 30 days":
        cmd = f"tail -n 500000 {log_path} 2>/dev/null"
    else:
        cmd = f"cat {log_path} 2>/dev/null"
    
    result = run_command(cmd, check=False, silent=True)
    if result.returncode != 0 or not result.stdout.strip():
        return stats
    
    lines = result.stdout.strip().split('\n')
    total_bytes = 0
    ips = set()
    
    for line in lines:
        if not line.strip():
            continue
        
        parts = line.split()
        if len(parts) < 10:
            continue
        
        try:
            ip = parts[0]
            url = parts[6] if len(parts) > 6 else "-"
            status = parts[8] if len(parts) > 8 else "0"
            size = parts[9] if len(parts) > 9 else "0"
            
            stats['total_requests'] += 1
            ips.add(ip)
            stats['top_ips'][ip] += 1
            stats['top_urls'][url] += 1
            stats['status_codes'][status] += 1
            
            if size.isdigit():
                total_bytes += int(size)
        except (IndexError, ValueError):
            continue
    
    stats['unique_ips'] = len(ips)
    
    # Format bandwidth
    if total_bytes > 1024**3:
        stats['bandwidth'] = f"{total_bytes / 1024**3:.2f} GB"
    elif total_bytes > 1024**2:
        stats['bandwidth'] = f"{total_bytes / 1024**2:.2f} MB"
    elif total_bytes > 1024:
        stats['bandwidth'] = f"{total_bytes / 1024:.2f} KB"
    else:
        stats['bandwidth'] = f"{total_bytes} B"
    
    return stats
