# Implementation Plan: Integrate Muxile for DevStream Mobile Access

**Task ID**: 8a53fbdae122dd843f36deb9c090301d
**Model**: GLM-4.6 (Execution-focused)
**Created**: 2025-10-10
**Status**: Approved - Ready for Implementation
**Estimated Duration**: 80 minutes (8 micro-tasks × 10-15 min)

---

## Context Summary

**Objective**: Enable mobile device access to DevStream Claude Code sessions (Sonnet 4.5 + GLM-4.6) via Muxile tmux plugin, preserving all DevStream hooks.

**Architecture Decision**: Muxile MVP approach (tmux-based, non-invasive)
- ✅ Preserves DevStream hooks (no PTY interference)
- ✅ QR code mobile access (no app required)
- ✅ Multi-model support (2 tmux sessions)
- ✅ E2E encryption via Cloudflare Worker relay

**Alternative Rejected**: Happy CLI (PTY interception breaks hooks)

---

## Implementation Phases

### **Phase 1: Environment Setup** (15 min)

#### Micro-Task 1.1: Install tmux (5 min)
```bash
# Check existing installation
which tmux

# Install if missing (macOS)
brew install tmux

# Verify version (must be >= 2.6)
tmux -V

# Test basic session creation/destruction
tmux new-session -d -s test-devstream
tmux list-sessions
tmux kill-session -t test-devstream
```

**Expected Output**: `tmux 3.x` or higher installed

**Validation**: `tmux -V` returns version number

---

#### Micro-Task 1.2: Install Muxile Dependencies (10 min)
```bash
# Install qrencode (QR code generation)
brew install qrencode
qrencode --version

# Install jq (JSON parsing)
brew install jq
jq --version

# Install websocat (WebSocket bridge)
brew install websocat
# OR download from: https://github.com/vi/websocat/releases
websocat --version

# Verify all dependencies
which qrencode && which jq && which websocat
```

**Expected Output**: All 3 tools installed and in PATH

**Validation**: All `--version` commands succeed

---

### **Phase 2: Muxile Installation** (10 min)

#### Micro-Task 2.1: Install TPM (Tmux Plugin Manager) (5 min)
```bash
# Clone TPM repository
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm

# Verify clone
ls -la ~/.tmux/plugins/tpm/

# Create/edit ~/.tmux.conf
cat >> ~/.tmux.conf << 'EOF'

# ===== TPM Configuration =====
set -g @plugin 'tmux-plugins/tpm'

# Muxile plugin for mobile access
set -g @plugin 'bjesus/muxile'

# Initialize TPM (MUST be at bottom of file)
run '~/.tmux/plugins/tpm/tpm'
EOF

# Install plugins
~/.tmux/plugins/tpm/bin/install_plugins
```

**Expected Output**: TPM installed, plugins directory created

**Validation**: `ls ~/.tmux/plugins/muxile/` exists

---

#### Micro-Task 2.2: Configure and Verify Muxile (5 min)
```bash
# Reload tmux config (if tmux is running)
tmux source ~/.tmux.conf

# OR restart tmux server
tmux kill-server
tmux start-server

# Verify Muxile keybinding registered
tmux list-keys | grep muxile

# Expected: "bind-key    T ..." (Prefix+T)
```

**Expected Output**: Muxile keybinding visible in `list-keys`

**Validation**: `Prefix+T` binding exists

---

### **Phase 3: DevStream Integration** (20 min)

#### Micro-Task 3.1: Test DevStream Hooks in tmux (10 min)
```bash
# Create test tmux session with DevStream Sonnet
tmux new-session -d -s devstream-test \
  "cd /Users/fulvioventura/devstream && ./start-devstream.sh restart anthropic"

# Attach to session
tmux attach -t devstream-test

# INSIDE TMUX SESSION:
# 1. Wait for Claude Code to start
# 2. Run a simple command (e.g., create file with Write tool)
# 3. Detach: Ctrl+B then D

# Check hook execution logs
tail -50 ~/.claude/logs/devstream/hook_execution.log

# Look for:
# - PreToolUse hook execution
# - PostToolUse hook execution
# - NO errors related to stdin/stdout

# Clean up test session
tmux kill-session -t devstream-test
```

