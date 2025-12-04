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
