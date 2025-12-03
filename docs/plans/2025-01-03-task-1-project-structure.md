# Task 1.0: Setup Project Structure & Dependencies - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Setup the foundational project structure and dependencies for vexo-cli VPS management application.

**Architecture:** Modular Python CLI with separated concerns - UI layer (`ui/`), business logic (`modules/`), utilities (`utils/`), and configuration templates (`templates/`). Entry point is `main.py` with global config in `config.py`.

**Tech Stack:** Python 3.8+, Rich (UI), Prompt Toolkit (interactivity), psutil (system monitoring)

**Note:** This is development environment only. No testing or installation steps - testing will be done manually on target VPS.

---

## Task 1.1: Create Folder Structure

**Files:**
- Create: `ui/` directory
- Create: `modules/` directory
- Create: `utils/` directory
- Create: `templates/` directory

**Step 1: Create all directories**

```bash
mkdir -p ui modules utils templates
```

**Step 2: Commit**

```bash
git add -A && git commit -m "chore: create folder structure for modular architecture"
```

---

## Task 1.2: Create Package Init Files

**Files:**
- Create: `ui/__init__.py`
- Create: `modules/__init__.py`
- Create: `utils/__init__.py`

**Step 1: Create ui/__init__.py**

```python
"""UI components for vexo-cli - menus, styles, and reusable widgets."""
```

**Step 2: Create modules/__init__.py**

```python
"""Business logic modules for vexo-cli - system, webserver, runtime, database, email."""
```

**Step 3: Create utils/__init__.py**

```python
"""Utility functions for vexo-cli - shell commands, logging."""
```

**Step 4: Commit**

```bash
git add -A && git commit -m "chore: add __init__.py to make directories Python packages"
```

---

## Task 1.3: Create requirements.txt

**Files:**
- Create: `requirements.txt`

**Step 1: Create requirements.txt**

```
rich>=13.0.0
prompt_toolkit>=3.0.0
psutil>=5.9.0
```

**Step 2: Commit**

```bash
git add requirements.txt && git commit -m "chore: add requirements.txt with core dependencies"
```

---

## Task 1.4: Create config.py

**Files:**
- Create: `config.py`

**Step 1: Create config.py**

```python
"""Global configuration for vexo-cli."""

import os

# Application Info
APP_NAME = "vexo-cli"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "VPS Management CLI for Ubuntu/Debian"

# Paths - Nginx
NGINX_SITES_AVAILABLE = "/etc/nginx/sites-available"
NGINX_SITES_ENABLED = "/etc/nginx/sites-enabled"
NGINX_CONFIG_PATH = "/etc/nginx/nginx.conf"

# Paths - PHP
PHP_FPM_PATH = "/etc/php"
PHP_VERSIONS = ["8.1", "8.2", "8.3"]

# Paths - Application
APP_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(APP_DIR, "templates")

# Default web root
DEFAULT_WEB_ROOT = "/var/www"

# NVM
NVM_DIR = os.path.expanduser("~/.nvm")
NVM_INSTALL_URL = "https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh"

# Database
MYSQL_CONFIG_PATH = "/etc/mysql/mysql.conf.d/mysqld.cnf"

# Postfix
POSTFIX_CONFIG_PATH = "/etc/postfix/main.cf"

# UI Colors (for reference, actual styling in ui/styles.py)
COLORS = {
    "primary": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "info": "blue",
}

# Thresholds for monitoring (percentage)
THRESHOLDS = {
    "good": 70,      # < 70% = green
    "warning": 85,   # 70-85% = yellow
                     # > 85% = red
}
```

**Step 2: Commit**

```bash
git add config.py && git commit -m "feat: add config.py with global constants and paths"
```

---

## Task 1.5: Create main.py Entry Point

**Files:**
- Create: `main.py`

**Step 1: Create main.py**

```python
#!/usr/bin/env python3
"""
vexo-cli - VPS Management CLI for Ubuntu/Debian

Entry point for the application.
"""

import sys
import os

from config import APP_NAME, APP_VERSION


def check_python_version():
    """Ensure Python 3.8+ is being used."""
    if sys.version_info < (3, 8):
        print(f"Error: {APP_NAME} requires Python 3.8 or higher.")
        print(f"Current version: {sys.version}")
        sys.exit(1)


def check_root():
    """Check if running with root/sudo privileges."""
    if os.geteuid() != 0:
        print(f"Warning: {APP_NAME} requires root privileges for most operations.")
        print("Consider running with: sudo python3 main.py")


def main():
    """Main entry point."""
    check_python_version()
    check_root()
    
    print(f"Welcome to {APP_NAME} v{APP_VERSION}")
    print("VPS Management CLI for Ubuntu/Debian")
    print("-" * 40)
    print("Menu system coming soon...")
    

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
```

**Step 2: Make executable**

```bash
chmod +x main.py
```

**Step 3: Commit**

```bash
git add main.py && git commit -m "feat: add main.py entry point with version and root checks"
```

---

## Task 1.6: Update task list

Mark Task 1.0 and all sub-tasks as completed in `tasks/tasks-vexo-cli.md`

---

## Summary

After completing this plan:

```
vexo-cli/
├── main.py              ✅ Entry point with version/root checks
├── config.py            ✅ Global constants and paths
├── requirements.txt     ✅ Dependencies (rich, prompt_toolkit, psutil)
├── ui/
│   └── __init__.py      ✅ Package init
├── modules/
│   └── __init__.py      ✅ Package init
├── utils/
│   └── __init__.py      ✅ Package init
└── templates/           ✅ Empty, ready for Nginx templates
```
