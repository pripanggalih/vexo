# VEXO-CLI

```
 ██╗   ██╗███████╗██╗  ██╗ ██████╗
 ██║   ██║██╔════╝╚██╗██╔╝██╔═══██╗
 ██║   ██║█████╗   ╚███╔╝ ██║   ██║
 ╚██╗ ██╔╝██╔══╝   ██╔██╗ ██║   ██║
  ╚████╔╝ ███████╗██╔╝ ██╗╚██████╔╝
   ╚═══╝  ╚══════╝╚═╝  ╚═╝ ╚═════╝
```

**VPS Easy eXecution Orchestrator** - Interactive CLI for managing Ubuntu/Debian VPS servers.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

### System Management

-   **System Setup** - Update/upgrade system, install basic tools
-   **System Monitoring** - Real-time CPU, RAM, Disk, Swap, Network, Process monitoring
-   **Monitoring History** - Historical data with graphs and analytics
-   **Alerts** - Configurable threshold alerts with notifications
-   **User Management** - Create, manage system users
-   **Hostname & Security** - SSH hardening, hostname configuration

### Web Server

-   **Nginx Management** - Install, configure, manage virtual hosts
-   **Domain Management** - Add/remove domains with preset templates, bulk operations
-   **Site Configuration** - Laravel, WordPress, Static, SPA, Node.js presets
-   **SSL Certificates** - Let's Encrypt, DNS challenge providers, certificate import
-   **Site Cloning** - Clone existing site configurations
-   **Traffic Stats** - Access/error logs viewer, traffic statistics

### Runtimes

-   **PHP Management** - Multiple PHP versions (8.3, 8.4, 8.5), extensions, Composer
-   **Node.js Management** - NVM integration, multiple Node.js versions

### Databases

-   **PostgreSQL** - Install, create databases/users, backup/restore
-   **MariaDB** - Install, secure installation, create databases/users, backup/restore
-   **Redis** - Install, status, flush cache, configuration

### Email

-   **Postfix** - Send-only and receive mode (catch-all)
-   **Dovecot** - IMAP/POP3 support
-   **Webmail** - Roundcube integration
-   **Multi-domain** - Configure multiple domains with Laravel pipe integration

### Security

-   **UFW Firewall** - Enable/disable, manage ports, rate limiting, security profiles
-   **Fail2ban** - Brute force protection, ban/unban IPs, history analytics, multi-channel notifications, filter management
-   **SSL/TLS** - Automatic HTTPS with Let's Encrypt, DNS challenge providers, certificate import
-   **Input Sanitization** - Protection against injection attacks

### Process Management

-   **Supervisor** - Queue workers with templates, monitoring, environment variables
-   **Cron Jobs** - Laravel scheduler, cron expression builder, execution history, backup/restore

## Requirements

-   **OS**: Ubuntu 20.04+ or Debian 11+
-   **Python**: 3.8 or higher
-   **Privileges**: Root access (sudo)

## Installation

### Quick Install (Recommended)

```bash
curl -sSL https://raw.githubusercontent.com/pripanggalih/vexo/main/install.sh | sudo bash
```

### Manual Install

```bash
# Clone repository
sudo git clone https://github.com/pripanggalih/vexo.git /opt/vexo
cd /opt/vexo

# Create virtual environment
sudo python3 -m venv venv
sudo ./venv/bin/pip install -r requirements.txt

# Create symlink
sudo ln -sf /opt/vexo/vexo /usr/local/bin/vexo

# Run
sudo vexo
```

## Usage

```bash
# Run vexo (requires sudo)
sudo vexo

# Show help
vexo --help

# Show version
vexo --version

# Manual update
sudo vexo --update

# Skip auto-update check
sudo vexo --no-update
```

## Main Menu

```
Host: myserver (192.168.1.10) | Uptime: 5d 3h
RAM: 2.1/4.0GB (52%) | Disk: 15/50GB (30%) | Swap: 0.0/2.0GB

? VEXO v1.0.0 - Select a module:
  1. System Setup & Update
  2. Domain & Nginx
  3. PHP Runtime
  4. Node.js Runtime
  5. Database
  6. Email Server
  7. System Monitoring
  8. Supervisor (Queue Workers)
  9. Cron Jobs
  10. Firewall (UFW)
  11. SSL Certificates
  12. Fail2ban
  ✕ Exit
```

## First Run Setup

On first run (when Nginx is not installed), vexo will show a setup wizard:

