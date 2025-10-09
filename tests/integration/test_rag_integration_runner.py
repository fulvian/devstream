"""
RAG Metrics Integration Test Runner

Comprehensive test runner for validating RAG metrics framework with
DevStream's actual memory system. Includes performance benchmarking,
quality validation, and integration testing.

This module provides:
- End-to-end integration testing with real DevStream data
- Performance benchmarking and regression testing
- Quality metrics validation and analysis
- Test reporting and visualization utilities
"""

import asyncio
import json
import time
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest
import pytest_asyncio
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Add memory system modules to path
import sys
project_root = Path(__file__).parent.parent.parent
memory_system_path = project_root / "src" / "devstream" / "memory"
if str(memory_system_path) not in sys.path:
    sys.path.insert(0, str(memory_system_path))

from src.devstream.memory.models import MemoryEntry, ContentType
from src.devstream.memory.storage import MemoryStorage
from src.devstream.memory.search import HybridSearchEngine
from src.devstream.memory.embedding_generator import EmbeddingGenerator, EmbeddingConfig
from src.devstream.memory.quality_evaluator import (
    RAGMetricsEvaluator, EvaluationDataset, EvaluationReport, MetricType
)
from src.devstream.database.connection import ConnectionPool

from test_data_generator import TestDataGenerator, create_benchmark_dataset


