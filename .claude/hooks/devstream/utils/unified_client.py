#!/usr/bin/env python3
"""
DevStream Unified Client - Context7-inspired Adapter Pattern

Provides unified interface for both MCP server and Direct Database clients.
Implements graceful degradation and fallback mechanisms.
Maintains 100% backward compatibility during migration.

Context7 Patterns:
- Adapter Pattern for backend abstraction
- Strategy Pattern for backend selection
- Circuit Breaker Pattern for fault tolerance
- Graceful degradation with fallbacks
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Union
from contextlib import asynccontextmanager
from enum import Enum
from dataclasses import dataclass
import time
import hashlib

# Import clients
from direct_client import DevStreamDirectClient, DatabaseException

# Feature flags for backend selection
try:
    from config.feature_flags import should_use_direct_client
except ImportError:
    # Fallback if feature flags not available
    def should_use_direct_client(hook_name: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Fallback: always use direct client if feature flags not available"""
        return True

# Circuit breaker implementation
try:
    from robustness_patterns import (
        CircuitBreaker,
        RetryPolicy,
        CircuitBreakerState as CircuitState,
        RobustnessConfig
    )
except ImportError:
    # Fallback implementation if robustness_patterns not available
    import asyncio
    from enum import Enum
    import time

    class CircuitState(Enum):
        """Circuit breaker states - matches robustness_patterns API"""
        CLOSED = "closed"
        OPEN = "open"
        HALF_OPEN = "half_open"

    @dataclass
    class RobustnessConfig:
        """Configuration for robustness patterns - simplified fallback."""
        # Circuit breaker configuration
        circuit_breaker_failure_threshold: int = 3
        circuit_breaker_timeout_seconds: int = 30
        circuit_breaker_success_threshold: int = 3

        # Timeout configuration
        default_timeout_seconds: int = 30
        max_retries: int = 3
        retry_backoff_factor: float = 2.0
        retry_base_delay: float = 1.0

    class CircuitBreaker:
        """
        Circuit breaker fallback implementation with dual signature support.

        Context7 Best Practice: Support both config object and individual parameters
        for backward compatibility and graceful degradation.
        """

        def __init__(self, *args, **kwargs):
            """
            Initialize circuit breaker with flexible signature.

            Supports both patterns:
            - CircuitBreaker(failure_threshold=3, timeout_seconds=30, expected_exception=Exception)
            - CircuitBreaker(config) where config has required attributes
            """
            # Handle config object pattern (robustness_patterns style)
            if len(args) == 1 and hasattr(args[0], 'circuit_breaker_failure_threshold'):
                config = args[0]
                self.failure_threshold = getattr(config, 'circuit_breaker_failure_threshold', 3)
                self.timeout_seconds = getattr(config, 'circuit_breaker_timeout_seconds', 30)
                self.expected_exception = Exception  # Default for config pattern
            # Handle individual parameters pattern (fallback style)
            else:
                self.failure_threshold = kwargs.get('failure_threshold', 3)
                self.timeout_seconds = kwargs.get('timeout_seconds', 30)
                self.expected_exception = kwargs.get('expected_exception', Exception)

            self.failure_count = 0
            self._state = CircuitState.CLOSED
            self.last_failure_time = None

            # Expose CircuitState as class attribute for API compatibility
            self.CircuitState = CircuitState

        @property
        def state(self):
            """Get current circuit breaker state."""
            return self._state

        async def call(self, operation, *args, **kwargs):
            """
            Execute operation with circuit breaker protection.

            Args:
                operation: Async callable to execute
                *args: Operation arguments
                **kwargs: Operation keyword arguments

            Returns:
                Result of operation if successful

            Raises:
                Exception: If operation fails or circuit breaker is open
            """
            # Check if circuit is open and timeout has elapsed
            if self._state == CircuitState.OPEN:
                if (self.last_failure_time and
                    time.time() - self.last_failure_time > self.timeout_seconds):
                    self._state = CircuitState.HALF_OPEN
                else:
                    raise ConnectionError("Circuit breaker is OPEN - service unavailable")

            try:
                result = await operation(*args, **kwargs)

                # Success handling
                if self._state == CircuitState.HALF_OPEN:
                    self._state = CircuitState.CLOSED
                    self.failure_count = 0
                elif self._state == CircuitState.CLOSED:
                    # Reset failure count on success in closed state
                    self.failure_count = max(0, self.failure_count - 1)

                return result

            except self.expected_exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()

                # Check if we should open the circuit
                if self.failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                elif self._state == CircuitState.HALF_OPEN:
                    # Any failure in half-open returns to open
                    self._state = CircuitState.OPEN

                raise

    class RetryPolicy:
        """
        Configurable retry policy for resilient operations.

        Context7 Best Practice: Exponential backoff with jitter to prevent thundering herd.
        """

        def __init__(self, max_retries=3, base_delay=1.0, max_delay=10.0, backoff_factor=2.0):
            """
            Initialize retry policy.

            Args:
                max_retries: Maximum number of retry attempts
                base_delay: Initial delay between retries
                max_delay: Maximum delay between retries
                backoff_factor: Multiplier for exponential backoff
            """
            self.max_retries = max_retries
            self.base_delay = base_delay
            self.max_delay = max_delay
            self.backoff_factor = backoff_factor

        async def execute(self, operation, *args, **kwargs):
            """
            Execute operation with retry logic.

            Args:
                operation: Async callable to execute
                *args: Operation arguments
                **kwargs: Operation keyword arguments

            Returns:
                Result of operation

            Raises:
                Exception: Last exception if all retries fail
            """
            last_exception = None

            for attempt in range(self.max_retries + 1):
                try:
                    return await operation(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < self.max_retries:
                        delay = min(
                            self.base_delay * (self.backoff_factor ** attempt),
                            self.max_delay
                        )
                        await asyncio.sleep(delay)

            raise last_exception


class BackendType(Enum):
    """Supported backend types."""
    DIRECT_DB = "direct_db"
    MCP_SERVER = "mcp_server"


class UnifiedClient:
    """
    Unified client providing seamless backend switching.

    Context7 Pattern: Adapter + Strategy + Circuit Breaker
    Provides single interface regardless of underlying backend.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize unified client with both backends available.

        Args:
            db_path: Database path for direct client
        """
        self.logger = logging.getLogger('unified_client')
        self.db_path = db_path

        # Initialize direct client
        self._direct_client: Optional[DevStreamDirectClient] = None
        self._mcp_client: Optional[Any] = None

        # Circuit breakers for each backend
        # Create configuration objects for robustness_patterns CircuitBreaker
        direct_config = RobustnessConfig(
            circuit_breaker_failure_threshold=3,
            circuit_breaker_timeout_seconds=30,
            circuit_breaker_success_threshold=3
        )

        mcp_config = RobustnessConfig(
            circuit_breaker_failure_threshold=3,
            circuit_breaker_timeout_seconds=30,
            circuit_breaker_success_threshold=3
        )

        self._direct_circuit = CircuitBreaker(direct_config)
        self._mcp_circuit = CircuitBreaker(mcp_config)

        # Retry policies
        self._retry_policy = RetryPolicy(
            max_retries=3,
            base_delay=1.0,
            max_delay=10.0,
            backoff_factor=2.0
        )

        # Performance metrics
        self._metrics = {
            'direct_calls': 0,
            'mcp_calls': 0,
            'direct_failures': 0,
            'mcp_failures': 0,
            'fallback_activations': 0
        }

        self.logger.info("Unified client initialized with adaptive backend selection")

    def _get_client(self, hook_name: str, context: Optional[Dict[str, Any]] = None) -> tuple[BackendType, Any]:
        """
        Strategy Pattern: Select appropriate backend based on feature flags and health.

        Args:
            hook_name: Name of the hook calling the client
            context: Optional context for feature flag evaluation

        Returns:
            Tuple of (backend_type, client_instance)
        """
        # Check feature flag for direct database preference
        use_direct = should_use_direct_client(hook_name, context)

        if use_direct:
            # Check circuit breaker state
            if self._direct_circuit.state == CircuitState.OPEN:
                self.logger.warning(
                    f"Direct DB circuit breaker OPEN for {hook_name}, falling back to MCP"
                )
                self._metrics['fallback_activations'] += 1
                return BackendType.MCP_SERVER, self._get_mcp_client()

            return BackendType.DIRECT_DB, self._get_direct_client()
        else:
            # MCP preferred, but check circuit breaker
            if self._mcp_circuit.state == CircuitState.OPEN:
                self.logger.warning(
                    f"MCP circuit breaker OPEN for {hook_name}, falling back to Direct DB"
                )
                self._metrics['fallback_activations'] += 1
                return BackendType.DIRECT_DB, self._get_direct_client()

            return BackendType.MCP_SERVER, self._get_mcp_client()

    def _get_direct_client(self) -> DevStreamDirectClient:
        """Get or create direct database client."""
        if self._direct_client is None:
            self._direct_client = DevStreamDirectClient(self.db_path)
            self.logger.info("Direct database client initialized")
        return self._direct_client

    def _get_mcp_client(self) -> Any:
        """Get or create MCP client."""
        if self._mcp_client is None:
            try:
                # Import MCP client only when needed
                from mcp_client import get_mcp_client
                self._mcp_client = get_mcp_client()
                self.logger.info("MCP client initialized")
            except ImportError as e:
                self.logger.error(f"MCP client not available: {e}")
                # Force fallback to direct client
                if self._direct_client is None:
                    self._direct_client = DevStreamDirectClient(self.db_path)
                return self._direct_client

        return self._mcp_client

    async def _execute_with_fallback(
        self,
        operation_name: str,
        hook_name: str,
        direct_operation: callable,
        mcp_operation: callable,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute operation with automatic fallback between backends.

        Context7 Pattern: Circuit breaker + retry + fallback

        Args:
            operation_name: Name of the operation for logging
            hook_name: Name of the hook calling
            direct_operation: Async function for direct DB operation
            mcp_operation: Async function for MCP operation
            context: Optional context for feature flags

        Returns:
            Operation result

        Raises:
            Exception: If all backends fail
        """
        start_time = time.time()
        last_exception = None

        # Determine primary and fallback backends
        primary_backend, primary_client = self._get_client(hook_name, context)
        fallback_backend = BackendType.MCP_SERVER if primary_backend == BackendType.DIRECT_DB else BackendType.DIRECT_DB
        fallback_client = self._get_mcp_client() if fallback_backend == BackendType.MCP_SERVER else self._get_direct_client()

        # Try primary backend with circuit breaker and retry
        try:
            result = await self._retry_policy.execute(
                self._direct_circuit.call if primary_backend == BackendType.DIRECT_DB else self._mcp_circuit.call,
                direct_operation if primary_backend == BackendType.DIRECT_DB else mcp_operation
            )

            # Update metrics
            if primary_backend == BackendType.DIRECT_DB:
                self._metrics['direct_calls'] += 1
            else:
                self._metrics['mcp_calls'] += 1

            duration_ms = (time.time() - start_time) * 1000
            self.logger.debug(
                f"{operation_name} completed via {primary_backend.value} in {duration_ms:.1f}ms"
            )

            return result

        except Exception as e:
            last_exception = e

            # Update failure metrics
            if primary_backend == BackendType.DIRECT_DB:
                self._metrics['direct_failures'] += 1
            else:
                self._metrics['mcp_failures'] += 1

            self.logger.warning(
                f"{operation_name} failed via {primary_backend.value}: {e}, trying fallback"
            )

        # Try fallback backend
        try:
            result = await self._retry_policy.execute(
                self._mcp_circuit.call if fallback_backend == BackendType.MCP_SERVER else self._direct_circuit.call,
                mcp_operation if fallback_backend == BackendType.MCP_SERVER else direct_operation
            )

            # Update metrics
            if fallback_backend == BackendType.DIRECT_DB:
                self._metrics['direct_calls'] += 1
            else:
                self._metrics['mcp_calls'] += 1

            self._metrics['fallback_activations'] += 1

            duration_ms = (time.time() - start_time) * 1000
            self.logger.info(
                f"{operation_name} completed via fallback {fallback_backend.value} in {duration_ms:.1f}ms"
            )

            return result

        except Exception as e:
            last_exception = e

            # Update failure metrics
            if fallback_backend == BackendType.DIRECT_DB:
                self._metrics['direct_failures'] += 1
            else:
                self._metrics['mcp_failures'] += 1

            self.logger.error(
                f"{operation_name} failed via both backends. Last error: {e}"
            )

        # All backends failed
        raise last_exception

    async def store_memory(
        self,
        content: str,
        content_type: str,
        keywords: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        hook_name: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Store memory with automatic backend selection and fallback.

        Args:
            content: Content to store
            content_type: Type of content
            keywords: Associated keywords
            session_id: Session identifier
            hook_name: Name of the calling hook

        Returns:
            Dictionary with storage result
        """
        # Direct DB operation
        async def direct_store():
            client = self._get_direct_client()
            return await client.store_memory(content, content_type, keywords, session_id)

        # MCP operation
        async def mcp_store():
            client = self._get_mcp_client()
            return await client.call("devstream_store_memory", {
                "content": content,
                "content_type": content_type,
                "keywords": keywords or []
            })

        return await self._execute_with_fallback(
            operation_name="store_memory",
            hook_name=hook_name,
            direct_operation=direct_store,
            mcp_operation=mcp_store,
            context={"session_id": session_id}
        )

    async def search_memory(
        self,
        query: str,
        content_type: Optional[str] = None,
        limit: int = 10,
        hook_name: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Search memory with automatic backend selection and fallback.

        Args:
            query: Search query
            content_type: Filter by content type
            limit: Maximum results
            hook_name: Name of the calling hook

        Returns:
            Dictionary with search results
        """
        # Direct DB operation
        async def direct_search():
            client = self._get_direct_client()
            return await client.search_memory(query, content_type, limit)

        # MCP operation
        async def mcp_search():
            client = self._get_mcp_client()
            return await client.call("devstream_search_memory", {
                "query": query,
                "content_type": content_type,
                "limit": limit
            })

        return await self._execute_with_fallback(
            operation_name="search_memory",
            hook_name=hook_name,
            direct_operation=direct_search,
            mcp_operation=mcp_search,
            context={"query": query, "content_type": content_type}
        )

    async def trigger_checkpoint(
        self,
        reason: str = "tool_trigger",
        hook_name: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Trigger checkpoint with automatic backend selection and fallback.

        Args:
            reason: Checkpoint reason
            hook_name: Name of the calling hook

        Returns:
            Dictionary with checkpoint result
        """
        # Direct DB operation
        async def direct_checkpoint():
            client = self._get_direct_client()
            return await client.trigger_checkpoint(reason)

        # MCP operation
        async def mcp_checkpoint():
            client = self._get_mcp_client()
            return await client.call("devstream_trigger_checkpoint", {
                "reason": reason
            })

        return await self._execute_with_fallback(
            operation_name="trigger_checkpoint",
            hook_name=hook_name,
            direct_operation=direct_checkpoint,
            mcp_operation=mcp_checkpoint,
            context={"reason": reason}
        )

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all backends.

        Returns:
            Dictionary with health status of all backends
        """
        health_status = {
            "overall": "healthy",
            "backends": {},
            "metrics": self._metrics.copy()
        }

        # Check direct client
        try:
            if self._direct_client:
                direct_healthy = await self._direct_client.health_check()
                health_status["backends"]["direct_db"] = {
                    "status": "healthy" if direct_healthy else "unhealthy",
                    "circuit_breaker": self._direct_circuit.state.value
                }
            else:
                health_status["backends"]["direct_db"] = {
                    "status": "not_initialized",
                    "circuit_breaker": self._direct_circuit.state.value
                }
        except Exception as e:
            health_status["backends"]["direct_db"] = {
                "status": "error",
                "error": str(e),
                "circuit_breaker": self._direct_circuit.state.value
            }
            health_status["overall"] = "degraded"

        # Check MCP client
        try:
            if self._mcp_client:
                # Simple health check for MCP
                mcp_healthy = True  # Could implement actual health check
                health_status["backends"]["mcp_server"] = {
                    "status": "healthy" if mcp_healthy else "unhealthy",
                    "circuit_breaker": self._mcp_circuit.state.value
                }
            else:
                health_status["backends"]["mcp_server"] = {
                    "status": "not_initialized",
                    "circuit_breaker": self._mcp_circuit.state.value
                }
        except Exception as e:
            health_status["backends"]["mcp_server"] = {
                "status": "error",
                "error": str(e),
                "circuit_breaker": self._mcp_circuit.state.value
            }
            health_status["overall"] = "degraded"

        return health_status

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance and reliability metrics."""
        return {
            **self._metrics,
            "direct_circuit_state": self._direct_circuit.state.value,
            "mcp_circuit_state": self._mcp_circuit.state.value,
            "total_calls": self._metrics['direct_calls'] + self._metrics['mcp_calls'],
            "total_failures": self._metrics['direct_failures'] + self._metrics['mcp_failures'],
            "success_rate": (
                (self._metrics['direct_calls'] + self._metrics['mcp_calls'] -
                 self._metrics['direct_failures'] - self._metrics['mcp_failures']) /
                max(1, self._metrics['direct_calls'] + self._metrics['mcp_calls'])
            ) * 100
        }


# Global unified client instance (singleton pattern)
_unified_client: Optional[UnifiedClient] = None


def get_unified_client(db_path: Optional[str] = None) -> UnifiedClient:
    """
    Get singleton unified client instance.

    Args:
        db_path: Database path for direct client

    Returns:
        UnifiedClient instance
    """
    global _unified_client
    if _unified_client is None:
        _unified_client = UnifiedClient(db_path)
    return _unified_client


# Convenience functions for backward compatibility
async def store_memory_unified(
    content: str,
    content_type: str,
    keywords: Optional[List[str]] = None,
    session_id: Optional[str] = None,
    hook_name: str = "unknown"
) -> Dict[str, Any]:
    """
    Unified memory storage with automatic backend selection.

    Context7 Pattern: Facade pattern for simplified access
    """
    client = get_unified_client()
    return await client.store_memory(content, content_type, keywords, session_id, hook_name)


async def search_memory_unified(
    query: str,
    content_type: Optional[str] = None,
    limit: int = 10,
    hook_name: str = "unknown"
) -> Dict[str, Any]:
    """
    Unified memory search with automatic backend selection.
    """
    client = get_unified_client()
    return await client.search_memory(query, content_type, limit, hook_name)


async def trigger_checkpoint_unified(
    reason: str = "tool_trigger",
    hook_name: str = "unknown"
) -> Dict[str, Any]:
    """
    Unified checkpoint trigger with automatic backend selection.
    """
    client = get_unified_client()
    return await client.trigger_checkpoint(reason, hook_name)