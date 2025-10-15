#!/bin/bash

# DevStream Production Launcher v2.0 - Direct DB Architecture
# Starts DevStream with Direct DB Architecture and Agent Auto-Delegation System
# Integrated: Context7, Agent Routing, Memory System, Direct Database

set -euo pipefail

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

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Use project root from environment if set (multi-project mode), otherwise use script directory
if [ -n "${DEVSTREAM_PROJECT_ROOT:-}" ]; then
  PROJECT_ROOT="$DEVSTREAM_PROJECT_ROOT"
  DEVSTREAM_SCRIPT_DIR="$SCRIPT_DIR"
  print_info "Multi-project mode: Using project directory $PROJECT_ROOT"
  print_info "DevStream installation: $DEVSTREAM_SCRIPT_DIR"
else
  PROJECT_ROOT="$SCRIPT_DIR"
  DEVSTREAM_SCRIPT_DIR="$SCRIPT_DIR"
  print_info "Single-project mode: Using DevStream directory $PROJECT_ROOT"
fi
# MCP server directory (kept for compatibility but not used in Direct DB mode)
MCP_SERVER_DIR="$DEVSTREAM_SCRIPT_DIR/mcp-devstream-server"
VENV_DIR="$DEVSTREAM_SCRIPT_DIR/.devstream"

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

  # Check critical dependencies (Context7 best practice: handle broken pipes)
  print_status "Checking hook dependencies..."
  if ! "$VENV_DIR/bin/python" -m pip list 2>/dev/null | grep -q "cchooks"; then
    print_warning "Installing hook dependencies..."
    # Context7 best practice: use proper error handling and pipe management
    if "$VENV_DIR/bin/pip" install -q cchooks>=0.1.4 aiohttp>=3.8.0 structlog>=23.0.0 python-dotenv>=1.0.0 2>/dev/null; then
      print_status "✅ Hook dependencies installed"
    else
      print_error "❌ Failed to install hook dependencies"
      return 1
    fi
  else
    print_info "Hook dependencies: OK"
  fi
}

