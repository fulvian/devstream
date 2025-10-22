#!/usr/bin/env python3
"""
Integration tests for Context7 Hybrid Manager.

Tests end-to-end functionality including:
- Direct mode resolution and documentation retrieval
- MCP fallback mechanisms
- Feature flag gradual rollout logic
- Performance metrics collection
- Circuit breaker functionality
"""

import pytest
import asyncio
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

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


class TestContext7HybridIntegration:
    """Integration tests for Context7 Hybrid Manager."""

    @pytest.fixture
    async def hybrid_manager(self):
        """Create hybrid manager for testing."""
        manager = Context7HybridManager(direct_enabled=True, mcp_fallback=True)
        yield manager
        await manager.close()

    @pytest.fixture
    def mock_direct_client(self):
        """Create a mock direct client."""
        client = AsyncMock()
        client.resolve_library_id.return_value = "/test/library"
        client.get_library_docs.return_value = "Test documentation content"
        client.close = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_direct_mode_resolution(self, hybrid_manager, mock_direct_client):
        """Test library resolution in direct mode."""
        hybrid_manager.direct_client = mock_direct_client

        result = await hybrid_manager.resolve_library_id("test-library")

        assert result == "/test/library"
        mock_direct_client.resolve_library_id.assert_called_once_with("test-library")

        # Check metrics
        metrics = hybrid_manager.get_metrics()
        assert metrics["direct"]["calls"] == 1
        assert metrics["direct"]["successes"] == 1
        assert metrics["direct"]["success_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_mcp_fallback_on_direct_failure(self, hybrid_manager, mock_direct_client):
        """Test MCP fallback when direct mode fails."""
        hybrid_manager.direct_client = mock_direct_client
        hybrid_manager.mcp_available = True
        mock_direct_client.resolve_library_id.side_effect = Exception("Direct failed")

        result = await hybrid_manager.resolve_library_id("test-library")

        assert result == "/simulated/test-library"  # Simulated MCP response
        assert hybrid_manager.metrics.fallback_activations == 1

        # Check metrics
        metrics = hybrid_manager.get_metrics()
        assert metrics["direct"]["failures"] == 1
        assert metrics["mcp"]["successes"] == 1
        assert metrics["overall"]["fallback_activations"] == 1

    @pytest.mark.asyncio
    async def test_feature_flag_rollout_logic(self):
        """Test gradual rollout feature flag logic."""
        # Test with rollout enabled
        manager = Context7HybridManager(direct_enabled=None)  # Will use env
        manager.direct_client = MagicMock()  # Mock direct client as available

        with patch.dict(os.environ, {"DEVSTREAM_CONTEXT7_DIRECT_ENABLED": "rollout"}):
            # Test consistency - same library should always return same result
            result1 = manager._should_use_direct_mode("test-library")
            result2 = manager._should_use_direct_mode("test-library")
            assert result1 == result2

            # Test distribution - should be approximately 10% true
            test_libraries = [f"lib-{i}" for i in range(100)]
            true_count = sum(manager._should_use_direct_mode(lib) for lib in test_libraries)
            assert 5 <= true_count <= 15  # Allow some variance in hash distribution

            # Test different libraries get different results
            results = [manager._should_use_direct_mode(f"unique-lib-{i}") for i in range(20)]
            # Should have mixed results
            assert any(results) and any(not r for r in results)

    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self, hybrid_manager, mock_direct_client):
        """Test circuit breaker triggers fallback."""
        hybrid_manager.direct_client = mock_direct_client
        hybrid_manager.mcp_available = True

        # Simulate direct client failures
        mock_direct_client.resolve_library_id.side_effect = [
            Exception("Failure 1"),
            Exception("Failure 2"),
            Exception("Failure 3"),
            "/success-after-circuit-breaker"
        ]

        # First 3 calls should fail and trigger fallback
        for i in range(3):
            result = await hybrid_manager.resolve_library_id(f"test-lib-{i}")
            assert result == f"/simulated/test-lib-{i}"  # MCP fallback

        # Check circuit breaker state
        circuit_breaker = hybrid_manager.mode_circuit_breaker
        assert circuit_breaker['direct_failures'] == 3

    @pytest.mark.asyncio
    async def test_pre_tool_use_integration(self):
        """Test PreToolUse hook integration."""
        # This would test the actual integration with PreToolUse
        # For now, we'll simulate the integration

        # Simulate Python code with FastAPI imports
        sample_content = '''
from fastapi import FastAPI
from pydantic import BaseModel
import pytest

app = FastAPI()

class User(BaseModel):
    name: str
    email: str

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}
'''

        # Create manager
        manager = Context7HybridManager(direct_enabled=True)
        mock_client = AsyncMock()
        mock_client.resolve_library_id.return_value = "/fastapi/fastapi"
        mock_client.get_library_docs.return_value = "FastAPI documentation"
        mock_client.close = AsyncMock()
        manager.direct_client = mock_client

        try:
            # Simulate what PreToolUse would do
            libraries = ["fastapi", "pydantic", "pytest"]
            docs_sections = []

            for lib in libraries[:1]:  # Test with just FastAPI
                library_id = await manager.resolve_library_id(lib)
                if library_id:
                    docs = await manager.get_library_docs(library_id)
                    if docs:
                        docs_sections.append(f"### {lib.title()} ({library_id})\n\n{docs}")

            assert len(docs_sections) == 1
            assert "Fastapi (/fastapi/fastapi)" in docs_sections[0]

        finally:
            await manager.close()

    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self, hybrid_manager, mock_direct_client):
        """Test metrics collection for monitoring."""
        hybrid_manager.direct_client = mock_direct_client

        # Perform multiple operations
        operations = [
            ("resolve", "fastapi"),
            ("resolve", "django"),
            ("docs", "/fastapi/fastapi"),
            ("docs", "/django/django")
        ]

        for op_type, param in operations:
            if op_type == "resolve":
                await hybrid_manager.resolve_library_id(param)
            else:
                await hybrid_manager.get_library_docs(param)

        # Check metrics
        metrics = hybrid_manager.get_metrics()

        assert metrics["direct"]["calls"] == 4
        assert metrics["direct"]["successes"] == 4
        assert metrics["direct"]["success_rate"] == 100.0
        assert metrics["overall"]["total_calls"] == 4
        assert metrics["overall"]["success_rate"] == 100.0

        # Check configuration section
        assert "configuration" in metrics
        config = metrics["configuration"]
        assert config["direct_enabled_override"] is True
        assert config["mcp_fallback"] is True

    @pytest.mark.asyncio
    async def test_end_to_end_documentation_retrieval(self, hybrid_manager):
        """Test complete flow from library detection to docs retrieval."""
        # Mock direct client
        mock_direct_client = AsyncMock()
        mock_direct_client.resolve_library_id.return_value = "/fastapi/fastapi"
        mock_direct_client.get_library_docs.return_value = """
        FastAPI is a modern, fast (high-performance) web framework for building APIs with Python 3.6+ based on standard Python type hints.

        Key features:
        - Fast: Very high performance, on par with NodeJS and Go (thanks to Starlette and Pydantic).
        - Fast to code: Increase the speed to develop features by about 200% to 300% *.
        - Fewer bugs: Reduce about 40% of human-induced bugs. *
        - Intuitive: Great editor support. Completion everywhere. Less time debugging.
        - Easy: Designed to be easy to learn and use. Less time reading docs.
        - Short: Minimize code duplication. Multiple features from each parameter declaration.
        """
        hybrid_manager.direct_client = mock_direct_client

        try:
            # Simulate detecting libraries from code
            detected_libraries = ["fastapi", "pydantic", "pytest"]

            # Process each library
            retrieved_docs = []
            for lib in detected_libraries:
                # Resolve library ID
                library_id = await hybrid_manager.resolve_library_id(lib)
                if library_id:
                    # Get documentation
                    docs = await hybrid_manager.get_library_docs(
                        library_id=library_id,
                        topic="routing" if lib == "fastapi" else None,
                        tokens=1500
                    )
                    if docs:
                        retrieved_docs.append({
                            "library": lib,
                            "library_id": library_id,
                            "documentation": docs
                        })

            # Validate results
            assert len(retrieved_docs) == 3  # All libraries processed
            assert all(doc["library"] in detected_libraries for doc in retrieved_docs)

            # Check metrics
            metrics = hybrid_manager.get_metrics()
            assert metrics["direct"]["calls"] == 6  # 3 resolve + 3 docs
            assert metrics["direct"]["successes"] == 6

        finally:
            await hybrid_manager.close()

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, hybrid_manager, mock_direct_client):
        """Test concurrent operations don't interfere with each other."""
        hybrid_manager.direct_client = mock_direct_client

        # Create multiple concurrent tasks
        tasks = []
        for i in range(10):
            # Mix of resolve and docs operations
            if i % 2 == 0:
                tasks.append(hybrid_manager.resolve_library_id(f"library-{i}"))
            else:
                tasks.append(hybrid_manager.get_library_docs(f"/library-{i}", tokens=1000))

        # Execute all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check all succeeded
        assert all(not isinstance(r, Exception) for r in results)
        assert len(results) == 10

        # Check metrics
        metrics = hybrid_manager.get_metrics()
        assert metrics["direct"]["calls"] == 10
        assert metrics["direct"]["successes"] == 10
        assert metrics["direct"]["success_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_error_scenarios_comprehensive(self, hybrid_manager):
        """Test comprehensive error scenarios and graceful degradation."""
        # Test with no direct client
        hybrid_manager.direct_client = None
        hybrid_manager.mcp_available = False

        # Should fail gracefully
        with pytest.raises(Context7Error):
            await hybrid_manager.resolve_library_id("unknown-lib")

        # Test with direct client that fails
        mock_client = AsyncMock()
        mock_client.resolve_library_id.side_effect = Exception("Direct client failed")
        hybrid_manager.direct_client = mock_client
        hybrid_manager.mcp_available = False

        # Should fail gracefully without fallback
        with pytest.raises(Context7Error):
            await hybrid_manager.resolve_library_id("unknown-lib")

        # Test with direct client and MCP fallback
        hybrid_manager.mcp_available = True
        result = await hybrid_manager.resolve_library_id("unknown-lib")
        assert result == "/simulated/unknown-lib"  # MCP fallback succeeded

    @pytest.mark.asyncio
    async def test_memory_cleanup(self, hybrid_manager, mock_direct_client):
        """Test proper resource cleanup."""
        hybrid_manager.direct_client = mock_direct_client

        # Use the manager
        await hybrid_manager.resolve_library_id("test-lib")
        await hybrid_manager.get_library_docs("/test/lib")

        # Check client exists
        assert hybrid_manager.direct_client is not None

        # Close and verify cleanup
        await hybrid_manager.close()
        mock_direct_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_configuration_changes_at_runtime(self):
        """Test configuration changes during runtime."""
        # Create manager with direct mode
        manager = Context7HybridManager(direct_enabled=True, mcp_fallback=True)
        manager.direct_client = AsyncMock()

        # Test direct mode works
        should_use_direct = manager._should_use_direct_mode("test-lib")
        assert should_use_direct is True

        # Change configuration
        manager._direct_enabled_override = False

        # Test MCP mode now
        should_use_direct = manager._should_use_direct_mode("test-lib")
        assert should_use_direct is False

        await manager.close()

    @pytest.mark.asyncio
    async def test_token_budget_management(self, hybrid_manager, mock_direct_client):
        """Test token budget is respected in documentation requests."""
        hybrid_manager.direct_client = mock_direct_client

        # Request documentation with specific token limits
        await hybrid_manager.get_library_docs(
            "/test/library",
            topic="routing",
            tokens=3000
        )

        # Verify the call was made with correct parameters (called with positional args)
        mock_direct_client.get_library_docs.assert_called_once_with(
            "/test/library",
            "routing",
            3000
        )

        await hybrid_manager.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])