## Relevant Files

-   `main.py` - Entry point aplikasi, menjalankan main loop dan menu utama
-   `requirements.txt` - Daftar dependencies Python (rich, prompt_toolkit, psutil)
-   `config.py` - Global configuration (paths, constants, settings)
-   `ui/__init__.py` - Package init untuk UI module
-   `ui/menu.py` - Logic untuk render menu interaktif dengan prompt_toolkit
-   `ui/styles.py` - Tema warna dan style definitions
-   `ui/components.py` - Reusable UI widgets (header, footer, panels, tables)
-   `modules/__init__.py` - Package init untuk modules
-   `modules/system.py` - System setup module (apt update, install basic tools)
-   `modules/webserver.py` - Nginx & Domain management module
-   `modules/runtime.py` - PHP & Node.js runtime management module
-   `modules/database.py` - MySQL/MariaDB database management module
-   `modules/email.py` - Postfix email server module
-   `modules/monitor.py` - System monitoring module (CPU, RAM, Disk)
-   `utils/__init__.py` - Package init untuk utils
-   `utils/shell.py` - Wrapper untuk subprocess/shell command execution
-   `utils/logger.py` - Logging utility
-   `install.sh` - One-liner install script untuk distribusi
-   `templates/nginx_vhost.conf` - Template Nginx virtual host configuration

### Notes

-   Aplikasi ini ditujukan untuk Ubuntu/Debian VPS dan memerlukan sudo/root privileges
-   Gunakan `python3 main.py` atau `sudo python3 main.py` untuk menjalankan aplikasi
-   Dependencies diinstall dengan `pip install -r requirements.txt`

## Instructions for Completing Tasks

**IMPORTANT:** As you complete each task, you must check it off in this markdown file by changing `- [ ]` to `- [x]`. This helps track progress and ensures you don't skip any steps.

Example:

-   `- [ ] 1.1 Read file` → `- [x] 1.1 Read file` (after completing)

Update the file after completing each sub-task, not just after completing an entire parent task.

## Tasks

