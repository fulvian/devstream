#!/usr/bin/env python3
"""
Unit tests for Context7 Direct HTTP Client.

Tests the aiohttp-based direct HTTP client with connection pooling,
circuit breaker, and caching functionality.
"""

import pytest
import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

# Add path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'utils'))

from context7_direct_client import (
    Context7DirectHttpClient,
    Context7APIError,
    CircuitBreakerError,
    CircuitBreaker
)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)

        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 60.0
        assert cb.failure_count == 0
        assert cb.state == "CLOSED"

    def test_circuit_breaker_closed_allows_calls(self):
        """Test that closed circuit breaker allows calls."""
        cb = CircuitBreaker()
        assert cb.call_allowed() is True

    def test_circuit_breaker_records_success(self):
        """Test that success is recorded correctly."""
        cb = CircuitBreaker()

        # Record success in closed state
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == "CLOSED"

    def test_circuit_breaker_opens_on_threshold(self):
        """Test that circuit breaker opens after threshold failures."""
        cb = CircuitBreaker(failure_threshold=2)

        # Record failures
        cb.record_failure()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 1

        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.failure_count == 2

    def test_circuit_breaker_blocks_calls_when_open(self):
        """Test that open circuit breaker blocks calls."""
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()  # Opens the circuit

        assert cb.call_allowed() is False

    def test_circuit_breaker_half_open_after_timeout(self):
        """Test that circuit breaker transitions to half-open after timeout."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()  # Opens the circuit

        assert cb.call_allowed() is False

        # Wait for recovery timeout
        time.sleep(0.2)
        assert cb.call_allowed() is True
        assert cb.state == "HALF_OPEN"

    def test_circuit_breaker_closes_on_half_open_success(self):
        """Test that circuit breaker closes on success in half-open state."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()  # Opens the circuit

        # Wait for recovery timeout
        time.sleep(0.2)
        assert cb.state == "HALF_OPEN"

        # Record success in half-open
        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_circuit_breaker_stats(self):
        """Test circuit breaker statistics."""
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()

        stats = cb.get_stats()
        assert stats['state'] == "CLOSED"
        assert stats['failure_count'] == 1
        assert stats['recovery_timeout'] == 60.0


