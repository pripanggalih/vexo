"""Web application jail templates."""

WEB_APP_TEMPLATES = {
    "wordpress-login": {
        "display_name": "WordPress Login",
        "description": "Protect wp-login.php and xmlrpc.php from brute force",
        "category": "Web Applications",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "5",
            "findtime": "5m",
            "bantime": "1h",
        },
        "filter_content": """[Definition]
# WordPress login brute force protection
failregex = ^<HOST> .* "POST /wp-login\\.php
            ^<HOST> .* "POST /xmlrpc\\.php
ignoreregex =
""",
        "requirements": ["nginx"],
    },
    
    "wordpress-xmlrpc": {
        "display_name": "WordPress XML-RPC",
        "description": "Block XML-RPC abuse (pingback attacks)",
        "category": "Web Applications",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "3",
            "findtime": "1m",
            "bantime": "24h",
        },
        "filter_content": """[Definition]
# WordPress XML-RPC abuse protection
failregex = ^<HOST> .* "POST /xmlrpc\\.php.*" (200|403)
ignoreregex =
""",
        "requirements": ["nginx"],
    },
    
    "phpmyadmin": {
        "display_name": "phpMyAdmin",
        "description": "Protect phpMyAdmin login from brute force",
        "category": "Web Applications",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "5",
            "findtime": "5m",
            "bantime": "1h",
        },
        "filter_content": """[Definition]
# phpMyAdmin brute force protection
failregex = ^<HOST> .* "POST .*/phpmyadmin/index\\.php.*" 200
            ^<HOST> .* "POST .*/pma/index\\.php.*" 200
            ^<HOST> .* "POST .*/phpMyAdmin/index\\.php.*" 200
ignoreregex =
""",
        "requirements": ["nginx"],
    },
    
    "drupal-login": {
        "display_name": "Drupal Login",
        "description": "Protect Drupal user login from brute force",
        "category": "Web Applications",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "5",
            "findtime": "5m",
            "bantime": "1h",
        },
        "filter_content": """[Definition]
# Drupal login brute force protection
failregex = ^<HOST> .* "POST /user/login.*" 200
            ^<HOST> .* "POST /user\\?.*" 200
ignoreregex =
""",
        "requirements": ["nginx"],
    },
    
    "joomla-login": {
        "display_name": "Joomla Login",
        "description": "Protect Joomla administrator login",
        "category": "Web Applications",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "5",
            "findtime": "5m",
            "bantime": "1h",
        },
        "filter_content": """[Definition]
# Joomla login brute force protection
failregex = ^<HOST> .* "POST /administrator/index\\.php.*" 200
            ^<HOST> .* "POST /administrator/.*" 303
ignoreregex =
""",
        "requirements": ["nginx"],
    },
    
    "laravel-login": {
        "display_name": "Laravel Login",
        "description": "Protect Laravel application login",
        "category": "Web Applications",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "5",
            "findtime": "5m",
            "bantime": "1h",
        },
        "filter_content": """[Definition]
# Laravel login brute force protection
failregex = ^<HOST> .* "POST /login.*" (200|302|422)
            ^<HOST> .* "POST /auth/login.*" (200|302|422)
ignoreregex =
""",
        "requirements": ["nginx"],
    },
}
