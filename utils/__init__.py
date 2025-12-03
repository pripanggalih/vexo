"""Utility functions for vexo-cli - shell commands, logging."""

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
