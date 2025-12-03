"""System cleanup - autoremove, clean cache, old kernels, journals."""

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_success,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import confirm_action
from utils.shell import run_command, run_command_realtime, require_root


def system_cleanup():
    """Clean up system: remove unused packages, clean cache, old kernels."""
    clear_screen()
    show_header()
    show_panel("System Cleanup", title="System Setup", style="cyan")
    
    console.print("[bold]This will:[/bold]")
    console.print("  • Remove unused packages (apt autoremove)")
    console.print("  • Clean apt cache (apt clean)")
    console.print("  • Remove old kernels (keep current + 1)")
    console.print("  • Clear journal logs older than 7 days")
    console.print()
    
    result = run_command("apt-get --dry-run autoremove 2>/dev/null | grep -oP '\\d+(?= to remove)'", check=False, silent=True)
    packages_to_remove = result.stdout.strip() if result.returncode == 0 else "0"
    
    result = run_command("du -sh /var/cache/apt/archives 2>/dev/null | cut -f1", check=False, silent=True)
    cache_size = result.stdout.strip() if result.returncode == 0 else "Unknown"
    
    result = run_command("journalctl --disk-usage 2>/dev/null | grep -oP '[\\d.]+[GMK]'", check=False, silent=True)
    journal_size = result.stdout.strip() if result.returncode == 0 else "Unknown"
    
    console.print(f"[dim]Packages to remove: {packages_to_remove}[/dim]")
    console.print(f"[dim]Apt cache size: {cache_size}[/dim]")
    console.print(f"[dim]Journal size: {journal_size}[/dim]")
    console.print()
    
    if not confirm_action("Proceed with cleanup?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print()
    
    show_info("Removing unused packages...")
    run_command_realtime("apt autoremove -y", "Autoremove...")
    
    show_info("Cleaning apt cache...")
    run_command("apt clean", check=False, silent=True)
    show_success("Apt cache cleaned.")
    
    show_info("Checking old kernels...")
    current_kernel = run_command("uname -r", check=False, silent=True).stdout.strip()
    result = run_command(
        f"dpkg -l 'linux-image-*' | grep '^ii' | awk '{{print $2}}' | grep -v '{current_kernel}' | head -n -1",
        check=False, silent=True
    )
    old_kernels = [k.strip() for k in result.stdout.strip().split('\n') if k.strip() and 'linux-image' in k]
    
    if old_kernels:
        show_info(f"Removing {len(old_kernels)} old kernel(s)...")
        for kernel in old_kernels:
            run_command(f"apt remove -y {kernel}", check=False, silent=True)
    else:
        show_info("No old kernels to remove.")
    
    show_info("Cleaning journal logs...")
    run_command("journalctl --vacuum-time=7d", check=False, silent=True)
    show_success("Journal cleaned.")
    
    console.print()
    show_success("System cleanup completed!")
    press_enter_to_continue()
