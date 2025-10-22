# Implementation Plan: Fix Multi-Project Installation & Launcher System

**FOR MODEL**: GLM-4.6 (Tool-Focused, Execution-Optimized)
**Task ID**: `e54c3e46-91ed-4aca-bf28-284034e547d5`
**Phase**: Implementation
**Priority**: 10/10
**Estimated Duration**: 4-6 hours

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

### ✅ TodoWrite Tasks (10 total)

1. Implementare find_devstream_project_root() in start-devstream.sh (60 min)
2. Modificare logica PROJECT_ROOT in start-devstream.sh con upward search (45 min)
3. Implementare validate_devstream_project() in start-devstream.sh (30 min)
4. Aggiungere print_project_info() per feedback utente (15 min)
5. Applicare stesse modifiche a start-claude-zai.sh (45 min)
6. Rimuovere venv spurio da .claude/hooks/devstream/utils/.devstream (10 min)
7. Aggiornare install-devstream.sh per prevenire copia venv spurio (30 min)
8. Creare test end-to-end per multi-project detection (45 min)
9. Testare con 3+ progetti diversi (devstream, exc-to-pdf, nuovo) (30 min)
10. Validare che database isolation funzioni correttamente (30 min)

---

## 🔧 TASK 1: Implementare find_devstream_project_root() (60 min)

**File**: `start-devstream.sh` (Lines: ~40-70, new function)

**ACTION**: Create universal upward search function for .env.devstream marker file

**FUNCTION SIGNATURE** (USE EXACTLY):
```bash
find_devstream_project_root() {
    local start_dir="${1:-$(pwd)}"
    local current_dir="$start_dir"
    local max_depth=20
    local depth=0

    # Upward search for .env.devstream marker
    while [ "$current_dir" != "/" ] && [ $depth -lt $max_depth ]; do
        if [ -f "$current_dir/.env.devstream" ]; then
            # Validate complete DevStream installation
            if [ -d "$current_dir/.claude/hooks/devstream" ] && \
               [ -d "$current_dir/.devstream" ]; then
                echo "$current_dir"
                return 0
            fi
        fi

        current_dir="$(dirname "$current_dir")"
        depth=$((depth + 1))
    done

    return 1  # Not found
}
```

**PATTERN REFERENCE**: See Context7 findings below (npm/package-directory + pyenv upward search)

**VALIDATION CHECKS**:
```bash
# Test the function
test_upward_search() {
    # Test 1: From nested directory
    cd /path/to/project/src/components
    result=$(find_devstream_project_root)
    [ "$result" = "/path/to/project" ] || return 1

    # Test 2: From project root
    cd /path/to/project
    result=$(find_devstream_project_root)
    [ "$result" = "/path/to/project" ] || return 1

    # Test 3: Not in DevStream project
    cd /tmp
    find_devstream_project_root
    [ $? -eq 1 ] || return 1  # Should fail

    return 0
}
```

**ACCEPTANCE CRITERIA**:
- [ ] Function finds .env.devstream in current directory
- [ ] Function searches upward through parent directories
- [ ] Function stops at filesystem root (safety)
- [ ] Function validates .claude/hooks/devstream exists
- [ ] Function validates .devstream venv exists
- [ ] Function returns 0 on success, 1 on failure
- [ ] Max depth limit prevents infinite loops

**COMPLETION COMMAND**:
```bash
# Manual test after implementation
bash -c "source start-devstream.sh && test_upward_search"
```

---

## 🔧 TASK 2: Modificare logica PROJECT_ROOT (45 min)

**File**: `start-devstream.sh` (Lines: 41-50, replace existing logic)

**ACTION**: Replace hardcoded SCRIPT_DIR fallback with intelligent upward search

**BEFORE** (current broken code):
```bash
if [ -n "${DEVSTREAM_PROJECT_ROOT:-}" ]; then
  PROJECT_ROOT="$DEVSTREAM_PROJECT_ROOT"
else
  PROJECT_ROOT="$SCRIPT_DIR"  # ❌ WRONG: forces script location
fi
```

