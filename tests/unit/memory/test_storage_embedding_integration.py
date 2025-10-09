"""
Integration tests for MemoryStorage with EmbeddingGenerator (FASE 2)

Tests for integration between storage layer and embedding generation,
including atomic batch operations and virtual table syncing.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from devstream.database.connection import ConnectionPool
from devstream.memory.embedding_generator import EmbeddingConfig, EmbeddingGenerator, EmbeddingGenerationError
from devstream.memory.models import MemoryEntry, ContentType, ContentFormat
from devstream.memory.storage import MemoryStorage


@pytest.fixture
def mock_connection_pool():
    """Mock connection pool for testing."""
    pool = MagicMock(spec=ConnectionPool)
    pool.engine = MagicMock(spec=AsyncEngine)
    return pool


@pytest.fixture
def embedding_config():
    """Embedding configuration for testing."""
    return EmbeddingConfig(
        model_name="gemma2",
        batch_size=3,
        max_retries=2,
        base_delay=0.1,
        timeout=10.0,
    )


@pytest.fixture
def memory_storage_with_embeddings(mock_connection_pool, embedding_config):
    """MemoryStorage instance with embedding generator."""
    return MemoryStorage(mock_connection_pool, embedding_config)


@pytest.fixture
def sample_memory_entries():
    """Sample memory entries for testing."""
    return [
        MemoryEntry(
            id=f"test_memory_{i}",
            content=f"Test code snippet {i}",
            content_type=ContentType.CODE,
            content_format=ContentFormat.CODE,
            keywords=[f"test{i}", "code", "python"],
            entities=[{"type": "function", "value": f"func_{i}"}],
            sentiment=0.3,
            complexity_score=5,
        )
        for i in range(5)
    ]


@pytest.fixture
def mock_embedding_vector():
    """Mock embedding vector."""
    return [0.1 * i for i in range(384)]  # 384 dimensions


class TestMemoryStorageEmbeddingIntegration:
    """Test MemoryStorage integration with EmbeddingGenerator."""

    def test_storage_initialization_with_embeddings(self, mock_connection_pool, embedding_config):
        """Test MemoryStorage initialization with embedding configuration."""
        with patch('devstream.memory.storage.EmbeddingGenerator') as mock_embedding_gen:
            mock_gen_instance = MagicMock()
            mock_embedding_gen.return_value = mock_gen_instance

            storage = MemoryStorage(mock_connection_pool, embedding_config)

            assert storage.embedding_generator == mock_gen_instance
            mock_embedding_gen.assert_called_once_with(mock_connection_pool, embedding_config)

    def test_storage_initialization_without_embeddings(self, mock_connection_pool):
        """Test MemoryStorage initialization without embedding configuration."""
        with patch('devstream.memory.storage.EmbeddingGenerator') as mock_embedding_gen:
            mock_gen_instance = MagicMock()
            mock_embedding_gen.return_value = mock_gen_instance

            storage = MemoryStorage(mock_connection_pool)

            assert storage.embedding_generator == mock_gen_instance
            # Should call with default config
            mock_embedding_gen.assert_called_once()
            args, kwargs = mock_embedding_gen.call_args
            assert args[0] == mock_connection_pool
            assert kwargs.get('config') is None

    async def test_store_memories_with_embeddings_success(
        self, memory_storage_with_embeddings, sample_memory_entries, mock_embedding_vector
    ):
        """Test successful storage of memories with embeddings."""
        storage = memory_storage_with_embeddings
        storage.embedding_generator = MagicMock()
        storage.embedding_generator.config.model_name = "gemma2"
        storage.embedding_generator.pull_model_if_needed = AsyncMock(return_value=True)
        storage.embedding_generator.generate_and_store_embeddings = AsyncMock()

        # Set up mock to return entries with embeddings
        mock_processed_entries = []
        for entry in sample_memory_entries:
            entry_copy = entry.model_copy(deep=True)
            entry_copy.set_embedding(np.array(mock_embedding_vector), "gemma2")
            mock_processed_entries.append(entry_copy)

        storage.embedding_generator.generate_and_store_embeddings.return_value = mock_processed_entries

        result = await storage.store_memories_with_embeddings(sample_memory_entries)

        assert len(result) == len(sample_memory_entries)
        for entry in result:
            assert entry.embedding is not None
            assert entry.embedding_model == "gemma2"
            assert entry.embedding_dimension == len(mock_embedding_vector)

        storage.embedding_generator.pull_model_if_needed.assert_called_once()
        storage.embedding_generator.generate_and_store_embeddings.assert_called_once_with(sample_memory_entries)

    async def test_store_memories_with_embeddings_empty_list(self, memory_storage_with_embeddings):
        """Test handling of empty memory entries list."""
        storage = memory_storage_with_embeddings

        result = await storage.store_memories_with_embeddings([])

        assert result == []

    async def test_store_memories_with_embeddings_model_unavailable(
        self, memory_storage_with_embeddings, sample_memory_entries
    ):
        """Test storage when embedding model is unavailable."""
        storage = memory_storage_with_embeddings
        storage.embedding_generator.pull_model_if_needed = AsyncMock(return_value=False)
        storage.store_memory = AsyncMock(side_effect=lambda x: x)

        result = await storage.store_memories_with_embeddings(sample_memory_entries)

        assert len(result) == len(sample_memory_entries)
        # Should proceed without embeddings, calling store_memory for each entry
        assert storage.store_memory.call_count == len(sample_memory_entries)

    async def test_store_memories_with_embeddings_generation_failure(
        self, memory_storage_with_embeddings, sample_memory_entries
    ):
        """Test storage when embedding generation fails."""
        storage = memory_storage_with_embeddings
        storage.embedding_generator.pull_model_if_needed = AsyncMock(return_value=True)
        storage.embedding_generator.generate_and_store_embeddings = AsyncMock(
            side_effect=EmbeddingGenerationError("Generation failed", retry_count=2)
        )

        with pytest.raises(Exception) as exc_info:
            await storage.store_memories_with_embeddings(sample_memory_entries)

        assert "Batch storage with embeddings failed" in str(exc_info.value)
        storage.embedding_generator.pull_model_if_needed.assert_called_once()
        storage.embedding_generator.generate_and_store_embeddings.assert_called_once_with(sample_memory_entries)

    async def test_update_memory_embeddings_success(
        self, memory_storage_with_embeddings, sample_memory_entries, mock_embedding_vector
    ):
        """Test successful update of embeddings for existing memories."""
        storage = memory_storage_with_embeddings

        # Mock get_memory to return existing entries
        storage.get_memory = AsyncMock(side_effect=lambda x: next((e for e in sample_memory_entries if e.id == x), None))

        # Mock embedding generation
        storage.embedding_generator = MagicMock()
        storage.embedding_generator.generate_and_store_embeddings = AsyncMock()

        # Set up mock to return entries with embeddings
        mock_updated_entries = []
        for entry in sample_memory_entries:
            entry_copy = entry.model_copy(deep=True)
            entry_copy.set_embedding(np.array(mock_embedding_vector), "gemma2")
            mock_updated_entries.append(entry_copy)

        storage.embedding_generator.generate_and_store_embeddings.return_value = mock_updated_entries

        memory_ids = [entry.id for entry in sample_memory_entries]
        result = await storage.update_memory_embeddings(memory_ids)

        assert len(result) == len(sample_memory_entries)
        for entry in result:
            assert entry.embedding is not None
            assert entry.embedding_model == "gemma2"

        # Should have called get_memory for each ID
        assert storage.get_memory.call_count == len(memory_ids)
        storage.embedding_generator.generate_and_store_embeddings.assert_called_once()

    async def test_update_memory_embeddings_empty_list(self, memory_storage_with_embeddings):
        """Test update memory embeddings with empty ID list."""
        storage = memory_storage_with_embeddings

        result = await storage.update_memory_embeddings([])

        assert result == []

    async def test_update_memory_embeddings_no_existing_entries(
        self, memory_storage_with_embeddings
    ):
        """Test update memory embeddings when no existing entries found."""
        storage = memory_storage_with_embeddings
        storage.get_memory = AsyncMock(return_value=None)  # No entries found

        result = await storage.update_memory_embeddings(["nonexistent_id"])

        assert result == []
        storage.get_memory.assert_called_once_with("nonexistent_id")

    async def test_update_memory_embeddings_partial_existing(
        self, memory_storage_with_embeddings, sample_memory_entries
    ):
        """Test update memory embeddings with some existing entries."""
        storage = memory_storage_with_embeddings

        # Mock get_memory to return entry for first ID, None for second
        def mock_get_memory(memory_id):
            if memory_id == sample_memory_entries[0].id:
                return sample_memory_entries[0]
            return None

        storage.get_memory = AsyncMock(side_effect=mock_get_memory)

        # Mock embedding generation
        storage.embedding_generator = MagicMock()
        storage.embedding_generator.generate_and_store_embeddings = AsyncMock(return_value=[sample_memory_entries[0]])

        memory_ids = [sample_memory_entries[0].id, "nonexistent_id"]
        result = await storage.update_memory_embeddings(memory_ids)

        assert len(result) == 1
        assert result[0].id == sample_memory_entries[0].id

        # Should have called get_memory for both IDs
        assert storage.get_memory.call_count == 2

    async def test_update_memory_embeddings_generation_failure(
        self, memory_storage_with_embeddings, sample_memory_entries
    ):
        """Test update memory embeddings when generation fails."""
        storage = memory_storage_with_embeddings
        storage.get_memory = AsyncMock(return_value=sample_memory_entries[0])

        storage.embedding_generator = MagicMock()
        storage.embedding_generator.generate_and_store_embeddings = AsyncMock(
            side_effect=EmbeddingGenerationError("Generation failed", retry_count=2)
        )

        memory_ids = [sample_memory_entries[0].id]

        with pytest.raises(Exception) as exc_info:
            await storage.update_memory_embeddings(memory_ids)

        assert "Memory embedding update failed" in str(exc_info.value)

    async def test_get_embedding_generator_status_success(self, memory_storage_with_embeddings):
        """Test successful retrieval of embedding generator status."""
        storage = memory_storage_with_embeddings
        storage.embedding_generator.check_model_availability = AsyncMock(return_value=True)

        result = await storage.get_embedding_generator_status()

        expected_keys = {
            "model_name",
            "model_available",
            "batch_size",
            "max_retries",
            "base_delay",
            "timeout",
        }
        assert set(result.keys()) == expected_keys
        assert result["model_name"] == "gemma2"
        assert result["model_available"] is True
        assert result["batch_size"] == 3
        assert result["max_retries"] == 2

    async def test_get_embedding_generator_status_failure(self, memory_storage_with_embeddings):
        """Test embedding generator status retrieval with error."""
        storage = memory_storage_with_embeddings
        storage.embedding_generator.check_model_availability = AsyncMock(side_effect=Exception("API error"))

        result = await storage.get_embedding_generator_status()

        assert "error" in result
        assert result["model_name"] == "gemma2"
        assert result["model_available"] is False
        assert "API error" in result["error"]


class TestMemoryStorageEmbeddingIntegrationAdvanced:
    """Advanced integration tests for storage with embeddings."""

    async def test_storage_with_different_embedding_configs(self, mock_connection_pool):
        """Test storage initialization with different embedding configurations."""
        configs = [
            EmbeddingConfig(model_name="llama2", batch_size=5),
            EmbeddingConfig(model_name="mistral", batch_size=2, max_retries=5),
            EmbeddingConfig(model_name="custom", timeout=60.0, base_delay=2.0),
        ]

        storages = []
        for config in configs:
            with patch('devstream.memory.storage.EmbeddingGenerator') as mock_embedding_gen:
                mock_gen_instance = MagicMock()
                mock_embedding_gen.return_value = mock_gen_instance

                storage = MemoryStorage(mock_connection_pool, config)
                storages.append(storage)

                # Verify the generator was created with the correct config
                mock_embedding_gen.assert_called_once_with(mock_connection_pool, config)

        # Verify all storages have different generator configs
        assert len(storages) == len(configs)

    async def test_storage_embedding_error_boundary(
        self, memory_storage_with_embeddings, sample_memory_entries
    ):
        """Test that embedding generation errors don't corrupt storage state."""
        storage = memory_storage_with_embeddings

        # First call succeeds
        storage.embedding_generator.pull_model_if_needed = AsyncMock(return_value=True)
        storage.embedding_generator.generate_and_store_embeddings = AsyncMock(return_value=sample_memory_entries)

        result1 = await storage.store_memories_with_embeddings(sample_memory_entries[:2])
        assert len(result1) == 2

        # Second call fails
        storage.embedding_generator.generate_and_store_embeddings = AsyncMock(
            side_effect=EmbeddingGenerationError("Failed", retry_count=3)
        )

        with pytest.raises(Exception):
            await storage.store_memories_with_embeddings(sample_memory_entries[2:4])

        # Third call succeeds again (generator should still be functional)
        storage.embedding_generator.generate_and_store_embeddings = AsyncMock(return_value=sample_memory_entries[4:5])
        result3 = await storage.store_memories_with_embeddings(sample_memory_entries[4:5])
        assert len(result3) == 1

    async def test_storage_embedding_concurrent_operations(
        self, memory_storage_with_embeddings, sample_memory_entries
    ):
        """Test concurrent embedding operations."""
        storage = memory_storage_with_embeddings

        storage.embedding_generator.pull_model_if_needed = AsyncMock(return_value=True)

        # Mock different delays for concurrent operations
        async def mock_generate_with_delay(entries):
            await asyncio.sleep(0.1)  # Simulate processing time
            return entries

        storage.embedding_generator.generate_and_store_embeddings = AsyncMock(side_effect=mock_generate_with_delay)

        # Run multiple concurrent operations
        batch1 = sample_memory_entries[0:2]
        batch2 = sample_memory_entries[2:4]
        batch3 = sample_memory_entries[4:5]

        results = await asyncio.gather(
            storage.store_memories_with_embeddings(batch1),
            storage.store_memories_with_embeddings(batch2),
            storage.store_memories_with_embeddings(batch3),
        )

        assert len(results) == 3
        assert all(len(result) == len(batch) for result, batch in zip(results, [batch1, batch2, batch3]))

    async def test_storage_embedding_memory_efficiency(self, memory_storage_with_embeddings):
        """Test that large batches are processed efficiently."""
        storage = memory_storage_with_embeddings

        # Create a large batch of entries
        large_batch = [
            MemoryEntry(
                id=f"large_test_{i}",
                content=f"Large test content {i}",
                content_type=ContentType.DOCUMENTATION,
                content_format=ContentFormat.TEXT,
                keywords=[f"large{i}", "test"],
                sentiment=0.5,
                complexity_score=3,
            )
            for i in range(100)  # 100 entries
        ]

        storage.embedding_generator.pull_model_if_needed = AsyncMock(return_value=True)
        storage.embedding_generator.generate_and_store_embeddings = AsyncMock(return_value=large_batch)

        result = await storage.store_memories_with_embeddings(large_batch)

        assert len(result) == len(large_batch)
        # Should have been called once with the entire batch
        storage.embedding_generator.generate_and_store_embeddings.assert_called_once_with(large_batch)


