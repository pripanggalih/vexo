"""SSL security audit."""

import json
import time
from urllib.request import urlopen, Request
from urllib.error import URLError

from ui.components import (
    console,
    clear_screen,
    show_header,
    show_panel,
    show_table,
    show_success,
    show_warning,
    show_info,
    press_enter_to_continue,
)
from ui.menu import run_menu_loop, text_input, select_from_list, confirm_action
from utils.shell import run_command
from utils.error_handler import handle_error
from modules.ssl.common import (
    get_certbot_status_text,
    list_all_certificates,
    parse_certificate,
    format_status,
)


# Security headers to check
SECURITY_HEADERS = {
    "strict-transport-security": {
        "name": "HSTS",
        "recommended": "max-age=31536000; includeSubDomains",
        "description": "HTTP Strict Transport Security",
        "priority": "high"
    },
    "x-frame-options": {
        "name": "X-Frame-Options",
        "recommended": "DENY or SAMEORIGIN",
        "description": "Clickjacking protection",
        "priority": "high"
    },
    "x-content-type-options": {
        "name": "X-Content-Type-Options",
        "recommended": "nosniff",
        "description": "MIME type sniffing prevention",
        "priority": "high"
    },
    "x-xss-protection": {
        "name": "X-XSS-Protection",
        "recommended": "1; mode=block",
        "description": "XSS filter (legacy)",
        "priority": "medium"
    },
    "content-security-policy": {
        "name": "CSP",
        "recommended": "default-src 'self'",
        "description": "Content Security Policy",
        "priority": "high"
    },
    "referrer-policy": {
        "name": "Referrer-Policy",
        "recommended": "strict-origin-when-cross-origin",
        "description": "Referrer information control",
        "priority": "medium"
    },
    "permissions-policy": {
        "name": "Permissions-Policy",
        "recommended": "geolocation=(), microphone=(), camera=()",
        "description": "Browser features control",
        "priority": "medium"
    }
}


def show_security_menu():
    """Display security audit submenu."""
    def get_status():
        return f"Certbot: {get_certbot_status_text()}"
    
    options = [
        ("quick", "1. Quick Check"),
        ("full", "2. Full SSL Audit"),
        ("headers", "3. Security Headers"),
        ("recommend", "4. Get Recommendations"),
        ("back", "← Back"),
    ]
    
    handlers = {
        "quick": quick_check,
        "full": full_ssl_audit,
        "headers": security_headers_audit,
        "recommend": get_recommendations,
    }
    
    run_menu_loop("Security Audit", options, handlers, get_status)


def _get_domain():
    """Get domain from user or certificate list."""
    certificates = list_all_certificates()
    
    if certificates:
        options = [c['name'] for c in certificates]
        options.append("Enter manually")
        
        choice = select_from_list(
            title="Domain",
            message="Select domain to audit:",
            options=options
        )
        
        if choice == "Enter manually":
            return text_input(title="Domain", message="Enter domain name:")
        return choice
    else:
        return text_input(title="Domain", message="Enter domain name:")


def quick_check():
    """Perform quick SSL check."""
    clear_screen()
    show_header()
    show_panel("Quick SSL Check", title="Security Audit", style="cyan")
    
    domain = _get_domain()
    if not domain:
        press_enter_to_continue()
        return
    
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
    
    console.print(f"\n[bold]Checking: {domain}[/bold]\n")
    
    results = []
    
    show_info("Checking certificate...")
    cert_result = _check_certificate(domain)
    results.append(cert_result)
    
    show_info("Checking certificate chain...")
    chain_result = _check_chain(domain)
    results.append(chain_result)
    
    show_info("Testing HTTPS connection...")
    https_result = _check_https(domain)
    results.append(https_result)
    
    show_info("Checking HTTP redirect...")
    redirect_result = _check_http_redirect(domain)
    results.append(redirect_result)
    
    console.print()
    console.print("[bold]Results:[/bold]")
    console.print()
    
    all_passed = True
    for check, status, details in results:
        if status == "pass":
            console.print(f"  [green]✓[/green] {check}: {details}")
        elif status == "warn":
            console.print(f"  [yellow]![/yellow] {check}: {details}")
        else:
            console.print(f"  [red]✗[/red] {check}: {details}")
            all_passed = False
    
    console.print()
    if all_passed:
        console.print("[green bold]All checks passed![/green bold]")
    else:
        console.print("[yellow]Some checks need attention.[/yellow]")
    
    press_enter_to_continue()


