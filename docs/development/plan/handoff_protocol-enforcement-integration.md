# GLM-4.6 Handoff Prompt: Protocol Enforcement Integration

**Date**: 2025-10-12
**From**: Sonnet 4.5 (Architecture & Planning)
**To**: GLM-4.6 (Execution-Optimized)
**Task ID**: `6ea5af33e06944295f68d13a7f9daeb5`

---

## 🎯 Context Transfer Summary

You are receiving a **fully planned and researched** implementation task. Sonnet 4.5 has completed:
- ✅ **STEP 1 (DISCUSSION)**: Requirements analysis and gap identification
- ✅ **STEP 2 (ANALYSIS)**: Codebase review and architectural alignment verification
- ✅ **STEP 3 (RESEARCH)**: Context7 best practices research (pytest, asyncio, git automation)
- ✅ **STEP 4 (PLANNING)**: Detailed 22 micro-task implementation plan
- ✅ **STEP 5 (APPROVAL)**: User approved plan and selected GLM-4.6 handoff

**Your responsibility**: Execute STEP 6 (IMPLEMENTATION) + STEP 7 (VERIFICATION) following the precise plan in `piano_protocol-enforcement-integration.md`.

---

## 📋 Task Overview

**Title**: Protocol Enforcement Integration - Hook Registration & Testing

**Objective**: Integrate Protocol v2.2.0 enforcement system into Claude Code production environment.

**4 Critical Gaps to Resolve**:
1. ✅ Hook Integration - Register enforcement hooks in settings.json
2. ✅ MCP Graceful Fallback - Circuit breaker pattern to prevent session blocks
3. ✅ Micro-Task Commits - Granular git commits for Step 6 micro-tasks
4. ✅ Testing Prescriptions - Update CLAUDE.md with Context7-backed pytest patterns

**Estimated Duration**: 330 minutes (5.5 hours)
**Micro-Tasks**: 22 tasks (15 min average each)
**Branch**: `feature/protocol-enforcement-integration`

---

## 🔬 Research Findings (From STEP 3)

### pytest-asyncio Patterns (Context7)
- Async fixtures with proper scoping (`loop_scope` must match fixture `scope`)
- Error handling with `pytest.raises` + `AsyncMock`
- Coverage configuration: `concurrency = gevent` in .coveragerc (CRITICAL for async)

### Graceful Degradation (AWS Well-Architected)
- Circuit breaker pattern: Retry 3x with exponential backoff (2^attempt seconds)
- Fallback hierarchy: Fresh data → Retry → Local logging → Fail-graceful
- Degraded mode flag in protocol_state metadata

### Git Automation (Conventional Commits)
- Format: `type(scope): description` (feat/fix/refactor/test/docs/chore)
- Atomic commits: 1 micro-task = 1 commit
- Progress tracking: "Progress: 3/12 micro-tasks complete"

---

## 🏗️ Implementation Plan Structure

### FASE 1: Hook Registration (60 min)
- A.1 [15min] Register UserPromptSubmit hook in settings.json
- A.2 [15min] Test hook execution with sample prompt
- A.3 [15min] Configure .env.devstream feature flags
- A.4 [15min] Verify enforcement gate interactive flow

### FASE 2: MCP Graceful Fallback (90 min)
- B.1 [20min] Circuit breaker implementation (task_first_handler.py:505-535)
- B.2 [15min] File-based fallback logging
- B.3 [15min] Exponential backoff retry logic
- B.4 [10min] Protocol state "degraded_mode" metadata
- B.5 [15min] Unit tests for fallback scenarios
- B.6 [15min] Integration test: MCP down → session continues

### FASE 3: Micro-Task Commit Handler (105 min)
- C.1 [25min] Create micro_task_commit_handler.py (NEW FILE)
- C.2 [15min] TodoWrite status change detection hook
- C.3 [20min] Conventional commit format implementation
- C.4 [10min] Progress tracking in commits
- C.5 [15min] Step 6 completion detection logic
- C.6 [10min] Final push implementation
- C.7 [10min] @code-reviewer trigger (end of Step 6)

