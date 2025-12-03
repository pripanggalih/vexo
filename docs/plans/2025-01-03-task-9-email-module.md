# Task 9.0: Email Module Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create email module for Postfix installation and configuration in send-only mode.

**Architecture:** Single `modules/email.py` with Postfix installation, configuration for send-only mode (no receiving), and test email functionality. Uses debconf for non-interactive installation.

**Tech Stack:** Postfix MTA, mailutils for testing, existing shell.py utilities, Rich UI components

---

## Sub-tasks Overview

| Sub-task | Description | Commit |
|----------|-------------|--------|
| 9.1 | Create email.py with show_menu() | Yes |
| 9.2 | Add install_postfix() | Yes |
| 9.3 | Add configure_postfix() | Yes |
| 9.4 | Add setup_send_only() | Yes |
| 9.5 | Add show_postfix_status() | Yes |
| 9.6 | Add test_email() | Yes |
| 9.7 | Update modules/__init__.py and task list | Yes |

**Total: 7 sub-tasks, 7 commits**

---

## Task 9.1: Create email.py with show_menu()

**Files:**
- Create: `modules/email.py`

**Step 1: Create email module with menu**

```python
"""Email server module for vexo-cli (Postfix)."""

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
from ui.menu import show_submenu, confirm_action, text_input
from utils.shell import (
    run_command,
    run_command_with_progress,
    run_command_realtime,
    is_installed,
    is_service_running,
    service_control,
    require_root,
    get_hostname,
)


def show_menu():
    """
    Display the Email Management submenu and handle user selection.
    """
    while True:
        clear_screen()
        show_header()
        
        # Show Postfix status
        if is_service_running("postfix"):
            status = "[green]Running[/green]"
        elif is_installed("postfix"):
            status = "[red]Stopped[/red]"
        else:
            status = "[dim]Not installed[/dim]"
        
        console.print(f"[dim]Postfix Status: {status}[/dim]")
        console.print()
        
        choice = show_submenu(
            title="Email Server (Postfix)",
            options=[
                ("install", "1. Install Postfix"),
                ("configure", "2. Configure Postfix"),
                ("send_only", "3. Setup Send-Only Mode"),
                ("status", "4. Show Status"),
                ("test", "5. Send Test Email"),
                ("back", "← Back to Main Menu"),
            ],
        )
        
        if choice == "install":
            install_postfix()
        elif choice == "configure":
            configure_postfix_interactive()
        elif choice == "send_only":
            setup_send_only()
        elif choice == "status":
            show_postfix_status()
        elif choice == "test":
            test_email_interactive()
        elif choice == "back" or choice is None:
            break
```

**Step 2: Commit**

```bash
git add modules/email.py
git commit -m "feat(email): add email.py with menu structure"
```

---

## Task 9.2: Add install_postfix()

**Files:**
- Modify: `modules/email.py`

**Step 1: Add Postfix installation function**

Append to `modules/email.py`:

```python
def install_postfix():
    """Install Postfix mail server."""
    clear_screen()
    show_header()
    show_panel("Install Postfix", title="Email Server", style="cyan")
    
    if is_installed("postfix"):
        show_info("Postfix is already installed.")
        
        if is_service_running("postfix"):
            console.print("[dim]Service is running.[/dim]")
        else:
            if confirm_action("Start Postfix service?"):
                service_control("postfix", "start")
                show_success("Postfix started!")
        
        press_enter_to_continue()
        return
    
    console.print("[bold]Postfix will be installed with:[/bold]")
    console.print("  • Internet Site configuration")
    console.print("  • System mail name from hostname")
    console.print()
    
    if not confirm_action("Install Postfix mail server?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Get hostname for mail name
    hostname = get_hostname()
    
    show_info("Pre-configuring Postfix...")
    
    # Set debconf selections for non-interactive install
    debconf_settings = f"""postfix postfix/main_mailer_type select Internet Site
postfix postfix/mailname string {hostname}
"""
    
    result = run_command(
        f'echo "{debconf_settings}" | debconf-set-selections',
        check=False,
        silent=True
    )
    
    show_info("Installing Postfix...")
    
    # Install with DEBIAN_FRONTEND=noninteractive
    returncode = run_command_realtime(
        "DEBIAN_FRONTEND=noninteractive apt install -y postfix mailutils",
        "Installing Postfix..."
    )
    
    if returncode != 0:
        show_error("Failed to install Postfix.")
        press_enter_to_continue()
        return
    
    service_control("postfix", "start")
    service_control("postfix", "enable")
    
    if is_service_running("postfix"):
        show_success("Postfix installed and running!")
        console.print()
        console.print(f"[bold]Mail Name:[/bold] {hostname}")
        console.print()
        console.print("[yellow]Recommended: Run 'Setup Send-Only Mode' next![/yellow]")
    else:
        show_warning("Postfix installed but service may not be running.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/email.py
git commit -m "feat(email): add install_postfix() with non-interactive setup"
```

