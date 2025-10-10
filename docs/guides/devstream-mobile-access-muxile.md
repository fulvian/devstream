# DevStream Mobile Access with Muxile

Enable remote terminal control of Claude Code sessions from mobile devices via QR code while preserving all DevStream hooks.

## Overview

This guide sets up **Muxile**, a tmux plugin that provides mobile access to terminal sessions through:
- QR code generation for instant mobile browser access
- Bidirectional I/O streaming (desktop ↔ mobile)
- WebSocket relay via Cloudflare Workers
- Zero app installation required (mobile browser only)

## Architecture

```
Desktop (DevStream + tmux)
    ↓
Muxile Plugin (UNIX socket)
    ↓
websocat (WebSocket bridge)
    ↓
Cloudflare Worker (HTTPS relay)
    ↓
Mobile Browser (QR code → terminal)
```

## Prerequisites

- **macOS** with Homebrew installed
- **tmux** (version 2.6+)
- **DevStream** with working hooks
- **Mobile device** with camera and web browser

## Installation

### 1. Install Dependencies

```bash
# Install required tools
brew install qrencode jq websocat

# Verify installation
qrencode --version  # Should show 4.1.1+
jq --version        # Should show 1.8+
websocat --version  # Should show 1.14+
```

### 2. Install TPM (Tmux Plugin Manager)

```bash
# Clone TPM
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm

# Add to ~/.tmux.conf
cat >> ~/.tmux.conf << 'EOF'
# TPM (Tmux Plugin Manager)
set -g @plugin 'tmux-plugins/tpm'
set -g @plugin 'bjesus/muxile'

# Initialize TPM (keep this line at the very bottom)
run '~/.tmux/plugins/tpm/tpm'
EOF

# Install plugins
tmux source ~/.tmux.conf
~/.tmux/plugins/tpm/bin/install_plugins
```

### 3. Create Wrapper Scripts

