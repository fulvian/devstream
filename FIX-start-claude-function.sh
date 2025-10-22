# ============================================================================
# SOLUZIONE ROBUSTA PER start_claude_with_devstream
# Context7-compliant: Error handling + Directory management + Process control
# ============================================================================

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

  # =========================================================================
  # CRITICAL FIX: Robust directory management and error handling
  # Context7 best practice: Validate before execute, clear error messages
  # =========================================================================

  # Step 1: Validate project directory exists
  if [ ! -d "$PROJECT_ROOT" ]; then
    print_error "❌ Project directory not found: $PROJECT_ROOT"
    print_error "   Expected directory does not exist"
    print_error ""
    print_error "   Troubleshooting:"
    print_error "   1. Verify project path is correct"
    print_error "   2. Check if project was moved or deleted"
    print_error "   3. Re-run DevStream installation if needed"
    exit 1
  fi

  # Step 2: Show current state before changing directory
  local launcher_cwd="$(pwd)"
  print_info "🔍 Pre-launch validation:"
  print_info "   Launcher directory: $launcher_cwd"
  print_info "   Project directory:  $PROJECT_ROOT"
  print_info "   Database path:      $DEVSTREAM_DB_PATH"
  echo ""

  # Step 3: Verify Claude Code command is available
  if ! command -v claude >/dev/null 2>&1; then
    print_error "❌ Claude Code command not found in PATH"
    print_error "   The 'claude' command is not available"
    print_error ""
    print_error "   Troubleshooting:"
    print_error "   1. Install Claude Code: brew install claude"
    print_error "   2. Verify PATH includes: /opt/homebrew/bin"
    print_error "   3. Run: which claude"
    exit 1
  fi

  # Step 4: Validate database exists (critical for DevStream)
  if [ ! -f "$DEVSTREAM_DB_PATH" ]; then
    print_warning "⚠️  Database not found: $DEVSTREAM_DB_PATH"
    print_warning "   DevStream will create it on first use"
  else
    local db_size=$(stat -f%z "$DEVSTREAM_DB_PATH" 2>/dev/null || echo "unknown")
    print_info "   Database verified: $(numfmt --to=iec $db_size 2>/dev/null || echo $db_size bytes)"
  fi

  # Step 5: Change to project directory with robust error handling
  # Context7 pattern: Always validate directory operations
  print_status "📁 Changing to project directory..."

  if ! cd "$PROJECT_ROOT" 2>/dev/null; then
    print_error "❌ Failed to change to project directory"
    print_error "   Target: $PROJECT_ROOT"
    print_error "   Current: $(pwd)"
    print_error ""
    print_error "   Possible causes:"
    print_error "   1. Directory permissions issue"
    print_error "   2. Directory was deleted or moved"
    print_error "   3. Filesystem mount issue"
    print_error ""
    print_error "   Try: ls -ld \"$PROJECT_ROOT\""
    exit 1
  fi

  # Step 6: Verify we're in the correct directory
  local actual_cwd="$(pwd)"
  if [ "$actual_cwd" != "$PROJECT_ROOT" ]; then
    print_error "❌ Directory change verification failed"
    print_error "   Expected: $PROJECT_ROOT"
    print_error "   Actual:   $actual_cwd"
    print_error ""
    print_error "   This indicates a serious filesystem or shell issue"
    exit 1
  fi

  print_status "✅ Working directory set: $actual_cwd"
  echo ""

  # Step 7: Display final environment summary
  print_feature "🚀 Launching Claude Code with DevStream"
  print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  print_info "  Project:   $(basename "$PROJECT_ROOT")"
  print_info "  Directory: $PROJECT_ROOT"
  print_info "  Provider:  $active_provider"
  print_info "  Database:  $DEVSTREAM_DB_PATH"
  print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""

  # Step 8: Launch Claude Code with process substitution
  # Context7 pattern: Use exec to replace launcher process with Claude Code
  # This is the correct behavior for a launcher - become the target process

  if [ "$active_provider" = "z.ai" ]; then
    print_info "🔄 Starting Claude Code with GLM-4.6 via z.ai script..."

    # Verify z.ai script exists
    local zai_script="$DEVSTREAM_SCRIPT_DIR/scripts/start-claude-zai.sh"
    if [ ! -f "$zai_script" ]; then
      print_error "❌ z.ai launcher script not found: $zai_script"
      exit 1
    fi

    # exec replaces current process with z.ai script
    # This line never returns - launcher becomes z.ai launcher
    exec "$zai_script"

  else
    print_info "🚀 Starting Claude Code with Anthropic provider..."

    # exec replaces current process with Claude Code
    # This line never returns - launcher becomes Claude Code
    exec claude
  fi

  # =========================================================================
  # UNREACHABLE CODE: exec replaces the process, so we never get here
  # If we reach this point, it means exec failed (extremely rare)
  # =========================================================================

  print_error "❌ CRITICAL: Failed to launch Claude Code"
  print_error "   exec command failed unexpectedly"
  print_error ""
  print_error "   This should never happen. Possible causes:"
  print_error "   1. Claude Code binary is corrupted"
  print_error "   2. System resource exhaustion"
  print_error "   3. Permission issue with exec"
  exit 1
}

# ============================================================================
# ADDITIONAL FIX: initialize_project_venv directory restoration
# Context7 best practice: Don't restore cwd if we want to stay in project
# ============================================================================

# MODIFY THIS SECTION in initialize_project_venv (around line 2230):

# BEFORE (lines 2230-2237):
#   print_info "📁 Project config: .env.project"
#
#   # Context7 Pattern: Always restore original working directory
#   cd "$original_pwd" || {
#     print_warning "⚠️ Could not restore original directory: $original_pwd"
#     print_warning "   Current directory: $(pwd)"
#   }
# }

# AFTER:
#   print_info "📁 Project config: .env.project"
#
#   # Context7 Pattern: Restore working directory for multi-project isolation
#   # EXCEPTION: In multi-project mode, we want to STAY in project directory
#   # so that subsequent operations (like starting Claude Code) work correctly
#
#   if [ -z "${DEVSTREAM_PROJECT_ROOT:-}" ]; then
#     # Single-project mode: restore to DevStream installation directory
#     cd "$original_pwd" || {
#       print_warning "⚠️ Could not restore original directory: $original_pwd"
#       print_warning "   Current directory: $(pwd)"
#     }
#   else
#     # Multi-project mode: verify we're in project directory
#     local current_dir="$(pwd)"
#     if [ "$current_dir" != "$PROJECT_ROOT" ]; then
#       print_warning "⚠️ Not in expected project directory"
#       print_warning "   Expected: $PROJECT_ROOT"
#       print_warning "   Current:  $current_dir"
#       print_warning "   Correcting..."
#       cd "$PROJECT_ROOT" || {
#         print_error "❌ Failed to correct directory"
#         exit 1
#       }
#     fi
#     print_info "✅ Verified project directory: $(pwd)"
#   fi
# }

# ============================================================================
# END OF FIX
# ============================================================================
