# GLM-4.6 Handoff Prompt: Security Hardening - Muxile Integration

**Handoff Date**: 2025-10-10
**From**: Sonnet 4.5 (Architectural Planning + Research)
**To**: GLM-4.6 (Precise Execution)
**Related Task ID**: 8a53fbdae122dd843f36deb9c090301d (Muxile Integration)
**Implementation Plan**: `docs/development/plan/piano_security-hardening-muxile.md`

---

## 🎯 Mission

Execute **mandatory security fixes** for Muxile mobile integration identified by @code-reviewer. Apply fixes to wrapper scripts (command injection, error handling) and documentation (security warnings, threat model) to achieve production-ready status.

---

## 📋 Context Transfer (Complete Session Summary)

### **Problem Statement**

**@code-reviewer blocked commit** due to 3 HIGH/MEDIUM severity security issues:

1. **Command Injection** (CVSS 8.5) - Wrapper scripts execute `start-devstream.sh` without validation
2. **Data Privacy Documentation** (Impact 7.5) - Users unaware of Cloudflare relay data exposure
3. **Insufficient Error Handling** (Impact 6.5) - No `set -euo pipefail`, no retry logic, no logging

**Decision**: User approved Option A (Fix Now) - implement all fixes before commit (65 min estimated).

---

### **Architecture Context** ✅

**Muxile Integration (Already Implemented by GLM-4.6 earlier)**:
- tmux-based mobile access via QR code (NO PTY interference)
- Cloudflare Worker relay (WebSocket, HTTPS transport)
- Preserves DevStream hooks (verified in testing)
- Multi-model support: 2 wrapper scripts (`devstream-sonnet`, `devstream-glm`)

**Files Created** (already exist):
- `/Users/fulvioventura/bin/devstream-sonnet` (49 lines, needs hardening)
- `/Users/fulvioventura/bin/devstream-glm` (49 lines, needs hardening)
- `docs/guides/devstream-mobile-access-muxile.md` (328 lines, needs security warnings)

**Current Status**: Implementation complete, @code-reviewer found security gaps, fixes required before merge.

---

### **@code-reviewer Findings** ✅ (MANDATORY Fixes)

**Issue 1: Command Injection** (Location: wrapper scripts line 32)
```bash
# CURRENT (UNSAFE):
$TMUX_CMD new-session -d -s "$SESSION_NAME" "./start-devstream.sh restart anthropic"

# RISK: Attacker replaces start-devstream.sh with malicious code
# FIX: Validate script existence, ownership (must match current user), permissions (not world-writable)
```

**Issue 2: Data Privacy Documentation** (Location: docs line 274-285)
```markdown
# CURRENT (VAGUE):
"Data relayed through Cloudflare Workers (HTTPS)"

# RISK: Users may unknowingly expose API keys/passwords via Cloudflare relay
# FIX: Add "CRITICAL SECURITY WARNINGS" section with:
  - NO end-to-end encryption (Cloudflare can read terminal data)
  - Threat model (STRIDE: QR interception, Cloudflare compromise, MITM, mobile device access)
  - Safe vs Unsafe use cases (explicit examples)
  - Compliance notes (NOT suitable for GDPR, HIPAA, PCI DSS)
  - Emergency disconnect procedure
```

**Issue 3: Insufficient Error Handling** (Location: multiple)
```bash
# MISSING:
set -euo pipefail  # Line 1 - strict error handling

# MISSING: tmux binary validation (line 18)
if [[ ! -x "$TMUX_CMD" ]]; then exit 1; fi

# MISSING: PROJECT_DIR validation (line 9)
if [[ ! -d "$PROJECT_DIR" ]]; then exit 1; fi

# ARBITRARY SLEEP (line 36):
sleep 3  # No retry mechanism, no timeout

# MISSING: Cleanup trap + logging (no audit trail)
```

---

### **Research Findings** ✅ (Context7 + Web Search)

**Source 1: Web Search** (2024 Security Best Practices)
- Command injection vulnerabilities increased 2,348 → 2,600 (2024)
- File validation: whitelist approach, verify ownership + permissions
- Error handling: `set -euo pipefail` standard defensive practice
- Retry logic: timeout with incremental backoff (15s recommended)
- Logging: "always log steps and errors for debugging"

