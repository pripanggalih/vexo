# Task 2.0: Implement Core UI Components - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the UI layer with reusable components for menus, styles, and visual feedback.

**Architecture:** Three files in `ui/` package - `styles.py` for theme constants, `components.py` for Rich-based display widgets, `menu.py` for Prompt Toolkit interactive menus. All components are stateless functions that can be imported and used by any module.

**Tech Stack:** Rich (panels, tables, console), Prompt Toolkit (radiolist_dialog, yes_no_dialog, input_dialog)

**Note:** Development only - no testing/running. Code will be tested by user on target environment.

---

## Task 2.1: Create ui/styles.py

**Files:**
- Create: `ui/styles.py`

**Step 1: Create styles.py with theme constants**

```python
"""Theme and style definitions for vexo."""

from prompt_toolkit.styles import Style

# Color constants
PRIMARY = "cyan"
SUCCESS = "green"
WARNING = "yellow"
ERROR = "red"
INFO = "blue"
MUTED = "dim"

# Rich markup shortcuts
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

# Prompt Toolkit style for dialogs
DIALOG_STYLE = Style.from_dict({
    "dialog": "bg:#1a1a2e",
    "dialog.body": "bg:#1a1a2e #ffffff",
    "dialog frame.label": f"bg:#{PRIMARY} #ffffff",
    "dialog.shadow": "bg:#000000",
    "button": "bg:#333333 #ffffff",
    "button.focused": f"bg:{PRIMARY} #000000",
    "radiolist": "bg:#1a1a2e",
    "radiolist focused": f"bg:{PRIMARY} #000000",
})

# Status indicator symbols
INDICATOR_OK = f"[{SUCCESS}]●[/{SUCCESS}]"
INDICATOR_WARN = f"[{WARNING}]●[/{WARNING}]"
INDICATOR_ERROR = f"[{ERROR}]●[/{ERROR}]"
INDICATOR_INFO = f"[{INFO}]●[/{INFO}]"
```

**Step 2: Commit**

```bash
git add ui/styles.py && git commit -m "feat(ui): add styles.py with theme constants and helpers"
```

---

## Task 2.2: Create ui/components.py - Header

**Files:**
- Create: `ui/components.py`

**Step 1: Create components.py with console and show_header()**

```python
"""Reusable UI components for vexo."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from config import APP_NAME, APP_VERSION
from ui.styles import PRIMARY, SUCCESS, WARNING, ERROR, bold, primary

# Global console instance
console = Console()


def clear_screen():
    """Clear the terminal screen."""
    console.clear()


def show_header():
    """Display the application header/branding."""
    header_text = Text()
    header_text.append(f"  {APP_NAME}  ", style=f"bold white on {PRIMARY}")
    header_text.append(f"  v{APP_VERSION}", style="dim")
    
    console.print()
    console.print(header_text)
    console.print(f"[dim]VPS Management CLI for Ubuntu/Debian[/dim]")
    console.print()
```

**Step 2: Commit**

```bash
git add ui/components.py && git commit -m "feat(ui): add components.py with console and show_header()"
```

---

## Task 2.3: Add show_panel() to components.py

**Files:**
- Modify: `ui/components.py`

**Step 1: Add show_panel() function**

Append to `ui/components.py`:

```python


def show_panel(content, title="", style="cyan", padding=(1, 2)):
    """
    Display content in a styled panel.
    
    Args:
        content: Text or Rich renderable to display
        title: Optional panel title
        style: Border style color
        padding: Tuple of (vertical, horizontal) padding
    """
    panel = Panel(
        content,
        title=title if title else None,
        border_style=style,
        padding=padding,
    )
    console.print(panel)
```

**Step 2: Commit**

```bash
git add ui/components.py && git commit -m "feat(ui): add show_panel() for styled panels"
```

---

## Task 2.4: Add show_table() to components.py

**Files:**
- Modify: `ui/components.py`

**Step 1: Add show_table() function**

Append to `ui/components.py`:

```python


def show_table(title, columns, rows, show_header=True):
    """
    Display data in a formatted table.
    
    Args:
        title: Table title
        columns: List of column definitions, each is dict with 'name' and optional 'style', 'justify'
        rows: List of row data (list of values matching column order)
        show_header: Whether to show column headers
    
    Example:
        columns = [
            {"name": "Domain", "style": "cyan"},
            {"name": "Status", "justify": "center"},
        ]
        rows = [
            ["example.com", "Active"],
            ["test.com", "Inactive"],
        ]
        show_table("Domains", columns, rows)
    """
    table = Table(title=title, show_header=show_header, border_style="dim")
    
    for col in columns:
        table.add_column(
            col.get("name", ""),
            style=col.get("style", None),
            justify=col.get("justify", "left"),
        )
    
    for row in rows:
        table.add_row(*[str(cell) for cell in row])
    
    console.print(table)
    console.print()
```

**Step 2: Commit**

```bash
git add ui/components.py && git commit -m "feat(ui): add show_table() for formatted tables"
```

---

## Task 2.5: Add message functions to components.py

**Files:**
- Modify: `ui/components.py`

**Step 1: Add show_success(), show_error(), show_warning(), show_info()**

Append to `ui/components.py`:

```python


def show_success(message):
    """Display a success message."""
    console.print(f"[{SUCCESS}]✓[/{SUCCESS}] {message}")


def show_error(message):
    """Display an error message."""
    console.print(f"[{ERROR}]✗[/{ERROR}] {message}")


def show_warning(message):
    """Display a warning message."""
    console.print(f"[{WARNING}]![/{WARNING}] {message}")


def show_info(message):
    """Display an info message."""
    console.print(f"[{PRIMARY}]→[/{PRIMARY}] {message}")


def show_spinner(message):
    """
    Return a spinner context manager for long operations.
    
    Usage:
        with show_spinner("Installing..."):
            run_command("apt install nginx")
    """
    from rich.spinner import Spinner
    return console.status(message, spinner="dots")


def press_enter_to_continue():
    """Wait for user to press Enter."""
    console.print()
    console.input("[dim]Press Enter to continue...[/dim]")
```

**Step 2: Commit**

```bash
git add ui/components.py && git commit -m "feat(ui): add message functions (success, error, warning, info, spinner)"
```

---

## Task 2.6: Create ui/menu.py - Main Menu

**Files:**
- Create: `ui/menu.py`

**Step 1: Create menu.py with show_main_menu()**

```python
"""Interactive menu system for vexo using Prompt Toolkit."""

from prompt_toolkit.shortcuts import radiolist_dialog, yes_no_dialog, input_dialog

from ui.styles import DIALOG_STYLE
from config import APP_NAME


def show_main_menu():
    """
    Display the main menu and return the selected option.
    
    Returns:
        str: Selected menu key or None if cancelled
    """
    result = radiolist_dialog(
        title=f"{APP_NAME} - Main Menu",
        text="Select a module to manage:",
        values=[
            ("system", "1. System Setup & Update"),
            ("domain", "2. Domain & Nginx"),
            ("php", "3. PHP Runtime"),
            ("nodejs", "4. Node.js Runtime"),
            ("database", "5. Database (MySQL/MariaDB)"),
            ("email", "6. Email Server (Postfix)"),
            ("monitor", "7. System Monitoring"),
            ("exit", "8. Exit"),
        ],
        style=DIALOG_STYLE,
    ).run()
    
    return result
```

**Step 2: Commit**

```bash
git add ui/menu.py && git commit -m "feat(ui): add menu.py with show_main_menu()"
```

---

## Task 2.7: Add show_submenu() to menu.py

**Files:**
- Modify: `ui/menu.py`

**Step 1: Add show_submenu() function**

Append to `ui/menu.py`:

```python


def show_submenu(title, options):
    """
    Display a submenu with custom options.
    
    Args:
        title: Menu title
        options: List of tuples (key, label) for menu items
                 Example: [("install", "Install Nginx"), ("back", "← Back")]
    
    Returns:
        str: Selected menu key or None if cancelled
    """
    result = radiolist_dialog(
        title=title,
        text="Select an option:",
        values=options,
        style=DIALOG_STYLE,
    ).run()
    
    return result
```

