#!/usr/bin/env bash

#==============================================================================
# DevStream Installation Script
# Version: 2.1.0
# Description: Automated setup for DevStream project with comprehensive checks
#==============================================================================

set -e  # Exit on error (disable with --no-exit)
set -u  # Exit on undefined variable

#------------------------------------------------------------------------------
# Configuration
#------------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
VENV_DIR="${PROJECT_ROOT}/.devstream"
DATA_DIR="${PROJECT_ROOT}/data"
MCP_SERVER_DIR="${PROJECT_ROOT}/mcp-devstream-server"
CLAUDE_SETTINGS="${HOME}/.claude/settings.json"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Flags
VERBOSE=false
DRY_RUN=false
NO_EXIT=false
SKIP_OPTIONAL=false

#------------------------------------------------------------------------------
# Helper Functions
#------------------------------------------------------------------------------

print_header() {
    echo ""
    echo -e "${BLUE}===================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}===================================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[VERBOSE]${NC} $1"
    fi
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

check_exit_code() {
    local exit_code=$1
    local success_msg=$2
    local error_msg=$3

    if [ $exit_code -eq 0 ]; then
        print_success "$success_msg"
        return 0
    else
        print_error "$error_msg (exit code: $exit_code)"
        if [ "$NO_EXIT" = false ]; then
            exit $exit_code
        fi
        return $exit_code
    fi
}

prompt_continue() {
    local message=$1
    if [ "$SKIP_OPTIONAL" = true ]; then
        print_warning "Skipping: $message"
        return 1
    fi

    echo -e "${YELLOW}?${NC} $message"
    read -p "Continue? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        return 0
    else
        return 1
    fi
}

#------------------------------------------------------------------------------
# Parse Arguments
#------------------------------------------------------------------------------

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --verbose|-v)
                VERBOSE=true
                print_info "Verbose mode enabled"
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                print_warning "Dry-run mode: No changes will be made"
                shift
                ;;
            --no-exit)
                NO_EXIT=true
                print_warning "No-exit mode: Script will continue on errors"
                shift
                ;;
            --skip-optional)
                SKIP_OPTIONAL=true
                print_info "Skipping optional steps"
                shift
                ;;
            --help|-h)
                cat << EOF
DevStream Installation Script

Usage: $0 [OPTIONS]

Options:
  --verbose, -v       Enable verbose output
  --dry-run          Show what would be done without making changes
  --no-exit          Continue on errors instead of exiting
  --skip-optional    Skip optional steps without prompting
  --help, -h         Show this help message

Examples:
  $0                              # Standard installation
  $0 --verbose                    # Installation with detailed output
  $0 --dry-run                    # Test installation without changes
  $0 --no-exit --skip-optional    # Force installation, skip optional steps

EOF
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
}

#------------------------------------------------------------------------------
# Step 1: Prerequisites Check
#------------------------------------------------------------------------------

