# Nginx Site Configuration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add per-site Nginx configuration with presets (Laravel, WordPress, Static, SPA, Node.js, Custom) and fine-grained options (PHP version, SSL, gzip, cache, security headers, rate limiting, IP rules).

**Architecture:** Template-based config generation using preset templates + reusable snippets. Wizard flow for new domains, separate "Configure Site" menu for editing existing sites. All configs stored in `/etc/nginx/sites-available/`.

**Tech Stack:** Python, Jinja2-style placeholders, InquirerPy for menus

---

## Task 1: Create Nginx Template Directory Structure

**Files:**
- Create: `templates/nginx/laravel.conf`
- Create: `templates/nginx/wordpress.conf`
- Create: `templates/nginx/static.conf`
- Create: `templates/nginx/spa.conf`
- Create: `templates/nginx/nodejs.conf`

**Step 1: Create Laravel template**

```nginx
# templates/nginx/laravel.conf
server {
    listen 80;
    listen [::]:80;
    {{ssl_listen}}

    server_name {{domain}}{{www_alias}};
    root {{root_path}};

    index index.php index.html index.htm;

    # Logging
    access_log /var/log/nginx/{{domain}}.access.log;
    error_log /var/log/nginx/{{domain}}.error.log;

    {{ssl_config}}
    {{redirect_config}}
    {{gzip_config}}
    {{security_headers}}
    {{rate_limit_config}}
    {{ip_rules}}

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    {{php_fpm_config}}

    {{cache_static_config}}

    # Deny access to hidden files
    location ~ /\. {
        deny all;
    }

    # Deny access to sensitive files
    location ~* \.(env|log|sql)$ {
        deny all;
    }
}
```

**Step 2: Create WordPress template**

```nginx
# templates/nginx/wordpress.conf
server {
    listen 80;
    listen [::]:80;
    {{ssl_listen}}

    server_name {{domain}}{{www_alias}};
    root {{root_path}};

    index index.php index.html index.htm;

    access_log /var/log/nginx/{{domain}}.access.log;
    error_log /var/log/nginx/{{domain}}.error.log;

    {{ssl_config}}
    {{redirect_config}}
    {{gzip_config}}
    {{security_headers}}
    {{rate_limit_config}}
    {{ip_rules}}

    location / {
        try_files $uri $uri/ /index.php?$args;
    }

    {{php_fpm_config}}

    {{cache_static_config}}

    # WordPress security
    location ~* /(?:uploads|files)/.*\.php$ {
        deny all;
    }

    location ~* /wp-includes/.*\.php$ {
        deny all;
    }

    location ~* /wp-content/.*\.php$ {
        allow all;
    }

    # Deny access to sensitive WP files
    location ~ /(\.|wp-config\.php|readme\.html|license\.txt) {
        deny all;
    }
}
```

**Step 3: Create Static template**

```nginx
# templates/nginx/static.conf
server {
    listen 80;
    listen [::]:80;
    {{ssl_listen}}

    server_name {{domain}}{{www_alias}};
    root {{root_path}};

    index index.html index.htm;

    access_log /var/log/nginx/{{domain}}.access.log;
    error_log /var/log/nginx/{{domain}}.error.log;

    {{ssl_config}}
    {{redirect_config}}
    {{gzip_config}}
    {{security_headers}}
    {{rate_limit_config}}
    {{ip_rules}}

    location / {
        try_files $uri $uri/ =404;
    }

    {{cache_static_config}}

    location ~ /\. {
        deny all;
    }
}
```

**Step 4: Create SPA template**

```nginx
# templates/nginx/spa.conf
server {
    listen 80;
    listen [::]:80;
    {{ssl_listen}}

    server_name {{domain}}{{www_alias}};
    root {{root_path}};

    index index.html;

    access_log /var/log/nginx/{{domain}}.access.log;
    error_log /var/log/nginx/{{domain}}.error.log;

    {{ssl_config}}
    {{redirect_config}}
    {{gzip_config}}
    {{security_headers}}
    {{rate_limit_config}}
    {{ip_rules}}

    location / {
        try_files $uri $uri/ /index.html;
    }

    {{cache_static_config}}

    location ~ /\. {
        deny all;
    }
}
```

