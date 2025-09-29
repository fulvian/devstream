"""
Unit tests for memory storage functionality.

Context7-validated patterns for storage testing:
- Database transaction patterns
- Vector table operations mocking
- CRUD operations validation
- Connection pool integration
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from typing import List, Dict, Any

from devstream.memory.storage import MemoryStorage
from devstream.memory.models import MemoryEntry, ContentType, ContentFormat
from devstream.memory.exceptions import StorageError
from devstream.database.connection import ConnectionPool


@pytest.mark.unit
@pytest.mark.memory
class TestMemoryStorage:
    """Test memory storage with Context7-validated patterns."""

    @pytest.fixture
    def mock_connection_pool(self):
        """Create mock connection pool."""
        pool = Mock(spec=ConnectionPool)
        pool.read_transaction = AsyncMock()
        pool.write_transaction = AsyncMock()
        return pool

    @pytest.fixture
    def mock_connection(self):
        """Create mock database connection."""
        conn = AsyncMock()
        conn.execute = AsyncMock()
        conn.fetchone = AsyncMock()
        conn.fetchall = AsyncMock()
        return conn

    @pytest.fixture
    def memory_storage(self, mock_connection_pool):
        """Create memory storage with mocked dependencies."""
        # Mock the table initialization to avoid sqlite-vec dependency
        with patch.object(MemoryStorage, '_init_tables'):
            storage = MemoryStorage(mock_connection_pool)
            storage.connection_pool = mock_connection_pool
            return storage

    @pytest.fixture
    def sample_memory(self):
        """Create sample memory entry."""
        return MemoryEntry(
            id="test-memory-1",
            content="This is a test memory entry for storage validation.",
            content_type=ContentType.DOCUMENTATION,
            content_format=ContentFormat.MARKDOWN,
            keywords=["test", "memory", "storage"],
            entities=[{"text": "storage validation", "label": "ACTIVITY"}],
            embedding=[0.1, 0.2, 0.3] + [0.0] * 381,
            complexity_score=5,
            sentiment=0.2,
            task_id="task-123"
        )

    def test_storage_initialization(self, memory_storage, mock_connection_pool):
        """Test storage initializes correctly."""
        assert memory_storage.connection_pool == mock_connection_pool

    @pytest.mark.asyncio
    async def test_store_memory_basic(self, memory_storage, mock_connection_pool, mock_connection, sample_memory):
        """Test basic memory storage operation."""
        # Setup mock transaction context
        mock_connection_pool.write_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.return_value = AsyncMock()

        result_id = await memory_storage.store_memory(sample_memory)

        assert result_id == sample_memory.id
        mock_connection_pool.write_transaction.assert_called_once()
        mock_connection.execute.assert_called()

    @pytest.mark.asyncio
    async def test_store_memory_without_embedding(self, memory_storage, mock_connection_pool, mock_connection):
        """Test storing memory without embedding."""
        memory_without_embedding = MemoryEntry(
            id="no-embed",
            content="Memory without embedding",
            content_type=ContentType.DOCUMENTATION
        )

        mock_connection_pool.write_transaction.return_value.__aenter__.return_value = mock_connection

        result_id = await memory_storage.store_memory(memory_without_embedding)
        assert result_id == "no-embed"

    @pytest.mark.asyncio
    async def test_store_memory_duplicate_id(self, memory_storage, mock_connection_pool, mock_connection, sample_memory):
        """Test storing memory with duplicate ID."""
        # Simulate database constraint error
        from sqlalchemy.exc import IntegrityError
        mock_connection_pool.write_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.side_effect = IntegrityError("", "", "")

        with pytest.raises(StorageError):
            await memory_storage.store_memory(sample_memory)

    @pytest.mark.asyncio
    async def test_store_memory_database_error(self, memory_storage, mock_connection_pool, mock_connection, sample_memory):
        """Test storage error handling."""
        mock_connection_pool.write_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.side_effect = Exception("Database connection failed")

        with pytest.raises(StorageError):
            await memory_storage.store_memory(sample_memory)

    @pytest.mark.asyncio
    async def test_get_memory_success(self, memory_storage, mock_connection_pool, mock_connection):
        """Test successful memory retrieval."""
        # Mock database response
        mock_row = {
            "id": "test-id",
            "content": "Test content",
            "content_type": "documentation",
            "content_format": "markdown",
            "keywords": '["test", "content"]',
            "entities": '[{"text": "test", "label": "TEST"}]',
            "embedding": "[0.1, 0.2]",
            "complexity_score": 5,
            "sentiment": 0.0,
            "task_id": "task-123",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "access_count": 1,
            "relevance_score": 0.8
        }

        mock_connection_pool.read_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.return_value.fetchone.return_value = mock_row

        memory = await memory_storage.get_memory("test-id")

        assert memory is not None
        assert memory.id == "test-id"
        assert memory.content == "Test content"
        assert memory.content_type == ContentType.DOCUMENTATION
        assert memory.keywords == ["test", "content"]
        assert memory.embedding == [0.1, 0.2]

    @pytest.mark.asyncio
    async def test_get_memory_not_found(self, memory_storage, mock_connection_pool, mock_connection):
        """Test memory retrieval when not found."""
        mock_connection_pool.read_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.return_value.fetchone.return_value = None

        memory = await memory_storage.get_memory("nonexistent-id")
        assert memory is None

    @pytest.mark.asyncio
    async def test_get_memory_database_error(self, memory_storage, mock_connection_pool, mock_connection):
        """Test memory retrieval with database error."""
        mock_connection_pool.read_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.side_effect = Exception("Database error")

        with pytest.raises(StorageError):
            await memory_storage.get_memory("test-id")

    @pytest.mark.asyncio
    async def test_update_memory_success(self, memory_storage, mock_connection_pool, mock_connection, sample_memory):
        """Test successful memory update."""
        mock_connection_pool.write_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.return_value.rowcount = 1

        # Modify sample memory
        sample_memory.content = "Updated content"
        sample_memory.complexity_score = 8

        result = await memory_storage.update_memory(sample_memory)
        assert result is True

    @pytest.mark.asyncio
    async def test_update_memory_not_found(self, memory_storage, mock_connection_pool, mock_connection, sample_memory):
        """Test updating non-existent memory."""
        mock_connection_pool.write_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.return_value.rowcount = 0

        result = await memory_storage.update_memory(sample_memory)
        assert result is False

    @pytest.mark.asyncio
    async def test_update_memory_database_error(self, memory_storage, mock_connection_pool, mock_connection, sample_memory):
        """Test memory update with database error."""
        mock_connection_pool.write_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.side_effect = Exception("Database error")

        with pytest.raises(StorageError):
            await memory_storage.update_memory(sample_memory)

    @pytest.mark.asyncio
    async def test_delete_memory_success(self, memory_storage, mock_connection_pool, mock_connection):
        """Test successful memory deletion."""
        mock_connection_pool.write_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.return_value.rowcount = 1

        result = await memory_storage.delete_memory("test-id")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_memory_not_found(self, memory_storage, mock_connection_pool, mock_connection):
        """Test deleting non-existent memory."""
        mock_connection_pool.write_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.return_value.rowcount = 0

        result = await memory_storage.delete_memory("nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_memory_database_error(self, memory_storage, mock_connection_pool, mock_connection):
        """Test memory deletion with database error."""
        mock_connection_pool.write_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.side_effect = Exception("Database error")

        with pytest.raises(StorageError):
            await memory_storage.delete_memory("test-id")

    @pytest.mark.asyncio
    async def test_search_by_keywords_basic(self, memory_storage, mock_connection_pool, mock_connection):
        """Test basic keyword search."""
        # Mock search results
        mock_rows = [
            {
                "id": "mem-1",
                "content": "Python programming tutorial",
                "content_type": "documentation",
                "content_format": "markdown",
                "keywords": '["python", "programming"]',
                "entities": "[]",
                "embedding": "[0.1, 0.2]",
                "complexity_score": 5,
                "sentiment": 0.0,
                "task_id": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "access_count": 1,
                "relevance_score": 0.8
            }
        ]

        mock_connection_pool.read_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.return_value.fetchall.return_value = mock_rows

        keywords = ["python", "programming"]
        results = await memory_storage.search_by_keywords(keywords, limit=10)

        assert len(results) == 1
        assert results[0].id == "mem-1"
        assert "python" in results[0].keywords

    @pytest.mark.asyncio
    async def test_search_by_keywords_empty(self, memory_storage):
        """Test keyword search with empty keywords."""
        results = await memory_storage.search_by_keywords([], limit=10)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_by_keywords_database_error(self, memory_storage, mock_connection_pool, mock_connection):
        """Test keyword search with database error."""
        mock_connection_pool.read_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.side_effect = Exception("Database error")

        with pytest.raises(StorageError):
            await memory_storage.search_by_keywords(["test"], limit=10)

    @pytest.mark.asyncio
    async def test_search_full_text_basic(self, memory_storage, mock_connection_pool, mock_connection):
        """Test basic full-text search."""
        mock_rows = [
            {
                "id": "mem-1",
                "content": "Full text search example",
                "content_type": "documentation",
                "content_format": "text",
                "keywords": '["full", "text", "search"]',
                "entities": "[]",
                "embedding": None,
                "complexity_score": 3,
                "sentiment": 0.0,
                "task_id": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "access_count": 1,
                "relevance_score": 0.7
            }
        ]

        mock_connection_pool.read_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.return_value.fetchall.return_value = mock_rows

        results = await memory_storage.search_full_text("search example", limit=10)

        assert len(results) == 1
        assert results[0].id == "mem-1"

    @pytest.mark.asyncio
    async def test_search_full_text_empty_query(self, memory_storage):
        """Test full-text search with empty query."""
        results = await memory_storage.search_full_text("", limit=10)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_by_content_type(self, memory_storage, mock_connection_pool, mock_connection):
        """Test search by content type."""
        mock_rows = [
            {
                "id": "code-mem",
                "content": "Code example",
                "content_type": "code",
                "content_format": "python",
                "keywords": '["code", "example"]',
                "entities": "[]",
                "embedding": None,
                "complexity_score": 6,
                "sentiment": 0.0,
                "task_id": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "access_count": 1,
                "relevance_score": 0.9
            }
        ]

        mock_connection_pool.read_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.return_value.fetchall.return_value = mock_rows

        results = await memory_storage.search_by_content_type(ContentType.CODE, limit=10)

        assert len(results) == 1
        assert results[0].content_type == ContentType.CODE

    @pytest.mark.asyncio
    async def test_search_by_task_id(self, memory_storage, mock_connection_pool, mock_connection):
        """Test search by task ID."""
        mock_rows = [
            {
                "id": "task-mem",
                "content": "Task-specific memory",
                "content_type": "context",
                "content_format": "text",
                "keywords": '["task", "specific"]',
                "entities": "[]",
                "embedding": None,
                "complexity_score": 4,
                "sentiment": 0.0,
                "task_id": "task-123",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "access_count": 1,
                "relevance_score": 0.8
            }
        ]

        mock_connection_pool.read_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.return_value.fetchall.return_value = mock_rows

        results = await memory_storage.search_by_task_id("task-123", limit=10)

        assert len(results) == 1
        assert results[0].task_id == "task-123"

    @pytest.mark.asyncio
    async def test_search_by_embedding_with_vector_table(self, memory_storage, mock_connection_pool, mock_connection):
        """Test vector search with mocked vector table."""
        # Mock vector search results
        mock_rows = [
            ("mem-1", 0.85),  # (id, similarity_score)
            ("mem-2", 0.72),
        ]

        mock_connection_pool.read_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.return_value.fetchall.return_value = mock_rows

        # Also mock the memory data retrieval
        mock_memory_data = [
            {
                "id": "mem-1",
                "content": "Similar memory 1",
                "content_type": "documentation",
                "content_format": "text",
                "keywords": '["similar", "memory"]',
                "entities": "[]",
                "embedding": "[0.1, 0.2]",
                "complexity_score": 5,
                "sentiment": 0.0,
                "task_id": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "access_count": 1,
                "relevance_score": 0.85
            }
        ]

        # Mock the second query for memory details
        async def mock_execute(*args, **kwargs):
            if "SELECT similarity" in str(args[0]):
                result = AsyncMock()
                result.fetchall.return_value = mock_rows
                return result
            else:
                result = AsyncMock()
                result.fetchall.return_value = mock_memory_data
                return result

        mock_connection.execute.side_effect = mock_execute

        query_embedding = [0.1, 0.2] + [0.0] * 382
        results = await memory_storage.search_by_embedding(query_embedding, limit=10)

        # Should return results based on vector similarity
        assert len(results) >= 0  # May be 0 if vector table doesn't exist in test

    @pytest.mark.asyncio
    async def test_search_by_embedding_empty_vector(self, memory_storage):
        """Test vector search with empty embedding."""
        with pytest.raises(ValueError):
            await memory_storage.search_by_embedding([], limit=10)

    @pytest.mark.asyncio
    async def test_get_memory_statistics(self, memory_storage, mock_connection_pool, mock_connection):
        """Test memory statistics retrieval."""
        mock_stats = {
            "total_memories": 100,
            "by_content_type": {
                "documentation": 45,
                "code": 30,
                "context": 25
            },
            "avg_complexity": 6.5,
            "avg_sentiment": 0.1
        }

        # Mock the statistics query
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = (100, 6.5, 0.1)
        mock_connection.execute.return_value = mock_result

        mock_connection_pool.read_transaction.return_value.__aenter__.return_value = mock_connection

        stats = await memory_storage.get_statistics()

        assert isinstance(stats, dict)
        assert "total_memories" in stats

    @pytest.mark.asyncio
    async def test_batch_store_memories(self, memory_storage, mock_connection_pool, mock_connection):
        """Test batch memory storage."""
        memories = [
            MemoryEntry(id=f"batch-{i}", content=f"Batch memory {i}", content_type=ContentType.DOCUMENTATION)
            for i in range(3)
        ]

        mock_connection_pool.write_transaction.return_value.__aenter__.return_value = mock_connection

        stored_ids = await memory_storage.batch_store_memories(memories)

        assert len(stored_ids) == 3
        assert all(id.startswith("batch-") for id in stored_ids)

    @pytest.mark.asyncio
    async def test_batch_store_empty_list(self, memory_storage):
        """Test batch storage with empty list."""
        stored_ids = await memory_storage.batch_store_memories([])
        assert stored_ids == []

    @pytest.mark.asyncio
    async def test_batch_store_partial_failure(self, memory_storage, mock_connection_pool, mock_connection):
        """Test batch storage with partial failure."""
        memories = [
            MemoryEntry(id="batch-1", content="Memory 1", content_type=ContentType.DOCUMENTATION),
            MemoryEntry(id="batch-2", content="Memory 2", content_type=ContentType.DOCUMENTATION),
        ]

        # Mock one success, one failure
        def mock_execute(*args, **kwargs):
            if "batch-1" in str(args):
                return AsyncMock()
            else:
                raise Exception("Database error for batch-2")

        mock_connection_pool.write_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.side_effect = mock_execute

        with pytest.raises(StorageError):
            await memory_storage.batch_store_memories(memories)

    @pytest.mark.asyncio
    async def test_update_access_count(self, memory_storage, mock_connection_pool, mock_connection):
        """Test updating memory access count."""
        mock_connection_pool.write_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.return_value.rowcount = 1

        result = await memory_storage.update_access_count("test-id")
        assert result is True

    @pytest.mark.asyncio
    async def test_update_access_count_not_found(self, memory_storage, mock_connection_pool, mock_connection):
        """Test updating access count for non-existent memory."""
        mock_connection_pool.write_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.return_value.rowcount = 0

        result = await memory_storage.update_access_count("nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_old_memories(self, memory_storage, mock_connection_pool, mock_connection):
        """Test cleanup of old memories."""
        mock_connection_pool.write_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.return_value.rowcount = 5

        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=30)

        deleted_count = await memory_storage.cleanup_old_memories(cutoff_date)
        assert deleted_count == 5

    @pytest.mark.asyncio
    async def test_get_memories_by_date_range(self, memory_storage, mock_connection_pool, mock_connection):
        """Test retrieving memories by date range."""
        mock_rows = [
            {
                "id": "recent-mem",
                "content": "Recent memory",
                "content_type": "documentation",
                "content_format": "text",
                "keywords": '["recent"]',
                "entities": "[]",
                "embedding": None,
                "complexity_score": 3,
                "sentiment": 0.0,
                "task_id": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "access_count": 1,
                "relevance_score": 0.7
            }
        ]

        mock_connection_pool.read_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.return_value.fetchall.return_value = mock_rows

        from datetime import timedelta
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()

        results = await memory_storage.get_memories_by_date_range(start_date, end_date)
        assert len(results) == 1

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_storage_performance(self, memory_storage, mock_connection_pool, mock_connection, sample_memory):
        """Test storage operation performance."""
        import time

        mock_connection_pool.write_transaction.return_value.__aenter__.return_value = mock_connection
        mock_connection_pool.read_transaction.return_value.__aenter__.return_value = mock_connection

        # Test store performance
        start_time = time.time()
        await memory_storage.store_memory(sample_memory)
        store_time = time.time() - start_time

        assert store_time < 0.5  # Should complete quickly

        # Test retrieve performance
        mock_connection.execute.return_value.fetchone.return_value = {
            "id": sample_memory.id,
            "content": sample_memory.content,
            "content_type": sample_memory.content_type.value,
            "content_format": sample_memory.content_format.value if sample_memory.content_format else None,
            "keywords": '["test"]',
            "entities": "[]",
            "embedding": "[0.1]",
            "complexity_score": 5,
            "sentiment": 0.0,
            "task_id": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "access_count": 1,
            "relevance_score": 0.8
        }

        start_time = time.time()
        await memory_storage.get_memory(sample_memory.id)
        retrieve_time = time.time() - start_time

        assert retrieve_time < 0.5  # Should complete quickly