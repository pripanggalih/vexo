"""Setup wizard module for vexo (First Run Setup)."""

import os

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.utils import InquirerPyStyle

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_success,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from utils.shell import run_command, run_apt_with_progress, run_apt_update_with_progress, is_installed
from utils.error_handler import handle_error


# Cyan theme for checkbox
SETUP_STYLE = InquirerPyStyle({
    "questionmark": "#00ffff bold",
    "answermark": "#00ffff bold",
    "answer": "#00ffff",
    "question": "#ffffff bold",
    "instruction": "#666666",
    "pointer": "#00ffff bold",
    "checkbox": "#00ffff",
    "separator": "#666666",
})


def _check_nvm_installed():
    """Check if NVM is installed."""
    nvm_dir = os.path.expanduser("~/.nvm")
    return os.path.exists(nvm_dir)


# Component definitions
COMPONENTS = [
    {
        "key": "nginx",
        "name": "Nginx",
        "description": "Web Server",
        "default": True,
        "check": lambda: is_installed("nginx"),
        "packages": ["nginx"],
    },
    {
        "key": "php",
        "name": "PHP 8.3",
        "description": "Runtime + Composer",
        "default": True,
        "check": lambda: is_installed("php8.3-fpm"),
        "packages": [
            "php8.3-fpm", "php8.3-cli", "php8.3-common", "php8.3-mysql",
            "php8.3-pgsql", "php8.3-sqlite3", "php8.3-redis", "php8.3-mbstring",
            "php8.3-xml", "php8.3-curl", "php8.3-zip", "php8.3-gd", "php8.3-bcmath",
        ],
        "ppa": "ppa:ondrej/php",
        "post_install": "_install_composer",
    },
    {
        "key": "nodejs",
        "name": "Node.js",
        "description": "via NVM",
        "default": False,
        "check": _check_nvm_installed,
        "custom_install": "_install_nodejs",
    },
    {
        "key": "mysql",
        "name": "MySQL/MariaDB",
        "description": "Database",
        "default": True,
        "check": lambda: is_installed("mariadb-server") or is_installed("mysql-server"),
        "packages": ["mariadb-server", "mariadb-client"],
        "post_install": "_secure_mysql",
    },
    {
        "key": "postgresql",
        "name": "PostgreSQL",
        "description": "Database",
        "default": False,
        "check": lambda: is_installed("postgresql"),
        "packages": ["postgresql", "postgresql-contrib"],
    },
    {
        "key": "redis",
        "name": "Redis",
        "description": "Cache",
        "default": True,
        "check": lambda: is_installed("redis-server"),
        "packages": ["redis-server"],
    },
    {
        "key": "supervisor",
        "name": "Supervisor",
        "description": "Queue Workers",
        "default": True,
        "check": lambda: is_installed("supervisor"),
        "packages": ["supervisor"],
    },
    {
        "key": "ufw",
        "name": "UFW Firewall",
        "description": "Security",
        "default": True,
        "check": lambda: is_installed("ufw"),
        "packages": ["ufw"],
        "post_install": "_configure_ufw",
    },
    {
        "key": "fail2ban",
        "name": "Fail2ban",
        "description": "Security",
        "default": True,
        "check": lambda: is_installed("fail2ban"),
        "packages": ["fail2ban"],
    },
    {
        "key": "postfix",
        "name": "Postfix",
        "description": "Email (send only)",
        "default": False,
        "check": lambda: is_installed("postfix"),
        "packages": ["postfix", "mailutils"],
    },
    {
        "key": "utilities",
        "name": "Utilities",
        "description": "Git, Curl, Htop, etc",
        "default": True,
        "check": lambda: is_installed("git") and is_installed("htop"),
        "packages": [
            "git", "curl", "wget", "zip", "unzip", "htop", "nano",
            "logrotate", "chrony", "rsync", "jq",
        ],
    },
]


# =============================================================================
# Installation Helper Functions
# =============================================================================

def _install_composer():
    """Install Composer globally."""
    show_info("Installing Composer...")
    commands = [
        "curl -sS https://getcomposer.org/installer | php",
        "mv composer.phar /usr/local/bin/composer",
        "chmod +x /usr/local/bin/composer",
    ]
    for cmd in commands:
        result = run_command(cmd, check=False, silent=True)
        if result.returncode != 0:
            return False
    return True


def _install_nodejs():
    """Install Node.js via NVM."""
    show_info("Installing NVM and Node.js...")
    
    # Install NVM
    nvm_install = "curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash"
    result = run_command(nvm_install, check=False, silent=True)
    if result.returncode != 0:
        return False
    
    # Install latest LTS Node.js
    nvm_dir = os.path.expanduser("~/.nvm")
    node_install = f'export NVM_DIR="{nvm_dir}" && . "$NVM_DIR/nvm.sh" && nvm install --lts'
    result = run_command(node_install, check=False, silent=True)
    return result.returncode == 0