def _check_certificate(domain):
    """Check certificate validity."""
    result = run_command(
        f"echo | openssl s_client -servername {domain} -connect {domain}:443 2>/dev/null | "
        f"openssl x509 -noout -dates 2>/dev/null",
        check=False,
        silent=True
    )
    
    if result.returncode != 0:
        return ("Certificate", "fail", "Could not retrieve certificate")
    
    for line in result.stdout.split('\n'):
        if 'notAfter' in line:
            from datetime import datetime
            date_str = line.split('=')[1].strip()
            try:
                expiry = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
                days_left = (expiry - datetime.now()).days
                
                if days_left < 0:
                    return ("Certificate", "fail", f"Expired {abs(days_left)} days ago")
                elif days_left < 14:
                    return ("Certificate", "warn", f"Expires in {days_left} days")
                else:
                    return ("Certificate", "pass", f"Valid, {days_left} days remaining")
            except ValueError:
                return ("Certificate", "warn", "Could not parse expiry date")
    
    return ("Certificate", "pass", "Valid")


def _check_chain(domain):
    """Check certificate chain completeness."""
    result = run_command(
        f"echo | openssl s_client -servername {domain} -connect {domain}:443 "
        f"-showcerts 2>/dev/null | grep -c 'BEGIN CERTIFICATE'",
        check=False,
        silent=True
    )
    
    if result.returncode != 0:
        return ("Chain", "fail", "Could not retrieve chain")
    
    try:
        cert_count = int(result.stdout.strip())
        if cert_count >= 2:
            return ("Chain", "pass", f"Complete ({cert_count} certificates)")
        else:
            return ("Chain", "warn", "May be incomplete (1 certificate)")
    except ValueError:
        return ("Chain", "warn", "Could not verify chain")


def _check_https(domain):
    """Check HTTPS connection."""
    result = run_command(
        f"curl -sI -o /dev/null -w '%{{http_code}}' https://{domain} --connect-timeout 10",
        check=False,
        silent=True
    )
    
    if result.returncode == 0:
        code = result.stdout.strip()
        if code.startswith('2') or code.startswith('3'):
            return ("HTTPS", "pass", f"Working (HTTP {code})")
        else:
            return ("HTTPS", "warn", f"HTTP {code}")
    else:
        return ("HTTPS", "fail", "Connection failed")


def _check_http_redirect(domain):
    """Check if HTTP redirects to HTTPS."""
    result = run_command(
        f"curl -sI -o /dev/null -w '%{{redirect_url}}' http://{domain} --connect-timeout 10",
        check=False,
        silent=True
    )
    
    if result.returncode == 0:
        redirect = result.stdout.strip()
        if redirect.startswith('https://'):
            return ("HTTP Redirect", "pass", "Redirects to HTTPS")
        elif redirect:
            return ("HTTP Redirect", "warn", f"Redirects to {redirect}")
        else:
            return ("HTTP Redirect", "warn", "No redirect configured")
    else:
        return ("HTTP Redirect", "warn", "Could not check")