**Step 5: Create Node.js/Proxy template**

```nginx
# templates/nginx/nodejs.conf
server {
    listen 80;
    listen [::]:80;
    {{ssl_listen}}

    server_name {{domain}}{{www_alias}};

    access_log /var/log/nginx/{{domain}}.access.log;
    error_log /var/log/nginx/{{domain}}.error.log;

    {{ssl_config}}
    {{redirect_config}}
    {{gzip_config}}
    {{security_headers}}
    {{rate_limit_config}}
    {{ip_rules}}

    location / {
        proxy_pass http://127.0.0.1:{{proxy_port}};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
```

**Step 6: Commit**

```bash
git add templates/nginx/
git commit -m "feat(nginx): add site type preset templates"
```

---

## Task 2: Create Nginx Snippets

**Files:**
- Create: `templates/nginx/snippets/ssl.conf`
- Create: `templates/nginx/snippets/gzip.conf`
- Create: `templates/nginx/snippets/cache-static.conf`
- Create: `templates/nginx/snippets/security-headers.conf`
- Create: `templates/nginx/snippets/rate-limit.conf`
- Create: `templates/nginx/snippets/php-fpm.conf`

**Step 1: Create SSL snippet**

```nginx
# templates/nginx/snippets/ssl.conf
    listen 443 ssl http2;
    listen [::]:443 ssl http2;

    ssl_certificate /etc/letsencrypt/live/{{domain}}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{{domain}}/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/{{domain}}/chain.pem;

    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    ssl_stapling on;
    ssl_stapling_verify on;
```

**Step 2: Create Gzip snippet**

```nginx
# templates/nginx/snippets/gzip.conf
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_min_length 256;
    gzip_types
        application/atom+xml
        application/javascript
        application/json
        application/ld+json
        application/manifest+json
        application/rss+xml
        application/vnd.geo+json
        application/vnd.ms-fontobject
        application/x-font-ttf
        application/x-web-app-manifest+json
        application/xhtml+xml
        application/xml
        font/opentype
        image/bmp
        image/svg+xml
        image/x-icon
        text/cache-manifest
        text/css
        text/plain
        text/vcard
        text/vnd.rim.location.xloc
        text/vtt
        text/x-component
        text/x-cross-domain-policy
        text/xml;
```

**Step 3: Create cache-static snippet**

```nginx
# templates/nginx/snippets/cache-static.conf
    location ~* \.(jpg|jpeg|png|gif|ico|webp|svg)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location ~* \.(css|js)$ {
        expires 7d;
        add_header Cache-Control "public";
    }

    location ~* \.(woff|woff2|ttf|otf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
```

**Step 4: Create security-headers snippet**

```nginx
# templates/nginx/snippets/security-headers.conf
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

**Step 5: Create rate-limit snippet**

```nginx
# templates/nginx/snippets/rate-limit.conf
    limit_req zone={{domain_safe}}_limit burst=20 nodelay;
    limit_conn {{domain_safe}}_conn 20;
```

**Step 6: Create PHP-FPM snippet**

```nginx
# templates/nginx/snippets/php-fpm.conf
    location ~ \.php$ {
        fastcgi_pass unix:/run/php/php{{php_version}}-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
        include fastcgi_params;
        fastcgi_hide_header X-Powered-By;
    }
```

**Step 7: Commit**

```bash
git add templates/nginx/snippets/
git commit -m "feat(nginx): add reusable config snippets"
```

---

## Task 3: Add Site Config Data Structure

**Files:**
- Modify: `modules/webserver.py` (add at top after imports)

**Step 1: Add SITE_TYPES constant and helper functions**

Add after the imports in `modules/webserver.py`:

```python
# Site type presets
SITE_TYPES = [
    ("laravel", "Laravel/PHP Application"),
    ("wordpress", "WordPress"),
    ("static", "Static HTML"),
    ("spa", "SPA (React/Vue/Angular)"),
    ("nodejs", "Node.js/Proxy"),
    ("custom", "Custom Configuration"),
]

