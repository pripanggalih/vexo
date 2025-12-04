"""MariaDB monitoring functions."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, is_service_running
from modules.database.mariadb.utils import (
    is_mariadb_ready, run_mysql, get_databases, get_database_size,
    format_size, get_mariadb_version, get_mariadb_datadir, get_user_databases,
)


def show_monitor_menu():
    """Display Monitoring submenu."""
    options = [
        ("stats", "1. Database Stats"),
        ("tables", "2. Table Sizes"),
        ("connections", "3. Active Connections"),
        ("slow", "4. Slow Query Log"),
        ("health", "5. Health Check"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "stats": database_stats,
        "tables": table_sizes,
        "connections": active_connections,
        "slow": slow_query_log,
        "health": health_check,
    }
    
    run_menu_loop("Monitoring", options, handlers)


def database_stats():
    """Show database statistics."""
    clear_screen()
    show_header()
    show_panel("Database Statistics", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    version = get_mariadb_version()
    datadir = get_mariadb_datadir()
    
    console.print(f"[bold]MariaDB Version:[/bold] {version}")
    console.print(f"[bold]Data Directory:[/bold] {datadir}")
    console.print()
    
    result = run_mysql("SHOW GLOBAL STATUS LIKE 'Uptime';")
    if result.returncode == 0 and '\t' in result.stdout:
        uptime = result.stdout.split('\t')[1].strip()
        hours = int(uptime) // 3600 if uptime.isdigit() else 0
        console.print(f"[bold]Uptime:[/bold] {hours} hours")
    
    result = run_mysql("SHOW GLOBAL STATUS LIKE 'Threads_connected';")
    if result.returncode == 0 and '\t' in result.stdout:
        connections = result.stdout.split('\t')[1].strip()
        console.print(f"[bold]Active Connections:[/bold] {connections}")
    
    result = run_mysql("SELECT @@max_connections;")
    if result.returncode == 0:
        console.print(f"[bold]Max Connections:[/bold] {result.stdout.strip()}")
    
    console.print()
    
    databases = get_databases()
    
    columns = [
        {"name": "Database", "style": "cyan"},
        {"name": "Size", "justify": "right"},
        {"name": "Tables", "justify": "right"},
    ]
    
    rows = []
    total_size = 0
    
    for db in databases:
        size = get_database_size(db)
        total_size += size
        
        result = run_mysql(
            f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '{db}';"
        )
        table_count = result.stdout.strip() if result.returncode == 0 else "?"
        
        rows.append([db, format_size(size), table_count])
    
    show_table(f"Total: {format_size(total_size)}", columns, rows, show_header=True)
    
    press_enter_to_continue()


def table_sizes():
    """Show table sizes for a database."""
    clear_screen()
    show_header()
    show_panel("Table Sizes", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    databases = get_user_databases()
    
    if not databases:
        show_info("No user databases found.")
        press_enter_to_continue()
        return
    
    database = select_from_list("Select Database", "Show tables for:", databases)
    if not database:
        return
    
    sql = f"""
    SELECT 
        table_name,
        ROUND((data_length + index_length) / 1024 / 1024, 2) as total_mb,
        ROUND(data_length / 1024 / 1024, 2) as data_mb,
        ROUND(index_length / 1024 / 1024, 2) as index_mb,
        table_rows
    FROM information_schema.tables 
    WHERE table_schema = '{database}'
    ORDER BY (data_length + index_length) DESC
    LIMIT 20;
    """
    
    result = run_mysql(sql)
    
    if result.returncode != 0 or not result.stdout.strip():
        show_info("No tables found.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Table", "style": "cyan"},
        {"name": "Total MB", "justify": "right"},
        {"name": "Data MB", "justify": "right"},
        {"name": "Index MB", "justify": "right"},
        {"name": "Rows", "justify": "right"},
    ]
    
    rows = []
    for line in result.stdout.strip().split('\n'):
        parts = line.split('\t')
        if len(parts) >= 5:
            rows.append(parts[:5])
    
    if rows:
        show_table(f"Top tables in {database}", columns, rows, show_header=True)
    else:
        show_info("No tables found.")
    
    press_enter_to_continue()


def active_connections():
    """Show active database connections."""
    clear_screen()
    show_header()
    show_panel("Active Connections", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    result = run_mysql("SHOW FULL PROCESSLIST;")
    
    if result.returncode != 0:
        show_error("Failed to get connections.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "ID", "style": "cyan"},
        {"name": "User"},
        {"name": "Host"},
        {"name": "DB"},
        {"name": "Time"},
        {"name": "State"},
    ]
    
    rows = []
    for line in result.stdout.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) >= 6:
            rows.append(parts[:6])
    
    if rows:
        show_table(f"{len(rows)} connection(s)", columns, rows, show_header=True)
        
        console.print()
        if confirm_action("Kill a connection?"):
            pid = text_input("Enter ID to kill:")
            if pid and pid.isdigit():
                result = run_mysql(f"KILL {pid};")
                if result.returncode == 0:
                    show_success(f"Connection {pid} terminated.")
                else:
                    show_error("Failed to terminate connection.")
    else:
        show_info("No active connections.")
    
    press_enter_to_continue()


def slow_query_log():
    """Configure and view slow query log."""
    clear_screen()
    show_header()
    show_panel("Slow Query Log", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        show_error("MariaDB is not running.")
        press_enter_to_continue()
        return
    
    result = run_mysql("SELECT @@slow_query_log;")
    enabled = result.stdout.strip() == "1" if result.returncode == 0 else False
    
    result = run_mysql("SELECT @@long_query_time;")
    threshold = result.stdout.strip() if result.returncode == 0 else "10"
    
    console.print(f"[bold]Slow Query Log:[/bold] {'Enabled' if enabled else 'Disabled'}")
    console.print(f"[bold]Threshold:[/bold] {threshold} seconds")
    console.print()
    
    options = [
        "Enable (log queries > 2 seconds)",
        "Enable (log queries > 5 seconds)",
        "Disable slow query logging",
        "View recent slow queries",
    ]
    
    choice = select_from_list("Action", "What to do?", options)
    if not choice:
        return
    
    if "2 seconds" in choice:
        run_mysql("SET GLOBAL slow_query_log = 'ON';")
        run_mysql("SET GLOBAL long_query_time = 2;")
        show_success("Slow query log enabled (> 2s)")
    elif "5 seconds" in choice:
        run_mysql("SET GLOBAL slow_query_log = 'ON';")
        run_mysql("SET GLOBAL long_query_time = 5;")
        show_success("Slow query log enabled (> 5s)")
    elif "Disable" in choice:
        run_mysql("SET GLOBAL slow_query_log = 'OFF';")
        show_success("Slow query log disabled.")
    else:
        result = run_mysql("SELECT @@slow_query_log_file;")
        log_file = result.stdout.strip() if result.returncode == 0 else "/var/log/mysql/mariadb-slow.log"
        
        console.print()
        console.print("[bold]Recent Slow Queries:[/bold]")
        result = run_command(f"tail -50 {log_file} 2>/dev/null", check=False, silent=True)
        if result.stdout.strip():
            console.print(result.stdout[:2000])
        else:
            show_info("No slow queries found or log file not accessible.")
    
    press_enter_to_continue()


def health_check():
    """Run MariaDB health check."""
    clear_screen()
    show_header()
    show_panel("Health Check", title="MariaDB", style="cyan")
    
    checks = []
    recommendations = []
    
    running = is_service_running("mariadb")
    checks.append(("Service Running", running, "Yes" if running else "No"))
    if not running:
        recommendations.append("Start MariaDB: systemctl start mariadb")
        _show_health_results(checks, recommendations)
        return
    
    result = run_mysql("SELECT 1;")
    accepting = result.returncode == 0
    checks.append(("Accepting Connections", accepting, "Yes" if accepting else "No"))
    
    result = run_mysql("SHOW GLOBAL STATUS LIKE 'Threads_connected';")
    conn_count = int(result.stdout.split('\t')[1]) if result.returncode == 0 and '\t' in result.stdout else 0
    result = run_mysql("SELECT @@max_connections;")
    max_conn = int(result.stdout.strip()) if result.returncode == 0 else 151
    conn_pct = (conn_count / max_conn) * 100
    conn_ok = conn_pct < 80
    checks.append(("Connection Usage", conn_ok, f"{conn_count}/{max_conn} ({conn_pct:.0f}%)"))
    if not conn_ok:
        recommendations.append("Connection usage high - consider increasing max_connections")
    
    datadir = get_mariadb_datadir()
    if datadir:
        result = run_command(f"df -h {datadir} | tail -1", check=False, silent=True)
        if result.returncode == 0:
            parts = result.stdout.split()
            if len(parts) >= 5:
                usage = parts[4].replace('%', '')
                disk_ok = int(usage) < 85
                checks.append(("Disk Space", disk_ok, f"{parts[4]} used"))
                if not disk_ok:
                    recommendations.append("Disk space low - clean up or expand storage")
    
    result = run_mysql("SELECT @@innodb_buffer_pool_size / 1024 / 1024 as mb;")
    buffer_mb = int(float(result.stdout.strip())) if result.returncode == 0 else 0
    buffer_ok = buffer_mb >= 128
    checks.append(("InnoDB Buffer Pool", buffer_ok, f"{buffer_mb} MB"))
    if not buffer_ok:
        recommendations.append("InnoDB buffer pool is small - consider increasing")
    
    _show_health_results(checks, recommendations)


def _show_health_results(checks, recommendations):
    """Display health check results."""
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
    
    show_table(f"Score: {passed}/{len(checks)}", columns, rows, show_header=True)
    
    if recommendations:
        console.print()
        console.print("[bold yellow]Recommendations:[/bold yellow]")
        for rec in recommendations:
            console.print(f"  • {rec}")
    else:
        console.print()
        console.print("[bold green]All checks passed![/bold green]")
    
    press_enter_to_continue()
