# Implementation Plan: GitHub Repository Cleanup and Release 0.2.0

**FOR MODEL**: GLM-4.6 (Tool-Focused, Execution-Optimized)
**Task ID**: `a708b697-6291-40cd-af06-d3fb9ec8569f`
**Phase**: repository-synchronization
**Priority**: 8/10
**Estimated Duration**: 4 hours

---

## 🎯 EXECUTION PROFILE FOR GLM-4.6

You are an **expert coding agent** specialized in **precise execution** of well-defined tasks.

**YOUR STRENGTHS** (leverage these):
- ✅ Tool calling accuracy 90.6% (best-in-class)
- ✅ Efficient token usage (15% fewer than alternatives)
- ✅ Standard coding patterns excellence
- ✅ Integration with Claude Code ecosystem

**YOUR CONSTRAINTS** (respect these):
- ⚠️ AVOID prolonged reasoning (thinking mode costly - 18K tokens)
- ⚠️ FOCUS on execution over exploration
- ⚠️ FOLLOW provided patterns exactly (framework knowledge gaps)
- ⚠️ CHECK syntax precision (13% error rate - mitigate with type hints)
- ⚠️ COMPLETE micro-tasks fully (no early quit - acceptance criteria mandatory)

---

## 📋 MICRO-TASK BREAKDOWN

### Task 1: Clean .gitignore violations and remove tracked files (Duration: 45 min)

**File**: `.gitignore` (Lines: 1-150)
**ACTION**: Remove files that should be ignored but are tracked, update .gitignore with missing patterns

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
def cleanup_gitignore_violations() -> Dict[str, Any]:
    """
    Clean up files that should be ignored but are currently tracked.

    Uses git commands to identify and remove tracked files that violate .gitignore rules.
    Context7 best practices: aggressive cleanup of development artifacts.

    Args:
        None

    Returns:
        Dictionary with cleanup results and file statistics

    Raises:
        GitOperationError: If git operations fail

    Example:
        >>> result = cleanup_gitignore_violations()
        {'removed_files': 12, 'updated_gitignore': True}
    """
```

**PATTERN REFERENCE**: See Context7 research on git rm --cached patterns

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    result = cleanup_gitignore_violations()
except GitOperationError as e:
    logger.error(
        "Git cleanup operation failed",
        extra={"operation": "gitignore_cleanup", "error": str(e)}
    )
    raise GitOperationError(f"Failed to cleanup gitignore violations: {e}") from e
```

**TOOL USAGE**:
1. **Tool**: Bash commands for git operations
   **When**: Identifying and removing tracked files
   **Example**:
   ```bash
   git ls-files | grep -E "\.(DS_Store|log|bak)$"
   git rm --cached FILENAME
   ```

**TEST FILE**: `tests/unit/test_github_cleanup.py::test_cleanup_gitignore_violations`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] All .DS_Store files removed from tracking
- [ ] All .log files removed from tracking
- [ ] All .bak files removed from tracking
- [ ] .gitignore updated with missing patterns
- [ ] Function signature matches exactly
- [ ] Full type hints present
- [ ] Error handling implemented
- [ ] Test written and passing

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -m pytest tests/unit/test_github_cleanup.py::test_cleanup_gitignore_violations -v
```

---

### Task 2: Remove deprecated MCP server directories (Duration: 30 min)

**File**: Repository root directories
**ACTION**: Remove mcp-devstream-server/ and node_modules/ directories using git-filter-repo

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
def remove_deprecated_directories() -> Dict[str, Any]:
    """
    Remove deprecated MCP server directories from repository history.

    Uses git-filter-repo to completely remove directories from Git history.
    Context7 best practice: complete removal of deprecated infrastructure.

    Args:
        None

    Returns:
        Dictionary with removal results and statistics

    Raises:
        GitOperationError: If git-filter-repo operations fail

    Example:
        >>> result = remove_deprecated_directories()
        {'directories_removed': ['mcp-devstream-server', 'node_modules']}
    """
```

**PATTERN REFERENCE**: See Context7 git-filter-repo research for directory removal

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    result = remove_deprecated_directories()
except GitOperationError as e:
    logger.error(
        "Directory removal failed",
        extra={"operation": "git_filter_repo", "error": str(e)}
    )
    raise GitOperationError(f"Failed to remove deprecated directories: {e}") from e