```
? Select components to install:
  ◉ Nginx (Web Server)
  ◉ PHP 8.3 + Extensions
  ◉ MySQL/MariaDB
  ◉ Redis
  ◉ Supervisor
  ◉ UFW Firewall
  ◉ Fail2ban
  ◉ Basic Utilities
```

## Configuration

### Nginx Site Presets

| Preset    | Description                                   |
| --------- | --------------------------------------------- |
| Laravel   | PHP-FPM, try_files for pretty URLs            |
| WordPress | PHP-FPM, WordPress-specific rules             |
| Static    | HTML/CSS/JS only                              |
| SPA       | React/Vue/Angular with fallback to index.html |
| Node.js   | Reverse proxy to Node.js application          |

### PHP Extensions (Laravel-compatible)

```
bcmath, ctype, curl, dom, fileinfo, mbstring, pdo, tokenizer, xml,
mysql, pgsql, sqlite3, zip, gd, intl, opcache, redis, imagick
```

## Auto-Update

vexo automatically checks for updates on every run:

-   Fetches latest from GitHub
-   Updates code via `git pull`
-   Installs new dependencies
-   Restarts automatically

To skip: `sudo vexo --no-update`

## Project Structure

```
vexo/
├── main.py              # Entry point
├── config.py            # Global configuration
├── requirements.txt     # Python dependencies
├── install.sh           # Installation script
├── dev.sh               # Development helper script
├── ui/                  # UI components
│   ├── components.py    # Rich-based UI elements
│   ├── menu.py          # InquirerPy menu system
│   └── styles.py        # Color themes
├── modules/             # Feature modules (modular structure)
│   ├── system/          # System setup & management
│   │   ├── cleanup.py, hostname.py, info.py
│   │   ├── power.py, security.py, swap.py, users.py
│   ├── webserver/       # Nginx & domains
│   │   ├── backup.py, bulk.py, clone.py, configure.py
│   │   ├── domains.py, logs.py, nginx.py, ssl.py, stats.py
│   ├── runtime/         # PHP & Node.js
│   │   ├── php/         # PHP versions, extensions, Composer
│   │   └── nodejs/      # NVM, Node.js versions
│   ├── database/        # Database management
│   │   ├── postgresql/, mariadb/, redis/
│   ├── email/           # Email server
│   │   ├── postfix/, dovecot/, webmail/
│   ├── monitor/         # System monitoring
│   │   ├── alert.py, cpu.py, dashboard.py, disk.py
│   │   ├── history.py, memory.py, network.py, process.py, service.py
│   ├── supervisor/      # Queue workers
│   │   ├── add_worker.py, control.py, edit.py, env.py
│   │   ├── logs.py, monitor.py, templates.py, worker.py
│   ├── cron/            # Scheduled tasks
│   │   ├── add_job.py, backup.py, builder.py, control.py
│   │   ├── edit.py, history.py, jobs.py, laravel.py, logs.py
│   ├── firewall/        # UFW Firewall
│   │   ├── backup.py, ip_management.py, logs.py, ports.py
│   │   ├── presets.py, profiles.py, quick_setup.py, rate_limiting.py
│   ├── ssl/             # SSL Certificates
│   │   ├── backup.py, dashboard.py, dns_providers.py
│   │   ├── import_cert.py, issue.py, manage.py, security.py
│   ├── fail2ban/        # Brute force protection
│   │   ├── backup.py, bans.py, dashboard.py, filters.py
│   │   ├── history.py, jails.py, notifications.py, settings.py
│   │   ├── whitelist.py, templates/
│   └── setup.py         # First-run wizard
├── utils/               # Utilities
│   ├── shell.py         # Shell command wrapper
│   ├── logger.py        # Logging utility
│   ├── monitor_logger.py # Monitoring data logger
│   └── sanitize.py      # Input sanitization & escaping
├── templates/           # Config templates
│   └── nginx/           # Nginx presets & snippets
└── scripts/             # Helper scripts
    └── vexo-cron-wrapper # Cron job wrapper
```

## Dependencies

| Package                                             | Purpose                             |
| --------------------------------------------------- | ----------------------------------- |
| [Rich](https://github.com/Textualize/rich)          | Terminal formatting, tables, panels |
| [psutil](https://github.com/giampaolo/psutil)       | System monitoring                   |
| [InquirerPy](https://github.com/kazhala/InquirerPy) | Interactive prompts                 |

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

-   [Rich](https://github.com/Textualize/rich) for beautiful terminal output
-   [InquirerPy](https://github.com/kazhala/InquirerPy) for interactive prompts
-   [psutil](https://github.com/giampaolo/psutil) for system information

---

**Made with ❤️ for VPS administrators**
