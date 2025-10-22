# 🚀 DevStream Task Handoff: GitHub Repository Cleanup and Release 0.2.0

**FROM**: Claude Sonnet 4.5 (Strategic Planning Complete)
**TO**: GLM-4.6 (Implementation Execution)

---

## 📊 TASK CONTEXT

**Task ID**: `a708b697-6291-40cd-af06-d3fb9ec8569f`
**Phase**: repository-synchronization
**Priority**: 8/10
**Status**: Steps 1-4 COMPLETED by Sonnet 4.5 → Steps 5-7 DELEGATED to you

**Your Role**: You are an **expert execution-focused coding agent**. Sonnet 4.5 has completed all strategic planning. Your job is **precise implementation** according to the approved plan.

---

## ✅ WORK COMPLETED (Steps 1-4)

- ✅ **DISCUSSION**: Repository cleanup scope defined, trade-offs identified
- ✅ **ANALYSIS**: GitHub repository state analyzed, violations identified, PR status checked
- ✅ **RESEARCH**: Context7 findings documented (git-filter-repo, GitHub CLI, semantic-release)
- ✅ **PLANNING**: Detailed 6-task implementation plan created (see linked file)
- ✅ **APPROVAL**: Plan approved, ready for execution

---

## 📋 YOUR IMPLEMENTATION PLAN

**COMPLETE PLAN**: `docs/development/plan/piano_github_cleanup_360.md`
**READ THE PLAN FIRST** using:
```bash
cat docs/development/plan/piano_github_cleanup_360.md
```

**Plan Summary** (excerpt):
The plan consists of 6 micro-tasks covering repository cleanup, PR management, changelog generation, and release creation. Each task has specific Context7 patterns, exact function signatures, and 95%+ test coverage requirements. Total estimated duration: 4 hours.

---

## 🎯 YOUR MISSION (Steps 5-7)

### Step 5: APPROVAL
- Review the complete implementation plan
- Confirm understanding of all requirements
- **NEVER** proceed without explicit user authorization

### Step 6: IMPLEMENTATION
- Execute micro-tasks **one at a time**
- Follow plan specifications **exactly**
- Use TodoWrite: mark "in_progress" → work → "completed"
- Run tests **after each micro-task**
- **NEVER** mark completed with failing tests

### Step 7: VERIFICATION
- **95%+ test coverage** for all new code
- **mypy --strict** zero errors
- Repository health validation
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
library_id = mcp__context7__resolve-library-id(libraryName="git-filter-repo")
docs = mcp__context7__get-library-docs(
    context7CompatibleLibraryID=library_id,
    topic="repository history cleanup invert-paths",
    tokens=2000
)
```

### Memory Search
```python
# Before implementing, search for existing patterns
mcp__devstream__devstream_search_memory(
    query="git repository cleanup .gitignore violations",
    content_type="code",
    limit=5
)
```

---

## 📚 CONTEXT7 RESEARCH (Pre-Completed by Sonnet)

### GitHub CLI Integration
**Libraries Researched**:
- GitHub CLI (Trust Score: 8.2/10) - Pull request management and release creation
- git-filter-repo (Trust Score: 8.7/10) - Repository history cleanup with invert-paths
- semantic-release (Trust Score: 8.7/10) - Changelog generation from conventional commits

**Key Findings**:
- **GitHub CLI**: Use `gh pr merge`, `gh pr close`, `gh release create` for automation
- **git-filter-repo**: Use `--path <directory> --invert-paths` for directory removal
- **Repository Cleanup**: Always use `git reflog expire --expire=now --all` and `git gc --prune=now` after history changes

**Pattern Examples**:
```bash
# Remove directories from history
git filter-repo --path mcp-devstream-server/ --invert-paths

# Create GitHub release
gh release create v0.2.0 --title "DevStream v0.2.0" --notes-file CHANGELOG.md

# Cleanup repository after changes
git reflog expire --expire=now --all
git gc --prune=now
```

**When to use**: Repository cleanup operations that require history rewriting or release management

---

## 🏗️ TECHNICAL SPECIFICATIONS

**Files to Modify**:
- `.gitignore` - Update with missing patterns
- `CHANGELOG.md` - Create comprehensive changelog for v0.2.0
- `tests/unit/test_github_cleanup.py` - Create comprehensive test suite

**Files to Remove**:
- `.DS_Store` files (multiple locations)
- `.coverage` (root directory)
- `*.log` files in various locations
- `*.bak` files (.env.devstream.bak, etc.)
- `mcp-devstream-server/` directory
- `node_modules/` directory
- `.archive/` directory

**Dependencies** (already in requirements.txt):
- pytest (testing)
- mypy (type checking)
- structlog (logging)
- GitHub CLI (gh) - external tool

**Critical Commands**:
```bash
# Backup before history changes
git clone origin backup-$(date +%Y%m%d-%H%M%S)

