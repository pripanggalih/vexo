# Task 16.0: Postfix Receive Mode Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform Postfix email module from send-only to receive mode with multi-domain catch-all that pipes to Laravel artisan commands.

**Architecture:** Postfix receives email → virtual_alias_maps routes to pipe transport → vexo-pipe script reads config → executes Laravel artisan command with raw email on stdin.

**Tech Stack:** Postfix, jq, bash, existing shell.py utilities, JSON config file

---

## Sub-tasks Overview

| Sub-task | Description | Commit |
|----------|-------------|--------|
| 16.1 | Add config constants and imports | Yes |
| 16.2 | Refactor show_menu() with new structure | Yes |
| 16.3 | Add config file management functions | Yes |
| 16.4 | Implement setup_receive_mode() | Yes |
| 16.5 | Implement add_domain_interactive() and add_domain() | Yes |
| 16.6 | Implement remove_domain() and list_domains() | Yes |
| 16.7 | Implement edit_domain_interactive() | Yes |
| 16.8 | Add Postfix file generators | Yes |
| 16.9 | Create vexo-pipe script installer | Yes |
| 16.10 | Implement test_incoming_interactive() | Yes |
| 16.11 | Implement view_mail_log() | Yes |
| 16.12 | Implement queue management functions | Yes |
| 16.13 | Update show_postfix_status() for receive mode | Yes |

**Total: 13 sub-tasks, 13 commits**

---

## Task 16.1: Add config constants and imports

**Files:**
- Modify: `modules/email.py`

**Step 1: Add new imports and constants at top of file**

After existing imports, add:

```python
import os
import json

# Config paths
VEXO_CONFIG_DIR = "/etc/vexo"
EMAIL_DOMAINS_CONFIG = "/etc/vexo/email-domains.json"
VEXO_PIPE_SCRIPT = "/usr/local/bin/vexo-pipe"
VEXO_EMAIL_LOG = "/var/log/vexo-email.log"

# Postfix paths
POSTFIX_VIRTUAL = "/etc/postfix/virtual"
POSTFIX_MASTER = "/etc/postfix/master.cf"
```

**Step 2: Commit**

```bash
git add modules/email.py
git commit -m "feat(email): add config constants for receive mode"
```

---

## Task 16.2: Refactor show_menu() with new structure

**Files:**
- Modify: `modules/email.py`

**Step 1: Replace show_menu() function**

```python
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
            mode = _get_current_mode()
            console.print(f"[dim]Postfix: {status} ({mode})[/dim]")
        elif is_installed("postfix"):
            console.print("[dim]Postfix: [red]Stopped[/red][/dim]")
        else:
            console.print("[dim]Postfix: Not installed[/dim]")
        console.print()
        
        choice = show_submenu(
            title="Email Server (Postfix)",
            options=[
                ("install", "1. Install Postfix"),
                ("mode", "2. Configure Mode"),
                ("domains", "3. Manage Domains"),
                ("test", "4. Test Email"),
                ("log", "5. View Mail Log"),
                ("queue", "6. Queue Management"),
                ("status", "7. Show Status"),
                ("back", "← Back to Main Menu"),
            ],
        )
        
        if choice == "install":
            install_postfix()
        elif choice == "mode":
            configure_mode_menu()
        elif choice == "domains":
            manage_domains_menu()
        elif choice == "test":
            test_email_menu()
        elif choice == "log":
            view_mail_log()
        elif choice == "queue":
            queue_management_menu()
        elif choice == "status":
            show_postfix_status()
        elif choice == "back" or choice is None:
            break


def _get_current_mode():
    """Get current Postfix mode (Send-Only or Receive)."""
    inet_interfaces = _get_postfix_setting("inet_interfaces")
    if inet_interfaces == "loopback-only":
        return "[cyan]Send-Only[/cyan]"
    elif inet_interfaces == "all":
        return "[yellow]Receive[/yellow]"
    return "[dim]Unknown[/dim]"
```

**Step 2: Add submenu functions (stubs for now)**