**Source 2: Context7 - ShellCheck** (/koalaman/shellcheck - Trust Score 8.2)
```bash
# Secure find -exec pattern (prevents command injection)
find . -type f -exec sh -c 'cat "$1" | wc -l' _ {} \;

# set -e with command substitution
shopt -s inherit_errexit  # Ensures -e works in $()

# File validation pattern
stat -f "%u" "$SCRIPT"  # Get owner UID
stat -f "%Lp" "$SCRIPT"  # Get permissions
```

**Source 3: Context7 - Bats-core** (/bats-core/bats-core - Trust Score 7.0)
```bash
# Teardown cleanup pattern
teardown() { rm -f /tmp/test-file; }

# Signal handling (UPPERCASE names)
trap - INT EXIT  # Correct (not "int exit")

# Conditional cleanup (status check)
if [[ -n "$BATS_TEST_COMPLETED" ]]; then echo "Success"; fi
```

**Source 4: OWASP Mobile Top 10 2024**
- #3: Insecure Communication (relevant for Muxile relay)
- 35% of iOS vulnerabilities HIGH/CRITICAL
- STRIDE threat modeling framework recommended

---

### **Decisions Log** ✅

**Decision 1**: Apply ALL 4 mandatory fixes (not partial)
- **Rationale**: @code-reviewer blocks commit without complete fixes, command injection is HIGH severity
- **Alternative Rejected**: Partial fixes (defer documentation) - unacceptable user risk

**Decision 2**: Use research-backed patterns (ShellCheck + Bats-core)
- **Rationale**: Context7 libraries (Trust Score 7.0-8.2) validated by community
- **Evidence**: ShellCheck has 1125 code snippets, Bats-core 177 snippets

**Decision 3**: Add comprehensive security documentation (not minimal)
- **Rationale**: OWASP Mobile Top 10 emphasizes threat modeling, user awareness critical
- **Evidence**: 2024 mobile malware increased 39 new families in Q1

**Decision 4**: Strategic Choice Gate → GLM-4.6 Handoff
- **Rationale**: Sonnet completed research/planning (Steps 1-5), GLM excels at precise execution (Step 6)
- **Cost Optimization**: ~70% savings for implementation phase

---

## 🚀 Your Mission (GLM-4.6 Execution)

### **Phase 1: Wrapper Script Hardening** (40 min)

**Your Task**: Apply 8 micro-tasks from implementation plan sequentially.

**Micro-Task 1.1** (5 min): Add strict error handling
```bash
# File: /Users/fulvioventura/bin/devstream-sonnet
# Location: After line 1 (#!/bin/bash)

set -euo pipefail  # Exit on error, undefined vars, pipeline failures
```

**Micro-Task 1.2** (10 min): Add start-devstream.sh validation
```bash
# File: /Users/fulvioventura/bin/devstream-sonnet
# Location: After line 17, before cd "$PROJECT_DIR"

STARTUP_SCRIPT="$PROJECT_DIR/start-devstream.sh"

# Validate existence
if [[ ! -f "$STARTUP_SCRIPT" ]]; then
    echo "❌ Error: start-devstream.sh not found: $STARTUP_SCRIPT"
    exit 1
fi

# Validate ownership (must match current user)
SCRIPT_OWNER=$(stat -f "%u" "$STARTUP_SCRIPT")
if [[ "$SCRIPT_OWNER" != "$(id -u)" ]]; then
    echo "❌ Security Error: start-devstream.sh not owned by current user"
    echo "Expected owner: $(id -u), Actual owner: $SCRIPT_OWNER"
    exit 1
fi

# Validate permissions (not world-writable)
SCRIPT_PERMS=$(stat -f "%Lp" "$STARTUP_SCRIPT")
if [[ "$SCRIPT_PERMS" =~ [0-9][0-9][2-7] ]]; then
    echo "❌ Security Error: start-devstream.sh is world-writable (permissions: $SCRIPT_PERMS)"
    echo "Fix with: chmod 755 $STARTUP_SCRIPT"
    exit 1
fi
```

**Micro-Task 1.3** (10 min): Add retry logic with timeout
```bash
# File: /Users/fulvioventura/bin/devstream-sonnet
# Location: Replace line 36 (sleep 3)

echo "⏳ Waiting for DevStream to initialize..."

TIMEOUT=15
ELAPSED=0
while ! $TMUX_CMD has-session -t "$SESSION_NAME" 2>/dev/null; do
    if [[ $ELAPSED -ge $TIMEOUT ]]; then
        echo "❌ Timeout waiting for DevStream session to start"
        echo "Check logs for errors"
        exit 1
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done
```

