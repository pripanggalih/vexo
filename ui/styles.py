"""Theme and style definitions for vexo."""

# Color constants
PRIMARY = "cyan"
SUCCESS = "green"
WARNING = "yellow"
ERROR = "red"
INFO = "blue"
MUTED = "dim"


def primary(text):
    """Wrap text in primary color."""
    return f"[{PRIMARY}]{text}[/{PRIMARY}]"


def success(text):
    """Wrap text in success color."""
    return f"[{SUCCESS}]{text}[/{SUCCESS}]"


def warning(text):
    """Wrap text in warning color."""
    return f"[{WARNING}]{text}[/{WARNING}]"


def error(text):
    """Wrap text in error color."""
    return f"[{ERROR}]{text}[/{ERROR}]"


def info(text):
    """Wrap text in info color."""
    return f"[{INFO}]{text}[/{INFO}]"


def bold(text):
    """Wrap text in bold."""
    return f"[bold]{text}[/bold]"


def muted(text):
    """Wrap text in muted/dim style."""
    return f"[{MUTED}]{text}[/{MUTED}]"


# Status indicator symbols
INDICATOR_OK = f"[{SUCCESS}]●[/{SUCCESS}]"
INDICATOR_WARN = f"[{WARNING}]●[/{WARNING}]"
INDICATOR_ERROR = f"[{ERROR}]●[/{ERROR}]"
INDICATOR_INFO = f"[{INFO}]●[/{INFO}]"
