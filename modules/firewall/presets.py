"""Port preset definitions for common services."""

# Web Stack
WEB_PRESETS = [
    {"port": "80", "protocol": "tcp", "name": "HTTP", "description": "Web server"},
    {"port": "443", "protocol": "tcp", "name": "HTTPS", "description": "Secure web server"},
    {"port": "443", "protocol": "udp", "name": "HTTP/3", "description": "QUIC protocol"},
]

# Database
DATABASE_PRESETS = [
    {"port": "3306", "protocol": "tcp", "name": "MySQL", "description": "MySQL/MariaDB"},
    {"port": "5432", "protocol": "tcp", "name": "PostgreSQL", "description": "PostgreSQL"},
    {"port": "27017", "protocol": "tcp", "name": "MongoDB", "description": "MongoDB"},
    {"port": "6379", "protocol": "tcp", "name": "Redis", "description": "Redis cache"},
    {"port": "11211", "protocol": "tcp", "name": "Memcached", "description": "Memcached"},
]

# Mail Server
MAIL_PRESETS = [
    {"port": "25", "protocol": "tcp", "name": "SMTP", "description": "Mail transfer"},
    {"port": "587", "protocol": "tcp", "name": "Submission", "description": "Mail submission"},
    {"port": "465", "protocol": "tcp", "name": "SMTPS", "description": "SMTP over SSL"},
    {"port": "143", "protocol": "tcp", "name": "IMAP", "description": "Mail access"},
    {"port": "993", "protocol": "tcp", "name": "IMAPS", "description": "IMAP over SSL"},
    {"port": "110", "protocol": "tcp", "name": "POP3", "description": "Mail retrieval"},
    {"port": "995", "protocol": "tcp", "name": "POP3S", "description": "POP3 over SSL"},
]

# Development
DEV_PRESETS = [
    {"port": "21", "protocol": "tcp", "name": "FTP", "description": "File transfer"},
    {"port": "22", "protocol": "tcp", "name": "SSH", "description": "Secure shell"},
    {"port": "9418", "protocol": "tcp", "name": "Git", "description": "Git protocol"},
    {"port": "3000", "protocol": "tcp", "name": "Node.js", "description": "Node.js dev server"},
    {"port": "5000", "protocol": "tcp", "name": "Flask", "description": "Flask/Django dev"},
    {"port": "8080", "protocol": "tcp", "name": "Alt HTTP", "description": "Alternative HTTP"},
    {"port": "8443", "protocol": "tcp", "name": "Alt HTTPS", "description": "Alternative HTTPS"},
]

# Other Services
OTHER_PRESETS = [
    {"port": "53", "protocol": "tcp", "name": "DNS (TCP)", "description": "Domain name system"},
    {"port": "53", "protocol": "udp", "name": "DNS (UDP)", "description": "Domain name system"},
    {"port": "123", "protocol": "udp", "name": "NTP", "description": "Network time"},
    {"port": "51820", "protocol": "udp", "name": "WireGuard", "description": "WireGuard VPN"},
    {"port": "1194", "protocol": "udp", "name": "OpenVPN", "description": "OpenVPN"},
]

# All presets grouped by category
ALL_PRESETS = {
    "web": {"name": "Web Stack", "ports": WEB_PRESETS},
    "database": {"name": "Database", "ports": DATABASE_PRESETS},
    "mail": {"name": "Mail Server", "ports": MAIL_PRESETS},
    "dev": {"name": "Development", "ports": DEV_PRESETS},
    "other": {"name": "Other Services", "ports": OTHER_PRESETS},
}


def get_preset_display(preset, is_open=False):
    """Get display string for a preset."""
    status = "[green]✓[/green] " if is_open else "  "
    return f"{status}{preset['name']} ({preset['port']}/{preset['protocol']}) - {preset['description']}"


def get_all_presets_flat():
    """Get all presets as a flat list."""
    all_ports = []
    for category in ALL_PRESETS.values():
        all_ports.extend(category["ports"])
    return all_ports
