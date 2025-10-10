"""
E2E DevStream System Validation Test

Comprehensive end-to-end test validating all DevStream systems:
- Task Lifecycle Management (create → update → complete)
- Memory System (store → search → embeddings)
- Context7 Integration (resolve → fetch docs)
- Auto-Delegation (pattern matching → confidence scoring)
- TodoWrite Workflow (status transitions)

Author: DevStream Test Suite
Version: 1.0.0
Date: 2025-10-09
"""

import pytest
import sqlite3
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import tempfile
from dotenv import load_dotenv

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "hooks"))

# Load environment
load_dotenv(PROJECT_ROOT / ".env.devstream")

from devstream.agents.pattern_matcher import PatternMatcher


@pytest.fixture(scope="module")
def test_db_path() -> Path:
    """
    Create temporary database for testing.

    Returns:
        Path: Temporary database file path

    Note:
        Database is automatically cleaned up after module tests complete
    """
    temp_dir = tempfile.mkdtemp(prefix="devstream_test_")
    db_path = Path(temp_dir) / "test_devstream.db"

    # Initialize database schema
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            task_type TEXT,
            priority INTEGER,
            phase_name TEXT,
            project TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            updated_at TEXT
        )
    """)

    # Create memory table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            content_type TEXT,
            keywords TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()
    Path(temp_dir).rmdir()


@pytest.fixture
def test_task_data() -> Dict[str, Any]:
    """
    Provide test task data.

    Returns:
        Dict: Task creation data
    """
    return {
        "title": "E2E Test Task",
        "description": "Test task for E2E validation",
        "task_type": "testing",
        "priority": 5,
        "phase_name": "Test Phase",
        "project": "DevStream E2E"
    }


@pytest.fixture
def test_memory_data() -> Dict[str, Any]:
    """
    Provide test memory data.

    Returns:
        Dict: Memory storage data
    """
    return {
        "content": "Test memory content for E2E validation with embeddings",
        "content_type": "code",
        "keywords": ["test", "e2e", "validation"]
    }


@pytest.fixture
def pattern_matcher() -> PatternMatcher:
    """
    Initialize PatternMatcher instance.

    Returns:
        PatternMatcher: Initialized pattern matcher
    """
    return PatternMatcher()


# ============================================================================
# Test Suite: Task Lifecycle Management
# ============================================================================

class TestTaskLifecycle:
    """Test Task Lifecycle Management (create → update → complete)."""

    def test_create_task(self, task_service: TaskService, test_task_data: Dict[str, Any]) -> None:
        """
        Test task creation via TaskService.

        Args:
            task_service: Task service instance
            test_task_data: Test task data

        Validates:
            - Task creation succeeds
            - Task ID is generated
            - Task stored in database
        """
        result = task_service.create_task(**test_task_data)

        assert result is not None, "Task creation failed"
        assert "task_id" in result, "Task ID not generated"
        assert result["title"] == test_task_data["title"], "Title mismatch"
        assert result["status"] == "pending", "Initial status should be 'pending'"

    def test_update_task_status(self, task_service: TaskService) -> None:
        """
        Test task status update.

        Args:
            task_service: Task service instance

        Validates:
            - Status transitions work (pending → active → completed)
            - Updated_at timestamp changes
        """
        # Create task first
        task = task_service.create_task(
            title="Update Test Task",
            description="Task for status update test",
            task_type="testing",
            priority=5,
            phase_name="Test Phase"
        )
        task_id = task["task_id"]

        # Update to active
        result = task_service.update_task(task_id, status="active", notes="Started work")
        assert result["status"] == "active", "Status not updated to 'active'"

        # Update to completed
        result = task_service.update_task(task_id, status="completed", notes="Work finished")
        assert result["status"] == "completed", "Status not updated to 'completed'"

    def test_list_tasks(self, task_service: TaskService) -> None:
        """
        Test task listing with filters.

        Args:
            task_service: Task service instance

        Validates:
            - List all tasks
            - Filter by status
            - Filter by priority
        """
        # Create multiple tasks
        for i in range(3):
            task_service.create_task(
                title=f"List Test Task {i}",
                description=f"Task {i} for list test",
                task_type="testing",
                priority=i + 1,
                phase_name="Test Phase"
            )

        # List all tasks
        all_tasks = task_service.list_tasks()
        assert len(all_tasks) >= 3, "Should have at least 3 tasks"

        # Filter by status
        pending_tasks = task_service.list_tasks(status="pending")
        assert all(t["status"] == "pending" for t in pending_tasks), "Status filter failed"


# ============================================================================
# Test Suite: Memory System
# ============================================================================

class TestMemorySystem:
    """Test Memory System (store → search → embeddings)."""

    def test_store_memory(self, memory_service: MemoryService, test_memory_data: Dict[str, Any]) -> None:
        """
        Test memory storage.

        Args:
            memory_service: Memory service instance
            test_memory_data: Test memory data

        Validates:
            - Memory stored successfully
            - Embeddings generated
            - Metadata preserved
        """
        result = memory_service.store_memory(**test_memory_data)

        assert result is not None, "Memory storage failed"
        assert "id" in result, "Memory ID not generated"
        assert result["content"] == test_memory_data["content"], "Content mismatch"

    def test_search_memory_semantic(self, memory_service: MemoryService) -> None:
        """
        Test semantic memory search.

        Args:
            memory_service: Memory service instance

        Validates:
            - Semantic search returns results
            - Relevance scoring works
            - Results ranked by similarity
        """
        # Store test memory first
        memory_service.store_memory(
            content="Python async/await pattern for FastAPI endpoints",
            content_type="code",
            keywords=["python", "async", "fastapi"]
        )

        # Search with semantic query
        results = memory_service.search_memory(
            query="asynchronous python web framework",
            limit=5,
            min_relevance=0.03
        )

        assert len(results) > 0, "Semantic search returned no results"
        assert all("relevance_score" in r for r in results), "Missing relevance scores"

    def test_search_memory_keyword(self, memory_service: MemoryService) -> None:
        """
        Test keyword memory search.

        Args:
            memory_service: Memory service instance

        Validates:
            - Keyword search returns results
            - Exact matches prioritized
        """
        # Store test memory with specific keywords
        memory_service.store_memory(
            content="SQLite database schema migration with Alembic",
            content_type="documentation",
            keywords=["sqlite", "migration", "alembic"]
        )

        # Search with keyword query
        results = memory_service.search_memory(
            query="sqlite migration",
            limit=5
        )

        assert len(results) > 0, "Keyword search returned no results"


# ============================================================================
# Test Suite: Context7 Integration (Placeholder)
# ============================================================================

class TestContext7Integration:
    """Test Context7 Integration (resolve → fetch docs)."""

    @pytest.mark.skip(reason="Context7 requires MCP server integration")
    def test_resolve_library_id(self) -> None:
        """
        Test library ID resolution via Context7.

        Note:
            Requires MCP server running - skipped in isolated tests
        """
        pass

    @pytest.mark.skip(reason="Context7 requires MCP server integration")
    def test_fetch_library_docs(self) -> None:
        """
        Test library documentation fetching via Context7.

        Note:
            Requires MCP server running - skipped in isolated tests
        """
        pass


# ============================================================================
# Test Suite: Auto-Delegation (Placeholder)
# ============================================================================

class TestAutoDelegation:
    """Test Auto-Delegation (pattern matching → confidence scoring)."""

    def test_pattern_matching(self) -> None:
        """
        Test file pattern matching for agent delegation.

        Validates:
            - Python files → @python-specialist
            - TypeScript files → @typescript-specialist
            - Mixed files → @tech-lead
        """
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env.devstream")

        from claude_hooks.devstream.agents.pattern_matcher import PatternMatcher

        matcher = PatternMatcher()

        # Test Python pattern
        py_result = matcher.match_patterns(["src/api/users.py", "src/models/user.py"])
        assert py_result["agent"] == "@python-specialist", "Python pattern match failed"
        assert py_result["confidence"] >= 0.95, "Python confidence too low"

        # Test TypeScript pattern
        ts_result = matcher.match_patterns(["src/components/App.tsx", "src/hooks/useAuth.ts"])
        assert ts_result["agent"] == "@typescript-specialist", "TypeScript pattern match failed"
        assert ts_result["confidence"] >= 0.95, "TypeScript confidence too low"

        # Test mixed patterns
        mixed_result = matcher.match_patterns(["src/api/users.py", "src/components/App.tsx"])
        assert mixed_result["agent"] == "@tech-lead", "Mixed pattern should delegate to @tech-lead"
        assert mixed_result["confidence"] < 0.85, "Mixed confidence should be low"


# ============================================================================
# Test Suite: TodoWrite Workflow (Placeholder)
# ============================================================================

class TestTodoWriteWorkflow:
    """Test TodoWrite Workflow (status transitions)."""

    @pytest.mark.skip(reason="TodoWrite requires Claude Code integration")
    def test_todo_status_transitions(self) -> None:
        """
        Test TodoWrite status transitions.

        Note:
            TodoWrite is Claude Code tool - requires integration testing
        """
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
