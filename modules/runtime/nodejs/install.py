"""Node.js installation and version management."""

import os

from config import NVM_DIR, NVM_INSTALL_URL
from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, select_from_list, text_input, run_menu_loop
from utils.shell import run_command_with_progress
from utils.error_handler import handle_error
from modules.runtime.nodejs.utils import (
    is_nvm_installed, get_nvm_version, run_with_nvm, run_with_nvm_realtime,
    get_installed_nodejs_versions, get_current_nodejs_version, get_default_nodejs_version,
)


def install_nvm_interactive():
    """Interactive prompt to install or update NVM."""
    clear_screen()
    show_header()
    show_panel("Install/Update NVM", title="Node.js Runtime", style="cyan")
    
    if is_nvm_installed():
        nvm_version = get_nvm_version()
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
        handle_error("E3003", "Failed to install NVM.")
    
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
        handle_error("E3003", "Failed to download/install NVM")
        return False
    
    if is_nvm_installed():
        show_success("NVM installed!")
        return True
    else:
        show_warning("NVM script ran but installation could not be verified")
        return True


def install_nodejs_interactive():
    """Interactive prompt to install a Node.js version."""
    clear_screen()
    show_header()
    show_panel("Install Node.js", title="Node.js Runtime", style="cyan")
    
    if not is_nvm_installed():
        handle_error("E3003", "NVM is not installed. Please install NVM first.")
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
        node_ver = get_current_nodejs_version()
        if node_ver:
            console.print(f"[dim]Installed: {node_ver}[/dim]")
    else:
        handle_error("E3003", "Failed to install Node.js")
    
    press_enter_to_continue()


def install_nodejs(version):
    """
    Install a specific Node.js version via NVM.
    
    Args:
        version: Version string (e.g., "20", "18.19.0", "--lts", "node")
    
    Returns:
        bool: True if successful
    """
    if not is_nvm_installed():
        handle_error("E3003", "NVM is not installed")
        return False
    
    show_info(f"Installing Node.js {version}...")
    
    returncode = run_with_nvm_realtime(
        f"nvm install {version}",
        f"Installing Node.js {version}..."
    )
    
    return returncode == 0


def switch_nodejs_interactive():
    """Interactive prompt to switch Node.js version."""
    clear_screen()
    show_header()
    show_panel("Switch Node.js Version", title="Node.js Runtime", style="cyan")
    
    if not is_nvm_installed():
        handle_error("E3003", "NVM is not installed.")
        press_enter_to_continue()
        return
    
    installed = get_installed_nodejs_versions()
    
    if not installed:
        handle_error("E3003", "No Node.js versions installed.")
        press_enter_to_continue()
        return
    
    if len(installed) < 2:
        show_info("Only one Node.js version installed. Nothing to switch.")
        press_enter_to_continue()
        return
    
    current = get_current_nodejs_version()
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
        
        new_ver = get_current_nodejs_version()
        if new_ver:
            console.print(f"[dim]Now using: {new_ver}[/dim]")
    else:
        handle_error("E3003", f"Failed to switch to Node.js {version}")
    
    press_enter_to_continue()


def switch_nodejs_version(version):
    """
    Switch to a specific Node.js version and set as default.
    
    Args:
        version: Version string (e.g., "v20.10.0", "20.10.0")
    
    Returns:
        bool: True if successful
    """
    if not is_nvm_installed():
        return False
    
    version_clean = version.lstrip('v')
    
    show_info(f"Switching to Node.js {version}...")
    
    result = run_with_nvm(f"nvm use {version_clean}")
    if result is None or result.returncode != 0:
        return False
    
    result = run_with_nvm(f"nvm alias default {version_clean}")
    if result is None or result.returncode != 0:
        show_warning("Switched version but failed to set as default")
    
    return True


def list_nodejs_versions():
    """Display a table of installed Node.js versions."""
    clear_screen()
    show_header()
    show_panel("Installed Node.js Versions", title="Node.js Runtime", style="cyan")
    
    if not is_nvm_installed():
        handle_error("E3003", "NVM is not installed.")
        console.print()
        console.print("[dim]Use 'Install/Update NVM' first.[/dim]")
        press_enter_to_continue()
        return
    
    installed = get_installed_nodejs_versions()
    
    if not installed:
        show_info("No Node.js versions installed.")
        console.print()
        console.print("[dim]Use 'Install Node.js Version' to install.[/dim]")
        press_enter_to_continue()
        return
    
    current = get_current_nodejs_version()
    default = get_default_nodejs_version()
    
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


def _get_npm_version_for_node(node_version):
    """Get npm version for a specific Node.js version."""
    version_clean = node_version.lstrip('v')
    result = run_with_nvm(f"nvm exec {version_clean} npm --version")
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None


def show_nodejs_info():
    """Display current Node.js and npm information."""
    clear_screen()
    show_header()
    show_panel("Node.js Information", title="Node.js Runtime", style="cyan")
    
    if not is_nvm_installed():
        handle_error("E3003", "NVM is not installed.")
        press_enter_to_continue()
        return
    
    nvm_version = get_nvm_version()
    console.print(f"[bold]NVM Version:[/bold] {nvm_version or 'Unknown'}")
    console.print()
    
    node_version = get_current_nodejs_version()
    if node_version:
        console.print(f"[bold]Node.js Version:[/bold] {node_version}")
        
        npm_version = run_with_nvm("npm --version")
        if npm_version and npm_version.returncode == 0:
            console.print(f"[bold]npm Version:[/bold] {npm_version.stdout.strip()}")
        
        npx_version = run_with_nvm("npx --version")
        if npx_version and npx_version.returncode == 0:
            console.print(f"[bold]npx Version:[/bold] {npx_version.stdout.strip()}")
        
        console.print()
        
        node_path = run_with_nvm("which node")
        if node_path and node_path.returncode == 0:
            console.print(f"[bold]Node Path:[/bold] {node_path.stdout.strip()}")
        
        npm_path = run_with_nvm("which npm")
        if npm_path and npm_path.returncode == 0:
            console.print(f"[bold]npm Path:[/bold] {npm_path.stdout.strip()}")
        
        console.print()
        
        default = get_default_nodejs_version()
        if default:
            console.print(f"[bold]Default Version:[/bold] {default}")
        
        console.print()
        
        result = run_with_nvm("npm config get prefix")
        if result and result.returncode == 0:
            console.print(f"[bold]npm Prefix:[/bold] {result.stdout.strip()}")
        
        result = run_with_nvm("npm root -g")
        if result and result.returncode == 0:
            console.print(f"[bold]Global Modules:[/bold] {result.stdout.strip()}")
    else:
        show_warning("No Node.js version is currently active.")
        console.print()
        console.print("[dim]Install Node.js first with 'Install Node.js Version'[/dim]")
    
    press_enter_to_continue()