**Step 2: Commit**

```bash
git add ui/menu.py && git commit -m "feat(ui): add show_submenu() for module submenus"
```

---

## Task 2.8: Add confirm_action() to menu.py

**Files:**
- Modify: `ui/menu.py`

**Step 1: Add confirm_action() function**

Append to `ui/menu.py`:

```python


def confirm_action(message, title="Confirm"):
    """
    Show a yes/no confirmation dialog.
    
    Args:
        message: Question to ask the user
        title: Dialog title
    
    Returns:
        bool: True if confirmed, False if cancelled
    """
    result = yes_no_dialog(
        title=title,
        text=message,
        style=DIALOG_STYLE,
    ).run()
    
    return result
```

**Step 2: Commit**

```bash
git add ui/menu.py && git commit -m "feat(ui): add confirm_action() for yes/no dialogs"
```

---

## Task 2.9: Add text_input() to menu.py

**Files:**
- Modify: `ui/menu.py`

**Step 1: Add text_input() function**

Append to `ui/menu.py`:

```python


def text_input(message, title="Input", default="", password=False):
    """
    Show a text input dialog.
    
    Args:
        message: Prompt message
        title: Dialog title
        default: Default value
        password: If True, hide input (for passwords)
    
    Returns:
        str: User input or None if cancelled
    """
    result = input_dialog(
        title=title,
        text=message,
        default=default,
        password=password,
        style=DIALOG_STYLE,
    ).run()
    
    return result


def select_from_list(title, message, options):
    """
    Let user select one item from a list.
    
    Args:
        title: Dialog title
        message: Prompt message
        options: List of string options
    
    Returns:
        str: Selected option or None if cancelled
    """
    values = [(opt, opt) for opt in options]
    
    result = radiolist_dialog(
        title=title,
        text=message,
        values=values,
        style=DIALOG_STYLE,
    ).run()
    
    return result
```

**Step 2: Commit**

```bash
git add ui/menu.py && git commit -m "feat(ui): add text_input() and select_from_list() dialogs"
```

---

## Task 2.10: Update ui/__init__.py exports

**Files:**
- Modify: `ui/__init__.py`

**Step 1: Update __init__.py to export all public functions**

```python
"""UI components for vexo - menus, styles, and reusable widgets."""

from ui.styles import (
    PRIMARY, SUCCESS, WARNING, ERROR, INFO, MUTED,
    primary, success, warning, error, info, bold, muted,
    DIALOG_STYLE,
    INDICATOR_OK, INDICATOR_WARN, INDICATOR_ERROR, INDICATOR_INFO,
)

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_success,
    show_error,
    show_warning,
    show_info,
    show_spinner,
    press_enter_to_continue,
)

from ui.menu import (
    show_main_menu,
    show_submenu,
    confirm_action,
    text_input,
    select_from_list,
)
```

**Step 2: Commit**

```bash
git add ui/__init__.py && git commit -m "feat(ui): update __init__.py with all exports"
```

---

## Task 2.11: Update task list

Mark Task 2.0 and all sub-tasks as completed in `tasks/tasks-vexo.md`

---

## Summary

After completing this plan:

```
ui/
├── __init__.py      ✅ Exports all public functions
├── styles.py        ✅ Theme constants, color helpers, dialog style
├── components.py    ✅ Console, header, panel, table, messages, spinner
└── menu.py          ✅ Main menu, submenu, confirm, text input, select list
```

**Functions available after Task 2:**

| File | Functions |
|------|-----------|
| `styles.py` | `primary()`, `success()`, `warning()`, `error()`, `info()`, `bold()`, `muted()` |
| `components.py` | `clear_screen()`, `show_header()`, `show_panel()`, `show_table()`, `show_success()`, `show_error()`, `show_warning()`, `show_info()`, `show_spinner()`, `press_enter_to_continue()` |
| `menu.py` | `show_main_menu()`, `show_submenu()`, `confirm_action()`, `text_input()`, `select_from_list()` |