# Default site configuration
DEFAULT_SITE_CONFIG = {
    "site_type": "laravel",
    "php_version": "8.3",
    "ssl_enabled": False,
    "www_redirect": "none",  # none, www_to_non, non_to_www
    "gzip_enabled": True,
    "cache_static": True,
    "security_headers": True,
    "rate_limit_enabled": False,
    "rate_limit_requests": 10,
    "ip_whitelist": [],
    "ip_blacklist": [],
    "proxy_port": 3000,
}


def _get_site_config(domain):
    """
    Read site configuration from Nginx config file comments.
    Returns DEFAULT_SITE_CONFIG merged with saved values.
    """
    config = DEFAULT_SITE_CONFIG.copy()
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    
    if not os.path.exists(config_path):
        return config
    
    try:
        with open(config_path, "r") as f:
            content = f.read()
        
        # Parse config from header comment: # VEXO_CONFIG: {"key": "value", ...}
        match = re.search(r'# VEXO_CONFIG: ({.*})', content)
        if match:
            import json
            saved = json.loads(match.group(1))
            config.update(saved)
    except Exception:
        pass
    
    return config


def _domain_to_safe_name(domain):
    """Convert domain to safe variable name for nginx."""
    return domain.replace(".", "_").replace("-", "_")
```

**Step 2: Commit**

```bash
git add modules/webserver.py
git commit -m "feat(nginx): add site config data structure"
```

---

## Task 4: Create Config Generator Function

**Files:**
- Modify: `modules/webserver.py` (add function)

**Step 1: Add generate_site_config function**

```python
def generate_site_config(domain, root_path, config):
    """
    Generate Nginx config from template and options.
    
    Args:
        domain: Domain name
        root_path: Document root path
        config: Site configuration dict
    
    Returns:
        str: Generated Nginx configuration
    """
    import json
    
    site_type = config.get("site_type", "laravel")
    template_path = os.path.join(TEMPLATES_DIR, "nginx", f"{site_type}.conf")
    
    # Fallback to laravel if template not found
    if not os.path.exists(template_path):
        template_path = os.path.join(TEMPLATES_DIR, "nginx", "laravel.conf")
    
    with open(template_path, "r") as f:
        template = f.read()
    
    snippets_dir = os.path.join(TEMPLATES_DIR, "nginx", "snippets")
    
    # Basic replacements
    output = template.replace("{{domain}}", domain)
    output = output.replace("{{root_path}}", root_path)
    output = output.replace("{{domain_safe}}", _domain_to_safe_name(domain))
    
    # WWW alias
    www_redirect = config.get("www_redirect", "none")
    if www_redirect == "none":
        output = output.replace("{{www_alias}}", f" www.{domain}")
    else:
        output = output.replace("{{www_alias}}", "")
    
    # SSL config
    if config.get("ssl_enabled", False):
        with open(os.path.join(snippets_dir, "ssl.conf"), "r") as f:
            ssl_snippet = f.read().replace("{{domain}}", domain)
        output = output.replace("{{ssl_listen}}", "")
        output = output.replace("{{ssl_config}}", ssl_snippet)
    else:
        output = output.replace("{{ssl_listen}}", "")
        output = output.replace("{{ssl_config}}", "")
    
    # Redirect config
    redirect_config = ""
    if www_redirect == "www_to_non":
        redirect_config = f"""
    if ($host = www.{domain}) {{
        return 301 $scheme://{domain}$request_uri;
    }}"""
    elif www_redirect == "non_to_www":
        redirect_config = f"""
    if ($host = {domain}) {{
        return 301 $scheme://www.{domain}$request_uri;
    }}"""
    output = output.replace("{{redirect_config}}", redirect_config)
    
    # Gzip
    if config.get("gzip_enabled", True):
        with open(os.path.join(snippets_dir, "gzip.conf"), "r") as f:
            output = output.replace("{{gzip_config}}", f.read())
    else:
        output = output.replace("{{gzip_config}}", "")
    
    # Security headers
    if config.get("security_headers", True):
        with open(os.path.join(snippets_dir, "security-headers.conf"), "r") as f:
            output = output.replace("{{security_headers}}", f.read())
    else:
        output = output.replace("{{security_headers}}", "")
    
    # Rate limiting
    if config.get("rate_limit_enabled", False):
        with open(os.path.join(snippets_dir, "rate-limit.conf"), "r") as f:
            rate_limit = f.read()
            rate_limit = rate_limit.replace("{{domain_safe}}", _domain_to_safe_name(domain))
        output = output.replace("{{rate_limit_config}}", rate_limit)
    else:
        output = output.replace("{{rate_limit_config}}", "")
    
    # IP rules
    ip_rules = ""
    for ip in config.get("ip_whitelist", []):
        ip_rules += f"    allow {ip};\n"
    if config.get("ip_whitelist"):
        ip_rules += "    deny all;\n"
    for ip in config.get("ip_blacklist", []):
        ip_rules += f"    deny {ip};\n"
    output = output.replace("{{ip_rules}}", ip_rules)
    
    # PHP-FPM config
    php_version = config.get("php_version", "8.3")
    if site_type in ["laravel", "wordpress"]:
        with open(os.path.join(snippets_dir, "php-fpm.conf"), "r") as f:
            php_config = f.read().replace("{{php_version}}", php_version)
        output = output.replace("{{php_fpm_config}}", php_config)
    else:
        output = output.replace("{{php_fpm_config}}", "")
    
    # Static cache
    if config.get("cache_static", True):
        with open(os.path.join(snippets_dir, "cache-static.conf"), "r") as f:
            output = output.replace("{{cache_static_config}}", f.read())
    else:
        output = output.replace("{{cache_static_config}}", "")
    
    # Proxy port for Node.js
    proxy_port = config.get("proxy_port", 3000)
    output = output.replace("{{proxy_port}}", str(proxy_port))
    
    # Add config header for future reads
    config_json = json.dumps(config)
    header = f"# VEXO_CONFIG: {config_json}\n"
    output = header + output
    
    return output
