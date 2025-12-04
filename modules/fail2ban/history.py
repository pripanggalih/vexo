"""History and analytics for fail2ban module."""

import os
import re
import sqlite3
from datetime import datetime, timedelta

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_success,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from utils.error_handler import handle_error
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop

from .common import (
    FAIL2BAN_LOG,
    VEXO_FAIL2BAN_DIR,
    HISTORY_DB,
    ensure_data_dir,
    get_active_jails,
)


def show_menu():
    """Display history menu."""
    def get_status():
        count = _get_total_bans()
        return f"{count} total bans recorded"
    
    def get_options():
        return [
            ("history", "1. Ban History"),
            ("live", "2. Live Activity"),
            ("offenders", "3. Repeat Offenders"),
            ("patterns", "4. Attack Patterns"),
            ("export", "5. Export Report"),
            ("import", "6. Import from Log"),
            ("back", "← Back"),
        ]
    
    handlers = {
        "history": show_ban_history,
        "live": show_live_activity,
        "offenders": show_repeat_offenders,
        "patterns": show_attack_patterns,
        "export": export_report,
        "import": import_from_log,
    }
    
    run_menu_loop("History & Logs", get_options, handlers, get_status)


def show_ban_history():
    """Show searchable ban history."""
    clear_screen()
    show_header()
    show_panel("Ban History", title="History", style="cyan")
    
    console.print("[dim]Filter options:[/dim]")
    console.print()
    
    ip_filter = text_input(
        title="Filter by IP",
        message="IP address (empty for all):",
        default=""
    )
    
    jails = ["(all)"] + get_active_jails()
    jail_filter = select_from_list(
        title="Filter by Jail",
        message="Select jail:",
        options=jails
    )
    jail_filter = None if jail_filter == "(all)" else jail_filter
    
    period_options = ["Last 24 hours", "Last 7 days", "Last 30 days", "All time"]
    period = select_from_list(
        title="Time Period",
        message="Select period:",
        options=period_options
    )
    
    now = datetime.now()
    if period == "Last 24 hours":
        start_date = now - timedelta(days=1)
    elif period == "Last 7 days":
        start_date = now - timedelta(days=7)
    elif period == "Last 30 days":
        start_date = now - timedelta(days=30)
    else:
        start_date = None
    
    bans = _query_bans(ip=ip_filter, jail=jail_filter, start_date=start_date, limit=100)
    
    if not bans:
        show_info("No ban records found.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Time", "style": "dim", "width": 19},
        {"name": "IP Address", "style": "cyan"},
        {"name": "Jail"},
        {"name": "Action"},
        {"name": "Duration", "style": "dim"},
    ]
    
    rows = []
    for ban in bans:
        action_style = "[green]BAN[/green]" if ban['action'] == 'ban' else "[yellow]UNBAN[/yellow]"
        rows.append([
            ban['timestamp'][:19],
            ban['ip'],
            ban['jail'],
            action_style,
            ban.get('duration', '-') or '-',
        ])
    
    show_table(f"Ban History ({len(bans)} records)", columns, rows)
    
    console.print()
    console.print(f"[dim]Showing {len(bans)} of {_get_total_bans()} total records[/dim]")
    
    press_enter_to_continue()


def show_live_activity():
    """Show live activity monitor."""
    clear_screen()
    show_header()
    show_panel("Live Activity Monitor", title="History", style="cyan")
    
    if not os.path.exists(FAIL2BAN_LOG):
        handle_error("E6003", f"Log file not found: {FAIL2BAN_LOG}")
        press_enter_to_continue()
        return
    
    console.print("[dim]Watching fail2ban.log... Press Ctrl+C to stop[/dim]")
    console.print()
    
    try:
        import subprocess
        process = subprocess.Popen(
            ['tail', '-f', '-n', '20', FAIL2BAN_LOG],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        while True:
            line = process.stdout.readline()
            if line:
                if 'Ban' in line and 'Unban' not in line:
                    console.print(f"[green]{line.strip()}[/green]")
                elif 'Unban' in line:
                    console.print(f"[yellow]{line.strip()}[/yellow]")
                elif 'Found' in line:
                    console.print(f"[cyan]{line.strip()}[/cyan]")
                else:
                    console.print(f"[dim]{line.strip()}[/dim]")
    except KeyboardInterrupt:
        process.terminate()
        console.print()
        show_info("Stopped monitoring.")
    except Exception as e:
        handle_error("E6003", f"Error: {e}")
    
    press_enter_to_continue()


def show_repeat_offenders():
    """Show repeat offenders analysis."""
    clear_screen()
    show_header()
    show_panel("Repeat Offenders", title="History", style="cyan")
    
    offenders = _get_repeat_offenders(min_bans=3, limit=20)
    
    if not offenders:
        show_info("No repeat offenders found (IPs banned 3+ times).")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "#", "style": "dim", "width": 4},
        {"name": "IP Address", "style": "cyan"},
        {"name": "Total Bans", "justify": "right"},
        {"name": "First Seen", "style": "dim"},
        {"name": "Last Seen", "style": "dim"},
        {"name": "Status"},
    ]
    
    rows = []
    for i, off in enumerate(offenders, 1):
        status = "[green]Active[/green]" if _is_currently_banned(off['ip']) else "[dim]Released[/dim]"
        rows.append([
            str(i),
            off['ip'],
            str(off['total_bans']),
            off['first_seen'][:10],
            off['last_seen'][:10],
            status,
        ])
    
    show_table("Repeat Offenders (3+ bans)", columns, rows)
    
    console.print()
    
    if confirm_action("Add any to permanent ban list?"):
        ip = select_from_list(
            title="Select IP",
            message="Choose IP to permanently ban:",
            options=[o['ip'] for o in offenders]
        )
        if ip:
            from .bans import _add_to_permanent_list
            _add_to_permanent_list(ip, "all", "Repeat offender")
            show_success(f"IP {ip} added to permanent ban list!")
    
    press_enter_to_continue()


