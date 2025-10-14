"""
Comprehensive tests for TwoStageSearch system.

Tests validate the <100ms query time target vs 500ms baseline through binary quantization
and two-stage search optimization.
"""
import time
import pytest
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../.claude/hooks'))

from optimization.two_stage_search import (
    TwoStageSearch,
    get_two_stage_search,
    QuantizationType,
    SearchStage,
    QuantizedVector,
    SearchCandidate,
    SearchResults
)


class TestTwoStageSearch:
    """Test the main TwoStageSearch functionality."""

    @pytest.fixture
    def search_engine(self):
        """Create a two-stage search engine for testing."""
        return TwoStageSearch(
            vector_dimension=384,
            quantization_type=QuantizationType.BINARY,
            coarse_candidate_limit=50,
            fine_result_limit=10,
            similarity_threshold=0.7
        )

    def test_search_engine_initialization(self, search_engine):
        """Test search engine initialization with default parameters."""
        assert search_engine.vector_dimension == 384
        assert search_engine.quantization_type == QuantizationType.BINARY
        assert search_engine.coarse_candidate_limit == 50
        assert search_engine.fine_result_limit == 10
        assert search_engine.similarity_threshold == 0.7
        assert search_engine.enable_adaptive_limits is True

        # Check internal structures
        assert len(search_engine._vector_store) == 0
        assert len(search_engine._metadata_store) == 0
        assert len(search_engine._search_cache) == 0
        assert isinstance(search_engine._metrics, type(search_engine._metrics))

    def test_binary_quantization(self, search_engine):
        """Test binary quantization of vectors."""
        # Test vector
        vector = [0.5, -0.3, 0.8, -0.1, 0.9, -0.7] * 64  # 384 dimensions

        # Quantize vector
        quantized = search_engine.quantize_vector(vector)

        # Validate quantization
        assert isinstance(quantized, QuantizedVector)
        assert quantized.original_vector == vector
        assert quantized.quantization_type == QuantizationType.BINARY
        assert quantized.dimension == len(vector)
        assert quantized.compression_ratio == 32.0  # 32x compression for binary

        # Verify quantized data
        assert isinstance(quantized.quantized_data, bytes)
        assert len(quantized.quantized_data) > 0

    def test_vector_dequantization(self, search_engine):
        """Test vector dequantization."""
        # Test vector
        vector = [0.5, -0.3, 0.8, -0.1, 0.9, -0.7] * 64

        # Quantize and dequantize
        quantized = search_engine.quantize_vector(vector)
        dequantized = search_engine.dequantize_vector(quantized)

        # Validate dequantization
        assert isinstance(dequantized, list)
        assert len(dequantized) == len(vector)

        # Binary quantization should preserve sign information
        for original, recovered in zip(vector, dequantized):
            if original > 0:
                assert recovered > 0
            elif original < 0:
                assert recovered < 0

    def test_add_vector_to_index(self, search_engine):
        """Test adding vectors to the search index."""
        vector_id = "test_vector_1"
        vector = [0.1, 0.2, 0.3] * 128  # 384 dimensions
        metadata = {"type": "test", "source": "unittest"}

        # Add vector
        search_engine.add_vector(vector_id, vector, metadata)

        # Validate storage
        assert vector_id in search_engine._vector_store
        assert vector_id in search_engine._metadata_store
        assert search_engine._metadata_store[vector_id] == metadata

        # Validate quantized vector
        stored_quantized = search_engine._vector_store[vector_id]
        assert isinstance(stored_quantized, QuantizedVector)
        assert stored_quantized.original_vector == vector

    def test_binary_similarity_calculation(self, search_engine):
        """Test binary similarity calculation."""
        # Create test vectors
        vector1 = [0.5, -0.3, 0.8, -0.1] * 96
        vector2 = [0.4, -0.2, 0.7, -0.2] * 96  # Similar vector
        vector3 = [-0.5, 0.3, -0.8, 0.1] * 96  # Opposite vector

        # Quantize vectors
        q1 = search_engine.quantize_vector(vector1)
        q2 = search_engine.quantize_vector(vector2)
        q3 = search_engine.quantize_vector(vector3)

        # Calculate similarities
        sim_12 = search_engine._binary_similarity(q1.quantized_data, q2.quantized_data)
        sim_13 = search_engine._binary_similarity(q1.quantized_data, q3.quantized_data)
        sim_11 = search_engine._binary_similarity(q1.quantized_data, q1.quantized_data)

        # Validate similarity scores
        assert 0.0 <= sim_12 <= 1.0
        assert 0.0 <= sim_13 <= 1.0
        assert sim_11 == pytest.approx(1.0)  # Identical vectors

        # Similar vector should have higher similarity than opposite
        assert sim_12 > sim_13

    def test_cosine_similarity_calculation(self, search_engine):
        """Test cosine similarity calculation."""
        # Test vectors
        vector1 = [1.0, 0.0, 0.0]
        vector2 = [0.0, 1.0, 0.0]
        vector3 = [1.0, 0.0, 0.0]  # Same as vector1
        vector4 = [2.0, 0.0, 0.0]  # Same direction as vector1

        # Calculate similarities
        sim_12 = search_engine._cosine_similarity(vector1, vector2)
        sim_13 = search_engine._cosine_similarity(vector1, vector3)
        sim_14 = search_engine._cosine_similarity(vector1, vector4)

        # Validate similarities
        assert sim_12 == pytest.approx(0.0)  # Orthogonal vectors
        assert sim_13 == pytest.approx(1.0)  # Identical vectors
        assert sim_14 == pytest.approx(1.0)  # Same direction

    def test_coarse_filtering_stage(self, search_engine):
        """Test coarse filtering stage of two-stage search."""
        # Add test vectors to index
        for i in range(10):
            vector = [0.1 * i, 0.2 * i, 0.3 * i] * 128
            vector_id = f"vector_{i}"
            search_engine.add_vector(vector_id, vector)

        # Query vector similar to first few vectors
        query_vector = [0.05, 0.1, 0.15] * 128
        query_quantized = search_engine.quantize_vector(query_vector)

        # Perform coarse filtering
        candidates = search_engine._coarse_filter_search(
            query_vector,
            query_quantized,
            candidate_limit=5
        )

        # Validate results
        assert isinstance(candidates, list)
        assert len(candidates) <= 5
        assert len(candidates) >= 0

        # Check candidate structure
        for candidate in candidates:
            assert isinstance(candidate, SearchCandidate)
            assert candidate.id.startswith("vector_")
            assert candidate.source_stage == SearchStage.COARSE_FILTER
            assert 0.0 <= candidate.coarse_score <= 1.0

        # Candidates should be sorted by score
        if len(candidates) > 1:
            for i in range(len(candidates) - 1):
                assert candidates[i].coarse_score >= candidates[i + 1].coarse_score

    def test_fine_ranking_stage(self, search_engine):
        """Test fine re-ranking stage of two-stage search."""
        # Create test candidates
        candidates = []
        for i in range(5):
            vector = [0.1 * i, 0.2 * i, 0.3 * i] * 128
            quantized = search_engine.quantize_vector(vector)

            candidate = SearchCandidate(
                id=f"candidate_{i}",
                quantized_vector=quantized,
                coarse_score=0.8 - i * 0.1,
                metadata={"index": i}
            )
            candidates.append(candidate)

        # Query vector
        query_vector = [0.05, 0.1, 0.15] * 128

        # Perform fine ranking
        ranked_candidates = search_engine._fine_rank_search(query_vector, candidates)

        # Validate results
        assert len(ranked_candidates) == len(candidates)
        assert all(candidate.vector is not None for candidate in ranked_candidates)
        assert all(candidate.fine_score >= 0.0 for candidate in ranked_candidates)

        # Results should be sorted by fine score
        for i in range(len(ranked_candidates) - 1):
            assert ranked_candidates[i].fine_score >= ranked_candidates[i + 1].fine_score

    def test_full_two_stage_search(self, search_engine):
        """Test complete two-stage search process."""
        # Add test vectors to index
        test_data = [
            ("doc1", [0.9, 0.1, 0.05] * 128, {"type": "documentation"}),
            ("doc2", [0.8, 0.15, 0.1] * 128, {"type": "code"}),
            ("doc3", [0.1, 0.9, 0.05] * 128, {"type": "test"}),
            ("doc4", [0.05, 0.1, 0.9] * 128, {"type": "config"}),
            ("doc5", [-0.5, 0.3, 0.8] * 128, {"type": "misc"})
        ]

        for vector_id, vector, metadata in test_data:
            search_engine.add_vector(vector_id, vector, metadata)

        # Query vector similar to first two documents
        query_vector = [0.85, 0.12, 0.08] * 128

        # Perform search
        results = search_engine.search(query_vector, result_limit=3)

        # Validate results structure
        assert isinstance(results, SearchResults)
        assert results.quantization_used == QuantizationType.BINARY
        assert results.total_candidates >= 0
        assert len(results.candidates) <= 3
        assert results.coarse_time_ms > 0.0
        assert results.fine_time_ms > 0.0
        assert results.total_time_ms > 0.0

        # Validate performance target
        assert results.total_time_ms < 100.0, f"Search time {results.total_time_ms:.2f}ms exceeds 100ms target"

        # Check performance gain calculation
        assert results.performance_gain > 0.0

        # Validate top results
        top_results = results.top_results
        assert len(top_results) <= 3
        assert all(candidate.fine_score >= 0.0 for candidate in top_results)

        # Results should be sorted by fine score
        for i in range(len(top_results) - 1):
            assert top_results[i].fine_score >= top_results[i + 1].fine_score

    def test_adaptive_limit_selection(self, search_engine):
        """Test adaptive limit selection based on query characteristics."""
        base_coarse = 50
        base_fine = 10

        # Sparse query
        sparse_query = [0.0] * 380 + [1.0, 1.0, 1.0, 1.0]  # 4 non-zero elements
        coarse_limit, fine_limit = search_engine._adaptive_limit_selection(
            sparse_query, base_coarse, base_fine
        )
        assert coarse_limit > base_coarse  # Should increase for sparse queries
        assert fine_limit >= base_fine

        # Dense query with high magnitude
        dense_query = [10.0] * 384
        coarse_limit, fine_limit = search_engine._adaptive_limit_selection(
            dense_query, base_coarse, base_fine
        )
        assert coarse_limit < base_coarse  # Should decrease for high magnitude
        assert fine_limit <= base_fine

        # Normal query
        normal_query = [0.1, 0.2, 0.3] * 128
        coarse_limit, fine_limit = search_engine._adaptive_limit_selection(
            normal_query, base_coarse, base_fine
        )
        assert coarse_limit == base_coarse  # Should remain unchanged
        assert fine_limit == base_fine

    def test_search_caching(self, search_engine):
        """Test search result caching functionality."""
        # Add test vector
        vector_id = "cache_test"
        vector = [0.5, 0.3, 0.8] * 128
        search_engine.add_vector(vector_id, vector)

        query_vector = [0.4, 0.35, 0.75] * 128

        # First search (should cache result)
        start_time = time.time()
        results1 = search_engine.search(query_vector, use_cache=True)
        first_time = time.time() - start_time

        # Second search (should use cache)
        start_time = time.time()
        results2 = search_engine.search(query_vector, use_cache=True)
        second_time = time.time() - start_time

        # Results should be identical
        assert results1.query == results2.query
        assert len(results1.candidates) == len(results2.candidates)

        # Cached search should be faster
        assert second_time < first_time

    def test_performance_targets(self, search_engine):
        """Test performance targets are met."""
        # Performance target: <100ms total search time
        max_search_time = 100.0

        # Add test vectors
        for i in range(20):
            vector = [0.1 * (i % 5), 0.2 * (i % 3), 0.3 * (i % 7)] * 128
            vector_id = f"perf_test_{i}"
            search_engine.add_vector(vector_id, vector)

        # Test multiple searches
        search_times = []
        for i in range(10):
            query_vector = [0.1 * i, 0.2 * i, 0.3 * i] * 128

            start_time = time.time()
            results = search_engine.search(query_vector, use_cache=False)
            search_time = (time.time() - start_time) * 1000
            search_times.append(search_time)

            # Each search should meet target
            assert results.total_time_ms < max_search_time, f"Search {i} took {results.total_time_ms:.2f}ms"

        # Calculate average performance
        avg_time = sum(search_times) / len(search_times)

        assert avg_time < max_search_time, f"Average search time {avg_time:.2f}ms exceeds {max_search_time}ms target"

    def test_storage_statistics(self, search_engine):
        """Test storage statistics functionality."""
        # Initially empty
        stats = search_engine.get_storage_stats()
        assert stats['total_vectors'] == 0
        assert stats['storage_size_bytes'] == 0
        assert stats['quantization_type'] == QuantizationType.BINARY.value

        # Add some vectors
        for i in range(5):
            vector = [0.1 * i, 0.2 * i, 0.3 * i] * 128
            vector_id = f"stats_test_{i}"
            metadata = {"index": i, "type": "test"}
            search_engine.add_vector(vector_id, vector, metadata)

        # Check updated statistics
        stats = search_engine.get_storage_stats()
        assert stats['total_vectors'] == 5
        assert stats['storage_size_bytes'] > 0
        assert stats['avg_compression_ratio'] == 32.0  # Binary quantization
        assert stats['metadata_entries'] == 5
        assert stats['vector_dimension'] == 384

    def test_metrics_tracking(self, search_engine):
        """Test performance metrics tracking."""
        # Perform several searches to generate metrics
        for i in range(3):
            query_vector = [0.1 * i, 0.2 * i, 0.3 * i] * 128
            search_engine.search(query_vector, use_cache=False)

        # Get metrics
        metrics = search_engine.get_metrics()

        # Validate metrics structure
        assert metrics.total_searches >= 3
        assert metrics.avg_coarse_time_ms > 0.0
        assert metrics.avg_fine_time_ms > 0.0
        assert metrics.avg_total_time_ms > 0.0
        assert metrics.compression_efficiency > 0.0

        # Reset metrics
        search_engine.reset_metrics()
        reset_metrics = search_engine.get_metrics()

        # Should reset to defaults
        assert reset_metrics.total_searches == 0
        assert reset_metrics.avg_total_time_ms == 0.0

    def test_index_optimization(self, search_engine):
        """Test index optimization functionality."""
        # Add vectors with different quantization type initially
        old_quant_type = search_engine.quantization_type
        search_engine.quantization_type = QuantizationType.FLOAT32

        # Add a vector with old quantization
        vector = [0.5, 0.3, 0.8] * 128
        search_engine.add_vector("old_vector", vector)

        # Change quantization type and optimize
        search_engine.quantization_type = QuantizationType.BINARY
        optimization_results = search_engine.optimize_index()

        # Validate optimization results
        assert 'vectors_requantized' in optimization_results
        assert 'optimization_time_ms' in optimization_results
        assert 'total_vectors' in optimization_results
        assert optimization_results['vectors_requantized'] >= 0
        assert optimization_results['quantization_type'] == QuantizationType.BINARY.value

        # Check that vectors were re-quantized
        quantized_vector = search_engine._vector_store["old_vector"]
        assert quantized_vector.quantization_type == QuantizationType.BINARY

    def test_singleton_factory_function(self):
        """Test the factory function for getting search engine instance."""
        # Test singleton behavior
        engine1 = get_two_stage_search()
        engine2 = get_two_stage_search()

        # Should return same instance (singleton)
        assert engine1 is engine2

        # Test with custom parameters
        custom_engine = get_two_stage_search(
            vector_dimension=256,
            quantization_type=QuantizationType.INT8,
            coarse_candidate_limit=30
        )

        # Should have custom parameters
        assert custom_engine.vector_dimension == 256
        assert custom_engine.quantization_type == QuantizationType.INT8
        assert custom_engine.coarse_candidate_limit == 30

        # Should be different instance due to parameter change
        assert custom_engine is not engine1


