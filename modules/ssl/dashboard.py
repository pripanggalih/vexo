"""SSL Certificate dashboard."""

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_success,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import select_from_list, confirm_action
from modules.ssl.common import (
    list_all_certificates,
    format_status,
    format_days_left,
    ALERT_WARNING,
    ALERT_CRITICAL,
)
from utils.shell import run_command


def show_dashboard():
    """Display SSL certificate dashboard."""
    clear_screen()
    show_header()
    
    certificates = list_all_certificates()
    
    # Calculate stats
    total = len(certificates)
    valid = sum(1 for c in certificates if c["status"] == "valid" or c["status"] == "notice")
    expiring = sum(1 for c in certificates if c["status"] in ("warning", "critical"))
    expired = sum(1 for c in certificates if c["status"] == "expired")
    
    # Summary panel
    summary = f"""[bold]Total:[/bold] {total}  |  [green]Valid:[/green] {valid}  |  [yellow]Expiring:[/yellow] {expiring}  |  [red]Expired:[/red] {expired}"""
    
    show_panel(summary, title="SSL Certificate Dashboard", style="cyan")
    
    if not certificates:
        console.print()
        show_info("No SSL certificates found.")
        console.print("[dim]Use 'Issue Certificate' to generate a new certificate.[/dim]")
        press_enter_to_continue()
        return
    
    # Certificate table
    console.print()
    
    columns = [
        {"name": "Domain", "style": "cyan"},
        {"name": "Status", "justify": "center"},
        {"name": "Days Left", "justify": "right"},
        {"name": "CA"},
        {"name": "Type"},
    ]
    
    rows = []
    for cert in certificates:
        rows.append([
            cert.get("name", "unknown")[:25],
            format_status(cert.get("status", "unknown")),
            format_days_left(cert.get("days_left", 0)),
            cert.get("ca", "unknown")[:15],
            cert.get("type", "unknown"),
        ])
    
    show_table("Certificates", columns, rows)
    
    # Alerts section
    alerts = _get_alerts(certificates)
    if alerts:
        console.print()
        console.print("[bold yellow]Alerts:[/bold yellow]")
        for alert in alerts[:5]:
            console.print(f"  {alert}")
        if len(alerts) > 5:
            console.print(f"  [dim]... and {len(alerts) - 5} more alerts[/dim]")
    
    # Next renewal check
    console.print()
    _show_renewal_info()
    
    # Actions
    console.print()
    action = select_from_list(
        title="Action",
        message="Quick actions:",
        options=[
            "Refresh",
            "Renew Expiring Certificates",
            "View Certificate Details",
            "Back to Menu"
        ]
    )
    
    if action == "Refresh":
        show_dashboard()
    elif action == "Renew Expiring Certificates":
        _renew_expiring(certificates)
    elif action == "View Certificate Details":
        _view_details(certificates)


def _get_alerts(certificates):
    """Generate alert messages for certificates."""
    alerts = []
    
    for cert in certificates:
        status = cert.get("status", "")
        name = cert.get("name", "unknown")
        days = cert.get("days_left", 0)
        
        if status == "expired":
            alerts.append(f"[red]* {name} has EXPIRED - immediate action required![/red]")
        elif status == "critical":
            alerts.append(f"[red]* {name} expires in {days} days - renew now![/red]")
        elif status == "warning":
            alerts.append(f"[yellow]* {name} expires in {days} days - renew soon[/yellow]")
    
    return alerts


def _show_renewal_info():
    """Show auto-renewal timer information."""
    result = run_command(
        "systemctl list-timers certbot.timer --no-pager 2>/dev/null | grep certbot",
        check=False,
        silent=True
    )
    
    if result.returncode == 0 and result.stdout.strip():
        console.print(f"[dim]Auto-renewal: Active (via certbot.timer)[/dim]")
    else:
        console.print("[dim]Auto-renewal: Check certbot.timer or cron[/dim]")


def _renew_expiring(certificates):
    """Renew certificates that are expiring soon."""
    expiring = [c for c in certificates if c["status"] in ("warning", "critical") and c["source"] == "certbot"]
    
    if not expiring:
        show_info("No certbot certificates need renewal.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print("[bold]Certificates to renew:[/bold]")
    for cert in expiring:
        console.print(f"  * {cert['name']} ({cert['days_left']} days left)")
    console.print()
    
    if not confirm_action(f"Renew {len(expiring)} certificate(s)?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    from utils.shell import run_command_realtime, require_root
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    run_command_realtime("certbot renew", "Renewing certificates...")
    
    press_enter_to_continue()
    show_dashboard()


def _view_details(certificates):
    """View detailed info about a certificate."""
    if not certificates:
        return
    
    options = [f"{c['name']} ({c['status']})" for c in certificates]
    
    choice = select_from_list(
        title="Certificate",
        message="Select certificate:",
        options=options
    )
    
    if not choice:
        return
    
    # Find selected certificate
    idx = options.index(choice)
    cert = certificates[idx]
    
    clear_screen()
    show_header()
    
    show_panel(f"Certificate Details: {cert['name']}", title="SSL Certificate", style="cyan")
    
    console.print()
    console.print(f"[bold]Domain(s):[/bold]")
    for domain in cert.get("domains", []):
        console.print(f"  * {domain}")
    
    console.print()
    console.print(f"[bold]Status:[/bold] {format_status(cert.get('status', 'unknown'))}")
    console.print(f"[bold]Days Left:[/bold] {format_days_left(cert.get('days_left', 0))}")
    console.print(f"[bold]CA:[/bold] {cert.get('ca', 'unknown')}")
    console.print(f"[bold]Type:[/bold] {cert.get('type', 'unknown')}")
    console.print(f"[bold]Source:[/bold] {cert.get('source', 'unknown')}")
    
    if cert.get("not_before"):
        console.print(f"[bold]Valid From:[/bold] {cert['not_before'].strftime('%Y-%m-%d %H:%M')}")
    if cert.get("not_after"):
        console.print(f"[bold]Valid Until:[/bold] {cert['not_after'].strftime('%Y-%m-%d %H:%M')}")
    
    console.print(f"[bold]Path:[/bold] {cert.get('path', 'unknown')}")
    
    press_enter_to_continue()
    show_dashboard()
