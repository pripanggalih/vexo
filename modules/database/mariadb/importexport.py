"""MariaDB import/export functions."""

import os

from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_success, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, require_root
from utils.error_handler import handle_error
from modules.database.mariadb.utils import (
    is_mariadb_ready, get_user_databases, run_mysql, format_size,
    get_mysql_credentials,
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
    show_panel("Import SQL File", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        handle_error("E4001", "MariaDB is not running.")
        press_enter_to_continue()
        return
    
    sql_file = text_input("SQL file path:")
    if not sql_file:
        return
    
    if not os.path.exists(sql_file):
        handle_error("E4001", "File not found.")
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
        
        result = run_mysql(f"CREATE DATABASE `{db_name}`;")
        if result.returncode != 0:
            handle_error("E4001", f"Failed to create database: {result.stderr}")
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
    
    user, password = get_mysql_credentials()
    if user and password:
        auth = f"-u{user} -p{password}"
    else:
        auth = "-u root"
    
    if is_gzip:
        cmd = f"gunzip -c {sql_file} | mysql {auth} {target}"
    elif is_zip:
        import tempfile
        temp_dir = tempfile.mkdtemp()
        run_command(f"unzip -o {sql_file} -d {temp_dir}", check=False, silent=True)
        sql_files = [f for f in os.listdir(temp_dir) if f.endswith('.sql')]
        if sql_files:
            extracted = os.path.join(temp_dir, sql_files[0])
            cmd = f"mysql {auth} {target} < {extracted}"
        else:
            handle_error("E4001", "No SQL file found in archive.")
            press_enter_to_continue()
            return
    else:
        cmd = f"mysql {auth} {target} < {sql_file}"
    
    result = run_command(cmd, check=False, silent=False)
    
    if result.returncode == 0:
        show_success(f"Import completed to '{target}'!")
    else:
        handle_error("E4001", "Import failed!")
    
    press_enter_to_continue()


def export_database():
    """Export database with options."""
    clear_screen()
    show_header()
    show_panel("Export Database", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        handle_error("E4001", "MariaDB is not running.")
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
        "Structure only (no data)",
        "Data only (no structure)",
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
    
    user, password = get_mysql_credentials()
    if user and password:
        auth = f"-u{user} -p{password}"
    else:
        auth = "-u root"
    
    options = ""
    if "Structure only" in export_type:
        options = "--no-data"
    elif "Data only" in export_type:
        options = "--no-create-info"
    
    if compress:
        cmd = f"mysqldump {auth} {options} {database} | gzip > {output_path}"
    else:
        cmd = f"mysqldump {auth} {options} {database} > {output_path}"
    
    console.print()
    show_info("Exporting...")
    
    result = run_command(cmd, check=False, silent=True)
    
    if result.returncode == 0 and os.path.exists(output_path):
        size = format_size(os.path.getsize(output_path))
        show_success(f"Exported to: {output_path} ({size})")
    else:
        handle_error("E4001", "Export failed!")
    
    press_enter_to_continue()


def export_table():
    """Export a single table."""
    clear_screen()
    show_header()
    show_panel("Export Table", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        handle_error("E4001", "MariaDB is not running.")
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
    
    result = run_mysql(f"SHOW TABLES FROM `{database}`;")
    
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
    
    user, password = get_mysql_credentials()
    if user and password:
        auth = f"-u{user} -p{password}"
    else:
        auth = "-u root"
    
    if fmt == "CSV":
        cmd = f"mysql {auth} -D {database} -e \"SELECT * FROM {table}\" -B | sed 's/\\t/,/g' > {output_path}"
    else:
        cmd = f"mysqldump {auth} {database} {table} > {output_path}"
    
    result = run_command(cmd, check=False, silent=True)
    
    if result.returncode == 0:
        size = format_size(os.path.getsize(output_path))
        show_success(f"Table exported: {output_path} ({size})")
    else:
        handle_error("E4001", "Export failed!")
    
    press_enter_to_continue()


def clone_database():
    """Clone database to new name."""
    clear_screen()
    show_header()
    show_panel("Clone Database", title="MariaDB", style="cyan")
    
    if not is_mariadb_ready():
        handle_error("E4001", "MariaDB is not running.")
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
        handle_error("E4001", f"Database '{new_name}' already exists.")
        press_enter_to_continue()
        return
    
    console.print()
    show_info(f"Cloning {source} to {new_name}...")
    
    result = run_mysql(f"CREATE DATABASE `{new_name}`;")
    if result.returncode != 0:
        handle_error("E4001", "Failed to create database.")
        press_enter_to_continue()
        return
    
    user, password = get_mysql_credentials()
    if user and password:
        auth = f"-u{user} -p{password}"
    else:
        auth = "-u root"
    
    cmd = f"mysqldump {auth} {source} | mysql {auth} {new_name}"
    result = run_command(cmd, check=False, silent=True)
    
    if result.returncode == 0:
        show_success(f"Database cloned: {source} → {new_name}")
    else:
        handle_error("E4001", "Clone failed!")
        run_mysql(f"DROP DATABASE `{new_name}`;")
    
    press_enter_to_continue()


def migration_helper():
    """Generate migration commands for remote transfer."""
    clear_screen()
    show_header()
    show_panel("Migration Helper", title="MariaDB", style="cyan")
    
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
    console.print(f"  mysqldump -u root -p {database} | gzip > /tmp/{database}.sql.gz")
    console.print()
    console.print("[cyan]Step 2: Transfer to remote[/cyan]")
    console.print(f"  scp /tmp/{database}.sql.gz {remote_host}:/tmp/")
    console.print()
    console.print("[cyan]Step 3: Import on remote (run on remote server)[/cyan]")
    console.print(f"  mysql -u root -p -e 'CREATE DATABASE {database}'")
    console.print(f"  gunzip -c /tmp/{database}.sql.gz | mysql -u root -p {database}")
    console.print()
    console.print("[cyan]One-liner (pipe over SSH):[/cyan]")
    console.print(f"  mysqldump -u root -p {database} | ssh {remote_host} 'mysql -u root -p {database}'")
    
    press_enter_to_continue()
