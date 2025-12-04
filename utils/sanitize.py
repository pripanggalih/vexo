"""Input sanitization and escaping utilities for vexo-cli.

This module provides secure escaping functions to prevent:
- SQL injection attacks
- Shell command injection attacks
- Path traversal attacks
"""

import re
import shlex
from typing import Optional


def escape_shell(value: str) -> str:
    """
    Escape a string for safe use in shell commands.
    
    Uses shlex.quote() which wraps value in single quotes
    and escapes any single quotes within.
    
    Args:
        value: String to escape
    
    Returns:
        Shell-safe escaped string
    
    Example:
        >>> escape_shell("test; rm -rf /")
        "'test; rm -rf /'"
        >>> escape_shell("it's a test")
        "'it'\"'\"'s a test'"
    """
    if not value:
        return "''"
    return shlex.quote(str(value))


def escape_mysql(value: str) -> str:
    """
    Escape a string for safe use in MySQL/MariaDB queries.
    
    Escapes special characters that could be used for SQL injection.
    Note: This is for VALUES only, not for identifiers (table/column names).
    
    Args:
        value: String to escape
    
    Returns:
        MySQL-safe escaped string (without surrounding quotes)
    
    Example:
        >>> escape_mysql("test'; DROP TABLE users; --")
        "test\\'; DROP TABLE users; --"
    """
    if value is None:
        return "NULL"
    
    value = str(value)
    
    replacements = [
        ("\\", "\\\\"),  # Backslash first
        ("'", "\\'"),    # Single quote
        ('"', '\\"'),    # Double quote
        ("\n", "\\n"),   # Newline
        ("\r", "\\r"),   # Carriage return
        ("\t", "\\t"),   # Tab
        ("\x00", ""),    # NULL byte - remove entirely
        ("\x1a", ""),    # Ctrl+Z - remove entirely
    ]
    
    for old, new in replacements:
        value = value.replace(old, new)
    
    return value


def escape_mysql_identifier(identifier: str) -> str:
    """
    Escape a MySQL identifier (database/table/column name).
    
    Uses backticks and escapes any backticks within the identifier.
    
    Args:
        identifier: Database, table, or column name
    
    Returns:
        Backtick-quoted identifier
    
    Example:
        >>> escape_mysql_identifier("my`table")
        "`my``table`"
    """
    if not identifier:
        raise ValueError("Identifier cannot be empty")
    
    escaped = str(identifier).replace("`", "``")
    return f"`{escaped}`"


def escape_postgresql(value: str) -> str:
    """
    Escape a string for safe use in PostgreSQL queries.
    
    Args:
        value: String to escape
    
    Returns:
        PostgreSQL-safe escaped string (without surrounding quotes)
    
    Example:
        >>> escape_postgresql("test'; DROP TABLE users; --")
        "test''; DROP TABLE users; --"
    """
    if value is None:
        return "NULL"
    
    value = str(value)
    
    # PostgreSQL uses doubled single quotes for escaping
    value = value.replace("'", "''")
    
    # Remove NULL bytes
    value = value.replace("\x00", "")
    
    return value


def escape_postgresql_identifier(identifier: str) -> str:
    """
    Escape a PostgreSQL identifier (database/table/column name).
    
    Uses double quotes and escapes any double quotes within.
    
    Args:
        identifier: Database, table, or column name
    
    Returns:
        Double-quoted identifier
    
    Example:
        >>> escape_postgresql_identifier('my"table')
        '"my""table"'
    """
    if not identifier:
        raise ValueError("Identifier cannot be empty")
    
    escaped = str(identifier).replace('"', '""')
    return f'"{escaped}"'


def sanitize_identifier(identifier: str, allow_chars: str = "a-zA-Z0-9_") -> str:
    """
    Sanitize an identifier to contain only allowed characters.
    
    Useful for usernames, database names, etc. where you want
    to restrict to alphanumeric characters.
    
    Args:
        identifier: String to sanitize
        allow_chars: Regex character class of allowed characters
    
    Returns:
        Sanitized string with disallowed characters removed
    
    Raises:
        ValueError: If result is empty after sanitization
    """
    if not identifier:
        raise ValueError("Identifier cannot be empty")
    
    pattern = f"[^{allow_chars}]"
    sanitized = re.sub(pattern, "", str(identifier))
    
    if not sanitized:
        raise ValueError(f"Identifier '{identifier}' contains no valid characters")
    
    return sanitized


