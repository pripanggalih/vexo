"""Shell command utilities for vexo."""

import subprocess
import os

from ui.components import console, show_error


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
            show_error(f"Command failed: {command}")
            if e.stderr:
                console.print(f"[dim]{e.stderr.strip()}[/dim]")
        raise
    
    except FileNotFoundError:
        if not silent:
            show_error(f"Command not found: {command}")
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
        show_error(f"Invalid action: {action}. Must be one of: {valid_actions}")
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
        show_error("This operation requires root privileges.")
        console.print("[dim]Run with: sudo python3 main.py[/dim]")
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
