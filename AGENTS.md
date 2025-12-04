# AGENTS.md - vexo

## Project Overview

**vexo** adalah VPS Management CLI berbasis Python untuk Ubuntu/Debian. Aplikasi ini menggunakan interface menu interaktif (bukan command-based) dengan tampilan visual modern.

## Tech Stack

- **Language:** Python 3.8+
- **UI:** Rich (tables, panels, progress bars, colors)
- **Interactivity:** InquirerPy (menu navigation, dialogs)
- **System Monitoring:** psutil
- **Target OS:** Ubuntu/Debian

## Project Structure

```
vexo/
├── main.py                  # Entry point
├── config.py                # Global configuration & constants
├── requirements.txt         # Python dependencies
├── install.sh               # Installation script
├── dev.sh                   # Development helper script
├── ui/                      # UI layer
│   ├── __init__.py
│   ├── menu.py              # Menu rendering (InquirerPy)
│   ├── styles.py            # Color themes & styles
│   └── components.py        # Reusable widgets (header, tables, panels)
├── modules/                 # Business logic (modular structure)
│   ├── __init__.py
│   ├── system/              # System setup & management
│   │   ├── cleanup.py       # System cleanup utilities
│   │   ├── hostname.py      # Hostname configuration
│   │   ├── info.py          # System information
│   │   ├── power.py         # Power management (reboot/shutdown)
│   │   ├── security.py      # SSH & security hardening
│   │   ├── swap.py          # Swap management
│   │   └── users.py         # User management
│   ├── webserver/           # Nginx & domain management
│   │   ├── backup.py        # Configuration backup
│   │   ├── bulk.py          # Bulk domain operations
│   │   ├── clone.py         # Site cloning
│   │   ├── configure.py     # Site configuration
│   │   ├── domains.py       # Domain management
│   │   ├── logs.py          # Access/error logs
│   │   ├── nginx.py         # Nginx service control
│   │   ├── ssl.py           # SSL integration
│   │   ├── stats.py         # Traffic statistics
│   │   └── utils.py         # Webserver utilities
│   ├── runtime/             # Runtime management
│   │   ├── php/             # PHP versions, extensions, Composer
│   │   └── nodejs/          # NVM, Node.js versions
│   ├── database/            # Database management
│   │   ├── postgresql/      # PostgreSQL management
│   │   ├── mariadb/         # MariaDB management
│   │   └── redis/           # Redis management
│   ├── email/               # Email server
│   │   ├── postfix/         # Postfix configuration
│   │   ├── dovecot/         # Dovecot IMAP/POP3
│   │   ├── webmail/         # Webmail (Roundcube)
│   │   └── utils.py         # Email utilities
│   ├── monitor/             # System monitoring
│   │   ├── alert.py         # Alert notifications
│   │   ├── cpu.py           # CPU monitoring
│   │   ├── dashboard.py     # Monitoring dashboard
│   │   ├── disk.py          # Disk monitoring
│   │   ├── history.py       # Historical data & graphs
│   │   ├── memory.py        # Memory monitoring
│   │   ├── network.py       # Network monitoring
│   │   ├── process.py       # Process monitoring
│   │   └── service.py       # Service status monitoring
│   ├── supervisor/          # Queue workers (Supervisor)
│   │   ├── add_worker.py    # Add new worker
│   │   ├── control.py       # Start/stop/restart workers
│   │   ├── edit.py          # Edit worker configuration
│   │   ├── env.py           # Environment variables
│   │   ├── logs.py          # Worker logs viewer
│   │   ├── monitor.py       # Worker monitoring
│   │   ├── templates.py     # Worker templates (Laravel, etc.)
│   │   └── worker.py        # Worker management
│   ├── cron/                # Scheduled tasks
│   │   ├── add_job.py       # Add new cron job
│   │   ├── backup.py        # Cron backup/restore
│   │   ├── builder.py       # Cron expression builder
│   │   ├── control.py       # Enable/disable jobs
│   │   ├── edit.py          # Edit cron jobs
│   │   ├── history.py       # Execution history
│   │   ├── jobs.py          # List jobs
│   │   ├── laravel.py       # Laravel scheduler helper
│   │   ├── logs.py          # Cron logs viewer
│   │   └── templates.py     # Job templates
│   ├── firewall/            # UFW Firewall
│   │   ├── backup.py        # Rules backup/restore
│   │   ├── ip_management.py # IP allow/deny rules
│   │   ├── logs.py          # Firewall logs
│   │   ├── ports.py         # Port management
│   │   ├── presets.py       # Service presets
│   │   ├── profiles.py      # Security profiles
│   │   ├── quick_setup.py   # Quick setup wizard
│   │   ├── rate_limiting.py # Connection rate limiting
│   │   └── status.py        # Firewall status
│   ├── ssl/                 # SSL Certificate management
│   │   ├── backup.py        # Certificate backup
│   │   ├── dashboard.py     # SSL dashboard
│   │   ├── dns_providers.py # DNS challenge providers
│   │   ├── import_cert.py   # Import external certs
│   │   ├── issue.py         # Issue new certificates
│   │   ├── manage.py        # Certificate management
│   │   ├── security.py      # SSL security settings
│   │   └── settings.py      # SSL configuration
│   ├── fail2ban/            # Brute force protection
│   │   ├── backup.py        # Config backup/restore with scheduling
│   │   ├── bans.py          # Ban/unban IP management
│   │   ├── dashboard.py     # Fail2ban dashboard
│   │   ├── filters.py       # Filter management & testing
│   │   ├── history.py       # Ban history (SQLite), analytics
│   │   ├── jails.py         # Jail configuration
│   │   ├── notifications.py # Multi-channel notifications
│   │   ├── settings.py      # Global settings
│   │   ├── whitelist.py     # IP whitelist management
│   │   └── templates/       # Filter templates
│   │       ├── web_apps.py  # Web application filters
│   │       └── web_security.py # Security filters
│   ├── setup.py             # First-run setup wizard
│   ├── database.py          # Legacy database module
│   ├── email.py             # Legacy email module
│   └── runtime.py           # Legacy runtime module
├── utils/                   # Utilities
│   ├── __init__.py
│   ├── shell.py             # Shell command wrapper (subprocess)
│   ├── logger.py            # Logging utility
│   ├── monitor_logger.py    # Monitoring data logger
│   └── sanitize.py          # Input sanitization & escaping
├── templates/               # Config templates
│   └── nginx/               # Nginx templates
│       ├── laravel.conf     # Laravel preset
│       ├── wordpress.conf   # WordPress preset
│       ├── static.conf      # Static site preset
│       ├── spa.conf         # SPA preset
│       ├── nodejs.conf      # Node.js preset
│       └── snippets/        # Reusable snippets
├── scripts/                 # Helper scripts
│   └── vexo-cron-wrapper    # Cron job wrapper script
├── docs/
│   └── plans/               # Implementation plans
└── tasks/                   # PRD & task tracking
    ├── prd-vexo.md
    └── tasks-vexo.md
```

