"""PostgreSQL monitoring functions."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, is_service_running
from modules.database.postgresql.utils import (
    is_postgresql_ready, run_psql, get_databases, get_database_size,
    format_size, get_pg_version, get_pg_data_dir, get_user_databases,
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
    show_panel("Database Statistics", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    version = get_pg_version()
    data_dir = get_pg_data_dir()
    
    console.print(f"[bold]PostgreSQL Version:[/bold] {version}")
    console.print(f"[bold]Data Directory:[/bold] {data_dir}")
    console.print()
    
    result = run_psql("SELECT pg_postmaster_start_time();")
    if result.returncode == 0:
        console.print(f"[bold]Started:[/bold] {result.stdout.strip()}")
    
    result = run_psql("SELECT count(*) FROM pg_stat_activity;")
    if result.returncode == 0:
        console.print(f"[bold]Active Connections:[/bold] {result.stdout.strip()}")
    
    result = run_psql("SHOW max_connections;")
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
        
        result = run_psql(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';",
            database=db
        )
        table_count = result.stdout.strip() if result.returncode == 0 else "?"
        
        rows.append([db, format_size(size), table_count])
    
    show_table(f"Total: {format_size(total_size)}", columns, rows, show_header=True)
    
    press_enter_to_continue()


def table_sizes():
    """Show table sizes for a database."""
    clear_screen()
    show_header()
    show_panel("Table Sizes", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
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
    
    sql = """
    SELECT 
        tablename,
        pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) as total_size,
        pg_size_pretty(pg_relation_size(schemaname || '.' || tablename)) as data_size,
        pg_size_pretty(pg_indexes_size(schemaname || '.' || tablename)) as index_size
    FROM pg_tables 
    WHERE schemaname = 'public'
    ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC
    LIMIT 20;
    """
    
    result = run_psql(sql, database=database)
    
    if result.returncode != 0 or not result.stdout.strip():
        show_info("No tables found.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Table", "style": "cyan"},
        {"name": "Total Size", "justify": "right"},
        {"name": "Data Size", "justify": "right"},
        {"name": "Index Size", "justify": "right"},
    ]
    
    rows = []
    for line in result.stdout.strip().split('\n'):
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 4:
            rows.append(parts[:4])
    
    if rows:
        show_table(f"Top tables in {database}", columns, rows, show_header=True)
    else:
        show_info("No tables found.")
    
    press_enter_to_continue()


def active_connections():
    """Show active database connections."""
    clear_screen()
    show_header()
    show_panel("Active Connections", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    sql = """
    SELECT 
        pid,
        usename,
        datname,
        client_addr,
        state,
        query_start::text,
        LEFT(query, 50) as query
    FROM pg_stat_activity
    WHERE state IS NOT NULL
    ORDER BY query_start DESC
    LIMIT 20;
    """
    
    result = run_psql(sql)
    
    if result.returncode != 0:
        show_error("Failed to get connections.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "PID", "style": "cyan"},
        {"name": "User"},
        {"name": "Database"},
        {"name": "Client"},
        {"name": "State"},
        {"name": "Query"},
    ]
    
    rows = []
    for line in result.stdout.strip().split('\n'):
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 6:
            state = parts[4]
            if state == "active":
                state = "[green]active[/green]"
            elif state == "idle":
                state = "[dim]idle[/dim]"
            parts[4] = state
            rows.append(parts[:6])
    
    if rows:
        show_table(f"{len(rows)} connection(s)", columns, rows, show_header=True)
        
        console.print()
        if confirm_action("Kill a connection?"):
            pid = text_input("Enter PID to kill:")
            if pid and pid.isdigit():
                result = run_psql(f"SELECT pg_terminate_backend({pid});")
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
    show_panel("Slow Query Log", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    result = run_psql("SHOW log_min_duration_statement;")
    current = result.stdout.strip() if result.returncode == 0 else "-1"
    
    console.print(f"[bold]Current slow query threshold:[/bold] {current}")
    console.print()
    
    if current == "-1":
        console.print("[yellow]Slow query logging is disabled.[/yellow]")
    else:
        console.print(f"[green]Logging queries slower than {current}[/green]")
    
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
        run_psql("ALTER SYSTEM SET log_min_duration_statement = '2s';")
        run_psql("SELECT pg_reload_conf();")
        show_success("Slow query log enabled (> 2s)")
    elif "5 seconds" in choice:
        run_psql("ALTER SYSTEM SET log_min_duration_statement = '5s';")
        run_psql("SELECT pg_reload_conf();")
        show_success("Slow query log enabled (> 5s)")
    elif "Disable" in choice:
        run_psql("ALTER SYSTEM SET log_min_duration_statement = '-1';")
        run_psql("SELECT pg_reload_conf();")
        show_success("Slow query log disabled.")
    else:
        console.print()
        console.print("[bold]Recent PostgreSQL log:[/bold]")
        result = run_command(
            "tail -50 /var/log/postgresql/*.log 2>/dev/null | grep -i duration",
            check=False, silent=True
        )
        if result.stdout.strip():
            console.print(result.stdout)
        else:
            show_info("No slow queries found in recent logs.")
    
    press_enter_to_continue()


def health_check():
    """Run PostgreSQL health check."""
    clear_screen()
    show_header()
    show_panel("Health Check", title="PostgreSQL", style="cyan")
    
    checks = []
    recommendations = []
    
    running = is_service_running("postgresql")
    checks.append(("Service Running", running, "Yes" if running else "No"))
    if not running:
        recommendations.append("Start PostgreSQL: systemctl start postgresql")
        _show_health_results(checks, recommendations)
        return
    
    result = run_psql("SELECT 1;")
    accepting = result.returncode == 0
    checks.append(("Accepting Connections", accepting, "Yes" if accepting else "No"))
    
    result = run_psql("SELECT count(*) FROM pg_stat_activity;")
    conn_count = int(result.stdout.strip()) if result.returncode == 0 else 0
    result = run_psql("SHOW max_connections;")
    max_conn = int(result.stdout.strip()) if result.returncode == 0 else 100
    conn_pct = (conn_count / max_conn) * 100
    conn_ok = conn_pct < 80
    checks.append(("Connection Usage", conn_ok, f"{conn_count}/{max_conn} ({conn_pct:.0f}%)"))
    if not conn_ok:
        recommendations.append("Connection usage high - consider increasing max_connections")
    
    data_dir = get_pg_data_dir()
    if data_dir:
        result = run_command(f"df -h {data_dir} | tail -1", check=False, silent=True)
        if result.returncode == 0:
            parts = result.stdout.split()
            if len(parts) >= 5:
                usage = parts[4].replace('%', '')
                disk_ok = int(usage) < 85
                checks.append(("Disk Space", disk_ok, f"{parts[4]} used"))
                if not disk_ok:
                    recommendations.append("Disk space low - clean up or expand storage")
    
    result = run_psql(
        "SELECT count(*) FROM pg_stat_activity WHERE state = 'active' AND now() - query_start > interval '5 minutes';"
    )
    long_queries = int(result.stdout.strip()) if result.returncode == 0 else 0
    checks.append(("Long Queries (>5min)", long_queries == 0, str(long_queries)))
    if long_queries > 0:
        recommendations.append(f"{long_queries} query running > 5 minutes - check for locks")
    
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
