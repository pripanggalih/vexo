<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# cukup

Ini adalah **Cetak Biru (Blueprint) dan Rencana Implementasi** lengkap untuk aplikasi CLI VPS Management Anda. Laporan ini dirancang untuk menjadi panduan arsitektur dan teknis agar Anda bisa langsung mulai coding dengan fondasi yang kuat.

### **Executive Summary**

Anda akan membangun **"VPS Control Panel CLI"**—sebuah aplikasi Python interaktif yang berjalan di atas VPS Ubuntu/Debian. Tidak seperti CLI biasa yang berbasis perintah teks kaku, aplikasi ini menggunakan antarmuka berbasis menu (menu-driven) yang navigable, visual yang modern (tabel, warna, progress bar), dan arsitektur modular.

**Key Characteristics:**

* **Framework:** Python + Rich (UI) + Prompt Toolkit (Interactivity).
* **Target OS:** Ubuntu/Debian (Fokus pada stabilitas).
* **UX Style:** Dashboard interaktif di terminal (Navigasi panah atas/bawah).
* **Fitur Utama:** Instalasi auto, Domain, Nginx, PHP Multi-version, Node.js (NVM), Database, \& Email (Postfix).

***

### **1. Arsitektur Sistem**

Struktur folder ini dirancang agar aplikasi tetap rapi saat fitur bertambah banyak (Modular Design).

```plaintext
vps-cli/
├── main.py                  # Entry point (File utama yang dijalankan)
├── requirements.txt         # Daftar library (Rich, Prompt Toolkit, dll)
├── config.py                # Global configuration (Path, Konstanta)
├── ui/                      # Folder khusus UI/Tampilan
│   ├── __init__.py
│   ├── menu.py              # Logic untuk render menu interaktif
│   ├── styles.py            # Tema warna & style guide
│   └── components.py        # Reusable widgets (Header, Footer, Status Bar)
├── modules/                 # Folder logika bisnis (Brain of the app)
│   ├── __init__.py
│   ├── system.py            # OS Setup, Update, Upgrade
│   ├── webserver.py         # Nginx & Domain management
│   ├── runtime.py           # PHP & Node.js management
│   ├── database.py          # MySQL/MariaDB logic
│   └── email.py             # Postfix logic
└── utils/                   # Folder helper functions
    ├── __init__.py
    ├── shell.py             # Wrapper untuk subprocess (Jalankan command bash)
    └── logger.py            # System logging
```


***

### **2. Tech Stack \& Dependencies**

Buat file `requirements.txt` dengan isi berikut untuk menginstall library yang diperlukan:

```text
rich==13.7.0            # Untuk tampilan UI cantik (Table, Panel, Progress)
prompt_toolkit==3.0.43  # Untuk navigasi menu interaktif (Arrow keys)
psutil==5.9.8           # Untuk monitoring system (CPU/RAM)
sh==2.0.6               # (Opsional) Wrapper mudah untuk command shell
```


***

### **3. Kode Implementasi (Starter Code)**

Berikut adalah kode **Skeleton (Kerangka Dasar)** yang sudah fungsional. Kode ini membangun sistem menu interaktif dan contoh integrasi modul. Anda bisa langsung copy-paste dan jalankan.

#### **A. `utils/shell.py` (Eksekusi Perintah Sistem)**

File ini penting agar aplikasi Python bisa "berbicara" dengan Linux.

```python
import subprocess
from rich.console import Console

console = Console()

def run_command(command, silent=False):
    """Menjalankan perintah shell dan mengembalikan output."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if not silent:
            console.print(f"[bold red]Error executing command:[/bold red] {command}")
            console.print(f"[red]{e.stderr}[/red]")
        return None
```


#### **B. `ui/menu.py` (Sistem Menu Interaktif)**

Inti dari UX aplikasi Anda. Menggunakan `prompt_toolkit` untuk seleksi menu.

```python
from prompt_toolkit.shortcuts import radiolist_dialog
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel

console = Console()

# Custom Style untuk Menu (Warna Cyan/Teal)
style = Style.from_dict({
    'dialog': 'bg:#222222',
    'dialog.body': 'bg:#222222 #ffffff',
    'dialog.shadow': 'bg:#000000',
    'button.focused': 'bg:#00ffff #000000',  # Cyan focus
})

def show_main_menu():
    """Menampilkan menu utama dan mengembalikan pilihan user."""
    result = radiolist_dialog(
        title="VPS CLI Manager",
        text="Pilih modul yang ingin dikelola:",
        values=[
            ("setup", "1. System Setup & Update"),
            ("domain", "2. Domain & Nginx Management"),
            ("runtime", "3. PHP & Node.js Runtime"),
            ("email", "4. Email Server (Postfix)"),
            ("monitor", "5. System Monitoring"),
            ("exit", "6. Keluar")
        ],
        style=style
    ).run()
    return result
```


