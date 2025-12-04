# Supervisor & Cron Design

> **Date:** 2025-01-03
> **Status:** Approved

## Overview

Menambahkan dua modul baru untuk mengelola Supervisor (queue workers) dan Cron (scheduled tasks) yang umum digunakan di Laravel projects.

## Architecture

### Module Structure

```
modules/
├── supervisor.py    # Queue worker management
└── cron.py          # Cron & Laravel scheduler
```

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Module structure | Separate modules | Konsisten dengan arsitektur vexo |
| Supervisor scope | Standard | Multi-worker, numprocs, logs |
| Cron scope | General + Laravel | Scheduler + custom cron jobs |
| Worker config | Direct to Supervisor | No abstraction layer needed |
| Worker naming | Custom name | Flexible for multiple workers |

## Supervisor Module

### Menu Structure

```
Supervisor (Queue Workers)
├── 1. Install Supervisor
├── 2. Add Worker
├── 3. Remove Worker
├── 4. List Workers
├── 5. Worker Control (start/stop/restart)
├── 6. View Logs
├── 7. Show Status
└── ← Back
```

### Config Location

`/etc/supervisor/conf.d/{worker-name}.conf`

### Add Worker Flow

1. Input worker name (e.g., `myapp-email`)
2. Input Laravel project path (e.g., `/var/www/myapp`)
3. Input queue connection (default: `database`)
4. Input queue names (default: `default`)
5. Input number of processes (default: `1`)
6. Generate config → `supervisorctl reread` → `supervisorctl update`

### Config Template

```ini
[program:{worker-name}]
process_name=%(program_name)s_%(process_num)02d
command=php {laravel-path}/artisan queue:work {connection} --queue={queues} --sleep=3 --tries=3 --max-time=3600
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
user=www-data
numprocs={num}
redirect_stderr=true
stdout_logfile=/var/log/supervisor/{worker-name}.log
stopwaitsecs=3600
```

### Worker Control Submenu

```
Worker Control
├── 1. Start Worker
├── 2. Stop Worker
├── 3. Restart Worker
├── 4. Restart All Workers
└── ← Back
```

## Cron Module

### Menu Structure

```
Cron Jobs
├── 1. Setup Laravel Scheduler
├── 2. Add Cron Job
├── 3. Remove Cron Job
├── 4. List Cron Jobs
├── 5. Enable/Disable Job
├── 6. Backup Crontab
├── 7. Restore Crontab
├── 8. Show Status
└── ← Back
```

### Laravel Scheduler Entry

```cron
* * * * * cd /var/www/myapp && php artisan schedule:run >> /dev/null 2>&1
```

### Custom Cron Job Flow

1. Input job name/description (untuk komentar)
2. Input cron expression atau pilih preset:
   - Every minute: `* * * * *`
   - Every hour: `0 * * * *`
   - Every day: `0 0 * * *`
   - Every week: `0 0 * * 0`
3. Input command to run
4. Tambah ke crontab dengan komentar `# vexo: {job-name}`

### Crontab Management

- **List:** Parse crontab, tampilkan dalam tabel
- **Enable/Disable:** Comment/uncomment line
- **Remove:** Hapus line dari crontab
- **Backup:** `crontab -l > /etc/vexo/crontab-backup-{date}.txt`
- **Restore:** Select backup file → `crontab {file}`

## Task Breakdown

### Task 17: Supervisor Module (8 sub-tasks)

| Sub-task | Description |
|----------|-------------|
| 17.1 | Create supervisor.py with imports, constants, show_menu() |
| 17.2 | Implement install_supervisor() |
| 17.3 | Implement add_worker_interactive() + config template |
| 17.4 | Implement remove_worker() |
| 17.5 | Implement list_workers() |
| 17.6 | Implement worker_control_menu() (start/stop/restart) |
| 17.7 | Implement view_logs() |
| 17.8 | Implement show_status() + update main.py |

### Task 18: Cron Module (9 sub-tasks)

| Sub-task | Description |
|----------|-------------|
| 18.1 | Create cron.py with imports, constants, show_menu() |
| 18.2 | Implement setup_laravel_scheduler() |
| 18.3 | Implement add_cron_job_interactive() |
| 18.4 | Implement remove_cron_job() |
| 18.5 | Implement list_cron_jobs() |
| 18.6 | Implement enable_disable_job() |
| 18.7 | Implement backup_crontab() |
| 18.8 | Implement restore_crontab() |
| 18.9 | Implement show_status() + update main.py |

**Total: 17 sub-tasks**
