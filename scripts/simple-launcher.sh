#!/bin/bash
# Simple DevStream Launcher - No blocking issues
# Launch DevStream from ANY project directory

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() { echo -e "${GREEN}[STATUS]${NC} $1"; }
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Main function
main() {
    local command="${1:-start}"
    local provider="${2:-anthropic}"

    echo ""
    print_status "🚀 Simple DevStream Launcher"
    print_status "==============================="
    echo ""

    # Get current directory
    local current_dir="$(pwd)"
    print_info "Current directory: $current_dir"

    # Find DevStream installation
    local devstream_root="/Users/fulvioventura/devstream"
    if [ ! -f "$devstream_root/start-devstream.sh" ]; then
        print_error "DevStream installation not found at: $devstream_root"
        exit 1
    fi

    print_info "DevStream installation: $devstream_root"
    print_info "Provider: $provider"
    echo ""

    # Build and execute command
    local full_cmd="cd \"$current_dir\" && \"$devstream_root/start-devstream.sh\" $command $provider"

    print_status "🔄 Launching DevStream..."
    print_info "Command: $full_cmd"
    echo ""

    # Execute command directly with project directory as argument
    cd "$current_dir"
    export DEVSTREAM_PROJECT_ROOT="$current_dir"
    "$devstream_root/start-devstream.sh" "$command" "$provider"
}

# Parse arguments and run main
main "$@"