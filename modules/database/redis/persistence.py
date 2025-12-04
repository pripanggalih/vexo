"""Redis persistence configuration."""

from ui.components import (
    console, clear_screen, show_header, show_panel,
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
