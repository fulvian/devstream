#!/bin/bash

# DevStream Claude Code Launcher for Z.AI GLM-4.6
# Modular script to launch Claude Code with GLM-4.6 model via Z.AI API
# Follows Context7 best practices for environment variable management

set -e

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
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

# Function to validate required environment variables
validate_environment() {
  print_status "Validating Z.AI environment..."

  # Check if we're in the correct directory
  if [ ! -f "$PROJECT_ROOT/.env" ]; then
    print_error ".env file not found in project root"
    exit 1
  fi

  # Load environment variables from project root
  set -a
  source "$PROJECT_ROOT/.env"
  set +a

  # Validate Z.AI API key
  if [ -z "${ZAI_API_KEY:-}" ]; then
    print_error "ZAI_API_KEY not configured in .env"
    print_error "Get your API key from: https://z.ai/manage-apikey/apikey-list"
    exit 1
  fi

  print_info "✅ Z.AI API key configured"
  print_info "✅ Environment validation complete"
}

# Function to setup Z.AI environment variables
setup_zai_environment() {
  print_status "Setting up Z.AI environment for Claude Code..."

  # Export Z.AI specific environment variables
  export ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic"
  export ANTHROPIC_AUTH_TOKEN="$ZAI_API_KEY"

  print_info "📡 Base URL: $ANTHROPIC_BASE_URL"
  print_info "🔑 Auth Token: ${ZAI_API_KEY:0:10}..."
  print_info "🤖 Target Model: GLM-4.6"
}

# Function to launch Claude Code with GLM-4.6
launch_claude_code() {
  print_status "🚀 Launching Claude Code with GLM-4.6..."

  # Change to project directory
  cd "$PROJECT_ROOT"

  # Configure Claude Code settings for z.ai (required for model switching)
  configure_claude_settings

  print_info "Working directory: $(pwd)"
  print_info "🤖 Model: GLM-4.6 (via z.ai API)"
  print_info "📡 API: $ANTHROPIC_BASE_URL"
  echo ""

  # Execute Claude Code (settings will handle model selection)
  exec claude
}

# Function to configure Claude Code settings for z.ai
configure_claude_settings() {
  local settings_file="$HOME/.claude/settings.json"

  print_status "⚙️ Configuring Claude Code settings for GLM-4.6..."

  # Backup existing settings
  if [ -f "$settings_file" ]; then
    cp "$settings_file" "$settings_file.backup-zai-$(date +%Y%m%d_%H%M%S)"
    print_info "✅ Backed up existing settings"
  fi

  # Use Python for JSON manipulation (following Context7 best practices)
  "$PROJECT_ROOT/.devstream/bin/python" << EOF
import json
import os

settings_file = "$settings_file"

# Read existing settings
existing_data = {}
if os.path.exists(settings_file):
    try:
        with open(settings_file, 'r') as f:
            existing_data = json.load(f)
    except (json.JSONDecodeError, IOError):
        print("Warning: Could not parse existing settings")

# Preserve important data
preserved_data = {
    "hooks": existing_data.get("hooks", {}),
    "mcpServers": existing_data.get("mcpServers", {}),
    "alwaysThinkingEnabled": existing_data.get("alwaysThinkingEnabled", False)
}

# Create z.ai configuration
zai_config = {
    **preserved_data,
    "model": "glm-4.6",
    "env": {
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm-4.6",
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-4.6",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "glm-4.5-air"
    }
}

# Write settings
with open(settings_file, 'w') as f:
    json.dump(zai_config, f, indent=2)

print("✅ Claude Code configured for GLM-4.6")
EOF

  if [ $? -eq 0 ]; then
    print_info "✅ Claude Code settings updated for GLM-4.6"
  else
    print_error "❌ Failed to update Claude Code settings"
    exit 1
  fi
}

# Main execution function
main() {
  echo ""
  print_status "🤖 DevStream Z.AI GLM-4.6 Launcher"
  print_status "==================================="
  echo ""

  # Execute setup steps
  validate_environment
  setup_zai_environment
  launch_claude_code
}

# Handle script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi