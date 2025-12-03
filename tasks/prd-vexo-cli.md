# PRD: vexo-cli - VPS Management CLI

## 1. Introduction/Overview

**vexo-cli** adalah aplikasi Command Line Interface (CLI) berbasis Python untuk mengelola VPS Ubuntu/Debian. Berbeda dengan CLI konvensional yang menggunakan perintah teks, vexo-cli menggunakan antarmuka menu interaktif (menu-driven) dengan navigasi arrow keys, tampilan visual modern (tabel, warna, progress bar), dan arsitektur modular.

**Problem Statement:** Developer individu yang mengelola VPS pribadi seringkali harus mengingat banyak command Linux untuk setup server, install dependencies, konfigurasi Nginx, PHP, Node.js, database, dan email. Proses ini memakan waktu, rawan error, dan tidak efisien.

**Solution:** vexo-cli menyediakan interface terpusat yang intuitif untuk mengelola semua aspek VPS dari satu aplikasi terminal.

---

## 2. Goals

1. **Simplifikasi Server Management** - Mengurangi kompleksitas pengelolaan VPS menjadi navigasi menu sederhana
2. **Otomatisasi Setup** - Mengotomatiskan proses instalasi dan konfigurasi komponen server
3. **Konsistensi Konfigurasi** - Memastikan konfigurasi server mengikuti best practices
4. **Developer Experience** - Memberikan visual feedback yang jelas (progress bar, status indicator, tabel informatif)
5. **Single Server Focus** - Mengelola satu VPS dengan efisien dan mendalam

---

## 3. User Stories

### System Setup

-   Sebagai developer, saya ingin mengupdate dan mengupgrade sistem dengan satu klik agar server selalu up-to-date
-   Sebagai developer, saya ingin menginstall basic tools (curl, git, unzip) secara otomatis saat setup awal

### Domain & Nginx

-   Sebagai developer, saya ingin menambah domain baru dengan mudah tanpa harus menulis config Nginx manual
-   Sebagai developer, saya ingin melihat daftar semua domain yang sudah dikonfigurasi
-   Sebagai developer, saya ingin menghapus domain yang tidak digunakan lagi

### PHP Runtime

-   Sebagai developer, saya ingin menginstall multiple versi PHP (8.3, 8.4, 8.5) untuk berbagai project
-   Sebagai developer, saya ingin switch default PHP version dengan mudah
-   Sebagai developer, saya ingin melihat PHP extensions yang terinstall

### Node.js Runtime

-   Sebagai developer, saya ingin menginstall Node.js via NVM untuk flexibility versi
-   Sebagai developer, saya ingin switch Node.js version sesuai kebutuhan project

### Database

-   Sebagai developer, saya ingin menginstall MySQL/MariaDB dengan konfigurasi aman
-   Sebagai developer, saya ingin membuat database dan user baru dengan mudah
-   Sebagai developer, saya ingin melihat daftar database yang ada

### Email Server

-   Sebagai developer, saya ingin setup Postfix untuk mengirim email dari aplikasi saya
-   Sebagai developer, saya ingin mengkonfigurasi SMTP settings dengan guided setup

### System Monitoring

-   Sebagai developer, saya ingin melihat penggunaan CPU, RAM, dan Disk dalam tampilan visual
-   Sebagai developer, saya ingin mendapat indikator status (hijau/kuning/merah) untuk resource usage

---

## 4. Functional Requirements

### 4.1 Core Application

1. Aplikasi harus berjalan di terminal dengan interface menu interaktif menggunakan arrow keys
2. Aplikasi harus menampilkan header/branding "vexo-cli" saat startup
3. Aplikasi harus memiliki navigasi menu utama dengan opsi: System Setup, Domain & Nginx, PHP & Node.js, Database, Email, Monitoring, Exit
4. Aplikasi harus menampilkan feedback visual (progress bar, spinner) saat menjalankan operasi panjang
5. Aplikasi harus menangani error dengan graceful dan menampilkan pesan error yang informatif
6. Aplikasi harus memvalidasi bahwa dijalankan dengan sudo/root privileges

