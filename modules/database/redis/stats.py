"""Redis performance statistics functions."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table, show_info, press_enter_to_continue,
)
from utils.error_handler import handle_error
from ui.menu import select_from_list, run_menu_loop
from modules.database.redis.utils import is_redis_ready, redis_info, run_redis_cli


def show_stats_menu():
    """Display Performance Stats submenu."""
    options = [
        ("overview", "1. Stats Overview"),
        ("commands", "2. Command Stats"),
        ("clients", "3. Client Stats"),
        ("replication", "4. Replication Status"),
        ("latency", "5. Latency Check"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "overview": stats_overview,
        "commands": command_stats,
        "clients": client_stats,
        "replication": replication_status,
        "latency": latency_check,
    }
    
    run_menu_loop("Performance Stats", options, handlers)


def stats_overview():
    """Show overall performance statistics."""
    clear_screen()
    show_header()
    show_panel("Stats Overview", title="Redis", style="cyan")
    
    if not is_redis_ready():
        handle_error("E4001", "Redis is not running.")
        press_enter_to_continue()
        return
    
    stats = redis_info("stats")
    server = redis_info("server")
    
    uptime_hours = int(server.get("uptime_in_seconds", 0)) // 3600
    
    columns = [
        {"name": "Metric", "style": "cyan"},
        {"name": "Value"},
    ]
    
    rows = [
        ["Uptime", f"{uptime_hours} hours"],
        ["Total Connections", stats.get("total_connections_received", "N/A")],
        ["Total Commands", stats.get("total_commands_processed", "N/A")],
        ["Ops/sec", stats.get("instantaneous_ops_per_sec", "N/A")],
        ["Input (kbps)", stats.get("instantaneous_input_kbps", "N/A")],
        ["Output (kbps)", stats.get("instantaneous_output_kbps", "N/A")],
        ["Rejected Connections", stats.get("rejected_connections", "0")],
        ["Expired Keys", stats.get("expired_keys", "0")],
        ["Evicted Keys", stats.get("evicted_keys", "0")],
        ["Keyspace Hits", stats.get("keyspace_hits", "0")],
        ["Keyspace Misses", stats.get("keyspace_misses", "0")],
    ]
    
    show_table("", columns, rows, show_header=True)
    
    # Calculate hit ratio
    hits = int(stats.get("keyspace_hits", 0))
    misses = int(stats.get("keyspace_misses", 0))
    total = hits + misses
    
    if total > 0:
        hit_ratio = (hits / total) * 100
        console.print()
        console.print(f"[bold]Cache Hit Ratio:[/bold] {hit_ratio:.2f}%")
        if hit_ratio < 80:
            console.print("[yellow]Low hit ratio - consider reviewing key expiration policies[/yellow]")
    
    press_enter_to_continue()


def command_stats():
    """Show statistics per command type."""
    clear_screen()
    show_header()
    show_panel("Command Stats", title="Redis", style="cyan")
    
    if not is_redis_ready():
        handle_error("E4001", "Redis is not running.")
        press_enter_to_continue()
        return
    
    result = run_redis_cli("INFO commandstats")
    if result.returncode != 0:
        handle_error("E4001", "Failed to get command stats.")
        press_enter_to_continue()
        return
    
    commands = []
    for line in result.stdout.strip().split('\n'):
        if line.startswith('cmdstat_'):
            cmd_name = line.split(':')[0].replace('cmdstat_', '')
            values = line.split(':')[1]
            
            parts = dict(item.split('=') for item in values.split(','))
            calls = int(parts.get('calls', 0))
            usec = int(parts.get('usec', 0))
            usec_per_call = float(parts.get('usec_per_call', 0))
            
            commands.append((cmd_name, calls, usec_per_call))
    
    commands.sort(key=lambda x: x[1], reverse=True)
    
    columns = [
        {"name": "Command", "style": "cyan"},
        {"name": "Calls", "justify": "right"},
        {"name": "Avg Time (μs)", "justify": "right"},
    ]
    
    rows = []
    for cmd, calls, usec in commands[:20]:
        rows.append([cmd.upper(), str(calls), f"{usec:.2f}"])
    
    if rows:
        show_table("Top 20 commands by call count", columns, rows, show_header=True)
    else:
        show_info("No command statistics available.")
    
    press_enter_to_continue()


def client_stats():
    """Show connected client statistics."""
    clear_screen()
    show_header()
    show_panel("Client Stats", title="Redis", style="cyan")
    
    if not is_redis_ready():
        handle_error("E4001", "Redis is not running.")
        press_enter_to_continue()
        return
    
    clients = redis_info("clients")
    
    columns = [
        {"name": "Metric", "style": "cyan"},
        {"name": "Value"},
    ]
    
    rows = [
        ["Connected Clients", clients.get("connected_clients", "N/A")],
        ["Blocked Clients", clients.get("blocked_clients", "0")],
        ["Tracking Clients", clients.get("tracking_clients", "0")],
        ["Max Clients", clients.get("maxclients", "N/A")],
    ]
    
    show_table("", columns, rows, show_header=True)
    
    # Show client list
    console.print()
    console.print("[bold]Connected Clients:[/bold]")
    
    result = run_redis_cli("CLIENT LIST")
    if result.returncode == 0 and result.stdout.strip():
        client_count = len(result.stdout.strip().split('\n'))
        console.print(f"[dim]{client_count} client(s) connected[/dim]")
        
        for line in result.stdout.strip().split('\n')[:5]:
            parts = dict(item.split('=') for item in line.split() if '=' in item)
            addr = parts.get('addr', 'unknown')
            cmd = parts.get('cmd', 'none')
            age = parts.get('age', '0')
            console.print(f"  • {addr} - cmd:{cmd} age:{age}s")
        
        if client_count > 5:
            console.print(f"  [dim]... and {client_count - 5} more[/dim]")
    
    press_enter_to_continue()


def replication_status():
    """Show replication status."""
    clear_screen()
    show_header()
    show_panel("Replication Status", title="Redis", style="cyan")
    
    if not is_redis_ready():
        handle_error("E4001", "Redis is not running.")
        press_enter_to_continue()
        return
    
    replication = redis_info("replication")
    
    role = replication.get("role", "unknown")
    
    console.print(f"[bold]Role:[/bold] {role}")
    console.print()
    
    if role == "master":
        connected_slaves = replication.get("connected_slaves", "0")
        console.print(f"[bold]Connected Replicas:[/bold] {connected_slaves}")
        
        # Show replica info
        for key, value in replication.items():
            if key.startswith("slave"):
                console.print(f"  • {key}: {value}")
    
    elif role == "slave":
        console.print(f"[bold]Master Host:[/bold] {replication.get('master_host', 'N/A')}")
        console.print(f"[bold]Master Port:[/bold] {replication.get('master_port', 'N/A')}")
        console.print(f"[bold]Master Link Status:[/bold] {replication.get('master_link_status', 'N/A')}")
        console.print(f"[bold]Replication Offset:[/bold] {replication.get('slave_repl_offset', 'N/A')}")
    
    else:
        console.print("[dim]Standalone mode - no replication configured[/dim]")
    
    press_enter_to_continue()


def latency_check():
    """Check Redis latency."""
    clear_screen()
    show_header()
    show_panel("Latency Check", title="Redis", style="cyan")
    
    if not is_redis_ready():
        handle_error("E4001", "Redis is not running.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Running latency test (10 samples)...[/bold]")
    console.print()
    
    import time
    latencies = []
    
    for i in range(10):
        start = time.time()
        result = run_redis_cli("PING")
        end = time.time()
        
        if result.returncode == 0:
            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)
            console.print(f"  Sample {i+1}: {latency_ms:.2f}ms")
        else:
            console.print(f"  Sample {i+1}: [red]FAILED[/red]")
    
    if latencies:
        console.print()
        avg = sum(latencies) / len(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)
        
        console.print(f"[bold]Average:[/bold] {avg:.2f}ms")
        console.print(f"[bold]Min:[/bold] {min_lat:.2f}ms")
        console.print(f"[bold]Max:[/bold] {max_lat:.2f}ms")
        
        if avg > 10:
            console.print()
            console.print("[yellow]High latency detected - check network or system load[/yellow]")
    
    press_enter_to_continue()