def validate_identifier(identifier: str, max_length: int = 64, 
                       allow_chars: str = "a-zA-Z0-9_") -> bool:
    """
    Validate an identifier against allowed character set and length.
    
    Args:
        identifier: String to validate
        max_length: Maximum allowed length
        allow_chars: Regex character class of allowed characters
    
    Returns:
        True if valid, False otherwise
    """
    if not identifier:
        return False
    
    if len(identifier) > max_length:
        return False
    
    pattern = f"^[{allow_chars}]+$"
    return bool(re.match(pattern, str(identifier)))


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
    
    Returns:
        True if valid email format
    """
    if not email:
        return False
    
    # RFC 5322 simplified pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, str(email)))


def validate_ipv4(ip: str) -> bool:
    """
    Validate IPv4 address format.
    
    Args:
        ip: IP address string
    
    Returns:
        True if valid IPv4 address
    """
    if not ip:
        return False
    
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    
    try:
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
            # Check for leading zeros (e.g., "01" is invalid)
            if part != str(num):
                return False
    except ValueError:
        return False
    
    return True


def validate_ipv6(ip: str) -> bool:
    """
    Validate IPv6 address format.
    
    Args:
        ip: IP address string
    
    Returns:
        True if valid IPv6 address
    """
    if not ip:
        return False
    
    # Handle IPv4-mapped IPv6 addresses
    if ip.startswith("::ffff:"):
        return validate_ipv4(ip[7:])
    
    # Split by :: for zero compression
    if "::" in ip:
        parts = ip.split("::")
        if len(parts) > 2:
            return False
        
        left = parts[0].split(":") if parts[0] else []
        right = parts[1].split(":") if len(parts) > 1 and parts[1] else []
        
        # Total groups must be <= 8
        if len(left) + len(right) > 7:
            return False
    else:
        parts = ip.split(":")
        if len(parts) != 8:
            return False
        left = parts
        right = []
    
    # Validate each group
    for group in left + right:
        if not group:
            continue
        if len(group) > 4:
            return False
        try:
            int(group, 16)
        except ValueError:
            return False
    
    return True


def validate_ip(ip: str) -> bool:
    """
    Validate IP address (IPv4 or IPv6).
    
    Args:
        ip: IP address string
    
    Returns:
        True if valid IPv4 or IPv6 address
    """
    return validate_ipv4(ip) or validate_ipv6(ip)


def validate_cidr(cidr: str) -> bool:
    """
    Validate CIDR notation (e.g., 192.168.0.0/24 or 2001:db8::/32).
    
    Args:
        cidr: CIDR string
    
    Returns:
        True if valid CIDR notation
    """
    if not cidr or '/' not in cidr:
        return False
    
    ip_part, prefix = cidr.rsplit('/', 1)
    
    try:
        prefix_int = int(prefix)
    except ValueError:
        return False
    
    if validate_ipv4(ip_part):
        return 0 <= prefix_int <= 32
    elif validate_ipv6(ip_part):
        return 0 <= prefix_int <= 128
    
    return False


def validate_port(port: int) -> bool:
    """
    Validate TCP/UDP port number.
    
    Args:
        port: Port number
    
    Returns:
        True if valid port (1-65535)
    """
    try:
        port_int = int(port)
        return 1 <= port_int <= 65535
    except (ValueError, TypeError):
        return False


def validate_port_range(port_range: str) -> bool:
    """
    Validate port range string (e.g., "6000:6010").
    
    Args:
        port_range: Port range in format "start:end"
    
    Returns:
        True if valid port range
    """
    if ':' not in port_range:
        return validate_port(port_range)
    
    parts = port_range.split(':')
    if len(parts) != 2:
        return False
    
    try:
        start = int(parts[0])
        end = int(parts[1])
        return (1 <= start <= 65535 and 
                1 <= end <= 65535 and 
                start < end)
    except ValueError:
        return False


def validate_domain(domain: str) -> bool:
    """
    Validate domain name format.
    
    Args:
        domain: Domain name
    
    Returns:
        True if valid domain format
    """
    if not domain:
        return False
    
    # Remove trailing dot if present
    domain = domain.rstrip('.')
    
    if len(domain) > 253:
        return False
    
    # Domain pattern: labels separated by dots
    # Each label: 1-63 chars, alphanumeric and hyphens, no start/end hyphen
    pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
    
    return bool(re.match(pattern, domain))


def validate_username(username: str) -> bool:
    """
    Validate Unix username format.
    
    Args:
        username: Username to validate
    
    Returns:
        True if valid Unix username
    """
    if not username:
        return False
    
    # Must start with lowercase letter
    # Can contain lowercase letters, digits, underscore, hyphen
    # Max 32 characters (Linux default)
    pattern = r'^[a-z][a-z0-9_-]{0,31}$'
    
    return bool(re.match(pattern, username))


def sanitize_path(path: str, base_dir: Optional[str] = None) -> str:
    """
    Sanitize a file path to prevent path traversal attacks.
    
    Args:
        path: Path to sanitize
        base_dir: If provided, ensure path stays within this directory
    
    Returns:
        Sanitized absolute path
    
    Raises:
        ValueError: If path escapes base_dir
    """
    import os
    
    if not path:
        raise ValueError("Path cannot be empty")
    
    # Normalize path (resolve .., ., etc.)
    normalized = os.path.normpath(path)
    
    # Make absolute
    abs_path = os.path.abspath(normalized)
    
    if base_dir:
        base_abs = os.path.abspath(base_dir)
        # Ensure path is within base_dir
        if not abs_path.startswith(base_abs + os.sep) and abs_path != base_abs:
            raise ValueError(f"Path '{path}' escapes base directory '{base_dir}'")
    
    return abs_path