```bash
# Create bin directory
mkdir -p ~/bin

# Create devstream-sonnet wrapper (with security hardening)
cat > ~/bin/devstream-sonnet << 'EOF'
#!/bin/bash

# DevStream Sonnet 4.5 Session Wrapper
# Usage: devstream-sonnet

set -euo pipefail

# Logging setup
LOG_DIR="$HOME/.devstream/logs"
LOG_FILE="$LOG_DIR/wrapper-$(date +%Y%m%d).log"
mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Cleanup trap
cleanup() {
    local result=$?
    if [[ $result -ne 0 ]] && [[ -n "${SESSION_NAME:-}" ]]; then
        log "ERROR: Script failed with exit code $result"
        if $TMUX_CMD has-session -t "$SESSION_NAME" 2>/dev/null; then
            log "Cleaning up failed session: $SESSION_NAME"
            $TMUX_CMD kill-session -t "$SESSION_NAME" 2>/dev/null || true
        fi
    fi
}

trap cleanup EXIT ERR INT TERM

SESSION_NAME="devstream-sonnet"
PROJECT_DIR="/Users/fulvioventura/devstream"

log "🚀 Starting DevStream Sonnet 4.5 session in tmux..."
log "📱 Mobile access: Press Ctrl+B then T to generate QR code"
log "🔄 To detach: Ctrl+B then D"
log "❌ To kill session: tmux kill-session -t $SESSION_NAME"
echo ""

# Use absolute paths for tmux
TMUX_CMD="/opt/homebrew/bin/tmux"

# Check if session already exists
if $TMUX_CMD has-session -t "$SESSION_NAME" 2>/dev/null; then
    log "⚠️  Session '$SESSION_NAME' already exists"
    log "📂 Attaching to existing session..."
    $TMUX_CMD attach -t "$SESSION_NAME"
    exit 0
fi

# Validate startup script
STARTUP_SCRIPT="$PROJECT_DIR/start-devstream.sh"

# Validate existence
if [[ ! -f "$STARTUP_SCRIPT" ]]; then
    log "❌ Error: start-devstream.sh not found: $STARTUP_SCRIPT"
    exit 1
fi

# Validate ownership (must match current user)
SCRIPT_OWNER=$(stat -f "%u" "$STARTUP_SCRIPT")
if [[ "$SCRIPT_OWNER" != "$(id -u)" ]]; then
    log "❌ Security Error: start-devstream.sh not owned by current user"
    log "Expected owner: $(id -u), Actual owner: $SCRIPT_OWNER"
    exit 1
fi

# Validate permissions (not world-writable)
SCRIPT_PERMS=$(stat -f "%Lp" "$STARTUP_SCRIPT")
if [[ "$SCRIPT_PERMS" =~ [0-9][0-9][2-7] ]]; then
    log "❌ Security Error: start-devstream.sh is world-writable (permissions: $SCRIPT_PERMS)"
    log "Fix with: chmod 755 $STARTUP_SCRIPT"
    exit 1
fi

# Create new tmux session with DevStream
log "🔧 Creating new tmux session: $SESSION_NAME"
cd "$PROJECT_DIR"

$TMUX_CMD new-session -d -s "$SESSION_NAME" "./start-devstream.sh restart anthropic"

# Wait for session to initialize
log "⏳ Waiting for DevStream to initialize..."

TIMEOUT=15
ELAPSED=0
while ! $TMUX_CMD has-session -t "$SESSION_NAME" 2>/dev/null; do
    if [[ $ELAPSED -ge $TIMEOUT ]]; then
        log "❌ Timeout waiting for DevStream session to start"
        log "Check logs for errors"
        exit 1
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

# Check if session is still running
if ! $TMUX_CMD has-session -t "$SESSION_NAME" 2>/dev/null; then
    log "❌ Failed to start DevStream session"
    exit 1
fi

log "✅ DevStream Sonnet 4.5 session started successfully!"
log "📱 Generate QR code with: Ctrl+B then T"
log "📂 Attaching to session..."

# Attach to the session
$TMUX_CMD attach -t "$SESSION_NAME"
EOF

# Create devstream-glm wrapper (with security hardening)
cat > ~/bin/devstream-glm << 'EOF'
#!/bin/bash

# DevStream GLM-4.6 Session Wrapper
# Usage: devstream-glm

set -euo pipefail

# Logging setup
LOG_DIR="$HOME/.devstream/logs"
LOG_FILE="$LOG_DIR/wrapper-$(date +%Y%m%d).log"
mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Cleanup trap
cleanup() {
    local result=$?
    if [[ $result -ne 0 ]] && [[ -n "${SESSION_NAME:-}" ]]; then
        log "ERROR: Script failed with exit code $result"
        if $TMUX_CMD has-session -t "$SESSION_NAME" 2>/dev/null; then
            log "Cleaning up failed session: $SESSION_NAME"
            $TMUX_CMD kill-session -t "$SESSION_NAME" 2>/dev/null || true
        fi
    fi
}

trap cleanup EXIT ERR INT TERM

SESSION_NAME="devstream-glm"
PROJECT_DIR="/Users/fulvioventura/devstream"

log "🚀 Starting DevStream GLM-4.6 session in tmux..."
log "📱 Mobile access: Press Ctrl+B then T to generate QR code"
log "🔄 To detach: Ctrl+B then D"
log "❌ To kill session: tmux kill-session -t $SESSION_NAME"
echo ""

# Use absolute paths for tmux
TMUX_CMD="/opt/homebrew/bin/tmux"

# Check if session already exists
if $TMUX_CMD has-session -t "$SESSION_NAME" 2>/dev/null; then
    log "⚠️  Session '$SESSION_NAME' already exists"
    log "📂 Attaching to existing session..."
    $TMUX_CMD attach -t "$SESSION_NAME"
    exit 0
fi

# Validate startup script
STARTUP_SCRIPT="$PROJECT_DIR/start-devstream.sh"

# Validate existence
if [[ ! -f "$STARTUP_SCRIPT" ]]; then
    log "❌ Error: start-devstream.sh not found: $STARTUP_SCRIPT"
    exit 1
fi

# Validate ownership (must match current user)
SCRIPT_OWNER=$(stat -f "%u" "$STARTUP_SCRIPT")
if [[ "$SCRIPT_OWNER" != "$(id -u)" ]]; then
    log "❌ Security Error: start-devstream.sh not owned by current user"
    log "Expected owner: $(id -u), Actual owner: $SCRIPT_OWNER"
    exit 1
fi

# Validate permissions (not world-writable)
SCRIPT_PERMS=$(stat -f "%Lp" "$STARTUP_SCRIPT")
if [[ "$SCRIPT_PERMS" =~ [0-9][0-9][2-7] ]]; then
    log "❌ Security Error: start-devstream.sh is world-writable (permissions: $SCRIPT_PERMS)"
    log "Fix with: chmod 755 $STARTUP_SCRIPT"
    exit 1
fi

# Create new tmux session with DevStream
log "🔧 Creating new tmux session: $SESSION_NAME"
cd "$PROJECT_DIR"

$TMUX_CMD new-session -d -s "$SESSION_NAME" "./start-devstream.sh restart glm"

# Wait for session to initialize
log "⏳ Waiting for DevStream to initialize..."

TIMEOUT=15
ELAPSED=0
while ! $TMUX_CMD has-session -t "$SESSION_NAME" 2>/dev/null; do
    if [[ $ELAPSED -ge $TIMEOUT ]]; then
        log "❌ Timeout waiting for DevStream session to start"
        log "Check logs for errors"
        exit 1
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

# Check if session is still running
if ! $TMUX_CMD has-session -t "$SESSION_NAME" 2>/dev/null; then
    log "❌ Failed to start DevStream session"
    exit 1
fi

log "✅ DevStream GLM-4.6 session started successfully!"
log "📱 Generate QR code with: Ctrl+B then T"
log "📂 Attaching to session..."

# Attach to the session
$TMUX_CMD attach -t "$SESSION_NAME"
EOF

# Make scripts executable
chmod +x ~/bin/devstream-sonnet ~/bin/devstream-glm

# Add to PATH
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## Usage

### Starting Mobile Sessions

#### Sonnet 4.5 Session
```bash
devstream-sonnet
```

#### GLM-4.6 Session
```bash
devstream-glm
```

### Generating QR Code for Mobile Access

1. **Start** a DevStream session using one of the wrapper scripts above
2. **Press** `Ctrl+B` then `T` to activate Muxile
3. **Scan** the QR code with your mobile device camera
4. **Open** the link in your mobile browser

### Session Management

```bash
# List active sessions
tmux list-sessions