**AFTER** (correct code):
```bash
# Get framework location (where DevStream is installed)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEVSTREAM_FRAMEWORK_ROOT="$(dirname "$SCRIPT_DIR")"

# Priority 1: Explicit project root (manual override)
if [ -n "${DEVSTREAM_PROJECT_ROOT:-}" ]; then
    PROJECT_ROOT="$DEVSTREAM_PROJECT_ROOT"
    print_info "Multi-project mode (explicit): $PROJECT_ROOT"

# Priority 2: Auto-detect from current working directory
elif PROJECT_ROOT=$(find_devstream_project_root "$(pwd)"); then
    export DEVSTREAM_PROJECT_ROOT="$PROJECT_ROOT"
    print_info "Multi-project mode (auto-detected): $PROJECT_ROOT"

# Priority 3: Error - not in DevStream project
else
    print_error "❌ No DevStream project found"
    print_error "   Searched from: $(pwd)"
    print_error "   Looking for:   .env.devstream marker file"
    print_error ""
    print_error "Solutions:"
    print_error "   1. cd to DevStream project directory first"
    print_error "   2. Run install-devstream.sh in current directory"
    print_error "   3. Set DEVSTREAM_PROJECT_ROOT=/path/to/project"
    exit 1
fi
```

**PATTERN REFERENCE**: See Context7 - pyenv priority resolution + direnv auto-loading

**ACCEPTANCE CRITERIA**:
- [ ] Explicit DEVSTREAM_PROJECT_ROOT takes highest priority
- [ ] Auto-detection from pwd works as fallback
- [ ] Clear error message if no project found
- [ ] Suggests 3 solutions to user
- [ ] Exits with non-zero code on error
- [ ] Exports DEVSTREAM_PROJECT_ROOT for child processes

**COMPLETION COMMAND**:
```bash
# Test priority 1 (explicit)
export DEVSTREAM_PROJECT_ROOT=/custom/path
./start-devstream.sh --dry-run

# Test priority 2 (auto-detect)
unset DEVSTREAM_PROJECT_ROOT
cd /Users/fulvioventura/exc-to-pdf
./start-devstream.sh --dry-run

# Test priority 3 (error)
cd /tmp
./start-devstream.sh --dry-run  # Should error
```

---

## 🔧 TASK 3: Implementare validate_devstream_project() (30 min)

**File**: `start-devstream.sh` (Lines: ~70-100, new function)

**ACTION**: Validate detected project has complete DevStream installation

**FUNCTION SIGNATURE** (USE EXACTLY):
```bash
validate_devstream_project() {
    local project_root="$1"
    local validation_failed=0

    print_status "Validating DevStream project at: $project_root"

    # Check required directories
    if [ ! -d "$project_root/.claude" ]; then
        print_error "Missing: .claude directory"
        validation_failed=1
    fi

    if [ ! -d "$project_root/.claude/hooks/devstream" ]; then
        print_error "Missing: .claude/hooks/devstream directory"
        validation_failed=1
    fi

    if [ ! -d "$project_root/.devstream" ]; then
        print_error "Missing: .devstream virtual environment"
        validation_failed=1
    fi

    # Check required files
    if [ ! -f "$project_root/.env.devstream" ]; then
        print_error "Missing: .env.devstream configuration"
        validation_failed=1
    fi

    if [ ! -f "$project_root/data/devstream.db" ]; then
        print_warning "Missing: data/devstream.db (will be created)"
    fi

    # Check Python version in venv
    if [ -x "$project_root/.devstream/bin/python" ]; then
        local python_version=$("$project_root/.devstream/bin/python" --version 2>&1 | awk '{print $2}')
        if [[ ! "$python_version" =~ ^3\.11\. ]]; then
            print_error "Wrong Python version: $python_version (expected 3.11.x)"
            validation_failed=1
        fi
    else
        print_error "Python interpreter not found in .devstream/bin/"
        validation_failed=1
    fi

    if [ $validation_failed -eq 1 ]; then
        print_error ""
        print_error "DevStream installation incomplete or corrupted"
        print_error "Run: $DEVSTREAM_FRAMEWORK_ROOT/scripts/install-devstream.sh"
        return 1
    fi

    print_status "✅ DevStream project validation passed"
    return 0
}
```

