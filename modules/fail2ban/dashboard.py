"""Dashboard and monitoring for fail2ban module."""

import os
from datetime import datetime, timedelta

from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)

from .common import (
    is_fail2ban_installed,
    is_fail2ban_running,
    get_fail2ban_version,
    get_active_jails,
    get_jail_stats,
    FAIL2BAN_LOG,
)


def show_dashboard():
    """Display the fail2ban dashboard with stats overview."""
    clear_screen()
    show_header()
    
    if not is_fail2ban_installed():
        show_error("Fail2ban is not installed.")
        press_enter_to_continue()
        return
    
    _render_status_header()
    console.print()
    _render_statistics()
    console.print()
    _render_two_column_stats()
    console.print()
    _render_recent_activity()
    console.print()
    _render_alerts()
    
    press_enter_to_continue()


def _render_status_header():
    """Render the service status header."""
    if is_fail2ban_running():
        status = "[green]● Running[/green]"
        version = get_fail2ban_version()
    else:
        status = "[red]● Stopped[/red]"
        version = "-"
    
    jails = get_active_jails()
    total_banned = sum(get_jail_stats(j).get('currently_banned', 0) for j in jails)
    uptime = _get_service_uptime()
    
    header_text = (
        f"Service: {status}  │  "
        f"Version: {version}  │  "
        f"Jails: {len(jails)} active  │  "
        f"Currently Banned: {total_banned}  │  "
        f"Uptime: {uptime}"
    )
    
    console.print(Panel(header_text, title="[bold cyan]Fail2ban Dashboard[/bold cyan]", border_style="cyan"))


def _render_statistics():
    """Render ban statistics."""
    stats = _get_ban_statistics()
    
    stats_text = (
        f"[bold]Today:[/bold] {stats['today']} bans    "
        f"[bold]This Week:[/bold] {stats['week']} bans    "
        f"[bold]Total:[/bold] {stats['total']} bans"
    )
    
    console.print(Panel(stats_text, title="Ban Statistics", border_style="blue"))


def _render_two_column_stats():
    """Render top offenders and bans by jail in two columns."""
    offenders_table = Table(title="Top Offenders (24h)", show_header=True, header_style="bold yellow")
    offenders_table.add_column("#", style="dim", width=3)
    offenders_table.add_column("IP Address", style="cyan")
    offenders_table.add_column("Bans", justify="right")
    
    top_offenders = _get_top_offenders(limit=5)
    for i, (ip, count) in enumerate(top_offenders, 1):
        offenders_table.add_row(str(i), ip, str(count))
    
    if not top_offenders:
        offenders_table.add_row("-", "[dim]No data[/dim]", "-")
    
    jails_table = Table(title="Bans by Jail", show_header=True, header_style="bold green")
    jails_table.add_column("Jail", style="cyan")
    jails_table.add_column("Banned", justify="right")
    jails_table.add_column("Total", justify="right")
    
    for jail in get_active_jails():
        stats = get_jail_stats(jail)
        jails_table.add_row(
            jail,
            str(stats.get('currently_banned', 0)),
            str(stats.get('total_banned', 0))
        )
    
    console.print(Columns([offenders_table, jails_table], equal=True, expand=True))


def _render_recent_activity():
    """Render recent activity from fail2ban log."""
    activities = _get_recent_activity(limit=5)
    
    activity_table = Table(title="Recent Activity", show_header=True, header_style="bold")
    activity_table.add_column("Time", style="dim", width=10)
    activity_table.add_column("Action", width=8)
    activity_table.add_column("IP Address", style="cyan")
    activity_table.add_column("Jail")
    activity_table.add_column("Details", style="dim")
    
    for activity in activities:
        action_style = "[green]BAN[/green]" if activity['action'] == 'Ban' else "[yellow]UNBAN[/yellow]"
        activity_table.add_row(
            activity['time'],
            action_style,
            activity['ip'],
            activity['jail'],
            activity.get('details', '')
        )
    
    if not activities:
        activity_table.add_row("-", "-", "[dim]No recent activity[/dim]", "-", "-")
    
    console.print(activity_table)


def _render_alerts():
    """Render active alerts."""
    alerts = _get_alerts()
    
    if alerts:
        alert_text = "\n".join(f"[yellow]![/yellow] {alert}" for alert in alerts)
        console.print(Panel(alert_text, title="[bold yellow]Alerts[/bold yellow]", border_style="yellow"))


