# Setup Wizard Progress Bar Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add live progress bar with real-time status updates during setup wizard installation, showing download/unpack/setup phases.

**Architecture:** Create `run_apt_with_progress()` function in `utils/shell.py` that parses apt output in real-time and updates a Rich Live display. Modify `modules/setup.py` to use this new function for package installation.

**Tech Stack:** Rich (Progress, Live, Console), subprocess.Popen for real-time output streaming

---

## Task 1: Add `run_apt_with_progress()` function to utils/shell.py

**Files:**
- Modify: `/Users/galih/Projects/vexo/utils/shell.py` (add new function at end of file)

**Step 1: Add the new function**

Add this function at the end of `utils/shell.py`, before any if `__name__` block (if exists):

```python
def run_apt_with_progress(packages, step_info="Installing"):
    """
    Run apt install with live progress bar showing download/unpack/setup phases.
    
    Args:
        packages: List of package names to install
        step_info: Header text (e.g., "[2/9] PHP 8.3")
    
    Returns:
        bool: True if installation successful, False otherwise
    """
    import re
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.live import Live
    from rich.console import Group
    from rich.text import Text
    
    if not packages:
        return True
    
    total_packages = len(packages)
    packages_str = " ".join(packages)
    
    # Track progress
    processed = 0
    current_status = "Preparing..."
    current_phase = ""  # ↓ download, ⚙ unpack, ✦ setup
    
    # Regex patterns for apt output
    patterns = {
        "download": re.compile(r"Get:\d+.*?(\S+)\s+\S+\s+\S+\s+\[([^\]]+)\]"),
        "unpack": re.compile(r"Unpacking\s+(\S+)"),
        "setup": re.compile(r"Setting up\s+(\S+)"),
    }
    
    # Track which packages we've seen to count progress
    seen_packages = set()
    
    def make_display():
        """Generate the display content."""
        # Progress bar
        progress_pct = (processed / total_packages * 100) if total_packages > 0 else 0
        bar_width = 40
        filled = int(bar_width * processed / total_packages) if total_packages > 0 else 0
        bar = "█" * filled + "░" * (bar_width - filled)
        
        # Build display
        lines = []
        lines.append(Text(step_info, style="bold"))
        lines.append(Text(f"[{bar}] {progress_pct:.0f}% ({processed}/{total_packages} packages)", style="cyan"))
        if current_status:
            lines.append(Text(f"     {current_phase} {current_status}", style="dim"))
        
        return Group(*lines)
    
    # Run apt install
    cmd = f"DEBIAN_FRONTEND=noninteractive apt-get install -y {packages_str}"
    
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"},
    )
    
    with Live(make_display(), refresh_per_second=10, console=console) as live:
        for line in process.stdout:
            line = line.strip()
            
            # Check download phase
            match = patterns["download"].search(line)
            if match:
                pkg_name = match.group(1).split(":")[0]  # Remove arch suffix
                size = match.group(2)
                current_phase = "↓"
                current_status = f"Downloading {pkg_name} ({size})"
                live.update(make_display())
                continue
            
            # Check unpack phase
            match = patterns["unpack"].search(line)
            if match:
                pkg_name = match.group(1).split(":")[0]
                current_phase = "⚙"
                current_status = f"Unpacking {pkg_name}..."
                live.update(make_display())
                continue
            
            # Check setup phase
            match = patterns["setup"].search(line)
            if match:
                pkg_name = match.group(1).split(":")[0]
                # Count unique packages being set up as progress
                if pkg_name not in seen_packages:
                    seen_packages.add(pkg_name)
                    # Only count if it's one of our requested packages (base name match)
                    for req_pkg in packages:
                        if pkg_name.startswith(req_pkg.split("-")[0]):
                            processed = min(processed + 1, total_packages)
                            break
                current_phase = "✦"
                current_status = f"Setting up {pkg_name}..."
                live.update(make_display())
                continue
        
        # Final update - show complete
        processed = total_packages
        current_phase = "✓"
        current_status = "Complete"
        live.update(make_display())
    
    process.wait()
    return process.returncode == 0
```

**Step 2: Commit**

```bash
git add utils/shell.py
git commit -m "feat(shell): add run_apt_with_progress for live installation progress"
```

---

## Task 2: Update setup.py to use progress bar for package installation

**Files:**
- Modify: `/Users/galih/Projects/vexo/modules/setup.py`

**Step 1: Update import**

Find the import section at the top of `modules/setup.py` and add `run_apt_with_progress` to the imports from `utils.shell`:

Change:
```python
from utils.shell import run_command, is_installed
```

To:
```python
from utils.shell import run_command, run_apt_with_progress, is_installed
```

**Step 2: Modify `install_component()` function**

Find the section in `install_component()` that installs packages (around line 130-140). 

Change this block:
```python
    # Install packages
    if "packages" in component:
        packages = " ".join(component["packages"])
        result = run_command(
            f"apt install -y {packages}",
            check=False, silent=False
        )
        if result.returncode != 0:
            handle_error("E1006", f"{name} installation failed", details=result.stderr if result.stderr else None)
            return False
```

To:
```python
    # Install packages with progress bar
    if "packages" in component:
        success = run_apt_with_progress(
            component["packages"],
            step_info=f"Installing {name}"
        )
        if not success:
            handle_error("E1006", f"{name} installation failed")
            return False
```

