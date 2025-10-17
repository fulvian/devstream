"""
Tests for Hook Integrity Validator - Context7 Compliant Implementation.

Tests comprehensive integrity validation for DevStream hooks in multi-project environments.
"""

import pytest
import tempfile
import shutil
import json
import asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

# Import the module under test
import sys
sys.path.append(str(Path(__file__).parent.parent.parent / ".claude" / "hooks" / "devstream" / "utils"))

try:
    from hook_integrity_validator import (
        HookIntegrityValidator,
        ValidationResult,
        HookMetadata,
        validate_project_hooks
    )
    INTEGRITY_VALIDATOR_AVAILABLE = True
except ImportError:
    INTEGRITY_VALIDATOR_AVAILABLE = False
    HookIntegrityValidator = None
    ValidationResult = None
    HookMetadata = None


class TestHookIntegrityValidator:
    """Test suite for HookIntegrityValidator functionality."""

    @pytest.fixture
    def temp_devstream_root(self):
        """Create a temporary DevStream root directory with hooks."""
        with tempfile.TemporaryDirectory() as temp_dir:
            devstream_root = Path(temp_dir)

            # Create .claude/hooks/devstream structure
            hooks_dir = devstream_root / ".claude" / "hooks" / "devstream"
            hooks_dir.mkdir(parents=True)

            # Create test hooks
            test_hooks = {
                "memory/pre_tool_use.py": """
import asyncio
import structlog
from pathlib import Path

logger = structlog.get_logger(__name__)

async def main():
    logger.info("PreToolUse hook executed")
    return True

if __name__ == "__main__":
    asyncio.run(main())
""",
                "utils/direct_client.py": """
import sqlite3
import structlog

logger = structlog.get_logger(__name__)

def get_direct_client():
    '''Get direct database client.'''
    return MockClient()

class MockClient:
    def search_memory(self, query, limit=10):
        return {"results": []}
""",
                "context/user_query_context_enhancer.py": """
import json
import sys

def enhance_query(query):
    return f"Enhanced: {query}"

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "test"
    print(enhance_query(query))
"""
            }

            for hook_path, content in test_hooks.items():
                full_path = hooks_dir / hook_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)

            yield devstream_root

    @pytest.fixture
    def temp_project_root(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.mark.skipif(not INTEGRITY_VALIDATOR_AVAILABLE, reason="HookIntegrityValidator not available")
    def test_validator_initialization(self, temp_devstream_root):
        """Test HookIntegrityValidator initialization."""
        validator = HookIntegrityValidator(str(temp_devstream_root))

        assert validator.devstream_root == temp_devstream_root.resolve()
        assert validator.framework_hooks.resolve() == (temp_devstream_root / ".claude" / "hooks" / "devstream").resolve()
        assert isinstance(validator.validation_cache, dict)

    @pytest.mark.skipif(not INTEGRITY_VALIDATOR_AVAILABLE, reason="HookIntegrityValidator not available")
    @pytest.mark.asyncio
    async def test_validate_project_hooks_success(self, temp_devstream_root, temp_project_root):
        """Test successful project hooks validation."""
        # Copy hooks to project
        project_hooks = temp_project_root / ".claude" / "hooks" / "devstream"
        project_hooks.mkdir(parents=True)

        # Copy a test hook
        source_hook = temp_devstream_root / ".claude" / "hooks" / "devstream" / "memory" / "pre_tool_use.py"
        target_hook = project_hooks / "memory" / "pre_tool_use.py"
        target_hook.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_hook, target_hook)

        validator = HookIntegrityValidator(str(temp_devstream_root))
        overall_valid, results = await validator.validate_project_hooks(str(temp_project_root))

        assert overall_valid is True
        assert len(results) > 0

        # Check result structure
        for result in results:
            assert isinstance(result, ValidationResult)
            assert result.hook_name is not None
            assert result.validation_type is not None
            assert result.timestamp is not None
            assert result.project_root == str(temp_project_root)

    @pytest.mark.skipif(not INTEGRITY_VALIDATOR_AVAILABLE, reason="HookIntegrityValidator not available")
    @pytest.mark.asyncio
    async def test_validate_project_hooks_missing_directory(self, temp_devstream_root, temp_project_root):
        """Test validation when hooks directory doesn't exist."""
        validator = HookIntegrityValidator(str(temp_devstream_root))
        overall_valid, results = await validator.validate_project_hooks(str(temp_project_root))

        assert overall_valid is False
        assert len(results) == 1
        assert results[0].valid is False
        assert results[0].severity == "critical"
        assert "does not exist" in results[0].message

    @pytest.mark.skipif(not INTEGRITY_VALIDATOR_AVAILABLE, reason="HookIntegrityValidator not available")
    @pytest.mark.asyncio
    async def test_file_existence_validation(self, temp_devstream_root, temp_project_root):
        """Test file existence validation."""
        # Create hooks directory but no files
        project_hooks = temp_project_root / ".claude" / "hooks" / "devstream"
        project_hooks.mkdir(parents=True)

        validator = HookIntegrityValidator(str(temp_devstream_root))
        result = await validator._validate_file_existence(str(temp_project_root), "non_existent.py")

        assert result[0] is False  # not valid
        assert result[1]["exists"] is False

    @pytest.mark.skipif(not INTEGRITY_VALIDATOR_AVAILABLE, reason="HookIntegrityValidator not available")
    @pytest.mark.asyncio
    async def test_syntax_validation(self, temp_devstream_root, temp_project_root):
        """Test Python syntax validation."""
        project_hooks = temp_project_root / ".claude" / "hooks" / "devstream"
        project_hooks.mkdir(parents=True)

        # Test valid Python file
        valid_hook = project_hooks / "valid_hook.py"
        valid_hook.write_text("print('Hello, World!')")

        validator = HookIntegrityValidator(str(temp_devstream_root))
        valid, details = await validator._validate_syntax(str(temp_project_root), "valid_hook.py")

        assert valid is True
        assert details["syntax_valid"] is True

        # Test invalid Python file
        invalid_hook = project_hooks / "invalid_hook.py"
        invalid_hook.write_text("print('Hello, World!'")  # Missing closing parenthesis

        valid, details = await validator._validate_syntax(str(temp_project_root), "invalid_hook.py")

        assert valid is False
        assert details["syntax_valid"] is False

    @pytest.mark.skipif(not INTEGRITY_VALIDATOR_AVAILABLE, reason="HookIntegrityValidator not available")
    @pytest.mark.asyncio
    async def test_dependency_validation(self, temp_devstream_root, temp_project_root):
        """Test dependency validation."""
        project_hooks = temp_project_root / ".claude" / "hooks" / "devstream"
        project_hooks.mkdir(parents=True)

        # Create hook with standard library dependencies
        hook_with_stdlib = project_hooks / "stdlib_hook.py"
        hook_with_stdlib.write_text("""
import os
import sys
from pathlib import Path

def main():
    return True
""")

        validator = HookIntegrityValidator(str(temp_devstream_root))
        valid, details = await validator._validate_dependencies(str(temp_project_root), "stdlib_hook.py")

        assert valid is True  # Standard library dependencies should be available
        assert len(details["missing_dependencies"]) == 0

    @pytest.mark.skipif(not INTEGRITY_VALIDATOR_AVAILABLE, reason="HookIntegrityValidator not available")
    @pytest.mark.asyncio
    async def test_functionality_validation(self, temp_devstream_root, temp_project_root):
        """Test basic functionality validation."""
        project_hooks = temp_project_root / ".claude" / "hooks" / "devstream"
        project_hooks.mkdir(parents=True)

        # Create functional hook
        functional_hook = project_hooks / "functional_hook.py"
        functional_hook.write_text("""
def test_function():
    return "test_result"

if __name__ == "__main__":
    print(test_function())
""")

        validator = HookIntegrityValidator(str(temp_devstream_root))
        valid, details = await validator._validate_functionality(str(temp_project_root), "functional_hook.py")

        # Should be valid as the module can be imported
        assert valid is True
        assert details["functionality_test"] == "module_import"

    @pytest.mark.skipif(not INTEGRITY_VALIDATOR_AVAILABLE, reason="HookIntegrityValidator not available")
    @pytest.mark.asyncio
    async def test_integration_validation(self, temp_devstream_root, temp_project_root):
        """Test integration validation."""
        # Create proper project structure
        project_hooks = temp_project_root / ".claude" / "hooks" / "devstream"
        project_hooks.mkdir(parents=True)

        # Create settings.json
        settings_file = temp_project_root / ".claude" / "settings.json"
        settings_file.write_text(json.dumps({
            "hooks": {
                "PreToolUse": [{
                    "hooks": [{
                        "command": "python hook.py"
                    }]
                }]
            }
        }))

        validator = HookIntegrityValidator(str(temp_devstream_root))
        valid, details = await validator._validate_integration(str(temp_project_root), "test_hook.py")

        # Integration validation checks structure, not specific hook existence
        # For this test, we create a mock hook file to ensure structure validation passes
        test_hook_file = project_hooks / "test_hook.py"
        test_hook_file.write_text("print('test')")

        valid, details = await validator._validate_integration(str(temp_project_root), "test_hook.py")

        assert details["project_structure_valid"] is True
        assert details["settings_compatible"] is True

    @pytest.mark.skipif(not INTEGRITY_VALIDATOR_AVAILABLE, reason="HookIntegrityValidator not available")
    @pytest.mark.asyncio
    async def test_generate_integrity_report(self, temp_devstream_root, temp_project_root):
        """Test integrity report generation."""
        # Copy a hook to project
        project_hooks = temp_project_root / ".claude" / "hooks" / "devstream"
        project_hooks.mkdir(parents=True)

        source_hook = temp_devstream_root / ".claude" / "hooks" / "devstream" / "memory" / "pre_tool_use.py"
        target_hook = project_hooks / "memory" / "pre_tool_use.py"
        target_hook.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_hook, target_hook)

        validator = HookIntegrityValidator(str(temp_devstream_root))
        report = await validator.generate_integrity_report(str(temp_project_root))

        # Check report structure
        assert "project_root" in report
        assert "validation_timestamp" in report
        assert "overall_valid" in report
        assert "summary" in report
        assert "results" in report
        assert "recommendations" in report

        # Check summary structure
        summary = report["summary"]
        assert "total_hooks" in summary
        assert "valid_hooks" in summary
        assert "critical_failures" in summary
        assert "warnings" in summary

        # Check results
        assert len(report["results"]) > 0
        for result in report["results"]:
            assert "hook_name" in result
            assert "valid" in result
            assert "severity" in result

    @pytest.mark.skipif(not INTEGRITY_VALIDATOR_AVAILABLE, reason="HookIntegrityValidator not available")
    def test_extract_python_imports(self):
        """Test Python import extraction."""
        validator = HookIntegrityValidator("/fake/path")

        # Test various import patterns
        content = """
import os
import sys, json
from pathlib import Path
from datetime import datetime, timedelta
import collections.abc
"""

        imports = validator._extract_python_imports(content)
        expected_imports = ["os", "sys", "pathlib", "datetime", "collections.abc"]

        for expected in expected_imports:
            assert expected in imports

    @pytest.mark.skipif(not INTEGRITY_VALIDATOR_AVAILABLE, reason="HookIntegrityValidator not available")
    def test_discover_project_hooks(self):
        """Test hook discovery in project directory."""
        validator = HookIntegrityValidator("/fake/path")

        with tempfile.TemporaryDirectory() as temp_dir:
            hooks_dir = Path(temp_dir)

            # Create various hook files
            (hooks_dir / "hook1.py").write_text("print('hook1')")
            (hooks_dir / "subdir").mkdir()
            (hooks_dir / "subdir" / "hook2.py").write_text("print('hook2')")

            # Create executable file
            exec_file = hooks_dir / "script.sh"
            exec_file.write_text("#!/bin/bash\necho 'test'")
            exec_file.chmod(0o755)

            discovered_hooks = validator._discover_project_hooks(hooks_dir)

            assert "hook1.py" in discovered_hooks
            assert str(Path("subdir") / "hook2.py") in discovered_hooks
            assert "script.sh" in discovered_hooks

    @pytest.mark.skipif(not INTEGRITY_VALIDATOR_AVAILABLE, reason="HookIntegrityValidator not available")
    def test_generate_recommendations(self):
        """Test recommendation generation."""
        validator = HookIntegrityValidator("/fake/path")

        # Test with no failures
        valid_results = [
            ValidationResult(
                valid=True, hook_name="hook1", validation_type="test",
                message="OK", details={}, timestamp=datetime.now(),
                project_root="/test", severity="info"
            )
        ]

        recommendations = validator._generate_recommendations(valid_results)
        assert len(recommendations) == 1
        assert "successfully" in recommendations[0]

        # Test with failures
        failed_results = [
            ValidationResult(
                valid=False, hook_name="hook1", validation_type="syntax",
                message="Syntax error", details={}, timestamp=datetime.now(),
                project_root="/test", severity="critical"
            ),
            ValidationResult(
                valid=False, hook_name="hook2", validation_type="dependencies",
                message="Missing deps", details={}, timestamp=datetime.now(),
                project_root="/test", severity="warning"
            )
        ]

        recommendations = validator._generate_recommendations(failed_results)
        assert len(recommendations) >= 2
        assert any("critical" in rec for rec in recommendations)

    @pytest.mark.asyncio
    async def test_convenience_function(self, temp_devstream_root, temp_project_root):
        """Test the convenience validation function."""
        if not INTEGRITY_VALIDATOR_AVAILABLE:
            pytest.skip("HookIntegrityValidator not available")

        # Create minimal structure
        project_hooks = temp_project_root / ".claude" / "hooks" / "devstream"
        project_hooks.mkdir(parents=True)

        report = await validate_project_hooks(
            project_root=str(temp_project_root),
            devstream_root=str(temp_devstream_root)
        )

        assert "project_root" in report
        assert "overall_valid" in report
        assert "summary" in report


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test ValidationResult creation and attributes."""
        timestamp = datetime.now()
        result = ValidationResult(
            valid=True,
            hook_name="test_hook",
            validation_type="syntax",
            message="Validation passed",
            details={"test": "value"},
            timestamp=timestamp,
            project_root="/test/project",
            severity="info"
        )

        assert result.valid is True
        assert result.hook_name == "test_hook"
        assert result.validation_type == "syntax"
        assert result.message == "Validation passed"
        assert result.details == {"test": "value"}
        assert result.timestamp == timestamp
        assert result.project_root == "/test/project"
        assert result.severity == "info"


class TestHookMetadata:
    """Test HookMetadata dataclass."""

    def test_hook_metadata_creation(self):
        """Test HookMetadata creation and default values."""
        metadata = HookMetadata(
            name="test_hook",
            path="/test/hook.py"
        )

        assert metadata.name == "test_hook"
        assert metadata.path == "/test/hook.py"
        assert metadata.expected_size is None
        assert metadata.expected_checksum is None
        assert metadata.required_dependencies == []
        assert metadata.validation_functions == []

    def test_hook_metadata_with_values(self):
        """Test HookMetadata with explicit values."""
        metadata = HookMetadata(
            name="test_hook",
            path="/test/hook.py",
            expected_size=1024,
            expected_checksum="abc123",
            required_dependencies=["structlog", "asyncio"],
            validation_functions=["test_syntax", "test_functionality"]
        )

        assert metadata.expected_size == 1024
        assert metadata.expected_checksum == "abc123"
        assert metadata.required_dependencies == ["structlog", "asyncio"]
        assert metadata.validation_functions == ["test_syntax", "test_functionality"]


@pytest.mark.asyncio
async def test_integration_with_copier_module():
    """Test integration with multi_project_hook_copier module."""
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent / ".claude" / "hooks" / "devstream" / "utils"))

    try:
        from multi_project_hook_copier import _basic_integrity_check
    except ImportError:
        pytest.skip("multi_project_hook_copier not available")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_root = temp_path / "source"
        target_root = temp_path / "target"

        # Create source hooks
        source_hooks = source_root / ".claude" / "hooks" / "devstream"
        source_hooks.mkdir(parents=True)

        test_hook = source_hooks / "memory" / "pre_tool_use.py"
        test_hook.parent.mkdir(parents=True)
        test_hook.write_text("print('test')")

        # Create target structure
        target_hooks = target_root / ".claude" / "hooks" / "devstream"
        target_hooks.mkdir(parents=True)

        # Copy hook
        target_hook = target_hooks / "memory" / "pre_tool_use.py"
        target_hook.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(test_hook, target_hook)

        # Run basic integrity check
        result = await _basic_integrity_check(source_root, target_root)

        assert "overall_valid" in result
        assert "summary" in result
        assert "results" in result
        assert "validation_method" in result
        assert result["validation_method"] == "basic_fallback"


if __name__ == "__main__":
    # Run tests manually
    print("Running hook integrity validator tests...")

    if INTEGRITY_VALIDATOR_AVAILABLE:
        print("✅ HookIntegrityValidator is available")
    else:
        print("⚠️ HookIntegrityValidator not available - some tests will be skipped")

    print("\nRun with: pytest tests/unit/test_hook_integrity_validator.py -v")