"""Global npm packages management."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from modules.runtime.nodejs.utils import run_with_nvm, run_with_nvm_realtime


# Popular global packages
POPULAR_PACKAGES = {
    "pm2": "Production process manager",
    "yarn": "Alternative package manager",
    "pnpm": "Fast, disk space efficient package manager",
    "nodemon": "Auto-restart on file changes",
    "typescript": "TypeScript compiler",
    "ts-node": "TypeScript execution engine",
    "eslint": "JavaScript linter",
    "prettier": "Code formatter",
    "webpack": "Module bundler",
    "vite": "Next generation frontend tooling",
    "serve": "Static file server",
    "http-server": "Simple HTTP server",
    "npm-check-updates": "Update package.json dependencies",
    "npx": "Package runner (usually included)",
}


def show_packages_menu():
    """Display Global Packages submenu."""
    def get_status():
        result = run_with_nvm("npm -g ls --depth=0 2>/dev/null | wc -l")
        if result and result.returncode == 0:
            count = int(result.stdout.strip()) - 1  # Subtract header line
            return f"Global packages: {max(0, count)}"
        return "Global packages: ?"
    
    options = [
        ("list", "1. List Global Packages"),
        ("install", "2. Install Package"),
        ("update", "3. Update Packages"),
        ("remove", "4. Remove Package"),
        ("outdated", "5. Check Outdated"),
        ("cache", "6. Clean npm Cache"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "list": list_global_packages,
        "install": install_global_package,
        "update": update_global_packages,
        "remove": remove_global_package,
        "outdated": check_outdated,
        "cache": clean_npm_cache,
    }
    
    run_menu_loop("Global Packages", options, handlers, get_status)


def list_global_packages():
    """List all globally installed packages."""
    clear_screen()
    show_header()
    show_panel("Global Packages", title="npm Packages", style="cyan")
    
    result = run_with_nvm("npm -g ls --depth=0 --json")
    
    if result is None or result.returncode != 0:
        show_error("Failed to list packages.")
        press_enter_to_continue()
        return
    
    try:
        import json
        data = json.loads(result.stdout)
        dependencies = data.get("dependencies", {})
    except Exception:
        show_error("Failed to parse package list.")
        press_enter_to_continue()
        return
    
    if not dependencies:
        show_info("No global packages installed.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Package", "style": "cyan"},
        {"name": "Version", "style": "white"},
        {"name": "Description"},
    ]
    
    rows = []
    for name, info in sorted(dependencies.items()):
        version = info.get("version", "?")
        desc = POPULAR_PACKAGES.get(name, "")
        rows.append([name, version, desc])
    
    show_table(f"Total: {len(rows)} package(s)", columns, rows, show_header=True)
    
    # Show global path
    result = run_with_nvm("npm root -g")
    if result and result.returncode == 0:
        console.print()
        console.print(f"[dim]Location: {result.stdout.strip()}[/dim]")
    
    press_enter_to_continue()


def install_global_package():
    """Install a global package."""
    clear_screen()
    show_header()
    show_panel("Install Global Package", title="npm Packages", style="cyan")
    
    console.print("[bold]Popular Packages:[/bold]")
    console.print()
    for name, desc in list(POPULAR_PACKAGES.items())[:10]:
        console.print(f"  • [cyan]{name}[/cyan] - {desc}")
    console.print()
    
    # Options
    options = list(POPULAR_PACKAGES.keys()) + ["(Enter custom package name)"]
    
    package = select_from_list("Select Package", "Install:", options)
    if not package:
        return
    
    if package == "(Enter custom package name)":
        package = text_input("Enter package name:")
        if not package:
            return
        package = package.strip()
    
    # Check if already installed
    result = run_with_nvm(f"npm -g ls {package} --depth=0 2>/dev/null")
    if result and result.returncode == 0 and package in result.stdout:
        show_info(f"{package} is already installed.")
        if not confirm_action("Reinstall?"):
            press_enter_to_continue()
            return
    
    console.print()
    returncode = run_with_nvm_realtime(f"npm install -g {package}", f"Installing {package}...")
    
    if returncode == 0:
        show_success(f"{package} installed successfully!")
    else:
        show_error(f"Failed to install {package}.")
    
    press_enter_to_continue()


def update_global_packages():
    """Update global packages."""
    clear_screen()
    show_header()
    show_panel("Update Global Packages", title="npm Packages", style="cyan")
    
    options = [
        "Update all packages",
        "Update specific package",
    ]
    
    choice = select_from_list("Action", "What to do?", options)
    if not choice:
        return
    
    if "all" in choice:
        show_warning("This will update all global packages.")
        if not confirm_action("Continue?"):
            press_enter_to_continue()
            return
        
        console.print()
        returncode = run_with_nvm_realtime("npm update -g", "Updating all packages...")
        
        if returncode == 0:
            show_success("All packages updated!")
        else:
            show_error("Some packages may have failed to update.")
    else:
        # Get installed packages
        packages = _get_global_packages()
        if not packages:
            show_info("No packages installed.")
            press_enter_to_continue()
            return
        
        package = select_from_list("Select Package", "Update:", packages)
        if not package:
            return
        
        console.print()
        returncode = run_with_nvm_realtime(f"npm update -g {package}", f"Updating {package}...")
        
        if returncode == 0:
            show_success(f"{package} updated!")
        else:
            show_error(f"Failed to update {package}.")
    
    press_enter_to_continue()


def remove_global_package():
    """Remove a global package."""
    clear_screen()
    show_header()
    show_panel("Remove Global Package", title="npm Packages", style="cyan")
    
    packages = _get_global_packages()
    
    if not packages:
        show_info("No packages installed.")
        press_enter_to_continue()
        return
    
    package = select_from_list("Select Package", "Remove:", packages)
    if not package:
        return
    
    if not confirm_action(f"Remove {package}?"):
        press_enter_to_continue()
        return
    
    console.print()
    returncode = run_with_nvm_realtime(f"npm uninstall -g {package}", f"Removing {package}...")
    
    if returncode == 0:
        show_success(f"{package} removed!")
    else:
        show_error(f"Failed to remove {package}.")
    
    press_enter_to_continue()


def check_outdated():
    """Check for outdated global packages."""
    clear_screen()
    show_header()
    show_panel("Outdated Packages", title="npm Packages", style="cyan")
    
    console.print("Checking for updates...")
    console.print()
    
    result = run_with_nvm("npm -g outdated --json")
    
    if result is None:
        show_error("Failed to check outdated packages.")
        press_enter_to_continue()
        return
    
    # npm outdated returns exit code 1 if there are outdated packages
    if not result.stdout.strip() or result.stdout.strip() == "{}":
        show_success("All packages are up to date!")
        press_enter_to_continue()
        return
    
    try:
        import json
        outdated = json.loads(result.stdout)
    except Exception:
        show_error("Failed to parse response.")
        press_enter_to_continue()
        return
    
    if not outdated:
        show_success("All packages are up to date!")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Package", "style": "cyan"},
        {"name": "Current", "style": "yellow"},
        {"name": "Wanted", "style": "white"},
        {"name": "Latest", "style": "green"},
    ]
    
    rows = []
    for name, info in sorted(outdated.items()):
        current = info.get("current", "?")
        wanted = info.get("wanted", "?")
        latest = info.get("latest", "?")
        rows.append([name, current, wanted, latest])
    
    show_table(f"{len(rows)} package(s) can be updated", columns, rows, show_header=True)
    
    console.print()
    if confirm_action("Update all outdated packages?"):
        console.print()
        returncode = run_with_nvm_realtime("npm update -g", "Updating...")
        if returncode == 0:
            show_success("Packages updated!")
    
    press_enter_to_continue()


def clean_npm_cache():
    """Clean npm cache."""
    clear_screen()
    show_header()
    show_panel("Clean npm Cache", title="npm Packages", style="cyan")
    
    # Show cache size
    result = run_with_nvm("npm cache ls 2>/dev/null | wc -l")
    
    console.print("[bold]npm Cache[/bold]")
    console.print()
    
    # Get cache folder
    result = run_with_nvm("npm config get cache")
    if result and result.returncode == 0:
        cache_path = result.stdout.strip()
        console.print(f"  Location: {cache_path}")
        
        # Get size
        import subprocess
        try:
            size_result = subprocess.run(
                f"du -sh {cache_path} 2>/dev/null | cut -f1",
                shell=True, capture_output=True, text=True
            )
            if size_result.returncode == 0:
                console.print(f"  Size: {size_result.stdout.strip()}")
        except Exception:
            pass
    
    console.print()
    
    if not confirm_action("Clean npm cache?"):
        press_enter_to_continue()
        return
    
    console.print()
    returncode = run_with_nvm_realtime("npm cache clean --force", "Cleaning cache...")
    
    if returncode == 0:
        show_success("npm cache cleaned!")
    else:
        show_error("Failed to clean cache.")
    
    press_enter_to_continue()


def _get_global_packages():
    """Get list of globally installed package names."""
    result = run_with_nvm("npm -g ls --depth=0 --json")
    
    if result is None or result.returncode != 0:
        return []
    
    try:
        import json
        data = json.loads(result.stdout)
        return sorted(data.get("dependencies", {}).keys())
    except Exception:
        return []
