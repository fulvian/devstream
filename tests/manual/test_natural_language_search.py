#!/usr/bin/env python3
"""
Natural Language Vector Search Quality Test Suite

Test comprehensivo per verificare la qualità e precisione della ricerca vettoriale
con query in linguaggio naturale usando il sistema DevStream Memory.
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


async def setup_test_environment():
    """Setup del database e memory manager per testing."""

    print("🔧 Setting up test environment...")

    # Initialize connection pool
    connection_pool = ConnectionPool(
        db_path="data/devstream.db",
        max_connections=5
    )
    await connection_pool.initialize()

    # Initialize memory manager
    memory_manager = MemoryManager(
        connection_pool=connection_pool,
        enable_quality_evaluator=True
    )
    await memory_manager.initialize()

    print("  ✅ Test environment initialized")
    return memory_manager


async def test_natural_language_queries(memory_manager):
    """Test query in linguaggio naturale per verificare semantic search."""

    print("\n🔍 Testing Natural Language Vector Search")
    print("=" * 60)

    # Query test per verificare la qualità della ricerca semantica
    test_queries = [
        {
            "query": "Come gestire gli errori in Python?",
            "expected_keywords": ["error", "except", "try", "exception"],
            "description": "Error handling in Italian"
        },
        {
            "query": "Python decorators explained simply",
            "expected_keywords": ["decorator", "function", "modify", "extend"],
            "description": "Python decorators explanation"
        },
        {
            "query": "What are Python lists and how to manipulate them?",
            "expected_keywords": ["list", "append", "extend", "methods"],
            "description": "Python list operations"
        },
        {
            "query": "Setting up isolated Python environments",
            "expected_keywords": ["virtual", "environment", "venv", "dependencies"],
            "description": "Virtual environments"
        },
        {
            "query": "Functional programming in Python",
            "expected_keywords": ["functional", "programming", "paradigms"],
            "description": "Functional programming concepts"
        }
    ]

    results = []

    for i, test_case in enumerate(test_queries, 1):
        print(f"\n📝 Query {i}: {test_case['description']}")
        print(f"   Query: \"{test_case['query']}\"")

        try:
            # Test search
            search_results = await memory_manager.search_memories(
                query_text=test_case['query'],
                max_results=5
            )

            print(f"   📊 Found {len(search_results)} results:")

            # Analizza qualità dei risultati
            relevance_scores = []
            keyword_matches = 0

            for j, result in enumerate(search_results, 1):
                content_preview = result.memory_entry.content[:100] + "..."
                score = result.combined_score if hasattr(result, 'combined_score') else getattr(result, 'score', 0.0)

                print(f"     {j}. Score: {score:.3f} | {content_preview}")

                # Verifica pertinenza con keyword attese
                content_lower = result.memory_entry.content.lower()
                keywords_found = sum(1 for kw in test_case['expected_keywords'] if kw in content_lower)

                if keywords_found > 0:
                    keyword_matches += 1

                relevance_scores.append(score)

            # Calcola metriche di qualità
            avg_score = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
            keyword_relevance = keyword_matches / len(search_results) if search_results else 0

            result_data = {
                "query": test_case['query'],
                "description": test_case['description'],
                "results_count": len(search_results),
                "avg_score": avg_score,
                "keyword_relevance": keyword_relevance,
                "expected_keywords": test_case['expected_keywords']
            }

            results.append(result_data)

            print(f"   📈 Quality Metrics:")
            print(f"      Average Score: {avg_score:.3f}")
            print(f"      Keyword Relevance: {keyword_relevance:.2%}")

        except Exception as e:
            print(f"   ❌ Query failed: {e}")
            results.append({
                "query": test_case['query'],
                "error": str(e),
                "results_count": 0,
                "avg_score": 0,
                "keyword_relevance": 0
            })

    return results


async def test_context_assembly_quality(memory_manager):
    """Test qualità del context assembly per diverse query."""

    print("\n📝 Testing Context Assembly Quality")
    print("=" * 60)

    context_test_queries = [
        "How to handle exceptions in Python programming?",
        "Explain Python decorators and their use cases",
        "Working with Python lists and common operations",
        "Managing Python project dependencies with venv"
    ]

    context_results = []

    for i, query in enumerate(context_test_queries, 1):
        print(f"\n🔧 Context Assembly Test {i}:")
        print(f"   Query: \"{query}\"")

        try:
            # Test context assembly con diversi token budgets
            for budget in [200, 500, 1000]:
                context_result = await memory_manager.assemble_context(
                    query_text=query,
                    token_budget=budget
                )

                print(f"     📊 Budget {budget} tokens:")
                print(f"        Used: {context_result.total_tokens} tokens")
                print(f"        Memories: {len(context_result.memory_entries)} entries")

                # Preview del context
                preview = context_result.assembled_context[:150] + "..."
                print(f"        Preview: {preview}")

            context_results.append({
                "query": query,
                "success": True
            })

        except Exception as e:
            print(f"     ❌ Context assembly failed: {e}")
            context_results.append({
                "query": query,
                "success": False,
                "error": str(e)
            })

    return context_results


async def test_rag_quality_metrics(memory_manager):
    """Test avanzati con metriche RAG per valutare qualità retrieval."""

    print("\n📊 Testing RAG Quality Metrics")
    print("=" * 60)

    # Test cases con ground truth answers
    quality_test_cases = [
        {
            "query": "How do you handle errors in Python?",
            "ground_truth": "Python uses try-except blocks for error handling. You can catch specific exceptions like ValueError or TypeError, and use finally blocks for cleanup code that always executes.",
            "generated_answer": "In Python, error handling is done with try-except blocks. The try block contains code that might raise an exception, and except blocks catch specific errors. A finally block can be used for cleanup."
        },
        {
            "query": "What are Python lists?",
            "ground_truth": "Python lists are ordered, mutable collections defined with square brackets. They can contain elements of different types and support methods like append(), extend(), remove(), and can be accessed using index notation.",
            "generated_answer": "Lists in Python are ordered collections that can be modified. They are created using square brackets and can hold different types of data. Common methods include append() for adding items and remove() for deleting items."
        }
    ]

    rag_results = []

    for i, test_case in enumerate(quality_test_cases, 1):
        print(f"\n🎯 RAG Quality Test {i}:")
        print(f"   Query: \"{test_case['query']}\"")

        try:
            # Valuta qualità con metriche RAG
            evaluation_result = await memory_manager.evaluate_query_quality(
                query=test_case['query'],
                ground_truth_answer=test_case['ground_truth'],
                generated_answer=test_case['generated_answer'],
                max_contexts=3,
                metrics=[MetricType.CONTEXT_PRECISION, MetricType.ANSWER_RELEVANCY, MetricType.CONTEXT_RECALL]
            )

            print(f"   📊 Quality Metrics Results:")
            print(f"      Retrieved Contexts: {evaluation_result['retrieved_contexts_count']}")

            for metric_name, result in evaluation_result['metrics'].items():
                score = result['score']
                reasoning = result.get('reasoning', 'N/A')

                print(f"      {metric_name}: {score:.3f}")
                if reasoning != 'N/A':
                    print(f"        Reasoning: {reasoning[:100]}...")

            rag_results.append({
                "query": test_case['query'],
                "context_precision": evaluation_result['metrics'].get('context_precision', {}).get('score', 0),
                "answer_relevancy": evaluation_result['metrics'].get('answer_relevancy', {}).get('score', 0),
                "context_recall": evaluation_result['metrics'].get('context_recall', {}).get('score', 0),
                "retrieved_contexts": evaluation_result['retrieved_contexts_count']
            })

        except Exception as e:
            print(f"   ❌ RAG evaluation failed: {e}")
            rag_results.append({
                "query": test_case['query'],
                "error": str(e),
                "context_precision": 0,
                "answer_relevancy": 0,
                "context_recall": 0
            })

    return rag_results


async def test_batch_evaluation_performance(memory_manager):
    """Test performance di batch evaluation per multiple queries."""

    print("\n⚡ Testing Batch Evaluation Performance")
    print("=" * 60)

    # Prepare batch test data
    batch_queries = [
        "Python error handling best practices",
        "Understanding decorators in Python",
        "Working with Python lists effectively",
        "Virtual environments for Python projects",
        "Functional programming concepts in Python"
    ]

    batch_ground_truth = [
        "Python provides try-except-else-finally blocks for comprehensive error handling, allowing specific exception catching and cleanup operations.",
        "Decorators are functions that modify other functions without changing their source code, using the @syntax for meta-programming.",
        "Python lists are mutable sequences supporting append, extend, remove, pop, and various other operations for data manipulation.",
        "Virtual environments create isolated Python environments with separate package installations using tools like venv.",
        "Functional programming in Python includes concepts like higher-order functions, lambda expressions, and immutable data structures."
    ]

    batch_answers = [
        "Error handling in Python uses try-except blocks to catch and manage exceptions gracefully.",
        "Decorators extend function behavior using the @decorator syntax without modifying the original function.",
        "Lists in Python are mutable collections that support various operations for adding and removing elements.",
        "Virtual environments help manage Python project dependencies in isolated spaces.",
        "Functional programming emphasizes using functions as first-class citizens in Python programming."
    ]

    print(f"   📊 Processing {len(batch_queries)} queries in batch...")

    start_time = time.time()

    try:
        # Esegui batch evaluation
        batch_report = await memory_manager.evaluate_batch_quality(
            queries=batch_queries,
            ground_truth_answers=batch_ground_truth,
            generated_answers=batch_answers,
            max_contexts=3,
            metrics=[MetricType.CONTEXT_PRECISION, MetricType.ANSWER_RELEVANCY]
        )

        execution_time = time.time() - start_time

        print(f"   ⏱️  Batch Performance:")
        print(f"      Total Queries: {batch_report.total_queries}")
        print(f"      Successful: {batch_report.successful_evaluations}")
        print(f"      Execution Time: {execution_time:.2f}s")
        print(f"      Avg Time per Query: {batch_report.average_query_time_ms:.0f}ms")
        print(f"      Overall Score: {batch_report.overall_score:.3f}")
        print(f"      Context Precision: {batch_report.context_precision_score:.3f}")
        print(f"      Answer Relevancy: {batch_report.answer_relevancy_score:.3f}")

        return {
            "success": True,
            "total_queries": batch_report.total_queries,
            "execution_time": execution_time,
            "avg_query_time_ms": batch_report.average_query_time_ms,
            "overall_score": batch_report.overall_score,
            "context_precision": batch_report.context_precision_score,
            "answer_relevancy": batch_report.answer_relevancy_score
        }

    except Exception as e:
        print(f"   ❌ Batch evaluation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "execution_time": time.time() - start_time
        }


async def generate_quality_report(search_results, context_results, rag_results, batch_results):
    """Genera report finale della qualità del sistema."""

    print("\n" + "=" * 60)
    print("📊 VECTOR SEARCH QUALITY REPORT")
    print("=" * 60)

    # Search Quality Summary
    successful_searches = [r for r in search_results if 'error' not in r]
    avg_search_score = sum(r['avg_score'] for r in successful_searches) / len(successful_searches) if successful_searches else 0
    avg_keyword_relevance = sum(r['keyword_relevance'] for r in successful_searches) / len(successful_searches) if successful_searches else 0

    print(f"\n🔍 SEARCH QUALITY SUMMARY:")
    print(f"   Total Queries Tested: {len(search_results)}")
    print(f"   Successful Searches: {len(successful_searches)}")
    print(f"   Average Search Score: {avg_search_score:.3f}")
    print(f"   Average Keyword Relevance: {avg_keyword_relevance:.2%}")

    # Context Assembly Summary
    successful_contexts = [r for r in context_results if r.get('success', False)]
    print(f"\n📝 CONTEXT ASSEMBLY SUMMARY:")
    print(f"   Total Context Tests: {len(context_results)}")
    print(f"   Successful Assemblies: {len(successful_contexts)}")
    print(f"   Success Rate: {len(successful_contexts)/len(context_results):.1%}")

    # RAG Quality Summary
    successful_rag = [r for r in rag_results if 'error' not in r]
    if successful_rag:
        avg_precision = sum(r['context_precision'] for r in successful_rag) / len(successful_rag)
        avg_relevancy = sum(r['answer_relevancy'] for r in successful_rag) / len(successful_rag)
        avg_recall = sum(r['context_recall'] for r in successful_rag) / len(successful_rag)

        print(f"\n📊 RAG QUALITY SUMMARY:")
        print(f"   Total RAG Tests: {len(rag_results)}")
        print(f"   Successful Evaluations: {len(successful_rag)}")
        print(f"   Average Context Precision: {avg_precision:.3f}")
        print(f"   Average Answer Relevancy: {avg_relevancy:.3f}")
        print(f"   Average Context Recall: {avg_recall:.3f}")

    # Batch Performance Summary
    if batch_results.get('success', False):
        print(f"\n⚡ BATCH PERFORMANCE SUMMARY:")
        print(f"   Batch Processing: ✅ SUCCESS")
        print(f"   Queries Processed: {batch_results['total_queries']}")
        print(f"   Total Execution Time: {batch_results['execution_time']:.2f}s")
        print(f"   Avg Query Time: {batch_results['avg_query_time_ms']:.0f}ms")
        print(f"   Overall Quality Score: {batch_results['overall_score']:.3f}")
    else:
        print(f"\n⚡ BATCH PERFORMANCE SUMMARY:")
        print(f"   Batch Processing: ❌ FAILED")
        print(f"   Error: {batch_results.get('error', 'Unknown error')}")

    # Overall Assessment
    print(f"\n🎯 OVERALL SYSTEM ASSESSMENT:")

    # Calculate overall quality score
    search_quality_score = min(avg_search_score * 100, 100)  # Normalize to 0-100
    context_quality_score = len(successful_contexts) / len(context_results) * 100
    rag_quality_score = 0
    if successful_rag:
        avg_precision = sum(r['context_precision'] for r in successful_rag) / len(successful_rag)
        rag_quality_score = avg_precision * 100

    overall_score = (search_quality_score + context_quality_score + rag_quality_score) / 3

    print(f"   Search Quality: {search_quality_score:.1f}/100")
    print(f"   Context Assembly: {context_quality_score:.1f}/100")
    print(f"   RAG Metrics: {rag_quality_score:.1f}/100")
    print(f"   OVERALL SCORE: {overall_score:.1f}/100")

    # Quality classification
    if overall_score >= 80:
        quality_grade = "🏆 EXCELLENT"
    elif overall_score >= 70:
        quality_grade = "✅ GOOD"
    elif overall_score >= 60:
        quality_grade = "⚠️  ACCEPTABLE"
    else:
        quality_grade = "❌ NEEDS IMPROVEMENT"

    print(f"   QUALITY GRADE: {quality_grade}")

    return overall_score


async def main():
    """Main test function."""

    print("🚀 Starting Natural Language Vector Search Quality Tests")
    print("=" * 60)

    memory_manager = None

    try:
        # Setup test environment
        memory_manager = await setup_test_environment()

        # Test 1: Natural Language Queries
        search_results = await test_natural_language_queries(memory_manager)

        # Test 2: Context Assembly Quality
        context_results = await test_context_assembly_quality(memory_manager)

        # Test 3: RAG Quality Metrics
        rag_results = await test_rag_quality_metrics(memory_manager)

        # Test 4: Batch Evaluation Performance
        batch_results = await test_batch_evaluation_performance(memory_manager)

        # Generate comprehensive quality report
        overall_score = await generate_quality_report(
            search_results, context_results, rag_results, batch_results
        )

        print(f"\n🎉 Vector Search Quality Testing Completed!")
        print(f"   Overall System Quality Score: {overall_score:.1f}/100")

    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        if memory_manager:
            print("\n🧹 Cleaning up...")
            try:
                await memory_manager.cleanup()
                print("  ✅ Memory manager cleaned up")
            except Exception as e:
                print(f"  ❌ Cleanup failed: {e}")


if __name__ == "__main__":
    # Run the comprehensive test suite
    asyncio.run(main())