"""Common utilities for monitor module."""

from config import THRESHOLDS


def get_status_color(percentage):
    """
    Get color based on usage percentage and thresholds.
    
    Args:
        percentage: Usage percentage (0-100)
    
    Returns:
        str: Color name ('green', 'yellow', or 'red')
    """
    if percentage < THRESHOLDS['good']:
        return 'green'
    elif percentage < THRESHOLDS['warning']:
        return 'yellow'
    else:
        return 'red'


def format_bytes(bytes_value):
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024
    return f"{bytes_value:.1f} PB"