check_prerequisites() {
    print_header "Step 1: Checking Prerequisites"

    local has_errors=false

    # Check Python 3.11+
    print_info "Checking Python 3.11+..."
    if command_exists python3.11; then
        local python_version=$(python3.11 --version 2>&1 | awk '{print $2}')
        print_success "Python 3.11 found: $python_version"
        print_verbose "Python path: $(which python3.11)"
    else
        print_error "Python 3.11+ not found"
        echo ""
        echo "Installation instructions:"
        echo "  macOS:   brew install python@3.11"
        echo "  Ubuntu:  sudo apt install python3.11 python3.11-venv"
        echo "  Fedora:  sudo dnf install python3.11"
        echo ""
        has_errors=true
    fi

    # Check Node.js 16+
    print_info "Checking Node.js 16+..."
    if command_exists node; then
        local node_version=$(node --version)
        local node_major=$(echo "$node_version" | sed 's/v\([0-9]*\).*/\1/')
        if [ "$node_major" -ge 16 ]; then
            print_success "Node.js found: $node_version"
            print_verbose "Node path: $(which node)"
        else
            print_error "Node.js version must be 16+, found: $node_version"
            echo ""
            echo "Installation instructions:"
            echo "  macOS:   brew install node"
            echo "  Ubuntu:  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install nodejs"
            echo "  Fedora:  sudo dnf install nodejs"
            echo ""
            has_errors=true
        fi
    else
        print_error "Node.js not found"
        echo ""
        echo "Installation instructions:"
        echo "  macOS:   brew install node"
        echo "  Ubuntu:  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install nodejs"
        echo "  Fedora:  sudo dnf install nodejs"
        echo ""
        has_errors=true
    fi

    # Check npm
    if command_exists npm; then
        local npm_version=$(npm --version)
        print_success "npm found: $npm_version"
        print_verbose "npm path: $(which npm)"
    else
        print_warning "npm not found (usually installed with Node.js)"
    fi

    # Check Git
    print_info "Checking Git..."
    if command_exists git; then
        local git_version=$(git --version | awk '{print $3}')
        print_success "Git found: $git_version"
        print_verbose "Git path: $(which git)"
    else
        print_error "Git not found"
        echo ""
        echo "Installation instructions:"
        echo "  macOS:   brew install git"
        echo "  Ubuntu:  sudo apt install git"
        echo "  Fedora:  sudo dnf install git"
        echo ""
        has_errors=true
    fi

    # Check Ollama (optional)
    print_info "Checking Ollama (optional)..."
    if command_exists ollama; then
        print_success "Ollama found"
        print_verbose "Ollama path: $(which ollama)"

        # Check if nomic-embed-text model is available
        if ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
            print_success "nomic-embed-text model installed"
        else
            print_warning "nomic-embed-text model not installed"
            echo "  Run: ollama pull nomic-embed-text"
        fi
    else
        print_warning "Ollama not found (required for semantic search)"
        echo "  Installation: https://ollama.ai/"
        echo "  After installation, run: ollama pull nomic-embed-text"
    fi

    if [ "$has_errors" = true ]; then
        print_error "Prerequisites check failed"
        if [ "$NO_EXIT" = false ]; then
            exit 1
        fi
        return 1
    fi

    print_success "All prerequisites met"
}

#------------------------------------------------------------------------------
# Step 2: Python Environment Setup
#------------------------------------------------------------------------------

setup_python_environment() {
    print_header "Step 2: Setting up Python Virtual Environment"

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would create venv at: $VENV_DIR"
        print_info "[DRY-RUN] Would install requirements from: ${PROJECT_ROOT}/requirements.txt"
        return 0
    fi

    # Create venv
    if [ -d "$VENV_DIR" ]; then
        print_warning "Virtual environment already exists at: $VENV_DIR"
        if ! prompt_continue "Remove and recreate virtual environment?"; then
            print_info "Keeping existing virtual environment"
        else
            print_info "Removing existing virtual environment..."
            rm -rf "$VENV_DIR"
            print_verbose "Removed: $VENV_DIR"
        fi
    fi

    if [ ! -d "$VENV_DIR" ]; then
        print_info "Creating virtual environment..."
        python3.11 -m venv "$VENV_DIR"
        check_exit_code $? "Virtual environment created" "Failed to create virtual environment"
        print_verbose "Created: $VENV_DIR"
    fi

    # Activate venv
    print_info "Activating virtual environment..."
    source "${VENV_DIR}/bin/activate"
    print_verbose "Activated: $VENV_DIR"

    # Verify Python version
    local venv_python_version=$("${VENV_DIR}/bin/python" --version 2>&1 | awk '{print $2}')
    print_success "Using Python $venv_python_version from venv"

    # Upgrade pip
    print_info "Upgrading pip..."
    "${VENV_DIR}/bin/python" -m pip install --upgrade pip >/dev/null 2>&1
    check_exit_code $? "pip upgraded" "Failed to upgrade pip"

    local pip_version=$("${VENV_DIR}/bin/pip" --version | awk '{print $2}')
    print_verbose "pip version: $pip_version"

    # Install requirements.txt
    if [ -f "${PROJECT_ROOT}/requirements.txt" ]; then
        print_info "Installing requirements from requirements.txt..."
        "${VENV_DIR}/bin/pip" install -r "${PROJECT_ROOT}/requirements.txt" >/dev/null 2>&1
        check_exit_code $? "Requirements installed" "Failed to install requirements"
        print_verbose "Installed packages from requirements.txt"
    else
        print_warning "requirements.txt not found, skipping"
    fi

    # Install critical hook dependencies
    print_info "Installing hook dependencies (cchooks, aiohttp, structlog)..."
    "${VENV_DIR}/bin/pip" install "cchooks>=0.1.4" "aiohttp>=3.8.0" "structlog>=23.0.0" "python-dotenv>=1.0.0" >/dev/null 2>&1
    check_exit_code $? "Hook dependencies installed" "Failed to install hook dependencies"

    # Verify installations
    print_info "Verifying installed packages..."
    local installed_count=$("${VENV_DIR}/bin/pip" list 2>/dev/null | tail -n +3 | wc -l | tr -d ' ')
    print_success "Installed $installed_count packages"

    if [ "$VERBOSE" = true ]; then
        echo ""
        echo "Installed packages (first 20):"
        "${VENV_DIR}/bin/pip" list 2>/dev/null | head -20
        echo ""
    fi

    # Verify critical packages
    print_info "Verifying critical packages..."
    local critical_packages=("cchooks" "aiohttp" "structlog" "python-dotenv")
    for package in "${critical_packages[@]}"; do
        if "${VENV_DIR}/bin/pip" list 2>/dev/null | grep -qi "^${package}"; then
            local version=$("${VENV_DIR}/bin/pip" show "$package" 2>/dev/null | grep "^Version:" | awk '{print $2}')
            print_success "$package ($version)"
        else
            print_error "$package not installed"
            if [ "$NO_EXIT" = false ]; then
                exit 1
            fi
        fi
    done
}

