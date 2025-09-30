#!/bin/bash

# DevStream Production Launcher
# Starts DevStream MCP Server with monitoring and Claude Code integration

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
MCP_SERVER_DIR="$PROJECT_ROOT/mcp-devstream-server"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
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

print_error() {
  echo -e "${RED}[ERROR]${NC} $1"
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

# Function to check prerequisites
check_prerequisites() {
  print_status "Checking prerequisites..."

  local all_good=true

  # Check Node.js
  if ! command -v node >/dev/null 2>&1; then
    print_error "Node.js not found"
    all_good=false
  else
    print_info "Node.js: $(node --version)"
  fi

  # Check database
  if [ ! -f "$PROJECT_ROOT/data/devstream.db" ]; then
    print_error "Database not found at data/devstream.db"
    all_good=false
  else
    print_info "Database: Found"
  fi

  # Check Ollama
  if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    print_warning "Ollama service not responding at http://localhost:11434"
    print_info "Make sure Ollama is running: brew services start ollama"
    all_good=false
  else
    print_info "Ollama: Running"
  fi

  # Check MCP server build
  if [ ! -d "$MCP_SERVER_DIR/dist" ]; then
    print_warning "MCP server not built, running build..."
    cd "$MCP_SERVER_DIR" && npm run build
  else
    print_info "MCP Server: Built"
  fi

  if [ "$all_good" = false ]; then
    print_error "Prerequisites not met. Please fix the issues above."
    exit 1
  fi

  print_status "✅ All prerequisites met"
}

# Function to start MCP server
start_mcp_server() {
  print_status "Starting DevStream MCP Server..."

  cd "$MCP_SERVER_DIR"

  # Check if already running
  if lsof -i :9090 >/dev/null 2>&1; then
    print_warning "Metrics server already running on port 9090"
    print_info "Skipping server startup"
    return 0
  fi

  # Start production server in background
  nohup node start-production.js > "$PROJECT_ROOT/devstream-server.log" 2>&1 &
  local server_pid=$!

  print_info "Server PID: $server_pid"
  print_info "Log file: $PROJECT_ROOT/devstream-server.log"

  # Wait for server to start
  print_status "Waiting for server to start..."
  local max_attempts=30
  local attempt=0

  while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:9090/health >/dev/null 2>&1; then
      print_status "✅ MCP Server started successfully"
      print_info "Metrics: http://localhost:9090/metrics"
      print_info "Health: http://localhost:9090/health"
      return 0
    fi
    sleep 1
    attempt=$((attempt + 1))
  done

  print_error "Server failed to start within 30 seconds"
  print_info "Check logs: tail -f $PROJECT_ROOT/devstream-server.log"
  exit 1
}

# Function to setup Claude Code MCP for DevStream
setup_claude_mcp() {
  print_status "Setting up Claude Code MCP integration..."

  # Remove existing devstream MCP if present
  claude mcp remove devstream -s local 2>/dev/null || true

  # Add DevStream MCP server
  print_info "Adding DevStream MCP server..."
  cd "$MCP_SERVER_DIR"

  # Note: The actual MCP integration will be configured via Claude Code settings
  # This is a placeholder for future MCP server registration
  print_warning "MCP server registration via CLI not yet implemented"
  print_info "To integrate with Claude Code:"
  print_info "  1. Open Claude Code settings"
  print_info "  2. Navigate to MCP Servers section"
  print_info "  3. Add DevStream server: $MCP_SERVER_DIR/dist/index.js"

  # Setup Context7
  print_status "Setting up Context7..."
  claude mcp remove context7 -s local 2>/dev/null || true

  # Add Context7 with proper wrapper script
  if [ -f "$PROJECT_ROOT/context7-wrapper.sh" ]; then
    claude mcp add context7 "$PROJECT_ROOT/context7-wrapper.sh" || {
      print_warning "Could not add Context7 MCP server"
    }
    print_status "✅ Context7 added to Claude Code MCP configuration"
  else
    print_warning "Context7 wrapper script not found"
  fi
}

# Function to show server status
show_server_status() {
  print_status "📊 DevStream Server Status"
  print_status "============================="
  echo ""

  # Check health
  if curl -s http://localhost:9090/health >/dev/null 2>&1; then
    local health_json=$(curl -s http://localhost:9090/health)
    print_status "✅ Server is healthy"
    print_info "   Uptime: $(echo $health_json | grep -o '"uptime":[0-9.]*' | cut -d: -f2)s"
  else
    print_error "❌ Server is not responding"
  fi

  # Show endpoints
  echo ""
  print_info "📈 Monitoring Endpoints:"
  print_info "   Health:     http://localhost:9090/health"
  print_info "   Metrics:    http://localhost:9090/metrics"
  print_info "   Quality:    http://localhost:9090/quality"
  print_info "   Errors:     http://localhost:9090/errors"

  echo ""
  print_info "📝 Server Log:"
  print_info "   tail -f $PROJECT_ROOT/devstream-server.log"

  echo ""
}

# Function to start Claude Code with DevStream
start_claude_with_devstream() {
  print_status "🚀 Starting Claude Code with DevStream..."
  print_info ""
  print_info "DevStream Features:"
  print_info "  - Semantic memory with hybrid search (Vector + FTS5)"
  print_info "  - Task management with AI-powered planning"
  print_info "  - Context7 integration for up-to-date docs"
  print_info "  - Real-time monitoring and metrics"
  print_info ""
  print_info "Context7 Usage:"
  print_info "  - Add 'use context7' to your prompts"
  print_info "  - Context7 will provide up-to-date documentation"
  if [ -n "$CONTEXT7_SESSION_ID" ]; then
    print_info "  - Session ID: $CONTEXT7_SESSION_ID"
  fi
  print_info ""
  print_status "Starting Claude Code..."

  # Start Claude Code in the project directory
  cd "$PROJECT_ROOT"
  claude
}

# Function to stop server
stop_server() {
  print_status "Stopping DevStream MCP Server..."

  # Find and kill the server process
  local server_pid=$(lsof -t -i:9090 2>/dev/null)

  if [ -n "$server_pid" ]; then
    kill $server_pid
    print_status "✅ Server stopped (PID: $server_pid)"
  else
    print_info "No server running on port 9090"
  fi
}

# Main function
main() {
  echo ""
  print_status "🚀 DevStream Production Launcher"
  print_status "====================================="
  echo ""

  # Parse command line arguments
  case "${1:-start}" in
    start)
      # Check prerequisites
      check_prerequisites

      # Initialize Context7
      initialize_context7

      # Verify Context7 availability
      verify_context7

      # Start MCP server
      start_mcp_server

      # Show server status
      show_server_status

      # Setup Claude MCP
      setup_claude_mcp

      echo ""
      print_status "🎉 DevStream is ready!"
      echo ""

      # Start Claude Code
      start_claude_with_devstream
      ;;

    stop)
      stop_server
      ;;

    status)
      show_server_status
      ;;

    restart)
      stop_server
      sleep 2
      main start
      ;;

    *)
      print_error "Unknown command: $1"
      print_info "Usage: $0 {start|stop|status|restart}"
      exit 1
      ;;
  esac
}

# Run main function
main "$@"