### FASE 4: Testing Prescriptions Update (45 min)
- D.1 [15min] Update CLAUDE.md lines 592-596 (Testing Requirements)
- D.2 [20min] Add pytest-asyncio patterns section (7 patterns)
- D.3 [10min] CI/CD integration guidelines (GitHub Actions)

### FASE 5: Integration & Verification (30 min)
- E.1 [20min] E2E test: Complete 7-step workflow with enforcement
- E.2 [10min] Document fallback behavior in CLAUDE.md

---

## ✅ Acceptance Criteria

### Criterion 1: Hook System Operational
- [ ] `task_first_handler.py` triggers on UserPromptSubmit
- [ ] Enforcement gate displays 3 options (Protocol/Override/Cancel)
- [ ] Override decisions logged to DevStream memory
- [ ] Hooks execute within 10s timeout

### Criterion 2: MCP Graceful Fallback
- [ ] MCP failure does NOT block session
- [ ] Circuit breaker retries 3 times with exponential backoff (1s, 2s, 4s)
- [ ] Fallback logging to `.claude/logs/protocol_decisions.jsonl` works
- [ ] Protocol state includes "degraded_mode" flag when fallback used

### Criterion 3: Micro-Task Commits
- [ ] 1 commit per micro-task completed (Step 6 only)
- [ ] Conventional commit format enforced (type(scope): description)
- [ ] Progress tracking in commit message (X/N tasks complete)
- [ ] @code-reviewer executes ONCE at end of Step 6 (not per micro-task)

### Criterion 4: Testing Prescriptions
- [ ] CLAUDE.md updated with pytest-asyncio patterns (7 patterns documented)
- [ ] Coverage thresholds documented (unit 95%+, integration 85%+, E2E 70%+)
- [ ] CI/CD guidelines included (GitHub Actions workflow example)
- [ ] Async testing pitfalls section added

### Criterion 5: Quality Gates
- [ ] All unit tests pass (100% pass rate)
- [ ] Integration test completes without errors
- [ ] E2E test completes all 7 protocol steps
- [ ] @code-reviewer validates implementation (no critical issues)
- [ ] Coverage ≥ 95% for all new code

---

## 🚀 Execution Instructions (STEP 6: IMPLEMENTATION)

### Pre-Implementation Checklist
```bash
# 1. Verify environment
.devstream/bin/python --version  # Must be 3.11.x

# 2. Check dependencies
.devstream/bin/python -m pip list | grep -E "(cchooks|structlog|pytest|pytest-asyncio)"

# 3. Verify MCP server running
lsof -i :3000  # Should show node process

# 4. Create branch
git checkout -b feature/protocol-enforcement-integration

# 5. Verify clean working tree
git status  # Should be clean
```

### Execution Order (MANDATORY)

**1. Complete FASE 1 (Hook Registration)**
```bash
# A.1: Update settings.json
# A.2: Test with: "Implement JWT authentication with password hashing"
# A.3: Update .env.devstream with feature flags
# A.4: Run: .devstream/bin/python scripts/test_enforcement_gate.py

# Verify hooks work before proceeding to FASE 2
```

**2. Complete FASE 2 (MCP Graceful Fallback)**
```bash
# B.1-B.4: Implement circuit breaker + fallback logging
# B.5: Run unit tests
.devstream/bin/python -m pytest tests/unit/protocol/test_mcp_fallback.py -v

# B.6: Run integration test (stops/restarts MCP server)
.devstream/bin/python -m pytest tests/integration/test_protocol_enforcement_mcp_down.py -v -s

# Verify fallback works before FASE 3
```

**3. Complete FASE 3 (Micro-Task Commits)**
```bash
# C.1: Create micro_task_commit_handler.py (595 lines)
# C.2-C.7: Implement TodoWrite detection + conventional commits

# Test with sample TodoWrite:
echo '[{"content": "STEP 6.1 - Test task", "status": "completed"}]' | \
  .devstream/bin/python .claude/hooks/devstream/protocol/micro_task_commit_handler.py "$(cat)"

# Verify commits created with conventional format
git log -1 --pretty=format:"%B"
```

