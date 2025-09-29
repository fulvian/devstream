"""
Unit tests for Ollama Pydantic models.

Tests model validation, serialization, and business logic.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
import numpy as np

from devstream.ollama.models import (
    ModelInfo,
    EmbeddingRequest,
    EmbeddingResponse,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    BatchRequest,
    BatchResponse,
    HealthCheckResponse,
    ModelPullRequest,
    ModelPullProgress,
)


class TestModelInfo:
    """Test ModelInfo model."""

    def test_valid_model_info(self):
        """Test valid model info creation."""
        info = ModelInfo(
            name="llama3.2",
            size=4096000000,  # 4GB
            digest="sha256:abcd1234",
            modified_at=datetime.now(),
        )
        assert info.name == "llama3.2"
        assert info.size == 4096000000
        assert info.digest == "sha256:abcd1234"

    def test_model_name_validation(self):
        """Test model name validation."""
        # Valid names
        ModelInfo(
            name="llama3.2",
            size=1000,
            digest="abc123",
            modified_at=datetime.now()
        )

        # Empty name should fail
        with pytest.raises(ValidationError):
            ModelInfo(
                name="",
                size=1000,
                digest="abc123",
                modified_at=datetime.now()
            )

        # Whitespace-only name should fail
        with pytest.raises(ValidationError):
            ModelInfo(
                name="   ",
                size=1000,
                digest="abc123",
                modified_at=datetime.now()
            )

    def test_model_name_trimming(self):
        """Test that model names are trimmed."""
        info = ModelInfo(
            name="  llama3.2  ",
            size=1000,
            digest="abc123",
            modified_at=datetime.now()
        )
        assert info.name == "llama3.2"


class TestEmbeddingRequest:
    """Test EmbeddingRequest model."""

    def test_valid_request(self):
        """Test valid embedding request."""
        request = EmbeddingRequest(
            model="nomic-embed-text",
            prompt="Hello world",
        )
        assert request.model == "nomic-embed-text"
        assert request.prompt == "Hello world"
        assert request.options is None
        assert request.keep_alive is None

    def test_with_options(self):
        """Test request with options."""
        request = EmbeddingRequest(
            model="nomic-embed-text",
            prompt="Hello world",
            options={"temperature": 0.7},
            keep_alive="5m",
        )
        assert request.options == {"temperature": 0.7}
        assert request.keep_alive == "5m"

    def test_prompt_validation(self):
        """Test prompt validation."""
        # Empty prompt should fail
        with pytest.raises(ValidationError):
            EmbeddingRequest(model="test", prompt="")

        # Whitespace-only prompt should fail
        with pytest.raises(ValidationError):
            EmbeddingRequest(model="test", prompt="   ")

    def test_model_validation(self):
        """Test model validation."""
        # Empty model should fail
        with pytest.raises(ValidationError):
            EmbeddingRequest(model="", prompt="test")

    def test_prompt_trimming(self):
        """Test that prompts are trimmed."""
        request = EmbeddingRequest(
            model="test",
            prompt="  Hello world  "
        )
        assert request.prompt == "Hello world"


class TestEmbeddingResponse:
    """Test EmbeddingResponse model."""

    def test_valid_response(self):
        """Test valid embedding response."""
        response = EmbeddingResponse(
            model="nomic-embed-text",
            embedding=[0.1, 0.2, -0.3, 0.4],
        )
        assert response.model == "nomic-embed-text"
        assert response.embedding == [0.1, 0.2, -0.3, 0.4]
        assert response.dimension == 4

    def test_embedding_validation(self):
        """Test embedding vector validation."""
        # Empty embedding should fail
        with pytest.raises(ValidationError):
            EmbeddingResponse(model="test", embedding=[])

        # Non-numeric values should fail
        with pytest.raises(ValidationError):
            EmbeddingResponse(model="test", embedding=[0.1, "invalid", 0.3])

    def test_to_numpy(self):
        """Test conversion to numpy array."""
        response = EmbeddingResponse(
            model="test",
            embedding=[0.1, 0.2, -0.3, 0.4],
        )
        array = response.to_numpy()
        assert isinstance(array, np.ndarray)
        assert array.dtype == np.float32
        # Use approximate equality for float32 precision
        expected = np.array([0.1, 0.2, -0.3, 0.4], dtype=np.float32)
        assert np.allclose(array, expected)

    def test_dimension_property(self):
        """Test dimension property."""
        response = EmbeddingResponse(
            model="test",
            embedding=[1.0, 2.0, 3.0],
        )
        assert response.dimension == 3


class TestChatMessage:
    """Test ChatMessage model."""

    def test_valid_message(self):
        """Test valid chat message."""
        message = ChatMessage(
            role="user",
            content="Hello, how are you?",
        )
        assert message.role == "user"
        assert message.content == "Hello, how are you?"
        assert message.images is None

    def test_with_images(self):
        """Test message with images."""
        message = ChatMessage(
            role="user",
            content="What's in this image?",
            images=["base64encodedimage"],
        )
        assert message.images == ["base64encodedimage"]

    def test_role_validation(self):
        """Test role validation."""
        # Valid roles
        for role in ["system", "user", "assistant"]:
            ChatMessage(role=role, content="test")

        # Invalid role should fail
        with pytest.raises(ValidationError):
            ChatMessage(role="invalid", content="test")

    def test_content_validation(self):
        """Test content validation."""
        # Empty content should fail
        with pytest.raises(ValidationError):
            ChatMessage(role="user", content="")

        # Whitespace-only content should fail
        with pytest.raises(ValidationError):
            ChatMessage(role="user", content="   ")

    def test_content_trimming(self):
        """Test that content is trimmed."""
        message = ChatMessage(
            role="user",
            content="  Hello world  "
        )
        assert message.content == "Hello world"


class TestChatRequest:
    """Test ChatRequest model."""

    def test_valid_request(self):
        """Test valid chat request."""
        messages = [
            ChatMessage(role="user", content="Hello"),
        ]
        request = ChatRequest(
            model="llama3.2",
            messages=messages,
        )
        assert request.model == "llama3.2"
        assert len(request.messages) == 1
        assert request.stream is False
        assert request.format is None

    def test_with_streaming(self):
        """Test request with streaming enabled."""
        messages = [ChatMessage(role="user", content="Hello")]
        request = ChatRequest(
            model="llama3.2",
            messages=messages,
            stream=True,
            format="json",
        )
        assert request.stream is True
        assert request.format == "json"

    def test_messages_validation(self):
        """Test messages validation."""
        # Empty messages should fail
        with pytest.raises(ValidationError):
            ChatRequest(model="test", messages=[])

    def test_model_validation(self):
        """Test model validation."""
        messages = [ChatMessage(role="user", content="Hello")]

        # Empty model should fail
        with pytest.raises(ValidationError):
            ChatRequest(model="", messages=messages)


class TestBatchRequest:
    """Test BatchRequest model."""

    def test_valid_embedding_batch(self):
        """Test valid embedding batch request."""
        request = BatchRequest(
            model="nomic-embed-text",
            items=["Hello", "World", "Test"],
            operation="embedding",
        )
        assert request.model == "nomic-embed-text"
        assert request.items == ["Hello", "World", "Test"]
        assert request.operation == "embedding"
        assert request.batch_size == 10  # default

    def test_valid_chat_batch(self):
        """Test valid chat batch request."""
        messages = [
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="user", content="Hi there"),
        ]
        request = BatchRequest(
            model="llama3.2",
            items=messages,
            operation="chat",
            batch_size=5,
        )
        assert request.operation == "chat"
        assert request.batch_size == 5

    def test_items_validation(self):
        """Test items validation."""
        # Empty items should fail
        with pytest.raises(ValidationError):
            BatchRequest(model="test", items=[], operation="embedding")

        # Too many items should fail
        large_items = ["item"] * 1001  # Over limit
        with pytest.raises(ValidationError):
            BatchRequest(model="test", items=large_items, operation="embedding")

    def test_batch_size_validation(self):
        """Test batch size validation."""
        items = ["test1", "test2"]

        # Valid batch sizes
        BatchRequest(model="test", items=items, operation="embedding", batch_size=1)
        BatchRequest(model="test", items=items, operation="embedding", batch_size=100)

        # Invalid batch sizes
        with pytest.raises(ValidationError):
            BatchRequest(model="test", items=items, operation="embedding", batch_size=0)

        with pytest.raises(ValidationError):
            BatchRequest(model="test", items=items, operation="embedding", batch_size=101)


class TestBatchResponse:
    """Test BatchResponse model."""

    def test_valid_response(self):
        """Test valid batch response."""
        results = [
            EmbeddingResponse(model="test", embedding=[0.1, 0.2]),
            EmbeddingResponse(model="test", embedding=[0.3, 0.4]),
        ]
        response = BatchResponse(
            model="test",
            operation="embedding",
            results=results,
            total_items=3,
            successful_items=2,
            failed_items=1,
            total_duration=5.5,
        )
        assert response.model == "test"
        assert response.operation == "embedding"
        assert len(response.results) == 2
        assert response.total_items == 3
        assert response.successful_items == 2
        assert response.failed_items == 1
        assert response.total_duration == 5.5

    def test_success_rate_property(self):
        """Test success rate calculation."""
        response = BatchResponse(
            model="test",
            operation="embedding",
            results=[],
            total_items=10,
            successful_items=8,
            failed_items=2,
            total_duration=1.0,
        )
        assert response.success_rate == 80.0

        # Test zero division
        response_empty = BatchResponse(
            model="test",
            operation="embedding",
            results=[],
            total_items=0,
            successful_items=0,
            failed_items=0,
            total_duration=1.0,
        )
        assert response_empty.success_rate == 0.0

    def test_average_duration_property(self):
        """Test average duration calculation."""
        response = BatchResponse(
            model="test",
            operation="embedding",
            results=[],
            total_items=5,
            successful_items=3,
            failed_items=2,
            total_duration=10.0,
        )
        assert response.average_duration_per_item == 2.0

        # Test zero division
        response_empty = BatchResponse(
            model="test",
            operation="embedding",
            results=[],
            total_items=0,
            successful_items=0,
            failed_items=0,
            total_duration=5.0,
        )
        assert response_empty.average_duration_per_item == 0.0


class TestHealthCheckResponse:
    """Test HealthCheckResponse model."""

    def test_healthy_response(self):
        """Test healthy response."""
        response = HealthCheckResponse(
            status="healthy",
            version="0.1.0",
            models_available=5,
            response_time_ms=150.5,
            timestamp=datetime.now(),
        )
        assert response.status == "healthy"
        assert response.version == "0.1.0"
        assert response.models_available == 5
        assert response.response_time_ms == 150.5

    def test_unhealthy_response(self):
        """Test unhealthy response."""
        response = HealthCheckResponse(
            status="unhealthy",
            models_available=0,
            response_time_ms=5000.0,
            timestamp=datetime.now(),
        )
        assert response.status == "unhealthy"
        assert response.models_available == 0
        assert response.version is None


class TestModelPullProgress:
    """Test ModelPullProgress model."""

    def test_progress_percentage(self):
        """Test progress percentage calculation."""
        # Complete progress
        progress = ModelPullProgress(
            status="downloading",
            total=1000,
            completed=750,
        )
        assert progress.progress_percentage == 75.0

        # No progress info
        progress_no_info = ModelPullProgress(status="starting")
        assert progress_no_info.progress_percentage is None

        # Zero total
        progress_zero = ModelPullProgress(
            status="downloading",
            total=0,
            completed=0,
        )
        assert progress_zero.progress_percentage == 100.0

    def test_valid_progress(self):
        """Test valid progress creation."""
        progress = ModelPullProgress(
            status="downloading",
            digest="sha256:abc123",
            total=1000000,
            completed=500000,
        )
        assert progress.status == "downloading"
        assert progress.digest == "sha256:abc123"
        assert progress.total == 1000000
        assert progress.completed == 500000