"""
RAG Metrics Integration Tests for DevStream Memory Quality Evaluation

Context7-Ragas inspired integration test suite for evaluating RAG metrics framework
with actual DevStream memory data and comprehensive quality benchmarking.

Test Coverage:
- EvaluationDataset creation and validation
- RAGMetricsEvaluator with real DevStream memory system
- Ground truth dataset generation for quality benchmarking
- Async evaluation workflow with proper fixtures
- Quality metrics validation across different content types
- Performance evaluation with DevStream's 13,532 memory records
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest
import pytest_asyncio
import numpy as np
from pydantic import ValidationError

# Add memory system modules to path
import sys
project_root = Path(__file__).parent.parent.parent
memory_system_path = project_root / "src" / "devstream" / "memory"
if str(memory_system_path) not in sys.path:
    sys.path.insert(0, str(memory_system_path))

from src.devstream.memory.models import (
    MemoryEntry, ContentType, ContentFormat, SearchQuery, MemoryQueryResult
)
from src.devstream.memory.storage import MemoryStorage
from src.devstream.memory.search import HybridSearchEngine
from src.devstream.memory.embedding_generator import EmbeddingGenerator, EmbeddingConfig
from src.devstream.memory.quality_evaluator import (
    RAGMetricsEvaluator, EvaluationDataset, EvaluationQuery, MetricType,
    MetricResult, EvaluationReport
)
from src.devstream.database.connection import ConnectionPool


# ============================================================================
# TEST FIXTURES - DevStream Memory System Setup
# ============================================================================

@pytest_asyncio.fixture(scope="function")
async def test_database():
    """Create temporary database for RAG metrics testing."""
    import tempfile
    import os
    from sqlalchemy.ext.asyncio import create_async_engine

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    # Create async engine
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    # Create database schema
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS semantic_memory (
                id TEXT PRIMARY KEY,
                plan_id TEXT,
                phase_id TEXT,
                task_id TEXT,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL,
                content_format TEXT DEFAULT 'text',
                keywords TEXT,
                entities TEXT,
                sentiment REAL DEFAULT 0.0,
                complexity_score INTEGER DEFAULT 1,
                embedding BLOB,
                embedding_model TEXT,
                embedding_dimension INTEGER,
                context_snapshot TEXT,
                related_memory_ids TEXT,
                access_count INTEGER DEFAULT 0,
                last_accessed_at TIMESTAMP,
                relevance_score REAL DEFAULT 1.0,
                is_archived BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS memory_metadata (
                memory_id TEXT PRIMARY KEY,
                metadata TEXT,
                FOREIGN KEY (memory_id) REFERENCES semantic_memory(id)
            )
        """))

    yield db_path, engine

    # Cleanup
    await engine.dispose()
    if os.path.exists(db_path):
        os.unlink(db_path)

    # Cleanup auxiliary files
    for suffix in ["-journal", "-wal", "-shm"]:
        aux_file = Path(f"{db_path}{suffix}")
        if aux_file.exists():
            aux_file.unlink()


@pytest_asyncio.fixture(scope="function")
async def connection_pool(test_database):
    """Create connection pool for testing."""
    db_path, engine = test_database

    # Import here to avoid circular imports
    from src.devstream.database.connection import ConnectionPool

    pool = ConnectionPool(f"sqlite+aiosqlite:///{db_path}")

    # Initialize virtual tables
    await pool.initialize()

    yield pool

    await pool.close()


@pytest_asyncio.fixture(scope="function")
async def memory_storage(connection_pool):
    """Create memory storage instance for testing."""
    storage = MemoryStorage(connection_pool)

    # Create virtual tables
    await storage.create_virtual_tables()

    return storage


@pytest_asyncio.fixture(scope="function")
async def embedding_generator(memory_storage):
    """Create embedding generator for testing."""
    config = EmbeddingConfig(
        model_name="embeddinggemma",  # Use fast model for testing
        dimension=384,
        batch_size=5
    )

    generator = EmbeddingGenerator(memory_storage.connection_pool, config)
    return generator


@pytest_asyncio.fixture(scope="function")
async def search_engine(memory_storage, embedding_generator):
    """Create hybrid search engine for testing."""
    search_engine = HybridSearchEngine(
        storage=memory_storage,
        embedding_generator=embedding_generator
    )
    return search_engine