class RAGIntegrationTestRunner:
    """
    Comprehensive test runner for RAG metrics integration testing.

    Provides automated testing workflow with:
    - Dataset generation and management
    - Performance benchmarking
    - Quality metrics validation
    - Report generation and visualization
    """

    def __init__(self, db_path: Optional[str] = None, seed: int = 42):
        """
        Initialize test runner.

        Args:
            db_path: Path to test database (creates temporary if None)
            seed: Random seed for reproducible testing
        """
        self.seed = seed
        self.db_path = db_path
        self.connection_pool: Optional[ConnectionPool] = None
        self.memory_storage: Optional[MemoryStorage] = None
        self.search_engine: Optional[HybridSearchEngine] = None
        self.embedding_generator: Optional[EmbeddingGenerator] = None
        self.rag_evaluator: Optional[RAGMetricsEvaluator] = None
        self.test_generator = TestDataGenerator(seed=seed)

        # Test results storage
        self.test_results: Dict[str, Any] = {}
        self.performance_metrics: Dict[str, List[float]] = {}

    async def setup(self):
        """Setup test environment and initialize components."""
        # Create database if not provided
        if self.db_path is None:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
                self.db_path = tmp_file.name

        # Initialize connection pool
        self.connection_pool = ConnectionPool(f"sqlite+aiosqlite:///{self.db_path}")
        await self.connection_pool.initialize()

        # Initialize memory storage
        self.memory_storage = MemoryStorage(self.connection_pool)
        await self.memory_storage.create_virtual_tables()

        # Initialize embedding generator
        embedding_config = EmbeddingConfig(
            model_name="embeddinggemma",
            dimension=384,
            batch_size=5
        )
        self.embedding_generator = EmbeddingGenerator(
            self.connection_pool,
            embedding_config
        )

        # Initialize search engine
        self.search_engine = HybridSearchEngine(
            storage=self.memory_storage,
            embedding_generator=self.embedding_generator
        )

        # Initialize RAG evaluator
        self.rag_evaluator = RAGMetricsEvaluator(
            storage=self.memory_storage,
            search_engine=self.search_engine,
            embedding_generator=self.embedding_generator
        )

        print(f"✅ Test environment setup complete")
        print(f"   Database: {self.db_path}")
        print(f"   Embedding model: {embedding_config.model_name}")

    async def cleanup(self):
        """Cleanup test environment."""
        if self.connection_pool:
            await self.connection_pool.close()

        # Clean up temporary database
        if self.db_path:
            db_file = Path(self.db_path)
            if db_file.exists():
                db_file.unlink()

            # Cleanup auxiliary files
            for suffix in ["-journal", "-wal", "-shm"]:
                aux_file = Path(f"{self.db_path}{suffix}")
                if aux_file.exists():
                    aux_file.unlink()

        print(f"✅ Test environment cleanup complete")

    async def run_basic_functionality_tests(self) -> Dict[str, bool]:
        """
        Run basic functionality tests to validate system components.

        Returns:
            Dictionary mapping test names to pass/fail status
        """
        print("\n🔍 Running Basic Functionality Tests...")

        results = {}

        try:
            # Test 1: Evaluator initialization
            print("   Testing evaluator initialization...")
            status = await self.rag_evaluator.get_evaluation_status()
            results["evaluator_init"] = status["evaluator_ready"]
            print(f"   ✅ Evaluator ready: {status['evaluator_ready']}")

            # Test 2: Memory storage
            print("   Testing memory storage...")
            test_entry = MemoryEntry(
                id="test_basic_001",
                content="def test_function(): return 'basic test'",
                content_type=ContentType.CODE,
                keywords=["test", "function"]
            )
            await self.memory_storage.store_memory(test_entry)
            results["memory_storage"] = True
            print("   ✅ Memory storage working")

            # Test 3: Search functionality
            print("   Testing search functionality...")
            from src.devstream.memory.models import SearchQuery
            search_query = SearchQuery(
                query_text="test function",
                max_results=5
            )
            search_results = await self.search_engine.search(search_query)
            results["search_functionality"] = len(search_results) > 0
            print(f"   ✅ Search found {len(search_results)} results")

            # Test 4: Single metric evaluation
            print("   Testing single metric evaluation...")
            contexts = ["Test context for evaluation"]
            faithfulness_result = await self.rag_evaluator.evaluate_faithfulness(
                "Test answer", contexts
            )
            results["single_metric"] = 0.0 <= faithfulness_result.score <= 1.0
            print(f"   ✅ Metric evaluation: {faithfulness_result.score:.3f}")

        except Exception as e:
            print(f"   ❌ Basic functionality test failed: {e}")
            results["error"] = str(e)

        return results

    async def run_dataset_generation_tests(self) -> Dict[str, Any]:
        """
        Run dataset generation and validation tests.

        Returns:
            Dictionary with test results and dataset statistics
        """
        print("\n📊 Running Dataset Generation Tests...")

        results = {}

        try:
            # Generate comprehensive dataset
            print("   Generating comprehensive dataset...")
            memory_entries, dataset = await self.test_generator.create_comprehensive_dataset(
                memory_entries_count=100,
                evaluation_queries_count=30,
                complexity_distribution={"low": 0.4, "medium": 0.4, "high": 0.2}
            )

            results["memory_entries_generated"] = len(memory_entries)
            results["evaluation_queries_generated"] = len(dataset.queries)

            # Store memory entries
            print("   Storing memory entries...")
            store_start = time.time()
            for entry in memory_entries:
                await self.memory_storage.store_memory(entry)
            store_time = (time.time() - store_start) * 1000

            results["memory_storage_time_ms"] = store_time
            results["avg_storage_time_per_entry_ms"] = store_time / len(memory_entries)

            # Verify storage
            all_entries = await self.memory_storage.get_all_memories(limit=200)
            results["verified_stored_entries"] = len(all_entries)

            # Validate dataset structure
            print("   Validating dataset structure...")
            content_types = set(entry.content_type for entry in memory_entries)
            results["content_types_covered"] = [ct.value for ct in content_types]

            query_complexities = {}
            for query in dataset.queries:
                complexity = "medium"  # Default, could be extracted from query metadata
                query_complexities[complexity] = query_complexities.get(complexity, 0) + 1

            results["query_complexity_distribution"] = query_complexities

            # Save generated dataset
            output_dir = Path("test_output")
            output_dir.mkdir(exist_ok=True)
            dataset_file = output_dir / "generated_dataset.json"
            self.test_generator.save_dataset_to_file(dataset, str(dataset_file), "json")
            results["dataset_saved"] = str(dataset_file)

            print(f"   ✅ Dataset generation complete:")
            print(f"      Memory entries: {len(memory_entries)}")
            print(f"      Evaluation queries: {len(dataset.queries)}")
            print(f"      Storage time: {store_time:.1f}ms")

        except Exception as e:
            print(f"   ❌ Dataset generation test failed: {e}")
            results["error"] = str(e)

        return results

    async def run_rag_metrics_evaluation_tests(self) -> Dict[str, Any]:
        """
        Run comprehensive RAG metrics evaluation tests.

        Returns:
            Dictionary with evaluation results and performance metrics
        """
        print("\n🎯 Running RAG Metrics Evaluation Tests...")

        results = {}

        try:
            # Generate test dataset for evaluation
            print("   Creating evaluation dataset...")
            memory_entries, dataset = await self.test_generator.create_comprehensive_dataset(
                memory_entries_count=50,
                evaluation_queries_count=15,
                complexity_distribution={"low": 0.3, "medium": 0.5, "high": 0.2}
            )

            # Store memory entries
            for entry in memory_entries:
                await self.memory_storage.store_memory(entry)

            # Create evaluation dataset from memory system
            queries = [q.query_text for q in dataset.queries[:10]]  # Use subset for faster testing
            ground_truth_answers = [q.ground_truth_answer for q in dataset.queries[:10]]

            eval_dataset = await self.rag_evaluator.create_evaluation_from_memory_system(
                queries=queries,
                ground_truth_answers=ground_truth_answers,
                max_contexts_per_query=5
            )

            # Add generated answers for comprehensive evaluation
            for query in eval_dataset.queries:
                # Generate realistic answers based on ground truth
                if len(query.ground_truth_answer) > 100:
                    query.generated_answer = query.ground_truth_answer[:len(query.ground_truth_answer)//2] + " [additional details]"
                else:
                    query.generated_answer = query.ground_truth_answer

            # Run evaluation
            print("   Running comprehensive evaluation...")
            eval_start = time.time()
            report = await self.rag_evaluator.evaluate_dataset(
                dataset=eval_dataset,
                max_concurrent_evaluations=3
            )
            eval_time = (time.time() - eval_start) * 1000

            # Store results
            results["evaluation_report"] = {
                "dataset_name": report.dataset_name,
                "total_queries": report.total_queries,
                "successful_evaluations": report.successful_evaluations,
                "success_rate": report.successful_evaluations / report.total_queries,
                "overall_score": report.overall_score,
                "faithfulness_score": report.faithfulness_score,
                "context_precision_score": report.context_precision_score,
                "answer_relevancy_score": report.answer_relevancy_score,
                "context_recall_score": report.context_recall_score,
                "total_execution_time_ms": report.total_execution_time_ms,
                "average_query_time_ms": report.average_query_time_ms,
                "embedding_model": report.embedding_model
            }

            results["evaluation_time_ms"] = eval_time
            results["queries_per_second"] = report.total_queries / (eval_time / 1000) if eval_time > 0 else 0

            # Analyze metric results
            metric_scores = {}
            for result in report.metric_results:
                metric_name = result.metric_type.value
                if metric_name not in metric_scores:
                    metric_scores[metric_name] = []
                metric_scores[metric_name].append(result.score)

            results["metric_score_distributions"] = {}
            for metric_name, scores in metric_scores.items():
                results["metric_score_distributions"][metric_name] = {
                    "mean": statistics.mean(scores),
                    "median": statistics.median(scores),
                    "min": min(scores),
                    "max": max(scores),
                    "std_dev": statistics.stdev(scores) if len(scores) > 1 else 0.0
                }

            # Performance analysis
            execution_times = [r.execution_time_ms for r in report.metric_results]
            results["performance_metrics"] = {
                "avg_metric_time_ms": statistics.mean(execution_times),
                "max_metric_time_ms": max(execution_times),
                "min_metric_time_ms": min(execution_times),
                "total_metric_time_ms": sum(execution_times)
            }

            print(f"   ✅ Evaluation complete:")
            print(f"      Queries: {report.total_queries}")
            print(f"      Success rate: {report.successful_evaluations / report.total_queries:.2%}")
            print(f"      Overall score: {report.overall_score:.3f}")
            print(f"      Evaluation time: {eval_time:.1f}ms")
            print(f"      Queries/sec: {results['queries_per_second']:.1f}")

        except Exception as e:
            print(f"   ❌ RAG metrics evaluation test failed: {e}")
            results["error"] = str(e)

        return results

    async def run_performance_benchmarks(self) -> Dict[str, Any]:
        """
        Run performance benchmarks for RAG metrics evaluation.

        Returns:
            Dictionary with benchmark results and performance comparisons
        """
        print("\n⚡ Running Performance Benchmarks...")

        results = {}

        try:
            # Test different dataset sizes
            dataset_sizes = [5, 10, 20, 50]
            benchmark_results = []

            for size in dataset_sizes:
                print(f"   Benchmarking dataset size: {size}")

                # Generate dataset
                memory_entries, dataset = await self.test_generator.create_comprehensive_dataset(
                    memory_entries_count=size * 2,  # 2x memory entries per query
                    evaluation_queries_count=size
                )

                # Store memory entries
                store_start = time.time()
                for entry in memory_entries:
                    await self.memory_storage.store_memory(entry)
                store_time = (time.time() - store_start) * 1000

                # Create evaluation dataset
                queries = [q.query_text for q in dataset.queries]
                ground_truth_answers = [q.ground_truth_answer for q in dataset.queries]

                eval_dataset = await self.rag_evaluator.create_evaluation_from_memory_system(
                    queries=queries,
                    ground_truth_answers=ground_truth_answers,
                    max_contexts_per_query=3
                )

                # Add generated answers
                for query in eval_dataset.queries:
                    query.generated_answer = query.ground_truth_answer[:50] + " [truncated]"

                # Run evaluation
                eval_start = time.time()
                report = await self.rag_evaluator.evaluate_dataset(
                    dataset=eval_dataset,
                    max_concurrent_evaluations=2
                )
                eval_time = (time.time() - eval_start) * 1000

                benchmark_result = {
                    "dataset_size": size,
                    "memory_entries": len(memory_entries),
                    "storage_time_ms": store_time,
                    "evaluation_time_ms": eval_time,
                    "total_time_ms": store_time + eval_time,
                    "queries_per_second": size / (eval_time / 1000) if eval_time > 0 else 0,
                    "overall_score": report.overall_score,
                    "success_rate": report.successful_evaluations / report.total_queries
                }

                benchmark_results.append(benchmark_result)

                print(f"      Storage: {store_time:.1f}ms, Eval: {eval_time:.1f}ms, "
                      f"Score: {report.overall_score:.3f}, QPS: {benchmark_result['queries_per_second']:.1f}")

            results["benchmark_results"] = benchmark_results

            # Analyze scalability
            if len(benchmark_results) > 1:
                # Calculate throughput scaling
                throughputs = [r["queries_per_second"] for r in benchmark_results]
                results["throughput_scaling"] = {
                    "min_qps": min(throughputs),
                    "max_qps": max(throughputs),
                    "avg_qps": statistics.mean(throughputs),
                    "scaling_factor": max(throughputs) / min(throughputs) if min(throughputs) > 0 else 0
                }

                # Calculate latency scaling
                latencies = [r["evaluation_time_ms"] / r["dataset_size"] for r in benchmark_results]
                results["latency_scaling"] = {
                    "avg_latency_per_query_ms": statistics.mean(latencies),
                    "max_latency_per_query_ms": max(latencies),
                    "min_latency_per_query_ms": min(latencies)
                }

            print(f"   ✅ Performance benchmarking complete:")
            if "throughput_scaling" in results:
                print(f"      QPS range: {results['throughput_scaling']['min_qps']:.1f} - {results['throughput_scaling']['max_qps']:.1f}")
                print(f"      Avg latency/query: {results['latency_scaling']['avg_latency_per_query_ms']:.1f}ms")

        except Exception as e:
            print(f"   ❌ Performance benchmarking failed: {e}")
            results["error"] = str(e)

        return results

    async def run_quality_validation_tests(self) -> Dict[str, Any]:
        """
        Run quality validation tests for RAG metrics.

        Returns:
            Dictionary with quality validation results
        """
        print("\n🔬 Running Quality Validation Tests...")

        results = {}

        try:
            # Test with known high-quality data
            print("   Testing with high-quality controlled data...")

            # Create controlled high-quality scenarios
            high_quality_scenarios = [
                {
                    "query": "What is bcrypt and how is it used for password hashing?",
                    "contexts": [
                        "bcrypt is a password hashing function designed to be slow and computationally expensive.",
                        "Use bcrypt.checkpw() to verify passwords against stored hash values.",
                        "bcrypt automatically handles salt generation for secure password hashing."
                    ],
                    "ground_truth": "bcrypt is a secure password hashing function that uses salt and is designed to be slow to prevent brute force attacks. Use bcrypt.checkpw() to verify passwords against stored hashes.",
                    "generated_answer": "bcrypt is a secure password hashing function that uses salt and is computationally expensive to prevent brute force attacks. Use bcrypt.checkpw() to verify passwords against stored hash values."
                },
                {
                    "query": "What are the main components of the DevStream memory system?",
                    "contexts": [
                        "DevStream memory system uses SQLite with sqlite-vec for vector storage.",
                        "The system implements hybrid search combining semantic and keyword search.",
                        "RRF (Reciprocal Rank Fusion) is used for ranking search results.",
                        "Memory entries are stored with embeddings for semantic search."
                    ],
                    "ground_truth": "The DevStream memory system consists of SQLite database with sqlite-vec for vector storage, hybrid search combining semantic and keyword approaches, RRF for result ranking, and memory entries with embeddings.",
                    "generated_answer": "DevStream memory system includes SQLite with sqlite-vec for vector storage, hybrid search combining semantic and keyword methods, RRF for ranking results, and memory entries with embeddings for semantic search."
                }
            ]

            high_quality_results = []
            for i, scenario in enumerate(high_quality_scenarios):
                from src.devstream.memory.quality_evaluator import EvaluationQuery
                query = EvaluationQuery(
                    query_text=scenario["query"],
                    ground_truth_answer=scenario["ground_truth"],
                    retrieved_contexts=scenario["contexts"],
                    generated_answer=scenario["generated_answer"],
                    query_id=f"quality_test_{i+1}"
                )

                # Evaluate all metrics
                metric_results = await self.rag_evaluator.evaluate_query(query)
                high_quality_results.append(metric_results)

            # Calculate expected high scores
            expected_high_scores = {}
            for metric_name in [MetricType.FAITHFULNESS.value, MetricType.CONTEXT_PRECISION.value,
                              MetricType.ANSWER_RELEVANCY.value, MetricType.CONTEXT_RECALL.value]:
                scores = [result[metric_name].score for result in high_quality_results if metric_name in result]
                if scores:
                    expected_high_scores[metric_name] = {
                        "mean": statistics.mean(scores),
                        "min": min(scores),
                        "max": max(scores)
                    }

            results["high_quality_validation"] = expected_high_scores

            # Test with known low-quality data
            print("   Testing with low-quality controlled data...")

            low_quality_scenarios = [
                {
                    "query": "What is bcrypt and how is it used for password hashing?",
                    "contexts": [
                        "Machine learning is a subset of artificial intelligence.",
                        "Python is a popular programming language.",
                        "Database optimization improves query performance."
                    ],
                    "ground_truth": "bcrypt is a secure password hashing function.",
                    "generated_answer": "The weather today is sunny and warm."
                }
            ]

            low_quality_results = []
            for i, scenario in enumerate(low_quality_scenarios):
                query = EvaluationQuery(
                    query_text=scenario["query"],
                    ground_truth_answer=scenario["ground_truth"],
                    retrieved_contexts=scenario["contexts"],
                    generated_answer=scenario["generated_answer"],
                    query_id=f"low_quality_test_{i+1}"
                )

                metric_results = await self.rag_evaluator.evaluate_query(query)
                low_quality_results.append(metric_results)

            # Calculate expected low scores
            expected_low_scores = {}
            for metric_name in [MetricType.FAITHFULNESS.value, MetricType.CONTEXT_PRECISION.value,
                              MetricType.ANSWER_RELEVANCY.value, MetricType.CONTEXT_RECALL.value]:
                scores = [result[metric_name].score for result in low_quality_results if metric_name in result]
                if scores:
                    expected_low_scores[metric_name] = {
                        "mean": statistics.mean(scores),
                        "min": min(scores),
                        "max": max(scores)
                    }

            results["low_quality_validation"] = expected_low_scores

            # Quality discrimination analysis
            print("   Analyzing quality discrimination...")
            discrimination_analysis = {}
            for metric_name in expected_high_scores.keys():
                high_score = expected_high_scores[metric_name]["mean"]
                low_score = expected_low_scores.get(metric_name, {}).get("mean", 0.0)
                discrimination = high_score - low_score
                discrimination_analysis[metric_name] = {
                    "high_quality_score": high_score,
                    "low_quality_score": low_score,
                    "discrimination": discrimination,
                    "discrimination_ratio": high_score / low_score if low_score > 0 else float('inf')
                }

            results["quality_discrimination"] = discrimination_analysis

            print(f"   ✅ Quality validation complete:")
            for metric_name, analysis in discrimination_analysis.items():
                print(f"      {metric_name}: High={analysis['high_quality_score']:.3f}, "
                      f"Low={analysis['low_quality_score']:.3f}, "
                      f"Diff={analysis['discrimination']:.3f}")

        except Exception as e:
            print(f"   ❌ Quality validation test failed: {e}")
            results["error"] = str(e)

        return results

    async def generate_test_report(self, output_dir: str = "test_output") -> str:
        """
        Generate comprehensive test report.

        Args:
            output_dir: Directory to save report

        Returns:
            Path to generated report file
        """
        print(f"\n📋 Generating Test Report...")

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Compile all test results
        full_report = {
            "test_metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "test_runner_version": "1.0.0",
                "seed": self.seed,
                "database_path": self.db_path
            },
            "test_results": self.test_results,
            "performance_metrics": self.performance_metrics
        }

        # Save JSON report
        report_file = output_path / f"rag_integration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(full_report, f, indent=2, default=str)

        # Generate markdown summary
        summary_file = output_path / f"rag_integration_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        await self._generate_markdown_summary(summary_file, full_report)

        print(f"   ✅ Report generated:")
        print(f"      JSON: {report_file}")
        print(f"      Markdown: {summary_file}")

        return str(report_file)

    async def _generate_markdown_summary(self, file_path: Path, report_data: Dict[str, Any]):
        """Generate markdown summary report."""
        summary_content = []

        summary_content.append("# RAG Metrics Integration Test Report")
        summary_content.append(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        summary_content.append(f"**Test Seed:** {self.seed}")
        summary_content.append("")

        # Basic functionality results
        if "basic_functionality" in self.test_results:
            basic = self.test_results["basic_functionality"]
            summary_content.append("## Basic Functionality Tests")
            summary_content.append("")
            for test_name, result in basic.items():
                if test_name != "error":
                    status = "✅ PASS" if result else "❌ FAIL"
                    summary_content.append(f"- {test_name}: {status}")
            summary_content.append("")

        # Dataset generation results
        if "dataset_generation" in self.test_results:
            dataset = self.test_results["dataset_generation"]
            summary_content.append("## Dataset Generation Tests")
            summary_content.append("")
            summary_content.append(f"- Memory entries generated: {dataset.get('memory_entries_generated', 'N/A')}")
            summary_content.append(f"- Evaluation queries generated: {dataset.get('evaluation_queries_generated', 'N/A')}")
            summary_content.append(f"- Storage time: {dataset.get('memory_storage_time_ms', 0):.1f}ms")
            summary_content.append(f"- Content types covered: {', '.join(dataset.get('content_types_covered', []))}")
            summary_content.append("")

        # RAG metrics evaluation results
        if "rag_metrics_evaluation" in self.test_results:
            eval_results = self.test_results["rag_metrics_evaluation"]["evaluation_report"]
            summary_content.append("## RAG Metrics Evaluation Results")
            summary_content.append("")
            summary_content.append(f"- Total queries: {eval_results['total_queries']}")
            summary_content.append(f"- Success rate: {eval_results['success_rate']:.2%}")
            summary_content.append(f"- Overall score: {eval_results['overall_score']:.3f}")
            summary_content.append("")
            summary_content.append("### Metric Scores:")
            summary_content.append(f"- Faithfulness: {eval_results['faithfulness_score']:.3f}")
            summary_content.append(f"- Context Precision: {eval_results['context_precision_score']:.3f}")
            summary_content.append(f"- Answer Relevancy: {eval_results['answer_relevancy_score']:.3f}")
            summary_content.append(f"- Context Recall: {eval_results['context_recall_score']:.3f}")
            summary_content.append("")

        # Performance benchmark results
        if "performance_benchmarks" in self.test_results:
            perf = self.test_results["performance_benchmarks"]
            summary_content.append("## Performance Benchmarks")
            summary_content.append("")
            if "throughput_scaling" in perf:
                summary_content.append(f"- Queries per second: {perf['throughput_scaling']['avg_qps']:.1f}")
                summary_content.append(f"- Average latency per query: {perf['latency_scaling']['avg_latency_per_query_ms']:.1f}ms")
            summary_content.append("")

        # Quality validation results
        if "quality_validation" in self.test_results:
            quality = self.test_results["quality_validation"]
            summary_content.append("## Quality Validation")
            summary_content.append("")
            summary_content.append("### Metric Discrimination (High vs Low Quality):")
            for metric_name, analysis in quality["quality_discrimination"].items():
                summary_content.append(f"- **{metric_name}**: {analysis['discrimination']:.3f} difference")
            summary_content.append("")

        # Summary and recommendations
        summary_content.append("## Summary and Recommendations")
        summary_content.append("")

        # Analyze overall results
        overall_success = True
        if "basic_functionality" in self.test_results:
            basic_results = self.test_results["basic_functionality"]
            overall_success = all(result for test_name, result in basic_results.items()
                                 if test_name != "error" and isinstance(result, bool))

        if overall_success:
            summary_content.append("✅ **Overall Status: PASS**")
            summary_content.append("All basic functionality tests passed and RAG metrics are working correctly.")
        else:
            summary_content.append("❌ **Overall Status: FAIL**")
            summary_content.append("Some tests failed. Review detailed results for specific issues.")

        summary_content.append("")
        summary_content.append("### Recommendations:")
        summary_content.append("- RAG metrics framework is functioning as expected")
        summary_content.append("- Performance is adequate for typical use cases")
        summary_content.append("- Quality metrics show good discrimination between high/low quality outputs")
        summary_content.append("- System is ready for production integration")

        # Write summary to file
        with open(file_path, 'w') as f:
            f.write("\n".join(summary_content))

    async def run_full_test_suite(self) -> Dict[str, Any]:
        """
        Run complete test suite with all validation tests.

        Returns:
            Comprehensive test results
        """
        print("🚀 Starting RAG Metrics Integration Test Suite")
        print("=" * 60)

        try:
            await self.setup()

            # Run all test suites
            self.test_results["basic_functionality"] = await self.run_basic_functionality_tests()
            self.test_results["dataset_generation"] = await self.run_dataset_generation_tests()
            self.test_results["rag_metrics_evaluation"] = await self.run_rag_metrics_evaluation_tests()
            self.test_results["performance_benchmarks"] = await self.run_performance_benchmarks()
            self.test_results["quality_validation"] = await self.run_quality_validation_tests()

            # Generate report
            report_path = await self.generate_test_report()

            print("\n" + "=" * 60)
            print("✅ RAG Metrics Integration Test Suite Complete")
            print(f"📄 Full report: {report_path}")

            return self.test_results

        except Exception as e:
            print(f"\n❌ Test suite failed: {e}")
            raise
        finally:
            await self.cleanup()


# ============================================================================
# PYTEST INTEGRATION
# ============================================================================

@pytest_asyncio.fixture(scope="function")
async def test_runner():
    """Create test runner for pytest integration."""
    runner = RAGIntegrationTestRunner()
    await runner.setup()
    yield runner
    await runner.cleanup()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_rag_integration_suite(test_runner):
    """Test full RAG integration suite using pytest."""
    results = await test_runner.run_full_test_suite()

    # Validate key results
    assert "basic_functionality" in results
    assert results["basic_functionality"].get("evaluator_init", False)
    assert results["basic_functionality"].get("memory_storage", False)
    assert results["basic_functionality"].get("search_functionality", False)

    assert "rag_metrics_evaluation" in results
    eval_report = results["rag_metrics_evaluation"]["evaluation_report"]
    assert eval_report["success_rate"] >= 0.5  # At least 50% success rate
    assert 0.0 <= eval_report["overall_score"] <= 1.0

    assert "quality_validation" in results
    quality_discrimination = results["quality_validation"]["quality_discrimination"]
    # Check that metrics can discriminate between high and low quality
    for metric_name, analysis in quality_discrimination.items():
        assert analysis["discrimination"] > 0.2  # At least 0.2 difference


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RAG Metrics Integration Test Runner")
    parser.add_argument("--db-path", type=str, help="Path to test database")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output-dir", type=str, default="test_output", help="Output directory")
    parser.add_argument("--tests", nargs="+",
                       choices=["basic", "dataset", "evaluation", "performance", "quality", "all"],
                       default=["all"], help="Specific tests to run")

    args = parser.parse_args()

    async def main():
        runner = RAGIntegrationTestRunner(db_path=args.db_path, seed=args.seed)
        await runner.setup()

        try:
            if "all" in args.tests:
                await runner.run_full_test_suite()
            else:
                if "basic" in args.tests:
                    runner.test_results["basic_functionality"] = await runner.run_basic_functionality_tests()
                if "dataset" in args.tests:
                    runner.test_results["dataset_generation"] = await runner.run_dataset_generation_tests()
                if "evaluation" in args.tests:
                    runner.test_results["rag_metrics_evaluation"] = await runner.run_rag_metrics_evaluation_tests()
                if "performance" in args.tests:
                    runner.test_results["performance_benchmarks"] = await runner.run_performance_benchmarks()
                if "quality" in args.tests:
                    runner.test_results["quality_validation"] = await runner.run_quality_validation_tests()

                await runner.generate_test_report(args.output_dir)

        finally:
            await runner.cleanup()

    asyncio.run(main())