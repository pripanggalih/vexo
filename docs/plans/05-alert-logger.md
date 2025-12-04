# Phase 5: Alert Settings & Logger

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add configurable alert thresholds and background logging system that writes system metrics to log files.

**Architecture:** Create alert.py for threshold configuration UI and monitor_logger.py utility for writing metrics to log files. Thresholds stored in JSON config file. Log rotation based on configurable retention period.

**Tech Stack:** Python, psutil (existing), json (stdlib), logging (stdlib)

**Prerequisite:** Complete Phase 1 (monitor package structure)

---

## Task 1: Update Config with Alert Settings

**Files:**
- Modify: `config.py`

**Step 1: Add alert configuration to config.py**

Add after existing THRESHOLDS:

```python
# Alert Thresholds (percentage, can be overridden by user config)
ALERT_THRESHOLDS = {
    "cpu": {"warning": 70, "critical": 90},
    "memory": {"warning": 80, "critical": 95},
    "disk": {"warning": 80, "critical": 90},
    "swap": {"warning": 50, "critical": 80},
    "load_avg": {"warning": 2.0, "critical": 5.0},  # multiplier of CPU cores
}

# Logging Configuration
LOG_CONFIG = {
    "log_dir": "/var/log/vexo",
    "log_file": "monitor.log",
    "retention_days": 7,
    "log_interval": 60,  # seconds between log entries
    "max_log_size_mb": 50,
}

# User config file path
USER_CONFIG_PATH = os.path.expanduser("~/.vexo/config.json")
```

**Step 2: Commit**

```bash
git add config.py
git commit -m "feat(config): add alert thresholds and logging configuration"
```

---

## Task 2: Create Monitor Logger Utility

**Files:**
- Create: `utils/monitor_logger.py`

**Step 1: Create monitor_logger.py**