```python
def configure_mode_menu():
    """Submenu for configuring Postfix mode."""
    while True:
        clear_screen()
        show_header()
        
        choice = show_submenu(
            title="Configure Mode",
            options=[
                ("send_only", "1. Send-Only Mode"),
                ("receive", "2. Receive Mode (Catch-All)"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "send_only":
            setup_send_only()
        elif choice == "receive":
            setup_receive_mode()
        elif choice == "back" or choice is None:
            break


def manage_domains_menu():
    """Submenu for managing email domains."""
    while True:
        clear_screen()
        show_header()
        
        choice = show_submenu(
            title="Manage Domains",
            options=[
                ("add", "1. Add Domain"),
                ("remove", "2. Remove Domain"),
                ("list", "3. List Domains"),
                ("edit", "4. Edit Domain"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "add":
            add_domain_interactive()
        elif choice == "remove":
            remove_domain_interactive()
        elif choice == "list":
            list_domains()
        elif choice == "edit":
            edit_domain_interactive()
        elif choice == "back" or choice is None:
            break


def test_email_menu():
    """Submenu for testing email."""
    while True:
        clear_screen()
        show_header()
        
        choice = show_submenu(
            title="Test Email",
            options=[
                ("send", "1. Send Test Email"),
                ("incoming", "2. Test Incoming (to Laravel)"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "send":
            test_email_interactive()
        elif choice == "incoming":
            test_incoming_interactive()
        elif choice == "back" or choice is None:
            break


def queue_management_menu():
    """Submenu for queue management."""
    while True:
        clear_screen()
        show_header()
        
        choice = show_submenu(
            title="Queue Management",
            options=[
                ("view", "1. View Queue"),
                ("flush", "2. Flush Queue"),
                ("delete", "3. Delete All Queued"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "view":
            view_queue()
        elif choice == "flush":
            flush_queue()
        elif choice == "delete":
            delete_queue()
        elif choice == "back" or choice is None:
            break
```

**Step 3: Commit**

```bash
git add modules/email.py
git commit -m "feat(email): refactor menu structure with submenus"
```

---

## Task 16.3: Add config file management functions

**Files:**
- Modify: `modules/email.py`

**Step 1: Add config file management functions**

```python
# =============================================================================
# Config File Management
# =============================================================================

def _ensure_config_dir():
    """Ensure /etc/vexo directory exists."""
    if not os.path.exists(VEXO_CONFIG_DIR):
        os.makedirs(VEXO_CONFIG_DIR, mode=0o755)


def _load_domains_config():
    """Load email domains configuration."""
    if not os.path.exists(EMAIL_DOMAINS_CONFIG):
        return {}
    
    try:
        with open(EMAIL_DOMAINS_CONFIG, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_domains_config(config):
    """Save email domains configuration."""
    _ensure_config_dir()
    
    try:
        with open(EMAIL_DOMAINS_CONFIG, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except IOError as e:
        show_error(f"Failed to save config: {e}")
        return False


def _get_domain_config(domain):
    """Get configuration for a specific domain."""
    config = _load_domains_config()
    return config.get(domain)


def _validate_domain(domain):
    """Validate domain format."""
    if not domain or '.' not in domain:
        return False
    if domain.startswith('.') or domain.endswith('.'):
        return False
    return True


def _validate_laravel_path(path):
    """Validate Laravel project path."""
    if not os.path.exists(path):
        return False, "Path does not exist"
    
    artisan_path = os.path.join(path, 'artisan')
    if not os.path.exists(artisan_path):
        return False, "artisan file not found"
    
    return True, None
```

**Step 2: Commit**

```bash
git add modules/email.py
git commit -m "feat(email): add config file management functions"
```

---

## Task 16.4: Implement setup_receive_mode()

**Files:**
- Modify: `modules/email.py`

**Step 1: Add setup_receive_mode() function**

