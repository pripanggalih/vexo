#!/bin/bash
#
# Vexo Clean Uninstall Script
# Removes vexo and ALL installed packages/data
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${CYAN}→ $1${NC}"
}

# Check root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

# Show warning banner
show_warning_banner() {
    echo ""
    echo -e "${RED}┌─────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${RED}│                    ⚠️  CLEAN UNINSTALL                          │${NC}"
    echo -e "${RED}├─────────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${RED}│  This will PERMANENTLY DELETE:                                  │${NC}"
    echo -e "${RED}│                                                                 │${NC}"
    echo -e "${RED}│  📦 Packages:                                                   │${NC}"
    echo -e "${RED}│     • nginx, php8.x, mariadb, postgresql, redis                 │${NC}"
    echo -e "${RED}│     • postfix, dovecot, fail2ban, ufw, supervisor, certbot      │${NC}"
    echo -e "${RED}│                                                                 │${NC}"
    echo -e "${RED}│  📁 Data & Configs:                                             │${NC}"
    echo -e "${RED}│     • /var/www/* (all websites)                                 │${NC}"
    echo -e "${RED}│     • /var/lib/mysql, /var/lib/postgresql (databases)           │${NC}"
    echo -e "${RED}│     • /etc/nginx, /etc/php, /etc/postfix, etc.                  │${NC}"
    echo -e "${RED}│     • /etc/letsencrypt (SSL certificates)                       │${NC}"
    echo -e "${RED}│     • /var/mail/* (all emails)                                  │${NC}"
    echo -e "${RED}│                                                                 │${NC}"
    echo -e "${RED}│  🔧 Vexo:                                                       │${NC}"
    echo -e "${RED}│     • /opt/vexo, /var/log/vexo, ~/.vexo                         │${NC}"
    echo -e "${RED}│                                                                 │${NC}"
    echo -e "${RED}│  ⚠️  THIS CANNOT BE UNDONE!                                     │${NC}"
    echo -e "${RED}└─────────────────────────────────────────────────────────────────┘${NC}"
    echo ""
}

# First confirmation
confirm_step1() {
    read -p "Are you sure you want to continue? (y/N): " response
    case "$response" in
        [yY][eE][sS]|[yY]) 
            return 0
            ;;
        *)
            print_info "Cancelled."
            exit 0
            ;;
    esac
}

# Second confirmation - type exact phrase
confirm_step2() {
    echo ""
    read -p "Type 'CLEAN UNINSTALL' to confirm: " response
    if [ "$response" != "CLEAN UNINSTALL" ]; then
        print_error "Confirmation failed. Aborting."
        exit 1
    fi
}

# Stop services first
stop_services() {
    print_info "Stopping services..."
    
    services="nginx php8.3-fpm php8.2-fpm php8.1-fpm php8.0-fpm mariadb mysql postgresql redis-server postfix dovecot fail2ban supervisor"
    
    for service in $services; do
        systemctl stop "$service" 2>/dev/null || true
        systemctl disable "$service" 2>/dev/null || true
    done
    
    print_success "Services stopped"
}

# Remove packages
remove_packages() {
    print_info "Removing packages..."
    
    # Stop apt processes if any
    killall apt apt-get 2>/dev/null || true
    
    # Purge packages
    DEBIAN_FRONTEND=noninteractive apt purge -y \
        nginx* php* mariadb* mysql* postgresql* redis* \
        postfix* dovecot* roundcube* fail2ban ufw \
        supervisor certbot* python3-certbot* \
        2>/dev/null || true
    
    # Autoremove
    apt autoremove -y 2>/dev/null || true
    apt autoclean 2>/dev/null || true
    
    print_success "Packages removed"
}

# Remove directories
remove_directories() {
    print_info "Removing data and configurations..."
    
    # Vexo
    rm -rf /opt/vexo
    rm -rf /var/log/vexo
    rm -rf /etc/vexo
    rm -rf ~/.vexo
    rm -rf /root/.vexo
    rm -f /usr/local/bin/vexo
    
    # Web
    rm -rf /var/www
    rm -rf /etc/nginx
    
    # PHP
    rm -rf /etc/php
    
    # Databases
    rm -rf /var/lib/mysql
    rm -rf /var/lib/postgresql
    rm -rf /etc/mysql
    rm -rf /etc/postgresql
    
    # Redis
    rm -rf /var/lib/redis
    rm -rf /etc/redis
    
    # Email
    rm -rf /var/mail
    rm -rf /var/spool/mail
    rm -rf /etc/postfix
    rm -rf /etc/dovecot
    rm -rf /etc/opendkim
    
    # Security
    rm -rf /etc/fail2ban
    rm -rf /etc/letsencrypt
    
    # Supervisor
    rm -rf /etc/supervisor/conf.d/*
    
    # Logs
    rm -rf /var/log/nginx
    rm -rf /var/log/php*
    rm -rf /var/log/mysql
    rm -rf /var/log/postgresql
    rm -rf /var/log/mail.*
    rm -rf /var/log/fail2ban.log*
    
    print_success "Data and configurations removed"
}

# Main
main() {
    # Handle --no-confirm flag (called from vexo menu, already confirmed)
    if [ "${1:-}" = "--no-confirm" ]; then
        stop_services
        remove_packages
        remove_directories
        
        echo ""
        echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  ✓ Clean uninstall complete!                       ${NC}"
        echo -e "${GREEN}  Your VPS is now clean.                            ${NC}"
        echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
        echo ""
        exit 0
    fi
    
    show_warning_banner
    confirm_step1
    confirm_step2
    
    echo ""
    print_warning "Starting clean uninstall in 3 seconds... (Ctrl+C to cancel)"
    sleep 3
    
    echo ""
    stop_services
    remove_packages
    remove_directories
    
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✓ Clean uninstall complete!                       ${NC}"
    echo -e "${GREEN}  Your VPS is now clean.                            ${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
    echo ""
}

main "$@"
