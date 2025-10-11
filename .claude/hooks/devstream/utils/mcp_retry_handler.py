#!/usr/bin/env python3
"""
DevStream MCP Retry Handler
===========================

Advanced retry mechanism for MCP tool calls with exponential backoff,
error classification, and Context7 best practices implementation.

Features:
- Exponential backoff with jitter
- Error classification (retryable vs non-retryable)
- Circuit breaker pattern for cascade failures
- Comprehensive logging and metrics
- Context7-compliant error handling

Based on Claude Code MCP Enhanced retry patterns and industry best practices.
"""

import asyncio
import json
import time
import random
import statistics
from typing import Dict, Any, Optional, Callable, List, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

class ErrorType(Enum):
    """Classification of error types for retry decisions"""
    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"
    RATE_LIMIT = "rate_limit"
    CONCURRENCY = "concurrency"
    NETWORK = "network"
    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    SERVER_ERROR = "server_error"

@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    base_delay: float = 0.5  # seconds
    max_delay: float = 30.0  # seconds
    backoff_factor: float = 2.0
    jitter_factor: float = 0.1
    timeout: float = 60.0  # seconds per attempt
    circuit_breaker_threshold: int = 5  # failures before opening circuit
    circuit_breaker_timeout: float = 60.0  # seconds to keep circuit open

@dataclass
class RetryAttempt:
    """Data about a single retry attempt"""
    attempt_number: int
    delay: float
    error_type: Optional[ErrorType]
    error_message: str
    timestamp: datetime
    duration: float

@dataclass
class RetryResult:
    """Result of retry operation with detailed metrics"""
    success: bool
    total_attempts: int
    total_duration: float
    attempts: List[RetryAttempt]
    final_error: Optional[str]
    circuit_breaker_triggered: bool

class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascade failures.
    Opens after threshold failures and stays open for timeout period.
    """

    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half_open

    def call_allowed(self) -> bool:
        """Check if call is allowed based on circuit state"""
        if self.state == "closed":
            return True

        if self.state == "open":
            if self.last_failure_time and \
               datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = "half_open"
                logger.info("Circuit breaker moving to half-open state")
                return True
            return False

        # half_open - allow one call to test
        return True

    def record_success(self):
        """Record successful call"""
        self.failure_count = 0
        if self.state == "half_open":
            self.state = "closed"
            logger.info("Circuit breaker closed after successful call")

    def record_failure(self):
        """Record failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                "Circuit breaker opened",
                failure_count=self.failure_count,
                threshold=self.failure_threshold
            )

