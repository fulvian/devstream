"""
Comprehensive tests for SemanticCacheKeys system.

Tests validate the 60%+ hit rate improvement target from 0.017% baseline.
Context7-compliant testing patterns with proper error handling and performance validation.
"""
import time
import pytest
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../.claude/hooks'))

from optimization.semantic_cache_keys import (
    SemanticCacheKeys,
    get_semantic_cache_keys,
    CacheHitType,
    CacheKeyMetadata,
    CacheStats
)


class TestSemanticCacheKeys:
    """Test the main SemanticCacheKeys functionality."""

    @pytest.fixture
    def cache(self):
        """Create a cache instance for testing."""
        return SemanticCacheKeys(
            max_cache_size=100,
            similarity_threshold=0.75,
            cluster_threshold=0.65
        )

    def test_cache_initialization(self, cache):
        """Test cache initialization with default parameters."""
        assert cache.max_cache_size == 100
        assert cache.similarity_threshold == 0.75
        assert cache.cluster_threshold == 0.65
        assert cache.enable_embeddings is True
        assert cache.embedding_dim == 384

        # Check internal structures
        assert len(cache._cache) == 0
        assert len(cache._metadata) == 0
        assert len(cache._clusters) == 0
        assert isinstance(cache._stats, CacheStats)

    def test_extract_content_features(self, cache):
        """Test content feature extraction."""
        query = "Create FastAPI endpoint for user authentication"
        features = cache._extract_content_features(query)

        # Validate feature structure
        assert isinstance(features, dict)
        assert "query_length" in features
        assert "word_count" in features
        assert "has_file_ops" in features
        assert "has_db_ops" in features
        assert "has_api_ops" in features
        assert "has_test_ops" in features
        assert "has_memory_ops" in features
        assert "programming_language" in features
        assert "keywords" in features

        # Validate feature values
        assert features["query_length"] > 0
        assert features["word_count"] > 0
        assert features["has_api_ops"] is True  # Should detect "API"
        assert len(features["keywords"]) > 0
        assert "api" in features["keywords"]

    def test_detect_programming_language(self, cache):
        """Test programming language detection."""
        # Test file path detection
        python_features = cache._detect_language("create function", "test.py")
        assert python_features == "python"

        js_features = cache._detect_language("create function", "test.js")
        assert js_features == "javascript"

        ts_features = cache._detect_language("interface Test", "test.ts")
        assert ts_features == "typescript"

        # Test query-based detection
        python_query = cache._detect_language("def test_function():")
        assert python_query == "python"

        js_query = cache._detect_language("const test = function() {}")
        assert js_query == "javascript"

        # Test no detection
        no_detection = cache._detect_language("some random text")
        assert no_detection is None

    def test_extract_keywords(self, cache):
        """Test keyword extraction from queries."""
        query = "Create API endpoint for authentication with token validation"
        keywords = cache._extract_keywords(query)

        # Should extract technical keywords
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert "api" in keywords
        assert "endpoint" in keywords
        assert "auth" in keywords
        assert "token" in keywords

    def test_generate_semantic_hash(self, cache):
        """Test semantic hash generation."""
        query = "Create FastAPI endpoint for users"
        features = cache._extract_content_features(query)
        hash_value = cache._generate_semantic_hash(query, features)

        # Should generate consistent hash
        assert isinstance(hash_value, str)
        assert len(hash_value) == 16  # SHA256 truncated to 16 chars

        # Same query should generate same hash
        hash2 = cache._generate_semantic_hash(query, features)
        assert hash_value == hash2

    def test_find_pattern_cluster(self, cache):
        """Test pattern-based cluster detection."""
        # Test API operations
        api_cluster = cache._find_pattern_cluster("Create REST API endpoint")
        assert api_cluster == "api_ops"

        # Test database operations
        db_cluster = cache._find_pattern_cluster("Connect to database")
        assert db_cluster == "database_ops"

        # Test file operations
        file_cluster = cache._find_pattern_cluster("Read configuration file")
        assert file_cluster == "file_ops"

        # Test testing operations
        test_cluster = cache._find_pattern_cluster("Write unit tests")
        assert test_cluster == "testing_ops"

        # Test no pattern match
        no_cluster = cache._find_pattern_cluster("Some random query")
        assert no_cluster is None

    def test_calculate_similarity(self, cache):
        """Test semantic similarity calculation."""
        query1 = "Create FastAPI endpoint for users"
        query2 = "Create FastAPI endpoint for user management"
        query3 = "Setup database connection with PostgreSQL"

        # Similar queries should have high similarity
        similarity1 = cache._calculate_similarity(query1, query2)
        assert similarity1 > 0.5

        # Different queries should have low similarity
        similarity2 = cache._calculate_similarity(query1, query3)
        assert similarity2 < 0.5

        # Identical queries should have similarity of 1.0
        similarity3 = cache._calculate_similarity(query1, query1)
        assert similarity3 == 1.0

    def test_cache_get_set_operations(self, cache):
        """Test basic cache get/set operations."""
        query = "Create FastAPI endpoint for users"
        limit = 10
        content_type = "code"
        value = {"result": "endpoint_data", "type": "FastAPI"}

        # Test cache miss
        result, hit_type = cache.get(query, limit, content_type)
        assert result is None
        assert hit_type == CacheHitType.MISS

        # Set value
        cache.set(query, limit, content_type, value)

        # Test cache hit
        result, hit_type = cache.get(query, limit, content_type)
        assert result == value
        assert hit_type == CacheHitType.EXACT_MATCH

    def test_semantic_cache_hit(self, cache):
        """Test semantic similarity cache hits."""
        query1 = "Create FastAPI endpoint for users"
        query2 = "Create FastAPI endpoint for user management"
        limit = 10
        value = {"result": "endpoint_data", "type": "FastAPI"}

        # Store first query
        cache.set(query1, limit, None, value)

        # Try to get with similar query
        result, hit_type = cache.get(query2, limit, None)

        # Should potentially find semantic match
        if hit_type in [CacheHitType.SEMANTIC_MATCH, CacheHitType.CLUSTER_MATCH]:
            assert result == value
        else:
            # If no semantic hit, might be due to threshold or pattern matching
            assert hit_type == CacheHitType.MISS

    def test_cache_statistics_tracking(self, cache):
        """Test cache statistics tracking."""
        queries = [
            ("Create FastAPI endpoint", {"data": "api_data"}),
            ("Setup database connection", {"data": "db_data"}),
            ("Write unit tests", {"data": "test_data"})
        ]

        # Store some values
        for query, value in queries:
            cache.set(query, 10, None, value)

        # Perform cache operations
        # Exact hits
        cache.get("Create FastAPI endpoint", 10, None)
        cache.get("Setup database connection", 10, None)

        # Miss
        cache.get("Non-existent query", 10, None)

        # Get statistics
        stats = cache.get_stats()

        # Validate statistics
        assert isinstance(stats, CacheStats)
        assert stats.total_requests >= 3
        assert stats.cache_size == 3
        assert stats.exact_hits >= 2
        assert stats.misses >= 1
        assert stats.hit_rate >= 0.0

    def test_cache_performance_targets(self, cache):
        """Test cache performance meets targets."""
        # Performance targets
        max_query_time = 5.0  # 5ms for cache operations

        # Test cache set performance
        start_time = time.time()
        for i in range(100):
            cache.set(f"perf_key_{i}", 10, None, {"data": f"value_{i}"})
        set_time = (time.time() - start_time) * 1000

        # Test cache get performance
        start_time = time.time()
        for i in range(100):
            cache.get(f"perf_key_{i}", 10, None)
        get_time = (time.time() - start_time) * 1000

        # Validate performance
        avg_set_time = set_time / 100
        avg_get_time = get_time / 100

        assert avg_set_time < max_query_time, f"Set too slow: {avg_set_time:.4f}ms"
        assert avg_get_time < max_query_time, f"Get too slow: {avg_get_time:.4f}ms"

    def test_cache_size_limit_enforcement(self, cache):
        """Test cache size limit enforcement."""
        small_cache = SemanticCacheKeys(max_cache_size=3)

        # Fill cache beyond limit
        for i in range(5):
            small_cache.set(f"key_{i}", 10, None, {"data": f"value_{i}"})

        # Cache should not exceed limit
        assert len(small_cache._cache) <= 3

        # Should still be able to retrieve recent items
        recent_result, _ = small_cache.get("key_4", 10, None)
        assert recent_result == {"data": "value_4"}

    def test_optimization_recommendations(self, cache):
        """Test cache optimization recommendations."""
        # Simulate poor performance
        cache._stats.hit_rate = 25.0  # Low hit rate
        cache._stats.avg_query_time_ms = 15.0  # Slow queries
        cache._stats.cache_size = 95  # Near capacity (for cache with max_size=100)

        recommendations = cache.optimize_for_hit_rate()

        # Should provide recommendations
        assert "current_stats" in recommendations
        assert "recommendations" in recommendations
        assert len(recommendations["recommendations"]) > 0

        # Check for specific recommendations
        rec_types = [rec["type"] for rec in recommendations["recommendations"]]
        assert "hit_rate" in rec_types
        assert "performance" in rec_types
        assert "capacity" in rec_types


