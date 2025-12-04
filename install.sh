#!/bin/bash
#
# vexo installer
# Usage: curl -sSL https://raw.githubusercontent.com/pripanggalih/vexo/main/install.sh | sudo bash
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/pripanggalih/vexo.git"
INSTALL_DIR="/opt/vexo"
SYMLINK_PATH="/usr/local/bin/vexo"
MIN_PYTHON_VERSION="3.8"

# Functions
print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════╗"
    echo "║            Vexo Installer                 	  ║"
    echo "║   VPS Easy eXecution Orchestrator             ║"
    echo "║   Management CLI for Ubuntu/Debian            ║"
    echo "╚═══════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}! $1${NC}"
}

print_info() {
    echo -e "${CYAN}→ $1${NC}"
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
    print_success "Running as root"
}

# Check OS (Ubuntu/Debian only)
check_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [[ "$ID" != "ubuntu" && "$ID" != "debian" ]]; then
            print_error "This script only supports Ubuntu and Debian"
            print_info "Detected: $PRETTY_NAME"
            exit 1
        fi
        print_success "OS: $PRETTY_NAME"
    else
        print_error "Cannot detect OS. /etc/os-release not found."
        exit 1
    fi
}

# Check Python version
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        MIN_MAJOR=$(echo $MIN_PYTHON_VERSION | cut -d. -f1)
        MIN_MINOR=$(echo $MIN_PYTHON_VERSION | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -gt "$MIN_MAJOR" ] || ([ "$PYTHON_MAJOR" -eq "$MIN_MAJOR" ] && [ "$PYTHON_MINOR" -ge "$MIN_MINOR" ]); then
            print_success "Python $PYTHON_VERSION"
        else
            print_error "Python $MIN_PYTHON_VERSION or higher is required (found $PYTHON_VERSION)"
            exit 1
        fi
    else
        print_error "Python 3 is not installed"
        print_info "Install with: apt install python3"
        exit 1
    fi
}

# Check pip
check_pip() {
    if command -v pip3 &> /dev/null; then
        print_success "pip3 is installed"
    elif python3 -m pip --version &> /dev/null; then
        print_success "pip module is available"
    else
        print_warning "pip is not installed, installing..."
        apt update && apt install -y python3-pip
        print_success "pip installed"
    fi
}

# Check git
check_git() {
    if ! command -v git &> /dev/null; then
        print_warning "git is not installed, installing..."
        apt update && apt install -y git
    fi
    print_success "git is installed"
}

# Download/clone vexo
install_vexo() {
    print_info "Installing vexo to $INSTALL_DIR..."
    
    # Remove existing installation
    if [ -d "$INSTALL_DIR" ]; then
        print_warning "Existing installation found, removing..."
        rm -rf "$INSTALL_DIR"
    fi
    
    # Clone repository
    git clone "$REPO_URL" "$INSTALL_DIR"
    print_success "Downloaded vexo"
}

# Install Python dependencies
install_dependencies() {
    print_info "Installing Python dependencies..."
    
    cd "$INSTALL_DIR"
    
    # Try with --break-system-packages first (for newer pip/Ubuntu 23.04+)
    # Fall back to normal install if flag not supported
    if pip3 install -r requirements.txt --quiet --break-system-packages 2>/dev/null; then
        print_success "Dependencies installed"
    elif pip3 install -r requirements.txt --quiet 2>/dev/null; then
        print_success "Dependencies installed"
    else
        # Last resort: install python3-venv and use virtual environment
        print_warning "Standard pip install failed, trying virtual environment..."
        apt install -y python3-venv >/dev/null 2>&1 || true
        
        python3 -m venv "$INSTALL_DIR/venv"
        "$INSTALL_DIR/venv/bin/pip" install -r requirements.txt --quiet
        
        # Update shebang in main.py to use venv python
        sed -i "1s|.*|#!$INSTALL_DIR/venv/bin/python3|" "$INSTALL_DIR/main.py"
        
        print_success "Dependencies installed (using virtual environment)"
    fi
}

