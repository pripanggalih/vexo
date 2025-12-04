# Phase 7: Backup & Restore

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement certificate backup and restore with export formats, scheduled backups, and migration support.

**Architecture:** Create encrypted tar.gz backups containing certs, keys, chains, and Nginx configs. Store in /etc/vexo/ssl/backups/. Support scheduled backups via cron.

**Tech Stack:** Python, Rich, tar, OpenSSL encryption

---

## Task 1: Implement Backup & Restore Module

**Files:**
- Modify: `modules/ssl/backup.py`

**Step 1: Replace backup.py with full implementation**

```python
"""SSL certificate backup and restore."""

import os
import json
import shutil
import tarfile
from datetime import datetime

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
from ui.menu import run_menu_loop, text_input, select_from_list, confirm_action
from utils.shell import run_command, require_root
from modules.ssl.common import (
    get_certbot_status_text,
    list_all_certificates,
    list_certbot_certificates,
    list_custom_certificates,
    ensure_config_dir,
    log_event,
    VEXO_SSL_BACKUPS,
    VEXO_SSL_CERTS,
    LETSENCRYPT_LIVE,
    LETSENCRYPT_RENEWAL,
)


def show_backup_menu():
    """Display backup and restore submenu."""
    def get_status():
        backups = _list_backups()
        return f"Backups: {len(backups)}"
    
    options = [
        ("export_one", "1. Export Certificate"),
        ("export_all", "2. Export All"),
        ("restore", "3. Import/Restore"),
        ("schedule", "4. Scheduled Backups"),
        ("manage", "5. Manage Backups"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "export_one": export_single,
        "export_all": export_all,
        "restore": restore_backup,
        "schedule": scheduled_backups,
        "manage": manage_backups,
    }
    
    run_menu_loop("Backup & Restore", options, handlers, get_status)


def _list_backups():
    """List all backup files."""
    if not os.path.exists(VEXO_SSL_BACKUPS):
        return []
    
    backups = []
    for filename in os.listdir(VEXO_SSL_BACKUPS):
        if filename.endswith('.tar.gz') or filename.endswith('.tar.gz.enc'):
            filepath = os.path.join(VEXO_SSL_BACKUPS, filename)
            stat = os.stat(filepath)
            backups.append({
                "filename": filename,
                "filepath": filepath,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime),
                "encrypted": filename.endswith('.enc')
            })
    
    backups.sort(key=lambda x: x["created"], reverse=True)
    return backups


def export_single():
    """Export a single certificate."""
    clear_screen()
    show_header()
    show_panel("Export Certificate", title="Backup & Restore", style="cyan")
    
    certificates = list_all_certificates()
    
    if not certificates:
        show_info("No certificates to export.")
        press_enter_to_continue()
        return
    
    options = [f"{c['name']} ({c['source']})" for c in certificates]
    
    choice = select_from_list(
        title="Certificate",
        message="Select certificate to export:",
        options=options
    )
    
    if not choice:
        press_enter_to_continue()
        return
    
    idx = options.index(choice)
    cert = certificates[idx]
    
    # Export format
    format_choice = select_from_list(
        title="Format",
        message="Export format:",
        options=[
            "Full Backup (.tar.gz) - All files + Nginx config",
            "PEM Bundle - Certificate + key in single file",
            "Separate Files - Individual .pem files"
        ]
    )
    
    if not format_choice:
        press_enter_to_continue()
        return
    
    # Encryption option
    encrypt = confirm_action("Encrypt backup with password?")
    password = None
    if encrypt:
        password = text_input(
            title="Password",
            message="Enter encryption password:"
        )
        if not password:
            show_warning("Password required for encryption.")
            encrypt = False
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    ensure_config_dir()
    os.makedirs(VEXO_SSL_BACKUPS, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    
    if "Full Backup" in format_choice:
        success = _export_full_backup(cert, timestamp, encrypt, password)
    elif "PEM Bundle" in format_choice:
        success = _export_pem_bundle(cert, timestamp)
    else:
        success = _export_separate_files(cert, timestamp)
    
    if success:
        log_event(cert['name'], "exported", f"Format: {format_choice.split()[0]}")
    
    press_enter_to_continue()


def _export_full_backup(cert, timestamp, encrypt=False, password=None):
    """Create full backup of a certificate."""
    name = cert['name']
    source = cert['source']
    
    # Create temp directory
    temp_dir = f"/tmp/vexo-ssl-backup-{timestamp}"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Copy certificate files
        cert_dest = os.path.join(temp_dir, "certificates", name)
        os.makedirs(cert_dest, exist_ok=True)
        
        if source == "certbot":
            live_dir = os.path.join(LETSENCRYPT_LIVE, name)
            for f in ['fullchain.pem', 'privkey.pem', 'cert.pem', 'chain.pem']:
                src = os.path.join(live_dir, f)
                if os.path.exists(src):
                    shutil.copy2(src, cert_dest)
            
            # Copy renewal config
            renewal_src = os.path.join(LETSENCRYPT_RENEWAL, f"{name}.conf")
            if os.path.exists(renewal_src):
                renewal_dest = os.path.join(temp_dir, "certbot", "renewal")
                os.makedirs(renewal_dest, exist_ok=True)
                shutil.copy2(renewal_src, renewal_dest)
        else:
            custom_dir = os.path.join(VEXO_SSL_CERTS, name)
            if os.path.exists(custom_dir):
                shutil.copytree(custom_dir, cert_dest, dirs_exist_ok=True)
        
        # Copy Nginx config if exists
        nginx_conf = f"/etc/nginx/sites-available/{name}"
        if os.path.exists(nginx_conf):
            nginx_dest = os.path.join(temp_dir, "nginx")
            os.makedirs(nginx_dest, exist_ok=True)
            shutil.copy2(nginx_conf, nginx_dest)
        
        # Create manifest
        manifest = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "certificates": [name],
            "source": source
        }
        with open(os.path.join(temp_dir, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=2)
        
        # Create tar.gz
        backup_name = f"ssl-{name}-{timestamp}.tar.gz"
        backup_path = os.path.join(VEXO_SSL_BACKUPS, backup_name)
        
        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(temp_dir, arcname=".")
        
        # Encrypt if requested
        if encrypt and password:
            enc_path = backup_path + ".enc"
            result = run_command(
                f"openssl enc -aes-256-cbc -salt -pbkdf2 -in {backup_path} -out {enc_path} -pass pass:{password}",
                check=False,
                silent=True
            )
            if result.returncode == 0:
                os.remove(backup_path)
                backup_path = enc_path
                backup_name += ".enc"
            else:
                show_warning("Encryption failed, saving unencrypted.")
        
        show_success(f"Backup created: {backup_name}")
        console.print(f"[dim]Location: {backup_path}[/dim]")
        console.print(f"[dim]Size: {os.path.getsize(backup_path) / 1024:.1f} KB[/dim]")
        
        return True
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _export_pem_bundle(cert, timestamp):
    """Export certificate as PEM bundle."""
    name = cert['name']
    source = cert['source']
    
    # Get cert and key paths
    if source == "certbot":
        cert_path = os.path.join(LETSENCRYPT_LIVE, name, "fullchain.pem")
        key_path = os.path.join(LETSENCRYPT_LIVE, name, "privkey.pem")
    else:
        cert_path = os.path.join(VEXO_SSL_CERTS, name, "fullchain.pem")
        key_path = os.path.join(VEXO_SSL_CERTS, name, "privkey.pem")
    
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        show_error("Certificate files not found.")
        return False
    
    # Create bundle
    bundle_name = f"ssl-{name}-{timestamp}.pem"
    bundle_path = os.path.join(VEXO_SSL_BACKUPS, bundle_name)
    
    with open(bundle_path, "w") as bundle:
        with open(cert_path, "r") as cert_f:
            bundle.write(cert_f.read())
        bundle.write("\n")
        with open(key_path, "r") as key_f:
            bundle.write(key_f.read())
    
    os.chmod(bundle_path, 0o600)
    
    show_success(f"PEM bundle created: {bundle_name}")
    console.print(f"[dim]Location: {bundle_path}[/dim]")
    
    return True


def _export_separate_files(cert, timestamp):
    """Export certificate as separate files."""
    name = cert['name']
    source = cert['source']
    
    export_dir = os.path.join(VEXO_SSL_BACKUPS, f"ssl-{name}-{timestamp}")
    os.makedirs(export_dir, exist_ok=True)
    
    if source == "certbot":
        live_dir = os.path.join(LETSENCRYPT_LIVE, name)
    else:
        live_dir = os.path.join(VEXO_SSL_CERTS, name)
    
    files_copied = 0
    for f in ['fullchain.pem', 'privkey.pem', 'cert.pem', 'chain.pem']:
        src = os.path.join(live_dir, f)
        if os.path.exists(src):
            dest = os.path.join(export_dir, f)
            shutil.copy2(src, dest)
            if f == 'privkey.pem':
                os.chmod(dest, 0o600)
            files_copied += 1
    
    show_success(f"Files exported to: ssl-{name}-{timestamp}/")
    console.print(f"[dim]Files: {files_copied}[/dim]")
    
    return True


def export_all():
    """Export all certificates."""
    clear_screen()
    show_header()
    show_panel("Export All Certificates", title="Backup & Restore", style="cyan")
    
    certificates = list_all_certificates()
    
    if not certificates:
        show_info("No certificates to export.")
        press_enter_to_continue()
        return
    
    console.print(f"[bold]Certificates to export: {len(certificates)}[/bold]")
    for cert in certificates:
        console.print(f"  • {cert['name']} ({cert['source']})")
    console.print()
    
    # Encryption option
    encrypt = confirm_action("Encrypt backup with password?")
    password = None
    if encrypt:
        password = text_input(title="Password", message="Enter encryption password:")
        if not password:
            encrypt = False
    
    if not confirm_action(f"Export all {len(certificates)} certificates?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    ensure_config_dir()
    os.makedirs(VEXO_SSL_BACKUPS, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    temp_dir = f"/tmp/vexo-ssl-backup-all-{timestamp}"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        cert_names = []
        
        for cert in certificates:
            name = cert['name']
            source = cert['source']
            cert_names.append(name)
            
            cert_dest = os.path.join(temp_dir, "certificates", name)
            os.makedirs(cert_dest, exist_ok=True)
            
            if source == "certbot":
                live_dir = os.path.join(LETSENCRYPT_LIVE, name)
                for f in ['fullchain.pem', 'privkey.pem', 'cert.pem', 'chain.pem']:
                    src = os.path.join(live_dir, f)
                    if os.path.exists(src):
                        shutil.copy2(src, cert_dest)
                
                renewal_src = os.path.join(LETSENCRYPT_RENEWAL, f"{name}.conf")
                if os.path.exists(renewal_src):
                    renewal_dest = os.path.join(temp_dir, "certbot", "renewal")
                    os.makedirs(renewal_dest, exist_ok=True)
                    shutil.copy2(renewal_src, renewal_dest)
            else:
                custom_dir = os.path.join(VEXO_SSL_CERTS, name)
                if os.path.exists(custom_dir):
                    shutil.copytree(custom_dir, cert_dest, dirs_exist_ok=True)
            
            nginx_conf = f"/etc/nginx/sites-available/{name}"
            if os.path.exists(nginx_conf):
                nginx_dest = os.path.join(temp_dir, "nginx")
                os.makedirs(nginx_dest, exist_ok=True)
                shutil.copy2(nginx_conf, nginx_dest)
            
            console.print(f"  [green]✓[/green] {name}")
        
        # Create manifest
        manifest = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "certificates": cert_names,
            "total": len(cert_names)
        }
        with open(os.path.join(temp_dir, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=2)
        
        # Create tar.gz
        backup_name = f"ssl-all-{timestamp}.tar.gz"
        backup_path = os.path.join(VEXO_SSL_BACKUPS, backup_name)
        
        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(temp_dir, arcname=".")
        
        # Encrypt if requested
        if encrypt and password:
            enc_path = backup_path + ".enc"
            result = run_command(
                f"openssl enc -aes-256-cbc -salt -pbkdf2 -in {backup_path} -out {enc_path} -pass pass:{password}",
                check=False,
                silent=True
            )
            if result.returncode == 0:
                os.remove(backup_path)
                backup_path = enc_path
                backup_name += ".enc"
        
        console.print()
        show_success(f"Backup created: {backup_name}")
        console.print(f"[dim]Certificates: {len(cert_names)}[/dim]")
        console.print(f"[dim]Size: {os.path.getsize(backup_path) / 1024:.1f} KB[/dim]")
        
        log_event("all", "exported", f"{len(cert_names)} certificates")
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    press_enter_to_continue()


def restore_backup():
    """Restore certificates from backup."""
    clear_screen()
    show_header()
    show_panel("Restore Backup", title="Backup & Restore", style="cyan")
    
    backups = _list_backups()
    
    if not backups:
        show_info("No backups found.")
        console.print("[dim]Use 'Export Certificate' to create a backup first.[/dim]")
        press_enter_to_continue()
        return
    
    options = [
        f"{b['filename']} ({b['created'].strftime('%Y-%m-%d %H:%M')})"
        for b in backups
    ]
    
    choice = select_from_list(
        title="Backup",
        message="Select backup to restore:",
        options=options
    )
    
    if not choice:
        press_enter_to_continue()
        return
    
    idx = options.index(choice)
    backup = backups[idx]
    
    # Decrypt if needed
    backup_path = backup['filepath']
    
    if backup['encrypted']:
        password = text_input(
            title="Password",
            message="Enter decryption password:"
        )
        
        if not password:
            show_warning("Password required.")
            press_enter_to_continue()
            return
        
        decrypted_path = backup_path.replace('.enc', '')
        result = run_command(
            f"openssl enc -aes-256-cbc -d -pbkdf2 -in {backup_path} -out {decrypted_path} -pass pass:{password}",
            check=False,
            silent=True
        )
        
        if result.returncode != 0:
            show_error("Decryption failed. Wrong password?")
            press_enter_to_continue()
            return
        
        backup_path = decrypted_path
    
    # Extract and preview
    temp_dir = f"/tmp/vexo-ssl-restore-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    try:
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(temp_dir)
        
        # Read manifest
        manifest_path = os.path.join(temp_dir, "manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
            
            console.print()
            console.print("[bold]Backup Contents:[/bold]")
            console.print(f"  Created: {manifest.get('created', 'unknown')}")
            console.print(f"  Certificates: {manifest.get('total', len(manifest.get('certificates', [])))}")
            for cert_name in manifest.get('certificates', []):
                console.print(f"    • {cert_name}")
        
        console.print()
        
        if not confirm_action("Restore these certificates?"):
            show_warning("Cancelled.")
            return
        
        try:
            require_root()
        except PermissionError:
            return
        
        # Restore certificates
        certs_dir = os.path.join(temp_dir, "certificates")
        if os.path.exists(certs_dir):
            for cert_name in os.listdir(certs_dir):
                src_dir = os.path.join(certs_dir, cert_name)
                dest_dir = os.path.join(VEXO_SSL_CERTS, cert_name)
                
                os.makedirs(dest_dir, exist_ok=True)
                for f in os.listdir(src_dir):
                    shutil.copy2(
                        os.path.join(src_dir, f),
                        os.path.join(dest_dir, f)
                    )
                    if f == 'privkey.pem':
                        os.chmod(os.path.join(dest_dir, f), 0o600)
                
                console.print(f"  [green]✓[/green] Restored: {cert_name}")
                log_event(cert_name, "restored", f"From backup")
        
        console.print()
        show_success("Restore completed!")
        
        if confirm_action("Reload Nginx?"):
            result = run_command("nginx -t && systemctl reload nginx", check=False, silent=True)
            if result.returncode == 0:
                show_success("Nginx reloaded!")
            else:
                show_warning("Nginx reload failed. Check configuration.")
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        if backup['encrypted'] and os.path.exists(decrypted_path):
            os.remove(decrypted_path)
    
    press_enter_to_continue()


def scheduled_backups():
    """Configure scheduled backups."""
    clear_screen()
    show_header()
    show_panel("Scheduled Backups", title="Backup & Restore", style="cyan")
    
    from modules.ssl.common import load_settings, save_settings
    
    settings = load_settings()
    backup_settings = settings.get("scheduled_backup", {})
    
    enabled = backup_settings.get("enabled", False)
    schedule = backup_settings.get("schedule", "weekly")
    retention = backup_settings.get("retention", 7)
    
    console.print("[bold]Current Settings:[/bold]")
    console.print(f"  Enabled: {'[green]Yes[/green]' if enabled else '[dim]No[/dim]'}")
    console.print(f"  Schedule: {schedule}")
    console.print(f"  Keep last: {retention} backups")
    console.print()
    
    action = select_from_list(
        title="Action",
        message="Configure:",
        options=[
            "Toggle enabled/disabled",
            "Change schedule",
            "Change retention",
            "Run backup now"
        ]
    )
    
    if action == "Toggle enabled/disabled":
        backup_settings["enabled"] = not enabled
        settings["scheduled_backup"] = backup_settings
        save_settings(settings)
        
        status = "enabled" if backup_settings["enabled"] else "disabled"
        show_success(f"Scheduled backups {status}!")
        
        # Update cron
        if backup_settings["enabled"]:
            _setup_cron(schedule)
        else:
            _remove_cron()
    
    elif action == "Change schedule":
        new_schedule = select_from_list(
            title="Schedule",
            message="Backup frequency:",
            options=["daily", "weekly", "monthly"]
        )
        if new_schedule:
            backup_settings["schedule"] = new_schedule
            settings["scheduled_backup"] = backup_settings
            save_settings(settings)
            
            if enabled:
                _setup_cron(new_schedule)
            
            show_success(f"Schedule changed to {new_schedule}!")
    
    elif action == "Change retention":
        new_retention = text_input(
            title="Retention",
            message="Keep last N backups:",
            default=str(retention)
        )
        if new_retention:
            try:
                backup_settings["retention"] = int(new_retention)
                settings["scheduled_backup"] = backup_settings
                save_settings(settings)
                show_success(f"Will keep last {new_retention} backups!")
            except ValueError:
                show_error("Invalid number.")
    
    elif action == "Run backup now":
        show_info("Creating backup...")
        # Trigger export all
        export_all()
        return
    
    press_enter_to_continue()


def _setup_cron(schedule):
    """Setup cron job for scheduled backups."""
    cron_schedules = {
        "daily": "0 2 * * *",
        "weekly": "0 2 * * 0",
        "monthly": "0 2 1 * *"
    }
    
    cron_time = cron_schedules.get(schedule, cron_schedules["weekly"])
    cron_line = f'{cron_time} root /usr/bin/python3 -c "from modules.ssl.backup import _auto_backup; _auto_backup()"'
    
    cron_file = "/etc/cron.d/vexo-ssl-backup"
    
    try:
        with open(cron_file, "w") as f:
            f.write(f"# Vexo SSL automatic backup\n{cron_line}\n")
        os.chmod(cron_file, 0o644)
        console.print(f"[dim]Cron job configured: {cron_time}[/dim]")
    except Exception as e:
        show_warning(f"Could not setup cron: {e}")


def _remove_cron():
    """Remove cron job for scheduled backups."""
    cron_file = "/etc/cron.d/vexo-ssl-backup"
    if os.path.exists(cron_file):
        os.remove(cron_file)


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
    
    columns = [
        {"name": "#", "style": "dim", "justify": "right"},
        {"name": "Filename", "style": "cyan"},
        {"name": "Size"},
        {"name": "Created"},
    ]
    
    rows = []
    for i, b in enumerate(backups, 1):
        size = f"{b['size'] / 1024:.1f} KB"
        rows.append([
            str(i),
            b['filename'][:35],
            size,
            b['created'].strftime("%Y-%m-%d %H:%M")
        ])
    
    show_table("Backups", columns, rows)
    
    action = select_from_list(
        title="Action",
        message="Select action:",
        options=["Delete backup", "Download/copy backup", "Clean old backups"]
    )
    
    if action == "Delete backup":
        options = [b['filename'] for b in backups]
        choice = select_from_list(title="Delete", message="Select backup:", options=options)
        
        if choice and confirm_action(f"Delete {choice}?"):
            idx = options.index(choice)
            try:
                os.remove(backups[idx]['filepath'])
                show_success("Backup deleted!")
            except Exception as e:
                show_error(f"Failed: {e}")
    
    elif action == "Download/copy backup":
        options = [b['filename'] for b in backups]
        choice = select_from_list(title="Copy", message="Select backup:", options=options)
        
        if choice:
            dest = text_input(
                title="Destination",
                message="Copy to path:",
                default=f"/tmp/{choice}"
            )
            if dest:
                idx = options.index(choice)
                try:
                    shutil.copy2(backups[idx]['filepath'], dest)
                    show_success(f"Copied to: {dest}")
                except Exception as e:
                    show_error(f"Failed: {e}")
    
    elif action == "Clean old backups":
        from modules.ssl.common import load_settings
        settings = load_settings()
        retention = settings.get("scheduled_backup", {}).get("retention", 7)
        
        if len(backups) <= retention:
            show_info(f"Only {len(backups)} backups exist (retention: {retention}).")
        else:
            to_delete = len(backups) - retention
            if confirm_action(f"Delete {to_delete} oldest backups?"):
                for b in backups[retention:]:
                    try:
                        os.remove(b['filepath'])
                        console.print(f"  [dim]Deleted: {b['filename']}[/dim]")
                    except Exception:
                        pass
                show_success(f"Cleaned {to_delete} old backups!")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/ssl/backup.py
git commit -m "feat(ssl): implement backup/restore with encryption and scheduling"
```

---

## Verification

1. **Export Single works:**
   - Full backup, PEM bundle, separate files
   - Encryption option

2. **Export All works:**
   - All certificates in one archive
   - Includes Nginx configs

3. **Restore works:**
   - Preview before restore
   - Handles encrypted backups
   - Restores to correct locations

4. **Scheduled Backups works:**
   - Enable/disable
   - Cron job setup

5. **Manage Backups works:**
   - List, delete, copy
   - Clean old backups