# Function to verify Agent Auto-Delegation System
verify_agent_delegation() {
  print_status "Verifying Agent Auto-Delegation System..."

  # Check if agent modules exist
  if [ ! -f "$DEVSTREAM_SCRIPT_DIR/.claude/hooks/devstream/agents/pattern_matcher.py" ]; then
    print_error "Pattern matcher not found"
    return 1
  fi

  if [ ! -f "$DEVSTREAM_SCRIPT_DIR/.claude/hooks/devstream/agents/agent_router.py" ]; then
    print_error "Agent router not found"
    return 1
  fi

  # Test module import
  local import_test=$("$VENV_DIR/bin/python" -c "
import sys
sys.path.insert(0, '$DEVSTREAM_SCRIPT_DIR/.claude/hooks/devstream')
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

  # Load root .env first (single source of truth) - always from DevStream installation
  if [ -f "$DEVSTREAM_SCRIPT_DIR/.env" ]; then
    set -a
    source "$DEVSTREAM_SCRIPT_DIR/.env"
    set +a
    export DEVSTREAM_ANTHROPIC_API_KEY_DEFAULT="${ANTHROPIC_API_KEY:-}"
    print_info "Root .env loaded"
  fi

  # Switch authentication provider after base env is available
  switch_auth_provider "$provider"

  # For non-anthropic providers, load additional config
  if [ "$provider" != "anthropic" ] && [ -f "$DEVSTREAM_SCRIPT_DIR/.env.llm-providers" ]; then
    source "$DEVSTREAM_SCRIPT_DIR/.env.llm-providers"
    print_info "Additional provider configuration loaded"
  fi
}

# Function to load DevStream configuration
load_devstream_config() {
  print_status "Loading DevStream configuration..."

  # Load .env.devstream - always from DevStream installation
  if [ -f "$DEVSTREAM_SCRIPT_DIR/.env.devstream" ]; then
    export $(cat "$DEVSTREAM_SCRIPT_DIR/.env.devstream" | grep -v '^#' | grep -v '^$' | xargs)
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

    # Show Direct Client Hybrid Architecture status
    local direct_mode="${DEVSTREAM_CONTEXT7_DIRECT_ENABLED:-false}"
    local fallback="${DEVSTREAM_CONTEXT7_MCP_FALLBACK:-true}"

    if [ "$direct_mode" = "true" ]; then
      print_info "  🚀 Direct Client: ENABLED (bypass MCP for performance)"
    elif [ "$direct_mode" = "rollout" ]; then
      print_info "  🔄 Direct Client: ROLLOUT mode (10% gradual rollout)"
    else
      print_info "  📡 MCP Mode: ENABLED (traditional MCP server)"
    fi

    if [ "$fallback" = "true" ] && [ "$direct_mode" != "false" ]; then
      print_info "  🛡️  MCP Fallback: ENABLED (graceful degradation)"
    fi
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

  # Check database - use project directory for multi-project mode with Direct DB architecture
  local db_path=""
  if [ -n "${DEVSTREAM_PROJECT_ROOT:-}" ]; then
    db_path="$PROJECT_ROOT/data/devstream.db"
    print_info "Direct DB: Using project database at $db_path"
  else
    db_path="$DEVSTREAM_SCRIPT_DIR/data/devstream.db"
    print_info "Direct DB: Using DevStream database at $db_path"
  fi

  if [ ! -f "$db_path" ]; then
    print_error "Database not found: $db_path"
    all_good=false
  else
    print_info "Database: Found at $db_path"

    # Test Direct DB access
    local db_test=$("$VENV_DIR/bin/python" -c "
import sqlite3
import sys

db_path = r'$db_path'

def table_counts(connection):
    tables = [row[0] for row in connection.execute(
        \"SELECT name FROM sqlite_master WHERE type='table' AND name IN ('memory', 'semantic_memory')\"
    )]
    if not tables:
        return []
    counts = []
    for table_name in sorted(set(tables)):
        query = \"SELECT COUNT(*) FROM {}\".format(table_name)
        count = connection.execute(query).fetchone()[0]
        counts.append('{}={}'.format(table_name, count))
    return counts

try:
    conn = sqlite3.connect(db_path)
    stats = table_counts(conn)
    conn.close()
    if not stats:
        print('ERROR:No memory tables found. Run make db-init to initialize the schema.')
        sys.exit(1)
    print('OK:' + ','.join(stats))
except Exception as exc:
    print(f'ERROR:{exc}')
    sys.exit(1)
" 2>&1)

    if [[ "$db_test" == OK:* ]]; then
      local record_info=${db_test#OK:}
      print_info "Direct DB access: $record_info"
    else
      print_error "Direct DB access failed: ${db_test#ERROR:}"
      all_good=false
    fi
  fi

  # Check Ollama (non-blocking) - needed for embeddings in Direct DB
  if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    print_warning "Ollama service not responding at http://localhost:11434"
    print_info "Start Ollama: brew services start ollama"
    print_info "Embeddings will be disabled until Ollama is running"
  else
    print_info "Ollama: Running - embeddings available"
  fi

  if [ "$all_good" = false ]; then
    print_error "Critical prerequisites not met. Please fix the issues above."
    exit 1
  fi

  print_status "✅ All critical prerequisites met"
}

# Function to check Direct DB Architecture (NEW)
check_direct_db_architecture() {
  print_status "Checking Direct DB Architecture..."

  # Check if feature flag is enabled
  local direct_db_enabled=false
  if [ -f "$DEVSTREAM_SCRIPT_DIR/.env.devstream" ]; then
    if grep -q "DEVSTREAM_FEATURE_DIRECT_DB_ENABLED=true" "$DEVSTREAM_SCRIPT_DIR/.env.devstream"; then
      direct_db_enabled=true
    fi
  fi

  if [ "$direct_db_enabled" = true ]; then
    print_feature "✅ Direct DB Architecture: ENABLED"
    print_info "   Using SQLite direct connections via Python hooks"
    print_info "   MCP server is NOT required for core functionality"
    return 0
  else
    print_feature "⚠️  Direct DB Architecture: DISABLED (legacy mode)"
    print_info "   MCP server will be started for compatibility"
    return 1
  fi
}

# Function to initialize Direct DB Architecture with automatic schema management
initialize_direct_db() {
  print_status "Initializing Direct DB Architecture..."

  # Verify Direct DB is enabled
  if ! check_direct_db_architecture; then
    print_error "❌ Direct DB Architecture is disabled"
    print_error "   Enable it by setting DEVSTREAM_FEATURE_DIRECT_DB_ENABLED=true"
    exit 1
  fi

  # Set environment variables for Direct DB
  if [ -n "${DEVSTREAM_PROJECT_ROOT:-}" ]; then
    export DEVSTREAM_DB_PATH="$PROJECT_ROOT/data/devstream.db"
    export DEVSTREAM_PROJECT_ROOT="$PROJECT_ROOT"
    print_info "Direct DB configured for project: $PROJECT_ROOT"
  else
    export DEVSTREAM_DB_PATH="$DEVSTREAM_SCRIPT_DIR/data/devstream.db"
    print_info "Direct DB configured for DevStream installation"
  fi

  # Initialize or validate database schema (Context7 best practice)
  initialize_database_schema

  # Initialize project templates for multi-project setup
  initialize_project_templates

  # Initialize project virtual environment for multi-project setup (Context7 best practice)
  initialize_project_venv

  # Initialize project CLAUDE.md for multi-project setup (Context7 + projen/chezmoi patterns)
  initialize_project_claude_md

  # Initialize project memory for multi-project setup (Context7 best practices)
  initialize_project_memory_bootstrap

  print_status "✅ Direct DB Architecture initialized"
}

# Function to initialize database schema with automatic validation and creation
# Context7-inspired: robust database initialization with schema validation
initialize_database_schema() {
  local db_path="$DEVSTREAM_DB_PATH"
  print_status "🔧 Initializing database schema..."

  # Ensure data directory exists
  mkdir -p "$(dirname "$db_path")"

  # Check if database exists
  if [ ! -f "$db_path" ]; then
    print_info "📁 Creating new database: $db_path"
    create_complete_database "$db_path"
  else
    print_info "📁 Database exists: $db_path"
    validate_and_upgrade_schema "$db_path"
  fi
}

# Function to create complete database with all required tables
# Context7 best practice: atomic database creation with full schema
create_complete_database() {
  local db_path="$1"

  print_info "🏗️  Creating complete database schema..."

  # Use Python for robust database creation (Context7 pattern)
  "$VENV_DIR/bin/python" << EOF
import sqlite3
import sys
from datetime import datetime

db_path = r'$db_path'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Enable WAL mode for better concurrency (Context7 best practice)
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=10000")

    # Core tables for DevStream
    tables_sql = [
        # Memory table for semantic storage
        """
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            content_type TEXT NOT NULL DEFAULT 'code',
            keywords TEXT,
            metadata TEXT,
            embedding_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (embedding_id) REFERENCES semantic_memory(id)
        )
        """,

        # Semantic memory table for vector embeddings
        """
        CREATE TABLE IF NOT EXISTS semantic_memory (
            id INTEGER PRIMARY KEY,
            embedding BLOB,
            model TEXT NOT NULL DEFAULT 'default',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """,

        # Full-text search configuration
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS fts_semantic_memory USING fts5(
            content,
            content_type,
            keywords,
            metadata,
            content=semantic_memory,
            content_rowid=id
        )
        """,

        # Tasks table for project management
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            task_type TEXT NOT NULL DEFAULT 'development',
            priority INTEGER DEFAULT 5,
            status TEXT DEFAULT 'pending',
            phase_name TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT,
            metadata TEXT,
            implementation_plan_id TEXT
        )
        """,

        # Sessions table for session tracking
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            tokens_used INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            started_at TEXT NOT NULL,
            ended_at TEXT,
            files_modified INTEGER DEFAULT 0,
            tasks_completed INTEGER DEFAULT 0,
            metadata TEXT
        )
        """,

        # Implementation plans table (v2.2.0+)
        """
        CREATE TABLE IF NOT EXISTS implementation_plans (
            id TEXT PRIMARY KEY,
            task_id TEXT,
            model_type TEXT NOT NULL,
            plan_title TEXT NOT NULL,
            plan_content TEXT,
            plan_status TEXT DEFAULT 'draft',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            metadata TEXT,
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        )
        """,

        # Checkpoints table for memory snapshots
        """
        CREATE TABLE IF NOT EXISTS checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checkpoint_name TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            memory_count INTEGER DEFAULT 0,
            task_count INTEGER DEFAULT 0,
            session_count INTEGER DEFAULT 0,
            metadata TEXT
        )
        """
    ]

    # Execute table creation
    for table_sql in tables_sql:
        cursor.execute(table_sql)

    # Create indexes for performance (Context7 best practice)
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_memory_content_type ON memory(content_type)",
        "CREATE INDEX IF NOT EXISTS idx_memory_created_at ON memory(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(task_type)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at)",
        "CREATE INDEX IF NOT EXISTS idx_implementation_plans_task_id ON implementation_plans(task_id)",
        "CREATE INDEX IF NOT EXISTS idx_implementation_plans_status ON implementation_plans(plan_status)",
        "CREATE INDEX IF NOT EXISTS idx_implementation_plans_model_type ON implementation_plans(model_type)"
    ]

    for index_sql in indexes_sql:
        cursor.execute(index_sql)

    # Insert initial checkpoint
    cursor.execute("""
        INSERT INTO checkpoints (checkpoint_name, metadata)
        VALUES ('initial_setup', 'Database created with complete DevStream schema')
    """)

    conn.commit()
    conn.close()

    print("✅ Database schema created successfully")

except Exception as e:
    print(f"❌ Error creating database: {e}")
    sys.exit(1)
EOF

  if [ $? -eq 0 ]; then
    print_status "✅ Complete database schema created"
  else
    print_error "❌ Database creation failed"
    exit 1
  fi
}

# Function to validate and upgrade existing database schema
# Context7 best practice: schema validation with automatic upgrades
validate_and_upgrade_schema() {
  local db_path="$1"

  print_info "🔍 Validating existing database schema..."

  # Use Python for schema validation (Context7 pattern)
  local validation_result=$("$VENV_DIR/bin/python" << EOF
import sqlite3
import sys
from datetime import datetime

db_path = r'$db_path'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get existing tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = set(row[0] for row in cursor.fetchall())

    # Required tables for DevStream v2.2.0
    required_tables = {
        'memory', 'semantic_memory', 'fts_semantic_memory',
        'tasks', 'sessions', 'implementation_plans', 'checkpoints'
    }

    missing_tables = required_tables - existing_tables
    extra_tables = existing_tables - required_tables

    upgrade_needed = False

    if missing_tables:
        print(f"🔧 Missing tables detected: {', '.join(sorted(missing_tables))}")
        upgrade_needed = True

        # Create missing tables
        tables_to_create = {
            'sessions': '''
                CREATE TABLE sessions (
                    id TEXT PRIMARY KEY,
                    tokens_used INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    files_modified INTEGER DEFAULT 0,
                    tasks_completed INTEGER DEFAULT 0,
                    metadata TEXT
                )
            ''',
            'implementation_plans': '''
                CREATE TABLE implementation_plans (
                    id TEXT PRIMARY KEY,
                    task_id TEXT,
                    model_type TEXT NOT NULL,
                    plan_title TEXT NOT NULL,
                    plan_content TEXT,
                    plan_status TEXT DEFAULT 'draft',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now')),
                    metadata TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks (id)
                )
            '''
        }

        for table_name, table_sql in tables_to_create.items():
            if table_name in missing_tables:
                cursor.execute(table_sql)
                print(f"✅ Created missing table: {table_name}")

        # Create missing indexes
        missing_indexes = []
        if 'sessions' in missing_tables:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at)")
            missing_indexes.extend(['idx_sessions_status', 'idx_sessions_started_at'])

        if 'implementation_plans' in missing_tables:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_implementation_plans_task_id ON implementation_plans(task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_implementation_plans_status ON implementation_plans(plan_status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_implementation_plans_model_type ON implementation_plans(model_type)")
            missing_indexes.extend(['idx_implementation_plans_task_id', 'idx_implementation_plans_status', 'idx_implementation_plans_model_type'])

        for index_name in missing_indexes:
            print(f"✅ Created missing index: {index_name}")

    if extra_tables:
        print(f"ℹ️  Extra tables found: {', '.join(sorted(extra_tables))}")

    # Verify critical tables
    critical_tables = ['memory', 'sessions', 'tasks']
    missing_critical = critical_tables - existing_tables

    if missing_critical:
        print(f"❌ CRITICAL: Missing core tables: {', '.join(sorted(missing_critical))}")
        print("💡 Consider running: python scripts/init-project-db.py")
        sys.exit(1)

    if upgrade_needed:
        conn.commit()
        print("✅ Database schema upgraded successfully")
    else:
        print("✅ Database schema is valid and up to date")

    conn.close()

except Exception as e:
    print(f"❌ Error validating database: {e}")
    sys.exit(1)
EOF
)

  if [ $? -eq 0 ]; then
    print_status "✅ Database schema validation completed"
  else
    print_error "❌ Database schema validation failed"
    exit 1
  fi
}

# Function to validate Direct DB configuration
validate_direct_db_config() {
  print_status "Validating Direct DB configuration..."

  local db_path=""
  local validation_passed=true

  # Determine database path based on mode
  if [ -n "${DEVSTREAM_PROJECT_ROOT:-}" ]; then
    db_path="$PROJECT_ROOT/data/devstream.db"
    print_info "Direct DB: Using project database at $db_path"
  else
    db_path="$DEVSTREAM_SCRIPT_DIR/data/devstream.db"
    print_info "Direct DB: Using DevStream database at $db_path"
  fi

  # Check if database exists
  if [ ! -f "$db_path" ]; then
    print_error "❌ Database not found: $db_path"
    validation_passed=false
  else
    print_info "✅ Database found: $db_path"
  fi

  # Test Direct DB accessibility
  if [ "$validation_passed" = true ]; then
    local db_test=$("$VENV_DIR/bin/python" -c "
import sqlite3
import sys

db_path = r'$db_path'

def table_counts(connection):
    tables = [row[0] for row in connection.execute(
        \"SELECT name FROM sqlite_master WHERE type='table' AND name IN ('memory', 'semantic_memory')\"
    )]
    if not tables:
        return []
    counts = []
    for table_name in sorted(set(tables)):
        query = \"SELECT COUNT(*) FROM {}\".format(table_name)
        count = connection.execute(query).fetchone()[0]
        counts.append('{}={}'.format(table_name, count))
    return counts

try:
    conn = sqlite3.connect(db_path)
    stats = table_counts(conn)
    conn.close()
    if not stats:
        print('ERROR:No memory tables found. Run make db-init to initialize the schema.')
        sys.exit(1)
    print('OK:' + ','.join(stats))
except Exception as exc:
    print(f'ERROR:{exc}')
    sys.exit(1)
" 2>&1)

    if [[ "$db_test" == OK:* ]]; then
      local stats=${db_test#OK:}
      print_info "✅ Direct DB accessible:"
      IFS=',' read -ra entries <<< "$stats"
      for entry in "${entries[@]}"; do
        local table_name=${entry%%=*}
        local row_count=${entry#*=}
        print_info "   ${table_name//_/ }: $row_count records"
      done
    else
      print_error "❌ Direct DB access failed: ${db_test#ERROR:}"
      validation_passed=false
    fi
  fi

  # Check for legacy database paths
  if [ -d "$PROJECT_ROOT/data.noindex" ] && [ -f "$PROJECT_ROOT/data.noindex/devstream.db" ]; then
    print_warning "⚠️  Legacy database found at data.noindex/devstream.db"
    print_info "   Current database: data/devstream.db"
    print_info "   Consider archiving data.noindex/ directory"
  fi

  if [ "$validation_passed" = false ]; then
    print_error "❌ Direct DB validation failed"
    return 1
  fi

  print_status "✅ Direct DB configuration validated"
  return 0
}

# Function to show Direct DB status
show_direct_db_status() {
  print_status "📊 Direct DB Architecture Status"
  print_status "================================="
  echo ""

  # Check if Direct DB is enabled
  if check_direct_db_architecture; then
    print_status "✅ Direct DB Architecture: ENABLED"
    print_info "   Using SQLite direct connections via Python hooks"
    print_info "   No MCP server required for core functionality"
  else
    print_error "❌ Direct DB Architecture: DISABLED"
    print_info "   Enable with: DEVSTREAM_FEATURE_DIRECT_DB_ENABLED=true"
  fi

  # Show database path
  local db_path=""
  if [ -n "${DEVSTREAM_PROJECT_ROOT:-}" ]; then
    db_path="$PROJECT_ROOT/data/devstream.db"
  else
    db_path="$DEVSTREAM_SCRIPT_DIR/data/devstream.db"
  fi

  echo ""
  print_info "🗄️  Database Information:"
  print_info "   Path: $db_path"

  if [ -f "$db_path" ]; then
    local db_size=$(stat -f%z "$db_path" 2>/dev/null || stat -c%s "$db_path" 2>/dev/null)
    print_info "   Size: $(numfmt --to=iec $db_size 2>/dev/null || echo $db_size bytes)"

    # Get record counts
    local db_status=$("$VENV_DIR/bin/python" -c "
import sqlite3

db_path = r'$db_path'

def table_counts(connection):
    tables = [row[0] for row in connection.execute(
        \"SELECT name FROM sqlite_master WHERE type='table' AND name IN ('memory', 'semantic_memory')\"
    )]
    if not tables:
        return []
    counts = []
    for table_name in sorted(set(tables)):
        query = \"SELECT COUNT(*) FROM {}\".format(table_name)
        count = connection.execute(query).fetchone()[0]
        counts.append('{}={}'.format(table_name, count))
    return counts

try:
    conn = sqlite3.connect(db_path)
    stats = table_counts(conn)
    conn.close()
    if stats:
        print(', '.join(stats))
    else:
        print('missing memory tables (run make db-init)')
except Exception as exc:
    print(f'error: {exc}')
" 2>/dev/null)

    if [[ "$db_status" != "" ]]; then
      print_info "   Records: $db_status"
    fi
  else
    print_error "   Database file not found"
  fi

  echo ""
  print_info "🔧 Architecture Details:"
  print_info "   Python Hooks: $(ls -1 "$DEVSTREAM_SCRIPT_DIR/.claude/hooks/devstream/memory/" 2>/dev/null | wc -l | tr -d ' ') files"
  print_info "   Agent System: 17 specialist agents available"
  print_info "   Context7: $( [ "${DEVSTREAM_CONTEXT7_ENABLED:-true}" = "true" ] && echo "ENABLED" || echo "DISABLED")"
  print_info "   Memory System: $( [ "${DEVSTREAM_MEMORY_ENABLED:-true}" = "true" ] && echo "ENABLED" || echo "DISABLED")"

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
    # Use the dedicated z.ai script from DevStream installation
    exec "$DEVSTREAM_SCRIPT_DIR/scripts/start-claude-zai.sh"
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

# Function to validate existing virtual environment (Context7 best practice)
# Context7 pattern: comprehensive validation before reusing existing environments
validate_existing_venv() {
  local venv_path="$1"
  local project_name="$2"

  # Debug info goes to stderr (Context7 best practice for clean output)
  print_info "🔍 Validating existing virtual environment: $venv_path" >&2

  # Check basic structure
  if [ ! -d "$venv_path" ]; then
    print_warning "⚠️  Virtual environment directory not found" >&2
    return 1
  fi

  if [ ! -f "$venv_path/bin/python" ]; then
    print_warning "⚠️  Python executable not found in venv" >&2
    return 1
  fi

  # Test Python functionality (Context7 best practice: capture only the result)
  local python_test=$("$venv_path/bin/python" -c "
import sys
try:
    import pip
    import setuptools
    print('OK')
except ImportError as e:
    print(f'MISSING_DEPS:{e}')
    sys.exit(1)
except Exception as e:
    print(f'ERROR:{e}')
    sys.exit(1)
" 2>/dev/null)

  if [ "$python_test" != "OK" ]; then
    if [[ "$python_test" == MISSING_DEPS:* ]]; then
      print_warning "⚠️  Virtual environment missing dependencies: ${python_test#MISSING_DEPS:}" >&2
    else
      print_warning "⚠️  Virtual environment validation failed: ${python_test#ERROR:}" >&2
    fi
    return 1
  fi

  # Get Python version info
  local python_version=$("$venv_path/bin/python" --version 2>&1)
  local python_major=$("$venv_path/bin/python" -c "import sys; print(sys.version_info.major)")
  local python_minor=$("$venv_path/bin/python" -c "import sys; print(sys.version_info.minor)")

  # Validate Python version (require 3.8+ for modern features)
  if [ "$python_major" -lt 3 ] || ([ "$python_major" -eq 3 ] && [ "$python_minor" -lt 8 ]); then
    print_warning "⚠️  Python version $python_version is too old (requires 3.8+)" >&2
    return 1
  fi

  print_info "✅ Virtual environment validated: $python_version" >&2
  return 0
}

# Function to detect existing virtual environments (Context7 best practice)
# Context7 pattern: smart detection of existing project environments
# Note: This function outputs ONLY the path to stdout for capture
detect_existing_venv() {
  local project_root="$1"
  local project_name="$2"

  # Debug info goes to stderr (Context7 best practice for output redirection)
  print_info "🔍 Detecting existing virtual environments..." >&2

  # Common venv locations to check (in order of preference)
  local venv_locations=(
    "$project_root/.venv"
    "$project_root/venv"
    "$project_root/env"
    "$project_root/.env"
  )

  # Check for common Python project files that indicate a Python project
  local python_indicators=(
    "$project_root/pyproject.toml"
    "$project_root/requirements.txt"
    "$project_root/setup.py"
    "$project_root/Pipfile"
    "$project_root/poetry.lock"
  )

  local is_python_project=false
  for indicator in "${python_indicators[@]}"; do
    if [ -f "$indicator" ]; then
      is_python_project=true
      print_info "📝 Detected Python project from: $(basename "$indicator")" >&2
      break
    fi
  done

  if [ "$is_python_project" = false ]; then
    print_info "ℹ️  No Python project indicators found, will create new venv" >&2
    return 1
  fi

  # Search for existing virtual environments
  for venv_path in "${venv_locations[@]}"; do
    if [ -d "$venv_path" ]; then
      print_info "📁 Found virtual environment: $venv_path" >&2

      if validate_existing_venv "$venv_path" "$project_name"; then
        print_status "✅ Using existing virtual environment: $venv_path" >&2
        # Only output the path to stdout (Context7 best practice)
        echo "$venv_path"
        return 0
      else
        print_warning "⚠️  Found virtual environment but validation failed: $venv_path" >&2
        print_info "💡 Will create new virtual environment" >&2
      fi
    fi
  done

  print_info "ℹ️  No valid existing virtual environment found" >&2
  return 1
}

# Function to validate virtual environment health (Context7 best practice)
# Context7 pattern: comprehensive health check before using environment
validate_venv_health() {
  local venv_path="$1"
  local venv_name="$2"

  print_info "🔍 Validating virtual environment: $venv_name ($venv_path)" >&2

  # Check directory exists
  if [ ! -d "$venv_path" ]; then
    print_warning "⚠️  Directory not found: $venv_path" >&2
    return 1
  fi

  # Check Python executable
  local python_exec="$venv_path/bin/python"
  if [ ! -f "$python_exec" ]; then
    print_warning "⚠️  Python executable not found: $python_exec" >&2
    return 1
  fi

  # Check Python version compatibility (require 3.11+ for DevStream)
  local python_version=$("$python_exec" --version 2>&1)
  local python_major=$("$python_exec" -c "import sys; print(sys.version_info.major)")
  local python_minor=$("$python_exec" -c "import sys; print(sys.version_info.minor)")

  if [ "$python_major" -lt 3 ] || ([ "$python_major" -eq 3 ] && [ "$python_minor" -lt 11 ]); then
    print_warning "⚠️  Python version $python_version is incompatible (requires 3.11+)" >&2
    return 1
  fi

  # Test basic Python functionality
  local python_test=$("$python_exec" -c "
import sys
try:
    import sqlite3
    import ast
    import json
    print('OK')
except ImportError as e:
    print(f'MISSING_MODULE:{e}')
    sys.exit(1)
except Exception as e:
    print(f'ERROR:{e}')
    sys.exit(1)
" 2>/dev/null)

  if [ "$python_test" != "OK" ]; then
    if [[ "$python_test" == MISSING_MODULE:* ]]; then
      print_warning "⚠️  Missing required modules: ${python_test#MISSING_MODULE:}" >&2
    else
      print_warning "⚠️  Python functionality test failed: ${python_test#ERROR:}" >&2
    fi
    return 1
  fi

  print_info "✅ Virtual environment validated: $python_version" >&2
  return 0
}

# Function to validate required modules in virtual environment (Context7 best practice)
# Context7 pattern: validate dependencies before proceeding
validate_required_modules() {
  local python_exec="$1"
  shift
  local required_modules=("$@")

  print_info "🔍 Validating required modules..." >&2

  for module in "${required_modules[@]}"; do
    local module_test=$("$python_exec" -c "
import sys
try:
    import $module
    print('OK')
except ImportError:
    print('MISSING')
    sys.exit(1)
" 2>/dev/null)

    if [ "$module_test" != "OK" ]; then
      print_warning "⚠️  Missing required module: $module" >&2
      return 1
    fi
  done

  print_info "✅ All required modules available" >&2
  return 0
}

# Function to validate DevStream framework virtual environment (Context7 best practice)
# Context7 pattern: comprehensive validation of framework dependencies
validate_devstream_venv() {
  local venv_path="$1"
  local project_name="$2"

  print_info "🔍 Validating DevStream framework environment..." >&2

  # Basic health check
  if ! validate_venv_health "$venv_path" "DevStream Framework"; then
    return 1
  fi

  # Validate DevStream-specific modules
  local python_exec="$venv_path/bin/python"
  local required_modules=("cchooks" "aiohttp" "structlog" "dotenv")

  if ! validate_required_modules "$python_exec" "${required_modules[@]}"; then
    return 1
  fi

  # Test Direct DB client availability
  local direct_client_test=$("$python_exec" -c "
import sys
sys.path.insert(0, '$DEVSTREAM_SCRIPT_DIR/.claude/hooks/devstream/utils')
try:
    from direct_client import get_direct_client
    print('OK')
except ImportError as e:
    print('MISSING_DIRECT_CLIENT')
    sys.exit(1)
except Exception as e:
    print(f'ERROR:{e}')
    sys.exit(1)
" 2>/dev/null)

  if [ "$direct_client_test" != "OK" ]; then
    print_warning "⚠️  Direct DB client not available in framework environment" >&2
    return 1
  fi

  print_info "✅ DevStream framework environment validated" >&2
  return 0
}

# Function to copy framework virtual environment to project (Context7 best practice)
# Context7 pattern: atomic copy with validation and rollback
copy_framework_venv() {
  local project_root="$1"
  local project_name="$2"
  local framework_venv="$3"
  local project_venv="$project_root/.devstream"

  print_info "📋 Copying DevStream framework virtual environment..."

  # Validate source environment
  if ! validate_devstream_venv "$framework_venv" "Framework"; then
    print_error "❌ Framework virtual environment validation failed"
    return 1
  fi

  # Remove existing incomplete venv
  if [ -d "$project_venv" ]; then
    print_info "🗑️  Removing existing incomplete .devstream directory..."
    rm -rf "$project_venv"
  fi

  # Perform atomic copy with error handling
  print_info "📁 Copying framework virtual environment..."
  if cp -R "$framework_venv" "$project_venv" 2>/dev/null; then
    print_status "✅ Framework virtual environment copied successfully"
  else
    print_error "❌ Failed to copy framework virtual environment"
    return 1
  fi

  # Validate copied environment
  if validate_devstream_venv "$project_venv" "Project Framework"; then
    print_status "✅ Copied framework environment validated"
    print_info "   Framework venv: $project_venv"
    print_info "   Source: $framework_venv"
  else
    print_error "❌ Copied framework environment validation failed"
    print_error "   Rolling back..."
    rm -rf "$project_venv"
    return 1
  fi

  return 0
}

# Function to ensure DevStream framework virtual environment (Context7 best practice)
# Context7 pattern: automatic setup with validation and recovery
ensure_devstream_venv() {
  local project_root="$1"
  local project_name="$2"
  local project_venv="$project_root/.devstream"
  local framework_venv="$VENV_DIR"

  print_status "🔧 Ensuring DevStream framework virtual environment..."

  # Check if project venv exists and is valid
  if [ -d "$project_venv" ]; then
    print_info "📁 Found existing .devstream directory"

    if validate_devstream_venv "$project_venv" "$project_name"; then
      print_status "✅ DevStream framework environment is valid"
      return 0
    else
      print_warning "⚠️  Existing .devstream environment is invalid, will recreate"
      print_info "🔄 Removing invalid environment..."
      rm -rf "$project_venv"
    fi
  else
    print_info "📁 No .devstream directory found"
  fi

  # Copy framework venv to project
  if copy_framework_venv "$project_root" "$project_name" "$framework_venv"; then
    print_status "✅ DevStream framework environment ready"
  else
    print_error "❌ Failed to setup DevStream framework environment"
    return 1
  fi

  return 0
}

# Function to initialize project virtual environment (Context7 best practice)
# Context7 pattern: smart reuse of existing environments with validation
initialize_project_venv() {
  # Only initialize project venv in multi-project mode
  if [ -z "${DEVSTREAM_PROJECT_ROOT:-}" ]; then
    return 0
  fi

  print_status "🐍 Initializing project virtual environment..."

  local project_name=$(basename "$PROJECT_ROOT")
  local project_venv_path="$PROJECT_ROOT/.venv"
  local framework_python="$VENV_DIR/bin/python"
  local existing_venv=""

  # Step 0: Ensure DevStream framework venv is available
  if ! ensure_devstream_venv "$PROJECT_ROOT" "$project_name"; then
    print_error "❌ Failed to ensure DevStream framework environment"
    return 1
  fi

  # Step 1: Try to detect and use existing virtual environment
  # Context7 best practice: redirect stderr to avoid capturing debug output
  existing_venv=$(detect_existing_venv "$PROJECT_ROOT" "$project_name" 2>/dev/null)

  if [ -n "$existing_venv" ] && [ "$existing_venv" != "$project_venv_path" ]; then
    # Found existing venv in different location, create symlink for consistency
    print_info "🔗 Linking existing venv: $existing_venv -> .venv"

    # Remove broken .venv if it exists
    if [ -L "$project_venv_path" ] && [ ! -d "$project_venv_path" ]; then
      rm "$project_venv_path"
    fi

    # Create symlink if .venv doesn't exist
    if [ ! -e "$project_venv_path" ]; then
      ln -s "$existing_venv" "$project_venv_path"
      print_info "✅ Created symlink: .venv -> $existing_venv"
    fi

    # Use existing venv
    project_venv_path="$existing_venv"

  elif [ -n "$existing_venv" ] && [ "$existing_venv" = "$project_venv_path" ]; then
    # Found valid existing venv at standard location
    print_info "✅ Using existing virtual environment: .venv"

  else
    # Step 2: Create new virtual environment if no valid existing one found
    print_info "📁 Creating new project virtual environment: .venv"

    # Create project venv using framework Python for consistency
    "$framework_python" -m venv "$project_venv_path"

    print_info "✅ Created new project virtual environment"

    # Upgrade pip in project venv
    "$project_venv_path/bin/pip" install --upgrade pip setuptools wheel > /dev/null 2>&1

    # Install basic development dependencies if no requirements files exist
    if [ ! -f "$PROJECT_ROOT/requirements.txt" ] && [ ! -f "$PROJECT_ROOT/pyproject.toml" ]; then
      print_info "📦 Installing basic development dependencies..."
      "$project_venv_path/bin/pip" install -q \
        black \
        ruff \
        mypy \
        pytest \
        pytest-cov \
        pre-commit > /dev/null 2>&1
      print_info "✅ Installed basic development dependencies"
    fi
  fi

  # Step 3: Create or update project-specific configuration
  local project_env_file="$PROJECT_ROOT/.env.project"
  local needs_config_update=false

  # Check if config needs updating
  if [ ! -f "$project_env_file" ]; then
    needs_config_update=true
  else
    # Check if project paths have changed
    if ! grep -q "DEVSTREAM_PROJECT_ROOT=$PROJECT_ROOT" "$project_env_file"; then
      needs_config_update=true
    fi
  fi

  if [ "$needs_config_update" = true ]; then
    cat > "$project_env_file" << EOF
# Project Environment Configuration - $project_name
# Context7-compliant project isolation

# Environment type
DEVSTREAM_PROJECT_ENV=development

# Virtual environment paths
DEVSTREAM_PROJECT_VENV_PATH=$project_venv_path
DEVSTREAM_PROJECT_VENV_PYTHON=$project_venv_path/bin/python
DEVSTREAM_PROJECT_VENV_PIP=$project_venv_path/bin/pip

# DevStream framework virtual environment paths
DEVSTREAM_PROJECT_DEVSTREAM_VENV_PATH=$PROJECT_ROOT/.devstream
DEVSTREAM_PROJECT_DEVSTREAM_VENV_PYTHON=$PROJECT_ROOT/.devstream/bin/python
DEVSTREAM_PROJECT_DEVSTREAM_VENV_PIP=$PROJECT_ROOT/.devstream/bin/pip

# Project paths
DEVSTREAM_PROJECT_ROOT=$PROJECT_ROOT
DEVSTREAM_PROJECT_NAME=$project_name

# Framework paths (for reference)
DEVSTREAM_FRAMEWORK_PATH=$DEVSTREAM_SCRIPT_DIR
DEVSTREAM_FRAMEWORK_VENV_PATH=$VENV_DIR

# Python configuration
PYTHONPATH=${PYTHONPATH:-}:$PROJECT_ROOT/src
EOF
    print_info "✅ Created/updated project configuration"
  fi

  # Step 4: Set environment variables for current session
  export DEVSTREAM_PROJECT_VENV_PATH="$project_venv_path"
  export DEVSTREAM_PROJECT_VENV_PYTHON="$project_venv_path/bin/python"
  export DEVSTREAM_PROJECT_VENV_PIP="$project_venv_path/bin/pip"
  export DEVSTREAM_PROJECT_DEVSTREAM_VENV_PATH="$PROJECT_ROOT/.devstream"
  export DEVSTREAM_PROJECT_DEVSTREAM_VENV_PYTHON="$PROJECT_ROOT/.devstream/bin/python"
  export DEVSTREAM_PROJECT_DEVSTREAM_VENV_PIP="$PROJECT_ROOT/.devstream/bin/pip"

  # Update PATH to prioritize project venv and framework venv
  export PATH="$project_venv_path/bin:$PROJECT_ROOT/.devstream/bin:$PATH"

  # Step 5: Load project environment if it exists
  if [ -f "$project_env_file" ]; then
    set -a
    source "$project_env_file"
    set +a
    print_info "✅ Loaded project environment configuration"
  fi

  # Final verification
  if [ ! -f "$project_venv_path/bin/python" ]; then
    print_error "❌ Project venv setup failed - Python executable not found"
    return 1
  fi

  if [ ! -f "$PROJECT_ROOT/.devstream/bin/python" ]; then
    print_error "❌ Framework venv setup failed - Python executable not found"
    return 1
  fi

  local python_version=$("$project_venv_path/bin/python" --version 2>&1 | cut -d' ' -f2)
  local framework_python_version=$("$PROJECT_ROOT/.devstream/bin/python" --version 2>&1 | cut -d' ' -f2)

  print_status "✅ Project virtual environment ready"
  print_info "🐍 Project venv: $project_venv_path (Python $python_version)"
  print_info "🔧 Framework venv: $PROJECT_ROOT/.devstream (Python $framework_python_version)"
  print_info "📁 Project config: .env.project"
}

# Function to initialize project templates for multi-project setup
# Context7 best practice: template inheritance for consistent project setup
initialize_project_templates() {
  # Only initialize templates in multi-project mode
  if [ -z "${DEVSTREAM_PROJECT_ROOT:-}" ]; then
    return 0
  fi

  print_status "📋 Initializing project templates..."

  local templates_source_dir="$DEVSTREAM_SCRIPT_DIR/templates"
  local templates_target_dir="$PROJECT_ROOT/templates"

  # Check if source templates exist
  if [ ! -d "$templates_source_dir" ]; then
    print_warning "⚠️  Templates source directory not found: $templates_source_dir"
    return 0
  fi

  # Create templates directory in project if it doesn't exist
  if [ ! -d "$templates_target_dir" ]; then
    print_info "📁 Creating project templates directory..."
    mkdir -p "$templates_target_dir"
  fi

  # Template files to copy
  local template_files=(
    "implementation-plan-glm46.md"
    "implementation-plan-sonnet45.md"
    "handoff-prompt-glm46.md"
  )

  local copied_count=0
  local updated_count=0

  for template_file in "${template_files[@]}"; do
    local source_file="$templates_source_dir/$template_file"
    local target_file="$templates_target_dir/$template_file"

    if [ -f "$source_file" ]; then
      if [ ! -f "$target_file" ]; then
        # Copy new template
        cp "$source_file" "$target_file"
        print_info "✅ Copied template: $template_file"
        copied_count=$((copied_count + 1))
      else
        # Check if template needs update (based on modification time)
        if [ "$source_file" -nt "$target_file" ]; then
          cp "$source_file" "$target_file"
          print_info "🔄 Updated template: $template_file"
          updated_count=$((updated_count + 1))
        else
          print_info "✅ Template current: $template_file"
        fi
      fi
    else
      print_warning "⚠️  Template not found: $template_file"
    fi
  done

  # Create .templates_version file for tracking
  local version_file="$PROJECT_ROOT/.templates_version"
  local current_version=$(date +%Y%m%d_%H%M%S)

  if [ ! -f "$version_file" ] || [ "$templates_source_dir" -nt "$version_file" ]; then
    echo "$current_version" > "$version_file"
    print_info "📝 Updated templates version: $current_version"
  fi

  # Summary
  local total_actions=$((copied_count + updated_count))
  if [ $total_actions -gt 0 ]; then
    print_status "✅ Project templates initialized ($copied_count new, $updated_count updated)"
    print_info "   Templates directory: $templates_target_dir"
    print_info "   Available templates: $(IFS=', '; echo "${template_files[*]}")"
  else
    print_info "✅ All project templates are up to date"
  fi
}

# Function to detect if CLAUDE.md was manually modified (Context7 best practice)
# Context7 pattern: intelligent detection of manual vs generated configurations
detect_manual_claude_md() {
  local project_claude_md="$1"
  local version_file="$2"

  # No file means not manually modified
  if [ ! -f "$project_claude_md" ]; then
    return 1
  fi

  # Check for manual modification indicators
  local manual_indicators=(
    "Manual configuration"
    "Custom rules"
    "User-defined"
    "Hand-crafted"
    "Personalized"
    "Customized for"
    "Manual setup"
  )

  # Check content for manual indicators
  for indicator in "${manual_indicators[@]}"; do
    if grep -qi "$indicator" "$project_claude_md"; then
      return 0  # Manual modification detected
    fi
  done

  # Check for DevStream generation markers
  if grep -q "Generated with DevStream" "$project_claude_md"; then
    return 1  # DevStream-generated
  fi

  # Check for template markers
  if grep -q "Template:" "$project_claude_md"; then
    return 1  # Template-generated
  fi

  # Check version tracking consistency
  if [ -f "$version_file" ]; then
    local version_timestamp=$(cat "$version_file")
    local file_timestamp=$(stat -f %m "$project_claude_md" 2>/dev/null || stat -c %Y "$project_claude_md" 2>/dev/null)
    local version_timestamp_sec=$(date -j -f "%Y%m%d_%H%M%S" "$version_timestamp" +%s 2>/dev/null || date -d "$version_timestamp" +%s 2>/dev/null)

    # If file was modified significantly after version tracking, likely manual
    if [ "$file_timestamp" -gt "$((version_timestamp_sec + 3600))" ]; then
      return 0  # File modified more than 1 hour after generation
    fi
  fi

  return 1  # No manual modification detected
}

# Function to backup existing CLAUDE.md (Context7 best practice)
# Context7 pattern: safe configuration management with automatic backups
backup_existing_claude_md() {
  local project_claude_md="$1"
  local backup_dir="$PROJECT_ROOT/.claude/backups"

  if [ ! -f "$project_claude_md" ]; then
    return 0
  fi

  # Create backup directory
  mkdir -p "$backup_dir"

  # Create timestamped backup
  local timestamp=$(date +%Y%m%d_%H%M%S)
  local backup_file="$backup_dir/CLAUDE.md.backup.$timestamp"

  cp "$project_claude_md" "$backup_file"
  print_info "📋 Backed up existing CLAUDE.md to: $(basename "$backup_file")"

  # Keep only last 5 backups
  ls -t "$backup_dir"/CLAUDE.md.backup.* 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true

  return 0
}

# Function to prompt user for CLAUDE.md update confirmation (Context7 best practice)
# Context7 pattern: user confirmation for destructive operations
prompt_claude_md_update() {
  local project_claude_md="$1"
  local action="$2"  # "create", "update", or "overwrite"

  case "$action" in
    "create")
      print_warning "⚠️  About to create new CLAUDE.md in project directory"
      print_info "   This will add DevStream project-specific rules to: $(basename "$project_claude_md")"
      ;;
    "update")
      print_warning "⚠️  About to update existing CLAUDE.md"
      print_info "   This will refresh DevStream project-specific rules in: $(basename "$project_claude_md")"
      ;;
    "overwrite")
      print_warning "⚠️  About to overwrite existing CLAUDE.md"
      print_info "   This will REPLACE the current file with DevStream-generated content"
      print_warning "   Any manual customizations will be lost!"
      ;;
  esac

  echo ""
  print_info "Options:"
  print_info "  [Y] Yes - Proceed with CLAUDE.md update"
  print_info "  [N] No  - Skip CLAUDE.md update (keep existing file)"
  print_info "  [B] Backup - Create backup before updating"
  echo ""

  # Check if we're in an interactive session
  if [ -t 0 ] && [ "${DEVSTREAM_AUTO_CONFIRM_CLAUDE_MD:-false}" != "true" ]; then
    while true; do
      read -p "Proceed with CLAUDE.md $action? [Y/N/B] " -n 1 -r reply
      echo ""
      case $reply in
        [Yy]* )
          return 0  # Proceed
          ;;
        [Nn]* )
          return 1  # Skip
          ;;
        [Bb]* )
          backup_existing_claude_md "$project_claude_md"
          return 0  # Proceed after backup
          ;;
        * )
          echo "Please choose Y, N, or B"
          ;;
      esac
    done
  else
    # Non-interactive mode, proceed with backup if manual modifications detected
    if detect_manual_claude_md "$project_claude_md" "$PROJECT_ROOT/.claude_version"; then
      backup_existing_claude_md "$project_claude_md"
      print_warning "⚠️  Non-interactive mode: Created backup of existing CLAUDE.md"
    fi
    return 0
  fi
}

# Function to initialize project CLAUDE.md for multi-project setup
# Context7 + projen/chezmoi patterns: intelligent template inheritance and adaptation
# Enhanced with safety mechanisms: user confirmation, backups, manual detection
initialize_project_claude_md() {
  # Only initialize CLAUDE.md in multi-project mode
  if [ -z "${DEVSTREAM_PROJECT_ROOT:-}" ]; then
    return 0
  fi

  print_status "📝 Initializing project CLAUDE.md..."

  local project_name=$(basename "$PROJECT_ROOT")
  local templates_source_dir="$DEVSTREAM_SCRIPT_DIR/templates/claude"
  local project_claude_md="$PROJECT_ROOT/CLAUDE.md"
  local framework_claude_md="$DEVSTREAM_SCRIPT_DIR/CLAUDE.md"
  local version_file="$PROJECT_ROOT/.claude_version"

  # Check if template processor exists
  local template_processor="$templates_source_dir/template_processor.py"
  local template_variables="$templates_source_dir/template_variables.py"

  if [ ! -f "$template_processor" ] || [ ! -f "$template_variables" ]; then
    print_warning "⚠️  CLAUDE.md template processor not found, using fallback method"
    initialize_project_claude_md_fallback
    return 0
  fi

  # Check if project CLAUDE.md needs update
  local needs_update=false
  local update_action="create"

  # Always update if project CLAUDE.md doesn't exist
  if [ ! -f "$project_claude_md" ]; then
    needs_update=true
    update_action="create"
    print_info "📝 Project CLAUDE.md not found, will create"
  else
    # Check if framework CLAUDE.md is newer
    if [ "$framework_claude_md" -nt "$project_claude_md" ]; then
      needs_update=true
      update_action="update"
      print_info "📝 Framework CLAUDE.md is newer, will update project"
    fi

    # Check if templates have been updated
    if [ ! -f "$version_file" ] || [ "$templates_source_dir" -nt "$version_file" ]; then
      needs_update=true
      update_action="update"
      print_info "📝 Templates updated, will regenerate project CLAUDE.md"
    fi
  fi

  if [ "$needs_update" = false ]; then
    print_info "✅ Project CLAUDE.md is up to date"
    return 0
  fi

  # Safety check: Detect manual modifications and prompt for confirmation
  if [ -f "$project_claude_md" ] && detect_manual_claude_md "$project_claude_md" "$version_file"; then
    print_warning "⚠️  Manual modifications detected in existing CLAUDE.md"
    update_action="overwrite"

    if ! prompt_claude_md_update "$project_claude_md" "$update_action"; then
      print_info "ℹ️  CLAUDE.md update skipped by user"
      return 0
    fi
  elif [ -f "$project_claude_md" ]; then
    # File exists but no manual modifications detected
    if ! prompt_claude_md_update "$project_claude_md" "$update_action"; then
      print_info "ℹ️  CLAUDE.md update skipped by user"
      return 0
    fi
  else
    # New file creation
    if ! prompt_claude_md_update "$project_claude_md" "$update_action"; then
      print_info "ℹ️  CLAUDE.md creation skipped by user"
      return 0
    fi
  fi

  # Use the template processor to generate project-specific CLAUDE.md
  print_info "🔄 Generating project-specific CLAUDE.md..."

  # Run the template processor
  local processor_result=$("$VENV_DIR/bin/python" "$template_processor" "$PROJECT_ROOT" "$DEVSTREAM_SCRIPT_DIR" 2>&1)
  local processor_exit_code=$?

  if [ $processor_exit_code -eq 0 ]; then
    # Update version tracking
    local current_version=$(date +%Y%m%d_%H%M%S)
    echo "$current_version" > "$version_file"

    print_status "✅ Project CLAUDE.md generated successfully"
    print_info "   Project: $project_name"
    print_info "   Location: $project_claude_md"

    # Show what was generated (first few lines)
    if [ -f "$project_claude_md" ]; then
      local title=$(head -1 "$project_claude_md" 2>/dev/null || echo "CLAUDE.md")
      print_info "   Title: $title"
    fi

    # Add generation marker to the file
    echo "" >> "$project_claude_md"
    echo "<!--" >> "$project_claude_md"
    echo "Generated with DevStream v2.0 - Context7-compliant multi-project setup" >> "$project_claude_md"
    echo "Generation timestamp: $(date)" >> "$project_claude_md"
    echo "Template: $(basename "$template_processor")" >> "$project_claude_md"
    echo "-->" >> "$project_claude_md"
  else
    print_error "❌ Template processor failed: $processor_result"
    print_info "💡 Falling back to basic CLAUDE.md copy"
    initialize_project_claude_md_fallback
  fi
}

# Fallback method for CLAUDE.md initialization (if template processor fails)
# Enhanced with safety mechanisms: user confirmation, backups, manual detection
initialize_project_claude_md_fallback() {
  local project_name=$(basename "$PROJECT_ROOT")
  local project_claude_md="$PROJECT_ROOT/CLAUDE.md"
  local framework_claude_md="$DEVSTREAM_SCRIPT_DIR/CLAUDE.md"
  local version_file="$PROJECT_ROOT/.claude_version"

  print_info "🔄 Using fallback CLAUDE.md initialization..."

  # Safety check: Detect manual modifications and prompt for confirmation
  local update_action="create"
  if [ -f "$project_claude_md" ]; then
    update_action="overwrite"

    if detect_manual_claude_md "$project_claude_md" "$version_file"; then
      print_warning "⚠️  Manual modifications detected in existing CLAUDE.md"
      if ! prompt_claude_md_update "$project_claude_md" "$update_action"; then
        print_info "ℹ️  CLAUDE.md update skipped by user"
        return 0
      fi
    else
      if ! prompt_claude_md_update "$project_claude_md" "$update_action"; then
        print_info "ℹ️  CLAUDE.md update skipped by user"
        return 0
      fi
    fi
  else
    if ! prompt_claude_md_update "$project_claude_md" "$update_action"; then
      print_info "ℹ️  CLAUDE.md creation skipped by user"
      return 0
    fi
  fi

  # Create basic project-specific CLAUDE.md
  cat > "$project_claude_md" << EOF
# CLAUDE.md - $project_name Project Rules

**Version**: 2.2.0 | **Date**: $(date +%Y-%m-%d) | **Status**: Multi-Project Configuration

<critical_notice>
⚠️ **PROJECT-SPECIFIC RULES** - These rules are adapted for $project_name project.
Combined with DevStream framework rules for complete development workflow.
</critical_notice>

---

## 🎯 Project Environment (PROJECT-SPECIFIC)

### 🚨 CRITICAL RULE: Project Isolation

<rule type="project_isolation" priority="critical">
**Project Configuration**:
- Project Root: $PROJECT_ROOT
- Project Name: $project_name
- Environment File: .env.project

**Framework vs Project Separation**:
- **Project Development**: Work in project directory with project-specific tools
- **DevStream Operations**: Use DevStream framework for system operations

**Project Development Workflow**:
\`\`\`bash
# 1. Work in project directory
cd $PROJECT_ROOT

# 2. Start DevStream in multi-project mode
export DEVSTREAM_PROJECT_ROOT="$PROJECT_ROOT"
./path/to/devstream/start-devstream.sh start

# 3. Use project-specific tools and workflows
# (Depends on project type - see sections below)
\`\`\`

**DevStream System Commands**:
\`\`\`bash
# ✅ CORRECT - Use framework for DevStream operations
$VENV_DIR/bin/python .claude/hooks/devstream/memory/pre_tool_use.py
./start-devstream.sh status

# ✅ CORRECT - Project operations in project directory
cd $PROJECT_ROOT
# Use project-specific tools here
\`\`\`
</rule>

---

## 📚 Framework Rules (Inherited)

The following DevStream framework rules apply to this project:

### Memory System (MANDATORY)
- ✅ Use MemoryManager (\`get_direct_client()\`) for all memory operations
- ❌ NEVER use Python Specialist for memory database queries
- ❌ NEVER use MCP tools (eliminated in v2.2.0+)

### Context7 Integration (MANDATORY)
- ✅ Use Context7 for research and best practices
- ✅ Automatic library detection and documentation injection
- ❌ NEVER skip Context7 research for new technologies

### Quality Gates (MANDATORY)
- ✅ 95%+ test coverage for NEW code
- ✅ 100% test pass rate before commits
- ✅ Full type hints and docstrings
- ✅ @code-reviewer validation before commits

### 7-Step Workflow (MANDATORY)
- ✅ DISCUSS → ANALYZE → RESEARCH → PLAN → APPROVE → IMPLEMENT → VERIFY
- ✅ TodoWrite tracking for all non-trivial tasks
- ✅ Context7 research for technical decisions

---

<project_metadata>
**Project**: $project_name
**DevStream Version**: 2.2.0
**Framework Path**: $DEVSTREAM_SCRIPT_DIR
**Project Path**: $PROJECT_ROOT

**Context7 Compliance**: ✅ Multi-project setup
**Architecture**: Direct DB + Project Isolation
**Quality Gates**: Mandatory code review and testing requirements
</project_metadata>

<!--
Generated with DevStream v2.0 - Context7-compliant multi-project setup (Fallback)
Generation timestamp: $(date)
Template: initialize_project_claude_md_fallback
-->
EOF

  # Update version tracking
  local current_version=$(date +%Y%m%d_%H%M%S)
  echo "$current_version" > "$version_file"

  print_status "✅ Fallback CLAUDE.md created successfully"
  print_info "   Project: $project_name"
  print_info "   Location: $project_claude_md"
}

# Function to initialize project memory bootstrap for multi-project setup
# Context7 best practice: automatic memory population from existing codebase
initialize_project_memory_bootstrap() {
  # Only initialize memory bootstrap in multi-project mode
  if [ -z "${DEVSTREAM_PROJECT_ROOT:-}" ]; then
    return 0
  fi

  print_status "🧠 Initializing project memory bootstrap..."

  local memory_bootstrap_script="$DEVSTREAM_SCRIPT_DIR/.claude/hooks/devstream/memory/memory_bootstrap.py"

  # Check if memory bootstrap script exists
  if [ ! -f "$memory_bootstrap_script" ]; then
    print_warning "⚠️  Memory bootstrap script not found: $memory_bootstrap_script"
    return 0
  fi

  # Check if this is a new project (no memory records)
  local indexing_db="$PROJECT_ROOT/.claude/indexing.db"
  local needs_bootstrap=false

  if [ ! -f "$indexing_db" ]; then
    needs_bootstrap=true
    print_info "📝 No indexing database found, will run initial bootstrap"
  else
    # Check if database is empty (no records)
    local record_count=$("$VENV_DIR/bin/python" -c "
import sqlite3
import sys

db_path = r'$indexing_db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.execute('SELECT COUNT(*) FROM indexing_records')
    count = cursor.fetchone()[0]
    conn.close()
    print(count)
except Exception as e:
    print(f'ERROR:{e}')
    sys.exit(1)
" 2>/dev/null)

    if [[ "$record_count" =~ ^[0-9]+$ ]] && [ "$record_count" -eq 0 ]; then
      needs_bootstrap=true
      print_info "📝 Indexing database is empty, will run bootstrap"
    else
      print_info "✅ Memory bootstrap already completed ($record_count files indexed)"
    fi
  fi

  if [ "$needs_bootstrap" = false ]; then
    return 0
  fi

  # Run memory bootstrap
  print_info "🔄 Running memory bootstrap for project: $(basename "$PROJECT_ROOT")"
  print_info "   This may take a few minutes for large codebases..."

  # Run the bootstrap script with appropriate arguments
  local bootstrap_result=$("$VENV_DIR/bin/python" "$memory_bootstrap_script" \
    "$PROJECT_ROOT" \
    --mode incremental \
    --cleanup incremental \
    --batch-size 25 \
    --output summary \
    2>&1)
  local bootstrap_exit_code=$?

  if [ $bootstrap_exit_code -eq 0 ]; then
    print_status "✅ Project memory bootstrap completed successfully"

    # Show summary of what was indexed
    if echo "$bootstrap_result" | grep -q "Total files:"; then
      local files_info=$(echo "$bootstrap_result" | grep "Total files:" | head -1)
      print_info "   $files_info"
    fi

    if echo "$bootstrap_result" | grep -q "Total chunks:"; then
      local chunks_info=$(echo "$bootstrap_result" | grep "Total chunks:" | head -1)
      print_info "   $chunks_info"
    fi

    print_info "   Memory is now available for AI-powered search and context"
    print_info "   Run: .devstream/bin/python -c \"from .claude.hooks.devstream.utils.direct_client import get_direct_client; print(get_direct_client().search_memory('test query', limit=5))\""
  else
    print_error "❌ Memory bootstrap failed"
    print_error "   Error: $bootstrap_result"
    print_warning "   You can run it manually later:"
    print_warning "   $memory_bootstrap_script $PROJECT_ROOT --mode incremental"
    return 1
  fi
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

      # Initialize Direct DB Architecture
      initialize_direct_db

      # Check prerequisites (now database exists)
      check_prerequisites

      # Validate Direct DB configuration
      if validate_direct_db_config; then
        print_status "✅ Direct DB configuration validated"
      else
        print_error "Direct DB validation failed"
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

      # Show Direct DB status
      show_direct_db_status

      # Show Agent status
      show_agent_status

      echo ""
      print_status "🎉 DevStream v2.0 (Direct DB Architecture) is ready!"
      echo ""

      # Start Claude Code
      start_claude_with_devstream
      ;;

    stop)
      stop_server
      ;;

    status)
      load_devstream_config
      show_direct_db_status
      show_agent_status
      ;;

    restart)
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
