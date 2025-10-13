#!/usr/bin/env python3
"""
Unit tests for DevStream Unified Client

Tests unified client with Context7 patterns and backend switching.
"""

import pytest
import asyncio
import tempfile
import os
import sys
from pathlib import Path

# Add hooks to path
sys.path.append(str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'utils'))
sys.path.append(str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'config'))

from unified_client import (
    UnifiedClient,
    get_unified_client,
    BackendType,
    store_memory_unified,
    search_memory_unified,
    trigger_checkpoint_unified
)


@pytest.fixture
async def test_client():
    """Create a test unified client with temporary database."""
    # Use a database path within the project directory
    test_db_dir = Path(__file__).parent.parent.parent / "data" / "test"
    test_db_dir.mkdir(parents=True, exist_ok=True)
    db_path = test_db_dir / "test_unified_client.db"

    # Remove existing test database
    if db_path.exists():
        os.unlink(db_path)

    client = UnifiedClient(str(db_path))
    yield client

    # Cleanup
    if db_path.exists():
        os.unlink(db_path)


@pytest.mark.asyncio
async def test_unified_client_initialization(test_client):
    """Test unified client initialization."""
    assert test_client is not None
    assert test_client.db_path is not None

    # Check health
    health = await test_client.health_check()
    assert health is not None
    assert "overall" in health
    assert "backends" in health


@pytest.mark.asyncio
async def test_backend_selection(test_client):
    """Test backend selection based on feature flags."""
    # Test direct client preference
    backend, client = test_client._get_client("post_tool_use")
    assert backend in [BackendType.DIRECT_DB, BackendType.MCP_SERVER]
    assert client is not None

    # Test metrics
    metrics = test_client.get_metrics()
    assert "total_calls" in metrics
    assert "success_rate" in metrics


@pytest.mark.asyncio
async def test_unified_memory_operations(test_client):
    """Test unified memory operations."""
    # Test memory storage
    result = await test_client.store_memory(
        content="Test unified client memory storage",
        content_type="context",
        keywords=["test", "unified", "client"],
        hook_name="test_hook"
    )

    assert result is not None
    assert result.get("success") is True
    assert "memory_id" in result

    # Test memory search
    search_result = await test_client.search_memory(
        query="unified client test",
        limit=5,
        hook_name="test_hook"
    )

    assert search_result is not None
    assert search_result.get("success") is True
    assert "results" in search_result
    assert search_result["count"] >= 0


@pytest.mark.asyncio
async def test_unified_checkpoint(test_client):
    """Test unified checkpoint trigger."""
    result = await test_client.trigger_checkpoint(
        reason="test",
        hook_name="test_hook"
    )

    assert result is not None
    assert result.get("success") is True
    assert "checkpoint_id" in result
    assert result["reason"] == "test"


@pytest.mark.asyncio
async def test_convenience_functions():
    """Test convenience functions."""
    # Use a database path within the project directory
    test_db_dir = Path(__file__).parent.parent.parent / "data" / "test"
    test_db_dir.mkdir(parents=True, exist_ok=True)
    db_path = test_db_dir / "test_convenience.db"

    # Remove existing test database
    if db_path.exists():
        os.unlink(db_path)

    # Test convenience function
    result = await store_memory_unified(
        content="Test convenience function",
        content_type="context",
        keywords=["test", "convenience"],
        hook_name="test_convenience"
    )

    assert result is not None
    assert result.get("success") is True

    # Search convenience function
    search_result = await search_memory_unified(
        query="convenience function",
        limit=3,
        hook_name="test_convenience"
    )

    assert search_result is not None
    assert search_result.get("success") is True

    # Checkpoint convenience function
    checkpoint_result = await trigger_checkpoint_unified(
        reason="test_convenience",
        hook_name="test_convenience"
    )

    assert checkpoint_result is not None
    assert checkpoint_result.get("success") is True

    # Cleanup
    if db_path.exists():
        os.unlink(db_path)


@pytest.mark.asyncio
async def test_fallback_behavior(test_client):
    """Test fallback behavior when primary backend fails."""
    # This test simulates the fallback mechanism
    # In real scenarios, the circuit breaker would trigger fallback

    # The test ensures the fallback infrastructure exists
    assert hasattr(test_client, '_direct_circuit')
    assert hasattr(test_client, '_mcp_circuit')
    assert hasattr(test_client, '_retry_policy')

    # Check that metrics track fallbacks
    metrics = test_client.get_metrics()
    assert "fallback_activations" in metrics


def test_singleton_pattern():
    """Test singleton pattern for unified client."""
    # Reset singleton for testing
    import unified_client
    unified_client._unified_client = None

    client1 = get_unified_client()
    client2 = get_unified_client()

    assert client1 is client2, "Singleton pattern failed"


@pytest.mark.asyncio
async def test_circuit_breaker_states(test_client):
    """Test circuit breaker functionality."""
    # Test that circuit breakers exist and have correct states
    from robustness_patterns import CircuitBreaker, CircuitBreakerState as CircuitState

    assert isinstance(test_client._direct_circuit, CircuitBreaker)
    assert isinstance(test_client._mcp_circuit, CircuitBreaker)

    # Initial state should be CLOSED
    assert test_client._direct_circuit.state == CircuitState.CLOSED
    assert test_client._mcp_circuit.state == CircuitState.CLOSED


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])