### 4.2 System Setup Module

7. Sistem harus dapat menjalankan `apt update && apt upgrade` dengan progress indicator
8. Sistem harus dapat menginstall basic tools: `curl`, `git`, `unzip`, `software-properties-common`
9. Sistem harus mengecek apakah tool sudah terinstall sebelum mencoba install ulang (idempotent)

### 4.3 Domain & Nginx Module

10. Sistem harus dapat menginstall Nginx jika belum ada
11. Sistem harus dapat menambah domain baru dengan input: domain name, root directory
12. Sistem harus generate Nginx config dari template dan menyimpan di `/etc/nginx/sites-available/`
13. Sistem harus membuat symlink ke `/etc/nginx/sites-enabled/`
14. Sistem harus reload Nginx setelah perubahan config
15. Sistem harus dapat menampilkan daftar domain yang dikonfigurasi dalam format tabel
16. Sistem harus dapat menghapus domain (remove config, symlink)

### 4.4 PHP Runtime Module

17. Sistem harus dapat menambahkan PPA `ondrej/php` untuk akses multi-version PHP
18. Sistem harus dapat menginstall PHP versi 8.1, 8.2, atau 8.3 sesuai pilihan user
19. Sistem harus menginstall PHP-FPM dan extensions umum (mysql, curl, mbstring, xml, zip, gd)
20. Sistem harus dapat switch default PHP CLI version
21. Sistem harus dapat menampilkan PHP version yang terinstall dan status service-nya

### 4.5 Node.js Runtime Module

22. Sistem harus dapat menginstall NVM (Node Version Manager) jika belum ada
23. Sistem harus dapat menginstall Node.js LTS atau versi spesifik via NVM
24. Sistem harus dapat switch default Node.js version
25. Sistem harus dapat menampilkan Node.js dan npm version yang aktif

### 4.6 Database Module

26. Sistem harus dapat menginstall MySQL atau MariaDB sesuai pilihan user
27. Sistem harus dapat menjalankan `mysql_secure_installation` secara automated
28. Sistem harus dapat membuat database baru dengan input nama database
29. Sistem harus dapat membuat database user dengan privileges ke database tertentu
30. Sistem harus dapat menampilkan daftar database dalam format tabel
31. Sistem harus dapat menghapus database dan user

### 4.7 Email Module

32. Sistem harus dapat menginstall Postfix dengan konfigurasi "Internet Site"
33. Sistem harus dapat mengkonfigurasi hostname dan domain untuk email
34. Sistem harus dapat menampilkan status Postfix service
35. Sistem harus menyediakan opsi untuk setup "send-only" mode (tanpa receiving)

### 4.8 Monitoring Module

36. Sistem harus dapat menampilkan CPU usage percentage dengan status indicator
37. Sistem harus dapat menampilkan RAM usage (percentage dan MB used) dengan status indicator
38. Sistem harus dapat menampilkan Disk usage percentage
39. Sistem harus menampilkan data dalam format tabel dengan warna (hijau < 70%, kuning 70-85%, merah > 85%)

---

## 5. Non-Goals (Out of Scope)

-   **Multi-server management** - Fokus hanya pada single VPS
-   **Backup & Restore** - Tidak termasuk di versi ini
-   **SSL/Let's Encrypt integration** - Mungkin di versi mendatang
-   **Firewall management (UFW)** - Tidak termasuk di versi ini
-   **Docker/Container management** - Tidak termasuk
-   **GUI/Web interface** - CLI only
-   **Support untuk OS selain Ubuntu/Debian** - Hanya Ubuntu/Debian
-   **Cloud provider API integration** - Tidak ada integrasi dengan AWS, DO, dll

---

## 6. Design Considerations

### UI/UX Style