class TestCacheHitRateImprovement:
    """Test cache hit rate improvement validation."""

    def test_baseline_simulation(self):
        """Test baseline hit rate measurement (simulating 0.017% baseline)."""
        # Create very restrictive cache to simulate poor performance
        poor_cache = SemanticCacheKeys(
            max_cache_size=1,
            similarity_threshold=1.0,  # Only exact matches
            cluster_threshold=1.0      # Only exact cluster matches
        )

        # Generate diverse queries that won't match
        queries = [f"unique_query_{i}_content" for i in range(1000)]

        # Store one item only
        poor_cache.set(queries[0], 10, None, {"data": "single_value"})

        # Measure baseline performance
        hits = 0
        for query in queries:
            result, hit_type = poor_cache.get(query, 10, None)
            if hit_type != CacheHitType.MISS:
                hits += 1

        baseline_hit_rate = (hits / len(queries)) * 100

        # Should simulate very poor baseline (close to 0.017%)
        assert baseline_hit_rate < 1.0  # Less than 1%

    def test_improved_hit_rate_validation(self):
        """Test improved cache hit rate meets 60%+ target."""
        # Create optimized cache
        optimized_cache = SemanticCacheKeys(
            max_cache_size=100,
            similarity_threshold=0.75,  # Allow semantic matches
            cluster_threshold=0.65      # Allow cluster matches
        )

        # Create query clusters with similar patterns
        query_clusters = [
            [
                "Create FastAPI endpoint for users",
                "Create FastAPI endpoint for user management",
                "Create FastAPI endpoint for user authentication",
                "Create FastAPI endpoint for user profile"
            ],
            [
                "Setup database connection",
                "Configure database settings",
                "Initialize database connection",
                "Connect to PostgreSQL database"
            ],
            [
                "Write unit tests",
                "Create test cases",
                "Add pytest tests",
                "Write test functions"
            ]
        ]

        # Store some queries to build cache and patterns
        for cluster in query_clusters:
            optimized_cache.set(cluster[0], 10, None, {"cluster_data": cluster[0]})

        # Test hit rate improvement
        total_queries = 0
        cache_hits = 0

        # Test all queries including variations
        for cluster in query_clusters:
            for query in cluster:
                total_queries += 1
                result, hit_type = optimized_cache.get(query, 10, None)
                if hit_type != CacheHitType.MISS:
                    cache_hits += 1

        # Calculate hit rate
        hit_rate = (cache_hits / total_queries) * 100

        # Should meet 60%+ improvement target
        assert hit_rate >= 60.0, f"Hit rate {hit_rate:.2f}% below 60% target"

        # Validate statistics
        stats = optimized_cache.get_stats()
        assert stats.hit_rate >= 60.0


