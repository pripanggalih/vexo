"""Backup and restore for fail2ban module."""

from ui.components import show_info, press_enter_to_continue, clear_screen, show_header, show_panel


def show_menu():
    """Display backup menu."""
    clear_screen()
    show_header()
    show_panel("Backup & Restore", title="Fail2ban", style="cyan")
    show_info("Backup & restore will be implemented in Phase 8.")
    press_enter_to_continue()