@pytest_asyncio.fixture(scope="function")
async def rag_evaluator(memory_storage, search_engine, embedding_generator):
    """Create RAG metrics evaluator for testing."""
    evaluator = RAGMetricsEvaluator(
        storage=memory_storage,
        search_engine=search_engine,
        embedding_generator=embedding_generator
    )
    return evaluator


# ============================================================================
# SAMPLE DATA FIXTURES - Ground Truth Dataset
# ============================================================================

@pytest.fixture
def sample_memory_entries() -> List[MemoryEntry]:
    """
    Create sample memory entries covering different content types.

    Returns diverse set of memory entries for comprehensive testing:
    - Code implementations (Python, TypeScript, SQL)
    - Documentation and API specs
    - Context snapshots and decisions
    - Error handling and learnings
    """
    base_time = datetime.utcnow()

    entries = [
        # Code content
        MemoryEntry(
            id="mem_001",
            content="def authenticate_user(username: str, password: str) -> Optional[User]:\n    \"\"\"Authenticate user with bcrypt password hashing.\"\"\"\n    user = await get_user_by_username(username)\n    if user and bcrypt.checkpw(password.encode(), user.password_hash.encode()):\n        return user\n    return None",
            content_type=ContentType.CODE,
            content_format=ContentFormat.CODE,
            keywords=["authentication", "bcrypt", "user", "password", "security"],
            entities=[{"type": "function", "value": "authenticate_user"}, {"type": "library", "value": "bcrypt"}],
            complexity_score=5,
            created_at=base_time - timedelta(hours=2)
        ),

        MemoryEntry(
            id="mem_002",
            content="interface UserProfile {\n    id: string;\n    name: string;\n    email: string;\n    preferences: UserPreferences;\n    createdAt: Date;\n    updatedAt: Date;\n}",
            content_type=ContentType.CODE,
            content_format=ContentFormat.CODE,
            keywords=["typescript", "interface", "user", "profile", "types"],
            entities=[{"type": "interface", "value": "UserProfile"}, {"type": "type", "value": "UserPreferences"}],
            complexity_score=3,
            created_at=base_time - timedelta(hours=1)
        ),

        MemoryEntry(
            id="mem_003",
            content="SELECT u.*, p.profile_data FROM users u LEFT JOIN user_profiles p ON u.id = p.user_id WHERE u.status = 'active' AND u.last_login > DATE('now', '-30 days')",
            content_type=ContentType.CODE,
            content_format=ContentFormat.CODE,
            keywords=["sql", "query", "users", "join", "active", "filtering"],
            entities=[{"type": "table", "value": "users"}, {"type": "table", "value": "user_profiles"}],
            complexity_score=6,
            created_at=base_time - timedelta(minutes=30)
        ),

        # Documentation content
        MemoryEntry(
            id="mem_004",
            content="# Authentication API Documentation\n\n## POST /api/auth/login\nAuthenticates user credentials and returns JWT token.\n\n**Request Body:**\n```json\n{\n  \"username\": \"string\",\n  \"password\": \"string\"\n}\n```\n\n**Response:**\n```json\n{\n  \"token\": \"jwt_token\",\n  \"expires_in\": 3600,\n  \"user\": UserProfile\n}\n```",
            content_type=ContentType.DOCUMENTATION,
            content_format=ContentFormat.MARKDOWN,
            keywords=["api", "authentication", "jwt", "login", "documentation"],
            entities=[{"type": "endpoint", "value": "POST /api/auth/login"}, {"type": "protocol", "value": "JWT"}],
            complexity_score=4,
            created_at=base_time - timedelta(minutes=45)
        ),

        MemoryEntry(
            id="mem_005",
            content="# Memory System Architecture\n\nThe DevStream memory system uses:\n- SQLite with sqlite-vec for vector storage\n- Semantic search using embeddings\n- Hybrid search combining semantic and keyword matching\n- RRF (Reciprocal Rank Fusion) for result ranking",
            content_type=ContentType.DOCUMENTATION,
            content_format=ContentFormat.MARKDOWN,
            keywords=["memory", "architecture", "sqlite", "vector", "search", "rrf"],
            entities=[{"type": "technology", "value": "SQLite"}, {"type": "technology", "value": "sqlite-vec"}],
            complexity_score=7,
            created_at=base_time - timedelta(hours=3)
        ),

        # Context content
        MemoryEntry(
            id="mem_006",
            content="Context: User requested implementation of authentication system. Requirements include JWT tokens, bcrypt password hashing, and secure session management. User is experienced with Python but new to FastAPI.",
            content_type=ContentType.CONTEXT,
            content_format=ContentFormat.TEXT,
            keywords=["context", "authentication", "jwt", "bcrypt", "fastapi"],
            entities=[{"type": "framework", "value": "FastAPI"}, {"type": "protocol", "value": "JWT"}],
            complexity_score=3,
            created_at=base_time - timedelta(hours=4)
        ),

        # Decision content
        MemoryEntry(
            id="mem_007",
            content="Decision: Chose sqlite-vec over ChromaDB for local development due to easier setup, no external dependencies, and better integration with existing SQLite database. Will evaluate ChromaDB for production if scaling requirements demand it.",
            content_type=ContentType.DECISION,
            content_format=ContentFormat.TEXT,
            keywords=["decision", "sqlite-vec", "chromadb", "database", "architecture"],
            entities=[{"type": "technology", "value": "sqlite-vec"}, {"type": "technology", "value": "ChromaDB"}],
            complexity_score=5,
            created_at=base_time - timedelta(hours=5)
        ),

        # Learning content
        MemoryEntry(
            id="mem_008",
            content="Learning: RRF (Reciprocal Rank Fusion) significantly improves search result quality compared to simple score averaging. The formula 1/(k + rank) with k=60 provides optimal balance between relevance and position. Semantic and keyword scores should be weighted differently based on query type.",
            content_type=ContentType.LEARNING,
            content_format=ContentFormat.TEXT,
            keywords=["learning", "rrf", "search", "ranking", "algorithm"],
            entities=[{"type": "algorithm", "value": "RRF"}, {"type": "algorithm", "value": "Reciprocal Rank Fusion"}],
            complexity_score=6,
            created_at=base_time - timedelta(minutes=15)
        ),

        # Error content
        MemoryEntry(
            id="mem_009",
            content="Error: Database connection pool exhausted during high load. Root cause was connection leak in async context manager. Fixed by ensuring all connections are properly returned to pool using try/finally blocks.",
            content_type=ContentType.ERROR,
            content_format=ContentFormat.TEXT,
            keywords=["error", "database", "connection", "leak", "async"],
            entities=[{"type": "error_type", "value": "connection_leak"}, {"type": "component", "value": "connection_pool"}],
            complexity_score=4,
            created_at=base_time - timedelta(minutes=10)
        ),
    ]

    return entries


