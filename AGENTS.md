# AGENTS.md - vexo-cli

## Project Overview

**vexo-cli** adalah VPS Management CLI berbasis Python untuk Ubuntu/Debian. Aplikasi ini menggunakan interface menu interaktif (bukan command-based) dengan tampilan visual modern.

## Tech Stack

- **Language:** Python 3.8+
- **UI:** Rich (tables, panels, progress bars, colors)
- **Interactivity:** Prompt Toolkit (menu navigation, dialogs)
- **System Monitoring:** psutil
- **Target OS:** Ubuntu/Debian

## Project Structure

```
vexo-cli/
├── main.py                  # Entry point
├── config.py                # Global configuration & constants
├── requirements.txt         # Python dependencies
├── ui/                      # UI layer
│   ├── __init__.py
│   ├── menu.py              # Menu rendering (prompt_toolkit)
│   ├── styles.py            # Color themes & styles
│   └── components.py        # Reusable widgets (header, tables, panels)
├── modules/                 # Business logic
│   ├── __init__.py
│   ├── system.py            # System setup & updates
│   ├── webserver.py         # Nginx & domain management
│   ├── runtime.py           # PHP & Node.js management
│   ├── database.py          # MySQL/MariaDB management
│   └── email.py             # Postfix email server
├── utils/                   # Utilities
│   ├── __init__.py
│   ├── shell.py             # Shell command wrapper (subprocess)
│   └── logger.py            # Logging utility
├── templates/               # Config templates
│   └── nginx_vhost.conf     # Nginx virtual host template
├── docs/
│   └── plans/               # Implementation plans
└── tasks/                   # PRD & task tracking
    ├── prd-vexo-cli.md
    └── tasks-vexo-cli.md
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

## Task Tracking

- PRD: `tasks/prd-vexo-cli.md`
- Tasks: `tasks/tasks-vexo-cli.md`
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
