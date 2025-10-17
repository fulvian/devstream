"""
Tests for enhanced multi-project hook copying module.

Tests Copier integration, error handling, and validation functionality.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List
from unittest.mock import Mock, patch, AsyncMock

# Import the module under test
import sys
sys.path.append(str(Path(__file__).parent.parent.parent / ".claude" / "hooks" / "devstream" / "utils"))

from multi_project_hook_copier import (
    copy_devstream_hooks_enhanced,
    _validate_hook_copying,
    calculate_file_checksums,
    verify_hook_integrity,
    HookCopyError,
    DependencyError,
    HookValidationError
)


class TestMultiProjectHookCopier:
    """Test suite for multi-project hook copying functionality."""

    @pytest.fixture
    def temp_source_root(self):
        """Create a temporary source DevStream root directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)

            # Create .claude directory structure
            claude_dir = source_root / ".claude"
            claude_dir.mkdir()

            hooks_dir = claude_dir / "hooks" / "devstream"
            hooks_dir.mkdir(parents=True)

            # Create required directories with test files
            required_dirs = ["protocol", "agents", "context", "memory", "sessions", "utils"]
            for dir_name in required_dirs:
                dir_path = hooks_dir / dir_name
                dir_path.mkdir()

                # Add a test file to each directory
                test_file = dir_path / f"{dir_name}_test.py"
                test_file.write_text(f"# Test file for {dir_name} directory\\n")

            yield source_root

    @pytest.fixture
    def temp_target_root(self):
        """Create a temporary target directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_calculate_file_checksums(self, temp_source_root):
        """Test checksum calculation for files."""
        checksums = calculate_file_checksums(temp_source_root)

        # Should have checksums for all files
        assert len(checksums) > 0

        # Check that checksums are valid SHA256 hashes (64 hex characters)
        for file_path, checksum in checksums.items():
            assert len(checksum) == 64
            assert all(c in "0123456789abcdef" for c in checksum.lower())
            assert file_path.startswith(".claude/")

    @pytest.mark.asyncio
    async def test_validate_hook_copying_success(self, temp_target_root):
        """Test successful hook copying validation."""
        # Create expected directory structure
        target_claude = temp_target_root / ".claude"
        target_hooks = target_claude / "hooks" / "devstream"
        target_hooks.mkdir(parents=True)

        # Create required directories
        required_dirs = ["protocol", "agents", "utils"]
        for dir_name in required_dirs:
            (target_hooks / dir_name).mkdir()
            (target_hooks / dir_name / "test.py").write_text("# test")

        # Test validation
        result = await _validate_hook_copying(
            target_root=temp_target_root,
            required_directories=required_dirs
        )

        assert result["valid"] is True
        assert len(result["missing_directories"]) == 0
        assert len(result["copied_files"]) > 0

    @pytest.mark.asyncio
    async def test_validate_hook_copying_missing_directories(self, temp_target_root):
        """Test validation failure with missing directories."""
        # Create incomplete directory structure
        target_claude = temp_target_root / ".claude"
        target_hooks = target_claude / "hooks" / "devstream"
        target_hooks.mkdir(parents=True)

        # Only create one directory, but expect three
        (target_hooks / "protocol").mkdir()
        required_dirs = ["protocol", "agents", "utils"]

        # Test validation should fail
        with pytest.raises(HookValidationError) as exc_info:
            await _validate_hook_copying(
                target_root=temp_target_root,
                required_directories=required_dirs
            )

        assert "missing directories" in str(exc_info.value)
        assert "agents" in str(exc_info.value)
        assert "utils" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_hook_integrity_success(self, temp_target_root):
        """Test successful integrity verification."""
        # Create test files
        target_hooks = temp_target_root / ".claude" / "hooks" / "devstream"
        target_hooks.mkdir(parents=True)

        test_file = target_hooks / "test.py"
        test_content = "# Test content\\nprint('hello')"
        test_file.write_text(test_content)

        # Calculate expected checksums
        expected_checksums = calculate_file_checksums(target_hooks)

        # Verify integrity
        result = await verify_hook_integrity(
            target_root=temp_target_root,
            expected_checksums=expected_checksums
        )

        assert result["verified"] is True
        assert len(result["missing_files"]) == 0
        assert len(result["corrupted_files"]) == 0
        assert result["total_files"] >= 1

    @pytest.mark.asyncio
    async def test_verify_hook_integrity_corrupted_files(self, temp_target_root):
        """Test integrity verification with corrupted files."""
        # Create test files
        target_hooks = temp_target_root / ".claude" / "hooks" / "devstream"
        target_hooks.mkdir(parents=True)

        test_file = target_hooks / "test.py"
        test_file.write_text("# Original content")

        # Calculate expected checksums
        expected_checksums = calculate_file_checksums(target_hooks)

        # Corrupt the file
        test_file.write_text("# Corrupted content")

        # Verify integrity should fail
        result = await verify_hook_integrity(
            target_root=temp_target_root,
            expected_checksums=expected_checksums
        )

        assert result["verified"] is False
        assert len(result["corrupted_files"]) == 1
        assert result["corrupted_files"][0]["file"] == "test.py"

    @pytest.mark.asyncio
    async def test_copy_devstream_hooks_enhanced_success(self, temp_source_root, temp_target_root):
        """Test successful hook copying with Copier integration."""
        # Mock Copier's run_copy function to simulate successful copying
        with patch('multi_project_hook_copier.run_copy') as mock_run_copy:
            # Create a mock worker object
            mock_worker = Mock()
            mock_run_copy.return_value = mock_worker

            # Also mock the validation function to simulate success
            with patch('multi_project_hook_copier._validate_hook_copying') as mock_validate:
                mock_validate.return_value = {
                    "valid": True,
                    "missing_directories": [],
                    "copied_files": [".claude/hooks/devstream/protocol/test.py"]
                }

                # Test the copying function
                result = await copy_devstream_hooks_enhanced(
                    source_root=temp_source_root,
                    target_root=temp_target_root,
                    required_directories=["protocol", "agents", "utils"]
                )

                # Verify result structure
                assert result["status"] == "success"
                assert "copied_directories" in result
                assert "source_root" in result
                assert "target_root" in result
                assert "validation" in result
                assert result["copied_directories"] == ["protocol", "agents", "utils"]

                # Verify Copier was called with correct parameters
                mock_run_copy.assert_called_once()
                call_args = mock_run_copy.call_args

                assert call_args[1]["src_path"] == str(temp_source_root / ".claude")
                assert call_args[1]["dst_path"] == str(temp_target_root / ".claude")
                assert call_args[1]["defaults"] is True
                assert call_args[1]["overwrite"] is True
                assert call_args[1]["vcs_ref"] == "HEAD"

                # Verify validation was called
                mock_validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_copy_devstream_hooks_invalid_source(self, temp_target_root):
        """Test hook copying with invalid source directory."""
        non_existent_source = Path("/non/existent/path")

        with pytest.raises(HookCopyError) as exc_info:
            await copy_devstream_hooks_enhanced(
                source_root=non_existent_source,
                target_root=temp_target_root
            )

        assert "Source root does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_copy_devstream_hooks_missing_claude_dir(self, temp_source_root, temp_target_root):
        """Test hook copying when source lacks .claude directory."""
        # Remove .claude directory from source
        shutil.rmtree(temp_source_root / ".claude")

        with pytest.raises(HookCopyError) as exc_info:
            await copy_devstream_hooks_enhanced(
                source_root=temp_source_root,
                target_root=temp_target_root
            )

        assert "Source does not contain .claude directory" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_copy_devstream_hooks_copier_error(self, temp_source_root, temp_target_root):
        """Test handling of Copier errors during hook copying."""
        # Mock Copier to raise an error
        with patch('multi_project_hook_copier.run_copy') as mock_run_copy:
            from copier.errors import CopierError
            mock_run_copy.side_effect = CopierError("Template rendering failed")

            with pytest.raises(HookCopyError) as exc_info:
                await copy_devstream_hooks_enhanced(
                    source_root=temp_source_root,
                    target_root=temp_target_root
                )

            assert "Failed to copy hooks with Copier" in str(exc_info.value)
            assert "Template rendering failed" in str(exc_info.value)

    def test_module_imports(self):
        """Test that all required imports are available."""
        # This should not raise any ImportError if the module is correctly set up
        from multi_project_hook_copier import (
            copy_devstream_hooks_enhanced,
            HookCopyError,
            DependencyError,
            HookValidationError
        )

        # Verify Copier is importable
        import copier
        assert hasattr(copier, 'run_copy')

        # Verify error classes are importable
        from copier.errors import CopierError
        assert issubclass(CopierError, Exception)

    def test_function_signatures(self):
        """Test that function signatures match the specification."""
        import inspect

        # Test main function signature
        sig = inspect.signature(copy_devstream_hooks_enhanced)
        expected_params = ['source_root', 'target_root', 'required_directories']
        actual_params = list(sig.parameters.keys())

        for param in expected_params:
            assert param in actual_params

        # Test parameter types
        assert sig.parameters['source_root'].annotation == Path
        assert sig.parameters['target_root'].annotation == Path
        assert sig.parameters['required_directories'].annotation == Optional[List[str]]

    @pytest.mark.asyncio
    async def test_default_required_directories(self, temp_source_root, temp_target_root):
        """Test that default required directories are used when not specified."""
        with patch('multi_project_hook_copier.run_copy') as mock_run_copy:
            mock_worker = Mock()
            mock_run_copy.return_value = mock_worker

            # Also mock the validation function to simulate success
            with patch('multi_project_hook_copier._validate_hook_copying') as mock_validate:
                mock_validate.return_value = {
                    "valid": True,
                    "missing_directories": [],
                    "copied_files": [".claude/hooks/devstream/protocol/test.py"]
                }

                # Call without specifying required_directories
                result = await copy_devstream_hooks_enhanced(
                    source_root=temp_source_root,
                    target_root=temp_target_root
                )

                # Verify function was called
                mock_run_copy.assert_called_once()
                mock_validate.assert_called_once()

                # Verify result structure
                assert result["status"] == "success"
                assert "copied_directories" in result

                # The function should use default directories (we can check the length)
                # Default should include protocol, agents, context, memory, sessions, utils, etc.
                assert len(result["copied_directories"]) >= 6  # At least the core directories

    def test_error_classes_inheritance(self):
        """Test that custom error classes inherit correctly."""
        assert issubclass(HookCopyError, Exception)
        assert issubclass(DependencyError, Exception)
        assert issubclass(HookValidationError, Exception)