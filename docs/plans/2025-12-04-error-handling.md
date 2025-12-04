# Error Handling System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement centralized error handling with user-friendly console messages, JSON file logging, auto-detection of common issues, and contextual recovery suggestions.

**Architecture:** Create `utils/error_handler.py` with VexoError exception class, error codes by module (E1xxx-E7xxx), auto-detection patterns for common issues, dual output (Rich console + JSON log file), and auto-cleanup of logs older than 7 days.

**Tech Stack:** Python 3.8+, Rich (console output), JSON (log format), logging module (rotation)

---

## Task 1: Create Error Handler Core

**Files:**
- Create: `utils/error_handler.py`

**Step 1: Create error codes and VexoError class**

```python
"""Centralized error handling for vexo.

Provides:
- VexoError exception class with error codes
- Dual logging: Rich console (user-friendly) + JSON file (debugging)
- Auto-detection of common issues with contextual suggestions
- Log rotation by date (keep 7 days)
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

# Log directory
LOG_DIR = Path("/var/log/vexo")

# Error codes by module
ERROR_CODES = {
    # E1xxx - SYSTEM
    "E1001": ("System", "Permission denied (need sudo)"),
    "E1002": ("System", "Network unreachable"),
    "E1003": ("System", "Disk full"),
    "E1004": ("System", "File not found"),
    "E1005": ("System", "Invalid configuration"),
    "E1006": ("System", "Service failed to start/stop"),
    
    # E2xxx - WEBSERVER (Nginx)
    "E2001": ("Webserver", "Nginx install failed"),
    "E2002": ("Webserver", "Config syntax error"),
    "E2003": ("Webserver", "Domain already exists"),
    "E2004": ("Webserver", "SSL certificate error"),
    "E2005": ("Webserver", "Port already in use"),
    
    # E3xxx - RUNTIME (PHP/Node)
    "E3001": ("Runtime", "PHP install failed"),
    "E3002": ("Runtime", "PHP extension not found"),
    "E3003": ("Runtime", "Node/NVM install failed"),
    "E3004": ("Runtime", "npm/composer error"),
    "E3005": ("Runtime", "Version not available"),
    
    # E4xxx - DATABASE
    "E4001": ("Database", "Database install failed"),
    "E4002": ("Database", "Connection refused"),
    "E4003": ("Database", "Authentication failed"),
    "E4004": ("Database", "Database already exists"),
    "E4005": ("Database", "Backup/restore failed"),
    
    # E5xxx - EMAIL
    "E5001": ("Email", "Postfix install failed"),
    "E5002": ("Email", "Domain config error"),
    "E5003": ("Email", "DKIM setup failed"),
    "E5004": ("Email", "Relay authentication failed"),
    "E5005": ("Email", "Mail delivery failed"),
    
    # E6xxx - SECURITY
    "E6001": ("Security", "UFW command failed"),
    "E6002": ("Security", "SSL/Certbot error"),
    "E6003": ("Security", "Fail2ban error"),
    "E6004": ("Security", "Invalid IP address"),
    "E6005": ("Security", "Rule already exists"),
    
    # E7xxx - PROCESS (Supervisor/Cron)
    "E7001": ("Process", "Supervisor install failed"),
    "E7002": ("Process", "Worker config error"),
    "E7003": ("Process", "Cron syntax invalid"),
    "E7004": ("Process", "Job already exists"),
    "E7005": ("Process", "Process not found"),
}

# Auto-detection patterns for common issues
KNOWN_ISSUES = {
    "apt_lock": {
        "patterns": ["Could not get lock", "dpkg lock", "E: Unable to acquire", "is another process using it"],
        "suggestions": [
            "Wait for other apt process to finish",
            "Run: sudo killall apt apt-get",
            "Run: sudo rm /var/lib/dpkg/lock-frontend",
        ]
    },
    "permission": {
        "patterns": ["Permission denied", "EACCES", "Operation not permitted", "must be run as root"],
        "suggestions": [
            "Run with sudo: sudo vexo",
            "Check file ownership: ls -la <path>",
        ]
    },
    "network": {
        "patterns": ["Connection refused", "Network unreachable", "Could not resolve", "Temporary failure in name resolution"],
        "suggestions": [
            "Check internet: ping -c 3 google.com",
            "Check DNS: cat /etc/resolv.conf",
            "Restart networking: sudo systemctl restart networking",
        ]
    },
    "disk_full": {
        "patterns": ["No space left", "Disk quota exceeded", "ENOSPC"],
        "suggestions": [
            "Check disk: df -h",
            "Clean apt cache: sudo apt clean",
            "Find large files: sudo du -sh /* 2>/dev/null | sort -hr | head -10",
        ]
    },
    "port_in_use": {
        "patterns": ["Address already in use", "bind: Address", "port is already allocated"],
        "suggestions": [
            "Find process using port: sudo lsof -i :<port>",
            "Or: sudo netstat -tlnp | grep <port>",
            "Kill process: sudo kill <pid>",
        ]
    },
    "service_failed": {
        "patterns": ["Failed to start", "Unit .* not found", "service failed", "Job failed"],
        "suggestions": [
            "Check service status: sudo systemctl status <service>",
            "View logs: sudo journalctl -u <service> -n 50",
            "Reload systemd: sudo systemctl daemon-reload",
        ]
    },
    "package_not_found": {
        "patterns": ["Unable to locate package", "has no installation candidate", "Package .* is not available"],
        "suggestions": [
            "Update package list: sudo apt update",
            "Check package name spelling",
            "Add required repository if needed",
        ]
    },
}


class VexoError(Exception):
    """Custom exception for vexo with error codes and suggestions."""
    
    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        module: Optional[str] = None,
    ):
        self.code = code
        self.message = message
        self.details = details
        self.suggestions = suggestions or []
        self.module = module or self._get_module_from_code(code)
        self.timestamp = datetime.now()
        
        # Auto-detect additional suggestions based on details
        if details:
            self._auto_detect_suggestions(details)
        
        super().__init__(f"[{code}] {message}")
    
    def _get_module_from_code(self, code: str) -> str:
        """Get module name from error code."""
        if code in ERROR_CODES:
            return ERROR_CODES[code][0]
        return "Unknown"
    
    def _auto_detect_suggestions(self, text: str) -> None:
        """Auto-detect common issues and add suggestions."""
        text_lower = text.lower()
        for issue_type, issue_data in KNOWN_ISSUES.items():
            for pattern in issue_data["patterns"]:
                if pattern.lower() in text_lower:
                    for suggestion in issue_data["suggestions"]:
                        if suggestion not in self.suggestions:
                            self.suggestions.append(suggestion)
                    break
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON logging."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "code": self.code,
            "module": self.module,
            "level": "ERROR",
            "message": self.message,
            "details": self.details,
            "suggestions": self.suggestions,
            "context": {
                "user": os.environ.get("USER", "unknown"),
                "cwd": os.getcwd(),
            }
        }


def _ensure_log_dir() -> bool:
    """Ensure log directory exists."""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        return True
    except PermissionError:
        return False


def _get_log_file() -> Path:
    """Get today's log file path."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOG_DIR / f"error-{date_str}.log"


def _cleanup_old_logs(keep_days: int = 7) -> None:
    """Remove log files older than keep_days."""
    if not LOG_DIR.exists():
        return
    
    cutoff = datetime.now() - timedelta(days=keep_days)
    
    for log_file in LOG_DIR.glob("error-*.log"):
        try:
            # Extract date from filename (error-YYYY-MM-DD.log)
            date_str = log_file.stem.replace("error-", "")
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            
            if file_date < cutoff:
                log_file.unlink()
        except (ValueError, OSError):
            pass


def _log_to_file(error: VexoError) -> Optional[str]:
    """Log error to JSON file. Returns log path or None if failed."""
    if not _ensure_log_dir():
        return None
    
    log_file = _get_log_file()
    
    try:
        with open(log_file, "a") as f:
            f.write(json.dumps(error.to_dict()) + "\n")
        return str(log_file)
    except (IOError, PermissionError):
        return None


def _display_error(error: VexoError, log_path: Optional[str] = None) -> None:
    """Display error in Rich console format."""
    # Build error content
    content = Text()
    content.append(f"{error.message}\n", style="bold red")
    
    if error.details:
        content.append(f"\nDetected: ", style="bold")
        content.append(f"{error.details}\n", style="yellow")
    
    if error.suggestions:
        content.append(f"\nSuggestions:\n", style="bold")
        for i, suggestion in enumerate(error.suggestions, 1):
            content.append(f"  {i}. {suggestion}\n", style="cyan")
    
    if log_path:
        content.append(f"\nLog: ", style="dim")
        content.append(f"{log_path}", style="dim blue")
    
    # Display in panel
    panel = Panel(
        content,
        title=f"[bold red]ERROR {error.code}[/bold red]",
        border_style="red",
        padding=(0, 1),
    )
    console.print(panel)


def handle_error(
    code: str,
    message: str,
    details: Optional[str] = None,
    suggestions: Optional[List[str]] = None,
    module: Optional[str] = None,
    raise_exception: bool = False,
) -> VexoError:
    """
    Handle an error: display to console and log to file.
    
    Args:
        code: Error code (e.g., "E2001")
        message: User-friendly error message
        details: Technical details (used for auto-detection)
        suggestions: Manual suggestions (auto-detection adds more)
        module: Module name (auto-detected from code if not provided)
        raise_exception: If True, raise VexoError after handling
    
    Returns:
        VexoError instance
    
    Example:
        handle_error(
            "E2001",
            "Failed to install nginx",
            details="Could not get lock /var/lib/dpkg/lock-frontend",
        )
    """
    error = VexoError(
        code=code,
        message=message,
        details=details,
        suggestions=suggestions,
        module=module,
    )
    
    # Log to file
    log_path = _log_to_file(error)
    
    # Display to console
    _display_error(error, log_path)
    
    if raise_exception:
        raise error
    
    return error


def handle_exception(
    code: str,
    message: str,
    exception: Exception,
    suggestions: Optional[List[str]] = None,
    module: Optional[str] = None,
    raise_exception: bool = False,
) -> VexoError:
    """
    Handle a caught exception: extract details and handle as error.
    
    Args:
        code: Error code (e.g., "E2001")
        message: User-friendly error message
        exception: The caught exception
        suggestions: Manual suggestions
        module: Module name
        raise_exception: If True, raise VexoError after handling
    
    Example:
        try:
            run_command("apt install nginx")
        except subprocess.CalledProcessError as e:
            handle_exception("E2001", "Failed to install nginx", e)
    """
    details = str(exception)
    if hasattr(exception, 'stderr') and exception.stderr:
        details = exception.stderr.strip()
    
    return handle_error(
        code=code,
        message=message,
        details=details,
        suggestions=suggestions,
        module=module,
        raise_exception=raise_exception,
    )


def init_error_handler() -> None:
    """Initialize error handler: ensure log dir and cleanup old logs."""
    _ensure_log_dir()
    _cleanup_old_logs(keep_days=7)


# Quick helper functions for common error types
def permission_error(message: str, details: Optional[str] = None) -> VexoError:
    """Handle permission error."""
    return handle_error("E1001", message, details)


def network_error(message: str, details: Optional[str] = None) -> VexoError:
    """Handle network error."""
    return handle_error("E1002", message, details)


def file_error(message: str, details: Optional[str] = None) -> VexoError:
    """Handle file not found error."""
    return handle_error("E1004", message, details)


def service_error(message: str, details: Optional[str] = None) -> VexoError:
    """Handle service error."""
    return handle_error("E1006", message, details)
```