def full_ssl_audit():
    """Perform full SSL audit using SSL Labs API."""
    clear_screen()
    show_header()
    show_panel("Full SSL Audit (SSL Labs)", title="Security Audit", style="cyan")
    
    domain = _get_domain()
    if not domain:
        press_enter_to_continue()
        return
    
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
    
    console.print(f"\n[bold]Analyzing: {domain}[/bold]")
    console.print("[dim]This may take 1-3 minutes...[/dim]\n")
    
    api_url = f"https://api.ssllabs.com/api/v3/analyze?host={domain}&startNew=on&all=done"
    
    try:
        show_info("Starting SSL Labs analysis...")
        
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                req = Request(api_url, headers={'User-Agent': 'vexo/1.0'})
                response = urlopen(req, timeout=30)
                data = json.loads(response.read().decode())
                
                status = data.get('status', '')
                
                if status == 'READY':
                    _display_ssl_labs_results(data)
                    break
                elif status == 'ERROR':
                    handle_error("E6002", f"SSL Labs error: {data.get('statusMessage', 'Unknown error')}")
                    break
                else:
                    console.print(f"  Status: {status}... (attempt {attempt + 1}/{max_attempts})")
                    time.sleep(10)
                    api_url = f"https://api.ssllabs.com/api/v3/analyze?host={domain}&all=done"
            
            except URLError:
                console.print(f"  [yellow]Network issue, retrying...[/yellow]")
                time.sleep(5)
        else:
            show_warning("Analysis timed out. Try again later.")
    
    except Exception as e:
        handle_error("E6002", f"Failed to connect to SSL Labs: {e}")
    
    press_enter_to_continue()


def _display_ssl_labs_results(data):
    """Display SSL Labs analysis results."""
    console.print()
    
    endpoints = data.get('endpoints', [])
    if not endpoints:
        show_warning("No endpoints found.")
        return
    
    endpoint = endpoints[0]
    grade = endpoint.get('grade', 'N/A')
    
    grade_colors = {
        'A+': 'green bold',
        'A': 'green',
        'A-': 'green',
        'B': 'yellow',
        'C': 'yellow',
        'D': 'red',
        'E': 'red',
        'F': 'red bold',
        'T': 'red',
    }
    
    color = grade_colors.get(grade, 'white')
    
    console.print(f"[bold]SSL Labs Grade:[/bold] [{color}]{grade}[/{color}]")
    console.print()
    
    details = endpoint.get('details', {})
    
    if details:
        protocols = details.get('protocols', [])
        console.print("[bold]Protocol Support:[/bold]")
        for proto in protocols:
            name = proto.get('name', '')
            version = proto.get('version', '')
            if 'TLS' in name and version in ('1.2', '1.3'):
                console.print(f"  [green]✓[/green] {name} {version}")
            elif 'SSL' in name or version in ('1.0', '1.1'):
                console.print(f"  [red]✗[/red] {name} {version} (insecure)")
            else:
                console.print(f"  [dim]-[/dim] {name} {version}")
        
        console.print()
        
        console.print("[bold]Vulnerability Checks:[/bold]")
        
        vuln_checks = [
            ('heartbleed', 'Heartbleed'),
            ('poodle', 'POODLE'),
            ('freak', 'FREAK'),
            ('logjam', 'Logjam'),
            ('drownVulnerable', 'DROWN'),
        ]
        
        for key, name in vuln_checks:
            value = details.get(key, False)
            if value:
                console.print(f"  [red]✗[/red] Vulnerable to {name}")
            else:
                console.print(f"  [green]✓[/green] Not vulnerable to {name}")
        
        if details.get('forwardSecrecy', 0) >= 2:
            console.print(f"  [green]✓[/green] Forward Secrecy supported")
        else:
            console.print(f"  [yellow]![/yellow] Forward Secrecy limited")