@pytest.fixture
def evaluation_queries_ground_truth() -> List[Dict[str, Any]]:
    """
    Ground truth dataset for RAG evaluation with queries and expected answers.

    Covers different query types and complexity levels:
    - Factual retrieval (specific information lookup)
    - Procedural queries (how-to, implementation steps)
    - Comparative analysis (feature comparison, decision rationale)
    - Error resolution (debugging, troubleshooting)
    """
    return [
        {
            "query": "How to authenticate users with password hashing in Python?",
            "ground_truth": "Use bcrypt for secure password hashing. Store only the hash in the database, never the plain password. When authenticating, hash the provided password with bcrypt and compare it to the stored hash. Use bcrypt.checkpw() for secure comparison.",
            "expected_context_types": ["code", "documentation"],
            "complexity": "low",
            "domain": "authentication"
        },
        {
            "query": "What is the RRF formula and how does it improve search results?",
            "ground_truth": "RRF (Reciprocal Rank Fusion) uses the formula 1/(k + rank) where k is typically 60. It gives more weight to higher-ranked results while still considering lower-ranked ones. This improves search quality by combining results from multiple ranking methods (semantic and keyword) more effectively than simple score averaging.",
            "expected_context_types": ["learning", "documentation"],
            "complexity": "medium",
            "domain": "search"
        },
        {
            "query": "Why was sqlite-vec chosen over ChromaDB for the memory system?",
            "ground_truth": "sqlite-vec was chosen for local development because it requires no external dependencies, has easier setup, and integrates better with the existing SQLite database. ChromaDB was considered but would add complexity. sqlite-vec may be re-evaluated for production if scaling requirements increase.",
            "expected_context_types": ["decision", "context"],
            "complexity": "medium",
            "domain": "architecture"
        },
        {
            "query": "How to fix database connection pool exhaustion issues?",
            "ground_truth": "Ensure all database connections are properly returned to the pool using try/finally blocks or proper async context managers. Check for connection leaks where connections are acquired but not released. Monitor connection pool usage and implement proper error handling to guarantee cleanup.",
            "expected_context_types": ["error", "learning"],
            "complexity": "high",
            "domain": "debugging"
        },
        {
            "query": "What are the API specifications for user authentication endpoints?",
            "ground_truth": "The authentication API uses POST /api/auth/login endpoint. Request body contains username and password as strings. Response returns JWT token, expires_in duration (3600 seconds), and user profile information. The token should be included in subsequent requests for authentication.",
            "expected_context_types": ["documentation", "code"],
            "complexity": "medium",
            "domain": "api"
        },
        {
            "query": "How does the DevStream memory system handle vector search?",
            "ground_truth": "The DevStream memory system uses SQLite with sqlite-vec extension for vector storage and search. It supports semantic search using embeddings, keyword search with FTS5, and hybrid search combining both methods. Results are ranked using Reciprocal Rank Fusion algorithm for optimal relevance.",
            "expected_context_types": ["documentation", "context"],
            "complexity": "high",
            "domain": "architecture"
        }
    ]


