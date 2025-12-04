"""Clean uninstall - remove vexo and all installed packages/data."""

import os
import subprocess
import time

from ui.components import (
    console,
    clear_screen,
    show_header,
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
    if not confirm_action("Are you sure you want to continue?"):
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
    
    # Use subprocess to run with --no-confirm since we already confirmed
    result = subprocess.run(
        ["bash", script_path, "--no-confirm"],
        capture_output=False
    )
    
    if result.returncode == 0:
        show_success("Clean uninstall complete!")
    else:
        handle_error("E1006", "Clean uninstall failed")
    
    # Don't press enter - vexo is gone!