```python
def setup_receive_mode():
    """Configure Postfix for receive mode (catch-all to Laravel)."""
    clear_screen()
    show_header()
    show_panel("Setup Receive Mode", title="Email Server", style="cyan")
    
    if not is_installed("postfix"):
        show_error("Postfix is not installed.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Receive Mode will:[/bold]")
    console.print("  • Listen on all interfaces (port 25)")
    console.print("  • Accept incoming email for configured domains")
    console.print("  • Pipe emails to Laravel artisan commands")
    console.print()
    console.print("[yellow]Prerequisites:[/yellow]")
    console.print("  • DNS MX record pointing to this server")
    console.print("  • Port 25 open in firewall")
    console.print("  • At least one domain configured")
    console.print()
    
    if not confirm_action("Configure Postfix for receive mode?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Install jq if needed
    if not is_installed("jq"):
        show_info("Installing jq (required for pipe script)...")
        run_command("apt install -y jq", check=False, silent=True)
    
    show_info("Configuring receive mode...")
    
    # Configure main.cf for receive mode
    settings = {
        "inet_interfaces": "all",
        "mydestination": "$myhostname, localhost.$mydomain, localhost",
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
    
    if not success:
        show_error("Failed to configure receive mode.")
        press_enter_to_continue()
        return
    
    # Install vexo-pipe script
    if not _install_vexo_pipe():
        show_error("Failed to install pipe script.")
        press_enter_to_continue()
        return
    
    # Regenerate Postfix files if domains exist
    config = _load_domains_config()
    if config:
        _regenerate_postfix_files()
    
    service_control("postfix", "restart")
    
    if is_service_running("postfix"):
        show_success("Receive mode configured!")
        console.print()
        if not config:
            console.print("[yellow]No domains configured yet.[/yellow]")
            console.print("[dim]Use 'Manage Domains > Add Domain' to add one.[/dim]")
        else:
            console.print(f"[dim]{len(config)} domain(s) configured.[/dim]")
    else:
        show_warning("Configuration applied but Postfix may not be running.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/email.py
git commit -m "feat(email): implement setup_receive_mode()"
```

---

## Task 16.5: Implement add_domain_interactive() and add_domain()

**Files:**
- Modify: `modules/email.py`

**Step 1: Add domain management functions**

```python
# =============================================================================
# Domain Management
# =============================================================================

def add_domain_interactive():
    """Interactive prompt to add a new email domain."""
    clear_screen()
    show_header()
    show_panel("Add Domain", title="Manage Domains", style="cyan")
    
    if not is_installed("postfix"):
        show_error("Postfix is not installed.")
        press_enter_to_continue()
        return
    
    # Check if receive mode is enabled
    inet_interfaces = _get_postfix_setting("inet_interfaces")
    if inet_interfaces == "loopback-only":
        show_warning("Postfix is in send-only mode.")
        console.print("[dim]Switch to receive mode first.[/dim]")
        press_enter_to_continue()
        return
    
    domain = text_input(
        title="Domain",
        message="Enter domain name (e.g., example.com):"
    )
    
    if not domain:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    domain = domain.lower().strip()
    
    if not _validate_domain(domain):
        show_error("Invalid domain format.")
        press_enter_to_continue()
        return
    
    # Check if domain already exists
    config = _load_domains_config()
    if domain in config:
        show_error(f"Domain {domain} already configured.")
        press_enter_to_continue()
        return
    
    laravel_path = text_input(
        title="Laravel Path",
        message="Enter Laravel project path:",
        default="/var/www/html"
    )
    
    if not laravel_path:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    valid, error = _validate_laravel_path(laravel_path)
    if not valid:
        show_error(f"Invalid Laravel path: {error}")
        press_enter_to_continue()
        return
    
    artisan_cmd = text_input(
        title="Artisan Command",
        message="Enter artisan command to handle emails:",
        default="email:incoming"
    )
    
    if not artisan_cmd:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  Domain: {domain}")
    console.print(f"  Laravel Path: {laravel_path}")
    console.print(f"  Artisan Command: {artisan_cmd}")
    console.print()
    
    if not confirm_action(f"Add domain {domain}?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = add_domain(domain, laravel_path, artisan_cmd)
    
    if success:
        show_success(f"Domain {domain} added!")
        console.print()
        console.print("[dim]Postfix has been reloaded.[/dim]")
    else:
        show_error("Failed to add domain.")
    
    press_enter_to_continue()


def add_domain(domain, laravel_path, artisan_cmd):
    """
    Add a new email domain.
    
    Args:
        domain: Domain name
        laravel_path: Path to Laravel project
        artisan_cmd: Artisan command to execute
    
    Returns:
        bool: True if successful
    """
    config = _load_domains_config()
    
    config[domain] = {
        "path": laravel_path,
        "command": artisan_cmd,
        "active": True
    }
    
    if not _save_domains_config(config):
        return False
    
    if not _regenerate_postfix_files():
        return False
    
    return service_control("postfix", "reload")
```

