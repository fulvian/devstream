#!/usr/bin/env python3
"""
Unit tests for OllamaEmbeddingClient LRU cache implementation.

Tests cache functionality:
- SHA256 cache key generation
- Cache hit/miss behavior
- LRU eviction logic
- Thread safety
- Performance metrics
"""

import sys
import pytest
import time
import hashlib
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from collections import OrderedDict
import threading
import concurrent.futures

# Add utils to path
sys.path.append(str(Path(__file__).parent.parent.parent / ".claude/hooks/devstream/utils"))

from ollama_client import OllamaEmbeddingClient


class TestOllamaCacheKeyGeneration:
    """Test SHA256-based cache key generation."""

    def test_cache_key_generation_deterministic(self):
        """Test that same content produces same cache key."""
        client = OllamaEmbeddingClient()
        text = "Test content for cache key"

        key1 = client._generate_cache_key(text)
        key2 = client._generate_cache_key(text)

        assert key1 == key2, "Same content should produce same cache key"

    def test_cache_key_generation_unique(self):
        """Test that different content produces different cache keys."""
        client = OllamaEmbeddingClient()

        key1 = client._generate_cache_key("Content 1")
        key2 = client._generate_cache_key("Content 2")

        assert key1 != key2, "Different content should produce different cache keys"

    def test_cache_key_format(self):
        """Test that cache key is valid SHA256 hash."""
        client = OllamaEmbeddingClient()
        text = "Test content"

        cache_key = client._generate_cache_key(text)

        # SHA256 produces 64 character hexadecimal string
        assert len(cache_key) == 64, "Cache key should be 64 characters (SHA256)"
        assert all(c in "0123456789abcdef" for c in cache_key), "Cache key should be hex string"

    def test_cache_key_matches_manual_hash(self):
        """Test that cache key matches manual SHA256 calculation."""
        client = OllamaEmbeddingClient()
        text = "Test content"

        cache_key = client._generate_cache_key(text)
        expected_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()

        assert cache_key == expected_hash, "Cache key should match manual SHA256 hash"


class TestOllamaCacheOperations:
    """Test cache get/put operations."""

    def test_cache_get_miss(self):
        """Test cache get returns None on miss."""
        client = OllamaEmbeddingClient()

        result = client._cache_get("nonexistent_key")

        assert result is None, "Cache get should return None on miss"
        assert client._cache_misses == 1, "Should increment miss counter"

    def test_cache_put_and_get_hit(self):
        """Test cache put and subsequent get hit."""
        client = OllamaEmbeddingClient()
        cache_key = "test_key"
        embedding = [1.0, 2.0, 3.0]

        # Put in cache
        client._cache_put(cache_key, embedding)

        # Get from cache
        result = client._cache_get(cache_key)

        assert result == embedding, "Cache get should return stored embedding"
        assert client._cache_hits == 1, "Should increment hit counter"

    def test_cache_disabled(self):
        """Test that cache operations are no-op when disabled."""
        client = OllamaEmbeddingClient()
        client.cache_enabled = False

        cache_key = "test_key"
        embedding = [1.0, 2.0, 3.0]

        # Put should be no-op
        client._cache_put(cache_key, embedding)
        result = client._cache_get(cache_key)

        assert result is None, "Cache should be disabled"
        assert len(client._embedding_cache) == 0, "Cache should be empty"

    def test_cache_update_existing_key(self):
        """Test that updating existing key updates value."""
        client = OllamaEmbeddingClient()
        cache_key = "test_key"
        embedding1 = [1.0, 2.0, 3.0]
        embedding2 = [4.0, 5.0, 6.0]

        # Put first embedding
        client._cache_put(cache_key, embedding1)

        # Update with second embedding
        client._cache_put(cache_key, embedding2)

        result = client._cache_get(cache_key)

        assert result == embedding2, "Cache should return updated embedding"
        assert len(client._embedding_cache) == 1, "Cache should have only one entry"


