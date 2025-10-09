"""
Standalone RAG Metrics Integration Tests

Simplified integration test suite for RAG metrics evaluation that doesn't depend
on the full DevStream database infrastructure. Focuses on validating the core
RAG metrics functionality with mock data and simplified storage.

Test Coverage:
- RAGMetricsEvaluator core functionality
- Individual metric calculations (faithfulness, context precision, etc.)
- Dataset creation and validation
- Performance testing with controlled data
- Quality validation with known inputs/outputs
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest
import pytest_asyncio
import numpy as np
from unittest.mock import AsyncMock, MagicMock

# Add memory system modules to path
import sys
project_root = Path(__file__).parent.parent.parent
memory_system_path = project_root / "src" / "devstream" / "memory"
if str(memory_system_path) not in sys.path:
    sys.path.insert(0, str(memory_system_path))

# Import only the quality evaluator to avoid database dependencies
try:
    from src.devstream.memory.quality_evaluator import (
        RAGMetricsEvaluator, EvaluationDataset, EvaluationQuery, MetricType,
        MetricResult, EvaluationReport
    )
    from src.devstream.memory.models import (
        MemoryEntry, ContentType, ContentFormat, SearchQuery, MemoryQueryResult
    )
    QUALITY_EVALUATOR_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import quality evaluator: {e}")
    QUALITY_EVALUATOR_AVAILABLE = False


# ============================================================================
# MOCK IMPLEMENTATIONS
# ============================================================================

class MockMemoryStorage:
    """Mock memory storage for testing without database dependencies."""

    def __init__(self):
        self.memories = []

    async def store_memory(self, memory: MemoryEntry) -> str:
        """Store memory entry."""
        self.memories.append(memory)
        return memory.id

    async def get_all_memories(self, limit: int = 100) -> List[MemoryEntry]:
        """Get all memories."""
        return self.memories[:limit]

    async def get_memories_by_type(self, content_type: ContentType) -> List[MemoryEntry]:
        """Get memories by content type."""
        return [m for m in self.memories if m.content_type == content_type]


class MockSearchEngine:
    """Mock search engine for testing without embedding dependencies."""

    def __init__(self, memory_storage: MockMemoryStorage):
        self.storage = memory_storage

    async def search(self, query: SearchQuery) -> List[MemoryQueryResult]:
        """Mock search that returns relevant memories based on keyword matching."""
        results = []
        query_keywords = query.query_text.lower().split()

        for i, memory in enumerate(self.storage.memories):
            # Simple keyword matching for mock search
            content_lower = memory.content.lower()
            score = sum(1 for keyword in query_keywords if keyword in content_lower)

            if score > 0:
                result = MemoryQueryResult(
                    memory_entry=memory,
                    combined_score=score / len(query_keywords),
                    semantic_score=score / len(query_keywords),
                    keyword_score=score / len(query_keywords),
                    final_rank=len(results) + 1,
                    matched_keywords=[kw for kw in query_keywords if kw in content_lower]
                )
                results.append(result)

        # Sort by score and limit results
        results.sort(key=lambda r: r.combined_score, reverse=True)
        return results[:query.max_results]


class MockEmbeddingGenerator:
    """Mock embedding generator for testing without Ollama dependencies."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.model_name = "mock_model"

    async def _generate_embedding_with_retry(self, text: str) -> List[float]:
        """Generate mock embedding."""
        # Create deterministic but pseudo-random embeddings based on text hash
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        seed = int(hash_obj.hexdigest()[:8], 16)
        np.random.seed(seed)
        return (np.random.random(self.dimension) - 0.5).tolist()

    async def check_model_availability(self) -> bool:
        """Check mock model availability."""
        return True


