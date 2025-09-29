#!/bin/bash

# DevStream Claude Code Launcher with Context7 Integration
# Replica dell'implementazione DevFlow funzionante

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
  echo -e "${GREEN}[STATUS]${NC} $1"
}

print_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to initialize Context7 (replica della funzione DevFlow)
initialize_context7() {
  print_status "Initializing Context7 MCP Integration..."

  # Check if Context7 is configured
  if [ ! -f "$PROJECT_ROOT/.config/context7.json" ]; then
    print_info "Setting up Context7 MCP configuration..."
    mkdir -p "$PROJECT_ROOT/.config"
    cat > "$PROJECT_ROOT/.config/context7.json" << EOF
{
  "enabled": true,
  "mcp_endpoint": "npx -y @upstash/context7-mcp@latest",
  "session_id": "devstream-$(date +%s)",
  "auto_inject": true,
  "cache_duration": 3600
}
EOF
    print_status "Context7 MCP configuration created"
  fi

  # Load environment variables from .env file
  if [ -f "$PROJECT_ROOT/.env" ]; then
    print_status "Loading environment variables from .env..."
    export $(cat "$PROJECT_ROOT/.env" | grep -v '^#' | grep -v '^$' | xargs)
  fi

  # Set Context7 environment variables
  export CONTEXT7_ENABLED=true
  export CONTEXT7_SESSION_ID=$(cat "$PROJECT_ROOT/.config/context7.json" | grep session_id | cut -d'"' -f4)
  export CONTEXT7_API_KEY="${CONTEXT7_API_KEY}"

  print_status "Context7 MCP initialized (Session: $CONTEXT7_SESSION_ID)"
  print_status "Context7 API Key: ${CONTEXT7_API_KEY:0:10}..."
}

# Function to check Context7 availability
verify_context7() {
  print_status "Verifying Context7 MCP availability..."

  if command -v npx >/dev/null 2>&1; then
    if npx -y @upstash/context7-mcp@latest --help >/dev/null 2>&1; then
      print_status "✅ Context7 MCP package available"
    else
      print_warning "⚠️  Context7 MCP package not available, will install on first use"
    fi
  else
    print_warning "⚠️  npx not available - Node.js may not be installed"
  fi
}

# Function to setup Claude Code MCP for Context7
setup_claude_mcp() {
  print_status "Setting up Claude Code MCP integration..."

  # Remove existing context7 MCP if present
  claude mcp remove context7 -s local 2>/dev/null || true

  # Add Context7 with proper wrapper script
  claude mcp add context7 ./context7-wrapper.sh || {
    print_warning "Failed to add Context7 to Claude MCP, trying alternative approach..."
    # Try with full path
    claude mcp add context7 "$PROJECT_ROOT/context7-wrapper.sh" || {
      print_warning "Could not add Context7 MCP server"
      return 1
    }
  }

  print_status "✅ Context7 added to Claude Code MCP configuration"
}

# Function to start Claude Code with Context7
start_claude_with_context7() {
  print_status "🚀 Starting Claude Code with Context7 integration..."
  print_info ""
  print_info "Context7 Usage:"
  print_info "  - Add 'use context7' to your prompts"
  print_info "  - Context7 will provide up-to-date documentation"
  print_info "  - Session ID: $CONTEXT7_SESSION_ID"
  print_info ""
  print_status "Starting Claude Code..."

  # Start Claude Code in the project directory
  cd "$PROJECT_ROOT"
  claude
}

# Main function
main() {
  echo ""
  print_status "🔧 DevStream Claude Code + Context7 Launcher"
  print_status "=============================================="
  echo ""

  # Initialize Context7
  initialize_context7

  # Verify Context7 availability
  verify_context7

  # Setup Claude MCP
  setup_claude_mcp

  echo ""
  print_status "🎉 Setup completed! Context7 is ready for use."
  echo ""

  # Start Claude Code
  start_claude_with_context7
}

# Run main function
main "$@"