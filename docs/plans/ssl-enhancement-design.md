# SSL Certificate Enhancement Design

## Overview

Enhance ssl.py module untuk VPS management dengan fitur yang lebih robust dan user-friendly.

## Current State

Fitur existing:
- Install Certbot
- Enable SSL untuk domain (Let's Encrypt)
- List Certificates
- Renew All/Single Certificate
- Revoke Certificate
- View Certificate Info
- Auto-Renewal Status

## Enhancement Goals

1. **Certificate Monitoring** - Dashboard, alerts, history
2. **Multi-Domain Support** - SAN + Wildcard certificates
3. **Custom Certificates** - Import PEM/PFX with validation
4. **DNS Challenge** - Multiple providers + manual mode
5. **Security Testing** - SSL Labs + security headers audit
6. **Backup/Restore** - Export, scheduled backups, migration
7. **Multiple CA Support** - Let's Encrypt, ZeroSSL, Buypass, custom ACME

---

## Design

### Menu Structure

```
SSL Certificates
├── 1. Dashboard
├── 2. Issue Certificate
│   ├── Single Domain
│   ├── Multiple Domains (SAN)
│   ├── Wildcard Certificate
│   └── Select CA
├── 3. Import Certificate
│   ├── Upload PEM
│   ├── Upload PFX/PKCS12
│   ├── Paste Certificate
│   └── Validate & Install
├── 4. Manage Certificates
│   ├── View Details
│   ├── Renew Certificate
│   ├── Revoke Certificate
│   └── Delete Certificate
├── 5. DNS Providers
│   ├── Configure Cloudflare
│   ├── Configure DigitalOcean
│   ├── Configure Route53
│   ├── Configure Other
│   └── Test DNS API
├── 6. Security Audit
│   ├── Quick Check
│   ├── Full SSL Audit
│   ├── Security Headers
│   └── Get Recommendations
├── 7. Backup & Restore
│   ├── Export Certificate
│   ├── Export All
│   ├── Import/Restore
│   ├── Scheduled Backups
│   └── Manage Backups
├── 8. Settings
│   ├── Default CA
│   ├── Alert Settings
│   ├── Auto-Renewal Config
│   └── Monitoring Schedule
└── ← Back
```

### Certificate Dashboard

**Main View:**
- Total certificates with status breakdown (valid/expiring/expired)
- Table: domain, status, days left, CA, type
- Alert section for certificates needing attention
- Next auto-renewal check time

**Alert System:**
- Thresholds: Critical (7 days), Warning (14 days), Notice (30 days)
- Methods: Console, log file, email (optional), webhook (optional)

**History Log:**
- Certificate events: issued, renewed, revoked
- Timestamps and details

### Issue Certificate

**Certificate Types:**
1. Single Domain - example.com
2. Multiple Domains (SAN) - example.com + www + api
3. Wildcard - *.example.com (requires DNS challenge)
4. Wildcard + Root - *.example.com + example.com

**CA Selection:**
- Let's Encrypt (default, free, 90 days)
- ZeroSSL (free, 90 days)
- Buypass (free, 180 days)
- Custom ACME Server

**Pre-flight Checks:**
- DNS A record points to server
- Port 80 accessible
- Nginx configuration valid
- Domain not rate-limited

### Import Certificate

**Supported Formats:**
- PEM files (cert.pem + key.pem)
- PFX/PKCS12 (single file with password)
- DER (binary, auto-convert)
- Paste PEM content

**Validation:**
- Certificate and key match
- Chain completeness
- Expiry check
- Domain extraction

**Post-Import:**
- Save to /etc/vexo/ssl/certs/{domain}/
- Auto-configure Nginx
- Set renewal reminder

### DNS Providers

**Supported Providers:**
- Cloudflare (API Token or Global Key)
- DigitalOcean (API Token)
- AWS Route53 (Access Key + Secret)
- Google Cloud DNS (Service Account)
- Manual mode (copy TXT record)

**Features:**
- Test connection before save
- Encrypted credential storage
- Auto DNS propagation check

### Security Audit

**Quick Check:**
- Certificate validity
- Expiry status
- Chain completeness
- HTTPS response test

**Full SSL Audit (via SSL Labs API):**
- Overall grade (A+ to F)
- Protocol support (TLS 1.2/1.3)
- Cipher suites
- Vulnerability checks (Heartbleed, POODLE, etc.)

**Security Headers:**
- HSTS, X-Frame-Options, X-Content-Type-Options
- CSP, Referrer-Policy, Permissions-Policy
- Recommendations with auto-fix option

### Backup & Restore

**Export Options:**
- Single certificate or all
- Formats: tar.gz, PEM bundle, PFX
- Include: certs, keys, chain, Nginx config, Certbot renewal
- Optional password encryption

**Scheduled Backups:**
- Daily/weekly/monthly options
- Retention policy (keep last N)
- Local or remote storage

**Restore:**
- Preview contents before restore
- Validate certificates
- Selective restore
- Auto-reload Nginx

---

## File Structure

### Module Refactor

```
modules/ssl/
├── __init__.py          # Package init, show_menu()
├── common.py            # Shared utilities, cert parsing
├── dashboard.py         # Certificate dashboard, monitoring
├── issue.py             # Issue new certs
├── import_cert.py       # Import custom certificates
├── manage.py            # Renew, revoke, delete
├── dns_providers.py     # DNS challenge providers
├── security.py          # SSL audit, headers check
├── backup.py            # Backup & restore
└── settings.py          # Settings, alerts config
```

### Config Files

```
/etc/vexo/ssl/
├── settings.json
├── certificates.json
├── alerts.json
├── history.log
├── certs/{domain}/
├── dns/
└── backups/
```

---

## Implementation Phases

| Phase | Scope | New Files |
|-------|-------|-----------|
| 1 | Refactor to package + Dashboard | common.py, dashboard.py |
| 2 | Issue Certificate | issue.py |
| 3 | Import Custom Certificates | import_cert.py |
| 4 | Certificate Management | manage.py |
| 5 | DNS Providers | dns_providers.py |
| 6 | Security Audit | security.py |
| 7 | Backup & Restore | backup.py |
| 8 | Settings & Alerts | settings.py |