**Step 2: Commit**

```bash
git add modules/email.py
git commit -m "feat(email): implement add_domain_interactive() and add_domain()"
```

---

## Task 16.6: Implement remove_domain() and list_domains()

**Files:**
- Modify: `modules/email.py`

**Step 1: Add remove and list functions**

```python
def remove_domain_interactive():
    """Interactive prompt to remove an email domain."""
    clear_screen()
    show_header()
    show_panel("Remove Domain", title="Manage Domains", style="cyan")
    
    config = _load_domains_config()
    
    if not config:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    domains = list(config.keys())
    
    console.print("[bold]Configured domains:[/bold]")
    for d in domains:
        console.print(f"  • {d}")
    console.print()
    
    domain = select_from_list(
        title="Remove Domain",
        message="Select domain to remove:",
        options=domains
    )
    
    if not domain:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print(f"[red bold]WARNING: This will stop receiving emails for {domain}![/red bold]")
    console.print()
    
    if not confirm_action(f"Remove domain {domain}?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    success = remove_domain(domain)
    
    if success:
        show_success(f"Domain {domain} removed!")
    else:
        show_error("Failed to remove domain.")
    
    press_enter_to_continue()


def remove_domain(domain):
    """
    Remove an email domain.
    
    Args:
        domain: Domain name to remove
    
    Returns:
        bool: True if successful
    """
    config = _load_domains_config()
    
    if domain not in config:
        return False
    
    del config[domain]
    
    if not _save_domains_config(config):
        return False
    
    if not _regenerate_postfix_files():
        return False
    
    return service_control("postfix", "reload")


def list_domains():
    """Display all configured email domains."""
    clear_screen()
    show_header()
    show_panel("Email Domains", title="Manage Domains", style="cyan")
    
    config = _load_domains_config()
    
    if not config:
        show_info("No domains configured.")
        console.print()
        console.print("[dim]Use 'Add Domain' to configure one.[/dim]")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Domain", "style": "cyan"},
        {"name": "Laravel Path"},
        {"name": "Command"},
        {"name": "Status"},
    ]
    
    rows = []
    for domain, cfg in config.items():
        status = "[green]Active[/green]" if cfg.get("active", True) else "[red]Inactive[/red]"
        rows.append([
            domain,
            cfg.get("path", "N/A"),
            cfg.get("command", "N/A"),
            status
        ])
    
    show_table("Configured Domains", columns, rows)
    
    press_enter_to_continue()
```

**Step 2: Add select_from_list import if not present**

Ensure `select_from_list` is imported from `ui.menu`.

**Step 3: Commit**

```bash
git add modules/email.py
git commit -m "feat(email): implement remove_domain() and list_domains()"
```

---

## Task 16.7: Implement edit_domain_interactive()

**Files:**
- Modify: `modules/email.py`

**Step 1: Add edit domain function**

