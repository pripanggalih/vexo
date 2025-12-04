"""Notification system for fail2ban module."""

from ui.components import show_info, press_enter_to_continue, clear_screen, show_header, show_panel


def show_menu():
    """Display notifications menu."""
    clear_screen()
    show_header()
    show_panel("Notifications", title="Fail2ban", style="cyan")
    show_info("Notification system will be implemented in Phase 7.")
    press_enter_to_continue()
