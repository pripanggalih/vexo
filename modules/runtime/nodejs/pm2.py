"""PM2 Process Manager integration."""

import json

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import require_root
from modules.runtime.nodejs.utils import (
    run_with_nvm, run_with_nvm_realtime, is_pm2_installed, get_pm2_version,
)


def show_pm2_menu():
    """Display PM2 Process Manager submenu."""
    def get_status():
        if is_pm2_installed():
            version = get_pm2_version()
            return f"PM2: [green]{version}[/green]"
        return "PM2: [yellow]Not installed[/yellow]"
    
    options = [
        ("install", "1. Install PM2"),
        ("list", "2. List Processes"),
        ("control", "3. Start/Stop/Restart"),
        ("logs", "4. View Logs"),
        ("monit", "5. Monitoring"),
        ("startup", "6. Startup Script"),
        ("save", "7. Save/Restore"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "install": install_pm2,
        "list": list_processes,
        "control": process_control,
        "logs": view_logs,
        "monit": pm2_monit,
        "startup": setup_startup,
        "save": save_restore,
    }
    
    run_menu_loop("PM2 Process Manager", options, handlers, get_status)


def install_pm2():
    """Install PM2 globally."""
    clear_screen()
    show_header()
    show_panel("Install PM2", title="PM2 Manager", style="cyan")
    
    if is_pm2_installed():
        version = get_pm2_version()
        show_info(f"PM2 is already installed (v{version}).")
        if not confirm_action("Reinstall/update PM2?"):
            press_enter_to_continue()
            return
    
    console.print()
    returncode = run_with_nvm_realtime("npm install -g pm2", "Installing PM2...")
    
    if returncode == 0:
        show_success("PM2 installed successfully!")
        version = get_pm2_version()
        if version:
            console.print(f"[dim]Version: {version}[/dim]")
    else:
        show_error("Failed to install PM2.")
    
    press_enter_to_continue()


def list_processes():
    """List all PM2 processes."""
    clear_screen()
    show_header()
    show_panel("PM2 Processes", title="PM2 Manager", style="cyan")
    
    if not is_pm2_installed():
        show_error("PM2 is not installed.")
        press_enter_to_continue()
        return
    
    # Get process list as JSON
    result = run_with_nvm("pm2 jlist")
    
    if result is None or result.returncode != 0:
        show_error("Failed to get process list.")
        press_enter_to_continue()
        return
    
    try:
        processes = json.loads(result.stdout)
    except json.JSONDecodeError:
        show_error("Failed to parse process list.")
        press_enter_to_continue()
        return
    
    if not processes:
        show_info("No processes running.")
        console.print()
        console.print("[dim]Use 'Start/Stop/Restart' to start an app.[/dim]")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "ID", "style": "cyan", "justify": "right"},
        {"name": "Name", "style": "white"},
        {"name": "Status", "justify": "center"},
        {"name": "CPU", "justify": "right"},
        {"name": "Memory", "justify": "right"},
        {"name": "Restarts", "justify": "right"},
        {"name": "Uptime"},
    ]
    
    rows = []
    for proc in processes:
        pm2_env = proc.get("pm2_env", {})
        monit = proc.get("monit", {})
        
        pid = str(proc.get("pm_id", "?"))
        name = proc.get("name", "unknown")
        status = pm2_env.get("status", "unknown")
        
        if status == "online":
            status_str = "[green]online[/green]"
        elif status == "stopped":
            status_str = "[yellow]stopped[/yellow]"
        else:
            status_str = f"[red]{status}[/red]"
        
        cpu = f"{monit.get('cpu', 0)}%"
        memory_bytes = monit.get("memory", 0)
        memory = f"{memory_bytes / 1024 / 1024:.1f}MB"
        restarts = str(pm2_env.get("restart_time", 0))
        
        # Calculate uptime
        uptime = "-"
        if pm2_env.get("pm_uptime"):
            import time
            uptime_ms = time.time() * 1000 - pm2_env["pm_uptime"]
            uptime_sec = uptime_ms / 1000
            if uptime_sec < 60:
                uptime = f"{int(uptime_sec)}s"
            elif uptime_sec < 3600:
                uptime = f"{int(uptime_sec / 60)}m"
            elif uptime_sec < 86400:
                uptime = f"{int(uptime_sec / 3600)}h"
            else:
                uptime = f"{int(uptime_sec / 86400)}d"
        
        rows.append([pid, name, status_str, cpu, memory, restarts, uptime])
    
    show_table(f"Total: {len(processes)} process(es)", columns, rows, show_header=True)
    press_enter_to_continue()


