"""
Memory-Database integration tests.

CONTEXT7-VALIDATED PATTERNS IMPLEMENTATION:
- Memory system integration with persistent SQLite storage
- Embedding persistence and retrieval testing
- Hybrid search functionality with database backend
- Memory-task relationship integrity testing
- Content processing pipeline integration
"""

import pytest
import pytest_asyncio
import asyncio
from typing import List, Dict, Any

from devstream.memory.models import MemoryEntry, ContentType, ContentFormat
from devstream.memory.storage import MemoryStorage
from devstream.memory.search import HybridSearchEngine
from devstream.memory.processing import TextProcessor
from devstream.database.queries import QueryManager


@pytest.mark.integration
@pytest.mark.memory
@pytest.mark.database
class TestMemoryDatabaseIntegration:
    """
    Test memory system integration with database storage.
    Context7-validated patterns for memory-database integration testing.
    """

    async def test_memory_storage_persistence(
        self,
        integration_query_manager: QueryManager,
        integration_mock_ollama_healthy
    ):
        """
        Test memory storage persistence in database.
        Context7 pattern: memory persistence with database backend.
        """
        storage = MemoryStorage(integration_query_manager)

        # Create and store memory entry
        memory = MemoryEntry(
            id="test-persistence-001",
            content="This is a test memory for persistence validation",
            content_type=ContentType.DOCUMENTATION,
            content_format=ContentFormat.MARKDOWN,
            keywords=["test", "persistence", "validation"],
            entities=["memory", "database"],
            complexity_score=5
        )

        # Store memory
        stored_id = await storage.store(memory)
        assert stored_id == memory.id

        # Retrieve memory
        retrieved_memory = await storage.get_by_id(memory.id)
        assert retrieved_memory is not None
        assert retrieved_memory.content == memory.content
        assert retrieved_memory.content_type == memory.content_type
        assert retrieved_memory.keywords == memory.keywords

    async def test_memory_embedding_persistence(
        self,
        integration_query_manager: QueryManager,
        integration_mock_ollama_healthy
    ):
        """
        Test embedding generation and persistence.
        Context7 pattern: embedding vector storage with database backend.
        """
        processor = TextProcessor(integration_query_manager)

        # Process memory with embedding generation
        memory = MemoryEntry(
            id="test-embedding-001",
            content="Content for embedding generation and persistence testing",
            content_type=ContentType.CODE,
            keywords=["embedding", "generation", "persistence"]
        )

        # Process memory (this should generate embeddings via mocked Ollama)
        processed_memory = await processor.process_entry(memory)

        # Verify embedding was generated and stored
        assert processed_memory.embedding is not None
        assert processed_memory.embedding_dimension > 0
        assert processed_memory.embedding_model is not None

        # Retrieve from database and verify embedding persistence
        storage = MemoryStorage(integration_query_manager)
        retrieved_memory = await storage.get_by_id(processed_memory.id)

        assert retrieved_memory.embedding == processed_memory.embedding
        assert retrieved_memory.embedding_dimension == processed_memory.embedding_dimension

    async def test_memory_search_integration(
        self,
        integration_query_manager: QueryManager,
        integration_memory_entries: List[str],
        integration_mock_ollama_healthy
    ):
        """
        Test memory search with database backend.
        Context7 pattern: hybrid search with database storage.
        """
        search = HybridSearchEngine(integration_query_manager)

        # Test keyword search
        keyword_results = await search.search_by_keywords(["fibonacci"])
        assert len(keyword_results) >= 1

        # Verify results contain expected content
        fibonacci_found = any("fibonacci" in result.content.lower() for result in keyword_results)
        assert fibonacci_found

        # Test content type filtering
        code_results = await search.search_by_content_type(ContentType.CODE)
        assert len(code_results) >= 1

        # Verify all results are code type
        for result in code_results:
            assert result.content_type == ContentType.CODE

    async def test_memory_full_text_search(
        self,
        integration_query_manager: QueryManager,
        integration_memory_entries: List[str],
        integration_mock_ollama_healthy
    ):
        """
        Test full-text search functionality.
        Context7 pattern: SQLite FTS integration with memory system.
        """
        search = HybridSearchEngine(integration_query_manager)

        # Test full-text search for specific terms
        fts_results = await search.full_text_search("recursive approach")
        assert len(fts_results) >= 1

        # Verify search results contain the search terms
        for result in fts_results:
            content_lower = result.content.lower()
            assert "recursive" in content_lower or "approach" in content_lower

    async def test_memory_relationship_integrity(
        self,
        integration_query_manager: QueryManager,
        integration_sample_task: str,
        integration_mock_ollama_healthy
    ):
        """
        Test memory-task relationship integrity.
        Context7 pattern: referential integrity testing across systems.
        """
        storage = MemoryStorage(integration_query_manager)

        # Create memory entry linked to task
        memory = MemoryEntry(
            id="test-relationship-001",
            content="Memory entry linked to a specific task for relationship testing",
            content_type=ContentType.OUTPUT,
            task_id=integration_sample_task,
            keywords=["relationship", "task", "integration"]
        )

        # Store memory with task relationship
        stored_id = await storage.store(memory)
        assert stored_id == memory.id

        # Retrieve and verify relationship
        retrieved_memory = await storage.get_by_id(memory.id)
        assert retrieved_memory.task_id == integration_sample_task

        # Test search by task relationship
        task_memories = await storage.get_by_task_id(integration_sample_task)
        assert len(task_memories) >= 1
        assert any(m.id == memory.id for m in task_memories)

    async def test_memory_concurrent_operations(
        self,
        integration_query_manager: QueryManager,
        integration_mock_ollama_healthy
    ):
        """
        Test concurrent memory operations.
        Context7 pattern: concurrent operation testing for memory system.
        """
        storage = MemoryStorage(integration_query_manager)

        async def create_memory_entry(index: int) -> str:
            memory = MemoryEntry(
                id=f"concurrent-memory-{index:03d}",
                content=f"Concurrent memory entry number {index} for testing parallel operations",
                content_type=ContentType.CONTEXT,
                keywords=[f"concurrent", f"parallel", f"test{index}"],
                complexity_score=index % 10 + 1
            )
            return await storage.store(memory)

        # Create 15 memory entries concurrently
        tasks = [create_memory_entry(i) for i in range(15)]
        memory_ids = await asyncio.gather(*tasks)

        assert len(memory_ids) == 15
        assert len(set(memory_ids)) == 15  # All IDs should be unique

        # Verify all memories were stored correctly
        for memory_id in memory_ids:
            memory = await storage.get_by_id(memory_id)
            assert memory is not None
            assert "concurrent" in memory.keywords

    async def test_memory_search_performance(
        self,
        integration_query_manager: QueryManager,
        integration_mock_ollama_healthy
    ):
        """
        Test memory search performance with larger dataset.
        Context7 pattern: performance testing with realistic data volumes.
        """
        storage = MemoryStorage(integration_query_manager)
        search = HybridSearchEngine(integration_query_manager)

        # Create batch of memory entries for performance testing
        memories = []
        for i in range(50):
            memory = MemoryEntry(
                id=f"perf-test-{i:03d}",
                content=f"Performance test memory entry {i} with searchable content including algorithm, data structure, and optimization keywords",
                content_type=ContentType.DOCUMENTATION if i % 2 == 0 else ContentType.CODE,
                keywords=["performance", "algorithm", "optimization", f"batch{i//10}"],
                complexity_score=(i % 10) + 1
            )
            memories.append(memory)

        # Store all memories
        for memory in memories:
            await storage.store(memory)

        # Test search performance
        import time
        start_time = time.time()

        search_results = await search.search_by_keywords(["algorithm", "optimization"])

        search_time = time.time() - start_time

        # Verify performance and results
        assert len(search_results) >= 10  # Should find multiple matches
        assert search_time < 1.0  # Should complete within 1 second

        # Verify result quality
        for result in search_results[:5]:  # Check first 5 results
            assert any(keyword in result.keywords for keyword in ["algorithm", "optimization"])

    async def test_memory_content_processing_pipeline(
        self,
        integration_query_manager: QueryManager,
        integration_mock_ollama_healthy
    ):
        """
        Test complete memory processing pipeline.
        Context7 pattern: end-to-end pipeline testing with integration.
        """
        processor = TextProcessor(integration_query_manager)
        storage = MemoryStorage(integration_query_manager)
        search = HybridSearchEngine(integration_query_manager)

        # Raw content for processing
        raw_content = """
        def quicksort(arr):
            if len(arr) <= 1:
                return arr
            pivot = arr[len(arr) // 2]
            left = [x for x in arr if x < pivot]
            middle = [x for x in arr if x == pivot]
            right = [x for x in arr if x > pivot]
            return quicksort(left) + middle + quicksort(right)
        """

        # Create memory entry
        memory = MemoryEntry(
            id="pipeline-test-001",
            content=raw_content,
            content_type=ContentType.CODE,
            content_format=ContentFormat.PYTHON
        )

        # Step 1: Process entry (extract keywords, entities, generate embedding)
        processed_memory = await processor.process_entry(memory)

        # Verify processing results
        assert len(processed_memory.keywords) > 0
        assert processed_memory.embedding is not None
        assert processed_memory.complexity_score > 1

        # Step 2: Store processed entry
        stored_id = await storage.store(processed_memory)
        assert stored_id == processed_memory.id

        # Step 3: Search for stored entry
        search_results = await search.search_by_content("quicksort algorithm")

        # Verify pipeline integration
        found_memory = None
        for result in search_results:
            if result.id == processed_memory.id:
                found_memory = result
                break

        assert found_memory is not None
        assert "quicksort" in found_memory.content.lower()

    async def test_memory_cleanup_and_archival(
        self,
        integration_query_manager: QueryManager,
        integration_mock_ollama_healthy
    ):
        """
        Test memory cleanup and archival functionality.
        Context7 pattern: data lifecycle management integration testing.
        """
        storage = MemoryStorage(integration_query_manager)

        # Create memory entries with different access patterns
        active_memory = MemoryEntry(
            id="cleanup-active-001",
            content="Frequently accessed memory entry that should remain active",
            content_type=ContentType.CONTEXT,
            keywords=["active", "frequent"],
            access_count=10
        )

        old_memory = MemoryEntry(
            id="cleanup-old-001",
            content="Old memory entry that could be archived",
            content_type=ContentType.OUTPUT,
            keywords=["old", "archive"],
            access_count=1,
            is_archived=False
        )

        # Store both memories
        await storage.store(active_memory)
        await storage.store(old_memory)

        # Test archival
        await storage.archive_memory(old_memory.id)

        # Verify archival status
        archived_memory = await storage.get_by_id(old_memory.id)
        assert archived_memory.is_archived == True

        # Verify active memory remains unarchived
        active_retrieved = await storage.get_by_id(active_memory.id)
        assert active_retrieved.is_archived == False

        # Test search excludes archived by default
        search = HybridSearchEngine(integration_query_manager)
        search_results = await search.search_by_keywords(["archive"])

        # Should not find archived memory in regular search
        archived_found = any(result.id == old_memory.id for result in search_results)
        assert not archived_found