class MCPRetryHandler:
    """
    Advanced retry handler for MCP tool calls with Context7 best practices.
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.metrics: Dict[str, List[float]] = {}

    def classify_error(self, error: Union[str, Exception]) -> ErrorType:
        """
        Classify error type for retry decision making.
        Based on Context7 and Claude Code MCP Enhanced patterns.
        """
        error_msg = str(error).lower()

        # Network and connectivity errors
        if any(pattern in error_msg for pattern in [
            "connection", "network", "econnreset", "etimedout",
            "econnrefused", "unreachable", "dns"
        ]):
            return ErrorType.NETWORK

        # Timeout errors
        if any(pattern in error_msg for pattern in [
            "timeout", "timed out", "deadline", "timeout exceeded"
        ]):
            return ErrorType.TIMEOUT

        # Concurrency and rate limiting
        if any(pattern in error_msg for pattern in [
            "400", "concurrency", "too many requests", "rate limit",
            "429", "throttled", "quota exceeded"
        ]):
            if "concurrency" in error_msg:
                return ErrorType.CONCURRENCY
            return ErrorType.RATE_LIMIT

        # Authentication errors (non-retryable)
        if any(pattern in error_msg for pattern in [
            "401", "403", "authentication", "authorization",
            "unauthorized", "forbidden", "access denied"
        ]):
            if "401" in error_msg or "authentication" in error_msg:
                return ErrorType.AUTHENTICATION
            return ErrorType.AUTHORIZATION

        # Server errors (retryable)
        if any(pattern in error_msg for pattern in [
            "500", "502", "503", "504", "server error",
            "internal error", "service unavailable"
        ]):
            return ErrorType.SERVER_ERROR

        # Client errors (non-retryable)
        if any(pattern in error_msg for pattern in [
            "400", "404", "bad request", "not found",
            "invalid format", "syntax error", "malformed"
        ]):
            return ErrorType.NON_RETRYABLE

        # Default to retryable for unknown errors
        return ErrorType.RETRYABLE

    def is_retryable(self, error_type: ErrorType) -> bool:
        """Determine if error type is retryable"""
        retryable_types = {
            ErrorType.RETRYABLE,
            ErrorType.NETWORK,
            ErrorType.TIMEOUT,
            ErrorType.RATE_LIMIT,
            ErrorType.CONCURRENCY,
            ErrorType.SERVER_ERROR
        }
        return error_type in retryable_types

    def calculate_delay_with_jitter(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay with jitter.
        Prevents thundering herd problems.
        """
        # Exponential backoff
        delay = min(
            self.config.base_delay * (self.config.backoff_factor ** attempt),
            self.config.max_delay
        )

        # Add jitter (±jitter_factor * delay)
        jitter_range = delay * self.config.jitter_factor
        jitter = random.uniform(-jitter_range, jitter_range)

        return max(0, delay + jitter)

    def get_circuit_breaker(self, operation_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for operation"""
        if operation_name not in self.circuit_breakers:
            self.circuit_breakers[operation_name] = CircuitBreaker(
                failure_threshold=self.config.circuit_breaker_threshold,
                timeout=self.config.circuit_breaker_timeout
            )
        return self.circuit_breakers[operation_name]

    def record_metric(self, operation_name: str, duration: float):
        """Record execution duration for metrics"""
        if operation_name not in self.metrics:
            self.metrics[operation_name] = []
        self.metrics[operation_name].append(duration)

        # Keep only last 100 measurements
        if len(self.metrics[operation_name]) > 100:
            self.metrics[operation_name] = self.metrics[operation_name][-100:]

    def get_metrics_summary(self, operation_name: str) -> Dict[str, float]:
        """Get summary statistics for operation"""
        if operation_name not in self.metrics or not self.metrics[operation_name]:
            return {}

        durations = self.metrics[operation_name]
        return {
            "count": len(durations),
            "avg": statistics.mean(durations),
            "min": min(durations),
            "max": max(durations),
            "p50": statistics.median(durations),
            "p95": durations[int(len(durations) * 0.95)] if len(durations) > 20 else max(durations),
            "p99": durations[int(len(durations) * 0.99)] if len(durations) > 100 else max(durations)
        }

    async def execute_with_retry(
        self,
        operation: Callable,
        operation_name: str,
        *args,
        **kwargs
    ) -> RetryResult:
        """
        Execute operation with retry logic and comprehensive monitoring.
        Returns detailed result with metrics.
        """
        circuit_breaker = self.get_circuit_breaker(operation_name)

        # Check circuit breaker
        if not circuit_breaker.call_allowed():
            logger.warning(
                "Circuit breaker open, call blocked",
                operation=operation_name,
                failure_count=circuit_breaker.failure_count
            )
            return RetryResult(
                success=False,
                total_attempts=0,
                total_duration=0.0,
                attempts=[],
                final_error="Circuit breaker open",
                circuit_breaker_triggered=True
            )

        attempts: List[RetryAttempt] = []
        start_time = time.time()
        last_error: Optional[Exception] = None

        for attempt in range(self.config.max_retries + 1):
            attempt_start = time.time()
            delay = self.calculate_delay_with_jitter(attempt) if attempt > 0 else 0

            # Add delay between attempts (except first)
            if attempt > 0:
                logger.info(
                    "Retrying operation after delay",
                    operation=operation_name,
                    attempt=attempt + 1,
                    max_attempts=self.config.max_retries + 1,
                    delay=delay
                )
                await asyncio.sleep(delay)

            try:
                # Execute operation with timeout
                result = await asyncio.wait_for(
                    operation(*args, **kwargs),
                    timeout=self.config.timeout
                )

                # Record successful attempt
                attempt_duration = time.time() - attempt_start
                attempts.append(RetryAttempt(
                    attempt_number=attempt + 1,
                    delay=delay,
                    error_type=None,
                    error_message="",
                    timestamp=datetime.utcnow(),
                    duration=attempt_duration
                ))

                # Record metrics
                total_duration = time.time() - start_time
                self.record_metric(operation_name, total_duration)

                # Update circuit breaker
                circuit_breaker.record_success()

                logger.info(
                    "Operation succeeded",
                    operation=operation_name,
                    attempt=attempt + 1,
                    duration=total_duration
                )

                return RetryResult(
                    success=True,
                    total_attempts=attempt + 1,
                    total_duration=total_duration,
                    attempts=attempts,
                    final_error=None,
                    circuit_breaker_triggered=False
                )

            except Exception as e:
                last_error = e
                attempt_duration = time.time() - attempt_start
                error_type = self.classify_error(e)

                # Record failed attempt
                attempts.append(RetryAttempt(
                    attempt_number=attempt + 1,
                    delay=delay,
                    error_type=error_type,
                    error_message=str(e),
                    timestamp=datetime.utcnow(),
                    duration=attempt_duration
                ))

                logger.warning(
                    "Operation attempt failed",
                    operation=operation_name,
                    attempt=attempt + 1,
                    error_type=error_type.value,
                    error=str(e),
                    retryable=self.is_retryable(error_type),
                    duration=attempt_duration
                )

                # Check if we should retry
                if not self.is_retryable(error_type) or attempt == self.config.max_retries:
                    circuit_breaker.record_failure()
                    break

        # All attempts failed
        total_duration = time.time() - start_time

        logger.error(
            "Operation failed after all retries",
            operation=operation_name,
            total_attempts=len(attempts),
            total_duration=total_duration,
            final_error=str(last_error) if last_error else "Unknown error"
        )

        return RetryResult(
            success=False,
            total_attempts=len(attempts),
            total_duration=total_duration,
            attempts=attempts,
            final_error=str(last_error) if last_error else "Unknown error",
            circuit_breaker_triggered=False
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert handler state to dictionary for monitoring"""
        return {
            "config": asdict(self.config),
            "circuit_breakers": {
                name: {
                    "state": cb.state,
                    "failure_count": cb.failure_count,
                    "last_failure_time": cb.last_failure_time.isoformat() if cb.last_failure_time else None
                }
                for name, cb in self.circuit_breakers.items()
            },
            "metrics": {
                name: self.get_metrics_summary(name)
                for name in self.metrics.keys()
            }
        }

# Global retry handler instance
_retry_handler = None

def get_retry_handler(config: Optional[RetryConfig] = None) -> MCPRetryHandler:
    """Get or create global retry handler instance"""
    global _retry_handler
    if _retry_handler is None:
        _retry_handler = MCPRetryHandler(config)
    return _retry_handler

async def retry_mcp_call(
    operation: Callable,
    operation_name: str,
    config: Optional[RetryConfig] = None,
    *args,
    **kwargs
) -> RetryResult:
    """
    Convenience function to retry MCP calls.
    Main entry point for retry functionality.
    """
    handler = get_retry_handler(config)
    return await handler.execute_with_retry(operation, operation_name, *args, **kwargs)

# Example usage and testing
if __name__ == "__main__":
    async def example_operation():
        """Example operation that might fail"""
        if random.random() < 0.7:  # 70% chance of failure
            raise Exception("Random failure for testing")
        return "success"

    async def main():
        """Test the retry handler"""
        config = RetryConfig(max_retries=3, base_delay=0.1)
        result = await retry_mcp_call(example_operation, "test_operation", config)

        print(f"Result: {result.success}")
        print(f"Attempts: {result.total_attempts}")
        print(f"Duration: {result.total_duration:.2f}s")

        if not result.success:
            print(f"Final error: {result.final_error}")

    asyncio.run(main())