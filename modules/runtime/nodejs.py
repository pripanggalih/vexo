"""Node.js Runtime management module for vexo-cli."""

import os

from config import NVM_DIR, NVM_INSTALL_URL
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
from ui.menu import confirm_action, select_from_list, run_menu_loop, text_input
from utils.shell import run_command, run_command_with_progress, run_command_realtime


def show_nodejs_menu():
    """Display the Node.js Runtime submenu."""
    def get_status():
        current_node = _get_current_nodejs_version()
        if current_node:
            return f"Current Node.js: {current_node}"
        return "Node.js: Not installed"
    
    def get_options():
        options = []
        current_node = _get_current_nodejs_version()
        if _is_nvm_installed() or current_node:
            options.extend([
                ("list", "1. List Node.js Versions"),
                ("install", "2. Install Node.js Version"),
                ("switch", "3. Switch Node.js Version"),
                ("info", "4. Node.js Info"),
                ("nvm", "5. Install/Update NVM"),
            ])
        else:
            options.append(("nvm", "1. Install NVM"))
        options.append(("back", "← Back to Main Menu"))
        return options
    
    handlers = {
        "list": list_nodejs_versions,
        "install": install_nodejs_interactive,
        "switch": switch_nodejs_interactive,
        "info": show_nodejs_info,
        "nvm": install_nvm_interactive,
    }
    
    run_menu_loop("Node.js Runtime Management", get_options, handlers, get_status)


def install_nvm_interactive():
    """Interactive prompt to install or update NVM."""
    clear_screen()
    show_header()
    show_panel("Install/Update NVM", title="Node.js Runtime", style="cyan")
    
    if _is_nvm_installed():
        nvm_version = _get_nvm_version()
        console.print(f"[dim]Current NVM: {nvm_version}[/dim]")
        console.print()
        if not confirm_action("NVM is already installed. Reinstall/update?"):
            press_enter_to_continue()
            return
    
    success = install_nvm()
    
    if success:
        show_success("NVM installed successfully!")
        console.print()
        console.print("[dim]Note: You may need to restart your terminal or run:[/dim]")
        console.print("[dim]  source ~/.bashrc[/dim]")
    else:
        show_error("Failed to install NVM.")
    
    press_enter_to_continue()


def install_nvm():
    """
    Install NVM (Node Version Manager) via curl script.
    
    Returns:
        bool: True if successful
    """
    show_info("Installing NVM...")
    
    result = run_command_with_progress(
        f"curl -o- {NVM_INSTALL_URL} | bash",
        "Downloading and installing NVM..."
    )
    
    if result.returncode != 0:
        show_error("Failed to download/install NVM")
        return False
    
    if _is_nvm_installed():
        show_success("NVM installed!")
        return True
    else:
        show_warning("NVM script ran but installation could not be verified")
        return True


def _is_nvm_installed():
    """Check if NVM is installed."""
    nvm_script = os.path.join(NVM_DIR, "nvm.sh")
    return os.path.exists(nvm_script)


def _get_nvm_version():
    """Get installed NVM version."""
    result = _run_with_nvm("nvm --version")
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None


def _run_with_nvm(command):
    """
    Run a command with NVM sourced.
    
    Args:
        command: Command to run after sourcing NVM
    
    Returns:
        CompletedProcess or None if NVM not installed
    """
    nvm_script = os.path.join(NVM_DIR, "nvm.sh")
    if not os.path.exists(nvm_script):
        return None
    
    full_command = f'bash -c "source {nvm_script} && {command}"'
    return run_command(full_command, check=False, silent=True)