```python
def edit_domain_interactive():
    """Interactive prompt to edit a domain configuration."""
    clear_screen()
    show_header()
    show_panel("Edit Domain", title="Manage Domains", style="cyan")
    
    config = _load_domains_config()
    
    if not config:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    domains = list(config.keys())
    
    domain = select_from_list(
        title="Edit Domain",
        message="Select domain to edit:",
        options=domains
    )
    
    if not domain:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    current = config[domain]
    
    console.print(f"[bold]Current configuration for {domain}:[/bold]")
    console.print(f"  Path: {current.get('path')}")
    console.print(f"  Command: {current.get('command')}")
    console.print(f"  Active: {current.get('active', True)}")
    console.print()
    
    laravel_path = text_input(
        title="Laravel Path",
        message="Enter new Laravel path (or keep current):",
        default=current.get("path", "")
    )
    
    if not laravel_path:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    valid, error = _validate_laravel_path(laravel_path)
    if not valid:
        show_error(f"Invalid Laravel path: {error}")
        press_enter_to_continue()
        return
    
    artisan_cmd = text_input(
        title="Artisan Command",
        message="Enter new artisan command (or keep current):",
        default=current.get("command", "email:incoming")
    )
    
    if not artisan_cmd:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    config[domain] = {
        "path": laravel_path,
        "command": artisan_cmd,
        "active": current.get("active", True)
    }
    
    if _save_domains_config(config):
        show_success(f"Domain {domain} updated!")
    else:
        show_error("Failed to update domain.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/email.py
git commit -m "feat(email): implement edit_domain_interactive()"
```

---

## Task 16.8: Add Postfix file generators

**Files:**
- Modify: `modules/email.py`

**Step 1: Add Postfix file generation functions**

```python
# =============================================================================
# Postfix File Generators
# =============================================================================

def _regenerate_postfix_files():
    """Regenerate Postfix virtual and master.cf files."""
    config = _load_domains_config()
    
    if not _generate_virtual_file(config):
        return False
    
    if not _generate_master_cf_entries(config):
        return False
    
    if not _update_main_cf_virtual(config):
        return False
    
    return True


def _generate_virtual_file(config):
    """Generate /etc/postfix/virtual file."""
    lines = ["# Generated by vexo-cli - DO NOT EDIT MANUALLY\n"]
    
    for domain in config.keys():
        if config[domain].get("active", True):
            transport_name = f"laravel-{domain.replace('.', '-')}"
            lines.append(f"@{domain}    {transport_name}\n")
    
    try:
        with open(POSTFIX_VIRTUAL, 'w') as f:
            f.writelines(lines)
        
        # Run postmap to create .db file
        result = run_command(f"postmap {POSTFIX_VIRTUAL}", check=False, silent=True)
        return result.returncode == 0
    except IOError as e:
        show_error(f"Failed to write virtual file: {e}")
        return False


def _generate_master_cf_entries(config):
    """Add pipe transport entries to master.cf."""
    try:
        # Read existing master.cf
        with open(POSTFIX_MASTER, 'r') as f:
            content = f.read()
        
        # Remove existing vexo-cli entries
        lines = content.split('\n')
        new_lines = []
        skip_next = False
        
        for line in lines:
            if '# vexo-cli-start' in line:
                skip_next = True
                continue
            if '# vexo-cli-end' in line:
                skip_next = False
                continue
            if skip_next:
                continue
            new_lines.append(line)
        
        # Add new entries
        new_lines.append("# vexo-cli-start")
        
        for domain in config.keys():
            if config[domain].get("active", True):
                transport_name = f"laravel-{domain.replace('.', '-')}"
                new_lines.append(f"{transport_name} unix - n n - - pipe")
                new_lines.append(f"  flags=F user=www-data argv={VEXO_PIPE_SCRIPT} {domain}")
        
        new_lines.append("# vexo-cli-end")
        
        with open(POSTFIX_MASTER, 'w') as f:
            f.write('\n'.join(new_lines))
        
        return True
    except IOError as e:
        show_error(f"Failed to update master.cf: {e}")
        return False


def _update_main_cf_virtual(config):
    """Update main.cf with virtual_alias settings."""
    domains = [d for d in config.keys() if config[d].get("active", True)]
    
    if domains:
        virtual_domains = ", ".join(domains)
        settings = {
            "virtual_alias_domains": virtual_domains,
            "virtual_alias_maps": f"hash:{POSTFIX_VIRTUAL}",
        }
    else:
        # Clear virtual settings if no domains
        settings = {
            "virtual_alias_domains": "",
            "virtual_alias_maps": "",
        }
    
    for key, value in settings.items():
        result = run_command(
            f'postconf -e "{key}={value}"',
            check=False,
            silent=True
        )
        if result.returncode != 0:
            return False
    
    return True
```