**Step 2: Commit**

```bash
git add utils/error_handler.py
git commit -m "feat(error): add centralized error handler with codes and auto-detection"
```

---

## Task 2: Update utils/__init__.py

**Files:**
- Modify: `utils/__init__.py`

**Step 1: Add error handler exports**

```python
"""Utility functions for vexo - shell commands, logging, error handling."""

from utils.shell import (
    run_command,
    run_with_spinner,
    is_installed,
    is_command_available,
    is_service_running,
    is_service_enabled,
    service_control,
    check_root,
    require_root,
    get_system_info,
    get_hostname,
    get_ip_address,
    check_package_status,
)

from utils.logger import AppLogger

from utils.error_handler import (
    VexoError,
    handle_error,
    handle_exception,
    init_error_handler,
    permission_error,
    network_error,
    file_error,
    service_error,
    ERROR_CODES,
)

__all__ = [
    # Shell utilities
    "run_command",
    "run_with_spinner",
    "is_installed",
    "is_command_available",
    "is_service_running",
    "is_service_enabled",
    "service_control",
    "check_root",
    "require_root",
    "get_system_info",
    "get_hostname",
    "get_ip_address",
    "check_package_status",
    # Logger
    "AppLogger",
    # Error handler
    "VexoError",
    "handle_error",
    "handle_exception",
    "init_error_handler",
    "permission_error",
    "network_error",
    "file_error",
    "service_error",
    "ERROR_CODES",
]
```

