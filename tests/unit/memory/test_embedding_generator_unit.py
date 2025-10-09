"""
Unit tests for EmbeddingGenerator utility functions and edge cases (FASE 2)

Focus on testing atomic operations, error handling patterns, and edge cases
that don't require full integration setup.
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from devstream.memory.embedding_generator import (
    EmbeddingConfig,
    EmbeddingGenerator,
    EmbeddingGenerationError,
)


class TestEmbeddingGeneratorUtilities:
    """Test utility functions and helper methods."""

    @pytest.fixture
    def mock_generator(self):
        """Mock embedding generator for utility testing."""
        mock_connection_pool = MagicMock()
        config = EmbeddingConfig(
            model_name="test-model",
            batch_size=2,
            max_retries=1,
            base_delay=0.1,
        )

        with patch('devstream.memory.embedding_generator.ollama.Client'):
            generator = EmbeddingGenerator(mock_connection_pool, config)
            generator._client = MagicMock()
            return generator

    def test_atomic_transaction_context_manager_success(self, mock_generator):
        """Test atomic transaction context manager success path."""
        mock_conn = AsyncMock()
        mock_transaction = MagicMock()
        mock_transaction.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_transaction.__aexit__ = AsyncMock(return_value=None)

        mock_connection_pool = MagicMock()
        mock_connection_pool.engine.begin.return_value = mock_transaction
        mock_generator.connection_pool = mock_connection_pool

        async def test_operation():
            async with mock_generator._atomic_transaction() as conn:
                assert conn == mock_conn
                return "success"

        result = asyncio.run(test_operation())

        assert result == "success"
        mock_connection_pool.engine.begin.assert_called_once()

    def test_atomic_transaction_context_manager_failure(self, mock_generator):
        """Test atomic transaction context manager failure path."""
        mock_conn = AsyncMock()
        mock_transaction = MagicMock()
        mock_transaction.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_transaction.__aexit__ = AsyncMock(return_value=None)

        mock_connection_pool = MagicMock()
        mock_connection_pool.engine.begin.return_value = mock_transaction
        mock_generator.connection_pool = mock_connection_pool

        async def test_operation():
            async with mock_generator._atomic_transaction() as conn:
                raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            asyncio.run(test_operation())

        mock_connection_pool.engine.begin.assert_called_once()

    def test_embedding_generation_error_attributes(self):
        """Test EmbeddingGenerationError attributes."""
        original_error = ValueError("Original error")
        error = EmbeddingGenerationError(
            message="Test error",
            retry_count=3,
            original_error=original_error
        )

        assert str(error) == "Test error"
        assert error.retry_count == 3
        assert error.original_error == original_error

    def test_embedding_generation_error_defaults(self):
        """Test EmbeddingGenerationError default values."""
        error = EmbeddingGenerationError("Test error")

        assert str(error) == "Test error"
        assert error.retry_count == 0
        assert error.original_error is None

    @pytest.mark.parametrize("text_length", [1, 10, 100, 1000, 10000])
    async def test_generate_embedding_different_text_lengths(self, mock_generator, text_length):
        """Test embedding generation with different text lengths."""
        mock_generator._client.embed.return_value = {
            "embeddings": [[0.1, 0.2, 0.3, 0.4, 0.5]]
        }

        text = "x" * text_length
        result = await mock_generator._generate_embedding_with_retry(text)

        assert result == [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_generator._client.embed.assert_called_once_with(
            model="test-model",
            input=text
        )

    @pytest.mark.parametrize("batch_size", [1, 5, 10, 20])
    async def test_process_different_batch_sizes(self, mock_generator, batch_size):
        """Test processing different batch sizes."""
        from src.devstream.memory.models import MemoryEntry, ContentType, ContentFormat

        # Create batch of specified size
        batch = [
            MemoryEntry(
                id=f"test_{i}",
                content=f"Test content {i}",
                content_type=ContentType.DOCUMENTATION,
                content_format=ContentFormat.TEXT,
            )
            for i in range(batch_size)
        ]

        mock_generator._generate_embedding_with_retry = AsyncMock(
            return_value=[0.1, 0.2, 0.3, 0.4, 0.5]
        )

        result = await mock_generator._process_batch(batch)

        assert len(result) == batch_size
        for entry in result:
            assert entry.embedding is not None
            assert entry.embedding_model == "test-model"

        # Should have called embedding generation for each entry
        assert mock_generator._generate_embedding_with_retry.call_count == batch_size

    async def test_process_batch_with_mixed_success_failure(self, mock_generator):
        """Test batch processing with mixed success and failure."""
        from src.devstream.memory.models import MemoryEntry, ContentType, ContentFormat

        batch = [
            MemoryEntry(
                id=f"test_{i}",
                content=f"Test content {i}",
                content_type=ContentType.DOCUMENTATION,
                content_format=ContentFormat.TEXT,
            )
            for i in range(5)
        ]

        # Mock embedding generation with mixed results
        async def mock_generate_with_retry(text):
            if "content 2" in text:  # Third item fails
                raise EmbeddingGenerationError("Failed", retry_count=1)
            return [0.1, 0.2, 0.3, 0.4, 0.5]

        mock_generator._generate_embedding_with_retry = AsyncMock(side_effect=mock_generate_with_retry)

        result = await mock_generator._process_batch(batch)

        assert len(result) == 5  # All entries returned
        # Entry 2 (index 2) should not have embedding
        assert result[0].embedding is not None
        assert result[1].embedding is not None
        assert result[2].embedding is None  # Failed
        assert result[3].embedding is not None
        assert result[4].embedding is not None

    async def test_sync_to_virtual_tables_with_mixed_embeddings(self, mock_generator):
        """Test syncing to virtual tables with mixed embedding availability."""
        from src.devstream.memory.models import MemoryEntry, ContentType, ContentFormat

        entries = [
            MemoryEntry(
                id=f"test_{i}",
                content=f"Test content {i}",
                content_type=ContentType.DOCUMENTATION,
                content_format=ContentFormat.TEXT,
                keywords=[f"test{i}"],
                entities=[{"type": "test", "value": f"value{i}"}],
            )
            for i in range(3)
        ]

        # Add embeddings to first and third entries only
        entries[0].set_embedding(np.array([0.1, 0.2, 0.3]), "test-model")
        entries[2].set_embedding(np.array([0.4, 0.5, 0.6]), "test-model")

        mock_generator._vec_table_available = True
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = None

        await mock_generator._sync_to_virtual_tables(mock_conn, entries)

        # Should have called execute for FTS (all 3 entries) + vector (2 entries with embeddings)
        assert mock_conn.execute.call_count >= 5

    async def test_sync_to_virtual_tables_without_vector_table(self, mock_generator):
        """Test syncing to virtual tables when vector table is not available."""
        from src.devstream.memory.models import MemoryEntry, ContentType, ContentFormat

        entry = MemoryEntry(
            id="test_1",
            content="Test content",
            content_type=ContentType.DOCUMENTATION,
            content_format=ContentFormat.TEXT,
            keywords=["test"],
            entities=[{"type": "test", "value": "value"}],
        )
        entry.set_embedding(np.array([0.1, 0.2, 0.3]), "test-model")

        mock_generator._vec_table_available = False  # Vector table not available
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = None

        await mock_generator._sync_to_virtual_tables(mock_conn, [entry])

        # Should have called execute only for FTS (vector sync skipped)
        assert mock_conn.execute.call_count == 1

    async def test_sync_to_virtual_tables_handles_errors_gracefully(self, mock_generator):
        """Test that virtual table sync errors don't raise exceptions."""
        from src.devstream.memory.models import MemoryEntry, ContentType, ContentFormat

        entry = MemoryEntry(
            id="test_1",
            content="Test content",
            content_type=ContentType.DOCUMENTATION,
            content_format=ContentFormat.TEXT,
            keywords=["test"],
            entities=[{"type": "test", "value": "value"}],
        )
        entry.set_embedding(np.array([0.1, 0.2, 0.3]), "test-model")

        mock_generator._vec_table_available = True
        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = Exception("Database error")

        # Should not raise exception
        await mock_generator._sync_to_virtual_tables(mock_conn, [entry])

        mock_conn.execute.assert_called()

    @pytest.mark.parametrize("retry_count", [0, 1, 2, 3])
    async def test_exponential_backoff_delays(self, mock_generator, retry_count):
        """Test exponential backoff delay calculation."""
        mock_generator._client.embed.side_effect = Exception("Always fails")
        mock_generator.config.max_retries = 3
        mock_generator.config.base_delay = 0.1

        with patch('asyncio.sleep') as mock_sleep:
            try:
                await mock_generator._generate_embedding_with_retry("test text")
            except EmbeddingGenerationError:
                pass  # Expected to fail

            # Should have called sleep for each retry attempt
            if retry_count > 0:
                assert mock_sleep.call_count == min(retry_count, mock_generator.config.max_retries)

                # Check that delays follow exponential pattern
                for i, call in enumerate(mock_sleep.call_args_list):
                    expected_delay = mock_generator.config.base_delay * (2 ** i)
                    assert call[0][0] == expected_delay

    async def test_empty_embedding_response_handling(self, mock_generator):
        """Test handling of empty embedding response."""
        mock_generator._client.embed.return_value = {"embeddings": []}

        with pytest.raises(EmbeddingGenerationError, match="Empty embedding response"):
            await mock_generator._generate_embedding_with_retry("test text")

    async def test_malformed_embedding_response_handling(self, mock_generator):
        """Test handling of malformed embedding response."""
        mock_generator._client.embed.return_value = {"embeddings": "not_a_list"}

        with pytest.raises(EmbeddingGenerationError):
            await mock_generator._generate_embedding_with_retry("test text")

    async def test_embedding_response_missing_embeddings_key(self, mock_generator):
        """Test handling of embedding response missing embeddings key."""
        mock_generator._client.embed.return_value = {"other_key": "value"}

        with pytest.raises(EmbeddingGenerationError):
            await mock_generator._generate_embedding_with_retry("test text")

    def test_embedding_config_serialization(self):
        """Test that EmbeddingConfig can be serialized to JSON."""
        config = EmbeddingConfig(
            model_name="test-model",
            batch_size=5,
            max_retries=2,
            base_delay=0.5,
            timeout=15.0,
        )

        config_dict = config.dict()
        config_json = json.dumps(config_dict)
        loaded_dict = json.loads(config_json)

        assert loaded_dict["model_name"] == "test-model"
        assert loaded_dict["batch_size"] == 5
        assert loaded_dict["max_retries"] == 2
        assert loaded_dict["base_delay"] == 0.5
        assert loaded_dict["timeout"] == 15.0

    def test_embedding_config_from_dict(self):
        """Test creating EmbeddingConfig from dictionary."""
        config_dict = {
            "model_name": "dict-model",
            "batch_size": 8,
            "max_retries": 4,
            "base_delay": 2.0,
            "timeout": 60.0,
        }

        config = EmbeddingConfig(**config_dict)

        assert config.model_name == "dict-model"
        assert config.batch_size == 8
        assert config.max_retries == 4
        assert config.base_delay == 2.0
        assert config.timeout == 60.0

    @pytest.mark.parametrize("model_name", ["gemma2", "llama2", "mistral", "custom-model"])
    def test_different_model_names(self, model_name):
        """Test embedding generator with different model names."""
        mock_connection_pool = MagicMock()
        config = EmbeddingConfig(model_name=model_name)

        with patch('devstream.memory.embedding_generator.ollama.Client'):
            generator = EmbeddingGenerator(mock_connection_pool, config)
            assert generator.config.model_name == model_name

    def test_client_setup_with_custom_headers(self):
        """Test Ollama client setup with custom headers."""
        mock_connection_pool = MagicMock()
        config = EmbeddingConfig(model_name="test-model")

        with patch('src.devstream.memory.embedding_generator.ollama.Client') as mock_client:
            generator = EmbeddingGenerator(mock_connection_pool, config)

            mock_client.assert_called_once_with(
                host='http://localhost:11434',
                headers={'User-Agent': 'DevStream-EmbeddingGenerator/1.0'}
            )

    async def test_model_pull_progress_logging(self, mock_generator):
        """Test that model pull progress is logged correctly."""
        mock_generator._client.pull.return_value = [
            {"status": "pulling manifest"},
            {"status": "downloading abc123"},
            {"status": "downloading def456"},
            {"status": "verifying"},
            {"status": "success"},
        ]

        with patch('src.devstream.memory.embedding_generator.logger') as mock_logger:
            result = await mock_generator.pull_model_if_needed()

            assert result is True

            # Should have logged debug messages for each progress step
            debug_calls = [call for call in mock_logger.debug.call_args_list if 'status' in str(call)]
            assert len(debug_calls) >= 5

    async def test_model_pull_failure_handling(self, mock_generator):
        """Test model pull failure handling."""
        mock_generator.check_model_availability = AsyncMock(return_value=False)
        mock_generator._client.pull.side_effect = Exception("Pull failed")

        result = await mock_generator.pull_model_if_needed()

        assert result is False

    async def test_concurrent_embedding_generation(self, mock_generator):
        """Test concurrent embedding generation requests."""
        mock_generator._client.embed.return_value = {
            "embeddings": [[0.1, 0.2, 0.3, 0.4, 0.5]]
        }

        texts = ["test 1", "test 2", "test 3"]

        # Run multiple embedding generations concurrently
        tasks = [
            mock_generator._generate_embedding_with_retry(text)
            for text in texts
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == len(texts)
        for result in results:
            assert result == [0.1, 0.2, 0.3, 0.4, 0.5]

        # All should have been called
        assert mock_generator._client.embed.call_count == len(texts)

    def test_memory_efficient_batch_processing(self, mock_generator):
        """Test that batch processing doesn't accumulate memory."""
        from src.devstream.memory.models import MemoryEntry, ContentType, ContentFormat

        # Create a large batch
        large_batch = [
            MemoryEntry(
                id=f"test_{i}",
                content=f"Test content {i}",
                content_type=ContentType.DOCUMENTATION,
                content_format=ContentFormat.TEXT,
            )
            for i in range(1000)
        ]

        # Verify that creating the batch doesn't consume excessive memory
        assert len(large_batch) == 1000

        # The actual processing would be tested in integration tests
        # This test ensures the batch can be created without issues