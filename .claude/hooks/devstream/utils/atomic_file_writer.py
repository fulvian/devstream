#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "aiofiles>=23.0.0",
#     "structlog>=23.0.0",
# ]
# ///

"""
Atomic File Writer Utility - Context7 Async Pattern Compliant

Provides atomic file writing using temp file + rename pattern to prevent
partial writes in cross-session scenarios (SessionEnd, PreCompact hooks).

Best Practices Applied:
- aiofiles for async I/O (Context7 recommended)
- Write-rename pattern for atomicity (POSIX guarantee)
- tempfile.NamedTemporaryFile in same directory (same filesystem)
- os.replace() for cross-platform atomic rename (Python 3.3+)

Usage Example (SessionEnd Hook):
    from pathlib import Path
    from utils.atomic_file_writer import write_atomic_json

    async def save_session_summary(summary_data: dict) -> bool:
        summary_file = Path(".claude/state/session_summary.json")
        success = await write_atomic_json(summary_file, summary_data)
        if success:
            logger.info("session_summary_saved", file=str(summary_file))
        return success

Usage Example (PreCompact Hook):
    from pathlib import Path
    from utils.atomic_file_writer import write_atomic

    async def save_compact_summary(summary_text: str) -> bool:
        summary_file = Path(".claude/state/compact_summary.md")
        success = await write_atomic(summary_file, summary_text)
        return success
"""

import os
import tempfile
from pathlib import Path
from typing import Optional

import aiofiles
import aiofiles.os
import structlog

logger = structlog.get_logger(__name__)


async def write_atomic(
    file_path: Path,
    content: str,
    encoding: str = "utf-8"
) -> bool:
    """
    Write content to file atomically using temp file + rename pattern.

    This function ensures that file writes are atomic to prevent partial
    writes that can corrupt session summaries or other critical data.
    Uses the write-rename pattern:
    1. Create temp file in same directory as target
    2. Write content to temp file
    3. Flush and close temp file
    4. Atomic rename temp → target

    Args:
        file_path: Target file path to write to
        content: Content string to write
        encoding: File encoding (default: utf-8)

    Returns:
        True if write succeeded, False if failed

    Raises:
        OSError: If file operation fails (disk full, permissions, etc.)

    Note:
        Uses aiofiles for async I/O and os.replace() for atomic rename.
        Temp file created in same directory as target to ensure same filesystem
        (required for atomic rename on POSIX systems).

    Example:
        >>> success = await write_atomic(
        ...     Path("/path/to/file.json"),
        ...     json.dumps(data, indent=2)
        ... )
        >>> if success:
        ...     print("File written atomically")
    """
    tmp_fd = None
    tmp_path = None

    try:
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create temp file in same directory as target (same filesystem requirement)
        # delete=False because we need to rename it after closing
        tmp_fd = tempfile.NamedTemporaryFile(
            mode='w',
            encoding=encoding,
            dir=file_path.parent,
            delete=False,
            suffix='.tmp',
            prefix=f'.{file_path.name}.'
        )
        tmp_path = Path(tmp_fd.name)

        # Write content using aiofiles for async I/O
        async with aiofiles.open(tmp_path, 'w', encoding=encoding) as tmp_file:
            await tmp_file.write(content)
            await tmp_file.flush()
            # Ensure data is written to disk (fsync for durability)
            # Note: aiofiles doesn't provide async fsync, use sync version
            os.fsync(tmp_file.fileno())

        # Close the original file descriptor (already closed by aiofiles context manager)
        # tmp_fd is just the initial NamedTemporaryFile descriptor
        tmp_fd.close()

        # Atomic rename: temp → target
        # os.replace() is atomic on both POSIX and Windows (Python 3.3+)
        await aiofiles.os.replace(tmp_path, file_path)

        logger.debug(
            "atomic_write_success",
            file_path=str(file_path),
            content_size=len(content),
            encoding=encoding
        )

        return True

    except OSError as e:
        logger.error(
            "atomic_write_failed",
            file_path=str(file_path),
            error=str(e),
            error_type=type(e).__name__
        )

        # Cleanup temp file on failure
        if tmp_path and tmp_path.exists():
            try:
                await aiofiles.os.remove(tmp_path)
                logger.debug("temp_file_cleaned_up", tmp_path=str(tmp_path))
            except OSError as cleanup_error:
                logger.warning(
                    "temp_file_cleanup_failed",
                    tmp_path=str(tmp_path),
                    error=str(cleanup_error)
                )

        return False

    except Exception as e:
        # Unexpected errors (should rarely happen)
        logger.error(
            "atomic_write_unexpected_error",
            file_path=str(file_path),
            error=str(e),
            error_type=type(e).__name__
        )

        # Cleanup temp file on failure
        if tmp_path and tmp_path.exists():
            try:
                await aiofiles.os.remove(tmp_path)
            except OSError:
                pass  # Best effort cleanup

        return False

    finally:
        # Ensure temp file descriptor is closed if still open
        if tmp_fd and not tmp_fd.closed:
            tmp_fd.close()


