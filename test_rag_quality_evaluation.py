#!/usr/bin/env python3
"""
Test script for RAG Quality Evaluation Framework

Demonstrates the quality evaluation system using sample memory entries
and evaluates the implemented RAG metrics (Faithfulness, ContextPrecision,
AnswerRelevancy, ContextRecall).
"""

import asyncio
import json
import sys
import time
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from devstream.database.connection import ConnectionPool
from devstream.memory import MemoryManager, MetricType
from devstream.memory.models import MemoryEntry, ContentType


async def setup_test_memory_data(memory_manager: MemoryManager):
    """Create sample memory entries for testing."""

    # Sample memory entries representing a knowledge base about Python programming
    sample_memories = [
        {
            "content": "Python is a high-level, interpreted programming language known for its simple, readable syntax. It supports multiple programming paradigms including procedural, object-oriented, and functional programming.",
            "content_type": "documentation",
            "keywords": ["python", "programming", "high-level", "interpreted"]
        },
        {
            "content": "Lists in Python are ordered collections of items that can be modified. They are defined using square brackets [] and can contain elements of different types. Common operations include append(), extend(), and list comprehensions.",
            "content_type": "code",
            "keywords": ["python", "lists", "data-structures", "methods"]
        },
        {
            "content": "Python's exception handling uses try-except blocks to catch and handle errors. The finally block is always executed regardless of whether an exception occurred. Common exceptions include ValueError, TypeError, and IndexError.",
            "content_type": "documentation",
            "keywords": ["python", "exception-handling", "try-except", "errors"]
        },
        {
            "content": "Decorators in Python are a powerful feature that allows modifying or extending functions without changing their source code. They are defined using the @decorator_name syntax and are essentially functions that take other functions as arguments.",
            "content_type": "documentation",
            "keywords": ["python", "decorators", "functions", "metaprogramming"]
        },
        {
            "content": "Virtual environments in Python are isolated environments that allow managing package dependencies for different projects. The venv module is built into Python 3.3+ and allows creating lightweight virtual environments with 'python -m venv env_name'.",
            "content_type": "documentation",
            "keywords": ["python", "virtual-environments", "venv", "dependencies"]
        }
    ]

    print("📝 Creating sample memory entries...")

    memory_ids = []
    for i, memory_data in enumerate(sample_memories):
        memory_id = await memory_manager.store_memory_entry(
            content=memory_data["content"],
            content_type=memory_data["content_type"],
            keywords=memory_data["keywords"],
            complexity_score=3
        )
        memory_ids.append(memory_id)
        print(f"  ✅ Stored memory {i+1}: {memory_id}")

    print(f"📊 Created {len(memory_ids)} sample memory entries")
    return memory_ids


async def test_basic_functionality(memory_manager: MemoryManager):
    """Test basic memory system functionality."""

    print("\n🔍 Testing basic search functionality...")

    # Test search
    search_results = await memory_manager.search_memories(
        query_text="Python lists and methods",
        max_results=3
    )

    print(f"  📈 Found {len(search_results)} results for 'Python lists and methods'")
    for i, result in enumerate(search_results):
        print(f"    {i+1}. {result.memory_entry.content[:100]}...")
        print(f"       Score: {result.combined_score:.3f}")

    # Test context assembly
    context_result = await memory_manager.assemble_context(
        query_text="Python exception handling",
        token_budget=500
    )

    print(f"  📝 Assembled context: {context_result.total_tokens} tokens")
    print(f"     Used {len(context_result.memory_entries)} memory entries")
    print(f"     Context preview: {context_result.assembled_context[:200]}...")


async def test_single_query_evaluation(memory_manager: MemoryManager):
    """Test quality evaluation for a single query."""

    print("\n🎯 Testing single query quality evaluation...")

    query = "How do you handle errors in Python?"
    ground_truth = "Python handles errors using try-except blocks. You can catch specific exceptions like ValueError or TypeError, and use finally blocks for cleanup code."
    generated_answer = "In Python, you use try-except blocks for error handling. The try block contains code that might raise an exception, and except blocks catch specific errors. You can also use a finally block that always runs."

    try:
        evaluation_result = await memory_manager.evaluate_query_quality(
            query=query,
            ground_truth_answer=ground_truth,
            generated_answer=generated_answer,
            max_contexts=3,
            metrics=[MetricType.CONTEXT_PRECISION, MetricType.CONTEXT_RECALL]
        )

        print(f"  📊 Query: {query}")
        print(f"  🎯 Retrieved {evaluation_result['retrieved_contexts_count']} contexts")
        print(f"  📈 Metric Results:")

        for metric_name, result in evaluation_result['metrics'].items():
            print(f"    {metric_name}: {result['score']:.3f}")
            if result['reasoning']:
                print(f"      Reasoning: {result['reasoning'][:100]}...")
            if result['error']:
                print(f"      ⚠️  Error: {result['error']}")

        return evaluation_result

    except Exception as e:
        print(f"  ❌ Single query evaluation failed: {e}")
        return None


