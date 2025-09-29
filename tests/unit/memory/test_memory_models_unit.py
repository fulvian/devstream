"""
Simple unit tests for memory models and basic functionality.

Focus on testing the core memory models without external dependencies.
"""

import pytest
from datetime import datetime
from typing import List

from devstream.memory.models import (
    MemoryEntry,
    SearchQuery,
    ContentType,
    ContentFormat,
    MemoryQueryResult,
    ContextAssemblyResult
)
from devstream.memory.exceptions import (
    MemoryError,
    StorageError,
    SearchError,
    ProcessingError,
    ContextError,
    EmbeddingError,
    VectorSearchError,
    TokenBudgetError
)


@pytest.mark.unit
@pytest.mark.memory
class TestMemoryModels:
    """Test memory system models."""

    def test_content_type_enum(self):
        """Test ContentType enum values."""
        assert ContentType.CODE.value == "code"
        assert ContentType.DOCUMENTATION.value == "documentation"
        assert ContentType.CONTEXT.value == "context"
        assert ContentType.OUTPUT.value == "output"
        assert ContentType.ERROR.value == "error"
        assert ContentType.DECISION.value == "decision"
        assert ContentType.LEARNING.value == "learning"

    def test_content_format_enum(self):
        """Test ContentFormat enum values."""
        assert ContentFormat.TEXT.value == "text"
        assert ContentFormat.MARKDOWN.value == "markdown"
        assert ContentFormat.CODE.value == "code"
        assert ContentFormat.JSON.value == "json"
        assert ContentFormat.YAML.value == "yaml"

    def test_memory_entry_basic_creation(self):
        """Test basic memory entry creation."""
        memory = MemoryEntry(
            id="test-memory-1",
            content="This is a test memory entry.",
            content_type=ContentType.DOCUMENTATION
        )

        assert memory.id == "test-memory-1"
        assert memory.content == "This is a test memory entry."
        assert memory.content_type == ContentType.DOCUMENTATION
        assert memory.content_format == ContentFormat.TEXT
        assert memory.keywords == []
        assert memory.entities == []
        assert memory.sentiment == 0.0
        assert memory.complexity_score == 1
        assert memory.embedding is None
        assert memory.access_count == 0
        assert not memory.is_archived

    def test_memory_entry_with_all_fields(self):
        """Test memory entry creation with all fields."""
        now = datetime.utcnow()
        memory = MemoryEntry(
            id="comprehensive-memory",
            content="Comprehensive test memory entry.",
            content_type=ContentType.CODE,
            content_format=ContentFormat.PYTHON,
            keywords=["test", "comprehensive", "memory"],
            entities=[{"text": "test", "label": "ACTIVITY"}],
            sentiment=0.5,
            complexity_score=7,
            embedding=[0.1, 0.2, 0.3],
            embedding_model="test-model",
            embedding_dimension=3,
            context_snapshot={"test": "context"},
            related_memory_ids=["related-1", "related-2"],
            access_count=5,
            relevance_score=0.8,
            is_archived=True,
            task_id="task-123",
            phase_id="phase-456",
            plan_id="plan-789",
            created_at=now,
            updated_at=now
        )

        assert memory.id == "comprehensive-memory"
        assert memory.content_type == ContentType.CODE
        assert memory.content_format == ContentFormat.PYTHON
        assert memory.keywords == ["test", "comprehensive", "memory"]
        assert memory.entities == [{"text": "test", "label": "ACTIVITY"}]
        assert memory.sentiment == 0.5
        assert memory.complexity_score == 7
        assert memory.embedding == [0.1, 0.2, 0.3]
        assert memory.embedding_dimension == 3
        assert memory.context_snapshot == {"test": "context"}
        assert memory.related_memory_ids == ["related-1", "related-2"]
        assert memory.access_count == 5
        assert memory.relevance_score == 0.8
        assert memory.is_archived
        assert memory.task_id == "task-123"
        assert memory.phase_id == "phase-456"
        assert memory.plan_id == "plan-789"

    def test_memory_entry_embedding_validation(self):
        """Test embedding dimension validation."""
        # Valid embedding
        memory = MemoryEntry(
            id="valid-embedding",
            content="Test content",
            content_type=ContentType.DOCUMENTATION,
            embedding=[0.1, 0.2, 0.3, 0.4],
            embedding_dimension=4
        )
        assert len(memory.embedding) == 4

        # Invalid embedding dimension
        with pytest.raises(ValueError, match="Embedding length .* doesn't match dimension"):
            MemoryEntry(
                id="invalid-embedding",
                content="Test content",
                content_type=ContentType.DOCUMENTATION,
                embedding=[0.1, 0.2],  # Length 2
                embedding_dimension=4  # Expected 4
            )

    def test_memory_entry_set_embedding(self):
        """Test setting embedding from numpy array."""
        import numpy as np

        memory = MemoryEntry(
            id="numpy-embedding",
            content="Test content",
            content_type=ContentType.DOCUMENTATION
        )

        embedding_array = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        memory.set_embedding(embedding_array)

        assert memory.embedding == [0.1, 0.2, 0.3, 0.4]
        assert memory.embedding_dimension == 4

    def test_memory_entry_get_embedding_array(self):
        """Test getting embedding as numpy array."""
        import numpy as np

        memory = MemoryEntry(
            id="array-test",
            content="Test content",
            content_type=ContentType.DOCUMENTATION,
            embedding=[0.1, 0.2, 0.3]
        )

        array = memory.get_embedding_array()
        assert isinstance(array, np.ndarray)
        assert array.dtype == np.float32
        assert list(array) == [0.1, 0.2, 0.3]

        # Test with no embedding
        memory_no_embed = MemoryEntry(
            id="no-embed",
            content="No embedding",
            content_type=ContentType.DOCUMENTATION
        )
        assert memory_no_embed.get_embedding_array() is None

    def test_search_query_basic(self):
        """Test basic search query creation."""
        query = SearchQuery(
            query_text="test search",
            max_results=10
        )

        assert query.query_text == "test search"
        assert query.max_results == 10
        assert query.semantic_weight == 1.0
        assert query.keyword_weight == 0.8
        assert query.full_text_weight == 0.6
        assert query.min_relevance_score == 0.1

    def test_search_query_validation(self):
        """Test search query validation."""
        # Valid query
        query = SearchQuery(
            query_text="valid query",
            max_results=5,
            semantic_weight=0.9,
            keyword_weight=0.7,
            full_text_weight=0.5,
            min_relevance_score=0.3
        )
        assert query.max_results == 5

        # Invalid max_results
        with pytest.raises(ValueError):
            SearchQuery(
                query_text="test",
                max_results=0  # Should be >= 1
            )

        # Invalid weights
        with pytest.raises(ValueError):
            SearchQuery(
                query_text="test",
                semantic_weight=-1.0  # Should be >= 0
            )

        with pytest.raises(ValueError):
            SearchQuery(
                query_text="test",
                min_relevance_score=-0.5  # Should be >= 0
            )

        with pytest.raises(ValueError):
            SearchQuery(
                query_text="test",
                min_relevance_score=1.5  # Should be <= 1
            )

    def test_memory_query_result_basic(self):
        """Test memory query result creation."""
        memory = MemoryEntry(
            id="result-memory",
            content="Result test memory",
            content_type=ContentType.DOCUMENTATION
        )

        result = MemoryQueryResult(
            memory=memory,
            relevance_score=0.85,
            search_metadata={"method": "semantic", "distance": 0.15}
        )

        assert result.memory == memory
        assert result.relevance_score == 0.85
        assert result.search_metadata["method"] == "semantic"
        assert result.search_metadata["distance"] == 0.15

    def test_memory_query_result_validation(self):
        """Test memory query result validation."""
        memory = MemoryEntry(
            id="validation-test",
            content="Validation test",
            content_type=ContentType.DOCUMENTATION
        )

        # Valid score
        result = MemoryQueryResult(
            memory=memory,
            relevance_score=0.75
        )
        assert result.relevance_score == 0.75

        # Invalid relevance score
        with pytest.raises(ValueError):
            MemoryQueryResult(
                memory=memory,
                relevance_score=1.5  # Should be <= 1.0
            )

        with pytest.raises(ValueError):
            MemoryQueryResult(
                memory=memory,
                relevance_score=-0.1  # Should be >= 0.0
            )

    def test_context_assembly_result_basic(self):
        """Test context assembly result creation."""
        memory1 = MemoryEntry(
            id="context-mem-1",
            content="First memory for context",
            content_type=ContentType.DOCUMENTATION
        )
        memory2 = MemoryEntry(
            id="context-mem-2",
            content="Second memory for context",
            content_type=ContentType.CODE
        )

        memories = [memory1, memory2]
        result = ContextAssemblyResult(
            memories=memories,
            assembled_context="Combined context from memories",
            total_tokens=150,
            query_metadata={"strategy": "relevance"},
            assembly_metadata={"truncated": False, "method": "priority"}
        )

        assert len(result.memories) == 2
        assert result.assembled_context == "Combined context from memories"
        assert result.total_tokens == 150
        assert result.query_metadata["strategy"] == "relevance"
        assert result.assembly_metadata["truncated"] is False

    def test_context_assembly_result_validation(self):
        """Test context assembly result validation."""
        memory = MemoryEntry(
            id="validation-memory",
            content="Validation test",
            content_type=ContentType.DOCUMENTATION
        )

        # Valid token count
        result = ContextAssemblyResult(
            memories=[memory],
            assembled_context="Test context",
            total_tokens=100
        )
        assert result.total_tokens == 100

        # Invalid token count
        with pytest.raises(ValueError):
            ContextAssemblyResult(
                memories=[memory],
                assembled_context="Test context",
                total_tokens=-10  # Should be >= 0
            )


