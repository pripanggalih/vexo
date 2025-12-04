"""Whitelist management for fail2ban module."""

from ui.components import show_info, press_enter_to_continue, clear_screen, show_header, show_panel


def show_menu():
    """Display whitelist management menu."""
    clear_screen()
    show_header()
    show_panel("Whitelist Management", title="Fail2ban", style="cyan")
    show_info("Whitelist management will be implemented in Phase 4.")
    press_enter_to_continue()