**Step 3: Commit**

```bash
git add modules/setup.py
git commit -m "feat(setup): use progress bar for package installation"
```

---

## Task 3: Update `run_setup()` to pass step info to components

**Files:**
- Modify: `/Users/galih/Projects/vexo/modules/setup.py`

**Step 1: Add step tracking to install_component**

Modify the `install_component()` function signature to accept step info:

Change:
```python
def install_component(component):
    """
    Install a single component.
    
    Args:
        component: Component dict from COMPONENTS
    
    Returns:
        bool: True if successful
    """
```

To:
```python
def install_component(component, step_current=1, step_total=1):
    """
    Install a single component.
    
    Args:
        component: Component dict from COMPONENTS
        step_current: Current step number (e.g., 2)
        step_total: Total steps (e.g., 9)
    
    Returns:
        bool: True if successful
    """
```

**Step 2: Update the progress bar call to include step info**

In `install_component()`, update the `run_apt_with_progress` call:

Change:
```python
        success = run_apt_with_progress(
            component["packages"],
            step_info=f"Installing {name}"
        )
```

To:
```python
        success = run_apt_with_progress(
            component["packages"],
            step_info=f"[{step_current}/{step_total}] {name}"
        )
```

**Step 3: Update `run_setup()` to pass step numbers**

Find the for loop in `run_setup()` and update the `install_component()` call:

Change:
```python
        if install_component(comp):
            success_count += 1
```

To:
```python
        if install_component(comp, step_current=i, step_total=total):
            success_count += 1
```

**Step 4: Commit**

```bash
git add modules/setup.py
git commit -m "feat(setup): add step counter to progress display"
```

---

## Task 4: Handle apt update with progress

**Files:**
- Modify: `/Users/galih/Projects/vexo/utils/shell.py`

**Step 1: Add `run_apt_update_with_progress()` function**

Add this function after `run_apt_with_progress()` in `utils/shell.py`:

```python
def run_apt_update_with_progress():
    """
    Run apt update with live progress indicator.
    
    Returns:
        bool: True if successful
    """
    import re
    from rich.live import Live
    from rich.text import Text
    from rich.console import Group
    
    current_status = "Updating package lists..."
    repo_count = 0
    
    def make_display():
        lines = []
        lines.append(Text("Updating package lists", style="bold"))
        lines.append(Text(f"     ↓ {current_status}", style="dim"))
        if repo_count > 0:
            lines.append(Text(f"     ({repo_count} repositories)", style="dim"))
        return Group(*lines)
    
    # Pattern to match repository fetches
    pattern = re.compile(r"(Get|Hit|Ign):\d+\s+(\S+)")
    
    process = subprocess.Popen(
        "apt-get update",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    
    with Live(make_display(), refresh_per_second=10, console=console) as live:
        for line in process.stdout:
            line = line.strip()
            match = pattern.search(line)
            if match:
                action = match.group(1)
                url = match.group(2)
                # Shorten URL for display
                if len(url) > 50:
                    url = url[:47] + "..."
                current_status = f"{url}"
                repo_count += 1
                live.update(make_display())
        
        current_status = "Complete"
        live.update(make_display())
    
    process.wait()
    return process.returncode == 0
```

**Step 2: Commit**

```bash
git add utils/shell.py
git commit -m "feat(shell): add run_apt_update_with_progress"
```

---

## Task 5: Use apt update progress in setup.py

**Files:**
- Modify: `/Users/galih/Projects/vexo/modules/setup.py`

**Step 1: Update import**

Update the import to include the new function:

Change:
```python
from utils.shell import run_command, run_apt_with_progress, is_installed
```

To:
```python
from utils.shell import run_command, run_apt_with_progress, run_apt_update_with_progress, is_installed
```

**Step 2: Update `run_setup()` to use progress for apt update**

Find in `run_setup()`:
```python
    # Update apt first
    show_info("Updating package lists...")
    run_command("apt update", check=False, silent=True)
```

Change to:
```python
    # Update apt first with progress
    run_apt_update_with_progress()
```

**Step 3: Also update PPA apt update in `install_component()`**

Find in `install_component()`:
```python
        run_command("apt update", check=False, silent=True)
```

Change to:
```python
        run_apt_update_with_progress()
```

**Step 4: Commit**

```bash
git add modules/setup.py
git commit -m "feat(setup): use progress bar for apt update"
```

---

## Task 6: Final integration commit

**Step 1: Final commit with all changes**

```bash
git add -A
git commit -m "feat(setup): complete progress bar implementation for setup wizard

- Add run_apt_with_progress() for live package installation progress
- Add run_apt_update_with_progress() for repository updates
- Show download/unpack/setup phases with icons
- Display step counter [x/y] and package count
- Real-time progress bar updates"
```

---

## Summary of Changes

| File | Changes |
|------|---------|
| `utils/shell.py` | Added `run_apt_with_progress()` and `run_apt_update_with_progress()` functions |
| `modules/setup.py` | Updated `install_component()` and `run_setup()` to use new progress functions |

## Expected Result

```
[2/9] PHP 8.3
[████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 32% (5/15 packages)
     ↓ Downloading php8.3-mbstring (245 KB)
```

Progress bar updates in-place as installation proceeds through phases:
- `↓` Download phase
- `⚙` Unpack phase  
- `✦` Setup phase
- `✓` Complete
