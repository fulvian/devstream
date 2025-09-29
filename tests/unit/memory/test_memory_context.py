"""
Unit tests for memory context assembly functionality.

Context7-validated patterns for context assembly testing:
- Token budget management
- Content prioritization algorithms
- Context truncation strategies
- Memory relevance ranking
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

from devstream.memory.context import ContextAssembler
from devstream.memory.search import HybridSearchEngine
from devstream.memory.models import MemoryEntry, SearchQuery, ContentType, ContentFormat, MemoryQueryResult, ContextAssemblyResult
from devstream.memory.exceptions import ContextAssemblyError


@pytest.mark.unit
@pytest.mark.memory
class TestContextAssembler:
    """Test context assembly with Context7-validated patterns."""

    @pytest.fixture
    def mock_search_engine(self):
        """Create mock search engine."""
        engine = Mock(spec=HybridSearchEngine)
        engine.hybrid_search = AsyncMock(return_value=[])
        engine.search_by_content_type = AsyncMock(return_value=[])
        engine.search_by_task_id = AsyncMock(return_value=[])
        return engine

    @pytest.fixture
    def context_assembler(self, mock_search_engine):
        """Create context assembler with mocked dependencies."""
        return ContextAssembler(mock_search_engine)

    @pytest.fixture
    def sample_memories(self):
        """Create sample memory entries for testing."""
        return [
            MemoryEntry(
                id="mem-1",
                content="Python programming is a versatile language used for web development, data science, and automation.",
                content_type=ContentType.DOCUMENTATION,
                content_format=ContentFormat.MARKDOWN,
                keywords=["python", "programming", "versatile"],
                task_id="task-1",
                relevance_score=0.9,
                complexity_score=5
            ),
            MemoryEntry(
                id="mem-2",
                content="def calculate_fibonacci(n):\n    if n <= 1:\n        return n\n    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)",
                content_type=ContentType.CODE,
                content_format=ContentFormat.PYTHON,
                keywords=["fibonacci", "recursion", "algorithm"],
                task_id="task-1",
                relevance_score=0.8,
                complexity_score=7
            ),
            MemoryEntry(
                id="mem-3",
                content="The user requested help with implementing a fibonacci function. This is a common algorithmic problem.",
                content_type=ContentType.CONTEXT,
                content_format=ContentFormat.TEXT,
                keywords=["fibonacci", "implementation", "request"],
                task_id="task-1",
                relevance_score=0.7,
                complexity_score=3
            ),
            MemoryEntry(
                id="mem-4",
                content="A very long memory entry that contains extensive documentation about advanced Python concepts including object-oriented programming, metaclasses, decorators, context managers, generators, coroutines, and many other advanced features that would take up significant token space in the context window.",
                content_type=ContentType.DOCUMENTATION,
                content_format=ContentFormat.MARKDOWN,
                keywords=["python", "advanced", "concepts"],
                task_id="task-2",
                relevance_score=0.6,
                complexity_score=9
            )
        ]

    @pytest.fixture
    def sample_search_results(self, sample_memories):
        """Create sample search results."""
        return [
            MemoryQueryResult(sample_memories[0], 0.9, {"method": "semantic"}),
            MemoryQueryResult(sample_memories[1], 0.8, {"method": "keyword"}),
            MemoryQueryResult(sample_memories[2], 0.7, {"method": "full_text"}),
            MemoryQueryResult(sample_memories[3], 0.6, {"method": "semantic"})
        ]

    def test_assembler_initialization(self, context_assembler, mock_search_engine):
        """Test context assembler initializes correctly."""
        assert context_assembler.search_engine == mock_search_engine
        assert context_assembler.max_tokens == 4000
        assert context_assembler.min_tokens == 100
        assert context_assembler.relevance_threshold == 0.3

    def test_count_tokens_basic(self, context_assembler):
        """Test basic token counting."""
        text = "This is a simple test text for token counting."
        token_count = context_assembler.count_tokens(text)

        assert isinstance(token_count, int)
        assert token_count > 0
        assert token_count <= len(text.split()) * 2  # Rough upper bound

    def test_count_tokens_empty(self, context_assembler):
        """Test token counting with empty text."""
        token_count = context_assembler.count_tokens("")
        assert token_count == 0

    def test_count_tokens_long_text(self, context_assembler):
        """Test token counting with long text."""
        long_text = " ".join(["word"] * 1000)
        token_count = context_assembler.count_tokens(long_text)

        assert token_count > 500  # Should be substantial
        assert token_count < 2000  # But not excessive

    def test_estimate_memory_tokens(self, context_assembler, sample_memories):
        """Test memory token estimation."""
        memory = sample_memories[0]
        token_count = context_assembler._estimate_memory_tokens(memory)

        assert isinstance(token_count, int)
        assert token_count > 0
        # Should include content, keywords, and metadata
        assert token_count > len(memory.content.split())

    def test_estimate_memory_tokens_long_content(self, context_assembler, sample_memories):
        """Test token estimation for memory with long content."""
        memory = sample_memories[3]  # Has very long content
        token_count = context_assembler._estimate_memory_tokens(memory)

        assert token_count > 100  # Should be substantial

    def test_format_memory_content_basic(self, context_assembler, sample_memories):
        """Test basic memory content formatting."""
        memory = sample_memories[0]
        formatted = context_assembler._format_memory_content(memory)

        assert memory.content in formatted
        assert f"Type: {memory.content_type.value}" in formatted
        assert f"Task: {memory.task_id}" in formatted
        assert "Keywords:" in formatted
        assert formatted.startswith("===")

    def test_format_memory_content_no_task(self, context_assembler):
        """Test formatting memory without task ID."""
        memory = MemoryEntry(
            id="no-task",
            content="Memory without task",
            content_type=ContentType.DOCUMENTATION
        )

        formatted = context_assembler._format_memory_content(memory)
        assert "Task: None" in formatted

    def test_format_memory_content_no_keywords(self, context_assembler):
        """Test formatting memory without keywords."""
        memory = MemoryEntry(
            id="no-keywords",
            content="Memory without keywords",
            content_type=ContentType.DOCUMENTATION,
            keywords=[]
        )

        formatted = context_assembler._format_memory_content(memory)
        assert "Keywords: " in formatted

    def test_format_memory_content_code(self, context_assembler, sample_memories):
        """Test formatting code memory."""
        code_memory = sample_memories[1]  # CODE type
        formatted = context_assembler._format_memory_content(code_memory)

        assert "Type: code" in formatted
        assert code_memory.content in formatted
        assert "def calculate_fibonacci" in formatted

    def test_prioritize_memories_by_relevance(self, context_assembler, sample_search_results):
        """Test memory prioritization by relevance."""
        prioritized = context_assembler._prioritize_memories(
            sample_search_results,
            "relevance".RELEVANCE
        )

        # Should be sorted by score (descending)
        scores = [result.score for result in prioritized]
        assert scores == sorted(scores, reverse=True)
        assert prioritized[0].score == 0.9

    def test_prioritize_memories_by_recency(self, context_assembler, sample_search_results):
        """Test memory prioritization by recency."""
        # Mock creation dates
        from datetime import datetime, timedelta
        now = datetime.now()
        for i, result in enumerate(sample_search_results):
            result.memory.created_at = now - timedelta(days=i)

        prioritized = context_assembler._prioritize_memories(
            sample_search_results,
            "relevance".RECENCY
        )

        # Should be sorted by creation date (most recent first)
        dates = [result.memory.created_at for result in prioritized]
        assert dates == sorted(dates, reverse=True)

    def test_prioritize_memories_by_complexity(self, context_assembler, sample_search_results):
        """Test memory prioritization by complexity."""
        prioritized = context_assembler._prioritize_memories(
            sample_search_results,
            "relevance".COMPLEXITY
        )

        # Should be sorted by complexity (ascending for easier first)
        complexities = [result.memory.complexity_score for result in prioritized]
        assert complexities == sorted(complexities)

    def test_prioritize_memories_mixed_strategy(self, context_assembler, sample_search_results):
        """Test memory prioritization with mixed strategy."""
        prioritized = context_assembler._prioritize_memories(
            sample_search_results,
            "relevance".MIXED
        )

        # Should balance relevance and recency
        assert len(prioritized) == len(sample_search_results)
        # High relevance should still be near the top
        assert prioritized[0].score >= 0.7

    def test_apply_token_budget_within_limit(self, context_assembler, sample_search_results):
        """Test applying token budget when within limits."""
        token_budget = 2000
        selected = context_assembler._apply_token_budget(sample_search_results, token_budget)

        # Should include all results if within budget
        total_tokens = sum(
            context_assembler._estimate_memory_tokens(result.memory)
            for result in selected
        )
        assert total_tokens <= token_budget
        assert len(selected) > 0

    def test_apply_token_budget_exceeds_limit(self, context_assembler, sample_search_results):
        """Test applying token budget when exceeding limits."""
        token_budget = 50  # Very small budget
        selected = context_assembler._apply_token_budget(sample_search_results, token_budget)

        # Should select fewer results to stay within budget
        total_tokens = sum(
            context_assembler._estimate_memory_tokens(result.memory)
            for result in selected
        )
        assert total_tokens <= token_budget
        assert len(selected) < len(sample_search_results)

    def test_apply_token_budget_zero_budget(self, context_assembler, sample_search_results):
        """Test applying zero token budget."""
        selected = context_assembler._apply_token_budget(sample_search_results, 0)
        assert len(selected) == 0

    def test_apply_token_budget_empty_results(self, context_assembler):
        """Test applying token budget to empty results."""
        selected = context_assembler._apply_token_budget([], 1000)
        assert len(selected) == 0

    def test_filter_by_relevance_threshold(self, context_assembler, sample_search_results):
        """Test filtering by relevance threshold."""
        threshold = 0.75
        filtered = context_assembler._filter_by_relevance(sample_search_results, threshold)

        # Should only include results above threshold
        assert all(result.score >= threshold for result in filtered)
        assert len(filtered) < len(sample_search_results)

    def test_filter_by_relevance_no_threshold(self, context_assembler, sample_search_results):
        """Test filtering with no relevance threshold."""
        filtered = context_assembler._filter_by_relevance(sample_search_results, 0.0)
        assert len(filtered) == len(sample_search_results)

    def test_filter_by_relevance_high_threshold(self, context_assembler, sample_search_results):
        """Test filtering with very high relevance threshold."""
        filtered = context_assembler._filter_by_relevance(sample_search_results, 0.95)
        assert len(filtered) == 0  # No results should meet this threshold

    def test_empty_context_result(self, context_assembler):
        """Test empty context result creation."""
        token_budget = 1000
        strategy = "relevance".RELEVANCE

        result = context_assembler._empty_context_result(token_budget, strategy)

        assert isinstance(result, ContextAssemblyResult)
        assert result.assembled_context == ""
        assert result.total_tokens == 0
        assert result.tokens_remaining == token_budget
        assert result.memory_count == 0
        assert result.strategy == strategy
        assert not result.truncated

    @pytest.mark.asyncio
    async def test_assemble_context_basic(self, context_assembler, mock_search_engine, sample_search_results):
        """Test basic context assembly."""
        mock_search_engine.hybrid_search.return_value = sample_search_results

        query = SearchQuery(query_text="python fibonacci", max_results=10)
        result = await context_assembler.assemble_context(query)

        assert isinstance(result, ContextAssemblyResult)
        assert len(result.assembled_context) > 0
        assert result.total_tokens > 0
        assert result.memory_count > 0
        assert result.strategy == "relevance".RELEVANCE

    @pytest.mark.asyncio
    async def test_assemble_context_empty_query(self, context_assembler, mock_search_engine):
        """Test context assembly with empty query."""
        mock_search_engine.hybrid_search.return_value = []

        query = SearchQuery(query_text="", max_results=10)
        result = await context_assembler.assemble_context(query)

        assert result.assembled_context == ""
        assert result.memory_count == 0

    @pytest.mark.asyncio
    async def test_assemble_context_with_strategy(self, context_assembler, mock_search_engine, sample_search_results):
        """Test context assembly with specific strategy."""
        mock_search_engine.hybrid_search.return_value = sample_search_results

        query = SearchQuery(query_text="test query", max_results=10)
        result = await context_assembler.assemble_context(
            query,
            strategy="relevance".COMPLEXITY,
            token_budget=1500
        )

        assert result.strategy == "relevance".COMPLEXITY
        assert result.total_tokens <= 1500

    @pytest.mark.asyncio
    async def test_assemble_context_token_limit(self, context_assembler, mock_search_engine, sample_search_results):
        """Test context assembly with tight token limit."""
        mock_search_engine.hybrid_search.return_value = sample_search_results

        query = SearchQuery(query_text="test query", max_results=10)
        result = await context_assembler.assemble_context(
            query,
            token_budget=100  # Very small budget
        )

        assert result.total_tokens <= 100
        assert result.tokens_remaining >= 0
        # May be truncated due to small budget
        assert result.memory_count <= len(sample_search_results)

    @pytest.mark.asyncio
    async def test_assemble_context_search_error(self, context_assembler, mock_search_engine):
        """Test context assembly with search error."""
        mock_search_engine.hybrid_search.side_effect = Exception("Search failed")

        query = SearchQuery(query_text="test query", max_results=10)

        with pytest.raises(ContextAssemblyError):
            await context_assembler.assemble_context(query)

    @pytest.mark.asyncio
    async def test_assemble_context_for_task(self, context_assembler, mock_search_engine, sample_search_results):
        """Test context assembly for specific task."""
        # Filter results to only those from task-1
        task_results = [r for r in sample_search_results if r.memory.task_id == "task-1"]
        mock_search_engine.search_by_task_id.return_value = task_results

        result = await context_assembler.assemble_context_for_task(
            "task-1",
            query_text="fibonacci implementation"
        )

        assert result.memory_count <= 3  # Only 3 memories have task-1
        mock_search_engine.search_by_task_id.assert_called_once()

    @pytest.mark.asyncio
    async def test_assemble_context_for_task_no_results(self, context_assembler, mock_search_engine):
        """Test context assembly for task with no results."""
        mock_search_engine.search_by_task_id.return_value = []

        result = await context_assembler.assemble_context_for_task(
            "nonexistent-task",
            query_text="test query"
        )

        assert result.memory_count == 0
        assert result.assembled_context == ""

    @pytest.mark.asyncio
    async def test_assemble_context_by_type(self, context_assembler, mock_search_engine, sample_search_results):
        """Test context assembly by content type."""
        # Filter to only code results
        code_results = [r for r in sample_search_results if r.memory.content_type == ContentType.CODE]
        mock_search_engine.search_by_content_type.return_value = code_results

        result = await context_assembler.assemble_context_by_type(
            ContentType.CODE,
            query_text="fibonacci function"
        )

        assert all("code" in result.assembled_context.lower() or
                  "def " in result.assembled_context for _ in [1])  # Should contain code
        mock_search_engine.search_by_content_type.assert_called_once()

    @pytest.mark.asyncio
    async def test_assemble_recent_context(self, context_assembler, mock_search_engine, sample_search_results):
        """Test assembling recent context."""
        mock_search_engine.hybrid_search.return_value = sample_search_results

        query = SearchQuery(query_text="recent memories", max_results=10)
        result = await context_assembler.assemble_recent_context(
            query,
            strategy="relevance".RECENCY
        )

        assert result.strategy == "relevance".RECENCY
        assert result.memory_count > 0

    @pytest.mark.asyncio
    async def test_get_context_summary(self, context_assembler, mock_search_engine, sample_search_results):
        """Test getting context summary."""
        mock_search_engine.hybrid_search.return_value = sample_search_results

        query = SearchQuery(query_text="python programming", max_results=10)
        result = await context_assembler.assemble_context(query)

        summary = context_assembler.get_context_summary(result)

        assert isinstance(summary, dict)
        assert "memory_count" in summary
        assert "total_tokens" in summary
        assert "content_types" in summary
        assert "avg_relevance" in summary
        assert "strategy" in summary

    def test_get_context_summary_empty_result(self, context_assembler):
        """Test getting summary of empty context result."""
        empty_result = context_assembler._empty_context_result(1000, "relevance".RELEVANCE)
        summary = context_assembler.get_context_summary(empty_result)

        assert summary["memory_count"] == 0
        assert summary["total_tokens"] == 0
        assert summary["avg_relevance"] == 0.0

    @pytest.mark.asyncio
    async def test_progressive_context_building(self, context_assembler, mock_search_engine, sample_search_results):
        """Test progressive context building with increasing budget."""
        mock_search_engine.hybrid_search.return_value = sample_search_results

        query = SearchQuery(query_text="progressive test", max_results=10)

        # Build context with increasing token budgets
        small_result = await context_assembler.assemble_context(query, token_budget=200)
        medium_result = await context_assembler.assemble_context(query, token_budget=500)
        large_result = await context_assembler.assemble_context(query, token_budget=1000)

        # Should progressively include more content
        assert small_result.memory_count <= medium_result.memory_count
        assert medium_result.memory_count <= large_result.memory_count
        assert small_result.total_tokens <= medium_result.total_tokens
        assert medium_result.total_tokens <= large_result.total_tokens

    @pytest.mark.asyncio
    async def test_context_deduplication(self, context_assembler, mock_search_engine):
        """Test context assembly with duplicate memories."""
        # Create duplicate results
        memory = MemoryEntry(
            id="duplicate",
            content="Duplicate content",
            content_type=ContentType.DOCUMENTATION,
            relevance_score=0.8
        )

        duplicate_results = [
            MemoryQueryResult(memory, 0.9, {"method": "semantic"}),
            MemoryQueryResult(memory, 0.7, {"method": "keyword"}),  # Same memory, different score
        ]

        mock_search_engine.hybrid_search.return_value = duplicate_results

        query = SearchQuery(query_text="duplicate test", max_results=10)
        result = await context_assembler.assemble_context(query)

        # Should only include the memory once
        assert result.memory_count == 1
        assert "Duplicate content" in result.assembled_context
        # Should count the duplicate content only once in tokens

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_context_assembly_performance(self, context_assembler, mock_search_engine, sample_search_results):
        """Test context assembly performance."""
        import time

        # Create larger dataset for performance test
        large_results = sample_search_results * 10  # 40 results
        mock_search_engine.hybrid_search.return_value = large_results

        query = SearchQuery(query_text="performance test", max_results=50)

        start_time = time.time()
        result = await context_assembler.assemble_context(query, token_budget=2000)
        assembly_time = time.time() - start_time

        # Should complete within reasonable time
        assert assembly_time < 1.0  # Less than 1 second
        assert result.memory_count > 0

    @pytest.mark.asyncio
    async def test_concurrent_context_assembly(self, context_assembler, mock_search_engine, sample_search_results):
        """Test concurrent context assembly operations."""
        import asyncio

        mock_search_engine.hybrid_search.return_value = sample_search_results

        # Run multiple concurrent assembly operations
        queries = [
            SearchQuery(query_text=f"concurrent query {i}", max_results=10)
            for i in range(5)
        ]

        tasks = [
            context_assembler.assemble_context(query, token_budget=1000)
            for query in queries
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for result in results:
            assert isinstance(result, ContextAssemblyResult)
            assert result.total_tokens <= 1000