def show_attack_patterns():
    """Show attack patterns analysis."""
    clear_screen()
    show_header()
    show_panel("Attack Patterns", title="History", style="cyan")
    
    stats = _get_attack_statistics()
    
    console.print("[bold]Bans by Service:[/bold]")
    console.print()
    
    by_jail = stats.get('by_jail', {})
    total = sum(by_jail.values()) or 1
    
    for jail, count in sorted(by_jail.items(), key=lambda x: x[1], reverse=True)[:10]:
        pct = (count / total) * 100
        bar_len = int(pct / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        console.print(f"  {jail:20} {bar} {count:5} ({pct:.1f}%)")
    
    console.print()
    
    console.print("[bold]Bans by Hour (UTC):[/bold]")
    console.print()
    
    by_hour = stats.get('by_hour', {})
    max_hour = max(by_hour.values()) if by_hour else 1
    
    for hour in range(24):
        count = by_hour.get(hour, 0)
        bar_len = int((count / max_hour) * 20) if max_hour > 0 else 0
        bar = "█" * bar_len
        console.print(f"  {hour:02d}:00 {bar:20} {count}")
    
    console.print()
    
    console.print("[bold]Recent Trend (7 days):[/bold]")
    console.print()
    
    by_day = stats.get('by_day', {})
    
    for i in range(6, -1, -1):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        count = by_day.get(date, 0)
        bar_len = min(count // 5, 30)
        bar = "█" * bar_len
        day_name = (datetime.now() - timedelta(days=i)).strftime("%a")
        console.print(f"  {day_name} {date} {bar:30} {count}")
    
    press_enter_to_continue()


def export_report():
    """Export history to CSV."""
    clear_screen()
    show_header()
    show_panel("Export Report", title="History", style="cyan")
    
    path = text_input(
        title="Export Path",
        message="Enter file path:",
        default="/tmp/fail2ban_report.csv"
    )
    
    if not path:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    bans = _query_bans(limit=10000)
    
    try:
        with open(path, 'w') as f:
            f.write("timestamp,ip,jail,action,duration\n")
            for ban in bans:
                f.write(f"{ban['timestamp']},{ban['ip']},{ban['jail']},{ban['action']},{ban.get('duration', '')}\n")
        
        show_success(f"Exported {len(bans)} records to {path}")
    except Exception as e:
        handle_error("E6003", f"Export failed: {e}")
    
    press_enter_to_continue()


def import_from_log():
    """Import ban history from fail2ban.log."""
    clear_screen()
    show_header()
    show_panel("Import from Log", title="History", style="cyan")
    
    if not os.path.exists(FAIL2BAN_LOG):
        handle_error("E6003", f"Log file not found: {FAIL2BAN_LOG}")
        press_enter_to_continue()
        return
    
    console.print("This will parse fail2ban.log and import ban events to database.")
    console.print()
    
    if not confirm_action("Import from log?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    imported = _import_log_to_db()
    show_success(f"Imported {imported} ban events!")
    
    press_enter_to_continue()


def _init_db():
    """Initialize the history database."""
    ensure_data_dir()
    
    conn = sqlite3.connect(HISTORY_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            ip TEXT NOT NULL,
            jail TEXT NOT NULL,
            action TEXT NOT NULL,
            duration TEXT,
            reason TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_bans_ip ON bans(ip)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_bans_timestamp ON bans(timestamp)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_bans_jail ON bans(jail)
    ''')
    
    conn.commit()
    conn.close()


def _query_bans(ip=None, jail=None, start_date=None, limit=100):
    """Query ban history from database."""
    _init_db()
    
    conn = sqlite3.connect(HISTORY_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM bans WHERE 1=1"
    params = []
    
    if ip:
        query += " AND ip LIKE ?"
        params.append(f"%{ip}%")
    
    if jail:
        query += " AND jail = ?"
        params.append(jail)
    
    if start_date:
        query += " AND timestamp >= ?"
        params.append(start_date.isoformat())
    
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def _get_total_bans():
    """Get total number of ban records."""
    _init_db()
    
    try:
        conn = sqlite3.connect(HISTORY_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM bans WHERE action = 'ban'")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def _get_repeat_offenders(min_bans=3, limit=20):
    """Get IPs with multiple bans."""
    _init_db()
    
    conn = sqlite3.connect(HISTORY_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            ip,
            COUNT(*) as total_bans,
            MIN(timestamp) as first_seen,
            MAX(timestamp) as last_seen
        FROM bans
        WHERE action = 'ban'
        GROUP BY ip
        HAVING COUNT(*) >= ?
        ORDER BY total_bans DESC
        LIMIT ?
    ''', (min_bans, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def _get_attack_statistics():
    """Get attack statistics for patterns analysis."""
    _init_db()
    
    conn = sqlite3.connect(HISTORY_DB)
    cursor = conn.cursor()
    
    stats = {
        'by_jail': {},
        'by_hour': {},
        'by_day': {},
    }
    
    cursor.execute('''
        SELECT jail, COUNT(*) as count
        FROM bans WHERE action = 'ban'
        GROUP BY jail
    ''')
    for row in cursor.fetchall():
        stats['by_jail'][row[0]] = row[1]
    
    cursor.execute('''
        SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour, COUNT(*) as count
        FROM bans WHERE action = 'ban'
        GROUP BY hour
    ''')
    for row in cursor.fetchall():
        stats['by_hour'][row[0]] = row[1]
    
    cursor.execute('''
        SELECT DATE(timestamp) as day, COUNT(*) as count
        FROM bans 
        WHERE action = 'ban' AND timestamp >= DATE('now', '-7 days')
        GROUP BY day
    ''')
    for row in cursor.fetchall():
        stats['by_day'][row[0]] = row[1]
    
    conn.close()
    return stats


def _is_currently_banned(ip):
    """Check if IP is currently banned."""
    from .common import get_all_banned_ips
    all_banned = get_all_banned_ips()
    for jail_ips in all_banned.values():
        if ip in jail_ips:
            return True
    return False


def _import_log_to_db():
    """Import events from fail2ban.log to database."""
    _init_db()
    
    if not os.path.exists(FAIL2BAN_LOG):
        return 0
    
    conn = sqlite3.connect(HISTORY_DB)
    cursor = conn.cursor()
    
    imported = 0
    
    try:
        with open(FAIL2BAN_LOG, 'r') as f:
            for line in f:
                if 'Ban' in line or 'Unban' in line:
                    event = _parse_log_line(line)
                    if event:
                        cursor.execute('''
                            INSERT INTO bans (timestamp, ip, jail, action)
                            VALUES (?, ?, ?, ?)
                        ''', (event['timestamp'], event['ip'], event['jail'], event['action']))
                        imported += 1
        
        conn.commit()
    except Exception as e:
        handle_error("E6003", f"Import error: {e}")
    finally:
        conn.close()
    
    return imported


def _parse_log_line(line):
    """Parse a fail2ban log line."""
    try:
        ts_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if not ts_match:
            return None
        timestamp = ts_match.group(1)
        
        if 'Unban' in line:
            action = 'unban'
        elif 'Ban' in line:
            action = 'ban'
        else:
            return None
        
        jail_match = re.search(r'\[(\w+[-\w]*)\]', line)
        if jail_match:
            jail = jail_match.group(1)
        else:
            jail = 'unknown'
        
        ip_match = re.search(r'(Ban|Unban)\s+(\d+\.\d+\.\d+\.\d+)', line)
        if ip_match:
            ip = ip_match.group(2)
        else:
            return None
        
        return {
            'timestamp': timestamp,
            'ip': ip,
            'jail': jail,
            'action': action
        }
    except Exception:
        return None


def record_ban_event(ip, jail, action, duration=None, reason=None):
    """Record a ban event to database."""
    _init_db()
    
    conn = sqlite3.connect(HISTORY_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO bans (timestamp, ip, jail, action, duration, reason)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (datetime.now().isoformat(), ip, jail, action, duration, reason))
    
    conn.commit()
    conn.close()
