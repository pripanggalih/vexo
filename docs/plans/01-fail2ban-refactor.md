# Fail2ban Phase 1: Package Refactor + Dashboard

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convert single fail2ban.py to package structure and add comprehensive dashboard with real-time stats.

**Architecture:** Refactor monolithic module into package with common utilities, then add dashboard showing service status, ban statistics, top offenders, and recent activity.

**Tech Stack:** Python, Rich (tables, panels, progress bars), SQLite (for history tracking)

---

## Task 1: Create Package Structure

**Files:**
- Create: `modules/fail2ban/__init__.py`
- Create: `modules/fail2ban/common.py`
- Keep: `modules/fail2ban.py` (will be removed after migration)

**Step 1: Create package directory**

```bash
mkdir -p modules/fail2ban
```

**Step 2: Create common.py with constants and utilities**

```python
"""Common utilities and constants for fail2ban module."""

import os
import re
from pathlib import Path

from utils.shell import run_command, is_installed, is_service_running


# Paths
FAIL2BAN_CONFIG_DIR = "/etc/fail2ban"
JAIL_LOCAL = "/etc/fail2ban/jail.local"
JAIL_D_DIR = "/etc/fail2ban/jail.d"
FILTER_D_DIR = "/etc/fail2ban/filter.d"
FAIL2BAN_LOG = "/var/log/fail2ban.log"
FAIL2BAN_DB = "/var/lib/fail2ban/fail2ban.sqlite3"

# Vexo data directory
VEXO_FAIL2BAN_DIR = Path.home() / ".vexo" / "fail2ban"
HISTORY_DB = VEXO_FAIL2BAN_DIR / "history.db"
CONFIG_FILE = VEXO_FAIL2BAN_DIR / "config.json"
WHITELIST_FILE = VEXO_FAIL2BAN_DIR / "whitelist.json"
NOTIFICATIONS_FILE = VEXO_FAIL2BAN_DIR / "notifications.json"
BACKUPS_DIR = VEXO_FAIL2BAN_DIR / "backups"

# Defaults
DEFAULT_BANTIME = "1h"
DEFAULT_FINDTIME = "10m"
DEFAULT_MAXRETRY = "5"


def ensure_data_dir():
    """Ensure vexo fail2ban data directory exists."""
    VEXO_FAIL2BAN_DIR.mkdir(parents=True, exist_ok=True)
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


def is_fail2ban_installed():
    """Check if fail2ban is installed."""
    return is_installed("fail2ban")


def is_fail2ban_running():
    """Check if fail2ban service is running."""
    return is_service_running("fail2ban")


def get_fail2ban_version():
    """Get fail2ban version."""
    result = run_command("fail2ban-client --version", check=False, silent=True)
    if result.returncode == 0:
        # Parse "Fail2Ban v1.0.2"
        match = re.search(r'v?(\d+\.\d+\.\d+)', result.stdout)
        if match:
            return match.group(1)
    return "unknown"


def get_active_jails():
    """Get list of active jails."""
    result = run_command("fail2ban-client status", check=False, silent=True)
    if result.returncode != 0:
        return []
    
    jails = []
    for line in result.stdout.split('\n'):
        if 'Jail list:' in line:
            jail_part = line.split(':')[-1].strip()
            jails = [j.strip() for j in jail_part.split(',') if j.strip()]
            break
    
    return jails


def get_jail_stats(jail):
    """Get statistics for a specific jail."""
    result = run_command(f"fail2ban-client status {jail}", check=False, silent=True)
    if result.returncode != 0:
        return {'currently_banned': 0, 'total_banned': 0, 'failed': 0}
    
    stats = {'currently_banned': 0, 'total_banned': 0, 'failed': 0}
    
    for line in result.stdout.split('\n'):
        if 'Currently banned:' in line:
            try:
                stats['currently_banned'] = int(line.split(':')[-1].strip())
            except ValueError:
                pass
        elif 'Total banned:' in line:
            try:
                stats['total_banned'] = int(line.split(':')[-1].strip())
            except ValueError:
                pass
        elif 'Currently failed:' in line:
            try:
                stats['failed'] = int(line.split(':')[-1].strip())
            except ValueError:
                pass
    
    return stats


def get_banned_ips(jail):
    """Get list of banned IPs for a jail."""
    result = run_command(f"fail2ban-client status {jail}", check=False, silent=True)
    if result.returncode != 0:
        return []
    
    for line in result.stdout.split('\n'):
        if 'Banned IP list:' in line:
            ip_part = line.split(':')[-1].strip()
            if ip_part:
                return [ip.strip() for ip in ip_part.split() if ip.strip()]
    
    return []


def get_all_banned_ips():
    """Get all banned IPs across all jails."""
    banned = {}
    for jail in get_active_jails():
        ips = get_banned_ips(jail)
        if ips:
            banned[jail] = ips
    return banned


def is_valid_ip(ip):
    """Validate IPv4 address."""
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    try:
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
    except ValueError:
        return False
    return True


def is_valid_cidr(cidr):
    """Validate CIDR notation (e.g., 192.168.0.0/24)."""
    if '/' not in cidr:
        return False
    ip_part, prefix = cidr.rsplit('/', 1)
    if not is_valid_ip(ip_part):
        return False
    try:
        prefix_int = int(prefix)
        return 0 <= prefix_int <= 32
    except ValueError:
        return False


def detect_services():
    """Detect installed services for jail configuration."""
    return {
        'ssh': is_installed("openssh-server") or os.path.exists("/etc/ssh/sshd_config"),
        'nginx': is_installed("nginx"),
        'apache': is_installed("apache2"),
        'postfix': is_installed("postfix"),
        'dovecot': is_installed("dovecot-core"),
        'mysql': is_installed("mysql-server") or is_installed("mariadb-server"),
        'postgresql': is_installed("postgresql"),
    }
```

