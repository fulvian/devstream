#!/bin/bash

# DevStream Production Launcher v2.0
# Starts DevStream MCP Server with Agent Auto-Delegation System
# Integrated: Context7, Agent Routing, Memory System, Monitoring

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
MCP_SERVER_DIR="$PROJECT_ROOT/mcp-devstream-server"
VENV_DIR="$PROJECT_ROOT/.devstream"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
CYAN='\033[0;36m'
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

print_feature() {
  echo -e "${CYAN}[FEATURE]${NC} $1"
}

# Function to check and setup Python virtual environment
check_python_venv() {
  print_status "Checking Python virtual environment..."

  # Check if venv exists
  if [ ! -d "$VENV_DIR" ]; then
    print_warning "Virtual environment not found, creating..."
    python3.11 -m venv "$VENV_DIR"
    print_status "✅ Virtual environment created"
  fi

  # Verify Python version
  local python_version=$("$VENV_DIR/bin/python" --version 2>&1 | cut -d' ' -f2)
  print_info "Python: $python_version"

  # Check critical dependencies
  print_status "Checking hook dependencies..."
  if ! "$VENV_DIR/bin/python" -m pip list | grep -q "cchooks"; then
    print_warning "Installing hook dependencies..."
    "$VENV_DIR/bin/pip" install -q cchooks>=0.1.4 aiohttp>=3.8.0 structlog>=23.0.0 python-dotenv>=1.0.0
    print_status "✅ Hook dependencies installed"
  else
    print_info "Hook dependencies: OK"
  fi
}

# Function to verify Agent Auto-Delegation System
verify_agent_delegation() {
  print_status "Verifying Agent Auto-Delegation System..."

  # Check if agent modules exist
  if [ ! -f "$PROJECT_ROOT/.claude/hooks/devstream/agents/pattern_matcher.py" ]; then
    print_error "Pattern matcher not found"
    return 1
  fi

  if [ ! -f "$PROJECT_ROOT/.claude/hooks/devstream/agents/agent_router.py" ]; then
    print_error "Agent router not found"
    return 1
  fi

  # Test module import
  local import_test=$("$VENV_DIR/bin/python" -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/.claude/hooks/devstream')
try:
    from agents.pattern_matcher import PatternMatcher
    from agents.agent_router import AgentRouter
    print('OK')
except Exception as e:
    print(f'ERROR: {e}')
" 2>&1)

  if [ "$import_test" = "OK" ]; then
    print_status "✅ Agent Auto-Delegation System verified"
    return 0
  else
    print_error "Agent delegation import failed: $import_test"
    return 1
  fi
}

# Function to load DevStream configuration
load_devstream_config() {
  print_status "Loading DevStream configuration..."

  # Load .env.devstream
  if [ -f "$PROJECT_ROOT/.env.devstream" ]; then
    export $(cat "$PROJECT_ROOT/.env.devstream" | grep -v '^#' | grep -v '^$' | xargs)
    print_info ".env.devstream loaded"
  else
    print_warning ".env.devstream not found"
  fi

  # Verify Agent Auto-Delegation is enabled
  if [ "${DEVSTREAM_AGENT_AUTO_DELEGATION_ENABLED:-true}" = "true" ]; then
    print_feature "✅ Agent Auto-Delegation: ENABLED"
    print_info "   Confidence threshold: ${DEVSTREAM_AGENT_AUTO_DELEGATION_CONFIDENCE_THRESHOLD:-0.85}"
    print_info "   Auto-approve threshold: ${DEVSTREAM_AGENT_AUTO_DELEGATION_AUTO_APPROVE_THRESHOLD:-0.95}"
  else
    print_warning "⚠️  Agent Auto-Delegation: DISABLED"
  fi

  # Verify Memory System is enabled
  if [ "${DEVSTREAM_MEMORY_ENABLED:-true}" = "true" ]; then
    print_feature "✅ Semantic Memory: ENABLED"
  else
    print_warning "⚠️  Semantic Memory: DISABLED"
  fi

  # Verify Context7 is enabled
  if [ "${DEVSTREAM_CONTEXT7_ENABLED:-true}" = "true" ]; then
    print_feature "✅ Context7 Integration: ENABLED"
  else
    print_warning "⚠️  Context7 Integration: DISABLED"
  fi
}

# Function to initialize Context7
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
    print_status "✅ Context7 configuration created"
  fi

  # Set Context7 environment variables
  export CONTEXT7_ENABLED=true
  export CONTEXT7_SESSION_ID=$(cat "$PROJECT_ROOT/.config/context7.json" | grep session_id | cut -d'"' -f4)

  if [ -n "${CONTEXT7_API_KEY}" ]; then
    print_status "✅ Context7 initialized (Session: $CONTEXT7_SESSION_ID)"
  else
    print_warning "⚠️  CONTEXT7_API_KEY not set in environment"
  fi
}