```python
"""Monitor logging utility for vexo-cli."""

import os
import json
import logging
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

import psutil

from config import ALERT_THRESHOLDS, LOG_CONFIG, USER_CONFIG_PATH


class MonitorLogger:
    """Logger for system monitoring metrics."""
    
    def __init__(self):
        self.log_dir = LOG_CONFIG['log_dir']
        self.log_file = os.path.join(self.log_dir, LOG_CONFIG['log_file'])
        self.retention_days = LOG_CONFIG['retention_days']
        self.thresholds = self._load_thresholds()
        self.logger = self._setup_logger()
    
    def _load_thresholds(self):
        """Load thresholds from user config or use defaults."""
        thresholds = ALERT_THRESHOLDS.copy()
        
        if os.path.exists(USER_CONFIG_PATH):
            try:
                with open(USER_CONFIG_PATH, 'r') as f:
                    user_config = json.load(f)
                    if 'alert_thresholds' in user_config:
                        for key, value in user_config['alert_thresholds'].items():
                            if key in thresholds:
                                thresholds[key].update(value)
            except (json.JSONDecodeError, IOError):
                pass
        
        return thresholds
    
    def _setup_logger(self):
        """Set up the logging handler."""
        # Create log directory if needed
        os.makedirs(self.log_dir, exist_ok=True)
        
        logger = logging.getLogger('vexo_monitor')
        logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        logger.handlers = []
        
        # Rotating file handler (max 50MB, keep 5 backups)
        max_bytes = LOG_CONFIG['max_log_size_mb'] * 1024 * 1024
        handler = RotatingFileHandler(
            self.log_file,
            maxBytes=max_bytes,
            backupCount=5
        )
        
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _get_level(self, value, resource):
        """Determine log level based on threshold."""
        thresholds = self.thresholds.get(resource, {})
        warning = thresholds.get('warning', 70)
        critical = thresholds.get('critical', 90)
        
        if value >= critical:
            return 'CRITICAL'
        elif value >= warning:
            return 'WARNING'
        return 'INFO'
    
    def log_metrics(self):
        """Log current system metrics."""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_level = self._get_level(cpu_percent, 'cpu')
            
            # Memory
            mem = psutil.virtual_memory()
            mem_level = self._get_level(mem.percent, 'memory')
            
            # Disk
            disk = psutil.disk_usage('/')
            disk_level = self._get_level(disk.percent, 'disk')
            
            # Swap
            swap = psutil.swap_memory()
            swap_level = self._get_level(swap.percent, 'swap') if swap.total > 0 else 'INFO'
            
            # Load average (compared to CPU cores)
            try:
                load_1, load_5, load_15 = psutil.getloadavg()
                cpu_count = psutil.cpu_count() or 1
                load_ratio = load_1 / cpu_count
                load_level = self._get_level(load_ratio * 100 / 5, 'load_avg')  # normalize to percentage
            except (AttributeError, OSError):
                load_1 = load_5 = load_15 = 0
                load_level = 'INFO'
            
            # Determine overall level (highest severity)
            levels = [cpu_level, mem_level, disk_level, swap_level, load_level]
            if 'CRITICAL' in levels:
                overall_level = logging.CRITICAL
            elif 'WARNING' in levels:
                overall_level = logging.WARNING
            else:
                overall_level = logging.INFO
            
            # Build log message
            msg = f"CPU: {cpu_percent:.1f}% | MEM: {mem.percent:.1f}% | DISK: {disk.percent:.1f}%"
            if swap.total > 0:
                msg += f" | SWAP: {swap.percent:.1f}%"
            msg += f" | LOAD: {load_1:.2f}/{load_5:.2f}/{load_15:.2f}"
            
            self.logger.log(overall_level, msg)
            
            # Log individual alerts
            if cpu_level == 'CRITICAL':
                self.logger.critical(f"CPU usage {cpu_percent:.1f}% exceeded critical threshold ({self.thresholds['cpu']['critical']}%)")
            elif cpu_level == 'WARNING':
                self.logger.warning(f"CPU usage {cpu_percent:.1f}% exceeded warning threshold ({self.thresholds['cpu']['warning']}%)")
            
            if mem_level == 'CRITICAL':
                self.logger.critical(f"Memory usage {mem.percent:.1f}% exceeded critical threshold ({self.thresholds['memory']['critical']}%)")
            elif mem_level == 'WARNING':
                self.logger.warning(f"Memory usage {mem.percent:.1f}% exceeded warning threshold ({self.thresholds['memory']['warning']}%)")
            
            if disk_level == 'CRITICAL':
                self.logger.critical(f"Disk usage {disk.percent:.1f}% exceeded critical threshold ({self.thresholds['disk']['critical']}%)")
            elif disk_level == 'WARNING':
                self.logger.warning(f"Disk usage {disk.percent:.1f}% exceeded warning threshold ({self.thresholds['disk']['warning']}%)")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to log metrics: {e}")
            return False
    
    def log_event(self, message, level='INFO'):
        """Log a custom event."""
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.log(log_level, message)
    
    def cleanup_old_logs(self):
        """Remove log files older than retention period."""
        try:
            cutoff = datetime.now() - timedelta(days=self.retention_days)
            
            for filename in os.listdir(self.log_dir):
                filepath = os.path.join(self.log_dir, filename)
                if os.path.isfile(filepath):
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if mtime < cutoff:
                        os.remove(filepath)
                        self.logger.info(f"Removed old log file: {filename}")
        
        except Exception as e:
            self.logger.error(f"Failed to cleanup old logs: {e}")
    
    def get_log_stats(self):
        """Get statistics about log files."""
        stats = {
            'log_file': self.log_file,
            'log_dir': self.log_dir,
            'retention_days': self.retention_days,
            'total_size': 0,
            'file_count': 0,
        }
        
        try:
            for filename in os.listdir(self.log_dir):
                filepath = os.path.join(self.log_dir, filename)
                if os.path.isfile(filepath):
                    stats['total_size'] += os.path.getsize(filepath)
                    stats['file_count'] += 1
        except Exception:
            pass
        
        return stats


def save_thresholds(thresholds):
    """Save alert thresholds to user config file."""
    config_dir = os.path.dirname(USER_CONFIG_PATH)
    os.makedirs(config_dir, exist_ok=True)
    
    # Load existing config
    config = {}
    if os.path.exists(USER_CONFIG_PATH):
        try:
            with open(USER_CONFIG_PATH, 'r') as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    config['alert_thresholds'] = thresholds
    
    with open(USER_CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)


def load_thresholds():
    """Load alert thresholds from user config or defaults."""
    thresholds = {k: v.copy() for k, v in ALERT_THRESHOLDS.items()}
    
    if os.path.exists(USER_CONFIG_PATH):
        try:
            with open(USER_CONFIG_PATH, 'r') as f:
                user_config = json.load(f)
                if 'alert_thresholds' in user_config:
                    for key, value in user_config['alert_thresholds'].items():
                        if key in thresholds:
                            thresholds[key].update(value)
        except (json.JSONDecodeError, IOError):
            pass
    
    return thresholds


def save_log_config(log_config):
    """Save log configuration to user config file."""
    config_dir = os.path.dirname(USER_CONFIG_PATH)
    os.makedirs(config_dir, exist_ok=True)
    
    config = {}
    if os.path.exists(USER_CONFIG_PATH):
        try:
            with open(USER_CONFIG_PATH, 'r') as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    config['log_config'] = log_config
    
    with open(USER_CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)


def load_log_config():
    """Load log configuration from user config or defaults."""
    log_config = LOG_CONFIG.copy()
    
    if os.path.exists(USER_CONFIG_PATH):
        try:
            with open(USER_CONFIG_PATH, 'r') as f:
                user_config = json.load(f)
                if 'log_config' in user_config:
                    log_config.update(user_config['log_config'])
        except (json.JSONDecodeError, IOError):
            pass
    
    return log_config
```