**Step 3: Create __init__.py with main menu**

```python
"""Fail2ban (brute force protection) module for vexo-cli."""

from ui.menu import run_menu_loop
from utils.shell import is_installed, is_service_running

from .common import is_fail2ban_installed, is_fail2ban_running


def show_menu():
    """Display the Fail2ban main menu."""
    def get_status():
        if is_fail2ban_running():
            return "Fail2ban: [green]Running[/green]"
        elif is_fail2ban_installed():
            return "Fail2ban: [red]Stopped[/red]"
        return "Fail2ban: [dim]Not installed[/dim]"
    
    def get_options():
        options = []
        if is_fail2ban_installed():
            options.extend([
                ("dashboard", "1. Dashboard"),
                ("jails", "2. Jail Management"),
                ("bans", "3. Ban Management"),
                ("whitelist", "4. Whitelist"),
                ("filters", "5. Filters"),
                ("history", "6. History & Logs"),
                ("notifications", "7. Notifications"),
                ("backup", "8. Backup & Restore"),
                ("settings", "9. Settings"),
            ])
        else:
            options.append(("install", "1. Install Fail2ban"))
        options.append(("back", "← Back to Main Menu"))
        return options
    
    handlers = {
        "install": _install_handler,
        "dashboard": _dashboard_handler,
        "jails": _jails_handler,
        "bans": _bans_handler,
        "whitelist": _whitelist_handler,
        "filters": _filters_handler,
        "history": _history_handler,
        "notifications": _notifications_handler,
        "backup": _backup_handler,
        "settings": _settings_handler,
    }
    
    run_menu_loop("Fail2ban (Brute Force Protection)", get_options, handlers, get_status)


def _install_handler():
    """Handle install menu option."""
    from .settings import install_fail2ban
    install_fail2ban()


def _dashboard_handler():
    """Handle dashboard menu option."""
    from .dashboard import show_dashboard
    show_dashboard()


def _jails_handler():
    """Handle jails menu option."""
    from .jails import show_menu as show_jails_menu
    show_jails_menu()


def _bans_handler():
    """Handle bans menu option."""
    from .bans import show_menu as show_bans_menu
    show_bans_menu()


def _whitelist_handler():
    """Handle whitelist menu option."""
    from .whitelist import show_menu as show_whitelist_menu
    show_whitelist_menu()


def _filters_handler():
    """Handle filters menu option."""
    from .filters import show_menu as show_filters_menu
    show_filters_menu()


def _history_handler():
    """Handle history menu option."""
    from .history import show_menu as show_history_menu
    show_history_menu()


def _notifications_handler():
    """Handle notifications menu option."""
    from .notifications import show_menu as show_notifications_menu
    show_notifications_menu()


def _backup_handler():
    """Handle backup menu option."""
    from .backup import show_menu as show_backup_menu
    show_backup_menu()


def _settings_handler():
    """Handle settings menu option."""
    from .settings import show_menu as show_settings_menu
    show_settings_menu()
```

**Step 4: Commit package structure**

```bash
git add modules/fail2ban/
git commit -m "refactor(fail2ban): create package structure with common utilities"
```

