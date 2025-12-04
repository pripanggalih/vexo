# Node.js Project Management Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Node.js project management features including project discovery, quick commands, project info, dependency audit, and cleanup tools.

**Architecture:** Create `modules/runtime/nodejs/projects.py` with functions for managing multiple Node.js projects on the server.

**Tech Stack:** Python, npm, package.json parsing

**Dependency:** Requires `2025-01-15-nodejs-01-pm2.md` to be executed first (creates folder structure).

---

## Task 1: Create Project Management Module

**Files:**
- Create: `modules/runtime/nodejs/projects.py`

**Step 1: Create projects.py**

```python
"""Node.js project management."""

import os
import json

from config import DEFAULT_WEB_ROOT
from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from modules.runtime.nodejs.utils import run_with_nvm, run_with_nvm_realtime, is_pm2_installed


def show_projects_menu():
    """Display Project Management submenu."""
    options = [
        ("list", "1. List Projects"),
        ("commands", "2. Quick Commands"),
        ("info", "3. Project Info"),
        ("audit", "4. Dependency Audit"),
        ("clean", "5. Clean Project"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "list": list_projects,
        "commands": quick_commands,
        "info": project_info,
        "audit": dependency_audit,
        "clean": clean_project,
    }
    
    run_menu_loop("Project Management", options, handlers)


def list_projects():
    """List Node.js projects on the server."""
    clear_screen()
    show_header()
    show_panel("Node.js Projects", title="Project Management", style="cyan")
    
    console.print("Scanning for Node.js projects...")
    console.print()
    
    # Scan common directories
    search_dirs = [
        DEFAULT_WEB_ROOT,
        "/var/www",
        "/home",
        "/opt",
    ]
    
    projects = []
    
    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue
        
        # Walk directory tree (limited depth)
        for root, dirs, files in os.walk(search_dir):
            # Limit depth
            depth = root.replace(search_dir, '').count(os.sep)
            if depth > 3:
                dirs.clear()
                continue
            
            # Skip common non-project directories
            dirs[:] = [d for d in dirs if d not in [
                'node_modules', '.git', 'dist', 'build', '.cache',
                'coverage', '.next', '.nuxt', 'vendor'
            ]]
            
            if 'package.json' in files:
                pkg_path = os.path.join(root, 'package.json')
                try:
                    with open(pkg_path, 'r') as f:
                        pkg = json.load(f)
                    
                    projects.append({
                        'path': root,
                        'name': pkg.get('name', os.path.basename(root)),
                        'version': pkg.get('version', '?'),
                        'main': pkg.get('main', 'index.js'),
                        'scripts': list(pkg.get('scripts', {}).keys()),
                        'deps': len(pkg.get('dependencies', {})),
                        'dev_deps': len(pkg.get('devDependencies', {})),
                    })
                except Exception:
                    pass
    
    if not projects:
        show_info("No Node.js projects found.")
        console.print()
        console.print(f"[dim]Searched: {', '.join(search_dirs)}[/dim]")
        press_enter_to_continue()
        return
    
    # Check PM2 status
    pm2_apps = {}
    if is_pm2_installed():
        result = run_with_nvm("pm2 jlist")
        if result and result.returncode == 0:
            try:
                for proc in json.loads(result.stdout):
                    pm2_env = proc.get("pm2_env", {})
                    cwd = pm2_env.get("pm_cwd", "")
                    status = pm2_env.get("status", "unknown")
                    pm2_apps[cwd] = status
            except json.JSONDecodeError:
                pass
    
    columns = [
        {"name": "Project", "style": "cyan"},
        {"name": "Version", "style": "white"},
        {"name": "Deps", "justify": "right"},
        {"name": "PM2 Status", "justify": "center"},
        {"name": "Path"},
    ]
    
    rows = []
    for proj in projects:
        pm2_status = pm2_apps.get(proj['path'], "")
        if pm2_status == "online":
            status_str = "[green]online[/green]"
        elif pm2_status == "stopped":
            status_str = "[yellow]stopped[/yellow]"
        elif pm2_status:
            status_str = f"[red]{pm2_status}[/red]"
        else:
            status_str = "[dim]-[/dim]"
        
        path_display = proj['path']
        if len(path_display) > 35:
            path_display = "..." + path_display[-32:]
        
        rows.append([
            proj['name'],
            proj['version'],
            str(proj['deps'] + proj['dev_deps']),
            status_str,
            path_display,
        ])
    
    show_table(f"Found: {len(projects)} project(s)", columns, rows, show_header=True)
    press_enter_to_continue()


def quick_commands():
    """Run quick npm/yarn commands for a project."""
    clear_screen()
    show_header()
    show_panel("Quick Commands", title="Project Management", style="cyan")
    
    # Get project directory
    project_dir = text_input("Project directory:")
    if not project_dir:
        return
    
    project_dir = project_dir.strip()
    
    if not os.path.exists(os.path.join(project_dir, "package.json")):
        show_error("No package.json found in directory.")
        press_enter_to_continue()
        return
    
    # Read package.json for scripts
    try:
        with open(os.path.join(project_dir, "package.json"), "r") as f:
            pkg = json.load(f)
        scripts = pkg.get("scripts", {})
    except Exception:
        scripts = {}
    
    # Detect package manager
    has_yarn = os.path.exists(os.path.join(project_dir, "yarn.lock"))
    has_pnpm = os.path.exists(os.path.join(project_dir, "pnpm-lock.yaml"))
    
    if has_pnpm:
        pm = "pnpm"
    elif has_yarn:
        pm = "yarn"
    else:
        pm = "npm"
    
    console.print(f"[dim]Package manager: {pm}[/dim]")
    console.print()
    
    # Common commands + scripts
    commands = [
        (f"{pm} install", "Install dependencies"),
        (f"{pm} run build", "Build project"),
        (f"{pm} run start", "Start project"),
        (f"{pm} run dev", "Start development server"),
        (f"{pm} test", "Run tests"),
    ]
    
    # Add custom scripts
    for script_name in scripts:
        if script_name not in ["install", "build", "start", "dev", "test"]:
            commands.append((f"{pm} run {script_name}", f"Script: {script_name}"))
    
    commands.append(("(Enter custom command)", "Custom"))
    
    options = [f"{cmd} ({desc})" for cmd, desc in commands]
    
    choice = select_from_list("Select Command", "Run:", options)
    if not choice:
        return
    
    if "custom" in choice.lower():
        cmd = text_input(f"Enter command (will run in {project_dir}):")
        if not cmd:
            return
    else:
        cmd = choice.split(" (")[0]
    
    console.print()
    console.print(f"[bold]Running:[/bold] {cmd}")
    console.print(f"[dim]Directory: {project_dir}[/dim]")
    console.print()
    
    run_with_nvm_realtime(f"cd {project_dir} && {cmd}", "")
    
    press_enter_to_continue()


def project_info():
    """Show detailed information about a project."""
    clear_screen()
    show_header()
    show_panel("Project Info", title="Project Management", style="cyan")
    
    project_dir = text_input("Project directory:")
    if not project_dir:
        return
    
    project_dir = project_dir.strip()
    pkg_path = os.path.join(project_dir, "package.json")
    
    if not os.path.exists(pkg_path):
        show_error("No package.json found.")
        press_enter_to_continue()
        return
    
    try:
        with open(pkg_path, "r") as f:
            pkg = json.load(f)
    except Exception as e:
        show_error(f"Failed to read package.json: {e}")
        press_enter_to_continue()
        return
    
    clear_screen()
    show_header()
    show_panel(pkg.get("name", "Project Info"), title="Project Management", style="cyan")
    
    # Basic info
    console.print("[bold]Basic Information:[/bold]")
    console.print(f"  Name: {pkg.get('name', 'N/A')}")
    console.print(f"  Version: {pkg.get('version', 'N/A')}")
    console.print(f"  Description: {pkg.get('description', 'N/A')}")
    console.print(f"  Main: {pkg.get('main', 'index.js')}")
    console.print(f"  License: {pkg.get('license', 'N/A')}")
    console.print()
    
    # Engine requirements
    engines = pkg.get("engines", {})
    if engines:
        console.print("[bold]Engine Requirements:[/bold]")
        for engine, version in engines.items():
            console.print(f"  {engine}: {version}")
        console.print()
    
    # Dependencies count
    deps = pkg.get("dependencies", {})
    dev_deps = pkg.get("devDependencies", {})
    console.print("[bold]Dependencies:[/bold]")
    console.print(f"  Production: {len(deps)}")
    console.print(f"  Development: {len(dev_deps)}")
    console.print()
    
    # Scripts
    scripts = pkg.get("scripts", {})
    if scripts:
        console.print("[bold]Available Scripts:[/bold]")
        for name, cmd in list(scripts.items())[:10]:
            cmd_display = cmd[:50] + "..." if len(cmd) > 50 else cmd
            console.print(f"  [cyan]{name}[/cyan]: {cmd_display}")
        if len(scripts) > 10:
            console.print(f"  [dim]... and {len(scripts) - 10} more[/dim]")
        console.print()
    
    # Check node_modules
    node_modules = os.path.join(project_dir, "node_modules")
    if os.path.exists(node_modules):
        # Get size
        import subprocess
        result = subprocess.run(
            f"du -sh {node_modules} 2>/dev/null | cut -f1",
            shell=True, capture_output=True, text=True
        )
        size = result.stdout.strip() if result.returncode == 0 else "?"
        console.print(f"[bold]node_modules:[/bold] {size}")
    else:
        console.print("[bold]node_modules:[/bold] [yellow]Not installed[/yellow]")
    
    # Last modified
    import time
    mtime = os.path.getmtime(pkg_path)
    modified = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))
    console.print(f"[bold]Last modified:[/bold] {modified}")
    
    press_enter_to_continue()


def dependency_audit():
    """Run security audit on project dependencies."""
    clear_screen()
    show_header()
    show_panel("Dependency Audit", title="Project Management", style="cyan")
    
    project_dir = text_input("Project directory:")
    if not project_dir:
        return
    
    project_dir = project_dir.strip()
    
    if not os.path.exists(os.path.join(project_dir, "package.json")):
        show_error("No package.json found.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print("Running security audit...")
    console.print()
    
    # Run npm audit
    result = run_with_nvm(f"cd {project_dir} && npm audit --json 2>/dev/null")
    
    if result is None:
        show_error("Failed to run audit.")
        press_enter_to_continue()
        return
    
    try:
        audit = json.loads(result.stdout)
    except json.JSONDecodeError:
        # npm audit might not return valid JSON on error
        show_info("Running audit in verbose mode...")
        console.print()
        run_with_nvm_realtime(f"cd {project_dir} && npm audit", "")
        press_enter_to_continue()
        return
    
    # Parse audit results
    vulnerabilities = audit.get("vulnerabilities", {})
    metadata = audit.get("metadata", {})
    
    total = metadata.get("vulnerabilities", {})
    critical = total.get("critical", 0)
    high = total.get("high", 0)
    moderate = total.get("moderate", 0)
    low = total.get("low", 0)
    
    console.print("[bold]Vulnerability Summary:[/bold]")
    console.print()
    
    if critical > 0:
        console.print(f"  [bold red]Critical: {critical}[/bold red]")
    if high > 0:
        console.print(f"  [red]High: {high}[/red]")
    if moderate > 0:
        console.print(f"  [yellow]Moderate: {moderate}[/yellow]")
    if low > 0:
        console.print(f"  [dim]Low: {low}[/dim]")
    
    total_vulns = critical + high + moderate + low
    
    if total_vulns == 0:
        show_success("No vulnerabilities found!")
    else:
        console.print()
        console.print(f"[bold]Total: {total_vulns} vulnerabilities[/bold]")
        
        # Show details for critical/high
        if critical > 0 or high > 0:
            console.print()
            console.print("[bold]Critical/High Severity:[/bold]")
            for name, info in vulnerabilities.items():
                severity = info.get("severity", "")
                if severity in ["critical", "high"]:
                    via = info.get("via", [])
                    if via and isinstance(via[0], dict):
                        title = via[0].get("title", "Unknown")
                    else:
                        title = str(via[0]) if via else "Unknown"
                    console.print(f"  • [cyan]{name}[/cyan]: {title}")
        
        console.print()
        if confirm_action("Try to auto-fix vulnerabilities?"):
            console.print()
            run_with_nvm_realtime(f"cd {project_dir} && npm audit fix", "Fixing...")
    
    press_enter_to_continue()


def clean_project():
    """Clean project (remove node_modules, cache, etc.)."""
    clear_screen()
    show_header()
    show_panel("Clean Project", title="Project Management", style="cyan")
    
    project_dir = text_input("Project directory:")
    if not project_dir:
        return
    
    project_dir = project_dir.strip()
    
    if not os.path.exists(os.path.join(project_dir, "package.json")):
        show_error("No package.json found.")
        press_enter_to_continue()
        return
    
    # Calculate sizes
    items_to_clean = []
    
    node_modules = os.path.join(project_dir, "node_modules")
    if os.path.exists(node_modules):
        size = _get_dir_size(node_modules)
        items_to_clean.append(("node_modules", node_modules, size))
    
    dist_dir = os.path.join(project_dir, "dist")
    if os.path.exists(dist_dir):
        size = _get_dir_size(dist_dir)
        items_to_clean.append(("dist", dist_dir, size))
    
    build_dir = os.path.join(project_dir, "build")
    if os.path.exists(build_dir):
        size = _get_dir_size(build_dir)
        items_to_clean.append(("build", build_dir, size))
    
    cache_dir = os.path.join(project_dir, ".cache")
    if os.path.exists(cache_dir):
        size = _get_dir_size(cache_dir)
        items_to_clean.append((".cache", cache_dir, size))
    
    next_dir = os.path.join(project_dir, ".next")
    if os.path.exists(next_dir):
        size = _get_dir_size(next_dir)
        items_to_clean.append((".next", next_dir, size))
    
    nuxt_dir = os.path.join(project_dir, ".nuxt")
    if os.path.exists(nuxt_dir):
        size = _get_dir_size(nuxt_dir)
        items_to_clean.append((".nuxt", nuxt_dir, size))
    
    if not items_to_clean:
        show_info("Nothing to clean.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Items to clean:[/bold]")
    console.print()
    
    total_size = 0
    for name, path, size in items_to_clean:
        total_size += size
        console.print(f"  • {name}: {_format_size(size)}")
    
    console.print()
    console.print(f"[bold]Total: {_format_size(total_size)}[/bold]")
    console.print()
    
    options = [
        "Remove all",
        "Remove node_modules only",
        "Select items to remove",
    ]
    
    choice = select_from_list("Action", "What to clean?", options)
    if not choice:
        return
    
    to_remove = []
    
    if "all" in choice:
        to_remove = [path for _, path, _ in items_to_clean]
    elif "node_modules" in choice:
        to_remove = [path for name, path, _ in items_to_clean if name == "node_modules"]
    else:
        # Select items
        for name, path, size in items_to_clean:
            if confirm_action(f"Remove {name} ({_format_size(size)})?"):
                to_remove.append(path)
    
    if not to_remove:
        show_info("Nothing selected.")
        press_enter_to_continue()
        return
    
    show_warning(f"This will delete {len(to_remove)} item(s)!")
    if not confirm_action("Continue?"):
        press_enter_to_continue()
        return
    
    console.print()
    
    import shutil
    for path in to_remove:
        name = os.path.basename(path)
        try:
            console.print(f"Removing {name}...")
            shutil.rmtree(path)
            console.print(f"  [green]✓[/green] Removed {name}")
        except Exception as e:
            console.print(f"  [red]✗[/red] Failed: {e}")
    
    console.print()
    show_success("Cleanup complete!")
    
    if confirm_action("Reinstall dependencies?"):
        console.print()
        run_with_nvm_realtime(f"cd {project_dir} && npm install", "Installing...")
    
    press_enter_to_continue()


def _get_dir_size(path):
    """Get directory size in bytes."""
    total = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _format_size(size_bytes):
    """Format size in bytes to human readable."""
    if size_bytes >= 1024 ** 3:
        return f"{size_bytes / 1024 ** 3:.1f} GB"
    elif size_bytes >= 1024 ** 2:
        return f"{size_bytes / 1024 ** 2:.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes} B"
```

