"""Node.js app deployment tools."""

import os
import re

from config import NGINX_SITES_AVAILABLE, NGINX_SITES_ENABLED, DEFAULT_WEB_ROOT
from ui.components import (
    console, clear_screen, show_header, show_panel,
    show_success, show_error, show_warning, show_info, press_enter_to_continue,
)
from ui.menu import confirm_action, text_input, select_from_list, run_menu_loop
from utils.shell import run_command, service_control, require_root
from modules.runtime.nodejs.utils import run_with_nvm, run_with_nvm_realtime, is_pm2_installed


def show_deploy_menu():
    """Display App Deployment submenu."""
    options = [
        ("deploy", "1. Deploy New App"),
        ("proxy", "2. Configure Nginx Proxy"),
        ("env", "3. Environment Variables"),
        ("systemd", "4. Setup Systemd Service"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "deploy": deploy_new_app,
        "proxy": configure_nginx_proxy,
        "env": manage_env_vars,
        "systemd": setup_systemd_service,
    }
    
    run_menu_loop("App Deployment", options, handlers)


def deploy_new_app():
    """Wizard to deploy a new Node.js app."""
    clear_screen()
    show_header()
    show_panel("Deploy New App", title="App Deployment", style="cyan")
    
    console.print("[bold]Node.js App Deployment Wizard[/bold]")
    console.print()
    
    # Step 1: App directory
    app_dir = text_input("App directory (e.g., /var/www/myapp):")
    if not app_dir:
        return
    
    app_dir = app_dir.strip()
    
    if not os.path.exists(app_dir):
        show_error(f"Directory not found: {app_dir}")
        press_enter_to_continue()
        return
    
    # Check for package.json
    package_json = os.path.join(app_dir, "package.json")
    if not os.path.exists(package_json):
        show_warning("No package.json found. Is this a Node.js project?")
        if not confirm_action("Continue anyway?"):
            press_enter_to_continue()
            return
    
    # Step 2: App name
    default_name = os.path.basename(app_dir)
    app_name = text_input("App name:", default=default_name)
    if not app_name:
        return
    app_name = app_name.strip().lower().replace(" ", "-")
    
    # Step 3: Entry point
    entry_point = text_input("Entry point:", default="server.js")
    if not entry_point:
        return
    
    # Step 4: Port
    port = text_input("App port:", default="3000")
    if not port:
        return
    
    try:
        port = int(port)
    except ValueError:
        show_error("Invalid port number.")
        press_enter_to_continue()
        return
    
    # Step 5: Domain (optional)
    console.print()
    setup_domain = confirm_action("Setup domain with nginx proxy?")
    domain = None
    
    if setup_domain:
        domain = text_input("Domain name (e.g., app.example.com):")
        if domain:
            domain = domain.strip().lower()
    
    # Step 6: Process manager
    console.print()
    pm_options = ["PM2 (recommended)", "Systemd", "None (manual)"]
    pm_choice = select_from_list("Process Manager", "How to manage the app?", pm_options)
    if not pm_choice:
        return
    
    # Confirm
    console.print()
    console.print("[bold]Deployment Summary:[/bold]")
    console.print(f"  Directory: {app_dir}")
    console.print(f"  App Name: {app_name}")
    console.print(f"  Entry: {entry_point}")
    console.print(f"  Port: {port}")
    console.print(f"  Domain: {domain or 'None'}")
    console.print(f"  Process Manager: {pm_choice}")
    console.print()
    
    if not confirm_action("Deploy with these settings?"):
        press_enter_to_continue()
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Execute deployment
    console.print()
    
    # 1. Setup nginx if domain provided
    if domain:
        show_info("Configuring nginx...")
        _create_nginx_proxy(domain, port)
    
    # 2. Setup process manager
    if "PM2" in pm_choice:
        if not is_pm2_installed():
            show_info("Installing PM2...")
            run_with_nvm_realtime("npm install -g pm2", "Installing PM2...")
        
        show_info("Starting app with PM2...")
        entry_path = os.path.join(app_dir, entry_point)
        run_with_nvm_realtime(
            f"cd {app_dir} && pm2 start {entry_path} --name {app_name}",
            f"Starting {app_name}..."
        )
        run_with_nvm("pm2 save")
    
    elif "Systemd" in pm_choice:
        show_info("Creating systemd service...")
        _create_systemd_service(app_name, app_dir, entry_point, port)
    
    console.print()
    show_success(f"App {app_name} deployed!")
    
    if domain:
        console.print()
        console.print(f"[dim]Access: http://{domain}[/dim]")
        console.print(f"[dim]For SSL, run: certbot --nginx -d {domain}[/dim]")
    
    press_enter_to_continue()


def _create_nginx_proxy(domain, port, websocket=False):
    """Create nginx reverse proxy configuration."""
    websocket_config = ""
    if websocket:
        websocket_config = """
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";"""
    
    config = f"""server {{
    listen 80;
    listen [::]:80;
    server_name {domain};

    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;{websocket_config}
    }}
}}
"""
    
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    
    try:
        with open(config_path, "w") as f:
            f.write(config)
        
        # Enable site
        enabled_path = os.path.join(NGINX_SITES_ENABLED, domain)
        if os.path.islink(enabled_path):
            os.remove(enabled_path)
        os.symlink(config_path, enabled_path)
        
        # Test and reload
        result = run_command("nginx -t", check=False, silent=True)
        if result.returncode == 0:
            service_control("nginx", "reload")
            show_success(f"Nginx configured for {domain}")
            return True
        else:
            show_error("Nginx config test failed!")
            console.print(f"[dim]{result.stderr}[/dim]")
            return False
    except Exception as e:
        show_error(f"Failed to create nginx config: {e}")
        return False


def _create_systemd_service(name, app_dir, entry_point, port):
    """Create systemd service for Node.js app."""
    from config import NVM_DIR
    
    service_content = f"""[Unit]
Description={name} Node.js Application
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory={app_dir}
Environment=NODE_ENV=production
Environment=PORT={port}
ExecStart=/bin/bash -c 'source {NVM_DIR}/nvm.sh && node {entry_point}'
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    service_path = f"/etc/systemd/system/{name}.service"
    
    try:
        with open(service_path, "w") as f:
            f.write(service_content)
        
        run_command("systemctl daemon-reload", check=False, silent=True)
        service_control(name, "enable")
        service_control(name, "start")
        
        show_success(f"Systemd service created: {name}")
        return True
    except Exception as e:
        show_error(f"Failed to create service: {e}")
        return False


def configure_nginx_proxy():
    """Configure nginx reverse proxy for existing app."""
    clear_screen()
    show_header()
    show_panel("Configure Nginx Proxy", title="App Deployment", style="cyan")
    
    domain = text_input("Domain name:")
    if not domain:
        return
    domain = domain.strip().lower()
    
    port = text_input("Backend port:", default="3000")
    if not port:
        return
    
    try:
        port = int(port)
    except ValueError:
        show_error("Invalid port.")
        press_enter_to_continue()
        return
    
    websocket = confirm_action("Enable WebSocket support?")
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    if _create_nginx_proxy(domain, port, websocket):
        console.print()
        console.print(f"[dim]For SSL: certbot --nginx -d {domain}[/dim]")
    
    press_enter_to_continue()


def manage_env_vars():
    """Manage environment variables for Node.js apps."""
    clear_screen()
    show_header()
    show_panel("Environment Variables", title="App Deployment", style="cyan")
    
    # Get app directory
    app_dir = text_input("App directory:")
    if not app_dir:
        return
    
    app_dir = app_dir.strip()
    env_path = os.path.join(app_dir, ".env")
    
    # Read current .env if exists
    env_vars = {}
    if os.path.exists(env_path):
        try:
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip()
        except Exception:
            pass
    
    console.print(f"[bold]Current Environment Variables ({len(env_vars)}):[/bold]")
    console.print()
    
    if env_vars:
        for key, value in env_vars.items():
            # Mask sensitive values
            if any(s in key.lower() for s in ["password", "secret", "key", "token"]):
                display_value = "*" * min(len(value), 8)
            else:
                display_value = value[:30] + "..." if len(value) > 30 else value
            console.print(f"  {key}={display_value}")
    else:
        console.print("  [dim]No variables set[/dim]")
    
    console.print()
    
    # Options
    options = ["Add/Edit variable", "Remove variable", "Copy from template"]
    action = select_from_list("Action", "What to do?", options)
    if not action:
        return
    
    if "Add" in action:
        key = text_input("Variable name:")
        if not key:
            return
        key = key.strip().upper()
        
        current = env_vars.get(key, "")
        value = text_input(f"Value for {key}:", default=current)
        if value is None:
            return
        
        env_vars[key] = value
        _save_env_file(env_path, env_vars)
        show_success(f"Set {key}")
    
    elif "Remove" in action:
        if not env_vars:
            show_info("No variables to remove.")
            press_enter_to_continue()
            return
        
        key = select_from_list("Remove Variable", "Select:", list(env_vars.keys()))
        if key:
            del env_vars[key]
            _save_env_file(env_path, env_vars)
            show_success(f"Removed {key}")
    
    elif "template" in action:
        template_path = text_input("Template file path (e.g., .env.example):")
        if not template_path:
            return
        
        template_full = os.path.join(app_dir, template_path)
        if not os.path.exists(template_full):
            show_error("Template file not found.")
            press_enter_to_continue()
            return
        
        if confirm_action("Copy template to .env? (existing values will be preserved)"):
            try:
                with open(template_full, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            if key not in env_vars:
                                env_vars[key] = value.strip()
                
                _save_env_file(env_path, env_vars)
                show_success("Template copied!")
            except Exception as e:
                show_error(f"Failed: {e}")
    
    press_enter_to_continue()


def _save_env_file(path, env_vars):
    """Save environment variables to .env file."""
    try:
        with open(path, "w") as f:
            for key, value in sorted(env_vars.items()):
                f.write(f"{key}={value}\n")
        return True
    except Exception as e:
        show_error(f"Failed to save .env: {e}")
        return False


def setup_systemd_service():
    """Setup systemd service for Node.js app."""
    clear_screen()
    show_header()
    show_panel("Setup Systemd Service", title="App Deployment", style="cyan")
    
    console.print("[bold]Create Systemd Service[/bold]")
    console.print()
    console.print("[dim]Use this as alternative to PM2 for production.[/dim]")
    console.print()
    
    # Get details
    app_dir = text_input("App directory:")
    if not app_dir:
        return
    app_dir = app_dir.strip()
    
    if not os.path.exists(app_dir):
        show_error("Directory not found.")
        press_enter_to_continue()
        return
    
    default_name = os.path.basename(app_dir)
    name = text_input("Service name:", default=default_name)
    if not name:
        return
    name = name.strip().lower().replace(" ", "-")
    
    entry = text_input("Entry point:", default="server.js")
    if not entry:
        return
    
    port = text_input("Port:", default="3000")
    if not port:
        return
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    try:
        port = int(port)
    except ValueError:
        show_error("Invalid port.")
        press_enter_to_continue()
        return
    
    if _create_systemd_service(name, app_dir, entry, port):
        console.print()
        console.print(f"[dim]Manage with: systemctl {{start|stop|restart|status}} {name}[/dim]")
    
    press_enter_to_continue()
