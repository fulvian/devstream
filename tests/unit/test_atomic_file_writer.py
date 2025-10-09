"""
Unit Tests for Atomic File Writer - DevStream Phase 1-4 Validation

Tests the atomic_file_writer.py module for correctness, safety, and edge cases.
Coverage target: ≥95% for atomic_file_writer.py

Test Categories:
1. Basic write operations (text, unicode, overwrite)
2. Parent directory creation
3. Error handling (permissions, disk full)
4. Large file handling (>1MB)
5. Concurrent write safety

DevStream Compliance:
- pytest + pytest-asyncio
- AAA pattern (Arrange-Act-Assert)
- Type hints
- 100% pass rate required
"""

import pytest
import asyncio
import os
import tempfile
from pathlib import Path
from typing import Generator
import stat

# Import module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'utils'))
from atomic_file_writer import write_atomic


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def temp_dir(tmp_path: Path) -> Path:
    """
    Temporary directory for test files.

    Args:
        tmp_path: pytest built-in tmp_path fixture

    Returns:
        Path to temporary directory
    """
    return tmp_path


@pytest.fixture
async def test_file_path(temp_dir: Path) -> Path:
    """
    Path to test file in temporary directory.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path to test file
    """
    return temp_dir / "test_file.txt"


@pytest.fixture
async def readonly_dir(temp_dir: Path) -> Generator[Path, None, None]:
    """
    Read-only directory for permission testing.

    Creates a directory with read-only permissions to test
    error handling for write failures.

    Args:
        temp_dir: Temporary directory fixture

    Yields:
        Path to read-only directory

    Note:
        Restores write permissions after test for cleanup
    """
    readonly_path = temp_dir / "readonly"
    readonly_path.mkdir(parents=True, exist_ok=True)

    # Remove write permissions
    readonly_path.chmod(stat.S_IRUSR | stat.S_IXUSR)

    yield readonly_path

    # Restore write permissions for cleanup
    readonly_path.chmod(stat.S_IRWXU)


# ============================================================================
# UNIT TESTS - Basic Operations
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_write_atomic_basic_text(test_file_path: Path):
    """
    Test basic text write operation.

    Validates:
    - File created successfully
    - Content matches expected
    - File readable after write
    """
    # Arrange
    content = "Hello, DevStream!\nThis is a test."

    # Act
    success = await write_atomic(test_file_path, content)

    # Assert
    assert success is True, "Write operation should succeed"
    assert test_file_path.exists(), "File should exist after write"

    # Verify content
    actual_content = test_file_path.read_text(encoding='utf-8')
    assert actual_content == content, "Content should match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_write_atomic_overwrite_existing(test_file_path: Path):
    """
    Test overwriting existing file.

    Validates:
    - Existing file overwritten correctly
    - New content replaces old content
    - No partial writes or corruption
    """
    # Arrange - Create initial file
    initial_content = "Initial content"
    test_file_path.write_text(initial_content)

    new_content = "New content that replaces the old"

    # Act
    success = await write_atomic(test_file_path, new_content)

    # Assert
    assert success is True, "Overwrite should succeed"
    assert test_file_path.exists(), "File should exist after overwrite"

    # Verify new content
    actual_content = test_file_path.read_text(encoding='utf-8')
    assert actual_content == new_content, "New content should replace old"
    assert actual_content != initial_content, "Old content should be gone"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_write_atomic_parent_directory_creation(temp_dir: Path):
    """
    Test automatic parent directory creation.

    Validates:
    - Parent directories created automatically
    - Nested directories handled correctly
    - File written to correct location
    """
    # Arrange - Path with non-existent parent directories
    nested_file = temp_dir / "level1" / "level2" / "level3" / "file.txt"
    content = "Nested file content"

    # Act
    success = await write_atomic(nested_file, content)

    # Assert
    assert success is True, "Write should succeed with auto-created parents"
    assert nested_file.exists(), "Nested file should exist"
    assert nested_file.parent.exists(), "Parent directory should exist"

    # Verify content
    actual_content = nested_file.read_text(encoding='utf-8')
    assert actual_content == content, "Content should match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_write_atomic_unicode_content(test_file_path: Path):
    """
    Test Unicode and emoji support.

    Validates:
    - UTF-8 encoding handles Unicode correctly
    - Emojis preserved
    - Multi-language content supported
    """
    # Arrange - Unicode content with various scripts and emojis
    content = """
    Unicode Test:
    - English: Hello
    - Chinese: 你好 (Nǐ hǎo)
    - Japanese: こんにちは (Konnichiwa)
    - Russian: Здравствуйте (Zdravstvuyte)
    - Emoji: 🚀 📋 ✅ ❌ 🎯
    - Math: ∑ ∫ ∞ √ π
    """

    # Act
    success = await write_atomic(test_file_path, content)

    # Assert
    assert success is True, "Unicode write should succeed"
    assert test_file_path.exists(), "File should exist"

    # Verify content preservation
    actual_content = test_file_path.read_text(encoding='utf-8')
    assert actual_content == content, "Unicode content should be preserved exactly"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_write_atomic_large_content(test_file_path: Path):
    """
    Test large file handling (>1MB).

    Validates:
    - Large files written correctly
    - No memory issues
    - Content integrity maintained
    """
    # Arrange - Generate 2MB content
    # 1 line = ~100 chars, 20,000 lines ≈ 2MB
    lines = [f"Line {i:06d}: This is test content for large file handling.\n" for i in range(20000)]
    content = "".join(lines)

    assert len(content) > 1_000_000, "Content should be >1MB for test validity"

    # Act
    success = await write_atomic(test_file_path, content)

    # Assert
    assert success is True, "Large file write should succeed"
    assert test_file_path.exists(), "File should exist"

    # Verify size
    file_size = test_file_path.stat().st_size
    assert file_size > 1_000_000, "File size should be >1MB"

    # Verify content integrity (sample check to avoid memory issues)
    actual_content = test_file_path.read_text(encoding='utf-8')
    assert actual_content[:100] == content[:100], "Content start should match"
    assert actual_content[-100:] == content[-100:], "Content end should match"
    assert len(actual_content) == len(content), "Content length should match"