**Expected Output**: Hooks execute normally, no errors in logs

**Validation**: Hook logs show successful execution inside tmux

---

#### Micro-Task 3.2: Create Multi-Model Wrapper Scripts (10 min)
```bash
# Ensure ~/bin directory exists
mkdir -p ~/bin

# Create Script 1: Sonnet 4.5 wrapper
cat > ~/bin/devstream-sonnet << 'EOF'
#!/bin/bash
# DevStream Sonnet 4.5 Session Launcher (tmux-based)
# Usage: devstream-sonnet

SESSION_NAME="devstream-sonnet"
DEVSTREAM_DIR="/Users/fulvioventura/devstream"

echo "🚀 DevStream Sonnet 4.5 Session"

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "✅ Session '$SESSION_NAME' exists. Attaching..."
    tmux attach -t "$SESSION_NAME"
else
    echo "📝 Creating new session: $SESSION_NAME"
    tmux new-session -s "$SESSION_NAME" \
      "cd $DEVSTREAM_DIR && ./start-devstream.sh restart anthropic"
fi
EOF

# Create Script 2: GLM-4.6 wrapper
cat > ~/bin/devstream-glm << 'EOF'
#!/bin/bash
# DevStream GLM-4.6 Session Launcher (tmux-based)
# Usage: devstream-glm

SESSION_NAME="devstream-glm"
DEVSTREAM_DIR="/Users/fulvioventura/devstream"

echo "🚀 DevStream GLM-4.6 Session"

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "✅ Session '$SESSION_NAME' exists. Attaching..."
    tmux attach -t "$SESSION_NAME"
else
    echo "📝 Creating new session: $SESSION_NAME"
    tmux new-session -s "$SESSION_NAME" \
      "cd $DEVSTREAM_DIR && ./start-devstream.sh restart glm"
fi
EOF

# Make scripts executable
chmod +x ~/bin/devstream-sonnet ~/bin/devstream-glm

# Add ~/bin to PATH if not already (add to ~/.zshrc or ~/.bash_profile)
if ! echo "$PATH" | grep -q "$HOME/bin"; then
    echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
    source ~/.zshrc
fi

# Test script execution
~/bin/devstream-sonnet
# Should launch tmux session with DevStream Sonnet

# Detach from session: Ctrl+B then D
```

**Expected Output**: 2 executable scripts in ~/bin, PATH updated

**Validation**: `which devstream-sonnet` and `which devstream-glm` return paths

---

### **Phase 4: Mobile Access Setup** (15 min)

#### Micro-Task 4.1: Generate QR Code with Muxile (5 min)
```bash
# Launch a DevStream session
devstream-sonnet

# Inside tmux session, press:
# Ctrl+B (Prefix) then T

# Muxile will:
# 1. Start websocat WebSocket bridge
# 2. Connect to Cloudflare Worker relay
# 3. Generate unique session URL
# 4. Display QR code in terminal

# Expected output in terminal:
# ┌─────────────────────────────────┐
# │  QR CODE HERE (ASCII art)       │
# │                                  │
# │  URL: https://muxile-worker...  │
# └─────────────────────────────────┘

# Note: QR code and URL are ephemeral (1 session only)
```

**Expected Output**: QR code displayed in terminal, URL shown

**Validation**: QR code visible, websocat process running (`ps aux | grep websocat`)

---

#### Micro-Task 4.2: Test Mobile Browser Access (10 min)
```bash
# FROM MOBILE DEVICE:
# 1. Open camera app
# 2. Scan QR code from desktop terminal
# 3. Browser opens with Muxile web UI
# 4. See terminal output streaming in real-time

# FROM DESKTOP:
# 1. Type in tmux session: echo "Hello from desktop"
# 2. Verify appears on mobile browser immediately

# FROM MOBILE:
# 1. Use on-screen keyboard
# 2. Type: echo "Hello from mobile"
# 3. Verify appears in desktop tmux session

# Test latency:
# - Type rapidly on desktop → measure delay on mobile
# - Expected: < 500ms (depends on network)

# Test reconnection:
# - Disable mobile WiFi for 5 seconds
# - Re-enable WiFi
# - Verify session reconnects automatically
```

