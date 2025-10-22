# 🚀 DevStream Task Handoff: Session Tracking System Rewrite - Context7-Based Simplified Architecture

**FROM**: Claude Sonnet 4.5 (Strategic Planning Complete)
**TO**: GLM-4.6 (Implementation Execution)

---

## 📊 TASK CONTEXT

**Task ID**: `session-tracking-rewrite-2025-10-13`
**Phase**: Implementation
**Priority**: 9/10
**Status**: Steps 1-5 COMPLETED by Sonnet 4.5 → Steps 6-7 DELEGATED to you

**Your Role**: You are an **expert execution-focused coding agent**. Sonnet 4.5 has completed all strategic planning. Your job is **precise implementation** according to the approved plan.

---

## ✅ WORK COMPLETED (Steps 1-5)

- ✅ **DISCUSSION**: Problem analyzed (10+ zombie sessions, double creation, zero tracking), trade-offs identified, approach agreed
- ✅ **ANALYSIS**: Codebase patterns identified (15+ components over-engineered), files to modify determined, root causes found
- ✅ **RESEARCH**: Context7 findings documented (aiosqlite, structlog, anyio patterns with trust scores 7.7-9.3)
- ✅ **PLANNING**: Detailed implementation plan created with 10 micro-tasks (6.5 hours estimated)
- ✅ **APPROVAL**: User approved rewrite approach, ready for GLM-4.6 execution

---

## 📋 YOUR IMPLEMENTATION PLAN

**COMPLETE PLAN**: `docs/development/plan/piano_session-tracking-rewrite-2025-10-13.md`

**READ THE PLAN FIRST** using:
```bash
cat docs/development/plan/piano_session-tracking-rewrite-2025-10-13.md
```

**Plan Summary** (excerpt):
Complete rewrite using Context7 best practices:
- New simplified sessions table schema (6 columns vs 15+)
- SessionManager singleton with aiosqlite patterns
- SessionTracker with AnyIO task groups
- SessionSummary generator with structlog context
- Simplified SessionStart/SessionEnd hooks
- Data migration + 95%+ test coverage

---

## 🎯 YOUR MISSION (Steps 6-7)

### Step 6: IMPLEMENTATION
- Execute 10 micro-tasks **one at a time**
- Follow plan specifications **exactly**
- Use TodoWrite: mark "in_progress" → work → "completed"
- Run tests **after each micro-task**
- **NEVER** mark completed with failing tests

### Step 7: VERIFICATION
- **95%+ test coverage** for all new code
- **mypy --strict** zero errors
- **Performance validation** (<100ms session ops)
- **@code-reviewer** validation (automatic on commit)

---

## 🔧 DEVSTREAM PROTOCOL COMPLIANCE (MANDATORY)

**CRITICAL RULES** (from @CLAUDE.md):

### Python Environment
```bash
# ALWAYS use .devstream venv
.devstream/bin/python script.py       # ✅ CORRECT
.devstream/bin/python -m pytest       # ✅ CORRECT
python script.py                       # ❌ FORBIDDEN
```

### TodoWrite Workflow
1. Mark first task "in_progress"
2. Implement according to plan
3. Run tests
4. Mark "completed" ONLY when:
   - Tests pass 100%
   - Type check passes
   - Acceptance criteria met
5. Proceed to next task

### Context7 Usage
```python
# When you encounter unknowns
library_id = mcp__context7__resolve-library-id(libraryName="{{library}}")
docs = mcp__context7__get-library-docs(
    context7CompatibleLibraryID=library_id,
    topic="{{specific_question}}",
    tokens=3000
)
```

### Memory Search
```python
# Before implementing, search for existing patterns
mcp__devstream__devstream_search_memory(
    query="{{task_context}}",
    content_type="code",
    limit=5
)
```

---

## 📚 CONTEXT7 RESEARCH (Pre-Completed by Sonnet)

**aiosqlite 0.20.0** (Trust Score 7.7/10):
```python
async with aiosqlite.connect(...) as db:
    await db.execute("INSERT INTO some_table ...")
    await db.commit()
```

**structlog 24.1.0** (Trust Score 9.2/10):
```python
structlog.contextvars.bind_contextvars(session_id=session_id, user_id=user_id)
```

**anyio 4.0.0** (Trust Score 9.3/10):
```python
async with anyio.create_task_group() as tg:
    tg.start_soon(task_function, *args)
```

**Key Findings**:
- aiosqlite async context managers for automatic cleanup
- structlog context binding for automatic session propagation
- anyio task groups for structured concurrency with cancellation

---

## 🏗️ TECHNICAL SPECIFICATIONS

**Files to Modify**:
- `data/migrations/001_simplify_sessions.sql` (NEW)
- `.claude/hooks/devstream/sessions/session_manager.py` (NEW)
- `.claude/hooks/devstream/sessions/session_tracker.py` (NEW)
- `.claude/hooks/devstream/sessions/session_summary.py` (NEW)
- `.claude/hooks/devstream/sessions/session_start_simple.py` (NEW)
- `.claude/hooks/devstream/sessions/session_end_simple.py` (NEW)
- `scripts/migrate_sessions.py` (NEW)
- `.claude/settings.json` (UPDATE)
- Various test files (NEW)