**Step 2: Commit**

```bash
git add utils/__init__.py
git commit -m "feat(error): export error handler from utils"
```

---

## Task 3: Initialize Error Handler in main.py

**Files:**
- Modify: `main.py`

**Step 1: Add init call after imports**

Find this section near the top of main.py (around line 15-20):
```python
from ui.menu import main_menu
from ui.components import show_header, console
```

Add after it:
```python
from utils.error_handler import init_error_handler

# Initialize error handler (ensure log dir, cleanup old logs)
init_error_handler()
```

**Step 2: Commit**

```bash
git add main.py
git commit -m "feat(error): initialize error handler on startup"
```

---

## Task 4: Update modules/webserver/nginx.py

**Files:**
- Modify: `modules/webserver/nginx.py`

**Step 1: Add error handler import**

Find imports at top. Add:
```python
from utils.error_handler import handle_error, handle_exception
```

**Step 2: Update install function error handling**

Find the install function and update exception handling. Replace generic `show_error` calls with `handle_error`:

Example pattern - Before:
```python
try:
    run_command("apt install -y nginx")
except subprocess.CalledProcessError as e:
    show_error("Failed to install nginx")
    return False
```

After:
```python
try:
    run_command("apt install -y nginx")
except subprocess.CalledProcessError as e:
    handle_exception("E2001", "Failed to install nginx", e)
    return False
```

