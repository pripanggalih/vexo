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
-   **System Monitoring** - Real-time CPU, RAM, Disk, and Swap usage

### Web Server

-   **Nginx Management** - Install, configure, manage virtual hosts
-   **Domain Management** - Add/remove domains with preset templates
-   **Site Configuration** - Laravel, WordPress, Static, SPA, Node.js presets
-   **SSL Certificates** - Let's Encrypt integration via Certbot

### Runtimes

-   **PHP Management** - Multiple PHP versions (8.3, 8.4, 8.5), extensions, Composer
-   **Node.js Management** - NVM integration, multiple Node.js versions

### Databases

-   **PostgreSQL** - Install, create databases/users
-   **MariaDB** - Install, secure installation, create databases/users
-   **Redis** - Install, status, flush cache

### Email

-   **Postfix** - Send-only and receive mode (catch-all)
-   **Multi-domain** - Configure multiple domains with Laravel pipe integration

### Security

-   **UFW Firewall** - Enable/disable, manage ports
-   **Fail2ban** - Brute force protection, ban/unban IPs
-   **SSL/TLS** - Automatic HTTPS with Let's Encrypt

### Process Management

-   **Supervisor** - Queue workers for Laravel/PHP applications
-   **Cron Jobs** - Laravel scheduler, custom cron jobs

## Requirements

-   **OS**: Ubuntu 20.04+ or Debian 11+
-   **Python**: 3.8 or higher
-   **Privileges**: Root access (sudo)

## Installation

### Quick Install (Recommended)

```bash
curl -sSL https://raw.githubusercontent.com/pripanggalih/vexo-cli/main/install.sh | sudo bash
```

### Manual Install

```bash
# Clone repository
sudo git clone https://github.com/pripanggalih/vexo-cli.git /opt/vexo-cli
cd /opt/vexo-cli

# Create virtual environment
sudo python3 -m venv venv
sudo ./venv/bin/pip install -r requirements.txt

# Create symlink
sudo ln -sf /opt/vexo-cli/vexo /usr/local/bin/vexo

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
vexo-cli/
├── main.py              # Entry point
├── config.py            # Global configuration
├── requirements.txt     # Python dependencies
├── install.sh           # Installation script
├── ui/                  # UI components
│   ├── components.py    # Rich-based UI elements
│   ├── menu.py          # InquirerPy menu system
│   └── styles.py        # Color themes
├── modules/             # Feature modules
│   ├── system.py        # System setup
│   ├── webserver.py     # Nginx & domains
│   ├── runtime.py       # PHP & Node.js
│   ├── database.py      # PostgreSQL, MariaDB, Redis
│   ├── email.py         # Postfix
│   ├── monitor.py       # System monitoring
│   ├── supervisor.py    # Queue workers
│   ├── cron.py          # Scheduled tasks
│   ├── firewall.py      # UFW
│   ├── ssl.py           # Let's Encrypt
│   ├── fail2ban.py      # Brute force protection
│   └── setup.py         # First-run wizard
├── utils/               # Utilities
│   └── shell.py         # Shell command wrapper
└── templates/           # Config templates
    └── nginx/           # Nginx presets & snippets
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