**Step 2: Commit**

```bash
git add modules/runtime/nodejs/projects.py
git commit -m "feat(runtime): add Node.js project management"
```

---

## Task 2: Create install.py from original runtime.py

**Files:**
- Create: `modules/runtime/nodejs/install.py`

**Step 1: Create install.py**

Copy Node.js install/switch/list functions from original `runtime.py`:
- `install_nvm_interactive()`, `install_nvm()`
- `install_nodejs_interactive()`, `install_nodejs()`
- `switch_nodejs_interactive()`, `switch_nodejs_version()`
- `list_nodejs_versions()`
- `show_nodejs_info()`
- `_get_npm_version_for_node()`

Update imports to use `modules.runtime.nodejs.utils`.

**Step 2: Delete original runtime.py**

```bash
rm modules/runtime.py
```

**Step 3: Commit**

```bash
git add modules/runtime/nodejs/install.py
git commit -m "refactor(runtime): complete nodejs folder migration"
```

---

## Execution Handoff

**Plans saved to:**
1. `docs/plans/2025-01-15-nodejs-01-pm2.md`
2. `docs/plans/2025-01-15-nodejs-02-global-packages.md`
3. `docs/plans/2025-01-15-nodejs-03-app-deployment.md`
4. `docs/plans/2025-01-15-nodejs-04-monitoring.md`
5. `docs/plans/2025-01-15-nodejs-05-project-management.md`

**Execution Order:**
1. Execute all PHP plans first (creates `modules/runtime/php/` structure)
2. Execute `nodejs-01-pm2.md` (creates `modules/runtime/nodejs/` structure)
3. Execute remaining Node.js plans in order (02-05)

**Total new features:** ~25 features for Node.js runtime management
