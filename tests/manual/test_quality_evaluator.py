#!/usr/bin/env .devstream/bin/python3
"""
Test script for RAG Quality Evaluator

Tests the Context7-Ragas inspired evaluation framework with sample memory entries
to verify all metrics work correctly with the DevStream memory system.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.devstream.memory.quality_evaluator import (
    RAGMetricsEvaluator,
    EvaluationQuery,
    EvaluationDataset,
    MetricType
)
from src.devstream.memory.storage import MemoryStorage
from src.devstream.memory.search import HybridSearchEngine
from src.devstream.memory.processing import TextProcessor
from src.devstream.memory.embedding_generator import EmbeddingConfig
from src.devstream.memory.models import MemoryEntry, ContentType
from src.devstream.database.connection import ConnectionPool
from src.devstream.database.sqlite_vec_manager import vec_manager
import structlog

logger = structlog.get_logger()


async def create_test_memory_entries(storage: MemoryStorage) -> list[MemoryEntry]:
    """Create test memory entries for evaluation."""

    test_entries = [
        MemoryEntry(
            id="test_memory_1",
            content="DevStream is a comprehensive memory system that integrates semantic vector search with keyword-based retrieval using sqlite-vec. It provides automatic embedding generation and supports hybrid search operations.",
            content_type=ContentType.DOCUMENTATION,
            keywords=["devstream", "memory", "vector search", "semantic", "hybrid search"],
            embedding_model="embeddinggemma"
        ),
        MemoryEntry(
            id="test_memory_2",
            content="The RAG Quality Evaluator implements Faithfulness, ContextPrecision, AnswerRelevancy, and ContextRecall metrics following Context7-Ragas best practices from 2025. It uses Ollama embeddinggemma:300m for semantic similarity calculations.",
            content_type=ContentType.DOCUMENTATION,
            keywords=["rag", "quality evaluator", "faithfulness", "context precision", "answer relevancy", "context recall"],
            embedding_model="embeddinggemma"
        ),
        MemoryEntry(
            id="test_memory_3",
            content="Vector embeddings are generated using Ollama's embeddinggemma model with 384 dimensions. The system supports batch processing and automatic retry logic for robust embedding generation.",
            content_type=ContentType.DOCUMENTATION,
            keywords=["embeddings", "ollama", "embeddinggemma", "batch processing", "384 dimensions"],
            embedding_model="embeddinggemma"
        ),
        MemoryEntry(
            id="test_memory_4",
            content="The memory system uses SQLite with sqlite-vec extension for efficient vector storage and retrieval. FTS5 provides full-text search capabilities for keyword-based queries.",
            content_type=ContentType.DOCUMENTATION,
            keywords=["sqlite", "sqlite-vec", "fts5", "vector storage", "full-text search"],
            embedding_model="embeddinggemma"
        ),
        MemoryEntry(
            id="test_memory_5",
            content="Context injection automatically retrieves relevant documentation from Context7 and DevStream memory to provide Claude with comprehensive background information before tool execution.",
            content_type=ContentType.DOCUMENTATION,
            keywords=["context injection", "context7", "devstream memory", "documentation retrieval", "claude"],
            embedding_model="embeddinggemma"
        )
    ]

    # Store test entries
    for entry in test_entries:
        try:
            await storage.store_memory(entry)
            logger.info(f"Stored test memory entry: {entry.id}")
        except Exception as e:
            logger.error(f"Failed to store test entry {entry.id}: {e}")

    return test_entries


async def test_quality_evaluator():
    """Test the RAG Quality Evaluator with sample data."""

    print("🚀 Starting RAG Quality Evaluator Test")
    print("=" * 50)

    # Initialize database connection
    db_path = "data/test_devstream.db"
    connection_pool = ConnectionPool(f"sqlite:///{db_path}")
    await connection_pool.initialize()

    try:
        # Initialize storage
        storage = MemoryStorage(connection_pool)
        await storage.create_virtual_tables()

        # Initialize text processor and search engine
        processor = TextProcessor()
        search_engine = HybridSearchEngine(storage, processor)

        # Initialize quality evaluator
        embedding_config = EmbeddingConfig(model_name="embeddinggemma")
        evaluator = RAGMetricsEvaluator(
            storage=storage,
            search_engine=search_engine,
            embedding_config=embedding_config
        )

        # Check evaluator status
        status = await evaluator.get_evaluation_status()
        print(f"Evaluator Status: {status}")
        print()

        # Create test memory entries
        print("📝 Creating test memory entries...")
        test_entries = await create_test_memory_entries(storage)
        print(f"Created {len(test_entries)} test entries")
        print()

        # Test Case 1: Basic Query Evaluation
        print("🔍 Test Case 1: Basic Query Evaluation")
        print("-" * 40)

        evaluation_query = EvaluationQuery(
            query_text="What is DevStream and how does it handle vector search?",
            ground_truth_answer="DevStream is a comprehensive memory system that integrates semantic vector search with keyword-based retrieval using sqlite-vec extension for SQLite.",
            retrieved_contexts=[
                "DevStream is a comprehensive memory system that integrates semantic vector search with keyword-based retrieval using sqlite-vec. It provides automatic embedding generation and supports hybrid search operations.",
                "The memory system uses SQLite with sqlite-vec extension for efficient vector storage and retrieval. FTS5 provides full-text search capabilities for keyword-based queries."
            ],
            generated_answer="DevStream is a memory system that uses sqlite-vec for vector search and FTS5 for keyword search, providing hybrid search capabilities with automatic embedding generation.",
            query_id="test_query_1"
        )

        # Evaluate all metrics for this query
        results = await evaluator.evaluate_query(evaluation_query)

        print("Results for Test Query 1:")
        for metric_name, result in results.items():
            print(f"  {metric_name}: {result.score:.3f}")
            if result.reasoning:
                print(f"    Reasoning: {result.reasoning[:100]}...")
            if result.error:
                print(f"    Error: {result.error}")
        print()

        # Test Case 2: Dataset Evaluation
        print("📊 Test Case 2: Dataset Evaluation")
        print("-" * 40)

        # Create evaluation dataset from memory system
        queries = [
            "What embedding model does DevStream use?",
            "How does the RAG Quality Evaluator work?",
            "What database technology is used for vector storage?",
            "What metrics are implemented in the quality evaluator?",
            "How does context injection work in DevStream?"
        ]

        ground_truth_answers = [
            "DevStream uses Ollama's embeddinggemma model with 384 dimensions for vector embeddings.",
            "The RAG Quality Evaluator implements Faithfulness, ContextPrecision, AnswerRelevancy, and ContextRecall metrics following Context7-Ragas best practices.",
            "DevStream uses SQLite with the sqlite-vec extension for efficient vector storage and retrieval.",
            "The quality evaluator implements Faithfulness, ContextPrecision, AnswerRelevancy, and ContextRecall metrics for RAG evaluation.",
            "Context injection automatically retrieves relevant documentation from Context7 and DevStream memory to provide comprehensive background information."
        ]

        # Create evaluation dataset
        dataset = await evaluator.create_evaluation_from_memory_system(
            queries=queries,
            ground_truth_answers=ground_truth_answers,
            max_contexts_per_query=3
        )

        print(f"Created evaluation dataset: {dataset.name}")
        print(f"Total queries: {len(dataset.queries)}")
        print(f"Description: {dataset.description}")
        print()

        # Evaluate dataset
        print("🎯 Running Dataset Evaluation...")
        start_time = time.time()

        report = await evaluator.evaluate_dataset(
            dataset=dataset,
            metrics=[MetricType.CONTEXT_PRECISION, MetricType.CONTEXT_RECALL],
            max_concurrent_evaluations=3
        )

        evaluation_time = time.time() - start_time

        print("📈 Evaluation Results:")
        print(f"  Overall Score: {report.overall_score:.3f}")
        print(f"  Context Precision: {report.context_precision_score:.3f}")
        print(f"  Context Recall: {report.context_recall_score:.3f}")
        print(f"  Success Rate: {report.successful_evaluations}/{report.total_queries}")
        print(f"  Total Time: {evaluation_time:.2f}s")
        print(f"  Avg Query Time: {report.average_query_time_ms:.2f}ms")
        print()

        # Test Case 3: Individual Metrics
        print("🧪 Test Case 3: Individual Metric Tests")
        print("-" * 40)

        # Test Faithfulness
        faith_result = await evaluator.evaluate_faithfulness(
            generated_answer="DevStream uses PostgreSQL for vector storage with pgvector extension.",
            retrieved_contexts=[
                "DevStream uses SQLite with sqlite-vec extension for efficient vector storage and retrieval.",
                "The system supports both semantic vector search and keyword-based retrieval."
            ]
        )
        print(f"Faithfulness Test: {faith_result.score:.3f}")
        if faith_result.reasoning:
            print(f"  {faith_result.reasoning[:150]}...")
        print()

        # Test Answer Relevancy
        relevancy_result = await evaluator.evaluate_answer_relevancy(
            query="What is the embedding dimension?",
            generated_answer="The system uses 384-dimensional embeddings generated by the embeddinggemma model."
        )
        print(f"Answer Relevancy Test: {relevancy_result.score:.3f}")
        if relevancy_result.reasoning:
            print(f"  {relevancy_result.reasoning[:150]}...")
        print()

        # Test Case 4: Error Handling
        print("⚠️  Test Case 4: Error Handling")
        print("-" * 40)

        # Test with empty contexts
        empty_context_result = await evaluator.evaluate_context_precision(
            query="test query",
            retrieved_contexts=[]
        )
        print(f"Empty Context Test: {empty_context_result.score:.3f} - {empty_context_result.reasoning}")

        # Test with missing generated answer
        missing_answer_query = EvaluationQuery(
            query_text="test query",
            ground_truth_answer="test answer",
            retrieved_contexts=["test context"],
            generated_answer=None  # Missing answer
        )
        missing_answer_results = await evaluator.evaluate_query(missing_answer_query, [MetricType.FAITHFULNESS])
        print(f"Missing Answer Test: {missing_answer_results['faithfulness'].score:.3f} - {missing_answer_results['faithfulness'].reasoning}")

        print()
        print("✅ All tests completed successfully!")
        print("=" * 50)

    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"❌ Test failed: {e}")
        return False

    finally:
        await connection_pool.close()

    return True


async def main():
    """Main test function."""
    print("RAG Quality Evaluator Test Suite")
    print("Testing Context7-Ragas inspired evaluation framework")
    print()

    success = await test_quality_evaluator()

    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())