def security_headers_audit():
    """Audit security headers."""
    clear_screen()
    show_header()
    show_panel("Security Headers Audit", title="Security Audit", style="cyan")
    
    domain = _get_domain()
    if not domain:
        press_enter_to_continue()
        return
    
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
    
    console.print(f"\n[bold]Checking headers for: {domain}[/bold]\n")
    
    result = run_command(
        f"curl -sI https://{domain} --connect-timeout 10",
        check=False,
        silent=True
    )
    
    if result.returncode != 0:
        handle_error("E6002", "Could not fetch headers.")
        press_enter_to_continue()
        return
    
    headers = {}
    for line in result.stdout.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip().lower()] = value.strip()
    
    console.print("[bold]Security Headers:[/bold]")
    console.print()
    
    columns = [
        {"name": "Header", "style": "cyan"},
        {"name": "Status", "justify": "center"},
        {"name": "Value"},
    ]
    
    rows = []
    score = 0
    total = len(SECURITY_HEADERS)
    
    for header_key, header_info in SECURITY_HEADERS.items():
        value = headers.get(header_key, None)
        
        if value:
            status = "[green]✓[/green]"
            score += 1
            display_value = value[:40] + "..." if len(value) > 40 else value
        else:
            status = "[red]✗[/red]"
            display_value = "[dim]Missing[/dim]"
        
        rows.append([header_info['name'], status, display_value])
    
    show_table("", columns, rows)
    
    console.print()
    console.print(f"[bold]Score:[/bold] {score}/{total} headers configured")
    
    if score < total:
        console.print()
        if confirm_action("View recommendations?"):
            _show_header_recommendations(headers)
    
    press_enter_to_continue()


def _show_header_recommendations(current_headers):
    """Show recommendations for missing headers."""
    console.print()
    console.print("[bold]Recommendations:[/bold]")
    console.print()
    
    for header_key, header_info in SECURITY_HEADERS.items():
        if header_key not in current_headers:
            priority_color = "red" if header_info['priority'] == 'high' else "yellow"
            console.print(f"[{priority_color}]{header_info['priority'].upper()}:[/{priority_color}] Add {header_info['name']}")
            console.print(f"  [dim]{header_info['description']}[/dim]")
            console.print(f"  Recommended: {header_info['recommended']}")
            console.print()


def get_recommendations():
    """Get security recommendations for a domain."""
    clear_screen()
    show_header()
    show_panel("Security Recommendations", title="Security Audit", style="cyan")
    
    domain = _get_domain()
    if not domain:
        press_enter_to_continue()
        return
    
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
    
    console.print(f"\n[bold]Generating recommendations for: {domain}[/bold]\n")
    
    recommendations = []
    
    cert_result = _check_certificate(domain)
    if cert_result[1] != "pass":
        recommendations.append(("HIGH", "Certificate", cert_result[2]))
    
    https_result = _check_https(domain)
    if https_result[1] != "pass":
        recommendations.append(("HIGH", "HTTPS", https_result[2]))
    
    redirect_result = _check_http_redirect(domain)
    if redirect_result[1] != "pass":
        recommendations.append(("MEDIUM", "HTTP Redirect", "Configure redirect from HTTP to HTTPS"))
    
    result = run_command(f"curl -sI https://{domain} --connect-timeout 10", check=False, silent=True)
    if result.returncode == 0:
        headers = {}
        for line in result.stdout.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()
        
        for header_key, header_info in SECURITY_HEADERS.items():
            if header_key not in headers:
                priority = "HIGH" if header_info['priority'] == 'high' else "MEDIUM"
                recommendations.append((priority, header_info['name'], f"Add header: {header_info['recommended']}"))
    
    if not recommendations:
        console.print("[green]No major issues found![/green]")
    else:
        console.print("[bold]Recommendations:[/bold]")
        console.print()
        
        recommendations.sort(key=lambda x: 0 if x[0] == "HIGH" else 1)
        
        for priority, area, recommendation in recommendations:
            color = "red" if priority == "HIGH" else "yellow"
            console.print(f"[{color}]{priority}[/{color}] [{area}]")
            console.print(f"  {recommendation}")
            console.print()
    
    if recommendations and confirm_action("Generate Nginx security headers snippet?"):
        _generate_nginx_snippet()
    
    press_enter_to_continue()


def _generate_nginx_snippet():
    """Generate Nginx config snippet for security headers."""
    console.print()
    console.print("[bold]Nginx Security Headers Snippet:[/bold]")
    console.print()
    console.print("[dim]Add to your server block:[/dim]")
    console.print()
    
    snippet = """# Security Headers
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;"""
    
    console.print(f"[cyan]{snippet}[/cyan]")
    console.print()
