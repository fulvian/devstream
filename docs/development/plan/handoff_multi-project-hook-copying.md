# 🚀 DevStream Task Handoff: Multi-Project Hook Copying with Copier Integration

**FROM**: Claude Sonnet 4.5 (Strategic Planning Complete)
**TO**: GLM-4.6 (Implementation Execution)

---

## 📊 TASK CONTEXT

**Task ID**: `79cbed37-0030-4ec9-a628-c68aa993558a`
**Phase**: Implementation
**Priority**: 8/10
**Status**: Steps 1-5 COMPLETED by Sonnet 4.5 → Steps 6-7 DELEGATED to you

**Your Role**: You are an **expert execution-focused coding agent**. Sonnet 4.5 has completed all strategic planning. Your job is **precise implementation** according to the approved plan.

---

## ✅ WORK COMPLETED (Steps 1-5)

- ✅ **DISCUSSION**: UserPromptSubmit hook errors analyzed, multi-project mode requirements identified
- ✅ **ANALYSIS**: Root cause found - incomplete hook copying (missing `protocol/` and `agents/` directories)
- ✅ **RESEARCH**: Context7-compliant solutions researched (Copier library selected - Trust Score 7.4/10)
- ✅ **PLANNING**: Detailed implementation plan created with 10 micro-tasks
- ✅ **APPROVAL**: User approved plan, ready for execution

---

## 📋 YOUR IMPLEMENTATION PLAN

**COMPLETE PLAN**: `/Users/fulvioventura/devstream/docs/development/plan/piano_multi-project-hook-copying.md`

**READ THE PLAN FIRST** using:
```bash
cat /Users/fulvioventura/devstream/docs/development/plan/piano_multi-project-hook-copying.md
```

**Plan Summary** (excerpt):
Implement Context7-compliant multi-project hook copying using Copier library with:
- Enhanced `copy_devstream_hooks_enhanced()` function
- Agent Auto-Delegation import fixes
- Integrity validation with checksums
- Bootstrap system integration
- Comprehensive test suite

---

## 🎯 YOUR MISSION (Steps 6-7)

### Step 6: IMPLEMENTATION
- Execute micro-tasks **one at a time**
- Follow plan specifications **exactly**
- Use TodoWrite: mark "in_progress" → work → "completed"
- Run tests **after each micro-task**
- **NEVER** mark completed with failing tests

### Step 7: VERIFICATION
- **95%+ test coverage** for all new code
- **mypy --strict** zero errors
- **Performance validation** (< 30s copying time)
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
library_id = mcp__context7__resolve-library-id(libraryName="copier")
docs = mcp__context7__get-library-docs(
    context7CompatibleLibraryID=library_id,
    topic="run_copy_async error handling",
    tokens=3000
)
```

### Memory Search
```python
# Before implementing, search for existing patterns
mcp__devstream__devstream_search_memory(
    query="hook copying multi-project patterns",
    content_type="code",
    limit=5
)
```

---

## 📚 CONTEXT7 RESEARCH (Pre-Completed by Sonnet)

**Libraries Researched**:
- copier 9.0.0 (Trust Score: 7.4/10, Context7 ID: /copier-org/copier)
- pathlib and shutil for robust file operations
- structlog for Context7-compliant logging

**Research Findings**:
- Copier provides template-based copying with Jinja templating
- Robust error handling with `copier.CopierError` exceptions
- Async operations supported via `copier.run_copy_async()`
- Integrity validation through checksums

**Pattern Examples**:
```python
# Async copying with proper error handling
async def copy_with_copier(source, destination):
    try:
        result = await copier.run_copy_async(
            source, destination,
            defaults=True,
            quiet=False
        )
        return result
    except copier.CopierError as e:
        logger.error("Copy failed", error=str(e))
        raise