```

**TOOL USAGE**:
1. **Tool**: git-filter-repo with --path and --invert-paths
   **When**: Removing directories from Git history
   **Example**:
   ```bash
   git filter-repo --path mcp-devstream-server/ --invert-paths
   git filter-repo --path node_modules/ --invert-paths
   ```

2. **Tool**: Context7 research patterns for git-filter-repo
   **When**: Verifying git-filter-repo usage patterns
   **Example**:
   ```python
   library_id = mcp__context7__resolve-library-id(libraryName="git-filter-repo")
   docs = mcp__context7__get-library-docs(
       context7CompatibleLibraryID=library_id,
       topic="directory removal invert-paths",
       tokens=2000
   )
   ```

**TEST FILE**: `tests/unit/test_github_cleanup.py::test_remove_deprecated_directories`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] mcp-devstream-server/ completely removed from history
- [ ] node_modules/ completely removed from history
- [ ] git reflog expired and garbage collected
- [ ] Function signature matches exactly
- [ ] Full type hints present
- [ ] Error handling implemented
- [ ] Test written and passing

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -m pytest tests/unit/test_github_cleanup.py::test_remove_deprecated_directories -v
```

---

### Task 3: Merge and close Pull Requests (Duration: 30 min)

**File**: GitHub repository remote operations
**ACTION**: Merge PR #10, evaluate PR #6, close obsolete branches

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
def manage_pull_requests() -> Dict[str, Any]:
    """
    Merge approved Pull Requests and close obsolete ones.

    Uses GitHub CLI to manage PR lifecycle according to project standards.
    Context7 best practice: clean branch management before release.

    Args:
        None

    Returns:
        Dictionary with PR management results and statistics

    Raises:
        GitHubOperationError: If GitHub CLI operations fail

    Example:
        >>> result = manage_pull_requests()
        {'merged_prs': [10], 'closed_prs': [6], 'branches_closed': 2}
    """
```

**PATTERN REFERENCE**: See GitHub CLI documentation for PR management

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    result = manage_pull_requests()
except GitHubOperationError as e:
    logger.error(
        "PR management failed",
        extra={"operation": "github_cli", "error": str(e)}
    )
    raise GitHubOperationError(f"Failed to manage pull requests: {e}") from e
```

**TOOL USAGE**:
1. **Tool**: GitHub CLI (gh) for PR operations
   **When**: Managing pull requests and branches
   **Example**:
   ```bash
   gh pr merge 10 --merge
   gh pr close 6
   gh pr list --state closed
   ```

**TEST FILE**: `tests/unit/test_github_cleanup.py::test_manage_pull_requests`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] PR #10 merged to main branch
- [ ] PR #6 evaluated and appropriately closed/merged
- [ ] Obsolete branches identified
- [ ] Function signature matches exactly
- [ ] Full type hints present
- [ ] Error handling implemented
- [ ] Test written and passing

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -m pytest tests/unit/test_github_cleanup.py::test_manage_pull_requests -v
```

---

### Task 4: Create comprehensive CHANGELOG for v0.2.0 (Duration: 45 min)

**File**: `CHANGELOG.md` (Lines: 1-200)
**ACTION**: Generate comprehensive changelog for release v0.2.0

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
def generate_changelog_v0_2_0() -> str:
    """
    Generate comprehensive changelog for v0.2.0 release.

    Analyzes git history and creates structured changelog following
    semantic versioning conventions. Context7 best practice:
    detailed change documentation for major releases.

    Args:
        None

    Returns:
        Formatted changelog content as string

    Raises:
        GitOperationError: If git history analysis fails

    Example:
        >>> changelog = generate_changelog_v0_2_0()
        print(changelog[:100])  # Shows first 100 chars
    """
```

**PATTERN REFERENCE**: See semantic-release changelog patterns

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    changelog = generate_changelog_v0_2_0()
except GitOperationError as e:
    logger.error(
        "Changelog generation failed",
        extra={"operation": "git_history_analysis", "error": str(e)}
    )
    raise GitOperationError(f"Failed to generate changelog: {e}") from e
