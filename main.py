#!/usr/bin/env python3
"""
vexo - VPS Management CLI for Ubuntu/Debian

Entry point for the application.
"""

import sys
import os
import subprocess

from config import APP_NAME, APP_VERSION, APP_DESCRIPTION
from ui.components import clear_screen, show_header, show_system_bar, console
from ui.menu import show_main_menu

# Installation directory (when installed via install.sh)
INSTALL_DIR = "/opt/vexo"

from modules import system
from modules import webserver
from modules import runtime
from modules import database
from modules import email
from modules import monitor
from modules import firewall
from modules import ssl
from modules import fail2ban
from modules import supervisor
from modules import cron
from modules import setup


def check_python_version():
    """Ensure Python 3.8+ is being used."""
    if sys.version_info < (3, 8):
        print(f"Error: {APP_NAME} requires Python 3.8 or higher.")
        print(f"Current version: {sys.version}")
        sys.exit(1)


def show_root_warning():
    """Show warning if not running as root."""
    if os.geteuid() != 0:
        console.print(f"[yellow]Warning: {APP_NAME} requires root privileges for most operations.[/yellow]")
        console.print("[dim]Consider running with: sudo vexo[/dim]")
        console.print()


def check_for_updates():
    """Check if updates are available from GitHub."""
    # Only check if running from install directory
    if not os.path.exists(os.path.join(INSTALL_DIR, ".git")):
        return False, None
    
    try:
        # Fetch latest from remote
        result = subprocess.run(
            ["git", "fetch", "origin", "main"],
            cwd=INSTALL_DIR,
            capture_output=True,
            timeout=10
        )
        if result.returncode != 0:
            return False, None
        
        # Check if we're behind
        result = subprocess.run(
            ["git", "rev-list", "HEAD..origin/main", "--count"],
            cwd=INSTALL_DIR,
            capture_output=True,
            timeout=5
        )
        if result.returncode != 0:
            return False, None
        
        commits_behind = int(result.stdout.decode().strip())
        return commits_behind > 0, commits_behind
    except subprocess.TimeoutExpired:
        return False, None
    except ValueError:
        return False, None
    except OSError:
        return False, None


def perform_update():
    """Perform auto-update from GitHub with rollback support."""
    console.print("[cyan]⚡ Updating vexo...[/cyan]")
    
    previous_commit = None
    
    try:
        # Save current commit for rollback
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=INSTALL_DIR,
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            previous_commit = result.stdout.decode().strip()
        
        # Reset any local changes before pull
        subprocess.run(
            ["git", "reset", "--hard", "HEAD"],
            cwd=INSTALL_DIR,
            capture_output=True,
            timeout=10
        )
        
        # Git pull
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=INSTALL_DIR,
            capture_output=True,
            timeout=30
        )
        if result.returncode != 0:
            console.print("[red]✗ Failed to pull updates[/red]")
            if result.stderr:
                console.print(f"[dim]{result.stderr.decode()}[/dim]")
            return False
        
        console.print("[green]✓ Code updated[/green]")
        
        # Install dependencies
        console.print("[cyan]→ Updating dependencies...[/cyan]")
        
        # Check if using venv
        venv_pip = os.path.join(INSTALL_DIR, "venv", "bin", "pip")
        if os.path.exists(venv_pip):
            pip_cmd = [venv_pip, "install", "-r", "requirements.txt", "--quiet", "--upgrade"]
        else:
            pip_cmd = ["pip3", "install", "-r", "requirements.txt", "--quiet", "--upgrade", "--break-system-packages"]
        
        result = subprocess.run(
            pip_cmd,
            cwd=INSTALL_DIR,
            capture_output=True,
            timeout=120
        )
        
        # Fallback without --break-system-packages (create new list to avoid mutation)
        if result.returncode != 0 and "--break-system-packages" in pip_cmd:
            pip_cmd_fallback = [x for x in pip_cmd if x != "--break-system-packages"]
            result = subprocess.run(pip_cmd_fallback, cwd=INSTALL_DIR, capture_output=True, timeout=120)
        
        if result.returncode == 0:
            console.print("[green]✓ Dependencies updated[/green]")
        else:
            console.print("[yellow]! Dependencies may need manual update[/yellow]")
        
        console.print("[green]✓ Update complete! Restarting...[/green]")
        console.print()
        
        # Restart the application with --no-update to prevent infinite loop
        restart_args = [sys.executable] + [arg for arg in sys.argv if arg != "--no-update"]
        restart_args.append("--no-update")
        
        try:
            os.execv(sys.executable, restart_args)
        except OSError as e:
            console.print(f"[red]✗ Failed to restart: {e}[/red]")
            return False
        
    except subprocess.TimeoutExpired:
        console.print("[red]✗ Update timed out[/red]")
        _rollback_update(previous_commit)
        return False
    except OSError as e:
        console.print(f"[red]✗ Update failed: {e}[/red]")
        _rollback_update(previous_commit)
        return False


