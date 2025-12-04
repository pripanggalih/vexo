"""Email routing - aliases, forwarding, spam filter, blacklist."""

import os
import json

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import (
    run_command, run_command_realtime, is_installed, is_service_running,
    service_control, require_root,
)
from utils.error_handler import handle_error
from modules.email.postfix.utils import (
    is_postfix_ready, set_postfix_settings, reload_postfix,
)
from modules.email.utils import load_email_config, save_email_config


# File paths
POSTFIX_ALIASES = "/etc/postfix/virtual_aliases"
POSTFIX_ACCESS = "/etc/postfix/access"
SPAMASSASSIN_LOCAL = "/etc/spamassassin/local.cf"


def show_routing_menu():
    """Display routing menu."""
    def get_status():
        config = load_email_config()
        aliases = len(config.get("aliases", {}))
        forwards = len(config.get("forwards", {}))
        spam = "[green]On[/green]" if is_service_running("spamassassin") else "[dim]Off[/dim]"
        return f"Aliases:{aliases} Fwd:{forwards} Spam:{spam}"
    
    options = [
        ("aliases", "1. Email Aliases"),
        ("forward", "2. Email Forwarding"),
        ("spam", "3. Spam Filter (SpamAssassin)"),
        ("blacklist", "4. Blacklist / Whitelist"),
        ("restrict", "5. Sender Restrictions"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "aliases": show_aliases_menu,
        "forward": show_forward_menu,
        "spam": show_spam_menu,
        "blacklist": show_blacklist_menu,
        "restrict": show_restrictions_menu,
    }
    
    run_menu_loop("Email Routing", options, handlers, get_status)


# =============================================================================
# Email Aliases
# =============================================================================

def show_aliases_menu():
    """Email aliases management menu."""
    def get_status():
        config = load_email_config()
        count = len(config.get("aliases", {}))
        return f"Aliases: {count}"
    
    options = [
        ("list", "1. List Aliases"),
        ("add", "2. Add Alias"),
        ("remove", "3. Remove Alias"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "list": list_aliases,
        "add": add_alias,
        "remove": remove_alias,
    }
    
    run_menu_loop("Email Aliases", options, handlers, get_status)


def list_aliases():
    """List configured email aliases."""
    clear_screen()
    show_header()
    show_panel("Email Aliases", title="Routing", style="cyan")
    
    config = load_email_config()
    aliases = config.get("aliases", {})
    
    if not aliases:
        show_info("No aliases configured.")
        console.print()
        console.print("[dim]Aliases map one email address to another.[/dim]")
        console.print("[dim]Example: info@domain.com → admin@domain.com[/dim]")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Alias", "style": "cyan"},
        {"name": "Destination"},
    ]
    
    rows = [[alias, dest] for alias, dest in aliases.items()]
    
    show_table(f"{len(aliases)} alias(es)", columns, rows, show_header=True)
    press_enter_to_continue()


def add_alias():
    """Add email alias."""
    clear_screen()
    show_header()
    show_panel("Add Alias", title="Email Aliases", style="cyan")
    
    console.print("[bold]Email Alias[/bold]")
    console.print("[dim]Maps one address to another (internal redirect).[/dim]")
    console.print()
    
    alias = text_input("Alias address (e.g., info@example.com):")
    if not alias or "@" not in alias:
        handle_error("E5002", "Invalid email address.")
        press_enter_to_continue()
        return
    
    destination = text_input("Destination address:")
    if not destination or "@" not in destination:
        handle_error("E5002", "Invalid email address.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    config = load_email_config()
    if "aliases" not in config:
        config["aliases"] = {}
    
    config["aliases"][alias.lower()] = destination.lower()
    save_email_config(config)
    
    _regenerate_aliases_file(config)
    reload_postfix()
    
    show_success(f"Alias added: {alias} → {destination}")
    press_enter_to_continue()


def remove_alias():
    """Remove email alias."""
    clear_screen()
    show_header()
    show_panel("Remove Alias", title="Email Aliases", style="red")
    
    config = load_email_config()
    aliases = config.get("aliases", {})
    
    if not aliases:
        show_info("No aliases configured.")
        press_enter_to_continue()
        return
    
    alias_list = list(aliases.keys())
    alias = select_from_list("Select Alias", "Remove:", alias_list)
    if not alias:
        return
    
    if not confirm_action(f"Remove alias {alias}?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    del config["aliases"][alias]
    save_email_config(config)
    
    _regenerate_aliases_file(config)
    reload_postfix()
    
    show_success(f"Alias removed: {alias}")
    press_enter_to_continue()


def _regenerate_aliases_file(config):
    """Regenerate Postfix aliases file."""
    aliases = config.get("aliases", {})
    
    with open(POSTFIX_ALIASES, 'w') as f:
        f.write("# Email aliases - managed by vexo\n")
        for alias, dest in aliases.items():
            f.write(f"{alias} {dest}\n")
    
    run_command(f"postmap {POSTFIX_ALIASES}", check=False, silent=True)
    
    # Update Postfix config
    set_postfix_settings({
        "virtual_alias_maps": f"hash:{POSTFIX_ALIASES}",
    })


# =============================================================================
# Email Forwarding
# =============================================================================

def show_forward_menu():
    """Email forwarding management menu."""
    def get_status():
        config = load_email_config()
        count = len(config.get("forwards", {}))
        return f"Forwards: {count}"
    
    options = [
        ("list", "1. List Forwards"),
        ("add", "2. Add Forward"),
        ("remove", "3. Remove Forward"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "list": list_forwards,
        "add": add_forward,
        "remove": remove_forward,
    }
    
    run_menu_loop("Email Forwarding", options, handlers, get_status)


def list_forwards():
    """List email forwards."""
    clear_screen()
    show_header()
    show_panel("Email Forwards", title="Routing", style="cyan")
    
    config = load_email_config()
    forwards = config.get("forwards", {})
    
    if not forwards:
        show_info("No forwards configured.")
        console.print()
        console.print("[dim]Forwards send copies to external addresses.[/dim]")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Address", "style": "cyan"},
        {"name": "Forward To"},
        {"name": "Keep Copy"},
    ]
    
    rows = []
    for addr, cfg in forwards.items():
        keep = "[green]Yes[/green]" if cfg.get("keep_copy", False) else "No"
        rows.append([addr, cfg.get("forward_to", ""), keep])
    
    show_table(f"{len(forwards)} forward(s)", columns, rows, show_header=True)
    press_enter_to_continue()


def add_forward():
    """Add email forward."""
    clear_screen()
    show_header()
    show_panel("Add Forward", title="Email Forwarding", style="cyan")
    
    console.print("[bold]Email Forwarding[/bold]")
    console.print("[dim]Forward emails to an external address.[/dim]")
    console.print()
    
    address = text_input("Local address (e.g., alerts@example.com):")
    if not address or "@" not in address:
        handle_error("E5002", "Invalid email address.")
        press_enter_to_continue()
        return
    
    forward_to = text_input("Forward to (external email):")
    if not forward_to or "@" not in forward_to:
        handle_error("E5002", "Invalid email address.")
        press_enter_to_continue()
        return
    
    keep_copy = confirm_action("Keep a local copy?")
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    config = load_email_config()
    if "forwards" not in config:
        config["forwards"] = {}
    
    config["forwards"][address.lower()] = {
        "forward_to": forward_to.lower(),
        "keep_copy": keep_copy,
    }
    save_email_config(config)
    
    _regenerate_forwards(config)
    reload_postfix()
    
    show_success(f"Forward added: {address} → {forward_to}")
    press_enter_to_continue()


def remove_forward():
    """Remove email forward."""
    clear_screen()
    show_header()
    show_panel("Remove Forward", title="Email Forwarding", style="red")
    
    config = load_email_config()
    forwards = config.get("forwards", {})
    
    if not forwards:
        show_info("No forwards configured.")
        press_enter_to_continue()
        return
    
    addr_list = list(forwards.keys())
    address = select_from_list("Select Address", "Remove forward for:", addr_list)
    if not address:
        return
    
    if not confirm_action(f"Remove forward for {address}?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    del config["forwards"][address]
    save_email_config(config)
    
    _regenerate_forwards(config)
    reload_postfix()
    
    show_success(f"Forward removed: {address}")
    press_enter_to_continue()


def _regenerate_forwards(config):
    """Add forwards to aliases file."""
    forwards = config.get("forwards", {})
    aliases = config.get("aliases", {})
    
    with open(POSTFIX_ALIASES, 'w') as f:
        f.write("# Email aliases and forwards - managed by vexo\n")
        
        # Write aliases
        for alias, dest in aliases.items():
            f.write(f"{alias} {dest}\n")
        
        # Write forwards
        for addr, cfg in forwards.items():
            forward_to = cfg.get("forward_to", "")
            if cfg.get("keep_copy", False):
                # Keep copy locally
                f.write(f"{addr} {addr}, {forward_to}\n")
            else:
                f.write(f"{addr} {forward_to}\n")
    
    run_command(f"postmap {POSTFIX_ALIASES}", check=False, silent=True)


# =============================================================================
# Spam Filter (SpamAssassin)
# =============================================================================

def show_spam_menu():
    """SpamAssassin management menu."""
    def get_status():
        if not is_installed("spamassassin"):
            return "SpamAssassin: [dim]Not Installed[/dim]"
        if is_service_running("spamassassin"):
            return "SpamAssassin: [green]Running[/green]"
        return "SpamAssassin: [red]Stopped[/red]"
    
    options = [
        ("status", "1. View Status"),
        ("install", "2. Install SpamAssassin"),
        ("config", "3. Configure"),
        ("test", "4. Test Spam Check"),
        ("service", "5. Service Control"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "status": spam_status,
        "install": install_spamassassin,
        "config": configure_spamassassin,
        "test": test_spam_check,
        "service": spam_service_control,
    }
    
    run_menu_loop("Spam Filter", options, handlers, get_status)


def spam_status():
    """View SpamAssassin status."""
    clear_screen()
    show_header()
    show_panel("SpamAssassin Status", title="Spam Filter", style="cyan")
    
    if not is_installed("spamassassin"):
        show_info("SpamAssassin is not installed.")
        press_enter_to_continue()
        return
    
    running = is_service_running("spamassassin")
    console.print(f"[bold]Service:[/bold] {'[green]Running[/green]' if running else '[red]Stopped[/red]'}")
    
    # Get config
    if os.path.exists(SPAMASSASSIN_LOCAL):
        console.print()
        console.print("[bold]Configuration:[/bold]")
        
        result = run_command(f"grep -E '^[^#]' {SPAMASSASSIN_LOCAL}", check=False, silent=True)
        if result.stdout:
            for line in result.stdout.strip().split('\n')[:10]:
                console.print(f"  {line}")
    
    press_enter_to_continue()


def install_spamassassin():
    """Install SpamAssassin."""
    clear_screen()
    show_header()
    show_panel("Install SpamAssassin", title="Spam Filter", style="cyan")
    
    if is_installed("spamassassin"):
        show_info("SpamAssassin is already installed.")
        press_enter_to_continue()
        return
    
    console.print("[bold]SpamAssassin will filter incoming spam emails.[/bold]")
    console.print()
    
    if not confirm_action("Install SpamAssassin?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    show_info("Installing SpamAssassin...")
    
    returncode = run_command_realtime(
        "apt install -y spamassassin spamc",
        "Installing SpamAssassin..."
    )
    
    if returncode != 0:
        handle_error("E5002", "Failed to install SpamAssassin.")
        press_enter_to_continue()
        return
    
    # Enable service
    run_command("systemctl enable spamassassin", check=False, silent=True)
    
    # Basic configuration
    config_content = """# SpamAssassin configuration - managed by vexo
required_score 5.0
report_safe 0
rewrite_header Subject [SPAM]
use_bayes 1
bayes_auto_learn 1
"""
    
    with open(SPAMASSASSIN_LOCAL, 'w') as f:
        f.write(config_content)
    
    # Enable in /etc/default/spamassassin
    run_command(
        'sed -i "s/ENABLED=0/ENABLED=1/" /etc/default/spamassassin',
        check=False, silent=True
    )
    
    service_control("spamassassin", "start")
    
    # Configure Postfix to use SpamAssassin
    # Add content filter
    set_postfix_settings({
        "content_filter": "spamassassin",
    })
    
    # Add to master.cf
    _add_spamassassin_to_master_cf()
    
    reload_postfix()
    
    show_success("SpamAssassin installed and configured!")
    press_enter_to_continue()


def _add_spamassassin_to_master_cf():
    """Add SpamAssassin transport to master.cf."""
    master_cf = "/etc/postfix/master.cf"
    
    # Check if already configured
    result = run_command(f"grep 'spamassassin' {master_cf}", check=False, silent=True)
    if result.returncode == 0:
        return
    
    spamassassin_config = """
# SpamAssassin - added by vexo
spamassassin unix - n n - - pipe
  user=spamd argv=/usr/bin/spamc -f -e /usr/sbin/sendmail -oi -f ${sender} ${recipient}
"""
    
    with open(master_cf, 'a') as f:
        f.write(spamassassin_config)


def configure_spamassassin():
    """Configure SpamAssassin settings."""
    clear_screen()
    show_header()
    show_panel("Configure SpamAssassin", title="Spam Filter", style="cyan")
    
    if not is_installed("spamassassin"):
        handle_error("E5002", "SpamAssassin is not installed.")
        press_enter_to_continue()
        return
    
    # Get current threshold
    result = run_command(
        f"grep 'required_score' {SPAMASSASSIN_LOCAL} | awk '{{print $2}}'",
        check=False, silent=True
    )
    current_threshold = result.stdout.strip() if result.returncode == 0 else "5.0"
    
    console.print(f"[bold]Current spam threshold:[/bold] {current_threshold}")
    console.print("[dim]Lower = more strict, Higher = more permissive[/dim]")
    console.print()
    
    options = [
        "Set threshold (score)",
        "Set subject prefix",
        "Enable/Disable Bayes learning",
    ]
    
    choice = select_from_list("Configure", "Select option:", options)
    if not choice:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if "threshold" in choice:
        thresholds = ["3.0 (strict)", "5.0 (default)", "7.0 (permissive)", "Custom"]
        threshold = select_from_list("Threshold", "Select spam threshold:", thresholds)
        
        if threshold:
            if "Custom" in threshold:
                threshold = text_input("Custom threshold (e.g., 4.5):")
            else:
                threshold = threshold.split(" ")[0]
            
            if threshold:
                run_command(
                    f'sed -i "s/required_score.*/required_score {threshold}/" {SPAMASSASSIN_LOCAL}',
                    check=False, silent=True
                )
                service_control("spamassassin", "restart")
                show_success(f"Threshold set to {threshold}")
    
    elif "prefix" in choice:
        prefix = text_input("Subject prefix for spam:", default="[SPAM]")
        if prefix:
            run_command(
                f'sed -i "s/rewrite_header Subject.*/rewrite_header Subject {prefix}/" {SPAMASSASSIN_LOCAL}',
                check=False, silent=True
            )
            service_control("spamassassin", "restart")
            show_success(f"Subject prefix set to {prefix}")
    
    elif "Bayes" in choice:
        if confirm_action("Enable Bayes auto-learning?"):
            run_command(
                f'sed -i "s/use_bayes.*/use_bayes 1/" {SPAMASSASSIN_LOCAL}',
                check=False, silent=True
            )
            show_success("Bayes learning enabled!")
        else:
            run_command(
                f'sed -i "s/use_bayes.*/use_bayes 0/" {SPAMASSASSIN_LOCAL}',
                check=False, silent=True
            )
            show_success("Bayes learning disabled!")
        
        service_control("spamassassin", "restart")
    
    press_enter_to_continue()


def test_spam_check():
    """Test SpamAssassin with sample spam."""
    clear_screen()
    show_header()
    show_panel("Test Spam Check", title="Spam Filter", style="cyan")
    
    if not is_installed("spamassassin"):
        handle_error("E5002", "SpamAssassin is not installed.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Testing SpamAssassin with GTUBE test string...[/bold]")
    console.print()
    
    # GTUBE (Generic Test for Unsolicited Bulk Email)
    gtube = "XJS*C4JDBQADN1.NSBN3*2IDNEN*GTUBE-STANDARD-ANTI-UBE-TEST-EMAIL*C.34X"
    
    test_email = f"""Subject: Test spam email
From: test@example.com
To: test@localhost

This is a test email containing the GTUBE test string:
{gtube}

If SpamAssassin is working, this should be marked as spam.
"""
    
    result = run_command(
        f'echo "{test_email}" | spamc',
        check=False, silent=True
    )
    
    if "X-Spam-Flag: YES" in result.stdout or "GTUBE" in result.stdout:
        show_success("SpamAssassin is working correctly!")
        console.print()
        console.print("[dim]GTUBE test string detected as spam.[/dim]")
    else:
        show_warning("Test inconclusive.")
    
    console.print()
    console.print("[bold]Output:[/bold]")
    console.print(result.stdout[:1000] if result.stdout else "[dim]No output[/dim]")
    
    press_enter_to_continue()


def spam_service_control():
    """Control SpamAssassin service."""
    clear_screen()
    show_header()
    show_panel("Service Control", title="SpamAssassin", style="cyan")
    
    if not is_installed("spamassassin"):
        handle_error("E5002", "SpamAssassin is not installed.")
        press_enter_to_continue()
        return
    
    running = is_service_running("spamassassin")
    console.print(f"[bold]Status:[/bold] {'[green]Running[/green]' if running else '[red]Stopped[/red]'}")
    console.print()
    
    options = ["Start", "Stop", "Restart"]
    action = select_from_list("Action", "Select:", options)
    
    if not action:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    service_control("spamassassin", action.lower())
    show_success(f"SpamAssassin {action.lower()}ed!")
    
    press_enter_to_continue()


# =============================================================================
# Blacklist / Whitelist
# =============================================================================

def show_blacklist_menu():
    """Blacklist/whitelist management menu."""
    def get_status():
        config = load_email_config()
        bl = len(config.get("blacklist", []))
        wl = len(config.get("whitelist", []))
        return f"Black:{bl} White:{wl}"
    
    options = [
        ("view", "1. View Lists"),
        ("add_black", "2. Add to Blacklist"),
        ("add_white", "3. Add to Whitelist"),
        ("remove", "4. Remove Entry"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "view": view_lists,
        "add_black": add_to_blacklist,
        "add_white": add_to_whitelist,
        "remove": remove_from_list,
    }
    
    run_menu_loop("Blacklist / Whitelist", options, handlers, get_status)


def view_lists():
    """View blacklist and whitelist."""
    clear_screen()
    show_header()
    show_panel("Blacklist / Whitelist", title="Routing", style="cyan")
    
    config = load_email_config()
    blacklist = config.get("blacklist", [])
    whitelist = config.get("whitelist", [])
    
    console.print("[bold red]Blacklist (blocked):[/bold red]")
    if blacklist:
        for entry in blacklist:
            console.print(f"  • {entry}")
    else:
        console.print("  [dim]Empty[/dim]")
    
    console.print()
    
    console.print("[bold green]Whitelist (always allow):[/bold green]")
    if whitelist:
        for entry in whitelist:
            console.print(f"  • {entry}")
    else:
        console.print("  [dim]Empty[/dim]")
    
    press_enter_to_continue()


def add_to_blacklist():
    """Add sender to blacklist."""
    clear_screen()
    show_header()
    show_panel("Add to Blacklist", title="Blacklist", style="red")
    
    console.print("[bold]Block emails from sender or domain.[/bold]")
    console.print("[dim]Examples: spam@example.com or @spamdomain.com[/dim]")
    console.print()
    
    entry = text_input("Email or domain to block:")
    if not entry:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    config = load_email_config()
    if "blacklist" not in config:
        config["blacklist"] = []
    
    if entry not in config["blacklist"]:
        config["blacklist"].append(entry.lower())
        save_email_config(config)
        _regenerate_access_file(config)
        reload_postfix()
        show_success(f"Added to blacklist: {entry}")
    else:
        show_info("Already in blacklist.")
    
    press_enter_to_continue()


def add_to_whitelist():
    """Add sender to whitelist."""
    clear_screen()
    show_header()
    show_panel("Add to Whitelist", title="Whitelist", style="green")
    
    console.print("[bold]Always allow emails from sender or domain.[/bold]")
    console.print()
    
    entry = text_input("Email or domain to allow:")
    if not entry:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    config = load_email_config()
    if "whitelist" not in config:
        config["whitelist"] = []
    
    if entry not in config["whitelist"]:
        config["whitelist"].append(entry.lower())
        save_email_config(config)
        _regenerate_access_file(config)
        reload_postfix()
        show_success(f"Added to whitelist: {entry}")
    else:
        show_info("Already in whitelist.")
    
    press_enter_to_continue()


def remove_from_list():
    """Remove entry from blacklist or whitelist."""
    clear_screen()
    show_header()
    show_panel("Remove Entry", title="Blacklist / Whitelist", style="yellow")
    
    config = load_email_config()
    blacklist = config.get("blacklist", [])
    whitelist = config.get("whitelist", [])
    
    all_entries = []
    for e in blacklist:
        all_entries.append(f"[black] {e}")
    for e in whitelist:
        all_entries.append(f"[white] {e}")
    
    if not all_entries:
        show_info("No entries in either list.")
        press_enter_to_continue()
        return
    
    entry = select_from_list("Select Entry", "Remove:", all_entries)
    if not entry:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Parse selection
    if entry.startswith("[black]"):
        actual = entry.replace("[black] ", "")
        config["blacklist"].remove(actual)
    else:
        actual = entry.replace("[white] ", "")
        config["whitelist"].remove(actual)
    
    save_email_config(config)
    _regenerate_access_file(config)
    reload_postfix()
    
    show_success(f"Removed: {actual}")
    press_enter_to_continue()


def _regenerate_access_file(config):
    """Regenerate Postfix access file."""
    blacklist = config.get("blacklist", [])
    whitelist = config.get("whitelist", [])
    
    with open(POSTFIX_ACCESS, 'w') as f:
        f.write("# Sender access control - managed by vexo\n")
        
        # Whitelist first (OK)
        for entry in whitelist:
            f.write(f"{entry} OK\n")
        
        # Blacklist (REJECT)
        for entry in blacklist:
            f.write(f"{entry} REJECT\n")
    
    run_command(f"postmap {POSTFIX_ACCESS}", check=False, silent=True)
    
    # Update Postfix config
    set_postfix_settings({
        "smtpd_sender_restrictions": f"check_sender_access hash:{POSTFIX_ACCESS}",
    })


# =============================================================================
# Sender Restrictions
# =============================================================================

def show_restrictions_menu():
    """Sender restrictions menu."""
    clear_screen()
    show_header()
    show_panel("Sender Restrictions", title="Routing", style="cyan")
    
    console.print("[bold]Sender restrictions control who can send email FROM this server.[/bold]")
    console.print()
    
    # Current settings
    mynetworks = run_command("postconf -h mynetworks", check=False, silent=True).stdout.strip()
    console.print(f"[bold]Allowed networks:[/bold] {mynetworks}")
    console.print()
    
    options = [
        "Allow localhost only (most secure)",
        "Allow local network",
        "Add custom IP/network",
        "View current restrictions",
    ]
    
    choice = select_from_list("Action", "Select:", options)
    if not choice:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if "localhost only" in choice:
        set_postfix_settings({"mynetworks": "127.0.0.0/8 [::1]/128"})
        reload_postfix()
        show_success("Restricted to localhost only.")
    
    elif "local network" in choice:
        set_postfix_settings({"mynetworks": "127.0.0.0/8 [::1]/128 192.168.0.0/16 10.0.0.0/8"})
        reload_postfix()
        show_success("Local network allowed.")
    
    elif "custom" in choice:
        ip = text_input("IP or network (e.g., 192.168.1.0/24):")
        if ip:
            current = run_command("postconf -h mynetworks", check=False, silent=True).stdout.strip()
            new_networks = f"{current} {ip}"
            set_postfix_settings({"mynetworks": new_networks})
            reload_postfix()
            show_success(f"Added {ip} to allowed networks.")
    
    else:
        # View restrictions
        result = run_command("postconf mynetworks smtpd_sender_restrictions smtpd_recipient_restrictions", check=False, silent=True)
        console.print(result.stdout)
    
    press_enter_to_continue()