```

**TOOL USAGE**:
1. **Tool**: git log for commit analysis
   **When**: Analyzing changes since last release
   **Example**:
   ```bash
   git log --oneline --since="2025-10-01" --grep="feat\|fix\|BREAKING"
   ```

2. **Tool**: Context7 semantic versioning research
   **When**: Structuring changelog format
   **Example**:
   ```python
   library_id = mcp__context7__resolve-library-id(libraryName="semantic-release")
   docs = mcp__context7__get-library-docs(
       context7CompatibleLibraryID=library_id,
       topic="changelog generation conventional commits",
       tokens=2000
   )
   ```

**TEST FILE**: `tests/unit/test_github_cleanup.py::test_generate_changelog_v0_2_0`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] CHANGELOG.md created with proper structure
- [ ] All features since v0.1.0 documented
- [ ] Breaking changes clearly marked
- [ ] Semantic versioning sections present
- [ ] Function signature matches exactly
- [ ] Full type hints present
- [ ] Error handling implemented
- [ ] Test written and passing

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -m pytest tests/unit/test_github_cleanup.py::test_generate_changelog_v0_2_0 -v
```

---

### Task 5: Create and push release v0.2.0 (Duration: 30 min)

**File**: GitHub remote operations
**ACTION**: Create release tag and GitHub release with comprehensive notes

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
def create_release_v0_2_0() -> Dict[str, Any]:
    """
    Create and publish release v0.2.0 with comprehensive notes.

    Creates Git tag, GitHub release, and uploads artifacts.
    Context7 best practice: automated release with full documentation.

    Args:
        None

    Returns:
        Dictionary with release creation results and URLs

    Raises:
        GitOperationError: If release creation fails

    Example:
        >>> result = create_release_v0_2_0()
        {'tag': 'v0.2.0', 'release_url': 'https://github.com/...'}
    """
```

**PATTERN REFERENCE**: See GitHub release creation patterns

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    result = create_release_v0_2_0()
except GitOperationError as e:
    logger.error(
        "Release creation failed",
        extra={"operation": "github_release", "error": str(e)}
    )
    raise GitOperationError(f"Failed to create release: {e}") from e
```

**TOOL USAGE**:
1. **Tool**: GitHub CLI for release operations
   **When**: Creating release and tag
   **Example**:
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   gh release create v0.2.0 --title "DevStream v0.2.0" --notes-file CHANGELOG.md
   ```

**TEST FILE**: `tests/unit/test_github_cleanup.py::test_create_release_v0_2_0`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Git tag v0.2.0 created locally
- [ ] Tag pushed to remote repository
- [ ] GitHub release created with proper title
- [ ] Release notes include CHANGELOG content
- [ ] Function signature matches exactly
- [ ] Full type hints present
- [ ] Error handling implemented
- [ ] Test written and passing

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -m pytest tests/unit/test_github_cleanup.py::test_create_release_v0_2_0 -v
```

---

### Task 6: Final repository verification and cleanup (Duration: 30 min)

**File**: Repository health checks
**ACTION**: Verify repository health and perform final cleanup

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
def final_repository_verification() -> Dict[str, Any]:
    """
    Perform final repository health verification and cleanup.

    Validates repository state, checks for remaining issues,
    and performs final cleanup operations. Context7 best practice:
    comprehensive repository validation before release.

    Args:
        None

    Returns:
        Dictionary with verification results and health metrics

    Raises:
        RepositoryHealthError: If critical issues remain

    Example:
        >>> result = final_repository_verification()
        {'health_score': 95, 'issues_remaining': 0}
    """
```

**PATTERN REFERENCE**: See Context7 repository health patterns

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    result = final_repository_verification()
except RepositoryHealthError as e:
    logger.error(
        "Repository verification failed",
        extra={"operation": "health_check", "error": str(e)}
    )
    raise RepositoryHealthError(f"Repository health check failed: {e}") from e
```

**TOOL USAGE**:
1. **Tool**: Repository health checks
   **When**: Final validation before completion
   **Example**:
   ```bash
   git status
   git log --oneline -5
   gh release list
   ```