```

**Step 2: Commit**

```bash
git add modules/webserver.py
git commit -m "feat(nginx): add config generator function"
```

---

## Task 5: Update add_domain_interactive with Wizard

**Files:**
- Modify: `modules/webserver.py` (replace add_domain_interactive function)

**Step 1: Replace add_domain_interactive with wizard flow**

```python
def add_domain_interactive():
    """Interactive wizard to add a new domain with site type selection."""
    clear_screen()
    show_header()
    show_panel("Add New Domain", title="Domain & Nginx", style="cyan")
    
    if not is_installed("nginx"):
        show_error("Nginx is not installed. Please install it first.")
        press_enter_to_continue()
        return
    
    # Step 1: Domain name
    domain = text_input(
        "Enter domain name (e.g., example.com):",
        title="Add Domain"
    )
    
    if not domain:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    domain = domain.strip().lower()
    if not _is_valid_domain(domain):
        show_error(f"Invalid domain name: {domain}")
        press_enter_to_continue()
        return
    
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    if os.path.exists(config_path):
        show_error(f"Domain {domain} already exists.")
        press_enter_to_continue()
        return
    
    # Step 2: Site type
    console.print()
    site_type = select_from_list(
        title="Site Type",
        message="Select site type",
        options=[label for _, label in SITE_TYPES]
    )
    
    if not site_type:
        show_warning("Cancelled.")
        press_enter_to_continue()
        return
    
    # Map label back to key
    site_type_key = next((k for k, v in SITE_TYPES if v == site_type), "laravel")
    
    # Step 3: Root path (not for Node.js)
    if site_type_key == "nodejs":
        root_path = ""
        proxy_port = text_input(
            "Enter application port:",
            title="Proxy Port",
            default="3000"
        )
        if not proxy_port:
            show_warning("Cancelled.")
            press_enter_to_continue()
            return
    else:
        default_root = os.path.join(DEFAULT_WEB_ROOT, domain, "public")
        if site_type_key in ["static", "spa"]:
            default_root = os.path.join(DEFAULT_WEB_ROOT, domain, "dist")
        
        root_path = text_input(
            "Enter document root path:",
            title="Document Root",
            default=default_root
        )
        
        if not root_path:
            show_warning("Cancelled.")
            press_enter_to_continue()
            return
        proxy_port = 3000
    
    # Step 4: PHP version (only for PHP sites)
    php_version = "8.3"
    if site_type_key in ["laravel", "wordpress"]:
        from modules.runtime import _get_installed_php_versions
        installed_php = _get_installed_php_versions()
        if installed_php:
            php_choice = select_from_list(
                title="PHP Version",
                message="Select PHP version",
                options=[f"PHP {v}" for v in installed_php]
            )
            if php_choice:
                php_version = php_choice.replace("PHP ", "")
    
    # Step 5: Quick options
    console.print()
    ssl_enabled = confirm_action("Enable SSL? (requires existing certificate)")
    
    www_options = ["No redirect", "www → non-www", "non-www → www"]
    www_choice = select_from_list(
        title="WWW Redirect",
        message="Configure www redirect",
        options=www_options
    )
    www_redirect = "none"
    if www_choice == "www → non-www":
        www_redirect = "www_to_non"
    elif www_choice == "non-www → www":
        www_redirect = "non_to_www"
    
    # Step 6: Advanced options
    gzip_enabled = True
    cache_static = True
    security_headers = True
    rate_limit_enabled = False
    
    console.print()
    if confirm_action("Configure advanced options?"):
        gzip_enabled = confirm_action("Enable Gzip compression?")
        cache_static = confirm_action("Enable browser caching for static files?")
        security_headers = confirm_action("Enable security headers?")
        rate_limit_enabled = confirm_action("Enable rate limiting?")
    
    # Build config
    config = {
        "site_type": site_type_key,
        "php_version": php_version,
        "ssl_enabled": ssl_enabled,
        "www_redirect": www_redirect,
        "gzip_enabled": gzip_enabled,
        "cache_static": cache_static,
        "security_headers": security_headers,
        "rate_limit_enabled": rate_limit_enabled,
        "proxy_port": int(proxy_port) if site_type_key == "nodejs" else 3000,
        "ip_whitelist": [],
        "ip_blacklist": [],
    }
    
    try:
        require_root()
    except PermissionError:
        press_enter_to_continue()
        return
    
    # Create document root if needed
    if root_path and not os.path.exists(root_path):
        os.makedirs(root_path, exist_ok=True)
        if site_type_key in ["static", "spa"]:
            index_path = os.path.join(root_path, "index.html")
            with open(index_path, "w") as f:
                f.write(f"<!DOCTYPE html>\n<html><body><h1>Welcome to {domain}</h1></body></html>\n")
    
    # Generate and save config
    nginx_config = generate_site_config(domain, root_path, config)
    
    try:
        with open(config_path, "w") as f:
            f.write(nginx_config)
        
        if enable_domain(domain):
            show_success(f"Domain {domain} added successfully!")
            console.print()
            console.print(f"[dim]Type: {site_type}[/dim]")
            console.print(f"[dim]Config: {config_path}[/dim]")
            if root_path:
                console.print(f"[dim]Root: {root_path}[/dim]")
        else:
            show_error(f"Failed to enable domain {domain}")
    except Exception as e:
        show_error(f"Error: {e}")
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/webserver.py
git commit -m "feat(nginx): add wizard flow to add_domain_interactive"
```

---

## Task 6: Add Configure Site Menu

**Files:**
- Modify: `modules/webserver.py` (add to show_menu and new functions)

**Step 1: Update show_menu to include Configure Site option**

Update the options list in show_menu():

```python
        if is_installed("nginx"):
            options.extend([
                ("list", "1. List Domains"),
                ("add", "2. Add New Domain"),
                ("configure", "3. Configure Site"),
                ("remove", "4. Remove Domain"),
                ("reload", "5. Reload Nginx"),
                ("status", "6. Nginx Status"),
            ])