#------------------------------------------------------------------------------
# Step 3: Database Initialization
#------------------------------------------------------------------------------

initialize_database() {
    print_header "Step 3: Initializing Database"

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would initialize database at: ${DATA_DIR}/devstream.db"
        return 0
    fi

    # Create data directory
    if [ ! -d "$DATA_DIR" ]; then
        print_info "Creating data directory..."
        mkdir -p "$DATA_DIR"
        print_verbose "Created: $DATA_DIR"
    fi

    # Check if database already exists
    if [ -f "${DATA_DIR}/devstream.db" ]; then
        print_warning "Database already exists at: ${DATA_DIR}/devstream.db"
        if ! prompt_continue "Remove and recreate database? (ALL DATA WILL BE LOST)"; then
            print_info "Keeping existing database"
            return 0
        else
            print_info "Removing existing database..."
            rm -f "${DATA_DIR}/devstream.db"
            print_verbose "Removed: ${DATA_DIR}/devstream.db"
        fi
    fi

    # Run setup script
    if [ -f "${PROJECT_ROOT}/scripts/setup-db.py" ]; then
        print_info "Running database setup script..."
        "${VENV_DIR}/bin/python" "${PROJECT_ROOT}/scripts/setup-db.py"
        check_exit_code $? "Database initialized" "Failed to initialize database"
        print_verbose "Database created at: ${DATA_DIR}/devstream.db"
    else
        print_error "Database setup script not found: ${PROJECT_ROOT}/scripts/setup-db.py"
        print_info "You may need to run database initialization manually later"
        if [ "$NO_EXIT" = false ]; then
            exit 1
        fi
        return 1
    fi

    # Verify database
    if [ -f "${DATA_DIR}/devstream.db" ]; then
        local db_size=$(du -h "${DATA_DIR}/devstream.db" | awk '{print $1}')
        print_success "Database created (size: $db_size)"

        # Check tables (if sqlite3 available)
        if command_exists sqlite3; then
            local table_count=$(sqlite3 "${DATA_DIR}/devstream.db" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" 2>/dev/null)
            print_success "Database contains $table_count tables"

            if [ "$VERBOSE" = true ]; then
                echo ""
                echo "Database tables:"
                sqlite3 "${DATA_DIR}/devstream.db" "SELECT name FROM sqlite_master WHERE type='table';" 2>/dev/null | sed 's/^/  - /'
                echo ""
            fi
        fi
    else
        print_error "Database file not created"
        if [ "$NO_EXIT" = false ]; then
            exit 1
        fi
        return 1
    fi
}

#------------------------------------------------------------------------------
# Step 4: MCP Server Setup
#------------------------------------------------------------------------------

setup_mcp_server() {
    print_header "Step 4: Setting up MCP Server"

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would run npm install and build in: $MCP_SERVER_DIR"
        return 0
    fi

    # Check if MCP server directory exists
    if [ ! -d "$MCP_SERVER_DIR" ]; then
        print_error "MCP server directory not found: $MCP_SERVER_DIR"
        if [ "$NO_EXIT" = false ]; then
            exit 1
        fi
        return 1
    fi

    cd "$MCP_SERVER_DIR"
    print_verbose "Changed directory to: $MCP_SERVER_DIR"

    # Install dependencies
    print_info "Installing MCP server dependencies (this may take a minute)..."
    npm install >/dev/null 2>&1
    check_exit_code $? "Dependencies installed" "Failed to install dependencies"

    # Build project
    print_info "Building MCP server..."
    npm run build >/dev/null 2>&1
    check_exit_code $? "MCP server built successfully" "Failed to build MCP server"

    # Verify dist directory
    if [ -d "${MCP_SERVER_DIR}/dist" ]; then
        local file_count=$(find "${MCP_SERVER_DIR}/dist" -type f | wc -l | tr -d ' ')
        print_success "Build artifacts created ($file_count files in dist/)"

        if [ "$VERBOSE" = true ]; then
            echo ""
            echo "Build artifacts:"
            find "${MCP_SERVER_DIR}/dist" -type f | head -10 | sed 's/^/  - /'
            if [ "$file_count" -gt 10 ]; then
                echo "  ... and $((file_count - 10)) more files"
            fi
            echo ""
        fi
    else
        print_error "Build artifacts not created (dist/ directory missing)"
        if [ "$NO_EXIT" = false ]; then
            exit 1
        fi
        return 1
    fi

    cd "$PROJECT_ROOT"
    print_verbose "Changed directory back to: $PROJECT_ROOT"
}

#------------------------------------------------------------------------------
# Step 5: Hook Configuration Check
#------------------------------------------------------------------------------

check_hook_configuration() {
    print_header "Step 5: Checking Hook Configuration"

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would check for: $CLAUDE_SETTINGS"
        return 0
    fi

    if [ -f "$CLAUDE_SETTINGS" ]; then
        print_success "Claude settings file found: $CLAUDE_SETTINGS"

        # Check for hook configuration
        if grep -q "PreToolUse" "$CLAUDE_SETTINGS" 2>/dev/null; then
            print_success "Hook configuration detected"
            print_verbose "PreToolUse hook found in settings.json"
        else
            print_warning "No hook configuration detected in settings.json"
            print_info "You may need to configure hooks manually"
        fi
    else
        print_warning "Claude settings file not found: $CLAUDE_SETTINGS"
        echo ""
        print_info "You need to configure hooks in Claude Code settings"
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Hook Configuration Instructions"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Add the following to your ~/.claude/settings.json:"
    echo ""
    cat << 'EOF'
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/memory/pre_tool_use.py"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "hooks": [
          {
            "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/memory/post_tool_use.py"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/context/user_query_context_enhancer.py"
          }
        ]
      }
    ]
  }
}
EOF
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

