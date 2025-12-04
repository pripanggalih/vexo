# Redis Enhancements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add advanced Redis management features including persistence configuration, memory management, key browser, database management, performance stats, and configuration editor.

**Architecture:** Create `modules/database/redis/` folder structure with separate files for each feature group. Uses `redis-cli` commands.

**Tech Stack:** Python, Redis, redis-cli

---

## Task 1: Create Redis Folder Structure

**Files:**
- Create: `modules/database/redis/__init__.py`
- Create: `modules/database/redis/utils.py`

**Step 1: Create modules/database/redis/utils.py**

```python
"""Shared utilities for Redis module."""

from utils.shell import run_command, is_installed, is_service_running


def is_redis_ready():
    """Check if Redis is installed and running."""
    return is_installed("redis-server") and is_service_running("redis-server")


def run_redis_cli(cmd, silent=True):
    """Run Redis CLI command."""
    return run_command(f'redis-cli {cmd}', check=False, silent=silent)


def redis_info(section=None):
    """Get Redis INFO output."""
    cmd = f"INFO {section}" if section else "INFO"
    result = run_redis_cli(cmd)
    if result.returncode != 0:
        return {}
    
    info = {}
    for line in result.stdout.strip().split('\n'):
        if ':' in line and not line.startswith('#'):
            key, value = line.split(':', 1)
            info[key.strip()] = value.strip()
    return info


def get_redis_config(key):
    """Get Redis configuration value."""
    result = run_redis_cli(f"CONFIG GET {key}")
    if result.returncode == 0 and result.stdout.strip():
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            return lines[1]
    return None


def set_redis_config(key, value):
    """Set Redis configuration value."""
    return run_redis_cli(f'CONFIG SET {key} "{value}"')


def format_size(size_bytes):
    """Format size in bytes to human readable."""
    try:
        size_bytes = int(size_bytes)
    except (ValueError, TypeError):
        return str(size_bytes)
    
    if size_bytes >= 1024 ** 3:
        return f"{size_bytes / 1024 ** 3:.2f} GB"
    elif size_bytes >= 1024 ** 2:
        return f"{size_bytes / 1024 ** 2:.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes} B"


def get_redis_version():
    """Get Redis version."""
    info = redis_info("server")
    return info.get("redis_version", "Unknown")


def get_db_keys_count():
    """Get key count per database."""
    info = redis_info("keyspace")
    dbs = {}
    for key, value in info.items():
        if key.startswith('db'):
            # Format: db0:keys=123,expires=45,avg_ttl=6789
            parts = dict(item.split('=') for item in value.split(','))
            dbs[key] = int(parts.get('keys', 0))
    return dbs
```

**Step 2: Create modules/database/redis/__init__.py**

```python
"""Redis management module."""

from ui.menu import run_menu_loop
from utils.shell import is_installed, is_service_running


def show_menu():
    """Display Redis Management submenu."""
    def get_status():
        if not is_installed("redis-server"):
            return "Redis: [yellow]Not installed[/yellow]"
        if is_service_running("redis-server"):
            return "Redis: [green]Running[/green]"
        return "Redis: [red]Stopped[/red]"
    
    def get_options():
        options = []
        if is_installed("redis-server"):
            options.extend([
                ("info", "1. Server Info"),
                ("keys", "2. Key Browser"),
                ("databases", "3. Database Management"),
                ("memory", "4. Memory Management"),
                ("persist", "5. Persistence Config"),
                ("stats", "6. Performance Stats"),
                ("config", "7. Configuration"),
                ("service", "8. Service Control"),
            ])
        else:
            options.append(("install", "1. Install Redis"))
        options.append(("back", "← Back"))
        return options
    
    def get_handlers():
        from modules.database.redis.core import (
            server_info, install_redis, service_control_menu,
        )
        from modules.database.redis.keys import show_keys_menu
        from modules.database.redis.databases import show_databases_menu
        from modules.database.redis.memory import show_memory_menu
        from modules.database.redis.persistence import show_persistence_menu
        from modules.database.redis.stats import show_stats_menu
        from modules.database.redis.config import show_config_menu
        
        return {
            "install": install_redis,
            "info": server_info,
            "keys": show_keys_menu,
            "databases": show_databases_menu,
            "memory": show_memory_menu,
            "persist": show_persistence_menu,
            "stats": show_stats_menu,
            "config": show_config_menu,
            "service": service_control_menu,
        }
    
    run_menu_loop("Redis Management", get_options, get_handlers(), get_status)
```

