"""Backup and restore for vexo-cli cron."""

import os
from datetime import datetime

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_success,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import confirm_action, select_from_list
from utils.shell import run_command, require_root

from modules.cron.common import (
    CRON_BACKUP_DIR,
    CRON_USER,
    get_crontab_lines,
)


def backup_crontab():
    """Backup current crontab to file."""
    clear_screen()
    show_header()
    show_panel("Backup Crontab", title="Cron Jobs", style="cyan")
    
    lines = get_crontab_lines()
    
    if not lines:
        show_info("Crontab is empty, nothing to backup.")
        press_enter_to_continue()
        return
    
    console.print(f"[bold]Current crontab ({len(lines)} lines):[/bold]")
    console.print()
    for line in lines[:10]:
        console.print(f"  {line}")
    if len(lines) > 10:
        console.print(f"  [dim]... and {len(lines) - 10} more lines[/dim]")
    console.print()
    
    if not confirm_action("Create backup?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    os.makedirs(CRON_BACKUP_DIR, mode=0o755, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_file = os.path.join(CRON_BACKUP_DIR, f"crontab-{timestamp}.txt")
    
    try:
        with open(backup_file, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        
        show_success("Crontab backed up!")
        console.print()
        console.print(f"[dim]File: {backup_file}[/dim]")
    except IOError as e:
        show_error(f"Failed to create backup: {e}")
    
    press_enter_to_continue()


def restore_crontab():
    """Restore crontab from backup file."""
    clear_screen()
    show_header()
    show_panel("Restore Crontab", title="Cron Jobs", style="cyan")
    
    if not os.path.exists(CRON_BACKUP_DIR):
        show_info("No backups found.")
        press_enter_to_continue()
        return
    
    backups = []
    for filename in os.listdir(CRON_BACKUP_DIR):
        if filename.startswith("crontab-") and filename.endswith(".txt"):
            filepath = os.path.join(CRON_BACKUP_DIR, filename)
            mtime = os.path.getmtime(filepath)
            backups.append((filename, filepath, mtime))
    
    if not backups:
        show_info("No backups found.")
        press_enter_to_continue()
        return
    
    backups.sort(key=lambda x: x[2], reverse=True)
    
    options = [b[0] for b in backups]
    
    selection = select_from_list(
        title="Restore Backup",
        message="Select backup to restore:",
        options=options
    )
    
    if not selection:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    backup_path = next(b[1] for b in backups if b[0] == selection)
    
    with open(backup_path, 'r') as f:
        content = f.read()
    
    console.print(f"[bold]Backup contents:[/bold]")
    console.print()
    console.print(content)
    console.print()
    
    console.print("[red bold]WARNING: This will replace the current crontab![/red bold]")
    console.print()
    
    if not confirm_action("Restore this backup?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    result = run_command(f"crontab -u {CRON_USER} {backup_path}", check=False, silent=True)
    
    if result.returncode == 0:
        show_success("Crontab restored!")
    else:
        show_error("Failed to restore crontab.")
    
    press_enter_to_continue()