```

**When to use**: Template-based project copying requiring robust error handling and validation

---

## 🏗️ TECHNICAL SPECIFICATIONS

**Files to Modify**:
- `requirements.txt` - Add Copier dependency
- `.claude/hooks/devstream/utils/multi_project_hook_copier.py` - NEW enhanced hook copying module
- `.claude/hooks/devstream/agents/pattern_matcher.py` - Fix relative imports
- `.claude/hooks/devstream/utils/hook_integrity_validator.py` - NEW integrity validation
- `tests/unit/test_multi_project_hook_copier.py` - NEW comprehensive tests
- `tests/integration/test_multi_project_deployment.py` - NEW integration tests
- `scripts/devstream-init.py` - Update bootstrap system
- `docs/guides/multi-project-deployment.md` - NEW documentation

**New Files to Create**:
- Enhanced hook copying module with Copier integration
- Integrity validation system with checksums
- Comprehensive test suite for multi-project deployment
- Performance optimization utilities
- Multi-project deployment documentation

**Dependencies** (to add to requirements.txt):
- `copier>=9.0.0,<10.0.0`

---

## 🚨 CRITICAL CONSTRAINTS (DO NOT VIOLATE)

**FORBIDDEN ACTIONS**:
- ❌ **NO** removal of Protocol Enforcement features (find proper solution instead)
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
Follow plan in `/Users/fulvioventura/devstream/docs/development/plan/piano_multi-project-hook-copying.md`

### 3. Testing
```bash
# After EVERY micro-task
.devstream/bin/python -m pytest tests/unit/test_multi_project_hook_copier.py -v
.devstream/bin/python -m mypy .claude/hooks/devstream/utils/multi_project_hook_copier.py --strict

# Before completion (ALL tests)
.devstream/bin/python -m pytest tests/ -v \
    --cov=.claude/hooks/devstream \
    --cov-report=term-missing \
    --cov-report=html

# REQUIREMENT: ≥95% coverage, 100% pass rate
```

### 4. Performance Benchmark
```bash
# Test copying performance
time .devstream/bin/python -c "
import asyncio
from pathlib import Path
sys.path.append('.claude/hooks/devstream/utils')
from multi_project_hook_copier import copy_devstream_hooks_enhanced

async def test():
    result = await copy_devstream_hooks_enhanced(
        Path('/Users/fulvioventura/devstream'),
        Path('/tmp/test-project')
    )
    print(f'Copy result: {result}')

asyncio.run(test())
"

# TARGET: < 30 seconds for complete hook copying
```

### 5. Commit (if all tests pass)
```bash
git add requirements.txt .claude/hooks/devstream/utils/multi_project_hook_copier.py .claude/hooks/devstream/agents/pattern_matcher.py .claude/hooks/devstream/utils/hook_integrity_validator.py tests/ docs/guides/multi-project-deployment.md scripts/devstream-init.py
git commit -m "$(cat <<'EOF'
feat(multi-project): implement Context7-compliant hook copying with Copier

Resolve UserPromptSubmit hook errors in multi-project mode by implementing
robust hook copying system using Copier library with integrity validation.

Implementation Details:
- Added Copier library for template-based hook copying
- Created enhanced multi-project hook copying module
- Fixed Agent Auto-Delegation relative import issues
- Implemented integrity validation with checksums
- Added comprehensive test suite for multi-project deployment
- Updated bootstrap system to use enhanced copying
- Optimized performance for large projects

Quality Validation:
- ✅ Tests: 10 tests passing, 95%+ coverage
- ✅ Type safety: mypy --strict passed
- ✅ Performance: < 30s copy time achieved

Task ID: 79cbed37-0030-4ec9-a628-c68aa993558a

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
    query="multi-project hook copying UserPromptSubmit errors",
    content_type="code",
    limit=10
)
```

---

## 📊 SUCCESS CRITERIA

- [ ] All TodoWrite tasks completed
- [ ] Tests pass 100%
- [ ] Coverage ≥ 95%
- [ ] mypy --strict passes (zero errors)
- [ ] Performance meets target: < 30s copying time
- [ ] @code-reviewer validation passed
- [ ] All acceptance criteria met
- [ ] Protocol Enforcement works in multi-project mode
- [ ] No UserPromptSubmit hook errors

---

## 🚀 EXECUTION CHECKLIST

1. [ ] **READ** the complete plan: `cat /Users/fulvioventura/devstream/docs/development/plan/piano_multi-project-hook-copying.md`
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

**Key Success Factors**:
- Follow the plan exactly (don't improvise)
- Test after each micro-task (don't skip testing)
- Use Context7 when you encounter unknowns (don't guess)
- Maintain all existing functionality (don't remove features)
- Complete all acceptance criteria (don't quit early)