```

And add the handler:

```python
        elif choice == "configure":
            configure_site_menu()
```

**Step 2: Add configure_site_menu function**

```python
def configure_site_menu():
    """Menu to configure an existing site."""
    clear_screen()
    show_header()
    show_panel("Configure Site", title="Domain & Nginx", style="cyan")
    
    domains = _get_configured_domains()
    if not domains:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    domain = select_from_list(
        title="Select Domain",
        message="Choose site to configure",
        options=domains
    )
    
    if not domain:
        return
    
    while True:
        clear_screen()
        show_header()
        
        config = _get_site_config(domain)
        site_type_label = next((v for k, v in SITE_TYPES if k == config.get("site_type")), "Unknown")
        
        console.print(f"[bold cyan]Configuring: {domain}[/bold cyan]")
        console.print(f"[dim]Type: {site_type_label} | PHP: {config.get('php_version', 'N/A')} | SSL: {'Yes' if config.get('ssl_enabled') else 'No'}[/dim]")
        console.print()
        
        choice = show_submenu(
            title=f"Configure: {domain}",
            options=[
                ("type", "1. Change Site Type"),
                ("php", "2. Change PHP Version"),
                ("ssl", "3. SSL Settings"),
                ("redirect", "4. WWW Redirect"),
                ("performance", "5. Performance (Gzip, Cache)"),
                ("security", "6. Security (Headers, Rate Limit)"),
                ("ip", "7. IP Rules (Whitelist/Blacklist)"),
                ("view", "8. View Current Config"),
                ("edit", "9. Edit Raw Config"),
                ("back", "← Back"),
            ],
        )
        
        if choice == "type":
            configure_site_type(domain, config)
        elif choice == "php":
            configure_php_version(domain, config)
        elif choice == "ssl":
            configure_ssl(domain, config)
        elif choice == "redirect":
            configure_redirect(domain, config)
        elif choice == "performance":
            configure_performance(domain, config)
        elif choice == "security":
            configure_security(domain, config)
        elif choice == "ip":
            configure_ip_rules(domain, config)
        elif choice == "view":
            view_site_config(domain)
        elif choice == "edit":
            edit_raw_config(domain)
        elif choice == "back" or choice is None:
            break
