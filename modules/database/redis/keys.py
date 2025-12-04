"""Redis key browser functions."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_warning, show_info, press_enter_to_continue,
)
from utils.error_handler import handle_error
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
        handle_error("E4001", "Redis is not running.")
        press_enter_to_continue()
        return
    
    pattern = text_input("Pattern (default: *):", default="*")
    if not pattern:
        pattern = "*"
    
    result = run_redis_cli(f'SCAN 0 MATCH "{pattern}" COUNT 100')
    
    if result.returncode != 0:
        handle_error("E4001", "Failed to scan keys.")
        press_enter_to_continue()
        return
    
    lines = result.stdout.strip().split('\n')
    if len(lines) < 2:
        show_info("No keys found.")
        press_enter_to_continue()
        return
    
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
    for key in keys[:50]:
        if not key:
            continue
        
        type_result = run_redis_cli(f'TYPE "{key}"')
        key_type = type_result.stdout.strip() if type_result.returncode == 0 else "?"
        
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
        handle_error("E4001", "Redis is not running.")
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
        handle_error("E4001", "Search failed.")
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
        handle_error("E4001", "Redis is not running.")
        press_enter_to_continue()
        return
    
    key = text_input("Key name:")
    if not key:
        return
    
    result = run_redis_cli(f'EXISTS "{key}"')
    if result.returncode != 0 or result.stdout.strip() == "0":
        handle_error("E4001", f"Key '{key}' does not exist.")
        press_enter_to_continue()
        return
    
    type_result = run_redis_cli(f'TYPE "{key}"')
    key_type = type_result.stdout.strip()
    
    console.print(f"[bold]Key:[/bold] {key}")
    console.print(f"[bold]Type:[/bold] {key_type}")
    console.print()
    
    if key_type == "string":
        result = run_redis_cli(f'GET "{key}"')
        console.print(f"[bold]Value:[/bold]")
        console.print(result.stdout[:1000])
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
        handle_error("E4001", "Redis is not running.")
        press_enter_to_continue()
        return
    
    key = text_input("Key to delete:")
    if not key:
        return
    
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
        result = run_redis_cli(f'EXISTS "{key}"')
        if result.stdout.strip() == "0":
            handle_error("E4001", f"Key '{key}' does not exist.")
            press_enter_to_continue()
            return
        
        if not confirm_action(f"Delete key '{key}'?"):
            return
        
        result = run_redis_cli(f'DEL "{key}"')
        if result.returncode == 0:
            show_success(f"Key '{key}' deleted!")
        else:
            handle_error("E4001", "Failed to delete key.")
    
    press_enter_to_continue()


def set_key_ttl():
    """Set expiry time for a key."""
    clear_screen()
    show_header()
    show_panel("Set TTL", title="Redis", style="cyan")
    
    if not is_redis_ready():
        handle_error("E4001", "Redis is not running.")
        press_enter_to_continue()
        return
    
    key = text_input("Key name:")
    if not key:
        return
    
    result = run_redis_cli(f'EXISTS "{key}"')
    if result.stdout.strip() == "0":
        handle_error("E4001", f"Key '{key}' does not exist.")
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
        handle_error("E4001", "Failed to set TTL.")
    
    press_enter_to_continue()
