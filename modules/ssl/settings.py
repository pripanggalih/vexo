"""SSL settings and alerts configuration."""

import os
import json

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_success,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import run_menu_loop, text_input, select_from_list, confirm_action
from utils.shell import run_command, require_root
from utils.error_handler import handle_error
from modules.ssl.common import (
    get_certbot_status_text,
    ensure_config_dir,
    CERTIFICATE_AUTHORITIES,
    SETTINGS_FILE,
    ALERTS_FILE,
    ALERT_CRITICAL,
    ALERT_WARNING,
    ALERT_NOTICE,
)


def show_settings_menu():
    """Display settings submenu."""
    def get_status():
        settings = _load_settings()
        ca = settings.get("default_ca", "letsencrypt")
        ca_name = CERTIFICATE_AUTHORITIES.get(ca, {}).get("name", ca)
        return f"Default CA: {ca_name}"
    
    options = [
        ("ca", "1. Default CA"),
        ("alerts", "2. Alert Settings"),
        ("renewal", "3. Auto-Renewal Config"),
        ("thresholds", "4. Alert Thresholds"),
        ("view", "5. View All Settings"),
        ("reset", "6. Reset to Defaults"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "ca": configure_default_ca,
        "alerts": configure_alerts,
        "renewal": configure_auto_renewal,
        "thresholds": configure_thresholds,
        "view": view_all_settings,
        "reset": reset_settings,
    }
    
    run_menu_loop("Settings", options, handlers, get_status)


def _load_settings():
    """Load settings from file."""
    if not os.path.exists(SETTINGS_FILE):
        return _default_settings()
    
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return _default_settings()


def _save_settings(settings):
    """Save settings to file."""
    ensure_config_dir()
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)


def _default_settings():
    """Return default settings."""
    return {
        "default_ca": "letsencrypt",
        "alert_thresholds": {
            "critical": ALERT_CRITICAL,
            "warning": ALERT_WARNING,
            "notice": ALERT_NOTICE
        },
        "alerts": {
            "enabled": False,
            "email": None,
            "webhook": None
        },
        "auto_renewal": {
            "enabled": True,
            "pre_hook": None,
            "post_hook": None
        },
        "scheduled_backup": {
            "enabled": False,
            "schedule": "weekly",
            "retention": 7
        }
    }


def configure_default_ca():
    """Configure default Certificate Authority."""
    clear_screen()
    show_header()
    show_panel("Default Certificate Authority", title="Settings", style="cyan")
    
    settings = _load_settings()
    current_ca = settings.get("default_ca", "letsencrypt")
    current_name = CERTIFICATE_AUTHORITIES.get(current_ca, {}).get("name", current_ca)
    
    console.print(f"[bold]Current Default:[/bold] {current_name}")
    console.print()
    
    options = []
    for key, ca in CERTIFICATE_AUTHORITIES.items():
        if key == "letsencrypt_staging":
            continue
        marker = " (current)" if key == current_ca else ""
        options.append(f"{ca['name']}{marker} - {ca['description']}")
    
    choice = select_from_list(
        title="CA",
        message="Select default CA:",
        options=options
    )
    
    if not choice:
        press_enter_to_continue()
        return
    
    for key, ca in CERTIFICATE_AUTHORITIES.items():
        if ca['name'] in choice:
            settings["default_ca"] = key
            _save_settings(settings)
            show_success(f"Default CA set to {ca['name']}!")
            break
    
    press_enter_to_continue()


