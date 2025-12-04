# Task 3.0: Implement Utility Functions - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement utility functions for shell command execution, system checks, and logging that all modules will use.

**Architecture:** Two files in `utils/` - `shell.py` for subprocess wrapper and system checks, `logger.py` for Rich-formatted console logging. All functions are stateless and can be imported by any module. Shell commands use subprocess with proper error handling and optional progress display.

**Tech Stack:** Python subprocess module, Rich (progress, console), os module for system checks

**Note:** Development only - no testing/running. Code will be tested by user on target environment.

---

## Task 3.1: Create utils/shell.py with run_command()

**Files:**
- Create: `utils/shell.py`

**Step 1: Create shell.py with run_command() function**

```python
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
    
    Example:
        result = run_command("ls -la")
        print(result.stdout)
        
        result = run_command(["apt", "install", "-y", "nginx"])
    """
    try:
        # Convert string to shell command
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
    
    except FileNotFoundError as e:
        if not silent:
            show_error(f"Command not found: {command}")
        raise
```

**Step 2: Commit**

```bash
git add utils/shell.py && git commit -m "feat(utils): add shell.py with run_command() function"
```

---

## Task 3.2: Add run_command_with_progress() to shell.py

**Files:**
- Modify: `utils/shell.py`

**Step 1: Add run_command_with_progress() function**

Append to `utils/shell.py`:

```python


def run_command_with_progress(command, description="Processing..."):
    """
    Execute a shell command with a spinner/progress indicator.
    
    Args:
        command: Command string or list of arguments
        description: Text to show while command runs
    
    Returns:
        subprocess.CompletedProcess object
    
    Example:
        result = run_command_with_progress(
            "apt update",
            "Updating package lists..."
        )
    """
    from ui.components import show_spinner
    
    with show_spinner(description):
        result = run_command(command, check=False, silent=True)
    
    return result


def run_command_realtime(command, description=""):
    """
    Execute a shell command and stream output in realtime.
    
    Useful for long-running commands where you want to see progress.
    
    Args:
        command: Command string
        description: Optional description to print before running
    
    Returns:
        int: Return code of the command
    
    Example:
        code = run_command_realtime("apt upgrade -y", "Upgrading packages...")
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
    
    # Stream output line by line
    for line in process.stdout:
        console.print(f"[dim]{line.rstrip()}[/dim]")
    
    process.wait()
    return process.returncode
```

**Step 2: Commit**

```bash
git add utils/shell.py && git commit -m "feat(utils): add run_command_with_progress() and run_command_realtime()"
```

---

## Task 3.3: Add is_installed() to shell.py

**Files:**
- Modify: `utils/shell.py`

**Step 1: Add is_installed() function**

Append to `utils/shell.py`:

```python


def is_installed(package):
    """
    Check if a package is installed via dpkg.
    
    Args:
        package: Package name (e.g., "nginx", "php8.2-fpm")
    
    Returns:
        bool: True if package is installed
    
    Example:
        if not is_installed("nginx"):
            run_command("apt install -y nginx")
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
    
    Example:
        if is_command_available("git"):
            run_command("git clone ...")
    """
    try:
        result = run_command(f"which {command}", check=False, silent=True)
        return result.returncode == 0
    except Exception:
        return False
```

**Step 2: Commit**

```bash
git add utils/shell.py && git commit -m "feat(utils): add is_installed() and is_command_available()"
```

---

## Task 3.4: Add is_service_running() to shell.py

**Files:**
- Modify: `utils/shell.py`

**Step 1: Add is_service_running() and service control functions**

Append to `utils/shell.py`:

```python


def is_service_running(service):
    """
    Check if a systemd service is running.
    
    Args:
        service: Service name (e.g., "nginx", "mysql", "php8.2-fpm")
    
    Returns:
        bool: True if service is active/running
    
    Example:
        if is_service_running("nginx"):
            print("Nginx is running")
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
    
    Example:
        service_control("nginx", "restart")
        service_control("php8.2-fpm", "reload")
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
```

**Step 2: Commit**

```bash
git add utils/shell.py && git commit -m "feat(utils): add service management functions"
```

---

## Task 3.5: Create utils/logger.py

**Files:**
- Create: `utils/logger.py`

**Step 1: Create logger.py with logging functions**

