"""Ban management for fail2ban module."""

from ui.components import show_info, press_enter_to_continue, clear_screen, show_header, show_panel


def show_menu():
    """Display ban management menu."""
    clear_screen()
    show_header()
    show_panel("Ban Management", title="Fail2ban", style="cyan")
    show_info("Ban management will be implemented in Phase 3.")
    press_enter_to_continue()
