# GLM-4.6 Handoff Prompt: Integrate Muxile Mobile Access

**Handoff Date**: 2025-10-10
**From**: Sonnet 4.5 (Architectural Planning)
**To**: GLM-4.6 (Precise Execution)
**Task ID**: 8a53fbdae122dd843f36deb9c090301d
**Implementation Plan**: `docs/development/plan/piano_integrate-muxile-mobile-access.md`

---

## 🎯 Mission

Execute the **Muxile MVP integration** for DevStream mobile access. Enable remote terminal control of Claude Code sessions (Sonnet 4.5 + GLM-4.6) from mobile devices via QR code, while preserving ALL DevStream hooks.

---

## 📋 Context Transfer (Complete Session Summary)

### **Problem Statement**
User requested integration of Happy mobile app (https://github.com/slopus/happy) with DevStream to enable mobile access to Claude Code sessions.

### **Architecture Analysis Completed** ✅

**Research Findings**:
1. **Happy Architecture**: 3 components (CLI wrapper, mobile app, relay server)
   - Uses PTY interception to capture Claude Code I/O
   - End-to-end encryption (TweetNaCl + AES-256-GCM)
   - WebSocket bidirectional sync

2. **CRITICAL ISSUE IDENTIFIED**: Happy PTY interception **breaks DevStream hooks**
   - DevStream hooks communicate via stdin/stdout
   - PTY interception captures/redirects I/O streams
   - Risk: Race conditions, hook timeouts, communication failures

3. **Alternative Solutions Researched**:
   - **Muxile**: tmux plugin, UNIX socket bridge, Cloudflare Worker relay ✅ CHOSEN
   - **termpair**: PTY fork (same risk as Happy) ❌ REJECTED
   - **tmate**: tmux fork, self-hosted option ⚠️ FUTURE (post-MVP)

4. **tmux Compatibility VALIDATED** ✅:
   - Claude Code works in tmux without breaking hooks
   - Community success: tmux-cli, Vibe Coding workflows
   - Hooks receive JSON via stdin normally in tmux
   - Minor cosmetic issues only (rendering glitches)

### **Architecture Decision** ✅

**Chosen Approach**: Muxile MVP (tmux-based, non-invasive)

**Why Muxile**:
- ✅ **NO PTY interference** (uses UNIX sockets + websocat bridge)
- ✅ **5-minute setup** (tmux plugin via TPM)
- ✅ **QR code mobile access** (no app required, browser-based)
- ✅ **Multi-model support** (2 separate tmux sessions)
- ✅ **Encryption** (Cloudflare Worker HTTPS relay)

**Trade-offs Accepted**:
- ⚠️ **Third-party dependency** (Cloudflare Worker - acceptable for MVP)
- ⚠️ **Encryption unclear** (docs don't specify, assume HTTPS only)
- ⚠️ **Young project** (2023, less mature than tmate)

**Future Migration Path**: tmate self-hosted (after MVP validation)

### **Multi-Model Strategy** ✅

**2 tmux sessions approach**:
```bash
# Session 1: Sonnet 4.5
tmux new-session -s devstream-sonnet \
  "cd /Users/fulvioventura/devstream && ./start-devstream.sh restart anthropic"

# Session 2: GLM-4.6
tmux new-session -s devstream-glm \
  "cd /Users/fulvioventura/devstream && ./start-devstream.sh restart glm"
```

**Mobile Access**: 2 separate QR codes (one per session)

---

## 📝 Decisions Log (Context7 Research-Backed)

### **Decision 1**: Reject Happy Integration
- **Reason**: PTY interception breaks DevStream hooks (non-negotiable)
- **Evidence**: Happy uses `pty.fork()` (same as termpair - unsafe)
- **Alternative**: tmux-based solutions preserve process I/O

### **Decision 2**: Choose Muxile over tmate for MVP
- **Reason**: Faster setup (plugin vs build), good enough for validation
- **Trade-off**: Third-party relay (acceptable for MVP, migrate later)
- **Evidence**: Muxile uses websocat + UNIX sockets (non-invasive)

### **Decision 3**: Multi-Model via Separate Sessions
- **Reason**: Simplest approach, clean separation, no shared state
- **Alternative Rejected**: Single session with model switching (complex)
- **Implementation**: 2 wrapper scripts (`devstream-sonnet`, `devstream-glm`)

### **Decision 4**: Approve MVP Scope
- **Scope**: Terminal I/O streaming only (no DevStream state sync)
- **Rationale**: Validate concept before building custom mobile UI
- **Future**: Mobile task list, memory search (Phase 2)

---

## 🚀 Your Mission (GLM-4.6 Execution)

### **Phase 1: Environment Setup** (15 min)

Execute Micro-Tasks 1.1-1.2 from implementation plan:

1. **Install tmux** (if missing):
   ```bash
   which tmux || brew install tmux
   tmux -V  # Verify >= 2.6
   ```

2. **Install dependencies**:
   ```bash
   brew install qrencode jq websocat
   # Verify all installed
   qrencode --version && jq --version && websocat --version
   ```

**Validation**: All commands return version numbers

---

### **Phase 2: Muxile Installation** (10 min)

Execute Micro-Tasks 2.1-2.2:

1. **Install TPM**:
   ```bash
   git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm

   # Add to ~/.tmux.conf
   cat >> ~/.tmux.conf << 'EOF'
   set -g @plugin 'tmux-plugins/tpm'
   set -g @plugin 'bjesus/muxile'
   run '~/.tmux/plugins/tpm/tpm'
   EOF

   ~/.tmux/plugins/tpm/bin/install_plugins
   ```

2. **Verify Muxile loaded**:
   ```bash
   tmux source ~/.tmux.conf
   tmux list-keys | grep muxile
   # Expected: "bind-key T ..."
   ```

**Validation**: Muxile plugin directory exists, keybinding registered

---

### **Phase 3: DevStream Integration** (20 min)

Execute Micro-Tasks 3.1-3.2:

1. **Test hooks in tmux**:
   ```bash
   tmux new-session -d -s devstream-test \
     "cd /Users/fulvioventura/devstream && ./start-devstream.sh restart anthropic"
   tmux attach -t devstream-test

   # Inside tmux: Run Write tool, then detach (Ctrl+B D)
   # Check logs
   tail -50 ~/.claude/logs/devstream/hook_execution.log
   # Look for: PreToolUse, PostToolUse, NO errors

   tmux kill-session -t devstream-test
   ```

2. **Create wrapper scripts**:
   ```bash
   mkdir -p ~/bin

   # Create devstream-sonnet (see implementation plan for full script)
   # Create devstream-glm (see implementation plan for full script)

   chmod +x ~/bin/devstream-*

   # Add ~/bin to PATH if needed
   echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
   source ~/.zshrc
   ```

**Validation**: Hooks execute normally, wrapper scripts functional

---

### **Phase 4: Mobile Access** (15 min)

Execute Micro-Tasks 4.1-4.2:

1. **Generate QR code**:
   ```bash
   devstream-sonnet
   # Inside tmux: Press Ctrl+B then T
   # QR code appears in terminal
   ```

2. **Test from mobile**:
   - Scan QR code with phone camera
   - Browser opens with terminal view
   - Type on desktop → appears on mobile immediately
   - Type on mobile → appears on desktop immediately

**Validation**: Bidirectional I/O working, latency < 500ms

---

### **Phase 5: Validation** (20 min)

Execute Micro-Tasks 5.1-5.2:

1. **Verify hooks during remote access**:
   ```bash
   # With mobile connected:
   # Run DevStream commands (create task, write file)
   # Monitor: tail -f ~/.claude/logs/devstream/hook_execution.log
   # Verify: PreToolUse, PostToolUse execute normally
   ```

2. **Document setup** (create `docs/guides/devstream-mobile-access-muxile.md`):
   - Installation steps
   - Multi-model session management
   - QR code generation
   - Troubleshooting guide

**Validation**: All acceptance criteria pass (see implementation plan)

---

## ✅ Acceptance Criteria (MANDATORY)

**ALL of these MUST PASS before marking task complete**:

- [ ] 1. Hook Preservation: DevStream hooks execute normally in tmux
- [ ] 2. Mobile Access: QR code → mobile browser → terminal streaming
- [ ] 3. Bidirectional I/O: Desktop ↔ Mobile communication working
- [ ] 4. Multi-Model: Both Sonnet + GLM sessions accessible
- [ ] 5. Encryption: Cloudflare Worker HTTPS relay confirmed
- [ ] 6. Latency: < 500ms desktop → mobile delay
- [ ] 7. Stability: Session survives network reconnection
- [ ] 8. Documentation: Complete setup guide created

---

## 🔍 Quality Gates (Protocol v2.2.0)

### **Before Implementation**:
- [x] Context7 research completed (Muxile, termpair, tmate analyzed)
- [x] Architecture decision documented (Muxile MVP chosen)
- [x] Implementation plan created (`piano_integrate-muxile-mobile-access.md`)
- [x] Approval received (User confirmed MVP approach)

### **During Implementation**:
- [ ] TodoWrite: Mark tasks "in_progress" → work → "completed" (ONE at a time)
- [ ] Testing: Verify hooks after EACH phase
- [ ] Documentation: Update guide as you implement

### **After Implementation**:
- [ ] All acceptance criteria pass
- [ ] @code-reviewer validation (MANDATORY before commit)
- [ ] Test coverage: Manual testing documented
- [ ] Lessons learned: Document in DevStream memory

---

## 📁 File References

**Implementation Plan**: `docs/development/plan/piano_integrate-muxile-mobile-access.md`
**Handoff Prompt** (this file): `docs/development/plan/handoff_integrate-muxile-mobile-access.md`
**Hook Logs**: `~/.claude/logs/devstream/hook_execution.log`
**tmux Config**: `~/.tmux.conf`
**Wrapper Scripts**: `~/bin/devstream-sonnet`, `~/bin/devstream-glm`

---

## 🚨 Critical Constraints

1. **NEVER modify DevStream hooks** - they must work unmodified in tmux
2. **Verify hooks AFTER EACH PHASE** - immediate detection of issues
3. **Test both models** (Sonnet + GLM) - ensure no model-specific problems
4. **Document troubleshooting** - capture ALL issues encountered

---

## 🎯 Success Metrics

**MVP Success** = User can:
1. Launch DevStream session from desktop
2. Scan QR code with mobile phone
3. See Claude Code terminal output in mobile browser
4. Type commands from mobile keyboard
5. Verify DevStream hooks continue working
6. Switch between Sonnet 4.5 and GLM-4.6 sessions

**Estimated Duration**: 80 minutes (8 micro-tasks × 10-15 min)

---

## 🔄 Next Steps After Completion

1. **Git Commit**: After @code-reviewer validation
2. **Task Completion**: Mark task 8a53fbdae122dd843f36deb9c090301d as "completed"
3. **Session Summary**: SessionEnd hook will generate summary
4. **Future Enhancements**: Evaluate tmate migration (Phase 2)

---

## 💡 GLM-4.6 Execution Tips

**Your Strengths** (why you were chosen):
- ✅ **Precise execution**: Follow implementation plan exactly
- ✅ **Tool calling**: 90.6% accuracy (excellent for bash commands)
- ✅ **Cost-optimized**: ~70% cheaper than Sonnet for execution tasks
- ✅ **Syntax precision**: Fewer bash errors, cleaner scripts

**Avoid**:
- ❌ Architectural decisions (already made by Sonnet)
- ❌ Deviating from plan (follow micro-tasks sequentially)
- ❌ Skipping validation steps (hooks MUST be verified)

**When Stuck**:
- Re-read implementation plan micro-task
- Check troubleshooting section
- Verify prerequisites (dependencies installed)
- Check hook logs for errors

---

**Ready to Execute!** 🚀

Start with Phase 1, Micro-Task 1.1 (Install tmux). Mark TodoWrite as "in_progress" and begin implementation.

Good luck, GLM-4.6! You've got this. 💪