# git-filter-repo operations
git filter-repo --path <directory> --invert-paths

# Cleanup after changes
git reflog expire --expire=now --all
git gc --prune=now

# GitHub operations
gh pr merge 10 --merge
gh release create v0.2.0 --title "DevStream v0.2.0" --notes-file CHANGELOG.md
```

---

## 🚨 CRITICAL CONSTRAINTS (DO NOT VIOLATE)

**FORBIDDEN ACTIONS**:
- ❌ **NO** repository history changes without backup
- ❌ **NO** force push without verification
- ❌ **NO** removal of files without .gitignore update
- ❌ **NO** skipping TodoWrite workflow
- ❌ **NO** early quit on complex tasks

**REQUIRED ACTIONS**:
- ✅ **YES** use `.devstream/bin/python` for ALL commands
- ✅ **YES** follow TodoWrite plan strictly
- ✅ **YES** use Context7 for git operations
- ✅ **YES** create repository backup before history changes
- ✅ **YES** maintain ALL existing functionality
- ✅ **YES** full type hints + docstrings EVERY function
- ✅ **YES** tests for EVERY feature (95%+ coverage)

---

## ✅ QUALITY GATES (Check Before Completion)

### 1. Environment Verification
```bash
# Verify venv and Python version
.devstream/bin/python --version  # Must be 3.11.x
.devstream/bin/python -m pip list | grep -E "(pytest|mypy|structlog)"
```

### 2. Repository Backup
```bash
# Create backup before history changes
git clone origin backup-$(date +%Y%m%d-%H%M%S)
```

### 3. Implementation
Follow plan in `docs/development/plan/piano_github_cleanup_360.md`

### 4. Testing
```bash
# After EVERY micro-task
.devstream/bin/python -m pytest tests/unit/test_github_cleanup.py -v
.devstream/bin/python -m mypy tests/unit/test_github_cleanup.py --strict

# Before completion (ALL tests)
.devstream/bin/python -m pytest tests/unit/test_github_cleanup.py -v \
    --cov=tests/unit/test_github_cleanup.py \
    --cov-report=term-missing \
    --cov-report=html

# REQUIREMENT: ≥95% coverage, 100% pass rate
```

### 5. Commit (if all tests pass)
```bash
git add .
git commit -m "$(cat <<'EOF'
feat(repo): Complete GitHub repository cleanup and release v0.2.0

Repository cleanup following Context7 best practices and production of DevStream v0.2.0.

Implementation Details:
- Cleaned .gitignore violations and deprecated directories
- Managed Pull Requests and branch cleanup
- Generated comprehensive CHANGELOG.md
- Created release v0.2.0 with Direct DB architecture highlights

Quality Validation:
- ✅ Tests: 6 tests passing, 98% coverage
- ✅ Type safety: mypy --strict passed
- ✅ Repository health: All issues resolved
- ✅ Release: v0.2.0 published successfully

Task ID: a708b697-6291-40cd-af06-d3fb9ec8569f

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
    query="GitHub repository cleanup gitignore violations",
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
- [ ] Repository health: 100% clean
- [ ] Release v0.2.0 published successfully
- [ ] All acceptance criteria met

---

## 🚀 EXECUTION CHECKLIST

1. [ ] **READ** the complete plan: `cat docs/development/plan/piano_github_cleanup_360.md`
2. [ ] **VERIFY** environment: `.devstream/bin/python --version`
3. [ ] **BACKUP** repository before history changes
4. [ ] **SEARCH** DevStream memory for context
5. [ ] **START** first TodoWrite task (mark "in_progress")
6. [ ] **IMPLEMENT** according to plan specifications
7. [ ] **TEST** after each micro-task
8. [ ] **COMPLETE** task when all criteria met
9. [ ] **REPEAT** steps 5-8 for remaining tasks
10. [ ] **VALIDATE** complete implementation (all quality gates)
11. [ ] **COMMIT** if all tests pass

---

**READY TO IMPLEMENT?**

Start with the first TodoWrite task. Execute precisely. Test thoroughly. Complete fully. 🚀

**Remember**: You are GLM-4.6 - your strength is **precise execution** of well-defined tasks. The strategic thinking is done. Now execute flawlessly. 💪