class TestContext7DirectHttpClient:
    """Test Context7 Direct HTTP Client."""

    @pytest.fixture
    async def client(self):
        """Create a test client instance."""
        client = Context7DirectHttpClient(
            api_key="test-api-key",
            base_url="https://test.context7.com"
        )
        yield client
        await client.close()

    @pytest.fixture
    def mock_session(self):
        """Create a mock aiohttp session."""
        session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {'library_id': '/test/library'}
        mock_response.raise_for_status = AsyncMock()

        # Create a proper async context manager mock
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        session.get.return_value = mock_context_manager

        return session

    def test_client_initialization(self):
        """Test client initialization."""
        client = Context7DirectHttpClient(
            api_key="test-key",
            base_url="https://test.com",
            cache_size=50,
            circuit_breaker_threshold=5
        )

        assert client.api_key == "test-key"
        assert client.base_url == "https://test.com"
        assert client._session is None
        assert client.circuit_breaker.failure_threshold == 5

    def test_client_initialization_without_api_key(self):
        """Test client initialization without API key."""
        with patch.dict('os.environ', {}, clear=True):
            client = Context7DirectHttpClient()
            assert client.api_key is None

    @pytest.mark.asyncio
    async def test_get_session_creates_optimized_session(self, client):
        """Test that session is created with optimized settings."""
        # Patch the TCPConnector to verify it's called with correct parameters
        with patch('context7_direct_client.TCPConnector') as mock_connector, \
             patch('context7_direct_client.ClientSession') as mock_session_class:

            mock_session_instance = AsyncMock()
            mock_session_instance.closed = False
            mock_session_class.return_value = mock_session_instance

            session = await client._get_session()

            assert session is not None
            assert not session.closed

            # Verify TCPConnector was called with optimized settings
            mock_connector.assert_called_once_with(
                limit=30,
                limit_per_host=10,
                keepalive_timeout=15,
                enable_cleanup_closed=True,
                force_close=False,
                use_dns_cache=True
            )

    @pytest.mark.asyncio
    async def test_get_session_reuses_existing_session(self, client):
        """Test that existing session is reused."""
        session1 = await client._get_session()
        session2 = await client._get_session()

        assert session1 is session2

    def test_generate_cache_key(self, client):
        """Test cache key generation."""
        key1 = client._generate_cache_key('resolve', library_name='test')
        key2 = client._generate_cache_key('resolve', library_name='test')
        key3 = client._generate_cache_key('resolve', library_name='other')

        assert key1 == key2
        assert key1 != key3
        assert key1.startswith('ctx7:')

    def test_extract_library_id_from_response(self, client):
        """Test library ID extraction from various response formats."""
        # Test direct library_id field
        data1 = {'library_id': '/org/project'}
        assert client._extract_library_id(data1) == '/org/project'

        # Test id field with slash
        data2 = {'id': '/another/repo'}
        assert client._extract_library_id(data2) == '/another/repo'

        # Test nested data
        data3 = {'data': {'library_id': '/nested/lib'}}
        assert client._extract_library_id(data3) == '/nested/lib'

        # Test content extraction
        data4 = {'content': 'Library: /extract/from/text available here'}
        assert client._extract_library_id(data4) == '/extract/from/text'

        # Test no match
        data5 = {'no_library_id': 'here'}
        assert client._extract_library_id(data5) is None

    @pytest.mark.asyncio
    async def test_resolve_library_id_success(self, client, mock_session):
        """Test successful library ID resolution."""
        # Mock session already has proper context manager setup from fixture
        with patch.object(client, '_get_session', return_value=mock_session):
            result = await client.resolve_library_id('test-library')

        assert result == '/test/library'

        # Verify metrics updated
        metrics = client.get_metrics()
        assert metrics['requests_total'] == 1
        assert metrics['requests_successful'] == 1
        assert metrics['requests_failed'] == 0

    @pytest.mark.asyncio
    async def test_resolve_library_id_not_found(self, client, mock_session):
        """Test library ID resolution when library not found."""
        # Override the mock response for this test
        mock_response = AsyncMock()
        mock_response.json.return_value = {'error': 'Library not found'}
        mock_response.raise_for_status = AsyncMock()

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_context_manager

        with patch.object(client, '_get_session', return_value=mock_session):
            with pytest.raises(Context7APIError, match="Library ID not found"):
                await client.resolve_library_id('unknown-library')

    @pytest.mark.asyncio
    async def test_resolve_library_id_circuit_breaker_open(self, client):
        """Test library resolution with open circuit breaker."""
        # Force circuit breaker open
        for _ in range(3):
            client.circuit_breaker.record_failure()

        assert client.circuit_breaker.call_allowed() is False

        with pytest.raises(CircuitBreakerError):
            await client.resolve_library_id('test-library')

    @pytest.mark.asyncio
    async def test_resolve_library_id_timeout(self, client, mock_session):
        """Test library resolution with timeout."""
        # Make the context manager raise timeout
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_context_manager

        with patch.object(client, '_get_session', return_value=mock_session):
            with pytest.raises(Context7APIError, match="Timeout resolving library"):
                await client.resolve_library_id('test-library')

        # Verify circuit breaker recorded failure
        assert client.circuit_breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_resolve_library_id_http_error(self, client, mock_session):
        """Test library resolution with HTTP error."""
        import aiohttp

        # Make the context manager raise the error
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Connection failed"))
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_context_manager

        with patch.object(client, '_get_session', return_value=mock_session):
            with pytest.raises(Context7APIError, match="Failed to resolve library"):
                await client.resolve_library_id('test-library')

    @pytest.mark.asyncio
    async def test_get_library_docs_success(self, client, mock_session):
        """Test successful documentation retrieval."""
        # Override the mock response for docs
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            'content': 'This is test documentation content'
        }
        mock_response.raise_for_status = AsyncMock()

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_context_manager

        with patch.object(client, '_get_session', return_value=mock_session):
            result = await client.get_library_docs(
                '/test/library',
                topic='installation',
                tokens=3000
            )

        assert result == 'This is test documentation content'

        # Verify metrics updated
        metrics = client.get_metrics()
        assert metrics['requests_total'] == 1
        assert metrics['requests_successful'] == 1

    @pytest.mark.asyncio
    async def test_get_library_docs_with_topic(self, client, mock_session):
        """Test documentation retrieval with topic parameter."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            'documentation': 'Topic-specific documentation'
        }
        mock_response.raise_for_status = AsyncMock()

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_context_manager

        with patch.object(client, '_get_session', return_value=mock_session):
            result = await client.get_library_docs(
                '/test/library',
                topic='routing',
                tokens=2000
            )

        assert result == 'Topic-specific documentation'

    @pytest.mark.asyncio
    async def test_get_library_docs_invalid_library_id(self, client):
        """Test documentation retrieval with invalid library ID."""
        with pytest.raises(Context7APIError, match="Invalid library ID format"):
            await client.get_library_docs('invalid-id')

    @pytest.mark.asyncio
    async def test_get_library_docs_token_clamping(self, client, mock_session):
        """Test token limits are enforced."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {'content': 'docs'}
        mock_response.raise_for_status = AsyncMock()

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_context_manager

        with patch.object(client, '_get_session', return_value=mock_session):
            # Test token clamping
            await client.get_library_docs('/test/lib', tokens=15000)  # Should be clamped to 10000
            await client.get_library_docs('/test/lib', tokens=50)     # Should be clamped to 100

    @pytest.mark.asyncio
    async def test_get_library_docs_no_content_in_response(self, client, mock_session):
        """Test documentation retrieval when no content in response."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {'error': 'No documentation available'}
        mock_response.raise_for_status = AsyncMock()

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_context_manager

        with patch.object(client, '_get_session', return_value=mock_session):
            with pytest.raises(Context7APIError, match="Documentation not found"):
                await client.get_library_docs('/test/library')

    def test_get_metrics(self, client):
        """Test metrics collection."""
        metrics = client.get_metrics()

        assert 'requests_total' in metrics
        assert 'requests_successful' in metrics
        assert 'requests_failed' in metrics
        assert 'cache_hits' in metrics
        assert 'cache_misses' in metrics
        assert 'success_rate_percent' in metrics
        assert 'cache_hit_rate_percent' in metrics
        assert 'circuit_breaker' in metrics

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        client = Context7DirectHttpClient(api_key="test")

        # Patch the close method to track if it was called
        original_close = client.close
        client.close = AsyncMock()

        async with client:
            assert client is not None
            assert client.api_key == "test"

        # Verify close was called
        client.close.assert_called_once()

        # Restore original close method
        client.close = original_close

    @pytest.mark.asyncio
    async def test_multiple_concurrent_requests(self, client, mock_session):
        """Test handling multiple concurrent requests."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {'library_id': '/test/library'}
        mock_response.raise_for_status = AsyncMock()

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_context_manager

        with patch.object(client, '_get_session', return_value=mock_session):
            # Create multiple concurrent requests
            tasks = [
                client.resolve_library_id(f'library-{i}')
                for i in range(5)
            ]

            results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all(result == '/test/library' for result in results)

        # Verify all requests were counted
        metrics = client.get_metrics()
        assert metrics['requests_total'] == 5
        assert metrics['requests_successful'] == 5


# Mock class for patching aiohttp components
class MockMock:
    """Mock class for type checking in tests."""
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])