## Development Guidelines

### Environment

- **Development only** - tulis kode, jangan run/test
- **Testing:** Dilakukan manual oleh user di environment terpisah
- **Dependencies:** JANGAN install di dev environment

### Coding Conventions

1. **Imports:** Standard library first, then third-party, then local
2. **Docstrings:** Required for all modules, classes, and public functions
3. **Type hints:** Preferred but not required
4. **Error handling:** Always wrap shell commands in try-except
5. **Idempotency:** Check state before modifying (e.g., check if package installed before installing)

### UI Patterns

```python
# Use Rich console for output
from rich.console import Console
console = Console()

# Use prompt_toolkit for interactive menus
from prompt_toolkit.shortcuts import radiolist_dialog

# Color scheme
# - Cyan: Primary/headers
# - Green: Success
# - Yellow: Warning
# - Red: Error
```

### Shell Command Pattern

```python
# Always use utils/shell.py wrapper
from utils.shell import run_command, is_installed

# Check before install
if not is_installed("nginx"):
    run_command("apt install -y nginx")
```

## Key Files Reference

| File | Purpose |
|------|---------|
| `config.py` | All paths, constants, thresholds |
| `ui/menu.py` | Main menu and submenu functions |
| `utils/shell.py` | `run_command()`, `is_installed()`, `check_root()` |
| `utils/sanitize.py` | Input sanitization, escaping, injection prevention |
| `utils/monitor_logger.py` | Monitoring data logging with SQLite |
| `modules/fail2ban/` | Complete fail2ban management with history, notifications |
| `modules/firewall/` | UFW management with profiles, rate limiting |
| `modules/ssl/` | SSL certificates with DNS providers, security settings |

## Task Tracking

- PRD: `tasks/prd-vexo.md`
- Tasks: `tasks/tasks-vexo.md`
- Plans: `docs/plans/`

## Do NOT

- **JANGAN** install dependencies
- **JANGAN** run/execute code
- **JANGAN** test apapun
- **JANGAN** modifikasi system files
- **JANGAN** gunakan `os.system()` - gunakan `subprocess` via `utils/shell.py`

## Agent Task

Fokus agent hanya:
1. **Tulis kode** yang benar dan best practice
2. **Commit** perubahan ke git
3. **Update task list** setelah selesai

Testing dan verifikasi adalah tanggung jawab user.
