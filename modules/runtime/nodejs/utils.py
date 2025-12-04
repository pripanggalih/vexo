"""Shared utilities for Node.js runtime module."""

import os

from config import NVM_DIR
from utils.shell import run_command


def is_nvm_installed():
    """Check if NVM is installed."""
    nvm_script = os.path.join(NVM_DIR, "nvm.sh")
    return os.path.exists(nvm_script)


def get_nvm_version():
    """Get installed NVM version."""
    result = run_with_nvm("nvm --version")
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None


def run_with_nvm(command):
    """
    Run a command with NVM sourced.
    
    Args:
        command: Command to run after sourcing NVM
    
    Returns:
        CompletedProcess or None if NVM not installed
    """
    nvm_script = os.path.join(NVM_DIR, "nvm.sh")
    if not os.path.exists(nvm_script):
        return None
    
    full_command = f'bash -c "source {nvm_script} && {command}"'
    return run_command(full_command, check=False, silent=True)


def run_with_nvm_realtime(command, description=""):
    """Run command with NVM sourced and show realtime output."""
    from utils.shell import run_command_realtime
    
    nvm_script = os.path.join(NVM_DIR, "nvm.sh")
    if not os.path.exists(nvm_script):
        return 1
    
    full_command = f'bash -c "source {nvm_script} && {command}"'
    return run_command_realtime(full_command, description)


def get_installed_nodejs_versions():
    """Get list of installed Node.js versions via NVM."""
    result = run_with_nvm("nvm ls --no-colors")
    if result is None or result.returncode != 0:
        return []
    
    versions = []
    for line in result.stdout.strip().split('\n'):
        line = line.strip()
        line = line.replace('->', '').replace('*', '').strip()
        
        if line.startswith('v') and '.' in line:
            version = line.split()[0] if ' ' in line else line
            version = version.strip()
            if version and version not in versions:
                versions.append(version)
    
    return sorted(versions, key=lambda v: [int(x) for x in v.lstrip('v').split('.')], reverse=True)


def get_current_nodejs_version():
    """Get the current active Node.js version."""
    result = run_with_nvm("node --version")
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None


def get_default_nodejs_version():
    """Get the default Node.js version set in NVM."""
    result = run_with_nvm("nvm alias default")
    if result and result.returncode == 0:
        output = result.stdout.strip()
        if '->' in output:
            version = output.split('->')[-1].strip()
            version = version.replace('*', '').strip()
            if version.startswith('v'):
                return version
    return None


def is_pm2_installed():
    """Check if PM2 is installed globally."""
    result = run_with_nvm("pm2 --version")
    return result is not None and result.returncode == 0


def get_pm2_version():
    """Get PM2 version."""
    result = run_with_nvm("pm2 --version")
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None
