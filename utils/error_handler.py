"""Centralized error handling for vexo.

Provides:
- VexoError exception class with error codes
- Dual logging: Rich console (user-friendly) + JSON file (debugging)
- Auto-detection of common issues with contextual suggestions
- Log rotation by date (keep 7 days)
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

LOG_DIR = Path("/var/log/vexo")

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
        
        if details:
            self._auto_detect_suggestions(details)
        
        super().__init__(f"[{code}] {message}")
    
    def _get_module_from_code(self, code: str) -> str:
        if code in ERROR_CODES:
            return ERROR_CODES[code][0]
        return "Unknown"
    
    def _auto_detect_suggestions(self, text: str) -> None:
        text_lower = text.lower()
        for issue_type, issue_data in KNOWN_ISSUES.items():
            for pattern in issue_data["patterns"]:
                if pattern.lower() in text_lower:
                    for suggestion in issue_data["suggestions"]:
                        if suggestion not in self.suggestions:
                            self.suggestions.append(suggestion)
                    break
    
    def to_dict(self) -> Dict[str, Any]:
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
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        return True
    except PermissionError:
        return False


def _get_log_file() -> Path:
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOG_DIR / f"error-{date_str}.log"


def _cleanup_old_logs(keep_days: int = 7) -> None:
    if not LOG_DIR.exists():
        return
    
    cutoff = datetime.now() - timedelta(days=keep_days)
    
    for log_file in LOG_DIR.glob("error-*.log"):
        try:
            date_str = log_file.stem.replace("error-", "")
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            
            if file_date < cutoff:
                log_file.unlink()
        except (ValueError, OSError):
            pass


def _log_to_file(error: VexoError) -> Optional[str]:
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
    """
    error = VexoError(
        code=code,
        message=message,
        details=details,
        suggestions=suggestions,
        module=module,
    )
    
    log_path = _log_to_file(error)
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


def permission_error(message: str, details: Optional[str] = None) -> VexoError:
    return handle_error("E1001", message, details)


def network_error(message: str, details: Optional[str] = None) -> VexoError:
    return handle_error("E1002", message, details)


def file_error(message: str, details: Optional[str] = None) -> VexoError:
    return handle_error("E1004", message, details)


def service_error(message: str, details: Optional[str] = None) -> VexoError:
    return handle_error("E1006", message, details)
