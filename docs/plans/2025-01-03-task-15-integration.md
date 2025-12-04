# Task 15.0: Security Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate firewall, ssl, and fail2ban modules into main.py menu and update task list.

**Architecture:** Update main.py main_loop() to include 3 new menu entries (Firewall, SSL, Fail2ban). Update task list with new tasks.

**Tech Stack:** Existing main.py structure, modules/__init__.py

---

## Sub-tasks Overview

| Sub-task | Description | Commit |
|----------|-------------|--------|
| 15.1 | Update main.py with new menu entries | Yes |
| 15.2 | Update tasks-vexo.md with new tasks | Yes |

**Total: 2 sub-tasks, 2 commits**

---

## Task 15.1: Update main.py with new menu entries

**Files:**
- Modify: `main.py`

**Step 1: Add imports for new modules**

Update imports in `main.py`:

```python
from modules import system
from modules import webserver
from modules import runtime
from modules import database
from modules import email
from modules import monitor
from modules import firewall
from modules import ssl
from modules import fail2ban
```

**Step 2: Update main_loop() menu options**

```python
def main_loop():
    """Main menu loop."""
    while True:
        clear_screen()
        show_header()
        show_root_warning()
        
        choice = show_main_menu(
            title=f"{APP_NAME} v{APP_VERSION}",
            options=[
                ("system", "1. System Setup & Update"),
                ("webserver", "2. Domain & Nginx"),
                ("php", "3. PHP Runtime"),
                ("nodejs", "4. Node.js Runtime"),
                ("database", "5. Database"),
                ("email", "6. Email Server"),
                ("monitor", "7. System Monitoring"),
                ("firewall", "8. Firewall (UFW)"),
                ("ssl", "9. SSL Certificates"),
                ("fail2ban", "10. Fail2ban"),
                ("exit", "✕ Exit"),
            ],
        )
        
        if choice == "system":
            system.show_menu()
        elif choice == "webserver":
            webserver.show_menu()
        elif choice == "php":
            runtime.show_php_menu()
        elif choice == "nodejs":
            runtime.show_nodejs_menu()
        elif choice == "database":
            database.show_menu()
        elif choice == "email":
            email.show_menu()
        elif choice == "monitor":
            monitor.show_menu()
        elif choice == "firewall":
            firewall.show_menu()
        elif choice == "ssl":
            ssl.show_menu()
        elif choice == "fail2ban":
            fail2ban.show_menu()
        elif choice == "exit" or choice is None:
            clear_screen()
            console.print(f"[cyan]Thank you for using {APP_NAME}![/cyan]")
            console.print("[dim]Goodbye.[/dim]")
            break
```

**Step 3: Update show_help() with new modules**

```python
def show_help():
    """Show help message."""
    print(f"{APP_NAME} v{APP_VERSION}")
    print(APP_DESCRIPTION)
    print()
    print("Usage:")
    print("  sudo vexo              Run vexo")
    print("  vexo --help            Show this help")
    print("  vexo --version         Show version")
    print()
    print("Modules:")
    print("  1. System Setup        Update system, install tools")
    print("  2. Domain & Nginx      Manage domains and web server")
    print("  3. PHP Runtime         PHP versions, Composer")
    print("  4. Node.js Runtime     NVM, Node.js versions")
    print("  5. Database            PostgreSQL, MariaDB")
    print("  6. Email Server        Postfix configuration")
    print("  7. System Monitoring   CPU, RAM, Disk usage")
    print("  8. Firewall            UFW firewall management")
    print("  9. SSL Certificates    Let's Encrypt / Certbot")
    print("  10. Fail2ban           Brute force protection")
```

**Step 4: Commit**

```bash
git add main.py
git commit -m "feat(main): add firewall, ssl, fail2ban menu entries"
```

---

## Task 15.2: Update tasks-vexo.md

**Files:**
- Modify: `tasks/tasks-vexo.md`

**Step 1: Add new tasks to task list**

Append to tasks-vexo.md after Task 11.0:

```markdown
-   [x] 12.0 Implement Firewall Module

    -   [x] 12.1 Buat `modules/firewall.py` dengan `show_menu()`
    -   [x] 12.2 Implement `install_ufw()`
    -   [x] 12.3 Implement `enable_firewall()` dengan default rules (SSH, HTTP, HTTPS)
    -   [x] 12.4 Implement `disable_firewall()` dengan warning
    -   [x] 12.5 Implement `add_port()` dan `add_email_ports()`
    -   [x] 12.6 Implement `remove_port()` dan `list_rules()`
    -   [x] 12.7 Implement `show_status()`

-   [x] 13.0 Implement SSL Module

    -   [x] 13.1 Buat `modules/ssl.py` dengan `show_menu()`
    -   [x] 13.2 Implement `install_certbot()`
    -   [x] 13.3 Implement `enable_ssl()` dan `enable_ssl_interactive()`
    -   [x] 13.4 Implement `list_certificates()`
    -   [x] 13.5 Implement `renew_certificates()` dan `revoke_certificate()`
    -   [x] 13.6 Implement `show_renewal_status()`

-   [x] 14.0 Implement Fail2ban Module

    -   [x] 14.1 Buat `modules/fail2ban.py` dengan `show_menu()`
    -   [x] 14.2 Implement `install_fail2ban()` dengan auto-detect jails
    -   [x] 14.3 Implement `show_status()` dan `view_jail_status()`
    -   [x] 14.4 Implement `list_banned_ips()`
    -   [x] 14.5 Implement `unban_ip()` dan `ban_ip()`
    -   [x] 14.6 Implement `configure_settings()`
    -   [x] 14.7 Export module ke `__init__.py`

-   [x] 15.0 Security Integration

    -   [x] 15.1 Update `main.py` dengan 3 menu entry baru
    -   [x] 15.2 Update task list
```

**Step 2: Commit**

```bash
git add tasks/tasks-vexo.md
git commit -m "docs: add security hardening tasks (12.0-15.0) - ALL SECURITY TASKS DONE"
```

---

## Summary

After completion:

**Updated main.py:**
- 10 main menu options (was 7)
- New entries: Firewall (8), SSL (9), Fail2ban (10)
- Updated help text

**Task List:**
- 4 new tasks (12.0-15.0)
- ~23 new sub-tasks
- Total project tasks: 16 (was 12)

**Final Menu Structure:**
```
vexo v1.0.0
├── 1. System Setup & Update
├── 2. Domain & Nginx
├── 3. PHP Runtime
├── 4. Node.js Runtime
├── 5. Database
├── 6. Email Server
├── 7. System Monitoring
├── 8. Firewall (UFW)          ← NEW
├── 9. SSL Certificates        ← NEW
├── 10. Fail2ban               ← NEW
└── ✕ Exit
```
