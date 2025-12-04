# Security Hardening Design for vexo

## Overview

Add security hardening features to vexo: UFW Firewall, Let's Encrypt SSL, and Fail2ban brute force protection.

## Decisions Made

1. **Scope:** Standard security (UFW + Let's Encrypt + Fail2ban)
2. **Structure:** Separate modules (`firewall.py`, `ssl.py`, `fail2ban.py`)
3. **UFW Defaults:** SSH (22), HTTP (80), HTTPS (443) + configurable email ports
4. **SSL:** Manual per-domain with auto-renewal (Certbot default behavior)
5. **Fail2ban:** Smart auto-detect jails based on installed services

---

## Module 1: Firewall (firewall.py)

### Menu Structure

```
Firewall (UFW)
├── 1. Show Status           # ufw status verbose
├── 2. Enable Firewall       # Setup default rules + enable
├── 3. Disable Firewall      # ufw disable (dengan warning)
├── 4. Add Custom Port       # Input port + protocol (tcp/udp)
├── 5. Add Email Ports       # Buka 25, 587, 465 sekaligus
├── 6. Remove Port           # Pilih dari list open ports
├── 7. List Rules            # ufw status numbered
└── ← Back
```

### Default Rules (Enable Firewall)

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
```

### Functions

| Function | Description |
|----------|-------------|
| `show_menu()` | Display firewall submenu |
| `install_ufw()` | Install UFW if not present |
| `enable_firewall()` | Setup default rules + enable |
| `disable_firewall()` | Disable UFW with warning |
| `add_port(port, protocol)` | Add custom port rule |
| `add_email_ports()` | Batch add 25/587/465 |
| `remove_port(port)` | Delete port rule |
| `show_status()` | Display current status |
| `list_rules()` | Show numbered rules |

---

## Module 2: SSL Certificates (ssl.py)

### Menu Structure

```
SSL Certificates (Let's Encrypt)
├── 1. Install Certbot        # apt install certbot python3-certbot-nginx
├── 2. Enable SSL for Domain  # Pilih domain → certbot --nginx
├── 3. List Certificates      # certbot certificates
├── 4. Renew All Certificates # certbot renew (manual trigger)
├── 5. Revoke Certificate     # Pilih cert → certbot revoke
├── 6. Auto-Renewal Status    # systemctl status certbot.timer
└── ← Back
```

### Flow: Enable SSL for Domain

1. Scan `/etc/nginx/sites-available/` for domains
2. Display domains without SSL
3. User selects domain
4. Run: `certbot --nginx -d {domain} --non-interactive --agree-tos -m {email}`
5. Nginx auto-updated with SSL config
6. Auto-renewal already configured via `certbot.timer`

### Functions

| Function | Description |
|----------|-------------|
| `show_menu()` | Display SSL submenu |
| `install_certbot()` | Install certbot + nginx plugin |
| `enable_ssl(domain)` | Generate cert + configure Nginx |
| `enable_ssl_interactive()` | Interactive domain selection |
| `list_certificates()` | Show all certs with expiry |
| `renew_certificates()` | Force renewal |
| `revoke_certificate(domain)` | Revoke + delete cert |
| `show_renewal_status()` | Check systemd timer status |
| `_get_domains_without_ssl()` | Helper to scan domains |

---

## Module 3: Fail2ban (fail2ban.py)

### Menu Structure

```
Fail2ban (Brute Force Protection)
├── 1. Install Fail2ban       # apt install + auto-enable jails
├── 2. Show Status            # fail2ban-client status
├── 3. List Banned IPs        # fail2ban-client status {jail}
├── 4. Unban IP               # Input IP → fail2ban-client unban
├── 5. Ban IP Manually        # Input IP → fail2ban-client ban
├── 6. Configure Ban Time     # Set bantime, findtime, maxretry
├── 7. View Jail Status       # Detail per-jail (sshd, nginx, etc)
└── ← Back
```

### Smart Auto-Detect Jails

```python
# Auto-enable jails based on installed services
if is_installed("openssh-server"):
    enable_jail("sshd")

if is_installed("nginx"):
    enable_jail("nginx-http-auth")
    enable_jail("nginx-botsearch")

if is_installed("postfix"):
    enable_jail("postfix")
    enable_jail("postfix-sasl")
```

### Default Settings (Configurable)

| Setting | Default | Description |
|---------|---------|-------------|
| `bantime` | 1h | Duration of ban |
| `findtime` | 10m | Window to count failures |
| `maxretry` | 5 | Max attempts before ban |

### Functions

| Function | Description |
|----------|-------------|
| `show_menu()` | Display fail2ban submenu |
| `install_fail2ban()` | Install + auto-detect + enable jails |
| `show_status()` | Overall fail2ban status |
| `list_banned_ips(jail)` | Show banned IPs per jail |
| `unban_ip(ip)` | Remove IP from ban list |
| `ban_ip(ip, jail)` | Manual ban |
| `configure_settings()` | Update bantime/findtime/maxretry |
| `view_jail_status(jail)` | Detailed jail status |
| `_detect_services()` | Helper for auto-detect |
| `_enable_jail(jail)` | Enable specific jail |

---

## Task Breakdown

### Task 12.0: Firewall Module

- 12.1: Create `modules/firewall.py` with `show_menu()`
- 12.2: Implement `install_ufw()`
- 12.3: Implement `enable_firewall()` with default rules
- 12.4: Implement `disable_firewall()`
- 12.5: Implement `add_port()` and `add_email_ports()`
- 12.6: Implement `remove_port()` and `list_rules()`
- 12.7: Implement `show_status()`

### Task 13.0: SSL Module

- 13.1: Create `modules/ssl.py` with `show_menu()`
- 13.2: Implement `install_certbot()`
- 13.3: Implement `enable_ssl()` and `enable_ssl_interactive()`
- 13.4: Implement `list_certificates()`
- 13.5: Implement `renew_certificates()` and `revoke_certificate()`
- 13.6: Implement `show_renewal_status()`

### Task 14.0: Fail2ban Module

- 14.1: Create `modules/fail2ban.py` with `show_menu()`
- 14.2: Implement `install_fail2ban()` with auto-detect
- 14.3: Implement `show_status()` and `view_jail_status()`
- 14.4: Implement `list_banned_ips()`
- 14.5: Implement `unban_ip()` and `ban_ip()`
- 14.6: Implement `configure_settings()`
- 14.7: Add helper functions `_detect_services()`, `_enable_jail()`

### Task 15.0: Integration

- 15.1: Update `modules/__init__.py` with new imports
- 15.2: Update `main.py` with 3 new menu entries
- 15.3: Update `tasks/tasks-vexo.md` with new tasks

---

## Updated Main Menu

```
vexo v1.0.0
├── 1. System Setup & Update
├── 2. Domain & Nginx
├── 3. PHP Runtime
├── 4. Node.js Runtime
├── 5. Database
├── 6. Email Server
├── 7. System Monitoring
├── 8. Firewall (UFW)        ← NEW
├── 9. SSL Certificates      ← NEW
├── 10. Fail2ban             ← NEW
└── ✕ Exit
```

---

## Summary

| Item | Count |
|------|-------|
| New Modules | 3 |
| New Menu Items | 3 |
| New Tasks | 4 |
| Total Sub-tasks | ~25 |
