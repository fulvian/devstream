#!/usr/bin/env .devstream/bin/python
"""
Unit tests for AsyncEmbeddingBatchProcessor component.

Tests async batch processing system for increasing embedding coverage
from 0.4% to 80%+ with exponential backoff retry logic.
"""

import asyncio
import pytest
import time
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import AsyncMock, ANY, MagicMock, patch

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'optimization'))

from async_embedding_processor import (
    AsyncEmbeddingBatchProcessor,
    EmbeddingProcessingError,
    BatchStatus,
    BatchResult,
    get_async_embedding_processor
)


class TestAsyncEmbeddingBatchProcessor:
    """Test cases for AsyncEmbeddingBatchProcessor class."""

    @pytest.fixture
    def processor_instance(self):
        """Create an AsyncEmbeddingBatchProcessor instance for testing."""
        return AsyncEmbeddingBatchProcessor(
            batch_size=5,
            max_retries=2,
            max_concurrent_batches=2,
            base_delay=0.1,  # Shorter delays for testing
            max_delay=1.0,   # Shorter max delay for testing
            jitter_factor=0.1
        )

    @pytest.fixture
    def sample_data(self):
        """Sample data for testing."""
        return {
            "memory_ids": [f"mem_{i:03d}" for i in range(1, 13)],  # 12 items
            "contents": [
                "def function_name():\n    return 'test'",
                "import asyncio\n\nasync def main():\n    await asyncio.sleep(1)",
                "class TestClass:\n    def __init__(self):\n        self.value = 42",
                "from fastapi import FastAPI\n\napp = FastAPI()",
                "SELECT * FROM users WHERE id = ?",
                "const ReactComponent = () => {\n    return <div>Hello</div>\n}",
                "# Configuration file\nDEBUG=True\nPORT=8000",
                "def calculate_sum(a, b):\n    return a + b",
                "async def fetch_data(url):\n    async with aiohttp.ClientSession() as session:\n        async with session.get(url) as response:\n            return await response.json()",
                "interface User {\n    id: number;\n    name: string;\n}",
                "try:\n    risky_operation()\nexcept Exception as e:\n    logger.error(f\"Error: {e}\")",
                "from datetime import datetime\n\nnow = datetime.now()"
            ]
        }

    @pytest.fixture
    def mock_ollama_client(self):
        """Create a mock OllamaEmbeddingClient."""
        mock_client = AsyncMock()

        def generate_embedding(content: str) -> List[float]:
            # Generate deterministic embedding based on content hash
            content_hash = hash(content) % 1000
            return [float((content_hash + i) % 1000) / 1000.0 for i in range(768)]  # 768 dimensions

        mock_client.generate_embedding.side_effect = generate_embedding
        return mock_client

    @pytest.fixture
    def mock_database(self):
        """Create a mock database connection."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_cursor.rowcount = 1
        return mock_conn, mock_cursor

    def test_processor_initialization(self, processor_instance):
        """Test processor initialization with default and custom parameters."""
        assert processor_instance.batch_size == 5
        assert processor_instance.max_retries == 2
        assert processor_instance.max_concurrent_batches == 2
        assert processor_instance.base_delay == 0.1
        assert processor_instance.max_delay == 1.0
        assert processor_instance.jitter_factor == 0.1
        assert processor_instance._semaphore._value == 2

        # Test custom initialization
        custom_processor = AsyncEmbeddingBatchProcessor(
            batch_size=10,
            max_retries=5,
            max_concurrent_batches=4
        )
        assert custom_processor.batch_size == 10
        assert custom_processor.max_retries == 5
        assert custom_processor.max_concurrent_batches == 4

    def test_split_into_batches(self, processor_instance, sample_data):
        """Test batch splitting functionality."""
        memory_ids = sample_data["memory_ids"]
        contents = sample_data["contents"]

        batches = processor_instance._split_into_batches(memory_ids, contents)

        # Should split 12 items into 3 batches of 5, 5, 2
        assert len(batches) == 3

        assert len(batches[0][0]) == 5  # First batch has 5 IDs
        assert len(batches[0][1]) == 5  # First batch has 5 contents
        assert len(batches[1][0]) == 5  # Second batch has 5 IDs
        assert len(batches[1][1]) == 5  # Second batch has 5 contents
        assert len(batches[2][0]) == 2  # Third batch has 2 IDs
        assert len(batches[2][1]) == 2  # Third batch has 2 contents

        # Test with mismatched lengths
        with pytest.raises(ValueError, match="Memory IDs and contents must have the same length"):
            processor_instance._split_into_batches(["id1", "id2"], ["content1"])

    def test_calculate_delay(self, processor_instance):
        """Test exponential backoff delay calculation."""
        # Test exponential backoff progression
        delay_0 = processor_instance._calculate_delay(0)
        delay_1 = processor_instance._calculate_delay(1)
        delay_2 = processor_instance._calculate_delay(2)

        # Should increase exponentially
        assert 0 <= delay_0 <= processor_instance.max_delay
        assert delay_1 > delay_0
        assert delay_2 > delay_1

        # Test max delay capping
        large_attempt_delay = processor_instance._calculate_delay(20)
        assert large_attempt_delay <= processor_instance.max_delay + (processor_instance.max_delay * processor_instance.jitter_factor)

        # Test jitter is applied (delay should not be exact exponential value)
        expected_exponential = processor_instance.base_delay * (2 ** 1)
        actual_delay = processor_instance._calculate_delay(1)
        assert abs(actual_delay - expected_exponential) <= (expected_exponential * processor_instance.jitter_factor)

    @pytest.mark.asyncio
    async def test_process_single_batch_success(self, processor_instance, sample_data, mock_ollama_client, mock_database):
        """Test successful single batch processing."""
        with patch.object(processor_instance, '_store_embedding', new=AsyncMock(return_value=True)) as mock_store:
            with patch.object(processor_instance, '_get_ollama_client', return_value=mock_ollama_client):
                memory_ids = sample_data["memory_ids"][:3]
                contents = sample_data["contents"][:3]

                result = await processor_instance._process_single_batch(memory_ids, contents, "test_batch")

                assert result.batch_id == "test_batch"
                assert result.status == BatchStatus.COMPLETED
                assert len(result.memory_ids) == 3
                assert result.success_count == 3
                assert result.failure_count == 0
                assert result.success_rate == 100.0
                assert result.retry_count == 0
                assert result.processing_time_ms > 0
                assert result.error is None

                # Verify _store_embedding was called for each memory_id
                assert mock_store.call_count == 3

    @pytest.mark.asyncio
    async def test_process_single_batch_with_failures(self, processor_instance, sample_data, mock_ollama_client, mock_database):
        """Test batch processing with some failures."""
        # Create a custom processor instance that we can control more precisely
        test_processor = AsyncEmbeddingBatchProcessor(
            batch_size=5,
            max_retries=2,
            max_concurrent_batches=2,
            base_delay=0.01,  # Very short delays for testing
            max_delay=0.1,
            jitter_factor=0.1
        )

        # Patch the _store_embedding method to simulate storage failures
        storage_calls = []
        async def mock_store_embedding_with_failures(memory_id: str, embedding: List[float]) -> bool:
            storage_calls.append(memory_id)
            # Fail on second item (mem_002)
            if memory_id == "mem_002":
                return False  # Storage failure
            return True  # Storage success

        with patch.object(test_processor, '_store_embedding', side_effect=mock_store_embedding_with_failures):
            # Mock Ollama client to always succeed
            with patch.object(test_processor, '_get_ollama_client', return_value=mock_ollama_client):
                memory_ids = sample_data["memory_ids"][:3]
                contents = sample_data["contents"][:3]

                result = await test_processor._process_single_batch(memory_ids, contents, "test_batch")

                assert result.status == BatchStatus.COMPLETED
                assert result.success_count == 2  # 2 out of 3 succeeded
                assert result.failure_count == 1   # 1 out of 3 failed
                assert 66.0 <= result.success_rate <= 67.0  # ~66.7% success rate

                # Verify storage was attempted for all items
                assert len(storage_calls) == 3

    @pytest.mark.asyncio
    async def test_process_single_batch_retry_success(self, processor_instance, sample_data, mock_ollama_client, mock_database):
        """Test batch processing with retry success."""
        # Create a custom processor instance that we can control more precisely
        test_processor = AsyncEmbeddingBatchProcessor(
            batch_size=5,
            max_retries=2,
            max_concurrent_batches=2,
            base_delay=0.01,  # Very short delays for testing
            max_delay=0.1,
            jitter_factor=0.1
        )

        # Create a mock _get_ollama_client method that fails initially then succeeds
        call_count = 0
        def mock_get_ollama_client_with_retry():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first 2 attempts
                raise ConnectionError("Temporary connection error")
            # Return successful client on 3rd attempt
            return mock_ollama_client

        with patch.object(test_processor, '_store_embedding', new=AsyncMock(return_value=True)):
            with patch.object(test_processor, '_get_ollama_client', side_effect=mock_get_ollama_client_with_retry):
                memory_ids = sample_data["memory_ids"][:2]
                contents = sample_data["contents"][:2]

                start_time = time.time()
                result = await test_processor._process_single_batch(memory_ids, contents, "test_batch")
                end_time = time.time()

                assert result.status == BatchStatus.COMPLETED
                assert result.success_count == 2
                assert result.failure_count == 0
                assert result.retry_count == 2  # Should have retried twice
                assert result.success_rate == 100.0
                # Should have taken some time due to retries
                assert end_time - start_time >= 0.01  # At least base delay

    @pytest.mark.asyncio
    async def test_process_single_batch_max_retries_exceeded(self, processor_instance, sample_data, mock_ollama_client):
        """Test batch processing when max retries are exceeded."""
        # Create a custom processor instance that we can control more precisely
        test_processor = AsyncEmbeddingBatchProcessor(
            batch_size=5,
            max_retries=2,
            max_concurrent_batches=2,
            base_delay=0.01,  # Very short delays for testing
            max_delay=0.1,
            jitter_factor=0.1
        )

        # Mock _get_ollama_client to always fail with connection errors
        def mock_get_ollama_client_always_fails():
            raise ConnectionError("Persistent connection error")

        with patch.object(test_processor, '_get_ollama_client', side_effect=mock_get_ollama_client_always_fails):
            memory_ids = sample_data["memory_ids"][:2]
            contents = sample_data["contents"][:2]

            result = await test_processor._process_single_batch(memory_ids, contents, "test_batch")

            assert result.status == BatchStatus.FAILED
            assert result.success_count == 0
            assert result.failure_count == 2
            assert result.retry_count == test_processor.max_retries + 1  # Should exceed max retries
            assert result.error is not None
            assert "Persistent connection error" in result.error

    @pytest.mark.asyncio
    async def test_process_embedding_batch_success(self, processor_instance, sample_data, mock_ollama_client, mock_database):
        """Test successful embedding batch processing."""
        with patch.object(processor_instance, '_store_embedding', new=AsyncMock(return_value=True)) as mock_store:
            # Database mocked via _store_embedding patch

            with patch.object(processor_instance, '_get_ollama_client', return_value=mock_ollama_client):
                memory_ids = sample_data["memory_ids"]
                contents = sample_data["contents"]

                results = await processor_instance.process_embedding_batch(memory_ids, contents)

                assert len(results) == len(memory_ids)
                assert all(memory_id in results for memory_id in memory_ids)
                assert all(results[memory_id] is True for memory_id in memory_ids)

    @pytest.mark.asyncio
    async def test_process_embedding_batch_with_custom_parameters(self, processor_instance, sample_data, mock_ollama_client, mock_database):
        """Test batch processing with custom parameters."""
        with patch.object(processor_instance, '_store_embedding', new=AsyncMock(return_value=True)) as mock_store:
            # Database mocked via _store_embedding patch

            with patch.object(processor_instance, '_get_ollama_client', return_value=mock_ollama_client):
                memory_ids = sample_data["memory_ids"]
                contents = sample_data["contents"]

                # Use custom batch size and max retries
                results = await processor_instance.process_embedding_batch(
                    memory_ids,
                    contents,
                    batch_size=3,  # Smaller batches
                    max_retries=1  # Fewer retries
                )

                assert len(results) == len(memory_ids)
                assert all(results[memory_id] is True for memory_id in memory_ids)

    @pytest.mark.asyncio
    async def test_process_embedding_batch_empty_input(self, processor_instance):
        """Test batch processing with empty input."""
        results = await processor_instance.process_embedding_batch([], [])
        assert results == {}

        results = await processor_instance.process_embedding_batch(None, None)
        assert results == {}

    @pytest.mark.asyncio
    async def test_process_embedding_batch_mismatched_lengths(self, processor_instance, sample_data):
        """Test batch processing with mismatched input lengths."""
        memory_ids = sample_data["memory_ids"]
        contents = sample_data["contents"][:-1]  # One less content

        with pytest.raises(ValueError, match="Memory IDs and contents must have the same length"):
            await processor_instance.process_embedding_batch(memory_ids, contents)

    @pytest.mark.asyncio
    async def test_process_missing_embeddings(self, processor_instance, mock_ollama_client, mock_database):
        """Test processing records that are missing embeddings."""
        # Mock the database query by patching the process_embedding_batch method instead
        expected_results = {"mem_001": True, "mem_002": True, "mem_003": True}

        with patch.object(processor_instance, 'process_embedding_batch', new=AsyncMock(return_value=expected_results)) as mock_batch:
            results = await processor_instance.process_missing_embeddings(limit=3)

            assert len(results) == 3
            assert "mem_001" in results
            assert "mem_002" in results
            assert "mem_003" in results
            assert all(results[memory_id] is True for memory_id in results)

            # Verify process_embedding_batch was called with correct arguments
            mock_batch.assert_called_once()
            args, kwargs = mock_batch.call_args
            assert len(args[0]) == 3  # 3 memory IDs
            assert len(args[1]) == 3  # 3 contents

    @pytest.mark.asyncio
    async def test_process_missing_embeddings_no_records(self, processor_instance, mock_database):
        """Test processing missing embeddings when no records are found."""
        # Mock empty database query result by patching process_embedding_batch to return empty
        with patch.object(processor_instance, 'process_embedding_batch', new=AsyncMock(return_value={})) as mock_batch:
            results = await processor_instance.process_missing_embeddings(limit=10)

            assert results == {}
            mock_batch.assert_called_once()

    def test_get_processing_statistics(self, processor_instance):
        """Test processing statistics collection."""
        # Initially should have zero statistics
        stats = processor_instance.get_processing_statistics()
        assert stats["total_processed"] == 0
        assert stats["success_count"] == 0
        assert stats["error_count"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["average_batch_time"] == 0.0
        assert stats["retry_count"] == 0
        assert "config" in stats

        # Manually update statistics
        processor_instance._total_processed = 10
        processor_instance._total_successful = 8
        processor_instance._total_failed = 2
        processor_instance._batch_times = [100.0, 150.0, 200.0]
        processor_instance._retry_count = 3

        stats = processor_instance.get_processing_statistics()
        assert stats["total_processed"] == 10
        assert stats["success_count"] == 8
        assert stats["error_count"] == 2
        assert stats["success_rate"] == 80.0
        assert stats["average_batch_time"] == 150.0
        assert stats["retry_count"] == 3

    def test_reset_statistics(self, processor_instance):
        """Test statistics reset functionality."""
        # Set some initial statistics
        processor_instance._total_processed = 100
        processor_instance._total_successful = 80
        processor_instance._total_failed = 20
        processor_instance._total_time_ms = 1000.0
        processor_instance._batch_times = [100.0, 200.0, 300.0]
        processor_instance._retry_count = 5

        # Reset statistics
        processor_instance.reset_statistics()

        # Verify statistics are reset
        stats = processor_instance.get_processing_statistics()
        assert stats["total_processed"] == 0
        assert stats["success_count"] == 0
        assert stats["error_count"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["average_batch_time"] == 0.0
        assert stats["retry_count"] == 0

    def test_batch_result_dataclass(self):
        """Test BatchResult dataclass."""
        result = BatchResult(
            batch_id="test_batch",
            status=BatchStatus.COMPLETED,
            memory_ids=["mem_1", "mem_2"],
            success_count=2,
            failure_count=0,
            processing_time_ms=100.5,
            retry_count=0
        )

        assert result.batch_id == "test_batch"
        assert result.status == BatchStatus.COMPLETED
        assert result.success_rate == 100.0

        # Test with failures
        result_with_failures = BatchResult(
            batch_id="test_batch_2",
            status=BatchStatus.COMPLETED,
            memory_ids=["mem_1", "mem_2", "mem_3"],
            success_count=2,
            failure_count=1,
            processing_time_ms=150.0,
            retry_count=1
        )

        assert result_with_failures.success_rate == 66.66666666666666

    def test_global_instance_function(self):
        """Test the global instance getter function."""
        # Test that it returns an instance
        processor = get_async_embedding_processor()
        assert isinstance(processor, AsyncEmbeddingBatchProcessor)

        # Test that subsequent calls return the same instance
        processor2 = get_async_embedding_processor()
        assert processor is processor2

        # Test custom parameters
        custom_processor = get_async_embedding_processor(
            batch_size=15,
            max_retries=5,
            max_concurrent_batches=4
        )
        assert custom_processor.batch_size == 15
        assert custom_processor.max_retries == 5
        assert custom_processor.max_concurrent_batches == 4

    def test_batch_status_enum(self):
        """Test BatchStatus enum."""
        assert BatchStatus.PENDING == "pending"
        assert BatchStatus.PROCESSING == "processing"
        assert BatchStatus.COMPLETED == "completed"
        assert BatchStatus.FAILED == "failed"
        assert BatchStatus.RETRY == "retry"

    def test_error_handling(self, processor_instance):
        """Test error handling in batch processing."""
        # Test with invalid input
        with pytest.raises(ValueError, match="Memory IDs and contents must have the same length"):
            asyncio.run(processor_instance._split_into_batches(["id1", "id2"], ["content1"]))

    @pytest.mark.asyncio
    async def test_concurrent_batch_processing(self, processor_instance, sample_data, mock_ollama_client, mock_database):
        """Test concurrent batch processing with semaphore control."""
        with patch.object(processor_instance, '_store_embedding', new=AsyncMock(return_value=True)) as mock_store:
            with patch.object(processor_instance, '_get_ollama_client', return_value=mock_ollama_client):
                # Create unique data to test concurrent processing
                memory_ids = [f"mem_concurrent_{i:03d}" for i in range(24)]  # 24 unique items
                contents = [f"content_{i}" for i in range(24)]

                # Process with concurrent batches
                results = await processor_instance.process_embedding_batch(memory_ids, contents)

                assert len(results) == len(memory_ids)
                assert all(results[memory_id] is True for memory_id in memory_ids)

    @pytest.mark.asyncio
    async def test_performance_monitoring(self, processor_instance, sample_data, mock_ollama_client, mock_database):
        """Test performance monitoring during batch processing."""
        with patch.object(processor_instance, '_store_embedding', new=AsyncMock(return_value=True)) as mock_store:
            # Database mocked via _store_embedding patch

            with patch.object(processor_instance, '_get_ollama_client', return_value=mock_ollama_client):
                memory_ids = sample_data["memory_ids"]
                contents = sample_data["contents"]

                # Get initial stats
                initial_stats = processor_instance.get_processing_statistics()
                assert initial_stats["total_processed"] == 0

                # Process batch
                await processor_instance.process_embedding_batch(memory_ids, contents)

                # Check updated stats
                final_stats = processor_instance.get_processing_statistics()
                assert final_stats["total_processed"] == len(memory_ids)
                assert final_stats["success_count"] == len(memory_ids)
                assert final_stats["success_rate"] == 100.0
                assert final_stats["average_batch_time"] > 0

    def test_edge_cases(self, processor_instance):
        """Test edge cases and boundary conditions."""
        # Test single item batch
        single_batch = processor_instance._split_into_batches(["id1"], ["content1"])
        assert len(single_batch) == 1
        assert len(single_batch[0][0]) == 1
        assert len(single_batch[0][1]) == 1

        # Test empty batch
        empty_batch = processor_instance._split_into_batches([], [])
        assert len(empty_batch) == 0

        # Test delay calculation with zero jitter
        no_jitter_processor = AsyncEmbeddingBatchProcessor(jitter_factor=0.0)
        delay = no_jitter_processor._calculate_delay(1)
        expected_delay = no_jitter_processor.base_delay * (2 ** 1)
        assert abs(delay - expected_delay) < 0.001  # Allow small floating point differences

    @pytest.mark.asyncio
    async def test_integration_with_database(self, processor_instance, sample_data, mock_ollama_client, mock_database):
        """Test integration with database storage."""
        with patch.object(processor_instance, '_store_embedding', new=AsyncMock(return_value=True)) as mock_store:
            with patch.object(processor_instance, '_get_ollama_client', return_value=mock_ollama_client):
                memory_ids = sample_data["memory_ids"][:3]
                contents = sample_data["contents"][:3]

                # Process batch
                results = await processor_instance.process_embedding_batch(memory_ids, contents)

                # Verify _store_embedding was called for each memory_id
                assert mock_store.call_count == 3

                # Verify the embedding storage was called with correct parameters
                for i, (memory_id, content) in enumerate(zip(memory_ids, contents)):
                    mock_store.assert_any_call(memory_id, ANY)  # ANY for the embedding vector