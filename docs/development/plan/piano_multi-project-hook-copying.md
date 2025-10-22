# Implementation Plan: Multi-Project Hook Copying with Copier Integration

**FOR MODEL**: GLM-4.6 (Tool-Focused, Execution-Optimized)
**Task ID**: `79cbed37-0030-4ec9-a628-c68aa993558a`
**Phase**: Implementation
**Priority**: 8/10
**Estimated Duration**: 2.5 hours

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

### Task 1: Install Copier library and add to requirements.txt (Duration: 10 min)

**File**: `requirements.txt` (Lines: 1-50)

**ACTION**: Add Copier library to requirements with version pinning

**FUNCTION SIGNATURE** (USE EXACTLY):
```bash
# Add to requirements.txt
copier>=9.0.0,<10.0.0
```

**PATTERN REFERENCE**: See `requirements.txt:1-20` for existing dependency format

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    # Install dependency
    result = subprocess.run([sys.executable, "-m", "pip", "install", "copier>=9.0.0"], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to install copier: {result.stderr}")
except subprocess.CalledProcessError as e:
    logger.error(
        "Copier installation failed",
        extra={"error": str(e), "returncode": e.returncode}
    )
    raise DependencyInstallationError("Failed to install Copier library") from e
```

**TOOL USAGE**:
1. **Tool**: `Read`
   **When**: Before modifying, check current requirements.txt
   **Example**:
   ```python
   Read("requirements.txt")
   ```

**TEST FILE**: `tests/unit/test_hook_copier.py::test_copier_installation`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Copier added to requirements.txt with correct version range
- [ ] Installation test passes
- [ ] Import test succeeds
- [ ] Version validation passes

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -c "import copier; print(f'Copier version: {copier.__version__}')"
.devstream/bin/python -m pytest tests/unit/test_hook_copier.py::test_copier_installation -v
```

### Task 2: Create enhanced hook copying module with Copier integration (Duration: 25 min)

**File**: `.claude/hooks/devstream/utils/multi_project_hook_copier.py` (Lines: 1-200)

**ACTION**: Create Context7-compliant hook copying system using Copier

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
async def copy_devstream_hooks_enhanced(
    source_root: Path,
    target_root: Path,
    required_directories: List[str] = None
) -> Dict[str, Any]:
    """
    Context7-compliant multi-project hook copying using Copier library.

    Provides robust copying of DevStream hooks with dependency resolution,
    error handling, and integrity validation for multi-project deployment.

    Args:
        source_root: Source DevStream root directory (typically devstream/)
        target_root: Target project root where hooks will be copied
        required_directories: List of required directories to copy
                            (defaults to all DevStream directories)

    Returns:
        Dict containing copy results, validation status, and metadata

    Raises:
        HookCopyError: If copying fails validation or encounters errors
        DependencyError: If required dependencies are missing

    Example:
        >>> result = await copy_devstream_hooks_enhanced(
        ...     source_root=Path("/Users/fulvioventura/devstream"),
        ...     target_root=Path("/Users/fulvioventura/reporting")
        ... )
        >>> result["status"]
        'success'
    """
```

**PATTERN REFERENCE**: See `.claude/hooks/devstream/utils/common.py:50-100` for similar async patterns

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    # Implementation with Copier
    result = await copier.run_copy_async(
        str(source_root / ".claude"),
        str(target_root / ".claude"),
        defaults=True,
        quiet=False,
        vcs_ref="HEAD"
    )
    logger.info("Hooks copied successfully", source=source_root, target=target_root)
    return {"status": "success", "copied_directories": required_directories}
except copier.CopierError as e:
    logger.error("Hook copying failed", error=str(e), source=source_root)
    raise HookCopyError(f"Failed to copy hooks: {e}") from e
```

**TOOL USAGE**:
1. **Tool**: `Read`
   **When**: Before implementing, study existing hook copying patterns
   **Example**:
   ```python
   Read(".claude/hooks/devstream/utils/common.py")
   ```

2. **Tool**: `mcp__context7__resolve-library-id` + `get-library-docs`
   **When**: Copier usage patterns needed
   **Example**:
   ```python
   # Step 1: Resolve
   library_id = mcp__context7__resolve-library-id(libraryName="copier")
   # Step 2: Get docs
   docs = mcp__context7__get-library-docs(
       context7CompatibleLibraryID=library_id,
       topic="run_copy_async error handling",
       tokens=3000
   )
   ```

**TEST FILE**: `tests/unit/test_multi_project_hook_copier.py::test_copy_hooks_enhanced`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Function signature matches exactly
- [ ] Full type hints present
- [ ] Docstring complete with example
- [ ] Copier integration implemented
- [ ] Error handling for CopierError
- [ ] Test written and passing
- [ ] mypy --strict passes (zero errors)

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -m pytest tests/unit/test_multi_project_hook_copier.py::test_copy_hooks_enhanced -v
.devstream/bin/python -m mypy .claude/hooks/devstream/utils/multi_project_hook_copier.py --strict
```

### Task 3: Fix Agent Auto-Delegation relative import issues (Duration: 20 min)

**File**: `.claude/hooks/devstream/agents/pattern_matcher.py` (Lines: 1-50)

**ACTION**: Resolve Python relative import errors in agent system

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
def load_pattern_catalog() -> Dict[str, Any]:
    """
    Load agent pattern catalog with proper import handling.

    Fixes relative import issues that prevent Agent Auto-Delegation
    from working in multi-project mode.

    Args:
        None

    Returns:
        Dict containing loaded pattern catalog

    Raises:
        PatternLoadError: If pattern catalog fails to load

    Example:
        >>> catalog = load_pattern_catalog()
        >>> "file_pattern_mappings" in catalog
        True
    """
```

**PATTERN REFERENCE**: See `.claude/hooks/devstream/agents/pattern_matcher.py:15-30` for current problematic imports

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    # Fix relative imports
    from .pattern_catalog import pattern_catalog
    return pattern_catalog
except ImportError as e:
    logger.error("Pattern catalog import failed", error=str(e))
    # Fallback to absolute import
    try:
        from claude.hooks.devstream.agents.pattern_catalog import pattern_catalog
        return pattern_catalog
    except ImportError as fallback_error:
        raise PatternLoadError(f"Failed to load pattern catalog: {fallback_error}") from fallback_error
```

**TOOL USAGE**:
1. **Tool**: `Read`
   **When**: Before fixing, examine current import structure
   **Example**:
   ```python
   Read(".claude/hooks/devstream/agents/pattern_matcher.py")
   ```

**TEST FILE**: `tests/unit/test_pattern_matcher.py::test_load_pattern_catalog`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Relative imports fixed
- [ ] Fallback import mechanism implemented
- [ ] Pattern catalog loads successfully
- [ ] Test written and passing
- [ ] Import errors resolved in multi-project mode

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -c "from .claude.hooks.devstream.agents.pattern_matcher import load_pattern_catalog; print('Import test passed')"
.devstream/bin/python -m pytest tests/unit/test_pattern_matcher.py::test_load_pattern_catalog -v
```

### Task 4: Implement integrity validation for copied hooks (Duration: 20 min)

**File**: `.claude/hooks/devstream/utils/hook_integrity_validator.py` (Lines: 1-150)

**ACTION**: Add post-copy validation and checksum verification

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
async def validate_hook_integrity(
    target_root: Path,
    required_directories: List[str]
) -> Dict[str, Any]:
    """
    Validate integrity of copied DevStream hooks using checksums.

    Ensures all required directories and files are present and uncorrupted
    after multi-project hook copying operations.

    Args:
        target_root: Target project root to validate
        required_directories: List of directories that must be present

    Returns:
        Dict containing validation results, missing files, and checksums

    Raises:
        HookValidationError: If validation fails or critical files missing

    Example:
        >>> result = await validate_hook_integrity(
        ...     target_root=Path("/Users/fulvioventura/reporting"),
        ...     required_directories=["protocol", "agents", "context"]
        ... )
        >>> result["valid"]
        True
    """
```

**PATTERN REFERENCE**: See `.claude/hooks/devstream/utils/common.py:100-150` for validation patterns

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    # Implementation with checksum validation
    missing_dirs = []
    for dir_name in required_directories:
        dir_path = target_root / ".claude" / "hooks" / "devstream" / dir_name
        if not dir_path.exists():
            missing_dirs.append(dir_name)

    if missing_dirs:
        raise HookValidationError(f"Missing required directories: {missing_dirs}")

    logger.info("Hook integrity validation passed", target_root=target_root)
    return {"valid": True, "missing_directories": []}
except Exception as e:
    logger.error("Hook integrity validation failed", error=str(e))
    raise HookValidationError(f"Integrity validation failed: {e}") from e
```

**TOOL USAGE**:
1. **Tool**: `Read`
   **When**: Before implementing, study existing validation patterns
   **Example**:
   ```python
   Read(".claude/hooks/devstream/utils/common.py")
   ```

**TEST FILE**: `tests/unit/test_hook_integrity_validator.py::test_validate_hook_integrity`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Directory presence validation implemented
- [ ] Checksum verification for critical files
- [ ] Detailed validation reporting
- [ ] Test written and passing
- [ ] mypy --strict passes (zero errors)

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -m pytest tests/unit/test_hook_integrity_validator.py::test_validate_hook_integrity -v
.devstream/bin/python -m mypy .claude/hooks/devstream/utils/hook_integrity_validator.py --strict
```

### Task 5: Create comprehensive test suite for multi-project deployment (Duration: 25 min)

**File**: `tests/integration/test_multi_project_deployment.py` (Lines: 1-200)

**ACTION**: Test hook copying from various project roots

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
@pytest.mark.asyncio
async def test_multi_project_hook_copying_end_to_end():
    """
    End-to-end test of multi-project hook copying functionality.

    Tests complete workflow from source to target project with validation
    and error handling for various scenarios.

    Args:
        None (pytest fixture)

    Returns:
        None (pytest assertion)

    Raises:
        AssertionError: If any test condition fails

    Example:
        >>> await test_multi_project_hook_copying_end_to_end()
        # Should pass without assertion errors
    """
```

**PATTERN REFERENCE**: See `tests/integration/test_memory_vector_enhancement.py:50-100` for integration test patterns

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    # Test implementation
    result = await copy_devstream_hooks_enhanced(
        source_root=test_source_dir,
        target_root=test_target_dir
    )
    assert result["status"] == "success"

    validation = await validate_hook_integrity(test_target_dir, required_dirs)
    assert validation["valid"] is True

    logger.info("Multi-project test passed", source=test_source_dir, target=test_target_dir)
except Exception as e:
    logger.error("Multi-project test failed", error=str(e))
    raise AssertionError(f"Multi-project test failed: {e}") from e
```

**TOOL USAGE**:
1. **Tool**: `Read`
   **When**: Before implementing, study existing integration test patterns
   **Example**:
   ```python
   Read("tests/integration/test_memory_vector_enhancement.py")
   ```

**TEST FILE**: `tests/integration/test_multi_project_deployment.py::test_multi_project_hook_copying_end_to_end`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] End-to-end workflow tested
- [ ] Multiple project root scenarios tested
- [ ] Error scenarios tested and handled
- [ ] Cleanup procedures implemented
- [ ] Test passes consistently

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -m pytest tests/integration/test_multi_project_deployment.py::test_multi_project_hook_copying_end_to_end -v
```

### Task 6: Update bootstrap system to use enhanced hook copying (Duration: 15 min)

**File**: `scripts/devstream-init.py` (Lines: 200-300)

**ACTION**: Integrate new hook copying into DevStream bootstrap

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
async def setup_devstream_multi_project(target_root: Path) -> bool:
    """
    Setup DevStream hooks for multi-project deployment using enhanced copying.

    Replaces basic hook copying with Context7-compliant Copier-based system
    that includes all required directories and validation.

    Args:
        target_root: Target project root directory

    Returns:
        bool: True if setup successful, False otherwise

    Raises:
        DevStreamSetupError: If setup fails critically

    Example:
        >>> success = await setup_devstream_multi_project(Path("/Users/fulvioventura/reporting"))
        >>> success
        True
    """
```

**PATTERN REFERENCE**: See `scripts/devstream-init.py:150-250` for existing setup functions

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    # Implementation with enhanced hook copying
    devstream_root = Path(__file__).parent.parent

    result = await copy_devstream_hooks_enhanced(
        source_root=devstream_root,
        target_root=target_root,
        required_directories=["protocol", "agents", "context", "memory", "sessions", "utils"]
    )

    if result["status"] != "success":
        raise DevStreamSetupError(f"Hook copying failed: {result}")

    logger.info("Multi-project setup completed", target_root=target_root)
    return True
except Exception as e:
    logger.error("Multi-project setup failed", error=str(e), target_root=target_root)
    raise DevStreamSetupError(f"Failed to setup multi-project: {e}") from e
```

**TOOL USAGE**:
1. **Tool**: `Read`
   **When**: Before modifying, examine current bootstrap implementation
   **Example**:
   ```python
   Read("scripts/devstream-init.py")
   ```

**TEST FILE**: `tests/unit/test_devstream_init.py::test_setup_devstream_multi_project`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Bootstrap system updated to use enhanced copying
- [ ] Backward compatibility maintained
- [ ] Error handling implemented
- [ ] Test written and passing
- [ ] Integration works with existing setup

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -m pytest tests/unit/test_devstream_init.py::test_setup_devstream_multi_project -v
```

### Task 6a: Update start-devstream.sh to integrate enhanced hook copying (Duration: 20 min)

**File**: `start-devstream.sh` (Lines: 86-120)

**ACTION**: Add hook copying integration to main launcher for multi-project mode

**FUNCTION SIGNATURE** (USE EXACTLY):
```bash
# Function to ensure DevStream hooks are copied in multi-project mode
ensure_devstream_hooks_copied() {
    local target_root="$1"

    print_status "Ensuring DevStream hooks are copied..."

    # Only run in multi-project mode
    if [ -z "${DEVSTREAM_PROJECT_ROOT:-}" ]; then
        print_info "Single-project mode detected, skipping hook copying"
        return 0
    fi

    # Check if hooks already exist
    local required_dirs=("protocol" "agents" "context" "memory" "sessions" "utils")
    local missing_dirs=()

    for dir_name in "${required_dirs[@]}"; do
        if [ ! -d "$target_root/.claude/hooks/devstream/$dir_name" ]; then
            missing_dirs+=("$dir_name")
        fi
    done

    # If all directories exist, no action needed
    if [ ${#missing_dirs[@]} -eq 0 ]; then
        print_info "All required hook directories already present"
        return 0
    fi

    print_info "Missing hook directories: ${missing_dirs[*]}"
    print_info "Running enhanced hook copying..."

    # Use enhanced hook copying with Copier
    local hook_copying_result=$(PYTHONPATH="$DEVSTREAM_SCRIPT_DIR/.claude/hooks/devstream/utils" \
        "$VENV_DIR/bin/python" -c "
import asyncio
import sys
import structlog
from pathlib import Path

sys.path.insert(0, '$DEVSTREAM_SCRIPT_DIR/.claude/hooks/devstream/utils')
from multi_project_hook_copier import copy_devstream_hooks_enhanced

async def copy_hooks():
    try:
        result = await copy_devstream_hooks_enhanced(
            source_root=Path('$DEVSTREAM_SCRIPT_DIR'),
            target_root=Path('$target_root'),
            required_directories=['protocol', 'agents', 'context', 'memory', 'sessions', 'utils']
        )
        return result
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

# Run async function in sync context
result=$(python3 -c "
import asyncio
result = asyncio.run(copy_hooks())
print(result.get('status', 'unknown'))
" 2>/dev/null)

    if [[ "$result" == "success" ]]; then
        print_status "✅ Enhanced hook copying completed"
        return 0
    else
        print_error "❌ Enhanced hook copying failed"
        return 1
    fi
}
```

**INTEGRATION POINT**: Add to `verify_agent_delegation()` function (lines 86-120):

```bash
verify_agent_delegation() {
  print_status "Verifying Agent Auto-Delegation System..."

  # NEW: Ensure hooks are copied in multi-project mode
  if [ -n "${DEVSTREAM_PROJECT_ROOT:-}" ]; then
    print_info "Multi-project mode detected, ensuring hooks are copied..."
    if ! ensure_devstream_hooks_copied "$PROJECT_ROOT"; then
      print_error "Failed to ensure DevStream hooks are copied"
      return 1
    fi
  fi

  # Existing verification logic continues...
```

**PATTERN REFERENCE**: See existing `verify_agent_delegation()` function for integration pattern

**ERROR HANDLING** (USE THIS PATTERN):
```bash
# In verify_agent_delegation() function
if ! ensure_devstream_hooks_copied "$PROJECT_ROOT"; then
    print_error "Agent Auto-Delegation setup failed"
    return 1
fi

# Continue with existing verification...
```

**TOOL USAGE**:
1. **Tool**: `Read`
   **When**: Before modifying, examine existing verify_agent_delegation function
   **Example**:
   ```python
   Read("start-devstream.sh", lines=86-120)
   ```

**TEST FILE**: `tests/integration/test_start_devstream.sh::test_verify_agent_delegation_multi_project`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Hook copying integration added to main launcher
- [ ] Multi-project mode detection implemented
- [] Required directories validation
- [ ] Error handling for hook copying failures
- [ ] Integration with existing verification logic
- [ ] Test written and passing

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -m pytest tests/integration/test_start_devstream.sh::test_verify_agent_delegation_multi_project -v
```

### Task 7: Test complete solution in multi-project environment (Duration: 20 min)

**File**: Multiple files (integration test)

**ACTION**: End-to-end testing of Protocol Enforcement in multi-project mode

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
@pytest.mark.asyncio
async def test_protocol_enforcement_multi_project():
    """
    Test Protocol Enforcement system functionality in multi-project mode.

    Verifies that Protocol Enforcement, Agent Auto-Delegation, and Direct DB
    Natural Language Commands work correctly after hook copying.

    Args:
        None (pytest fixture)

    Returns:
        None (pytest assertion)

    Raises:
        AssertionError: If protocol enforcement fails in multi-project mode

    Example:
        >>> await test_protocol_enforcement_multi_project()
        # Should pass without assertion errors
    """
```

**PATTERN REFERENCE**: See `tests/integration/` for protocol enforcement test patterns

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    # Test protocol enforcement in multi-project context
    from .claude.hooks.devstream.protocol.protocol_state_manager import ProtocolStateManager
    from .claude.hooks.devstream.agents.pattern_matcher import load_pattern_catalog

    # Test imports work
    manager = ProtocolStateManager()
    catalog = load_pattern_catalog()

    assert manager is not None
    assert catalog is not None
    assert len(catalog) > 0

    logger.info("Protocol enforcement multi-project test passed")
except Exception as e:
    logger.error("Protocol enforcement multi-project test failed", error=str(e))
    raise AssertionError(f"Protocol enforcement failed: {e}") from e
```

**TOOL USAGE**:
1. **Tool**: `Read`
   **When**: Before implementing, study protocol enforcement tests
   **Example**:
   ```python
   Read(".claude/hooks/devstream/protocol/protocol_state_manager.py")
   ```

**TEST FILE**: `tests/integration/test_multi_project_deployment.py::test_protocol_enforcement_multi_project`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Protocol Enforcement works in multi-project mode
- [ ] Agent Auto-Delegation functions correctly
- [ ] Direct DB commands operational
- [ ] All critical imports succeed
- [ ] No UserPromptSubmit hook errors

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -m pytest tests/integration/test_multi_project_deployment.py::test_protocol_enforcement_multi_project -v
```

### Task 8: Performance optimization and error handling refinement (Duration: 15 min)

**File**: `.claude/hooks/devstream/utils/multi_project_hook_copier.py` (Lines: 150-250)

**ACTION**: Optimizing copy performance and error resilience

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
def optimize_copy_performance(
    source_root: Path,
    target_root: Path
) -> Dict[str, Any]:
    """
    Optimize hook copying performance for large projects.

    Implements parallel copying, incremental updates, and caching
    to improve performance for large-scale deployments.

    Args:
        source_root: Source DevStream root directory
        target_root: Target project root directory

    Returns:
        Dict containing optimization metrics and recommendations

    Raises:
        OptimizationError: If optimization fails

    Example:
        >>> metrics = optimize_copy_performance(source, target)
        >>> metrics["improvement_percent"]
        45.2
    """
```

**PATTERN REFERENCE**: See existing performance patterns in codebase

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    # Performance optimization implementation
    start_time = time.time()

    # Optimized copying logic
    # ...

    end_time = time.time()
    improvement = calculate_improvement(start_time, end_time)

    logger.info("Copy performance optimized", improvement_percent=improvement)
    return {"improvement_percent": improvement, "status": "optimized"}
except Exception as e:
    logger.error("Performance optimization failed", error=str(e))
    raise OptimizationError(f"Failed to optimize performance: {e}") from e
```

**TOOL USAGE**:
1. **Tool**: `Read`
   **When**: Before optimizing, examine current performance bottlenecks
   **Example**:
   ```python
   Read(".claude/hooks/devstream/utils/multi_project_hook_copier.py")
   ```

**TEST FILE**: `tests/unit/test_multi_project_hook_copier.py::test_optimize_copy_performance`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Performance improvements implemented
- [ ] Parallel copying for large directories
- [ ] Incremental update support
- [ ] Performance metrics collection
- [ ] Optimization recommendations provided

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -m pytest tests/unit/test_multi_project_hook_copier.py::test_optimize_copy_performance -v
```

### Task 9: Documentation update for multi-project deployment (Duration: 15 min)

**File**: `docs/guides/multi-project-deployment.md` (Lines: 1-100)

**ACTION**: Updating docs with new multi-project capabilities

**FUNCTION SIGNATURE** (USE EXACTLY):
```markdown
# Multi-Project Deployment Guide

## Overview
...
```

**PATTERN REFERENCE**: See existing documentation patterns in `docs/`

**ERROR HANDLING** (USE THIS PATTERN):
```python
# Documentation validation
def validate_documentation():
    """Ensure documentation is complete and accurate."""
    # Implementation
    pass
```

**TOOL USAGE**:
1. **Tool**: `Read`
   **When**: Before updating, review existing documentation structure
   **Example**:
   ```python
   Read("docs/guides/")
   ```

**TEST FILE**: `tests/unit/test_documentation.py::test_multi_project_deployment_docs`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Multi-project deployment guide created
- [ ] Usage examples provided
- [ ] Troubleshooting section included
- [ ] Integration with existing docs
- [ ] Documentation validation passes

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -m pytest tests/unit/test_documentation.py::test_multi_project_deployment_docs -v
```

### Task 10: Final validation and code review (Duration: 15 min)

**File**: Multiple files (final validation)

**ACTION**: Final testing, code review, and quality validation

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
async def final_validation_suite():
    """
    Comprehensive final validation of multi-project hook copying solution.

    Runs all tests, validates code quality, checks performance, and ensures
    all acceptance criteria are met before completion.

    Args:
        None

    Returns:
        Dict containing validation results and quality metrics

    Raises:
        ValidationError: If any validation criterion fails

    Example:
        >>> results = await final_validation_suite()
        >>> results["all_tests_passed"]
        True
    """
```

**PATTERN REFERENCE**: See existing validation patterns

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    # Comprehensive validation
    test_results = run_all_tests()
    quality_metrics = run_quality_checks()
    performance_results = run_performance_benchmarks()

    if not test_results["all_passed"]:
        raise ValidationError("Some tests failed")

    if quality_metrics["coverage"] < 95:
        raise ValidationError(f"Coverage too low: {quality_metrics['coverage']}%")

    logger.info("Final validation passed", all_tests_passed=True)
    return {"status": "success", "validation_passed": True}
except Exception as e:
    logger.error("Final validation failed", error=str(e))
    raise ValidationError(f"Final validation failed: {e}") from e
```

**TOOL USAGE**:
1. **Tool**: `Bash`
   **When**: Running final validation commands
   **Example**:
   ```bash
   .devstream/bin/python -m pytest tests/ -v --cov=.claude/hooks/devstream
   ```

**TEST FILE**: All test files

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] All tests pass (100% pass rate)
- [ ] Coverage ≥ 95% for new code
- [ ] mypy --strict passes (zero errors)
- [ ] Performance benchmarks met
- [ ] Code review validation passed
- [ ] Documentation complete and accurate

**COMPLETION COMMAND**:
```bash
# Run final validation
.devstream/bin/python -m pytest tests/ -v --cov=.claude/hooks/devstream --cov-report=term-missing
.devstream/bin/python -m mypy .claude/hooks/devstream/utils/multi_project_hook_copier.py --strict
.devstream/bin/python -m flake8 .claude/hooks/devstream/utils/multi_project_hook_copier.py
```

---

## 🔍 CONTEXT7 RESEARCH FINDINGS (Pre-Researched)

**Library**: copier 9.0.0
**Trust Score**: 7.4/10
**Context7 ID**: /copier-org/copier

**Key Pattern 1**: Async copier operations
```python
import copier
import asyncio

async def copy_with_copier(source, destination):
    """Async copying with proper error handling."""
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
**When to use**: Template-based project copying with Jinja templating

**Key Pattern 2**: Robust error handling
```python
import structlog

logger = structlog.get_logger()

def handle_copier_errors(func):
    """Decorator for Copier error handling."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except copier.CopierError as e:
            logger.error("Copier operation failed", error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error", error=str(e))
            raise
    return wrapper
```

**Key Pattern 3**: Integrity validation
```python
import hashlib
from pathlib import Path

def validate_copied_files(target_path, checksums):
    """Validate copied files using checksums."""
    for file_path, expected_checksum in checksums.items():
        full_path = target_path / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"Missing file: {file_path}")

        actual_checksum = hashlib.sha256(full_path.read_bytes()).hexdigest()
        if actual_checksum != expected_checksum:
            raise ValueError(f"Checksum mismatch: {file_path}")

    return True
```

**When to use**: Post-copy validation to ensure integrity

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
    --cov=.claude/hooks/devstream \
    --cov-report=term-missing \
    --cov-report=html

# REQUIREMENT: ≥ 95% coverage for NEW code
```

### 2. Type Safety
```bash
.devstream/bin/python -m mypy .claude/hooks/devstream/utils/multi_project_hook_copier.py --strict

# REQUIREMENT: Zero errors
```

### 3. Performance Benchmark
```bash
# Test copying performance
time .devstream/bin/python -c "
import asyncio
from pathlib import Path
from claude.hooks.devstream.utils.multi_project_hook_copier import copy_devstream_hooks_enhanced

async def test():
    await copy_devstream_hooks_enhanced(
        Path('/Users/fulvioventura/devstream'),
        Path('/tmp/test-project')
    )

asyncio.run(test())
"

# TARGET: < 30 seconds for complete hook copying
```

---

## 📝 COMMIT MESSAGE TEMPLATE

```
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
```

---

## 📊 SUCCESS METRICS

- **Completion**: 100% of micro-tasks with acceptance criteria met
- **Test Coverage**: ≥ 95% for new code
- **Type Safety**: Zero mypy errors
- **Performance**: < 30 seconds hook copying
- **Code Review**: @code-reviewer validation passed

---

**READY TO START?**
1. Mark first TodoWrite task as "in_progress"
2. Search DevStream memory for context
3. Implement according to specification
4. Run tests + type check
5. Mark "completed" when all acceptance criteria met
6. Proceed to next micro-task

**REMEMBER**: Execute, don't explore. Follow patterns, don't invent. Complete tasks, don't quit early. 🚀