**PATTERN REFERENCE**: See Context7 - Poetry virtualenv validation patterns

**ACCEPTANCE CRITERIA**:
- [ ] Checks .claude directory exists
- [ ] Checks .claude/hooks/devstream exists
- [ ] Checks .devstream venv exists
- [ ] Checks .env.devstream config exists
- [ ] Warns if database missing (non-fatal)
- [ ] Validates Python version is 3.11.x
- [ ] Returns 0 on success, 1 on failure
- [ ] Provides actionable error messages

**COMPLETION COMMAND**:
```bash
# Test validation function
bash -c "
source start-devstream.sh
validate_devstream_project /Users/fulvioventura/devstream && echo 'PASS' || echo 'FAIL'
validate_devstream_project /tmp && echo 'FAIL EXPECTED' || echo 'PASS'
"
```

---

## 🔧 TASK 4: Aggiungere print_project_info() (15 min)

**File**: `start-devstream.sh` (Lines: ~100-130, new function)

**ACTION**: Display clear project information to user

**FUNCTION SIGNATURE** (USE EXACTLY):
```bash
print_project_info() {
    local project_root="$1"
    local project_name=$(basename "$project_root")
    local db_size="N/A"

    if [ -f "$project_root/data/devstream.db" ]; then
        db_size=$(du -h "$project_root/data/devstream.db" | awk '{print $1}')
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚀 DevStream Project Detected"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "   Project Name:  $project_name"
    echo "   Location:      $project_root"
    echo "   Database:      data/devstream.db ($db_size)"
    echo "   Python Venv:   .devstream/"
    echo "   Python:        $($project_root/.devstream/bin/python --version 2>&1)"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}
```

**ACCEPTANCE CRITERIA**:
- [ ] Displays project name (from directory)
- [ ] Shows full project path
- [ ] Shows database size (if exists)
- [ ] Shows Python version from venv
- [ ] Clear visual formatting with unicode borders
- [ ] No errors if database missing

---

## 🔧 TASK 5: Applicare modifiche a start-claude-zai.sh (45 min)

**File**: `scripts/start-claude-zai.sh` (Lines: 13-25, 94)

**ACTION**: Apply identical upward search logic to GLM-4.6 launcher

**CHANGES REQUIRED**:
1. Copy `find_devstream_project_root()` function
2. Copy `validate_devstream_project()` function
3. Copy `print_project_info()` function
4. Replace PROJECT_ROOT logic (lines 13-25)
5. Update `cd "$PROJECT_ROOT"` (line 94) to use validated path

**PATTERN**: Identical to start-devstream.sh Task 1-4

**ACCEPTANCE CRITERIA**:
- [ ] All functions copied correctly
- [ ] PROJECT_ROOT logic matches start-devstream.sh
- [ ] Validation called before cd
- [ ] Project info displayed to user
- [ ] Works independently from start-devstream.sh

**COMPLETION COMMAND**:
```bash
# Test GLM launcher independently
cd /Users/fulvioventura/exc-to-pdf
./scripts/start-claude-zai.sh --dry-run
```

---

## 🔧 TASK 6: Rimuovere venv spurio (10 min)

**Directory**: `.claude/hooks/devstream/utils/.devstream/`

**ACTION**: Delete spurious venv copied during installation