async def test_batch_evaluation(memory_manager: MemoryManager):
    """Test batch quality evaluation."""

    print("\n📊 Testing batch quality evaluation...")

    queries = [
        "What are Python lists and how do you use them?",
        "How do virtual environments work in Python?",
        "What are decorators in Python?"
    ]

    ground_truth_answers = [
        "Python lists are ordered, mutable collections defined with square brackets. They support methods like append(), extend(), remove(), and can be accessed using index notation. Lists can contain elements of different types.",
        "Virtual environments in Python are isolated environments that manage package dependencies separately for each project. Using venv, you can create isolated Python environments with their own package installations, preventing conflicts between projects.",
        "Decorators in Python are functions that modify or extend other functions without changing their source code. They use the @decorator syntax and are essentially higher-order functions that take a function as input and return a modified function."
    ]

    generated_answers = [
        "Python lists are collections that can hold multiple items. You create them with square brackets and can add or remove items using methods like append() and remove(). Lists keep their order and can contain different types of data.",
        "Virtual environments help isolate Python project dependencies. You create them with venv, and each environment gets its own Python interpreter and package installation directory. This prevents package conflicts between different projects.",
        "Decorators are special functions in Python that add functionality to other functions. You use the @ symbol before a function definition to apply a decorator. They're useful for logging, timing, and modifying function behavior."
    ]

    try:
        # Test with fewer metrics for faster execution
        evaluation_report = await memory_manager.evaluate_batch_quality(
            queries=queries,
            ground_truth_answers=ground_truth_answers,
            generated_answers=generated_answers,
            max_contexts=3,
            metrics=[MetricType.CONTEXT_PRECISION, MetricType.ANSWER_RELEVANCY]
        )

        print(f"  📊 Batch Evaluation Report:")
        print(f"    Dataset: {evaluation_report.dataset_name}")
        print(f"    Total Queries: {evaluation_report.total_queries}")
        print(f"    Successful: {evaluation_report.successful_evaluations}")
        print(f"    Overall Score: {evaluation_report.overall_score:.3f}")
        print(f"    Context Precision: {evaluation_report.context_precision_score:.3f}")
        print(f"    Answer Relevancy: {evaluation_report.answer_relevancy_score:.3f}")
        print(f"    Total Time: {evaluation_report.total_execution_time_ms:.0f}ms")
        print(f"    Avg Query Time: {evaluation_report.average_query_time_ms:.0f}ms")

        # Show per-query results
        print(f"  📈 Per-Query Results:")
        for i, query_result in enumerate(evaluation_report.query_results):
            print(f"    Query {i+1}: {queries[i][:50]}...")
            for metric_name, score in query_result['metrics'].items():
                print(f"      {metric_name}: {score:.3f}")

        return evaluation_report

    except Exception as e:
        print(f"  ❌ Batch evaluation failed: {e}")
        return None


async def test_system_status(memory_manager: MemoryManager):
    """Test system status functionality."""

    print("\n🔧 Testing system status...")

    try:
        status = await memory_manager.get_system_status()

        print(f"  📊 System Status:")
        print(f"    Storage: {'✅' if status['storage_initialized'] else '❌'}")
        print(f"    Search Engine: {'✅' if status['search_engine'] else '❌'}")
        print(f"    Context Assembler: {'✅' if status['context_assembler'] else '❌'}")

        # Embedding generator status
        embed_status = status['embedding_generator']
        print(f"    Embedding Generator:")
        print(f"      Model: {embed_status.get('model_name', 'unknown')}")
        print(f"      Available: {'✅' if embed_status.get('model_available') else '❌'}")

        # Quality evaluator status
        evaluator_status = status.get('quality_evaluator', {})
        if evaluator_status.get('enabled', False):
            print(f"    Quality Evaluator: ✅")
            print(f"      Embedding Model: {evaluator_status.get('embedding_model', 'unknown')}")
            print(f"      LLM Model: {evaluator_status.get('llm_model', 'unknown')}")
            print(f"      Ready: {'✅' if evaluator_status.get('evaluator_ready') else '❌'}")
        else:
            print(f"    Quality Evaluator: ❌ (disabled)")

        return status

    except Exception as e:
        print(f"  ❌ System status check failed: {e}")
        return None


async def main():
    """Main test function."""

    print("🚀 Starting RAG Quality Evaluation Framework Tests")
    print("=" * 60)

    # Initialize connection pool
    print("🔌 Initializing database connection...")
    try:
        connection_pool = ConnectionPool(
            db_path="data/devstream.db",
            max_connections=5
        )
        await connection_pool.initialize()
        print("  ✅ Database connection established")
    except Exception as e:
        print(f"  ❌ Failed to connect to database: {e}")
        return

    # Initialize memory manager
    print("🧠 Initializing memory manager...")
    try:
        memory_manager = MemoryManager(
            connection_pool=connection_pool,
            enable_quality_evaluator=True
        )
        await memory_manager.initialize()
        print("  ✅ Memory manager initialized")
    except Exception as e:
        print(f"  ❌ Failed to initialize memory manager: {e}")
        await connection_pool.close()
        return

    try:
        # Setup test data
        memory_ids = await setup_test_memory_data(memory_manager)

        # Test basic functionality
        await test_basic_functionality(memory_manager)

        # Test system status
        await test_system_status(memory_manager)

        # Test single query evaluation
        single_result = await test_single_query_evaluation(memory_manager)

        # Test batch evaluation
        batch_result = await test_batch_evaluation(memory_manager)

        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"  ✅ Sample memories created: {len(memory_ids)}")
        print(f"  {'✅' if single_result else '❌'} Single query evaluation")
        print(f"  {'✅' if batch_result else '❌'} Batch evaluation")

        if batch_result:
            print(f"  📈 Overall quality score: {batch_result.overall_score:.3f}")
            print(f"  ⏱️  Total evaluation time: {batch_result.total_execution_time_ms:.0f}ms")

        print("\n🎉 RAG Quality Evaluation Framework test completed!")

    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        try:
            await memory_manager.cleanup()
            print("  ✅ Memory manager cleaned up")
        except Exception as e:
            print(f"  ❌ Cleanup failed: {e}")


if __name__ == "__main__":
    # Run the test
    asyncio.run(main())