async def write_atomic_json(
    file_path: Path,
    data: dict,
    encoding: str = "utf-8",
    indent: int = 2
) -> bool:
    """
    Write JSON data to file atomically.

    Convenience wrapper around write_atomic() for JSON data.
    Automatically serializes dict to JSON string with formatting.

    Args:
        file_path: Target file path to write to
        data: Dictionary to serialize as JSON
        encoding: File encoding (default: utf-8)
        indent: JSON indentation spaces (default: 2)

    Returns:
        True if write succeeded, False if failed

    Raises:
        OSError: If file operation fails
        ValueError: If data cannot be serialized to JSON

    Note:
        Uses json.dumps() with indent for human-readable formatting.

    Example:
        >>> data = {"summary": "Session completed", "tasks": 5}
        >>> success = await write_atomic_json(
        ...     Path("/path/to/summary.json"),
        ...     data
        ... )
    """
    import json

    try:
        # Serialize to JSON string
        content = json.dumps(data, indent=indent, ensure_ascii=False)

        # Write atomically
        return await write_atomic(file_path, content, encoding=encoding)

    except (TypeError, ValueError) as e:
        logger.error(
            "json_serialization_failed",
            file_path=str(file_path),
            error=str(e),
            error_type=type(e).__name__
        )
        return False


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    import json

    async def test_atomic_writer():
        """Test atomic file writer functionality."""

        # Test 1: Basic text write
        test_file = Path("/tmp/test_atomic_write.txt")
        content = "Test content with\nmultiple lines\nand Unicode: 中文测试"

        success = await write_atomic(test_file, content)
        assert success, "Basic write failed"
        assert test_file.read_text() == content, "Content mismatch"
        print("✅ Test 1: Basic text write - PASSED")

        # Test 2: JSON write
        test_json = Path("/tmp/test_atomic_write.json")
        data = {
            "session_id": "test-123",
            "summary": "Test session summary",
            "tasks_completed": 5,
            "timestamp": "2025-10-02T12:00:00Z"
        }

        success = await write_atomic_json(test_json, data)
        assert success, "JSON write failed"
        loaded_data = json.loads(test_json.read_text())
        assert loaded_data == data, "JSON data mismatch"
        print("✅ Test 2: JSON write - PASSED")

        # Test 3: Overwrite existing file
        success = await write_atomic(test_file, "New content")
        assert success, "Overwrite failed"
        assert test_file.read_text() == "New content", "Overwrite content mismatch"
        print("✅ Test 3: Overwrite existing file - PASSED")

        # Test 4: Parent directory creation
        nested_file = Path("/tmp/atomic_test_nested/subdir/file.txt")
        success = await write_atomic(nested_file, "Nested content")
        assert success, "Nested directory write failed"
        assert nested_file.exists(), "Nested file not created"
        print("✅ Test 4: Parent directory creation - PASSED")

        # Cleanup
        test_file.unlink()
        test_json.unlink()
        nested_file.unlink()
        nested_file.parent.rmdir()
        nested_file.parent.parent.rmdir()

        print("\n🎉 All atomic file writer tests PASSED")

    # Run tests
    asyncio.run(test_atomic_writer())