def configure_alerts():
    """Configure alert notifications."""
    clear_screen()
    show_header()
    show_panel("Alert Settings", title="Settings", style="cyan")
    
    settings = _load_settings()
    alerts = settings.get("alerts", {})
    
    enabled = alerts.get("enabled", False)
    email = alerts.get("email")
    webhook = alerts.get("webhook")
    
    console.print("[bold]Current Settings:[/bold]")
    console.print(f"  Alerts Enabled: {'[green]Yes[/green]' if enabled else '[dim]No[/dim]'}")
    console.print(f"  Email: {email or '[dim]Not configured[/dim]'}")
    console.print(f"  Webhook: {webhook[:30] + '...' if webhook and len(webhook) > 30 else webhook or '[dim]Not configured[/dim]'}")
    console.print()
    
    action = select_from_list(
        title="Configure",
        message="What to configure:",
        options=[
            "Toggle alerts on/off",
            "Configure email",
            "Configure webhook",
            "Test alerts"
        ]
    )
    
    if action == "Toggle alerts on/off":
        alerts["enabled"] = not enabled
        settings["alerts"] = alerts
        _save_settings(settings)
        
        status = "enabled" if alerts["enabled"] else "disabled"
        show_success(f"Alerts {status}!")
    
    elif action == "Configure email":
        new_email = text_input(
            title="Email",
            message="Alert email address:",
            default=email or ""
        )
        
        if new_email:
            if "@" not in new_email:
                handle_error("E6002", "Invalid email address.")
            else:
                alerts["email"] = new_email
                settings["alerts"] = alerts
                _save_settings(settings)
                show_success(f"Alert email set to {new_email}!")
        elif new_email == "":
            alerts["email"] = None
            settings["alerts"] = alerts
            _save_settings(settings)
            show_info("Email alerts disabled.")
    
    elif action == "Configure webhook":
        console.print("[dim]Enter a webhook URL (Slack, Discord, etc.)[/dim]")
        new_webhook = text_input(
            title="Webhook",
            message="Webhook URL:",
            default=webhook or ""
        )
        
        if new_webhook:
            if not new_webhook.startswith("http"):
                handle_error("E6002", "Invalid webhook URL.")
            else:
                alerts["webhook"] = new_webhook
                settings["alerts"] = alerts
                _save_settings(settings)
                show_success("Webhook configured!")
        elif new_webhook == "":
            alerts["webhook"] = None
            settings["alerts"] = alerts
            _save_settings(settings)
            show_info("Webhook alerts disabled.")
    
    elif action == "Test alerts":
        _test_alerts(alerts)
    
    press_enter_to_continue()


def _test_alerts(alerts):
    """Send test alerts."""
    console.print()
    show_info("Sending test alerts...")
    
    test_message = "This is a test alert from Vexo SSL module."
    
    if alerts.get("email"):
        result = run_command(
            f'echo "{test_message}" | mail -s "Vexo SSL Test Alert" {alerts["email"]}',
            check=False,
            silent=True
        )
        if result.returncode == 0:
            console.print(f"  [green]✓[/green] Email sent to {alerts['email']}")
        else:
            console.print(f"  [red]✗[/red] Email failed (mail command may not be configured)")
    
    if alerts.get("webhook"):
        import json as json_module
        payload = json_module.dumps({"text": test_message})
        result = run_command(
            f"curl -s -X POST -H 'Content-Type: application/json' -d '{payload}' '{alerts['webhook']}'",
            check=False,
            silent=True
        )
        if result.returncode == 0:
            console.print(f"  [green]✓[/green] Webhook sent")
        else:
            console.print(f"  [red]✗[/red] Webhook failed")
    
    if not alerts.get("email") and not alerts.get("webhook"):
        show_warning("No alert methods configured.")


