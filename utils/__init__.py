"""Utility functions for vexo - shell commands, logging, error handling."""

from utils.shell import (
    run_command,
    run_command_with_progress,
    run_command_realtime,
    is_installed,
    is_command_available,
    is_service_running,
    is_service_enabled,
    service_control,
    check_root,
    require_root,
    get_os_info,
    get_hostname,
    get_ip_address,
)

from utils.logger import (
    Logger,
    log,
    log_info,
    log_success,
    log_warning,
    log_error,
    log_debug,
    log_step,
)

from utils.error_handler import (
    VexoError,
    handle_error,
    handle_exception,
    init_error_handler,
    permission_error,
    network_error,
    file_error,
    service_error,
    ERROR_CODES,
)