**New Database Schema**:
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'completed')),
    tokens_used INTEGER DEFAULT 0,
    files_modified INTEGER DEFAULT 0,
    tasks_completed INTEGER DEFAULT 0,
    metadata TEXT
);
```

**Dependencies** (already in requirements.txt):
- aiosqlite>=0.20.0
- structlog>=24.1.0
- anyio>=4.0.0
- pytest>=7.0.0
- mypy>=1.0.0

---

## 🚨 CRITICAL CONSTRAINTS (DO NOT VIOLATE)

**FORBIDDEN ACTIONS**:
- ❌ **NO** removal of features (find proper solution instead)
- ❌ **NO** workarounds (implement correctly using Context7)
- ❌ **NO** simplifications that reduce functionality
- ❌ **NO** skipping tests or type hints
- ❌ **NO** early quit on complex tasks (complete fully)

**REQUIRED ACTIONS**:
- ✅ **YES** use `.devstream/bin/python` for ALL commands
- ✅ **YES** follow TodoWrite plan strictly
- ✅ **YES** use Context7 for unknowns (tools provided)
- ✅ **YES** maintain ALL existing functionality
- ✅ **YES** full type hints + docstrings EVERY function
- ✅ **YES** tests for EVERY feature (95%+ coverage)

---

## ✅ QUALITY GATES (Check Before Completion)

### 1. Environment Verification
```bash
# Verify venv and Python version
.devstream/bin/python --version  # Must be 3.11.x
.devstream/bin/python -m pip list | grep -E "(cchooks|aiohttp|structlog)"
```

### 2. Implementation
Follow plan in `docs/development/plan/piano_session-tracking-rewrite-2025-10-13.md`

### 3. Testing
```bash
# After EVERY micro-task
.devstream/bin/python -m pytest tests/unit/test_{{module}}.py -v
.devstream/bin/python -m mypy {{file_path}} --strict

# Before completion (ALL tests)
.devstream/bin/python -m pytest tests/ -v \
    --cov=.claude/hooks/devstream/sessions \
    --cov-report=term-missing \
    --cov-report=html

# REQUIREMENT: ≥95% coverage, 100% pass rate
```

### 4. Performance
```bash
# Test session creation speed
time .devstream/bin/python -c "
import asyncio
from .claude.hooks.devstream.sessions.session_manager import SessionManager
async def test():
    sm = SessionManager('data/test.db')
    await sm.create_session('test-session')
asyncio.run(test())
"

# TARGET: <100ms per session operation
```

### 5. Commit (if all tests pass)
```bash
git add {{files}}
git commit -m "$(cat <<'EOF'
refactor(sessions): implement simplified Context7-based session tracking

Complete rewrite of session tracking system using Context7 best practices:
- aiosqlite async patterns with context managers
- structlog context binding for automatic session propagation
- anyio task groups for structured concurrency
- Simplified 3-component architecture
- Zero zombie sessions, correct token/task tracking
- 50%+ code reduction while maintaining all functionality

Task ID: session-tracking-rewrite-2025-10-13

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

**Note**: @code-reviewer validation automatic on commit

---

## 🔍 DEVSTREAM MEMORY ACCESS

Search for relevant context anytime:
```python
mcp__devstream__devstream_search_memory(
    query="session tracking patterns",
    content_type="code",
    limit=10
)
```

---

## 📊 SUCCESS CRITERIA

- [ ] All TodoWrite tasks completed (10/10)
- [ ] Tests pass 100%
- [ ] Coverage ≥ 95%
- [ ] mypy --strict passes (zero errors)
- [ ] Performance meets target: <100ms session operations
- [ ] @code-reviewer validation passed
- [ ] All acceptance criteria met
- [ ] Zero zombie sessions
- [ ] Correct token/task tracking
- [ ] MCP integration working

---

## 🚀 EXECUTION CHECKLIST

1. [ ] **READ** the complete plan: `cat docs/development/plan/piano_session-tracking-rewrite-2025-10-13.md`
2. [ ] **VERIFY** environment: `.devstream/bin/python --version`
3. [ ] **SEARCH** DevStream memory for context
4. [ ] **START** first TodoWrite task (mark "in_progress")
5. [ ] **IMPLEMENT** according to plan specifications
6. [ ] **TEST** after each micro-task
7. [ ] **COMPLETE** task when all criteria met
8. [ ] **REPEAT** steps 4-7 for remaining tasks
9. [ ] **VALIDATE** complete implementation (all quality gates)
10. [ ] **COMMIT** if all tests pass

---

**READY TO IMPLEMENT?**

Start with the first TodoWrite task. Execute precisely. Test thoroughly. Complete fully. 🚀

**Remember**: You are GLM-4.6 - your strength is **precise execution** of well-defined tasks. The strategic thinking is done. Now execute flawlessly. 💪

**Micro-tasks in order**:
1. Creare nuovo database schema semplificato per sessioni
2. Implementare SessionManager singleton con aiosqlite patterns
3. Sviluppare SessionTracker per real-time progress updates
4. Creare SessionSummary generator con structlog context
5. Implementare hook SessionStart semplificato
6. Implementare hook SessionEnd semplificato
7. Migrare dati sessioni esistenti al nuovo schema
8. Testare copertura 95%+ per nuovo sistema
9. Aggiornare configurazione hooks per nuovi componenti
10. Verificare integrazione con MCP memory system

**Total Estimated Time**: 6.5 hours

**Go GLM-4.6! Execute with precision!** 🎯