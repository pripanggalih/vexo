"""PHP extension management."""

import os
import re

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, run_command_realtime, is_installed, service_control, require_root
from modules.runtime.php.utils import (
    get_installed_php_versions, get_fpm_service_name, PHP_EXTENSIONS,
)


# PECL extensions with descriptions
PECL_EXTENSIONS = {
    "redis": "Redis client extension",
    "mongodb": "MongoDB driver",
    "swoole": "Coroutine-based async programming (Laravel Octane)",
    "xdebug": "Debugging and profiling",
    "apcu": "User cache (alternative to APC)",
    "imagick": "ImageMagick wrapper (may also be in apt)",
    "memcached": "Memcached client",
    "grpc": "gRPC client",
    "protobuf": "Protocol Buffers",
    "yaml": "YAML parser",
}


def show_extensions_menu():
    """Display Extension Management submenu."""
    options = [
        ("list", "1. List Extensions"),
        ("install", "2. Install Extension"),
        ("remove", "3. Remove Extension"),
        ("toggle", "4. Enable/Disable Extension"),
        ("pecl", "5. PECL Extensions"),
        ("info", "6. Extension Info"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "list": list_extensions,
        "install": install_extension,
        "remove": remove_extension,
        "toggle": toggle_extension,
        "pecl": pecl_extensions_menu,
        "info": show_extension_info,
    }
    
    run_menu_loop("Extension Management", options, handlers)


def list_extensions():
    """List all PHP extensions with status."""
    clear_screen()
    show_header()
    show_panel("PHP Extensions", title="Extension Management", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "List extensions for:", versions)
    if not version:
        return
    
    clear_screen()
    show_header()
    show_panel(f"PHP {version} Extensions", title="Extension Management", style="cyan")
    
    # Get loaded extensions
    result = run_command(f"php{version} -m 2>/dev/null", check=False, silent=True)
    loaded_extensions = set()
    if result.returncode == 0:
        for line in result.stdout.strip().split('\n'):
            ext = line.strip().lower()
            if ext and not ext.startswith('['):
                loaded_extensions.add(ext)
    
    columns = [
        {"name": "Extension", "style": "cyan"},
        {"name": "Installed", "justify": "center"},
        {"name": "Loaded", "justify": "center"},
    ]
    
    rows = []
    for ext in sorted(PHP_EXTENSIONS):
        if ext in ["cli", "fpm", "common"]:
            continue
        
        pkg = f"php{version}-{ext}"
        installed = is_installed(pkg)
        installed_str = "[green]✓[/green]" if installed else "[dim]○[/dim]"
        
        loaded = ext.lower() in loaded_extensions or ext in loaded_extensions
        loaded_str = "[green]✓[/green]" if loaded else "[dim]○[/dim]"
        
        rows.append([ext, installed_str, loaded_str])
    
    show_table(f"Total: {len(rows)} extensions", columns, rows, show_header=True)
    
    console.print()
    console.print(f"[dim]Loaded in PHP {version}: {len(loaded_extensions)} extensions[/dim]")
    
    press_enter_to_continue()


def install_extension():
    """Install a single PHP extension."""
    clear_screen()
    show_header()
    show_panel("Install Extension", title="Extension Management", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "Install extension for:", versions)
    if not version:
        return
    
    # Get not-installed extensions
    available = []
    for ext in PHP_EXTENSIONS:
        if ext in ["cli", "fpm", "common"]:
            continue
        pkg = f"php{version}-{ext}"
        if not is_installed(pkg):
            available.append(ext)
    
    if not available:
        show_info("All standard extensions are already installed.")
        console.print()
        console.print("[dim]Use 'PECL Extensions' for additional extensions.[/dim]")
        press_enter_to_continue()
        return
    
    # Allow custom input too
    available.append("(Enter custom extension name)")
    
    ext = select_from_list("Select Extension", "Install:", available)
    if not ext:
        return
    
    if ext == "(Enter custom extension name)":
        ext = text_input("Enter extension name (e.g., xsl, ldap):")
        if not ext:
            return
        ext = ext.strip().lower()
    
    pkg = f"php{version}-{ext}"
    
    if is_installed(pkg):
        show_info(f"{ext} is already installed.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print()
    returncode = run_command_realtime(f"apt install -y {pkg}", f"Installing {ext}...")
    
    if returncode == 0:
        show_success(f"Extension {ext} installed!")
        console.print()
        if confirm_action("Restart PHP-FPM to load extension?"):
            service_control(get_fpm_service_name(version), "restart")
            show_success("PHP-FPM restarted!")
    else:
        show_error(f"Failed to install {ext}.")
    
    press_enter_to_continue()


def remove_extension():
    """Remove a PHP extension."""
    clear_screen()
    show_header()
    show_panel("Remove Extension", title="Extension Management", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "Remove extension from:", versions)
    if not version:
        return
    
    # Get installed extensions
    installed = []
    for ext in PHP_EXTENSIONS:
        if ext in ["cli", "fpm", "common"]:
            continue
        pkg = f"php{version}-{ext}"
        if is_installed(pkg):
            installed.append(ext)
    
    if not installed:
        show_info("No removable extensions found.")
        press_enter_to_continue()
        return
    
    ext = select_from_list("Select Extension", "Remove:", installed)
    if not ext:
        return
    
    show_warning(f"This will remove php{version}-{ext}")
    if not confirm_action(f"Remove {ext} extension?"):
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    pkg = f"php{version}-{ext}"
    returncode = run_command_realtime(f"apt remove -y {pkg}", f"Removing {ext}...")
    
    if returncode == 0:
        show_success(f"Extension {ext} removed!")
        console.print()
        if confirm_action("Restart PHP-FPM?"):
            service_control(get_fpm_service_name(version), "restart")
    else:
        show_error(f"Failed to remove {ext}.")
    
    press_enter_to_continue()


def toggle_extension():
    """Enable or disable a PHP extension without removing."""
    clear_screen()
    show_header()
    show_panel("Enable/Disable Extension", title="Extension Management", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "Toggle extension for:", versions)
    if not version:
        return
    
    # Get installed extensions and their status
    result = run_command(f"php{version} -m 2>/dev/null", check=False, silent=True)
    loaded = set()
    if result.returncode == 0:
        for line in result.stdout.strip().split('\n'):
            ext = line.strip().lower()
            if ext and not ext.startswith('['):
                loaded.add(ext)
    
    # List installed extensions with status
    installed = []
    for ext in PHP_EXTENSIONS:
        if ext in ["cli", "fpm", "common"]:
            continue
        pkg = f"php{version}-{ext}"
        if is_installed(pkg):
            status = "enabled" if ext.lower() in loaded else "disabled"
            installed.append(f"{ext} ({status})")
    
    if not installed:
        show_info("No extensions installed.")
        press_enter_to_continue()
        return
    
    choice = select_from_list("Select Extension", "Toggle:", installed)
    if not choice:
        return
    
    ext = choice.split(" (")[0]
    current_status = "enabled" if "(enabled)" in choice else "disabled"
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if current_status == "enabled":
        # Disable extension
        result = run_command(f"phpdismod -v {version} {ext}", check=False, silent=True)
        if result.returncode == 0:
            show_success(f"Extension {ext} disabled!")
        else:
            show_error(f"Failed to disable {ext}.")
    else:
        # Enable extension
        result = run_command(f"phpenmod -v {version} {ext}", check=False, silent=True)
        if result.returncode == 0:
            show_success(f"Extension {ext} enabled!")
        else:
            show_error(f"Failed to enable {ext}.")
    
    console.print()
    if confirm_action("Restart PHP-FPM to apply changes?"):
        service_control(get_fpm_service_name(version), "restart")
        show_success("PHP-FPM restarted!")
    
    press_enter_to_continue()


def pecl_extensions_menu():
    """Install PECL extensions."""
    clear_screen()
    show_header()
    show_panel("PECL Extensions", title="Extension Management", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "Install PECL extension for:", versions)
    if not version:
        return
    
    # Check if pecl is available
    if not is_installed(f"php{version}-dev"):
        show_warning(f"php{version}-dev is required for PECL extensions.")
        if confirm_action(f"Install php{version}-dev?"):
            try:
                require_root()
            except PermissionError:
                press_enter_to_continue()
                return
            run_command_realtime(f"apt install -y php{version}-dev php-pear", "Installing...")
        else:
            press_enter_to_continue()
            return
    
    # Show available PECL extensions
    console.print("[bold]Available PECL Extensions:[/bold]")
    console.print()
    for ext, desc in PECL_EXTENSIONS.items():
        console.print(f"  • [cyan]{ext}[/cyan] - {desc}")
    console.print()
    
    ext_options = list(PECL_EXTENSIONS.keys()) + ["(Enter custom PECL extension)"]
    ext = select_from_list("Select Extension", "Install:", ext_options)
    if not ext:
        return
    
    if ext == "(Enter custom PECL extension)":
        ext = text_input("Enter PECL extension name:")
        if not ext:
            return
        ext = ext.strip().lower()
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print()
    console.print(f"[bold]Installing {ext} via PECL...[/bold]")
    console.print("[dim]This may take a few minutes...[/dim]")
    console.print()
    
    # Use pecl with specific PHP version
    returncode = run_command_realtime(
        f"pecl -d php_suffix={version} install {ext}",
        f"Installing {ext}..."
    )
    
    if returncode == 0:
        # Enable extension
        ini_dir = f"/etc/php/{version}/mods-available"
        ini_file = os.path.join(ini_dir, f"{ext}.ini")
        
        if not os.path.exists(ini_file):
            try:
                with open(ini_file, "w") as f:
                    f.write(f"extension={ext}.so\n")
                run_command(f"phpenmod -v {version} {ext}", check=False, silent=True)
            except Exception as e:
                show_warning(f"Extension installed but auto-enable failed: {e}")
        
        show_success(f"PECL extension {ext} installed!")
        console.print()
        if confirm_action("Restart PHP-FPM?"):
            service_control(get_fpm_service_name(version), "restart")
    else:
        show_error(f"Failed to install {ext}.")
        console.print("[dim]Check if extension is compatible with PHP {version}[/dim]")
    
    press_enter_to_continue()


def show_extension_info():
    """Show detailed information about an extension."""
    clear_screen()
    show_header()
    show_panel("Extension Info", title="Extension Management", style="cyan")
    
    versions = get_installed_php_versions()
    if not versions:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    version = select_from_list("Select PHP Version", "Show info for:", versions)
    if not version:
        return
    
    # Get loaded extensions
    result = run_command(f"php{version} -m 2>/dev/null", check=False, silent=True)
    loaded = []
    if result.returncode == 0:
        for line in result.stdout.strip().split('\n'):
            ext = line.strip()
            if ext and not ext.startswith('['):
                loaded.append(ext)
    
    if not loaded:
        show_info("No extensions loaded.")
        press_enter_to_continue()
        return
    
    ext = select_from_list("Select Extension", "Show info for:", sorted(loaded))
    if not ext:
        return
    
    clear_screen()
    show_header()
    show_panel(f"Extension: {ext}", title="Extension Management", style="cyan")
    
    # Get extension info using reflection
    php_code = f'''
$ext = new ReflectionExtension("{ext}");
echo "Version: " . ($ext->getVersion() ?: "N/A") . "\\n";
echo "INI Entries:\\n";
foreach ($ext->getINIEntries() as $k => $v) {{
    echo "  $k = $v\\n";
}}
'''
    
    result = run_command(f"php{version} -r '{php_code}' 2>/dev/null", check=False, silent=True)
    
    if result.returncode == 0:
        console.print(result.stdout)
    else:
        console.print(f"[dim]Could not get detailed info for {ext}[/dim]")
    
    # Check if it's loaded in different SAPIs
    console.print()
    console.print("[bold]SAPI Status:[/bold]")
    
    # CLI
    result = run_command(f"php{version} -m | grep -i '^{ext}$'", check=False, silent=True)
    cli_status = "[green]Loaded[/green]" if result.returncode == 0 else "[dim]Not loaded[/dim]"
    console.print(f"  CLI: {cli_status}")
    
    # FPM (check ini file)
    fpm_ini = f"/etc/php/{version}/fpm/conf.d"
    fpm_loaded = False
    if os.path.exists(fpm_ini):
        for f in os.listdir(fpm_ini):
            if ext.lower() in f.lower():
                fpm_loaded = True
                break
    fpm_status = "[green]Enabled[/green]" if fpm_loaded else "[dim]Not enabled[/dim]"
    console.print(f"  FPM: {fpm_status}")
    
    press_enter_to_continue()
