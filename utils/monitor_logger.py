"""Monitor logging utility for vexo."""

import os
import json
import logging
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

import psutil

from config import ALERT_THRESHOLDS, LOG_CONFIG, USER_CONFIG_PATH


class MonitorLogger:
    """Logger for system monitoring metrics."""
    
    def __init__(self):
        self.log_dir = LOG_CONFIG['log_dir']
        self.log_file = os.path.join(self.log_dir, LOG_CONFIG['log_file'])
        self.retention_days = LOG_CONFIG['retention_days']
        self.thresholds = self._load_thresholds()
        self.logger = self._setup_logger()
    
    def _load_thresholds(self):
        """Load thresholds from user config or use defaults."""
        thresholds = ALERT_THRESHOLDS.copy()
        
        if os.path.exists(USER_CONFIG_PATH):
            try:
                with open(USER_CONFIG_PATH, 'r') as f:
                    user_config = json.load(f)
                    if 'alert_thresholds' in user_config:
                        for key, value in user_config['alert_thresholds'].items():
                            if key in thresholds:
                                thresholds[key].update(value)
            except (json.JSONDecodeError, IOError):
                pass
        
        return thresholds
    
    def _setup_logger(self):
        """Set up the logging handler."""
        # Create log directory if needed
        os.makedirs(self.log_dir, exist_ok=True)
        
        logger = logging.getLogger('vexo_monitor')
        logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        logger.handlers = []
        
        # Rotating file handler (max 50MB, keep 5 backups)
        max_bytes = LOG_CONFIG['max_log_size_mb'] * 1024 * 1024
        handler = RotatingFileHandler(
            self.log_file,
            maxBytes=max_bytes,
            backupCount=5
        )
        
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _get_level(self, value, resource):
        """Determine log level based on threshold."""
        thresholds = self.thresholds.get(resource, {})
        warning = thresholds.get('warning', 70)
        critical = thresholds.get('critical', 90)
        
        if value >= critical:
            return 'CRITICAL'
        elif value >= warning:
            return 'WARNING'
        return 'INFO'
    
    def log_metrics(self):
        """Log current system metrics."""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_level = self._get_level(cpu_percent, 'cpu')
            
            # Memory
            mem = psutil.virtual_memory()
            mem_level = self._get_level(mem.percent, 'memory')
            
            # Disk
            disk = psutil.disk_usage('/')
            disk_level = self._get_level(disk.percent, 'disk')
            
            # Swap
            swap = psutil.swap_memory()
            swap_level = self._get_level(swap.percent, 'swap') if swap.total > 0 else 'INFO'
            
            # Load average (compared to CPU cores)
            try:
                load_1, load_5, load_15 = psutil.getloadavg()
                cpu_count = psutil.cpu_count() or 1
                load_ratio = load_1 / cpu_count
                load_level = self._get_level(load_ratio * 100 / 5, 'load_avg')  # normalize to percentage
            except (AttributeError, OSError):
                load_1 = load_5 = load_15 = 0
                load_level = 'INFO'
            
            # Determine overall level (highest severity)
            levels = [cpu_level, mem_level, disk_level, swap_level, load_level]
            if 'CRITICAL' in levels:
                overall_level = logging.CRITICAL
            elif 'WARNING' in levels:
                overall_level = logging.WARNING
            else:
                overall_level = logging.INFO
            
            # Build log message
            msg = f"CPU: {cpu_percent:.1f}% | MEM: {mem.percent:.1f}% | DISK: {disk.percent:.1f}%"
            if swap.total > 0:
                msg += f" | SWAP: {swap.percent:.1f}%"
            msg += f" | LOAD: {load_1:.2f}/{load_5:.2f}/{load_15:.2f}"
            
            self.logger.log(overall_level, msg)
            
            # Log individual alerts
            if cpu_level == 'CRITICAL':
                self.logger.critical(f"CPU usage {cpu_percent:.1f}% exceeded critical threshold ({self.thresholds['cpu']['critical']}%)")
            elif cpu_level == 'WARNING':
                self.logger.warning(f"CPU usage {cpu_percent:.1f}% exceeded warning threshold ({self.thresholds['cpu']['warning']}%)")
            
            if mem_level == 'CRITICAL':
                self.logger.critical(f"Memory usage {mem.percent:.1f}% exceeded critical threshold ({self.thresholds['memory']['critical']}%)")
            elif mem_level == 'WARNING':
                self.logger.warning(f"Memory usage {mem.percent:.1f}% exceeded warning threshold ({self.thresholds['memory']['warning']}%)")
            
            if disk_level == 'CRITICAL':
                self.logger.critical(f"Disk usage {disk.percent:.1f}% exceeded critical threshold ({self.thresholds['disk']['critical']}%)")
            elif disk_level == 'WARNING':
                self.logger.warning(f"Disk usage {disk.percent:.1f}% exceeded warning threshold ({self.thresholds['disk']['warning']}%)")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to log metrics: {e}")
            return False
    
    def log_event(self, message, level='INFO'):
        """Log a custom event."""
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.log(log_level, message)
    
    def cleanup_old_logs(self):
        """Remove log files older than retention period."""
        try:
            cutoff = datetime.now() - timedelta(days=self.retention_days)
            
            for filename in os.listdir(self.log_dir):
                filepath = os.path.join(self.log_dir, filename)
                if os.path.isfile(filepath):
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if mtime < cutoff:
                        os.remove(filepath)
                        self.logger.info(f"Removed old log file: {filename}")
        
        except Exception as e:
            self.logger.error(f"Failed to cleanup old logs: {e}")
    
    def get_log_stats(self):
        """Get statistics about log files."""
        stats = {
            'log_file': self.log_file,
            'log_dir': self.log_dir,
            'retention_days': self.retention_days,
            'total_size': 0,
            'file_count': 0,
        }
        
        try:
            for filename in os.listdir(self.log_dir):
                filepath = os.path.join(self.log_dir, filename)
                if os.path.isfile(filepath):
                    stats['total_size'] += os.path.getsize(filepath)
                    stats['file_count'] += 1
        except Exception:
            pass
        
        return stats