@pytest.mark.unit
@pytest.mark.memory
class TestMemoryExceptions:
    """Test memory system exceptions."""

    def test_memory_error_basic(self):
        """Test basic memory error."""
        error = MemoryError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.details == {}

    def test_memory_error_with_details(self):
        """Test memory error with details."""
        details = {"error_code": "MEM001", "context": "test_context"}
        error = MemoryError("Detailed error", details=details)

        assert error.message == "Detailed error"
        assert error.details == details
        assert error.details["error_code"] == "MEM001"

    def test_storage_error(self):
        """Test storage error inheritance."""
        error = StorageError("Storage failed")
        assert isinstance(error, MemoryError)
        assert str(error) == "Storage failed"

    def test_search_error(self):
        """Test search error inheritance."""
        error = SearchError("Search failed")
        assert isinstance(error, MemoryError)
        assert str(error) == "Search failed"

    def test_processing_error(self):
        """Test processing error inheritance."""
        error = ProcessingError("Processing failed")
        assert isinstance(error, MemoryError)
        assert str(error) == "Processing failed"

    def test_context_error(self):
        """Test context error inheritance."""
        error = ContextError("Context assembly failed")
        assert isinstance(error, MemoryError)
        assert str(error) == "Context assembly failed"

    def test_embedding_error(self):
        """Test embedding error inheritance."""
        error = EmbeddingError("Embedding generation failed")
        assert isinstance(error, ProcessingError)
        assert isinstance(error, MemoryError)
        assert str(error) == "Embedding generation failed"

    def test_vector_search_error(self):
        """Test vector search error inheritance."""
        error = VectorSearchError("Vector search failed")
        assert isinstance(error, SearchError)
        assert isinstance(error, MemoryError)
        assert str(error) == "Vector search failed"

    def test_token_budget_error(self):
        """Test token budget error inheritance."""
        error = TokenBudgetError("Token budget exceeded")
        assert isinstance(error, ContextError)
        assert isinstance(error, MemoryError)
        assert str(error) == "Token budget exceeded"

    def test_exception_hierarchy(self):
        """Test exception hierarchy is correct."""
        # Test inheritance chain
        assert issubclass(StorageError, MemoryError)
        assert issubclass(SearchError, MemoryError)
        assert issubclass(ProcessingError, MemoryError)
        assert issubclass(ContextError, MemoryError)

        assert issubclass(EmbeddingError, ProcessingError)
        assert issubclass(VectorSearchError, SearchError)
        assert issubclass(TokenBudgetError, ContextError)

        # Test they all inherit from Exception
        assert issubclass(MemoryError, Exception)
        assert issubclass(StorageError, Exception)
        assert issubclass(EmbeddingError, Exception)