---

## Task 2: Create Dashboard Module

**Files:**
- Create: `modules/fail2ban/dashboard.py`

**Step 1: Create dashboard.py with stats and overview**

```python
"""Dashboard and monitoring for fail2ban module."""

import os
from datetime import datetime, timedelta

from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text

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
from ui.menu import run_menu_loop

from .common import (
    is_fail2ban_installed,
    is_fail2ban_running,
    get_fail2ban_version,
    get_active_jails,
    get_jail_stats,
    get_all_banned_ips,
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
    
    # Service status header
    _render_status_header()
    
    console.print()
    
    # Statistics section
    _render_statistics()
    
    console.print()
    
    # Two column layout: Top Offenders | Bans by Jail
    _render_two_column_stats()
    
    console.print()
    
    # Recent activity
    _render_recent_activity()
    
    console.print()
    
    # Alerts
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
    
    # Calculate uptime from fail2ban process
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
    # Top offenders table
    offenders_table = Table(title="Top Offenders (24h)", show_header=True, header_style="bold yellow")
    offenders_table.add_column("#", style="dim", width=3)
    offenders_table.add_column("IP Address", style="cyan")
    offenders_table.add_column("Bans", justify="right")
    
    top_offenders = _get_top_offenders(limit=5)
    for i, (ip, count) in enumerate(top_offenders, 1):
        offenders_table.add_row(str(i), ip, str(count))
    
    if not top_offenders:
        offenders_table.add_row("-", "[dim]No data[/dim]", "-")
    
    # Bans by jail table
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
    
    # Render side by side
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
        # Parse "ActiveEnterTimestamp=Mon 2024-01-15 10:30:00 UTC"
        timestamp_str = result.stdout.split('=')[-1].strip()
        if not timestamp_str:
            return "unknown"
        
        # Parse the timestamp
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
        # Fallback to jail stats
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
                    
                    # Parse date from log line
                    # Format: 2024-01-15 14:32:15,123 fail2ban.actions...
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
                    # Extract IP from log line
                    # Format: ... Ban 192.168.1.1
                    parts = line.split('Ban')
                    if len(parts) > 1:
                        ip = parts[-1].strip().split()[0]
                        ip_counts[ip] = ip_counts.get(ip, 0) + 1
    except Exception:
        pass
    
    # Sort by count descending
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
        
        # Process from end (most recent)
        for line in reversed(lines):
            if len(activities) >= limit:
                break
            
            if 'Ban' in line or 'Unban' in line:
                try:
                    # Parse log line
                    parts = line.split()
                    time_str = parts[1].split(',')[0]  # HH:MM:SS
                    
                    if 'Unban' in line:
                        action = 'Unban'
                        ip_idx = line.index('Unban') + 6
                    else:
                        action = 'Ban'
                        ip_idx = line.index('Ban') + 4
                    
                    ip = line[ip_idx:].strip().split()[0]
                    
                    # Extract jail name
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
    
    # Check for repeat offenders
    top_offenders = _get_top_offenders(limit=3)
    for ip, count in top_offenders:
        if count >= 10:
            alerts.append(f"{ip} banned {count}x - consider adding to permanent ban list")
    
    # Check if service is down
    if not is_fail2ban_running():
        alerts.append("Fail2ban service is not running!")
    
    # Check for high ban rate
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
                # Highlight ban/unban
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
```

**Step 2: Commit dashboard module**

```bash
git add modules/fail2ban/dashboard.py
git commit -m "feat(fail2ban): add dashboard with stats, top offenders, and activity"
```

---

## Task 3: Create Placeholder Submodules

**Files:**
- Create: `modules/fail2ban/jails.py`
- Create: `modules/fail2ban/bans.py`
- Create: `modules/fail2ban/whitelist.py`
- Create: `modules/fail2ban/filters.py`
- Create: `modules/fail2ban/history.py`
- Create: `modules/fail2ban/notifications.py`
- Create: `modules/fail2ban/backup.py`
- Create: `modules/fail2ban/settings.py`

**Step 1: Create jails.py placeholder**

```python
"""Jail management for fail2ban module."""

from ui.components import show_info, press_enter_to_continue, clear_screen, show_header, show_panel


def show_menu():
    """Display jail management menu."""
    clear_screen()
    show_header()
    show_panel("Jail Management", title="Fail2ban", style="cyan")
    show_info("Jail management will be implemented in Phase 2.")
    press_enter_to_continue()
```

**Step 2: Create bans.py placeholder**

