"""Filter management for fail2ban module."""

from ui.components import show_info, press_enter_to_continue, clear_screen, show_header, show_panel


def show_menu():
    """Display filter management menu."""
    clear_screen()
    show_header()
    show_panel("Filter Management", title="Fail2ban", style="cyan")
    show_info("Filter management will be implemented in Phase 5.")
    press_enter_to_continue()