#### **C. `modules/monitor.py` (Contoh Modul Monitoring)**

Contoh bagaimana menampilkan data dengan format Tabel menggunakan Rich.

```python
import psutil
from rich.table import Table
from rich.panel import Panel
from rich.console import Console

console = Console()

def show_status():
    """Menampilkan status server dalam format tabel cantik."""
    
    # Ambil data system
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # Buat Tabel
    table = Table(title="System Resources", expand=True, border_style="cyan")
    table.add_column("Metric", style="bold white")
    table.add_column("Value", justify="right")
    table.add_column("Status", justify="center")

    # Logic warna status
    cpu_color = "green" if cpu < 70 else "red"
    ram_color = "green" if ram.percent < 80 else "yellow"

    table.add_row("CPU Usage", f"{cpu}%", f"[{cpu_color}]●[/{cpu_color}]")
    table.add_row("RAM Usage", f"{ram.percent}% ({ram.used // (1024**2)}MB used)", f"[{ram_color}]●[/{ram_color}]")
    table.add_row("Disk Usage", f"{disk.percent}%", "green")

    console.print(Panel(table, title="[bold cyan]Real-time Monitor[/bold cyan]", border_style="blue"))
    input("\nTekan Enter untuk kembali ke menu...")
```


#### **D. `main.py` (Aplikasi Utama)**

File pengikat yang menyatukan semuanya.

```python
import sys
import time
from rich.console import Console
from rich.progress import track
from ui.menu import show_main_menu
from modules import monitor
# Import modules lain nanti disini: from modules import setup, webserver...

console = Console()

def main():
    console.clear()
    console.print("[bold cyan]Welcome to VPS CLI Manager[/bold cyan]", justify="center")
    
    while True:
        choice = show_main_menu()
        
        if choice == "monitor":
            monitor.show_status()
        
        elif choice == "setup":
            console.print("[yellow]Fitur Setup sedang dalam pengembangan...[/yellow]")
            time.sleep(1)
            
        elif choice == "domain":
            console.print("[yellow]Fitur Domain sedang dalam pengembangan...[/yellow]")
            time.sleep(1)
            
        elif choice == "runtime":
            console.print("[yellow]Fitur PHP/Node.js sedang dalam pengembangan...[/yellow]")
            time.sleep(1)
            
        elif choice == "exit" or choice is None:
            console.print("[bold red]Bye![/bold red]")
            sys.exit()
            
        console.clear()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[red]Force Exit detected.[/red]")
        sys.exit()
```


***

### **4. Roadmap Pengembangan Fitur**

Sekarang setelah kerangka dasar jadi, berikut urutan logis untuk mengisi file-file di folder `modules/`:

#### **Tahap 1: System Setup (`modules/setup.py`)**

* **Task:** Jalankan `apt update && apt upgrade`.
* **Task:** Install basic tools: `curl`, `git`, `unzip`, `software-properties-common`.
* **UX:** Gunakan `rich.progress` bar saat install berjalan agar user tidak bosan menunggu.


#### **Tahap 2: Runtime Management (`modules/runtime.py`)**

* **PHP:** Gunakan PPA `ondrej/php` untuk install multi-version PHP (8.1, 8.2, 8.3).
* **Node.js:**

1. Cek apakah `nvm` ada.
2. Jika tidak, `curl | bash` script install NVM.
3. Command install: `nvm install --lts`.


#### **Tahap 3: Webserver \& Domain (`modules/webserver.py`)**

* **Task:** Install Nginx.
* **Logic:** Buat template string untuk file config Nginx block (vhost).
* **Action:** Saat user "Add Domain", script akan:

1. Copy template config.
2. Replace `{{domain_name}}` dengan input user.
3. Simpan di `/etc/nginx/sites-available/`.
4. Symlink ke `sites-enabled`.
5. Reload Nginx.


#### **Tahap 4: Email (`modules/email.py`)**

* **Task:** Install `postfix` dan `dovecot`.
* **Complexity:** Ini bagian tersulit. Mulai dengan "Send only" setup dulu sebelum full receiving setup.

***

### **Tips Penting**

1. **Sudo Privileges:** Karena aplikasi ini mengelola sistem (install apt, restart service), pastikan menjalankannya dengan `sudo python3 main.py`. Tambahkan pengecekan di awal script `main.py` jika user bukan root/sudo.
2. **Error Handling:** Selalu bungkus eksekusi command shell dalam blok `try-except` (seperti di contoh `utils/shell.py`) agar aplikasi tidak crash jika internet mati atau command gagal.
3. **Idempotency:** Buat script setup yang "pintar". Cek dulu "apakah Nginx sudah terinstall?" sebelum mencoba menginstallnya lagi.

Anda bisa mulai dengan membuat folder structure dan copy-paste kode di atas. Setelah itu, Anda bisa mulai mengisi logika `modules/setup.py` sebagai langkah pertama. Selamat coding

