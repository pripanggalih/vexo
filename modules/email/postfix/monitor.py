"""Email monitoring - statistics, logs, delivery reports, health check."""

import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, is_installed, is_service_running
from modules.email.postfix.utils import (
    is_postfix_ready, get_postfix_setting, get_configured_domains,
)


# Log files
MAIL_LOG = "/var/log/mail.log"
MAIL_LOG_1 = "/var/log/mail.log.1"
VEXO_EMAIL_LOG = "/var/log/vexo-email.log"


def show_monitor_menu():
    """Display monitoring menu."""
    def get_status():
        # Quick stats from today
        stats = _get_quick_stats()
        return f"Today: {stats['sent']}↑ {stats['received']}↓"
    
    options = [
        ("stats", "1. Mail Statistics"),
        ("delivery", "2. Delivery Reports"),
        ("logs", "3. Log Viewer"),
        ("health", "4. Health Check"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "stats": show_statistics,
        "delivery": show_delivery_reports,
        "logs": show_log_viewer,
        "health": run_health_check,
    }
    
    run_menu_loop("Monitoring & Stats", options, handlers, get_status)


def _get_quick_stats():
    """Get quick statistics for today."""
    stats = {"sent": 0, "received": 0, "bounced": 0}
    
    if not os.path.exists(MAIL_LOG):
        return stats
    
    today = datetime.now().strftime("%b %d")
    
    result = run_command(
        f"grep '{today}' {MAIL_LOG} 2>/dev/null | grep -c 'status=sent'",
        check=False, silent=True
    )
    try:
        stats["sent"] = int(result.stdout.strip())
    except ValueError:
        pass
    
    result = run_command(
        f"grep '{today}' {MAIL_LOG} 2>/dev/null | grep -c 'from=<.*>, size='",
        check=False, silent=True
    )
    try:
        stats["received"] = int(result.stdout.strip())
    except ValueError:
        pass
    
    return stats


def show_statistics():
    """Display mail statistics."""
    clear_screen()
    show_header()
    show_panel("Mail Statistics", title="Monitoring", style="cyan")
    
    periods = [
        "Today",
        "Last 7 days",
        "Last 30 days",
    ]
    
    period = select_from_list("Period", "Select time period:", periods)
    if not period:
        return
    
    if not os.path.exists(MAIL_LOG):
        show_error("Mail log not found.")
        press_enter_to_continue()
        return
    
    show_info("Analyzing mail logs...")
    
    # Determine date range
    if "Today" in period:
        days = 0
    elif "7" in period:
        days = 7
    else:
        days = 30
    
    stats = _analyze_mail_log(days)
    
    console.print()
    console.print(f"[bold]Statistics for {period}:[/bold]")
    console.print()
    
    # Summary
    columns = [
        {"name": "Metric", "style": "cyan"},
        {"name": "Count", "justify": "right"},
    ]
    
    rows = [
        ["Emails Sent", str(stats["sent"])],
        ["Emails Received", str(stats["received"])],
        ["Bounced", str(stats["bounced"])],
        ["Deferred", str(stats["deferred"])],
        ["Rejected", str(stats["rejected"])],
    ]
    
    show_table("Summary", columns, rows, show_header=True)
    
    # Top recipients
    if stats["top_recipients"]:
        console.print()
        console.print("[bold]Top Recipients:[/bold]")
        for domain, count in stats["top_recipients"][:5]:
            console.print(f"  {domain}: {count}")
    
    # Top senders
    if stats["top_senders"]:
        console.print()
        console.print("[bold]Top Senders:[/bold]")
        for sender, count in stats["top_senders"][:5]:
            console.print(f"  {sender}: {count}")
    
    press_enter_to_continue()


def _analyze_mail_log(days=0):
    """Analyze mail log for statistics."""
    stats = {
        "sent": 0,
        "received": 0,
        "bounced": 0,
        "deferred": 0,
        "rejected": 0,
        "top_recipients": [],
        "top_senders": [],
    }
    
    recipients = defaultdict(int)
    senders = defaultdict(int)
    
    # Build date patterns
    date_patterns = []
    for i in range(days + 1):
        date = datetime.now() - timedelta(days=i)
        date_patterns.append(date.strftime("%b %d"))
        date_patterns.append(date.strftime("%b  %d"))  # Single digit day
    
    # Process log file(s)
    log_files = [MAIL_LOG]
    if days > 1 and os.path.exists(MAIL_LOG_1):
        log_files.append(MAIL_LOG_1)
    
    for log_file in log_files:
        if not os.path.exists(log_file):
            continue
        
        try:
            with open(log_file, 'r', errors='ignore') as f:
                for line in f:
                    # Check date if filtering
                    if days > 0:
                        line_date = line[:6]
                        if not any(p in line_date for p in date_patterns):
                            continue
                    
                    # Count by status
                    if "status=sent" in line:
                        stats["sent"] += 1
                        
                        # Extract recipient domain
                        match = re.search(r'to=<[^@]+@([^>]+)>', line)
                        if match:
                            recipients[match.group(1)] += 1
                    
                    elif "status=bounced" in line:
                        stats["bounced"] += 1
                    
                    elif "status=deferred" in line:
                        stats["deferred"] += 1
                    
                    elif "reject:" in line.lower() or "NOQUEUE: reject" in line:
                        stats["rejected"] += 1
                    
                    # Count incoming
                    if "from=<" in line and "size=" in line:
                        stats["received"] += 1
                        
                        # Extract sender
                        match = re.search(r'from=<([^>]+)>', line)
                        if match and match.group(1):
                            senders[match.group(1)] += 1
        except Exception:
            pass
    
    # Sort top recipients/senders
    stats["top_recipients"] = sorted(recipients.items(), key=lambda x: x[1], reverse=True)
    stats["top_senders"] = sorted(senders.items(), key=lambda x: x[1], reverse=True)
    
    return stats


def show_delivery_reports():
    """Search and show delivery reports."""
    clear_screen()
    show_header()
    show_panel("Delivery Reports", title="Monitoring", style="cyan")
    
    console.print("[bold]Search delivery status by:[/bold]")
    console.print()
    
    options = [
        "Recipient email",
        "Message ID",
        "Recent failures",
        "Recent sent",
    ]
    
    choice = select_from_list("Search By", "Select:", options)
    if not choice:
        return
    
    if "Recipient" in choice:
        email = text_input("Recipient email address:")
        if not email:
            return
        _search_by_recipient(email)
    
    elif "Message ID" in choice:
        msg_id = text_input("Message ID:")
        if not msg_id:
            return
        _search_by_message_id(msg_id)
    
    elif "failures" in choice:
        _show_recent_failures()
    
    else:
        _show_recent_sent()
    
    press_enter_to_continue()


def _search_by_recipient(email):
    """Search delivery status by recipient."""
    console.print()
    console.print(f"[bold]Searching for {email}...[/bold]")
    console.print()
    
    result = run_command(
        f"grep -i '{email}' {MAIL_LOG} 2>/dev/null | tail -20",
        check=False, silent=True
    )
    
    if not result.stdout.strip():
        show_info(f"No entries found for {email}")
        return
    
    # Parse and display results
    entries = []
    
    for line in result.stdout.strip().split('\n'):
        # Extract timestamp
        timestamp = line[:15] if len(line) > 15 else ""
        
        # Determine status
        if "status=sent" in line:
            status = "[green]Sent[/green]"
        elif "status=bounced" in line:
            status = "[red]Bounced[/red]"
        elif "status=deferred" in line:
            status = "[yellow]Deferred[/yellow]"
        elif "reject" in line.lower():
            status = "[red]Rejected[/red]"
        else:
            status = "[dim]Unknown[/dim]"
        
        # Extract details
        details = ""
        if "dsn=" in line:
            match = re.search(r'dsn=(\S+)', line)
            if match:
                details = match.group(1)
        
        entries.append([timestamp, status, details[:30]])
    
    columns = [
        {"name": "Time", "style": "cyan"},
        {"name": "Status"},
        {"name": "Details"},
    ]
    
    show_table(f"Results for {email}", columns, entries[-10:], show_header=True)


def _search_by_message_id(msg_id):
    """Search by message ID."""
    console.print()
    console.print(f"[bold]Searching for message {msg_id}...[/bold]")
    console.print()
    
    result = run_command(
        f"grep -i '{msg_id}' {MAIL_LOG} 2>/dev/null",
        check=False, silent=True
    )
    
    if result.stdout.strip():
        console.print("[bold]Log entries:[/bold]")
        console.print(result.stdout[:2000])
    else:
        show_info("Message not found in recent logs.")


def _show_recent_failures():
    """Show recent delivery failures."""
    console.print()
    console.print("[bold]Recent Failures (bounced/deferred):[/bold]")
    console.print()
    
    result = run_command(
        f"grep -E 'status=(bounced|deferred)' {MAIL_LOG} 2>/dev/null | tail -20",
        check=False, silent=True
    )
    
    if not result.stdout.strip():
        show_info("No recent failures found.")
        return
    
    for line in result.stdout.strip().split('\n')[-10:]:
        # Extract key info
        timestamp = line[:15]
        
        to_match = re.search(r'to=<([^>]+)>', line)
        to_addr = to_match.group(1) if to_match else "unknown"
        
        status = "bounced" if "bounced" in line else "deferred"
        status_color = "red" if status == "bounced" else "yellow"
        
        console.print(f"{timestamp} [{status_color}]{status}[/{status_color}] → {to_addr}")


def _show_recent_sent():
    """Show recently sent emails."""
    console.print()
    console.print("[bold]Recently Sent:[/bold]")
    console.print()
    
    result = run_command(
        f"grep 'status=sent' {MAIL_LOG} 2>/dev/null | tail -15",
        check=False, silent=True
    )
    
    if not result.stdout.strip():
        show_info("No recent sent emails found.")
        return
    
    for line in result.stdout.strip().split('\n')[-10:]:
        timestamp = line[:15]
        
        to_match = re.search(r'to=<([^>]+)>', line)
        to_addr = to_match.group(1) if to_match else "unknown"
        
        console.print(f"{timestamp} [green]sent[/green] → {to_addr}")


def show_log_viewer():
    """Enhanced log viewer."""
    clear_screen()
    show_header()
    show_panel("Log Viewer", title="Monitoring", style="cyan")
    
    options = [
        "View recent (tail -50)",
        "Filter by status",
        "Filter by domain",
        "Real-time monitor (tail -f)",
        "View vexo pipe log",
    ]
    
    choice = select_from_list("View", "Select:", options)
    if not choice:
        return
    
    if "recent" in choice:
        result = run_command(f"tail -50 {MAIL_LOG}", check=False, silent=True)
        console.print(result.stdout if result.stdout else "[dim]Log is empty[/dim]")
    
    elif "status" in choice:
        statuses = ["sent", "bounced", "deferred", "reject"]
        status = select_from_list("Status", "Filter by:", statuses)
        if status:
            result = run_command(
                f"grep -i '{status}' {MAIL_LOG} 2>/dev/null | tail -30",
                check=False, silent=True
            )
            console.print(result.stdout if result.stdout else f"[dim]No {status} entries[/dim]")
    
    elif "domain" in choice:
        domain = text_input("Domain to filter:")
        if domain:
            result = run_command(
                f"grep -i '{domain}' {MAIL_LOG} 2>/dev/null | tail -30",
                check=False, silent=True
            )
            console.print(result.stdout if result.stdout else f"[dim]No entries for {domain}[/dim]")
    
    elif "Real-time" in choice:
        console.print("[yellow]Press Ctrl+C to stop[/yellow]")
        console.print()
        try:
            import subprocess
            subprocess.run(["tail", "-f", MAIL_LOG])
        except KeyboardInterrupt:
            pass
    
    elif "vexo" in choice:
        if os.path.exists(VEXO_EMAIL_LOG):
            result = run_command(f"tail -50 {VEXO_EMAIL_LOG}", check=False, silent=True)
            console.print(result.stdout if result.stdout else "[dim]Log is empty[/dim]")
        else:
            show_info("Vexo pipe log not found.")
    
    press_enter_to_continue()


def run_health_check():
    """Run email system health check."""
    clear_screen()
    show_header()
    show_panel("Health Check", title="Monitoring", style="cyan")
    
    checks = []
    recommendations = []
    
    # Check 1: Postfix service
    running = is_service_running("postfix")
    checks.append(("Postfix Service", running, "Running" if running else "Stopped"))
    if not running:
        recommendations.append("Start Postfix: systemctl start postfix")
    
    # Check 2: Port 25
    result = run_command("ss -tlnp | grep ':25 '", check=False, silent=True)
    port25 = result.returncode == 0
    checks.append(("Port 25 (SMTP)", port25, "Listening" if port25 else "Not listening"))
    
    # Check 3: Port 587
    result = run_command("ss -tlnp | grep ':587 '", check=False, silent=True)
    port587 = result.returncode == 0
    checks.append(("Port 587 (Submission)", port587, "Listening" if port587 else "Not listening"))
    
    # Check 4: Hostname configured
    hostname = get_postfix_setting("myhostname")
    has_hostname = bool(hostname and hostname != "localhost")
    checks.append(("Mail Hostname", has_hostname, hostname or "Not set"))
    if not has_hostname:
        recommendations.append("Configure mail hostname in Postfix")
    
    # Check 5: DKIM
    dkim_installed = is_installed("opendkim")
    dkim_running = is_service_running("opendkim") if dkim_installed else False
    if dkim_installed:
        checks.append(("DKIM (OpenDKIM)", dkim_running, "Running" if dkim_running else "Stopped"))
    else:
        checks.append(("DKIM (OpenDKIM)", False, "Not installed"))
        recommendations.append("Consider installing DKIM for better deliverability")
    
    # Check 6: Mail queue
    result = run_command("postqueue -p 2>/dev/null | grep -c '^[A-F0-9]'", check=False, silent=True)
    try:
        queue_count = int(result.stdout.strip())
    except ValueError:
        queue_count = 0
    
    queue_ok = queue_count < 100
    checks.append(("Mail Queue", queue_ok, f"{queue_count} messages"))
    if not queue_ok:
        recommendations.append(f"High queue count ({queue_count}) - check for delivery issues")
    
    # Check 7: Disk space
    result = run_command("df -h /var/spool/postfix | tail -1", check=False, silent=True)
    if result.returncode == 0:
        parts = result.stdout.split()
        if len(parts) >= 5:
            usage = parts[4].replace('%', '')
            try:
                disk_ok = int(usage) < 85
                checks.append(("Disk Space", disk_ok, f"{parts[4]} used"))
                if not disk_ok:
                    recommendations.append("Mail spool disk space is low")
            except ValueError:
                pass
    
    # Check 8: DNS (MX record)
    domains = get_configured_domains()
    if domains:
        domain = domains[0]
        result = run_command(f"dig +short MX {domain}", check=False, silent=True)
        has_mx = bool(result.stdout.strip())
        checks.append(("MX Record", has_mx, f"{domain}: {'Found' if has_mx else 'Missing'}"))
        if not has_mx:
            recommendations.append(f"Add MX record for {domain}")
    
    # Display results
    columns = [
        {"name": "Check", "style": "cyan"},
        {"name": "Status", "justify": "center"},
        {"name": "Details"},
    ]
    
    rows = []
    passed = 0
    
    for name, ok, details in checks:
        status = "[green]✓ PASS[/green]" if ok else "[red]✗ FAIL[/red]"
        if ok:
            passed += 1
        rows.append([name, status, details])
    
    show_table(f"Score: {passed}/{len(checks)}", columns, rows, show_header=True)
    
    if recommendations:
        console.print()
        console.print("[bold yellow]Recommendations:[/bold yellow]")
        for rec in recommendations:
            console.print(f"  • {rec}")
    else:
        console.print()
        console.print("[bold green]All checks passed![/bold green]")
    
    press_enter_to_continue()
