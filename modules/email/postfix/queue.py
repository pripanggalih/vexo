"""Postfix queue management."""

from ui.components import (
    console, clear_screen, show_header, show_panel, show_table,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, require_root
from modules.email.postfix.utils import is_postfix_ready


def show_queue_menu():
    """Display queue management menu."""
    def get_status():
        result = run_command("postqueue -p 2>/dev/null | grep -c '^[A-F0-9]'", check=False, silent=True)
        try:
            count = int(result.stdout.strip())
        except ValueError:
            count = 0
        return f"Queue: {count} message(s)"
    
    options = [
        ("view", "1. View Queue"),
        ("flush", "2. Flush Queue"),
        ("hold", "3. Hold/Release Messages"),
        ("delete", "4. Delete Messages"),
        ("requeue", "5. Requeue All"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "view": view_queue,
        "flush": flush_queue,
        "hold": hold_release_menu,
        "delete": delete_messages,
        "requeue": requeue_all,
    }
    
    run_menu_loop("Queue Management", options, handlers, get_status)


def view_queue():
    """Display mail queue."""
    clear_screen()
    show_header()
    show_panel("Mail Queue", title="Queue Management", style="cyan")
    
    if not is_postfix_ready():
        show_error("Postfix is not running.")
        press_enter_to_continue()
        return
    
    result = run_command("postqueue -p", check=False, silent=True)
    
    if result.returncode == 0:
        output = result.stdout.strip()
        if "Mail queue is empty" in output or not output:
            show_info("Mail queue is empty.")
        else:
            console.print("[bold]Mail Queue:[/bold]")
            console.print()
            console.print(output)
    else:
        show_error("Failed to get queue status.")
    
    press_enter_to_continue()


def flush_queue():
    """Attempt to deliver all queued messages."""
    clear_screen()
    show_header()
    show_panel("Flush Queue", title="Queue Management", style="cyan")
    
    if not is_postfix_ready():
        show_error("Postfix is not running.")
        press_enter_to_continue()
        return
    
    console.print("[bold]This will attempt to deliver all queued messages immediately.[/bold]")
    console.print()
    
    if not confirm_action("Flush mail queue?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    result = run_command("postqueue -f", check=False, silent=True)
    
    if result.returncode == 0:
        show_success("Queue flush initiated!")
        console.print("[dim]Messages will be delivered in the background.[/dim]")
    else:
        show_error("Failed to flush queue.")
    
    press_enter_to_continue()


def hold_release_menu():
    """Hold or release messages."""
    clear_screen()
    show_header()
    show_panel("Hold/Release Messages", title="Queue Management", style="cyan")
    
    options = [
        "Hold all messages",
        "Release all held messages",
        "Hold specific message",
        "Release specific message",
    ]
    
    choice = select_from_list("Action", "Select:", options)
    if not choice:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if "Hold all" in choice:
        result = run_command("postsuper -h ALL", check=False, silent=True)
        if result.returncode == 0:
            show_success("All messages held!")
        else:
            show_error("Failed to hold messages.")
    elif "Release all" in choice:
        result = run_command("postsuper -H ALL", check=False, silent=True)
        if result.returncode == 0:
            show_success("All messages released!")
        else:
            show_error("Failed to release messages.")
    elif "Hold specific" in choice:
        queue_id = text_input("Queue ID:")
        if queue_id:
            result = run_command(f"postsuper -h {queue_id}", check=False, silent=True)
            if result.returncode == 0:
                show_success(f"Message {queue_id} held!")
            else:
                show_error("Failed to hold message.")
    else:
        queue_id = text_input("Queue ID:")
        if queue_id:
            result = run_command(f"postsuper -H {queue_id}", check=False, silent=True)
            if result.returncode == 0:
                show_success(f"Message {queue_id} released!")
            else:
                show_error("Failed to release message.")
    
    press_enter_to_continue()


def delete_messages():
    """Delete queued messages."""
    clear_screen()
    show_header()
    show_panel("Delete Messages", title="Queue Management", style="red")
    
    if not is_postfix_ready():
        show_error("Postfix is not running.")
        press_enter_to_continue()
        return
    
    options = [
        "Delete ALL messages",
        "Delete specific message",
        "Delete by recipient",
    ]
    
    choice = select_from_list("Action", "Select:", options)
    if not choice:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if "ALL" in choice:
        console.print("[bold red]WARNING: This will permanently delete ALL queued emails![/bold red]")
        if not confirm_action("Delete all queued messages?"):
            return
        
        result = run_command("postsuper -d ALL", check=False, silent=True)
        if result.returncode == 0:
            show_success("All queued messages deleted!")
        else:
            show_error("Failed to delete messages.")
    
    elif "specific" in choice:
        queue_id = text_input("Queue ID:")
        if queue_id:
            result = run_command(f"postsuper -d {queue_id}", check=False, silent=True)
            if result.returncode == 0:
                show_success(f"Message {queue_id} deleted!")
            else:
                show_error("Failed to delete message.")
    
    else:
        recipient = text_input("Recipient email:")
        if recipient:
            # Find and delete by recipient
            result = run_command(
                f"postqueue -p | grep -B2 '{recipient}' | grep '^[A-F0-9]' | cut -d' ' -f1 | cut -d'*' -f1",
                check=False, silent=True
            )
            
            if result.stdout.strip():
                queue_ids = result.stdout.strip().split('\n')
                console.print(f"Found {len(queue_ids)} message(s) for {recipient}")
                
                if confirm_action("Delete these messages?"):
                    for qid in queue_ids:
                        if qid.strip():
                            run_command(f"postsuper -d {qid.strip()}", check=False, silent=True)
                    show_success(f"Deleted {len(queue_ids)} message(s)!")
            else:
                show_info(f"No messages found for {recipient}")
    
    press_enter_to_continue()


def requeue_all():
    """Requeue all deferred messages."""
    clear_screen()
    show_header()
    show_panel("Requeue All", title="Queue Management", style="cyan")
    
    console.print("[bold]This will requeue all deferred messages for immediate retry.[/bold]")
    console.print()
    
    if not confirm_action("Requeue all deferred messages?"):
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    result = run_command("postsuper -r ALL", check=False, silent=True)
    
    if result.returncode == 0:
        show_success("All messages requeued!")
    else:
        show_error("Failed to requeue messages.")
    
    press_enter_to_continue()