def configure_auto_renewal():
    """Configure auto-renewal settings."""
    clear_screen()
    show_header()
    show_panel("Auto-Renewal Configuration", title="Settings", style="cyan")
    
    result = run_command("systemctl is-active certbot.timer", check=False, silent=True)
    timer_active = result.returncode == 0 and "active" in result.stdout
    
    console.print("[bold]Certbot Timer Status:[/bold]")
    if timer_active:
        console.print("  [green]✓[/green] certbot.timer is active")
    else:
        console.print("  [yellow]![/yellow] certbot.timer is not active")
    console.print()
    
    result = run_command(
        "systemctl list-timers certbot.timer --no-pager 2>/dev/null | grep -v NEXT",
        check=False,
        silent=True
    )
    if result.returncode == 0 and result.stdout.strip():
        console.print("[bold]Timer Schedule:[/bold]")
        console.print(f"  {result.stdout.strip()}")
        console.print()
    
    settings = _load_settings()
    renewal = settings.get("auto_renewal", {})
    
    console.print("[bold]Current Settings:[/bold]")
    console.print(f"  Pre-hook: {renewal.get('pre_hook') or '[dim]None[/dim]'}")
    console.print(f"  Post-hook: {renewal.get('post_hook') or '[dim]None[/dim]'}")
    console.print()
    
    action = select_from_list(
        title="Action",
        message="Configure:",
        options=[
            "Enable certbot timer",
            "Disable certbot timer",
            "Configure pre-hook",
            "Configure post-hook",
            "Test renewal (dry-run)"
        ]
    )
    
    if action == "Enable certbot timer":
        try:
            require_root()
        except PermissionError:
            press_enter_to_continue()
            return
        
        run_command("systemctl enable certbot.timer", check=False, silent=True)
        result = run_command("systemctl start certbot.timer", check=False, silent=True)
        
        if result.returncode == 0:
            show_success("Certbot timer enabled!")
        else:
            handle_error("E6002", "Failed to enable timer.")
    
    elif action == "Disable certbot timer":
        if not confirm_action("Disable auto-renewal? Certificates will NOT renew automatically!"):
            press_enter_to_continue()
            return
        
        try:
            require_root()
        except PermissionError:
            press_enter_to_continue()
            return
        
        run_command("systemctl stop certbot.timer", check=False, silent=True)
        run_command("systemctl disable certbot.timer", check=False, silent=True)
        show_warning("Certbot timer disabled!")
    
    elif action == "Configure pre-hook":
        console.print("[dim]Command to run before renewal (e.g., nginx -s stop)[/dim]")
        hook = text_input(
            title="Pre-hook",
            message="Pre-renewal command:",
            default=renewal.get("pre_hook") or ""
        )
        
        renewal["pre_hook"] = hook if hook else None
        settings["auto_renewal"] = renewal
        _save_settings(settings)
        
        _update_certbot_hooks(renewal)
        show_success("Pre-hook configured!")
    
    elif action == "Configure post-hook":
        console.print("[dim]Command to run after renewal (e.g., nginx -s reload)[/dim]")
        hook = text_input(
            title="Post-hook",
            message="Post-renewal command:",
            default=renewal.get("post_hook") or ""
        )
        
        renewal["post_hook"] = hook if hook else None
        settings["auto_renewal"] = renewal
        _save_settings(settings)
        
        _update_certbot_hooks(renewal)
        show_success("Post-hook configured!")
    
    elif action == "Test renewal (dry-run)":
        try:
            require_root()
        except PermissionError:
            press_enter_to_continue()
            return
        
        show_info("Running renewal dry-run...")
        console.print()
        
        from utils.shell import run_command_realtime
        run_command_realtime("certbot renew --dry-run", "Testing renewal...")
    
    press_enter_to_continue()


def _update_certbot_hooks(renewal):
    """Update certbot hooks configuration."""
    hooks_dir = "/etc/letsencrypt/renewal-hooks"
    
    pre_hook_file = f"{hooks_dir}/pre/vexo-hook.sh"
    if renewal.get("pre_hook"):
        os.makedirs(f"{hooks_dir}/pre", exist_ok=True)
        with open(pre_hook_file, "w") as f:
            f.write(f"#!/bin/bash\n{renewal['pre_hook']}\n")
        os.chmod(pre_hook_file, 0o755)
    elif os.path.exists(pre_hook_file):
        os.remove(pre_hook_file)
    
    post_hook_file = f"{hooks_dir}/post/vexo-hook.sh"
    if renewal.get("post_hook"):
        os.makedirs(f"{hooks_dir}/post", exist_ok=True)
        with open(post_hook_file, "w") as f:
            f.write(f"#!/bin/bash\n{renewal['post_hook']}\n")
        os.chmod(post_hook_file, 0o755)
    elif os.path.exists(post_hook_file):
        os.remove(post_hook_file)