**TEST FILE**: `tests/unit/test_github_cleanup.py::test_final_repository_verification`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] No uncommitted changes remain
- [ ] All .gitignore violations resolved
- [ ] Repository size optimized
- [ ] Release v0.2.0 accessible
- [ ] Function signature matches exactly
- [ ] Full type hints present
- [ ] Error handling implemented
- [ ] Test written and passing

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -m pytest tests/unit/test_github_cleanup.py::test_final_repository_verification -v
```

---

## 🔍 CONTEXT7 RESEARCH FINDINGS (Pre-Researched)

### GitHub Repository Management
**Library**: GitHub CLI
**Trust Score**: 8.2/10
**Context7 ID**: /cli/cli

**Key Pattern 1**: Pull Request Management
```bash
gh pr merge <pr-number> --merge
gh pr close <pr-number>
gh pr list --state open
```
**When to use**: Managing GitHub pull requests and branches

**Key Pattern 2**: Release Creation
```bash
gh release create <tag> --title "Release Title" --notes-file CHANGELOG.md
```
**When to use**: Creating GitHub releases with notes

### Git History Cleanup
**Library**: git-filter-repo
**Trust Score**: 8.7/10
**Context7 ID**: /newren/git-filter-repo

**Key Pattern 1**: Directory Removal
```bash
git filter-repo --path <directory> --invert-paths
```
**When to use**: Completely removing directories from Git history

**Key Pattern 2**: Repository Cleanup
```bash
git reflog expire --expire=now --all
git gc --prune=now
```
**When to use**: Final cleanup after history changes

### Semantic Versioning
**Library**: semantic-release
**Trust Score**: 8.7/10
**Context7 ID**: /semantic-release/semantic-release

**Key Pattern 1**: Changelog Generation
```javascript
"@semantic-release/changelog"
```
**When to use**: Generating structured changelogs from commits

**Key Pattern 2**: Version Management
```bash
v0.1.0 -> v0.2.0 (minor release)
```
**When to use**: Planning release versioning strategy

---

## 🚨 CRITICAL CONSTRAINTS (DO NOT VIOLATE)

**FORBIDDEN ACTIONS**:
- ❌ **NO** removal of critical repository data without backup
- ❌ **NO** force push without verification
- ❌ **NO** workarounds instead of proper git-filter-repo usage
- ❌ **NO** skipping verification steps
- ❌ **NO** marking task complete with failing tests

**REQUIRED ACTIONS**:
- ✅ **YES** use Context7 for unknown git operations
- ✅ **YES** backup repository before history changes
- ✅ **YES** verify all git operations before force push
- ✅ **YES** follow exact error handling pattern
- ✅ **YES** full docstrings + type hints EVERY function
- ✅ **YES** check acceptance criteria per micro-task

---

## ✅ QUALITY GATES (MANDATORY BEFORE COMPLETION)

### 1. Repository Backup
```bash
# Create backup before history changes
git clone origin backup-$(date +%Y%m%d-%H%M%S)
```

### 2. Test Coverage
```bash
.devstream/bin/python -m pytest tests/ -v \
    --cov=.claude/hooks/devstream/optimization \
    --cov-report=term-missing \
    --cov-report=html

# REQUIREMENT: ≥ 95% coverage for NEW code
```

### 3. Type Safety
```bash
.devstream/bin/python -m mypy tests/unit/test_github_cleanup.py --strict

# REQUIREMENT: Zero errors
```

### 4. Repository Health
```bash
# Verify final repository state
git status
git log --oneline -5
gh release list
```

---

## 📝 COMMIT MESSAGE TEMPLATE

```
feat(repo): Complete GitHub repository cleanup and release v0.2.0

Comprehensive repository cleanup following Context7 best practices
and production of DevStream v0.2.0 with Direct DB architecture.

Implementation Details:
- Cleaned .gitignore violations (.DS_Store, .log, .bak files)
- Removed deprecated MCP server directories (mcp-devstream-server/, node_modules/)
- Managed Pull Requests: Merged PR #10, evaluated PR #6
- Generated comprehensive CHANGELOG.md for v0.2.0
- Created release v0.2.0 with detailed notes
- Optimized repository size and structure

Quality Validation:
- ✅ Tests: 6 tests passing, 98% coverage
- ✅ Type safety: mypy --strict passed
- ✅ Repository health: All issues resolved
- ✅ Release: v0.2.0 published successfully

Task ID: a708b697-6291-40cd-af06-d3fb9ec8569f

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## 📊 SUCCESS METRICS

- **Completion**: 100% of micro-tasks with acceptance criteria met
- **Test Coverage**: ≥ 95% for new code
- **Type Safety**: Zero mypy errors
- **Repository Health**: 100% clean, v0.2.0 released
- **Code Review**: @code-reviewer validation passed

---

**READY TO START?**
1. Mark first TodoWrite task as "in_progress"
2. Create repository backup before history changes
3. Implement according to specification
4. Run tests + type check
5. Mark "completed" when all acceptance criteria met
6. Proceed to next micro-task

**REMEMBER**: Execute, don't explore. Follow patterns, don't invent. Complete tasks, don't quit early. 🚀