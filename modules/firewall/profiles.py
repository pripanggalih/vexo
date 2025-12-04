"""Application profiles for firewall."""

import os
import re
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
from ui.menu import run_menu_loop, text_input, select_from_list, confirm_action
from utils.shell import run_command, require_root
from modules.firewall.common import is_ufw_installed, get_ufw_status_text


# UFW application profiles directory
UFW_APPS_DIR = "/etc/ufw/applications.d"
VEXO_CUSTOM_PROFILE = f"{UFW_APPS_DIR}/vexo-custom"


def show_profiles_menu():
    """Display application profiles submenu."""
    def get_status():
        profiles = _get_all_profiles()
        return f"UFW: {get_ufw_status_text()} | Profiles: {len(profiles)}"
    
    options = [
        ("list", "1. List Profiles"),
        ("apply", "2. Apply Profile"),
        ("create", "3. Create Custom Profile"),
        ("edit", "4. Edit Custom Profile"),
        ("delete", "5. Delete Custom Profile"),
        ("info", "6. Profile Info"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "list": list_profiles,
        "apply": apply_profile,
        "create": create_profile,
        "edit": edit_profile,
        "delete": delete_profile,
        "info": show_profile_info,
    }
    
    run_menu_loop("Application Profiles", options, handlers, get_status)


def _get_all_profiles():
    """Get list of all available UFW app profiles."""
    result = run_command("ufw app list", check=False, silent=True)
    if result.returncode != 0:
        return []
    
    profiles = []
    for line in result.stdout.split('\n'):
        line = line.strip()
        if line and "Available" not in line and ":" not in line:
            profiles.append(line)
    
    return profiles


def _get_profile_info(profile_name):
    """Get detailed info about a profile."""
    result = run_command(f"ufw app info '{profile_name}'", check=False, silent=True)
    if result.returncode != 0:
        return None
    
    info = {
        "name": profile_name,
        "title": "",
        "description": "",
        "ports": ""
    }
    
    for line in result.stdout.split('\n'):
        if line.startswith("Title:"):
            info["title"] = line.split(":", 1)[1].strip()
        elif line.startswith("Description:"):
            info["description"] = line.split(":", 1)[1].strip()
        elif line.startswith("Ports:"):
            info["ports"] = line.split(":", 1)[1].strip()
    
    return info


def _get_applied_profiles():
    """Get list of profiles that have rules in UFW."""
    result = run_command("ufw status", check=False, silent=True)
    if result.returncode != 0:
        return set()
    
    applied = set()
    profiles = _get_all_profiles()
    
    for profile in profiles:
        # Check if profile name appears in status output
        if profile.lower() in result.stdout.lower():
            applied.add(profile)
    
    return applied


def _get_custom_profiles():
    """Get list of custom profiles created by vexo."""
    if not os.path.exists(VEXO_CUSTOM_PROFILE):
        return []
    
    profiles = []
    try:
        with open(VEXO_CUSTOM_PROFILE, 'r') as f:
            content = f.read()
            # Find all [ProfileName] sections
            matches = re.findall(r'\[([^\]]+)\]', content)
            profiles = matches
    except IOError:
        pass
    
    return profiles


def list_profiles():
    """List all available application profiles."""
    clear_screen()
    show_header()
    show_panel("Application Profiles", title="App Profiles", style="cyan")
    
    if not is_ufw_installed():
        show_error("UFW is not installed.")
        press_enter_to_continue()
        return
    
    profiles = _get_all_profiles()
    applied = _get_applied_profiles()
    custom = set(_get_custom_profiles())
    
    if not profiles:
        show_info("No application profiles available.")
        press_enter_to_continue()
        return
    
    console.print("[bold]Available Profiles:[/bold]")
    console.print()
    
    columns = [
        {"name": "Profile", "style": "cyan"},
        {"name": "Type"},
        {"name": "Status", "justify": "center"},
    ]
    
    rows = []
    for profile in profiles:
        profile_type = "[yellow]Custom[/yellow]" if profile in custom else "System"
        status = "[green]Applied[/green]" if profile in applied else "[dim]-[/dim]"
        rows.append([profile, profile_type, status])
    
    show_table("", columns, rows)
    
    console.print(f"[dim]Total: {len(profiles)} profiles ({len(custom)} custom)[/dim]")
    
    press_enter_to_continue()


def apply_profile():
    """Apply an application profile."""
    clear_screen()
    show_header()
    show_panel("Apply Profile", title="App Profiles", style="cyan")
    
    if not is_ufw_installed():
        show_error("UFW is not installed.")
        press_enter_to_continue()
        return
    
    profiles = _get_all_profiles()
    applied = _get_applied_profiles()
    
    if not profiles:
        show_info("No profiles available.")
        press_enter_to_continue()
        return
    
    # Build options with status
    options = []
    for p in profiles:
        status = " [green](applied)[/green]" if p in applied else ""
        options.append(f"{p}{status}")
    
    choice = select_from_list(
        title="Profile",
        message="Select profile to apply:",
        options=options
    )
    
    if not choice:
        press_enter_to_continue()
        return
    
    # Extract profile name (remove status suffix)
    profile_name = choice.split(" [")[0]
    
    # Show profile info
    info = _get_profile_info(profile_name)
    if info:
        console.print()
        console.print(f"[bold]Profile:[/bold] {info['title'] or profile_name}")
        console.print(f"[bold]Ports:[/bold] {info['ports']}")
        if info['description']:
            console.print(f"[bold]Description:[/bold] {info['description']}")
        console.print()
    
    if not confirm_action(f"Apply profile '{profile_name}'?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    result = run_command(f"ufw allow '{profile_name}'", check=False, silent=True)
    
    if result.returncode == 0:
        show_success(f"Profile '{profile_name}' applied!")
    else:
        show_error(f"Failed to apply profile: {result.stderr}")
    
    press_enter_to_continue()


def create_profile():
    """Create a custom application profile."""
    clear_screen()
    show_header()
    show_panel("Create Custom Profile", title="App Profiles", style="cyan")
    
    console.print("Create a custom UFW application profile.")
    console.print("[dim]This will be saved to /etc/ufw/applications.d/vexo-custom[/dim]")
    console.print()
    
    # Profile name
    name = text_input(
        title="Name",
        message="Profile name (e.g., my-nodejs-app):"
    )
    
    if not name:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Validate name (alphanumeric and hyphens only)
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9-]*$', name):
        show_error("Invalid name. Use alphanumeric and hyphens, start with letter.")
        press_enter_to_continue()
        return
    
    # Check if profile already exists
    existing = _get_all_profiles()
    if name in existing:
        show_error(f"Profile '{name}' already exists.")
        press_enter_to_continue()
        return
    
    # Title
    title = text_input(
        title="Title",
        message="Profile title (e.g., My Node.js Application):"
    )
    
    if not title:
        title = name
    
    # Description
    description = text_input(
        title="Description",
        message="Description (optional):",
        default=""
    )
    
    # Ports
    console.print()
    console.print("[bold]Enter ports:[/bold]")
    console.print("[dim]Format: port/protocol (e.g., 3000/tcp, 8080/tcp,8081/tcp)[/dim]")
    console.print("[dim]Multiple ports: 3000,3001,3002/tcp or 3000:3005/tcp (range)[/dim]")
    console.print()
    
    ports = text_input(
        title="Ports",
        message="Ports:"
    )
    
    if not ports:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Validate ports format
    if not _validate_ports_format(ports):
        show_error("Invalid ports format.")
        press_enter_to_continue()
        return
    
    # Preview
    console.print()
    console.print("[bold]Profile Preview:[/bold]")
    console.print(f"  [{name}]")
    console.print(f"  title={title}")
    console.print(f"  description={description}")
    console.print(f"  ports={ports}")
    console.print()
    
    if not confirm_action("Create this profile?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Create profile
    success = _write_custom_profile(name, title, description, ports)
    
    if success:
        # Update UFW app list
        run_command("ufw app update vexo-custom", check=False, silent=True)
        show_success(f"Profile '{name}' created!")
        
        if confirm_action("Apply this profile now?"):
            result = run_command(f"ufw allow '{name}'", check=False, silent=True)
            if result.returncode == 0:
                show_success(f"Profile applied!")
            else:
                show_error("Failed to apply profile.")
    else:
        show_error("Failed to create profile.")
    
    press_enter_to_continue()


def _write_custom_profile(name, title, description, ports):
    """Write a custom profile to vexo-custom file."""
    try:
        # Read existing content
        existing_content = ""
        if os.path.exists(VEXO_CUSTOM_PROFILE):
            with open(VEXO_CUSTOM_PROFILE, 'r') as f:
                existing_content = f.read()
        
        # Add new profile
        new_profile = f"""
[{name}]
title={title}
description={description}
ports={ports}
"""
        
        # Write back
        with open(VEXO_CUSTOM_PROFILE, 'w') as f:
            f.write(existing_content.rstrip() + new_profile)
        
        return True
    except IOError as e:
        console.print(f"[red]Error: {e}[/red]")
        return False


def _validate_ports_format(ports_str):
    """Validate UFW ports format."""
    # Valid formats: 80/tcp, 80,443/tcp, 3000:3005/tcp, 80/tcp|443/tcp
    pattern = r'^(\d+([,-:]\d+)*/(tcp|udp)(\|(\d+([,-:]\d+)*/(tcp|udp)))*)|any$'
    return bool(re.match(pattern, ports_str, re.IGNORECASE))


def edit_profile():
    """Edit a custom profile."""
    clear_screen()
    show_header()
    show_panel("Edit Custom Profile", title="App Profiles", style="cyan")
    
    custom_profiles = _get_custom_profiles()
    
    if not custom_profiles:
        show_info("No custom profiles to edit.")
        show_info("Use 'Create Custom Profile' to add one.")
        press_enter_to_continue()
        return
    
    profile_name = select_from_list(
        title="Profile",
        message="Select profile to edit:",
        options=custom_profiles
    )
    
    if not profile_name:
        press_enter_to_continue()
        return
    
    # Get current info
    info = _get_profile_info(profile_name)
    
    if not info:
        show_error("Could not read profile info.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print(f"[bold]Current Configuration:[/bold]")
    console.print(f"  Title: {info['title']}")
    console.print(f"  Description: {info['description']}")
    console.print(f"  Ports: {info['ports']}")
    console.print()
    
    # What to edit
    action = select_from_list(
        title="Edit",
        message="What to edit:",
        options=["Title", "Description", "Ports"]
    )
    
    if not action:
        press_enter_to_continue()
        return
    
    if action == "Title":
        new_value = text_input(
            title="Title",
            message="New title:",
            default=info['title']
        )
        if new_value:
            _update_profile_field(profile_name, "title", new_value)
    
    elif action == "Description":
        new_value = text_input(
            title="Description",
            message="New description:",
            default=info['description']
        )
        if new_value is not None:
            _update_profile_field(profile_name, "description", new_value)
    
    elif action == "Ports":
        new_value = text_input(
            title="Ports",
            message="New ports:",
            default=info['ports']
        )
        if new_value and _validate_ports_format(new_value):
            _update_profile_field(profile_name, "ports", new_value)
        elif new_value:
            show_error("Invalid ports format.")
            press_enter_to_continue()
            return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Update UFW
    run_command("ufw app update vexo-custom", check=False, silent=True)
    show_success("Profile updated!")
    
    press_enter_to_continue()


def _update_profile_field(profile_name, field, value):
    """Update a field in a custom profile."""
    if not os.path.exists(VEXO_CUSTOM_PROFILE):
        return False
    
    try:
        with open(VEXO_CUSTOM_PROFILE, 'r') as f:
            content = f.read()
        
        # Find the profile section and update the field
        lines = content.split('\n')
        in_profile = False
        new_lines = []
        field_updated = False
        
        for line in lines:
            if line.strip() == f"[{profile_name}]":
                in_profile = True
                new_lines.append(line)
            elif line.strip().startswith('[') and in_profile:
                in_profile = False
                new_lines.append(line)
            elif in_profile and line.strip().startswith(f"{field}="):
                new_lines.append(f"{field}={value}")
                field_updated = True
            else:
                new_lines.append(line)
        
        with open(VEXO_CUSTOM_PROFILE, 'w') as f:
            f.write('\n'.join(new_lines))
        
        return True
    except IOError:
        return False


def delete_profile():
    """Delete a custom profile."""
    clear_screen()
    show_header()
    show_panel("Delete Custom Profile", title="App Profiles", style="cyan")
    
    custom_profiles = _get_custom_profiles()
    
    if not custom_profiles:
        show_info("No custom profiles to delete.")
        press_enter_to_continue()
        return
    
    profile_name = select_from_list(
        title="Profile",
        message="Select profile to delete:",
        options=custom_profiles
    )
    
    if not profile_name:
        press_enter_to_continue()
        return
    
    # Show profile info
    info = _get_profile_info(profile_name)
    if info:
        console.print()
        console.print(f"[bold]Profile:[/bold] {profile_name}")
        console.print(f"[bold]Ports:[/bold] {info['ports']}")
        console.print()
    
    if not confirm_action(f"Delete profile '{profile_name}'?"):
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # First remove any rules using this profile
    if confirm_action("Also remove firewall rules for this profile?"):
        run_command(f"ufw delete allow '{profile_name}'", check=False, silent=True)
    
    # Remove from file
    success = _remove_profile_from_file(profile_name)
    
    if success:
        run_command("ufw app update vexo-custom", check=False, silent=True)
        show_success(f"Profile '{profile_name}' deleted!")
    else:
        show_error("Failed to delete profile.")
    
    press_enter_to_continue()


def _remove_profile_from_file(profile_name):
    """Remove a profile section from vexo-custom file."""
    if not os.path.exists(VEXO_CUSTOM_PROFILE):
        return False
    
    try:
        with open(VEXO_CUSTOM_PROFILE, 'r') as f:
            content = f.read()
        
        # Remove the profile section
        lines = content.split('\n')
        new_lines = []
        skip_until_next_section = False
        
        for line in lines:
            if line.strip() == f"[{profile_name}]":
                skip_until_next_section = True
                continue
            elif line.strip().startswith('[') and skip_until_next_section:
                skip_until_next_section = False
            
            if not skip_until_next_section:
                new_lines.append(line)
        
        # Write back
        with open(VEXO_CUSTOM_PROFILE, 'w') as f:
            f.write('\n'.join(new_lines))
        
        return True
    except IOError:
        return False


def show_profile_info():
    """Show detailed info about a profile."""
    clear_screen()
    show_header()
    show_panel("Profile Info", title="App Profiles", style="cyan")
    
    profiles = _get_all_profiles()
    
    if not profiles:
        show_info("No profiles available.")
        press_enter_to_continue()
        return
    
    profile_name = select_from_list(
        title="Profile",
        message="Select profile:",
        options=profiles
    )
    
    if not profile_name:
        press_enter_to_continue()
        return
    
    info = _get_profile_info(profile_name)
    custom = _get_custom_profiles()
    
    if not info:
        show_error("Could not retrieve profile info.")
        press_enter_to_continue()
        return
    
    console.print()
    console.print(f"[bold cyan]Profile: {profile_name}[/bold cyan]")
    console.print()
    console.print(f"[bold]Title:[/bold] {info['title']}")
    console.print(f"[bold]Description:[/bold] {info['description'] or '[dim]No description[/dim]'}")
    console.print(f"[bold]Ports:[/bold] {info['ports']}")
    console.print(f"[bold]Type:[/bold] {'Custom (vexo)' if profile_name in custom else 'System'}")
    console.print()
    
    # Check if applied
    applied = _get_applied_profiles()
    if profile_name in applied:
        console.print("[green]This profile is currently applied[/green]")
    else:
        console.print("[dim]This profile is not currently applied[/dim]")
    
    press_enter_to_continue()