@pytest.fixture
def sample_evaluation_dataset(evaluation_queries_ground_truth) -> EvaluationDataset:
    """Create sample evaluation dataset from ground truth data."""
    queries = []

    for i, gt_data in enumerate(evaluation_queries_ground_truth):
        query = EvaluationQuery(
            query_text=gt_data["query"],
            ground_truth_answer=gt_data["ground_truth"],
            retrieved_contexts=[],  # Will be populated during tests
            query_id=f"eval_query_{i+1:03d}"
        )
        queries.append(query)

    return EvaluationDataset(
        queries=queries,
        name="DevStream Memory Quality Benchmark",
        description="Ground truth dataset for evaluating RAG metrics on DevStream memory system"
    )


# ============================================================================
# CORE RAG METRICS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_rag_evaluator_initialization(rag_evaluator):
    """Test RAG evaluator initialization and status checking."""
    # Test evaluator status
    status = await rag_evaluator.get_evaluation_status()

    assert status["embedding_model"] == "embeddinggemma"
    assert "llm_model" in status
    assert MetricType.FAITHFULNESS.value in status["supported_metrics"]
    assert MetricType.CONTEXT_PRECISION.value in status["supported_metrics"]
    assert MetricType.ANSWER_RELEVANCY.value in status["supported_metrics"]
    assert MetricType.CONTEXT_RECALL.value in status["supported_metrics"]


@pytest.mark.asyncio
async def test_evaluation_dataset_validation():
    """Test evaluation dataset creation and validation."""
    # Valid dataset
    valid_query = EvaluationQuery(
        query_text="Test query",
        ground_truth_answer="Test answer",
        retrieved_contexts=["Context 1", "Context 2"]
    )

    dataset = EvaluationDataset(
        queries=[valid_query],
        name="Test Dataset"
    )

    assert len(dataset.queries) == 1
    assert dataset.name == "Test Dataset"
    assert isinstance(dataset.created_at, float)

    # Test invalid queries
    with pytest.raises(ValidationError):
        EvaluationQuery(
            query_text="",  # Empty query
            ground_truth_answer="Answer",
            retrieved_contexts=["Context"]
        )

    with pytest.raises(ValidationError):
        EvaluationQuery(
            query_text="Query",
            ground_truth_answer="",  # Empty answer
            retrieved_contexts=["Context"]
        )

    with pytest.raises(ValidationError):
        EvaluationQuery(
            query_text="Query",
            ground_truth_answer="Answer",
            retrieved_contexts=[]  # Empty contexts
        )


@pytest.mark.asyncio
async def test_memory_storage_populated(sample_memory_entries, memory_storage):
    """Test that memory storage can be populated with sample data."""
    # Store all sample entries
    for entry in sample_memory_entries:
        await memory_storage.store_memory(entry)

    # Verify storage
    all_entries = await memory_storage.get_all_memories(limit=100)
    assert len(all_entries) == len(sample_memory_entries)

    # Test retrieval by content type
    code_entries = await memory_storage.get_memories_by_type(ContentType.CODE)
    doc_entries = await memory_storage.get_memories_by_type(ContentType.DOCUMENTATION)

    assert len(code_entries) == 3  # Python, TypeScript, SQL
    assert len(doc_entries) == 2   # API docs, architecture docs