**COMMANDS**:
```bash
# Navigate to project
cd /Users/fulvioventura/exc-to-pdf

# Verify it exists (should have hardcoded paths)
ls -la .claude/hooks/devstream/utils/.devstream/
grep "VIRTUAL_ENV=" .claude/hooks/devstream/utils/.devstream/bin/activate

# Remove it completely
rm -rf .claude/hooks/devstream/utils/.devstream/

# Verify removal
[ ! -d ".claude/hooks/devstream/utils/.devstream" ] && echo "✅ Removed" || echo "❌ Still exists"
```

**ACCEPTANCE CRITERIA**:
- [ ] Directory .claude/hooks/devstream/utils/.devstream removed
- [ ] No errors during removal
- [ ] Hooks still work after removal (test with pre_tool_use.py)

**COMPLETION COMMAND**:
```bash
# Test hooks still work
.devstream/bin/python .claude/hooks/devstream/memory/pre_tool_use.py --test
```

---

## 🔧 TASK 7: Aggiornare install-devstream.sh (30 min)

**File**: `scripts/install-devstream.sh`

**ACTION**: Prevent copying utils/.devstream during installation

**LOCATE**: Hook copying logic (search for "Copier integration" or "hook files")

**ADD EXCLUSION**:
```bash
# When copying hooks, exclude venv directories
rsync -av \
    --exclude '.devstream/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    "$SOURCE/.claude/hooks/devstream/" \
    "$TARGET/.claude/hooks/devstream/"
```

**ALTERNATIVE** (if using cp):
```bash
# Copy hooks but skip venv
find "$SOURCE/.claude/hooks/devstream" -type f \
    ! -path "*/.devstream/*" \
    ! -path "*/__pycache__/*" \
    ! -name "*.pyc" \
    -exec cp --parents {} "$TARGET/" \;
```

**ACCEPTANCE CRITERIA**:
- [ ] Hook files copied correctly
- [ ] .devstream directories excluded
- [ ] __pycache__ directories excluded
- [ ] Test installation creates no spurious venv

**COMPLETION COMMAND**:
```bash
# Test installation on clean directory
mkdir /tmp/test-project
cd /tmp/test-project
/Users/fulvioventura/devstream/scripts/install-devstream.sh

# Verify no spurious venv
[ ! -d ".claude/hooks/devstream/utils/.devstream" ] && echo "✅ PASS" || echo "❌ FAIL"

# Cleanup
rm -rf /tmp/test-project
```

---

## 🔧 TASK 8: Creare test E2E multi-project (45 min)

**File**: `tests/integration/test_multi_project_detection.sh` (NEW)

**ACTION**: Create comprehensive end-to-end tests for multi-project support

