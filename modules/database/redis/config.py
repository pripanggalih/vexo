"""Redis configuration management."""

import os

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, require_root
from utils.error_handler import handle_error
from modules.database.redis.utils import (
    is_redis_ready, run_redis_cli, get_redis_config, set_redis_config,
)


def show_config_menu():
    """Display Configuration submenu."""
    options = [
        ("view", "1. View Configuration"),
        ("edit", "2. Edit Setting"),
        ("password", "3. Set Password"),
        ("bind", "4. Bind Address"),
        ("file", "5. View Config File"),
        ("rewrite", "6. Save to Config File"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "view": view_configuration,
        "edit": edit_setting,
        "password": set_password,
        "bind": bind_address,
        "file": view_config_file,
        "rewrite": save_config,
    }
    
    run_menu_loop("Configuration", options, handlers)


def view_configuration():
    """View current Redis configuration."""
    clear_screen()
    show_header()
    show_panel("Current Configuration", title="Redis", style="cyan")
    
    if not is_redis_ready():
        handle_error("E4001", "Redis is not running.")
        press_enter_to_continue()
        return
    
    important_settings = [
        "port",
        "bind",
        "requirepass",
        "maxmemory",
        "maxmemory-policy",
        "maxclients",
        "timeout",
        "tcp-keepalive",
        "databases",
        "save",
        "appendonly",
        "appendfsync",
        "loglevel",
        "logfile",
    ]
    
    columns = [
        {"name": "Setting", "style": "cyan"},
        {"name": "Value"},
    ]
    
    rows = []
    for setting in important_settings:
        value = get_redis_config(setting)
        if setting == "requirepass":
            value = "[green]SET[/green]" if value else "[dim]Not set[/dim]"
        elif not value:
            value = "[dim]Default[/dim]"
        rows.append([setting, value])
    
    show_table("", columns, rows, show_header=True)
    
    press_enter_to_continue()


def edit_setting():
    """Edit a Redis configuration setting."""
    clear_screen()
    show_header()
    show_panel("Edit Setting", title="Redis", style="cyan")
    
    if not is_redis_ready():
        handle_error("E4001", "Redis is not running.")
        press_enter_to_continue()
        return
    
    common_settings = [
        ("maxclients", "Maximum client connections"),
        ("timeout", "Client timeout (seconds)"),
        ("tcp-keepalive", "TCP keepalive (seconds)"),
        ("loglevel", "Log level (debug, verbose, notice, warning)"),
        ("slowlog-log-slower-than", "Slow log threshold (microseconds)"),
        ("slowlog-max-len", "Slow log max entries"),
        ("Custom", "Enter setting name manually"),
    ]
    
    options = [f"{s[0]} ({s[1]})" for s in common_settings]
    choice = select_from_list("Setting", "Edit:", options)
    
    if not choice:
        return
    
    setting_name = choice.split(" (")[0]
    
    if setting_name == "Custom":
        setting_name = text_input("Setting name:")
        if not setting_name:
            return
    
    current = get_redis_config(setting_name)
    console.print(f"[bold]Current value:[/bold] {current or 'Not set'}")
    
    new_value = text_input(f"New value for {setting_name}:")
    if not new_value:
        return
    
    result = set_redis_config(setting_name, new_value)
    
    if result.returncode == 0:
        show_success(f"Set {setting_name} = {new_value}")
        console.print("[dim]Use 'Save to Config File' to persist across restarts[/dim]")
    else:
        handle_error("E4001", "Failed to set configuration.")
    
    press_enter_to_continue()


def set_password():
    """Set or remove Redis password."""
    clear_screen()
    show_header()
    show_panel("Set Password", title="Redis", style="cyan")
    
    if not is_redis_ready():
        handle_error("E4001", "Redis is not running.")
        press_enter_to_continue()
        return
    
    current = get_redis_config("requirepass")
    has_password = bool(current)
    
    console.print(f"[bold]Password Status:[/bold] {'Set' if has_password else 'Not set'}")
    console.print()
    
    options = [
        "Set new password",
        "Remove password (disable auth)",
    ]
    
    choice = select_from_list("Action", "Select:", options)
    if not choice:
        return
    
    if "Set new" in choice:
        from getpass import getpass
        try:
            password = getpass("New password: ")
            confirm = getpass("Confirm password: ")
        except Exception:
            password = text_input("New password:")
            confirm = text_input("Confirm password:")
        
        if not password or not confirm:
            return
        
        if password != confirm:
            handle_error("E4001", "Passwords do not match.")
            press_enter_to_continue()
            return
        
        if len(password) < 8:
            show_warning("Password should be at least 8 characters.")
            if not confirm_action("Continue anyway?"):
                return
        
        result = set_redis_config("requirepass", password)
        
        if result.returncode == 0:
            show_success("Password set!")
            console.print("[dim]Clients must now use AUTH command[/dim]")
            console.print("[dim]Use 'Save to Config File' to persist[/dim]")
        else:
            handle_error("E4001", "Failed to set password.")
    
    else:
        if not confirm_action("Remove password protection?"):
            return
        
        result = set_redis_config("requirepass", "")
        
        if result.returncode == 0:
            show_success("Password removed!")
        else:
            handle_error("E4001", "Failed to remove password.")
    
    press_enter_to_continue()


def bind_address():
    """Configure bind address."""
    clear_screen()
    show_header()
    show_panel("Bind Address", title="Redis", style="cyan")
    
    if not is_redis_ready():
        handle_error("E4001", "Redis is not running.")
        press_enter_to_continue()
        return
    
    current = get_redis_config("bind")
    console.print(f"[bold]Current bind:[/bold] {current or '127.0.0.1'}")
    console.print()
    
    if "0.0.0.0" in str(current):
        console.print("[yellow]Warning: Redis is accessible from all interfaces![/yellow]")
    else:
        console.print("[green]Redis is bound to localhost only[/green]")
    console.print()
    
    options = [
        "127.0.0.1 (localhost only - secure)",
        "0.0.0.0 (all interfaces - requires password!)",
        "Custom IP address",
    ]
    
    choice = select_from_list("Bind Address", "Set to:", options)
    if not choice:
        return
    
    if "127.0.0.1" in choice:
        new_bind = "127.0.0.1"
    elif "0.0.0.0" in choice:
        show_warning("Binding to all interfaces exposes Redis to network!")
        if not confirm_action("Make sure password is set. Continue?"):
            return
        new_bind = "0.0.0.0"
    else:
        new_bind = text_input("IP address:")
        if not new_bind:
            return
    
    result = set_redis_config("bind", new_bind)
    
    if result.returncode == 0:
        show_success(f"Bind address set to {new_bind}!")
        show_warning("Restart Redis for this change to take effect.")
    else:
        handle_error("E4001", "Failed to set bind address.")
    
    press_enter_to_continue()


def view_config_file():
    """View Redis configuration file."""
    clear_screen()
    show_header()
    show_panel("Config File", title="Redis", style="cyan")
    
    config_paths = [
        "/etc/redis/redis.conf",
        "/etc/redis.conf",
    ]
    
    config_file = None
    for path in config_paths:
        if os.path.exists(path):
            config_file = path
            break
    
    if not config_file:
        handle_error("E4001", "Could not find Redis config file.")
        press_enter_to_continue()
        return
    
    console.print(f"[bold]Config File:[/bold] {config_file}")
    console.print()
    
    result = run_command(f"grep -v '^#' {config_file} | grep -v '^$' | head -50", check=False, silent=True)
    
    if result.returncode == 0:
        console.print(result.stdout)
    
    press_enter_to_continue()


def save_config():
    """Save current configuration to config file."""
    clear_screen()
    show_header()
    show_panel("Save Configuration", title="Redis", style="cyan")
    
    if not is_redis_ready():
        handle_error("E4001", "Redis is not running.")
        press_enter_to_continue()
        return
    
    console.print("[bold]This will save runtime configuration to redis.conf[/bold]")
    console.print("[dim]Changes made with CONFIG SET will be persisted.[/dim]")
    console.print()
    
    if not confirm_action("Save current configuration?"):
        return
    
    result = run_redis_cli("CONFIG REWRITE")
    
    if result.returncode == 0:
        show_success("Configuration saved to redis.conf!")
    else:
        handle_error("E4001", "Failed to save configuration.")
        console.print("[dim]Make sure Redis has write access to config file[/dim]")
    
    press_enter_to_continue()