class TestOllamaLRUEviction:
    """Test LRU eviction logic."""

    def test_lru_eviction_when_full(self):
        """Test that least recently used item is evicted when cache full."""
        client = OllamaEmbeddingClient()
        client.cache_max_size = 3

        # Fill cache
        client._cache_put("key1", [1.0])
        client._cache_put("key2", [2.0])
        client._cache_put("key3", [3.0])

        assert len(client._embedding_cache) == 3, "Cache should be full"

        # Add 4th item - should evict key1 (oldest)
        client._cache_put("key4", [4.0])

        assert len(client._embedding_cache) == 3, "Cache should still have 3 items"
        assert "key1" not in client._embedding_cache, "Oldest key should be evicted"
        assert "key4" in client._embedding_cache, "New key should be in cache"
        assert client._cache_evictions == 1, "Should increment eviction counter"

    def test_lru_eviction_multiple(self):
        """Test multiple evictions."""
        client = OllamaEmbeddingClient()
        client.cache_max_size = 2

        # Add 5 items - should evict first 3
        for i in range(5):
            client._cache_put(f"key{i}", [float(i)])

        assert len(client._embedding_cache) == 2, "Cache should have max size"
        assert "key3" in client._embedding_cache, "Second-to-last key should be in cache"
        assert "key4" in client._embedding_cache, "Last key should be in cache"
        assert client._cache_evictions == 3, "Should have 3 evictions"

    def test_lru_access_updates_order(self):
        """Test that accessing item moves it to end (most recent)."""
        client = OllamaEmbeddingClient()
        client.cache_max_size = 3

        # Fill cache
        client._cache_put("key1", [1.0])
        client._cache_put("key2", [2.0])
        client._cache_put("key3", [3.0])

        # Access key1 (makes it most recent)
        client._cache_get("key1")

        # Add 4th item - should evict key2 (now oldest)
        client._cache_put("key4", [4.0])

        assert "key1" in client._embedding_cache, "Accessed key should not be evicted"
        assert "key2" not in client._embedding_cache, "Oldest key should be evicted"


class TestOllamaCacheStats:
    """Test cache performance statistics."""

    def test_cache_stats_initial(self):
        """Test initial cache stats."""
        client = OllamaEmbeddingClient()

        stats = client.get_cache_stats()

        assert stats["enabled"] is True, "Cache should be enabled by default"
        assert stats["size"] == 0, "Cache should be empty initially"
        assert stats["hits"] == 0, "No hits initially"
        assert stats["misses"] == 0, "No misses initially"
        assert stats["evictions"] == 0, "No evictions initially"
        assert stats["hit_rate"] == 0.0, "Hit rate should be 0"

    def test_cache_stats_after_operations(self):
        """Test cache stats after operations."""
        client = OllamaEmbeddingClient()

        # Put 2 items
        client._cache_put("key1", [1.0])
        client._cache_put("key2", [2.0])

        # Hit key1, miss key3
        client._cache_get("key1")
        client._cache_get("key3")

        stats = client.get_cache_stats()

        assert stats["size"] == 2, "Cache should have 2 items"
        assert stats["hits"] == 1, "Should have 1 hit"
        assert stats["misses"] == 1, "Should have 1 miss"
        assert stats["hit_rate"] == 50.0, "Hit rate should be 50%"

    def test_cache_clear(self):
        """Test cache clear operation."""
        client = OllamaEmbeddingClient()

        # Add items and generate stats
        client._cache_put("key1", [1.0])
        client._cache_get("key1")
        client._cache_get("key2")

        # Clear cache
        client.clear_cache()

        stats = client.get_cache_stats()

        assert stats["size"] == 0, "Cache should be empty"
        assert stats["hits"] == 0, "Hits should be reset"
        assert stats["misses"] == 0, "Misses should be reset"
        assert stats["evictions"] == 0, "Evictions should be reset"