**TEST SCRIPT**:
```bash
#!/usr/bin/env bash
# End-to-End Test: Multi-Project Detection

set -e

# Setup
TEST_ROOT="/tmp/devstream-multiproject-test-$$"
mkdir -p "$TEST_ROOT"
trap "rm -rf $TEST_ROOT" EXIT

# Test 1: Auto-detection from nested directory
test_auto_detection() {
    echo "Test 1: Auto-detection from nested directory"

    # Create mock project
    local project="$TEST_ROOT/project1"
    mkdir -p "$project"/{.claude/hooks/devstream,.devstream,data,src/components}
    touch "$project/.env.devstream"
    touch "$project/data/devstream.db"
    echo "#!/usr/bin/env bash" > "$project/.devstream/bin/python"
    chmod +x "$project/.devstream/bin/python"

    # Test from nested directory
    cd "$project/src/components"
    source /Users/fulvioventura/devstream/start-devstream.sh

    local detected=$(find_devstream_project_root)
    [ "$detected" = "$project" ] || {
        echo "FAIL: Expected $project, got $detected"
        return 1
    }

    echo "✅ PASS"
}

# Test 2: Explicit DEVSTREAM_PROJECT_ROOT override
test_explicit_override() {
    echo "Test 2: Explicit override"

    local project="$TEST_ROOT/project2"
    mkdir -p "$project"/{.claude/hooks/devstream,.devstream,data}
    touch "$project/.env.devstream"

    export DEVSTREAM_PROJECT_ROOT="$project"

    source /Users/fulvioventura/devstream/start-devstream.sh
    [ "$PROJECT_ROOT" = "$project" ] || {
        echo "FAIL: Override not respected"
        return 1
    }

    unset DEVSTREAM_PROJECT_ROOT
    echo "✅ PASS"
}

# Test 3: Error when not in DevStream project
test_error_detection() {
    echo "Test 3: Error detection"

    cd "$TEST_ROOT"

    if source /Users/fulvioventura/devstream/start-devstream.sh 2>/dev/null; then
        echo "FAIL: Should have errored"
        return 1
    fi

    echo "✅ PASS"
}

# Test 4: Multiple projects isolation
test_project_isolation() {
    echo "Test 4: Project isolation"

    # Create two projects
    local proj1="$TEST_ROOT/app1"
    local proj2="$TEST_ROOT/app2"

    for proj in "$proj1" "$proj2"; do
        mkdir -p "$proj"/{.claude/hooks/devstream,.devstream,data}
        touch "$proj/.env.devstream"
        echo "DEVSTREAM_DB_PATH=$proj/data/devstream.db" > "$proj/.env.devstream"
    done

    # Test project 1
    cd "$proj1"
    source /Users/fulvioventura/devstream/start-devstream.sh
    [ "$PROJECT_ROOT" = "$proj1" ] || return 1
    [ "$DEVSTREAM_DB_PATH" = "$proj1/data/devstream.db" ] || return 1

    # Test project 2
    cd "$proj2"
    source /Users/fulvioventura/devstream/start-devstream.sh
    [ "$PROJECT_ROOT" = "$proj2" ] || return 1
    [ "$DEVSTREAM_DB_PATH" = "$proj2/data/devstream.db" ] || return 1

    echo "✅ PASS"
}

# Run all tests
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Multi-Project Detection E2E Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

test_auto_detection
test_explicit_override
test_error_detection
test_project_isolation

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All tests passed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

**ACCEPTANCE CRITERIA**:
- [ ] Test 1: Auto-detection works from nested dirs
- [ ] Test 2: Explicit override takes priority
- [ ] Test 3: Errors when not in project
- [ ] Test 4: Multiple projects properly isolated
- [ ] All tests pass without errors

**COMPLETION COMMAND**:
```bash
chmod +x tests/integration/test_multi_project_detection.sh
./tests/integration/test_multi_project_detection.sh
```

---

## 🔧 TASK 9: Testare con progetti reali (30 min)

**ACTION**: Manual validation with 3+ real projects

**TEST PROJECTS**:
1. `/Users/fulvioventura/devstream` (original)
2. `/Users/fulvioventura/exc-to-pdf` (existing)
3. `/tmp/new-test-project` (fresh install)

**TEST PROCEDURE**:
```bash
# Project 1: DevStream
cd /Users/fulvioventura/devstream
./start-devstream.sh start anthropic
# Verify: Uses /Users/fulvioventura/devstream/data/devstream.db

# Project 2: exc-to-pdf
cd /Users/fulvioventura/exc-to-pdf/src
/Users/fulvioventura/devstream/start-devstream.sh start z.ai
# Verify: Uses /Users/fulvioventura/exc-to-pdf/data/devstream.db

# Project 3: New installation
mkdir /tmp/new-test-project
cd /tmp/new-test-project
/Users/fulvioventura/devstream/scripts/install-devstream.sh
./start-devstream.sh start anthropic
# Verify: Uses /tmp/new-test-project/data/devstream.db
```

**ACCEPTANCE CRITERIA**:
- [ ] All 3 projects launch Claude Code successfully
- [ ] Each uses its own database (verified via logs)
- [ ] No cross-contamination between projects
- [ ] Working directory is project root (not devstream)
- [ ] Hooks execute in correct project context

---

## 🔧 TASK 10: Validare database isolation (30 min)

**ACTION**: Verify each project uses its own database

**VALIDATION SCRIPT**:
```bash
#!/usr/bin/env bash
# Validate Database Isolation

