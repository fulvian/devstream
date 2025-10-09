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

  # Build Claude Code command with GLM-4.6 model
  local claude_command="claude --model glm-4.6"

  print_info "Command: $claude_command"
  print_info "Working directory: $(pwd)"
  echo ""

  # Execute Claude Code with GLM-4.6
  exec $claude_command
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