def save_thresholds(thresholds):
    """Save alert thresholds to user config file."""
    config_dir = os.path.dirname(USER_CONFIG_PATH)
    os.makedirs(config_dir, exist_ok=True)
    
    # Load existing config
    config = {}
    if os.path.exists(USER_CONFIG_PATH):
        try:
            with open(USER_CONFIG_PATH, 'r') as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    config['alert_thresholds'] = thresholds
    
    with open(USER_CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)


def load_thresholds():
    """Load alert thresholds from user config or defaults."""
    thresholds = {k: v.copy() for k, v in ALERT_THRESHOLDS.items()}
    
    if os.path.exists(USER_CONFIG_PATH):
        try:
            with open(USER_CONFIG_PATH, 'r') as f:
                user_config = json.load(f)
                if 'alert_thresholds' in user_config:
                    for key, value in user_config['alert_thresholds'].items():
                        if key in thresholds:
                            thresholds[key].update(value)
        except (json.JSONDecodeError, IOError):
            pass
    
    return thresholds


def save_log_config(log_config):
    """Save log configuration to user config file."""
    config_dir = os.path.dirname(USER_CONFIG_PATH)
    os.makedirs(config_dir, exist_ok=True)
    
    config = {}
    if os.path.exists(USER_CONFIG_PATH):
        try:
            with open(USER_CONFIG_PATH, 'r') as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    config['log_config'] = log_config
    
    with open(USER_CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)


def load_log_config():
    """Load log configuration from user config or defaults."""
    log_config = LOG_CONFIG.copy()
    
    if os.path.exists(USER_CONFIG_PATH):
        try:
            with open(USER_CONFIG_PATH, 'r') as f:
                user_config = json.load(f)
                if 'log_config' in user_config:
                    log_config.update(user_config['log_config'])
        except (json.JSONDecodeError, IOError):
            pass
    
    return log_config
