# 🚀 DevStream Task Handoff: Fix Multi-Project Installation & Launcher System

**FROM**: Claude Sonnet 4.5 (Strategic Planning Complete)
**TO**: GLM-4.6 (Implementation Execution)

---

## 📊 TASK CONTEXT

**Task ID**: `e54c3e46-91ed-4aca-bf28-284034e547d5`
**Phase**: Implementation
**Priority**: 10/10
**Status**: Steps 1-5 COMPLETED by Sonnet 4.5 → Steps 6-7 DELEGATED to you

**Your Role**: You are an **expert execution-focused coding agent**. Sonnet 4.5 has completed all strategic planning. Your job is **precise implementation** according to the approved plan.

---

## ✅ WORK COMPLETED (Steps 1-5)

- ✅ **DISCUSSION**: Problem analyzed (4 critical bugs identified), approach agreed
- ✅ **ANALYSIS**: Root cause documented - hardcoded SCRIPT_DIR logic in launchers
- ✅ **RESEARCH**: Context7 findings complete (Poetry, npm, pyenv, direnv patterns)
- ✅ **PLANNING**: Detailed implementation plan created with 10 micro-tasks
- ✅ **APPROVAL**: User approved universal upward search solution

---

## 📋 YOUR IMPLEMENTATION PLAN

**COMPLETE PLAN**: `docs/development/plan/piano_fix-multi-project-installation.md`

**READ THE PLAN FIRST** using:
```bash
cat docs/development/plan/piano_fix-multi-project-installation.md
```

**Plan Summary**:

