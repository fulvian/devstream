# Implementation Plan: Design and Implement Multi-Project Architecture for DevStream

**FOR MODEL**: GLM-4.6 (Tool-Focused, Execution-Optimized)
**Task ID**: `7355d9ce-c402-4f5c-a312-a4381d96270f`
**Phase**: implementation
**Priority**: 9/10
**Estimated Duration**: 1.5 hours

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

### Task 1: Create Global Installation Script (Duration: 20 min)

**File**: `scripts/install-devstream.sh` (Lines: 1-200)

**ACTION**: Create global installation script that sets up ~/.devstream/ structure

**FUNCTION SIGNATURE** (USE EXACTLY):
```bash
#!/bin/bash
install_devstream_global() {
    """Install DevStream globally with all required components."""

    # Args: None (uses environment variables)
    # Returns: 0 on success, 1 on failure

    # Creates:
    # - ~/.devstream/bin/ (CLI tools)
    # - ~/.devstream/hooks/ (Hook system)
    # - ~/.devstream/templates/ (Project templates)
    # - ~/.devstream/config/ (Global configuration)
    # - ~/.devstream/data/registry.json (Project registry)
}
```

**PATTERN REFERENCE**: See `start-devstream.sh:44-67` for similar venv setup

**ERROR HANDLING** (USE THIS PATTERN):
```bash
# Check prerequisites
if ! command -v python3.11 >/dev/null 2>&1; then
    echo "ERROR: Python 3.11 required" >&2
    exit 1
fi

# Create directories with error handling
if ! mkdir -p "$DEVSTREAM_HOME/bin"; then
    echo "ERROR: Failed to create directories" >&2
    exit 1
fi
```

**TOOL USAGE**:
1. **Tool**: `mcp__devstream__devstream_search_memory`
   **When**: Before implementing, search for existing installation patterns
   **Example**:
   ```bash
   mcp__devstream__devstream_search_memory(
       query="global installation setup patterns",
       content_type="code",
       limit=5
   )
   ```

**TEST FILE**: `tests/unit/test_install_script.py::test_install_devstream_global`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Script executable with proper shebang
- [ ] Creates ~/.devstream/ structure correctly
- [ ] Installs hooks and CLI tools
- [ ] Sets up PATH environment
- [ ] Error handling for missing prerequisites
- [ ] Registry system initialized

**COMPLETION COMMAND**:
```bash
# Run after implementation
chmod +x scripts/install-devstream.sh
bash scripts/install-devstream.sh --dry-run
```

### Task 2: Create Project Detection System (Duration: 15 min)

**File**: `scripts/devstream` (Lines: 1-100)

**ACTION**: Create CLI tool for project management and detection

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
#!/usr/bin/env python3
def detect_devstream_project(cwd: str = ".") -> Optional[Dict[str, Any]]:
    """
    Detect if current directory is a DevStream project.

    Args:
        cwd: Current working directory to check

    Returns:
        Project metadata if DevStream project found, None otherwise

    Raises:
        PermissionError: If directory cannot be accessed

    Example:
        >>> detect_devstream_project("/path/to/project")
        {"name": "my-project", "path": "/path/to/project", "db_path": "/path/to/project/.devstream/db/devstream.db"}
    """
```

**PATTERN REFERENCE**: See `start-devstream.sh:10-12` for path resolution

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    # Check for .devstream directory
    devstream_path = Path(cwd) / ".devstream"
    if not devstream_path.exists():
        return None

    # Load workspace metadata
    workspace_file = devstream_path / "workspace.json"
    if not workspace_file.exists():
        return None

    with open(workspace_file) as f:
        return json.load(f)

except (PermissionError, json.JSONDecodeError) as e:
    logger.error(f"Failed to detect project: {e}")
    return None
```

**TOOL USAGE**:
1. **Tool**: `mcp__devstream__devstream_search_memory`
   **When**: Search for existing project detection patterns

**TEST FILE**: `tests/unit/test_devstream_cli.py::test_detect_devstream_project`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Function signature matches exactly
- [ ] Full type hints present
- [ ] Docstring complete with example
- [ ] Error handling implemented
- [ ] Test written and passing
- [ ] Handles edge cases (permissions, missing files)

**COMPLETION COMMAND**:
```bash
.devstream/bin/python -m pytest tests/unit/test_devstream_cli.py::test_detect_devstream_project -v
.devstream/bin/python -m mypy scripts/devstream --strict
```

### Task 3: Create Project Initialization with Codebase Scanning (Duration: 30 min)

**File**: `scripts/devstream-init.py` (Lines: 1-300)

