# Setup Wizard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add first-run setup wizard with checkbox UI to install essential VPS components automatically.

**Architecture:** Create new `modules/setup.py` with checkbox wizard using InquirerPy. Detect first run in `main.py` by checking if nginx is installed. Each module hides "Install" option if component already installed.

**Tech Stack:** InquirerPy (checkbox), existing utils/shell.py helpers

---

## Task 1: Create setup.py with component definitions

**Files:**
- Create: `modules/setup.py`

**Step 1: Create setup module with component config**

```python
"""Setup wizard module for vexo-cli (First Run Setup)."""

from InquirerPy import inquirer
from InquirerPy.base.control import Choice

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_success,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from utils.shell import run_command, is_installed


# Component definitions: (key, name, description, default_checked, install_func)
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
        "check": lambda: _check_nvm_installed(),
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
    {
        "key": "docker",
        "name": "Docker",
        "description": "Container Runtime",
        "default": False,
        "check": lambda: is_installed("docker-ce") or is_installed("docker.io"),
        "custom_install": "_install_docker",
    },
]


def _check_nvm_installed():
    """Check if NVM is installed."""
    import os
    nvm_dir = os.path.expanduser("~/.nvm")
    return os.path.exists(nvm_dir)
```

**Step 2: Commit**

```bash
git add modules/setup.py
git commit -m "feat(setup): add component definitions for setup wizard"
```

---

## Task 2: Add installation functions to setup.py

**Files:**
- Modify: `modules/setup.py`

**Step 1: Add helper install functions**

Append to `modules/setup.py`:

```python
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
    import os
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
    # Auto-secure: remove anonymous users, disallow remote root
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


def _install_docker():
    """Install Docker using official script."""
    show_info("Installing Docker...")
    commands = [
        "curl -fsSL https://get.docker.com | bash",
        "systemctl enable docker",
        "systemctl start docker",
    ]
    for cmd in commands:
        result = run_command(cmd, check=False, silent=True)
        if result.returncode != 0:
            return False
    return True
```

**Step 2: Commit**

```bash
git add modules/setup.py
git commit -m "feat(setup): add component installation helper functions"
```

---

## Task 3: Add main install_component function

**Files:**
- Modify: `modules/setup.py`

**Step 1: Add install_component function**

Append to `modules/setup.py`:

```python
def install_component(component):
    """
    Install a single component.
    
    Args:
        component: Component dict from COMPONENTS
    
    Returns:
        bool: True if successful
    """
    key = component["key"]
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
                show_error(f"{name} installation failed")
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
        run_command("apt update", check=False, silent=True)
    
    # Install packages
    if "packages" in component:
        packages = " ".join(component["packages"])
        result = run_command(
            f"apt install -y {packages}",
            check=False, silent=False
        )
        if result.returncode != 0:
            show_error(f"{name} installation failed")
            return False
    
    # Post-install hook
    if "post_install" in component:
        func_name = component["post_install"]
        func = globals().get(func_name)
        if func:
            func()
    
    show_success(f"{name} installed")
    return True
```

**Step 2: Commit**

```bash
git add modules/setup.py
git commit -m "feat(setup): add install_component function"
```

---

## Task 4: Add setup wizard UI

**Files:**
- Modify: `modules/setup.py`

**Step 1: Add show_setup_wizard function**

Append to `modules/setup.py`:

```python
from InquirerPy.utils import InquirerPyStyle

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


def show_setup_wizard():
    """
    Display the first-run setup wizard.
    
    Returns:
        bool: True if setup completed, False if skipped
    """
    clear_screen()
    show_header()
    
    console.print("[bold cyan]Welcome to vexo-cli![/bold cyan]")
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
    
    # Update apt first
    show_info("Updating package lists...")
    run_command("apt update", check=False, silent=True)
    
    total = len(selected_keys)
    success_count = 0
    failed = []
    
    for i, key in enumerate(selected_keys, 1):
        # Find component
        comp = next((c for c in COMPONENTS if c["key"] == key), None)
        if not comp:
            continue
        
        console.print(f"\n[bold][{i}/{total}] {comp['name']}[/bold]")
        
        if install_component(comp):
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
            show_error(f"Failed: {', '.join(failed)}")
    
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
```

**Step 2: Commit**

```bash
git add modules/setup.py
git commit -m "feat(setup): add setup wizard UI with checkbox"
```

---

## Task 5: Integrate setup wizard into main.py

**Files:**
- Modify: `main.py`
- Modify: `modules/__init__.py`

**Step 1: Add setup import to modules/__init__.py**

Add to `modules/__init__.py`:

```python
from modules import setup
```

**Step 2: Modify main.py to call setup wizard**

In `main.py`, find the `main()` function and add first run check after auto-update check:

```python
from modules import setup

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
            perform_update()
            sys.exit(0)
        elif arg == "--no-update":
            # Check first run even with --no-update
            if setup.is_first_run():
                setup.show_setup_wizard()
            main_loop()
            return
        elif arg == "--skip-setup":
            # Skip both update and setup
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
```

**Step 3: Commit**

```bash
git add main.py modules/__init__.py
git commit -m "feat(setup): integrate setup wizard into main startup"
```

---

## Task 6: Update module menus to hide install when installed

**Files:**
- Modify: `modules/webserver.py`
- Modify: `modules/runtime.py`
- Modify: `modules/database.py`
- Modify: `modules/supervisor.py`
- Modify: `modules/firewall.py`
- Modify: `modules/fail2ban.py`
- Modify: `modules/email.py`

**Step 1: Update each module's show_menu()**

For each module, modify the menu to conditionally show "Install" option.

**Example for webserver.py:**

Find the `show_menu()` function and update options:

```python
def show_menu():
    """Display the Webserver Management submenu."""
    while True:
        clear_screen()
        show_header()
        
        # Build dynamic options based on install status
        options = []
        
        if not is_installed("nginx"):
            options.append(("install", "1. Install Nginx"))
        
        options.extend([
            ("domains", "2. Manage Domains"),
            ("vhosts", "3. Virtual Hosts"),
            ("status", "4. Service Status"),
            ("restart", "5. Restart Nginx"),
            ("back", "← Back to Main Menu"),
        ])
        
        choice = show_submenu(title="Domain & Nginx", options=options)
        
        # ... rest of menu handling
```

**Apply similar pattern to all other modules.**

**Step 2: Commit**

```bash
git add modules/webserver.py modules/runtime.py modules/database.py \
       modules/supervisor.py modules/firewall.py modules/fail2ban.py modules/email.py
git commit -m "feat(modules): hide install options when component already installed"
```

---

## Task 7: Final verification

**Step 1: Verify syntax**

```bash
python3 -m py_compile modules/setup.py main.py
```

**Step 2: Verify imports**

```bash
python3 -c "from modules.setup import show_setup_wizard, is_first_run"
```

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat(setup): complete setup wizard implementation"
```

---

## Verification Checklist

After implementation:

1. [ ] `python3 -m py_compile modules/setup.py` - no errors
2. [ ] `python3 -m py_compile main.py` - no errors
3. [ ] First run detection works (`is_first_run()`)
4. [ ] Checkbox UI displays correctly
5. [ ] Component installation works
6. [ ] Module menus hide install options correctly

## Expected Behavior

- **Fresh VPS**: Wizard appears automatically, user selects components, installation proceeds
- **After setup**: Wizard doesn't appear, menus hide installed component install options
- **Skip setup**: User can press Escape or select nothing to skip
- **Partial install**: Failed components can be installed later via menu
