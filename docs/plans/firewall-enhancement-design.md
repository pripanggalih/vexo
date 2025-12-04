# Firewall Enhancement Design

## Overview

Enhance firewall.py module untuk VPS management dengan fitur yang lebih robust dan user-friendly.

## Current State

Fitur existing:
- Install/Enable/Disable UFW
- Add custom port (tcp/udp/both)
- Add email ports preset (25, 587, 465)
- Remove port by rule number
- List rules & Show status

## Enhancement Goals

1. **IP Management** - Allow/deny IPs, IP ranges, groups, whitelist
2. **Rate Limiting** - Configurable per-port brute-force protection
3. **Port Presets** - Quick add untuk services populer
4. **Logging & Monitoring** - Dashboard, stats, live monitor
5. **Backup/Restore** - Save/restore configs, compare, auto-backup
6. **Application Profiles** - Manage UFW app profiles

---

## Design

### Menu Structure

```
Firewall (UFW)
├── 1. Status Dashboard
├── 2. Quick Setup
├── 3. Port Management
│   ├── Add Port (Custom)
│   ├── Port Presets (Web/DB/Mail/Dev/Other)
│   └── Remove Port
├── 4. IP Management
│   ├── Allow IP
│   ├── Deny/Block IP
│   ├── IP Whitelist
│   ├── IP Groups
│   └── List IP Rules
├── 5. Rate Limiting
│   ├── Enable Rate Limit
│   ├── Configure Limits
│   └── List Rate Limits
├── 6. Application Profiles
│   ├── List Profiles
│   ├── Apply Profile
│   ├── Create Custom Profile
│   └── Edit/Delete Profile
├── 7. Logs & Monitoring
│   ├── View Firewall Logs
│   ├── Blocked Attempts Stats
│   ├── Log Settings
│   └── Live Monitor
├── 8. Backup & Restore
│   ├── Create Backup
│   ├── Restore Backup
│   ├── Compare Configs
│   ├── Auto-Backup Settings
│   └── Manage Backups
└── ← Back
```

### IP Management

**Three Flexibility Levels:**

1. **Simple Mode** - Allow/deny single IP
2. **Advanced Mode** - IP ranges, CIDR, per-port rules
3. **Full Mode** - IP groups/aliases for easier management

```
IP Groups Example:
- "office": 192.168.1.0/24, 10.10.0.5 → Allowed: 22, 3306
- "blocked": 45.33.32.0/24 → Denied: all ports
```

Storage: `/etc/vexo/firewall/ip-groups.json`

### Port Presets

Categories:
- **Web Stack**: HTTP(80), HTTPS(443), HTTP/3(443/udp)
- **Database**: MySQL(3306), PostgreSQL(5432), MongoDB(27017), Redis(6379), Memcached(11211)
- **Mail Server**: SMTP(25,587,465), IMAP(143,993), POP3(110,995)
- **Development**: FTP(21), Git(9418), Node(3000), Flask(5000), Alt HTTP(8080)
- **Other Services**: DNS(53), NTP(123), WireGuard(51820), OpenVPN(1194)

Features:
- Checkbox multi-select
- Indicator if port already open
- Option to restrict to specific IPs

### Rate Limiting

**Configuration Options:**
- Port selection (any port)
- Protocol (TCP/UDP)
- Presets: SSH (6/30sec), Web Standard (100/min), Web Strict (30/min)
- Custom threshold

**Implementation:**
- UFW `limit` rule for basic
- iptables `hashlimit` for advanced custom thresholds
- Config: `/etc/vexo/firewall/rate-limits.json`

### Logging & Monitoring

**Status Dashboard:**
```
┌─ Firewall Stats (Last 24h) ────────────────┐
│ Blocked: 1,247  │  Allowed: 45,892         │
│ Top Blocked IP: 45.33.32.156 (342x)        │
│ Most Targeted Port: 22 (890 attempts)      │
│ [!] Alert: Consider banning suspicious IPs │
└────────────────────────────────────────────┘
```

**Live Monitor:**
- Real-time log streaming with filtering
- Filter: Blocked only, Allowed only, Rate Limited, All

**Log Settings:**
- Levels: off, low, medium, high, full
- Parse `/var/log/ufw.log`

### Backup & Restore

**Features:**
- Named backups with descriptions
- Compare two configurations (diff view)
- Auto-backup: daily schedule, before changes
- Keep N latest backups

**Backup Format (JSON):**
```json
{
  "version": "1.0",
  "created": "2024-01-15T10:30:00Z",
  "server": "vps-prod-01",
  "ufw_rules": [...],
  "ip_groups": {...},
  "rate_limits": [...],
  "app_profiles": [...]
}
```

Storage: `/etc/vexo/firewall/backups/`

### Application Profiles

**Features:**
- List system + custom profiles
- Apply/remove profiles
- Create custom profiles
- Edit/delete custom profiles

**Custom Profile Storage:**
```ini
# /etc/ufw/applications.d/vexo-custom
[my-nodejs-app]
title=My Node.js Application
description=Production Node.js server
ports=3000,3001,8080/tcp
```

---

## File Structure

### Module Refactor

```
modules/firewall/
├── __init__.py          # Package init, show_menu()
├── common.py            # Shared utilities, UFW helpers
├── status.py            # Status dashboard, stats
├── ports.py             # Port management, presets
├── ip_management.py     # IP rules, groups, whitelist
├── rate_limiting.py     # Rate limit configuration
├── profiles.py          # Application profiles
├── logs.py              # Log viewing, live monitor
├── backup.py            # Backup/restore, compare
└── presets.py           # Port preset definitions
```

### Config Files

```
/etc/vexo/firewall/
├── ip-groups.json
├── rate-limits.json
├── settings.json
└── backups/
    └── *.json

/etc/ufw/applications.d/
└── vexo-custom
```

---

## Implementation Phases

| Phase | Scope | New Files |
|-------|-------|-----------|
| 1 | Refactor to package + Status Dashboard | common.py, status.py, __init__.py |
| 2 | Port Management + Presets | ports.py, presets.py |
| 3 | IP Management | ip_management.py |
| 4 | Rate Limiting | rate_limiting.py |
| 5 | Application Profiles | profiles.py |
| 6 | Logging & Monitoring | logs.py |
| 7 | Backup & Restore | backup.py |
