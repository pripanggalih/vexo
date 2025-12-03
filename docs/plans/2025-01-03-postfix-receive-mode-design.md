# Postfix Receive Mode Design

> Catch-all email receiver dengan pipe ke Laravel artisan command

## Overview

Mengubah Postfix dari send-only mode menjadi receive mode untuk:
- Multi-domain catch-all email
- Pipe ke Laravel artisan command per domain
- Configurable project path dan command per domain

## Architecture

```
Internet → Postfix (port 25) → virtual_alias_maps → pipe transport → Laravel artisan
```

**Config file:** `/etc/vexo/email-domains.json`
```json
{
  "example.com": {
    "path": "/var/www/myapp",
    "command": "email:incoming",
    "active": true
  },
  "another.com": {
    "path": "/var/www/otherapp",
    "command": "mail:process",
    "active": true
  }
}
```

**Postfix files yang dimanage:**
- `/etc/postfix/virtual` - catch-all mapping
- `/etc/postfix/master.cf` - pipe transport
- `/etc/postfix/main.cf` - enable virtual alias

## Postfix Configuration

**main.cf additions:**
```
virtual_alias_domains = example.com, another.com
virtual_alias_maps = hash:/etc/postfix/virtual
inet_interfaces = all
```

**virtual file:**
```
@example.com    laravel-example.com
@another.com    laravel-another.com
```

**master.cf (pipe transport):**
```
laravel-example.com unix - n n - - pipe
  flags=F user=www-data argv=/usr/local/bin/vexo-pipe example.com

laravel-another.com unix - n n - - pipe
  flags=F user=www-data argv=/usr/local/bin/vexo-pipe another.com
```

**vexo-pipe script** (`/usr/local/bin/vexo-pipe`):
```bash
#!/bin/bash
DOMAIN=$1
CONFIG=$(cat /etc/vexo/email-domains.json)
PATH=$(echo $CONFIG | jq -r ".\"$DOMAIN\".path")
CMD=$(echo $CONFIG | jq -r ".\"$DOMAIN\".command")

cd $PATH && /usr/bin/php artisan $CMD < /dev/stdin
```

## Menu Structure

```
Email Server (Postfix)
├── 1. Install Postfix
├── 2. Configure Mode
│   ├── Send-Only Mode
│   └── Receive Mode (catch-all)
├── 3. Manage Domains
│   ├── Add Domain
│   ├── Remove Domain
│   ├── List Domains
│   └── Edit Domain Config
├── 4. Test Email
│   ├── Send Test
│   └── Test Incoming
├── 5. View Mail Log
├── 6. Queue Management
│   ├── View Queue
│   ├── Flush Queue
│   └── Delete Queued
├── 7. Show Status
└── ← Back
```

## Add Domain Flow

1. Input domain name
2. Input Laravel project path
3. Input artisan command (default: `email:incoming`)
4. Verify path exists & artisan accessible
5. Update config + regenerate Postfix files
6. Reload Postfix

## Error Handling

| Error | Handling |
|-------|----------|
| Laravel path tidak ada | Reject saat add domain |
| Artisan command gagal | Email tetap diterima, log error |
| Postfix down | Email queue di sender |
| Permission denied | vexo-pipe run as www-data |

**Validations saat Add Domain:**
- Domain format valid
- Path exists & readable
- `php artisan` executable di path tersebut

## Debug Mode

- Log ke `/var/log/vexo-email.log`
- Include: timestamp, domain, sender, subject, artisan exit code
- Toggle on/off dari menu

## Dependencies

- `jq` - parse JSON di vexo-pipe script
- Postfix (existing)

## Task Breakdown

1. Refactor email.py menu structure
2. Implement domain CRUD (add/remove/list/edit)
3. Implement config file management
4. Implement Postfix file generators
5. Create vexo-pipe script installer
6. Implement test incoming
7. Implement view log & queue management
8. Update firewall module port 25 option