class TestQuantizationTypes:
    """Test different quantization types."""

    def test_float32_quantization(self):
        """Test float32 quantization (no compression)."""
        engine = TwoStageSearch(
            vector_dimension=384,
            quantization_type=QuantizationType.FLOAT32
        )

        vector = [0.1, 0.2, 0.3] * 128
        quantized = engine.quantize_vector(vector)

        assert quantized.quantization_type == QuantizationType.FLOAT32
        assert quantized.compression_ratio == 1.0  # No compression

        # Dequantization should be lossless
        dequantized = engine.dequantize_vector(quantized)
        for original, recovered in zip(vector, dequantized):
            assert original == pytest.approx(recovered)

    def test_binary_quantization_compression(self):
        """Test binary quantization compression efficiency."""
        engine = TwoStageSearch(
            vector_dimension=384,
            quantization_type=QuantizationType.BINARY
        )

        vector = [0.1, 0.2, 0.3] * 128
        quantized = engine.quantize_vector(vector)

        assert quantized.compression_ratio == 32.0  # 32x compression

        # Binary should be much smaller than original
        original_size = len(vector) * 4  # 4 bytes per float32
        compressed_size = len(quantized.quantized_data)
        assert compressed_size < original_size / 10  # At least 10x smaller

    def test_int8_quantization_range(self):
        """Test int8 quantization preserves value ranges."""
        engine = TwoStageSearch(
            vector_dimension=384,
            quantization_type=QuantizationType.INT8
        )

        vector = [1.0, -1.0, 0.5, -0.5] * 96
        quantized = engine.quantize_vector(vector)
        dequantized = engine.dequantize_vector(quantized)

        # Should preserve sign information
        for original, recovered in zip(vector, dequantized):
            if original > 0:
                assert recovered > 0
            elif original < 0:
                assert recovered < 0

        # Should be within reasonable range
        assert all(-1.0 <= val <= 1.0 for val in dequantized)


