# Clean Uninstall Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add clean uninstall feature that completely removes vexo and all installed packages/data, returning VPS to clean state.

**Architecture:** Create shared bash script `scripts/clean-uninstall.sh` with triple confirmation (preview + y/N + type "CLEAN UNINSTALL"). Accessible via `install.sh --clean-uninstall` and vexo menu (System Setup > Clean Uninstall).

**Tech Stack:** Bash (install.sh, clean-uninstall.sh), Python (vexo menu integration)

---

## Task 1: Create Clean Uninstall Script

**Files:**
- Create: `scripts/clean-uninstall.sh`

**Step 1: Create the script**

```bash
#!/bin/bash
#
# Vexo Clean Uninstall Script
# Removes vexo and ALL installed packages/data
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${CYAN}→ $1${NC}"
}

# Check root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

# Show warning banner
show_warning_banner() {
    echo ""
    echo -e "${RED}┌─────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${RED}│                    ⚠️  CLEAN UNINSTALL                          │${NC}"
    echo -e "${RED}├─────────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${RED}│  This will PERMANENTLY DELETE:                                  │${NC}"
    echo -e "${RED}│                                                                 │${NC}"
    echo -e "${RED}│  📦 Packages:                                                   │${NC}"
    echo -e "${RED}│     • nginx, php8.x, mariadb, postgresql, redis                 │${NC}"
    echo -e "${RED}│     • postfix, dovecot, fail2ban, ufw, supervisor, certbot      │${NC}"
    echo -e "${RED}│                                                                 │${NC}"
    echo -e "${RED}│  📁 Data & Configs:                                             │${NC}"
    echo -e "${RED}│     • /var/www/* (all websites)                                 │${NC}"
    echo -e "${RED}│     • /var/lib/mysql, /var/lib/postgresql (databases)           │${NC}"
    echo -e "${RED}│     • /etc/nginx, /etc/php, /etc/postfix, etc.                  │${NC}"
    echo -e "${RED}│     • /etc/letsencrypt (SSL certificates)                       │${NC}"
    echo -e "${RED}│     • /var/mail/* (all emails)                                  │${NC}"
    echo -e "${RED}│                                                                 │${NC}"
    echo -e "${RED}│  🔧 Vexo:                                                       │${NC}"
    echo -e "${RED}│     • /opt/vexo, /var/log/vexo, ~/.vexo                         │${NC}"
    echo -e "${RED}│                                                                 │${NC}"
    echo -e "${RED}│  ⚠️  THIS CANNOT BE UNDONE!                                     │${NC}"
    echo -e "${RED}└─────────────────────────────────────────────────────────────────┘${NC}"
    echo ""
}

# First confirmation
confirm_step1() {
    read -p "Are you sure you want to continue? (y/N): " response
    case "$response" in
        [yY][eE][sS]|[yY]) 
            return 0
            ;;
        *)
            print_info "Cancelled."
            exit 0
            ;;
    esac
}

# Second confirmation - type exact phrase
confirm_step2() {
    echo ""
    read -p "Type 'CLEAN UNINSTALL' to confirm: " response
    if [ "$response" != "CLEAN UNINSTALL" ]; then
        print_error "Confirmation failed. Aborting."
        exit 1
    fi
}

# Stop services first
stop_services() {
    print_info "Stopping services..."
    
    services="nginx php8.3-fpm php8.2-fpm php8.1-fpm php8.0-fpm mariadb mysql postgresql redis-server postfix dovecot fail2ban supervisor"
    
    for service in $services; do
        systemctl stop "$service" 2>/dev/null || true
        systemctl disable "$service" 2>/dev/null || true
    done
    
    print_success "Services stopped"
}

# Remove packages
remove_packages() {
    print_info "Removing packages..."
    
    # Stop apt processes if any
    killall apt apt-get 2>/dev/null || true
    
    # Purge packages
    DEBIAN_FRONTEND=noninteractive apt purge -y \
        nginx* php* mariadb* mysql* postgresql* redis* \
        postfix* dovecot* roundcube* fail2ban ufw \
        supervisor certbot* python3-certbot* \
        2>/dev/null || true
    
    # Autoremove
    apt autoremove -y 2>/dev/null || true
    apt autoclean 2>/dev/null || true
    
    print_success "Packages removed"
}

# Remove directories
remove_directories() {
    print_info "Removing data and configurations..."
    
    # Vexo
    rm -rf /opt/vexo
    rm -rf /var/log/vexo
    rm -rf /etc/vexo
    rm -rf ~/.vexo
    rm -rf /root/.vexo
    rm -f /usr/local/bin/vexo
    
    # Web
    rm -rf /var/www
    rm -rf /etc/nginx
    
    # PHP
    rm -rf /etc/php
    
    # Databases
    rm -rf /var/lib/mysql
    rm -rf /var/lib/postgresql
    rm -rf /etc/mysql
    rm -rf /etc/postgresql
    
    # Redis
    rm -rf /var/lib/redis
    rm -rf /etc/redis
    
    # Email
    rm -rf /var/mail
    rm -rf /var/spool/mail
    rm -rf /etc/postfix
    rm -rf /etc/dovecot
    rm -rf /etc/opendkim
    
    # Security
    rm -rf /etc/fail2ban
    rm -rf /etc/letsencrypt
    
    # Supervisor
    rm -rf /etc/supervisor/conf.d/*
    
    # Logs
    rm -rf /var/log/nginx
    rm -rf /var/log/php*
    rm -rf /var/log/mysql
    rm -rf /var/log/postgresql
    rm -rf /var/log/mail.*
    rm -rf /var/log/fail2ban.log*
    
    print_success "Data and configurations removed"
}

# Main
main() {
    show_warning_banner
    confirm_step1
    confirm_step2
    
    echo ""
    print_warning "Starting clean uninstall in 3 seconds... (Ctrl+C to cancel)"
    sleep 3
    
    echo ""
    stop_services
    remove_packages
    remove_directories
    
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✓ Clean uninstall complete!                       ${NC}"
    echo -e "${GREEN}  Your VPS is now clean.                            ${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
    echo ""
}

main
```

