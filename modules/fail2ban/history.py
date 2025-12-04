"""History and analytics for fail2ban module."""

from ui.components import show_info, press_enter_to_continue, clear_screen, show_header, show_panel


def show_menu():
    """Display history menu."""
    clear_screen()
    show_header()
    show_panel("History & Logs", title="Fail2ban", style="cyan")
    show_info("History & analytics will be implemented in Phase 6.")
    press_enter_to_continue()
