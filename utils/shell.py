"""Shell command utilities for vexo."""

import subprocess
import os

from ui.components import console
from utils.error_handler import handle_error


def run_command(command, capture_output=True, check=True, silent=False):
    """
    Execute a shell command and return the result.
    
    Args:
        command: Command string or list of arguments
        capture_output: If True, capture stdout/stderr
        check: If True, raise exception on non-zero exit
        silent: If True, don't print errors
    
    Returns:
        subprocess.CompletedProcess object with:
        - returncode: Exit code (0 = success)
        - stdout: Command output (if capture_output=True)
        - stderr: Error output (if capture_output=True)
    
    Raises:
        subprocess.CalledProcessError: If check=True and command fails
    """
    try:
        if isinstance(command, str):
            result = subprocess.run(
                command,
                shell=True,
                capture_output=capture_output,
                text=True,
                check=check,
            )
        else:
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                check=check,
            )
        return result
    
    except subprocess.CalledProcessError as e:
        if not silent:
            handle_error("E1006", f"Command failed: {command}", details=e.stderr.strip() if e.stderr else None)
        raise
    
    except FileNotFoundError:
        if not silent:
            handle_error("E1004", f"Command not found: {command}")
        raise


def run_command_with_progress(command, description="Processing..."):
    """
    Execute a shell command with a spinner/progress indicator.
    
    Args:
        command: Command string or list of arguments
        description: Text to show while command runs
    
    Returns:
        subprocess.CompletedProcess object
    """
    from ui.components import show_spinner
    
    with show_spinner(description):
        result = run_command(command, check=False, silent=True)
    
    return result


def run_command_realtime(command, description=""):
    """
    Execute a shell command and stream output in realtime.
    
    Args:
        command: Command string
        description: Optional description to print before running
    
    Returns:
        int: Return code of the command
    """
    if description:
        console.print(f"[cyan]→[/cyan] {description}")
        console.print()
    
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    
    for line in process.stdout:
        console.print(f"[dim]{line.rstrip()}[/dim]")
    
    process.wait()
    return process.returncode