---

## Task 9.3: Add configure_postfix()

**Files:**
- Modify: `modules/email.py`

**Step 1: Add Postfix configuration function**

Append to `modules/email.py`:

```python
def configure_postfix_interactive():
    """Interactive prompt to configure Postfix."""
    clear_screen()
    show_header()
    show_panel("Configure Postfix", title="Email Server", style="cyan")
    
    if not is_installed("postfix"):
        show_error("Postfix is not installed.")
        press_enter_to_continue()
        return
    
    # Get current settings
    current_hostname = _get_postfix_setting("myhostname")
    current_domain = _get_postfix_setting("mydomain")
    
    console.print("[bold]Current Configuration:[/bold]")
    console.print(f"  Hostname: {current_hostname or 'Not set'}")
    console.print(f"  Domain: {current_domain or 'Not set'}")
    console.print()
    
    hostname = text_input(
        title="Hostname",
        message="Enter mail hostname (e.g., mail.example.com):",
        default=current_hostname or get_hostname()
    )
    
    if not hostname:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Extract domain from hostname
    domain_parts = hostname.split(".")
    if len(domain_parts) >= 2:
        default_domain = ".".join(domain_parts[-2:])
    else:
        default_domain = hostname
    
    domain = text_input(
        title="Domain",
        message="Enter mail domain (e.g., example.com):",
        default=current_domain or default_domain
    )
    
    if not domain:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = configure_postfix(hostname, domain)
    
    if success:
        show_success("Postfix configured successfully!")
        console.print()
        console.print(f"[dim]Hostname: {hostname}[/dim]")
        console.print(f"[dim]Domain: {domain}[/dim]")
    else:
        show_error("Failed to configure Postfix.")
    
    press_enter_to_continue()


def configure_postfix(hostname, domain):
    """
    Configure Postfix hostname and domain.
    
    Args:
        hostname: Mail hostname (e.g., mail.example.com)
        domain: Mail domain (e.g., example.com)
    
    Returns:
        bool: True if successful
    """
    from config import POSTFIX_CONFIG_PATH
    
    settings = {
        "myhostname": hostname,
        "mydomain": domain,
        "myorigin": f"$mydomain",
    }
    
    for key, value in settings.items():
        result = run_command(
            f'postconf -e "{key}={value}"',
            check=False,
            silent=True
        )
        if result.returncode != 0:
            return False
    
    # Reload Postfix
    return service_control("postfix", "reload")


def _get_postfix_setting(key):
    """Get a Postfix configuration value."""
    result = run_command(
        f"postconf -h {key} 2>/dev/null",
        check=False,
        silent=True
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None
```

**Step 2: Commit**

```bash
git add modules/email.py
git commit -m "feat(email): add configure_postfix() for hostname and domain"
```

---

## Task 9.4: Add setup_send_only()

**Files:**
- Modify: `modules/email.py`

**Step 1: Add send-only mode setup**

Append to `modules/email.py`:

```python
def setup_send_only():
    """Configure Postfix for send-only mode (no incoming mail)."""
    clear_screen()
    show_header()
    show_panel("Setup Send-Only Mode", title="Email Server", style="cyan")
    
    if not is_installed("postfix"):
        show_error("Postfix is not installed.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Send-Only Mode will:[/bold]")
    console.print("  • Disable incoming mail (listen on localhost only)")
    console.print("  • Allow sending outgoing emails")
    console.print("  • Disable local delivery to mailboxes")
    console.print()
    console.print("[dim]This is ideal for application servers that only need")
    console.print("to send notifications, alerts, and transactional emails.[/dim]")
    console.print()
    
    if not confirm_action("Configure Postfix for send-only mode?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    show_info("Configuring send-only mode...")
    
    # Send-only configuration
    settings = {
        "inet_interfaces": "loopback-only",
        "mydestination": "$myhostname, localhost.$mydomain, localhost",
        "local_transport": "error:local delivery disabled",
    }
    
    success = True
    for key, value in settings.items():
        result = run_command(
            f'postconf -e "{key}={value}"',
            check=False,
            silent=True
        )
        if result.returncode != 0:
            success = False
            break
    
    if success:
        service_control("postfix", "restart")
        
        if is_service_running("postfix"):
            show_success("Send-only mode configured!")
            console.print()
            console.print("[dim]Postfix now only listens on localhost (127.0.0.1).[/dim]")
            console.print("[dim]Incoming mail from outside is disabled.[/dim]")
        else:
            show_warning("Configuration applied but Postfix may not be running.")
    else:
        show_error("Failed to configure send-only mode.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/email.py
git commit -m "feat(email): add setup_send_only() for send-only mode"
```

---

## Task 9.5: Add show_postfix_status()

**Files:**
- Modify: `modules/email.py`

**Step 1: Add status display function**

Append to `modules/email.py`:

```python
def show_postfix_status():
    """Display Postfix service status and configuration."""
    clear_screen()
    show_header()
    show_panel("Postfix Status", title="Email Server", style="cyan")
    
    if not is_installed("postfix"):
        show_error("Postfix is not installed.")
        press_enter_to_continue()
        return
    
    # Service status
    if is_service_running("postfix"):
        console.print("[bold]Service Status:[/bold] [green]Running[/green]")
    else:
        console.print("[bold]Service Status:[/bold] [red]Stopped[/red]")
    
    console.print()
    
    # Configuration
    console.print("[bold]Configuration:[/bold]")
    
    settings = [
        ("myhostname", "Hostname"),
        ("mydomain", "Domain"),
        ("myorigin", "Origin"),
        ("inet_interfaces", "Listen On"),
        ("mydestination", "Destination"),
    ]
    
    columns = [
        {"name": "Setting", "style": "cyan"},
        {"name": "Value"},
    ]
    
    rows = []
    for key, label in settings:
        value = _get_postfix_setting(key)
        rows.append([label, value or "[dim]Not set[/dim]"])
    
    show_table("Postfix Configuration", columns, rows)
    
    # Mail queue
    console.print()
    console.print("[bold]Mail Queue:[/bold]")
    
    result = run_command("postqueue -p 2>/dev/null", check=False, silent=True)
    if result.returncode == 0:
        output = result.stdout.strip()
        if "Mail queue is empty" in output or not output:
            console.print("[dim]  Queue is empty[/dim]")
        else:
            lines = output.split('\n')
            queue_count = sum(1 for line in lines if line and not line.startswith('-'))
            console.print(f"  {queue_count} message(s) in queue")
    else:
        console.print("[dim]  Unable to check queue[/dim]")
    
    # Listening ports
    console.print()
    console.print("[bold]Network:[/bold]")
    
    inet_interfaces = _get_postfix_setting("inet_interfaces")
    if inet_interfaces == "loopback-only":
        console.print("  Mode: [cyan]Send-Only[/cyan] (localhost only)")
    elif inet_interfaces == "all":
        console.print("  Mode: [yellow]Full Server[/yellow] (all interfaces)")
    else:
        console.print(f"  Mode: {inet_interfaces}")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/email.py
git commit -m "feat(email): add show_postfix_status() with config and queue info"
```