# Create symlink
create_symlink() {
    print_info "Creating symlink..."
    
    # Remove existing symlink
    if [ -L "$SYMLINK_PATH" ]; then
        rm "$SYMLINK_PATH"
    fi
    
    # Make main.py executable
    chmod +x "$INSTALL_DIR/main.py"
    
    # Create symlink
    ln -s "$INSTALL_DIR/main.py" "$SYMLINK_PATH"
    print_success "Symlink created: $SYMLINK_PATH"
}

# Set permissions
set_permissions() {
    print_info "Setting permissions..."
    
    chmod -R 755 "$INSTALL_DIR"
    print_success "Permissions set"
}

# Main installation
main() {
    print_banner
    
    echo "Pre-flight checks..."
    echo "─────────────────────"
    check_root
    check_os
    check_python
    check_pip
    check_git
    echo ""
    
    echo "Installation..."
    echo "─────────────────────"
    install_vexo
    install_dependencies
    create_symlink
    set_permissions
    echo ""
    
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo -e "${GREEN}   vexo installed successfully!        ${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo ""
    echo "Usage:"
    echo "  sudo vexo          - Run vexo"
    echo "  sudo vexo --help   - Show help"
    echo ""
    echo "Or run directly:"
    echo "  sudo python3 $INSTALL_DIR/main.py"
    echo ""
}

# Uninstall function
uninstall() {
    print_banner
    print_info "Uninstalling vexo..."
    
    if [ -L "$SYMLINK_PATH" ]; then
        rm "$SYMLINK_PATH"
        print_success "Removed symlink"
    fi
    
    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
        print_success "Removed $INSTALL_DIR"
    fi
    
    echo -e "${GREEN}vexo uninstalled successfully${NC}"
}

# Clean uninstall function
clean_uninstall() {
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    if [ -f "$SCRIPT_DIR/scripts/clean-uninstall.sh" ]; then
        bash "$SCRIPT_DIR/scripts/clean-uninstall.sh"
    elif [ -f "/opt/vexo/scripts/clean-uninstall.sh" ]; then
        bash "/opt/vexo/scripts/clean-uninstall.sh"
    else
        print_error "Clean uninstall script not found."
        print_info "Download and run manually:"
        echo "  curl -sSL https://raw.githubusercontent.com/pripanggalih/vexo/main/scripts/clean-uninstall.sh | sudo bash"
        exit 1
    fi
}

# Update function
update() {
    print_banner
    print_info "Updating vexo..."
    
    if [ ! -d "$INSTALL_DIR" ]; then
        print_error "vexo is not installed. Run install first."
        exit 1
    fi
    
    cd "$INSTALL_DIR"
    
    # Pull latest changes
    print_info "Fetching latest version..."
    git pull origin main
    print_success "Code updated"
    
    # Reinstall dependencies (in case new ones added)
    print_info "Updating dependencies..."
    
    # Check if using virtual environment
    if [ -d "$INSTALL_DIR/venv" ]; then
        "$INSTALL_DIR/venv/bin/pip" install -r requirements.txt --quiet --upgrade
    elif pip3 install -r requirements.txt --quiet --upgrade --break-system-packages 2>/dev/null; then
        :  # Success
    else
        pip3 install -r requirements.txt --quiet --upgrade 2>/dev/null || true
    fi
    print_success "Dependencies updated"
    
    echo ""
    echo -e "${GREEN}vexo updated successfully!${NC}"
}

# Handle arguments
case "${1:-}" in
    --uninstall)
        check_root
        uninstall
        ;;
    --clean-uninstall)
        check_root
        clean_uninstall
        ;;
    --update)
        check_root
        update
        ;;
    --help)
        print_banner
        echo "Usage:"
        echo "  sudo ./install.sh              Install vexo"
        echo "  sudo ./install.sh --update     Update to latest version"
        echo "  sudo ./install.sh --uninstall  Uninstall vexo"
        echo "  sudo ./install.sh --clean-uninstall  Remove vexo + ALL packages/data"
        echo "  ./install.sh --help            Show this help"
        ;;
    *)
        main
        ;;
esac