```python
"""Logging utilities for vexo."""

from datetime import datetime
from ui.components import console
from ui.styles import PRIMARY, SUCCESS, WARNING, ERROR, INFO


class Logger:
    """Simple logger with Rich formatting."""
    
    def __init__(self, name="vexo"):
        self.name = name
        self.show_timestamp = False
    
    def _format_message(self, level, message, color):
        """Format a log message with optional timestamp."""
        timestamp = ""
        if self.show_timestamp:
            timestamp = f"[dim]{datetime.now().strftime('%H:%M:%S')}[/dim] "
        
        return f"{timestamp}[{color}][{level}][/{color}] {message}"
    
    def info(self, message):
        """Log an info message."""
        console.print(self._format_message("INFO", message, INFO))
    
    def success(self, message):
        """Log a success message."""
        console.print(self._format_message("OK", message, SUCCESS))
    
    def warning(self, message):
        """Log a warning message."""
        console.print(self._format_message("WARN", message, WARNING))
    
    def error(self, message):
        """Log an error message."""
        console.print(self._format_message("ERR", message, ERROR))
    
    def debug(self, message):
        """Log a debug message (dimmed)."""
        console.print(f"[dim][DEBUG] {message}[/dim]")
    
    def step(self, message):
        """Log a step in a process."""
        console.print(f"[{PRIMARY}]→[/{PRIMARY}] {message}")
    
    def divider(self, char="-", length=40):
        """Print a divider line."""
        console.print(f"[dim]{char * length}[/dim]")


# Default logger instance
log = Logger()


def log_info(message):
    """Shortcut for log.info()"""
    log.info(message)


def log_success(message):
    """Shortcut for log.success()"""
    log.success(message)


def log_warning(message):
    """Shortcut for log.warning()"""
    log.warning(message)


def log_error(message):
    """Shortcut for log.error()"""
    log.error(message)


def log_debug(message):
    """Shortcut for log.debug()"""
    log.debug(message)


def log_step(message):
    """Shortcut for log.step()"""
    log.step(message)
```

**Step 2: Commit**

```bash
git add utils/logger.py && git commit -m "feat(utils): add logger.py with Rich-formatted logging"
```

---

## Task 3.6: Add check_root() to shell.py

**Files:**
- Modify: `utils/shell.py`

**Step 1: Add check_root() and other system checks**

Append to `utils/shell.py`:

```python


def check_root():
    """
    Check if running as root/sudo.
    
    Returns:
        bool: True if running as root
    
    Example:
        if not check_root():
            show_error("This operation requires root privileges")
            return
    """
    return os.geteuid() == 0


def require_root():
    """
    Require root privileges. Exit if not root.
    
    Use this at the start of functions that need root.
    
    Example:
        def install_nginx():
            require_root()
            run_command("apt install -y nginx")
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
    
    Example:
        info = get_os_info()
        print(f"Running on {info['name']} {info['version']}")
    """
    info = {
        "name": "Unknown",
        "version": "Unknown",
        "codename": "Unknown",
        "arch": "Unknown",
    }
    
    try:
        # Try to read /etc/os-release
        result = run_command("cat /etc/os-release", check=False, silent=True)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.startswith("NAME="):
                    info["name"] = line.split("=")[1].strip('"')
                elif line.startswith("VERSION_ID="):
                    info["version"] = line.split("=")[1].strip('"')
                elif line.startswith("VERSION_CODENAME="):
                    info["codename"] = line.split("=")[1].strip('"')
        
        # Get architecture
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
        # Try to get the IP used for outbound connections
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
```

**Step 2: Commit**

```bash
git add utils/shell.py && git commit -m "feat(utils): add system check functions (root, os info, hostname, ip)"
```

---

## Task 3.7: Update utils/__init__.py exports

**Files:**
- Modify: `utils/__init__.py`

**Step 1: Update __init__.py with all exports**

```python
"""Utility functions for vexo - shell commands, logging."""

from utils.shell import (
    run_command,
    run_command_with_progress,
    run_command_realtime,
    is_installed,
    is_command_available,
    is_service_running,
    is_service_enabled,
    service_control,
    check_root,
    require_root,
    get_os_info,
    get_hostname,
    get_ip_address,
)

from utils.logger import (
    Logger,
    log,
    log_info,
    log_success,
    log_warning,
    log_error,
    log_debug,
    log_step,
)
```

**Step 2: Commit**

```bash
git add utils/__init__.py && git commit -m "feat(utils): update __init__.py with all exports"
```

---

## Task 3.8: Update task list

Mark Task 3.0 and all sub-tasks as completed in `tasks/tasks-vexo.md`

---

## Summary

After completing this plan:

```
utils/
├── __init__.py      ✅ Exports all public functions
├── shell.py         ✅ Command execution, package/service checks, system info
└── logger.py        ✅ Rich-formatted logging
```

**Functions available after Task 3:**

| File | Functions |
|------|-----------|
| `shell.py` | `run_command()`, `run_command_with_progress()`, `run_command_realtime()`, `is_installed()`, `is_command_available()`, `is_service_running()`, `is_service_enabled()`, `service_control()`, `check_root()`, `require_root()`, `get_os_info()`, `get_hostname()`, `get_ip_address()` |
| `logger.py` | `Logger` class, `log` instance, `log_info()`, `log_success()`, `log_warning()`, `log_error()`, `log_debug()`, `log_step()` |