```

**Step 3: Add configuration helper functions**

```python
def _save_site_config(domain, config):
    """Regenerate and save site config."""
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    
    # Get root path from existing config
    root_path = ""
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            content = f.read()
        match = re.search(r'root\s+([^;]+);', content)
        if match:
            root_path = match.group(1).strip()
    
    nginx_config = generate_site_config(domain, root_path, config)
    
    try:
        with open(config_path, "w") as f:
            f.write(nginx_config)
        
        result = run_command("nginx -t", check=False, silent=True)
        if result.returncode != 0:
            show_error("Nginx config test failed!")
            console.print(f"[dim]{result.stderr}[/dim]")
            return False
        
        reload_nginx(silent=True)
        return True
    except Exception as e:
        show_error(f"Error saving config: {e}")
        return False


def configure_site_type(domain, config):
    """Change site type."""
    clear_screen()
    show_header()
    
    current = next((v for k, v in SITE_TYPES if k == config.get("site_type")), "Unknown")
    console.print(f"[dim]Current type: {current}[/dim]")
    console.print()
    
    new_type = select_from_list(
        title="Site Type",
        message="Select new site type",
        options=[label for _, label in SITE_TYPES if _ != "custom"]
    )
    
    if not new_type:
        return
    
    new_type_key = next((k for k, v in SITE_TYPES if v == new_type), config.get("site_type"))
    
    if new_type_key == config.get("site_type"):
        show_info("Site type unchanged.")
        press_enter_to_continue()
        return
    
    config["site_type"] = new_type_key
    
    if _save_site_config(domain, config):
        show_success(f"Site type changed to {new_type}!")
    
    press_enter_to_continue()


def configure_php_version(domain, config):
    """Change PHP version for site."""
    clear_screen()
    show_header()
    
    if config.get("site_type") not in ["laravel", "wordpress"]:
        show_info("PHP version only applies to Laravel/WordPress sites.")
        press_enter_to_continue()
        return
    
    from modules.runtime import _get_installed_php_versions
    installed = _get_installed_php_versions()
    
    if not installed:
        show_error("No PHP versions installed.")
        press_enter_to_continue()
        return
    
    console.print(f"[dim]Current: PHP {config.get('php_version', '8.3')}[/dim]")
    console.print()
    
    choice = select_from_list(
        title="PHP Version",
        message="Select PHP version",
        options=[f"PHP {v}" for v in installed]
    )
    
    if not choice:
        return
    
    new_version = choice.replace("PHP ", "")
    config["php_version"] = new_version
    
    if _save_site_config(domain, config):
        show_success(f"PHP version changed to {new_version}!")
    
    press_enter_to_continue()