**Micro-Task 1.4** (15 min): Add cleanup trap + logging
```bash
# File: /Users/fulvioventura/bin/devstream-sonnet
# Location: After line 5 (set -euo pipefail)

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

# ALSO: Replace all "echo" statements with "log" for audit trail
```

**Micro-Task 2.1** (20 min): Apply same fixes to devstream-glm
- Repeat Micro-Tasks 1.1-1.4 for `/Users/fulvioventura/bin/devstream-glm`
- Only difference: `restart glm` instead of `restart anthropic`

---

### **Phase 2: Documentation Enhancement** (25 min)

**Micro-Task 3.1** (10 min): Add CRITICAL SECURITY WARNINGS
```markdown
# File: docs/guides/devstream-mobile-access-muxile.md
# Location: After line 273, BEFORE "Security Considerations"

## ⚠️ CRITICAL SECURITY WARNINGS

### Data Privacy and Encryption

**IMPORTANT**: Muxile relays ALL terminal input/output through a third-party Cloudflare Worker.

**Encryption Status**:
- ✅ **Transport Encryption**: HTTPS/TLS between your devices and Cloudflare
- ❌ **End-to-End Encryption**: NO client-side encryption of terminal content
- ⚠️ **Data Exposure**: Cloudflare Worker can potentially read all terminal I/O

(See implementation plan for full text - 150 lines)
```

**Micro-Task 3.2** (10 min): Add Threat Model + Safe/Unsafe Use Cases
```markdown
### Threat Model (STRIDE Framework)

1. **QR Code Interception (Spoofing)** - Risk: Attacker photographs QR
2. **Cloudflare Worker Compromise (Tampering)** - Risk: Third-party logs data
3. **Man-in-the-Middle Attack (Information Disclosure)** - Risk: WiFi MITM
4. **Mobile Device Compromise (Elevation of Privilege)** - Risk: Unlocked phone

### Safe vs Unsafe Use Cases

✅ SAFE: Viewing build logs, monitoring scripts (read-only)
❌ UNSAFE: Entering passwords, API keys, accessing production

(See implementation plan for full examples)
```

**Micro-Task 3.3** (5 min): Add Emergency Disconnect Procedure
```markdown
### Emergency Disconnect Procedure

If you suspect session compromise:

```bash
# 1. Kill session immediately
tmux kill-session -t devstream-sonnet

# 2. Verify terminated
tmux list-sessions

# 3. Rotate credentials
history | grep -i "password\|api\|key\|token"

# 4. Document incident
echo "Session compromised at $(date)" >> ~/.devstream/security-incidents.log
```

(See implementation plan for complete procedure)
```

---

## ✅ Acceptance Criteria (MANDATORY)

**Before @code-reviewer re-approval**:

- [ ] 1. `set -euo pipefail` in both wrapper scripts
- [ ] 2. `start-devstream.sh` validated (existence, ownership, permissions)
- [ ] 3. Retry logic (15s timeout) replaces `sleep 3`
- [ ] 4. Cleanup trap + logging added (audit trail)
- [ ] 5. Both Sonnet + GLM wrappers hardened identically
- [ ] 6. CRITICAL SECURITY WARNINGS section added to docs
- [ ] 7. Threat model (STRIDE) + safe/unsafe use cases documented
- [ ] 8. Emergency disconnect procedure added
- [ ] 9. All `echo` replaced with `log` in wrapper scripts
- [ ] 10. Validation tests executed (see implementation plan)

---

## 🔍 Validation Steps (MANDATORY After Implementation)

**Test 1**: Security validation works
```bash
# Test ownership check (should fail)
sudo chown root ~/bin/devstream-sonnet
devstream-sonnet  # Expect: "Security Error: not owned by current user"
sudo chown $(whoami) ~/bin/devstream-sonnet  # Restore

# Test permissions check (should fail)
chmod 777 /Users/fulvioventura/devstream/start-devstream.sh
devstream-sonnet  # Expect: "Security Error: world-writable"
chmod 755 /Users/fulvioventura/devstream/start-devstream.sh  # Restore
```

**Test 2**: Retry logic works
```bash
# Test timeout (should fail after 15s)
mv /Users/fulvioventura/devstream/start-devstream.sh /tmp/start-devstream.sh.bak
devstream-sonnet  # Expect: "Timeout waiting for session"
mv /tmp/start-devstream.sh.bak /Users/fulvioventura/devstream/start-devstream.sh  # Restore
```