def install_nodejs_interactive():
    """Interactive prompt to install a Node.js version."""
    clear_screen()
    show_header()
    show_panel("Install Node.js", title="Node.js Runtime", style="cyan")
    
    if not _is_nvm_installed():
        show_error("NVM is not installed. Please install NVM first.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Common options:[/bold]")
    console.print()
    console.print("  • [cyan]lts[/cyan]     - Latest LTS version (recommended)")
    console.print("  • [cyan]latest[/cyan]  - Latest current version")
    console.print("  • [cyan]20[/cyan]      - Latest Node.js 20.x")
    console.print("  • [cyan]18[/cyan]      - Latest Node.js 18.x")
    console.print("  • [cyan]20.10.0[/cyan] - Specific version")
    console.print()
    
    version = text_input(
        title="Install Node.js",
        message="Enter version to install (e.g., lts, 20, 18.19.0):",
        default="lts"
    )
    
    if not version:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    version = version.strip().lower()
    
    if version == "lts":
        version = "--lts"
    elif version == "latest":
        version = "node"
    
    success = install_nodejs(version)
    
    if success:
        show_success("Node.js installed successfully!")
        node_ver = _get_current_nodejs_version()
        if node_ver:
            console.print(f"[dim]Installed: {node_ver}[/dim]")
    else:
        show_error("Failed to install Node.js")
    
    press_enter_to_continue()


def install_nodejs(version):
    """
    Install a specific Node.js version via NVM.
    
    Args:
        version: Version string (e.g., "20", "18.19.0", "--lts", "node")
    
    Returns:
        bool: True if successful
    """
    if not _is_nvm_installed():
        show_error("NVM is not installed")
        return False
    
    show_info(f"Installing Node.js {version}...")
    
    nvm_script = os.path.join(NVM_DIR, "nvm.sh")
    
    returncode = run_command_realtime(
        f'bash -c "source {nvm_script} && nvm install {version}"',
        f"Installing Node.js {version}..."
    )
    
    return returncode == 0


def switch_nodejs_interactive():
    """Interactive prompt to switch Node.js version."""
    clear_screen()
    show_header()
    show_panel("Switch Node.js Version", title="Node.js Runtime", style="cyan")
    
    if not _is_nvm_installed():
        show_error("NVM is not installed.")
        press_enter_to_continue()
        return
    
    installed = _get_installed_nodejs_versions()
    
    if not installed:
        show_error("No Node.js versions installed.")
        press_enter_to_continue()
        return
    
    if len(installed) < 2:
        show_info("Only one Node.js version installed. Nothing to switch.")
        press_enter_to_continue()
        return
    
    current = _get_current_nodejs_version()
    console.print(f"[dim]Current: {current}[/dim]")
    console.print()
    
    version = select_from_list(
        title="Switch Node.js",
        message="Select Node.js version to use:",
        options=installed
    )
    
    if not version:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    success = switch_nodejs_version(version)
    
    if success:
        show_success(f"Switched to Node.js {version}!")
        
        new_ver = _get_current_nodejs_version()
        if new_ver:
            console.print(f"[dim]Now using: {new_ver}[/dim]")
    else:
        show_error(f"Failed to switch to Node.js {version}")
    
    press_enter_to_continue()


def switch_nodejs_version(version):
    """
    Switch to a specific Node.js version and set as default.
    
    Args:
        version: Version string (e.g., "v20.10.0", "20.10.0")
    
    Returns:
        bool: True if successful
    """
    if not _is_nvm_installed():
        return False
    
    version_clean = version.lstrip('v')
    
    show_info(f"Switching to Node.js {version}...")
    
    result = _run_with_nvm(f"nvm use {version_clean}")
    if result is None or result.returncode != 0:
        return False
    
    result = _run_with_nvm(f"nvm alias default {version_clean}")
    if result is None or result.returncode != 0:
        show_warning("Switched version but failed to set as default")
    
    return True


def list_nodejs_versions():
    """Display a table of installed Node.js versions."""
    clear_screen()
    show_header()
    show_panel("Installed Node.js Versions", title="Node.js Runtime", style="cyan")
    
    if not _is_nvm_installed():
        show_error("NVM is not installed.")
        console.print()
        console.print("[dim]Use 'Install/Update NVM' first.[/dim]")
        press_enter_to_continue()
        return
    
    installed = _get_installed_nodejs_versions()
    
    if not installed:
        show_info("No Node.js versions installed.")
        console.print()
        console.print("[dim]Use 'Install Node.js Version' to install.[/dim]")
        press_enter_to_continue()
        return
    
    current = _get_current_nodejs_version()
    default = _get_default_nodejs_version()
    
    columns = [
        {"name": "Version", "style": "cyan"},
        {"name": "Current", "justify": "center"},
        {"name": "Default", "justify": "center"},
        {"name": "npm Version"},
    ]
    
    rows = []
    for version in installed:
        is_current = "[green]✓[/green]" if version == current else ""
        is_default = "[green]✓[/green]" if version == default else ""
        
        npm_ver = _get_npm_version_for_node(version)
        npm_display = npm_ver if npm_ver else "[dim]N/A[/dim]"
        
        rows.append([version, is_current, is_default, npm_display])
    
    show_table(f"Total: {len(installed)} version(s)", columns, rows)
    
    press_enter_to_continue()


