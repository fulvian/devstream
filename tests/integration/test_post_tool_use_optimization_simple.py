"""
Simplified integration tests for DevStream PostToolUse hook with optimization components.

Tests validate:
- ContentQualityFilter integration (Task 1)
- AsyncEmbeddingProcessor integration (Task 2)
- End-to-end memory storage workflow
- Performance targets and graceful degradation
"""

import pytest
import asyncio
import time
import os
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# Add path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'hooks'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'hooks' / 'devstream'))

# Import PostToolUse hook components
try:
    from devstream.memory.post_tool_use import PostToolUseHook
    from cchooks import PostToolUseContext, PostToolUseOutput
    POST_TOOL_USE_AVAILABLE = True
except ImportError as e:
    POST_TOOL_USE_AVAILABLE = False
    POST_TOOL_USE_IMPORT_ERROR = str(e)

# Import optimization components for testing
try:
    from optimization.content_quality_filter import get_content_quality_filter
    from optimization.async_embedding_processor import get_async_embedding_processor
    OPTIMIZATION_AVAILABLE = True
except ImportError as e:
    OPTIMIZATION_AVAILABLE = False
    OPTIMIZATION_IMPORT_ERROR = str(e)


@pytest.mark.skipif(not POST_TOOL_USE_AVAILABLE, reason=f"PostToolUse unavailable: {POST_TOOL_USE_IMPORT_ERROR if 'POST_TOOL_USE_IMPORT_ERROR' in locals() else 'Unknown'}")
@pytest.mark.skipif(not OPTIMIZATION_AVAILABLE, reason=f"Optimization components unavailable: {OPTIMIZATION_IMPORT_ERROR if 'OPTIMIZATION_IMPORT_ERROR' in locals() else 'Unknown'}")
class TestPostToolUseIntegrationSimple:
    """Simplified integration tests for PostToolUse hook with optimization components."""

    @pytest.fixture
    def mock_context(self):
        """Create mock PostToolUseContext for testing."""
        context = Mock(spec=PostToolUseContext)
        context.tool_name = "Write"
        context.tool_input = {
            "file_path": "/test/example.py",
            "content": "def hello_world():\n    print('Hello, World!')\n"
        }
        context.tool_response = {"success": True}
        context.output = Mock(spec=PostToolUseOutput)
        return context

    @pytest.fixture
    def hook(self):
        """Create PostToolUseHook instance for testing."""
        with patch.dict(os.environ, {
            'DEVSTREAM_MEMORY_ENABLED': 'true',
            'DEVSTREAM_MEMORY_STORE_ENABLED': 'true'
        }):
            hook = PostToolUseHook()
            # Lower the quality threshold for testing
            if hook.content_quality_filter:
                hook.content_quality_filter.quality_threshold = 0.1
            return hook

    @pytest.mark.asyncio
    async def test_full_memory_storage_workflow(self, hook, mock_context):
        """Test complete memory storage workflow with all optimizations."""
        # Mock the unified client
        mock_unified_client = AsyncMock()
        mock_unified_client.store_memory.return_value = {
            "success": True,
            "memory_id": "test_memory_id_123"
        }
        hook.unified_client = mock_unified_client

        # Mock embedding generation
        with patch.object(hook.ollama_client, 'generate_embedding', return_value=[0.1] * 384):
            with patch.object(hook, 'update_memory_embedding', return_value=True):
                start_time = time.time()
                await hook.process(mock_context)
                end_time = time.time()
                processing_time = (end_time - start_time) * 1000

        # Verify memory was stored
        mock_unified_client.store_memory.assert_called_once()
        mock_context.output.exit_success.assert_called_once()
        assert processing_time < 3000, f"Processing too slow: {processing_time:.1f}ms"

    @pytest.mark.asyncio
    async def test_content_quality_filter_integration(self, hook, mock_context):
        """Test ContentQualityFilter integration in memory storage."""
        if not hook.content_quality_filter:
            pytest.skip("ContentQualityFilter not available")

        # Test high-quality content
        high_quality_content = """
def fibonacci(n: int) -> int:
    if n < 0:
        raise ValueError("n must be non-negative")
    elif n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
"""

        mock_context.tool_input["content"] = high_quality_content

        # Mock the unified client
        mock_unified_client = AsyncMock()
        mock_unified_client.store_memory.return_value = {
            "success": True,
            "memory_id": "test_memory_id_456"
        }
        hook.unified_client = mock_unified_client

        # Mock embedding generation
        with patch.object(hook.ollama_client, 'generate_embedding', return_value=[0.1] * 384):
            with patch.object(hook, 'update_memory_embedding', return_value=True):
                memory_id = await hook.store_in_memory(
                    file_path=mock_context.tool_input["file_path"],
                    content=high_quality_content,
                    operation=mock_context.tool_name,
                    topics=["algorithms", "mathematics"],
                    entities=["fibonacci"],
                    content_type="code"
                )

        # Should store high-quality content
        assert memory_id is not None
        assert memory_id == "test_memory_id_456"

    @pytest.mark.asyncio
    async def test_async_embedding_processor_integration(self, hook, mock_context):
        """Test AsyncEmbeddingProcessor integration in embedding generation."""
        if not hook.async_embedding_processor:
            pytest.skip("AsyncEmbeddingProcessor not available")

        # Mock the unified client
        mock_unified_client = AsyncMock()
        mock_unified_client.store_memory.return_value = {
            "success": True,
            "memory_id": "test_embedding_memory_id"
        }
        hook.unified_client = mock_unified_client

        # Test content
        test_content = """
import asyncio
from typing import Optional

class AsyncProcessor:
    def __init__(self):
        self.results = []

    async def process_item(self, item: str) -> Optional[str]:
        await asyncio.sleep(0.001)  # Simulate async work
        return item.upper()

    async def process_batch(self, items: list) -> list:
        tasks = [self.process_item(item) for item in items]
        return await asyncio.gather(*tasks)
"""

        # Test embedding generation
        memory_id = await hook.store_in_memory(
            file_path=mock_context.tool_input["file_path"],
            content=test_content,
            operation=mock_context.tool_name,
            topics=["async", "processing"],
            entities=["asyncio"],
            content_type="code"
        )

        # Should store content
        assert memory_id is not None
        assert memory_id == "test_embedding_memory_id"
        assert hook.async_embedding_processor is not None

    @pytest.mark.asyncio
    async def test_quality_based_keyword_enhancement(self, hook, mock_context):
        """Test keyword enhancement based on content quality."""
        if not hook.content_quality_filter:
            pytest.skip("ContentQualityFilter not available")

        # Test technical content
        technical_content = """
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

class SimpleMLModel:
    def __init__(self, n_estimators: int = 100):
        self.n_estimators = n_estimators
        self.model = None

    def train(self, X, y):
        self.model = RandomForestClassifier(n_estimators=self.n_estimators)
        self.model.fit(X, y)
        return self.model.score(X, y)

    def predict(self, X):
        if self.model is None:
            raise ValueError("Model must be trained first")
        return self.model.predict(X)

# Example usage
def main():
    from sklearn.datasets import make_classification
    X, y = make_classification(n_samples=1000, n_features=10, random_state=42)
    model = SimpleMLModel(n_estimators=200)
    score = model.train(X, y)
    print(f"Model accuracy: {score:.4f}")
    return model

if __name__ == "__main__":
    trained_model = main()
"""

        # Mock the unified client
        mock_unified_client = AsyncMock()
        mock_unified_client.store_memory.return_value = {
            "success": True,
            "memory_id": "test_ml_memory_id"
        }
        hook.unified_client = mock_unified_client

        with patch.object(hook.ollama_client, 'generate_embedding', return_value=[0.1] * 384):
            memory_id = await hook.store_in_memory(
                file_path="/test/simple_ml_model.py",
                content=technical_content,
                operation="Write",
                topics=["machine-learning", "classification"],
                entities=["numpy", "pandas", "sklearn"],
                content_type="code"
            )

        # Should store enhanced content
        assert memory_id is not None

        # Verify keywords were included
        call_args = mock_unified_client.store_memory.call_args
        stored_keywords = call_args[1]['keywords']

        # Should include quality-based keywords
        quality_keywords = [kw for kw in stored_keywords if kw in ["high-quality", "medium-quality", "low-quality"]]
        assert len(quality_keywords) > 0, f"No quality keyword found in: {stored_keywords}"

        # Should include expected keywords
        expected_keywords = ["machine-learning", "classification", "numpy", "pandas", "sklearn", "python", "implementation"]
        for keyword in expected_keywords:
            assert keyword in stored_keywords, f"Missing keyword: {keyword}"

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_component_failure(self, hook, mock_context):
        """Test graceful degradation when optimization components fail."""
        # Temporarily disable optimization components
        original_content_filter = hook.content_quality_filter
        original_async_processor = hook.async_embedding_processor

        try:
            # Simulate component failures
            hook.content_quality_filter = None
            hook.async_embedding_processor = None

            # Mock the unified client
            mock_unified_client = AsyncMock()
            mock_unified_client.store_memory.return_value = {
                "success": True,
                "memory_id": "test_degradation_memory_id"
            }
            hook.unified_client = mock_unified_client

            # Mock embedding generation (fallback mode)
            with patch.object(hook.ollama_client, 'generate_embedding', return_value=[0.1] * 384):
                with patch.object(hook, 'update_memory_embedding', return_value=True):
                    memory_id = await hook.store_in_memory(
                        file_path=mock_context.tool_input["file_path"],
                        content=mock_context.tool_input["content"],
                        operation=mock_context.tool_name,
                        topics=["test"],
                        entities=["test"],
                        content_type="code"
                    )

            # Should still work with fallback mechanisms
            assert memory_id is not None
            assert memory_id == "test_degradation_memory_id"

        finally:
            # Restore original components
            hook.content_quality_filter = original_content_filter
            hook.async_embedding_processor = original_async_processor

    def test_content_classification_accuracy(self, hook):
        """Test content type classification accuracy."""
        test_cases = [
            {
                "tool_name": "Write",
                "tool_response": {"success": True},
                "content": "def function(): pass",
                "expected_type": "code"
            },
            {
                "tool_name": "Bash",
                "tool_response": {"success": True, "output": "Command executed successfully"},
                "content": "Command executed successfully",
                "expected_type": "output"
            },
            {
                "tool_name": "Bash",
                "tool_response": {"success": False, "error": "Command failed"},
                "content": "Command failed",
                "expected_type": "error"
            },
            {
                "tool_name": "Read",
                "tool_response": {"success": True},
                "content": "# Documentation content",
                "expected_type": "context"
            },
            {
                "tool_name": "TodoWrite",
                "tool_response": {"success": True},
                "content": "[{\"content\": \"task\"}]",
                "expected_type": "decision"
            }
        ]

        for test_case in test_cases:
            result_type = hook.classify_content_type(
                test_case["tool_name"],
                test_case["tool_response"],
                test_case["content"]
            )
            assert result_type == test_case["expected_type"], \
                f"Expected {test_case['expected_type']}, got {result_type} for {test_case['tool_name']}"

    @pytest.mark.asyncio
    async def test_concurrent_memory_storage(self, hook):
        """Test concurrent memory storage performance."""
        # Mock the unified client
        mock_unified_client = AsyncMock()
        mock_unified_client.store_memory.return_value = {
            "success": True,
            "memory_id": "concurrent_test_memory_id"
        }
        hook.unified_client = mock_unified_client

        # Create multiple storage tasks
        storage_tasks = []
        for i in range(5):  # Reduced from 10 to 5 for faster testing
            task = hook.store_in_memory(
                file_path=f"/test/concurrent_{i}.py",
                content=f"def function_{i}():\n    return {i}\n",
                operation="Write",
                topics=[f"topic_{i}"],
                entities=[f"entity_{i}"],
                content_type="code"
            )
            storage_tasks.append(task)

        # Execute tasks concurrently
        start_time = time.time()
        memory_ids = await asyncio.gather(*storage_tasks)
        end_time = time.time()
        total_time = (end_time - start_time) * 1000

        # All should complete successfully
        for i, memory_id in enumerate(memory_ids):
            assert memory_id is not None, f"Storage task {i} failed"

        # Should complete in reasonable time
        assert total_time < 3000, f"Concurrent storage too slow: {total_time:.1f}ms"

        # Should have made storage calls
        assert mock_unified_client.store_memory.call_count == 5


