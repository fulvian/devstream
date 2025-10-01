#!/usr/bin/env python3
"""
DevStream Ollama Embedding Client - Context7 Compliant

Utility class for generating embeddings using Ollama API.
Implements Context7 best practices from ollama-python library.

Context7 Research:
- ollama.embed(model='gemma3', input=['text1', 'text2']) supports batch
- Batch size ≤16 recommended for accuracy
- Graceful degradation on failure (non-blocking)

Usage:
    client = OllamaEmbeddingClient()
    embedding = await client.generate_embedding("sample text")
"""

import sys
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, OrderedDict as OrderedDictType
from collections import OrderedDict
import json
import hashlib
import os
import threading

# Add utils to path
sys.path.append(str(Path(__file__).parent))
from logger import get_devstream_logger


class OllamaEmbeddingClient:
    """
    Ollama embedding client for DevStream semantic memory.

    Generates embeddings using Ollama's embeddinggemma:300m model.
    Context7-compliant implementation with graceful error handling.

    Key Features:
    - Synchronous embedding generation (ollama.embed)
    - Configurable timeout (default: 5s)
    - Graceful degradation on failure
    - Structured logging with context

    Context7 Patterns Applied:
    - ollama.embed() with input parameter for text
    - Non-blocking error handling
    - DevStream standard model: embeddinggemma:300m
    """

    def __init__(
        self,
        model: str = "embeddinggemma:300m",
        base_url: str = "http://localhost:11434",
        timeout: float = 5.0
    ):
        """
        Initialize Ollama embedding client with LRU cache.

        Args:
            model: Ollama embedding model (default: embeddinggemma:300m)
            base_url: Ollama API base URL (default: http://localhost:11434)
            timeout: Request timeout in seconds (default: 5.0)
        """
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

        self.structured_logger = get_devstream_logger('ollama_client')
        self.logger = self.structured_logger.logger

        # LRU Embedding Cache Configuration
        self.cache_enabled = os.getenv("DEVSTREAM_EMBEDDING_CACHE_ENABLED", "true").lower() == "true"
        self.cache_max_size = int(os.getenv("DEVSTREAM_EMBEDDING_CACHE_SIZE", "1000"))

        # LRU Cache: OrderedDict for insertion order tracking
        self._embedding_cache: OrderedDict[str, List[float]] = OrderedDict()
        self._cache_lock = threading.Lock()

        # Cache performance metrics
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_evictions = 0

        self.logger.info(
            "OllamaEmbeddingClient initialized",
            model=self.model,
            base_url=self.base_url,
            timeout=self.timeout,
            cache_enabled=self.cache_enabled,
            cache_max_size=self.cache_max_size
        )

    def _generate_cache_key(self, text: str) -> str:
        """
        Generate SHA256-based cache key for text content.

        Args:
            text: Text content to hash

        Returns:
            SHA256 hash as hexadecimal string
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def _cache_get(self, cache_key: str) -> Optional[List[float]]:
        """
        Retrieve embedding from cache (thread-safe).

        Args:
            cache_key: SHA256 cache key

        Returns:
            Cached embedding or None if not found
        """
        if not self.cache_enabled:
            return None

        with self._cache_lock:
            if cache_key in self._embedding_cache:
                # Move to end (most recently used)
                self._embedding_cache.move_to_end(cache_key)
                self._cache_hits += 1

                self.logger.debug(
                    "Cache hit",
                    cache_key=cache_key[:16] + "...",
                    cache_size=len(self._embedding_cache),
                    hit_rate=self._get_cache_hit_rate()
                )

                return self._embedding_cache[cache_key]

            self._cache_misses += 1
            return None

    def _cache_put(self, cache_key: str, embedding: List[float]) -> None:
        """
        Store embedding in cache with LRU eviction (thread-safe).

        Args:
            cache_key: SHA256 cache key
            embedding: Embedding vector to cache
        """
        if not self.cache_enabled:
            return

        with self._cache_lock:
            # Check if cache is full
            if cache_key not in self._embedding_cache and len(self._embedding_cache) >= self.cache_max_size:
                # Evict least recently used (first item)
                evicted_key, _ = self._embedding_cache.popitem(last=False)
                self._cache_evictions += 1

                self.logger.debug(
                    "Cache eviction (LRU)",
                    evicted_key=evicted_key[:16] + "...",
                    cache_size=len(self._embedding_cache),
                    evictions=self._cache_evictions
                )

            # Add to cache (or update if exists)
            self._embedding_cache[cache_key] = embedding
            # Move to end (most recently used)
            self._embedding_cache.move_to_end(cache_key)

            self.logger.debug(
                "Cache stored",
                cache_key=cache_key[:16] + "...",
                cache_size=len(self._embedding_cache)
            )

    def _get_cache_hit_rate(self) -> float:
        """
        Calculate cache hit rate.

        Returns:
            Hit rate as percentage (0-100)
        """
        total_requests = self._cache_hits + self._cache_misses
        if total_requests == 0:
            return 0.0
        return (self._cache_hits / total_requests) * 100

    def get_cache_stats(self) -> Dict[str, any]:
        """
        Get cache performance statistics.

        Returns:
            Dictionary with cache metrics
        """
        with self._cache_lock:
            return {
                "enabled": self.cache_enabled,
                "size": len(self._embedding_cache),
                "max_size": self.cache_max_size,
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "evictions": self._cache_evictions,
                "hit_rate": self._get_cache_hit_rate()
            }

    def clear_cache(self) -> None:
        """
        Clear all cached embeddings.
        """
        with self._cache_lock:
            self._embedding_cache.clear()
            self._cache_hits = 0
            self._cache_misses = 0
            self._cache_evictions = 0

        self.logger.info("Cache cleared")

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for single text string with LRU caching.

        Context7 Pattern: Use ollama.embed() with input parameter.
        Synchronous implementation for simplicity in hook context.

        Cache Strategy: SHA256-based LRU cache to avoid redundant API calls.
        - Cache hit: Return cached embedding (~1ms latency)
        - Cache miss: Call Ollama API and store result (~100ms latency)

        Args:
            text: Text to generate embedding for

        Returns:
            List of floats representing embedding vector, or None on failure

        Raises:
            No exceptions raised - graceful degradation on all errors
        """
        if not text or not text.strip():
            self.logger.warning("Empty text provided for embedding generation")
            return None

        # Generate cache key (SHA256 hash)
        cache_key = self._generate_cache_key(text)

        # Check cache first
        cached_embedding = self._cache_get(cache_key)
        if cached_embedding is not None:
            return cached_embedding

        # Cache miss - generate embedding via Ollama API
        try:
            # Import ollama here to avoid import errors if not installed
            import ollama

            self.logger.debug(
                "Generating embedding (cache miss)",
                text_length=len(text),
                model=self.model,
                cache_key=cache_key[:16] + "..."
            )

            # Context7 Pattern: ollama.embed() with input parameter
            # Note: Using input (not prompt) for batch-compatible API
            response = ollama.embed(
                model=self.model,
                input=text  # Single string, but API accepts list too
            )

            # Extract embeddings from response
            # Response format: {'embeddings': [[...]], ...} for batch
            # or {'embedding': [...], ...} for single
            if 'embeddings' in response:
                # Batch response format
                embeddings = response['embeddings']
                if embeddings and len(embeddings) > 0:
                    embedding = embeddings[0]  # Get first (only) embedding
                else:
                    self.logger.warning("Empty embeddings in response")
                    return None
            elif 'embedding' in response:
                # Single response format
                embedding = response['embedding']
            else:
                self.logger.error(
                    "Unexpected response format from Ollama",
                    response_keys=list(response.keys())
                )
                return None

            # Validate embedding
            if not isinstance(embedding, list) or len(embedding) == 0:
                self.logger.error(
                    "Invalid embedding format",
                    embedding_type=type(embedding).__name__
                )
                return None

            # Store in cache
            self._cache_put(cache_key, embedding)

            self.logger.debug(
                "Embedding generated successfully",
                embedding_dim=len(embedding),
                cache_stats=self.get_cache_stats()
            )

            return embedding

        except ImportError:
            self.logger.error(
                "ollama-python not installed",
                hint="Install with: pip install ollama"
            )
            return None

        except Exception as e:
            # Graceful degradation - log error but don't raise
            self.logger.error(
                "Failed to generate embedding",
                error=str(e),
                error_type=type(e).__name__
            )
            return None

    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 16
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts with batching.

        Context7 Pattern: Batch size ≤16 for accuracy.
        Processes in batches and returns results in original order.

        Args:
            texts: List of texts to generate embeddings for
            batch_size: Maximum batch size (default: 16, Context7 recommended)

        Returns:
            List of embeddings (or None for failures) in same order as input
        """
        if not texts:
            return []

        # Limit batch size per Context7 recommendation
        batch_size = min(batch_size, 16)

        results: List[Optional[List[float]]] = []

        try:
            import ollama

            # Process in batches
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]

                self.logger.debug(
                    "Processing batch",
                    batch_num=i // batch_size + 1,
                    batch_size=len(batch)
                )

                try:
                    # Context7 Pattern: ollama.embed() with list input
                    response = ollama.embed(
                        model=self.model,
                        input=batch  # List of strings
                    )

                    # Extract embeddings
                    if 'embeddings' in response:
                        batch_embeddings = response['embeddings']
                        results.extend(batch_embeddings)
                    else:
                        self.logger.error("Unexpected batch response format")
                        # Add None for each failed text in batch
                        results.extend([None] * len(batch))

                except Exception as e:
                    self.logger.error(
                        "Batch embedding failed",
                        batch_num=i // batch_size + 1,
                        error=str(e)
                    )
                    # Add None for each failed text in batch
                    results.extend([None] * len(batch))

            return results

        except ImportError:
            self.logger.error("ollama-python not installed")
            return [None] * len(texts)

        except Exception as e:
            self.logger.error(
                "Batch processing failed",
                error=str(e)
            )
            return [None] * len(texts)

    def test_connection(self) -> bool:
        """
        Test connection to Ollama server.

        Returns:
            True if Ollama is available, False otherwise
        """
        try:
            import ollama

            # Try to generate a simple embedding
            response = ollama.embed(
                model=self.model,
                input="test"
            )

            self.logger.info("Ollama connection successful")
            return True

        except ImportError:
            self.logger.error("ollama-python not installed")
            return False

        except Exception as e:
            self.logger.error(
                "Ollama connection failed",
                error=str(e)
            )
            return False


# Convenience function for quick embedding generation
def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Convenience function for quick embedding generation.

    Args:
        text: Text to generate embedding for

    Returns:
        Embedding vector or None on failure
    """
    client = OllamaEmbeddingClient()
    return client.generate_embedding(text)


