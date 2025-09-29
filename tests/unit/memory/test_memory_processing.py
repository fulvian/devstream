"""
Unit tests for memory text processing functionality.

Context7-validated patterns for NLP and embedding testing:
- Text feature extraction validation
- Embedding generation mocking
- Batch processing efficiency
- Error handling for NLP pipelines
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, AsyncMock

from devstream.memory.processing import TextProcessor
from devstream.memory.models import MemoryEntry, ContentType, ContentFormat
from devstream.memory.exceptions import ProcessingError, EmbeddingError
from devstream.ollama.client import OllamaClient
from devstream.ollama.config import OllamaConfig


@pytest.mark.unit
@pytest.mark.memory
class TestTextProcessor:
    """Test text processing functionality with Context7-validated patterns."""

    @pytest.fixture
    def mock_ollama_config(self):
        """Create mock Ollama config for testing."""
        return OllamaConfig(
            base_url="http://localhost:11434",
            timeout=30.0
        )

    @pytest.fixture
    def mock_ollama_client(self, mock_ollama_config):
        """Create mock Ollama client."""
        client = Mock(spec=OllamaClient)
        client.config = mock_ollama_config
        client.is_available = AsyncMock(return_value=True)
        client.generate_embedding = AsyncMock(return_value=[0.1] * 384)
        client.generate_text = AsyncMock(return_value="Test generated text")
        return client

    @pytest.fixture
    def text_processor(self, mock_ollama_client):
        """Create text processor with mocked dependencies."""
        return TextProcessor(mock_ollama_client)

    def test_processor_initialization(self, text_processor, mock_ollama_client):
        """Test processor initializes correctly."""
        assert text_processor.client == mock_ollama_client
        assert text_processor.stop_words is not None
        assert len(text_processor.stop_words) > 0

    @pytest.mark.asyncio
    async def test_extract_keywords_basic(self, text_processor):
        """Test basic keyword extraction."""
        text = "This is a test document about machine learning and artificial intelligence."

        keywords = await text_processor._extract_keywords(text)

        assert isinstance(keywords, list)
        assert len(keywords) > 0
        # Should extract meaningful keywords, not stop words
        assert "machine" in " ".join(keywords).lower()
        assert "learning" in " ".join(keywords).lower()
        assert "the" not in keywords  # Stop word should be filtered

    @pytest.mark.asyncio
    async def test_extract_keywords_empty_text(self, text_processor):
        """Test keyword extraction with empty text."""
        keywords = await text_processor._extract_keywords("")
        assert keywords == []

    @pytest.mark.asyncio
    async def test_extract_keywords_stop_words_only(self, text_processor):
        """Test keyword extraction with only stop words."""
        text = "the and or but"
        keywords = await text_processor._extract_keywords(text)
        assert len(keywords) == 0

    @pytest.mark.asyncio
    async def test_extract_entities_basic(self, text_processor):
        """Test basic entity extraction."""
        text = "Python is a programming language used for machine learning."

        entities = await text_processor._extract_entities(text)

        assert isinstance(entities, list)
        assert len(entities) > 0
        # Should find Python as a technology entity
        entity_texts = [e["text"].lower() for e in entities]
        assert any("python" in text for text in entity_texts)

    @pytest.mark.asyncio
    async def test_extract_entities_empty_text(self, text_processor):
        """Test entity extraction with empty text."""
        entities = await text_processor._extract_entities("")
        assert entities == []

    def test_calculate_complexity_simple(self, text_processor):
        """Test complexity calculation for simple text."""
        text = "This is simple."
        complexity = text_processor._calculate_complexity(text)
        assert isinstance(complexity, int)
        assert 1 <= complexity <= 3  # Simple text should have low complexity

    def test_calculate_complexity_complex(self, text_processor):
        """Test complexity calculation for complex text."""
        text = """
        The implementation of asynchronous programming paradigms in distributed
        microservices architectures requires sophisticated understanding of
        concurrent execution models and thread-safe data synchronization mechanisms.
        """
        complexity = text_processor._calculate_complexity(text)
        assert isinstance(complexity, int)
        assert 7 <= complexity <= 10  # Complex text should have high complexity

    def test_calculate_complexity_empty(self, text_processor):
        """Test complexity calculation for empty text."""
        complexity = text_processor._calculate_complexity("")
        assert complexity == 1  # Minimum complexity

    def test_analyze_sentiment_positive(self, text_processor):
        """Test sentiment analysis for positive text."""
        text = "This is amazing and wonderful! I love it!"
        sentiment = text_processor._analyze_sentiment(text)
        assert isinstance(sentiment, float)
        assert sentiment > 0  # Should be positive

    def test_analyze_sentiment_negative(self, text_processor):
        """Test sentiment analysis for negative text."""
        text = "This is terrible and awful! I hate it!"
        sentiment = text_processor._analyze_sentiment(text)
        assert isinstance(sentiment, float)
        assert sentiment < 0  # Should be negative

    def test_analyze_sentiment_neutral(self, text_processor):
        """Test sentiment analysis for neutral text."""
        text = "This is a factual statement about programming."
        sentiment = text_processor._analyze_sentiment(text)
        assert isinstance(sentiment, float)
        assert -0.3 <= sentiment <= 0.3  # Should be roughly neutral

    def test_analyze_sentiment_empty(self, text_processor):
        """Test sentiment analysis for empty text."""
        sentiment = text_processor._analyze_sentiment("")
        assert sentiment == 0.0  # Empty text should be neutral

    def test_calculate_stats(self, text_processor):
        """Test text statistics calculation."""
        text = "This is a test. Another sentence here."

        stats = text_processor._calculate_stats(text)

        assert "word_count" in stats
        assert "sentence_count" in stats
        assert "avg_word_length" in stats
        assert "reading_level" in stats

        assert stats["word_count"] == 8
        assert stats["sentence_count"] == 2
        assert stats["avg_word_length"] > 0
        assert isinstance(stats["reading_level"], (int, float))

    def test_calculate_stats_empty(self, text_processor):
        """Test statistics calculation for empty text."""
        stats = text_processor._calculate_stats("")

        assert stats["word_count"] == 0
        assert stats["sentence_count"] == 0
        assert stats["avg_word_length"] == 0
        assert stats["reading_level"] == 0

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, text_processor, mock_ollama_client):
        """Test successful embedding generation."""
        text = "Test text for embedding"

        embedding = await text_processor._generate_embedding(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)
        mock_ollama_client.generate_embedding.assert_called_once_with(
            text, model="nomic-embed-text"
        )

    @pytest.mark.asyncio
    async def test_generate_embedding_error(self, text_processor, mock_ollama_client):
        """Test embedding generation error handling."""
        mock_ollama_client.generate_embedding.side_effect = Exception("Ollama error")

        with pytest.raises(EmbeddingError):
            await text_processor._generate_embedding("test text")

    @pytest.mark.asyncio
    async def test_process_text_basic(self, text_processor):
        """Test basic text processing."""
        text = "This is a comprehensive test document for natural language processing."

        features = await text_processor.process_text(text, include_embedding=True)

        assert "keywords" in features
        assert "entities" in features
        assert "complexity_score" in features
        assert "sentiment" in features
        assert "stats" in features
        assert "embedding" in features

        assert isinstance(features["keywords"], list)
        assert isinstance(features["entities"], list)
        assert isinstance(features["complexity_score"], int)
        assert isinstance(features["sentiment"], float)
        assert isinstance(features["stats"], dict)
        assert isinstance(features["embedding"], list)

    @pytest.mark.asyncio
    async def test_process_text_no_embedding(self, text_processor):
        """Test text processing without embedding generation."""
        text = "Test text without embedding"

        features = await text_processor.process_text(text, include_embedding=False)

        assert "embedding" not in features
        assert "keywords" in features
        assert "entities" in features

    @pytest.mark.asyncio
    async def test_process_text_empty(self, text_processor):
        """Test processing of empty text."""
        features = await text_processor.process_text("", include_embedding=False)

        assert features["keywords"] == []
        assert features["entities"] == []
        assert features["complexity_score"] == 1
        assert features["sentiment"] == 0.0

    @pytest.mark.asyncio
    async def test_process_memory_entry(self, text_processor):
        """Test processing of complete memory entry."""
        memory = MemoryEntry(
            id="test-memory-1",
            content="This is a test memory entry for processing validation.",
            content_type=ContentType.DOCUMENTATION,
            content_format=ContentFormat.MARKDOWN
        )

        processed = await text_processor.process_memory_entry(memory)

        assert processed.id == memory.id
        assert processed.content == memory.content
        assert len(processed.keywords) > 0
        assert len(processed.entities) >= 0
        assert 1 <= processed.complexity_score <= 10
        assert -1.0 <= processed.sentiment <= 1.0
        assert processed.embedding is not None
        assert len(processed.embedding) == 384
        assert "processing" in processed.context_snapshot

    @pytest.mark.asyncio
    async def test_process_memory_entry_preserve_metadata(self, text_processor):
        """Test that memory entry processing preserves existing metadata."""
        memory = MemoryEntry(
            id="test-metadata",
            content="Test content",
            content_type=ContentType.CODE,
            keywords=["existing", "keyword"],
            task_id="task-123",
            related_memory_ids=["mem-1", "mem-2"]
        )

        processed = await text_processor.process_memory_entry(memory)

        # Should preserve original metadata while adding processing results
        assert processed.task_id == "task-123"
        assert processed.related_memory_ids == ["mem-1", "mem-2"]
        assert "existing" in processed.keywords
        assert "keyword" in processed.keywords

    @pytest.mark.asyncio
    async def test_batch_process(self, text_processor):
        """Test batch processing of multiple texts."""
        texts = [
            "First document about machine learning algorithms.",
            "Second document covering data science methodologies.",
            "Third document on software engineering best practices."
        ]

        results = await text_processor.batch_process(texts, batch_size=2)

        assert len(results) == 3
        for i, result in enumerate(results):
            assert "keywords" in result
            assert "entities" in result
            assert "complexity_score" in result
            assert isinstance(result["keywords"], list)

    @pytest.mark.asyncio
    async def test_batch_process_empty_list(self, text_processor):
        """Test batch processing with empty list."""
        results = await text_processor.batch_process([])
        assert results == []

    @pytest.mark.asyncio
    async def test_batch_process_single_item(self, text_processor):
        """Test batch processing with single item."""
        texts = ["Single test document"]
        results = await text_processor.batch_process(texts, batch_size=5)

        assert len(results) == 1
        assert "keywords" in results[0]

    @pytest.mark.asyncio
    async def test_process_text_error_handling(self, text_processor, mock_ollama_client):
        """Test error handling during text processing."""
        mock_ollama_client.generate_embedding.side_effect = Exception("Network error")

        with pytest.raises(ProcessingError):
            await text_processor.process_text("test", include_embedding=True)

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, text_processor):
        """Test concurrent text processing."""
        import asyncio

        texts = [f"Document {i} content" for i in range(5)]

        # Process texts concurrently
        tasks = [
            text_processor.process_text(text, include_embedding=False)
            for text in texts
        ]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for result in results:
            assert "keywords" in result
            assert "complexity_score" in result

    def test_stop_words_filtering(self, text_processor):
        """Test that stop words are properly filtered."""
        # Test that common stop words are in the filter
        assert "the" in text_processor.stop_words
        assert "and" in text_processor.stop_words
        assert "or" in text_processor.stop_words
        assert "but" in text_processor.stop_words

    @pytest.mark.asyncio
    async def test_memory_entry_content_types(self, text_processor):
        """Test processing different content types."""
        content_types = [
            ContentType.CODE,
            ContentType.DOCUMENTATION,
            ContentType.CONTEXT,
            ContentType.OUTPUT,
            ContentType.ERROR
        ]

        for content_type in content_types:
            memory = MemoryEntry(
                id=f"test-{content_type.value}",
                content=f"Test content for {content_type.value}",
                content_type=content_type
            )

            processed = await text_processor.process_memory_entry(memory)
            assert processed.content_type == content_type
            assert len(processed.keywords) >= 0

    @pytest.mark.asyncio
    async def test_processing_large_text(self, text_processor):
        """Test processing of large text documents."""
        # Create a large text document
        large_text = " ".join([
            "This is a comprehensive document with many sentences and complex vocabulary."
        ] * 100)  # 100 repetitions

        features = await text_processor.process_text(large_text, include_embedding=False)

        assert features["stats"]["word_count"] > 1000
        assert features["complexity_score"] >= 1
        assert len(features["keywords"]) > 0

    @pytest.mark.asyncio
    async def test_multilingual_text_handling(self, text_processor):
        """Test handling of non-English text."""
        # Test with some non-English text
        text = "Ceci est un document de test en français avec du vocabulaire technique."

        features = await text_processor.process_text(text, include_embedding=False)

        # Should still extract features even for non-English text
        assert isinstance(features["keywords"], list)
        assert isinstance(features["complexity_score"], int)
        assert isinstance(features["sentiment"], float)

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_processing_performance(self, text_processor):
        """Test text processing performance."""
        import time

        text = "Performance test document with moderate complexity and multiple concepts."

        start_time = time.time()
        features = await text_processor.process_text(text, include_embedding=False)
        processing_time = time.time() - start_time

        # Processing should complete within reasonable time
        assert processing_time < 1.0  # Less than 1 second
        assert len(features["keywords"]) > 0