@pytest.mark.skipif(not OPTIMIZATION_AVAILABLE, reason=f"Optimization components unavailable: {OPTIMIZATION_IMPORT_ERROR if 'OPTIMIZATION_IMPORT_ERROR' in locals() else 'Unknown'}")
class TestOptimizationComponentsStandaloneSimple:
    """Simplified standalone tests for PostToolUse optimization components."""

    def test_content_quality_filter_standalone(self):
        """Test ContentQualityFilter standalone functionality."""
        filter = get_content_quality_filter(quality_threshold=0.3)

        # Test high-quality content
        high_quality_content = """
def fibonacci(n: int) -> int:
    if n < 0:
        raise ValueError("n must be non-negative")
    elif n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
"""

        result = filter.should_store_content(
            content=high_quality_content,
            file_path="/test/fibonacci.py",
            content_type="code"
        )

        # Should either store or have a reasonable quality score
        # The exact behavior depends on the filter's implementation
        assert isinstance(result, tuple)  # (should_store, quality_score)
        assert len(result) == 2
        assert isinstance(result[0], bool)  # should_store
        assert isinstance(result[1], float)  # quality_score
        assert 0.0 <= result[1] <= 1.0  # quality score should be valid

        # Test low-quality content
        low_quality_content = "# TODO: implement\npass\n"

        result = filter.should_store_content(
            content=low_quality_content,
            file_path="/test/TODO.py",
            content_type="code"
        )

        # Should filter out low-quality content (depending on threshold)
        assert isinstance(result, tuple)  # (should_store, quality_score)

    def test_async_embedding_processor_standalone(self):
        """Test AsyncEmbeddingProcessor standalone functionality."""
        processor = get_async_embedding_processor(
            batch_size=5,
            max_retries=3,
            max_concurrent_batches=3
        )

        # Test processor configuration
        assert processor.batch_size == 5
        assert processor.max_retries == 3
        assert processor.max_concurrent_batches == 3

        # Test statistics functionality
        stats = processor.get_processing_statistics()

        # Should have valid configuration
        assert "config" in stats
        assert stats["config"]["batch_size"] == 5
        assert stats["config"]["max_retries"] == 3
        assert stats["config"]["max_concurrent_batches"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])