**Step 2: Commit**

```bash
git add modules/email.py
git commit -m "feat(email): add Postfix file generators"
```

---

## Task 16.9: Create vexo-pipe script installer

**Files:**
- Modify: `modules/email.py`

**Step 1: Add vexo-pipe script installer**

```python
def _install_vexo_pipe():
    """Install the vexo-pipe script."""
    script_content = '''#!/bin/bash
#
# vexo-pipe - Email pipe handler for vexo-cli
# Pipes incoming email to Laravel artisan command
#

DOMAIN="$1"
CONFIG_FILE="/etc/vexo/email-domains.json"
LOG_FILE="/var/log/vexo-email.log"

# Check if config exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "$(date): ERROR - Config file not found" >> "$LOG_FILE"
    exit 75
fi

# Get config for domain
PATH_VALUE=$(jq -r ".\\\"$DOMAIN\\\".path" "$CONFIG_FILE")
CMD_VALUE=$(jq -r ".\\\"$DOMAIN\\\".command" "$CONFIG_FILE")

# Validate
if [ "$PATH_VALUE" == "null" ] || [ -z "$PATH_VALUE" ]; then
    echo "$(date): ERROR - Domain $DOMAIN not configured" >> "$LOG_FILE"
    exit 75
fi

if [ ! -d "$PATH_VALUE" ]; then
    echo "$(date): ERROR - Laravel path not found: $PATH_VALUE" >> "$LOG_FILE"
    exit 75
fi

# Log incoming email
echo "$(date): Incoming email for $DOMAIN -> $CMD_VALUE" >> "$LOG_FILE"

# Execute artisan command with email on stdin
cd "$PATH_VALUE" && /usr/bin/php artisan $CMD_VALUE 2>> "$LOG_FILE"
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "$(date): ERROR - Artisan exited with code $EXIT_CODE" >> "$LOG_FILE"
fi

exit $EXIT_CODE
'''
    
    try:
        with open(VEXO_PIPE_SCRIPT, 'w') as f:
            f.write(script_content)
        
        # Make executable
        os.chmod(VEXO_PIPE_SCRIPT, 0o755)
        
        # Create log file with proper permissions
        if not os.path.exists(VEXO_EMAIL_LOG):
            with open(VEXO_EMAIL_LOG, 'w') as f:
                f.write("")
            os.chmod(VEXO_EMAIL_LOG, 0o666)
        
        return True
    except IOError as e:
        show_error(f"Failed to install pipe script: {e}")
        return False
```

**Step 2: Commit**

```bash
git add modules/email.py
git commit -m "feat(email): add vexo-pipe script installer"
```

---

## Task 16.10: Implement test_incoming_interactive()

**Files:**
- Modify: `modules/email.py`

**Step 1: Add test incoming function**