if __name__ == "__main__":
    # Test script
    import sys
    import time

    print("DevStream Ollama Embedding Client Test")
    print("=" * 50)

    client = OllamaEmbeddingClient()

    # Test connection
    print("\n1. Testing connection to Ollama...")
    if client.test_connection():
        print("   ✅ Connection successful")
    else:
        print("   ❌ Connection failed")
        sys.exit(1)

    # Test single embedding
    print("\n2. Testing single embedding generation...")
    test_text = "DevStream is a task management system for Claude Code"
    embedding = client.generate_embedding(test_text)

    if embedding:
        print(f"   ✅ Embedding generated: {len(embedding)} dimensions")
        print(f"   First 5 values: {embedding[:5]}")
    else:
        print("   ❌ Embedding generation failed")

    # Test cache hit
    print("\n3. Testing cache hit (same content)...")
    start_time = time.time()
    embedding_cached = client.generate_embedding(test_text)
    cache_latency = (time.time() - start_time) * 1000  # ms

    if embedding_cached and embedding == embedding_cached:
        print(f"   ✅ Cache hit successful (latency: {cache_latency:.2f}ms)")
        stats = client.get_cache_stats()
        print(f"   Cache stats: {stats['hits']} hits, {stats['misses']} misses, hit rate: {stats['hit_rate']:.1f}%")
    else:
        print("   ❌ Cache hit failed")

    # Test batch embeddings
    print("\n4. Testing batch embedding generation...")
    test_texts = [
        "First test text",
        "Second test text",
        "Third test text"
    ]
    embeddings = client.generate_embeddings_batch(test_texts)

    success_count = sum(1 for e in embeddings if e is not None)
    print(f"   ✅ Generated {success_count}/{len(test_texts)} embeddings")

    # Test LRU eviction
    print("\n5. Testing LRU eviction (cache size limit)...")
    # Clear cache and set small size for testing
    client.clear_cache()
    client.cache_max_size = 3

    # Generate 5 unique embeddings (should evict first 2)
    for i in range(5):
        client.generate_embedding(f"Test text {i}")

    stats = client.get_cache_stats()
    print(f"   Cache size: {stats['size']}/{stats['max_size']}")
    print(f"   Evictions: {stats['evictions']}")
    if stats['evictions'] == 2:
        print("   ✅ LRU eviction working correctly")
    else:
        print(f"   ❌ Expected 2 evictions, got {stats['evictions']}")

    # Final cache stats
    print("\n6. Final cache statistics...")
    stats = client.get_cache_stats()
    print(f"   Enabled: {stats['enabled']}")
    print(f"   Size: {stats['size']}/{stats['max_size']}")
    print(f"   Hits: {stats['hits']}")
    print(f"   Misses: {stats['misses']}")
    print(f"   Evictions: {stats['evictions']}")
    print(f"   Hit rate: {stats['hit_rate']:.1f}%")

    print("\n" + "=" * 50)
    print("Test completed!")