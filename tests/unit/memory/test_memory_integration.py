"""
Integration tests per Memory System

Test end-to-end del memory system con database,
processing, search e context assembly.
"""

import asyncio
import pytest
import tempfile
from datetime import datetime
from pathlib import Path

from devstream.database.connection import ConnectionPool
from devstream.database.migrations import MigrationRunner
from devstream.ollama.client import OllamaClient
from devstream.ollama.config import OllamaConfig
from devstream.memory import (
    MemoryStorage,
    TextProcessor,
    HybridSearchEngine,
    ContextAssembler,
    MemoryEntry,
    SearchQuery,
    ContentType,
)


class TestMemorySystemIntegration:
    """Integration test suite per Memory System."""

    @pytest.fixture
    async def temp_db_path(self):
        """Create temporary database per testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    async def connection_pool(self, temp_db_path):
        """Setup connection pool con schema."""
        pool = ConnectionPool(db_path=temp_db_path, max_connections=3)
        await pool.initialize()

        # Run migrations to create schema
        migration_runner = MigrationRunner(pool)
        await migration_runner.run_migrations()

        yield pool
        await pool.close()

    @pytest.fixture
    def ollama_config(self):
        """Mock Ollama config per testing."""
        return OllamaConfig(
            base_url="http://localhost:11434",
            timeout=30.0
        )

    @pytest.fixture
    async def memory_storage(self, connection_pool):
        """Setup memory storage con virtual tables."""
        storage = MemoryStorage(connection_pool)
        # Note: In real tests, would need sqlite-vec extension
        # For now, skip virtual table creation in tests
        yield storage

    @pytest.fixture
    async def text_processor(self, ollama_config):
        """Setup text processor (with mock Ollama)."""
        # Note: In real tests, would need Ollama running
        # For now, create processor that can work without embeddings
        ollama_client = OllamaClient(ollama_config)
        processor = TextProcessor(ollama_client)
        yield processor

    @pytest.fixture
    async def search_engine(self, memory_storage, text_processor):
        """Setup hybrid search engine."""
        return HybridSearchEngine(memory_storage, text_processor)

    @pytest.fixture
    async def context_assembler(self, search_engine):
        """Setup context assembler."""
        return ContextAssembler(search_engine)

    @pytest.mark.asyncio
    async def test_memory_entry_lifecycle(self, memory_storage):
        """Test complete memory entry lifecycle."""
        # Create memory entry
        memory = MemoryEntry(
            id="test-memory-1",
            content="This is a test memory entry for unit testing.",
            content_type=ContentType.DOCUMENTATION,
            keywords=["test", "memory", "unit"],
            entities=[{"text": "unit testing", "label": "ACTIVITY"}],
            complexity_score=5,
            sentiment=0.2
        )

        # Store memory
        memory_id = await memory_storage.store_memory(memory)
        assert memory_id == "test-memory-1"

        # Retrieve memory
        retrieved = await memory_storage.get_memory(memory_id)
        assert retrieved is not None
        assert retrieved.id == memory_id
        assert retrieved.content == memory.content
        assert retrieved.content_type == memory.content_type
        assert retrieved.keywords == memory.keywords

        # Update memory
        retrieved.sentiment = 0.5
        retrieved.complexity_score = 7
        success = await memory_storage.update_memory(retrieved)
        assert success

        # Verify update
        updated = await memory_storage.get_memory(memory_id)
        assert updated.sentiment == 0.5
        assert updated.complexity_score == 7

        # Delete memory
        deleted = await memory_storage.delete_memory(memory_id)
        assert deleted

        # Verify deletion
        not_found = await memory_storage.get_memory(memory_id)
        assert not_found is None

    @pytest.mark.asyncio
    async def test_text_processing_features(self, text_processor):
        """Test text processing e feature extraction."""
        test_text = """
        This is a comprehensive test document for natural language processing.
        It contains multiple sentences with various linguistic features.
        The document includes named entities like Python and machine learning.
        We expect the processor to extract keywords, entities, and complexity metrics.
        """

        # Process text (skip embedding generation per test speed)
        features = await text_processor.process_text(test_text, include_embedding=False)

        # Verify extracted features
        assert "keywords" in features
        assert "entities" in features
        assert "complexity_score" in features
        assert "sentiment" in features
        assert "stats" in features

        # Check keywords extraction
        keywords = features["keywords"]
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert any("test" in keyword.lower() for keyword in keywords)

        # Check complexity score
        complexity = features["complexity_score"]
        assert isinstance(complexity, int)
        assert 1 <= complexity <= 10

        # Check sentiment
        sentiment = features["sentiment"]
        assert isinstance(sentiment, float)
        assert -1.0 <= sentiment <= 1.0

    @pytest.mark.asyncio
    async def test_memory_entry_processing(self, text_processor):
        """Test complete memory entry processing."""
        memory = MemoryEntry(
            id="test-process-1",
            content="This is a code implementation for data processing algorithms.",
            content_type=ContentType.CODE
        )

        # Process memory entry (skip embedding generation)
        # Mock the embedding generation method
        original_generate = text_processor._generate_embedding
        text_processor._generate_embedding = lambda text: [0.1] * 384  # Mock embedding

        try:
            processed = await text_processor.process_memory_entry(memory)

            # Verify processing results
            assert processed.id == memory.id
            assert len(processed.keywords) > 0
            assert processed.complexity_score >= 1
            assert processed.embedding is not None
            assert len(processed.embedding) == 384
            assert "processing" in processed.context_snapshot

        finally:
            # Restore original method
            text_processor._generate_embedding = original_generate

    @pytest.mark.asyncio
    async def test_search_query_validation(self):
        """Test search query model validation."""
        # Valid query
        query = SearchQuery(
            query_text="test search",
            max_results=10,
            semantic_weight=1.0,
            keyword_weight=0.8
        )
        assert query.query_text == "test search"
        assert query.max_results == 10

        # Test validation constraints
        with pytest.raises(ValueError):
            SearchQuery(
                query_text="test",
                max_results=0  # Should be >= 1
            )

        with pytest.raises(ValueError):
            SearchQuery(
                query_text="test",
                semantic_weight=-1.0  # Should be >= 0
            )

    @pytest.mark.asyncio
    async def test_context_assembly_token_budget(self, context_assembler):
        """Test context assembly con token budget management."""
        # Test token counting
        text = "This is a sample text for token counting."
        token_count = context_assembler.count_tokens(text)
        assert isinstance(token_count, int)
        assert token_count > 0

        # Test empty context result
        empty_result = context_assembler._empty_context_result(1000, "relevance")
        assert empty_result.assembled_context == ""
        assert empty_result.total_tokens == 0
        assert empty_result.tokens_remaining == 1000
        assert not empty_result.truncated

    @pytest.mark.asyncio
    async def test_memory_content_formatting(self, context_assembler):
        """Test memory content formatting per context assembly."""
        memory = MemoryEntry(
            id="format-test",
            content="Sample content for formatting test.",
            content_type=ContentType.DOCUMENTATION,
            task_id="task-123",
            keywords=["sample", "format", "test"]
        )

        formatted = context_assembler._format_memory_content(memory)

        assert "Type: documentation" in formatted
        assert "Task: task-123" in formatted
        assert "Keywords: sample, format, test" in formatted
        assert memory.content in formatted
        assert formatted.startswith("===")

    @pytest.mark.asyncio
    async def test_batch_text_processing(self, text_processor):
        """Test batch processing di multiple texts."""
        texts = [
            "First document about machine learning and AI.",
            "Second document covering data science topics.",
            "Third document on software engineering practices."
        ]

        # Mock embedding generation per batch test
        original_generate = text_processor._generate_embedding
        text_processor._generate_embedding = lambda text: [0.1] * 384

        try:
            results = await text_processor.batch_process(texts, batch_size=2)

            assert len(results) == 3
            for i, result in enumerate(results):
                assert "keywords" in result
                assert "complexity_score" in result
                assert isinstance(result["keywords"], list)

        finally:
            text_processor._generate_embedding = original_generate

    @pytest.mark.asyncio
    async def test_error_handling(self, memory_storage):
        """Test error handling scenarios."""
        # Test storing memory con invalid data
        with pytest.raises(Exception):  # Should raise validation error
            invalid_memory = MemoryEntry(
                id="",  # Empty ID should be invalid
                content="test",
                content_type=ContentType.CODE
            )
            await memory_storage.store_memory(invalid_memory)

        # Test retrieving non-existent memory
        result = await memory_storage.get_memory("non-existent-id")
        assert result is None

        # Test updating non-existent memory
        memory = MemoryEntry(
            id="non-existent",
            content="test",
            content_type=ContentType.CODE
        )
        success = await memory_storage.update_memory(memory)
        assert not success

    @pytest.mark.asyncio
    async def test_memory_metadata_handling(self, memory_storage):
        """Test memory metadata e timestamps."""
        now = datetime.utcnow()

        memory = MemoryEntry(
            id="metadata-test",
            content="Test content with metadata",
            content_type=ContentType.CONTEXT,
            context_snapshot={"test": "metadata"},
            related_memory_ids=["related-1", "related-2"],
            access_count=5,
            relevance_score=0.8,
            created_at=now
        )

        # Store e retrieve
        await memory_storage.store_memory(memory)
        retrieved = await memory_storage.get_memory("metadata-test")

        assert retrieved.context_snapshot == {"test": "metadata"}
        assert retrieved.related_memory_ids == ["related-1", "related-2"]
        assert retrieved.access_count == 5
        assert retrieved.relevance_score == 0.8
        assert retrieved.created_at == now

    def test_content_type_enum(self):
        """Test ContentType enum values."""
        assert ContentType.CODE.value == "code"
        assert ContentType.DOCUMENTATION.value == "documentation"
        assert ContentType.CONTEXT.value == "context"
        assert ContentType.OUTPUT.value == "output"
        assert ContentType.ERROR.value == "error"
        assert ContentType.DECISION.value == "decision"
        assert ContentType.LEARNING.value == "learning"

    @pytest.mark.asyncio
    async def test_component_integration_flow(self, memory_storage, text_processor):
        """Test integration tra storage e processing components."""
        # Create e process memory
        memory = MemoryEntry(
            id="integration-test",
            content="Integration test for memory system components working together.",
            content_type=ContentType.LEARNING
        )

        # Mock embedding generation
        original_generate = text_processor._generate_embedding
        text_processor._generate_embedding = lambda text: [0.5] * 384

        try:
            # Process memory
            processed_memory = await text_processor.process_memory_entry(memory)

            # Store processed memory
            stored_id = await memory_storage.store_memory(processed_memory)
            assert stored_id == memory.id

            # Retrieve e verify all processing results are preserved
            retrieved = await memory_storage.get_memory(stored_id)
            assert retrieved.keywords == processed_memory.keywords
            assert retrieved.embedding == processed_memory.embedding
            assert retrieved.complexity_score == processed_memory.complexity_score
            assert "processing" in retrieved.context_snapshot

        finally:
            text_processor._generate_embedding = original_generate


if __name__ == "__main__":
    pytest.main([__file__, "-v"])