def _rollback_update(commit_hash):
    """Rollback to previous commit if update fails."""
    if not commit_hash:
        return
    
    console.print("[yellow]→ Rolling back to previous version...[/yellow]")
    try:
        result = subprocess.run(
            ["git", "checkout", commit_hash],
            cwd=INSTALL_DIR,
            capture_output=True,
            timeout=10
        )
        if result.returncode == 0:
            console.print("[green]✓ Rolled back successfully[/green]")
        else:
            console.print("[red]✗ Rollback failed - manual intervention needed[/red]")
    except (subprocess.TimeoutExpired, OSError):
        console.print("[red]✗ Rollback failed - manual intervention needed[/red]")


def main_loop():
    """Main menu loop."""
    while True:
        clear_screen()
        show_header()
        show_system_bar()
        show_root_warning()
        
        choice = show_main_menu(
            title=f"{APP_NAME} v{APP_VERSION}",
            options=[
                ("system", "1. System Setup & Update"),
                ("webserver", "2. Domain & Nginx"),
                ("php", "3. PHP Runtime"),
                ("nodejs", "4. Node.js Runtime"),
                ("database", "5. Database"),
                ("email", "6. Email Server"),
                ("monitor", "7. System Monitoring"),
                ("supervisor", "8. Supervisor (Queue Workers)"),
                ("cron", "9. Cron Jobs"),
                ("firewall", "10. Firewall (UFW)"),
                ("ssl", "11. SSL Certificates"),
                ("fail2ban", "12. Fail2ban"),
                ("exit", "✕ Exit"),
            ],
        )
        
        if choice == "system":
            system.show_menu()
        elif choice == "webserver":
            webserver.show_menu()
        elif choice == "php":
            runtime.show_php_menu()
        elif choice == "nodejs":
            runtime.show_nodejs_menu()
        elif choice == "database":
            database.show_menu()
        elif choice == "email":
            email.show_menu()
        elif choice == "monitor":
            monitor.show_menu()
        elif choice == "supervisor":
            supervisor.show_menu()
        elif choice == "cron":
            cron.show_menu()
        elif choice == "firewall":
            firewall.show_menu()
        elif choice == "ssl":
            ssl.show_menu()
        elif choice == "fail2ban":
            fail2ban.show_menu()
        elif choice == "exit" or choice is None:
            clear_screen()
            console.print(f"[cyan]Thank you for using {APP_NAME}![/cyan]")
            console.print("[dim]Goodbye.[/dim]")
            break


def show_help():
    """Show help message."""
    print(f"{APP_NAME} v{APP_VERSION}")
    print(APP_DESCRIPTION)
    print()
    print("Usage:")
    print("  sudo vexo              Run vexo")
    print("  vexo --help            Show this help")
    print("  vexo --version         Show version")
    print()
    print("Modules:")
    print("  1. System Setup        Update system, install tools")
    print("  2. Domain & Nginx      Manage domains and web server")
    print("  3. PHP Runtime         PHP versions, Composer")
    print("  4. Node.js Runtime     NVM, Node.js versions")
    print("  5. Database            PostgreSQL, MariaDB")
    print("  6. Email Server        Postfix configuration")
    print("  7. System Monitoring   CPU, RAM, Disk usage")
    print("  8. Supervisor          Queue worker management")
    print("  9. Cron Jobs           Scheduled tasks")
    print("  10. Firewall           UFW firewall management")
    print("  11. SSL Certificates   Let's Encrypt / Certbot")
    print("  12. Fail2ban           Brute force protection")


def main():
    """Main entry point."""
    check_python_version()
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in ("--help", "-h"):
            show_help()
            sys.exit(0)
        elif arg in ("--version", "-v"):
            print(f"{APP_NAME} v{APP_VERSION}")
            sys.exit(0)
        elif arg in ("--update", "-u"):
            # Manual update trigger
            perform_update()
            sys.exit(0)
        elif arg == "--no-update":
            # Skip auto-update check, but still show setup wizard
            if setup.is_first_run():
                setup.show_setup_wizard()
            main_loop()
            return
        elif arg == "--skip-setup":
            # Skip both update and setup wizard
            main_loop()
            return
        else:
            print(f"Unknown argument: {arg}")
            print("Use --help for usage information.")
            sys.exit(1)
    
    # Auto-update check on startup
    has_update, commits = check_for_updates()
    if has_update:
        console.print(f"[cyan]⚡ Update available ({commits} new commits). Updating...[/cyan]")
        perform_update()
    
    # First run setup wizard
    if setup.is_first_run():
        setup.show_setup_wizard()
    
    main_loop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n")
        console.print("[dim]Exiting...[/dim]")
        sys.exit(0)
