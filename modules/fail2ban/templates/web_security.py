"""Web security jail templates."""

WEB_SECURITY_TEMPLATES = {
    "nginx-badbots": {
        "display_name": "Bad Bots & Scanners",
        "description": "Block known bad bots, scanners, and crawlers",
        "category": "Web Security",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "1",
            "findtime": "1d",
            "bantime": "7d",
        },
        "filter_content": """[Definition]
# Bad bots and vulnerability scanners
failregex = ^<HOST> .* "(GET|POST).*(?i)(sqlmap|nikto|nmap|masscan|zgrab).*"
            ^<HOST> .* ".*(?i)(acunetix|nessus|openvas|w3af).*"
            ^<HOST> .* ".*User-Agent:.*(?i)(sqlmap|nikto|masscan).*"
ignoreregex =
""",
        "requirements": ["nginx"],
    },
    
    "nginx-noscript": {
        "display_name": "Script Kiddies",
        "description": "Block requests for common vulnerable paths",
        "category": "Web Security",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "2",
            "findtime": "10m",
            "bantime": "1d",
        },
        "filter_content": """[Definition]
# Script kiddie and probe protection
failregex = ^<HOST> .* "(GET|POST).*/(?i)(wp-config|\\.env|\\.git|\\.svn|\\.htaccess).*"
            ^<HOST> .* "(GET|POST).*(?i)(phpunit|vendor/phpunit|eval-stdin).*"
            ^<HOST> .* "(GET|POST).*(?i)(shell|c99|r57|b374k).*"
ignoreregex =
""",
        "requirements": ["nginx"],
    },
    
    "nginx-sqli": {
        "display_name": "SQL Injection",
        "description": "Block SQL injection attempts",
        "category": "Web Security",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "1",
            "findtime": "1h",
            "bantime": "1d",
        },
        "filter_content": """[Definition]
# SQL injection attempt protection
failregex = ^<HOST> .* "(GET|POST).*(?i)(union.*select|select.*from|insert.*into|drop.*table|delete.*from).*"
            ^<HOST> .* "(GET|POST).*(?i)(\\/\\*.*\\*\\/|;.*--|'.*or.*'|".*or.*).*"
            ^<HOST> .* "(GET|POST).*(?i)(benchmark|sleep|load_file|into.*outfile).*"
ignoreregex =
""",
        "requirements": ["nginx"],
    },
    
    "nginx-traversal": {
        "display_name": "Path Traversal",
        "description": "Block directory traversal attempts",
        "category": "Web Security",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "2",
            "findtime": "10m",
            "bantime": "1d",
        },
        "filter_content": """[Definition]
# Path traversal protection
failregex = ^<HOST> .* "(GET|POST).*(?i)(\\.\\.\\/|\\.\\.\\\\\\\\|%2e%2e%2f|%252e%252e).*"
            ^<HOST> .* "(GET|POST).*(?i)(\\/etc\\/passwd|\\/etc\\/shadow|\\/proc\\/self).*"
            ^<HOST> .* "(GET|POST).*(?i)(boot\\.ini|win\\.ini|system32).*"
ignoreregex =
""",
        "requirements": ["nginx"],
    },
    
    "nginx-http-flood": {
        "display_name": "HTTP Flood (DDoS)",
        "description": "Rate limit aggressive request patterns",
        "category": "Web Security",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "100",
            "findtime": "1m",
            "bantime": "10m",
        },
        "filter_content": """[Definition]
# HTTP flood/DDoS protection
failregex = ^<HOST> -.*"(GET|POST|HEAD).*
ignoreregex = ^<HOST> .* "(GET|POST).*/health.*"
              ^<HOST> .* "(GET|POST).*/api/.*"
""",
        "requirements": ["nginx"],
        "warning": "May cause false positives on high-traffic sites. Adjust maxretry accordingly.",
    },
    
    "nginx-403-flood": {
        "display_name": "403 Flood",
        "description": "Ban IPs generating many 403 errors",
        "category": "Web Security",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "10",
            "findtime": "5m",
            "bantime": "1h",
        },
        "filter_content": """[Definition]
# 403 error flood protection
failregex = ^<HOST> .* "(GET|POST|HEAD).*" 403
ignoreregex =
""",
        "requirements": ["nginx"],
    },
    
    "nginx-404-flood": {
        "display_name": "404 Flood",
        "description": "Ban IPs generating many 404 errors (scanning)",
        "category": "Web Security",
        "jail_config": {
            "enabled": "true",
            "port": "http,https",
            "logpath": "/var/log/nginx/access.log",
            "maxretry": "20",
            "findtime": "5m",
            "bantime": "30m",
        },
        "filter_content": """[Definition]
# 404 error flood protection (directory scanning)
failregex = ^<HOST> .* "(GET|POST|HEAD).*" 404
ignoreregex = ^<HOST> .* "(GET|POST).*/favicon\\.ico.*" 404
              ^<HOST> .* "(GET|POST).*/robots\\.txt.*" 404
""",
        "requirements": ["nginx"],
    },
}