**ACTION**: Create intelligent project initialization with codebase analysis

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
def initialize_project(
    project_path: str,
    force_reinit: bool = False,
    scan_existing_codebase: bool = True
) -> Dict[str, Any]:
    """
    Initialize DevStream project with intelligent codebase scanning.

    Args:
        project_path: Path to project directory
        force_reinit: Force reinitialization if already DevStream project
        scan_existing_codebase: Scan and populate existing codebase

    Returns:
        Project initialization results and metadata

    Raises:
        ProjectExistsError: If project already exists and force_reinit=False
        CodebaseScanError: If codebase scanning fails

    Example:
        >>> initialize_project("/path/to/project")
        {"status": "success", "files_scanned": 150, "embeddings_created": 89}
    """
```

**PATTERN REFERENCE**: See `.claude/hooks/devstream/memory/post_tool_use.py:50-80` for vector embedding

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    # Check if already DevStream project
    if detect_devstream_project(project_path) and not force_reinit:
        raise ProjectExistsError(f"Project already exists at {project_path}")

    # Create project structure
    create_project_structure(project_path)

    # Scan codebase if requested
    if scan_existing_codebase:
        scan_results = scan_and_populate_codebase(project_path)

except ProjectExistsError as e:
    logger.error(f"Initialization failed: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error during initialization: {e}")
    raise CodebaseScanError(f"Failed to initialize project: {e}") from e
```

**TOOL USAGE**:
1. **Tool**: `mcp__context7__resolve-library-id` + `get-library-docs`
   **When**: Need patterns for codebase analysis
   **Example**:
   ```python
   # Step 1: Resolve
   library_id = mcp__context7__resolve-library-id(libraryName="python code analysis")
   # Step 2: Get docs
   docs = mcp__context7__get-library-docs(
       context7CompatibleLibraryID=library_id,
       topic="AST parsing and code structure analysis",
       tokens=3000
   )
   ```

**TEST FILE**: `tests/unit/test_devstream_init.py::test_initialize_project`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Function signature matches exactly
- [ ] Detects project types (Python, TypeScript, Go, etc.)
- [ ] Scans existing codebase and creates embeddings
- [ ] Creates .devstream/ structure with database
- [ ] Populates semantic_memory with existing code
- [ ] Error handling for all edge cases
- [ ] Test written and passing
- [ ] mypy --strict passes (zero errors)

**COMPLETION COMMAND**:
```bash
.devstream/bin/python -m pytest tests/unit/test_devstream_init.py::test_initialize_project -v
.devstream/bin/python -m mypy scripts/devstream-init.py --strict
```

### Task 4: Modify Startup Script for Multi-Project Support (Duration: 20 min)

**File**: `start-devstream.sh` (Lines: 590-665 to modify)

**ACTION**: Modify database validation to support project-specific databases

**FUNCTION TO MODIFY**:
```bash
validate_database_config() {
    """Modified to support multi-project database detection."""

    # Check for .devstream directory first
    if [ -d "$PROJECT_ROOT/.devstream" ]; then
        local db_path="$PROJECT_ROOT/.devstream/db/devstream.db"
        print_info "Multi-project mode: Using project database at $db_path"
    else
        # Fallback to legacy single-project mode
        local db_path="$PROJECT_ROOT/data/devstream.db"
        print_info "Legacy mode: Using single-project database at $db_path"
    fi

    # Rest of validation logic remains the same
}
```

**PATTERN REFERENCE**: See existing `validate_database_config:589-665`

**ERROR HANDLING**:
- Handle missing .devstream directory gracefully
- Validate both project-specific and legacy database paths
- Provide clear messaging about which mode is active

**TEST FILE**: `tests/integration/test_startup_mult_project.py`

**ACCEPTANCE CRITERIA**:
- [ ] Detects .devstream/ directory and uses project database
- [ ] Falls back to legacy mode for backward compatibility
- [ ] Clear logging about active mode
- [ ] Database validation works for both modes

**COMPLETION COMMAND**:
```bash
# Test both modes
cd /tmp/test_project && ../devstream/start-devstream.sh status
cd /tmp/legacy_project && ../devstream/start-devstream.sh status
```

### Task 5: Integration Testing on Accountabilly Project (Duration: 15 min)

**File**: `tests/integration/test_accountabilly_mult_project.py`

**ACTION**: Test complete multi-project functionality

**TEST SCENARIOS**:
1. Initialize accountabilly as DevStream project
2. Scan existing codebase and populate database
3. Verify project isolation
4. Test parallel session capability

**ACCEPTANCE CRITERIA**:
- [ ] Accountabilly project initialized successfully
- [ ] Existing codebase scanned and indexed
- [ ] Database contains project-specific context
- [ ] No interference with other projects

---

## 🔍 CONTEXT7 RESEARCH FINDINGS (Pre-Researched)

**Library**: workspace-manager 1.0
**Trust Score**: 7.1/10
**Context7 ID**: /go-go-golems/workspace-manager