def _get_service_uptime():
    """Get fail2ban service uptime."""
    from utils.shell import run_command
    
    result = run_command(
        "systemctl show fail2ban --property=ActiveEnterTimestamp",
        check=False,
        silent=True
    )
    
    if result.returncode != 0:
        return "unknown"
    
    try:
        timestamp_str = result.stdout.split('=')[-1].strip()
        if not timestamp_str:
            return "unknown"
        
        start_time = datetime.strptime(timestamp_str, "%a %Y-%m-%d %H:%M:%S %Z")
        delta = datetime.now() - start_time
        
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except Exception:
        return "unknown"


def _get_ban_statistics():
    """Get ban statistics from fail2ban log."""
    stats = {'today': 0, 'week': 0, 'total': 0}
    
    if not os.path.exists(FAIL2BAN_LOG):
        for jail in get_active_jails():
            jail_stats = get_jail_stats(jail)
            stats['total'] += jail_stats.get('total_banned', 0)
        return stats
    
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    try:
        with open(FAIL2BAN_LOG, 'r') as f:
            for line in f:
                if 'Ban' in line and 'Unban' not in line:
                    stats['total'] += 1
                    
                    try:
                        date_str = line.split()[0]
                        log_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        
                        if log_date == today:
                            stats['today'] += 1
                        if log_date >= week_ago:
                            stats['week'] += 1
                    except (ValueError, IndexError):
                        pass
    except Exception:
        pass
    
    return stats


def _get_top_offenders(limit=5):
    """Get top offending IPs from recent bans."""
    ip_counts = {}
    
    if not os.path.exists(FAIL2BAN_LOG):
        return []
    
    try:
        with open(FAIL2BAN_LOG, 'r') as f:
            for line in f:
                if 'Ban' in line and 'Unban' not in line:
                    parts = line.split('Ban')
                    if len(parts) > 1:
                        ip = parts[-1].strip().split()[0]
                        ip_counts[ip] = ip_counts.get(ip, 0) + 1
    except Exception:
        pass
    
    sorted_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_ips[:limit]


def _get_recent_activity(limit=10):
    """Get recent ban/unban activity from log."""
    activities = []
    
    if not os.path.exists(FAIL2BAN_LOG):
        return activities
    
    try:
        with open(FAIL2BAN_LOG, 'r') as f:
            lines = f.readlines()
        
        for line in reversed(lines):
            if len(activities) >= limit:
                break
            
            if 'Ban' in line or 'Unban' in line:
                try:
                    parts = line.split()
                    time_str = parts[1].split(',')[0]
                    
                    if 'Unban' in line:
                        action = 'Unban'
                        ip_idx = line.index('Unban') + 6
                    else:
                        action = 'Ban'
                        ip_idx = line.index('Ban') + 4
                    
                    ip = line[ip_idx:].strip().split()[0]
                    
                    jail = "unknown"
                    if '[' in line and ']' in line:
                        jail = line.split('[')[-1].split(']')[0]
                    
                    activities.append({
                        'time': time_str,
                        'action': action,
                        'ip': ip,
                        'jail': jail,
                        'details': ''
                    })
                except (ValueError, IndexError):
                    pass
    except Exception:
        pass
    
    return activities


def _get_alerts():
    """Get active alerts based on current state."""
    alerts = []
    
    top_offenders = _get_top_offenders(limit=3)
    for ip, count in top_offenders:
        if count >= 10:
            alerts.append(f"{ip} banned {count}x - consider adding to permanent ban list")
    
    if not is_fail2ban_running():
        alerts.append("Fail2ban service is not running!")
    
    stats = _get_ban_statistics()
    if stats['today'] > 100:
        alerts.append(f"High activity: {stats['today']} bans today - possible attack in progress")
    
    return alerts


def show_live_activity():
    """Show live activity monitor (tail -f style)."""
    clear_screen()
    show_header()
    show_panel("Live Activity Monitor", title="Fail2ban", style="cyan")
    
    if not os.path.exists(FAIL2BAN_LOG):
        show_error(f"Log file not found: {FAIL2BAN_LOG}")
        press_enter_to_continue()
        return
    
    console.print("[dim]Watching fail2ban.log... Press Ctrl+C to stop[/dim]")
    console.print()
    
    try:
        import subprocess
        process = subprocess.Popen(
            ['tail', '-f', FAIL2BAN_LOG],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        while True:
            line = process.stdout.readline()
            if line:
                if 'Ban' in line:
                    console.print(f"[green]{line.strip()}[/green]")
                elif 'Unban' in line:
                    console.print(f"[yellow]{line.strip()}[/yellow]")
                else:
                    console.print(line.strip())
    except KeyboardInterrupt:
        process.terminate()
        console.print()
        show_info("Stopped monitoring.")
    
    press_enter_to_continue()
