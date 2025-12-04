"""PostgreSQL import/export functions."""

import os

from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_success, show_error, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, require_root
from modules.database.postgresql.utils import (
    is_postgresql_ready, get_user_databases, run_psql, format_size,
)


def show_import_menu():
    """Display Import/Export submenu."""
    options = [
        ("import", "1. Import SQL File"),
        ("export", "2. Export Database"),
        ("export_table", "3. Export Table"),
        ("clone", "4. Clone Database"),
        ("migrate", "5. Migration Helper"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "import": import_sql_file,
        "export": export_database,
        "export_table": export_table,
        "clone": clone_database,
        "migrate": migration_helper,
    }
    
    run_menu_loop("Import/Export", options, handlers)


def import_sql_file():
    """Import SQL file into database."""
    clear_screen()
    show_header()
    show_panel("Import SQL File", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    sql_file = text_input("SQL file path:")
    if not sql_file:
        return
    
    if not os.path.exists(sql_file):
        show_error("File not found.")
        press_enter_to_continue()
        return
    
    is_gzip = sql_file.endswith('.gz')
    is_zip = sql_file.endswith('.zip')
    
    databases = get_user_databases()
    db_options = ["(Create new database)"] + databases
    
    target = select_from_list("Target Database", "Import to:", db_options)
    if not target:
        return
    
    if target == "(Create new database)":
        db_name = text_input("New database name:")
        if not db_name:
            return
        
        result = run_psql(f"CREATE DATABASE {db_name};")
        if result.returncode != 0:
            show_error(f"Failed to create database: {result.stderr}")
            press_enter_to_continue()
            return
        target = db_name
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    console.print()
    show_info(f"Importing to {target}...")
    
    if is_gzip:
        cmd = f"gunzip -c {sql_file} | sudo -u postgres psql {target}"
    elif is_zip:
        import tempfile
        temp_dir = tempfile.mkdtemp()
        run_command(f"unzip -o {sql_file} -d {temp_dir}", check=False, silent=True)
        sql_files = [f for f in os.listdir(temp_dir) if f.endswith('.sql')]
        if sql_files:
            extracted = os.path.join(temp_dir, sql_files[0])
            cmd = f"sudo -u postgres psql {target} < {extracted}"
        else:
            show_error("No SQL file found in archive.")
            press_enter_to_continue()
            return
    else:
        cmd = f"sudo -u postgres psql {target} < {sql_file}"
    
    result = run_command(cmd, check=False, silent=False)
    
    if result.returncode == 0:
        show_success(f"Import completed to '{target}'!")
    else:
        show_error("Import failed!")
    
    press_enter_to_continue()


def export_database():
    """Export database with options."""
    clear_screen()
    show_header()
    show_panel("Export Database", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    databases = get_user_databases()
    if not databases:
        show_info("No user databases found.")
        press_enter_to_continue()
        return
    
    database = select_from_list("Select Database", "Export:", databases)
    if not database:
        return
    
    export_types = [
        "Structure + Data (full)",
        "Structure only (schema)",
        "Data only",
    ]
    
    export_type = select_from_list("Export Type", "What to export:", export_types)
    if not export_type:
        return
    
    compress = confirm_action("Compress output (gzip)?")
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = ".sql.gz" if compress else ".sql"
    default_path = f"/tmp/{database}_{timestamp}{ext}"
    
    output_path = text_input("Output path:", default=default_path)
    if not output_path:
        return
    
    options = ""
    if "Structure only" in export_type:
        options = "--schema-only"
    elif "Data only" in export_type:
        options = "--data-only"
    
    if compress:
        cmd = f"sudo -u postgres pg_dump {options} {database} | gzip > {output_path}"
    else:
        cmd = f"sudo -u postgres pg_dump {options} {database} > {output_path}"
    
    console.print()
    show_info("Exporting...")
    
    result = run_command(cmd, check=False, silent=True)
    
    if result.returncode == 0 and os.path.exists(output_path):
        size = format_size(os.path.getsize(output_path))
        show_success(f"Exported to: {output_path} ({size})")
    else:
        show_error("Export failed!")
    
    press_enter_to_continue()


def export_table():
    """Export a single table."""
    clear_screen()
    show_header()
    show_panel("Export Table", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    databases = get_user_databases()
    if not databases:
        show_info("No user databases found.")
        press_enter_to_continue()
        return
    
    database = select_from_list("Select Database", "From:", databases)
    if not database:
        return
    
    result = run_psql(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public';",
        database=database
    )
    
    if result.returncode != 0 or not result.stdout.strip():
        show_info("No tables found.")
        press_enter_to_continue()
        return
    
    tables = [t.strip() for t in result.stdout.strip().split('\n') if t.strip()]
    
    table = select_from_list("Select Table", "Export:", tables)
    if not table:
        return
    
    formats = ["SQL", "CSV"]
    fmt = select_from_list("Format", "Export as:", formats)
    if not fmt:
        return
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = ".csv" if fmt == "CSV" else ".sql"
    default_path = f"/tmp/{database}_{table}_{timestamp}{ext}"
    
    output_path = text_input("Output path:", default=default_path)
    if not output_path:
        return
    
    if fmt == "CSV":
        cmd = f"sudo -u postgres psql -d {database} -c \"COPY {table} TO STDOUT WITH CSV HEADER\" > {output_path}"
    else:
        cmd = f"sudo -u postgres pg_dump -t {table} {database} > {output_path}"
    
    result = run_command(cmd, check=False, silent=True)
    
    if result.returncode == 0:
        size = format_size(os.path.getsize(output_path))
        show_success(f"Table exported: {output_path} ({size})")
    else:
        show_error("Export failed!")
    
    press_enter_to_continue()


def clone_database():
    """Clone database to new name."""
    clear_screen()
    show_header()
    show_panel("Clone Database", title="PostgreSQL", style="cyan")
    
    if not is_postgresql_ready():
        show_error("PostgreSQL is not running.")
        press_enter_to_continue()
        return
    
    databases = get_user_databases()
    if not databases:
        show_info("No user databases found.")
        press_enter_to_continue()
        return
    
    source = select_from_list("Source Database", "Clone from:", databases)
    if not source:
        return
    
    new_name = text_input("New database name:")
    if not new_name:
        return
    
    if new_name in databases:
        show_error(f"Database '{new_name}' already exists.")
        press_enter_to_continue()
        return
    
    console.print()
    show_info(f"Cloning {source} to {new_name}...")
    
    result = run_psql(f"CREATE DATABASE {new_name} WITH TEMPLATE {source};")
    
    if result.returncode == 0:
        show_success(f"Database cloned: {source} → {new_name}")
    else:
        show_error("Clone failed!")
        console.print(f"[dim]{result.stderr}[/dim]")
    
    press_enter_to_continue()


def migration_helper():
    """Generate migration commands for remote transfer."""
    clear_screen()
    show_header()
    show_panel("Migration Helper", title="PostgreSQL", style="cyan")
    
    databases = get_user_databases()
    if not databases:
        show_info("No user databases found.")
        press_enter_to_continue()
        return
    
    database = select_from_list("Select Database", "Migrate:", databases)
    if not database:
        return
    
    remote_host = text_input("Remote host (e.g., user@server.com):")
    if not remote_host:
        return
    
    console.print()
    console.print("[bold]Migration Commands:[/bold]")
    console.print()
    console.print("[cyan]Step 1: Export on this server[/cyan]")
    console.print(f"  sudo -u postgres pg_dump {database} | gzip > /tmp/{database}.sql.gz")
    console.print()
    console.print("[cyan]Step 2: Transfer to remote[/cyan]")
    console.print(f"  scp /tmp/{database}.sql.gz {remote_host}:/tmp/")
    console.print()
    console.print("[cyan]Step 3: Import on remote (run on remote server)[/cyan]")
    console.print(f"  sudo -u postgres createdb {database}")
    console.print(f"  gunzip -c /tmp/{database}.sql.gz | sudo -u postgres psql {database}")
    console.print()
    console.print("[cyan]One-liner (pipe over SSH):[/cyan]")
    console.print(f"  sudo -u postgres pg_dump {database} | ssh {remote_host} 'sudo -u postgres psql {database}'")
    
    press_enter_to_continue()