class TestSearchPerformanceImprovement:
    """Test search performance improvement validation."""

    def test_baseline_vs_optimized_performance(self):
        """Test performance improvement from baseline to optimized search."""
        # Create optimized engine with binary quantization
        optimized_engine = TwoStageSearch(
            vector_dimension=384,
            quantization_type=QuantizationType.BINARY,
            coarse_candidate_limit=50,
            fine_result_limit=10
        )

        # Add test vectors
        for i in range(50):
            vector = [0.1 * (i % 10), 0.2 * (i % 5), 0.3 * (i % 7)] * 128
            vector_id = f"perf_vector_{i}"
            optimized_engine.add_vector(vector_id, vector)

        # Test query
        query_vector = [0.5, 0.3, 0.8] * 128

        # Measure optimized performance
        start_time = time.time()
        optimized_results = optimized_engine.search(query_vector, use_cache=False)
        optimized_time = (time.time() - start_time) * 1000

        # Validate performance target
        assert optimized_time < 100.0, f"Optimized search {optimized_time:.2f}ms exceeds 100ms target"

        # Calculate performance improvement vs 500ms baseline
        baseline_time = 500.0
        performance_improvement = ((baseline_time - optimized_time) / baseline_time) * 100

        assert performance_improvement > 80.0, f"Performance improvement {performance_improvement:.2f}% below 80% target"
        assert optimized_results.performance_gain > 80.0

        # Validate search quality
        assert len(optimized_results.candidates) > 0
        assert all(candidate.fine_score >= 0.0 for candidate in optimized_results.candidates)

    def test_compression_efficiency_validation(self):
        """Test quantization compression efficiency."""
        test_cases = [
            (QuantizationType.BINARY, 32.0),
            (QuantizationType.INT8, 4.0),
            (QuantizationType.FLOAT16, 2.0),
            (QuantizationType.FLOAT32, 1.0)
        ]

        for quant_type, expected_compression in test_cases:
            engine = TwoStageSearch(
                vector_dimension=384,
                quantization_type=quant_type
            )

            # Add test vectors
            for i in range(10):
                vector = [0.1 * i, 0.2 * i, 0.3 * i] * 128
                vector_id = f"compression_test_{i}"
                engine.add_vector(vector_id, vector)

            # Check storage statistics
            stats = engine.get_storage_stats()
            actual_compression = stats['avg_compression_ratio']

            assert actual_compression == pytest.approx(expected_compression, rel=0.1), \
                f"{quant_type.value} compression {actual_compression:.2f}x != expected {expected_compression:.2f}x"

    def test_search_accuracy_retention(self):
        """Test that quantization maintains search accuracy."""
        # Create engines with different quantization types
        engines = {
            'full_precision': TwoStageSearch(quantization_type=QuantizationType.FLOAT32),
            'binary': TwoStageSearch(quantization_type=QuantizationType.BINARY),
            'int8': TwoStageSearch(quantization_type=QuantizationType.INT8)
        }

        # Add same vectors to all engines
        test_vectors = []
        for i in range(20):
            vector = [0.1 * i, 0.2 * i, 0.3 * i] * 128
            vector_id = f"accuracy_test_{i}"
            test_vectors.append((vector_id, vector))

            for engine in engines.values():
                engine.add_vector(vector_id, vector)

        # Test queries
        test_queries = [
            [0.5, 0.3, 0.8] * 128,
            [0.1, 0.9, 0.2] * 128,
            [0.7, 0.1, 0.6] * 128
        ]

        # Compare results
        reference_results = {}
        for query_idx, query_vector in enumerate(test_queries):
            reference = engines['full_precision'].search(query_vector)
            reference_results[query_idx] = set(result.id for result in reference.candidates[:5])

        # Check accuracy retention
        for engine_name, engine in engines.items():
            if engine_name == 'full_precision':
                continue

            accuracy_scores = []
            for query_idx, query_vector in enumerate(test_queries):
                results = engine.search(query_vector)
                result_ids = set(result.id for result in results.candidates[:5])
                reference_ids = reference_results[query_idx]

                # Calculate overlap ratio
                if reference_ids:
                    overlap = len(result_ids.intersection(reference_ids)) / len(reference_ids)
                    accuracy_scores.append(overlap)

            if accuracy_scores:
                avg_accuracy = sum(accuracy_scores) / len(accuracy_scores)
                # Should maintain at least 85% accuracy
                assert avg_accuracy >= 0.85, f"{engine_name} accuracy {avg_accuracy:.2f} below 85% target"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])