# Attach to existing session
tmux attach -t devstream-sonnet
tmux attach -t devstream-glm

# Detach from session (keep it running)
# Press: Ctrl+B then D

# Kill session
tmux kill-session -t devstream-sonnet
tmux kill-session -t devstream-glm
```

### Stopping Mobile Access

Press `Ctrl+B` then `T` again to toggle Muxile off and disconnect mobile access.

## Validation

### Verify DevStream Hooks Work

```bash
# Start session
devstream-sonnet

# In tmux session, test hooks with any command that triggers tools:
echo "Testing hooks" > /tmp/test.txt

# Check hook logs
tail -f ~/.claude/logs/devstream/post_tool_use.log
```

### Test Mobile Access

1. Generate QR code with `Ctrl+B T`
2. Scan with mobile device
3. Type in desktop terminal → should appear on mobile
4. Type in mobile browser → should appear on desktop
5. Verify DevStream hooks still execute (check logs)

## Troubleshooting

### Common Issues

#### QR Code Not Generated
```bash
# Check if Muxile plugin is loaded
tmux list-keys | grep muxile

# Reload tmux config
tmux source ~/.tmux.conf

# Manually run Muxile
tmux run-shell "~/.tmux/plugins/muxile/scripts/main.sh"
```

#### Mobile Connection Issues
```bash
# Check if websocat is installed
which websocat

# Check if socket exists
ls -la /tmp/muxile.socket

# Restart Muxile
# Press Ctrl+B T twice (off, then on)
```

#### DevStream Hooks Not Working
```bash
# Check hook logs
tail -20 ~/.claude/logs/devstream/post_tool_use.log

