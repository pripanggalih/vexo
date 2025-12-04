"""Service monitoring for vexo."""

import re
from collections import defaultdict

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
from ui.menu import run_menu_loop, confirm_action, select_from_list, text_input
from utils.shell import run_command


# Predefined vexo-managed services
VEXO_SERVICES = [
    'nginx',
    'apache2',
    'mysql',
    'mariadb',
    'postgresql',
    'redis-server',
    'memcached',
    'php*-fpm',  # php7.4-fpm, php8.1-fpm, etc.
    'postfix',
    'dovecot',
    'fail2ban',
    'ufw',
    'ssh',
    'cron',
]


def show_menu():
    """Display the Service Status submenu."""
    options = [
        ("all", "1. All Services"),
        ("vexo", "2. Vexo Services Only"),
        ("failed", "3. Failed Services"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "all": show_all_services,
        "vexo": show_vexo_services,
        "failed": show_failed_services,
    }
    
    run_menu_loop("Service Status", options, handlers)


def get_systemd_services():
    """
    Get all systemd services with their status.
    
    Returns:
        list: List of service dicts
    """
    services = []
    
    try:
        result = run_command(
            "systemctl list-units --type=service --all --no-pager --plain",
            check=False,
            silent=True
        )
        
        if result.returncode != 0:
            return services
        
        lines = result.stdout.strip().split('\n')
        
        for line in lines:
            if not line or line.startswith('UNIT') or line.startswith(' '):
                continue
            
            parts = line.split()
            if len(parts) < 4:
                continue
            
            unit = parts[0]
            if not unit.endswith('.service'):
                continue
            
            name = unit.replace('.service', '')
            load = parts[1] if len(parts) > 1 else '-'
            active = parts[2] if len(parts) > 2 else '-'
            sub = parts[3] if len(parts) > 3 else '-'
            description = ' '.join(parts[4:]) if len(parts) > 4 else ''
            
            services.append({
                'name': name,
                'load': load,
                'active': active,
                'sub': sub,
                'description': description[:40],
            })
    
    except Exception:
        pass
    
    return services


def get_service_details(service_name):
    """
    Get detailed status of a specific service.
    
    Args:
        service_name: Name of the service
    
    Returns:
        dict: Service details or None if not found
    """
    details = {
        'name': service_name,
        'active': '-',
        'enabled': '-',
        'running': False,
        'pid': '-',
        'memory': '-',
        'uptime': '-',
        'description': '-',
    }
    
    try:
        # Get active state
        result = run_command(
            f"systemctl is-active {service_name}",
            check=False,
            silent=True
        )
        details['active'] = result.stdout.strip()
        details['running'] = details['active'] == 'active'
        
        # Get enabled state
        result = run_command(
            f"systemctl is-enabled {service_name}",
            check=False,
            silent=True
        )
        details['enabled'] = result.stdout.strip()
        
        # Get detailed status
        result = run_command(
            f"systemctl show {service_name} --property=MainPID,MemoryCurrent,Description,ActiveEnterTimestamp",
            check=False,
            silent=True
        )
        
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    if key == 'MainPID':
                        details['pid'] = value if value != '0' else '-'
                    elif key == 'MemoryCurrent':
                        if value and value != '[not set]':
                            try:
                                mem_bytes = int(value)
                                if mem_bytes > 0:
                                    details['memory'] = _format_memory(mem_bytes)
                            except ValueError:
                                pass
                    elif key == 'Description':
                        details['description'] = value[:50]
                    elif key == 'ActiveEnterTimestamp':
                        details['uptime'] = _parse_timestamp(value)
    
    except Exception:
        pass
    
    return details


def _format_memory(bytes_value):
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_value < 1024:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024
    return f"{bytes_value:.1f} TB"


def _parse_timestamp(timestamp_str):
    """Parse systemd timestamp to relative time."""
    if not timestamp_str or timestamp_str == 'n/a':
        return '-'
    
    try:
        from datetime import datetime
        # Format: "Wed 2024-01-15 10:30:00 UTC"
        parts = timestamp_str.split()
        if len(parts) >= 3:
            date_str = f"{parts[1]} {parts[2]}"
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            delta = datetime.now() - dt
            
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
        pass
    
    return '-'


def _match_service_pattern(service_name, pattern):
    """Check if service name matches pattern (supports *)."""
    if '*' in pattern:
        regex = pattern.replace('*', '.*')
        return bool(re.match(f'^{regex}$', service_name))
    return service_name == pattern


def filter_vexo_services(all_services):
    """Filter services to only vexo-managed ones."""
    vexo = []
    for svc in all_services:
        for pattern in VEXO_SERVICES:
            if _match_service_pattern(svc['name'], pattern):
                vexo.append(svc)
                break
    return vexo


# =============================================================================
# Service List Views
# =============================================================================

def _display_services(services, title):
    """Display a list of services in a table."""
    if not services:
        show_info("No services found.")
        press_enter_to_continue()
        return
    
    # Count by status
    active_count = sum(1 for s in services if s['active'] == 'active')
    inactive_count = sum(1 for s in services if s['active'] == 'inactive')
    failed_count = sum(1 for s in services if s['active'] == 'failed')
    
    console.print(f"[bold]Total:[/bold] {len(services)} services")
    console.print(f"[green]● Active: {active_count}[/green] | [dim]○ Inactive: {inactive_count}[/dim] | [red]● Failed: {failed_count}[/red]")
    console.print()
    
    columns = [
        {"name": "Service", "style": "cyan"},
        {"name": "Status", "justify": "center"},
        {"name": "State"},
        {"name": "Description"},
    ]
    
    rows = []
    for svc in services[:30]:
        if svc['active'] == 'active':
            status = "[green]● active[/green]"
        elif svc['active'] == 'failed':
            status = "[red]● failed[/red]"
        else:
            status = "[dim]○ inactive[/dim]"
        
        rows.append([
            svc['name'],
            status,
            svc['sub'],
            svc['description'][:30],
        ])
    
    show_table(title, columns, rows)
    
    if len(services) > 30:
        console.print(f"[dim]... and {len(services) - 30} more services[/dim]")
    
    console.print()
    console.print("[dim]Enter service name to manage, or press Enter to go back[/dim]")
    
    service_input = text_input("Service name (or Enter to skip):", default="")
    if service_input:
        show_service_actions(service_input)


def show_all_services():
    """Display all systemd services."""
    clear_screen()
    show_header()
    show_panel("All Services", title="Service Status", style="cyan")
    
    services = get_systemd_services()
    _display_services(services, f"{len(services)} systemd services")


def show_vexo_services():
    """Display vexo-managed services."""
    clear_screen()
    show_header()
    show_panel("Vexo Services", title="Service Status", style="cyan")
    
    all_services = get_systemd_services()
    vexo_services = filter_vexo_services(all_services)
    
    # Also add services that might not be running but are in VEXO_SERVICES
    existing_names = {s['name'] for s in vexo_services}
    for pattern in VEXO_SERVICES:
        if '*' not in pattern and pattern not in existing_names:
            # Check if service exists
            details = get_service_details(pattern)
            if details and details['active'] != '-':
                vexo_services.append({
                    'name': pattern,
                    'load': 'loaded',
                    'active': details['active'],
                    'sub': details['enabled'],
                    'description': details['description'],
                })
    
    _display_services(vexo_services, "Vexo-managed services")


def show_failed_services():
    """Display failed services."""
    clear_screen()
    show_header()
    show_panel("Failed Services", title="Service Status", style="cyan")
    
    services = get_systemd_services()
    failed = [s for s in services if s['active'] == 'failed']
    
    if not failed:
        show_success("No failed services found!")
        press_enter_to_continue()
        return
    
    _display_services(failed, f"{len(failed)} failed services")


# =============================================================================
# Service Actions
# =============================================================================

def show_service_actions(service_name):
    """Display service details and action menu."""
    clear_screen()
    show_header()
    
    details = get_service_details(service_name)
    
    if details['active'] == '-':
        show_error(f"Service '{service_name}' not found.")
        press_enter_to_continue()
        return
    
    show_panel(f"Service: {service_name}", title="Service Status", style="cyan")
    
    # Show details
    status_color = "green" if details['running'] else "red"
    enabled_color = "green" if details['enabled'] == 'enabled' else "dim"
    
    console.print(f"[bold]Status:[/bold] [{status_color}]{details['active']}[/{status_color}]")
    console.print(f"[bold]Enabled:[/bold] [{enabled_color}]{details['enabled']}[/{enabled_color}]")
    console.print(f"[bold]PID:[/bold] {details['pid']}")
    console.print(f"[bold]Memory:[/bold] {details['memory']}")
    console.print(f"[bold]Uptime:[/bold] {details['uptime']}")
    console.print(f"[bold]Description:[/bold] {details['description']}")
    console.print()
    
    # Action menu based on current state
    if details['running']:
        actions = [
            ("stop", "1. Stop Service"),
            ("restart", "2. Restart Service"),
            ("reload", "3. Reload Configuration"),
            ("logs", "4. View Logs"),
        ]
    else:
        actions = [
            ("start", "1. Start Service"),
            ("logs", "2. View Logs"),
        ]
    
    # Add enable/disable based on current state
    if details['enabled'] == 'enabled':
        actions.append(("disable", f"{len(actions)+1}. Disable AutoStart"))
    else:
        actions.append(("enable", f"{len(actions)+1}. Enable AutoStart"))
    
    actions.append(("back", "← Back"))
    
    action_labels = [label for _, label in actions]
    action_keys = [key for key, _ in actions]
    
    choice = select_from_list(
        "Service Actions",
        "Select action:",
        action_labels,
        allow_cancel=False
    )
    
    if not choice or choice == "← Back":
        return
    
    # Map label back to key
    action_idx = action_labels.index(choice)
    action = action_keys[action_idx]
    
    if action == "start":
        _service_control(service_name, "start")
    elif action == "stop":
        _service_control(service_name, "stop")
    elif action == "restart":
        _service_control(service_name, "restart")
    elif action == "reload":
        _service_control(service_name, "reload")
    elif action == "enable":
        _service_control(service_name, "enable")
    elif action == "disable":
        _service_control(service_name, "disable")
    elif action == "logs":
        _view_service_logs(service_name)


def _service_control(service_name, action):
    """Execute service control action."""
    action_names = {
        "start": "Start",
        "stop": "Stop",
        "restart": "Restart",
        "reload": "Reload",
        "enable": "Enable",
        "disable": "Disable",
    }
    
    action_display = action_names.get(action, action)
    
    if not confirm_action(f"{action_display} service '{service_name}'?"):
        show_info("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        result = run_command(
            f"systemctl {action} {service_name}",
            check=False,
            silent=True
        )
        
        if result.returncode == 0:
            show_success(f"Service {service_name} {action}ed successfully.")
        else:
            show_error(f"Failed to {action} service: {result.stderr}")
    
    except Exception as e:
        show_error(f"Error: {e}")
    
    press_enter_to_continue()


def _view_service_logs(service_name, lines=50):
    """View recent logs for a service."""
    clear_screen()
    show_header()
    show_panel(f"Logs: {service_name}", title="Service Status", style="cyan")
    
    try:
        result = run_command(
            f"journalctl -u {service_name} -n {lines} --no-pager",
            check=False,
            silent=True
        )
        
        if result.returncode == 0 and result.stdout:
            console.print(f"[dim]Last {lines} log entries:[/dim]\n")
            
            for line in result.stdout.strip().split('\n')[-30:]:
                # Color code log levels
                if 'error' in line.lower() or 'failed' in line.lower():
                    console.print(f"[red]{line}[/red]")
                elif 'warning' in line.lower() or 'warn' in line.lower():
                    console.print(f"[yellow]{line}[/yellow]")
                else:
                    console.print(f"[dim]{line}[/dim]")
        else:
            show_info("No logs available or access denied.")
    
    except Exception as e:
        show_error(f"Failed to retrieve logs: {e}")
    
    press_enter_to_continue()