```python
def test_incoming_interactive():
    """Test incoming email handling by piping directly to Laravel."""
    clear_screen()
    show_header()
    show_panel("Test Incoming Email", title="Test Email", style="cyan")
    
    config = _load_domains_config()
    
    if not config:
        show_error("No domains configured.")
        press_enter_to_continue()
        return
    
    domains = [d for d in config.keys() if config[d].get("active", True)]
    
    if not domains:
        show_error("No active domains.")
        press_enter_to_continue()
        return
    
    domain = select_from_list(
        title="Test Domain",
        message="Select domain to test:",
        options=domains
    )
    
    if not domain:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    cfg = config[domain]
    
    console.print(f"[bold]Testing {domain}:[/bold]")
    console.print(f"  Path: {cfg['path']}")
    console.print(f"  Command: {cfg['command']}")
    console.print()
    
    if not confirm_action("Send test email to Laravel?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Generate test email (RFC 2822 format)
    hostname = get_hostname()
    test_email = f"""From: test@{domain}
To: catchall@{domain}
Subject: Test Email from vexo-cli
Date: {_get_rfc2822_date()}
Message-ID: <test-{int(__import__('time').time())}@{hostname}>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8

This is a test email from vexo-cli.

If your Laravel application received this, the pipe configuration is working correctly.

--
Generated by vexo-cli test
"""
    
    show_info("Piping test email to Laravel...")
    
    # Pipe directly to artisan (bypass Postfix for testing)
    cmd = f'cd {cfg["path"]} && echo "{test_email}" | /usr/bin/php artisan {cfg["command"]}'
    
    result = run_command(cmd, check=False, silent=False)
    
    console.print()
    if result.returncode == 0:
        show_success("Test email processed successfully!")
        if result.stdout:
            console.print("[dim]Output:[/dim]")
            console.print(result.stdout)
    else:
        show_error(f"Test failed with exit code {result.returncode}")
        if result.stderr:
            console.print("[dim]Error:[/dim]")
            console.print(result.stderr)
    
    press_enter_to_continue()


def _get_rfc2822_date():
    """Get current date in RFC 2822 format."""
    from email.utils import formatdate
    return formatdate(localtime=True)
```

**Step 2: Commit**

```bash
git add modules/email.py
git commit -m "feat(email): implement test_incoming_interactive()"
```

---

## Task 16.11: Implement view_mail_log()

**Files:**
- Modify: `modules/email.py`

**Step 1: Add view mail log function**

```python
def view_mail_log():
    """Display mail log entries."""
    clear_screen()
    show_header()
    show_panel("Mail Log", title="Email Server", style="cyan")
    
    choice = show_submenu(
        title="Select Log",
        options=[
            ("system", "1. System Mail Log (/var/log/mail.log)"),
            ("vexo", "2. Vexo Pipe Log (/var/log/vexo-email.log)"),
            ("back", "← Back"),
        ],
    )
    
    if choice == "system":
        log_path = "/var/log/mail.log"
    elif choice == "vexo":
        log_path = VEXO_EMAIL_LOG
    else:
        return
    
    if not os.path.exists(log_path):
        show_error(f"Log file not found: {log_path}")
        press_enter_to_continue()
        return
    
    console.print(f"[bold]Last 50 lines of {log_path}:[/bold]")
    console.print()
    
    result = run_command(f"tail -50 {log_path}", check=False, silent=True)
    
    if result.returncode == 0:
        console.print(result.stdout or "[dim]Log is empty[/dim]")
    else:
        show_error("Failed to read log file.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/email.py
git commit -m "feat(email): implement view_mail_log()"
```

---

## Task 16.12: Implement queue management functions

**Files:**
- Modify: `modules/email.py`

**Step 1: Add queue management functions**