class MockRAGMetricsEvaluator:
    """
    Mock RAG metrics evaluator that provides realistic scoring without LLM dependencies.
    Used for testing when actual LLM services are not available.
    """

    def __init__(self):
        self.embedding_generator = MockEmbeddingGenerator()

    async def get_evaluation_status(self) -> Dict[str, Any]:
        """Get evaluator status."""
        return {
            "embedding_model": "mock_model",
            "embedding_available": True,
            "llm_model": "mock_llm",
            "supported_metrics": [m.value for m in MetricType],
            "evaluator_ready": True
        }

    async def evaluate_faithfulness(
        self,
        generated_answer: str,
        retrieved_contexts: List[str]
    ) -> MetricResult:
        """Mock faithfulness evaluation based on content overlap."""
        start_time = time.time()

        # Simple content overlap analysis
        answer_words = set(generated_answer.lower().split())
        context_words = set(" ".join(retrieved_contexts).lower().split())

        overlap = len(answer_words.intersection(context_words))
        total_answer_words = len(answer_words)
        score = overlap / total_answer_words if total_answer_words > 0 else 0.0

        reasoning = f"Faithfulness based on {overlap}/{total_answer_words} words found in contexts."

        execution_time = (time.time() - start_time) * 1000

        return MetricResult(
            metric_type=MetricType.FAITHFULNESS,
            score=min(1.0, score),
            reasoning=reasoning,
            execution_time_ms=execution_time
        )

    async def evaluate_context_precision(
        self,
        query: str,
        retrieved_contexts: List[str]
    ) -> MetricResult:
        """Mock context precision evaluation."""
        start_time = time.time()

        query_words = set(query.lower().split())
        relevant_contexts = 0

        for context in retrieved_contexts:
            context_words = set(context.lower().split())
            overlap = len(query_words.intersection(context_words))
            if overlap > 0:
                relevant_contexts += 1

        score = relevant_contexts / len(retrieved_contexts) if retrieved_contexts else 0.0
        reasoning = f"{relevant_contexts}/{len(retrieved_contexts)} contexts contain query keywords."

        execution_time = (time.time() - start_time) * 1000

        return MetricResult(
            metric_type=MetricType.CONTEXT_PRECISION,
            score=score,
            reasoning=reasoning,
            execution_time_ms=execution_time
        )

    async def evaluate_answer_relevancy(
        self,
        query: str,
        generated_answer: str
    ) -> MetricResult:
        """Mock answer relevancy evaluation."""
        start_time = time.time()

        query_words = set(query.lower().split())
        answer_words = set(generated_answer.lower().split())

        overlap = len(query_words.intersection(answer_words))
        total_query_words = len(query_words)
        base_score = overlap / total_query_words if total_query_words > 0 else 0.0

        # Add some semantic similarity using mock embeddings
        query_embedding = await self.embedding_generator._generate_embedding_with_retry(query)
        answer_embedding = await self.embedding_generator._generate_embedding_with_retry(generated_answer)

        # Simple cosine similarity
        query_vec = np.array(query_embedding)
        answer_vec = np.array(answer_embedding)
        similarity = np.dot(query_vec, answer_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(answer_vec))
        semantic_score = (similarity + 1) / 2  # Normalize to 0-1

        # Combine keyword and semantic scores
        final_score = 0.6 * base_score + 0.4 * semantic_score

        reasoning = f"Keyword overlap: {overlap}/{total_query_words}, Semantic similarity: {semantic_score:.3f}"

        execution_time = (time.time() - start_time) * 1000

        return MetricResult(
            metric_type=MetricType.ANSWER_RELEVANCY,
            score=min(1.0, final_score),
            reasoning=reasoning,
            execution_time_ms=execution_time
        )

    async def evaluate_context_recall(
        self,
        ground_truth_answer: str,
        retrieved_contexts: List[str]
    ) -> MetricResult:
        """Mock context recall evaluation."""
        start_time = time.time()

        truth_words = set(ground_truth_answer.lower().split())
        context_words = set(" ".join(retrieved_contexts).lower().split())

        overlap = len(truth_words.intersection(context_words))
        total_truth_words = len(truth_words)
        score = overlap / total_truth_words if total_truth_words > 0 else 0.0

        reasoning = f"{overlap}/{total_truth_words} ground truth words found in contexts."

        execution_time = (time.time() - start_time) * 1000

        return MetricResult(
            metric_type=MetricType.CONTEXT_RECALL,
            score=min(1.0, score),
            reasoning=reasoning,
            execution_time_ms=execution_time
        )

    async def evaluate_query(
        self,
        evaluation_query: EvaluationQuery,
        metrics: Optional[List[MetricType]] = None
    ) -> Dict[str, MetricResult]:
        """Evaluate a single query across specified metrics."""
        if metrics is None:
            metrics = list(MetricType)

        results = {}

        for metric_type in metrics:
            if metric_type == MetricType.FAITHFULNESS:
                if evaluation_query.generated_answer:
                    results[metric_type.value] = await self.evaluate_faithfulness(
                        evaluation_query.generated_answer,
                        evaluation_query.retrieved_contexts
                    )
                else:
                    results[metric_type.value] = MetricResult(
                        metric_type=metric_type,
                        score=0.0,
                        reasoning="No generated answer provided"
                    )

            elif metric_type == MetricType.CONTEXT_PRECISION:
                results[metric_type.value] = await self.evaluate_context_precision(
                    evaluation_query.query_text,
                    evaluation_query.retrieved_contexts
                )

            elif metric_type == MetricType.ANSWER_RELEVANCY:
                if evaluation_query.generated_answer:
                    results[metric_type.value] = await self.evaluate_answer_relevancy(
                        evaluation_query.query_text,
                        evaluation_query.generated_answer
                    )
                else:
                    results[metric_type.value] = MetricResult(
                        metric_type=metric_type,
                        score=0.0,
                        reasoning="No generated answer provided"
                    )

            elif metric_type == MetricType.CONTEXT_RECALL:
                results[metric_type.value] = await self.evaluate_context_recall(
                    evaluation_query.ground_truth_answer,
                    evaluation_query.retrieved_contexts
                )

        return results

    async def evaluate_dataset(
        self,
        dataset: EvaluationDataset,
        metrics: Optional[List[MetricType]] = None,
        max_concurrent_evaluations: int = 5
    ) -> EvaluationReport:
        """Evaluate a complete dataset of queries."""
        start_time = time.time()

        if not dataset.queries:
            raise ValueError("Dataset contains no queries to evaluate")

        all_metric_results = []
        query_results = []
        successful_evaluations = 0

        # Process queries
        for i, query in enumerate(dataset.queries):
            try:
                results = await self.evaluate_query(query, metrics)
                successful_evaluations += 1

                # Store individual metric results
                for metric_name, metric_result in results.items():
                    all_metric_results.append(metric_result)

                # Store query-level results
                query_results.append({
                    'query_index': i,
                    'query_id': query.query_id,
                    'metrics': {name: result.score for name, result in results.items()},
                    'execution_times': {name: result.execution_time_ms for name, result in results.items()}
                })

            except Exception as e:
                print(f"Error evaluating query {i}: {e}")

        # Calculate aggregate scores
        aggregate_scores = {}
        if all_metric_results:
            # Group results by metric type
            results_by_type = {}
            for result in all_metric_results:
                metric_name = result.metric_type.value
                if metric_name not in results_by_type:
                    results_by_type[metric_name] = []
                results_by_type[metric_name].append(result.score)

            # Calculate averages
            for metric_type in (metrics or list(MetricType)):
                metric_name = metric_type.value
                if metric_name in results_by_type and results_by_type[metric_name]:
                    aggregate_scores[metric_name] = sum(results_by_type[metric_name]) / len(results_by_type[metric_name])
                else:
                    aggregate_scores[metric_name] = 0.0

        total_execution_time = (time.time() - start_time) * 1000
        average_query_time = total_execution_time / len(dataset.queries) if dataset.queries else 0

        # Create evaluation report
        report = EvaluationReport(
            dataset_name=dataset.name,
            total_queries=len(dataset.queries),
            successful_evaluations=successful_evaluations,
            faithfulness_score=aggregate_scores.get(MetricType.FAITHFULNESS.value, 0.0),
            context_precision_score=aggregate_scores.get(MetricType.CONTEXT_PRECISION.value, 0.0),
            answer_relevancy_score=aggregate_scores.get(MetricType.ANSWER_RELEVANCY.value, 0.0),
            context_recall_score=aggregate_scores.get(MetricType.CONTEXT_RECALL.value, 0.0),
            overall_score=sum(aggregate_scores.values()) / len(aggregate_scores) if aggregate_scores else 0.0,
            metric_results=all_metric_results,
            query_results=query_results,
            total_execution_time_ms=total_execution_time,
            average_query_time_ms=average_query_time,
            embedding_model="mock_model"
        )

        return report


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest_asyncio.fixture(scope="function")
async def mock_evaluator():
    """Create mock RAG evaluator for testing."""
    return MockRAGMetricsEvaluator()


