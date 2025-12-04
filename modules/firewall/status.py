"""Firewall status dashboard."""

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_error,
    press_enter_to_continue,
)
from modules.firewall.common import (
    is_ufw_installed,
    is_ufw_active,
    get_ufw_rules,
    get_ufw_defaults,
    get_rule_count,
)
from utils.shell import run_command


def show_status_dashboard():
    """Display comprehensive firewall status dashboard."""
    clear_screen()
    show_header()
    
    if not is_ufw_installed():
        show_error("UFW is not installed.")
        console.print()
        console.print("[dim]Use 'Enable Firewall' to install and configure UFW.[/dim]")
        press_enter_to_continue()
        return
    
    # Build status info
    active = is_ufw_active()
    defaults = get_ufw_defaults()
    rule_count = get_rule_count()
    
    # Status line
    status_color = "green" if active else "yellow"
    status_text = "Active" if active else "Inactive"
    
    # Header panel
    header_content = f"""[bold]UFW Status:[/bold] [{status_color}]{status_text}[/{status_color}]
[bold]Rules:[/bold] {rule_count} active
[bold]Default Incoming:[/bold] {_format_policy(defaults['incoming'])}
[bold]Default Outgoing:[/bold] {_format_policy(defaults['outgoing'])}"""
    
    show_panel(header_content, title="Firewall (UFW) Dashboard", style="cyan")
    
    # Show rules table
    _show_rules_table()
    
    # Show app profiles summary
    _show_app_profiles_summary()
    
    press_enter_to_continue()


def _format_policy(policy):
    """Format policy with color."""
    if policy == "deny":
        return "[green]deny[/green]"
    elif policy == "allow":
        return "[yellow]allow[/yellow]"
    elif policy == "disabled":
        return "[dim]disabled[/dim]"
    return f"[dim]{policy}[/dim]"


def _show_rules_table():
    """Display rules in a table format."""
    rules = get_ufw_rules()
    
    if not rules:
        console.print("[dim]No rules configured.[/dim]")
        console.print()
        return
    
    console.print("[bold]Active Rules:[/bold]")
    console.print()
    
    columns = [
        {"name": "#", "style": "dim", "justify": "right"},
        {"name": "Rule", "style": "cyan"},
    ]
    
    rows = [[str(r["number"]), r["rule"]] for r in rules[:15]]
    
    show_table("", columns, rows, show_header=True)
    
    if len(rules) > 15:
        console.print(f"[dim]... and {len(rules) - 15} more rules[/dim]")
        console.print()


def _show_app_profiles_summary():
    """Show summary of available app profiles."""
    result = run_command("ufw app list", check=False, silent=True)
    
    if result.returncode != 0:
        return
    
    lines = result.stdout.strip().split('\n')
    profiles = [l.strip() for l in lines if l.strip() and "Available" not in l]
    
    if profiles:
        console.print(f"[bold]App Profiles:[/bold] {len(profiles)} available")
        console.print(f"[dim]{', '.join(profiles[:5])}", end="")
        if len(profiles) > 5:
            console.print(f" +{len(profiles) - 5} more[/dim]")
        else:
            console.print("[/dim]")
        console.print()