---

## Task 9.6: Add test_email()

**Files:**
- Modify: `modules/email.py`

**Step 1: Add test email function**

Append to `modules/email.py`:

```python
def test_email_interactive():
    """Interactive prompt to send a test email."""
    clear_screen()
    show_header()
    show_panel("Send Test Email", title="Email Server", style="cyan")
    
    if not is_installed("postfix"):
        show_error("Postfix is not installed.")
        press_enter_to_continue()
        return
    
    if not is_service_running("postfix"):
        show_error("Postfix service is not running.")
        press_enter_to_continue()
        return
    
    if not is_installed("mailutils"):
        show_warning("mailutils is not installed. Installing...")
        try:
            require_root()
            run_command_with_progress(
                "apt install -y mailutils",
                "Installing mailutils..."
            )
        except PermissionError:
            press_enter_to_continue()
            return
    
    recipient = text_input(
        title="Test Email",
        message="Enter recipient email address:"
    )
    
    if not recipient:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Basic email validation
    if "@" not in recipient or "." not in recipient:
        show_error("Invalid email address format.")
        press_enter_to_continue()
        return
    
    success = test_email(recipient)
    
    if success:
        show_success("Test email sent!")
        console.print()
        console.print(f"[dim]Recipient: {recipient}[/dim]")
        console.print("[dim]Check your inbox (and spam folder).[/dim]")
        console.print()
        console.print("[dim]To check mail queue: postqueue -p[/dim]")
        console.print("[dim]To view mail log: tail -f /var/log/mail.log[/dim]")
    else:
        show_error("Failed to send test email.")
        console.print()
        console.print("[dim]Check /var/log/mail.log for errors.[/dim]")
    
    press_enter_to_continue()


def test_email(recipient):
    """
    Send a test email.
    
    Args:
        recipient: Email address to send to
    
    Returns:
        bool: True if command succeeded (email queued)
    """
    hostname = get_hostname()
    subject = f"Test Email from {hostname}"
    body = f"""This is a test email from vexo-cli.

Server: {hostname}
Time: $(date)

If you received this email, your Postfix configuration is working correctly.

--
Sent by vexo-cli
"""
    
    result = run_command(
        f'echo "{body}" | mail -s "{subject}" {recipient}',
        check=False,
        silent=True
    )
    
    return result.returncode == 0
```

**Step 2: Commit**

```bash
git add modules/email.py
git commit -m "feat(email): add test_email() for sending test emails"
```

---

## Task 9.7: Update modules/__init__.py and task list

**Files:**
- Modify: `modules/__init__.py`
- Modify: `tasks/tasks-vexo-cli.md`

**Step 1: Update modules/__init__.py**

Add email import:

```python
"""Business logic modules for vexo-cli - system, webserver, runtime, database, email."""

from modules import system
from modules import webserver
from modules import runtime
from modules import database
from modules import email
```

**Step 2: Update task list**

Mark all Task 9.x items as `[x]` complete.

**Step 3: Commit**

```bash
git add modules/__init__.py tasks/tasks-vexo-cli.md
git commit -m "docs: mark Task 9.0 Email Module as complete"
```

---

## Summary

After completion, `modules/email.py` will have:

**Menu Function:**
- `show_menu()` - Email submenu (6 options)

**Installation:**
- `install_postfix()` - Non-interactive install with debconf

**Configuration:**
- `configure_postfix()` - Set hostname and domain
- `setup_send_only()` - Configure send-only mode (loopback-only)

**Status & Testing:**
- `show_postfix_status()` - Display config, queue, network mode
- `test_email()` - Send test email via mailutils

**Helper:**
- `_get_postfix_setting()` - Read postconf values

**Send-Only Mode Settings:**
- `inet_interfaces = loopback-only` - Only listen on localhost
- `local_transport = error:local delivery disabled` - No local mailboxes
- `mydestination` - Minimal destinations

**Use Case:** VPS applications that need to send notifications, password resets, alerts without receiving mail.