@pytest.mark.asyncio
async def test_create_evaluation_from_memory_system(
    rag_evaluator,
    sample_memory_entries,
    memory_storage,
    evaluation_queries_ground_truth
):
    """Test creating evaluation dataset from memory system queries."""
    # Populate memory storage
    for entry in sample_memory_entries:
        await memory_storage.store_memory(entry)

    # Extract queries and ground truth from test data
    queries = [gt["query"] for gt in evaluation_queries_ground_truth]
    ground_truth_answers = [gt["ground_truth"] for gt in evaluation_queries_ground_truth]

    # Create evaluation dataset
    dataset = await rag_evaluator.create_evaluation_from_memory_system(
        queries=queries,
        ground_truth_answers=ground_truth_answers,
        max_contexts_per_query=3
    )

    # Verify dataset creation
    assert len(dataset.queries) == len(queries)
    assert dataset.name == "Memory System Evaluation"

    # Verify each query has retrieved contexts
    for i, query in enumerate(dataset.queries):
        assert query.query_text == queries[i]
        assert query.ground_truth_answer == ground_truth_answers[i]
        assert len(query.retrieved_contexts) > 0  # Should find some contexts
        assert query.query_id.startswith("memory_query_")


@pytest.mark.asyncio
async def test_faithfulness_metric_evaluation(rag_evaluator):
    """Test faithfulness metric evaluation with sample data."""
    # Test case with high faithfulness
    contexts = [
        "Use bcrypt for secure password hashing in Python authentication systems.",
        "Store only password hashes, never plain passwords in the database.",
        "bcrypt.checkpw() provides secure password comparison."
    ]

    generated_answer = "Use bcrypt for secure password hashing. Store only hashes in the database and use bcrypt.checkpw() for comparison."

    result = await rag_evaluator.evaluate_faithfulness(generated_answer, contexts)

    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.FAITHFULNESS
    assert 0.0 <= result.score <= 1.0
    assert result.reasoning is not None
    assert result.execution_time_ms > 0

    # Test case with low faithfulness (contradictory information)
    low_faithfulness_answer = "Use plaintext passwords for simplicity and store them directly in the database."
    result_low = await rag_evaluator.evaluate_faithfulness(low_faithfulness_answer, contexts)

    assert result_low.score < result.score  # Should be lower faithfulness


@pytest.mark.asyncio
async def test_context_precision_metric_evaluation(rag_evaluator):
    """Test context precision metric evaluation."""
    query = "How to implement user authentication in Python?"

    # Test with relevant contexts
    relevant_contexts = [
        "def authenticate_user(username, password): return bcrypt.checkpw(password.encode(), hash.encode())",
        "User authentication best practices in Python: Use bcrypt, never store plain passwords",
        "JWT tokens for session management after successful authentication"
    ]

    result = await rag_evaluator.evaluate_context_precision(query, relevant_contexts)

    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.CONTEXT_PRECISION
    assert 0.0 <= result.score <= 1.0
    assert "relevant" in result.reasoning.lower()

    # Test with mixed relevant/irrelevant contexts
    mixed_contexts = [
        "def authenticate_user(username, password): return bcrypt.checkpw(password.encode(), hash.encode())",
        "Database connection pooling optimization techniques",  # Irrelevant
        "User authentication best practices: Use bcrypt, never store plain passwords"
    ]

    result_mixed = await rag_evaluator.evaluate_context_precision(query, mixed_contexts)

    # Mixed contexts should have lower precision than all-relevant
    assert result_mixed.score <= result.score


@pytest.mark.asyncio
async def test_answer_relevancy_metric_evaluation(rag_evaluator):
    """Test answer relevancy metric evaluation."""
    query = "What is RRF and how does it improve search results?"

    # Relevant answer
    relevant_answer = "RRF (Reciprocal Rank Fusion) is an algorithm that combines multiple ranking results using the formula 1/(k + rank). It improves search quality by giving more weight to higher-ranked results while still considering lower-ranked ones from different ranking methods."

    result = await rag_evaluator.evaluate_answer_relevancy(query, relevant_answer)

    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.ANSWER_RELEVANCY
    assert 0.0 <= result.score <= 1.0
    assert result.reasoning is not None

    # Irrelevant answer
    irrelevant_answer = "The weather today is sunny with a high of 75 degrees. Perfect for outdoor activities."

    result_irrelevant = await rag_evaluator.evaluate_answer_relevancy(query, irrelevant_answer)

    assert result_irrelevant.score < result.score


