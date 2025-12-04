#!/bin/bash
#
# vexo local development runner
# Usage: ./dev.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}vexo Development Runner${NC}"
echo "─────────────────────────────"

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)

# Install Python if not found
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Python 3 not found, installing...${NC}"
    
    case "$OS" in
        ubuntu|debian)
            sudo apt update
            sudo apt install -y python3 python3-pip
            ;;
        macos)
            if command -v brew &> /dev/null; then
                brew install python3
            else
                echo -e "${RED}Please install Homebrew first: https://brew.sh${NC}"
                exit 1
            fi
            ;;
        *)
            echo -e "${RED}Unsupported OS. Please install Python 3 manually.${NC}"
            exit 1
            ;;
    esac
    
    echo -e "${GREEN}✓ Python installed${NC}"
fi

# Install pip if not found
if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
    echo -e "${YELLOW}Installing pip...${NC}"
    case "$OS" in
        ubuntu|debian)
            sudo apt update
            sudo apt install -y python3-pip
            ;;
        *)
            curl -sS https://bootstrap.pypa.io/get-pip.py | python3
            ;;
    esac
    echo -e "${GREEN}✓ pip installed${NC}"
fi

# Function to run pip
run_pip() {
    if command -v pip3 &> /dev/null; then
        pip3 "$@"
    else
        python3 -m pip "$@"
    fi
}

# Install dependencies if needed (auto-detect from requirements.txt)
install_deps() {
    echo -e "${YELLOW}Installing dependencies...${NC}"
    run_pip install -r "$SCRIPT_DIR/requirements.txt" --quiet --break-system-packages 2>/dev/null || \
    run_pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
    echo -e "${GREEN}✓ Dependencies installed${NC}"
}

# Check all packages from requirements.txt
check_deps() {
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" =~ ^# ]] && continue
        # Extract package name (before >= or ==)
        pkg=$(echo "$line" | sed 's/[>=<].*//' | tr '-' '_')
        if ! python3 -c "import $pkg" 2>/dev/null; then
            return 1
        fi
    done < "$SCRIPT_DIR/requirements.txt"
    return 0
}

if ! check_deps; then
    install_deps
fi

echo -e "${GREEN}✓ Starting vexo...${NC}"
echo ""

# Run vexo
cd "$SCRIPT_DIR"
python3 main.py "$@"