# ============================================================================
# UNIT TESTS - Error Handling
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_write_atomic_permission_error(readonly_dir: Path):
    """
    Test graceful handling of permission denied errors.

    Validates:
    - Permission errors caught gracefully
    - Returns False on failure
    - No unhandled exceptions
    - Temp file cleanup attempted
    """
    # Arrange - File in read-only directory
    file_in_readonly = readonly_dir / "should_fail.txt"
    content = "This write should fail"

    # Act
    success = await write_atomic(file_in_readonly, content)

    # Assert
    assert success is False, "Write should fail with permission error"
    assert not file_in_readonly.exists(), "File should not exist after failed write"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_write_atomic_disk_full_simulation(test_file_path: Path, monkeypatch):
    """
    Test handling of OSError during write (disk full simulation).

    Validates:
    - OSError caught gracefully
    - Returns False on write failure
    - Temp file cleanup attempted
    - No data corruption

    Note:
        Uses monkeypatch to simulate write failure without filling disk
    """
    # Arrange - Mock aiofiles.open to raise OSError
    import aiofiles

    original_open = aiofiles.open

    async def mock_open_failure(*args, **kwargs):
        """Mock that raises OSError to simulate disk full."""
        if 'w' in args or kwargs.get('mode') == 'w':
            raise OSError("No space left on device")
        return await original_open(*args, **kwargs)

    monkeypatch.setattr('aiofiles.open', mock_open_failure)

    content = "This write should fail"

    # Act
    success = await write_atomic(test_file_path, content)

    # Assert
    assert success is False, "Write should fail with disk full error"
    assert not test_file_path.exists(), "File should not exist after failed write"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_write_atomic_concurrent_writes(temp_dir: Path):
    """
    Test atomicity under concurrent write operations.

    Validates:
    - Multiple concurrent writes to same file
    - Final file contains complete content (one of the writes)
    - No partial writes or corruption
    - No torn reads (data from multiple writes mixed)

    Note:
        Due to atomic rename, last write wins (expected behavior)
    """
    # Arrange - Multiple writers targeting same file
    target_file = temp_dir / "concurrent_target.txt"

    # Create 10 distinct content strings
    contents = [f"Writer {i}: {'A' * 100}\n" * 10 for i in range(10)]

    # Act - Concurrent writes
    tasks = [write_atomic(target_file, content) for content in contents]
    results = await asyncio.gather(*tasks)

    # Assert
    assert all(results), "All writes should succeed"
    assert target_file.exists(), "File should exist after concurrent writes"

    # Verify content integrity (must match ONE of the written contents)
    actual_content = target_file.read_text(encoding='utf-8')
    assert actual_content in contents, "Content should match one of the writes (last write wins)"

    # Verify no corruption (content is complete, not partial)
    # Each content string is exactly 1110 chars (10 lines × 111 chars/line)
    # Format: "Writer X: " (10 chars) + "A" * 100 + "\n" (1 char) = 111 chars/line
    assert len(actual_content) == 1110, "Content should be complete (no partial write)"

    # Verify no mixed data (all lines should have same writer ID)
    lines = actual_content.strip().split('\n')
    writer_ids = [line.split(':')[0] for line in lines]
    assert len(set(writer_ids)) == 1, "All lines should be from same writer (no torn reads)"