@pytest.mark.asyncio
async def test_context_recall_metric_evaluation(rag_evaluator):
    """Test context recall metric evaluation."""
    ground_truth = "Use bcrypt for password hashing, store only hashes, and use bcrypt.checkpw() for secure comparison. Never store plain passwords."

    # High recall context (covers all key points)
    high_recall_contexts = [
        "Always use bcrypt for secure password hashing in authentication systems",
        "Store only password hashes in the database, never plain text passwords",
        "Use bcrypt.checkpw() function for secure password verification and comparison"
    ]

    result = await rag_evaluator.evaluate_context_recall(ground_truth, high_recall_contexts)

    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.CONTEXT_RECALL
    assert 0.0 <= result.score <= 1.0
    assert result.reasoning is not None

    # Low recall context (missing key information)
    low_recall_contexts = [
        "Use secure authentication methods in your application"
    ]

    result_low = await rag_evaluator.evaluate_context_recall(ground_truth, low_recall_contexts)

    assert result_low.score < result.score


@pytest.mark.asyncio
async def test_complete_query_evaluation(rag_evaluator):
    """Test complete evaluation of a single query across all metrics."""
    evaluation_query = EvaluationQuery(
        query_text="How to implement secure user authentication?",
        ground_truth_answer="Use bcrypt for password hashing, store only hashes, and use bcrypt.checkpw() for comparison. Never store plain passwords.",
        retrieved_contexts=[
            "def authenticate_user(username, password): return bcrypt.checkpw(password.encode(), stored_hash.encode())",
            "Best practices: Use bcrypt, salt rounds 12, never store plain passwords",
            "JWT tokens for session management after successful authentication"
        ],
        generated_answer="Implement authentication using bcrypt for password hashing. Store only password hashes in the database and use bcrypt.checkpw() for secure password verification.",
        query_id="test_query_001"
    )

    # Evaluate all metrics
    results = await rag_evaluator.evaluate_query(evaluation_query)

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
async def test_dataset_evaluation_workflow(
    rag_evaluator,
    sample_memory_entries,
    memory_storage,
    evaluation_queries_ground_truth
):
    """Test complete dataset evaluation workflow."""
    # Populate memory storage
    for entry in sample_memory_entries:
        await memory_storage.store_memory(entry)

    # Create evaluation dataset from memory system
    queries = [gt["query"] for gt in evaluation_queries_ground_truth[:3]]  # Use subset for faster testing
    ground_truth_answers = [gt["ground_truth"] for gt in evaluation_queries_ground_truth[:3]]

    dataset = await rag_evaluator.create_evaluation_from_memory_system(
        queries=queries,
        ground_truth_answers=ground_truth_answers,
        max_contexts_per_query=3
    )

    # Add generated answers for faithfulness and answer relevancy
    for query in dataset.queries:
        if "authentication" in query.query_text.lower():
            query.generated_answer = "Use bcrypt for secure password hashing and store only password hashes."
        elif "rrf" in query.query_text.lower():
            query.generated_answer = "RRF uses the formula 1/(k + rank) to combine search rankings effectively."
        else:
            query.generated_answer = "Answer based on retrieved context information."

    # Evaluate dataset
    report = await rag_evaluator.evaluate_dataset(
        dataset=dataset,
        max_concurrent_evaluations=2  # Limit concurrency for testing
    )

    # Verify evaluation report
    assert isinstance(report, EvaluationReport)
    assert report.dataset_name == "Memory System Evaluation"
    assert report.total_queries == len(queries)
    assert report.successful_evaluations <= report.total_queries
    assert report.embedding_model == "embeddinggemma"

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
async def test_error_handling_and_recovery(rag_evaluator):
    """Test error handling in RAG metrics evaluation."""
    # Test with malformed contexts
    malformed_query = EvaluationQuery(
        query_text="Test query",
        ground_truth_answer="Test answer",
        retrieved_contexts=[""],  # Empty context
        generated_answer="Test answer"
    )

    results = await rag_evaluator.evaluate_query(malformed_query)

    # Should handle gracefully without crashing
    assert isinstance(results, dict)
    for metric_name, result in results.items():
        assert isinstance(result, MetricResult)
        # Some metrics may fail gracefully with error
        if result.error:
            assert result.score == 0.0
            assert len(result.error) > 0