def configure_thresholds():
    """Configure alert thresholds."""
    clear_screen()
    show_header()
    show_panel("Alert Thresholds", title="Settings", style="cyan")
    
    settings = _load_settings()
    thresholds = settings.get("alert_thresholds", {
        "critical": ALERT_CRITICAL,
        "warning": ALERT_WARNING,
        "notice": ALERT_NOTICE
    })
    
    console.print("[bold]Current Thresholds (days before expiry):[/bold]")
    console.print(f"  [red]Critical:[/red] {thresholds.get('critical', ALERT_CRITICAL)} days")
    console.print(f"  [yellow]Warning:[/yellow] {thresholds.get('warning', ALERT_WARNING)} days")
    console.print(f"  [cyan]Notice:[/cyan] {thresholds.get('notice', ALERT_NOTICE)} days")
    console.print()
    
    level = select_from_list(
        title="Level",
        message="Which threshold to change:",
        options=["Critical", "Warning", "Notice"]
    )
    
    if not level:
        press_enter_to_continue()
        return
    
    level_key = level.lower()
    current = thresholds.get(level_key, 7)
    
    new_value = text_input(
        title="Days",
        message=f"{level} threshold (days):",
        default=str(current)
    )
    
    if new_value:
        try:
            thresholds[level_key] = int(new_value)
            settings["alert_thresholds"] = thresholds
            _save_settings(settings)
            show_success(f"{level} threshold set to {new_value} days!")
        except ValueError:
            handle_error("E6002", "Invalid number.")
    
    press_enter_to_continue()


def view_all_settings():
    """View all current settings."""
    clear_screen()
    show_header()
    show_panel("All Settings", title="Settings", style="cyan")
    
    settings = _load_settings()
    
    console.print("[bold]Default CA:[/bold]")
    ca_key = settings.get("default_ca", "letsencrypt")
    ca_name = CERTIFICATE_AUTHORITIES.get(ca_key, {}).get("name", ca_key)
    console.print(f"  {ca_name}")
    console.print()
    
    console.print("[bold]Alert Thresholds:[/bold]")
    thresholds = settings.get("alert_thresholds", {})
    console.print(f"  Critical: {thresholds.get('critical', ALERT_CRITICAL)} days")
    console.print(f"  Warning: {thresholds.get('warning', ALERT_WARNING)} days")
    console.print(f"  Notice: {thresholds.get('notice', ALERT_NOTICE)} days")
    console.print()
    
    console.print("[bold]Alerts:[/bold]")
    alerts = settings.get("alerts", {})
    console.print(f"  Enabled: {alerts.get('enabled', False)}")
    console.print(f"  Email: {alerts.get('email') or 'Not set'}")
    console.print(f"  Webhook: {'Configured' if alerts.get('webhook') else 'Not set'}")
    console.print()
    
    console.print("[bold]Auto-Renewal:[/bold]")
    renewal = settings.get("auto_renewal", {})
    console.print(f"  Pre-hook: {renewal.get('pre_hook') or 'None'}")
    console.print(f"  Post-hook: {renewal.get('post_hook') or 'None'}")
    console.print()
    
    console.print("[bold]Scheduled Backups:[/bold]")
    backup = settings.get("scheduled_backup", {})
    console.print(f"  Enabled: {backup.get('enabled', False)}")
    console.print(f"  Schedule: {backup.get('schedule', 'weekly')}")
    console.print(f"  Retention: {backup.get('retention', 7)} backups")
    console.print()
    
    console.print(f"[dim]Settings file: {SETTINGS_FILE}[/dim]")
    
    press_enter_to_continue()


def reset_settings():
    """Reset all settings to defaults."""
    clear_screen()
    show_header()
    show_panel("Reset Settings", title="Settings", style="cyan")
    
    console.print("[red bold]WARNING: This will reset ALL settings to defaults![/red bold]")
    console.print()
    console.print("This includes:")
    console.print("  - Default CA selection")
    console.print("  - Alert thresholds")
    console.print("  - Email/webhook alerts")
    console.print("  - Auto-renewal hooks")
    console.print("  - Scheduled backup settings")
    console.print()
    
    if not confirm_action("Reset all settings to defaults?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    confirm_text = text_input(
        title="Confirm",
        message="Type 'RESET' to confirm:"
    )
    
    if confirm_text != "RESET":
        show_warning("Confirmation did not match. Cancelled.")
        press_enter_to_continue()
        return
    
    _save_settings(_default_settings())
    show_success("Settings reset to defaults!")
    
    press_enter_to_continue()


def load_settings():
    """Public function to load settings."""
    return _load_settings()


def save_settings(settings):
    """Public function to save settings."""
    _save_settings(settings)