def configure_ssl(domain, config):
    """Configure SSL settings."""
    clear_screen()
    show_header()
    
    current = "Enabled" if config.get("ssl_enabled") else "Disabled"
    console.print(f"[dim]SSL currently: {current}[/dim]")
    console.print()
    
    ssl_enabled = confirm_action("Enable SSL?")
    config["ssl_enabled"] = ssl_enabled
    
    if _save_site_config(domain, config):
        status = "enabled" if ssl_enabled else "disabled"
        show_success(f"SSL {status}!")
    
    press_enter_to_continue()


def configure_redirect(domain, config):
    """Configure www redirect."""
    clear_screen()
    show_header()
    
    current = config.get("www_redirect", "none")
    console.print(f"[dim]Current redirect: {current}[/dim]")
    console.print()
    
    options = ["No redirect", "www → non-www", "non-www → www"]
    choice = select_from_list(
        title="WWW Redirect",
        message="Select redirect option",
        options=options
    )
    
    if not choice:
        return
    
    if choice == "www → non-www":
        config["www_redirect"] = "www_to_non"
    elif choice == "non-www → www":
        config["www_redirect"] = "non_to_www"
    else:
        config["www_redirect"] = "none"
    
    if _save_site_config(domain, config):
        show_success("Redirect settings updated!")
    
    press_enter_to_continue()


def configure_performance(domain, config):
    """Configure performance options."""
    clear_screen()
    show_header()
    show_panel("Performance Settings", title=domain, style="cyan")
    
    console.print(f"[dim]Gzip: {'On' if config.get('gzip_enabled') else 'Off'}[/dim]")
    console.print(f"[dim]Static Cache: {'On' if config.get('cache_static') else 'Off'}[/dim]")
    console.print()
    
    config["gzip_enabled"] = confirm_action("Enable Gzip compression?")
    config["cache_static"] = confirm_action("Enable browser caching for static files?")
    
    if _save_site_config(domain, config):
        show_success("Performance settings updated!")
    
    press_enter_to_continue()


def configure_security(domain, config):
    """Configure security options."""
    clear_screen()
    show_header()
    show_panel("Security Settings", title=domain, style="cyan")
    
    console.print(f"[dim]Security Headers: {'On' if config.get('security_headers') else 'Off'}[/dim]")
    console.print(f"[dim]Rate Limiting: {'On' if config.get('rate_limit_enabled') else 'Off'}[/dim]")
    console.print()
    
    config["security_headers"] = confirm_action("Enable security headers?")
    config["rate_limit_enabled"] = confirm_action("Enable rate limiting?")
    
    if _save_site_config(domain, config):
        show_success("Security settings updated!")
    
    press_enter_to_continue()


def configure_ip_rules(domain, config):
    """Configure IP whitelist/blacklist."""
    clear_screen()
    show_header()
    show_panel("IP Rules", title=domain, style="cyan")
    
    whitelist = config.get("ip_whitelist", [])
    blacklist = config.get("ip_blacklist", [])
    
    console.print(f"[dim]Whitelist: {', '.join(whitelist) if whitelist else 'None'}[/dim]")
    console.print(f"[dim]Blacklist: {', '.join(blacklist) if blacklist else 'None'}[/dim]")
    console.print()
    
    choice = show_submenu(
        title="IP Rules",
        options=[
            ("add_white", "1. Add IP to Whitelist"),
            ("add_black", "2. Add IP to Blacklist"),
            ("clear_white", "3. Clear Whitelist"),
            ("clear_black", "4. Clear Blacklist"),
            ("back", "← Back"),
        ],
    )
    
    if choice == "add_white":
        ip = text_input("Enter IP address:", title="Whitelist")
        if ip:
            config["ip_whitelist"] = whitelist + [ip.strip()]
            if _save_site_config(domain, config):
                show_success(f"Added {ip} to whitelist!")
    elif choice == "add_black":
        ip = text_input("Enter IP address:", title="Blacklist")
        if ip:
            config["ip_blacklist"] = blacklist + [ip.strip()]
            if _save_site_config(domain, config):
                show_success(f"Added {ip} to blacklist!")
    elif choice == "clear_white":
        if confirm_action("Clear whitelist?"):
            config["ip_whitelist"] = []
            if _save_site_config(domain, config):
                show_success("Whitelist cleared!")
    elif choice == "clear_black":
        if confirm_action("Clear blacklist?"):
            config["ip_blacklist"] = []
            if _save_site_config(domain, config):
                show_success("Blacklist cleared!")
    
    if choice != "back":
        press_enter_to_continue()