-   **Color Scheme:** Cyan/Teal sebagai warna utama, dengan aksen hijau (success), kuning (warning), merah (error)
-   **Menu Style:** Radio list dialog dengan arrow key navigation
-   **Data Display:** Rich tables dengan border dan column alignment
-   **Feedback:** Progress bars untuk operasi panjang, status indicators (●) dengan warna
-   **Layout:** Panel dengan judul untuk grouping informasi

### Terminal Requirements

-   Minimum terminal width: 80 columns
-   Support untuk 256 colors
-   UTF-8 encoding support

---

## 7. Technical Considerations

### Tech Stack

-   **Language:** Python 3.8+
-   **UI Library:** Rich (tables, panels, progress bars, colors)
-   **Interactivity:** Prompt Toolkit (menu navigation, dialogs)
-   **System Info:** psutil (CPU, RAM, Disk monitoring)
-   **Shell Execution:** subprocess module dengan proper error handling

### Project Structure

```
vexo-cli/
├── main.py                  # Entry point
├── requirements.txt         # Dependencies
├── config.py                # Global configuration
├── ui/
│   ├── menu.py              # Menu rendering logic
│   ├── styles.py            # Color themes
│   └── components.py        # Reusable widgets
├── modules/
│   ├── system.py            # OS Setup module
│   ├── webserver.py         # Nginx & Domain module
│   ├── runtime.py           # PHP & Node.js module
│   ├── database.py          # MySQL/MariaDB module
│   └── email.py             # Postfix module
└── utils/
    ├── shell.py             # Shell command wrapper
    └── logger.py            # Logging utility
```

### Distribution Method

-   Download via raw GitHub URL menggunakan curl/wget
-   One-liner install script: `curl -fsSL https://raw.githubusercontent.com/[user]/vexo-cli/main/install.sh | sudo bash`
-   Install script akan:
    1. Clone/download repository ke `/opt/vexo-cli`
    2. Install Python dependencies
    3. Create symlink `/usr/local/bin/vexo`
    4. Set proper permissions

### Dependencies

```
rich==latest
prompt_toolkit==latest
psutil==latest
```

### Security Considerations

-   Semua operasi sensitif memerlukan sudo/root
-   Password database tidak disimpan dalam plain text
-   Logging tidak mencatat credentials
-   Input validation untuk semua user input (domain names, usernames, etc.)

---

## 8. Success Metrics

1. **Installation Success Rate** - 95%+ user berhasil install tanpa error
2. **Task Completion Time** - Setup domain baru < 2 menit (vs 10+ menit manual)
3. **Error Rate** - < 5% operasi gagal karena bug aplikasi
4. **Code Quality** - Semua modules memiliki error handling yang proper
5. **User Adoption** - Digunakan secara regular oleh developer target

---

## 9. Open Questions

1. **PHP Extensions** - Apakah ada PHP extensions spesifik yang wajib diinclude selain yang umum?
2. **Database Default** - Apakah default ke MySQL atau MariaDB?
3. **Postfix Configuration** - Seberapa detail konfigurasi email yang dibutuhkan? Apakah cukup send-only?
4. **Logging** - Apakah perlu menyimpan log operasi ke file untuk debugging?
5. **Update Mechanism** - Bagaimana mekanisme update vexo-cli ke versi terbaru?

---

## Appendix: Development Roadmap

### Phase 1: Foundation

-   [ ] Setup project structure
-   [ ] Implement core UI (menu system, styles)
-   [ ] Implement utils (shell wrapper, logger)
-   [ ] Implement System Setup module

### Phase 2: Web Stack

-   [ ] Implement Nginx & Domain module
-   [ ] Implement PHP Runtime module
-   [ ] Implement Node.js Runtime module

### Phase 3: Data & Communication

-   [ ] Implement Database module
-   [ ] Implement Email module

### Phase 4: Polish

-   [ ] Implement Monitoring module
-   [ ] Create install script
-   [ ] Testing & bug fixes
-   [ ] Documentation