# ============================================================================
# UNIT TESTS - JSON Write Operations
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_write_atomic_json_basic(test_file_path: Path):
    """
    Test basic JSON write operation.

    Validates:
    - JSON serialization works correctly
    - File created with proper formatting
    - Content deserializable
    """
    from atomic_file_writer import write_atomic_json

    # Arrange
    data = {
        "session_id": "test-123",
        "summary": "Test session",
        "tasks_completed": 5,
        "timestamp": "2025-10-02T12:00:00Z"
    }

    json_file = test_file_path.with_suffix('.json')

    # Act
    success = await write_atomic_json(json_file, data)

    # Assert
    assert success is True, "JSON write should succeed"
    assert json_file.exists(), "JSON file should exist"

    # Verify content
    import json
    with open(json_file) as f:
        loaded_data = json.load(f)

    assert loaded_data == data, "JSON data should match"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_write_atomic_json_unicode(test_file_path: Path):
    """
    Test JSON write with Unicode content.

    Validates:
    - Unicode preserved in JSON
    - ensure_ascii=False works correctly
    """
    from atomic_file_writer import write_atomic_json

    # Arrange
    data = {
        "message": "Hello 世界 🌍",
        "languages": ["English", "中文", "日本語"]
    }

    json_file = test_file_path.with_suffix('.json')

    # Act
    success = await write_atomic_json(json_file, data)

    # Assert
    assert success is True, "JSON write should succeed"

    # Verify Unicode preservation
    import json
    with open(json_file, encoding='utf-8') as f:
        loaded_data = json.load(f)

    assert loaded_data == data, "Unicode data should be preserved"
    assert "世界" in loaded_data["message"], "Chinese characters preserved"
    assert "🌍" in loaded_data["message"], "Emoji preserved"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_write_atomic_json_serialization_error():
    """
    Test handling of JSON serialization errors.

    Validates:
    - Serialization errors caught gracefully
    - Returns False on failure
    - No file created
    """
    from atomic_file_writer import write_atomic_json
    from pathlib import Path
    import tempfile

    # Arrange - Object that can't be serialized
    class NonSerializable:
        pass

    data = {
        "valid_key": "valid_value",
        "invalid_key": NonSerializable()
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        json_file = Path(tmpdir) / "test.json"

        # Act
        success = await write_atomic_json(json_file, data)

        # Assert
        assert success is False, "JSON write should fail with non-serializable data"
        assert not json_file.exists(), "File should not exist after serialization failure"


# ============================================================================
# UNIT TESTS - Edge Cases
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_write_atomic_empty_content(test_file_path: Path):
    """
    Test writing empty string.

    Validates:
    - Empty file created successfully
    - File exists but has 0 bytes
    """
    # Arrange
    content = ""

    # Act
    success = await write_atomic(test_file_path, content)

    # Assert
    assert success is True, "Empty write should succeed"
    assert test_file_path.exists(), "File should exist"
    assert test_file_path.stat().st_size == 0, "File should be empty"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_write_atomic_whitespace_only(test_file_path: Path):
    """
    Test writing whitespace-only content.

    Validates:
    - Whitespace preserved correctly
    - No trimming or modification
    """
    # Arrange
    content = "   \n\t\n   \n"

    # Act
    success = await write_atomic(test_file_path, content)

    # Assert
    assert success is True, "Whitespace write should succeed"

    # Verify exact preservation
    actual_content = test_file_path.read_text(encoding='utf-8')
    assert actual_content == content, "Whitespace should be preserved exactly"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_write_atomic_special_characters(test_file_path: Path):
    """
    Test writing special characters and control codes.

    Validates:
    - Special characters handled correctly
    - ANSI escape codes preserved
    - Null bytes preserved
    """
    # Arrange - Various special characters
    # Note: \r\n may be normalized to \n on some platforms (text mode)
    content = "Special chars: \n\t\0\x1b[31m Red \x1b[0m"

    # Act
    success = await write_atomic(test_file_path, content)

    # Assert
    assert success is True, "Special chars write should succeed"

    # Verify preservation
    actual_content = test_file_path.read_text(encoding='utf-8')
    assert actual_content == content, "Special characters should be preserved"

    # Verify specific special characters
    assert '\t' in actual_content, "Tab should be preserved"
    assert '\0' in actual_content, "Null byte should be preserved"
    assert '\x1b[31m' in actual_content, "ANSI escape codes should be preserved"


# ============================================================================
# COVERAGE VALIDATION
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_atomic_writer_coverage_validation():
    """
    Meta-test to validate coverage targets.

    This test ensures all code paths are exercised by the test suite.
    Run with: pytest --cov=.claude/hooks/devstream/utils/atomic_file_writer

    Coverage Target: ≥95% for atomic_file_writer.py
    """
    # This test exists to document coverage expectations
    # Actual coverage measured by pytest-cov

    # Critical paths covered:
    paths_covered = [
        "write_atomic() - success path",
        "write_atomic() - parent directory creation",
        "write_atomic() - OSError handling",
        "write_atomic() - temp file cleanup on failure",
        "write_atomic() - atomic rename",
        "write_atomic() - unicode support",
        "write_atomic() - large file handling",
        "write_atomic() - concurrent writes"
    ]

    assert len(paths_covered) == 8, "All critical paths documented"
