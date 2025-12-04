# Arrow-Key Menu Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace radiolist_dialog menus with questionary arrow-key menus for better UX (Enter directly selects without Tab to OK).

**Architecture:** Replace prompt_toolkit's radiolist_dialog with questionary.select() for all menu functions. Keep confirm_action() and text_input() unchanged. Add emoji icons to menu items.

**Tech Stack:** questionary>=2.0.0, existing Rich for output

---

## Task 1: Add questionary dependency

**Files:**
- Modify: `requirements.txt`

**Step 1: Add questionary to requirements**

```txt
rich>=13.0.0
prompt_toolkit>=3.0.0
psutil>=5.9.0
questionary>=2.0.0
```

**Step 2: Commit**

```bash
git add requirements.txt
git commit -m "deps: add questionary for arrow-key menus"
```

---

## Task 2: Create icon mappings and style

**Files:**
- Modify: `ui/menu.py` (lines 1-10)

**Step 1: Update imports and add constants**

Replace the top of `ui/menu.py`:

```python
"""Interactive menu system for vexo using questionary."""

import questionary
from questionary import Style, Choice
from prompt_toolkit.shortcuts import yes_no_dialog, input_dialog

from ui.styles import DIALOG_STYLE
from config import APP_NAME


# Custom style matching cyan theme
MENU_STYLE = Style([
    ('qmark', 'fg:cyan bold'),
    ('question', 'bold'),
    ('pointer', 'fg:cyan bold'),
    ('highlighted', 'fg:cyan bold'),
    ('selected', 'fg:cyan'),
])

# Main menu icons
MENU_ICONS = {
    "system": "⚙️",
    "webserver": "🌐",
    "php": "🐘",
    "nodejs": "📦",
    "database": "🗄️",
    "email": "📧",
    "monitor": "📊",
    "firewall": "🛡️",
    "ssl": "🔒",
    "fail2ban": "🚫",
    "supervisor": "👷",
    "cron": "⏰",
    "exit": "🚪",
    "back": "←",
}

# Submenu icons
SUBMENU_ICONS = {
    "install": "📥",
    "remove": "🗑️",
    "configure": "⚙️",
    "status": "📋",
    "start": "▶️",
    "stop": "⏹️",
    "restart": "🔄",
    "logs": "📜",
    "list": "📝",
    "add": "➕",
    "edit": "✏️",
    "test": "🧪",
    "backup": "💾",
    "restore": "📂",
    "view": "👁️",
    "flush": "🚿",
    "delete": "❌",
    "toggle": "🔀",
    "laravel": "🎨",
    "mode": "🔧",
    "domains": "🌍",
    "queue": "📬",
    "control": "🎮",
    "workers": "👥",
}
```

**Step 2: Commit**

```bash
git add ui/menu.py
git commit -m "feat(menu): add questionary imports and icon mappings"
```

---

## Task 3: Rewrite show_main_menu()

**Files:**
- Modify: `ui/menu.py`

**Step 1: Replace show_main_menu function**

Find and replace the entire `show_main_menu` function:

```python
def show_main_menu(title=None, options=None):
    """
    Display the main menu with arrow-key navigation.
    
    Args:
        title: Menu title (optional, used for display context)
        options: List of tuples (key, label) for menu items
    
    Returns:
        str: Selected menu key or None if cancelled (Escape)
    """
    if options is None:
        options = [
            ("system", "1. System Setup & Update"),
            ("webserver", "2. Domain & Nginx"),
            ("php", "3. PHP Runtime"),
            ("nodejs", "4. Node.js Runtime"),
            ("database", "5. Database (MySQL/MariaDB)"),
            ("email", "6. Email Server (Postfix)"),
            ("monitor", "7. System Monitoring"),
            ("exit", "8. Exit"),
        ]
    
    # Build choices with icons
    choices = []
    for key, label in options:
        icon = MENU_ICONS.get(key, "")
        display = f"{icon} {label}" if icon else label
        choices.append(Choice(title=display, value=key))
    
    result = questionary.select(
        "Select a module:",
        choices=choices,
        style=MENU_STYLE,
        use_arrow_keys=True,
        use_shortcuts=False,
    ).ask()
    
    return result
```

**Step 2: Commit**

```bash
git add ui/menu.py
git commit -m "feat(menu): rewrite show_main_menu with questionary"
```

---

## Task 4: Rewrite show_submenu()

**Files:**
- Modify: `ui/menu.py`

**Step 1: Replace show_submenu function**

Find and replace the entire `show_submenu` function:

```python
def show_submenu(title, options):
    """
    Display a submenu with arrow-key navigation.
    
    Args:
        title: Menu title/question
        options: List of tuples (key, label) for menu items
    
    Returns:
        str: Selected menu key or None if cancelled (Escape)
    """
    # Build choices with icons
    choices = []
    for key, label in options:
        icon = SUBMENU_ICONS.get(key, "")
        display = f"{icon} {label}" if icon else label
        choices.append(Choice(title=display, value=key))
    
    result = questionary.select(
        title,
        choices=choices,
        style=MENU_STYLE,
        use_arrow_keys=True,
        use_shortcuts=False,
    ).ask()
    
    return result
```

**Step 2: Commit**

```bash
git add ui/menu.py
git commit -m "feat(menu): rewrite show_submenu with questionary"
```

---

## Task 5: Rewrite select_from_list()

**Files:**
- Modify: `ui/menu.py`

**Step 1: Replace select_from_list function**

Find and replace the entire `select_from_list` function:

```python
def select_from_list(title, message, options):
    """
    Let user select one item from a dynamic list (no icons).
    
    Args:
        title: Dialog title (unused, kept for API compatibility)
        message: Prompt message
        options: List of string options
    
    Returns:
        str: Selected option or None if cancelled (Escape)
    """
    if not options:
        return None
    
    result = questionary.select(
        message,
        choices=options,
        style=MENU_STYLE,
        use_arrow_keys=True,
        use_shortcuts=False,
    ).ask()
    
    return result
```

**Step 2: Commit**

```bash
git add ui/menu.py
git commit -m "feat(menu): rewrite select_from_list with questionary"
```

---

## Task 6: Remove unused imports and verify

**Files:**
- Modify: `ui/menu.py`

**Step 1: Verify final menu.py structure**

The complete `ui/menu.py` should now be:

```python
"""Interactive menu system for vexo using questionary."""

import questionary
from questionary import Style, Choice
from prompt_toolkit.shortcuts import yes_no_dialog, input_dialog

from ui.styles import DIALOG_STYLE
from config import APP_NAME


# Custom style matching cyan theme
MENU_STYLE = Style([
    ('qmark', 'fg:cyan bold'),
    ('question', 'bold'),
    ('pointer', 'fg:cyan bold'),
    ('highlighted', 'fg:cyan bold'),
    ('selected', 'fg:cyan'),
])

# Main menu icons
MENU_ICONS = {
    "system": "⚙️",
    "webserver": "🌐",
    "php": "🐘",
    "nodejs": "📦",
    "database": "🗄️",
    "email": "📧",
    "monitor": "📊",
    "firewall": "🛡️",
    "ssl": "🔒",
    "fail2ban": "🚫",
    "supervisor": "👷",
    "cron": "⏰",
    "exit": "🚪",
    "back": "←",
}

# Submenu icons
SUBMENU_ICONS = {
    "install": "📥",
    "remove": "🗑️",
    "configure": "⚙️",
    "status": "📋",
    "start": "▶️",
    "stop": "⏹️",
    "restart": "🔄",
    "logs": "📜",
    "list": "📝",
    "add": "➕",
    "edit": "✏️",
    "test": "🧪",
    "backup": "💾",
    "restore": "📂",
    "view": "👁️",
    "flush": "🚿",
    "delete": "❌",
    "toggle": "🔀",
    "laravel": "🎨",
    "mode": "🔧",
    "domains": "🌍",
    "queue": "📬",
    "control": "🎮",
    "workers": "👥",
}


def show_main_menu(title=None, options=None):
    """
    Display the main menu with arrow-key navigation.
    
    Args:
        title: Menu title (optional, used for display context)
        options: List of tuples (key, label) for menu items
    
    Returns:
        str: Selected menu key or None if cancelled (Escape)
    """
    if options is None:
        options = [
            ("system", "1. System Setup & Update"),
            ("webserver", "2. Domain & Nginx"),
            ("php", "3. PHP Runtime"),
            ("nodejs", "4. Node.js Runtime"),
            ("database", "5. Database (MySQL/MariaDB)"),
            ("email", "6. Email Server (Postfix)"),
            ("monitor", "7. System Monitoring"),
            ("exit", "8. Exit"),
        ]
    
    # Build choices with icons
    choices = []
    for key, label in options:
        icon = MENU_ICONS.get(key, "")
        display = f"{icon} {label}" if icon else label
        choices.append(Choice(title=display, value=key))
    
    result = questionary.select(
        "Select a module:",
        choices=choices,
        style=MENU_STYLE,
        use_arrow_keys=True,
        use_shortcuts=False,
    ).ask()
    
    return result


def show_submenu(title, options):
    """
    Display a submenu with arrow-key navigation.
    
    Args:
        title: Menu title/question
        options: List of tuples (key, label) for menu items
    
    Returns:
        str: Selected menu key or None if cancelled (Escape)
    """
    # Build choices with icons
    choices = []
    for key, label in options:
        icon = SUBMENU_ICONS.get(key, "")
        display = f"{icon} {label}" if icon else label
        choices.append(Choice(title=display, value=key))
    
    result = questionary.select(
        title,
        choices=choices,
        style=MENU_STYLE,
        use_arrow_keys=True,
        use_shortcuts=False,
    ).ask()
    
    return result


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
    Let user select one item from a dynamic list (no icons).
    
    Args:
        title: Dialog title (unused, kept for API compatibility)
        message: Prompt message
        options: List of string options
    
    Returns:
        str: Selected option or None if cancelled (Escape)
    """
    if not options:
        return None
    
    result = questionary.select(
        message,
        choices=options,
        style=MENU_STYLE,
        use_arrow_keys=True,
        use_shortcuts=False,
    ).ask()
    
    return result
```

**Step 2: Run syntax check**

```bash
python3 -m py_compile ui/menu.py && echo "Syntax OK"
```

**Step 3: Final commit**

```bash
git add ui/menu.py
git commit -m "feat(menu): complete arrow-key menu migration to questionary"
```

---

## Verification Checklist

After implementation, verify:

1. [ ] `python3 -m py_compile ui/menu.py` - no errors
2. [ ] `python3 -m py_compile main.py` - no errors
3. [ ] All module imports work: `python3 -c "from ui.menu import show_main_menu, show_submenu, select_from_list"`

## Expected Behavior

- **Main menu**: Arrow keys navigate, Enter selects, Escape cancels
- **Submenus**: Same behavior with relevant icons
- **Select from list**: Arrow navigation for dynamic lists (domain selection, etc.)
- **Confirm/Input dialogs**: Unchanged (still use prompt_toolkit)