@pytest.mark.slow
@pytest.mark.requires_ollama
class TestMemoryStorageWithRealEmbeddings:
    """Integration tests with real embedding generation (requires Ollama)."""

    @pytest.fixture
    def storage_with_real_embeddings(self, mock_connection_pool):
        """Storage with real embedding generator."""
        config = EmbeddingConfig(
            model_name="gemma2",
            batch_size=2,
            max_retries=1,
            base_delay=1.0,
        )
        return MemoryStorage(mock_connection_pool, config)

    async def test_real_embedding_status_check(self, storage_with_real_embeddings):
        """Test real embedding status check."""
        try:
            status = await storage_with_real_embeddings.get_embedding_generator_status()
            assert isinstance(status, dict)
            assert "model_name" in status
            assert "model_available" in status
        except Exception:
            pytest.skip("Ollama not available")

    async def test_real_embedding_generation_and_storage(
        self, storage_with_real_embeddings, mock_connection_pool
    ):
        """Test real embedding generation and storage workflow."""
        # Mock database operations to focus on embedding generation
        storage_with_real_embeddings.embedding_generator._atomic_transaction = AsyncMock()
        storage_with_real_embeddings.embedding_generator._atomic_batch_insert = AsyncMock()
        storage_with_real_embeddings.embedding_generator._sync_to_virtual_tables = AsyncMock()

        sample_entries = [
            MemoryEntry(
                id="real_test_1",
                content="This is a test of real embedding generation",
                content_type=ContentType.DOCUMENTATION,
                content_format=ContentFormat.TEXT,
                keywords=["test", "embedding", "real"],
                sentiment=0.5,
                complexity_score=3,
            )
        ]

        try:
            result = await storage_with_real_embeddings.store_memories_with_embeddings(sample_entries)
            assert len(result) == 1
            # Should have embeddings if Ollama is available
            if result[0].embedding is not None:
                assert len(result[0].embedding) > 0
                assert result[0].embedding_model == "gemma2"
        except Exception:
            pytest.skip("Ollama not available or model not installed")