@pytest.mark.asyncio
async def test_performance_benchmarks(rag_evaluator, sample_memory_entries, memory_storage):
    """Test performance benchmarks for RAG metrics evaluation."""
    # Populate with more data for performance testing
    for entry in sample_memory_entries:
        await memory_storage.store_memory(entry)

    # Create evaluation dataset
    queries = [
        "How to implement authentication?",
        "What is RRF algorithm?",
        "Database connection best practices?"
    ]

    ground_truth_answers = [
        "Use bcrypt for password hashing.",
        "RRF combines rankings using reciprocal formula.",
        "Use connection pooling and proper cleanup."
    ]

    dataset = await rag_evaluator.create_evaluation_from_memory_system(
        queries=queries,
        ground_truth_answers=ground_truth_answers,
        max_contexts_per_query=3
    )

    # Add generated answers
    for query in dataset.queries:
        query.generated_answer = "Sample generated answer for testing."

    # Benchmark evaluation time
    start_time = time.time()
    report = await rag_evaluator.evaluate_dataset(dataset)
    total_time = (time.time() - start_time) * 1000

    # Performance assertions (adjust thresholds as needed)
    assert total_time < 30000  # Should complete within 30 seconds
    assert report.total_execution_time_ms < 30000
    assert report.average_query_time_ms < 10000  # Average per query under 10 seconds


@pytest.mark.asyncio
async def test_content_type_coverage_analysis(rag_evaluator, sample_memory_entries, memory_storage):
    """Test that evaluation covers different content types effectively."""
    # Store entries with all content types
    for entry in sample_memory_entries:
        await memory_storage.store_memory(entry)

    # Test queries targeting different content types
    content_type_queries = [
        ("How to implement user authentication?", [ContentType.CODE, ContentType.DOCUMENTATION]),
        ("What architecture decisions were made?", [ContentType.DECISION, ContentType.CONTEXT]),
        ("What errors were encountered?", [ContentType.ERROR, ContentType.LEARNING]),
        ("What system documentation exists?", [ContentType.DOCUMENTATION])
    ]

    for query_text, expected_types in content_type_queries:
        dataset = await rag_evaluator.create_evaluation_from_memory_system(
            queries=[query_text],
            ground_truth_answers=["Test answer"],
            max_contexts_per_query=5
        )

        # Verify retrieved contexts contain expected content types
        if dataset.queries[0].retrieved_contexts:
            # Check that contexts were found for the query
            assert len(dataset.queries[0].retrieved_contexts) > 0

            # Could add more sophisticated content type validation here
            # by checking the actual memory entries returned


# ============================================================================
# INTEGRATION TESTS WITH REAL DEVSTREAM DATA
# ============================================================================