def process_control():
    """Start/Stop/Restart PM2 processes."""
    clear_screen()
    show_header()
    show_panel("Process Control", title="PM2 Manager", style="cyan")
    
    if not is_pm2_installed():
        show_error("PM2 is not installed.")
        press_enter_to_continue()
        return
    
    # Options
    actions = [
        "Start new app",
        "Stop app",
        "Restart app",
        "Reload app (0-downtime)",
        "Delete app from PM2",
        "Stop all",
        "Restart all",
    ]
    
    action = select_from_list("Select Action", "What to do?", actions)
    if not action:
        return
    
    if action == "Start new app":
        _start_new_app()
    elif action == "Stop all":
        run_with_nvm_realtime("pm2 stop all", "Stopping all...")
        show_success("All processes stopped!")
        press_enter_to_continue()
    elif action == "Restart all":
        run_with_nvm_realtime("pm2 restart all", "Restarting all...")
        show_success("All processes restarted!")
        press_enter_to_continue()
    else:
        # Need to select a process
        processes = _get_process_names()
        if not processes:
            show_info("No processes found.")
            press_enter_to_continue()
            return
        
        proc = select_from_list("Select Process", "Choose:", processes)
        if not proc:
            return
        
        if "Stop" in action:
            run_with_nvm_realtime(f"pm2 stop {proc}", f"Stopping {proc}...")
            show_success(f"{proc} stopped!")
        elif "Restart" in action:
            run_with_nvm_realtime(f"pm2 restart {proc}", f"Restarting {proc}...")
            show_success(f"{proc} restarted!")
        elif "Reload" in action:
            run_with_nvm_realtime(f"pm2 reload {proc}", f"Reloading {proc}...")
            show_success(f"{proc} reloaded!")
        elif "Delete" in action:
            if confirm_action(f"Delete {proc} from PM2?"):
                run_with_nvm_realtime(f"pm2 delete {proc}", f"Deleting {proc}...")
                show_success(f"{proc} deleted!")
        
        press_enter_to_continue()


def _start_new_app():
    """Start a new app in PM2."""
    console.print()
    
    # Get app path
    app_path = text_input("Enter app path (e.g., /var/www/myapp/server.js):")
    if not app_path:
        return
    
    # Get app name
    import os
    default_name = os.path.basename(os.path.dirname(app_path))
    app_name = text_input("App name:", default=default_name)
    if not app_name:
        return
    
    # Build command
    cmd = f"pm2 start {app_path} --name {app_name}"
    
    # Options
    if confirm_action("Configure advanced options?"):
        instances = text_input("Instances (number or 'max'):", default="1")
        if instances and instances != "1":
            cmd += f" -i {instances}"
        
        if confirm_action("Watch for file changes?"):
            cmd += " --watch"
        
        max_memory = text_input("Max memory restart (e.g., 500M):", default="")
        if max_memory:
            cmd += f" --max-memory-restart {max_memory}"
    
    console.print()
    returncode = run_with_nvm_realtime(cmd, f"Starting {app_name}...")
    
    if returncode == 0:
        show_success(f"{app_name} started!")
    else:
        show_error(f"Failed to start {app_name}.")
    
    press_enter_to_continue()