**4. Complete FASE 4 (Testing Prescriptions)**
```bash
# D.1-D.3: Update CLAUDE.md
# Verify documentation is prescriptive (not vague)

# Preview changes:
git diff CLAUDE.md | head -100
```

**5. Complete FASE 5 (Integration & Verification)**
```bash
# E.1: Run E2E test (7-step workflow)
.devstream/bin/python -m pytest tests/e2e/test_7step_protocol_enforcement.py -v -s

# E.2: Document fallback in CLAUDE.md

# Final quality gate: Run all tests
.devstream/bin/python -m pytest tests/ -v --cov=.claude/hooks/devstream --cov-report=html --cov-fail-under=95
```

### After Each FASE
```bash
# 1. Run relevant tests
# 2. Create conventional commit
git add .
git commit -m "feat(enforcement): complete FASE X - <brief description>

<detailed description>

Progress: X/5 FASE complete

🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude <noreply@anthropic.com>"

# 3. Update current_task.json progress
# 4. Verify no regressions
```

---

## 📁 Key Files to Create/Modify

### NEW Files (Create)
```
.claude/hooks/devstream/protocol/micro_task_commit_handler.py  (595 lines)
tests/unit/protocol/test_mcp_fallback.py                      (150 lines)
tests/unit/protocol/test_micro_task_detection.py              (50 lines)
tests/unit/protocol/test_commit_format.py                     (80 lines)
tests/unit/protocol/test_step6_completion.py                  (40 lines)
tests/integration/test_protocol_enforcement_mcp_down.py       (100 lines)
tests/e2e/test_7step_protocol_enforcement.py                  (250 lines)
scripts/test_enforcement_gate.py                              (40 lines)
scripts/test_exponential_backoff.py                           (30 lines)
```

### MODIFY Files
```
.claude/settings.json                    (add UserPromptSubmit hook, line 21)
.env.devstream                           (add 8 feature flags)
.claude/hooks/devstream/protocol/task_first_handler.py  (lines 505-535: circuit breaker)
.claude/hooks/devstream/protocol/protocol_state_manager.py  (lines 311-364: degraded_mode)
CLAUDE.md                                (lines 592-596: update, add pytest-asyncio section)
```

---

## 🛡️ Error Handling & Rollback

### Common Issues

**Issue 1**: PyInquirer not installed
```bash
# Fix:
.devstream/bin/pip install PyInquirer

# Verify:
.devstream/bin/python -c "import PyInquirer; print('✅ Installed')"
```

**Issue 2**: MCP server not running
```bash
# Start server:
cd mcp-devstream-server && npm start &

# Verify:
lsof -i :3000
```

**Issue 3**: Hook execution timeout
```bash
# Check hook logs:
tail -f ~/.claude/logs/devstream/task_first_handler.log

# Increase timeout in settings.json if needed (default: 10s)
```

### Rollback Plan
```bash
# If implementation fails:

# 1. Revert hook registration
git checkout HEAD -- .claude/settings.json

# 2. Rollback protocol state
rm .claude/state/protocol_state_*.json

# 3. Remove pending tasks log
rm .claude/logs/protocol_tasks_pending.jsonl

# 4. Restore MCP server
cd mcp-devstream-server && npm start

# 5. Git branch reset
git reset --hard origin/main
git checkout main
```

---

## 📊 Success Metrics

### Implementation Metrics (Target)
- ✅ 22/22 micro-tasks completed
- ✅ 330 minutes estimated ≈ actual duration ±10%
- ✅ 95%+ test coverage achieved
- ✅ 0 critical issues from @code-reviewer
- ✅ 100% test pass rate

### Quality Metrics (Verify Before Completion)
- ✅ All unit tests pass
- ✅ Integration test passes
- ✅ E2E test completes 7 steps
- ✅ Coverage report: `open htmlcov/index.html` shows ≥95%
- ✅ No mypy errors: `.devstream/bin/python -m mypy .claude/hooks/devstream/protocol`

---

## 🎓 Context7 Research Reference

