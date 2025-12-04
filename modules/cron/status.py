"""Status display for vexo-cli cron."""

import os

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    press_enter_to_continue,
)
from utils.shell import run_command

from modules.cron.common import (
    CRON_BACKUP_DIR,
    get_vexo_jobs,
    get_crontab_lines,
)


def show_status():
    """Display cron status."""
    clear_screen()
    show_header()
    show_panel("Cron Status", title="Scheduled Tasks", style="cyan")
    
    result = run_command("systemctl is-active cron 2>/dev/null", check=False, silent=True)
    if result.returncode == 0 and "active" in result.stdout:
        console.print("[bold]Cron Service:[/bold] [green]Running[/green]")
    else:
        console.print("[bold]Cron Service:[/bold] [red]Not Running[/red]")
    
    console.print()
    
    jobs = get_vexo_jobs()
    all_lines = get_crontab_lines()
    
    enabled_count = sum(1 for j in jobs if j["enabled"])
    disabled_count = sum(1 for j in jobs if not j["enabled"])
    
    console.print(f"[bold]Vexo-Managed Jobs:[/bold] {len(jobs)}")
    console.print(f"  [green]●[/green] Enabled: {enabled_count}")
    console.print(f"  [red]●[/red] Disabled: {disabled_count}")
    
    console.print()
    
    console.print(f"[bold]Total Crontab Lines:[/bold] {len(all_lines)}")
    
    if os.path.exists(CRON_BACKUP_DIR):
        backups = [f for f in os.listdir(CRON_BACKUP_DIR) if f.endswith(".txt")]
        console.print(f"[bold]Backups Available:[/bold] {len(backups)}")
    else:
        console.print("[bold]Backups Available:[/bold] 0")
    
    press_enter_to_continue()
