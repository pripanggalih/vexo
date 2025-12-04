"""Backup and restore domain configurations."""

import os
import shutil
from datetime import datetime

from config import NGINX_SITES_AVAILABLE
from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, select_from_list, run_menu_loop
from utils.shell import run_command, require_root
from utils.error_handler import handle_error
from modules.webserver.utils import get_configured_domains, NGINX_BACKUP_DIR


def show_backup_menu():
    """Display Backup & Restore submenu."""
    options = [
        ("backup", "1. Backup Domain Config"),
        ("restore", "2. Restore Domain Config"),
        ("list", "3. List Backups"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "backup": backup_domain,
        "restore": restore_domain,
        "list": list_backups,
    }
    
    run_menu_loop("Backup & Restore", options, handlers)


def backup_domain():
    """Backup a domain configuration."""
    clear_screen()
    show_header()
    show_panel("Backup Domain Config", title="Backup & Restore", style="cyan")
    
    domains = get_configured_domains()
    if not domains:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    domain = select_from_list("Select Domain", "Choose domain to backup:", domains)
    if not domain:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    if not os.path.exists(config_path):
        handle_error("E2002", "Config file not found.")
        press_enter_to_continue()
        return
    
    # Create backup directory
    backup_dir = os.path.join(NGINX_BACKUP_DIR, domain)
    os.makedirs(backup_dir, exist_ok=True)
    
    # Create timestamped backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"{timestamp}.conf")
    
    shutil.copy2(config_path, backup_path)
    
    # Keep only last 5 backups
    backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.conf')], reverse=True)
    for old_backup in backups[5:]:
        os.remove(os.path.join(backup_dir, old_backup))
    
    show_success(f"Backup created: {backup_path}")
    press_enter_to_continue()


def restore_domain():
    """Restore a domain configuration from backup."""
    clear_screen()
    show_header()
    show_panel("Restore Domain Config", title="Backup & Restore", style="cyan")
    
    # Get domains with backups
    if not os.path.exists(NGINX_BACKUP_DIR):
        show_info("No backups found.")
        press_enter_to_continue()
        return
    
    domains_with_backups = [d for d in os.listdir(NGINX_BACKUP_DIR) 
                           if os.path.isdir(os.path.join(NGINX_BACKUP_DIR, d))]
    
    if not domains_with_backups:
        show_info("No backups found.")
        press_enter_to_continue()
        return
    
    domain = select_from_list("Select Domain", "Choose domain:", domains_with_backups)
    if not domain:
        return
    
    # List backups for domain
    backup_dir = os.path.join(NGINX_BACKUP_DIR, domain)
    backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.conf')], reverse=True)
    
    if not backups:
        show_info("No backups found for this domain.")
        press_enter_to_continue()
        return
    
    # Format backup options with timestamps
    backup_options = []
    for b in backups:
        ts = b.replace(".conf", "")
        try:
            dt = datetime.strptime(ts, "%Y%m%d_%H%M%S")
            formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            formatted = ts
        size = os.path.getsize(os.path.join(backup_dir, b))
        backup_options.append(f"{formatted} ({size/1024:.1f} KB)")
    
    choice = select_from_list("Select Backup", "Choose backup to restore:", backup_options)
    if not choice:
        return
    
    # Map choice back to filename
    idx = backup_options.index(choice)
    backup_file = backups[idx]
    backup_path = os.path.join(backup_dir, backup_file)
    
    if not confirm_action(f"Restore {domain} from {choice}?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    
    # Backup current before restore
    if os.path.exists(config_path):
        pre_restore = os.path.join(backup_dir, f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.conf")
        shutil.copy2(config_path, pre_restore)
    
    shutil.copy2(backup_path, config_path)
    
    # Test nginx config
    result = run_command("nginx -t", check=False, silent=True)
    if result.returncode != 0:
        handle_error("E2002", "Nginx config test failed after restore!")
        console.print(f"[dim]{result.stderr}[/dim]")
        press_enter_to_continue()
        return
    
    from modules.webserver.nginx import reload_nginx
    reload_nginx(silent=True)
    
    show_success(f"Config restored for {domain}!")
    press_enter_to_continue()


def list_backups():
    """List all backups."""
    clear_screen()
    show_header()
    show_panel("Backup List", title="Backup & Restore", style="cyan")
    
    if not os.path.exists(NGINX_BACKUP_DIR):
        show_info("No backups found.")
        press_enter_to_continue()
        return
    
    domains = [d for d in os.listdir(NGINX_BACKUP_DIR) 
               if os.path.isdir(os.path.join(NGINX_BACKUP_DIR, d))]
    
    if not domains:
        show_info("No backups found.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Domain", "style": "cyan"},
        {"name": "Backups", "justify": "center"},
        {"name": "Latest", "style": "white"},
        {"name": "Size", "justify": "right"},
    ]
    
    rows = []
    for domain in sorted(domains):
        backup_dir = os.path.join(NGINX_BACKUP_DIR, domain)
        backups = [f for f in os.listdir(backup_dir) if f.endswith('.conf')]
        
        if not backups:
            continue
        
        latest = sorted(backups, reverse=True)[0]
        try:
            ts = latest.replace(".conf", "")
            dt = datetime.strptime(ts, "%Y%m%d_%H%M%S")
            latest_str = dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            latest_str = latest
        
        total_size = sum(os.path.getsize(os.path.join(backup_dir, f)) for f in backups)
        
        rows.append([domain, str(len(backups)), latest_str, f"{total_size/1024:.1f} KB"])
    
    if rows:
        show_table("", columns, rows, show_header=True)
    else:
        show_info("No backups found.")
    
    press_enter_to_continue()