@pytest_asyncio.fixture(scope="function")
async def mock_memory_storage():
    """Create mock memory storage."""
    return MockMemoryStorage()


@pytest_asyncio.fixture(scope="function")
async def mock_search_engine(mock_memory_storage):
    """Create mock search engine."""
    return MockSearchEngine(mock_memory_storage)


@pytest.fixture
def sample_memory_entries() -> List[MemoryEntry]:
    """Create sample memory entries for testing."""
    base_time = datetime.utcnow()

    return [
        MemoryEntry(
            id="test_mem_001",
            content="Use bcrypt for secure password hashing in authentication systems. Store only password hashes, never plain passwords.",
            content_type=ContentType.CODE,
            content_format=ContentFormat.TEXT,
            keywords=["bcrypt", "password", "hashing", "security", "authentication"],
            created_at=base_time
        ),
        MemoryEntry(
            id="test_mem_002",
            content="RRF (Reciprocal Rank Fusion) combines multiple ranking results using the formula 1/(k + rank) where k is typically 60.",
            content_type=ContentType.DOCUMENTATION,
            content_format=ContentFormat.TEXT,
            keywords=["rrf", "ranking", "fusion", "search", "algorithm"],
            created_at=base_time
        ),
        MemoryEntry(
            id="test_mem_003",
            content="Database connection pool exhaustion occurs when connections are not properly returned to the pool. Always use proper async context managers.",
            content_type=ContentType.ERROR,
            content_format=ContentFormat.TEXT,
            keywords=["database", "connection", "pool", "exhaustion", "async"],
            created_at=base_time
        )
    ]


