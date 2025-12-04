"""Worker config templates for vexo supervisor."""

from modules.supervisor.common import SUPERVISOR_LOG_DIR, format_env_string


def generate_laravel_queue_config(name, laravel_path, connection="database", queues="default",
                                   numprocs=1, user="www-data", memory=128, 
                                   sleep=3, tries=3, max_time=3600, env_vars=None):
    """
    Generate Laravel queue:work worker config.
    
    Args:
        name: Worker name
        laravel_path: Path to Laravel project
        connection: Queue connection (database, redis, sqs, etc.)
        queues: Queue names (comma-separated)
        numprocs: Number of worker processes
        user: System user to run as
        memory: Memory limit in MB
        sleep: Sleep seconds when no jobs
        tries: Number of retry attempts
        max_time: Maximum job runtime in seconds
        env_vars: Optional environment variables dict
    
    Returns:
        str: Supervisor config content
    """
    env_line = ""
    if env_vars:
        env_line = f"environment={format_env_string(env_vars)}\n"
    
    return f"""# vexo-managed: laravel-queue
[program:{name}]
process_name=%(program_name)s_%(process_num)02d
command=php {laravel_path}/artisan queue:work {connection} --queue={queues} --sleep={sleep} --tries={tries} --max-time={max_time} --memory={memory}
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
user={user}
numprocs={numprocs}
redirect_stderr=true
stdout_logfile={SUPERVISOR_LOG_DIR}/{name}.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=5
stopwaitsecs={max_time}
{env_line}"""


def generate_laravel_horizon_config(name, laravel_path, user="www-data", env_vars=None):
    """
    Generate Laravel Horizon worker config.
    
    Args:
        name: Worker name
        laravel_path: Path to Laravel project
        user: System user to run as
        env_vars: Optional environment variables dict
    
    Returns:
        str: Supervisor config content
    """
    env_line = ""
    if env_vars:
        env_line = f"environment={format_env_string(env_vars)}\n"
    
    return f"""# vexo-managed: laravel-horizon
[program:{name}]
process_name=%(program_name)s
command=php {laravel_path}/artisan horizon
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
user={user}
numprocs=1
redirect_stderr=true
stdout_logfile={SUPERVISOR_LOG_DIR}/{name}.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=5
stopwaitsecs=3600
{env_line}"""


def generate_priority_queue_config(name, laravel_path, connection="database",
                                    high_queue="high", default_queue="default", 
                                    low_queue="low", numprocs=1, user="www-data",
                                    memory=128, env_vars=None):
    """
    Generate Laravel priority queue worker config.
    
    Args:
        name: Worker name
        laravel_path: Path to Laravel project
        connection: Queue connection
        high_queue: High priority queue name
        default_queue: Default priority queue name
        low_queue: Low priority queue name
        numprocs: Number of worker processes
        user: System user to run as
        memory: Memory limit in MB
        env_vars: Optional environment variables dict
    
    Returns:
        str: Supervisor config content
    """
    queues = f"{high_queue},{default_queue},{low_queue}"
    
    env_line = ""
    if env_vars:
        env_line = f"environment={format_env_string(env_vars)}\n"
    
    return f"""# vexo-managed: laravel-priority
[program:{name}]
process_name=%(program_name)s_%(process_num)02d
command=php {laravel_path}/artisan queue:work {connection} --queue={queues} --sleep=3 --tries=3 --max-time=3600 --memory={memory}
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
user={user}
numprocs={numprocs}
redirect_stderr=true
stdout_logfile={SUPERVISOR_LOG_DIR}/{name}.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=5
stopwaitsecs=3600
{env_line}"""


def generate_custom_command_config(name, command, working_dir=None, user="www-data",
                                    numprocs=1, autostart=True, autorestart=True,
                                    env_vars=None):
    """
    Generate custom command worker config.
    
    Args:
        name: Worker name
        command: Full command to execute
        working_dir: Working directory (optional)
        user: System user to run as
        numprocs: Number of processes
        autostart: Start on supervisor start
        autorestart: Restart on exit
        env_vars: Optional environment variables dict
    
    Returns:
        str: Supervisor config content
    """
    env_line = ""
    if env_vars:
        env_line = f"environment={format_env_string(env_vars)}\n"
    
    dir_line = ""
    if working_dir:
        dir_line = f"directory={working_dir}\n"
    
    process_name = "%(program_name)s_%(process_num)02d" if numprocs > 1 else "%(program_name)s"
    
    return f"""# vexo-managed: custom
[program:{name}]
process_name={process_name}
command={command}
{dir_line}autostart={'true' if autostart else 'false'}
autorestart={'true' if autorestart else 'false'}
stopasgroup=true
killasgroup=true
user={user}
numprocs={numprocs}
redirect_stderr=true
stdout_logfile={SUPERVISOR_LOG_DIR}/{name}.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=5
stopwaitsecs=60
{env_line}"""


def get_worker_type(config_content):
    """
    Detect worker type from config content.
    
    Args:
        config_content: Config file content
    
    Returns:
        str: Worker type ('laravel-queue', 'laravel-horizon', 'laravel-priority', 'custom')
    """
    if '# vexo-managed: laravel-horizon' in config_content:
        return 'laravel-horizon'
    elif '# vexo-managed: laravel-priority' in config_content:
        return 'laravel-priority'
    elif '# vexo-managed: laravel-queue' in config_content:
        return 'laravel-queue'
    elif '# vexo-managed: custom' in config_content:
        return 'custom'
    elif 'artisan horizon' in config_content:
        return 'laravel-horizon'
    elif 'artisan queue:work' in config_content:
        return 'laravel-queue'
    else:
        return 'custom'


TEMPLATE_INFO = {
    'laravel-queue': {
        'name': 'Laravel Queue Worker',
        'description': 'Standard queue:work for processing jobs',
        'icon': '📦',
    },
    'laravel-horizon': {
        'name': 'Laravel Horizon',
        'description': 'Horizon dashboard for Redis queues',
        'icon': '🌅',
    },
    'laravel-priority': {
        'name': 'Priority Queue Worker',
        'description': 'High/default/low priority queues',
        'icon': '⚡',
    },
    'custom': {
        'name': 'Custom Command',
        'description': 'Any shell command or script',
        'icon': '🔧',
    },
}
