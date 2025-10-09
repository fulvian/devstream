"""
Comprehensive tests for EmbeddingGenerator (FASE 2)

Tests for Context7 Ollama batch processing patterns, exponential backoff retry logic,
and atomic embedding insert operations following sqlite-utils patterns.
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from devstream.database.connection import ConnectionPool
from devstream.memory.embedding_generator import (
    EmbeddingConfig,
    EmbeddingGenerator,
    EmbeddingGenerationError,
)
from devstream.memory.models import MemoryEntry, ContentType, ContentFormat


@pytest.fixture
def mock_connection_pool():
    """Mock connection pool for testing."""
    pool = MagicMock(spec=ConnectionPool)
    pool.engine = MagicMock(spec=AsyncEngine)
    return pool


@pytest.fixture
def embedding_config():
    """Default embedding configuration for testing."""
    return EmbeddingConfig(
        model_name="gemma2",
        batch_size=3,  # Small batch for testing
        max_retries=2,
        base_delay=0.1,  # Fast retries for testing
        timeout=10.0,
    )


@pytest.fixture
def embedding_generator(mock_connection_pool, embedding_config):
    """Embedding generator instance for testing."""
    return EmbeddingGenerator(mock_connection_pool, embedding_config)


@pytest.fixture
def sample_memory_entries():
    """Sample memory entries for testing."""
    return [
        MemoryEntry(
            id=f"test_memory_{i}",
            content=f"Test content {i}",
            content_type=ContentType.CODE,
            content_format=ContentFormat.TEXT,
            keywords=[f"test{i}", "content"],
            entities=[{"type": "test", "value": f"value{i}"}],
            sentiment=0.5,
            complexity_score=3,
        )
        for i in range(5)
    ]


@pytest.fixture
def mock_embedding_response():
    """Mock embedding response from Ollama."""
    return {
        "embeddings": [
            [0.1, 0.2, 0.3, 0.4, 0.5] * 77  # 385 dimensions (gemma2 default)
        ]
    }


class TestEmbeddingConfig:
    """Test EmbeddingConfig validation and defaults."""

    def test_default_config(self):
        """Test default configuration values."""
        config = EmbeddingConfig()

        assert config.model_name == "gemma2"
        assert config.batch_size == 10
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.timeout == 30.0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = EmbeddingConfig(
            model_name="custom-model",
            batch_size=5,
            max_retries=5,
            base_delay=2.0,
            timeout=60.0,
        )

        assert config.model_name == "custom-model"
        assert config.batch_size == 5
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.timeout == 60.0

    def test_config_validation(self):
        """Test configuration validation constraints."""
        # Invalid batch size
        with pytest.raises(ValueError):
            EmbeddingConfig(batch_size=0)

        # Invalid max_retries
        with pytest.raises(ValueError):
            EmbeddingConfig(max_retries=0)

        # Invalid base_delay
        with pytest.raises(ValueError):
            EmbeddingConfig(base_delay=0.0)

        # Invalid timeout
        with pytest.raises(ValueError):
            EmbeddingConfig(timeout=0.0)


class TestEmbeddingGenerator:
    """Test EmbeddingGenerator main functionality."""

    @patch('devstream.memory.embedding_generator.ollama.Client')
    def test_initialization(self, mock_ollama_client, mock_connection_pool, embedding_config):
        """Test EmbeddingGenerator initialization."""
        mock_client = MagicMock()
        mock_ollama_client.return_value = mock_client

        generator = EmbeddingGenerator(mock_connection_pool, embedding_config)

        assert generator.connection_pool == mock_connection_pool
        assert generator.config == embedding_config
        assert generator._client == mock_client
        mock_ollama_client.assert_called_once_with(
            host='http://localhost:11434',
            headers={'User-Agent': 'DevStream-EmbeddingGenerator/1.0'}
        )

    @patch('devstream.memory.embedding_generator.ollama.Client')
    def test_initialization_failure(self, mock_ollama_client, mock_connection_pool):
        """Test EmbeddingGenerator initialization failure."""
        mock_ollama_client.side_effect = Exception("Connection failed")

        with pytest.raises(EmbeddingGenerationError, match="Client configuration failed"):
            EmbeddingGenerator(mock_connection_pool)

    async def test_generate_embedding_with_retry_success(
        self, embedding_generator, mock_embedding_response
    ):
        """Test successful embedding generation with retry logic."""
        embedding_generator._client = MagicMock()
        embedding_generator._client.embed.return_value = mock_embedding_response

        result = await embedding_generator._generate_embedding_with_retry("test text")

        expected_embedding = mock_embedding_response["embeddings"][0]
        assert result == expected_embedding
        embedding_generator._client.embed.assert_called_once_with(
            model="gemma2",
            input="test text"
        )

    async def test_generate_embedding_with_retry_success_after_failure(
        self, embedding_generator, mock_embedding_response
    ):
        """Test embedding generation succeeding after initial failures."""
        from ollama import ResponseError

        embedding_generator._client = MagicMock()
        # First call fails, second succeeds
        embedding_generator._client.embed.side_effect = [
            ResponseError("Temporary failure"),
            mock_embedding_response,
        ]

        result = await embedding_generator._generate_embedding_with_retry("test text")

        expected_embedding = mock_embedding_response["embeddings"][0]
        assert result == expected_embedding
        assert embedding_generator._client.embed.call_count == 2

    async def test_generate_embedding_with_retry_exhausted(self, embedding_generator):
        """Test embedding generation failure after exhausting retries."""
        from ollama import ResponseError

        embedding_generator._client = MagicMock()
        embedding_generator._client.embed.side_effect = ResponseError("Persistent failure")

        with pytest.raises(EmbeddingGenerationError) as exc_info:
            await embedding_generator._generate_embedding_with_retry("test text")

        assert "Failed to generate embedding after" in str(exc_info.value)
        assert exc_info.value.retry_count == embedding_generator.config.max_retries
        assert embedding_generator._client.embed.call_count == embedding_generator.config.max_retries + 1

    async def test_process_batch_success(
        self, embedding_generator, sample_memory_entries, mock_embedding_response
    ):
        """Test successful batch processing."""
        # Mock embedding generation
        embedding_generator._generate_embedding_with_retry = AsyncMock(
            return_value=mock_embedding_response["embeddings"][0]
        )

        batch = sample_memory_entries[:3]
        result = await embedding_generator._process_batch(batch)

        assert len(result) == len(batch)
        for entry in result:
            assert entry.embedding is not None
            assert entry.embedding_model == "gemma2"
            assert entry.embedding_dimension == 385

    async def test_process_batch_partial_failure(
        self, embedding_generator, sample_memory_entries, mock_embedding_response
    ):
        """Test batch processing with some failures."""
        # Mock embedding generation with some failures
        embedding_generator._generate_embedding_with_retry = AsyncMock(side_effect=[
            mock_embedding_response["embeddings"][0],  # Success
            EmbeddingGenerationError("Failed", retry_count=1),  # Failure
            mock_embedding_response["embeddings"][0],  # Success
        ])

        batch = sample_memory_entries[:3]
        result = await embedding_generator._process_batch(batch)

        assert len(result) == len(batch)  # All entries returned
        # First and third should have embeddings, second should not
        assert result[0].embedding is not None
        assert result[1].embedding is None  # Failed entry
        assert result[2].embedding is not None

    async def test_atomic_batch_insert(
        self, embedding_generator, sample_memory_entries
    ):
        """Test atomic batch insert to database."""
        # Prepare entries with embeddings
        for entry in sample_memory_entries:
            entry.set_embedding(np.array([0.1, 0.2, 0.3]), "gemma2")

        mock_conn = AsyncMock()
        mock_semantic_memory = MagicMock()
        mock_conn.execute.return_value = None

        with patch('devstream.memory.embedding_generator.semantic_memory', mock_semantic_memory):
            result = await embedding_generator._atomic_batch_insert(mock_conn, sample_memory_entries)

        assert result is True
        mock_conn.execute.assert_called_once()

    async def test_atomic_batch_insert_failure(
        self, embedding_generator, sample_memory_entries
    ):
        """Test atomic batch insert failure handling."""
        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await embedding_generator._atomic_batch_insert(mock_conn, sample_memory_entries)

    async def test_sync_to_virtual_tables(
        self, embedding_generator, sample_memory_entries
    ):
        """Test syncing to virtual tables."""
        # Set up embeddings for some entries
        sample_memory_entries[0].set_embedding(np.array([0.1, 0.2, 0.3]), "gemma2")
        embedding_generator._vec_table_available = True

        mock_conn = AsyncMock()
        mock_conn.execute.return_value = None

        await embedding_generator._sync_to_virtual_tables(mock_conn, sample_memory_entries)

        # Should have called execute for both FTS and vector tables
        assert mock_conn.execute.call_count >= 2  # FTS + vector for entry with embedding

    async def test_generate_and_store_embeddings_empty_list(self, embedding_generator):
        """Test handling of empty memory entries list."""
        result = await embedding_generator.generate_and_store_embeddings([])

        assert result == []

    async def test_generate_and_store_embeddings_success(
        self, embedding_generator, sample_memory_entries
    ):
        """Test successful full embedding generation and storage workflow."""
        # Mock the internal methods
        embedding_generator._process_batch = AsyncMock(side_effect=lambda x: x)
        embedding_generator._atomic_transaction = AsyncMock()
        embedding_generator._atomic_batch_insert = AsyncMock()
        embedding_generator._sync_to_virtual_tables = AsyncMock()
        embedding_generator.check_model_availability = AsyncMock(return_value=True)
        embedding_generator.pull_model_if_needed = AsyncMock(return_value=True)

        result = await embedding_generator.generate_and_store_embeddings(sample_memory_entries)

        assert len(result) == len(sample_memory_entries)
        embedding_generator.check_model_availability.assert_called_once()
        embedding_generator.pull_model_if_needed.assert_called_once()

    async def test_generate_and_store_embeddings_model_unavailable(
        self, embedding_generator, sample_memory_entries
    ):
        """Test handling when embedding model is unavailable."""
        embedding_generator.check_model_availability = AsyncMock(return_value=False)
        embedding_generator.pull_model_if_needed = AsyncMock(return_value=False)

        with patch.object(embedding_generator, 'store_memory', AsyncMock(side_effect=lambda x: x)):
            result = await embedding_generator.generate_and_store_embeddings(sample_memory_entries)

        assert len(result) == len(sample_memory_entries)
        # Should proceed without embeddings rather than failing

    async def test_check_model_availability_success(self, embedding_generator):
        """Test successful model availability check."""
        mock_models = {
            "models": [
                {"name": "gemma2:latest"},
                {"name": "llama2:latest"},
            ]
        }
        embedding_generator._client = MagicMock()
        embedding_generator._client.list.return_value = mock_models

        result = await embedding_generator.check_model_availability()

        assert result is True

    async def test_check_model_availability_not_found(self, embedding_generator):
        """Test model availability check when model not found."""
        mock_models = {
            "models": [
                {"name": "llama2:latest"},
                {"name": "mistral:latest"},
            ]
        }
        embedding_generator._client = MagicMock()
        embedding_generator._client.list.return_value = mock_models

        result = await embedding_generator.check_model_availability()

        assert result is False

    async def test_check_model_availability_api_error(self, embedding_generator):
        """Test model availability check with API error."""
        embedding_generator._client = MagicMock()
        embedding_generator._client.list.side_effect = Exception("API error")

        result = await embedding_generator.check_model_availability()

        assert result is False

    async def test_pull_model_if_needed_success(self, embedding_generator):
        """Test successful model pulling."""
        embedding_generator.check_model_availability = AsyncMock(return_value=False)
        embedding_generator._client = MagicMock()
        embedding_generator._client.pull.return_value = [
            {"status": "pulling manifest"},
            {"status": "downloading"},
            {"status": "success"},
        ]

        result = await embedding_generator.pull_model_if_needed()

        assert result is True
        embedding_generator._client.pull.assert_called_once_with("gemma2", stream=True)

    async def test_pull_model_if_needed_already_available(self, embedding_generator):
        """Test model pulling when model already available."""
        embedding_generator.check_model_availability = AsyncMock(return_value=True)

        result = await embedding_generator.pull_model_if_needed()

        assert result is True
        # Should not call pull method

    async def test_pull_model_if_needed_failure(self, embedding_generator):
        """Test model pulling failure."""
        embedding_generator.check_model_availability = AsyncMock(return_value=False)
        embedding_generator._client = MagicMock()
        embedding_generator._client.pull.side_effect = Exception("Pull failed")

        result = await embedding_generator.pull_model_if_needed()

        assert result is False


class TestEmbeddingGeneratorIntegration:
    """Integration tests for EmbeddingGenerator with storage layer."""

    @pytest.mark.asyncio
    async def test_embedding_generator_config_validation(self, mock_connection_pool):
        """Test that embedding generator properly validates configuration."""
        # Valid config should work
        config = EmbeddingConfig(batch_size=5, max_retries=2)
        generator = EmbeddingGenerator(mock_connection_pool, config)
        assert generator.config.batch_size == 5
        assert generator.config.max_retries == 2

    @pytest.mark.asyncio
    async def test_embedding_generator_context_manager(self, embedding_generator):
        """Test atomic transaction context manager."""
        mock_conn = AsyncMock()
        mock_transaction = AsyncMock()
        mock_connection_pool = AsyncMock()
        mock_connection_pool.engine.begin = MagicMock()
        mock_connection_pool.engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_connection_pool.engine.begin.return_value.__aexit__ = AsyncMock(return_value=None)

        embedding_generator.connection_pool = mock_connection_pool

        async with embedding_generator._atomic_transaction() as conn:
            assert conn == mock_conn

        mock_connection_pool.engine.begin.assert_called_once()

    def test_memory_entry_embedding_setter(self, sample_memory_entries):
        """Test MemoryEntry embedding setter method."""
        entry = sample_memory_entries[0]
        embedding_array = np.array([0.1, 0.2, 0.3, 0.4, 0.5])

        entry.set_embedding(embedding_array, "test-model")

        assert entry.embedding == [0.1, 0.2, 0.3, 0.4, 0.5]
        assert entry.embedding_model == "test-model"
        assert entry.embedding_dimension == 5

    def test_memory_entry_embedding_getter(self, sample_memory_entries):
        """Test MemoryEntry embedding getter method."""
        entry = sample_memory_entries[0]
        embedding_list = [0.1, 0.2, 0.3, 0.4, 0.5]
        entry.embedding = embedding_list
        entry.embedding_model = "test-model"
        entry.embedding_dimension = 5

        result = entry.get_embedding_array()

        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        np.testing.assert_array_equal(result, np.array(embedding_list, dtype=np.float32))

    def test_memory_entry_embedding_getter_none(self, sample_memory_entries):
        """Test MemoryEntry embedding getter when no embedding."""
        entry = sample_memory_entries[0]
        entry.embedding = None

        result = entry.get_embedding_array()

        assert result is None


@pytest.mark.slow
@pytest.mark.requires_ollama
class TestEmbeddingGeneratorWithRealOllama:
    """Integration tests with real Ollama server (requires Ollama to be running)."""

    @pytest.fixture
    def real_embedding_generator(self, mock_connection_pool):
        """Embedding generator with real Ollama client."""
        config = EmbeddingConfig(
            model_name="gemma2",
            batch_size=2,
            max_retries=1,
            base_delay=1.0,
        )
        return EmbeddingGenerator(mock_connection_pool, config)

    async def test_real_embedding_generation(self, real_embedding_generator):
        """Test real embedding generation with Ollama."""
        try:
            result = await real_embedding_generator._generate_embedding_with_retry("test text")
            assert isinstance(result, list)
            assert len(result) > 0
            assert all(isinstance(x, (int, float)) for x in result)
        except EmbeddingGenerationError:
            pytest.skip("Ollama not available or model not installed")

    async def test_real_model_availability_check(self, real_embedding_generator):
        """Test real model availability check."""
        try:
            result = await real_embedding_generator.check_model_availability()
            assert isinstance(result, bool)
        except Exception:
            pytest.skip("Ollama not available")