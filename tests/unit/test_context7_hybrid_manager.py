#!/usr/bin/env python3
"""
Unit tests for Context7 Hybrid Manager.

Tests the hybrid manager with feature flags, MCP fallback,
and performance metrics collection.
"""

import pytest
import asyncio
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

# Add path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'utils'))

from context7_hybrid_manager import (
    Context7HybridManager,
    Context7Error,
    Context7Mode,
    Context7Metrics
)


class TestContext7Metrics:
    """Test Context7 metrics functionality."""

    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = Context7Metrics()

        assert metrics.direct_calls == 0
        assert metrics.direct_successes == 0
        assert metrics.direct_failures == 0
        assert metrics.mcp_calls == 0
        assert metrics.mcp_successes == 0
        assert metrics.mcp_failures == 0
        assert metrics.fallback_activations == 0
        assert metrics.circuit_breaker_trips == 0

    def test_direct_success_rate(self):
        """Test direct mode success rate calculation."""
        metrics = Context7Metrics()
        metrics.direct_calls = 10
        metrics.direct_successes = 8

        assert metrics.get_direct_success_rate() == 80.0

    def test_direct_success_rate_no_calls(self):
        """Test direct success rate with no calls."""
        metrics = Context7Metrics()
        assert metrics.get_direct_success_rate() == 0.0

    def test_mcp_success_rate(self):
        """Test MCP mode success rate calculation."""
        metrics = Context7Metrics()
        metrics.mcp_calls = 5
        metrics.mcp_successes = 4

        assert metrics.get_mcp_success_rate() == 80.0

    def test_overall_success_rate(self):
        """Test overall success rate calculation."""
        metrics = Context7Metrics()
        metrics.direct_calls = 10
        metrics.direct_successes = 8
        metrics.mcp_calls = 5
        metrics.mcp_successes = 3

        total_calls = metrics.direct_calls + metrics.mcp_calls
        total_successes = metrics.direct_successes + metrics.mcp_successes
        expected_rate = (total_successes / total_calls) * 100

        assert metrics.get_overall_success_rate() == expected_rate


