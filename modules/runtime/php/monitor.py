"""PHP monitoring and troubleshooting tools."""

import os
import re
from datetime import datetime

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, service_control, require_root
from modules.runtime.php.utils import (
    get_installed_php_versions, get_fpm_service_name, is_fpm_running,
    get_fpm_pool_path, parse_fpm_pool_config,
)


# Log paths
PHP_FPM_LOG = "/var/log/php{version}-fpm.log"
PHP_ERROR_LOG = "/var/log/php{version}-fpm.log"
PHP_SLOW_LOG = "/var/log/php{version}-fpm.slow.log"


def show_monitor_menu():
    """Display Monitoring & Logs submenu."""
    options = [
        ("status", "1. FPM Status Page"),
        ("error", "2. Error Log Viewer"),
        ("slow", "3. Slow Log Viewer"),
        ("process", "4. Process Monitor"),
        ("health", "5. Health Check"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "status": fpm_status_page,
        "error": error_log_viewer,
        "slow": slow_log_viewer,
        "process": process_monitor,
        "health": health_check,
    }
    
    run_menu_loop("Monitoring & Logs", options, handlers)


def fpm_status_page():
    """View real-time PHP-FPM status via status page."""
    clear_screen()
    show_header()
    show_panel("FPM Status Page", title="Monitoring", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "View status for:", versions)
    if not version:
        return
    
    if not is_fpm_running(version):
        show_error(f"PHP {version} FPM is not running.")
        press_enter_to_continue()
        return
    
    # Check if status page is enabled in pool config
    config = parse_fpm_pool_config(version)
    status_path = config.get("pm.status_path", "")
    
    if not status_path:
        show_warning("FPM status page is not enabled.")
        console.print()
        if confirm_action("Enable FPM status page?"):
            _enable_fpm_status(version)
        else:
            press_enter_to_continue()
            return
    
    # Try to get status via FPM socket
    socket_path = f"/run/php/php{version}-fpm.sock"
    
    console.print(f"[bold]PHP {version} FPM Status:[/bold]")
    console.print()
    
    # Use cgi-fcgi if available, otherwise parse from process info
    result = run_command(
        f"SCRIPT_NAME=/fpm-status SCRIPT_FILENAME=/fpm-status REQUEST_METHOD=GET "
        f"cgi-fcgi -bind -connect {socket_path} 2>/dev/null | tail -n +5",
        check=False, silent=True
    )
    
    if result.returncode == 0 and result.stdout.strip():
        # Parse status output
        for line in result.stdout.strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Colorize some values
                if key == "active processes" and int(value) > 0:
                    value = f"[green]{value}[/green]"
                elif key == "idle processes":
                    value = f"[cyan]{value}[/cyan]"
                elif "slow requests" in key.lower() and int(value) > 0:
                    value = f"[yellow]{value}[/yellow]"
                
                console.print(f"  {key}: {value}")
    else:
        # Fallback to basic process info
        show_info("cgi-fcgi not available, showing basic info...")
        console.print()
        
        # Count processes
        result = run_command(
            f"pgrep -fa 'php-fpm.*{version}' | wc -l",
            check=False, silent=True
        )
        total = result.stdout.strip() if result.returncode == 0 else "?"
        
        result = run_command(
            f"pgrep -fa 'php-fpm: pool www.*{version}' | wc -l",
            check=False, silent=True
        )
        workers = result.stdout.strip() if result.returncode == 0 else "?"
        
        console.print(f"  Total FPM processes: {total}")
        console.print(f"  Worker processes: {workers}")
        console.print(f"  Max children: {config.get('pm.max_children', '?')}")
        console.print(f"  PM mode: {config.get('pm', 'dynamic')}")
    
    press_enter_to_continue()


def _enable_fpm_status(version):
    """Enable FPM status page in pool config."""
    try:
        require_root()
    except PermissionError:
        return
    
    pool_path = get_fpm_pool_path(version)
    
    try:
        with open(pool_path, "r") as f:
            content = f.read()
        
        # Add or uncomment pm.status_path
        if "pm.status_path" not in content or ";pm.status_path" in content:
            content = re.sub(
                r'^;?\s*pm\.status_path\s*=.*$',
                'pm.status_path = /fpm-status',
                content,
                flags=re.MULTILINE
            )
            
            # If not found, add it
            if "pm.status_path = /fpm-status" not in content:
                content = content.rstrip() + "\npm.status_path = /fpm-status\n"
        
        with open(pool_path, "w") as f:
            f.write(content)
        
        service_control(get_fpm_service_name(version), "restart")
        show_success("FPM status page enabled!")
        console.print(f"[dim]Status path: /fpm-status[/dim]")
    except Exception as e:
        show_error(f"Failed to enable status page: {e}")


def error_log_viewer():
    """View PHP error logs."""
    clear_screen()
    show_header()
    show_panel("Error Log Viewer", title="Monitoring", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "View logs for:", versions)
    if not version:
        return
    
    # Find log file
    log_paths = [
        f"/var/log/php{version}-fpm.log",
        f"/var/log/php-fpm/php{version}-fpm.log",
        "/var/log/php-fpm.log",
    ]
    
    log_path = None
    for path in log_paths:
        if os.path.exists(path):
            log_path = path
            break
    
    if not log_path:
        show_error("Log file not found.")
        console.print(f"[dim]Checked: {', '.join(log_paths)}[/dim]")
        press_enter_to_continue()
        return
    
    # Options
    options = ["Last 50 lines", "Last 100 lines", "Search pattern", "Errors only"]
    choice = select_from_list("View Mode", "How to view?", options)
    if not choice:
        return
    
    clear_screen()
    show_header()
    show_panel(f"PHP {version} Error Log", title="Monitoring", style="cyan")
    console.print(f"[dim]Log: {log_path}[/dim]")
    console.print()
    
    if choice == "Last 50 lines":
        result = run_command(f"tail -n 50 {log_path}", check=False, silent=True)
    elif choice == "Last 100 lines":
        result = run_command(f"tail -n 100 {log_path}", check=False, silent=True)
    elif choice == "Search pattern":
        pattern = text_input("Enter search pattern:")
        if not pattern:
            return
        result = run_command(f"grep -i '{pattern}' {log_path} | tail -n 50", check=False, silent=True)
    else:  # Errors only
        result = run_command(f"grep -iE '(error|fatal|critical)' {log_path} | tail -n 50", check=False, silent=True)
    
    if result.returncode == 0 and result.stdout.strip():
        # Colorize output
        for line in result.stdout.split('\n'):
            if 'error' in line.lower() or 'fatal' in line.lower():
                console.print(f"[red]{line}[/red]")
            elif 'warning' in line.lower():
                console.print(f"[yellow]{line}[/yellow]")
            elif 'notice' in line.lower():
                console.print(f"[dim]{line}[/dim]")
            else:
                console.print(line)
    else:
        show_info("No log entries found.")
    
    press_enter_to_continue()


def slow_log_viewer():
    """View and analyze PHP slow request logs."""
    clear_screen()
    show_header()
    show_panel("Slow Log Viewer", title="Monitoring", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "View slow log for:", versions)
    if not version:
        return
    
    # Check slow log configuration
    config = parse_fpm_pool_config(version)
    slowlog = config.get("slowlog", "")
    timeout = config.get("request_slowlog_timeout", "0")
    
    console.print(f"[bold]Slow Log Configuration:[/bold]")
    console.print(f"  Slowlog path: {slowlog or '(not set)'}")
    console.print(f"  Timeout: {timeout}")
    console.print()
    
    if timeout == "0" or not timeout:
        show_warning("Slow logging is disabled.")
        if confirm_action("Enable slow logging (5s threshold)?"):
            _enable_slow_log(version)
        else:
            press_enter_to_continue()
            return
    
    # Find slow log file
    log_paths = [
        slowlog,
        f"/var/log/php{version}-fpm.slow.log",
        f"/var/log/php-fpm/slow.log",
    ]
    
    log_path = None
    for path in log_paths:
        if path and os.path.exists(path):
            log_path = path
            break
    
    if not log_path or not os.path.exists(log_path):
        show_info("Slow log file not found or empty.")
        console.print("[dim]Slow requests will be logged after threshold is exceeded.[/dim]")
        press_enter_to_continue()
        return
    
    clear_screen()
    show_header()
    show_panel(f"PHP {version} Slow Log", title="Monitoring", style="cyan")
    console.print(f"[dim]Log: {log_path}[/dim]")
    console.print()
    
    # Parse slow log
    result = run_command(f"tail -n 200 {log_path}", check=False, silent=True)
    
    if result.returncode == 0 and result.stdout.strip():
        # Count slow requests by script
        scripts = {}
        current_script = None
        
        for line in result.stdout.split('\n'):
            if line.startswith('['):
                # New entry
                current_script = None
            elif 'script_filename' in line.lower():
                match = re.search(r'script_filename\s*=\s*(.+)', line, re.IGNORECASE)
                if match:
                    current_script = match.group(1).strip()
                    scripts[current_script] = scripts.get(current_script, 0) + 1
        
        if scripts:
            console.print("[bold]Slow Scripts (by frequency):[/bold]")
            console.print()
            for script, count in sorted(scripts.items(), key=lambda x: x[1], reverse=True)[:10]:
                script_display = script[-60:] if len(script) > 60 else script
                console.print(f"  [yellow]{count}x[/yellow] {script_display}")
        else:
            console.print("[dim]No slow requests recorded yet.[/dim]")
    else:
        show_info("Slow log is empty.")
    
    press_enter_to_continue()


def _enable_slow_log(version):
    """Enable slow request logging."""
    try:
        require_root()
    except PermissionError:
        return
    
    pool_path = get_fpm_pool_path(version)
    slow_log_path = f"/var/log/php{version}-fpm.slow.log"
    
    try:
        with open(pool_path, "r") as f:
            content = f.read()
        
        # Update slowlog settings
        settings = {
            "slowlog": slow_log_path,
            "request_slowlog_timeout": "5s",
        }
        
        for key, value in settings.items():
            pattern = rf'^;?\s*{key}\s*=.*$'
            replacement = f"{key} = {value}"
            new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
            if count == 0:
                content = content.rstrip() + f"\n{key} = {value}\n"
            else:
                content = new_content
        
        with open(pool_path, "w") as f:
            f.write(content)
        
        # Create log file
        open(slow_log_path, 'a').close()
        run_command(f"chown www-data:www-data {slow_log_path}", check=False, silent=True)
        
        service_control(get_fpm_service_name(version), "restart")
        show_success("Slow logging enabled (5s threshold)!")
    except Exception as e:
        show_error(f"Failed to enable slow logging: {e}")


def process_monitor():
    """Monitor PHP-FPM processes in real-time."""
    clear_screen()
    show_header()
    show_panel("Process Monitor", title="Monitoring", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "Monitor processes for:", versions)
    if not version:
        return
    
    if not is_fpm_running(version):
        show_error(f"PHP {version} FPM is not running.")
        press_enter_to_continue()
        return
    
    clear_screen()
    show_header()
    show_panel(f"PHP {version} Processes", title="Monitoring", style="cyan")
    
    # Get process info
    result = run_command(
        f"ps aux | grep 'php-fpm.*{version}' | grep -v grep",
        check=False, silent=True
    )
    
    if result.returncode != 0 or not result.stdout.strip():
        show_info("No FPM processes found.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "PID", "style": "cyan", "justify": "right"},
        {"name": "User", "style": "white"},
        {"name": "CPU%", "justify": "right"},
        {"name": "MEM%", "justify": "right"},
        {"name": "RSS (MB)", "justify": "right"},
        {"name": "Status"},
    ]
    
    rows = []
    total_rss = 0
    
    for line in result.stdout.strip().split('\n'):
        parts = line.split()
        if len(parts) >= 11:
            user = parts[0]
            pid = parts[1]
            cpu = parts[2]
            mem = parts[3]
            rss_kb = int(parts[5]) if parts[5].isdigit() else 0
            rss_mb = rss_kb / 1024
            total_rss += rss_mb
            
            # Determine status from command
            if "master" in line:
                status = "[cyan]master[/cyan]"
            elif "pool" in line:
                status = "[green]worker[/green]"
            else:
                status = "[dim]unknown[/dim]"
            
            rows.append([pid, user, cpu, mem, f"{rss_mb:.1f}", status])
    
    show_table(f"Total: {len(rows)} processes, {total_rss:.1f} MB RSS", columns, rows, show_header=True)
    
    console.print()
    console.print("[dim]Press Enter to refresh, or 'q' to quit[/dim]")
    
    # Option to kill a process
    console.print()
    if confirm_action("Kill a stuck process?"):
        pid = text_input("Enter PID to kill:")
        if pid and pid.isdigit():
            try:
                require_root()
                result = run_command(f"kill -9 {pid}", check=False, silent=True)
                if result.returncode == 0:
                    show_success(f"Process {pid} killed.")
                else:
                    show_error(f"Failed to kill process {pid}.")
            except PermissionError:
                pass
    
    press_enter_to_continue()


def health_check():
    """Run PHP health check diagnostics."""
    clear_screen()
    show_header()
    show_panel("PHP Health Check", title="Monitoring", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "Health check for:", versions)
    if not version:
        return
    
    clear_screen()
    show_header()
    show_panel(f"PHP {version} Health Check", title="Monitoring", style="cyan")
    
    checks = []
    
    # Check 1: FPM running
    fpm_running = is_fpm_running(version)
    checks.append(("FPM Service", fpm_running, "Running" if fpm_running else "Stopped"))
    
    # Check 2: FPM socket exists
    socket = f"/run/php/php{version}-fpm.sock"
    socket_exists = os.path.exists(socket)
    checks.append(("FPM Socket", socket_exists, socket if socket_exists else "Not found"))
    
    # Check 3: Socket permissions
    socket_ok = False
    socket_perm = "N/A"
    if socket_exists:
        try:
            import stat
            mode = os.stat(socket).st_mode
            socket_perm = oct(stat.S_IMODE(mode))
            socket_ok = mode & stat.S_IRWXO or mode & stat.S_IRWXG  # readable by others/group
        except Exception:
            pass
    checks.append(("Socket Permissions", socket_ok, socket_perm))
    
    # Check 4: Required extensions
    required_exts = ["pdo", "mbstring", "xml", "curl"]
    result = run_command(f"php{version} -m", check=False, silent=True)
    loaded_exts = result.stdout.lower() if result.returncode == 0 else ""
    
    missing_exts = [ext for ext in required_exts if ext.lower() not in loaded_exts]
    exts_ok = len(missing_exts) == 0
    exts_msg = "All loaded" if exts_ok else f"Missing: {', '.join(missing_exts)}"
    checks.append(("Required Extensions", exts_ok, exts_msg))
    
    # Check 5: OPcache enabled
    result = run_command(
        f"php{version} -r \"echo extension_loaded('Zend OPcache') ? '1' : '0';\"",
        check=False, silent=True
    )
    opcache_ok = result.stdout.strip() == "1" if result.returncode == 0 else False
    checks.append(("OPcache", opcache_ok, "Enabled" if opcache_ok else "Disabled"))
    
    # Check 6: Memory limit
    result = run_command(
        f"php{version} -r \"echo ini_get('memory_limit');\"",
        check=False, silent=True
    )
    mem_limit = result.stdout.strip() if result.returncode == 0 else "?"
    mem_ok = mem_limit not in ["-1", "0", ""]  # -1 = unlimited (risky)
    checks.append(("Memory Limit", mem_ok, mem_limit))
    
    # Check 7: Error log writable
    log_path = f"/var/log/php{version}-fpm.log"
    log_ok = os.path.exists(log_path) and os.access(log_path, os.W_OK)
    checks.append(("Error Log", log_ok, log_path if log_ok else "Not writable"))
    
    # Display results
    columns = [
        {"name": "Check", "style": "cyan"},
        {"name": "Status", "justify": "center"},
        {"name": "Details"},
    ]
    
    rows = []
    passed = 0
    for name, ok, details in checks:
        status = "[green]✓ PASS[/green]" if ok else "[red]✗ FAIL[/red]"
        if ok:
            passed += 1
        rows.append([name, status, details])
    
    show_table(f"Passed: {passed}/{len(checks)}", columns, rows, show_header=True)
    
    # Recommendations
    if passed < len(checks):
        console.print()
        console.print("[bold yellow]Recommendations:[/bold yellow]")
        
        if not fpm_running:
            console.print(f"  • Start FPM: systemctl start php{version}-fpm")
        if not socket_exists:
            console.print(f"  • Restart FPM to create socket")
        if missing_exts:
            console.print(f"  • Install missing: apt install php{version}-{' php{version}-'.join(missing_exts)}")
        if not opcache_ok:
            console.print(f"  • Enable OPcache in php.ini for better performance")
    
    press_enter_to_continue()
