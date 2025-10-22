#!/usr/bin/env python3
"""
Unit tests for automatic embedding generation in direct_client.py
"""
import pytest
import struct
from unittest.mock import AsyncMock, patch, MagicMock, mock_open
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'utils'))

from direct_client import DevStreamDirectClient


@pytest.mark.asyncio
async def test_store_memory_with_embedding_success():
    """Test that embedding_blob is generated and stored correctly."""
    client = DevStreamDirectClient()

    # Mock Ollama client by patching sys.modules
    import sys
    from tests.unit.memory.mock_ollama_client import ControlMockOllamaEmbeddingClient

    mock_ollama = ControlMockOllamaEmbeddingClient(return_value=[0.1] * 768)

    # Create a mock module for ollama_client
    mock_ollama_module = MagicMock()
    mock_ollama_module.OllamaEmbeddingClient.return_value = mock_ollama

    # Patch sys.modules to use our mock
    with patch.dict('sys.modules', {'ollama_client': mock_ollama_module}):
        result = await client.store_memory(
            content="Test content for embedding generation",
            content_type="code",
            keywords=["test", "embedding"]
        )

        # Verify result
        assert result["success"] is True
        assert result["embedding_generated"] is True
        assert result["embedding_format"] == "BLOB"
        assert result["embedding_dimension"] == 768

        # Verify Ollama was called
        assert mock_ollama.call_count == 1
        assert mock_ollama.last_content == "Test content for embedding generation"


@pytest.mark.asyncio
async def test_store_memory_embedding_ollama_failure():
    """Test graceful degradation when Ollama fails."""
    client = DevStreamDirectClient()

    # Mock Ollama client to raise exception
    from tests.unit.memory.mock_ollama_client import ControlMockOllamaEmbeddingClient

    mock_ollama = ControlMockOllamaEmbeddingClient(side_effect=Exception("Ollama unavailable"))

    # Create a mock module for ollama_client
    mock_ollama_module = MagicMock()
    mock_ollama_module.OllamaEmbeddingClient.return_value = mock_ollama

    # Patch sys.modules to use our mock
    with patch.dict('sys.modules', {'ollama_client': mock_ollama_module}):
        result = await client.store_memory(
            content="Test content",
            content_type="code"
        )

        # Record should be saved even if embedding fails
        assert result["success"] is True
        assert result["embedding_generated"] is False
        assert result["embedding_format"] is None


@pytest.mark.asyncio
async def test_store_memory_embedding_blob_format():
    """Test that BLOB format is correct (struct.pack)."""
    client = DevStreamDirectClient()

    # Mock Ollama client with specific test embedding
    from tests.unit.memory.mock_ollama_client import ControlMockOllamaEmbeddingClient

    # Use 768 dimensions to satisfy database constraint
    test_embedding = [0.1] * 768  # 768 floats for testing
    mock_ollama = ControlMockOllamaEmbeddingClient(return_value=test_embedding)

    # Create a mock module for ollama_client
    mock_ollama_module = MagicMock()
    mock_ollama_module.OllamaEmbeddingClient.return_value = mock_ollama

    # Patch sys.modules to use our mock
    with patch.dict('sys.modules', {'ollama_client': mock_ollama_module}):
        result = await client.store_memory(
            content="Test",
            content_type="code"
        )

        # Verify database contains correct BLOB
        memory_id = result["memory_id"]
        with client.connection_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT embedding_blob FROM semantic_memory WHERE id = ?",
                (memory_id,)
            )
            row = cursor.fetchone()

            # Verify BLOB size (768 floats * 4 bytes = 3072 bytes)
            assert row['embedding_blob'] is not None
            assert len(row['embedding_blob']) == 3072

            # Verify BLOB content (sample first few values) with floating-point tolerance
            unpacked_sample = struct.unpack('10f', row['embedding_blob'][:40])
            expected_sample = [0.1] * 10

            # Check each value with floating-point tolerance
            for actual, expected in zip(unpacked_sample, expected_sample):
                assert abs(actual - expected) < 1e-6, f"Expected {expected}, got {actual}"


@pytest.mark.asyncio
async def test_store_memory_backward_compatibility():
    """Test that existing callers work without changes."""
    client = DevStreamDirectClient()

    # Call without checking new fields (old caller behavior)
    result = await client.store_memory(
        content="Legacy caller test",
        content_type="code"
    )

    # Old fields should still work
    assert "success" in result
    assert "memory_id" in result
    assert result["success"] is True


@pytest.mark.asyncio
async def test_store_memory_performance_acceptable():
    """Test that storage latency is acceptable (≤200ms)."""
    import time
    client = DevStreamDirectClient()

    start_time = time.time()

    result = await client.store_memory(
        content="Performance test content",
        content_type="code"
    )

    elapsed_ms = (time.time() - start_time) * 1000

    # Should complete within 200ms (including embedding generation)
    assert elapsed_ms <= 200, f"Storage took {elapsed_ms:.1f}ms (expected ≤200ms)"
    assert result["success"] is True