class TestContext7HybridManager:
    """Test Context7 Hybrid Manager."""

    @pytest.fixture
    async def manager(self):
        """Create a test hybrid manager."""
        manager = Context7HybridManager(direct_enabled=True, mcp_fallback=True)
        yield manager
        await manager.close()

    @pytest.fixture
    def mock_direct_client(self):
        """Create a mock direct client."""
        client = AsyncMock()
        client.resolve_library_id.return_value = "/test/library"
        client.get_library_docs.return_value = "Test documentation"
        client.close = AsyncMock()
        return client

    def test_manager_initialization(self):
        """Test hybrid manager initialization."""
        manager = Context7HybridManager(
            direct_enabled=True,
            mcp_fallback=False
        )

        assert manager.mcp_fallback is False
        assert manager._direct_enabled_override is True

    def test_manager_initialization_with_defaults(self):
        """Test hybrid manager initialization with defaults."""
        manager = Context7HybridManager()

        assert manager.mcp_fallback is True
        assert manager._direct_enabled_override is None

    @patch.dict(os.environ, {"DEVSTREAM_CONTEXT7_DIRECT_ENABLED": "true"})
    def test_should_use_direct_mode_env_true(self):
        """Test direct mode selection with environment flag true."""
        manager = Context7HybridManager()
        # Mock direct client availability
        manager.direct_client = MagicMock()

        assert manager._should_use_direct_mode() is True

    @patch.dict(os.environ, {"DEVSTREAM_CONTEXT7_DIRECT_ENABLED": "false"})
    def test_should_use_direct_mode_env_false(self):
        """Test direct mode selection with environment flag false."""
        manager = Context7HybridManager()

        assert manager._should_use_direct_mode() is False

    @patch.dict(os.environ, {"DEVSTREAM_CONTEXT7_DIRECT_ENABLED": "rollout"})
    def test_should_use_direct_mode_env_rollout(self):
        """Test direct mode selection with rollout flag."""
        manager = Context7HybridManager()
        # Mock direct client availability
        manager.direct_client = MagicMock()

        # Test hash-based rollout (deterministic for specific library names)
        # This should be False for most names, True for some
        result1 = manager._should_use_direct_mode("test-library")
        result2 = manager._should_use_direct_mode("another-library")

        # Results should be consistent (deterministic)
        assert manager._should_use_direct_mode("test-library") == result1
        assert manager._should_use_direct_mode("another-library") == result2

    def test_should_use_direct_mode_override_true(self):
        """Test direct mode selection with override true."""
        manager = Context7HybridManager(direct_enabled=True)
        manager.direct_client = MagicMock()

        assert manager._should_use_direct_mode() is True

    def test_should_use_direct_mode_override_false(self):
        """Test direct mode selection with override false."""
        manager = Context7HybridManager(direct_enabled=False)

        assert manager._should_use_direct_mode() is False

    def test_should_use_direct_mode_no_client(self):
        """Test direct mode selection when no client available."""
        manager = Context7HybridManager(direct_enabled=True)
        # Don't set direct_client

        assert manager._should_use_direct_mode() is False

    def test_record_mode_metrics_direct_success(self, manager):
        """Test recording metrics for successful direct mode."""
        manager._record_mode_metrics("direct", True, 0.5)

        assert manager.metrics.direct_calls == 1
        assert manager.metrics.direct_successes == 1
        assert manager.metrics.direct_failures == 0

    def test_record_mode_metrics_direct_failure(self, manager):
        """Test recording metrics for failed direct mode."""
        manager._record_mode_metrics("direct", False, 1.0)

        assert manager.metrics.direct_calls == 1
        assert manager.metrics.direct_successes == 0
        assert manager.metrics.direct_failures == 1
        assert manager.mode_circuit_breaker['direct_failures'] == 1

    def test_record_mode_metrics_mcp_success(self, manager):
        """Test recording metrics for successful MCP mode."""
        manager._record_mode_metrics("mcp", True, 0.3)

        assert manager.metrics.mcp_calls == 1
        assert manager.metrics.mcp_successes == 1
        assert manager.metrics.mcp_failures == 0

    @pytest.mark.asyncio
    async def test_resolve_library_id_direct_success(self, manager, mock_direct_client):
        """Test successful library resolution via direct mode."""
        manager.direct_client = mock_direct_client

        result = await manager.resolve_library_id("test-library")

        assert result == "/test/library"
        mock_direct_client.resolve_library_id.assert_called_once_with("test-library")

        # Check metrics
        assert manager.metrics.direct_calls == 1
        assert manager.metrics.direct_successes == 1

    @pytest.mark.asyncio
    async def test_resolve_library_id_direct_fallback_to_mcp(self, manager, mock_direct_client):
        """Test library resolution with direct mode failing and MCP fallback."""
        manager.direct_client = mock_direct_client
        manager.mcp_available = True
        mock_direct_client.resolve_library_id.side_effect = Exception("Direct failed")

        result = await manager.resolve_library_id("test-library")

        assert result == "/simulated/test-library"  # Simulated MCP response
        assert manager.metrics.fallback_activations == 1

        # Should have recorded both direct failure and mcp success
        assert manager.metrics.direct_failures == 1
        assert manager.metrics.mcp_successes == 1

    @pytest.mark.asyncio
    async def test_resolve_library_id_force_mcp_mode(self, manager):
        """Test library resolution forced to MCP mode."""
        manager.mcp_available = True

        result = await manager.resolve_library_id("test-library", force_mode="mcp")

        assert result == "/simulated/test-library"
        assert manager.metrics.mcp_calls == 1
        assert manager.metrics.mcp_successes == 1

    @pytest.mark.asyncio
    async def test_resolve_library_id_both_modes_fail(self, manager, mock_direct_client):
        """Test library resolution when both modes fail."""
        manager.direct_client = mock_direct_client
        manager.mcp_available = True
        mock_direct_client.resolve_library_id.side_effect = Exception("Direct failed")

        # Mock MCP to also fail
        with patch.object(manager, '_call_mcp_resolve_library', return_value=None):
            with pytest.raises(Context7Error, match="Failed to resolve library"):
                await manager.resolve_library_id("test-library")

    @pytest.mark.asyncio
    async def test_get_library_docs_direct_success(self, manager, mock_direct_client):
        """Test successful documentation retrieval via direct mode."""
        manager.direct_client = mock_direct_client

        result = await manager.get_library_docs("/test/library", topic="installation", tokens=3000)

        assert result == "Test documentation"
        mock_direct_client.get_library_docs.assert_called_once_with("/test/library", "installation", 3000)

        # Check metrics
        assert manager.metrics.direct_calls == 1
        assert manager.metrics.direct_successes == 1

    @pytest.mark.asyncio
    async def test_get_library_docs_force_mcp_mode(self, manager):
        """Test documentation retrieval forced to MCP mode."""
        manager.mcp_available = True

        result = await manager.get_library_docs("/test/library", topic="routing", tokens=2000, force_mode="mcp")

        assert "Simulated documentation for /test/library" in result
        assert "routing" in result
        assert manager.metrics.mcp_calls == 1
        assert manager.metrics.mcp_successes == 1

    @pytest.mark.asyncio
    async def test_get_library_docs_no_direct_client(self, manager):
        """Test documentation retrieval when no direct client available."""
        manager.direct_client = None
        manager.mcp_available = True

        result = await manager.get_library_docs("/test/library")

        assert result == "Simulated documentation for /test/library"
        assert manager.metrics.mcp_calls == 1

    def test_get_metrics(self, manager):
        """Test metrics collection."""
        # Add some test data
        manager.metrics.direct_calls = 10
        manager.metrics.direct_successes = 8
        manager.metrics.mcp_calls = 5
        manager.metrics.mcp_successes = 4

        metrics = manager.get_metrics()

        assert "direct" in metrics
        assert "mcp" in metrics
        assert "overall" in metrics
        assert "configuration" in metrics

        # Check direct metrics
        assert metrics["direct"]["calls"] == 10
        assert metrics["direct"]["successes"] == 8
        assert metrics["direct"]["success_rate"] == 80.0

        # Check overall metrics
        assert metrics["overall"]["total_calls"] == 15
        assert metrics["overall"]["total_successes"] == 12
        assert metrics["overall"]["success_rate"] == 80.0

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        async with Context7HybridManager() as manager:
            assert manager is not None
            assert isinstance(manager, Context7HybridManager)

        # Client should be closed after context exit
        # (we can't easily test this without more complex mocking)

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, manager, mock_direct_client):
        """Test handling multiple concurrent operations."""
        manager.direct_client = mock_direct_client

        # Create multiple concurrent tasks
        tasks = [
            manager.resolve_library_id(f'library-{i}')
            for i in range(3)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert all(result == "/test/library" for result in results)

        # Verify all calls were counted
        assert manager.metrics.direct_calls == 3
        assert manager.metrics.direct_successes == 3

    @pytest.mark.asyncio
    async def test_mcp_availability_check(self):
        """Test MCP availability check."""
        manager = Context7HybridManager()
        # The check should not raise an exception
        available = manager._check_mcp_availability()
        assert isinstance(available, bool)

    @pytest.mark.asyncio
    async def test_close(self, manager, mock_direct_client):
        """Test manager cleanup."""
        manager.direct_client = mock_direct_client

        await manager.close()

        mock_direct_client.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])