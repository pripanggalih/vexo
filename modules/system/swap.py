"""Swap management - status, create, remove."""

from utils.error_handler import handle_error
from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_success,
    
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, run_menu_loop
from utils.shell import run_command, run_command_with_progress, run_command_realtime, require_root


def show_swap_menu():
    """Display Swap Management submenu."""
    def get_status():
        swap_info = _get_swap_info()
        if swap_info['active']:
            return f"Swap: [green]{swap_info['size']}[/green] ({swap_info['used']} used)"
        return "Swap: [dim]Not configured[/dim]"
    
    options = [
        ("status", "1. Show Swap Status"),
        ("create", "2. Create Swap File"),
        ("remove", "3. Remove Swap"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "status": show_swap_status,
        "create": create_swap,
        "remove": remove_swap,
    }
    
    run_menu_loop("Swap Management", options, handlers, get_status)


def _get_swap_info():
    """Get swap information."""
    result = run_command("swapon --show --noheadings --bytes", check=False, silent=True)
    if result.returncode != 0 or not result.stdout.strip():
        return {'active': False, 'size': '0', 'used': '0', 'path': None}
    
    parts = result.stdout.strip().split()
    if len(parts) >= 3:
        path = parts[0]
        size_bytes = int(parts[2]) if parts[2].isdigit() else 0
        used_bytes = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
        
        size_gb = size_bytes / (1024**3)
        used_mb = used_bytes / (1024**2)
        
        return {
            'active': True,
            'size': f"{size_gb:.1f} GB",
            'used': f"{used_mb:.0f} MB",
            'path': path,
            'size_bytes': size_bytes,
        }
    
    return {'active': False, 'size': '0', 'used': '0', 'path': None}


def _get_ram_gb():
    """Get total RAM in GB."""
    result = run_command("grep MemTotal /proc/meminfo", check=False, silent=True)
    if result.returncode == 0:
        parts = result.stdout.split()
        if len(parts) >= 2:
            kb = int(parts[1])
            return kb / (1024**2)
    return 2


def show_swap_status():
    """Show detailed swap status."""
    clear_screen()
    show_header()
    show_panel("Swap Status", title="Swap Management", style="cyan")
    
    swap_info = _get_swap_info()
    ram_gb = _get_ram_gb()
    
    if ram_gb <= 2:
        recommended = f"{ram_gb * 2:.0f} GB (2x RAM)"
    else:
        recommended = f"{ram_gb:.0f} GB (equal to RAM)"
    
    columns = [
        {"name": "Property", "style": "cyan"},
        {"name": "Value", "style": "white"},
    ]
    
    rows = [
        ["Status", "[green]Active[/green]" if swap_info['active'] else "[dim]Inactive[/dim]"],
        ["Swap File", swap_info['path'] or "N/A"],
        ["Size", swap_info['size']],
        ["Used", swap_info['used']],
        ["Total RAM", f"{ram_gb:.1f} GB"],
        ["Recommended Swap", recommended],
    ]
    
    show_table("", columns, rows, show_header=False)
    
    result = run_command("cat /proc/sys/vm/swappiness", check=False, silent=True)
    swappiness = result.stdout.strip() if result.returncode == 0 else "Unknown"
    console.print()
    console.print(f"[dim]Swappiness: {swappiness} (lower = less swap usage)[/dim]")
    
    press_enter_to_continue()


def create_swap():
    """Create a new swap file."""
    clear_screen()
    show_header()
    show_panel("Create Swap File", title="Swap Management", style="cyan")
    
    swap_info = _get_swap_info()
    if swap_info['active']:
        show_warning(f"Swap already exists: {swap_info['path']} ({swap_info['size']})")
        if not confirm_action("Remove existing swap and create new one?"):
            press_enter_to_continue()
            return
    
    ram_gb = _get_ram_gb()
    if ram_gb <= 2:
        default_size = int(ram_gb * 2)
    else:
        default_size = int(ram_gb)
    
    if default_size < 1:
        default_size = 1
    
    console.print(f"RAM: {ram_gb:.1f} GB | Recommended swap: {default_size} GB")
    console.print()
    
    size_input = text_input(f"Swap size in GB (default: {default_size}):")
    if size_input:
        try:
            swap_size = int(size_input)
        except ValueError:
            handle_error("E1005", "Invalid size. Enter a number.")
            press_enter_to_continue()
            return
    else:
        swap_size = default_size
    
    if swap_size < 1 or swap_size > 64:
        handle_error("E1005", "Swap size must be between 1 and 64 GB.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if swap_info['active']:
        show_info("Removing existing swap...")
        run_command(f"swapoff {swap_info['path']}", check=False, silent=True)
        if swap_info['path']:
            run_command(f"rm -f {swap_info['path']}", check=False, silent=True)
    
    swapfile = "/swapfile"
    
    show_info(f"Creating {swap_size} GB swap file...")
    console.print()
    
    result = run_command_with_progress(
        f"fallocate -l {swap_size}G {swapfile}",
        "Allocating space..."
    )
    if result.returncode != 0:
        run_command_realtime(
            f"dd if=/dev/zero of={swapfile} bs=1G count={swap_size}",
            "Creating swap file..."
        )
    
    run_command(f"chmod 600 {swapfile}", check=False, silent=True)
    run_command(f"mkswap {swapfile}", check=False, silent=True)
    run_command(f"swapon {swapfile}", check=False, silent=True)
    
    result = run_command(f"grep -q '{swapfile}' /etc/fstab", check=False, silent=True)
    if result.returncode != 0:
        try:
            with open("/etc/fstab", "a") as f:
                f.write(f"{swapfile} none swap sw 0 0\n")
        except (PermissionError, IOError) as e:
            show_warning(f"Could not update /etc/fstab: {e}")
    
    console.print()
    if confirm_action("Set swappiness to 10? (recommended for VPS, default is 60)"):
        run_command("sysctl vm.swappiness=10", check=False, silent=True)
        result = run_command("grep -q 'vm.swappiness' /etc/sysctl.conf", check=False, silent=True)
        if result.returncode != 0:
            try:
                with open("/etc/sysctl.conf", "a") as f:
                    f.write("vm.swappiness=10\n")
            except (PermissionError, IOError):
                pass
        else:
            run_command("sed -i 's/vm.swappiness=.*/vm.swappiness=10/' /etc/sysctl.conf", check=False, silent=True)
    
    show_success(f"Swap file created: {swap_size} GB")
    press_enter_to_continue()


def remove_swap():
    """Remove swap file."""
    clear_screen()
    show_header()
    show_panel("Remove Swap", title="Swap Management", style="cyan")
    
    swap_info = _get_swap_info()
    if not swap_info['active']:
        show_info("No swap is currently active.")
        press_enter_to_continue()
        return
    
    show_warning(f"This will remove: {swap_info['path']} ({swap_info['size']})")
    
    if not confirm_action("Are you sure you want to remove swap?"):
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    swapfile = swap_info['path']
    
    run_command(f"swapoff {swapfile}", check=False, silent=True)
    run_command(f"rm -f {swapfile}", check=False, silent=True)
    run_command(f"sed -i '\\|{swapfile}|d' /etc/fstab", check=False, silent=True)
    
    show_success("Swap removed.")
    press_enter_to_continue()