**Step 3: Commit**

```bash
git add modules/database/redis/
git commit -m "refactor(database): create Redis folder structure"
```

---

## Task 2: Create Redis Core Module

**Files:**
- Create: `modules/database/redis/core.py`

**Step 1: Create core.py**

```python
"""Redis core functions - install, info, service control."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, select_from_list, run_menu_loop
from utils.shell import run_command, is_installed, require_root, service_control
from modules.database.redis.utils import (
    is_redis_ready, redis_info, get_redis_version, format_size,
    get_db_keys_count,
)


def install_redis():
    """Install Redis."""
    clear_screen()
    show_header()
    show_panel("Install Redis", title="Database", style="cyan")
    
    if is_installed("redis-server"):
        show_info("Redis is already installed.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print("Installing Redis...")
    result = run_command("apt update && apt install -y redis-server", check=False)
    
    if result.returncode == 0:
        show_success("Redis installed successfully!")
    else:
        show_error("Installation failed!")
    
    press_enter_to_continue()


def server_info():
    """Show Redis server info."""
    clear_screen()
    show_header()
    show_panel("Server Info", title="Redis", style="cyan")
    
    if not is_redis_ready():
        show_error("Redis is not running.")
        press_enter_to_continue()
        return
    
    # Server info
    server = redis_info("server")
    memory = redis_info("memory")
    clients = redis_info("clients")
    stats = redis_info("stats")
    
    console.print(f"[bold]Version:[/bold] {server.get('redis_version', 'N/A')}")
    console.print(f"[bold]Mode:[/bold] {server.get('redis_mode', 'standalone')}")
    console.print(f"[bold]OS:[/bold] {server.get('os', 'N/A')}")
    console.print(f"[bold]Uptime:[/bold] {int(server.get('uptime_in_seconds', 0)) // 3600} hours")
    console.print()
    
    console.print(f"[bold]Used Memory:[/bold] {memory.get('used_memory_human', 'N/A')}")
    console.print(f"[bold]Peak Memory:[/bold] {memory.get('used_memory_peak_human', 'N/A')}")
    console.print(f"[bold]Max Memory:[/bold] {memory.get('maxmemory_human', 'unlimited')}")
    console.print()
    
    console.print(f"[bold]Connected Clients:[/bold] {clients.get('connected_clients', 'N/A')}")
    console.print(f"[bold]Blocked Clients:[/bold] {clients.get('blocked_clients', 'N/A')}")
    console.print()
    
    console.print(f"[bold]Total Commands:[/bold] {stats.get('total_commands_processed', 'N/A')}")
    console.print(f"[bold]Total Connections:[/bold] {stats.get('total_connections_received', 'N/A')}")
    console.print()
    
    # Key counts per database
    db_keys = get_db_keys_count()
    if db_keys:
        console.print("[bold]Keys per Database:[/bold]")
        for db, count in db_keys.items():
            console.print(f"  {db}: {count} keys")
    else:
        console.print("[dim]No keys in any database[/dim]")
    
    press_enter_to_continue()


def service_control_menu():
    """Service control menu."""
    clear_screen()
    show_header()
    show_panel("Service Control", title="Redis", style="cyan")
    
    from utils.shell import is_service_running
    running = is_service_running("redis-server")
    
    console.print(f"[bold]Status:[/bold] {'[green]Running[/green]' if running else '[red]Stopped[/red]'}")
    console.print()
    
    options = ["Start", "Stop", "Restart", "Enable (start on boot)", "Disable (don't start on boot)"]
    action = select_from_list("Action", "Select:", options)
    
    if not action:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    action_map = {
        "Start": "start",
        "Stop": "stop",
        "Restart": "restart",
        "Enable": "enable",
        "Disable": "disable",
    }
    
    for key, value in action_map.items():
        if action.startswith(key):
            service_control("redis-server", value)
            show_success(f"Redis {value}d!")
            break
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/database/redis/core.py
git commit -m "feat(database): add Redis core module"
```