def _get_process_names():
    """Get list of PM2 process names."""
    result = run_with_nvm("pm2 jlist")
    if result is None or result.returncode != 0:
        return []
    
    try:
        processes = json.loads(result.stdout)
        return [p.get("name", f"id:{p.get('pm_id')}") for p in processes]
    except json.JSONDecodeError:
        return []


def view_logs():
    """View PM2 logs."""
    clear_screen()
    show_header()
    show_panel("View Logs", title="PM2 Manager", style="cyan")
    
    if not is_pm2_installed():
        show_error("PM2 is not installed.")
        press_enter_to_continue()
        return
    
    processes = _get_process_names()
    processes.insert(0, "(All processes)")
    
    proc = select_from_list("Select Process", "View logs for:", processes)
    if not proc:
        return
    
    lines = text_input("Number of lines:", default="50")
    
    console.print()
    console.print("[dim]Press Ctrl+C to exit logs[/dim]")
    console.print()
    
    if proc == "(All processes)":
        cmd = f"pm2 logs --lines {lines} --nostream"
    else:
        cmd = f"pm2 logs {proc} --lines {lines} --nostream"
    
    result = run_with_nvm(cmd)
    if result and result.returncode == 0:
        console.print(result.stdout)
    
    press_enter_to_continue()


def pm2_monit():
    """Launch PM2 monitoring."""
    clear_screen()
    show_header()
    show_panel("PM2 Monitoring", title="PM2 Manager", style="cyan")
    
    if not is_pm2_installed():
        show_error("PM2 is not installed.")
        press_enter_to_continue()
        return
    
    console.print("Launching PM2 monitoring dashboard...")
    console.print("[dim]Press Ctrl+C or 'q' to exit[/dim]")
    console.print()
    
    # Run interactively
    import os
    from config import NVM_DIR
    nvm_script = os.path.join(NVM_DIR, "nvm.sh")
    os.system(f'bash -c "source {nvm_script} && pm2 monit"')
    
    press_enter_to_continue()


def setup_startup():
    """Setup PM2 startup script."""
    clear_screen()
    show_header()
    show_panel("Startup Script", title="PM2 Manager", style="cyan")
    
    if not is_pm2_installed():
        show_error("PM2 is not installed.")
        press_enter_to_continue()
        return
    
    console.print("[bold]PM2 Startup Script[/bold]")
    console.print()
    console.print("This will configure PM2 to start automatically on system boot.")
    console.print()
    
    if not confirm_action("Generate startup script?"):
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print()
    
    # Generate startup script
    result = run_with_nvm("pm2 startup systemd -u $USER --hp $HOME")
    
    if result and result.returncode == 0:
        show_success("Startup script configured!")
        console.print()
        console.print("[dim]PM2 will now start on boot.[/dim]")
        console.print("[dim]Don't forget to run 'pm2 save' to save current processes.[/dim]")
    else:
        show_error("Failed to setup startup script.")
        if result:
            console.print(f"[dim]{result.stderr}[/dim]")
    
    press_enter_to_continue()


def save_restore():
    """Save or restore PM2 process list."""
    clear_screen()
    show_header()
    show_panel("Save/Restore", title="PM2 Manager", style="cyan")
    
    if not is_pm2_installed():
        show_error("PM2 is not installed.")
        press_enter_to_continue()
        return
    
    options = [
        "Save current processes",
        "Restore saved processes",
    ]
    
    choice = select_from_list("Action", "What to do?", options)
    if not choice:
        return
    
    console.print()
    
    if "Save" in choice:
        result = run_with_nvm("pm2 save")
        if result and result.returncode == 0:
            show_success("Process list saved!")
            console.print("[dim]Processes will be restored on PM2 startup.[/dim]")
        else:
            show_error("Failed to save process list.")
    else:
        result = run_with_nvm("pm2 resurrect")
        if result and result.returncode == 0:
            show_success("Process list restored!")
        else:
            show_error("Failed to restore process list.")
    
    press_enter_to_continue()
