"""Node.js monitoring and diagnostics."""

import json

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command
from utils.error_handler import handle_error
from modules.runtime.nodejs.utils import (
    run_with_nvm, is_pm2_installed, get_current_nodejs_version,
)


def show_monitor_menu():
    """Display Monitoring submenu."""
    options = [
        ("stats", "1. Process Stats"),
        ("memory", "2. Memory Analysis"),
        ("connections", "3. Active Connections"),
        ("monit", "4. PM2 Dashboard"),
        ("health", "5. Health Check"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "stats": process_stats,
        "memory": memory_analysis,
        "connections": active_connections,
        "monit": pm2_dashboard,
        "health": health_check,
    }
    
    run_menu_loop("Monitoring", options, handlers)


def process_stats():
    """Show real-time stats for Node.js processes."""
    clear_screen()
    show_header()
    show_panel("Process Stats", title="Monitoring", style="cyan")
    
    # Try PM2 first for detailed stats
    if is_pm2_installed():
        result = run_with_nvm("pm2 jlist")
        
        if result and result.returncode == 0:
            try:
                processes = json.loads(result.stdout)
                
                if processes:
                    columns = [
                        {"name": "Name", "style": "cyan"},
                        {"name": "PID", "justify": "right"},
                        {"name": "Status", "justify": "center"},
                        {"name": "CPU", "justify": "right"},
                        {"name": "Memory", "justify": "right"},
                        {"name": "Restarts", "justify": "right"},
                        {"name": "Uptime"},
                    ]
                    
                    rows = []
                    total_cpu = 0
                    total_mem = 0
                    
                    for proc in processes:
                        pm2_env = proc.get("pm2_env", {})
                        monit = proc.get("monit", {})
                        
                        name = proc.get("name", "?")
                        pid = str(proc.get("pid", "?"))
                        status = pm2_env.get("status", "?")
                        
                        status_str = {
                            "online": "[green]online[/green]",
                            "stopped": "[yellow]stopped[/yellow]",
                            "errored": "[red]errored[/red]",
                        }.get(status, f"[dim]{status}[/dim]")
                        
                        cpu = monit.get("cpu", 0)
                        mem_bytes = monit.get("memory", 0)
                        mem_mb = mem_bytes / 1024 / 1024
                        
                        total_cpu += cpu
                        total_mem += mem_mb
                        
                        restarts = str(pm2_env.get("restart_time", 0))
                        uptime = _format_uptime(pm2_env.get("pm_uptime", 0))
                        
                        rows.append([
                            name, pid, status_str,
                            f"{cpu}%", f"{mem_mb:.1f}MB",
                            restarts, uptime
                        ])
                    
                    show_table("PM2 Processes", columns, rows, show_header=True)
                    
                    console.print()
                    console.print(f"[bold]Total:[/bold] CPU: {total_cpu:.1f}% | Memory: {total_mem:.1f}MB")
                else:
                    show_info("No PM2 processes running.")
            except json.JSONDecodeError:
                pass
    
    # Also show raw Node.js processes
    console.print()
    console.print("[bold]All Node.js Processes:[/bold]")
    console.print()
    
    result = run_command("ps aux | grep -E 'node|nodejs' | grep -v grep", check=False, silent=True)
    
    if result.returncode == 0 and result.stdout.strip():
        columns = [
            {"name": "PID", "style": "cyan", "justify": "right"},
            {"name": "CPU%", "justify": "right"},
            {"name": "MEM%", "justify": "right"},
            {"name": "RSS", "justify": "right"},
            {"name": "Command"},
        ]
        
        rows = []
        for line in result.stdout.strip().split('\n'):
            parts = line.split()
            if len(parts) >= 11:
                pid = parts[1]
                cpu = parts[2]
                mem = parts[3]
                rss_kb = int(parts[5]) if parts[5].isdigit() else 0
                rss_mb = f"{rss_kb / 1024:.1f}MB"
                cmd = " ".join(parts[10:])[:50]
                
                rows.append([pid, f"{cpu}%", f"{mem}%", rss_mb, cmd])
        
        if rows:
            show_table("", columns, rows, show_header=True)
        else:
            console.print("[dim]No Node.js processes found.[/dim]")
    else:
        console.print("[dim]No Node.js processes found.[/dim]")
    
    press_enter_to_continue()


def _format_uptime(pm_uptime):
    """Format PM2 uptime timestamp to human readable."""
    if not pm_uptime:
        return "-"
    
    import time
    uptime_ms = time.time() * 1000 - pm_uptime
    uptime_sec = uptime_ms / 1000
    
    if uptime_sec < 60:
        return f"{int(uptime_sec)}s"
    elif uptime_sec < 3600:
        return f"{int(uptime_sec / 60)}m"
    elif uptime_sec < 86400:
        return f"{int(uptime_sec / 3600)}h"
    else:
        return f"{int(uptime_sec / 86400)}d"


def memory_analysis():
    """Analyze Node.js memory usage."""
    clear_screen()
    show_header()
    show_panel("Memory Analysis", title="Monitoring", style="cyan")
    
    console.print("[bold]Node.js Memory Analysis[/bold]")
    console.print()
    
    # Get Node.js processes memory
    result = run_command(
        "ps -eo pid,rss,vsz,comm | grep -E 'node|nodejs' | grep -v grep",
        check=False, silent=True
    )
    
    if result.returncode != 0 or not result.stdout.strip():
        show_info("No Node.js processes running.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "PID", "style": "cyan", "justify": "right"},
        {"name": "RSS (Actual)", "justify": "right"},
        {"name": "VSZ (Virtual)", "justify": "right"},
        {"name": "Command"},
    ]
    
    rows = []
    total_rss = 0
    total_vsz = 0
    
    for line in result.stdout.strip().split('\n'):
        parts = line.split()
        if len(parts) >= 4:
            pid = parts[0]
            rss_kb = int(parts[1]) if parts[1].isdigit() else 0
            vsz_kb = int(parts[2]) if parts[2].isdigit() else 0
            cmd = parts[3]
            
            total_rss += rss_kb
            total_vsz += vsz_kb
            
            rows.append([
                pid,
                f"{rss_kb / 1024:.1f} MB",
                f"{vsz_kb / 1024:.1f} MB",
                cmd
            ])
    
    show_table("", columns, rows, show_header=True)
    
    console.print()
    console.print(f"[bold]Total RSS:[/bold] {total_rss / 1024:.1f} MB")
    console.print(f"[bold]Total VSZ:[/bold] {total_vsz / 1024:.1f} MB")
    
    # Get system memory
    console.print()
    result = run_command("free -m | grep Mem", check=False, silent=True)
    if result.returncode == 0:
        parts = result.stdout.split()
        if len(parts) >= 3:
            total_mem = int(parts[1])
            used_mem = int(parts[2])
            console.print(f"[bold]System Memory:[/bold] {used_mem} MB / {total_mem} MB ({used_mem * 100 // total_mem}% used)")
    
    # Recommendations
    console.print()
    console.print("[bold]Recommendations:[/bold]")
    
    if total_rss > 500 * 1024:  # > 500MB
        console.print("  [yellow]• High memory usage. Consider increasing --max-old-space-size[/yellow]")
    
    if len(rows) > 5:
        console.print("  [dim]• Multiple Node processes. Consider using PM2 cluster mode.[/dim]")
    
    console.print("  [dim]• Monitor for memory leaks with: node --inspect app.js[/dim]")
    
    press_enter_to_continue()


def active_connections():
    """Show active network connections for Node.js."""
    clear_screen()
    show_header()
    show_panel("Active Connections", title="Monitoring", style="cyan")
    
    console.print("[bold]Listening Ports (Node.js)[/bold]")
    console.print()
    
    # Get listening ports
    result = run_command(
        "ss -tlnp 2>/dev/null | grep -E 'node|nodejs' || "
        "netstat -tlnp 2>/dev/null | grep -E 'node|nodejs'",
        check=False, silent=True
    )
    
    if result.returncode == 0 and result.stdout.strip():
        for line in result.stdout.strip().split('\n'):
            # Parse port from output
            if ':' in line:
                console.print(f"  {line}")
    else:
        show_info("No Node.js ports listening.")
    
    console.print()
    console.print("[bold]Active TCP Connections[/bold]")
    console.print()
    
    # Get established connections
    result = run_command(
        "ss -tnp 2>/dev/null | grep -E 'node|nodejs' | grep ESTAB || "
        "netstat -tnp 2>/dev/null | grep -E 'node|nodejs' | grep ESTABLISHED",
        check=False, silent=True
    )
    
    if result.returncode == 0 and result.stdout.strip():
        lines = result.stdout.strip().split('\n')
        console.print(f"  Total: {len(lines)} connection(s)")
        console.print()
        
        # Show first 10
        for line in lines[:10]:
            console.print(f"  [dim]{line}[/dim]")
        
        if len(lines) > 10:
            console.print(f"  [dim]... and {len(lines) - 10} more[/dim]")
    else:
        console.print("  [dim]No active connections[/dim]")
    
    press_enter_to_continue()


def pm2_dashboard():
    """Launch PM2 monitoring dashboard."""
    clear_screen()
    show_header()
    show_panel("PM2 Dashboard", title="Monitoring", style="cyan")
    
    if not is_pm2_installed():
        handle_error("E3003", "PM2 is not installed.")
        console.print()
        console.print("[dim]Install PM2 first via 'PM2 Process Manager' menu.[/dim]")
        press_enter_to_continue()
        return
    
    console.print("Launching PM2 monitoring dashboard...")
    console.print()
    console.print("[dim]Press 'q' or Ctrl+C to exit[/dim]")
    console.print()
    
    if not confirm_action("Launch dashboard?"):
        return
    
    # Run interactively
    import os
    from config import NVM_DIR
    nvm_script = os.path.join(NVM_DIR, "nvm.sh")
    os.system(f'bash -c "source {nvm_script} && pm2 monit"')


def health_check():
    """Run Node.js health check diagnostics."""
    clear_screen()
    show_header()
    show_panel("Health Check", title="Monitoring", style="cyan")
    
    checks = []
    recommendations = []
    
    # Check 1: Node.js installed
    node_version = get_current_nodejs_version()
    node_ok = node_version is not None
    checks.append(("Node.js", node_ok, node_version or "Not installed"))
    if not node_ok:
        recommendations.append("Install Node.js via NVM")
    
    # Check 2: npm working
    result = run_with_nvm("npm --version")
    npm_ok = result is not None and result.returncode == 0
    npm_version = result.stdout.strip() if npm_ok else "Not working"
    checks.append(("npm", npm_ok, npm_version))
    
    # Check 3: PM2 installed
    pm2_ok = is_pm2_installed()
    result = run_with_nvm("pm2 --version") if pm2_ok else None
    pm2_version = result.stdout.strip() if result and result.returncode == 0 else "Not installed"
    checks.append(("PM2", pm2_ok, pm2_version))
    if not pm2_ok:
        recommendations.append("Install PM2 for process management")
    
    # Check 4: PM2 processes running
    pm2_running = False
    pm2_count = 0
    if pm2_ok:
        result = run_with_nvm("pm2 jlist")
        if result and result.returncode == 0:
            try:
                processes = json.loads(result.stdout)
                pm2_count = len(processes)
                pm2_running = pm2_count > 0
            except json.JSONDecodeError:
                pass
    checks.append(("PM2 Processes", pm2_running or None, f"{pm2_count} running"))
    
    # Check 5: PM2 startup configured
    pm2_startup = False
    result = run_command("systemctl is-enabled pm2-* 2>/dev/null", check=False, silent=True)
    if result.returncode == 0 and "enabled" in result.stdout:
        pm2_startup = True
    checks.append(("PM2 Startup", pm2_startup if pm2_ok else None, 
                   "Configured" if pm2_startup else "Not configured"))
    if pm2_ok and not pm2_startup:
        recommendations.append("Setup PM2 startup script for auto-restart on boot")
    
    # Check 6: Node.js processes
    result = run_command("pgrep -c node 2>/dev/null", check=False, silent=True)
    node_procs = int(result.stdout.strip()) if result.returncode == 0 else 0
    checks.append(("Node Processes", None, f"{node_procs} running"))
    
    # Check 7: Memory usage
    result = run_command(
        "ps -eo rss,comm | grep node | awk '{sum+=$1} END {print sum}'",
        check=False, silent=True
    )
    mem_kb = int(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip() else 0
    mem_mb = mem_kb / 1024
    mem_ok = mem_mb < 1024  # Less than 1GB
    checks.append(("Memory Usage", mem_ok if mem_mb > 0 else None, f"{mem_mb:.1f} MB"))
    if mem_mb > 1024:
        recommendations.append("High memory usage - check for memory leaks")
    
    # Display results
    columns = [
        {"name": "Check", "style": "cyan"},
        {"name": "Status", "justify": "center"},
        {"name": "Details"},
    ]
    
    rows = []
    passed = 0
    total = 0
    
    for name, ok, details in checks:
        if ok is None:
            status = "[dim]○ INFO[/dim]"
        elif ok:
            status = "[green]✓ PASS[/green]"
            passed += 1
            total += 1
        else:
            status = "[red]✗ FAIL[/red]"
            total += 1
        rows.append([name, status, details])
    
    show_table(f"Score: {passed}/{total}", columns, rows, show_header=True)
    
    # Recommendations
    if recommendations:
        console.print()
        console.print("[bold yellow]Recommendations:[/bold yellow]")
        for rec in recommendations:
            console.print(f"  • {rec}")
    else:
        console.print()
        console.print("[bold green]All critical checks passed![/bold green]")
    
    press_enter_to_continue()
