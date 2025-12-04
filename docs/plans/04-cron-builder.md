# Phase 4: Schedule Builder

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add interactive cron expression builder wizard that guides users step-by-step to create cron schedules without memorizing syntax.

**Architecture:** Create builder.py module with interactive wizard that asks frequency, then refines to specific time/day based on selection. Validates and previews the resulting cron expression.

**Tech Stack:** Python

**Prerequisite:** Complete Phase 1 (cron package structure)

---

## Task 1: Create Schedule Builder Module

**Files:**
- Create: `modules/cron/builder.py`

**Step 1: Create builder.py with interactive wizard**

```python
"""Interactive schedule builder for vexo-cli cron."""

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_success,
    show_error,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import show_submenu, confirm_action, text_input, select_from_list


# Human-readable descriptions for cron fields
MINUTE_OPTIONS = [
    ("*", "Every minute"),
    ("0", "At minute 0"),
    ("15", "At minute 15"),
    ("30", "At minute 30"),
    ("45", "At minute 45"),
    ("*/5", "Every 5 minutes"),
    ("*/10", "Every 10 minutes"),
    ("*/15", "Every 15 minutes"),
    ("*/30", "Every 30 minutes"),
    ("custom", "Custom value"),
]

HOUR_OPTIONS = [
    ("*", "Every hour"),
    ("0", "Midnight (00:00)"),
    ("6", "6 AM"),
    ("12", "Noon (12:00)"),
    ("18", "6 PM"),
    ("*/2", "Every 2 hours"),
    ("*/6", "Every 6 hours"),
    ("*/12", "Every 12 hours"),
    ("custom", "Custom value"),
]

DAY_OPTIONS = [
    ("*", "Every day"),
    ("1", "1st of month"),
    ("15", "15th of month"),
    ("1,15", "1st and 15th"),
    ("custom", "Custom value"),
]

MONTH_OPTIONS = [
    ("*", "Every month"),
    ("1", "January"),
    ("*/3", "Every 3 months"),
    ("1,4,7,10", "Quarterly"),
    ("custom", "Custom value"),
]

WEEKDAY_OPTIONS = [
    ("*", "Every day of week"),
    ("0", "Sunday"),
    ("1", "Monday"),
    ("1-5", "Weekdays (Mon-Fri)"),
    ("0,6", "Weekends (Sat-Sun)"),
    ("custom", "Custom value"),
]


def schedule_builder():
    """Interactive schedule builder wizard."""
    clear_screen()
    show_header()
    show_panel("Schedule Builder", title="Cron Jobs", style="cyan")
    
    console.print("[bold]Build a cron schedule step by step[/bold]")
    console.print()
    console.print("[dim]Cron format: minute hour day month weekday[/dim]")
    console.print()
    
    # Step 1: Choose frequency type
    frequency = select_from_list(
        title="Frequency",
        message="How often should this run?",
        options=[
            "Every minute",
            "Every X minutes",
            "Hourly",
            "Every X hours",
            "Daily at specific time",
            "Weekly on specific day",
            "Monthly on specific day",
            "Advanced (custom)",
        ]
    )
    
    if not frequency:
        return None
    
    # Route to appropriate builder
    if frequency == "Every minute":
        return _build_every_minute()
    elif frequency == "Every X minutes":
        return _build_every_x_minutes()
    elif frequency == "Hourly":
        return _build_hourly()
    elif frequency == "Every X hours":
        return _build_every_x_hours()
    elif frequency == "Daily at specific time":
        return _build_daily()
    elif frequency == "Weekly on specific day":
        return _build_weekly()
    elif frequency == "Monthly on specific day":
        return _build_monthly()
    elif frequency == "Advanced (custom)":
        return _build_advanced()
    
    return None


def _build_every_minute():
    """Build every minute schedule."""
    schedule = "* * * * *"
    return _confirm_schedule(schedule, "Every minute")


def _build_every_x_minutes():
    """Build every X minutes schedule."""
    minutes = text_input(
        title="Minutes",
        message="Run every how many minutes? (1-59):",
        default="5"
    )
    
    if not minutes:
        return None
    
    try:
        m = int(minutes)
        if m < 1 or m > 59:
            raise ValueError()
    except ValueError:
        show_error("Invalid value. Must be 1-59.")
        press_enter_to_continue()
        return None
    
    schedule = f"*/{m} * * * *"
    return _confirm_schedule(schedule, f"Every {m} minutes")


def _build_hourly():
    """Build hourly schedule."""
    minute = text_input(
        title="Minute",
        message="At which minute of each hour? (0-59):",
        default="0"
    )
    
    if minute is None:
        return None
    
    try:
        m = int(minute)
        if m < 0 or m > 59:
            raise ValueError()
    except ValueError:
        show_error("Invalid value. Must be 0-59.")
        press_enter_to_continue()
        return None
    
    schedule = f"{m} * * * *"
    return _confirm_schedule(schedule, f"Every hour at minute {m}")


def _build_every_x_hours():
    """Build every X hours schedule."""
    hours = text_input(
        title="Hours",
        message="Run every how many hours? (1-23):",
        default="6"
    )
    
    if not hours:
        return None
    
    try:
        h = int(hours)
        if h < 1 or h > 23:
            raise ValueError()
    except ValueError:
        show_error("Invalid value. Must be 1-23.")
        press_enter_to_continue()
        return None
    
    minute = text_input(
        title="Minute",
        message="At which minute? (0-59):",
        default="0"
    )
    
    if minute is None:
        return None
    
    try:
        m = int(minute)
        if m < 0 or m > 59:
            raise ValueError()
    except ValueError:
        show_error("Invalid value. Must be 0-59.")
        press_enter_to_continue()
        return None
    
    schedule = f"{m} */{h} * * *"
    return _confirm_schedule(schedule, f"Every {h} hours at minute {m}")


def _build_daily():
    """Build daily schedule at specific time."""
    hour = text_input(
        title="Hour",
        message="At which hour? (0-23, where 0=midnight):",
        default="0"
    )
    
    if hour is None:
        return None
    
    try:
        h = int(hour)
        if h < 0 or h > 23:
            raise ValueError()
    except ValueError:
        show_error("Invalid value. Must be 0-23.")
        press_enter_to_continue()
        return None
    
    minute = text_input(
        title="Minute",
        message="At which minute? (0-59):",
        default="0"
    )
    
    if minute is None:
        return None
    
    try:
        m = int(minute)
        if m < 0 or m > 59:
            raise ValueError()
    except ValueError:
        show_error("Invalid value. Must be 0-59.")
        press_enter_to_continue()
        return None
    
    schedule = f"{m} {h} * * *"
    time_str = f"{h:02d}:{m:02d}"
    return _confirm_schedule(schedule, f"Every day at {time_str}")


def _build_weekly():
    """Build weekly schedule on specific day."""
    weekday = select_from_list(
        title="Day of Week",
        message="On which day?",
        options=[
            "Sunday (0)",
            "Monday (1)",
            "Tuesday (2)",
            "Wednesday (3)",
            "Thursday (4)",
            "Friday (5)",
            "Saturday (6)",
            "Weekdays Mon-Fri (1-5)",
            "Weekends Sat-Sun (0,6)",
        ]
    )
    
    if not weekday:
        return None
    
    # Extract weekday value
    if "Mon-Fri" in weekday:
        dow = "1-5"
        day_name = "weekdays"
    elif "Sat-Sun" in weekday:
        dow = "0,6"
        day_name = "weekends"
    else:
        dow = weekday.split("(")[1].rstrip(")")
        day_name = weekday.split(" (")[0]
    
    hour = text_input(
        title="Hour",
        message="At which hour? (0-23):",
        default="0"
    )
    
    if hour is None:
        return None
    
    try:
        h = int(hour)
        if h < 0 or h > 23:
            raise ValueError()
    except ValueError:
        show_error("Invalid value. Must be 0-23.")
        press_enter_to_continue()
        return None
    
    minute = text_input(
        title="Minute",
        message="At which minute? (0-59):",
        default="0"
    )
    
    if minute is None:
        return None
    
    try:
        m = int(minute)
        if m < 0 or m > 59:
            raise ValueError()
    except ValueError:
        show_error("Invalid value. Must be 0-59.")
        press_enter_to_continue()
        return None
    
    schedule = f"{m} {h} * * {dow}"
    time_str = f"{h:02d}:{m:02d}"
    return _confirm_schedule(schedule, f"Every {day_name} at {time_str}")


def _build_monthly():
    """Build monthly schedule on specific day."""
    day = text_input(
        title="Day of Month",
        message="On which day of the month? (1-28):",
        default="1"
    )
    
    if not day:
        return None
    
    try:
        d = int(day)
        if d < 1 or d > 28:
            show_warning("Days 29-31 may not exist in all months. Using anyway.")
    except ValueError:
        show_error("Invalid day.")
        press_enter_to_continue()
        return None
    
    hour = text_input(
        title="Hour",
        message="At which hour? (0-23):",
        default="0"
    )
    
    if hour is None:
        return None
    
    try:
        h = int(hour)
        if h < 0 or h > 23:
            raise ValueError()
    except ValueError:
        show_error("Invalid value. Must be 0-23.")
        press_enter_to_continue()
        return None
    
    minute = text_input(
        title="Minute",
        message="At which minute? (0-59):",
        default="0"
    )
    
    if minute is None:
        return None
    
    try:
        m = int(minute)
        if m < 0 or m > 59:
            raise ValueError()
    except ValueError:
        show_error("Invalid value. Must be 0-59.")
        press_enter_to_continue()
        return None
    
    schedule = f"{m} {h} {d} * *"
    time_str = f"{h:02d}:{m:02d}"
    
    suffix = "th"
    if d == 1:
        suffix = "st"
    elif d == 2:
        suffix = "nd"
    elif d == 3:
        suffix = "rd"
    
    return _confirm_schedule(schedule, f"Monthly on {d}{suffix} at {time_str}")


def _build_advanced():
    """Build advanced custom schedule."""
    clear_screen()
    show_header()
    show_panel("Advanced Schedule Builder", title="Cron Jobs", style="cyan")
    
    console.print("[bold]Cron Expression Format:[/bold]")
    console.print("  minute hour day month weekday")
    console.print()
    console.print("[dim]Special characters:[/dim]")
    console.print("  *     = every value")
    console.print("  */n   = every n intervals")
    console.print("  n-m   = range from n to m")
    console.print("  n,m,o = specific values")
    console.print()
    
    # Minute
    minute = _get_cron_field("minute", "0-59", MINUTE_OPTIONS)
    if minute is None:
        return None
    
    # Hour
    hour = _get_cron_field("hour", "0-23", HOUR_OPTIONS)
    if hour is None:
        return None
    
    # Day of month
    day = _get_cron_field("day of month", "1-31", DAY_OPTIONS)
    if day is None:
        return None
    
    # Month
    month = _get_cron_field("month", "1-12", MONTH_OPTIONS)
    if month is None:
        return None
    
    # Day of week
    weekday = _get_cron_field("day of week", "0-6 (Sun-Sat)", WEEKDAY_OPTIONS)
    if weekday is None:
        return None
    
    schedule = f"{minute} {hour} {day} {month} {weekday}"
    description = _describe_schedule(schedule)
    
    return _confirm_schedule(schedule, description)


def _get_cron_field(field_name, valid_range, options):
    """Get a cron field value from user."""
    option_strs = [f"{v} ({d})" for v, d in options]
    
    selection = select_from_list(
        title=field_name.capitalize(),
        message=f"Select {field_name} ({valid_range}):",
        options=option_strs
    )
    
    if not selection:
        return None
    
    if "Custom value" in selection:
        value = text_input(
            title=field_name.capitalize(),
            message=f"Enter {field_name} value ({valid_range}):"
        )
        return value
    else:
        return selection.split(" (")[0]


def _describe_schedule(schedule):
    """Generate human-readable description of schedule."""
    parts = schedule.split()
    if len(parts) != 5:
        return schedule
    
    minute, hour, day, month, weekday = parts
    
    # Simple descriptions for common patterns
    if schedule == "* * * * *":
        return "Every minute"
    elif minute.startswith("*/") and hour == "*" and day == "*" and month == "*" and weekday == "*":
        return f"Every {minute[2:]} minutes"
    elif hour.startswith("*/") and day == "*" and month == "*" and weekday == "*":
        return f"Every {hour[2:]} hours at minute {minute}"
    elif hour != "*" and day == "*" and month == "*" and weekday == "*":
        return f"Daily at {hour}:{minute.zfill(2)}"
    elif weekday != "*" and day == "*" and month == "*":
        return f"Weekly on day {weekday} at {hour}:{minute.zfill(2)}"
    elif day != "*" and month == "*" and weekday == "*":
        return f"Monthly on day {day} at {hour}:{minute.zfill(2)}"
    
    return f"Custom: {schedule}"


def _confirm_schedule(schedule, description):
    """Confirm the schedule with user."""
    console.print()
    console.print(f"[bold]Schedule:[/bold] {schedule}")
    console.print(f"[bold]Description:[/bold] {description}")
    console.print()
    
    if confirm_action("Use this schedule?"):
        return schedule
    return None


def validate_cron_expression(expression):
    """
    Validate a cron expression.
    
    Args:
        expression: Cron expression string
    
    Returns:
        tuple: (is_valid, error_message)
    """
    parts = expression.split()
    
    if len(parts) != 5:
        return False, f"Expected 5 fields, got {len(parts)}"
    
    field_names = ["minute", "hour", "day", "month", "weekday"]
    field_ranges = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]
    
    for i, (part, name, (min_val, max_val)) in enumerate(zip(parts, field_names, field_ranges)):
        valid, error = _validate_cron_field(part, name, min_val, max_val)
        if not valid:
            return False, error
    
    return True, None


def _validate_cron_field(value, name, min_val, max_val):
    """Validate a single cron field."""
    if value == "*":
        return True, None
    
    # Handle */n
    if value.startswith("*/"):
        try:
            n = int(value[2:])
            if n < 1:
                return False, f"{name}: step must be >= 1"
            return True, None
        except ValueError:
            return False, f"{name}: invalid step value"
    
    # Handle ranges and lists
    for item in value.split(","):
        if "-" in item:
            try:
                start, end = item.split("-")
                start, end = int(start), int(end)
                if start < min_val or end > max_val or start > end:
                    return False, f"{name}: invalid range {item}"
            except ValueError:
                return False, f"{name}: invalid range {item}"
        else:
            try:
                n = int(item)
                if n < min_val or n > max_val:
                    return False, f"{name}: {n} out of range ({min_val}-{max_val})"
            except ValueError:
                return False, f"{name}: invalid value {item}"
    
    return True, None
```