**Test 3**: Logging works
```bash
# Verify log file created
ls ~/.devstream/logs/wrapper-$(date +%Y%m%d).log

# Check log entries
tail -20 ~/.devstream/logs/wrapper-$(date +%Y%m%d).log
```

**Test 4**: Documentation complete
```bash
# Verify sections added
grep -n "CRITICAL SECURITY WARNINGS" docs/guides/devstream-mobile-access-muxile.md
grep -n "Threat Model" docs/guides/devstream-mobile-access-muxile.md
grep -n "Emergency Disconnect" docs/guides/devstream-mobile-access-muxile.md
```

---

## 🚨 Critical Constraints

1. **NEVER skip validation tests** - @code-reviewer will re-check security
2. **NEVER commit before @code-reviewer approval** - violates Protocol v2.2.0
3. **Follow implementation plan EXACTLY** - research-backed patterns
4. **Test after EACH micro-task** - immediate detection of issues
5. **Document in TodoWrite** - mark "in_progress" → "completed" sequentially

---

## 🎯 Success Metrics

**MVP Success** = @code-reviewer approval after fixes:
1. NO HIGH/CRITICAL security issues remaining
2. All 10 acceptance criteria pass
3. Validation tests execute successfully
4. @code-reviewer status: APPROVED (not CONDITIONAL APPROVAL)

**Estimated Duration**: 65 minutes (validated by @code-reviewer report)

---

## 🔄 Next Steps After Completion

1. **Re-invoke @code-reviewer** (MANDATORY):
   ```bash
   # Use Task tool to invoke @code-reviewer agent
   # Provide files: ~/bin/devstream-{sonnet,glm}, docs/guides/devstream-mobile-access-muxile.md
   ```

2. **Address findings** (if any):
   - If @code-reviewer finds remaining issues, fix immediately
   - Re-invoke until APPROVED status achieved

3. **Commit with Security Message**:
   ```bash
   git add ~/bin/devstream-sonnet ~/bin/devstream-glm
   git add docs/guides/devstream-mobile-access-muxile.md
   git add docs/development/plan/piano_security-hardening-muxile.md
   git add docs/development/plan/handoff_security-hardening-muxile.md

   git commit -m "$(cat <<'EOF'
   security: Harden Muxile integration (fixes command injection, adds security docs)

   Applies @code-reviewer mandatory fixes:
   - Command injection prevention: validate start-devstream.sh ownership/permissions
   - Error handling: add set -euo pipefail, retry logic, cleanup trap, logging
   - Security documentation: CRITICAL WARNINGS, STRIDE threat model, safe/unsafe use cases
   - Emergency disconnect procedure for incident response

   Fixes: HIGH severity command injection (CVSS 8.5), data privacy risks (Impact 7.5)
   Research: ShellCheck + Bats-core patterns (Context7), OWASP Mobile Top 10 2024
   Testing: Ownership/permissions/retry validation executed successfully

   🤖 Generated with Claude Code
   Co-Authored-By: Claude <noreply@anthropic.com>
   EOF
   )"
   ```

4. **Push to GitHub** (if user approves):
   ```bash
   git push origin release/v0.1.0-beta
   ```

5. **Update Task Status**:
   - Mark Muxile integration task as "completed"
   - Store learnings in DevStream memory

---

## 💡 GLM-4.6 Execution Tips

**Your Strengths** (why you were chosen):
- ✅ **Precise execution**: Follow implementation plan micro-tasks exactly
- ✅ **Tool calling**: 90.6% accuracy (excellent for file edits)
- ✅ **Cost-optimized**: ~70% cheaper than Sonnet for implementation
- ✅ **Syntax precision**: Fewer bash errors, cleaner scripts

**Avoid**:
- ❌ Architectural decisions (already made by Sonnet)
- ❌ Deviating from implementation plan (follow sequentially)
- ❌ Skipping validation steps (@code-reviewer WILL re-check)
- ❌ Committing before @code-reviewer approval (Protocol violation)

**When Stuck**:
- Re-read implementation plan micro-task
- Check troubleshooting section
- Verify prerequisites (file paths correct)
- Review @code-reviewer findings in this handoff

---

**Ready to Execute!** 🚀

Start with Micro-Task 1.1 (Add `set -euo pipefail` to devstream-sonnet). Mark TodoWrite as "in_progress" and begin implementation.

Good luck, GLM-4.6! You've got this. 💪
