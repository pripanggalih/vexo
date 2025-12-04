"""Redis database management functions."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from modules.database.redis.utils import (
    is_redis_ready, run_redis_cli, get_db_keys_count,
)


def show_databases_menu():
    """Display Database Management submenu."""
    options = [
        ("list", "1. List Databases"),
        ("select", "2. Switch Database"),
        ("flush", "3. Flush Database"),
        ("flush_all", "4. Flush All Databases"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "list": list_databases,
        "select": switch_database,
        "flush": flush_database,
        "flush_all": flush_all_databases,
    }
    
    run_menu_loop("Database Management", options, handlers)


def list_databases():
    """List all Redis databases with key counts."""
    clear_screen()
    show_header()
    show_panel("Database List", title="Redis", style="cyan")
    
    if not is_redis_ready():
        show_error("Redis is not running.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Redis supports 16 databases (db0-db15) by default.[/bold]")
    console.print()
    
    db_keys = get_db_keys_count()
    
    columns = [
        {"name": "Database", "style": "cyan"},
        {"name": "Keys", "justify": "right"},
        {"name": "Status"},
    ]
    
    rows = []
    for i in range(16):
        db_name = f"db{i}"
        key_count = db_keys.get(db_name, 0)
        status = "[green]Has data[/green]" if key_count > 0 else "[dim]Empty[/dim]"
        rows.append([db_name, str(key_count), status])
    
    total_keys = sum(db_keys.values())
    show_table(f"Total: {total_keys} keys across all databases", columns, rows, show_header=True)
    
    press_enter_to_continue()


def switch_database():
    """Switch to a different database."""
    clear_screen()
    show_header()
    show_panel("Switch Database", title="Redis", style="cyan")
    
    if not is_redis_ready():
        show_error("Redis is not running.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Select a database to connect to.[/bold]")
    console.print("[dim]Note: This affects redis-cli commands only.[/dim]")
    console.print()
    
    db_keys = get_db_keys_count()
    
    options = []
    for i in range(16):
        db_name = f"db{i}"
        key_count = db_keys.get(db_name, 0)
        label = f"db{i} ({key_count} keys)"
        options.append(label)
    
    choice = select_from_list("Database", "Switch to:", options)
    if not choice:
        return
    
    db_num = choice.split()[0].replace("db", "")
    
    result = run_redis_cli(f"SELECT {db_num}")
    if result.returncode == 0:
        show_success(f"Switched to db{db_num}!")
        console.print("[dim]Use redis-cli with -n flag: redis-cli -n " + db_num + "[/dim]")
    else:
        show_error("Failed to switch database.")
    
    press_enter_to_continue()


def flush_database():
    """Flush a specific database."""
    clear_screen()
    show_header()
    show_panel("Flush Database", title="Redis", style="red")
    
    if not is_redis_ready():
        show_error("Redis is not running.")
        press_enter_to_continue()
        return
    
    db_keys = get_db_keys_count()
    
    options = []
    for i in range(16):
        db_name = f"db{i}"
        key_count = db_keys.get(db_name, 0)
        if key_count > 0:
            options.append(f"db{i} ({key_count} keys)")
    
    if not options:
        show_info("All databases are empty.")
        press_enter_to_continue()
        return
    
    choice = select_from_list("Database", "Flush:", options)
    if not choice:
        return
    
    db_num = choice.split()[0].replace("db", "")
    key_count = choice.split("(")[1].split()[0]
    
    show_warning(f"This will delete {key_count} keys from db{db_num}!")
    
    if not confirm_action(f"Flush db{db_num}?"):
        return
    
    run_redis_cli(f"SELECT {db_num}")
    result = run_redis_cli("FLUSHDB")
    
    if result.returncode == 0:
        show_success(f"Database db{db_num} flushed!")
    else:
        show_error("Failed to flush database.")
    
    press_enter_to_continue()


def flush_all_databases():
    """Flush all Redis databases."""
    clear_screen()
    show_header()
    show_panel("Flush All Databases", title="Redis", style="red")
    
    if not is_redis_ready():
        show_error("Redis is not running.")
        press_enter_to_continue()
        return
    
    db_keys = get_db_keys_count()
    total_keys = sum(db_keys.values())
    
    if total_keys == 0:
        show_info("All databases are already empty.")
        press_enter_to_continue()
        return
    
    show_warning(f"This will delete ALL {total_keys} keys from ALL databases!")
    console.print()
    
    console.print("[bold]Databases to be flushed:[/bold]")
    for db, count in db_keys.items():
        if count > 0:
            console.print(f"  • {db}: {count} keys")
    console.print()
    
    if not confirm_action("Flush ALL databases?"):
        return
    
    confirm_text = text_input("Type 'FLUSH ALL' to confirm:")
    if confirm_text != "FLUSH ALL":
        show_error("Confirmation text does not match.")
        press_enter_to_continue()
        return
    
    result = run_redis_cli("FLUSHALL")
    
    if result.returncode == 0:
        show_success("All databases flushed!")
    else:
        show_error("Failed to flush databases.")
    
    press_enter_to_continue()
