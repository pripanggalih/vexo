"""Redis memory management functions."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_warning, show_info, press_enter_to_continue,
)
from utils.error_handler import handle_error
from ui.menu import text_input, select_from_list, run_menu_loop
from modules.database.redis.utils import (
    is_redis_ready, redis_info, run_redis_cli, get_redis_config,
    set_redis_config, format_size,
)


def show_memory_menu():
    """Display Memory Management submenu."""
    options = [
        ("stats", "1. Memory Stats"),
        ("limit", "2. Set Max Memory"),
        ("policy", "3. Eviction Policy"),
        ("analyze", "4. Memory Analysis"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "stats": memory_stats,
        "limit": set_max_memory,
        "policy": eviction_policy,
        "analyze": memory_analysis,
    }
    
    run_menu_loop("Memory Management", options, handlers)


def memory_stats():
    """Show memory statistics."""
    clear_screen()
    show_header()
    show_panel("Memory Statistics", title="Redis", style="cyan")
    
    if not is_redis_ready():
        handle_error("E4001", "Redis is not running.")
        press_enter_to_continue()
        return
    
    memory = redis_info("memory")
    
    columns = [
        {"name": "Metric", "style": "cyan"},
        {"name": "Value"},
    ]
    
    rows = [
        ["Used Memory", memory.get("used_memory_human", "N/A")],
        ["Used Memory RSS", memory.get("used_memory_rss_human", "N/A")],
        ["Peak Memory", memory.get("used_memory_peak_human", "N/A")],
        ["Max Memory", memory.get("maxmemory_human", "unlimited")],
        ["Fragmentation Ratio", memory.get("mem_fragmentation_ratio", "N/A")],
        ["Memory Allocator", memory.get("mem_allocator", "N/A")],
        ["Used Memory Scripts", memory.get("used_memory_scripts_human", "N/A")],
        ["Clients Memory", memory.get("used_memory_clients_human", "N/A")],
    ]
    
    show_table("", columns, rows, show_header=True)
    
    frag_ratio = float(memory.get("mem_fragmentation_ratio", 1))
    console.print()
    
    if frag_ratio > 1.5:
        show_warning(f"High fragmentation ratio ({frag_ratio:.2f}) - consider restart")
    elif frag_ratio < 1:
        show_warning(f"Low fragmentation ratio ({frag_ratio:.2f}) - possible memory swapping")
    else:
        console.print(f"[green]Fragmentation ratio is healthy ({frag_ratio:.2f})[/green]")
    
    press_enter_to_continue()


def set_max_memory():
    """Set maximum memory limit."""
    clear_screen()
    show_header()
    show_panel("Set Max Memory", title="Redis", style="cyan")
    
    if not is_redis_ready():
        handle_error("E4001", "Redis is not running.")
        press_enter_to_continue()
        return
    
    current = get_redis_config("maxmemory")
    console.print(f"[bold]Current maxmemory:[/bold] {current or '0 (unlimited)'}")
    console.print()
    
    options = [
        "128 MB",
        "256 MB",
        "512 MB",
        "1 GB",
        "2 GB",
        "4 GB",
        "Unlimited (0)",
        "Custom",
    ]
    
    choice = select_from_list("Max Memory", "Set limit:", options)
    if not choice:
        return
    
    size_map = {
        "128 MB": "128mb",
        "256 MB": "256mb",
        "512 MB": "512mb",
        "1 GB": "1gb",
        "2 GB": "2gb",
        "4 GB": "4gb",
        "Unlimited": "0",
    }
    
    if "Custom" in choice:
        value = text_input("Value (e.g., 512mb, 2gb):")
        if not value:
            return
    else:
        for key, val in size_map.items():
            if key in choice:
                value = val
                break
    
    result = set_redis_config("maxmemory", value)
    
    if result.returncode == 0:
        show_success(f"Max memory set to {value}!")
        console.print("[dim]Note: Add to redis.conf for persistence across restarts[/dim]")
    else:
        handle_error("E4001", "Failed to set max memory.")
    
    press_enter_to_continue()


def eviction_policy():
    """Configure eviction policy."""
    clear_screen()
    show_header()
    show_panel("Eviction Policy", title="Redis", style="cyan")
    
    if not is_redis_ready():
        handle_error("E4001", "Redis is not running.")
        press_enter_to_continue()
        return
    
    current = get_redis_config("maxmemory-policy")
    console.print(f"[bold]Current policy:[/bold] {current or 'noeviction'}")
    console.print()
    
    policies = [
        ("noeviction", "Return error when memory limit reached"),
        ("allkeys-lru", "Evict least recently used keys"),
        ("allkeys-lfu", "Evict least frequently used keys"),
        ("volatile-lru", "Evict LRU keys with TTL set"),
        ("volatile-lfu", "Evict LFU keys with TTL set"),
        ("allkeys-random", "Evict random keys"),
        ("volatile-random", "Evict random keys with TTL"),
        ("volatile-ttl", "Evict keys with shortest TTL"),
    ]
    
    console.print("[bold]Available Policies:[/bold]")
    for policy, desc in policies:
        marker = "[green]→[/green] " if policy == current else "  "
        console.print(f"{marker}{policy}: [dim]{desc}[/dim]")
    console.print()
    
    policy_names = [p[0] for p in policies]
    choice = select_from_list("Select Policy", "Set to:", policy_names)
    
    if not choice:
        return
    
    result = set_redis_config("maxmemory-policy", choice)
    
    if result.returncode == 0:
        show_success(f"Eviction policy set to {choice}!")
    else:
        handle_error("E4001", "Failed to set policy.")
    
    press_enter_to_continue()


def memory_analysis():
    """Analyze memory usage by key patterns."""
    clear_screen()
    show_header()
    show_panel("Memory Analysis", title="Redis", style="cyan")
    
    if not is_redis_ready():
        handle_error("E4001", "Redis is not running.")
        press_enter_to_continue()
        return
    
    show_info("Analyzing keys (this may take a moment)...")
    console.print()
    
    result = run_redis_cli('KEYS "*"')
    if result.returncode != 0:
        handle_error("E4001", "Failed to get keys.")
        press_enter_to_continue()
        return
    
    keys = [k for k in result.stdout.strip().split('\n') if k]
    
    if not keys:
        show_info("No keys found.")
        press_enter_to_continue()
        return
    
    prefixes = {}
    sample_size = min(len(keys), 1000)
    
    import random
    sample_keys = random.sample(keys, sample_size) if len(keys) > sample_size else keys
    
    for key in sample_keys:
        prefix = key.split(':')[0] if ':' in key else key
        
        result = run_redis_cli(f'MEMORY USAGE "{key}"')
        try:
            mem = int(result.stdout.strip()) if result.returncode == 0 else 0
        except ValueError:
            mem = 0
        
        if prefix not in prefixes:
            prefixes[prefix] = {"count": 0, "memory": 0}
        prefixes[prefix]["count"] += 1
        prefixes[prefix]["memory"] += mem
    
    sorted_prefixes = sorted(prefixes.items(), key=lambda x: x[1]["memory"], reverse=True)
    
    columns = [
        {"name": "Prefix", "style": "cyan"},
        {"name": "Keys", "justify": "right"},
        {"name": "Memory", "justify": "right"},
    ]
    
    rows = []
    for prefix, data in sorted_prefixes[:20]:
        rows.append([
            prefix,
            str(data["count"]),
            format_size(data["memory"]),
        ])
    
    show_table(f"Analysis of {sample_size} keys (showing top 20 prefixes)", columns, rows, show_header=True)
    
    press_enter_to_continue()
