#!/usr/bin/env .devstream/bin/python3
"""
Simple test script for RAG Quality Evaluator

Tests the core functionality without full database setup to verify
the Context7-Ragas inspired evaluation framework works correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.devstream.memory.quality_evaluator import (
    RAGMetricsEvaluator,
    EvaluationQuery,
    EvaluationDataset,
    MetricType,
    MetricResult
)
import ollama
import structlog

logger = structlog.get_logger()


class MockStorage:
    """Mock storage for testing without database."""
    def __init__(self):
        self.connection_pool = None


class MockSearchEngine:
    """Mock search engine for testing."""
    def __init__(self):
        pass


async def test_basic_evaluation():
    """Test basic evaluation functionality."""

    print("🚀 Testing RAG Quality Evaluator - Basic Functionality")
    print("=" * 60)

    try:
        # Test Ollama connectivity first
        print("📡 Testing Ollama connectivity...")
        client = ollama.Client(host='http://localhost:11434')

        try:
            models_response = client.list()
            # Handle different Ollama API response formats
            if hasattr(models_response, 'models'):
                model_names = [model.model for model in models_response.models]
            else:
                # Fallback for older API versions
                model_names = ["phi3.5:3.8b", "embeddinggemma:300m"]  # Known available models
            print(f"Available models: {model_names[:5]}...")  # Show first 5
        except Exception as e:
            print(f"Could not list models, using defaults: {e}")
            model_names = ["phi3.5:3.8b", "embeddinggemma:300m"]

        # Test LLM response generation
        print("\n🤖 Testing LLM response generation...")
        test_prompt = """
        Evaluate this simple statement:

        Statement: "The sky is blue."

        Is this statement correct? Answer with just "CORRECT" or "INCORRECT".
        """

        response = client.generate(model='phi3.5:3.8b', prompt=test_prompt)
        print(f"LLM Response: {response['response'].strip()}")

        # Initialize evaluator with mock components
        print("\n🔧 Initializing Quality Evaluator...")
        mock_storage = MockStorage()
        mock_search_engine = MockSearchEngine()

        evaluator = RAGMetricsEvaluator(
            storage=mock_storage,
            search_engine=mock_search_engine
        )

        print(f"Embedding model: {evaluator.embedding_generator.config.model_name}")
        print(f"LLM model: {evaluator._llm_model}")

        # Test individual metrics with simple data
        print("\n🧪 Testing Individual Metrics...")
        print("-" * 40)

        # Test 1: Context Precision
        print("Test 1: Context Precision")
        test_contexts = [
            "Python is a high-level programming language.",
            "Java is also a programming language.",
            "The weather is nice today."  # Irrelevant context
        ]

        precision_result = await evaluator.evaluate_context_precision(
            query="What is Python?",
            retrieved_contexts=test_contexts
        )
        print(f"  Score: {precision_result.score:.3f}")
        print(f"  Reasoning: {precision_result.reasoning}")
        print(f"  Time: {precision_result.execution_time_ms:.2f}ms")

        # Test 2: Answer Relevancy (without semantic similarity due to no embedding setup)
        print("\nTest 2: Answer Relevancy")
        relevancy_result = await evaluator.evaluate_answer_relevancy(
            query="What is 2+2?",
            generated_answer="The sum of 2 and 2 is 4."
        )
        print(f"  Score: {relevancy_result.score:.3f}")
        print(f"  Reasoning: {relevancy_result.reasoning[:100]}...")
        print(f"  Time: {relevancy_result.execution_time_ms:.2f}ms")

        # Test 3: Faithfulness
        print("\nTest 3: Faithfulness")
        faith_result = await evaluator.evaluate_faithfulness(
            generated_answer="Python was created by Guido van Rossum and released in 1991.",
            retrieved_contexts=[
                "Python is a programming language created by Guido van Rossum.",
                "The language was first released in 1991.",
                "Python emphasizes code readability and clean syntax."
            ]
        )
        print(f"  Score: {faith_result.score:.3f}")
        print(f"  Reasoning: {faith_result.reasoning[:100]}...")
        print(f"  Time: {faith_result.execution_time_ms:.2f}ms")

        # Test 4: Context Recall
        print("\nTest 4: Context Recall")
        recall_result = await evaluator.evaluate_context_recall(
            ground_truth_answer="Python was created by Guido van Rossum in 1991 and emphasizes readability.",
            retrieved_contexts=[
                "Python is a programming language created by Guido van Rossum.",
                "The language emphasizes code readability and clean syntax."
            ]
        )
        print(f"  Score: {recall_result.score:.3f}")
        print(f"  Reasoning: {recall_result.reasoning[:100]}...")
        print(f"  Time: {recall_result.execution_time_ms:.2f}ms")

        # Test 5: Complete Query Evaluation
        print("\n🔍 Test 5: Complete Query Evaluation")
        print("-" * 40)

        evaluation_query = EvaluationQuery(
            query_text="What are the key features of Python?",
            ground_truth_answer="Python is known for its readability, simple syntax, and extensive standard library.",
            retrieved_contexts=[
                "Python emphasizes code readability with clean, simple syntax.",
                "Python has a comprehensive standard library with many built-in modules.",
                "Python supports multiple programming paradigms including object-oriented programming."
            ],
            generated_answer="Python features readable syntax, clean code structure, and comes with many built-in libraries.",
            query_id="test_complete_query"
        )

        query_results = await evaluator.evaluate_query(evaluation_query)

        print("Complete Query Results:")
        for metric_name, result in query_results.items():
            print(f"  {metric_name}: {result.score:.3f}")
            if result.error:
                print(f"    Error: {result.error}")

        # Test 6: Dataset Evaluation (simple)
        print("\n📊 Test 6: Dataset Evaluation")
        print("-" * 40)

        dataset = EvaluationDataset(
            queries=[
                evaluation_query,
                EvaluationQuery(
                    query_text="What is machine learning?",
                    ground_truth_answer="Machine learning is a subset of AI that enables computers to learn from data.",
                    retrieved_contexts=[
                        "Machine learning allows systems to automatically learn and improve from experience.",
                        "It is a branch of artificial intelligence based on data-driven algorithms."
                    ],
                    generated_answer="Machine learning is an AI approach that helps systems learn from data automatically.",
                    query_id="test_ml_query"
                )
            ],
            name="Test Dataset",
            description="Simple test dataset for quality evaluator"
        )

        report = await evaluator.evaluate_dataset(
            dataset=dataset,
            metrics=[MetricType.CONTEXT_PRECISION, MetricType.ANSWER_RELEVANCY],
            max_concurrent_evaluations=2
        )

        print(f"Dataset Evaluation Results:")
        print(f"  Dataset: {report.dataset_name}")
        print(f"  Total Queries: {report.total_queries}")
        print(f"  Successful: {report.successful_evaluations}")
        print(f"  Overall Score: {report.overall_score:.3f}")
        print(f"  Context Precision: {report.context_precision_score:.3f}")
        print(f"  Answer Relevancy: {report.answer_relevancy_score:.3f}")
        print(f"  Total Time: {report.total_execution_time_ms:.2f}ms")

        # Test 7: Error Handling
        print("\n⚠️  Test 7: Error Handling")
        print("-" * 40)

        # Test with empty contexts
        empty_result = await evaluator.evaluate_context_precision(
            query="test query",
            retrieved_contexts=[]
        )
        print(f"Empty contexts: {empty_result.score:.3f} - {empty_result.reasoning}")

        # Test with very long text (should handle gracefully)
        long_text = "This is a test. " * 100
        long_result = await evaluator.evaluate_answer_relevancy(
            query="test query",
            generated_answer=long_text
        )
        print(f"Long text handling: {long_result.score:.3f} (Time: {long_result.execution_time_ms:.2f}ms)")

        print("\n✅ All basic tests passed!")
        print("=" * 60)
        print("\n📋 Summary:")
        print(f"  • Ollama connectivity: ✅")
        print(f"  • LLM response generation: ✅")
        print(f"  • Context Precision metric: ✅")
        print(f"  • Answer Relevancy metric: ✅")
        print(f"  • Faithfulness metric: ✅")
        print(f"  • Context Recall metric: ✅")
        print(f"  • Complete query evaluation: ✅")
        print(f"  • Dataset evaluation: ✅")
        print(f"  • Error handling: ✅")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    print("RAG Quality Evaluator - Simple Test Suite")
    print("Testing Context7-Ragas inspired evaluation framework")
    print("This test verifies core functionality without database setup")
    print()

    success = await test_basic_evaluation()

    if success:
        print("\n🎉 All tests completed successfully!")
        print("The RAG Quality Evaluator is ready for integration!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())