"""Status display for vexo-cli supervisor."""

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_error,
    press_enter_to_continue,
)
from utils.shell import run_command, is_installed, is_service_running


def show_status():
    """Display Supervisor status."""
    clear_screen()
    show_header()
    show_panel("Supervisor Status", title="Queue Workers", style="cyan")
    
    if not is_installed("supervisor"):
        show_error("Supervisor is not installed.")
        press_enter_to_continue()
        return
    
    if is_service_running("supervisor"):
        console.print("[bold]Service Status:[/bold] [green]Running[/green]")
    else:
        console.print("[bold]Service Status:[/bold] [red]Stopped[/red]")
    
    console.print()
    
    result = run_command("supervisorctl status", check=False, silent=True)
    
    if result.returncode == 0 and result.stdout:
        console.print("[bold]Workers:[/bold]")
        console.print()
        
        for line in result.stdout.strip().split('\n'):
            if line:
                if "RUNNING" in line:
                    console.print(f"  [green]●[/green] {line}")
                elif "STOPPED" in line:
                    console.print(f"  [red]●[/red] {line}")
                elif "STARTING" in line or "BACKOFF" in line:
                    console.print(f"  [yellow]●[/yellow] {line}")
                else:
                    console.print(f"  [dim]●[/dim] {line}")
    else:
        console.print("[dim]No workers running.[/dim]")
    
    press_enter_to_continue()