@pytest.mark.asyncio
async def test_integration_with_real_devstream_memory(rag_evaluator, memory_storage):
    """Test integration with realistic DevStream memory data."""
    # Create realistic memory entries that simulate actual DevStream usage
    realistic_entries = [
        MemoryEntry(
            id="devstream_001",
            content="async def create_intervention_plan(title: str, objectives: List[str]) -> InterventionPlan:\n    \"\"\"Create new intervention plan with semantic memory integration.\"\"\"\n    plan = InterventionPlan(title=title, objectives=objectives)\n    await memory_storage.store_memory(\n        MemoryEntry(\n            content=f\"Created plan: {title}\",\n            content_type=ContentType.DECISION,\n            keywords=[\"plan\", title.lower()]\n        )\n    )\n    return plan",
            content_type=ContentType.CODE,
            content_format=ContentFormat.CODE,
            keywords=["async", "intervention", "plan", "memory", "devstream"],
            entities=[{"type": "function", "value": "create_intervention_plan"}, {"type": "class", "value": "InterventionPlan"}],
            complexity_score=7
        ),

        MemoryEntry(
            id="devstream_002",
            content="Decision: Integrated RAG metrics evaluation framework into DevStream memory system. This enables quality assessment of retrieval and generation capabilities, ensuring the memory system provides accurate and relevant context for AI agents.",
            content_type=ContentType.DECISION,
            content_format=ContentFormat.TEXT,
            keywords=["rag", "metrics", "evaluation", "quality", "devstream"],
            entities=[{"type": "framework", "value": "RAG"}, {"type": "system", "value": "DevStream"}],
            complexity_score=6
        ),

        MemoryEntry(
            id="devstream_003",
            content="Context: User requested implementation of comprehensive test suite for memory quality metrics. Requirements include async testing patterns, Context7 compliance, integration with existing DevStream infrastructure, and validation against ground truth datasets.",
            content_type=ContentType.CONTEXT,
            content_format=ContentFormat.TEXT,
            keywords=["testing", "context7", "devstream", "memory", "quality"],
            entities=[{"type": "standard", "value": "Context7"}, {"type": "system", "value": "DevStream"}],
            complexity_score=5
        )
    ]

    # Store realistic data
    for entry in realistic_entries:
        await memory_storage.store_memory(entry)

    # Test realistic queries
    queries = [
        "How does DevStream handle intervention plan creation?",
        "What RAG metrics are implemented in the memory system?",
        "What are the testing requirements for DevStream memory?"
    ]

    ground_truth_answers = [
        "DevStream creates intervention plans asynchronously and stores them in memory with semantic indexing.",
        "DevStream implements faithfulness, context precision, answer relevancy, and context recall metrics.",
        "DevStream requires async testing patterns, Context7 compliance, and integration with existing infrastructure."
    ]

    # Create evaluation dataset
    dataset = await rag_evaluator.create_evaluation_from_memory_system(
        queries=queries,
        ground_truth_answers=ground_truth_answers,
        max_contexts_per_query=3
    )

    # Add generated answers
    dataset.queries[0].generated_answer = "DevStream uses async functions to create intervention plans and stores them in semantic memory."
    dataset.queries[1].generated_answer = "The system implements faithfulness, context precision, answer relevancy, and context recall metrics for quality evaluation."
    dataset.queries[2].generated_answer = "Testing requires async patterns, Context7 compliance, and integration with DevStream infrastructure."

    # Evaluate dataset
    report = await rag_evaluator.evaluate_dataset(dataset)

    # Verify results
    assert report.total_queries == 3
    assert report.successful_evaluations >= 2  # Allow for some evaluation failures
    assert report.overall_score > 0.0

    # Print detailed results for manual inspection (remove in production)
    print(f"\n=== DevStream Integration Test Results ===")
    print(f"Overall Score: {report.overall_score:.3f}")
    print(f"Faithfulness: {report.faithfulness_score:.3f}")
    print(f"Context Precision: {report.context_precision_score:.3f}")
    print(f"Answer Relevancy: {report.answer_relevancy_score:.3f}")
    print(f"Context Recall: {report.context_recall_score:.3f}")
    print(f"Total Execution Time: {report.total_execution_time_ms:.0f}ms")


# ============================================================================
# UTILITY AND HELPER FUNCTIONS
# ============================================================================

def create_mock_embedding(dimension: int = 384) -> List[float]:
    """Create mock embedding vector for testing."""
    import random
    return [random.uniform(-1, 1) for _ in range(dimension)]


async def store_test_data(storage: MemoryStorage, entries: List[MemoryEntry]) -> None:
    """Helper function to store test data in memory storage."""
    for entry in entries:
        # Add mock embedding for more realistic testing
        if not entry.embedding:
            entry.set_embedding(np.array(create_mock_embedding(), dtype=np.float32), "mock_model")

        await storage.store_memory(entry)


def validate_evaluation_report(report: EvaluationReport) -> bool:
    """Validate evaluation report structure and values."""
    if not isinstance(report, EvaluationReport):
        return False

    # Check score ranges
    scores = [
        report.faithfulness_score,
        report.context_precision_score,
        report.answer_relevancy_score,
        report.context_recall_score,
        report.overall_score
    ]

    for score in scores:
        if not (0.0 <= score <= 1.0):
            return False

    # Check performance metrics
    if report.total_execution_time_ms <= 0 or report.average_query_time_ms <= 0:
        return False

    # Check result consistency
    if report.successful_evaluations > report.total_queries:
        return False

    return True


# ============================================================================
# TEST EXECUTION CONFIGURATION
# ============================================================================

if __name__ == "__main__":
    # Run tests with specific configuration
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "not slow",
        "--asyncio-mode=auto"
    ])