@pytest.mark.unit
@pytest.mark.memory
class TestMemoryModelEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_memory_entry_empty_content(self):
        """Test memory entry with empty content."""
        memory = MemoryEntry(
            id="empty-content",
            content="",
            content_type=ContentType.DOCUMENTATION
        )
        assert memory.content == ""
        assert memory.complexity_score == 1  # Should have minimum complexity

    def test_memory_entry_very_long_content(self):
        """Test memory entry with very long content."""
        long_content = "Very long content " * 1000
        memory = MemoryEntry(
            id="long-content",
            content=long_content,
            content_type=ContentType.DOCUMENTATION
        )
        assert len(memory.content) > 10000
        assert memory.id == "long-content"

    def test_memory_entry_boundary_values(self):
        """Test memory entry with boundary values."""
        memory = MemoryEntry(
            id="boundary-test",
            content="Boundary test",
            content_type=ContentType.DOCUMENTATION,
            sentiment=-1.0,  # Minimum
            complexity_score=10,  # Maximum
            relevance_score=1.0,  # Maximum
            access_count=0  # Minimum
        )

        assert memory.sentiment == -1.0
        assert memory.complexity_score == 10
        assert memory.relevance_score == 1.0
        assert memory.access_count == 0

    def test_search_query_boundary_values(self):
        """Test search query with boundary values."""
        query = SearchQuery(
            query_text="boundary test",
            max_results=1,  # Minimum
            semantic_weight=0.0,  # Minimum
            keyword_weight=0.0,  # Minimum
            full_text_weight=0.0,  # Minimum
            min_relevance_score=0.0  # Minimum
        )

        assert query.max_results == 1
        assert query.semantic_weight == 0.0
        assert query.min_relevance_score == 0.0

    def test_memory_entry_special_characters(self):
        """Test memory entry with special characters."""
        memory = MemoryEntry(
            id="special-chars-æøå-日本語-🎉",
            content="Content with special chars: æøå 日本語 🎉 !@#$%^&*()",
            content_type=ContentType.DOCUMENTATION,
            keywords=["special", "characters", "æøå", "日本語", "🎉"]
        )

        assert "æøå" in memory.id
        assert "日本語" in memory.content
        assert "🎉" in memory.keywords

    def test_memory_entry_large_embedding(self):
        """Test memory entry with large embedding."""
        large_embedding = [0.1] * 1536  # Large embedding dimension
        memory = MemoryEntry(
            id="large-embedding",
            content="Content with large embedding",
            content_type=ContentType.DOCUMENTATION,
            embedding=large_embedding,
            embedding_dimension=1536
        )

        assert len(memory.embedding) == 1536
        assert memory.embedding_dimension == 1536