---

## Task 3: Create Redis Key Browser Module

**Files:**
- Create: `modules/database/redis/keys.py`

**Step 1: Create keys.py**

```python
"""Redis key browser functions."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from modules.database.redis.utils import is_redis_ready, run_redis_cli


def show_keys_menu():
    """Display Key Browser submenu."""
    options = [
        ("browse", "1. Browse Keys"),
        ("search", "2. Search Keys"),
        ("view", "3. View Key Value"),
        ("delete", "4. Delete Key"),
        ("ttl", "5. Set TTL"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "browse": browse_keys,
        "search": search_keys,
        "view": view_key_value,
        "delete": delete_key,
        "ttl": set_key_ttl,
    }
    
    run_menu_loop("Key Browser", options, handlers)


def browse_keys():
    """Browse all keys with pagination."""
    clear_screen()
    show_header()
    show_panel("Browse Keys", title="Redis", style="cyan")
    
    if not is_redis_ready():
        show_error("Redis is not running.")
        press_enter_to_continue()
        return
    
    pattern = text_input("Pattern (default: *):", default="*")
    if not pattern:
        pattern = "*"
    
    # Use SCAN for safer iteration
    result = run_redis_cli(f'SCAN 0 MATCH "{pattern}" COUNT 100')
    
    if result.returncode != 0:
        show_error("Failed to scan keys.")
        press_enter_to_continue()
        return
    
    lines = result.stdout.strip().split('\n')
    if len(lines) < 2:
        show_info("No keys found.")
        press_enter_to_continue()
        return
    
    # First line is cursor, rest are keys
    keys = lines[1:]
    
    if not keys or keys == ['']:
        show_info("No keys found matching pattern.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Key", "style": "cyan"},
        {"name": "Type"},
        {"name": "TTL"},
    ]
    
    rows = []
    for key in keys[:50]:  # Limit display
        if not key:
            continue
        
        # Get type
        type_result = run_redis_cli(f'TYPE "{key}"')
        key_type = type_result.stdout.strip() if type_result.returncode == 0 else "?"
        
        # Get TTL
        ttl_result = run_redis_cli(f'TTL "{key}"')
        ttl = ttl_result.stdout.strip() if ttl_result.returncode == 0 else "?"
        if ttl == "-1":
            ttl = "[dim]No expiry[/dim]"
        elif ttl == "-2":
            ttl = "[red]Expired[/red]"
        else:
            ttl = f"{ttl}s"
        
        rows.append([key, key_type, ttl])
    
    show_table(f"Found {len(keys)} key(s) (showing first 50)", columns, rows, show_header=True)
    
    press_enter_to_continue()


def search_keys():
    """Search for keys by pattern."""
    clear_screen()
    show_header()
    show_panel("Search Keys", title="Redis", style="cyan")
    
    if not is_redis_ready():
        show_error("Redis is not running.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Pattern Examples:[/bold]")
    console.print("  user:*     - All keys starting with 'user:'")
    console.print("  *session*  - All keys containing 'session'")
    console.print("  cache:??   - Keys like 'cache:ab', 'cache:12'")
    console.print()
    
    pattern = text_input("Search pattern:")
    if not pattern:
        return
    
    result = run_redis_cli(f'KEYS "{pattern}"')
    
    if result.returncode != 0:
        show_error("Search failed.")
        press_enter_to_continue()
        return
    
    keys = [k for k in result.stdout.strip().split('\n') if k]
    
    if not keys:
        show_info("No keys found.")
    else:
        console.print(f"[bold]Found {len(keys)} key(s):[/bold]")
        for key in keys[:100]:
            console.print(f"  • {key}")
        if len(keys) > 100:
            console.print(f"  [dim]... and {len(keys) - 100} more[/dim]")
    
    press_enter_to_continue()


def view_key_value():
    """View value of a specific key."""
    clear_screen()
    show_header()
    show_panel("View Key Value", title="Redis", style="cyan")
    
    if not is_redis_ready():
        show_error("Redis is not running.")
        press_enter_to_continue()
        return
    
    key = text_input("Key name:")
    if not key:
        return
    
    # Check if key exists
    result = run_redis_cli(f'EXISTS "{key}"')
    if result.returncode != 0 or result.stdout.strip() == "0":
        show_error(f"Key '{key}' does not exist.")
        press_enter_to_continue()
        return
    
    # Get type
    type_result = run_redis_cli(f'TYPE "{key}"')
    key_type = type_result.stdout.strip()
    
    console.print(f"[bold]Key:[/bold] {key}")
    console.print(f"[bold]Type:[/bold] {key_type}")
    console.print()
    
    # Get value based on type
    if key_type == "string":
        result = run_redis_cli(f'GET "{key}"')
        console.print(f"[bold]Value:[/bold]")
        console.print(result.stdout[:1000])  # Limit output
    elif key_type == "list":
        result = run_redis_cli(f'LRANGE "{key}" 0 20')
        console.print(f"[bold]Values (first 20):[/bold]")
        for i, item in enumerate(result.stdout.strip().split('\n')):
            console.print(f"  {i}: {item}")
    elif key_type == "set":
        result = run_redis_cli(f'SMEMBERS "{key}"')
        console.print(f"[bold]Members:[/bold]")
        for item in result.stdout.strip().split('\n')[:20]:
            console.print(f"  • {item}")
    elif key_type == "hash":
        result = run_redis_cli(f'HGETALL "{key}"')
        console.print(f"[bold]Fields:[/bold]")
        lines = result.stdout.strip().split('\n')
        for i in range(0, min(len(lines), 40), 2):
            if i + 1 < len(lines):
                console.print(f"  {lines[i]}: {lines[i+1]}")
    elif key_type == "zset":
        result = run_redis_cli(f'ZRANGE "{key}" 0 20 WITHSCORES')
        console.print(f"[bold]Members (first 20):[/bold]")
        lines = result.stdout.strip().split('\n')
        for i in range(0, min(len(lines), 40), 2):
            if i + 1 < len(lines):
                console.print(f"  {lines[i]} (score: {lines[i+1]})")
    else:
        console.print(f"[dim]Cannot display value for type: {key_type}[/dim]")
    
    # Show TTL
    ttl_result = run_redis_cli(f'TTL "{key}"')
    ttl = ttl_result.stdout.strip()
    console.print()
    if ttl == "-1":
        console.print("[bold]TTL:[/bold] No expiry")
    else:
        console.print(f"[bold]TTL:[/bold] {ttl} seconds")
    
    press_enter_to_continue()


def delete_key():
    """Delete a key."""
    clear_screen()
    show_header()
    show_panel("Delete Key", title="Redis", style="red")
    
    if not is_redis_ready():
        show_error("Redis is not running.")
        press_enter_to_continue()
        return
    
    key = text_input("Key to delete:")
    if not key:
        return
    
    # Check wildcard
    if '*' in key or '?' in key:
        show_warning("Deleting multiple keys with pattern!")
        result = run_redis_cli(f'KEYS "{key}"')
        keys = [k for k in result.stdout.strip().split('\n') if k]
        
        if not keys:
            show_info("No matching keys found.")
            press_enter_to_continue()
            return
        
        console.print(f"[yellow]This will delete {len(keys)} key(s):[/yellow]")
        for k in keys[:10]:
            console.print(f"  • {k}")
        if len(keys) > 10:
            console.print(f"  ... and {len(keys) - 10} more")
        console.print()
        
        if not confirm_action(f"Delete all {len(keys)} keys?"):
            return
        
        deleted = 0
        for k in keys:
            result = run_redis_cli(f'DEL "{k}"')
            if result.returncode == 0:
                deleted += 1
        
        show_success(f"Deleted {deleted} key(s)!")
    else:
        # Single key
        result = run_redis_cli(f'EXISTS "{key}"')
        if result.stdout.strip() == "0":
            show_error(f"Key '{key}' does not exist.")
            press_enter_to_continue()
            return
        
        if not confirm_action(f"Delete key '{key}'?"):
            return
        
        result = run_redis_cli(f'DEL "{key}"')
        if result.returncode == 0:
            show_success(f"Key '{key}' deleted!")
        else:
            show_error("Failed to delete key.")
    
    press_enter_to_continue()


def set_key_ttl():
    """Set expiry time for a key."""
    clear_screen()
    show_header()
    show_panel("Set TTL", title="Redis", style="cyan")
    
    if not is_redis_ready():
        show_error("Redis is not running.")
        press_enter_to_continue()
        return
    
    key = text_input("Key name:")
    if not key:
        return
    
    result = run_redis_cli(f'EXISTS "{key}"')
    if result.stdout.strip() == "0":
        show_error(f"Key '{key}' does not exist.")
        press_enter_to_continue()
        return
    
    options = [
        "1 minute",
        "5 minutes",
        "1 hour",
        "1 day",
        "1 week",
        "Remove expiry (persist)",
        "Custom (seconds)",
    ]
    
    choice = select_from_list("TTL", "Set expiry:", options)
    if not choice:
        return
    
    if "1 minute" in choice:
        seconds = 60
    elif "5 minutes" in choice:
        seconds = 300
    elif "1 hour" in choice:
        seconds = 3600
    elif "1 day" in choice:
        seconds = 86400
    elif "1 week" in choice:
        seconds = 604800
    elif "Remove" in choice:
        result = run_redis_cli(f'PERSIST "{key}"')
        if result.returncode == 0:
            show_success(f"Expiry removed from '{key}'!")
        press_enter_to_continue()
        return
    else:
        seconds_input = text_input("Seconds:")
        if not seconds_input or not seconds_input.isdigit():
            return
        seconds = int(seconds_input)
    
    result = run_redis_cli(f'EXPIRE "{key}" {seconds}')
    if result.returncode == 0:
        show_success(f"TTL set to {seconds} seconds!")
    else:
        show_error("Failed to set TTL.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/database/redis/keys.py
git commit -m "feat(database): add Redis key browser"
```