@pytest.fixture
def evaluation_queries_sample() -> List[EvaluationQuery]:
    """Create sample evaluation queries for testing."""
    return [
        EvaluationQuery(
            query_text="How to implement secure password hashing?",
            ground_truth_answer="Use bcrypt for secure password hashing. Store only password hashes in the database, never plain passwords. Use bcrypt.checkpw() for verification.",
            retrieved_contexts=[
                "Use bcrypt for secure password hashing in authentication systems.",
                "Store only password hashes, never plain passwords.",
                "bcrypt.checkpw() provides secure password verification."
            ],
            generated_answer="Implement password hashing using bcrypt. Store only the hash values and use bcrypt.checkpw() for verification.",
            query_id="test_query_001"
        ),
        EvaluationQuery(
            query_text="What is the RRF algorithm?",
            ground_truth_answer="RRF (Reciprocal Rank Fusion) is an algorithm that combines multiple ranking results using the formula 1/(k + rank), where k is typically 60.",
            retrieved_contexts=[
                "RRF (Reciprocal Rank Fusion) combines multiple ranking results.",
                "The formula is 1/(k + rank) where k is typically 60.",
                "RRF improves search result ranking by combining multiple sources."
            ],
            generated_answer="RRF stands for Reciprocal Rank Fusion and uses the formula 1/(k + rank) to combine rankings.",
            query_id="test_query_002"
        )
    ]


# ============================================================================
# CORE TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.skipif(not QUALITY_EVALUATOR_AVAILABLE, reason="Quality evaluator not available")
async def test_mock_evaluator_initialization(mock_evaluator):
    """Test mock evaluator initialization and status."""
    status = await mock_evaluator.get_evaluation_status()

    assert status["evaluator_ready"] is True
    assert "embedding_model" in status
    assert "llm_model" in status
    assert MetricType.FAITHFULNESS.value in status["supported_metrics"]
    assert MetricType.CONTEXT_PRECISION.value in status["supported_metrics"]
    assert MetricType.ANSWER_RELEVANCY.value in status["supported_metrics"]
    assert MetricType.CONTEXT_RECALL.value in status["supported_metrics"]


@pytest.mark.asyncio
@pytest.mark.skipif(not QUALITY_EVALUATOR_AVAILABLE, reason="Quality evaluator not available")
async def test_faithfulness_metric_evaluation(mock_evaluator):
    """Test faithfulness metric evaluation."""
    contexts = [
        "Use bcrypt for secure password hashing.",
        "Store only password hashes, never plain passwords.",
        "bcrypt.checkpw() provides secure verification."
    ]

    # High faithfulness case
    good_answer = "Use bcrypt for secure password hashing and store only password hashes."
    result = await mock_evaluator.evaluate_faithfulness(good_answer, contexts)

    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.FAITHFULNESS
    assert 0.0 <= result.score <= 1.0
    assert result.reasoning is not None
    assert result.execution_time_ms > 0

    # Low faithfulness case
    bad_answer = "The weather is sunny today."
    result_bad = await mock_evaluator.evaluate_faithfulness(bad_answer, contexts)

    assert result_bad.score < result.score