-   [x] 0.0 Initialize Git Repository

    -   [x] 0.1 Run `git init` untuk initialize repository
    -   [x] 0.2 Buat file `.gitignore` dengan entries untuk Python (`__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `.env`)
    -   [x] 0.3 Buat initial commit dengan pesan "Initial commit"

-   [x] 1.0 Setup Project Structure & Dependencies

    -   [x] 1.1 Buat folder structure: `ui/`, `modules/`, `utils/`, `templates/`
    -   [x] 1.2 Buat file `__init__.py` kosong di setiap folder package (`ui/`, `modules/`, `utils/`)
    -   [x] 1.3 Buat `requirements.txt` dengan dependencies: `rich`, `prompt_toolkit`, `psutil`
    -   [x] 1.4 Buat `config.py` dengan constants: APP_NAME, VERSION, paths untuk Nginx config, dll
    -   [x] 1.5 Buat file `main.py` sebagai entry point

-   [x] 2.0 Implement Core UI Components

    -   [x] 2.1 Buat `ui/styles.py` - definisikan color scheme (cyan primary, green success, yellow warning, red error)
    -   [x] 2.2 Buat `ui/components.py` - implement fungsi `show_header()` untuk menampilkan branding vexo-cli
    -   [x] 2.3 Buat `ui/components.py` - implement fungsi `show_panel()` untuk wrapper Rich Panel
    -   [x] 2.4 Buat `ui/components.py` - implement fungsi `show_table()` untuk generic table rendering
    -   [x] 2.5 Buat `ui/components.py` - implement fungsi `show_success()`, `show_error()`, `show_warning()` messages
    -   [x] 2.6 Buat `ui/menu.py` - implement fungsi `show_main_menu()` dengan radiolist_dialog (prompt_toolkit)
    -   [x] 2.7 Buat `ui/menu.py` - implement fungsi `show_submenu()` untuk sub-menu di setiap module
    -   [x] 2.8 Buat `ui/menu.py` - implement fungsi `confirm_action()` untuk yes/no confirmation dialog
    -   [x] 2.9 Buat `ui/menu.py` - implement fungsi `text_input()` untuk input text dari user

-   [x] 3.0 Implement Utility Functions

    -   [x] 3.1 Buat `utils/shell.py` - implement fungsi `run_command(cmd)` wrapper subprocess dengan error handling
    -   [x] 3.2 Buat `utils/shell.py` - implement fungsi `run_command_with_progress(cmd, description)` dengan Rich progress bar
    -   [x] 3.3 Buat `utils/shell.py` - implement fungsi `is_installed(package)` untuk cek apakah package sudah terinstall
    -   [x] 3.4 Buat `utils/shell.py` - implement fungsi `is_service_running(service)` untuk cek status systemd service
    -   [x] 3.5 Buat `utils/logger.py` - implement basic logging ke console dengan Rich formatting
    -   [x] 3.6 Buat `utils/shell.py` - implement fungsi `check_root()` untuk validasi sudo/root privileges

-   [x] 4.0 Implement System Setup Module

    -   [x] 4.1 Buat `modules/system.py` - implement fungsi `show_menu()` untuk submenu System Setup
    -   [x] 4.2 Implement fungsi `update_system()` - jalankan `apt update && apt upgrade -y` dengan progress
    -   [x] 4.3 Implement fungsi `install_basic_tools()` - install curl, git, unzip, software-properties-common
    -   [x] 4.4 Implement fungsi `show_system_info()` - tampilkan OS version, hostname, IP address
    -   [x] 4.5 Pastikan semua operasi idempotent (cek dulu sebelum install)

-   [x] 5.0 Implement Domain & Nginx Module

    -   [x] 5.1 Buat `modules/webserver.py` - implement fungsi `show_menu()` untuk submenu Domain & Nginx
    -   [x] 5.2 Implement fungsi `install_nginx()` - install Nginx jika belum ada
    -   [x] 5.3 Buat `templates/nginx_vhost.conf` - template Nginx virtual host dengan placeholder {{domain}}, {{root_path}}
    -   [x] 5.4 Implement fungsi `add_domain(domain, root_path)` - generate config dari template, simpan ke sites-available
    -   [x] 5.5 Implement fungsi `enable_domain(domain)` - buat symlink ke sites-enabled dan reload Nginx
    -   [x] 5.6 Implement fungsi `list_domains()` - tampilkan daftar domain dari sites-available dalam tabel
    -   [x] 5.7 Implement fungsi `remove_domain(domain)` - hapus config dan symlink, reload Nginx
    -   [x] 5.8 Implement fungsi `reload_nginx()` - reload Nginx service

-   [x] 6.0 Implement PHP Runtime Module

    -   [x] 6.1 Buat `modules/runtime.py` - implement fungsi `show_php_menu()` untuk submenu PHP
    -   [x] 6.2 Implement fungsi `add_php_ppa()` - tambahkan PPA ondrej/php
    -   [x] 6.3 Implement fungsi `install_php(version)` - install PHP versi 8.3, 8.4, 8.5 dengan FPM
    -   [x] 6.4 Implement fungsi `install_php_extensions(version)` - install Laravel extensions
    -   [x] 6.5 Implement fungsi `switch_php_version(version)` - switch default PHP CLI version
    -   [x] 6.6 Implement fungsi `list_php_versions()` - tampilkan PHP versions yang terinstall dan status FPM service
    -   [x] 6.7 Implement fungsi `show_php_info(version)` - tampilkan extensions yang terinstall untuk versi tertentu
    -   [x] 6.8 Implement fungsi `install_composer()` - install/update Composer globally
    -   [x] 6.9 Implement fungsi `set_site_php(domain, version)` - per-site PHP isolation via Nginx

-   [x] 7.0 Implement Node.js Runtime Module

    -   [x] 7.1 Buat `modules/runtime.py` - implement fungsi `show_nodejs_menu()` untuk submenu Node.js
    -   [x] 7.2 Implement fungsi `install_nvm()` - install NVM via curl script jika belum ada
    -   [x] 7.3 Implement fungsi `install_nodejs(version)` - install Node.js versi tertentu atau LTS via NVM
    -   [x] 7.4 Implement fungsi `switch_nodejs_version(version)` - switch default Node.js version
    -   [x] 7.5 Implement fungsi `list_nodejs_versions()` - tampilkan Node.js versions yang terinstall via NVM
    -   [x] 7.6 Implement fungsi `show_nodejs_info()` - tampilkan current Node.js dan npm version

-   [x] 8.0 Implement Database Module

    -   [x] 8.1 Buat `modules/database.py` - implement fungsi `show_menu()` untuk submenu Database
    -   [x] 8.2 Implement fungsi `install_postgresql()` - install PostgreSQL server
    -   [x] 8.3 Implement fungsi `install_mariadb()` - install MariaDB server
    -   [x] 8.4 Implement fungsi `secure_mariadb_installation()` - jalankan mysql_secure_installation secara automated
    -   [x] 8.5 Implement fungsi `create_database(engine, db_name)` - buat database baru
    -   [x] 8.6 Implement fungsi `create_user(engine, username, password, db_name)` - buat user dengan privileges
    -   [x] 8.7 Implement fungsi `list_databases(engine)` - tampilkan daftar database dalam tabel
    -   [x] 8.8 Implement fungsi `delete_database(engine, db_name)` - hapus database
    -   [x] 8.9 Implement fungsi `delete_user(engine, username)` - hapus database user

-   [x] 9.0 Implement Email Module

    -   [x] 9.1 Buat `modules/email.py` - implement fungsi `show_menu()` untuk submenu Email
    -   [x] 9.2 Implement fungsi `install_postfix()` - install Postfix dengan konfigurasi "Internet Site"
    -   [x] 9.3 Implement fungsi `configure_postfix(hostname, domain)` - konfigurasi hostname dan domain
    -   [x] 9.4 Implement fungsi `setup_send_only()` - konfigurasi Postfix untuk send-only mode
    -   [x] 9.5 Implement fungsi `show_postfix_status()` - tampilkan status Postfix service
    -   [x] 9.6 Implement fungsi `test_email(recipient)` - kirim test email untuk verifikasi

-   [x] 10.0 Implement Monitoring Module

    -   [x] 10.1 Buat `modules/monitor.py` - implement fungsi `show_menu()` untuk submenu Monitoring
    -   [x] 10.2 Implement fungsi `get_cpu_usage()` - ambil CPU usage percentage menggunakan psutil
    -   [x] 10.3 Implement fungsi `get_ram_usage()` - ambil RAM usage (percentage dan MB) menggunakan psutil
    -   [x] 10.4 Implement fungsi `get_disk_usage()` - ambil Disk usage percentage menggunakan psutil
    -   [x] 10.5 Implement fungsi `get_status_color(percentage)` - return warna berdasarkan threshold (hijau < 70, kuning 70-85, merah > 85)
    -   [x] 10.6 Implement fungsi `show_status()` - tampilkan semua metrics dalam Rich table dengan status indicators

-   [x] 11.0 Create Install Script & Distribution
    -   [x] 11.1 Buat `install.sh` - script untuk download vexo-cli dari GitHub
    -   [x] 11.2 Implement logic untuk clone/download ke `/opt/vexo-cli`
    -   [x] 11.3 Implement logic untuk install Python dependencies dengan pip
    -   [x] 11.4 Implement logic untuk create symlink `/usr/local/bin/vexo` ke `main.py`
    -   [x] 11.5 Implement logic untuk set proper permissions (executable)
    -   [x] 11.6 Tambahkan pengecekan Python version (minimal 3.8)
    -   [x] 11.7 Tambahkan pengecekan apakah pip terinstall
    -   [x] 11.8 Update `main.py` - implement main loop yang menghubungkan semua modules
    -   [x] 11.9 Test full flow: (user responsibility per AGENTS.md)

-   [x] 12.0 Implement Firewall Module (UFW)
    -   [x] 12.1 Buat `modules/firewall.py` dengan `show_menu()`
    -   [x] 12.2 Implement `install_ufw()`
    -   [x] 12.3 Implement `enable_firewall()` dengan default rules (SSH, HTTP, HTTPS)
    -   [x] 12.4 Implement `disable_firewall()` dengan warning
    -   [x] 12.5 Implement `add_port()` dan `add_email_ports()` (25/587/465)
    -   [x] 12.6 Implement `remove_port()` dan `list_rules()`
    -   [x] 12.7 Implement `show_status()` dan export module

-   [x] 13.0 Implement SSL Module (Let's Encrypt)
    -   [x] 13.1 Buat `modules/ssl.py` dengan `show_menu()`
    -   [x] 13.2 Implement `install_certbot()`
    -   [x] 13.3 Implement `enable_ssl()` dan `enable_ssl_interactive()`
    -   [x] 13.4 Implement `list_certificates()`
    -   [x] 13.5 Implement `renew_certificates()` dan `revoke_certificate()`
    -   [x] 13.6 Implement `show_renewal_status()` dan export module

-   [x] 14.0 Implement Fail2ban Module
    -   [x] 14.1 Buat `modules/fail2ban.py` dengan `show_menu()`
    -   [x] 14.2 Implement `install_fail2ban()` dengan auto-detect jails (SSH/Nginx/Postfix)
    -   [x] 14.3 Implement `show_status()` dan `view_jail_status()`
    -   [x] 14.4 Implement `list_banned_ips()`
    -   [x] 14.5 Implement `unban_ip()` dan `ban_ip()`
    -   [x] 14.6 Implement `configure_settings()` (bantime/findtime/maxretry)
    -   [x] 14.7 Export module ke `__init__.py`

-   [x] 15.0 Security Integration
    -   [x] 15.1 Update `main.py` dengan 3 menu entry baru (Firewall, SSL, Fail2ban)
    -   [x] 15.2 Update task list
