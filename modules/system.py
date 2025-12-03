"""System Setup module for vexo-cli."""

from ui.components import (
    console,
    show_panel,
    show_table,
    show_success,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import confirm_action, run_menu_loop
from utils.shell import (
    run_command,
    run_command_with_progress,
    run_command_realtime,
    is_installed,
    require_root,
    get_os_info,
    get_hostname,
    get_ip_address,
)


# List of basic tools to install
BASIC_TOOLS = [
    "curl",
    "wget",
    "git",
    "unzip",
    "zip",
    "htop",
    "vim",
    "software-properties-common",
    "apt-transport-https",
    "ca-certificates",
    "gnupg",
    "lsb-release",
]


def show_menu():
    """Display the System Setup submenu."""
    options = [
        ("info", "1. Show System Info"),
        ("update", "2. Update & Upgrade System"),
        ("tools", "3. Install Basic Tools"),
        ("back", "← Back to Main Menu"),
    ]
    
    handlers = {
        "info": show_system_info,
        "update": update_system,
        "tools": install_basic_tools,
    }
    
    run_menu_loop("System Setup & Update", options, handlers)


def update_system():
    """
    Update package lists and upgrade all packages.
    
    Runs: apt update && apt upgrade -y
    """
    clear_screen()
    show_header()
    show_panel("System Update & Upgrade", title="System Setup", style="cyan")
    
    if not confirm_action("This will update and upgrade all system packages. Continue?"):
        show_warning("Update cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print()
    show_info("Updating package lists...")
    
    result = run_command_with_progress(
        "apt update",
        "Updating package lists..."
    )
    
    if result.returncode != 0:
        show_error("Failed to update package lists.")
        if result.stderr:
            console.print(f"[dim]{result.stderr}[/dim]")
        press_enter_to_continue()
        return
    
    show_success("Package lists updated.")
    console.print()
    
    show_info("Upgrading packages (this may take a while)...")
    console.print()
    
    returncode = run_command_realtime(
        "apt upgrade -y",
        "Upgrading packages..."
    )
    
    console.print()
    if returncode == 0:
        show_success("System upgraded successfully!")
    else:
        show_error("Some packages may have failed to upgrade.")
    
    press_enter_to_continue()


def install_basic_tools():
    """
    Install essential tools for server management.
    
    Checks each tool before installing (idempotent).
    """
    clear_screen()
    show_header()
    show_panel("Install Basic Tools", title="System Setup", style="cyan")
    
    console.print("[bold]The following tools will be checked/installed:[/bold]")
    console.print()
    for tool in BASIC_TOOLS:
        console.print(f"  • {tool}")
    console.print()
    
    if not confirm_action("Proceed with installation?"):
        show_warning("Installation cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print()
    
    to_install = []
    already_installed = []
    
    for tool in BASIC_TOOLS:
        if is_installed(tool):
            already_installed.append(tool)
        else:
            to_install.append(tool)
    
    if already_installed:
        show_info(f"Already installed: {', '.join(already_installed)}")
        console.print()
    
    if not to_install:
        show_success("All basic tools are already installed!")
        press_enter_to_continue()
        return
    
    show_info(f"Installing: {', '.join(to_install)}")
    console.print()
    
    result = run_command_with_progress("apt update", "Updating package lists...")
    if result.returncode != 0:
        show_error("Failed to update package lists.")
        press_enter_to_continue()
        return
    
    packages = " ".join(to_install)
    returncode = run_command_realtime(
        f"apt install -y {packages}",
        f"Installing {len(to_install)} packages..."
    )
    
    console.print()
    if returncode == 0:
        show_success(f"Successfully installed {len(to_install)} tools!")
    else:
        show_warning("Some tools may have failed to install. Check the output above.")
    
    press_enter_to_continue()


def show_system_info():
    """
    Display system information including OS, hostname, and IP.
    """
    clear_screen()
    show_header()
    show_panel("System Information", title="System Setup", style="cyan")
    
    os_info = get_os_info()
    hostname = get_hostname()
    ip_address = get_ip_address()
    
    kernel = _get_kernel_version()
    uptime = _get_uptime()
    
    columns = [
        {"name": "Property", "style": "cyan"},
        {"name": "Value", "style": "white"},
    ]
    
    rows = [
        ["Operating System", f"{os_info['name']} {os_info['version']}"],
        ["Codename", os_info['codename']],
        ["Architecture", os_info['arch']],
        ["Kernel", kernel],
        ["Hostname", hostname],
        ["IP Address", ip_address],
        ["Uptime", uptime],
    ]
    
    show_table("", columns, rows, show_header=False)
    
    console.print()
    console.print("[bold]Basic Tools Status:[/bold]")
    console.print()
    
    tool_columns = [
        {"name": "Tool", "style": "white"},
        {"name": "Status", "justify": "center"},
    ]
    
    tool_rows = []
    for tool in BASIC_TOOLS[:8]:
        status = "[green]✓ Installed[/green]" if is_installed(tool) else "[red]✗ Not installed[/red]"
        tool_rows.append([tool, status])
    
    show_table("", tool_columns, tool_rows, show_header=True)
    
    press_enter_to_continue()


def _get_kernel_version():
    """Get the Linux kernel version."""
    try:
        result = run_command("uname -r", check=False, silent=True)
        return result.stdout.strip() if result.returncode == 0 else "Unknown"
    except Exception:
        return "Unknown"


def _get_uptime():
    """Get system uptime in human-readable format."""
    try:
        result = run_command("uptime -p", check=False, silent=True)
        if result.returncode == 0:
            return result.stdout.strip().replace("up ", "")
        return "Unknown"
    except Exception:
        return "Unknown"