validate_db_isolation() {
    local project="$1"
    local expected_db="$project/data/devstream.db"

    cd "$project"
    source /Users/fulvioventura/devstream/start-devstream.sh

    # Check DEVSTREAM_DB_PATH
    if [ "$DEVSTREAM_DB_PATH" != "$expected_db" ]; then
        echo "❌ FAIL: Wrong DB path"
        echo "   Expected: $expected_db"
        echo "   Got:      $DEVSTREAM_DB_PATH"
        return 1
    fi

    # Check database file size (should be different for each project)
    local db_size=$(stat -f%z "$expected_db" 2>/dev/null || echo 0)
    echo "✅ PASS: $project uses $expected_db (size: $db_size bytes)"

    return 0
}

# Test all projects
validate_db_isolation /Users/fulvioventura/devstream
validate_db_isolation /Users/fulvioventura/exc-to-pdf

# Query each database to verify isolation
echo ""
echo "Querying databases for unique content..."

for proj in /Users/fulvioventura/{devstream,exc-to-pdf}; do
    echo "Project: $proj"
    cd "$proj"
    .devstream/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/devstream.db')
count = conn.execute('SELECT COUNT(*) FROM semantic_memory').fetchone()[0]
print(f'  Records: {count}')
conn.close()
"
done
```

**ACCEPTANCE CRITERIA**:
- [ ] Each project points to its own database
- [ ] Database paths are correctly set
- [ ] Record counts differ (proving isolation)
- [ ] No cross-project database access

**COMPLETION COMMAND**:
```bash
bash validate_db_isolation.sh
```

---

## 🔍 CONTEXT7 RESEARCH FINDINGS (Pre-Researched)

### Library 1: Poetry (Python Dependency Management)
**Trust Score**: 8.9/10
**Context7 ID**: `/python-poetry/website`

**Key Pattern 1: Per-Project Virtual Environments**
```python
# Poetry manages isolated venvs per project
# Config: virtualenvs.in-project = true
# Result: Each project has .venv/ directory with isolated dependencies
```
**When to use**: Multi-project setups requiring dependency isolation

**Key Pattern 2: Active Python Preference**
```bash
# Poetry detects active Python interpreter
poetry config virtualenvs.prefer-active-python true
# Uses currently active Python (from pyenv, system, etc.)
```
**When to use**: Projects with specific Python version requirements

---

### Library 2: npm/package-directory (Project Root Detection)
**Trust Score**: 9.6/10
**Context7 ID**: `/sindresorhus/package-directory`

**Key Pattern: Upward Search Algorithm**
```javascript
async function packageDirectory(options = {}) {
    const {cwd = process.cwd()} = options;
    let currentDir = cwd;

    while (currentDir !== '/') {
        const packagePath = path.join(currentDir, 'package.json');
        if (await exists(packagePath)) {
            return currentDir;
        }
        currentDir = path.dirname(currentDir);
    }

    return undefined;
}
```
**When to use**: Auto-detecting project root from any subdirectory

---

### Library 3: pyenv (Python Version Management)
**Trust Score**: 7.7/10
**Context7 ID**: `/pyenv/pyenv`

**Key Pattern: Priority-Based Resolution**
```bash
# pyenv version resolution order:
1. PYENV_VERSION environment variable (explicit)
2. .python-version in current directory
3. .python-version in parent directories (upward search)
4. ~/.pyenv/version (global)
5. system Python (fallback)
```
**When to use**: Multi-project with different Python versions

---

### Library 4: direnv (Directory-Based Environment Loading)
**Trust Score**: 6.7/10
**Context7 ID**: `/direnv/direnv`

**Key Pattern: Automatic Environment Loading**
```bash
# direnv automatically loads .envrc when entering directory
$ cd ~/my_project
direnv: loading .envrc
direnv export: +FOO