---

## Task 4: Create Redis Memory Module

**Files:**
- Create: `modules/database/redis/memory.py`

**Step 1: Create memory.py**

```python
"""Redis memory management functions."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import require_root
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
        show_error("Redis is not running.")
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
    
    # Check fragmentation
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
        show_error("Redis is not running.")
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
        show_error("Failed to set max memory.")
    
    press_enter_to_continue()


def eviction_policy():
    """Configure eviction policy."""
    clear_screen()
    show_header()
    show_panel("Eviction Policy", title="Redis", style="cyan")
    
    if not is_redis_ready():
        show_error("Redis is not running.")
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
        show_error("Failed to set policy.")
    
    press_enter_to_continue()


def memory_analysis():
    """Analyze memory usage by key patterns."""
    clear_screen()
    show_header()
    show_panel("Memory Analysis", title="Redis", style="cyan")
    
    if not is_redis_ready():
        show_error("Redis is not running.")
        press_enter_to_continue()
        return
    
    show_info("Analyzing keys (this may take a moment)...")
    console.print()
    
    # Get all keys and their memory usage
    result = run_redis_cli('KEYS "*"')
    if result.returncode != 0:
        show_error("Failed to get keys.")
        press_enter_to_continue()
        return
    
    keys = [k for k in result.stdout.strip().split('\n') if k]
    
    if not keys:
        show_info("No keys found.")
        press_enter_to_continue()
        return
    
    # Analyze by prefix
    prefixes = {}
    sample_size = min(len(keys), 1000)  # Limit for performance
    
    import random
    sample_keys = random.sample(keys, sample_size) if len(keys) > sample_size else keys
    
    for key in sample_keys:
        # Get prefix (first part before :)
        prefix = key.split(':')[0] if ':' in key else key
        
        # Get memory usage
        result = run_redis_cli(f'MEMORY USAGE "{key}"')
        try:
            mem = int(result.stdout.strip()) if result.returncode == 0 else 0
        except ValueError:
            mem = 0
        
        if prefix not in prefixes:
            prefixes[prefix] = {"count": 0, "memory": 0}
        prefixes[prefix]["count"] += 1
        prefixes[prefix]["memory"] += mem
    
    # Sort by memory usage
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
```