**Step 2: Commit**

```bash
git add modules/cron/builder.py
git commit -m "feat(cron): add interactive schedule builder wizard"
```

---

## Task 2: Integrate Builder into Add Job

**Files:**
- Modify: `modules/cron/add_job.py`

**Step 1: Update _get_schedule to use builder**

Add import at top:
```python
from modules.cron.builder import schedule_builder
```

Update `_get_schedule` function:

```python
def _get_schedule(default="0 2 * * *"):
    """Get schedule from user with preset options or builder."""
    options = [
        "Use Schedule Builder (recommended)",
    ]
    options.extend([f"{schedule} ({desc})" for schedule, desc in CRON_PRESETS])
    options.append("Custom (enter manually)")
    
    selection = select_from_list(
        title="Schedule",
        message="Select schedule:",
        options=options
    )
    
    if not selection:
        return None
    
    if selection == "Use Schedule Builder (recommended)":
        return schedule_builder()
    elif selection == "Custom (enter manually)":
        schedule = text_input(
            title="Cron Expression",
            message="Enter cron expression:",
            default=default
        )
        return schedule
    else:
        return selection.split(" (")[0]
```

**Step 2: Commit**

```bash
git add modules/cron/add_job.py
git commit -m "feat(cron): integrate schedule builder into add job flow"
```