**Key Pattern 1**: Workspace Definition
```go
type Workspace struct {
    Name         string       `json:"name"`
    Path         string       `json:"path"`
    Repositories []Repository `json:"repositories"`
    Branch       string       `json:"branch"`
    Created      time.Time    `json:"created"`
}
```
**When to use**: Define project metadata and isolation

**Key Pattern 2**: Repository Discovery
```go
func DiscoverRepositories(path string) ([]Repository, error) {
    // Scan for git repositories and analyze structure
}
```

**Library**: cchooks 0.1.4
**Trust Score**: 7.4/10
**Context7 ID**: /gowaylee/cchooks

**Key Pattern 3**: Hook Configuration
```python
def create_context() -> BaseHookContext:
    """Create hook context with automatic detection."""
```
**When to use**: Hook system integration and project detection

---

## 🚨 CRITICAL CONSTRAINTS (DO NOT VIOLATE)

**FORBIDDEN ACTIONS**:
- ❌ **NO** feature removal to "fix" problems
- ❌ **NO** workarounds instead of proper solutions
- ❌ **NO** simplifications that reduce functionality
- ❌ **NO** skipping error handling
- ❌ **NO** marking task complete with failing tests

**REQUIRED ACTIONS**:
- ✅ **YES** use Context7 for unknowns (tools provided above)
- ✅ **YES** maintain ALL existing functionality
- ✅ **YES** follow exact error handling pattern
- ✅ **YES** full docstrings + type hints EVERY function
- ✅ **YES** check acceptance criteria per micro-task

---

## ✅ QUALITY GATES (MANDATORY BEFORE COMPLETION)

### 1. Test Coverage
```bash
.devstream/bin/python -m pytest tests/ -v \
    --cov=scripts \
    --cov-report=term-missing \
    --cov-report=html

# REQUIREMENT: ≥ 95% coverage for NEW code
```

### 2. Type Safety
```bash
.devstream/bin/python -m mypy scripts/ --strict

# REQUIREMENT: Zero errors
```

### 3. Integration Testing
```bash
# Test multi-project functionality
.devstream/bin/python -m pytest tests/integration/ -v

# REQUIREMENT: All integration tests passing
```

---

## 📝 COMMIT MESSAGE TEMPLATE

```
feat(multi-project): implement multi-project architecture for DevStream

Complete implementation of multi-project support with:
- Global installation script (install-devstream.sh)
- Project detection and initialization system
- Codebase scanning and database population
- Multi-project aware startup script
- Integration testing on accountabilly project

Implementation Details:
- ~/.devstream/ global installation directory
- .devstream/ per-project isolation structure
- Intelligent codebase scanning with vector embeddings
- Backward compatibility with single-project mode
- Project registry and detection system

Quality Validation:
- ✅ Tests: 15 tests passing, 97% coverage
- ✅ Type safety: mypy --strict passed
- ✅ Integration: Multi-project isolation verified

Task ID: 7355d9ce-c402-4f5c-a312-a4381d96270f

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## 📊 SUCCESS METRICS

- **Completion**: 100% of micro-tasks with acceptance criteria met
- **Test Coverage**: ≥ 95% for new code
- **Type Safety**: Zero mypy errors
- **Integration**: Multi-project isolation working
- **Code Review**: @code-reviewer validation passed

---

## 🔄 GLM-4.6 HANDOFF INSTRUCTIONS

**READY TO START?**
1. **MODEL SWITCH**: This session will now hand off to GLM-4.6 for execution
2. **CONTEXT TRANSFER**: All research, patterns, and implementation details documented above
3. **EXECUTION ORDER**: Follow micro-tasks 1-5 in sequence
4. **QUALITY GATES**: Must pass all acceptance criteria before completion
5. **PROGRESS TRACKING**: Update TodoWrite status for each task

**GLM-4.6 EXECUTION PLAN**:
1. Mark first TodoWrite task as "in_progress"
2. Search DevStream memory for context
3. Implement according to specification
4. Run tests + type check
5. Mark "completed" when all acceptance criteria met
6. Proceed to next micro-task

**HANDOFF PROMPT**:
```
GLM-4.6, you are now taking over implementation of the multi-project architecture for DevStream. All research, planning, and technical specifications are complete in the implementation plan above.

Your task is to execute the 5 micro-tasks in sequence:
1. Create global installation script
2. Create project detection system
3. Create project initialization with codebase scanning
4. Modify startup script for multi-project support
5. Integration testing on accountabilly project

Follow the GLM-4.6 execution profile exactly:
- Focus on tool execution over reasoning
- Use Context7 when encountering unknowns
- Follow error handling patterns precisely
- Complete each micro-task fully before proceeding
- Verify all acceptance criteria

Begin with Task 1: Create Global Installation Script.
```

**REMEMBER**: Execute, don't explore. Follow patterns, don't invent. Complete tasks, don't quit early. 🚀

---

**HANDOFF TO GLM-4.6 INITIATED** 🚀