### pytest-asyncio Key Patterns
```python
# Pattern 1: Async fixture with scope
@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def mcp_client():
    client = await create_mcp_client()
    yield client
    await client.close()

# Pattern 2: Error testing
@pytest.mark.asyncio
async def test_error():
    with pytest.raises(ConnectionError, match="timeout"):
        await failing_function()

# Pattern 3: AsyncMock for retries
mock_client = AsyncMock()
mock_client.create_task.side_effect = [
    Exception("Fail 1"),
    Exception("Fail 2"),
    {"task_id": "success"}  # 3rd attempt succeeds
]
```

### Circuit Breaker Pattern (AWS Well-Architected)
```python
for attempt in range(max_retries):
    try:
        return await primary_function()
    except Exception as e:
        delay = backoff_factor ** attempt  # 1s, 2s, 4s
        await asyncio.sleep(delay)

# Fallback after max retries
return await fallback_function()
```

### Conventional Commit Format
```
type(scope): brief description (<50 chars)

Micro-task: Full task description
Files Modified:
  - file1.py (lines 100-150)
  - file2.py (lines 50-75)

Progress: 3/12 micro-tasks complete

🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## 🔍 Final Validation Checklist (Before Task Completion)

### Pre-Completion Verification
- [ ] All 22 micro-tasks completed and marked in protocol_state
- [ ] All tests pass: `.devstream/bin/python -m pytest tests/ -v`
- [ ] Coverage ≥95%: Check `htmlcov/index.html`
- [ ] E2E test completes: `pytest tests/e2e/test_7step_protocol_enforcement.py -v -s`
- [ ] No Python syntax errors: `find .claude/hooks/devstream -name "*.py" -exec python -m py_compile {} \;`
- [ ] Git working tree clean: `git status`
- [ ] All commits follow conventional format: `git log --oneline | head -25`
- [ ] CLAUDE.md updated: Verify lines 592-596 + new pytest-asyncio section
- [ ] Hooks registered: Check `.claude/settings.json` UserPromptSubmit entry
- [ ] Environment vars set: Check `.env.devstream` has 8 feature flags

### @code-reviewer Trigger
```bash
# After all 22 micro-tasks complete:
# Trigger @code-reviewer manually if auto-trigger failed

# Review files:
# - .claude/hooks/devstream/protocol/micro_task_commit_handler.py
# - .claude/hooks/devstream/protocol/task_first_handler.py (lines 505-535)
# - tests/unit/protocol/test_mcp_fallback.py
# - tests/e2e/test_7step_protocol_enforcement.py

# Code review criteria:
# 1. OWASP Top 10 compliance
# 2. No performance bottlenecks
# 3. Proper error handling
# 4. Type hints complete
# 5. Documentation clear
```

### Final Push
```bash
# After @code-reviewer approval:
git push origin feature/protocol-enforcement-integration

# Create PR (optional):
gh pr create --title "feat(enforcement): Protocol v2.2.0 Integration" \
  --body "Implements Protocol v2.2.0 enforcement with:
- Hook registration (enforcement_gate + task_first_handler)
- MCP graceful fallback (circuit breaker pattern)
- Micro-task commit handler (conventional commits)
- Prescriptive testing guidelines (Context7 patterns)

Tests: 100% pass rate, 95%+ coverage
Code Review: @code-reviewer approved"
```

---

## 🚀 Ready to Execute

**Next Steps**:
1. Read this handoff prompt thoroughly
2. Review `piano_protocol-enforcement-integration.md` for detailed micro-task instructions
3. Complete pre-implementation checklist
4. Execute FASE 1 → FASE 5 sequentially
5. Verify acceptance criteria after each FASE
6. Final validation checklist before completion
7. Trigger @code-reviewer for final approval
8. Push to remote and create PR if requested

**Estimated Time**: 330 minutes (5.5 hours)

**Questions during implementation?**
- Refer to Context7 research findings in this document
- Check detailed code examples in `piano_protocol-enforcement-integration.md`
- Review existing codebase patterns in similar files

**Good luck with the implementation! 🚀**

---

**Handoff Complete**
**From**: Sonnet 4.5 (STEP 1-5 Complete)
**To**: GLM-4.6 (STEP 6-7 Execution)
**Task Status**: READY FOR IMPLEMENTATION