# Function to check Context7 availability
verify_context7() {
  print_status "Verifying Context7 MCP availability..."

  if command -v npx >/dev/null 2>&1; then
    print_status "✅ npx available"
    # Silently check Context7 package (will install on first use if needed)
    print_info "Context7 will auto-install on first use if needed"
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

  # Check Ollama (non-blocking)
  if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    print_warning "Ollama service not responding at http://localhost:11434"
    print_info "Start Ollama: brew services start ollama"
    print_info "Continuing without Ollama (embeddings will be disabled)"
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
    print_error "Critical prerequisites not met. Please fix the issues above."
    exit 1
  fi

  print_status "✅ All critical prerequisites met"
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

  # Start production server in background with memory optimization flags
  # Context7 best practice: Increase heap size and expose GC for long-running Node.js processes
  nohup node --max-old-space-size=8192 --expose-gc start-production.js > "$PROJECT_ROOT/devstream-server.log" 2>&1 &
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

# Function to setup Claude Code MCP configuration
setup_claude_mcp() {
  print_status "Configuring Claude Code MCP servers..."

  local config_file="$HOME/.claude/config.json"

  # Check if config.json exists
  if [ ! -f "$config_file" ]; then
    print_warning "Claude config.json not found, creating..."
    mkdir -p "$HOME/.claude"
    echo '{"mcpServers":{}}' > "$config_file"
  fi

  # Check if DevStream is already configured
  if grep -q '"devstream"' "$config_file" 2>/dev/null; then
    print_info "DevStream MCP already configured"
  else
    print_info "DevStream MCP configuration:"
    print_info "  Add to ~/.claude/config.json manually:"
    print_info '  "devstream": {'
    print_info '    "command": "node",'
    print_info "    \"args\": [\"$MCP_SERVER_DIR/dist/index.js\"],"
    print_info '    "env": {'
    print_info "      \"DEVSTREAM_DB_PATH\": \"$PROJECT_ROOT/data/devstream.db\""
    print_info '    }'
    print_info '  }'
  fi

  # Setup Context7 (non-blocking)
  print_status "Configuring Context7..."

  if [ -f "$PROJECT_ROOT/context7-wrapper.sh" ]; then
    if grep -q '"context7"' "$config_file" 2>/dev/null; then
      print_info "Context7 MCP already configured"
    else
      print_info "Context7 configuration:"
      print_info "  Add to ~/.claude/config.json manually:"
      print_info '  "context7": {'
      print_info '    "command": "bash",'
      print_info "    \"args\": [\"$PROJECT_ROOT/context7-wrapper.sh\"]"
      print_info '  }'
    fi
  else
    print_warning "Context7 wrapper script not found at $PROJECT_ROOT/context7-wrapper.sh"
  fi

  echo ""
  print_info "📖 MCP Configuration Help:"
  print_info "  1. Edit ~/.claude/config.json"
  print_info "  2. Add 'devstream' and 'context7' to mcpServers"
  print_info "  3. Restart Claude Code to activate"
  echo ""
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

# Function to show Agent Auto-Delegation System status
show_agent_status() {
  print_status "🤖 Agent Auto-Delegation System"
  print_status "================================="
  echo ""

  print_feature "Phase 3 Implementation Complete (100%)"
  echo ""

  print_info "Available Agents (17 total):"
  print_info "  Orchestrator:"
  print_info "    • @tech-lead (Default owner, task decomposition)"
  print_info ""
  print_info "  Domain Specialists (6):"
  print_info "    • @python-specialist (Python 3.11+, FastAPI, async)"
  print_info "    • @typescript-specialist (TypeScript, React, Next.js)"
  print_info "    • @rust-specialist (Ownership, memory safety)"
  print_info "    • @go-specialist (Goroutines, cloud-native)"
  print_info "    • @database-specialist (PostgreSQL, MySQL, SQLite)"
  print_info "    • @devops-specialist (Docker, Kubernetes, CI/CD)"
  print_info ""
  print_info "  Task Specialists (4):"
  print_info "    • @api-architect (API design, OpenAPI)"
  print_info "    • @performance-optimizer (Profiling, optimization)"
  print_info "    • @testing-specialist (TDD, coverage, E2E)"
  print_info "    • @documentation-specialist (Technical writing)"
  print_info ""
  print_info "  Quality Assurance (7):"
  print_info "    • @code-reviewer (MANDATORY pre-commit)"
  print_info "    • @security-auditor (OWASP, threat modeling)"
  print_info "    • @debugger (Root cause analysis)"
  print_info "    • @refactoring-specialist (Technical debt)"
  print_info "    • @integration-specialist (Third-party APIs)"
  print_info "    • @migration-specialist (Database, framework)"
  print_info ""

  if [ "${DEVSTREAM_AGENT_AUTO_DELEGATION_ENABLED:-true}" = "true" ]; then
    print_status "✅ Pattern-based routing ACTIVE (<10ms)"
    print_info "   Quality Gates: MANDATORY @code-reviewer pre-commit"
    print_info "   Auto-approve: confidence ≥${DEVSTREAM_AGENT_AUTO_DELEGATION_AUTO_APPROVE_THRESHOLD:-0.95}"
  else
    print_warning "⚠️  Agent Auto-Delegation DISABLED"
  fi

  echo ""
}

# Function to start Claude Code with DevStream
start_claude_with_devstream() {
  print_status "🚀 Starting Claude Code with DevStream..."
  echo ""

  print_info "═══════════════════════════════════════════════"
  print_info "  DevStream v2.0 - Production Ready"
  print_info "═══════════════════════════════════════════════"
  echo ""

  print_feature "Core Features:"
  print_info "  ✅ Semantic Memory (Vector + FTS5 hybrid search)"
  print_info "  ✅ Agent Auto-Delegation (17 specialist agents)"
  print_info "  ✅ Context7 Integration (up-to-date docs)"
  print_info "  ✅ Task Management (AI-powered planning)"
  print_info "  ✅ Quality Gates (MANDATORY code review)"
  print_info "  ✅ Real-time Monitoring (metrics + health)"
  echo ""

  print_feature "New in v2.0:"
  print_info "  🆕 Pattern Matcher (<10ms agent routing)"
  print_info "  🆕 @tech-lead orchestration (default owner)"
  print_info "  🆕 Auto-approve for high-confidence tasks"
  print_info "  🆕 Delegation decision logging"
  echo ""

  print_info "Usage Tips:"
  print_info "  • Quality gate: ALL commits reviewed by @code-reviewer"
  print_info "  • Direct invocation: @python-specialist <task>"
  print_info "  • Complex features: @tech-lead <multi-stack task>"
  print_info "  • Context7: Automatic library detection + docs"
  echo ""

  print_status "Starting Claude Code..."
  echo ""

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
  print_status "🚀 DevStream Production Launcher v2.0"
  print_status "======================================="
  echo ""

  # Parse command line arguments
  case "${1:-start}" in
    start)
      # Check Python virtual environment
      check_python_venv

      # Load DevStream configuration
      load_devstream_config

      # Check prerequisites
      check_prerequisites

      # Verify Agent Auto-Delegation System
      if verify_agent_delegation; then
        print_status "✅ Agent Auto-Delegation System ready"
      else
        print_error "Agent Auto-Delegation verification failed"
        exit 1
      fi

      # Initialize Context7
      initialize_context7

      # Verify Context7 availability
      verify_context7

      # Start MCP server
      start_mcp_server

      # Show server status
      show_server_status

      # Show Agent status
      show_agent_status

      # Setup Claude MCP configuration
      setup_claude_mcp

      echo ""
      print_status "🎉 DevStream v2.0 is ready!"
      echo ""

      # Start Claude Code
      start_claude_with_devstream
      ;;

    stop)
      stop_server
      ;;

    status)
      load_devstream_config
      show_server_status
      show_agent_status
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