**Step 2: Make executable**

```bash
chmod +x scripts/clean-uninstall.sh
```

**Step 3: Commit**

```bash
git add scripts/clean-uninstall.sh
git commit -m "feat: add clean uninstall script"
```

---

## Task 2: Add --clean-uninstall to install.sh

**Files:**
- Modify: `install.sh`

**Step 1: Add clean_uninstall function after uninstall function (around line 240)**

Find this section:
```bash
# Uninstall function
uninstall() {
    ...
}
```

Add after it:
```bash
# Clean uninstall function
clean_uninstall() {
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    if [ -f "$SCRIPT_DIR/scripts/clean-uninstall.sh" ]; then
        bash "$SCRIPT_DIR/scripts/clean-uninstall.sh"
    elif [ -f "/opt/vexo/scripts/clean-uninstall.sh" ]; then
        bash "/opt/vexo/scripts/clean-uninstall.sh"
    else
        print_error "Clean uninstall script not found."
        print_info "Download and run manually:"
        echo "  curl -sSL https://raw.githubusercontent.com/pripanggalih/vexo/main/scripts/clean-uninstall.sh | sudo bash"
        exit 1
    fi
}
```

**Step 2: Add case handler for --clean-uninstall**

Find this section:
```bash
case "${1:-}" in
    --uninstall)
        check_root
        uninstall
        ;;
```

Add after --uninstall case:
```bash
    --clean-uninstall)
        check_root
        clean_uninstall
        ;;
```

**Step 3: Update help text**

Find:
```bash
        echo "  sudo ./install.sh --uninstall  Uninstall vexo"
```

Add after:
```bash
        echo "  sudo ./install.sh --clean-uninstall  Remove vexo + ALL packages/data"
```

**Step 4: Commit**

```bash
git add install.sh
git commit -m "feat: add --clean-uninstall flag to install.sh"
```

---

## Task 3: Add Clean Uninstall to Vexo Menu

**Files:**
- Create: `modules/system/clean_uninstall.py`
- Modify: `modules/system/__init__.py`

**Step 1: Create clean_uninstall.py**