def is_installed(package):
    """
    Check if a package is installed via dpkg.
    
    Args:
        package: Package name (e.g., "nginx", "php8.2-fpm")
    
    Returns:
        bool: True if package is installed
    """
    try:
        result = run_command(
            f"dpkg -l {package} 2>/dev/null | grep -q '^ii'",
            check=False,
            silent=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def is_command_available(command):
    """
    Check if a command is available in PATH.
    
    Args:
        command: Command name (e.g., "git", "curl")
    
    Returns:
        bool: True if command is available
    """
    try:
        result = run_command(f"which {command}", check=False, silent=True)
        return result.returncode == 0
    except Exception:
        return False


def is_service_running(service):
    """
    Check if a systemd service is running.
    
    Args:
        service: Service name (e.g., "nginx", "mysql", "php8.2-fpm")
    
    Returns:
        bool: True if service is active/running
    """
    try:
        result = run_command(
            f"systemctl is-active {service}",
            check=False,
            silent=True,
        )
        return result.stdout.strip() == "active"
    except Exception:
        return False


def is_service_enabled(service):
    """
    Check if a systemd service is enabled (starts on boot).
    
    Args:
        service: Service name
    
    Returns:
        bool: True if service is enabled
    """
    try:
        result = run_command(
            f"systemctl is-enabled {service}",
            check=False,
            silent=True,
        )
        return result.stdout.strip() == "enabled"
    except Exception:
        return False


def service_control(service, action):
    """
    Control a systemd service (start, stop, restart, reload, enable, disable).
    
    Args:
        service: Service name
        action: One of "start", "stop", "restart", "reload", "enable", "disable"
    
    Returns:
        bool: True if action succeeded
    """
    valid_actions = ["start", "stop", "restart", "reload", "enable", "disable"]
    if action not in valid_actions:
        handle_error("E1005", f"Invalid action: {action}", details=f"Must be one of: {valid_actions}")
        return False
    
    try:
        run_command(f"systemctl {action} {service}", silent=False)
        return True
    except subprocess.CalledProcessError:
        return False


def check_root():
    """
    Check if running as root/sudo.
    
    Returns:
        bool: True if running as root
    """
    return os.geteuid() == 0


def require_root():
    """
    Require root privileges. Exit if not root.
    
    Raises:
        PermissionError: If not running as root
    """
    if not check_root():
        handle_error("E1001", "This operation requires root privileges", suggestions=["Run with: sudo vexo"])
        raise PermissionError("Root privileges required")


def get_os_info():
    """
    Get basic OS information.
    
    Returns:
        dict with keys: name, version, codename, arch
    """
    info = {
        "name": "Unknown",
        "version": "Unknown",
        "codename": "Unknown",
        "arch": "Unknown",
    }
    
    try:
        result = run_command("cat /etc/os-release", check=False, silent=True)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.startswith("NAME="):
                    info["name"] = line.split("=")[1].strip('"')
                elif line.startswith("VERSION_ID="):
                    info["version"] = line.split("=")[1].strip('"')
                elif line.startswith("VERSION_CODENAME="):
                    info["codename"] = line.split("=")[1].strip('"')
        
        result = run_command("uname -m", check=False, silent=True)
        if result.returncode == 0:
            info["arch"] = result.stdout.strip()
    except Exception:
        pass
    
    return info


def get_hostname():
    """Get the system hostname."""
    try:
        result = run_command("hostname", check=False, silent=True)
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def get_ip_address():
    """Get the primary IP address."""
    try:
        result = run_command(
            "hostname -I | awk '{print $1}'",
            check=False,
            silent=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return "unknown"
    except Exception:
        return "unknown"


def get_service_status(package_name, service_name=None):
    """
    Get formatted status string for a service.
    
    Args:
        package_name: Package name to check installation
        service_name: Service name to check running state (defaults to package_name)
    
    Returns:
        tuple: (status_string, is_installed, is_running)
        
    Example:
        status, installed, running = get_service_status("nginx")
        # status = "[green]Running[/green]" or "[red]Stopped[/red]" or "[dim]Not installed[/dim]"
    """
    if service_name is None:
        service_name = package_name
    
    if not is_installed(package_name):
        return "[dim]Not installed[/dim]", False, False
    
    if is_service_running(service_name):
        return "[green]Running[/green]", True, True
    else:
        return "[red]Stopped[/red]", True, False


def run_apt_with_progress(packages, step_info="Installing"):
    """
    Run apt install with live progress bar showing download/unpack/setup phases.
    
    Args:
        packages: List of package names to install
        step_info: Header text (e.g., "[2/9] PHP 8.3")
    
    Returns:
        bool: True if installation successful, False otherwise
    """
    import re
    from rich.live import Live
    from rich.text import Text
    from rich.console import Group
    
    if not packages:
        return True
    
    total_packages = len(packages)
    packages_str = " ".join(packages)
    
    # Track progress
    processed = 0
    current_status = "Preparing..."
    current_phase = ""
    
    # Regex patterns for apt output
    patterns = {
        "download": re.compile(r"Get:\d+.*?(\S+)\s+\S+\s+\S+\s+\[([^\]]+)\]"),
        "unpack": re.compile(r"Unpacking\s+(\S+)"),
        "setup": re.compile(r"Setting up\s+(\S+)"),
    }
    
    # Track which packages we've seen to count progress
    seen_packages = set()
    
    def make_display():
        """Generate the display content."""
        progress_pct = (processed / total_packages * 100) if total_packages > 0 else 0
        bar_width = 40
        filled = int(bar_width * processed / total_packages) if total_packages > 0 else 0
        bar = "█" * filled + "░" * (bar_width - filled)
        
        lines = []
        lines.append(Text(step_info, style="bold"))
        lines.append(Text(f"[{bar}] {progress_pct:.0f}% ({processed}/{total_packages} packages)", style="cyan"))
        if current_status:
            lines.append(Text(f"     {current_phase} {current_status}", style="dim"))
        
        return Group(*lines)
    
    cmd = f"DEBIAN_FRONTEND=noninteractive apt-get install -y {packages_str}"
    
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"},
    )
    
    with Live(make_display(), refresh_per_second=10, console=console) as live:
        for line in process.stdout:
            line = line.strip()
            
            # Check download phase
            match = patterns["download"].search(line)
            if match:
                pkg_name = match.group(1).split(":")[0]
                size = match.group(2)
                current_phase = "↓"
                current_status = f"Downloading {pkg_name} ({size})"
                live.update(make_display())
                continue
            
            # Check unpack phase
            match = patterns["unpack"].search(line)
            if match:
                pkg_name = match.group(1).split(":")[0]
                current_phase = "⚙"
                current_status = f"Unpacking {pkg_name}..."
                live.update(make_display())
                continue
            
            # Check setup phase
            match = patterns["setup"].search(line)
            if match:
                pkg_name = match.group(1).split(":")[0]
                if pkg_name not in seen_packages:
                    seen_packages.add(pkg_name)
                    for req_pkg in packages:
                        if pkg_name.startswith(req_pkg.split("-")[0]):
                            processed = min(processed + 1, total_packages)
                            break
                current_phase = "✦"
                current_status = f"Setting up {pkg_name}..."
                live.update(make_display())
                continue
        
        # Final update
        processed = total_packages
        current_phase = "✓"
        current_status = "Complete"
        live.update(make_display())
    
    process.wait()
    return process.returncode == 0


def run_apt_update_with_progress():
    """
    Run apt update with live progress indicator.
    
    Returns:
        bool: True if successful
    """
    import re
    from rich.live import Live
    from rich.text import Text
    from rich.console import Group
    
    current_status = "Updating package lists..."
    repo_count = 0
    
    def make_display():
        lines = []
        lines.append(Text("Updating package lists", style="bold"))
        lines.append(Text(f"     ↓ {current_status}", style="dim"))
        if repo_count > 0:
            lines.append(Text(f"     ({repo_count} repositories)", style="dim"))
        return Group(*lines)
    
    pattern = re.compile(r"(Get|Hit|Ign):\d+\s+(\S+)")
    
    process = subprocess.Popen(
        "apt-get update",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    
    with Live(make_display(), refresh_per_second=10, console=console) as live:
        for line in process.stdout:
            line = line.strip()
            match = pattern.search(line)
            if match:
                url = match.group(2)
                if len(url) > 50:
                    url = url[:47] + "..."
                current_status = f"{url}"
                repo_count += 1
                live.update(make_display())
        
        current_status = "Complete"
        live.update(make_display())
    
    process.wait()
    return process.returncode == 0