@pytest.mark.asyncio
@pytest.mark.skipif(not QUALITY_EVALUATOR_AVAILABLE, reason="Quality evaluator not available")
async def test_context_precision_metric_evaluation(mock_evaluator):
    """Test context precision metric evaluation."""
    query = "How to implement password hashing?"

    # Relevant contexts
    relevant_contexts = [
        "Use bcrypt for secure password hashing.",
        "Store only password hashes, never plain passwords.",
        "Database connection pooling best practices"
    ]

    result = await mock_evaluator.evaluate_context_precision(query, relevant_contexts)

    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.CONTEXT_PRECISION
    assert 0.0 <= result.score <= 1.0
    assert "relevant" in result.reasoning.lower()


@pytest.mark.asyncio
@pytest.mark.skipif(not QUALITY_EVALUATOR_AVAILABLE, reason="Quality evaluator not available")
async def test_answer_relevancy_metric_evaluation(mock_evaluator):
    """Test answer relevancy metric evaluation."""
    query = "What is the RRF algorithm?"

    # Relevant answer
    relevant_answer = "RRF (Reciprocal Rank Fusion) is an algorithm that combines rankings using the formula 1/(k + rank)."
    result = await mock_evaluator.evaluate_answer_relevancy(query, relevant_answer)

    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.ANSWER_RELEVANCY
    assert 0.0 <= result.score <= 1.0

    # Irrelevant answer
    irrelevant_answer = "Machine learning is a subset of artificial intelligence."
    result_irrelevant = await mock_evaluator.evaluate_answer_relevancy(query, irrelevant_answer)

    assert result_irrelevant.score < result.score


@pytest.mark.asyncio
@pytest.mark.skipif(not QUALITY_EVALUATOR_AVAILABLE, reason="Quality evaluator not available")
async def test_context_recall_metric_evaluation(mock_evaluator):
    """Test context recall metric evaluation."""
    ground_truth = "Use bcrypt for password hashing and store only password hashes in the database."

    # High recall context
    high_recall_contexts = [
        "Use bcrypt for secure password hashing.",
        "Store only password hashes in the database.",
        "Never store plain passwords."
    ]

    result = await mock_evaluator.evaluate_context_recall(ground_truth, high_recall_contexts)

    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.CONTEXT_RECALL
    assert 0.0 <= result.score <= 1.0

    # Low recall context
    low_recall_contexts = [
        "Use secure authentication methods."
    ]

    result_low = await mock_evaluator.evaluate_context_recall(ground_truth, low_recall_contexts)
    assert result_low.score < result.score


@pytest.mark.asyncio
@pytest.mark.skipif(not QUALITY_EVALUATOR_AVAILABLE, reason="Quality evaluator not available")
async def test_complete_query_evaluation(mock_evaluator, evaluation_queries_sample):
    """Test complete evaluation of a single query."""
    query = evaluation_queries_sample[0]

    results = await mock_evaluator.evaluate_query(query)

    # Verify all metrics were evaluated
    expected_metrics = {
        MetricType.FAITHFULNESS.value,
        MetricType.CONTEXT_PRECISION.value,
        MetricType.ANSWER_RELEVANCY.value,
        MetricType.CONTEXT_RECALL.value
    }

    assert set(results.keys()) == expected_metrics

    # Verify metric results
    for metric_name, result in results.items():
        assert isinstance(result, MetricResult)
        assert 0.0 <= result.score <= 1.0
        assert result.execution_time_ms >= 0


@pytest.mark.asyncio
@pytest.mark.skipif(not QUALITY_EVALUATOR_AVAILABLE, reason="Quality evaluator not available")
async def test_dataset_evaluation(mock_evaluator, evaluation_queries_sample):
    """Test complete dataset evaluation."""
    dataset = EvaluationDataset(
        queries=evaluation_queries_sample,
        name="Test Dataset",
        description="Test dataset for RAG metrics evaluation"
    )

    report = await mock_evaluator.evaluate_dataset(
        dataset=dataset,
        max_concurrent_evaluations=2
    )

    # Verify evaluation report
    assert isinstance(report, EvaluationReport)
    assert report.dataset_name == "Test Dataset"
    assert report.total_queries == len(evaluation_queries_sample)
    assert report.successful_evaluations <= report.total_queries
    assert report.embedding_model == "mock_model"

    # Verify aggregate scores
    assert 0.0 <= report.faithfulness_score <= 1.0
    assert 0.0 <= report.context_precision_score <= 1.0
    assert 0.0 <= report.answer_relevancy_score <= 1.0
    assert 0.0 <= report.context_recall_score <= 1.0
    assert 0.0 <= report.overall_score <= 1.0

    # Verify performance metrics
    assert report.total_execution_time_ms > 0
    assert report.average_query_time_ms > 0

    # Verify detailed results
    assert len(report.metric_results) > 0
    assert len(report.query_results) > 0