**Step 2: Commit**

```bash
git add utils/monitor_logger.py
git commit -m "feat(utils): add monitor logging utility"
```

---

## Task 3: Create Alert Settings Module

**Files:**
- Create: `modules/monitor/alert.py`

**Step 1: Create alert.py**

```python
"""Alert settings for vexo-cli."""

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_info,
    show_success,
    show_error,
    press_enter_to_continue,
)
from ui.menu import run_menu_loop, text_input, confirm_action
from utils.monitor_logger import (
    load_thresholds,
    save_thresholds,
    load_log_config,
    save_log_config,
    MonitorLogger,
)
from modules.monitor.common import format_bytes


def show_menu():
    """Display the Alert Settings submenu."""
    options = [
        ("thresholds", "1. Configure Thresholds"),
        ("logging", "2. Log Settings"),
        ("test", "3. Test Logging"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "thresholds": show_threshold_settings,
        "logging": show_log_settings,
        "test": test_logging,
    }
    
    run_menu_loop("Alert Settings", options, handlers)


def show_threshold_settings():
    """Display and edit alert thresholds."""
    clear_screen()
    show_header()
    show_panel("Alert Thresholds", title="Alert Settings", style="cyan")
    
    thresholds = load_thresholds()
    
    columns = [
        {"name": "Resource", "style": "cyan"},
        {"name": "Warning", "justify": "right"},
        {"name": "Critical", "justify": "right"},
    ]
    
    rows = [
        ["CPU", f"{thresholds['cpu']['warning']}%", f"{thresholds['cpu']['critical']}%"],
        ["Memory", f"{thresholds['memory']['warning']}%", f"{thresholds['memory']['critical']}%"],
        ["Disk", f"{thresholds['disk']['warning']}%", f"{thresholds['disk']['critical']}%"],
        ["Swap", f"{thresholds['swap']['warning']}%", f"{thresholds['swap']['critical']}%"],
        ["Load Avg", f"{thresholds['load_avg']['warning']}x cores", f"{thresholds['load_avg']['critical']}x cores"],
    ]
    
    show_table("Current Thresholds", columns, rows)
    
    console.print()
    console.print("[dim]Status: [green]● Good (below warning)[/green] | [yellow]● Warning[/yellow] | [red]● Critical[/red][/dim]")
    console.print()
    
    # Edit menu
    edit_options = [
        ("cpu", "Edit CPU thresholds"),
        ("memory", "Edit Memory thresholds"),
        ("disk", "Edit Disk thresholds"),
        ("swap", "Edit Swap thresholds"),
        ("load", "Edit Load Average thresholds"),
        ("reset", "Reset to defaults"),
        ("back", "← Back"),
    ]
    
    from ui.menu import select_from_list
    
    choice = select_from_list(
        "Edit Thresholds",
        "Select resource to edit:",
        [label for _, label in edit_options],
        allow_cancel=False
    )
    
    if not choice or choice == "← Back":
        return
    
    if choice == "Reset to defaults":
        if confirm_action("Reset all thresholds to default values?"):
            from config import ALERT_THRESHOLDS
            save_thresholds(ALERT_THRESHOLDS)
            show_success("Thresholds reset to defaults.")
        press_enter_to_continue()
        return
    
    # Map to resource key
    resource_map = {
        "Edit CPU thresholds": "cpu",
        "Edit Memory thresholds": "memory",
        "Edit Disk thresholds": "disk",
        "Edit Swap thresholds": "swap",
        "Edit Load Average thresholds": "load_avg",
    }
    
    resource = resource_map.get(choice)
    if resource:
        _edit_threshold(resource, thresholds)


def _edit_threshold(resource, thresholds):
    """Edit threshold for a specific resource."""
    current = thresholds[resource]
    
    console.print(f"\n[bold]Editing {resource.upper()} thresholds[/bold]")
    console.print(f"[dim]Current: Warning={current['warning']}, Critical={current['critical']}[/dim]\n")
    
    unit = "x cores" if resource == "load_avg" else "%"
    
    # Warning threshold
    warning_input = text_input(
        f"Warning threshold ({unit}):",
        default=str(current['warning'])
    )
    if not warning_input:
        return
    
    try:
        warning = float(warning_input)
    except ValueError:
        show_error("Invalid number.")
        press_enter_to_continue()
        return
    
    # Critical threshold
    critical_input = text_input(
        f"Critical threshold ({unit}):",
        default=str(current['critical'])
    )
    if not critical_input:
        return
    
    try:
        critical = float(critical_input)
    except ValueError:
        show_error("Invalid number.")
        press_enter_to_continue()
        return
    
    # Validate
    if warning >= critical:
        show_error("Warning threshold must be less than critical threshold.")
        press_enter_to_continue()
        return
    
    if resource != "load_avg" and (warning < 0 or warning > 100 or critical < 0 or critical > 100):
        show_error("Percentage must be between 0 and 100.")
        press_enter_to_continue()
        return
    
    # Save
    thresholds[resource]['warning'] = warning
    thresholds[resource]['critical'] = critical
    save_thresholds(thresholds)
    
    show_success(f"{resource.upper()} thresholds updated: Warning={warning}{unit}, Critical={critical}{unit}")
    press_enter_to_continue()


def show_log_settings():
    """Display and edit log settings."""
    clear_screen()
    show_header()
    show_panel("Log Settings", title="Alert Settings", style="cyan")
    
    log_config = load_log_config()
    
    # Get log stats
    try:
        logger = MonitorLogger()
        stats = logger.get_log_stats()
    except Exception:
        stats = {'total_size': 0, 'file_count': 0}
    
    console.print(f"[bold]Log Directory:[/bold] {log_config['log_dir']}")
    console.print(f"[bold]Log File:[/bold] {log_config['log_file']}")
    console.print(f"[bold]Retention:[/bold] {log_config['retention_days']} days")
    console.print(f"[bold]Log Interval:[/bold] {log_config['log_interval']} seconds")
    console.print(f"[bold]Max Log Size:[/bold] {log_config['max_log_size_mb']} MB")
    console.print()
    console.print(f"[bold]Current Size:[/bold] {format_bytes(stats['total_size'])}")
    console.print(f"[bold]Log Files:[/bold] {stats['file_count']}")
    console.print()
    
    from ui.menu import select_from_list
    
    options = [
        "Change retention period",
        "Change log interval",
        "Clear logs",
        "← Back",
    ]
    
    choice = select_from_list("Log Settings", "Select option:", options, allow_cancel=False)
    
    if not choice or choice == "← Back":
        return
    
    if choice == "Change retention period":
        _edit_retention(log_config)
    elif choice == "Change log interval":
        _edit_interval(log_config)
    elif choice == "Clear logs":
        _clear_logs(log_config)


def _edit_retention(log_config):
    """Edit log retention period."""
    console.print(f"\n[dim]Current retention: {log_config['retention_days']} days[/dim]")
    
    days_input = text_input("Retention period (days):", default=str(log_config['retention_days']))
    if not days_input:
        return
    
    try:
        days = int(days_input)
        if days < 1 or days > 365:
            show_error("Retention must be between 1 and 365 days.")
            press_enter_to_continue()
            return
    except ValueError:
        show_error("Invalid number.")
        press_enter_to_continue()
        return
    
    log_config['retention_days'] = days
    save_log_config(log_config)
    
    show_success(f"Retention period set to {days} days.")
    press_enter_to_continue()


def _edit_interval(log_config):
    """Edit log interval."""
    console.print(f"\n[dim]Current interval: {log_config['log_interval']} seconds[/dim]")
    
    interval_input = text_input("Log interval (seconds):", default=str(log_config['log_interval']))
    if not interval_input:
        return
    
    try:
        interval = int(interval_input)
        if interval < 10 or interval > 3600:
            show_error("Interval must be between 10 and 3600 seconds.")
            press_enter_to_continue()
            return
    except ValueError:
        show_error("Invalid number.")
        press_enter_to_continue()
        return
    
    log_config['log_interval'] = interval
    save_log_config(log_config)
    
    show_success(f"Log interval set to {interval} seconds.")
    press_enter_to_continue()


def _clear_logs(log_config):
    """Clear all log files."""
    if not confirm_action("Clear all monitor logs? This cannot be undone."):
        show_info("Cancelled.")
        press_enter_to_continue()
        return
    
    import os
    
    try:
        log_dir = log_config['log_dir']
        count = 0
        
        for filename in os.listdir(log_dir):
            if filename.startswith('monitor'):
                filepath = os.path.join(log_dir, filename)
                os.remove(filepath)
                count += 1
        
        show_success(f"Cleared {count} log file(s).")
    except Exception as e:
        show_error(f"Failed to clear logs: {e}")
    
    press_enter_to_continue()


def test_logging():
    """Test the logging system."""
    clear_screen()
    show_header()
    show_panel("Test Logging", title="Alert Settings", style="cyan")
    
    console.print("[dim]Testing monitor logging...[/dim]\n")
    
    try:
        logger = MonitorLogger()
        
        # Log current metrics
        success = logger.log_metrics()
        
        if success:
            show_success("Metrics logged successfully!")
            console.print(f"\n[dim]Log file: {logger.log_file}[/dim]")
            
            # Show last few lines
            console.print("\n[bold]Last log entries:[/bold]")
            try:
                with open(logger.log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-5:]:
                        console.print(f"[dim]{line.rstrip()}[/dim]")
            except Exception:
                pass
        else:
            show_error("Failed to log metrics.")
    
    except Exception as e:
        show_error(f"Logging test failed: {e}")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/monitor/alert.py
git commit -m "feat(monitor): add alert settings configuration"
```