```python
"""Clean uninstall - remove vexo and all installed packages/data."""

import os
import subprocess

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_success,
    show_warning,
    press_enter_to_continue,
)
from ui.menu import confirm_action, text_input
from utils.shell import check_root
from utils.error_handler import handle_error


def show_clean_uninstall():
    """Show clean uninstall confirmation and execute."""
    clear_screen()
    show_header()
    
    # Warning panel
    console.print()
    console.print("[bold red]┌─────────────────────────────────────────────────────────────────┐[/bold red]")
    console.print("[bold red]│                    ⚠️  CLEAN UNINSTALL                          │[/bold red]")
    console.print("[bold red]├─────────────────────────────────────────────────────────────────┤[/bold red]")
    console.print("[bold red]│  This will PERMANENTLY DELETE:                                  │[/bold red]")
    console.print("[bold red]│                                                                 │[/bold red]")
    console.print("[bold red]│  📦 Packages:                                                   │[/bold red]")
    console.print("[bold red]│     • nginx, php8.x, mariadb, postgresql, redis                 │[/bold red]")
    console.print("[bold red]│     • postfix, dovecot, fail2ban, ufw, supervisor, certbot      │[/bold red]")
    console.print("[bold red]│                                                                 │[/bold red]")
    console.print("[bold red]│  📁 Data & Configs:                                             │[/bold red]")
    console.print("[bold red]│     • /var/www/* (all websites)                                 │[/bold red]")
    console.print("[bold red]│     • /var/lib/mysql, /var/lib/postgresql (databases)           │[/bold red]")
    console.print("[bold red]│     • /etc/nginx, /etc/php, /etc/postfix, etc.                  │[/bold red]")
    console.print("[bold red]│     • /etc/letsencrypt (SSL certificates)                       │[/bold red]")
    console.print("[bold red]│     • /var/mail/* (all emails)                                  │[/bold red]")
    console.print("[bold red]│                                                                 │[/bold red]")
    console.print("[bold red]│  🔧 Vexo:                                                       │[/bold red]")
    console.print("[bold red]│     • /opt/vexo, /var/log/vexo, ~/.vexo                         │[/bold red]")
    console.print("[bold red]│                                                                 │[/bold red]")
    console.print("[bold red]│  ⚠️  THIS CANNOT BE UNDONE!                                     │[/bold red]")
    console.print("[bold red]└─────────────────────────────────────────────────────────────────┘[/bold red]")
    console.print()
    
    # First confirmation
    if not confirm_action("Are you sure you want to continue?", default=False):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Second confirmation - type exact phrase
    console.print()
    response = text_input("Type 'CLEAN UNINSTALL' to confirm:")
    
    if response != "CLEAN UNINSTALL":
        handle_error("E1005", "Confirmation failed", details="You must type exactly: CLEAN UNINSTALL")
        press_enter_to_continue()
        return
    
    # Check root
    if not check_root():
        handle_error("E1001", "Root privileges required", suggestions=["Run with: sudo vexo"])
        press_enter_to_continue()
        return
    
    # Execute clean uninstall script
    console.print()
    show_warning("Starting clean uninstall in 3 seconds... (Ctrl+C to cancel)")
    
    import time
    time.sleep(3)
    
    script_path = "/opt/vexo/scripts/clean-uninstall.sh"
    
    if not os.path.exists(script_path):
        handle_error("E1004", "Clean uninstall script not found", details=script_path)
        press_enter_to_continue()
        return
    
    # Run the script (it will handle the rest)
    console.print()
    console.print("[cyan]Running clean uninstall...[/cyan]")
    console.print()
    
    # Use subprocess to run and show output
    result = subprocess.run(
        ["bash", script_path, "--no-confirm"],
        capture_output=False
    )
    
    if result.returncode == 0:
        show_success("Clean uninstall complete!")
    else:
        handle_error("E1006", "Clean uninstall failed")
    
    # Don't press enter - vexo is gone!
```

**Step 2: Update modules/system/__init__.py**

Add import:
```python
from modules.system.clean_uninstall import show_clean_uninstall
```

Add to __all__ if exists.

**Step 3: Commit**

```bash
git add modules/system/clean_uninstall.py modules/system/__init__.py
git commit -m "feat: add clean uninstall to system module"
```

---

## Task 4: Add Menu Entry in main.py

**Files:**
- Modify: `main.py`

**Step 1: Find system menu and add Clean Uninstall option**

Find where system menu is defined and add:
```python
("clean_uninstall", "⚠️ Clean Uninstall (remove everything)")
```

Add handler:
```python
if choice == "clean_uninstall":
    from modules.system.clean_uninstall import show_clean_uninstall
    show_clean_uninstall()
```

**Step 2: Commit**

```bash
git add main.py
git commit -m "feat: add clean uninstall to system menu"
```

---

## Task 5: Update clean-uninstall.sh for --no-confirm flag

**Files:**
- Modify: `scripts/clean-uninstall.sh`

**Step 1: Add --no-confirm handling at the start of main()**

```bash
# Handle --no-confirm flag (called from vexo menu, already confirmed)
if [ "${1:-}" = "--no-confirm" ]; then
    stop_services
    remove_packages
    remove_directories
    
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✓ Clean uninstall complete!                       ${NC}"
    echo -e "${GREEN}  Your VPS is now clean.                            ${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
    echo ""
    exit 0
fi
```

**Step 2: Commit all and push**

```bash
git add -A
git commit -m "feat: add --no-confirm flag to clean-uninstall.sh"
git push
```

---

## Summary

After completing all tasks:

1. ✅ `scripts/clean-uninstall.sh` - Standalone clean uninstall script
2. ✅ `install.sh --clean-uninstall` - CLI access from outside vexo
3. ✅ `modules/system/clean_uninstall.py` - Menu integration
4. ✅ Triple confirmation: preview → y/N → type "CLEAN UNINSTALL"
5. ✅ Removes all packages, data, configs, and vexo itself