```python
def view_queue():
    """Display mail queue."""
    clear_screen()
    show_header()
    show_panel("Mail Queue", title="Queue Management", style="cyan")
    
    if not is_installed("postfix"):
        show_error("Postfix is not installed.")
        press_enter_to_continue()
        return
    
    result = run_command("postqueue -p", check=False, silent=True)
    
    if result.returncode == 0:
        output = result.stdout.strip()
        if "Mail queue is empty" in output or not output:
            show_info("Mail queue is empty.")
        else:
            console.print("[bold]Mail Queue:[/bold]")
            console.print()
            console.print(output)
    else:
        show_error("Failed to get queue status.")
    
    press_enter_to_continue()


def flush_queue():
    """Attempt to deliver all queued messages."""
    clear_screen()
    show_header()
    show_panel("Flush Queue", title="Queue Management", style="cyan")
    
    if not is_installed("postfix"):
        show_error("Postfix is not installed.")
        press_enter_to_continue()
        return
    
    console.print("[bold]This will attempt to deliver all queued messages.[/bold]")
    console.print()
    
    if not confirm_action("Flush mail queue?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    result = run_command("postqueue -f", check=False, silent=True)
    
    if result.returncode == 0:
        show_success("Queue flush initiated!")
    else:
        show_error("Failed to flush queue.")
    
    press_enter_to_continue()


def delete_queue():
    """Delete all queued messages."""
    clear_screen()
    show_header()
    show_panel("Delete Queue", title="Queue Management", style="cyan")
    
    if not is_installed("postfix"):
        show_error("Postfix is not installed.")
        press_enter_to_continue()
        return
    
    console.print("[red bold]WARNING: This will permanently delete ALL queued emails![/red bold]")
    console.print()
    
    if not confirm_action("Delete all queued messages?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    result = run_command("postsuper -d ALL", check=False, silent=True)
    
    if result.returncode == 0:
        show_success("All queued messages deleted!")
    else:
        show_error("Failed to delete queue.")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/email.py
git commit -m "feat(email): implement queue management functions"
```

---

## Task 16.13: Update show_postfix_status() for receive mode

**Files:**
- Modify: `modules/email.py`

**Step 1: Update show_postfix_status() to show domain info**

Find the existing `show_postfix_status()` function and update it:

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
    
    # Mode
    console.print()
    inet_interfaces = _get_postfix_setting("inet_interfaces")
    if inet_interfaces == "loopback-only":
        console.print("[bold]Mode:[/bold] [cyan]Send-Only[/cyan]")
    elif inet_interfaces == "all":
        console.print("[bold]Mode:[/bold] [yellow]Receive (Catch-All)[/yellow]")
    else:
        console.print(f"[bold]Mode:[/bold] {inet_interfaces}")
    
    # Configuration
    console.print()
    console.print("[bold]Configuration:[/bold]")
    
    settings = [
        ("myhostname", "Hostname"),
        ("mydomain", "Domain"),
        ("myorigin", "Origin"),
        ("inet_interfaces", "Listen On"),
    ]
    
    columns = [
        {"name": "Setting", "style": "cyan"},
        {"name": "Value"},
    ]
    
    rows = []
    for key, label in settings:
        value = _get_postfix_setting(key)
        rows.append([label, value or "[dim]Not set[/dim]"])
    
    show_table("Postfix Settings", columns, rows)
    
    # Email domains (if receive mode)
    if inet_interfaces == "all":
        console.print()
        console.print("[bold]Email Domains:[/bold]")
        
        config = _load_domains_config()
        if config:
            for domain, cfg in config.items():
                status = "[green]●[/green]" if cfg.get("active", True) else "[red]●[/red]"
                console.print(f"  {status} {domain} → {cfg.get('command')}")
        else:
            console.print("[dim]  No domains configured[/dim]")
    
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
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/email.py
git commit -m "feat(email): update show_postfix_status() for receive mode"
```

---

## Summary

After completion, `modules/email.py` will have:

**Menu Structure:**
- Main menu with 7 options
- Configure Mode submenu (Send-Only / Receive)
- Manage Domains submenu (Add/Remove/List/Edit)
- Test Email submenu (Send/Incoming)
- Queue Management submenu (View/Flush/Delete)

**Core Functions:**
- `setup_receive_mode()` - Configure Postfix for catch-all
- `add_domain()` / `remove_domain()` - Domain CRUD
- `_regenerate_postfix_files()` - Generate virtual, master.cf
- `_install_vexo_pipe()` - Install pipe script
- `test_incoming_interactive()` - Test Laravel pipe
- Queue management (view/flush/delete)

**Config Files Managed:**
- `/etc/vexo/email-domains.json` - Domain configuration
- `/etc/postfix/virtual` - Catch-all mappings
- `/etc/postfix/master.cf` - Pipe transports
- `/usr/local/bin/vexo-pipe` - Pipe handler script