---

## Task 4: Wire Up Alert Menu

**Files:**
- Modify: `modules/monitor/__init__.py`

**Step 1: Update __init__.py to import alert module**

```python
"""System monitoring module for vexo-cli."""

from ui.menu import run_menu_loop

from modules.monitor.dashboard import show_dashboard
from modules.monitor.cpu import show_cpu_details
from modules.monitor.memory import show_ram_details
from modules.monitor.disk import show_disk_details
from modules.monitor.network import show_menu as show_network_menu
from modules.monitor.process import show_menu as show_process_menu
from modules.monitor.service import show_menu as show_service_menu
from modules.monitor.alert import show_menu as show_alert_menu


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
        "service": show_service_menu,
        "alert": show_alert_menu,
        # Phase 6 handler will be added later
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
git commit -m "feat(monitor): wire up alert settings menu"
```

---

## Summary

After Phase 5, the alert & logging system will have:

- **Alert Thresholds:**
  - Configure warning/critical thresholds for CPU, Memory, Disk, Swap, Load Average
  - User config stored in `~/.vexo/config.json`
  - Reset to defaults option

- **Log Settings:**
  - View current log configuration
  - Change retention period (1-365 days)
  - Change log interval (10-3600 seconds)
  - Clear logs

- **Monitor Logger:**
  - Logs to `/var/log/vexo/monitor.log`
  - Rotating log files (max 50MB, 5 backups)
  - Automatic log level based on thresholds
  - Cleanup old logs based on retention

- **Test Logging:**
  - Manual test to verify logging works
  - Shows last log entries

Files added/modified:
- `config.py` (updated)
- `utils/monitor_logger.py` (new)
- `modules/monitor/alert.py` (new)
- `modules/monitor/__init__.py` (updated)