def _secure_mysql():
    """Run basic MySQL security setup."""
    show_info("Securing MySQL...")
    commands = [
        "mysql -e \"DELETE FROM mysql.user WHERE User='';\"",
        "mysql -e \"DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');\"",
        "mysql -e \"FLUSH PRIVILEGES;\"",
    ]
    for cmd in commands:
        run_command(cmd, check=False, silent=True)
    return True


def _configure_ufw():
    """Configure UFW with basic rules."""
    show_info("Configuring UFW...")
    commands = [
        "ufw default deny incoming",
        "ufw default allow outgoing",
        "ufw allow ssh",
        "ufw allow http",
        "ufw allow https",
        "ufw --force enable",
    ]
    for cmd in commands:
        result = run_command(cmd, check=False, silent=True)
        if result.returncode != 0:
            return False
    return True


# =============================================================================
# Main Installation Function
# =============================================================================

def install_component(component, step_current=1, step_total=1):
    """
    Install a single component.
    
    Args:
        component: Component dict from COMPONENTS
        step_current: Current step number (e.g., 2)
        step_total: Total steps (e.g., 9)
    
    Returns:
        bool: True if successful
    """
    name = component["name"]
    
    # Check if already installed
    if component["check"]():
        show_info(f"{name} already installed, skipping...")
        return True
    
    console.print(f"[cyan]→ Installing {name}...[/cyan]")
    
    # Custom install function
    if "custom_install" in component:
        func_name = component["custom_install"]
        func = globals().get(func_name)
        if func:
            success = func()
            if success:
                show_success(f"{name} installed")
            else:
                handle_error("E1006", f"{name} installation failed")
            return success
        return False
    
    # Add PPA if needed
    if "ppa" in component:
        show_info(f"Adding PPA: {component['ppa']}")
        result = run_command(
            f"add-apt-repository -y {component['ppa']}",
            check=False, silent=True
        )
        if result.returncode != 0:
            show_warning(f"Failed to add PPA for {name}")
        run_apt_update_with_progress()
    
    # Install packages with progress bar
    if "packages" in component:
        success = run_apt_with_progress(
            component["packages"],
            step_info=f"[{step_current}/{step_total}] {name}"
        )
        if not success:
            handle_error("E1006", f"{name} installation failed")
            return False
    
    # Post-install hook
    if "post_install" in component:
        func_name = component["post_install"]
        func = globals().get(func_name)
        if func:
            func()
    
    show_success(f"{name} installed")
    return True


# =============================================================================
# Setup Wizard UI
# =============================================================================

def show_setup_wizard():
    """
    Display the first-run setup wizard.
    
    Returns:
        bool: True if setup completed, False if skipped
    """
    clear_screen()
    show_header()
    
    console.print("[bold cyan]Welcome to vexo![/bold cyan]")
    console.print()
    console.print("This appears to be a fresh VPS. Let's set up your server.")
    console.print("Select the components you want to install:")
    console.print()
    
    # Build checkbox choices
    choices = []
    for comp in COMPONENTS:
        # Skip if already installed
        if comp["check"]():
            continue
        
        choices.append(Choice(
            value=comp["key"],
            name=f"{comp['name']:20} {comp['description']}",
            enabled=comp["default"],
        ))
    
    if not choices:
        show_info("All components are already installed!")
        press_enter_to_continue()
        return True
    
    try:
        selected = inquirer.checkbox(
            message="Select components:",
            choices=choices,
            style=SETUP_STYLE,
            instruction="(Space toggle, Enter confirm, A select all)",
        ).execute()
    except KeyboardInterrupt:
        show_warning("Setup cancelled.")
        press_enter_to_continue()
        return False
    
    if not selected:
        show_warning("No components selected. Skipping setup.")
        press_enter_to_continue()
        return False
    
    # Run installation
    return run_setup(selected)


def run_setup(selected_keys):
    """
    Install selected components.
    
    Args:
        selected_keys: List of component keys to install
    
    Returns:
        bool: True if all successful
    """
    clear_screen()
    show_header()
    
    console.print("[bold]Installing selected components...[/bold]")
    console.print()
    
    # Update apt first with progress
    run_apt_update_with_progress()
    
    total = len(selected_keys)
    success_count = 0
    failed = []
    
    for i, key in enumerate(selected_keys, 1):
        # Find component
        comp = next((c for c in COMPONENTS if c["key"] == key), None)
        if not comp:
            continue
        
        console.print(f"\n[bold][{i}/{total}] {comp['name']}[/bold]")
        
        if install_component(comp, step_current=i, step_total=total):
            success_count += 1
        else:
            failed.append(comp["name"])
    
    # Summary
    console.print()
    console.print("─" * 40)
    
    if success_count == total:
        show_success(f"Setup complete! {success_count}/{total} components installed.")
    else:
        show_warning(f"Setup complete: {success_count}/{total} installed")
        if failed:
            handle_error("E1006", f"Failed to install: {', '.join(failed)}")
    
    press_enter_to_continue()
    return success_count == total


def is_first_run():
    """
    Check if this is a first run (setup wizard needed).
    
    Returns:
        bool: True if setup wizard should be shown
    """
    # Consider it first run if nginx is not installed
    return not is_installed("nginx")