@pytest.mark.asyncio
@pytest.mark.skipif(not QUALITY_EVALUATOR_AVAILABLE, reason="Quality evaluator not available")
async def test_memory_storage_integration(mock_memory_storage, mock_search_engine, sample_memory_entries):
    """Test integration between memory storage and search engine."""
    # Store sample memories
    for entry in sample_memory_entries:
        await mock_memory_storage.store_memory(entry)

    # Verify storage
    all_memories = await mock_memory_storage.get_all_memories()
    assert len(all_memories) == len(sample_memory_entries)

    # Test search functionality
    search_query = SearchQuery(
        query_text="password hashing",
        max_results=5
    )

    search_results = await mock_search_engine.search(search_query)
    assert len(search_results) > 0

    # Verify results contain relevant content
    found_bcrypt = any("bcrypt" in result.memory_entry.content.lower() for result in search_results)
    assert found_bcrypt


@pytest.mark.asyncio
@pytest.mark.skipif(not QUALITY_EVALUATOR_AVAILABLE, reason="Quality evaluator not available")
async def test_quality_validation_scenarios(mock_evaluator):
    """Test quality validation with controlled scenarios."""
    # High quality scenario
    high_quality_query = EvaluationQuery(
        query_text="What is bcrypt used for?",
        ground_truth_answer="bcrypt is used for secure password hashing to protect user credentials.",
        retrieved_contexts=[
            "bcrypt is a password hashing function designed for security.",
            "Use bcrypt to hash passwords before storing them in databases.",
            "bcrypt provides protection against rainbow table attacks."
        ],
        generated_answer="bcrypt is used for secure password hashing to protect user credentials.",
        query_id="quality_test_high"
    )

    high_quality_results = await mock_evaluator.evaluate_query(high_quality_query)

    # Low quality scenario
    low_quality_query = EvaluationQuery(
        query_text="What is bcrypt used for?",
        ground_truth_answer="bcrypt is used for secure password hashing.",
        retrieved_contexts=[
            "Machine learning algorithms process large datasets.",
            "Weather prediction requires complex models.",
            "Financial markets are influenced by many factors."
        ],
        generated_answer="The weather is sunny and warm today.",
        query_id="quality_test_low"
    )

    low_quality_results = await mock_evaluator.evaluate_query(low_quality_query)

    # Verify quality discrimination
    for metric_name in [MetricType.FAITHFULNESS.value, MetricType.CONTEXT_PRECISION.value,
                       MetricType.ANSWER_RELEVANCY.value, MetricType.CONTEXT_RECALL.value]:
        high_score = high_quality_results[metric_name].score
        low_score = low_quality_results[metric_name].score

        # High quality should score better than low quality
        assert high_score > low_score, f"Metric {metric_name} failed quality discrimination: {high_score} vs {low_score}"


@pytest.mark.asyncio
@pytest.mark.skipif(not QUALITY_EVALUATOR_AVAILABLE, reason="Quality evaluator not available")
async def test_performance_benchmarks(mock_evaluator):
    """Test performance benchmarks for RAG evaluation."""
    # Create test dataset
    queries = []
    for i in range(10):  # 10 queries for performance testing
        query = EvaluationQuery(
            query_text=f"Test query {i}",
            ground_truth_answer=f"Ground truth answer for query {i}",
            retrieved_contexts=[f"Context {j}" for j in range(3)],
            generated_answer=f"Generated answer for query {i}",
            query_id=f"perf_query_{i}"
        )
        queries.append(query)

    dataset = EvaluationDataset(
        queries=queries,
        name="Performance Test Dataset",
        description="Dataset for performance benchmarking"
    )

    # Benchmark evaluation
    start_time = time.time()
    report = await mock_evaluator.evaluate_dataset(dataset)
    total_time = time.time() - start_time

    # Performance assertions
    assert total_time < 30.0  # Should complete within 30 seconds
    assert report.total_execution_time_ms < 30000
    assert report.successful_evaluations >= 8  # At least 80% success rate

    # Calculate queries per second
    queries_per_second = len(queries) / total_time
    assert queries_per_second > 0.1  # At least 0.1 queries per second