#------------------------------------------------------------------------------
# Step 6: Final Steps
#------------------------------------------------------------------------------

final_steps() {
    print_header "Installation Complete!"

    echo ""
    echo -e "${GREEN}✓ DevStream installation completed successfully${NC}"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Next Steps"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "1. Configure environment variables:"
    echo "   cp .env.example .env.devstream"
    echo "   # Edit .env.devstream with your settings"
    echo ""
    echo "2. Configure Claude hooks (see instructions above)"
    echo ""
    echo "3. Start the MCP server:"
    echo "   cd mcp-devstream-server"
    echo "   npm start"
    echo ""
    echo "4. Activate the virtual environment:"
    echo "   source .devstream/bin/activate"
    echo ""
    echo "5. Run tests to verify installation:"
    echo "   .devstream/bin/python -m pytest tests/ -v"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Troubleshooting"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "• Database issues:"
    echo "  .devstream/bin/python scripts/setup-db.py"
    echo ""
    echo "• Hook errors:"
    echo "  Check logs at: ~/.claude/logs/devstream/"
    echo ""
    echo "• MCP server issues:"
    echo "  cd mcp-devstream-server && npm run build"
    echo ""
    echo "• Import errors:"
    echo "  .devstream/bin/pip install -r requirements.txt"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "For more information, see:"
    echo "  - README.md"
    echo "  - CLAUDE.md (project rules)"
    echo "  - docs/guides/ (documentation)"
    echo ""
}

#------------------------------------------------------------------------------
# Main Execution
#------------------------------------------------------------------------------

main() {
    print_header "DevStream Installation Script v2.1.0"

    # Parse arguments
    parse_args "$@"

    # Run installation steps
    check_prerequisites
    setup_python_environment
    initialize_database
    setup_mcp_server
    check_hook_configuration
    final_steps

    echo ""
    print_success "Installation completed successfully!"
    echo ""
}

# Run main function with all arguments
main "$@"