**Step 3: Commit**

```bash
git add modules/webserver/nginx.py
git commit -m "feat(error): add error handling to nginx module"
```

---

## Task 5: Update modules/setup.py

**Files:**
- Modify: `modules/setup.py`

**Step 1: Add error handler import**

```python
from utils.error_handler import handle_error, handle_exception
```

**Step 2: Update component installation error handling**

Find where components are installed and update error handling:

Before:
```python
show_error(f"{name} installation failed")
```

After:
```python
handle_error(
    code="E1006",
    message=f"{name} installation failed",
    details=str(e) if 'e' in dir() else None,
)
```

**Step 3: Commit**

```bash
git add modules/setup.py
git commit -m "feat(error): add error handling to setup module"
```

---

## Task 6: Create Error Handler Integration Helper

**Files:**
- Create: `scripts/update_error_handling.py`

This script helps identify files that need error handler updates:

```python
#!/usr/bin/env python3
"""Helper script to identify modules needing error handler updates."""

import os
import re
from pathlib import Path

MODULES_DIR = Path("modules")

def find_show_error_calls():
    """Find all show_error calls that should use handle_error."""
    results = []
    
    for py_file in MODULES_DIR.rglob("*.py"):
        with open(py_file, "r") as f:
            content = f.read()
            
        # Find show_error calls
        matches = re.finditer(r'show_error\(["\'](.+?)["\']\)', content)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            results.append({
                "file": str(py_file),
                "line": line_num,
                "message": match.group(1),
            })
    
    return results

def main():
    results = find_show_error_calls()
    
    print(f"Found {len(results)} show_error calls to review:\n")
    
    current_file = None
    for r in results:
        if r["file"] != current_file:
            current_file = r["file"]
            print(f"\n{current_file}:")
        print(f"  Line {r['line']}: {r['message'][:50]}...")

if __name__ == "__main__":
    main()
```

**Step 1: Run to identify files**

```bash
python3 scripts/update_error_handling.py
```

**Step 2: Commit helper script**

```bash
git add scripts/update_error_handling.py
git commit -m "chore: add helper script to identify error handling updates"
```

---

## Task 7: Update High-Priority Modules

Update these modules with error handling (same pattern as Task 4):

**Files to update:**
1. `modules/database/postgresql/install.py` - E4001
2. `modules/database/mariadb/install.py` - E4001
3. `modules/runtime/php/install.py` - E3001
4. `modules/runtime/nodejs/install.py` - E3003
5. `modules/email/postfix/install.py` - E5001
6. `modules/firewall/quick_setup.py` - E6001
7. `modules/ssl/issue.py` - E6002
8. `modules/fail2ban/jails.py` - E6003
9. `modules/supervisor/install.py` - E7001
10. `modules/cron/add_job.py` - E7003

**Pattern for each file:**

1. Add import:
```python
from utils.error_handler import handle_error, handle_exception
```

2. Replace `show_error(msg)` with:
```python
handle_error("EXXXX", msg, details=str(e) if applicable)
```

3. Replace exception handling:
```python
except SomeError as e:
    handle_exception("EXXXX", "User-friendly message", e)
```

**Step: Commit after each module or batch**

```bash
git add modules/database/
git commit -m "feat(error): add error handling to database modules"

git add modules/runtime/
git commit -m "feat(error): add error handling to runtime modules"

git add modules/email/ modules/firewall/ modules/ssl/ modules/fail2ban/
git commit -m "feat(error): add error handling to security/email modules"

git add modules/supervisor/ modules/cron/
git commit -m "feat(error): add error handling to process modules"
```

---

## Task 8: Final Testing & Cleanup

**Step 1: Test error display**

Create a quick test in Python REPL:
```python
from utils.error_handler import handle_error

# Test with auto-detection
handle_error(
    "E2001", 
    "Failed to install nginx",
    details="Could not get lock /var/lib/dpkg/lock-frontend"
)
```

Expected: Should show error panel with auto-detected suggestions.

**Step 2: Verify log file created**

```bash
cat /var/log/vexo/error-$(date +%Y-%m-%d).log
```

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat(error): complete error handling system implementation"
```

---

## Summary

After completing all tasks:

1. ✅ `utils/error_handler.py` - Core error handling with codes, auto-detection
2. ✅ `utils/__init__.py` - Exports error handler
3. ✅ `main.py` - Initializes error handler on startup
4. ✅ All major modules updated with proper error codes
5. ✅ JSON logs at `/var/log/vexo/error-YYYY-MM-DD.log`
6. ✅ Auto-cleanup of logs older than 7 days
7. ✅ Rich console output with contextual suggestions
