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
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Function to detect project directory using multiple methods
detect_project_directory() {
    local detected_dir=""

    # Method 1: Use current working directory (most reliable for launcher)
    if [[ -n "${PWD}" ]]; then
        detected_dir="$PWD"
    else
        # Method 2: Check if BASH_SOURCE[0] is available
        if [[ -n "${BASH_SOURCE[0]}" ]]; then
            # Get the directory where the script was called from
            detected_dir="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
        else
            # Method 3: Check if script was called with full path
            if [[ "$0" == /* ]]; then
                detected_dir="$(dirname "$0")"
            fi
        fi
    fi

    # Method 4: Look for workspace.json in parent directories (DevStream project marker)
    if [[ -n "$detected_dir" ]]; then
        local search_dir="$detected_dir"
        while [[ "$search_dir" != "/" ]]; do
            if [[ -f "$search_dir/.devstream/workspace.json" ]]; then
                detected_dir="$search_dir"
                break
            fi
            search_dir="$(dirname "$search_dir")"
        done
    fi

    # Method 5: Check for data/devstream.db (project database marker)
    if [[ -n "$detected_dir" ]]; then
        local search_dir="$detected_dir"
        while [[ "$search_dir" != "/" ]]; do
            if [[ -f "$search_dir/data/devstream.db" ]]; then
                detected_dir="$search_dir"
                break
            fi
            search_dir="$(dirname "$search_dir")"
        done
    fi

    # Method 6: Fallback to current working directory
    if [[ -z "$detected_dir" || "$detected_dir" == "." ]]; then
        detected_dir="$(pwd)"
    fi

    # Resolve to absolute path
    detected_dir="$(cd "$detected_dir" && pwd)"

    echo "$detected_dir"
}

# Main function
main() {
    local command="${1:-start}"
    local provider="${2:-anthropic}"

    echo ""
    print_status "🚀 Simple DevStream Launcher"
    print_status "==============================="
    echo ""

    # Detect project directory using multiple methods
    local project_dir="$(detect_project_directory)"
    print_info "Detected project directory: $project_dir"

    # Verify it's a valid DevStream project
    if [[ ! -f "$project_dir/.devstream/workspace.json" ]] && [[ ! -f "$project_dir/data/devstream.db" ]]; then
        print_warning "Directory doesn't appear to be a DevStream project"
        print_info "Initializing DevStream in current directory..."

        # Initialize DevStream if it's not a project yet
        cd "$project_dir"
        if [[ -f "/Users/fulvioventura/devstream/scripts/devstream-init.py" ]]; then
            python3 "/Users/fulvioventura/devstream/scripts/devstream-init.py" "$project_dir"
        else
            print_error "DevStream initialization script not found"
            exit 1
        fi
    fi

    # Find DevStream installation
    local devstream_root="/Users/fulvioventura/devstream"
    if [ ! -f "$devstream_root/start-devstream.sh" ]; then
        print_error "DevStream installation not found at: $devstream_root"
        exit 1
    fi

    print_info "DevStream installation: $devstream_root"
    print_info "Provider: $provider"
    echo ""

    print_status "🔄 Launching DevStream..."
    print_info "Project root: $project_dir"
    echo ""

    # Set environment variables and execute
    export DEVSTREAM_PROJECT_ROOT="$project_dir"
    cd "$project_dir"

    # Execute DevStream with project directory context
    exec "$devstream_root/start-devstream.sh" "$command" "$provider"
}

# Parse arguments and run main
main "$@"