# And unloads when leaving
$ cd ..
direnv: unloading
direnv export: ~FOO
```
**When to use**: Per-directory environment variable management

---

## 🚨 CRITICAL CONSTRAINTS (DO NOT VIOLATE)

**FORBIDDEN ACTIONS**:
- ❌ **NO** hardcoding of project names (exc-to-pdf, etc.)
- ❌ **NO** hardcoding of absolute paths
- ❌ **NO** removal of existing functionality
- ❌ **NO** workarounds instead of proper upward search
- ❌ **NO** silent failures (must error loudly if not in project)

**REQUIRED ACTIONS**:
- ✅ **YES** use upward search from pwd (universal)
- ✅ **YES** validate project structure before use
- ✅ **YES** provide clear error messages with solutions
- ✅ **YES** maintain backward compatibility (explicit DEVSTREAM_PROJECT_ROOT)
- ✅ **YES** test with multiple real projects
- ✅ **YES** verify database isolation

---

## ✅ QUALITY GATES (MANDATORY BEFORE COMPLETION)

### 1. Manual Testing with Real Projects
```bash
# Test with 3+ projects
cd /Users/fulvioventura/devstream && ./start-devstream.sh --dry-run
cd /Users/fulvioventura/exc-to-pdf && ./start-devstream.sh --dry-run
cd /tmp/new-project && ./start-devstream.sh --dry-run
```

### 2. E2E Integration Tests
```bash
./tests/integration/test_multi_project_detection.sh
# REQUIREMENT: All tests pass
```

### 3. Database Isolation Verification
```bash
# Verify each project uses own database
bash validate_db_isolation.sh
# REQUIREMENT: No cross-project contamination
```

### 4. Shell Script Validation (ShellCheck)
```bash
# Install shellcheck if needed
brew install shellcheck

# Lint all modified scripts
shellcheck start-devstream.sh
shellcheck scripts/start-claude-zai.sh
shellcheck scripts/install-devstream.sh

# REQUIREMENT: Zero errors or warnings
```

---

## 📝 COMMIT MESSAGE TEMPLATE

```
fix(launcher): implement universal multi-project detection

Replace hardcoded SCRIPT_DIR fallback with intelligent upward search
algorithm based on Context7 best practices (npm, pyenv, direnv).

Implementation Details:
- Add find_devstream_project_root() with upward search for .env.devstream
- Add validate_devstream_project() for installation verification
- Add print_project_info() for clear user feedback
- Update start-devstream.sh and start-claude-zai.sh with new logic
- Remove spurious venv from .claude/hooks/devstream/utils/
- Update install-devstream.sh to prevent venv copying
- Add E2E tests for multi-project detection

Quality Validation:
- ✅ Tests: E2E tests passing, database isolation verified
- ✅ Manual validation: 3+ real projects tested
- ✅ ShellCheck: Zero errors
- ✅ Backward compatibility: DEVSTREAM_PROJECT_ROOT override preserved

Fixes: #1 (Multi-project installation broken)
Task ID: e54c3e46-91ed-4aca-bf28-284034e547d5

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## 📊 SUCCESS METRICS

- **Completion**: 100% of 10 micro-tasks with acceptance criteria met
- **Test Coverage**: E2E integration tests passing
- **Manual Validation**: 3+ real projects working correctly
- **Database Isolation**: Verified per-project separation
- **Code Quality**: ShellCheck validation passed
- **User Experience**: Clear error messages and project info display

---

**READY TO START?**
1. Mark first TodoWrite task as "in_progress"
2. Implement find_devstream_project_root() exactly as specified
3. Test the function manually
4. Mark "completed" when all acceptance criteria met
5. Proceed to next micro-task

**REMEMBER**: Execute, don't explore. Follow patterns, don't invent. Complete tasks, don't quit early. 🚀