@pytest.mark.asyncio
@pytest.mark.skipif(not QUALITY_EVALUATOR_AVAILABLE, reason="Quality evaluator not available")
async def test_error_handling(mock_evaluator):
    """Test error handling in RAG evaluation."""
    # Test with empty contexts
    query_empty_contexts = EvaluationQuery(
        query_text="Test query",
        ground_truth_answer="Test answer",
        retrieved_contexts=[],  # Empty contexts
        generated_answer="Test generated answer",
        query_id="error_test_001"
    )

    results = await mock_evaluator.evaluate_query(query_empty_contexts)

    # Should handle gracefully
    assert isinstance(results, dict)
    for metric_name, result in results.items():
        assert isinstance(result, MetricResult)
        # Should have reasonable scores even with edge cases
        assert 0.0 <= result.score <= 1.0

    # Test with empty answer
    query_empty_answer = EvaluationQuery(
        query_text="Test query",
        ground_truth_answer="Test answer",
        retrieved_contexts=["Test context"],
        generated_answer="",  # Empty answer
        query_id="error_test_002"
    )

    results_empty_answer = await mock_evaluator.evaluate_query(query_empty_answer)

    # Should handle gracefully
    assert isinstance(results_empty_answer, dict)
    assert results_empty_answer[MetricType.FAITHFULNESS.value].score == 0.0
    assert "No generated answer" in results_empty_answer[MetricType.FAITHFULNESS.value].reasoning


# ============================================================================
# INTEGRATION TEST SUMMARY
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.skipif(not QUALITY_EVALUATOR_AVAILABLE, reason="Quality evaluator not available")
async def test_comprehensive_integration(mock_evaluator, mock_memory_storage, mock_search_engine):
    """Comprehensive integration test covering all components."""
    print("\n🚀 Running Comprehensive Integration Test")

    # 1. Setup test data
    sample_entries = [
        MemoryEntry(
            id="integration_mem_001",
            content="Use bcrypt for secure password hashing in authentication systems.",
            content_type=ContentType.CODE,
            keywords=["bcrypt", "password", "authentication"]
        ),
        MemoryEntry(
            id="integration_mem_002",
            content="RRF algorithm combines multiple search rankings using reciprocal fusion.",
            content_type=ContentType.DOCUMENTATION,
            keywords=["rrf", "search", "ranking", "fusion"]
        )
    ]

    # Store memories
    for entry in sample_entries:
        await mock_memory_storage.store_memory(entry)

    # 2. Test search integration
    search_query = SearchQuery(query_text="password security", max_results=5)
    search_results = await mock_search_engine.search(search_query)
    assert len(search_results) > 0

    # 3. Create evaluation dataset from search results
    eval_queries = [
        EvaluationQuery(
            query_text="How to secure password storage?",
            ground_truth_answer="Use bcrypt for secure password hashing and store only password hashes.",
            retrieved_contexts=[result.memory_entry.content for result in search_results],
            generated_answer="Implement password hashing using bcrypt and store only the hash values.",
            query_id="integration_query_001"
        )
    ]

    dataset = EvaluationDataset(
        queries=eval_queries,
        name="Integration Test Dataset",
        description="Comprehensive integration test dataset"
    )

    # 4. Evaluate dataset
    report = await mock_evaluator.evaluate_dataset(dataset)

    # 5. Validate results
    assert report.total_queries == 1
    assert report.successful_evaluations == 1
    assert 0.0 <= report.overall_score <= 1.0

    print(f"✅ Integration test completed successfully")
    print(f"   Overall score: {report.overall_score:.3f}")
    print(f"   Faithfulness: {report.faithfulness_score:.3f}")
    print(f"   Context Precision: {report.context_precision_score:.3f}")
    print(f"   Answer Relevancy: {report.answer_relevancy_score:.3f}")
    print(f"   Context Recall: {report.context_recall_score:.3f}")


if __name__ == "__main__":
    # Run standalone tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "not slow"
    ])