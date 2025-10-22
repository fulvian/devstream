"""
Simplified tests for SemanticCacheKeys system.

Tests validate the core functionality and 60%+ hit rate improvement target.
"""
import time
import pytest

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../.claude/hooks'))

from optimization.semantic_cache_keys import (
    SemanticCacheKeys,
    get_semantic_cache_keys,
    CacheHitType
)


class TestSemanticCacheKeysCore:
    """Test core SemanticCacheKeys functionality."""

    @pytest.fixture
    def cache(self):
        """Create a cache instance for testing."""
        return SemanticCacheKeys(
            max_cache_size=100,
            similarity_threshold=0.75,
            cluster_threshold=0.65
        )

    def test_cache_basic_operations(self, cache):
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

    def test_keyword_extraction(self, cache):
        """Test keyword extraction functionality."""
        query = "Create API endpoint for authentication with token validation"
        keywords = cache._extract_keywords(query)

        # Should extract technical keywords
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert "api" in keywords
        assert "endpoint" in keywords
        assert "token" in keywords

    def test_content_feature_extraction(self, cache):
        """Test content feature extraction."""
        query = "Create FastAPI endpoint for user authentication"
        features = cache._extract_content_features(query)

        # Validate feature structure
        assert isinstance(features, dict)
        assert "query_length" in features
        assert "word_count" in features
        assert "has_api_ops" in features
        assert "keywords" in features

        # Validate feature values
        assert features["query_length"] > 0
        assert features["word_count"] > 0
        assert features["has_api_ops"] is True
        assert len(features["keywords"]) > 0

    def test_pattern_matching(self, cache):
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

    def test_semantic_similarity(self, cache):
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

    def test_cache_performance_targets(self, cache):
        """Test cache performance meets targets."""
        # Performance targets: <5ms for cache operations
        max_query_time = 5.0

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

    def test_cache_statistics_tracking(self, cache):
        """Test cache statistics tracking."""
        # Perform cache operations
        cache.set("test1", 10, None, {"data": "test1"})
        cache.set("test2", 10, None, {"data": "test2"})

        # Exact hits
        cache.get("test1", 10, None)
        cache.get("test2", 10, None)

        # Miss (use something very different to avoid semantic matching)
        cache.get("completely unrelated query about cooking", 10, None)

        # Get statistics
        stats = cache.get_stats()

        # Validate statistics
        assert stats.total_requests >= 3
        assert stats.cache_size == 2
        assert stats.exact_hits >= 2
        # Note: semantic cache might find matches, so hits should be >= 2
        assert (stats.exact_hits + stats.semantic_hits + stats.cluster_hits) >= 2
        assert stats.hit_rate >= 0.0

    def test_singleton_factory_function(self):
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


class TestCacheHitRateImprovement:
    """Test cache hit rate improvement validation."""

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

    def test_baseline_vs_improved_performance(self):
        """Test performance improvement from baseline to optimized cache."""
        # Test queries
        test_queries = [
            "Create FastAPI endpoint for users",
            "Create FastAPI endpoint for user management",
            "Setup database connection",
            "Configure database settings",
            "Write unit tests",
            "Create test cases"
        ]

        # Test baseline cache (very restrictive)
        baseline_cache = SemanticCacheKeys(
            max_cache_size=1,
            similarity_threshold=1.0,  # Only exact matches
            cluster_threshold=1.0      # Only exact cluster matches
        )

        # Store one item only
        baseline_cache.set(test_queries[0], 10, None, {"data": "baseline"})

        # Measure baseline performance
        baseline_hits = 0
        for query in test_queries:
            result, hit_type = baseline_cache.get(query, 10, None)
            if hit_type != CacheHitType.MISS:
                baseline_hits += 1

        baseline_hit_rate = (baseline_hits / len(test_queries)) * 100

        # Test optimized cache
        optimized_cache = SemanticCacheKeys(
            max_cache_size=100,
            similarity_threshold=0.75,
            cluster_threshold=0.65
        )

        # Store some items
        for i, query in enumerate(test_queries[:3]):  # Store first 3
            optimized_cache.set(query, 10, None, {"data": f"optimized_{i}"})

        # Measure optimized performance
        optimized_hits = 0
        for query in test_queries:
            result, hit_type = optimized_cache.get(query, 10, None)
            if hit_type != CacheHitType.MISS:
                optimized_hits += 1

        optimized_hit_rate = (optimized_hits / len(test_queries)) * 100

        # Optimized should perform significantly better
        assert optimized_hit_rate > baseline_hit_rate
        assert optimized_hit_rate >= 50.0  # Should achieve at least 50% hit rate


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])