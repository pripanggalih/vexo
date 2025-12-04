"""Interactive menu system for vexo using InquirerPy."""

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.separator import Separator
from InquirerPy.utils import InquirerPyStyle

from config import APP_NAME


# Cyan theme style
MENU_STYLE = InquirerPyStyle({
    "questionmark": "#00ffff bold",
    "answermark": "#00ffff bold",
    "answer": "#00ffff",
    "input": "#ffffff",
    "question": "#ffffff bold",
    "answered_question": "#ffffff",
    "instruction": "#666666",
    "long_instruction": "#666666",
    "pointer": "#00ffff bold",
    "checkbox": "#00ffff",
    "separator": "#666666",
    "skipped": "#666666",
    "validator": "#ff0000",
    "marker": "#00ffff",
    "fuzzy_prompt": "#00ffff",
    "fuzzy_info": "#666666",
    "fuzzy_border": "#00ffff",
    "fuzzy_match": "#00ffff bold",
    "frame.border": "#00ffff",
})


def show_main_menu(title=None, options=None):
    """
    Display the main menu and return the selected option.
    
    Args:
        title: Menu title (optional)
        options: List of tuples (key, label) for menu items (optional)
    
    Returns:
        str: Selected menu key or None if cancelled
    """
    if title is None:
        title = f"{APP_NAME}"
    
    if options is None:
        options = [
            ("system", "1. System Setup & Update"),
            ("domain", "2. Domain & Nginx"),
            ("php", "3. PHP Runtime"),
            ("nodejs", "4. Node.js Runtime"),
            ("database", "5. Database (MySQL/MariaDB)"),
            ("email", "6. Email Server (Postfix)"),
            ("monitor", "7. System Monitoring"),
            ("exit", "8. Exit"),
        ]
    
    # Build choices for InquirerPy
    choices = [Choice(value=key, name=label) for key, label in options]
    
    try:
        result = inquirer.fuzzy(
            message=f"{title} - Select a module:",
            choices=choices,
            default=None,
            border=True,
            pointer="›",
            marker="›",
            cycle=True,
            max_height="70%",
            instruction="(↑↓ navigate, type to filter, enter to select)",
            style=MENU_STYLE,
        ).execute()
        return result
    except KeyboardInterrupt:
        return None


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
    # Build choices for InquirerPy
    choices = [Choice(value=key, name=label) for key, label in options]
    
    try:
        result = inquirer.fuzzy(
            message=title,
            choices=choices,
            default=None,
            border=True,
            pointer="›",
            marker="›",
            cycle=True,
            max_height="70%",
            instruction="(↑↓ navigate, type to filter, enter to select)",
            style=MENU_STYLE,
        ).execute()
        return result
    except KeyboardInterrupt:
        return None


def confirm_action(message, title="Confirm"):
    """
    Show a yes/no confirmation prompt.
    
    Args:
        message: Question to ask the user
        title: Dialog title (unused, kept for compatibility)
    
    Returns:
        bool: True if confirmed, False if cancelled
    """
    try:
        return inquirer.confirm(
            message=message,
            default=False,
            style=MENU_STYLE,
        ).execute()
    except KeyboardInterrupt:
        return False


def text_input(message, title="Input", default="", password=False):
    """
    Show a text input prompt.
    
    Args:
        message: Prompt message
        title: Dialog title (unused, kept for compatibility)
        default: Default value
        password: If True, hide input (for passwords)
    
    Returns:
        str: User input or None if cancelled
    """
    try:
        if password:
            return inquirer.secret(
                message=message,
                style=MENU_STYLE,
            ).execute()
        else:
            return inquirer.text(
                message=message,
                default=default,
                style=MENU_STYLE,
            ).execute()
    except KeyboardInterrupt:
        return None


def select_from_list(title, message, options, allow_cancel=True):
    """
    Let user select one item from a list.
    
    Args:
        title: Dialog title
        message: Prompt message
        options: List of string options
        allow_cancel: If True, add "← Cancel" option (default: True)
    
    Returns:
        str: Selected option or None if cancelled
    """
    if not options:
        return None
    
    # Build choices with optional cancel
    choices = [Choice(value=opt, name=opt) for opt in options]
    if allow_cancel:
        choices.append(Choice(value=None, name="← Cancel"))
    
    try:
        result = inquirer.fuzzy(
            message=message,
            choices=choices,
            default=None,
            border=True,
            pointer="›",
            marker="›",
            cycle=True,
            max_height="70%",
            instruction="(↑↓ navigate, type to filter, enter to select)",
            style=MENU_STYLE,
        ).execute()
        return result
    except KeyboardInterrupt:
        return None


def run_menu_loop(title, get_options, handlers, get_status=None):
    """
    Run a standard menu loop with automatic screen clearing and header.
    
    Args:
        title: Menu title string
        get_options: List of (key, label) tuples OR callable that returns such list
        handlers: Dict mapping choice keys to handler functions
        get_status: Optional callable that returns status string to display
    
    Example:
        def get_options():
            opts = [("list", "1. List Items")]
            opts.append(("back", "← Back"))
            return opts
        
        handlers = {
            "list": list_items,
        }
        
        run_menu_loop("My Menu", get_options, handlers)
    """
    from ui.components import clear_screen, show_header, console
    
    while True:
        clear_screen()
        show_header()
        
        if get_status:
            status = get_status()
            if status:
                console.print(f"[dim]{status}[/dim]")
                console.print()
        
        options = get_options() if callable(get_options) else get_options
        
        choice = show_submenu(title=title, options=options)
        
        if choice == "back" or choice is None:
            break
        
        handler = handlers.get(choice)
        if handler:
            handler()
