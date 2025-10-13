#!/bin/bash

# DevStream Production Launcher v2.0
# Starts DevStream MCP Server with Agent Auto-Delegation System
# Integrated: Context7, Agent Routing, Memory System, Monitoring

set -euo pipefail

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

# Function to handle authentication switching
switch_auth_provider() {
  local provider="${1:-anthropic}"

  print_status "Switching authentication provider to: $provider"

  case "$provider" in
    "z.ai")
      # Validate z.ai API key
      if [ -z "${ZAI_API_KEY:-}" ]; then
        print_error "ZAI_API_KEY not configured in .env"
        print_error "Get your API key from: https://z.ai/manage-apikey/apikey-list"
        return 1
      fi

      # Set z.ai environment with CORRECT variable names per official docs
      # See: https://docs.z.ai/scenario-example/develop-tools/claude
      export ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic"
      export ANTHROPIC_AUTH_TOKEN="$ZAI_API_KEY"  # z.ai requires AUTH_TOKEN, not API_KEY

      # Configure Claude Code settings for GLM-4.6
      configure_claude_settings_for_zai

      print_status "✅ Switched to z.ai (GLM-4.6)"
      print_info "   Base URL: $ANTHROPIC_BASE_URL"
      print_info "   Auth Token: ${ZAI_API_KEY:0:10}..."
      print_info "   Model: GLM-4.6 (configured in settings.json)"
      ;;
    "anthropic"|"")
      # Reset to Anthropic Max Plan (OAuth-based authentication)
      # CRITICAL: Must unset ALL API env vars to preserve Max Plan subscription
      # See: https://docs.anthropic.com/en/api/client-sdks
      print_info "Resetting to Anthropic Max Plan (OAuth)..."

      unset ANTHROPIC_BASE_URL      # Remove z.ai override
      unset ANTHROPIC_API_KEY       # CRITICAL: Prevents Max Plan bypass
      unset ANTHROPIC_AUTH_TOKEN    # CRITICAL: Prevents Max Plan bypass

      # Reset Claude Code settings to default
      reset_claude_settings_to_default

      # Verify Claude.ai authentication (non-blocking)
      if command -v claude >/dev/null 2>&1; then
        if ! claude auth status 2>/dev/null | grep -q "Logged in"; then
          print_warning "Claude CLI not logged in"
          print_info "   If Claude Code login fails, run: claude login"
          print_info "   Visit: https://claude.ai/"
        else
          print_status "✅ Claude CLI authenticated"
          print_info "   Using Claude.ai subscription via OAuth login"
        fi
      else
        print_info "Claude CLI not found (authentication handled by Claude Code)"
      fi

      print_status "✅ Switched to Anthropic Max Plan (OAuth)"
      print_info "   Authentication: Claude Code OAuth login"
      ;;
    *)
      print_error "Unknown provider: $provider"
      print_info "Supported providers: anthropic, z.ai"
      return 1
      ;;
  esac
}

# Function to configure Claude Code settings for z.ai
configure_claude_settings_for_zai() {
  local settings_file="$HOME/.claude/settings.json"

  print_status "Configuring Claude Code settings for GLM-4.6..."

  # Backup existing settings
  if [ -f "$settings_file" ]; then
    cp "$settings_file" "$settings_file.backup-zai-$(date +%Y%m%d_%H%M%S)"
    print_info "✅ Backed up existing settings"
  fi

  # Use Python for robust JSON manipulation (best practice from Context7)
  "$VENV_DIR/bin/python" << EOF
import json
import os

settings_file = "$settings_file"

# Read existing settings or create new
existing_data = {}
if os.path.exists(settings_file):
    try:
        with open(settings_file, 'r') as f:
            existing_data = json.load(f)
    except (json.JSONDecodeError, IOError):
        print("Warning: Could not parse existing settings, creating new ones")

# Preserve hooks and mcpServers if they exist
preserved_data = {
    "hooks": existing_data.get("hooks", {}),
    "mcpServers": existing_data.get("mcpServers", {}),
    "alwaysThinkingEnabled": existing_data.get("alwaysThinkingEnabled", False)
}

# Create new configuration
new_config = {
    **preserved_data,
    "model": "glm-4.6",
    "env": {
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm-4.6",
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-4.6",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "glm-4.5-air"
    }
}

# Write new settings
with open(settings_file, 'w') as f:
    json.dump(new_config, f, indent=2)

print("✅ Claude Code settings updated successfully")
EOF

  if [ $? -eq 0 ]; then
    print_status "✅ Claude Code configured for GLM-4.6"
  else
    print_error "❌ Failed to configure Claude Code settings"
    return 1
  fi
}