---

## Task 3: Add Builder to Main Menu

**Files:**
- Modify: `modules/cron/__init__.py`

**Step 1: Add builder option to menu**

Add import:
```python
from modules.cron.builder import schedule_builder
```

Add to job_management_menu options:
```python
def job_management_menu():
    """Submenu for job management operations."""
    from ui.components import clear_screen, show_header
    
    while True:
        clear_screen()
        show_header()
        
        choice = show_submenu(
            title="Job Management",
            options=[
                ("add", "1. Add Job"),
                ("edit", "2. Edit Job"),
                ("clone", "3. Clone Job"),
                ("remove", "4. Remove Job"),
                ("list", "5. List Jobs"),
                ("builder", "6. Schedule Builder"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "add":
            add_job_menu()
        elif choice == "edit":
            edit_job_menu()
        elif choice == "clone":
            clone_job_menu()
        elif choice == "remove":
            remove_cron_job_interactive()
        elif choice == "list":
            list_cron_jobs()
        elif choice == "builder":
            _show_builder_standalone()
        elif choice == "back" or choice is None:
            break


def _show_builder_standalone():
    """Show schedule builder as standalone tool."""
    from modules.cron.builder import schedule_builder
    from ui.components import console, press_enter_to_continue
    
    result = schedule_builder()
    if result:
        console.print()
        console.print(f"[bold green]Generated schedule:[/bold green] {result}")
        console.print()
        console.print("[dim]You can use this schedule when adding a new job.[/dim]")
        press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/cron/__init__.py
git commit -m "feat(cron): add standalone schedule builder to menu"
```

---

## Summary

After Phase 4, the schedule builder will have:

**Frequency Options:**
- Every minute
- Every X minutes
- Hourly
- Every X hours
- Daily at specific time
- Weekly on specific day
- Monthly on specific day
- Advanced (full control)

**Features:**
- Step-by-step wizard
- Input validation
- Human-readable preview
- Confirmation before use
- Standalone tool in menu
- Integrated into add job flow

Files added/modified:
- `modules/cron/builder.py` (new)
- `modules/cron/add_job.py` (updated)
- `modules/cron/__init__.py` (updated)
