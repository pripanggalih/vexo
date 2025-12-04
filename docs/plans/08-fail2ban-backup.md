# Fail2ban Phase 8: Backup & Restore

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement comprehensive backup and restore with config, filters, data, scheduled backups, and selective restore.

**Architecture:** Create tar.gz backups with manifest, support scheduled backups via cron, provide restore preview and selective restore options.

**Tech Stack:** Python, tarfile, JSON manifest, cron scheduling

---

## Task 1: Implement Backup Module

**Files:**
- Modify: `modules/fail2ban/backup.py`

**Step 1: Implement full backup.py**

```python
"""Backup and restore for fail2ban module."""

import json
import os
import tarfile
import shutil
from datetime import datetime
from pathlib import Path

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
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, require_root, service_control

from .common import (
    JAIL_LOCAL,
    JAIL_D_DIR,
    FILTER_D_DIR,
    VEXO_FAIL2BAN_DIR,
    HISTORY_DB,
    ensure_data_dir,
)


BACKUPS_DIR = VEXO_FAIL2BAN_DIR / "backups"
MAX_BACKUPS = 10
BACKUP_CRON_FILE = "/etc/cron.d/vexo-fail2ban-backup"


def show_menu():
    """Display backup menu."""
    def get_status():
        backups = _list_backups()
        return f"{len(backups)} backups stored"
    
    def get_options():
        return [
            ("create", "1. Create Backup"),
            ("restore", "2. Restore Backup"),
            ("list", "3. Manage Backups"),
            ("schedule", "4. Scheduled Backups"),
            ("back", "← Back"),
        ]
    
    handlers = {
        "create": create_backup,
        "restore": restore_backup,
        "list": manage_backups,
        "schedule": scheduled_backups,
    }
    
    run_menu_loop("Backup & Restore", get_options, handlers, get_status)


def create_backup():
    """Create a new backup."""
    clear_screen()
    show_header()
    show_panel("Create Backup", title="Backup & Restore", style="cyan")
    
    # Backup name
    default_name = f"fail2ban_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    name = text_input(
        title="Backup Name",
        message="Backup name:",
        default=default_name
    )
    
    if not name:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Options
    console.print()
    console.print("[bold]Include in backup:[/bold]")
    console.print()
    
    include_config = confirm_action("Configuration (jail.local, jail.d/*)?", default=True)
    include_filters = confirm_action("Custom filters (filter.d/*)?", default=True)
    include_data = confirm_action("Vexo data (whitelist, notifications)?", default=True)
    include_history = confirm_action("Ban history database?", default=True)
    include_banned = confirm_action("Currently banned IPs?", default=False)
    
    console.print()
    
    if not any([include_config, include_filters, include_data, include_history]):
        show_warning("Nothing selected to backup.")
        press_enter_to_continue()
        return
    
    # Create backup
    backup_path = _create_backup(
        name=name,
        include_config=include_config,
        include_filters=include_filters,
        include_data=include_data,
        include_history=include_history,
        include_banned=include_banned,
    )
    
    if backup_path:
        size = os.path.getsize(backup_path) / 1024  # KB
        show_success(f"Backup created: {backup_path}")
        console.print(f"[dim]Size: {size:.1f} KB[/dim]")
    else:
        show_error("Failed to create backup.")
    
    press_enter_to_continue()


def _create_backup(name, include_config=True, include_filters=True, 
                   include_data=True, include_history=True, include_banned=False):
    """Create backup archive."""
    ensure_data_dir()
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    
    backup_file = BACKUPS_DIR / f"{name}.tar.gz"
    temp_dir = VEXO_FAIL2BAN_DIR / "temp_backup"
    
    try:
        # Create temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True)
        
        # Create manifest
        manifest = {
            'name': name,
            'created': datetime.now().isoformat(),
            'version': '1.0',
            'contents': {
                'config': include_config,
                'filters': include_filters,
                'data': include_data,
                'history': include_history,
                'banned': include_banned,
            }
        }
        
        # Copy config
        if include_config:
            config_dir = temp_dir / "config"
            config_dir.mkdir()
            
            if os.path.exists(JAIL_LOCAL):
                shutil.copy2(JAIL_LOCAL, config_dir / "jail.local")
            
            if os.path.exists(JAIL_D_DIR):
                jail_d_backup = config_dir / "jail.d"
                jail_d_backup.mkdir()
                for f in os.listdir(JAIL_D_DIR):
                    if f.endswith('.conf'):
                        shutil.copy2(os.path.join(JAIL_D_DIR, f), jail_d_backup / f)
        
        # Copy custom filters
        if include_filters:
            filters_dir = temp_dir / "filters"
            filters_dir.mkdir()
            
            if os.path.exists(FILTER_D_DIR):
                for f in os.listdir(FILTER_D_DIR):
                    if f.endswith('.conf'):
                        filter_path = os.path.join(FILTER_D_DIR, f)
                        try:
                            with open(filter_path, 'r') as file:
                                content = file.read()
                                if 'vexo' in content.lower():
                                    shutil.copy2(filter_path, filters_dir / f)
                        except Exception:
                            pass
        
        # Copy vexo data
        if include_data:
            data_dir = temp_dir / "data"
            data_dir.mkdir()
            
            for data_file in ['whitelist.json', 'notifications.json', 
                              'permanent_bans.json', 'trusted_sources.json', 'config.json']:
                src = VEXO_FAIL2BAN_DIR / data_file
                if src.exists():
                    shutil.copy2(src, data_dir / data_file)
        
        # Copy history database
        if include_history:
            if HISTORY_DB.exists():
                shutil.copy2(HISTORY_DB, temp_dir / "history.db")
        
        # Export currently banned IPs
        if include_banned:
            from .common import get_all_banned_ips
            banned = get_all_banned_ips()
            with open(temp_dir / "banned_ips.json", 'w') as f:
                json.dump(banned, f, indent=2)
        
        # Write manifest
        with open(temp_dir / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Create tar.gz
        with tarfile.open(backup_file, "w:gz") as tar:
            for item in temp_dir.iterdir():
                tar.add(item, arcname=item.name)
        
        # Cleanup temp
        shutil.rmtree(temp_dir)
        
        # Cleanup old backups
        _cleanup_old_backups()
        
        return backup_file
        
    except Exception as e:
        show_error(f"Backup error: {e}")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        return None


def restore_backup():
    """Restore from a backup."""
    clear_screen()
    show_header()
    show_panel("Restore Backup", title="Backup & Restore", style="cyan")
    
    backups = _list_backups()
    
    if not backups:
        show_info("No backups found.")
        press_enter_to_continue()
        return
    
    # Select backup
    options = [f"{b['name']} ({b['date']}, {b['size']})" for b in backups]
    
    selected = select_from_list(
        title="Select Backup",
        message="Choose backup to restore:",
        options=options
    )
    
    if not selected:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Find backup
    idx = options.index(selected)
    backup = backups[idx]
    
    # Preview backup
    manifest = _get_backup_manifest(backup['path'])
    
    if not manifest:
        show_error("Could not read backup manifest.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print("[bold]Backup Contents:[/bold]")
    contents = manifest.get('contents', {})
    console.print(f"  Configuration: {'Yes' if contents.get('config') else 'No'}")
    console.print(f"  Custom Filters: {'Yes' if contents.get('filters') else 'No'}")
    console.print(f"  Vexo Data: {'Yes' if contents.get('data') else 'No'}")
    console.print(f"  History DB: {'Yes' if contents.get('history') else 'No'}")
    console.print(f"  Banned IPs: {'Yes' if contents.get('banned') else 'No'}")
    console.print()
    
    # Restore mode
    mode = select_from_list(
        title="Restore Mode",
        message="How to restore?",
        options=[
            "Full Restore (replace all)",
            "Merge (keep current, add from backup)",
            "Selective (choose components)",
        ]
    )
    
    if not mode:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Safety backup
    console.print()
    if confirm_action("Create safety backup first?", default=True):
        _create_backup(
            name=f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            include_config=True,
            include_filters=True,
            include_data=True,
            include_history=True,
        )
        show_info("Safety backup created.")
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Perform restore
    if mode.startswith("Full"):
        success = _restore_full(backup['path'])
    elif mode.startswith("Merge"):
        success = _restore_merge(backup['path'])
    else:
        success = _restore_selective(backup['path'], contents)
    
    if success:
        service_control("fail2ban", "reload")
        show_success("Backup restored!")
    else:
        show_error("Restore failed.")
    
    press_enter_to_continue()


def _restore_full(backup_path):
    """Full restore - replace everything."""
    temp_dir = VEXO_FAIL2BAN_DIR / "temp_restore"
    
    try:
        # Extract backup
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(temp_dir)
        
        # Restore config
        if (temp_dir / "config").exists():
            if (temp_dir / "config" / "jail.local").exists():
                shutil.copy2(temp_dir / "config" / "jail.local", JAIL_LOCAL)
            
            if (temp_dir / "config" / "jail.d").exists():
                for f in (temp_dir / "config" / "jail.d").iterdir():
                    shutil.copy2(f, os.path.join(JAIL_D_DIR, f.name))
        
        # Restore filters
        if (temp_dir / "filters").exists():
            for f in (temp_dir / "filters").iterdir():
                shutil.copy2(f, os.path.join(FILTER_D_DIR, f.name))
        
        # Restore data
        if (temp_dir / "data").exists():
            for f in (temp_dir / "data").iterdir():
                shutil.copy2(f, VEXO_FAIL2BAN_DIR / f.name)
        
        # Restore history
        if (temp_dir / "history.db").exists():
            shutil.copy2(temp_dir / "history.db", HISTORY_DB)
        
        # Re-ban IPs if included
        if (temp_dir / "banned_ips.json").exists():
            with open(temp_dir / "banned_ips.json", 'r') as f:
                banned = json.load(f)
            from .bans import ban_ip
            for jail, ips in banned.items():
                for ip in ips:
                    ban_ip(ip, jail)
        
        # Cleanup
        shutil.rmtree(temp_dir)
        return True
        
    except Exception as e:
        show_error(f"Restore error: {e}")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        return False


def _restore_merge(backup_path):
    """Merge restore - keep current, add missing."""
    temp_dir = VEXO_FAIL2BAN_DIR / "temp_restore"
    
    try:
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(temp_dir)
        
        # Merge jail.d (don't overwrite existing)
        if (temp_dir / "config" / "jail.d").exists():
            os.makedirs(JAIL_D_DIR, exist_ok=True)
            for f in (temp_dir / "config" / "jail.d").iterdir():
                dest = os.path.join(JAIL_D_DIR, f.name)
                if not os.path.exists(dest):
                    shutil.copy2(f, dest)
        
        # Merge filters (don't overwrite)
        if (temp_dir / "filters").exists():
            for f in (temp_dir / "filters").iterdir():
                dest = os.path.join(FILTER_D_DIR, f.name)
                if not os.path.exists(dest):
                    shutil.copy2(f, dest)
        
        # Merge data files
        if (temp_dir / "data").exists():
            for f in (temp_dir / "data").iterdir():
                dest = VEXO_FAIL2BAN_DIR / f.name
                if not dest.exists():
                    shutil.copy2(f, dest)
        
        shutil.rmtree(temp_dir)
        return True
        
    except Exception as e:
        show_error(f"Merge error: {e}")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        return False


def _restore_selective(backup_path, contents):
    """Selective restore - choose what to restore."""
    console.print()
    console.print("[bold]Select components to restore:[/bold]")
    console.print()
    
    restore_config = contents.get('config') and confirm_action("Restore configuration?", default=True)
    restore_filters = contents.get('filters') and confirm_action("Restore custom filters?", default=True)
    restore_data = contents.get('data') and confirm_action("Restore vexo data?", default=True)
    restore_history = contents.get('history') and confirm_action("Restore history database?", default=False)
    restore_banned = contents.get('banned') and confirm_action("Re-ban IPs?", default=False)
    
    temp_dir = VEXO_FAIL2BAN_DIR / "temp_restore"
    
    try:
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(temp_dir)
        
        if restore_config and (temp_dir / "config").exists():
            if (temp_dir / "config" / "jail.local").exists():
                shutil.copy2(temp_dir / "config" / "jail.local", JAIL_LOCAL)
            if (temp_dir / "config" / "jail.d").exists():
                for f in (temp_dir / "config" / "jail.d").iterdir():
                    shutil.copy2(f, os.path.join(JAIL_D_DIR, f.name))
        
        if restore_filters and (temp_dir / "filters").exists():
            for f in (temp_dir / "filters").iterdir():
                shutil.copy2(f, os.path.join(FILTER_D_DIR, f.name))
        
        if restore_data and (temp_dir / "data").exists():
            for f in (temp_dir / "data").iterdir():
                shutil.copy2(f, VEXO_FAIL2BAN_DIR / f.name)
        
        if restore_history and (temp_dir / "history.db").exists():
            shutil.copy2(temp_dir / "history.db", HISTORY_DB)
        
        if restore_banned and (temp_dir / "banned_ips.json").exists():
            with open(temp_dir / "banned_ips.json", 'r') as f:
                banned = json.load(f)
            from .bans import ban_ip
            for jail, ips in banned.items():
                for ip in ips:
                    ban_ip(ip, jail)
        
        shutil.rmtree(temp_dir)
        return True
        
    except Exception as e:
        show_error(f"Selective restore error: {e}")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        return False


def manage_backups():
    """Manage existing backups."""
    clear_screen()
    show_header()
    show_panel("Manage Backups", title="Backup & Restore", style="cyan")
    
    backups = _list_backups()
    
    if not backups:
        show_info("No backups found.")
        press_enter_to_continue()
        return
    
    # Display backups
    columns = [
        {"name": "#", "style": "dim", "width": 4},
        {"name": "Name", "style": "cyan"},
        {"name": "Date"},
        {"name": "Size", "justify": "right"},
    ]
    
    rows = []
    for i, b in enumerate(backups, 1):
        rows.append([str(i), b['name'], b['date'], b['size']])
    
    show_table(f"Backups ({len(backups)} total)", columns, rows)
    
    # Calculate total size
    total_size = sum(os.path.getsize(b['path']) for b in backups) / (1024 * 1024)
    console.print(f"[dim]Total size: {total_size:.2f} MB[/dim]")
    console.print()
    
    action = select_from_list(
        title="Action",
        message="What to do?",
        options=["Delete backup", "Download backup", "Back"]
    )
    
    if action == "Delete backup":
        options = [f"{b['name']} ({b['date']})" for b in backups]
        selected = select_from_list(
            title="Delete",
            message="Select backup to delete:",
            options=options
        )
        
        if selected and confirm_action(f"Delete this backup?"):
            idx = options.index(selected)
            os.remove(backups[idx]['path'])
            show_success("Backup deleted!")
    
    elif action == "Download backup":
        options = [f"{b['name']} ({b['date']})" for b in backups]
        selected = select_from_list(
            title="Download",
            message="Select backup:",
            options=options
        )
        
        if selected:
            idx = options.index(selected)
            console.print(f"[dim]Backup path: {backups[idx]['path']}[/dim]")
            console.print("[dim]Use scp or sftp to download.[/dim]")
    
    press_enter_to_continue()


def scheduled_backups():
    """Configure scheduled backups."""
    clear_screen()
    show_header()
    show_panel("Scheduled Backups", title="Backup & Restore", style="cyan")
    
    # Check current schedule
    schedule = _get_backup_schedule()
    
    console.print("[bold]Current Schedule:[/bold]")
    if schedule:
        console.print(f"  Enabled: Yes")
        console.print(f"  Frequency: {schedule.get('frequency', 'weekly')}")
        console.print(f"  Day: {schedule.get('day', 'sunday')}")
        console.print(f"  Time: {schedule.get('time', '02:00')}")
        console.print(f"  Keep: {schedule.get('keep', 4)} backups")
    else:
        console.print("  [dim]Not configured[/dim]")
    
    console.print()
    
    action = select_from_list(
        title="Action",
        message="What to do?",
        options=["Enable/Configure", "Disable", "Back"]
    )
    
    if action == "Enable/Configure":
        _configure_schedule()
    elif action == "Disable":
        _disable_schedule()
    
    press_enter_to_continue()


def _configure_schedule():
    """Configure backup schedule."""
    frequency = select_from_list(
        title="Frequency",
        message="Backup frequency:",
        options=["daily", "weekly", "monthly"]
    )
    
    if not frequency:
        return
    
    day = "1"
    if frequency == "weekly":
        day = select_from_list(
            title="Day",
            message="Day of week:",
            options=['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
        )
    elif frequency == "monthly":
        day = text_input(
            title="Day",
            message="Day of month (1-28):",
            default="1"
        )
    
    time = text_input(
        title="Time",
        message="Backup time (HH:MM):",
        default="02:00"
    )
    
    keep = text_input(
        title="Retention",
        message="Number of backups to keep:",
        default="4"
    )
    
    try:
        require_root()
    except PermissionError:
        return
    
    # Create cron entry
    schedule = {
        'frequency': frequency,
        'day': day,
        'time': time,
        'keep': int(keep),
    }
    
    success = _create_backup_cron(schedule)
    
    if success:
        # Save schedule config
        config_file = VEXO_FAIL2BAN_DIR / "backup_schedule.json"
        with open(config_file, 'w') as f:
            json.dump(schedule, f, indent=2)
        show_success("Backup schedule configured!")
    else:
        show_error("Failed to configure schedule.")


def _create_backup_cron(schedule):
    """Create cron job for scheduled backups."""
    hour, minute = schedule['time'].split(':')
    
    if schedule['frequency'] == 'daily':
        cron_time = f"{minute} {hour} * * *"
    elif schedule['frequency'] == 'weekly':
        days = {'sunday': 0, 'monday': 1, 'tuesday': 2, 'wednesday': 3,
                'thursday': 4, 'friday': 5, 'saturday': 6}
        day_num = days.get(schedule['day'], 0)
        cron_time = f"{minute} {hour} * * {day_num}"
    else:  # monthly
        cron_time = f"{minute} {hour} {schedule['day']} * *"
    
    cron_content = f"""# Vexo fail2ban backup schedule
# Generated by vexo
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

{cron_time} root /usr/bin/python3 -c "
from pathlib import Path
import sys
sys.path.insert(0, '/usr/local/share/vexo')
from modules.fail2ban.backup import _create_backup
_create_backup(name='scheduled_' + __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S'))
" >> /var/log/vexo-backup.log 2>&1
"""
    
    try:
        with open(BACKUP_CRON_FILE, 'w') as f:
            f.write(cron_content)
        os.chmod(BACKUP_CRON_FILE, 0o644)
        return True
    except Exception as e:
        show_error(f"Cron error: {e}")
        return False


def _disable_schedule():
    """Disable backup schedule."""
    try:
        require_root()
    except PermissionError:
        return
    
    if os.path.exists(BACKUP_CRON_FILE):
        os.remove(BACKUP_CRON_FILE)
    
    config_file = VEXO_FAIL2BAN_DIR / "backup_schedule.json"
    if config_file.exists():
        config_file.unlink()
    
    show_success("Backup schedule disabled!")


# Helper functions

def _list_backups():
    """List available backups."""
    ensure_data_dir()
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    
    backups = []
    
    for f in BACKUPS_DIR.iterdir():
        if f.suffix == '.gz' and f.name.endswith('.tar.gz'):
            stat = f.stat()
            backups.append({
                'name': f.stem.replace('.tar', ''),
                'path': str(f),
                'date': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                'size': f"{stat.st_size / 1024:.1f} KB",
            })
    
    # Sort by date (newest first)
    backups.sort(key=lambda x: x['date'], reverse=True)
    
    return backups


def _get_backup_manifest(backup_path):
    """Read manifest from backup."""
    try:
        with tarfile.open(backup_path, "r:gz") as tar:
            manifest_info = tar.getmember("manifest.json")
            manifest_file = tar.extractfile(manifest_info)
            return json.load(manifest_file)
    except Exception:
        return None


def _get_backup_schedule():
    """Get current backup schedule."""
    config_file = VEXO_FAIL2BAN_DIR / "backup_schedule.json"
    if not config_file.exists():
        return None
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception:
        return None


def _cleanup_old_backups():
    """Remove old backups beyond retention limit."""
    backups = _list_backups()
    
    if len(backups) > MAX_BACKUPS:
        for backup in backups[MAX_BACKUPS:]:
            try:
                os.remove(backup['path'])
            except Exception:
                pass
```

**Step 2: Commit backup module**

```bash
git add modules/fail2ban/backup.py
git commit -m "feat(fail2ban): implement backup/restore with scheduling"
```

---

## Verification

After completing all tasks:

1. Backup features:
   - Create backup with selectable components
   - Full/merge/selective restore
   - Backup preview and manifest
   - Manage backups (list, delete)
   - Scheduled backups via cron
   - Auto-cleanup old backups

2. Backups stored in `~/.vexo/fail2ban/backups/`
