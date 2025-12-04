# Fail2ban Phase 5: Filter Management + Testing

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement filter management with create, edit, test capabilities including regex helper and live testing against log files.

**Architecture:** List system and custom filters, provide wizard for creating custom filters with regex validation and testing against actual log files.

**Tech Stack:** Python, Rich (tables, syntax highlighting), fail2ban-regex for testing

---

## Task 1: Implement Filter Management Module

**Files:**
- Modify: `modules/fail2ban/filters.py`

**Step 1: Implement full filters.py**

```python
"""Filter management for fail2ban module."""

import os
import re

from rich.syntax import Syntax
from rich.panel import Panel

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_success,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, require_root

from .common import (
    FILTER_D_DIR,
    VEXO_FAIL2BAN_DIR,
    ensure_data_dir,
)


# Common regex patterns for helper
REGEX_PATTERNS = {
    "IP Address": "<HOST>",
    "Any characters": ".*",
    "Word characters": r"\w+",
    "Digits": r"\d+",
    "HTTP Methods": "(GET|POST|PUT|DELETE|HEAD)",
    "HTTP Status": r"\d{3}",
    "Date YYYY-MM-DD": r"\d{4}-\d{2}-\d{2}",
    "Time HH:MM:SS": r"\d{2}:\d{2}:\d{2}",
    "Quoted string": r'"[^"]*"',
    "Start of line": "^",
    "End of line": "$",
}


def show_menu():
    """Display filter management menu."""
    def get_status():
        custom = _get_custom_filters()
        return f"{len(custom)} custom filters"
    
    def get_options():
        return [
            ("list", "1. List Filters"),
            ("view", "2. View Filter"),
            ("create", "3. Create Filter"),
            ("edit", "4. Edit Filter"),
            ("test", "5. Test Filter"),
            ("regex", "6. Regex Helper"),
            ("delete", "7. Delete Filter"),
            ("back", "← Back"),
        ]
    
    handlers = {
        "list": list_filters,
        "view": view_filter,
        "create": create_filter,
        "edit": edit_filter,
        "test": test_filter,
        "regex": regex_helper,
        "delete": delete_filter,
    }
    
    run_menu_loop("Filter Management", get_options, handlers, get_status)


def list_filters():
    """List all installed filters."""
    clear_screen()
    show_header()
    show_panel("Installed Filters", title="Filter Management", style="cyan")
    
    system_filters = _get_system_filters()
    custom_filters = _get_custom_filters()
    
    columns = [
        {"name": "Filter Name", "style": "cyan"},
        {"name": "Type"},
        {"name": "Description", "style": "dim"},
    ]
    
    rows = []
    
    # Add system filters
    for name in sorted(system_filters)[:20]:  # Limit to 20
        rows.append([name, "[dim]system[/dim]", ""])
    
    if len(system_filters) > 20:
        rows.append(["...", "", f"({len(system_filters) - 20} more system filters)"])
    
    # Add custom filters
    for name in sorted(custom_filters):
        rows.append([name, "[green]custom[/green]", ""])
    
    show_table(f"Filters ({len(system_filters)} system, {len(custom_filters)} custom)", columns, rows)
    
    press_enter_to_continue()


def view_filter():
    """View filter content."""
    clear_screen()
    show_header()
    show_panel("View Filter", title="Filter Management", style="cyan")
    
    all_filters = _get_system_filters() + _get_custom_filters()
    
    if not all_filters:
        show_info("No filters found.")
        press_enter_to_continue()
        return
    
    # Group by type for selection
    options = []
    for name in sorted(_get_custom_filters()):
        options.append(f"{name} (custom)")
    for name in sorted(_get_system_filters())[:30]:
        options.append(f"{name} (system)")
    
    selected = select_from_list(
        title="Select Filter",
        message="Choose filter to view:",
        options=options
    )
    
    if not selected:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Parse selection
    name = selected.rsplit(" (", 1)[0]
    
    filter_path = os.path.join(FILTER_D_DIR, f"{name}.conf")
    
    if not os.path.exists(filter_path):
        show_error(f"Filter file not found: {filter_path}")
        press_enter_to_continue()
        return
    
    try:
        with open(filter_path, 'r') as f:
            content = f.read()
        
        console.print(f"[bold]Filter: {name}[/bold]")
        console.print(f"[dim]Path: {filter_path}[/dim]")
        console.print()
        
        syntax = Syntax(content, "ini", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=f"{name}.conf", border_style="cyan"))
        
    except Exception as e:
        show_error(f"Error reading filter: {e}")
    
    press_enter_to_continue()


def create_filter():
    """Create a new custom filter."""
    clear_screen()
    show_header()
    show_panel("Create Filter", title="Filter Management", style="cyan")
    
    console.print("[bold]Custom Filter Wizard[/bold]")
    console.print("[dim]Create a filter with failregex pattern to match log entries.[/dim]")
    console.print()
    
    # Step 1: Filter name
    name = text_input(
        title="Step 1: Filter Name",
        message="Enter filter name (lowercase, no spaces):"
    )
    
    if not name:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    name = name.lower().replace(" ", "-")
    
    # Check if exists
    if _filter_exists(name):
        show_error(f"Filter '{name}' already exists.")
        press_enter_to_continue()
        return
    
    # Step 2: Description
    description = text_input(
        title="Step 2: Description",
        message="Filter description (optional):",
        default=""
    )
    
    # Step 3: Failregex
    console.print()
    console.print("[bold]Step 3: Failregex Pattern[/bold]")
    console.print("[dim]Use <HOST> to capture the IP address.[/dim]")
    console.print("[dim]Example: ^<HOST> .* \"POST /login\" .* 401[/dim]")
    console.print()
    console.print("[dim]Tip: Use 'Regex Helper' menu for common patterns.[/dim]")
    console.print()
    
    failregex_lines = []
    console.print("[dim]Enter failregex patterns (empty line to finish):[/dim]")
    
    while True:
        line = text_input(
            title="Failregex",
            message=f"Pattern #{len(failregex_lines)+1}:",
            default=""
        )
        
        if not line:
            break
        
        # Validate regex
        try:
            re.compile(line.replace("<HOST>", r"(?P<host>\S+)"))
            failregex_lines.append(line)
        except re.error as e:
            show_warning(f"Invalid regex: {e}")
    
    if not failregex_lines:
        show_warning("No patterns added. Cancelled.")
        press_enter_to_continue()
        return
    
    # Step 4: Ignoreregex (optional)
    console.print()
    ignoreregex_lines = []
    
    if confirm_action("Add ignore patterns?", default=False):
        console.print("[dim]Enter ignoreregex patterns (empty line to finish):[/dim]")
        
        while True:
            line = text_input(
                title="Ignoreregex",
                message=f"Ignore pattern #{len(ignoreregex_lines)+1}:",
                default=""
            )
            
            if not line:
                break
            
            ignoreregex_lines.append(line)
    
    # Preview
    console.print()
    console.print("[bold]Preview:[/bold]")
    
    filter_content = _generate_filter_content(name, description, failregex_lines, ignoreregex_lines)
    syntax = Syntax(filter_content, "ini", theme="monokai")
    console.print(Panel(syntax, title=f"{name}.conf", border_style="cyan"))
    
    if not confirm_action("Create this filter?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Create filter file
    filter_path = os.path.join(FILTER_D_DIR, f"{name}.conf")
    
    try:
        with open(filter_path, 'w') as f:
            f.write(filter_content)
        
        show_success(f"Filter '{name}' created!")
        
        if confirm_action("Test filter against a log file?"):
            _test_filter_interactive(name)
    except Exception as e:
        show_error(f"Failed to create filter: {e}")
    
    press_enter_to_continue()


def edit_filter():
    """Edit an existing custom filter."""
    clear_screen()
    show_header()
    show_panel("Edit Filter", title="Filter Management", style="cyan")
    
    custom_filters = _get_custom_filters()
    
    if not custom_filters:
        show_info("No custom filters to edit.")
        press_enter_to_continue()
        return
    
    name = select_from_list(
        title="Select Filter",
        message="Choose filter to edit:",
        options=custom_filters
    )
    
    if not name:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    filter_path = os.path.join(FILTER_D_DIR, f"{name}.conf")
    
    # Read current content
    try:
        with open(filter_path, 'r') as f:
            current_content = f.read()
    except Exception as e:
        show_error(f"Error reading filter: {e}")
        press_enter_to_continue()
        return
    
    console.print("[bold]Current filter content:[/bold]")
    syntax = Syntax(current_content, "ini", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title=f"{name}.conf", border_style="cyan"))
    
    console.print()
    console.print("[dim]Edit options:[/dim]")
    
    action = select_from_list(
        title="Edit Action",
        message="What to modify?",
        options=["Add failregex", "Add ignoreregex", "Replace all", "Cancel"]
    )
    
    if action == "Cancel" or not action:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if action == "Add failregex":
        pattern = text_input(
            title="New Failregex",
            message="Enter new failregex pattern:"
        )
        if pattern:
            # Append to existing
            new_content = _add_pattern_to_filter(current_content, 'failregex', pattern)
            _save_filter(filter_path, new_content)
            show_success("Pattern added!")
    
    elif action == "Add ignoreregex":
        pattern = text_input(
            title="New Ignoreregex",
            message="Enter new ignoreregex pattern:"
        )
        if pattern:
            new_content = _add_pattern_to_filter(current_content, 'ignoreregex', pattern)
            _save_filter(filter_path, new_content)
            show_success("Pattern added!")
    
    elif action == "Replace all":
        console.print("[yellow]Warning: This will replace the entire filter content.[/yellow]")
        if confirm_action("Continue?"):
            # Re-run create wizard
            create_filter()
            return
    
    press_enter_to_continue()


def test_filter():
    """Test a filter against a log file."""
    clear_screen()
    show_header()
    show_panel("Test Filter", title="Filter Management", style="cyan")
    
    all_filters = _get_custom_filters() + _get_system_filters()[:20]
    
    name = select_from_list(
        title="Select Filter",
        message="Choose filter to test:",
        options=all_filters
    )
    
    if not name:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    _test_filter_interactive(name)
    press_enter_to_continue()


def _test_filter_interactive(filter_name):
    """Interactive filter testing."""
    console.print()
    console.print(f"[bold]Testing filter: {filter_name}[/bold]")
    console.print()
    
    # Get log file
    log_path = text_input(
        title="Log File",
        message="Enter path to log file:",
        default="/var/log/nginx/access.log"
    )
    
    if not log_path:
        show_warning("Cancelled.")
        return
    
    if not os.path.exists(log_path):
        show_error(f"Log file not found: {log_path}")
        return
    
    # Number of lines to test
    lines = text_input(
        title="Lines",
        message="Number of lines to test:",
        default="1000"
    )
    
    try:
        lines = int(lines)
    except ValueError:
        lines = 1000
    
    console.print()
    console.print("[dim]Running fail2ban-regex...[/dim]")
    console.print()
    
    # Run fail2ban-regex
    filter_path = os.path.join(FILTER_D_DIR, f"{filter_name}.conf")
    
    result = run_command(
        f"fail2ban-regex {log_path} {filter_path} --print-all-matched -l {lines}",
        check=False,
        silent=True
    )
    
    if result.returncode != 0 and not result.stdout:
        show_error("Failed to run filter test.")
        console.print(f"[red]{result.stderr}[/red]")
        return
    
    # Parse output
    output = result.stdout + result.stderr
    
    # Display results
    console.print("[bold]Test Results:[/bold]")
    console.print()
    
    # Parse statistics
    matched = 0
    missed = 0
    ignored = 0
    
    for line in output.split('\n'):
        if 'matched' in line.lower() and 'lines' in line.lower():
            console.print(f"[green]{line}[/green]")
        elif 'missed' in line.lower():
            console.print(f"[yellow]{line}[/yellow]")
        elif 'ignored' in line.lower():
            console.print(f"[dim]{line}[/dim]")
        elif line.strip().startswith('|-'):
            # Matched line
            console.print(f"[cyan]{line}[/cyan]")
    
    console.print()
    
    # Show sample matches
    if "Lines: " in output:
        console.print("[bold]Summary:[/bold]")
        for line in output.split('\n'):
            if line.startswith("Lines:") or line.startswith("Failregex:") or line.startswith("Ignoreregex:"):
                console.print(f"  {line}")


def regex_helper():
    """Interactive regex helper."""
    clear_screen()
    show_header()
    show_panel("Regex Helper", title="Filter Management", style="cyan")
    
    console.print("[bold]Common Regex Patterns for Fail2ban[/bold]")
    console.print()
    console.print("[yellow]Important:[/yellow] Use <HOST> to capture the attacker's IP address.")
    console.print()
    
    columns = [
        {"name": "Pattern", "style": "cyan"},
        {"name": "Description"},
    ]
    
    rows = [[v, k] for k, v in REGEX_PATTERNS.items()]
    show_table("Available Patterns", columns, rows)
    
    console.print()
    console.print("[bold]Examples:[/bold]")
    console.print()
    
    examples = [
        ("SSH Failed Login", "^.*Failed password for .* from <HOST>"),
        ("Nginx 401/403", '^<HOST> .* "(GET|POST).*" (401|403)'),
        ("WordPress Login", '^<HOST> .* "POST /wp-login\\.php'),
        ("Generic Auth Fail", "^.*[Aa]uthentication fail.* from <HOST>"),
    ]
    
    for name, pattern in examples:
        console.print(f"  [bold]{name}:[/bold]")
        console.print(f"    [cyan]{pattern}[/cyan]")
        console.print()
    
    # Live tester
    console.print()
    if confirm_action("Try live regex tester?"):
        _live_regex_tester()
    
    press_enter_to_continue()


def _live_regex_tester():
    """Live regex testing tool."""
    console.print()
    console.print("[bold]Live Regex Tester[/bold]")
    console.print("[dim]Test your regex pattern against sample log lines.[/dim]")
    console.print()
    
    pattern = text_input(
        title="Regex Pattern",
        message="Enter regex pattern (use <HOST> for IP):"
    )
    
    if not pattern:
        return
    
    test_string = text_input(
        title="Test String",
        message="Enter log line to test:"
    )
    
    if not test_string:
        return
    
    # Convert <HOST> to regex
    regex_pattern = pattern.replace("<HOST>", r"(?P<host>\S+)")
    
    try:
        compiled = re.compile(regex_pattern)
        match = compiled.search(test_string)
        
        console.print()
        if match:
            console.print("[green]✓ MATCH[/green]")
            if 'host' in match.groupdict():
                console.print(f"  Captured HOST: [cyan]{match.group('host')}[/cyan]")
            console.print(f"  Full match: {match.group(0)}")
        else:
            console.print("[red]✗ NO MATCH[/red]")
            
    except re.error as e:
        console.print(f"[red]Invalid regex: {e}[/red]")


def delete_filter():
    """Delete a custom filter."""
    clear_screen()
    show_header()
    show_panel("Delete Filter", title="Filter Management", style="cyan")
    
    custom_filters = _get_custom_filters()
    
    if not custom_filters:
        show_info("No custom filters to delete.")
        press_enter_to_continue()
        return
    
    name = select_from_list(
        title="Select Filter",
        message="Choose filter to delete:",
        options=custom_filters
    )
    
    if not name:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print(f"[yellow]Warning: This will delete filter '{name}'.[/yellow]")
    console.print("[yellow]Any jails using this filter will stop working.[/yellow]")
    console.print()
    
    if not confirm_action(f"Delete filter '{name}'?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    filter_path = os.path.join(FILTER_D_DIR, f"{name}.conf")
    
    try:
        os.remove(filter_path)
        show_success(f"Filter '{name}' deleted!")
    except Exception as e:
        show_error(f"Failed to delete: {e}")
    
    press_enter_to_continue()


# Helper functions

def _get_system_filters():
    """Get list of system filters."""
    system_filters = []
    
    if os.path.exists(FILTER_D_DIR):
        for filename in os.listdir(FILTER_D_DIR):
            if filename.endswith('.conf'):
                name = filename[:-5]
                # Check if it's a system filter (no vexo comment)
                filter_path = os.path.join(FILTER_D_DIR, filename)
                try:
                    with open(filter_path, 'r') as f:
                        content = f.read()
                        if 'vexo' not in content.lower():
                            system_filters.append(name)
                except Exception:
                    system_filters.append(name)
    
    return system_filters


def _get_custom_filters():
    """Get list of custom (vexo-created) filters."""
    custom_filters = []
    
    if os.path.exists(FILTER_D_DIR):
        for filename in os.listdir(FILTER_D_DIR):
            if filename.endswith('.conf'):
                name = filename[:-5]
                filter_path = os.path.join(FILTER_D_DIR, filename)
                try:
                    with open(filter_path, 'r') as f:
                        content = f.read()
                        if 'vexo' in content.lower():
                            custom_filters.append(name)
                except Exception:
                    pass
    
    return custom_filters


def _filter_exists(name):
    """Check if filter exists."""
    filter_path = os.path.join(FILTER_D_DIR, f"{name}.conf")
    return os.path.exists(filter_path)


def _generate_filter_content(name, description, failregex_lines, ignoreregex_lines):
    """Generate filter file content."""
    content = f"""[Definition]
# Filter: {name}
# {description}
# Generated by vexo

failregex = {failregex_lines[0]}
"""
    
    for line in failregex_lines[1:]:
        content += f"            {line}\n"
    
    if ignoreregex_lines:
        content += f"\nignoreregex = {ignoreregex_lines[0]}\n"
        for line in ignoreregex_lines[1:]:
            content += f"              {line}\n"
    else:
        content += "\nignoreregex =\n"
    
    return content


def _add_pattern_to_filter(content, pattern_type, new_pattern):
    """Add a pattern to existing filter content."""
    lines = content.split('\n')
    new_lines = []
    found = False
    
    for line in lines:
        new_lines.append(line)
        if line.strip().startswith(f'{pattern_type} =') or line.strip().startswith(f'{pattern_type}='):
            found = True
            # Add indented pattern on next line
            new_lines.append(f"            {new_pattern}")
    
    if not found:
        # Add new section
        new_lines.append(f"\n{pattern_type} = {new_pattern}")
    
    return '\n'.join(new_lines)


def _save_filter(path, content):
    """Save filter content to file."""
    try:
        with open(path, 'w') as f:
            f.write(content)
        return True
    except Exception:
        return False
```

**Step 2: Commit filter management**

```bash
git add modules/fail2ban/filters.py
git commit -m "feat(fail2ban): implement filter management with testing and regex helper"
```

---

## Verification

After completing all tasks:

1. Filter management features:
   - List system and custom filters
   - View filter content with syntax highlighting
   - Create custom filters with wizard
   - Edit existing custom filters
   - Test filters against log files
   - Regex helper with common patterns
   - Live regex tester
   - Delete custom filters

2. Custom filters marked with `vexo` comment for identification