# Verify venv is active
echo $VIRTUAL_ENV  # Should point to .devstream

# Test hooks outside tmux
echo "test" > /tmp/hook-test.txt
```

#### Session Already Exists
```bash
# Kill existing session
tmux kill-session -t devstream-sonnet

# Or attach to existing session
tmux attach -t devstream-sonnet
```

### Error Messages

- **"no current client"**: Session detached but still running. Use `tmux attach` to reconnect.
- **"can't find session"**: Session not started or was killed. Use wrapper script to start.
- **"command not found: tmux"**: tmux not in PATH. Check `/opt/homebrew/bin/tmux` exists.

### Performance Tips

- **Low latency**: Ensure good WiFi connection on both devices
- **Battery optimization**: Disable battery saver on mobile device
- **Screen timeout**: Increase screen timeout on mobile device for longer sessions

## ⚠️ CRITICAL SECURITY WARNINGS

### Data Privacy and Encryption

**IMPORTANT**: Muxile relays ALL terminal input/output through a third-party Cloudflare Worker.

**Encryption Status**:
- ✅ **Transport Encryption**: HTTPS/TLS between your devices and Cloudflare
- ❌ **End-to-End Encryption**: NO client-side encryption of terminal content
- ⚠️ **Data Exposure**: Cloudflare Worker can potentially read all terminal I/O

**Risk Assessment**:
- **HIGH RISK**: Passwords, API keys, secrets, credentials entered in terminal
- **MEDIUM RISK**: Source code, configuration files, internal documentation
- **LOW RISK**: Read-only operations, build logs, monitoring scripts

### Threat Model (STRIDE Framework)

1. **QR Code Interception (Spoofing)**
   - **Risk**: Attacker photographs QR code from your screen
   - **Impact**: Unauthorized access to current session
   - **Mitigation**: Generate QR codes in private environment, limit QR code display time

2. **Cloudflare Worker Compromise (Tampering)**
   - **Risk**: Third-party service logs or modifies terminal data
   - **Impact**: Data exposure, session hijacking
   - **Mitigation**: Never enter sensitive credentials, use self-hosted relay option

3. **Man-in-the-Middle Attack (Information Disclosure)**
   - **Risk**: WiFi network intercepts HTTPS traffic
   - **Impact**: Terminal content exposed to network attacker
   - **Mitigation**: Use trusted WiFi networks, VPN if available

4. **Mobile Device Compromise (Elevation of Privilege)**
   - **Risk**: Unlocked phone accessed by unauthorized person
   - **Impact**: Full terminal control and data access
   - **Mitigation**: Keep device locked, use biometric authentication

### Safe vs Unsafe Use Cases

✅ **SAFE Use Cases** (Recommended):
- **Code review**: Reading source code and documentation
- **Build monitoring**: Watching compilation, tests, deployment
- **Log analysis**: Reviewing application logs and output
- **Configuration viewing**: Reading config files (not editing)
- **Learning**: Following tutorials, documentation browsing

❌ **UNSAFE Use Cases** (Avoid):
- **Credential entry**: Passwords, API keys, tokens, secrets
- **Production access**: Database connections, server administration
- **Sensitive configuration**: Editing files with credentials
- **User management**: Creating/modifying user accounts
- **Security operations**: Firewall rules, access control changes

### Compliance Notes

**NOT SUITABLE FOR**:
- **GDPR**: Processing personal data of EU citizens
- **HIPAA**: Protected health information (PHI)
- **PCI DSS**: Payment card industry data
- **SOX**: Financial reporting and controls
- **Corporate secrets**: Intellectual property, trade secrets

**ALWAYS USE**:
- **Development environments**: Non-production systems
- **Public information**: Open source code, documentation
- **Test data**: Sample data, mock credentials
- **Educational purposes**: Learning, training materials

### Mandatory Security Practices

**BEFORE Using Muxile**:
- [ ] Verify you're on a trusted WiFi network (not public/guest)
- [ ] Ensure no one can see your screen when generating QR code
- [ ] Confirm terminal session contains NO sensitive operations
- [ ] Understand data passes through Cloudflare Worker unencrypted

**DURING Use**:
- [ ] Keep mobile device locked when not actively viewing terminal
- [ ] Monitor for unexpected commands (potential session hijacking)
- [ ] Close browser tab immediately when done viewing

**AFTER Use**:
- [ ] Toggle Muxile off (Ctrl+B then T again)
- [ ] Kill tmux session when completely done: `tmux kill-session -t devstream-sonnet`
- [ ] Clear mobile browser history/cache (optional, for privacy)

### Emergency Disconnect Procedure

If you suspect session compromise:

1. **Immediate Action**:
   ```bash
   # Kill session immediately
   tmux kill-session -t devstream-sonnet
   tmux kill-session -t devstream-glm
   ```

2. **Verify Termination**:
   ```bash
   # Confirm no active sessions
   tmux list-sessions
   ```

3. **Audit Recent Activity**:
   ```bash
   # Check for exposed credentials
   history | grep -i "password\|api\|key\|token\|secret"

   # Review recent commands
   history | tail -50
   ```

4. **Rotate Compromised Credentials**:
   - Change any passwords entered during session
   - Rotate API keys used in terminal
   - Update access tokens
   - Revoke any shared credentials

5. **Document Incident**:
   ```bash
   # Log security incident
   echo "Session compromised at $(date): [details]" >> ~/.devstream/security-incidents.log
   ```

6. **Prevent Recurrence**:
   - Use self-hosted relay option for sensitive work
   - Implement stricter session timeout policies
   - Consider VPN for additional transport security

### Risk Acceptance Checklist

**By using Muxile, you acknowledge**:

- [ ] I understand terminal data passes through Cloudflare Worker
- [ ] I will NOT enter passwords, API keys, or sensitive data in Muxile sessions
- [ ] I will use Muxile ONLY for non-production, non-sensitive tasks
- [ ] I accept the risk of third-party data exposure
- [ ] I will disconnect sessions immediately after use
- [ ] I understand QR code URLs provide unauthenticated access

**If you cannot accept these risks**, DO NOT use Muxile. Use standard desktop access only.

## Security Considerations

### Data Privacy
- **Encryption**: Data relayed through Cloudflare Workers (HTTPS)
- **Session isolation**: Each session gets unique UUID
- **No persistence**: Connections terminate when session ends

### Best Practices
- **Private WiFi**: Use trusted network connections
- **Session management**: Kill sessions when done
- **Access control**: QR codes provide one-time access to specific session

## Limitations

### Current MVP Scope
- **Terminal I/O only**: No DevStream state sync to mobile
- **Browser-based**: No native mobile app
- **Internet required**: Uses Cloudflare Worker relay

### Known Issues
- **Cosmetic rendering**: Minor display glitches on mobile
- **Connection drops**: WiFi interruptions require QR rescan
- **Large outputs**: Very large command outputs may lag on mobile

## Future Enhancements

### Phase 2 (Post-MVP)
- **Mobile UI**: Custom mobile interface for DevStream features
- **State sync**: Task list and memory search on mobile
- **Offline mode**: Local tmux sessions without internet
- **Self-hosted relay**: Replace Cloudflare Worker with personal server

### Migration Path
- **tmate integration**: Self-hosted option for full control
- **Native mobile app**: iOS/Android apps for better UX
- **End-to-end encryption**: Client-side encryption option

## Support

### Issues and Questions
- **Documentation**: Check this guide first
- **Logs**: Review `~/.claude/logs/devstream/` for hook issues
- **Community**: Refer to Muxile and tmux documentation

### Resources
- **Muxile GitHub**: https://github.com/bjesus/muxile
- **tmux Documentation**: https://github.com/tmux/tmux/wiki
- **DevStream Project**: Internal documentation

---

**Installation Time**: ~15 minutes
**MVP Validation**: ✅ All acceptance criteria passed
**Hook Preservation**: ✅ DevStream hooks work normally with Muxile
**Mobile Access**: ✅ QR code → browser → terminal streaming functional