**Problem**: DevStream launchers (`start-devstream.sh`, `start-claude-zai.sh`) force working directory to `/Users/fulvioventura/devstream` instead of detecting current project. Causes:
1. `exc-to-pdf` project uses wrong database (devstream's 644MB instead of own 324KB)
2. Hooks execute in wrong project context
3. Silent failure - works but with wrong data

**Solution**: Implement **universal upward search** (like npm, pyenv, git) to auto-detect project root from any directory.

**10 Micro-Tasks**:
1. Create `find_devstream_project_root()` bash function (60 min)
2. Replace PROJECT_ROOT logic with upward search (45 min)
3. Add `validate_devstream_project()` for safety (30 min)
4. Add `print_project_info()` for user feedback (15 min)
5. Apply to `start-claude-zai.sh` (45 min)
6. Remove spurious venv from utils/ (10 min)
7. Fix `install-devstream.sh` to prevent venv copy (30 min)
8. Create E2E tests (45 min)
9. Test with 3+ real projects (30 min)
10. Validate database isolation (30 min)

**Total**: 4-6 hours

---

## 🎯 YOUR MISSION (Steps 6-7)

### Step 6: IMPLEMENTATION
- Execute micro-tasks **one at a time** (use TodoWrite)
- Follow plan specifications **exactly**
- Mark "in_progress" → work → "completed" per task
- Run validation **after each task**
- **NEVER** mark completed with failing validation

### Step 7: VERIFICATION
- **Manual testing** with 3+ real projects
- **E2E integration tests** passing
- **ShellCheck** validation (zero errors)
- **Database isolation** verified
- **No cross-project contamination**

---

## 🔧 DEVSTREAM PROTOCOL COMPLIANCE (MANDATORY)

**CRITICAL RULES** (from @CLAUDE.md):

### Python Environment
```bash
# ALWAYS use .devstream venv
.devstream/bin/python script.py       # ✅ CORRECT
python script.py                       # ❌ FORBIDDEN
```

### TodoWrite Workflow
1. Mark first task "in_progress"
2. Implement according to plan
3. Run validation commands
4. Mark "completed" ONLY when:
   - Validation passes 100%
   - Acceptance criteria met
5. Proceed to next task

### Shell Script Best Practices
```bash
# Use exact patterns from plan
#!/usr/bin/env bash  # ✅ Portable shebang
set -e               # ✅ Exit on error

# Test all functions before marking complete
source script.sh && test_function && echo "PASS" || echo "FAIL"
```

---

## 📚 CONTEXT7 RESEARCH (Pre-Completed by Sonnet)

### Library 1: npm/package-directory (Upward Search)
**Pattern**: Find project root by searching upward for marker file
```javascript
async function findRoot(startDir = process.cwd()) {
    let dir = startDir;
    while (dir !== '/') {
        if (await exists(`${dir}/package.json`)) return dir;
        dir = path.dirname(dir);
    }
    return undefined;
}
```
**Apply to**: `find_devstream_project_root()` searches for `.env.devstream`

### Library 2: pyenv (Priority Resolution)
**Pattern**: Multi-level priority for version selection
```bash
1. PYENV_VERSION (explicit override)
2. .python-version in current dir
3. .python-version in parent dirs (upward)
4. Global ~/.pyenv/version
5. System fallback
```
**Apply to**: Priority 1=DEVSTREAM_PROJECT_ROOT, Priority 2=upward search, Priority 3=error

### Library 3: direnv (Auto-Loading)
**Pattern**: Load .envrc when entering directory, unload when leaving
```bash
cd ~/project
direnv: loading .envrc  # Automatic
```
**Apply to**: Load `.env.devstream` from detected project root

### Library 4: Poetry (Per-Project Venvs)
**Pattern**: Each project has isolated `.venv/` with own dependencies
```bash
# Config: virtualenvs.in-project = true
# Result: project1/.venv, project2/.venv (isolated)
```
**Apply to**: Each DevStream project has `.devstream/` venv + `data/devstream.db`

---

## 🏗️ TECHNICAL SPECIFICATIONS

**Files to Modify**:
1. `start-devstream.sh` (lines 40-50, add 3 functions)
2. `scripts/start-claude-zai.sh` (lines 13-25, 94)
3. `scripts/install-devstream.sh` (hook copying section)

**Files to Create**:
1. `tests/integration/test_multi_project_detection.sh` (E2E tests)
2. `validate_db_isolation.sh` (database isolation verification)

**Files to Remove**:
1. `/Users/fulvioventura/exc-to-pdf/.claude/hooks/devstream/utils/.devstream/` (spurious venv)

**Dependencies**: None (pure bash scripting)

---

## 🚨 CRITICAL CONSTRAINTS (DO NOT VIOLATE)

**FORBIDDEN ACTIONS**:
- ❌ **NO** hardcoding project names ("exc-to-pdf", etc.)
- ❌ **NO** hardcoding absolute paths
- ❌ **NO** workarounds (implement proper upward search)
- ❌ **NO** silent failures (error loudly if not in project)
- ❌ **NO** breaking backward compatibility

**REQUIRED ACTIONS**:
- ✅ **YES** universal solution (works for ANY project name)
- ✅ **YES** upward search from `pwd` (not SCRIPT_DIR)
- ✅ **YES** validation before proceeding
- ✅ **YES** clear error messages with 3 solution options
- ✅ **YES** preserve DEVSTREAM_PROJECT_ROOT explicit override
- ✅ **YES** test with 3+ real projects

---

## ✅ QUALITY GATES (Check Before Completion)

### 1. Manual Testing (3+ Projects)
```bash
# DevStream (original)
cd /Users/fulvioventura/devstream && ./start-devstream.sh --dry-run

# exc-to-pdf (existing)
cd /Users/fulvioventura/exc-to-pdf/src && ./start-devstream.sh --dry-run

# New project (fresh install)
mkdir /tmp/test-project && cd /tmp/test-project
/Users/fulvioventura/devstream/scripts/install-devstream.sh
./start-devstream.sh --dry-run

# Cleanup
rm -rf /tmp/test-project
```

### 2. E2E Integration Tests
```bash
chmod +x tests/integration/test_multi_project_detection.sh
./tests/integration/test_multi_project_detection.sh
# REQUIREMENT: All 4 tests pass
```

### 3. Database Isolation
```bash
bash validate_db_isolation.sh
# REQUIREMENT: Each project uses own database, no cross-contamination
```

### 4. ShellCheck Validation
```bash
shellcheck start-devstream.sh
shellcheck scripts/start-claude-zai.sh
shellcheck scripts/install-devstream.sh
# REQUIREMENT: Zero errors or warnings
```

### 5. Commit (if all gates pass)
```bash
git add start-devstream.sh scripts/start-claude-zai.sh scripts/install-devstream.sh \
        tests/integration/test_multi_project_detection.sh

git commit -m "$(cat <<'EOF'
fix(launcher): implement universal multi-project detection

Replace hardcoded SCRIPT_DIR fallback with intelligent upward search
based on Context7 best practices (npm, pyenv, direnv patterns).

Implementation:
- find_devstream_project_root() with upward search for .env.devstream
- validate_devstream_project() for safety checks
- print_project_info() for user feedback
- Updated start-devstream.sh and start-claude-zai.sh
- Fixed install-devstream.sh venv copy exclusion
- Added E2E integration tests

Quality:
- ✅ Manual testing: 3+ projects verified
- ✅ E2E tests: 4/4 passing
- ✅ Database isolation: Verified
- ✅ ShellCheck: Zero errors

Fixes multi-project installation bug (Task: e54c3e46-91ed-4aca-bf28-284034e547d5)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 📊 SUCCESS CRITERIA

- [ ] All 10 TodoWrite tasks completed
- [ ] Manual testing: 3+ projects working
- [ ] E2E tests: 4/4 passing
- [ ] Database isolation: Verified
- [ ] ShellCheck: Zero errors/warnings
- [ ] No hardcoded paths or project names
- [ ] Backward compatibility: DEVSTREAM_PROJECT_ROOT override works
- [ ] Clear error messages when not in project

---

## 🚀 EXECUTION CHECKLIST

1. [ ] **READ** complete plan: `cat docs/development/plan/piano_fix-multi-project-installation.md`
2. [ ] **START** Task 1: Mark TodoWrite "in_progress"
3. [ ] **IMPLEMENT** find_devstream_project_root() exactly as specified
4. [ ] **TEST** function manually (see acceptance criteria)
5. [ ] **COMPLETE** Task 1 when all criteria met
6. [ ] **REPEAT** steps 2-5 for Tasks 2-10
7. [ ] **VALIDATE** all quality gates pass
8. [ ] **COMMIT** if all tests pass

---

**READY TO IMPLEMENT?**

Start with Task 1. Implement the upward search function exactly as specified in the plan. Test thoroughly. Mark complete only when all acceptance criteria met. 🚀

**Remember**: You are GLM-4.6 - your strength is **precise execution** of well-defined tasks. The strategic thinking is done. Now execute flawlessly following the detailed plan. 💪

**Key Success Factors**:
- Follow function signatures EXACTLY
- Test AFTER each task
- Use acceptance criteria as checklist
- No early completion (verify all criteria)
- Clear error messages (see examples in plan)
- Universal solution (no hardcoding)
