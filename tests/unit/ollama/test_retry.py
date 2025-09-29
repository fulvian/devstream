"""
Unit tests for Ollama retry mechanisms.

Tests exponential backoff, retry logic, and error handling.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import ollama

from devstream.ollama.retry import (
    RetryStatistics,
    ExponentialBackoff,
    RetryHandler,
    with_retry,
    create_ollama_giveup_condition,
    retry_with_exponential_backoff,
)
from devstream.ollama.config import RetryConfig
from devstream.ollama.exceptions import (
    OllamaError,
    OllamaConnectionError,
    OllamaRetryExhaustedError,
    OllamaServerError,
)


class TestRetryStatistics:
    """Test retry statistics tracking."""

    def test_initial_state(self):
        """Test initial statistics state."""
        stats = RetryStatistics()
        assert stats.total_attempts == 0
        assert stats.successful_attempts == 0
        assert stats.failed_attempts == 0
        assert stats.total_delay == 0.0
        assert stats.last_attempt_time is None
        assert stats.exception_counts == {}

    def test_record_successful_attempt(self):
        """Test recording successful attempt."""
        stats = RetryStatistics()
        stats.record_attempt(success=True, delay=1.5)

        assert stats.total_attempts == 1
        assert stats.successful_attempts == 1
        assert stats.failed_attempts == 0
        assert stats.total_delay == 1.5
        assert stats.last_attempt_time is not None

    def test_record_failed_attempt(self):
        """Test recording failed attempt."""
        stats = RetryStatistics()
        exception = ValueError("test error")
        stats.record_attempt(success=False, delay=2.0, exception=exception)

        assert stats.total_attempts == 1
        assert stats.successful_attempts == 0
        assert stats.failed_attempts == 1
        assert stats.total_delay == 2.0
        assert stats.exception_counts["ValueError"] == 1

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        stats = RetryStatistics()

        # No attempts
        assert stats.success_rate == 0.0

        # Mixed attempts
        stats.record_attempt(success=True)
        stats.record_attempt(success=False)
        stats.record_attempt(success=True)

        assert stats.success_rate == 2.0 / 3 * 100  # 66.67%

    def test_average_delay_calculation(self):
        """Test average delay calculation."""
        stats = RetryStatistics()

        # No failed attempts
        stats.record_attempt(success=True, delay=1.0)
        assert stats.average_delay == 1.0  # Uses max(failed_attempts, 1)

        # With failed attempts
        stats.record_attempt(success=False, delay=2.0)
        stats.record_attempt(success=False, delay=4.0)
        assert stats.average_delay == 7.0 / 2  # Total delay / failed attempts

    def test_reset(self):
        """Test statistics reset."""
        stats = RetryStatistics()
        stats.record_attempt(success=True, delay=1.0)
        stats.record_attempt(success=False, delay=2.0, exception=ValueError())

        stats.reset()

        assert stats.total_attempts == 0
        assert stats.successful_attempts == 0
        assert stats.failed_attempts == 0
        assert stats.total_delay == 0.0
        assert stats.exception_counts == {}


class TestExponentialBackoff:
    """Test exponential backoff implementation."""

    def test_calculate_delay_progression(self):
        """Test exponential delay calculation progression."""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=60.0,
            jitter=False,
        )
        backoff = ExponentialBackoff(config)

        # Test progression: 1, 2, 4, 8, 16, ...
        assert backoff.calculate_delay(0) == 0.0  # No delay for attempt 0
        assert backoff.calculate_delay(1) == 1.0  # base_delay
        assert backoff.calculate_delay(2) == 2.0  # base_delay * base^1
        assert backoff.calculate_delay(3) == 4.0  # base_delay * base^2
        assert backoff.calculate_delay(4) == 8.0  # base_delay * base^3

    def test_max_delay_limit(self):
        """Test maximum delay limiting."""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=5.0,
            jitter=False,
        )
        backoff = ExponentialBackoff(config)

        # Should be capped at max_delay
        assert backoff.calculate_delay(10) == 5.0

    def test_jitter_enabled(self):
        """Test jitter randomization."""
        config = RetryConfig(
            base_delay=4.0,
            exponential_base=2.0,
            max_delay=60.0,
            jitter=True,
        )
        backoff = ExponentialBackoff(config)

        # With jitter, delays should vary but be within range
        delays = [backoff.calculate_delay(2) for _ in range(10)]

        # Base delay for attempt 2 should be 8.0
        # With ±25% jitter, range should be 6.0 to 10.0
        assert all(6.0 <= delay <= 10.0 for delay in delays)
        assert len(set(delays)) > 1  # Should have variation

    def test_minimum_delay_with_jitter(self):
        """Test minimum delay with jitter."""
        config = RetryConfig(
            base_delay=0.2,
            exponential_base=2.0,
            jitter=True,
        )
        backoff = ExponentialBackoff(config)

        # Even with negative jitter, should maintain minimum
        delay = backoff.calculate_delay(1)
        assert delay >= 0.1  # Minimum delay

    @pytest.mark.asyncio
    async def test_sleep_method(self):
        """Test async sleep method."""
        config = RetryConfig()
        backoff = ExponentialBackoff(config)

        start_time = time.time()
        await backoff.sleep(0.1)
        elapsed = time.time() - start_time

        assert elapsed >= 0.09  # Allow for some timing variance
        assert elapsed < 0.2  # But not too much


class TestRetryHandler:
    """Test retry handler functionality."""

    def test_should_retry_logic(self):
        """Test retry decision logic."""
        config = RetryConfig(
            max_retries=3,
            retry_on_status_codes=[429, 503],
            retry_on_timeout=True,
            retry_on_connection_error=True,
        )
        handler = RetryHandler(config)

        # Should retry on retryable exceptions
        assert handler.should_retry(OllamaConnectionError(), 1) is True
        assert handler.should_retry(httpx.TimeoutException("timeout"), 1) is True

        # Should not retry after max attempts
        assert handler.should_retry(OllamaConnectionError(), 4) is False

        # Should not retry on non-retryable exceptions
        assert handler.should_retry(ValueError("not retryable"), 1) is False

    def test_should_retry_http_status_codes(self):
        """Test retry logic for HTTP status codes."""
        config = RetryConfig(retry_on_status_codes=[429, 503])
        handler = RetryHandler(config)

        # Mock HTTPStatusError
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        error_429 = httpx.HTTPStatusError("Too Many Requests", request=MagicMock(), response=mock_response_429)

        mock_response_404 = MagicMock()
        mock_response_404.status_code = 404
        error_404 = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=mock_response_404)

        # Should retry 429
        assert handler.should_retry(error_429, 1) is True

        # Should not retry 404 (not in retry list)
        assert handler.should_retry(error_404, 1) is False

    def test_should_retry_with_giveup_condition(self):
        """Test retry with custom giveup condition."""
        def custom_giveup(exc):
            return isinstance(exc, ValueError)

        config = RetryConfig()
        handler = RetryHandler(config, giveup_condition=custom_giveup)

        # Should not retry when giveup condition is met
        assert handler.should_retry(ValueError("give up"), 1) is False

        # Should retry when giveup condition is not met
        assert handler.should_retry(OllamaConnectionError(), 1) is True

    @pytest.mark.asyncio
    async def test_retry_async_success_on_first_attempt(self):
        """Test successful operation on first attempt."""
        config = RetryConfig()
        handler = RetryHandler(config)

        async def successful_func():
            return "success"

        result = await handler.retry_async(successful_func)
        assert result == "success"
        assert handler.backoff.statistics.total_attempts == 1
        assert handler.backoff.statistics.successful_attempts == 1

    @pytest.mark.asyncio
    async def test_retry_async_success_after_retries(self):
        """Test successful operation after retries."""
        config = RetryConfig(base_delay=0.1, jitter=False)  # Fast testing
        handler = RetryHandler(config)

        call_count = 0

        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OllamaConnectionError("connection failed")
            return "success"

        result = await handler.retry_async(flaky_func)
        assert result == "success"
        assert call_count == 3
        assert handler.backoff.statistics.total_attempts == 3
        assert handler.backoff.statistics.successful_attempts == 1

    @pytest.mark.asyncio
    async def test_retry_async_exhausted(self):
        """Test retry exhaustion."""
        config = RetryConfig(max_retries=2, base_delay=0.1)
        handler = RetryHandler(config)

        async def always_fails():
            raise OllamaConnectionError("always fails")

        with pytest.raises(OllamaRetryExhaustedError) as exc_info:
            await handler.retry_async(always_fails)

        assert exc_info.value.context["max_retries"] == 2
        assert "always fails" in str(exc_info.value.original_error)

    @pytest.mark.asyncio
    async def test_retry_async_with_sync_function(self):
        """Test retry with synchronous function."""
        config = RetryConfig()
        handler = RetryHandler(config)

        def sync_func():
            return "sync_result"

        result = await handler.retry_async(sync_func)
        assert result == "sync_result"

    @pytest.mark.asyncio
    async def test_retry_event_handlers(self):
        """Test retry event handlers are called."""
        config = RetryConfig(max_retries=2, base_delay=0.1)

        backoff_calls = []
        giveup_calls = []
        success_calls = []

        def on_backoff(details):
            backoff_calls.append(details)

        def on_giveup(details):
            giveup_calls.append(details)

        def on_success(details):
            success_calls.append(details)

        handler = RetryHandler(
            config,
            on_backoff=on_backoff,
            on_giveup=on_giveup,
            on_success=on_success,
        )

        # Test successful after retry
        call_count = 0

        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OllamaConnectionError("fail once")
            return "success"

        result = await handler.retry_async(flaky_func)

        assert result == "success"
        assert len(backoff_calls) == 1
        assert len(success_calls) == 1
        assert len(giveup_calls) == 0

        # Test giveup
        async def always_fails():
            raise OllamaConnectionError("always fails")

        with pytest.raises(OllamaRetryExhaustedError):
            await handler.retry_async(always_fails)

        assert len(giveup_calls) == 1


class TestRetryDecorator:
    """Test retry decorator functionality."""

    @pytest.mark.asyncio
    async def test_with_retry_decorator(self):
        """Test with_retry decorator."""
        config = RetryConfig(base_delay=0.1)

        call_count = 0

        @with_retry(config)
        async def decorated_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OllamaConnectionError("retry me")
            return f"attempt {call_count}"

        result = await decorated_func()
        assert result == "attempt 3"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_with_retry_custom_exceptions(self):
        """Test with_retry with custom exception types."""
        config = RetryConfig(base_delay=0.1)

        @with_retry(config, exceptions=(ValueError,))
        async def value_error_func():
            raise ValueError("retryable")

        @with_retry(config, exceptions=(ValueError,))
        async def type_error_func():
            raise TypeError("not retryable")

        # Should retry ValueError
        with pytest.raises(OllamaRetryExhaustedError):
            await value_error_func()

        # Should not retry TypeError, should get original exception
        with pytest.raises(TypeError):
            await type_error_func()


class TestOllamaGiveupCondition:
    """Test Ollama-specific giveup conditions."""

    def test_auth_errors_give_up(self):
        """Test that authentication errors trigger giveup."""
        giveup_func = create_ollama_giveup_condition()

        # Mock 401 Unauthorized
        mock_response_401 = MagicMock()
        mock_response_401.status_code = 401
        auth_error = httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=mock_response_401)

        assert giveup_func(auth_error) is True

        # Mock 403 Forbidden
        mock_response_403 = MagicMock()
        mock_response_403.status_code = 403
        forbidden_error = httpx.HTTPStatusError("Forbidden", request=MagicMock(), response=mock_response_403)

        assert giveup_func(forbidden_error) is True

    def test_client_errors_give_up(self):
        """Test that most 4xx errors trigger giveup."""
        giveup_func = create_ollama_giveup_condition()

        # Mock OllamaServerError with 400
        server_error = OllamaServerError(status_code=400)
        assert giveup_func(server_error) is True

        # Mock OllamaServerError with 408 (should not give up)
        timeout_error = OllamaServerError(status_code=408)
        assert giveup_func(timeout_error) is False

        # Mock OllamaServerError with 429 (should not give up)
        rate_limit_error = OllamaServerError(status_code=429)
        assert giveup_func(rate_limit_error) is False

    def test_programming_errors_give_up(self):
        """Test that programming errors trigger giveup."""
        giveup_func = create_ollama_giveup_condition()

        assert giveup_func(ValueError("bad input")) is True
        assert giveup_func(TypeError("type error")) is True
        assert giveup_func(AttributeError("attribute error")) is True

    def test_retryable_errors_continue(self):
        """Test that retryable errors don't trigger giveup."""
        giveup_func = create_ollama_giveup_condition()

        assert giveup_func(OllamaConnectionError()) is False
        assert giveup_func(httpx.TimeoutException("timeout")) is False
        assert giveup_func(httpx.ConnectError("connect failed")) is False


class TestRetryUtilityFunction:
    """Test retry utility function."""

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self):
        """Test utility function for one-off retries."""
        config = RetryConfig(base_delay=0.1)

        call_count = 0

        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OllamaConnectionError("retry me")
            return "success"

        result = await retry_with_exponential_backoff(test_func, config)
        assert result == "success"
        assert call_count == 2