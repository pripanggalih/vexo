"""Alert settings for vexo."""

import os

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_info,
    show_success,
    press_enter_to_continue,
)
from utils.error_handler import handle_error
from ui.menu import run_menu_loop, text_input, confirm_action, select_from_list
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
        handle_error("E1006", "Invalid number.")
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
        handle_error("E1006", "Invalid number.")
        press_enter_to_continue()
        return
    
    # Validate
    if warning >= critical:
        handle_error("E1006", "Warning threshold must be less than critical threshold.")
        press_enter_to_continue()
        return
    
    if resource != "load_avg" and (warning < 0 or warning > 100 or critical < 0 or critical > 100):
        handle_error("E1006", "Percentage must be between 0 and 100.")
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
            handle_error("E1006", "Retention must be between 1 and 365 days.")
            press_enter_to_continue()
            return
    except ValueError:
        handle_error("E1006", "Invalid number.")
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
            handle_error("E1006", "Interval must be between 10 and 3600 seconds.")
            press_enter_to_continue()
            return
    except ValueError:
        handle_error("E1006", "Invalid number.")
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
        handle_error("E1006", f"Failed to clear logs: {e}")
    
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
            handle_error("E1006", "Failed to log metrics.")
    
    except Exception as e:
        handle_error("E1006", f"Logging test failed: {e}")
    
    press_enter_to_continue()
