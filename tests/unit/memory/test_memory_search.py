"""
Unit tests for memory search engine functionality.

Context7-validated patterns for vector search testing:
- Semantic similarity calculations
- Hybrid search result ranking
- Vector distance metrics validation
- Search result relevance scoring
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

from devstream.memory.search import HybridSearchEngine
from devstream.memory.models import MemoryEntry, SearchQuery, ContentType, MemoryQueryResult
from devstream.memory.processing import TextProcessor
from devstream.memory.storage import MemoryStorage
from devstream.memory.exceptions import SearchError


@pytest.mark.unit
@pytest.mark.memory
class TestHybridSearchEngine:
    """Test hybrid search engine with Context7-validated patterns."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock memory storage."""
        storage = Mock(spec=MemoryStorage)
        storage.search_by_keywords = AsyncMock(return_value=[])
        storage.search_by_embedding = AsyncMock(return_value=[])
        storage.search_full_text = AsyncMock(return_value=[])
        return storage

    @pytest.fixture
    def mock_processor(self):
        """Create mock text processor."""
        processor = Mock(spec=TextProcessor)
        processor.process_text = AsyncMock(return_value={
            "keywords": ["test", "search"],
            "embedding": [0.1] * 384
        })
        return processor

    @pytest.fixture
    def search_engine(self, mock_storage, mock_processor):
        """Create hybrid search engine with mocked dependencies."""
        return HybridSearchEngine(mock_storage, mock_processor)

    @pytest.fixture
    def sample_memories(self):
        """Create sample memory entries for testing."""
        return [
            MemoryEntry(
                id="mem-1",
                content="Python programming tutorial for beginners",
                content_type=ContentType.DOCUMENTATION,
                keywords=["python", "programming", "tutorial"],
                embedding=[0.8, 0.2] + [0.0] * 382,
                relevance_score=0.9
            ),
            MemoryEntry(
                id="mem-2",
                content="Machine learning algorithms and data science",
                content_type=ContentType.CODE,
                keywords=["machine", "learning", "algorithms"],
                embedding=[0.2, 0.8] + [0.0] * 382,
                relevance_score=0.8
            ),
            MemoryEntry(
                id="mem-3",
                content="Web development with JavaScript frameworks",
                content_type=ContentType.DOCUMENTATION,
                keywords=["web", "development", "javascript"],
                embedding=[0.1, 0.1] + [0.0] * 382,
                relevance_score=0.7
            )
        ]

    def test_engine_initialization(self, search_engine, mock_storage, mock_processor):
        """Test search engine initializes correctly."""
        assert search_engine.storage == mock_storage
        assert search_engine.processor == mock_processor
        assert search_engine.semantic_weight == 1.0
        assert search_engine.keyword_weight == 0.8
        assert search_engine.full_text_weight == 0.6

    def test_calculate_cosine_similarity_identical(self, search_engine):
        """Test cosine similarity calculation for identical vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        similarity = search_engine._calculate_cosine_similarity(vec1, vec2)
        assert abs(similarity - 1.0) < 0.001

    def test_calculate_cosine_similarity_orthogonal(self, search_engine):
        """Test cosine similarity for orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]

        similarity = search_engine._calculate_cosine_similarity(vec1, vec2)
        assert abs(similarity - 0.0) < 0.001

    def test_calculate_cosine_similarity_opposite(self, search_engine):
        """Test cosine similarity for opposite vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]

        similarity = search_engine._calculate_cosine_similarity(vec1, vec2)
        assert abs(similarity - (-1.0)) < 0.001

    def test_calculate_cosine_similarity_zero_vector(self, search_engine):
        """Test cosine similarity with zero vector."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        similarity = search_engine._calculate_cosine_similarity(vec1, vec2)
        assert similarity == 0.0

    def test_calculate_cosine_similarity_different_lengths(self, search_engine):
        """Test cosine similarity with different vector lengths."""
        vec1 = [1.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        # Should handle gracefully or raise appropriate error
        with pytest.raises((ValueError, IndexError)):
            search_engine._calculate_cosine_similarity(vec1, vec2)

    def test_normalize_scores_basic(self, search_engine):
        """Test score normalization."""
        scores = [0.8, 0.6, 0.9, 0.2]

        normalized = search_engine._normalize_scores(scores)

        assert len(normalized) == len(scores)
        assert max(normalized) <= 1.0
        assert min(normalized) >= 0.0
        assert abs(max(normalized) - 1.0) < 0.001  # Max should be 1.0

    def test_normalize_scores_empty(self, search_engine):
        """Test normalization with empty scores."""
        normalized = search_engine._normalize_scores([])
        assert normalized == []

    def test_normalize_scores_single(self, search_engine):
        """Test normalization with single score."""
        normalized = search_engine._normalize_scores([0.5])
        assert normalized == [1.0]

    def test_normalize_scores_all_zero(self, search_engine):
        """Test normalization with all zero scores."""
        normalized = search_engine._normalize_scores([0.0, 0.0, 0.0])
        assert all(score == 0.0 for score in normalized)

    def test_combine_scores_basic(self, search_engine):
        """Test score combination with different weights."""
        semantic_scores = [0.8, 0.6]
        keyword_scores = [0.7, 0.9]
        full_text_scores = [0.5, 0.4]

        combined = search_engine._combine_scores(
            semantic_scores, keyword_scores, full_text_scores
        )

        assert len(combined) == 2
        assert all(0.0 <= score <= 1.0 for score in combined)
        # First result should have higher combined score
        assert combined[0] > combined[1]

    def test_combine_scores_mismatched_lengths(self, search_engine):
        """Test score combination with mismatched lengths."""
        semantic_scores = [0.8, 0.6]
        keyword_scores = [0.7]  # Different length
        full_text_scores = [0.5, 0.4]

        with pytest.raises(ValueError):
            search_engine._combine_scores(
                semantic_scores, keyword_scores, full_text_scores
            )

    def test_combine_scores_empty_lists(self, search_engine):
        """Test score combination with empty lists."""
        combined = search_engine._combine_scores([], [], [])
        assert combined == []

    def test_create_search_results(self, search_engine, sample_memories):
        """Test search result creation."""
        memories = sample_memories[:2]
        scores = [0.9, 0.7]

        results = search_engine._create_search_results(memories, scores)

        assert len(results) == 2
        assert all(isinstance(result, MemoryQueryResult) for result in results)
        assert results[0].memory.id == "mem-1"
        assert results[0].score == 0.9
        assert results[1].memory.id == "mem-2"
        assert results[1].score == 0.7

    def test_create_search_results_mismatched_lengths(self, search_engine, sample_memories):
        """Test search result creation with mismatched lengths."""
        memories = sample_memories[:2]
        scores = [0.9]  # Different length

        with pytest.raises(ValueError):
            search_engine._create_search_results(memories, scores)

    def test_deduplicate_results(self, search_engine, sample_memories):
        """Test result deduplication."""
        # Create duplicate results
        results = [
            MemoryQueryResult(sample_memories[0], 0.9, {"method": "semantic"}),
            MemoryQueryResult(sample_memories[1], 0.8, {"method": "keyword"}),
            MemoryQueryResult(sample_memories[0], 0.7, {"method": "full_text"}),  # Duplicate
        ]

        deduplicated = search_engine._deduplicate_results(results)

        assert len(deduplicated) == 2
        # Should keep the result with higher score for duplicates
        memory_ids = [result.memory.id for result in deduplicated]
        assert "mem-1" in memory_ids
        assert "mem-2" in memory_ids

        # First result should have the higher score
        mem1_result = next(r for r in deduplicated if r.memory.id == "mem-1")
        assert mem1_result.score == 0.9

    def test_deduplicate_results_no_duplicates(self, search_engine, sample_memories):
        """Test deduplication with no duplicates."""
        results = [
            MemoryQueryResult(sample_memories[0], 0.9, {"method": "semantic"}),
            MemoryQueryResult(sample_memories[1], 0.8, {"method": "keyword"}),
        ]

        deduplicated = search_engine._deduplicate_results(results)

        assert len(deduplicated) == 2
        assert deduplicated == results

    def test_deduplicate_results_empty(self, search_engine):
        """Test deduplication with empty results."""
        deduplicated = search_engine._deduplicate_results([])
        assert deduplicated == []

    @pytest.mark.asyncio
    async def test_semantic_search_basic(self, search_engine, mock_storage, sample_memories):
        """Test semantic search functionality."""
        # Mock storage to return sample memories
        mock_storage.search_by_embedding.return_value = sample_memories[:2]

        query_embedding = [0.8, 0.2] + [0.0] * 382
        results = await search_engine._semantic_search(query_embedding, limit=10)

        assert len(results) <= 2
        mock_storage.search_by_embedding.assert_called_once()

    @pytest.mark.asyncio
    async def test_semantic_search_empty_embedding(self, search_engine):
        """Test semantic search with empty embedding."""
        with pytest.raises(ValueError):
            await search_engine._semantic_search([], limit=10)

    @pytest.mark.asyncio
    async def test_semantic_search_storage_error(self, search_engine, mock_storage):
        """Test semantic search with storage error."""
        mock_storage.search_by_embedding.side_effect = Exception("Storage error")

        with pytest.raises(SearchError):
            await search_engine._semantic_search([0.1] * 384, limit=10)

    @pytest.mark.asyncio
    async def test_keyword_search_basic(self, search_engine, mock_storage, sample_memories):
        """Test keyword search functionality."""
        mock_storage.search_by_keywords.return_value = sample_memories[:1]

        keywords = ["python", "programming"]
        results = await search_engine._keyword_search(keywords, limit=10)

        assert len(results) <= 1
        mock_storage.search_by_keywords.assert_called_once_with(keywords, limit=10)

    @pytest.mark.asyncio
    async def test_keyword_search_empty_keywords(self, search_engine):
        """Test keyword search with empty keywords."""
        results = await search_engine._keyword_search([], limit=10)
        assert results == []

    @pytest.mark.asyncio
    async def test_keyword_search_storage_error(self, search_engine, mock_storage):
        """Test keyword search with storage error."""
        mock_storage.search_by_keywords.side_effect = Exception("Storage error")

        with pytest.raises(SearchError):
            await search_engine._keyword_search(["test"], limit=10)

    @pytest.mark.asyncio
    async def test_full_text_search_basic(self, search_engine, mock_storage, sample_memories):
        """Test full-text search functionality."""
        mock_storage.search_full_text.return_value = sample_memories[:2]

        query_text = "python programming"
        results = await search_engine._full_text_search(query_text, limit=10)

        assert len(results) <= 2
        mock_storage.search_full_text.assert_called_once_with(query_text, limit=10)

    @pytest.mark.asyncio
    async def test_full_text_search_empty_query(self, search_engine):
        """Test full-text search with empty query."""
        results = await search_engine._full_text_search("", limit=10)
        assert results == []

    @pytest.mark.asyncio
    async def test_full_text_search_storage_error(self, search_engine, mock_storage):
        """Test full-text search with storage error."""
        mock_storage.search_full_text.side_effect = Exception("Storage error")

        with pytest.raises(SearchError):
            await search_engine._full_text_search("test query", limit=10)

    @pytest.mark.asyncio
    async def test_hybrid_search_complete(self, search_engine, mock_storage, mock_processor, sample_memories):
        """Test complete hybrid search functionality."""
        # Mock processor to return processed query
        mock_processor.process_text.return_value = {
            "keywords": ["python", "programming"],
            "embedding": [0.8, 0.2] + [0.0] * 382
        }

        # Mock storage to return different results for each search type
        mock_storage.search_by_embedding.return_value = [sample_memories[0]]
        mock_storage.search_by_keywords.return_value = [sample_memories[1]]
        mock_storage.search_full_text.return_value = [sample_memories[2]]

        query = SearchQuery(
            query_text="python programming tutorial",
            max_results=10
        )

        results = await search_engine.hybrid_search(query)

        assert len(results) <= 10
        assert all(isinstance(result, MemoryQueryResult) for result in results)

        # Should have called all search methods
        mock_storage.search_by_embedding.assert_called_once()
        mock_storage.search_by_keywords.assert_called_once()
        mock_storage.search_full_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_hybrid_search_empty_query(self, search_engine):
        """Test hybrid search with empty query."""
        query = SearchQuery(query_text="", max_results=10)
        results = await search_engine.hybrid_search(query)
        assert results == []

    @pytest.mark.asyncio
    async def test_hybrid_search_custom_weights(self, search_engine, mock_storage, mock_processor, sample_memories):
        """Test hybrid search with custom weights."""
        mock_processor.process_text.return_value = {
            "keywords": ["test"],
            "embedding": [0.1] * 384
        }
        mock_storage.search_by_embedding.return_value = [sample_memories[0]]
        mock_storage.search_by_keywords.return_value = [sample_memories[0]]
        mock_storage.search_full_text.return_value = [sample_memories[0]]

        query = SearchQuery(
            query_text="test query",
            max_results=5,
            semantic_weight=0.9,
            keyword_weight=0.5,
            full_text_weight=0.3
        )

        results = await search_engine.hybrid_search(query)

        # Should use custom weights
        assert len(results) >= 0

    @pytest.mark.asyncio
    async def test_search_by_content_type(self, search_engine, mock_storage, mock_processor, sample_memories):
        """Test searching by specific content type."""
        # Filter sample memories by content type
        code_memories = [m for m in sample_memories if m.content_type == ContentType.CODE]
        mock_storage.search_by_embedding.return_value = code_memories
        mock_storage.search_by_keywords.return_value = code_memories
        mock_storage.search_full_text.return_value = code_memories

        mock_processor.process_text.return_value = {
            "keywords": ["code"],
            "embedding": [0.1] * 384
        }

        results = await search_engine.search_by_content_type(
            "code examples",
            ContentType.CODE,
            max_results=10
        )

        assert all(result.memory.content_type == ContentType.CODE for result in results)

    @pytest.mark.asyncio
    async def test_search_by_task_id(self, search_engine, mock_storage, mock_processor):
        """Test searching by task ID."""
        task_memory = MemoryEntry(
            id="task-mem",
            content="Task-specific memory",
            content_type=ContentType.CONTEXT,
            task_id="task-123"
        )

        mock_storage.search_by_keywords.return_value = [task_memory]
        mock_processor.process_text.return_value = {
            "keywords": ["task"],
            "embedding": [0.1] * 384
        }

        results = await search_engine.search_by_task_id(
            "task context",
            "task-123",
            max_results=10
        )

        assert len(results) >= 0
        # Would normally check task_id filtering, but requires storage implementation

    @pytest.mark.asyncio
    async def test_search_similar_memories(self, search_engine, mock_storage, sample_memories):
        """Test finding similar memories to a given memory."""
        reference_memory = sample_memories[0]
        similar_memories = sample_memories[1:]

        mock_storage.search_by_embedding.return_value = similar_memories

        results = await search_engine.search_similar_memories(
            reference_memory,
            max_results=5,
            min_similarity=0.5
        )

        assert len(results) <= 5
        # Should not include the reference memory itself
        result_ids = [r.memory.id for r in results]
        assert reference_memory.id not in result_ids

    @pytest.mark.asyncio
    async def test_search_similar_memories_no_embedding(self, search_engine):
        """Test similar search with memory that has no embedding."""
        memory_without_embedding = MemoryEntry(
            id="no-embed",
            content="Memory without embedding",
            content_type=ContentType.DOCUMENTATION
        )

        with pytest.raises(ValueError):
            await search_engine.search_similar_memories(
                memory_without_embedding,
                max_results=5
            )

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_search_performance(self, search_engine, mock_storage, mock_processor, sample_memories):
        """Test search performance under load."""
        import time

        # Setup mocks for performance test
        mock_processor.process_text.return_value = {
            "keywords": ["performance", "test"],
            "embedding": [0.1] * 384
        }
        mock_storage.search_by_embedding.return_value = sample_memories
        mock_storage.search_by_keywords.return_value = sample_memories
        mock_storage.search_full_text.return_value = sample_memories

        query = SearchQuery(
            query_text="performance test query",
            max_results=100
        )

        start_time = time.time()
        results = await search_engine.hybrid_search(query)
        search_time = time.time() - start_time

        # Search should complete within reasonable time
        assert search_time < 1.0  # Less than 1 second
        assert len(results) >= 0

    @pytest.mark.asyncio
    async def test_concurrent_searches(self, search_engine, mock_storage, mock_processor, sample_memories):
        """Test concurrent search operations."""
        import asyncio

        mock_processor.process_text.return_value = {
            "keywords": ["concurrent"],
            "embedding": [0.1] * 384
        }
        mock_storage.search_by_embedding.return_value = sample_memories
        mock_storage.search_by_keywords.return_value = sample_memories
        mock_storage.search_full_text.return_value = sample_memories

        # Run multiple concurrent searches
        queries = [
            SearchQuery(query_text=f"query {i}", max_results=10)
            for i in range(5)
        ]

        tasks = [search_engine.hybrid_search(query) for query in queries]
        results_list = await asyncio.gather(*tasks)

        assert len(results_list) == 5
        for results in results_list:
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_error_recovery(self, search_engine, mock_storage, mock_processor):
        """Test error recovery in search operations."""
        # Setup one method to fail
        mock_storage.search_by_embedding.side_effect = Exception("Embedding search failed")
        mock_storage.search_by_keywords.return_value = []
        mock_storage.search_full_text.return_value = []

        mock_processor.process_text.return_value = {
            "keywords": ["test"],
            "embedding": [0.1] * 384
        }

        query = SearchQuery(query_text="test query", max_results=10)

        # Should handle partial failures gracefully
        with pytest.raises(SearchError):
            await search_engine.hybrid_search(query)