def _get_installed_nodejs_versions():
    """Get list of installed Node.js versions via NVM."""
    result = _run_with_nvm("nvm ls --no-colors")
    if result is None or result.returncode != 0:
        return []
    
    versions = []
    for line in result.stdout.strip().split('\n'):
        line = line.strip()
        line = line.replace('->', '').replace('*', '').strip()
        
        if line.startswith('v') and '.' in line:
            version = line.split()[0] if ' ' in line else line
            version = version.strip()
            if version and version not in versions:
                versions.append(version)
    
    return sorted(versions, key=lambda v: [int(x) for x in v.lstrip('v').split('.')], reverse=True)


def _get_current_nodejs_version():
    """Get the current active Node.js version."""
    result = _run_with_nvm("node --version")
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None


def _get_default_nodejs_version():
    """Get the default Node.js version set in NVM."""
    result = _run_with_nvm("nvm alias default")
    if result and result.returncode == 0:
        output = result.stdout.strip()
        if '->' in output:
            version = output.split('->')[-1].strip()
            version = version.replace('*', '').strip()
            if version.startswith('v'):
                return version
    return None


def _get_npm_version_for_node(node_version):
    """Get npm version for a specific Node.js version."""
    version_clean = node_version.lstrip('v')
    result = _run_with_nvm(f"nvm exec {version_clean} npm --version")
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None


def show_nodejs_info():
    """Display current Node.js and npm information."""
    clear_screen()
    show_header()
    show_panel("Node.js Information", title="Node.js Runtime", style="cyan")
    
    if not _is_nvm_installed():
        show_error("NVM is not installed.")
        press_enter_to_continue()
        return
    
    nvm_version = _get_nvm_version()
    console.print(f"[bold]NVM Version:[/bold] {nvm_version or 'Unknown'}")
    console.print()
    
    node_version = _get_current_nodejs_version()
    if node_version:
        console.print(f"[bold]Node.js Version:[/bold] {node_version}")
        
        npm_version = _run_with_nvm("npm --version")
        if npm_version and npm_version.returncode == 0:
            console.print(f"[bold]npm Version:[/bold] {npm_version.stdout.strip()}")
        
        npx_version = _run_with_nvm("npx --version")
        if npx_version and npx_version.returncode == 0:
            console.print(f"[bold]npx Version:[/bold] {npx_version.stdout.strip()}")
        
        console.print()
        
        node_path = _run_with_nvm("which node")
        if node_path and node_path.returncode == 0:
            console.print(f"[bold]Node Path:[/bold] {node_path.stdout.strip()}")
        
        npm_path = _run_with_nvm("which npm")
        if npm_path and npm_path.returncode == 0:
            console.print(f"[bold]npm Path:[/bold] {npm_path.stdout.strip()}")
        
        console.print()
        
        default = _get_default_nodejs_version()
        if default:
            console.print(f"[bold]Default Version:[/bold] {default}")
        
        console.print()
        
        result = _run_with_nvm("npm config get prefix")
        if result and result.returncode == 0:
            console.print(f"[bold]npm Prefix:[/bold] {result.stdout.strip()}")
        
        result = _run_with_nvm("npm root -g")
        if result and result.returncode == 0:
            console.print(f"[bold]Global Modules:[/bold] {result.stdout.strip()}")
    else:
        show_warning("No Node.js version is currently active.")
        console.print()
        console.print("[dim]Install Node.js first with 'Install Node.js Version'[/dim]")
    
    press_enter_to_continue()