class TestOllamaCacheThreadSafety:
    """Test cache thread safety."""

    def test_concurrent_cache_access(self):
        """Test that concurrent cache access is thread-safe."""
        client = OllamaEmbeddingClient()
        client.cache_max_size = 100

        def put_and_get(thread_id: int):
            """Put and get operation for thread."""
            for i in range(10):
                key = f"thread{thread_id}_key{i}"
                embedding = [float(thread_id * 10 + i)]
                client._cache_put(key, embedding)
                result = client._cache_get(key)
                assert result == embedding, "Should get same embedding back"

        # Run 10 threads concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(put_and_get, i) for i in range(10)]
            concurrent.futures.wait(futures)

        # Verify no exceptions raised
        for future in futures:
            future.result()

        stats = client.get_cache_stats()
        assert stats["size"] == 100, "Cache should have 100 items"

    def test_concurrent_eviction(self):
        """Test that concurrent eviction is thread-safe."""
        client = OllamaEmbeddingClient()
        client.cache_max_size = 50

        def put_many(thread_id: int):
            """Put many items to trigger eviction."""
            for i in range(30):
                key = f"thread{thread_id}_key{i}"
                embedding = [float(thread_id * 30 + i)]
                client._cache_put(key, embedding)

        # Run 5 threads concurrently (150 items total, 50 max)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(put_many, i) for i in range(5)]
            concurrent.futures.wait(futures)

        stats = client.get_cache_stats()
        assert stats["size"] == 50, "Cache should be at max size"
        assert stats["evictions"] == 100, "Should have evicted 100 items"


class TestOllamaEndToEndCache:
    """Test end-to-end cache integration with generate_embedding."""

    @patch('ollama.embed')
    def test_generate_embedding_cache_hit(self, mock_embed):
        """Test that second call to generate_embedding uses cache."""
        client = OllamaEmbeddingClient()
        text = "Test content"
        embedding = [1.0, 2.0, 3.0]

        # Mock Ollama response
        mock_embed.return_value = {"embedding": embedding}

        # First call - cache miss
        result1 = client.generate_embedding(text)

        # Second call - cache hit (should NOT call Ollama)
        result2 = client.generate_embedding(text)

        assert result1 == embedding, "First call should return embedding"
        assert result2 == embedding, "Second call should return cached embedding"
        assert mock_embed.call_count == 1, "Ollama should be called only once"

        stats = client.get_cache_stats()
        assert stats["hits"] == 1, "Should have 1 cache hit"
        assert stats["misses"] == 1, "Should have 1 cache miss"

    @patch('ollama.embed')
    def test_generate_embedding_cache_disabled(self, mock_embed):
        """Test that cache can be disabled."""
        client = OllamaEmbeddingClient()
        client.cache_enabled = False
        text = "Test content"
        embedding = [1.0, 2.0, 3.0]

        # Mock Ollama response
        mock_embed.return_value = {"embedding": embedding}

        # Call twice
        result1 = client.generate_embedding(text)
        result2 = client.generate_embedding(text)

        assert result1 == embedding
        assert result2 == embedding
        assert mock_embed.call_count == 2, "Ollama should be called twice (cache disabled)"

    @patch('ollama.embed')
    def test_generate_embedding_cache_performance(self, mock_embed):
        """Test cache performance improvement."""
        client = OllamaEmbeddingClient()
        text = "Test content"
        embedding = [1.0] * 768  # Realistic embedding size

        # Mock Ollama response with delay
        def mock_embed_slow(*args, **kwargs):
            time.sleep(0.01)  # Simulate 10ms API latency
            return {"embedding": embedding}

        mock_embed.side_effect = mock_embed_slow

        # First call - cache miss
        start_time = time.time()
        result1 = client.generate_embedding(text)
        miss_latency = (time.time() - start_time) * 1000  # ms

        # Second call - cache hit
        start_time = time.time()
        result2 = client.generate_embedding(text)
        hit_latency = (time.time() - start_time) * 1000  # ms

        assert result1 == embedding
        assert result2 == embedding
        assert hit_latency < miss_latency * 0.1, "Cache hit should be 10× faster than miss"
        assert hit_latency < 1.0, "Cache hit should be < 1ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
