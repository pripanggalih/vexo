"""UI components for vexo-cli - menus, styles, and reusable widgets."""

from ui.styles import (
    PRIMARY, SUCCESS, WARNING, ERROR, INFO, MUTED,
    primary, success, warning, error, info, bold, muted,
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