def view_site_config(domain):
    """View current Nginx config."""
    clear_screen()
    show_header()
    
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    
    if not os.path.exists(config_path):
        show_error("Config file not found.")
        press_enter_to_continue()
        return
    
    with open(config_path, "r") as f:
        content = f.read()
    
    console.print(f"[bold]Config: {config_path}[/bold]")
    console.print()
    console.print(content)
    
    press_enter_to_continue()


def edit_raw_config(domain):
    """Open config in editor."""
    config_path = os.path.join(NGINX_SITES_AVAILABLE, domain)
    
    if not os.path.exists(config_path):
        show_error("Config file not found.")
        press_enter_to_continue()
        return
    
    editor = os.environ.get("EDITOR", "nano")
    os.system(f"{editor} {config_path}")
    
    # Test and reload after edit
    result = run_command("nginx -t", check=False, silent=True)
    if result.returncode == 0:
        reload_nginx(silent=True)
        show_success("Config saved and Nginx reloaded!")
    else:
        show_error("Nginx config test failed!")
        console.print(f"[dim]{result.stderr}[/dim]")
    
    press_enter_to_continue()
```

**Step 4: Commit**

```bash
git add modules/webserver.py
git commit -m "feat(nginx): add configure site menu with all options"
```

---

## Task 7: Update list_domains to Show Site Type

**Files:**
- Modify: `modules/webserver.py` (update list_domains function)

**Step 1: Update list_domains to show site type column**

```python
def list_domains():
    """Display a table of configured domains."""
    clear_screen()
    show_header()
    show_panel("Configured Domains", title="Domain & Nginx", style="cyan")
    
    domains = _get_configured_domains()
    
    if not domains:
        show_info("No domains configured.")
        press_enter_to_continue()
        return
    
    columns = [
        {"name": "Domain", "style": "cyan"},
        {"name": "Type", "style": "white"},
        {"name": "Enabled", "justify": "center"},
        {"name": "SSL", "justify": "center"},
    ]
    
    rows = []
    for domain in domains:
        enabled = _is_domain_enabled(domain)
        enabled_str = "[green]✓[/green]" if enabled else "[red]✗[/red]"
        
        config = _get_site_config(domain)
        site_type = config.get("site_type", "unknown")
        site_type_label = next((v for k, v in SITE_TYPES if k == site_type), site_type)
        ssl = "[green]✓[/green]" if config.get("ssl_enabled") else "[dim]-[/dim]"
        
        rows.append([domain, site_type_label, enabled_str, ssl])
    
    show_table(f"Total: {len(domains)} domain(s)", columns, rows)
    
    press_enter_to_continue()
```

**Step 2: Commit**

```bash
git add modules/webserver.py
git commit -m "feat(nginx): show site type in domain list"
```

---

## Task 8: Final Cleanup and Testing

**Step 1: Remove old template**

```bash
rm templates/nginx_vhost.conf
```

**Step 2: Verify syntax**

```bash
python3 -m py_compile modules/webserver.py
```

**Step 3: Final commit**

```bash
git add -A
git commit -m "chore(nginx): remove legacy template, cleanup"
```

---

## Summary

| Task | Description |
|------|-------------|
| 1 | Create 5 preset templates (Laravel, WordPress, Static, SPA, Node.js) |
| 2 | Create 6 reusable snippets (SSL, Gzip, Cache, Security, Rate Limit, PHP-FPM) |
| 3 | Add site config data structure and helpers |
| 4 | Add config generator function |
| 5 | Update add_domain_interactive with wizard flow |
| 6 | Add Configure Site menu with all options |
| 7 | Update list_domains to show site type |
| 8 | Cleanup and verify |

**Total: 8 tasks, ~600 lines of code**