```python
"""Ban management for fail2ban module."""

from ui.components import show_info, press_enter_to_continue, clear_screen, show_header, show_panel


def show_menu():
    """Display ban management menu."""
    clear_screen()
    show_header()
    show_panel("Ban Management", title="Fail2ban", style="cyan")
    show_info("Ban management will be implemented in Phase 3.")
    press_enter_to_continue()
```

**Step 3: Create whitelist.py placeholder**

```python
"""Whitelist management for fail2ban module."""

from ui.components import show_info, press_enter_to_continue, clear_screen, show_header, show_panel


def show_menu():
    """Display whitelist management menu."""
    clear_screen()
    show_header()
    show_panel("Whitelist Management", title="Fail2ban", style="cyan")
    show_info("Whitelist management will be implemented in Phase 4.")
    press_enter_to_continue()
```

**Step 4: Create filters.py placeholder**

```python
"""Filter management for fail2ban module."""

from ui.components import show_info, press_enter_to_continue, clear_screen, show_header, show_panel


def show_menu():
    """Display filter management menu."""
    clear_screen()
    show_header()
    show_panel("Filter Management", title="Fail2ban", style="cyan")
    show_info("Filter management will be implemented in Phase 5.")
    press_enter_to_continue()
```

**Step 5: Create history.py placeholder**

```python
"""History and analytics for fail2ban module."""

from ui.components import show_info, press_enter_to_continue, clear_screen, show_header, show_panel


def show_menu():
    """Display history menu."""
    clear_screen()
    show_header()
    show_panel("History & Logs", title="Fail2ban", style="cyan")
    show_info("History & analytics will be implemented in Phase 6.")
    press_enter_to_continue()
```

**Step 6: Create notifications.py placeholder**

```python
"""Notification system for fail2ban module."""

from ui.components import show_info, press_enter_to_continue, clear_screen, show_header, show_panel


def show_menu():
    """Display notifications menu."""
    clear_screen()
    show_header()
    show_panel("Notifications", title="Fail2ban", style="cyan")
    show_info("Notification system will be implemented in Phase 7.")
    press_enter_to_continue()
```

**Step 7: Create backup.py placeholder**

```python
"""Backup and restore for fail2ban module."""

from ui.components import show_info, press_enter_to_continue, clear_screen, show_header, show_panel


def show_menu():
    """Display backup menu."""
    clear_screen()
    show_header()
    show_panel("Backup & Restore", title="Fail2ban", style="cyan")
    show_info("Backup & restore will be implemented in Phase 8.")
    press_enter_to_continue()
```

**Step 8: Create settings.py with install and basic settings**