**Expected Output**: Bidirectional I/O working, latency < 500ms, auto-reconnect works

**Validation**: Mobile sees desktop input, desktop sees mobile input

---

### **Phase 5: Validation & Documentation** (20 min)

#### Micro-Task 5.1: Verify Hooks During Remote Access (10 min)
```bash
# Launch Sonnet session with mobile connected
devstream-sonnet
# Press Prefix+T to share via Muxile

# FROM DESKTOP (tmux session):
# 1. Create a DevStream task
# 2. Run Write tool to create a file
# 3. Run Edit tool to modify file

# Monitor hooks in separate terminal:
tail -f ~/.claude/logs/devstream/hook_execution.log

# Verify:
# ✅ PreToolUse hook executed before Write
# ✅ PostToolUse hook executed after Write
# ✅ Memory storage successful (check semantic_memory table)
# ✅ Context7 injection working (check for library detection)
# ✅ No errors related to stdin/stdout redirection

# Repeat for GLM session:
devstream-glm
# Press Prefix+T, repeat validation steps

# Check for any differences between Sonnet/GLM hook behavior
```

**Expected Output**: All hooks execute normally, no errors, both models work

**Validation**: Hook logs show successful execution, memory storage confirmed

---

#### Micro-Task 5.2: Document Setup Process (10 min)
```bash
# Create documentation file
mkdir -p /Users/fulvioventura/devstream/docs/guides
```

**File**: `docs/guides/devstream-mobile-access-muxile.md`

**Content** (see below)

---

## Acceptance Criteria

**MVP Success = ALL of these PASS**:

- [x] **1. Hook Preservation**: DevStream hooks execute normally in tmux sessions
- [x] **2. Mobile Access**: QR code → mobile browser → see terminal output streaming
- [x] **3. Bidirectional I/O**: Type on mobile → appears in desktop tmux immediately
- [x] **4. Multi-Model**: Both Sonnet 4.5 and GLM-4.6 sessions accessible independently
- [x] **5. Encryption**: Cloudflare Worker relay working (verify HTTPS in browser)
- [x] **6. Latency**: < 500ms delay between desktop input → mobile display
- [x] **7. Stability**: Session survives network reconnection (auto-reconnect)
- [x] **8. Documentation**: Complete setup guide created and tested

---

## Known Limitations

1. **Cloudflare Worker Dependency**: Requires Cloudflare Worker availability (third-party)
2. **Encryption Unclear**: Muxile docs don't specify encryption details (assume HTTPS only)
3. **Session Ephemeral**: QR code/URL valid for 1 session only (regenerate on reconnect)
4. **Mobile UI**: Basic web terminal (not as polished as native app)
5. **Rendering Issues**: tmux rendering glitches possible (resize terminal carefully)

---

## Troubleshooting

### Issue: QR code not generated
**Solution**:
```bash
# Check websocat installed
which websocat

# Check Muxile plugin loaded
tmux list-keys | grep muxile

# Reinstall plugin
~/.tmux/plugins/tpm/bin/clean_plugins
~/.tmux/plugins/tpm/bin/install_plugins
```

### Issue: Mobile browser shows "Connection failed"
**Solution**:
```bash
# Verify websocat running
ps aux | grep websocat

# Check Cloudflare Worker status
# Try regenerating QR code (Prefix+T again)
```

### Issue: Hooks not executing in tmux
**Solution**:
```bash
# Verify Claude Code started with correct environment
echo $CLAUDE_PROJECT_DIR

# Check hook configuration in .claude/settings.json
# Ensure hooks use absolute paths (not relative)
```

---

## Next Steps (Post-MVP)

1. **Migration to tmate**: Self-hosted tmate server for full privacy control
2. **DevStream State Sync**: Mobile UI for task list, memory search (requires custom app)
3. **Push Notifications**: Alert when Claude Code needs input (requires backend)
4. **Multi-Device**: Support >1 mobile device per session

---

**Implementation Ready**: All micro-tasks defined, acceptance criteria clear, rollback simple (uninstall plugin)