# Function to reset Claude Code settings to default
reset_claude_settings_to_default() {
  local settings_file="$HOME/.claude/settings.json"

  print_status "Resetting Claude Code settings to default..."

  if [ -f "$settings_file" ]; then
    # Use Python for robust JSON manipulation
    "$VENV_DIR/bin/python" << EOF
import json
import os

settings_file = "$settings_file"

# Read existing settings
if os.path.exists(settings_file):
    try:
        with open(settings_file, 'r') as f:
            existing_data = json.load(f)
    except (json.JSONDecodeError, IOError):
        print("Warning: Could not parse existing settings")
        exit(1)

    # Preserve only hooks and mcpServers, remove model-specific config
    default_config = {
        "hooks": existing_data.get("hooks", {}),
        "mcpServers": existing_data.get("mcpServers", {}),
        "alwaysThinkingEnabled": existing_data.get("alwaysThinkingEnabled", False)
    }

    # Write default settings
    with open(settings_file, 'w') as f:
        json.dump(default_config, f, indent=2)

    print("✅ Claude Code settings reset to default")
else:
    print("No settings file found")
EOF
  fi
}

# Function to load LLM provider configuration
load_llm_provider() {
  local provider="${1:-anthropic}"

  print_status "Loading LLM Provider: $provider"

  # Export provider for downstream functions
  export DEVSTREAM_LLM_PROVIDER="$provider"

  # Load root .env first (single source of truth)
  if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
    export DEVSTREAM_ANTHROPIC_API_KEY_DEFAULT="${ANTHROPIC_API_KEY:-}"
    print_info "Root .env loaded"
  fi

  # Switch authentication provider after base env is available
  switch_auth_provider "$provider"

  # For non-anthropic providers, load additional config
  if [ "$provider" != "anthropic" ] && [ -f "$PROJECT_ROOT/.env.llm-providers" ]; then
    source "$PROJECT_ROOT/.env.llm-providers"
    print_info "Additional provider configuration loaded"
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

  # Extract session ID with safe pipeline (file must exist at this point)
  if [ -f "$PROJECT_ROOT/.config/context7.json" ]; then
    export CONTEXT7_SESSION_ID=$(cat "$PROJECT_ROOT/.config/context7.json" | grep session_id | cut -d'"' -f4)
  else
    export CONTEXT7_SESSION_ID="devstream-default"
  fi

  if [ -n "${CONTEXT7_API_KEY:-}" ]; then
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

  # Check jq (required for JSON manipulation)
  if ! command -v jq >/dev/null 2>&1; then
    print_error "jq not found - required for Claude Code settings management"
    print_info "Install jq: brew install jq"
    all_good=false
  else
    print_info "jq: $(jq --version)"
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

  # NEW: Cleanup zombie MCP processes BEFORE starting server
  print_status "Running pre-launch zombie cleanup..."
  local zombie_count=$(pgrep -f "mcp-devstream-server/dist/index.js" 2>/dev/null | wc -l | tr -d ' ')

  if [ "$zombie_count" -gt 0 ]; then
    print_warning "Found $zombie_count existing MCP processes, cleaning up..."
    if "$VENV_DIR/bin/python" "$PROJECT_ROOT/.claude/hooks/devstream/monitoring/mcp_cleanup_hook.py"; then
      print_status "✅ Pre-launch cleanup complete"
      sleep 1  # Brief pause to ensure processes fully terminated
    else
      print_warning "⚠️  Cleanup had issues, but continuing..."
    fi
  fi

  # ============================================================================
  # Pre-Launch MCP Configuration Validation
  # ============================================================================

  print_status "Validating MCP configuration before launch..."

  # Extract DEVSTREAM_DB_PATH from .mcp.json
  if [ -f "$PROJECT_ROOT/.mcp.json" ]; then
    MCP_DB_PATH=$(grep "DEVSTREAM_DB_PATH" "$PROJECT_ROOT/.mcp.json" | sed 's/.*": "//;s/".*//')

    # Validate it's NOT the wrong path
    if [[ "$MCP_DB_PATH" == *"mcp-devstream-server/data/devstream.db"* ]]; then
      print_error "❌ CRITICAL: .mcp.json contains WRONG database path!"
      print_error "   Found: $MCP_DB_PATH"
      print_error "   Expected: /Users/fulvioventura/devstream/data/devstream.db"
      print_error ""
      print_error "This indicates Claude Code configuration cache issue."
      print_error "SOLUTION: Restart Claude Code application completely (Cmd+Q then relaunch)."
      print_error ""
      exit 1
    fi

    # Validate correct path exists
    if [ ! -f "$MCP_DB_PATH" ]; then
      print_error "❌ ERROR: Database file not found at: $MCP_DB_PATH"
      exit 1
    fi

    # Validate database size (correct DB should be ~500MB)
    DB_SIZE=$(stat -f%z "$MCP_DB_PATH" 2>/dev/null || stat -c%s "$MCP_DB_PATH" 2>/dev/null)
    if [ "$DB_SIZE" -lt 50000000 ]; then  # Less than 50MB is suspicious
      print_warning "⚠️  WARNING: Database size is only $(numfmt --to=iec $DB_SIZE 2>/dev/null || echo $DB_SIZE bytes)"
      print_warning "   Expected ~500MB for production database"
      print_warning "   Verify you're using the correct database path"
    fi

    print_status "✅ MCP configuration validated - Path: $MCP_DB_PATH ($(numfmt --to=iec $DB_SIZE 2>/dev/null || echo $DB_SIZE bytes))"
  else
    print_warning "⚠️  .mcp.json file not found - skipping configuration validation"
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

# Function to validate database path and configuration
validate_database_config() {
  print_status "Validating database configuration..."

  local db_path="$PROJECT_ROOT/data/devstream.db"
  local config_file="$HOME/.claude/config.json"
  local validation_passed=true

  # Check if database exists
  if [ ! -f "$db_path" ]; then
    print_error "Database not found: $db_path"
    validation_passed=false
  else
    print_info "Database found: $db_path"
  fi

  # Check database accessibility
  if [ "$validation_passed" = true ]; then
    local db_test=$("$VENV_DIR/bin/python" -c "
import sqlite3
import sys
try:
    db = sqlite3.connect('$db_path')
    cursor = db.execute('SELECT COUNT(*) FROM semantic_memory')
    count = cursor.fetchone()[0]
    print(f'OK:{count}')
    db.close()
except Exception as e:
    print(f'ERROR:{e}')
    sys.exit(1)
" 2>&1)

    if [[ "$db_test" == OK:* ]]; then
      local record_count=${db_test#*:}
      print_info "Database accessible: $record_count records"
    else
      print_error "Database access failed: ${db_test#ERROR:}"
      validation_passed=false
    fi
  fi

  # Check MCP configuration consistency
  if [ -f "$config_file" ]; then
    local mcp_db_path=$(grep -A 5 '"devstream"' "$config_file" | grep "DEVSTREAM_DB_PATH" | cut -d'"' -f4 2>/dev/null || echo "")

    if [ -n "$mcp_db_path" ]; then
      # Expand variables if present
      local expanded_path="${mcp_db_path//\${CLAUDE_PROJECT_DIR}/$PROJECT_ROOT}"
      expanded_path="${expanded_path//\$CLAUDE_PROJECT_DIR/$PROJECT_ROOT}"

      if [ "$expanded_path" != "$db_path" ]; then
        print_warning "MCP configuration mismatch:"
        print_warning "  Expected: $db_path"
        print_warning "  Configured: $expanded_path"
        print_info "  Run: ./start-devstream.sh restart to fix configuration"
      else
        print_info "MCP configuration: Path matches database location"
      fi
    else
      print_warning "MCP configuration not found in ~/.claude/config.json"
    fi
  fi

  # Check for wrong database paths (data.noindex)
  if [ -d "$PROJECT_ROOT/data.noindex" ] && [ -f "$PROJECT_ROOT/data.noindex/devstream.db" ]; then
    print_warning "Legacy database found at data.noindex/devstream.db"
    print_info "  Current database: data/devstream.db"
    print_info "  Consider archiving data.noindex/ directory"
  fi

  if [ "$validation_passed" = false ]; then
    print_error "Database validation failed"
    return 1
  fi

  print_status "✅ Database configuration validated"
  return 0
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

prepare_codex_runtime() {
  print_status "🛠️  Preparing Codex CLI integration"
  echo ""

  local codex_home="${DEVSTREAM_CODEX_HOME:-$PROJECT_ROOT/data/codex_home}"
  export DEVSTREAM_CODEX_HOME="$codex_home"
  mkdir -p "$codex_home/.claude/logs/devstream"

  local sample_path="${DEVSTREAM_CODEX_SAMPLE_OUTPUT_PATH:-$PROJECT_ROOT/data/codex_event_samples.jsonl}"
  export DEVSTREAM_CODEX_SAMPLE_OUTPUT_PATH="$sample_path"
  mkdir -p "$(dirname "$sample_path")"

  print_info "Codex home: $DEVSTREAM_CODEX_HOME"
  print_info "Sample payload log: $DEVSTREAM_CODEX_SAMPLE_OUTPUT_PATH"
  echo ""

  print_feature "Comandi utili"
  print_info "  • Singolo evento: DEVSTREAM_CODEX_HOME=\"$codex_home\" scripts/codex/relay.sh --event '{\"event_type\":\"session_start\",\"session_id\":\"demo\",\"cwd\":\".\"}'"
  print_info "  • Sequenza JSON: DEVSTREAM_CODEX_HOME=\"$codex_home\" scripts/codex/relay.sh --file events_demo.json"
  print_info "  • Stream STDIN: cat events_demo.jsonl | DEVSTREAM_CODEX_HOME=\"$codex_home\" scripts/codex/relay.sh"
  echo ""

  print_feature "Concorrenza Claude + Codex"
  print_info "  • I log Codex sono isolati in $codex_home/.claude/logs/devstream"
  print_info "  • Claude Code continua a usare ~/.claude/logs/devstream (nessun conflitto)"
  print_info "  • Assicurati che l'MCP server sia in esecuzione una sola volta (condiviso da entrambi)"
  echo ""

  print_status "✅ Codex relay pronto: esegui i comandi sopra in una shell dedicata"
}

# Function to start Claude Code with DevStream
start_claude_with_devstream() {
  print_status "🚀 Starting Claude Code with DevStream..."
  echo ""

  print_info "═══════════════════════════════════════════════"
  print_info "  DevStream v2.0 - Production Ready"
  print_info "═══════════════════════════════════════════════"
  echo ""

  # Show active LLM provider
  local active_provider="${DEVSTREAM_LLM_PROVIDER:-anthropic}"
  local base_url="${ANTHROPIC_BASE_URL:-https://api.anthropic.com}"

  print_feature "LLM Provider:"
  if [ "$active_provider" = "z.ai" ]; then
    print_info "  🤖 z.ai (GLM-4.6) - Zhipu AI flagship model"
    print_info "  🧠 Reasoning Mode: ENABLED (default)"
    print_info "  📏 Context Window: 200K tokens"
    print_info "  🛠️  Tool Calling: Native support"
  else
    print_info "  🤖 Anthropic Max Plan - Claude Sonnet 4.5"
    print_info "  🔐 Authentication: OAuth login"
    print_info "  📏 Context Window: 200K tokens"
  fi
  print_info "  📡 Base URL: $base_url"
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

  # Show switching information
  if [ "$active_provider" = "z.ai" ]; then
    print_info "🔄 To switch back to Claude Sonnet:"
    print_info "   ./start-devstream.sh restart anthropic"
    print_info "   # or ./start-devstream.sh (default)"
  else
    print_info "🔄 To switch to GLM-4.6:"
    print_info "   ./start-devstream.sh restart z.ai"
  fi
  echo ""

  print_status "Starting Claude Code..."
  echo ""

  # Start Claude Code in the project directory
  cd "$PROJECT_ROOT"

  # Check if z.ai provider is selected and use dedicated script
  if [ "$active_provider" = "z.ai" ]; then
    print_info "🔄 Launching Claude Code with GLM-4.6 via dedicated script..."
    # Use the dedicated z.ai script which handles all environment setup
    exec "$PROJECT_ROOT/scripts/start-claude-zai.sh"
  else
    # Default Claude Code launch for Anthropic provider
    claude
  fi
}

# Function to start background monitors
start_monitors() {
  print_status "Starting background monitoring daemons..."

  local monitor_log_dir="$PROJECT_ROOT/.claude/logs/devstream"
  mkdir -p "$monitor_log_dir"

  # 1. MCP Process Monitor (60s interval)
  print_info "Starting MCP Process Monitor..."
  nohup "$VENV_DIR/bin/python" "$PROJECT_ROOT/.claude/hooks/devstream/monitoring/mcp_process_monitor.py" \
    > "$monitor_log_dir/process_monitor_daemon.log" 2>&1 &
  echo $! > "$PROJECT_ROOT/.devstream/process_monitor.pid"
  print_status "✅ Process Monitor PID: $(cat $PROJECT_ROOT/.devstream/process_monitor.pid)"

  # 2. MCP Health Check (30s interval)
  print_info "Starting MCP Health Check..."
  nohup "$VENV_DIR/bin/python" "$PROJECT_ROOT/.claude/hooks/devstream/monitoring/mcp_health_check.py" \
    --interval 30 --timeout 10 \
    > "$monitor_log_dir/health_check_daemon.log" 2>&1 &
  echo $! > "$PROJECT_ROOT/.devstream/health_check.pid"
  print_status "✅ Health Check PID: $(cat $PROJECT_ROOT/.devstream/health_check.pid)"

  # 3. Database Update Monitor (60s interval, 10min threshold)
  print_info "Starting Database Update Monitor..."
  nohup "$VENV_DIR/bin/python" "$PROJECT_ROOT/.claude/hooks/devstream/monitoring/database_update_monitor.py" \
    --interval 60 --threshold 600 \
    > "$monitor_log_dir/db_monitor_daemon.log" 2>&1 &
  echo $! > "$PROJECT_ROOT/.devstream/db_monitor.pid"
  print_status "✅ Database Monitor PID: $(cat $PROJECT_ROOT/.devstream/db_monitor.pid)"

  # 4. Embedding Coverage Monitor (60s interval, 95% threshold)
  print_info "Starting Embedding Coverage Monitor..."
  nohup "$VENV_DIR/bin/python" "$PROJECT_ROOT/.claude/hooks/devstream/monitoring/embedding_coverage_monitor.py" \
    --interval 60 --threshold 95.0 \
    > "$monitor_log_dir/embedding_coverage_daemon.log" 2>&1 &
  echo $! > "$PROJECT_ROOT/.devstream/embedding_coverage.pid"
  print_status "✅ Embedding Coverage PID: $(cat $PROJECT_ROOT/.devstream/embedding_coverage.pid)"

  sleep 1  # Brief pause to ensure monitors start

  print_status "✅ All monitoring daemons started"
  print_info "Monitor logs: $monitor_log_dir/*_daemon.log"
}

# Function to stop monitors
stop_monitors() {
  print_status "Stopping monitoring daemons..."

  local stopped_count=0

  # Stop Process Monitor
  if [ -f "$PROJECT_ROOT/.devstream/process_monitor.pid" ]; then
    local pid=$(cat "$PROJECT_ROOT/.devstream/process_monitor.pid")
    if kill "$pid" 2>/dev/null; then
      print_info "Process Monitor stopped (PID: $pid)"
      stopped_count=$((stopped_count + 1))
    fi
    rm -f "$PROJECT_ROOT/.devstream/process_monitor.pid"
  fi

  # Stop Health Check
  if [ -f "$PROJECT_ROOT/.devstream/health_check.pid" ]; then
    local pid=$(cat "$PROJECT_ROOT/.devstream/health_check.pid")
    if kill "$pid" 2>/dev/null; then
      print_info "Health Check stopped (PID: $pid)"
      stopped_count=$((stopped_count + 1))
    fi
    rm -f "$PROJECT_ROOT/.devstream/health_check.pid"
  fi

  # Stop Database Monitor
  if [ -f "$PROJECT_ROOT/.devstream/db_monitor.pid" ]; then
    local pid=$(cat "$PROJECT_ROOT/.devstream/db_monitor.pid")
    if kill "$pid" 2>/dev/null; then
      print_info "Database Monitor stopped (PID: $pid)"
      stopped_count=$((stopped_count + 1))
    fi
    rm -f "$PROJECT_ROOT/.devstream/db_monitor.pid"
  fi

  if [ $stopped_count -gt 0 ]; then
    print_status "✅ Stopped $stopped_count monitoring daemon(s)"
  else
    print_info "No monitoring daemons were running"
  fi
}

# Function to check monitor status
check_monitor_status() {
  print_status "📊 Monitoring Daemon Status"
  print_status "=============================="
  echo ""

  local monitors_running=0

  # Check Process Monitor
  if [ -f "$PROJECT_ROOT/.devstream/process_monitor.pid" ]; then
    local pid=$(cat "$PROJECT_ROOT/.devstream/process_monitor.pid")
    if ps -p "$pid" > /dev/null 2>&1; then
      print_status "✅ Process Monitor: Running (PID: $pid)"
      monitors_running=$((monitors_running + 1))
    else
      print_warning "⚠️  Process Monitor: PID file exists but process not running"
      rm -f "$PROJECT_ROOT/.devstream/process_monitor.pid"
    fi
  else
    print_info "❌ Process Monitor: Not running"
  fi

  # Check Health Check
  if [ -f "$PROJECT_ROOT/.devstream/health_check.pid" ]; then
    local pid=$(cat "$PROJECT_ROOT/.devstream/health_check.pid")
    if ps -p "$pid" > /dev/null 2>&1; then
      print_status "✅ Health Check: Running (PID: $pid)"
      monitors_running=$((monitors_running + 1))
    else
      print_warning "⚠️  Health Check: PID file exists but process not running"
      rm -f "$PROJECT_ROOT/.devstream/health_check.pid"
    fi
  else
    print_info "❌ Health Check: Not running"
  fi

  # Check Database Monitor
  if [ -f "$PROJECT_ROOT/.devstream/db_monitor.pid" ]; then
    local pid=$(cat "$PROJECT_ROOT/.devstream/db_monitor.pid")
    if ps -p "$pid" > /dev/null 2>&1; then
      print_status "✅ Database Monitor: Running (PID: $pid)"
      monitors_running=$((monitors_running + 1))
    else
      print_warning "⚠️  Database Monitor: PID file exists but process not running"
      rm -f "$PROJECT_ROOT/.devstream/db_monitor.pid"
    fi
  else
    print_info "❌ Database Monitor: Not running"
  fi

  echo ""
  if [ $monitors_running -eq 3 ]; then
    print_status "✅ All 3 monitoring daemons operational"
  elif [ $monitors_running -gt 0 ]; then
    print_warning "⚠️  Only $monitors_running/3 monitors running"
  else
    print_info "No monitoring daemons running (start with: ./start-devstream.sh start)"
  fi

  echo ""
  print_info "Monitor Logs:"
  print_info "  tail -f ~/.claude/logs/devstream/process_monitor_daemon.log"
  print_info "  tail -f ~/.claude/logs/devstream/health_check_daemon.log"
  print_info "  tail -f ~/.claude/logs/devstream/db_monitor_daemon.log"
  echo ""
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

  # Also stop monitoring daemons
  stop_monitors
}

# Main function
main() {
  echo ""
  print_status "🚀 DevStream Production Launcher v2.0"
  print_status "======================================="
  echo ""

  # Parse command line arguments
  local command="${1:-start}"
  local provider="${2:-anthropic}"

  case "$command" in
    start)
      # Load LLM provider configuration FIRST
      load_llm_provider "$provider"

      # Check Python virtual environment
      check_python_venv

      # Load DevStream configuration
      load_devstream_config

      # Check prerequisites
      check_prerequisites

      # Validate database configuration
      if validate_database_config; then
        print_status "✅ Database configuration validated"
      else
        print_error "Database validation failed"
        exit 1
      fi

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

      # Start monitoring daemons (NEW - Automatic monitoring)
      start_monitors

      # Show server status
      show_server_status

      # Show Agent status
      show_agent_status

      # Show monitoring status (NEW)
      check_monitor_status

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
      check_monitor_status
      ;;

    codex)
      load_llm_provider "$provider"
      check_python_venv
      load_devstream_config
      check_prerequisites
      start_mcp_server
      prepare_codex_runtime
      ;;

    restart)
      stop_server
      sleep 2
      main start "$provider"
      ;;

    *)
      print_error "Unknown command: $command"
      print_info "Usage: $0 {start|stop|status|restart} [provider]"
      print_info "       $0 codex [provider]"
      print_info ""
      print_info "Available providers:"
      print_info "  - anthropic (default, Anthropic Max Plan via OAuth)"
      print_info "  - z.ai (GLM-4.6 via z.ai API)"
      print_info ""
      print_info "Examples:"
      print_info "  $0 start           # Start with Anthropic Max Plan (OAuth)"
      print_info "  $0 start z.ai      # Start with z.ai provider (GLM-4.6)"
      exit 1
      ;;
  esac
}

# Run main function
main "$@"