```python
"""Settings and service control for fail2ban module."""

import os

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_success,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, run_menu_loop
from utils.shell import (
    run_command_realtime,
    service_control,
    require_root,
)

from .common import (
    is_fail2ban_installed,
    is_fail2ban_running,
    detect_services,
    JAIL_LOCAL,
    DEFAULT_BANTIME,
    DEFAULT_FINDTIME,
    DEFAULT_MAXRETRY,
)


def show_menu():
    """Display settings menu."""
    def get_status():
        if is_fail2ban_running():
            return "[green]Running[/green]"
        elif is_fail2ban_installed():
            return "[red]Stopped[/red]"
        return "[dim]Not installed[/dim]"
    
    def get_options():
        return [
            ("global", "1. Global Ban Settings"),
            ("recidive", "2. Recidive Settings"),
            ("service", "3. Service Control"),
            ("back", "← Back"),
        ]
    
    handlers = {
        "global": configure_global_settings,
        "recidive": configure_recidive,
        "service": service_control_menu,
    }
    
    run_menu_loop("Settings", get_options, handlers, get_status)


def install_fail2ban():
    """Install Fail2ban with auto-detected jail configuration."""
    clear_screen()
    show_header()
    show_panel("Install Fail2ban", title="Fail2ban", style="cyan")
    
    if is_fail2ban_installed():
        show_info("Fail2ban is already installed.")
        
        if is_fail2ban_running():
            console.print("[dim]Service is running.[/dim]")
        else:
            if confirm_action("Start Fail2ban service?"):
                service_control("fail2ban", "start")
                show_success("Fail2ban started!")
        
        press_enter_to_continue()
        return True
    
    # Detect services
    detected = detect_services()
    
    console.print("[bold]Fail2ban will protect against brute force attacks.[/bold]")
    console.print()
    console.print("[bold]Detected services to protect:[/bold]")
    
    if detected['ssh']:
        console.print("  [green]✓[/green] SSH (sshd)")
    if detected['nginx']:
        console.print("  [green]✓[/green] Nginx (http-auth, botsearch)")
    if detected['apache']:
        console.print("  [green]✓[/green] Apache (http-auth)")
    if detected['postfix']:
        console.print("  [green]✓[/green] Postfix (mail)")
    if detected['dovecot']:
        console.print("  [green]✓[/green] Dovecot (imap/pop3)")
    
    if not any(detected.values()):
        console.print("  [dim]No services detected (will enable sshd by default)[/dim]")
    
    console.print()
    console.print(f"[dim]Default settings: bantime={DEFAULT_BANTIME}, maxretry={DEFAULT_MAXRETRY}[/dim]")
    console.print()
    
    if not confirm_action("Install and configure Fail2ban?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return False
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return False
    
    show_info("Installing Fail2ban...")
    
    returncode = run_command_realtime(
        "apt install -y fail2ban",
        "Installing Fail2ban..."
    )
    
    if returncode != 0:
        show_error("Failed to install Fail2ban.")
        press_enter_to_continue()
        return False
    
    # Create local config
    show_info("Configuring Fail2ban...")
    _create_initial_config(detected)
    
    # Start service
    service_control("fail2ban", "start")
    service_control("fail2ban", "enable")
    
    if is_fail2ban_running():
        show_success("Fail2ban installed and running!")
        console.print()
        console.print("[dim]Use Dashboard to see status.[/dim]")
    else:
        show_warning("Fail2ban installed but service may not be running.")
    
    press_enter_to_continue()
    return True


def _create_initial_config(detected_services):
    """Create initial jail.local configuration."""
    config = f"""# Fail2ban local configuration
# Generated by vexo-cli

[DEFAULT]
bantime = {DEFAULT_BANTIME}
findtime = {DEFAULT_FINDTIME}
maxretry = {DEFAULT_MAXRETRY}
banaction = iptables-multiport

"""
    
    # Always enable sshd
    config += """[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 5

"""
    
    if detected_services.get('nginx'):
        config += """[nginx-http-auth]
enabled = true
port = http,https
filter = nginx-http-auth
logpath = /var/log/nginx/error.log

[nginx-botsearch]
enabled = true
port = http,https
filter = nginx-botsearch
logpath = /var/log/nginx/access.log

"""
    
    if detected_services.get('apache'):
        config += """[apache-auth]
enabled = true
port = http,https
filter = apache-auth
logpath = /var/log/apache2/error.log

"""
    
    if detected_services.get('postfix'):
        config += """[postfix]
enabled = true
port = smtp,465,submission
filter = postfix
logpath = /var/log/mail.log

[postfix-sasl]
enabled = true
port = smtp,465,submission
filter = postfix-sasl
logpath = /var/log/mail.log

"""
    
    if detected_services.get('dovecot'):
        config += """[dovecot]
enabled = true
port = pop3,pop3s,imap,imaps
filter = dovecot
logpath = /var/log/mail.log

"""
    
    try:
        with open(JAIL_LOCAL, "w") as f:
            f.write(config)
        return True
    except Exception as e:
        show_error(f"Failed to create config: {e}")
        return False


def configure_global_settings():
    """Configure global ban settings."""
    clear_screen()
    show_header()
    show_panel("Global Ban Settings", title="Settings", style="cyan")
    
    current = _get_current_settings()
    
    console.print("[bold]Current Settings:[/bold]")
    console.print(f"  Ban Time:   {current.get('bantime', DEFAULT_BANTIME)}")
    console.print(f"  Find Time:  {current.get('findtime', DEFAULT_FINDTIME)}")
    console.print(f"  Max Retry:  {current.get('maxretry', DEFAULT_MAXRETRY)}")
    console.print()
    
    bantime = text_input(
        title="Ban Time",
        message="Enter ban time (e.g., 1h, 30m, 1d):",
        default=current.get('bantime', DEFAULT_BANTIME)
    )
    
    if not bantime:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    findtime = text_input(
        title="Find Time",
        message="Enter find time (e.g., 10m, 1h):",
        default=current.get('findtime', DEFAULT_FINDTIME)
    )
    
    if not findtime:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    maxretry = text_input(
        title="Max Retry",
        message="Enter max retry count:",
        default=current.get('maxretry', DEFAULT_MAXRETRY)
    )
    
    if not maxretry:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = _update_settings(bantime, findtime, maxretry)
    
    if success:
        service_control("fail2ban", "reload")
        show_success("Settings updated!")
    else:
        show_error("Failed to update settings.")
    
    press_enter_to_continue()


def configure_recidive():
    """Configure recidive jail for repeat offenders."""
    clear_screen()
    show_header()
    show_panel("Recidive Settings", title="Settings", style="cyan")
    
    show_info("Recidive settings will be implemented in Phase 9.")
    press_enter_to_continue()


def service_control_menu():
    """Service control menu."""
    clear_screen()
    show_header()
    show_panel("Service Control", title="Settings", style="cyan")
    
    if is_fail2ban_running():
        console.print("Status: [green]● Running[/green]")
    else:
        console.print("Status: [red]● Stopped[/red]")
    
    console.print()
    
    options = []
    if is_fail2ban_running():
        options.extend([
            ("stop", "Stop Service"),
            ("restart", "Restart Service"),
            ("reload", "Reload Config"),
        ])
    else:
        options.append(("start", "Start Service"))
    
    from ui.menu import select_from_list
    action = select_from_list(
        title="Service Control",
        message="Select action:",
        options=options
    )
    
    if not action:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    service_control("fail2ban", action)
    show_success(f"Service {action} completed!")
    press_enter_to_continue()


def _get_current_settings():
    """Get current settings from jail.local."""
    settings = {}
    
    if not os.path.exists(JAIL_LOCAL):
        return settings
    
    try:
        with open(JAIL_LOCAL, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('bantime'):
                    settings['bantime'] = line.split('=')[-1].strip()
                elif line.startswith('findtime'):
                    settings['findtime'] = line.split('=')[-1].strip()
                elif line.startswith('maxretry'):
                    settings['maxretry'] = line.split('=')[-1].strip()
    except Exception:
        pass
    
    return settings


def _update_settings(bantime, findtime, maxretry):
    """Update settings in jail.local."""
    try:
        if os.path.exists(JAIL_LOCAL):
            with open(JAIL_LOCAL, 'r') as f:
                lines = f.readlines()
        else:
            lines = ["[DEFAULT]\n"]
        
        new_lines = []
        in_default = False
        updated = {'bantime': False, 'findtime': False, 'maxretry': False}
        
        for line in lines:
            if line.strip() == '[DEFAULT]':
                in_default = True
                new_lines.append(line)
                continue
            elif line.strip().startswith('[') and line.strip() != '[DEFAULT]':
                if in_default:
                    if not updated['bantime']:
                        new_lines.append(f"bantime = {bantime}\n")
                    if not updated['findtime']:
                        new_lines.append(f"findtime = {findtime}\n")
                    if not updated['maxretry']:
                        new_lines.append(f"maxretry = {maxretry}\n")
                in_default = False
            
            if in_default:
                if line.strip().startswith('bantime'):
                    new_lines.append(f"bantime = {bantime}\n")
                    updated['bantime'] = True
                elif line.strip().startswith('findtime'):
                    new_lines.append(f"findtime = {findtime}\n")
                    updated['findtime'] = True
                elif line.strip().startswith('maxretry'):
                    new_lines.append(f"maxretry = {maxretry}\n")
                    updated['maxretry'] = True
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        with open(JAIL_LOCAL, 'w') as f:
            f.writelines(new_lines)
        
        return True
    except Exception as e:
        show_error(f"Error: {e}")
        return False
```

**Step 9: Commit all placeholders**

```bash
git add modules/fail2ban/
git commit -m "feat(fail2ban): add placeholder submodules for all features"
```

---

## Task 4: Remove Old Module and Update Imports

**Files:**
- Delete: `modules/fail2ban.py`
- Modify: `main.py` (if needed)

**Step 1: Delete old module file**

```bash
rm modules/fail2ban.py
```

**Step 2: Verify imports work**

The package `modules/fail2ban/__init__.py` exports `show_menu()` which is the same interface as before.

**Step 3: Commit migration completion**

```bash
git add -A
git commit -m "refactor(fail2ban): complete migration to package structure"
```

---

## Verification

After completing all tasks:

1. Package structure exists:
```
modules/fail2ban/
├── __init__.py
├── common.py
├── dashboard.py
├── jails.py
├── bans.py
├── whitelist.py
├── filters.py
├── history.py
├── notifications.py
├── backup.py
└── settings.py
```

2. Main menu shows new options when fail2ban is installed
3. Dashboard displays stats, top offenders, and recent activity
4. Old `modules/fail2ban.py` is removed
