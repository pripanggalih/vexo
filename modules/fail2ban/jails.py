"""Jail management for fail2ban module."""

from ui.components import show_info, press_enter_to_continue, clear_screen, show_header, show_panel


def show_menu():
    """Display jail management menu."""
    clear_screen()
    show_header()
    show_panel("Jail Management", title="Fail2ban", style="cyan")
    show_info("Jail management will be implemented in Phase 2.")
    press_enter_to_continue()
