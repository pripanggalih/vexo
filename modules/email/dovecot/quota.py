"""Dovecot quota management."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import is_installed, require_root
from modules.email.utils import load_email_config, save_email_config


def show_quota_menu():
    """Display quota settings menu."""
    def get_status():
        config = load_email_config()
        default = config.get("default_quota", 0)
        return f"Default: {_format_size(default) if default else 'Unlimited'}"
    
    options = [
        ("default", "1. Set Default Quota"),
        ("user", "2. Set User Quota"),
        ("view", "3. View All Quotas"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "default": set_default_quota,
        "user": set_user_quota,
        "view": view_quotas,
    }
    
    run_menu_loop("Quota Settings", options, handlers, get_status)


def _format_size(size_bytes):
    """Format size to human readable."""
    if size_bytes >= 1024 ** 3:
        return f"{size_bytes / 1024 ** 3:.2f} GB"
    elif size_bytes >= 1024 ** 2:
        return f"{size_bytes / 1024 ** 2:.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    return f"{size_bytes} B"


def _parse_quota(quota_str):
    """Parse quota string to bytes."""
    quota_str = quota_str.upper().strip()
    
    multipliers = {
        'K': 1024,
        'M': 1024 ** 2,
        'G': 1024 ** 3,
    }
    
    for suffix, mult in multipliers.items():
        if quota_str.endswith(suffix):
            try:
                return int(float(quota_str[:-1]) * mult)
            except ValueError:
                pass
    
    try:
        return int(quota_str)
    except ValueError:
        return 0


def set_default_quota():
    """Set default quota for new mailboxes."""
    clear_screen()
    show_header()
    show_panel("Default Quota", title="Quota Settings", style="cyan")
    
    config = load_email_config()
    current = config.get("default_quota", 0)
    
    console.print(f"[bold]Current default:[/bold] {_format_size(current) if current else 'Unlimited'}")
    console.print()
    console.print("[dim]This quota will be applied to newly created mailboxes.[/dim]")
    console.print()
    
    quota_options = [
        "500 MB",
        "1 GB",
        "2 GB",
        "5 GB",
        "10 GB",
        "Unlimited",
        "Custom",
    ]
    
    choice = select_from_list("Default Quota", "Select:", quota_options)
    if not choice:
        return
    
    if "Unlimited" in choice:
        quota = 0
    elif "Custom" in choice:
        custom = text_input("Enter quota (e.g., 1G, 500M):")
        if not custom:
            return
        quota = _parse_quota(custom)
    else:
        quota = _parse_quota(choice.replace(" ", ""))
    
    config["default_quota"] = quota
    save_email_config(config)
    
    show_success(f"Default quota set to {_format_size(quota) if quota else 'Unlimited'}!")
    press_enter_to_continue()


def set_user_quota():
    """Set quota for specific user."""
    clear_screen()
    show_header()
    show_panel("User Quota", title="Quota Settings", style="cyan")
    
    if not is_installed("dovecot-core"):
        show_error("Dovecot is not installed.")
        press_enter_to_continue()
        return
    
    # Get mailboxes
    from modules.email.dovecot.mailboxes import _get_mailboxes
    mailboxes = _get_mailboxes()
    
    if not mailboxes:
        show_info("No mailboxes configured.")
        press_enter_to_continue()
        return
    
    email = select_from_list("Select Mailbox", "Set quota for:", mailboxes)
    if not email:
        return
    
    config = load_email_config()
    current = config.get("mailbox_quotas", {}).get(email, {}).get("quota", 0)
    
    console.print(f"[bold]Current quota for {email}:[/bold] {_format_size(current) if current else 'Unlimited'}")
    console.print()
    
    quota_options = [
        "500 MB",
        "1 GB",
        "2 GB",
        "5 GB",
        "10 GB",
        "Unlimited",
        "Custom",
    ]
    
    choice = select_from_list("Quota", "Select:", quota_options)
    if not choice:
        return
    
    if "Unlimited" in choice:
        quota = 0
    elif "Custom" in choice:
        custom = text_input("Enter quota (e.g., 1G, 500M):")
        if not custom:
            return
        quota = _parse_quota(custom)
    else:
        quota = _parse_quota(choice.replace(" ", ""))
    
    if "mailbox_quotas" not in config:
        config["mailbox_quotas"] = {}
    
    if email not in config["mailbox_quotas"]:
        config["mailbox_quotas"][email] = {}
    
    config["mailbox_quotas"][email]["quota"] = quota
    save_email_config(config)
    
    show_success(f"Quota for {email} set to {_format_size(quota) if quota else 'Unlimited'}!")
    press_enter_to_continue()


def view_quotas():
    """View all quota settings."""
    clear_screen()
    show_header()
    show_panel("All Quotas", title="Quota Settings", style="cyan")
    
    config = load_email_config()
    
    # Default quota
    default = config.get("default_quota", 0)
    console.print(f"[bold]Default Quota:[/bold] {_format_size(default) if default else 'Unlimited'}")
    console.print()
    
    # User quotas
    quotas = config.get("mailbox_quotas", {})
    
    if not quotas:
        show_info("No user-specific quotas configured.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Email", "style": "cyan"},
        {"name": "Quota", "justify": "right"},
    ]
    
    rows = []
    for email, info in quotas.items():
        quota = info.get("quota", 0)
        rows.append([email, _format_size(quota) if quota else "[dim]Unlimited[/dim]"])
    
    show_table(f"{len(quotas)} quota(s)", columns, rows, show_header=True)
    press_enter_to_continue()