**Step 2: Commit**

```bash
git add modules/database/redis/memory.py
git commit -m "feat(database): add Redis memory management"
```

---

## Task 5: Create Redis Persistence Module

**Files:**
- Create: `modules/database/redis/persistence.py`

**Step 1: Create persistence.py**

```python
"""Redis persistence configuration."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from modules.database.redis.utils import (
    is_redis_ready, redis_info, run_redis_cli, get_redis_config,
    set_redis_config,
)


def show_persistence_menu():
    """Display Persistence submenu."""
    options = [
        ("status", "1. Persistence Status"),
        ("rdb", "2. RDB Configuration"),
        ("aof", "3. AOF Configuration"),
        ("save", "4. Trigger Save Now"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "status": persistence_status,
        "rdb": rdb_config,
        "aof": aof_config,
        "save": trigger_save,
    }
    
    run_menu_loop("Persistence", options, handlers)


def persistence_status():
    """Show current persistence status."""
    clear_screen()
    show_header()
    show_panel("Persistence Status", title="Redis", style="cyan")
    
    if not is_redis_ready():
        show_error("Redis is not running.")
        press_enter_to_continue()
        return
    
    persistence = redis_info("persistence")
    
    console.print("[bold]RDB Snapshots:[/bold]")
    console.print(f"  Loading: {persistence.get('loading', 'N/A')}")
    console.print(f"  Last Save Time: {persistence.get('rdb_last_save_time', 'N/A')}")
    console.print(f"  Last Save Status: {persistence.get('rdb_last_bgsave_status', 'N/A')}")
    console.print(f"  Changes Since Save: {persistence.get('rdb_changes_since_last_save', 'N/A')}")
    console.print(f"  Current Save: {persistence.get('rdb_current_bgsave_time_sec', '-1')} sec")
    console.print()
    
    aof_enabled = persistence.get('aof_enabled', '0') == '1'
    console.print("[bold]AOF (Append Only File):[/bold]")
    console.print(f"  Enabled: {'Yes' if aof_enabled else 'No'}")
    
    if aof_enabled:
        console.print(f"  Rewrite In Progress: {persistence.get('aof_rewrite_in_progress', 'N/A')}")
        console.print(f"  Last Rewrite Status: {persistence.get('aof_last_bgrewrite_status', 'N/A')}")
        console.print(f"  Current Size: {persistence.get('aof_current_size', 'N/A')} bytes")
        console.print(f"  Base Size: {persistence.get('aof_base_size', 'N/A')} bytes")
    
    console.print()
    
    # Recommendations
    if not aof_enabled:
        show_info("AOF is disabled. Consider enabling for better durability.")
    
    press_enter_to_continue()


def rdb_config():
    """Configure RDB snapshots."""
    clear_screen()
    show_header()
    show_panel("RDB Configuration", title="Redis", style="cyan")
    
    if not is_redis_ready():
        show_error("Redis is not running.")
        press_enter_to_continue()
        return
    
    console.print("[bold]RDB Snapshots save data at intervals.[/bold]")
    console.print("[dim]Format: SAVE seconds changes - save if changes occur within seconds[/dim]")
    console.print()
    
    # Current save rules
    result = run_redis_cli("CONFIG GET save")
    current = result.stdout.strip().split('\n')[1] if result.returncode == 0 else ""
    console.print(f"[bold]Current save rules:[/bold] {current or 'disabled'}")
    console.print()
    
    presets = [
        ("Default (recommended)", "3600 1 300 100 60 10000"),
        ("High durability", "900 1 300 10 60 1000"),
        ("Performance (less frequent)", "3600 1"),
        ("Disable RDB", ""),
        ("Custom", None),
    ]
    
    options = [p[0] for p in presets]
    choice = select_from_list("Select Preset", "Configure:", options)
    
    if not choice:
        return
    
    for name, value in presets:
        if choice == name:
            if value is None:
                value = text_input("Save rules (e.g., 3600 1 300 100):")
                if not value:
                    return
            
            result = set_redis_config("save", value)
            if result.returncode == 0:
                show_success("RDB configuration updated!")
            else:
                show_error("Failed to update configuration.")
            break
    
    press_enter_to_continue()


def aof_config():
    """Configure AOF persistence."""
    clear_screen()
    show_header()
    show_panel("AOF Configuration", title="Redis", style="cyan")
    
    if not is_redis_ready():
        show_error("Redis is not running.")
        press_enter_to_continue()
        return
    
    console.print("[bold]AOF (Append Only File) logs every write operation.[/bold]")
    console.print("[dim]Provides better durability than RDB at cost of disk space.[/dim]")
    console.print()
    
    # Current status
    aof_enabled = get_redis_config("appendonly")
    aof_fsync = get_redis_config("appendfsync")
    
    console.print(f"[bold]AOF Enabled:[/bold] {aof_enabled or 'no'}")
    console.print(f"[bold]Fsync Policy:[/bold] {aof_fsync or 'everysec'}")
    console.print()
    
    options = [
        "Enable AOF",
        "Disable AOF",
        "Set fsync to 'always' (safest, slow)",
        "Set fsync to 'everysec' (balanced)",
        "Set fsync to 'no' (fastest, risky)",
    ]
    
    choice = select_from_list("Action", "Configure:", options)
    
    if not choice:
        return
    
    if "Enable" in choice:
        set_redis_config("appendonly", "yes")
        show_success("AOF enabled!")
    elif "Disable" in choice:
        set_redis_config("appendonly", "no")
        show_success("AOF disabled!")
    elif "always" in choice:
        set_redis_config("appendfsync", "always")
        show_success("Fsync set to 'always'!")
    elif "everysec" in choice:
        set_redis_config("appendfsync", "everysec")
        show_success("Fsync set to 'everysec'!")
    elif "'no'" in choice:
        set_redis_config("appendfsync", "no")
        show_success("Fsync set to 'no'!")
    
    press_enter_to_continue()


def trigger_save():
    """Trigger immediate save."""
    clear_screen()
    show_header()
    show_panel("Trigger Save", title="Redis", style="cyan")
    
    if not is_redis_ready():
        show_error("Redis is not running.")
        press_enter_to_continue()
        return
    
    options = [
        "BGSAVE (background save - non-blocking)",
        "SAVE (foreground save - blocks Redis)",
        "BGREWRITEAOF (rewrite AOF file)",
    ]
    
    choice = select_from_list("Save Type", "Trigger:", options)
    
    if not choice:
        return
    
    if "BGSAVE" in choice:
        result = run_redis_cli("BGSAVE")
        if result.returncode == 0:
            show_success("Background save started!")
        else:
            show_error("Failed to start background save.")
    elif "SAVE" in choice:
        show_warning("This will block Redis until complete!")
        if confirm_action("Continue?"):
            result = run_redis_cli("SAVE")
            if result.returncode == 0:
                show_success("Save completed!")
            else:
                show_error("Save failed.")
    elif "BGREWRITEAOF" in choice:
        result = run_redis_cli("BGREWRITEAOF")
        if result.returncode == 0:
            show_success("AOF rewrite started!")
        else:
            show_error("Failed to start AOF rewrite.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/database/redis/persistence.py
git commit -m "feat(database): add Redis persistence configuration"
```

---

## Task 6: Create Remaining Redis Modules

Create `databases.py`, `stats.py`, and `config.py` following the same pattern.

**Files:**
- Create: `modules/database/redis/databases.py` (database switching, flush)
- Create: `modules/database/redis/stats.py` (performance metrics)
- Create: `modules/database/redis/config.py` (config editor, password)

---

## Execution Handoff

Plan complete and saved to `docs/plans/2025-01-15-database-03-redis.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