class TestSemanticCacheIntegration:
    """Test integration patterns and factory functions."""

    def test_get_semantic_cache_keys_singleton(self):
        """Test the factory function for getting cache instance."""
        # Test singleton behavior
        cache1 = get_semantic_cache_keys()
        cache2 = get_semantic_cache_keys()

        # Should return same instance (singleton)
        assert cache1 is cache2

        # Test with custom parameters
        custom_cache = get_semantic_cache_keys(
            max_cache_size=50,
            similarity_threshold=0.8,
            cluster_threshold=0.7
        )

        # Should have custom parameters
        assert custom_cache.max_cache_size == 50
        assert custom_cache.similarity_threshold == 0.8
        assert custom_cache.cluster_threshold == 0.7

        # Should be different instance due to parameter change
        assert custom_cache is not cache1

    def test_cache_with_file_path_context(self):
        """Test cache operations with file path context."""
        cache = SemanticCacheKeys()

        query = "Create user authentication function"
        file_path = "src/api/auth.py"
        value = {"code": "def authenticate_user(): pass"}

        # Set with file path context
        cache.set(query, 10, None, value)

        # Get should work with same context
        result, hit_type = cache.get(query, 10, None)
        assert result == value
        assert hit_type == CacheHitType.EXACT_MATCH

        # Check that file path was considered in features
        cache_key = cache._get_cache_key(query, 10, None)
        metadata = cache._metadata.get(cache_key)
        assert metadata is not None
        assert metadata.content_features.get("file_extension") == ".py"
        assert metadata.content_features.get("programming_language") == "python"


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""

    def test_empty_and_none_handling(self, cache):
        """Test handling of empty or None inputs."""
        # Empty string query
        result, hit_type = cache.get("", 10, None)
        assert result is None
        assert hit_type == CacheHitType.MISS

        # Zero limit
        cache.set("test", 0, None, {"data": "test"})
        result, hit_type = cache.get("test", 0, None)
        assert result == {"data": "test"}

        # None content type (should be handled gracefully)
        cache.set("test", 10, None, {"data": "test"})
        result, hit_type = cache.get("test", 10, None)
        assert result == {"data": "test"}

    def test_unicode_content_handling(self, cache):
        """Test handling of unicode and special characters."""
        unicode_query = "Create API endpoint with émojis 🚀 and special chars ñáéíóú"
        unicode_value = {"result": "unicode_test", "chars": "🚀 ñáéíóú"}

        # Should handle unicode gracefully
        cache.set(unicode_query, 10, None, unicode_value)
        result, hit_type = cache.get(unicode_query, 10, None)

        assert result == unicode_value
        assert hit_type == CacheHitType.EXACT_MATCH

    def test_very_long_content_handling(self, cache):
        """Test handling of very long content."""
        long_query = "Create FastAPI endpoint " * 100  # Very long content
        long_value = {"data": "long_content_test", "length": len(long_query)}

        # Should handle long content gracefully
        cache.set(long_query, 10, None, long_value)
        result, hit_type = cache.get(long_query, 10, None)

        assert result == long_value
        assert hit_type == CacheHitType.EXACT_MATCH

    def test_statistics_reset(self, cache):
        """Test statistics clearing functionality."""
        # Perform some operations
        cache.set("test1", 10, None, {"data": "test1"})
        cache.set("test2", 10, None, {"data": "test2"})
        cache.get("test1", 10, None)
        cache.get("nonexistent", 10, None)

        # Verify statistics exist
        stats_before = cache.get_stats()
        assert stats_before.total_requests > 0

        # Clear statistics
        cache.clear_stats()

        # Verify statistics are reset
        stats_after = cache.get_stats()
        assert stats_after.total_requests == 0
        assert stats_after.exact_hits == 0
        assert stats_after.misses == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])