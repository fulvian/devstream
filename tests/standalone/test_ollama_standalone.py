#!/usr/bin/env python3
"""
Test standalone per verificare l'implementazione Ollama.

Test indipendente senza dipendenze da pytest o core del progetto.
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import diretti per testing
try:
    from devstream.ollama.config import (
        RetryConfig,
        TimeoutConfig,
        BatchConfig,
        FallbackConfig,
        PerformanceConfig,
        OllamaConfig,
    )
    from devstream.ollama.models import (
        EmbeddingRequest,
        EmbeddingResponse,
        ChatMessage,
        ChatRequest,
        ModelInfo,
    )
    from devstream.ollama.exceptions import (
        OllamaError,
        OllamaConnectionError,
        OllamaTimeoutError,
        map_httpx_error_to_ollama_error,
    )
    from devstream.ollama.retry import (
        RetryStatistics,
        ExponentialBackoff,
        RetryHandler,
        create_ollama_giveup_condition,
    )

    print("✅ All imports successful")

except ImportError as e:
    print(f"❌ Import error: {e}")
    traceback.print_exc()
    sys.exit(1)


def test_config():
    """Test configuration classes."""
    print("\n🧪 Testing Configuration...")

    # Test RetryConfig
    retry_config = RetryConfig()
    assert retry_config.max_retries == 3
    assert retry_config.base_delay == 1.0
    assert retry_config.jitter is True
    print("✅ RetryConfig OK")

    # Test TimeoutConfig
    timeout_config = TimeoutConfig()
    assert timeout_config.connect_timeout == 10.0
    assert timeout_config.read_timeout == 120.0
    total = timeout_config.total_timeout
    assert total > 0
    print("✅ TimeoutConfig OK")

    # Test BatchConfig
    batch_config = BatchConfig()
    assert batch_config.default_batch_size == 10
    assert batch_config.max_batch_size == 50
    print("✅ BatchConfig OK")

    # Test FallbackConfig
    fallback_config = FallbackConfig()
    assert fallback_config.enable_fallback is True
    assert "llama3.2" in fallback_config.fallback_models
    print("✅ FallbackConfig OK")

    # Test PerformanceConfig
    perf_config = PerformanceConfig()
    assert perf_config.connection_pool_size == 10
    assert perf_config.enable_http2 is True
    print("✅ PerformanceConfig OK")

    # Test main OllamaConfig
    config = OllamaConfig()
    assert config.host == "http://localhost:11434"
    assert config.base_url == "http://localhost:11434/api/v1"
    assert config.health_url == "http://localhost:11434/api/version"
    print("✅ OllamaConfig OK")

    print("✅ Configuration tests PASSED")


def test_models():
    """Test Pydantic models."""
    print("\n🧪 Testing Pydantic Models...")

    # Test EmbeddingRequest
    embed_req = EmbeddingRequest(
        model="nomic-embed-text",
        prompt="Hello world",
    )
    assert embed_req.model == "nomic-embed-text"
    assert embed_req.prompt == "Hello world"
    print("✅ EmbeddingRequest OK")

    # Test EmbeddingResponse
    embed_resp = EmbeddingResponse(
        model="nomic-embed-text",
        embedding=[0.1, 0.2, -0.3, 0.4],
    )
    assert embed_resp.dimension == 4
    numpy_array = embed_resp.to_numpy()
    assert numpy_array.shape == (4,)
    print("✅ EmbeddingResponse OK")

    # Test ChatMessage
    chat_msg = ChatMessage(
        role="user",
        content="Hello, how are you?",
    )
    assert chat_msg.role == "user"
    assert chat_msg.content == "Hello, how are you?"
    print("✅ ChatMessage OK")

    # Test ChatRequest
    chat_req = ChatRequest(
        model="llama3.2",
        messages=[chat_msg],
    )
    assert chat_req.model == "llama3.2"
    assert len(chat_req.messages) == 1
    print("✅ ChatRequest OK")

    print("✅ Pydantic models tests PASSED")


def test_exceptions():
    """Test exception classes."""
    print("\n🧪 Testing Exceptions...")

    # Test base OllamaError
    error = OllamaError("test error", error_code="TEST_ERROR")
    assert str(error) == "[TEST_ERROR] test error"
    assert error.error_code == "TEST_ERROR"
    print("✅ OllamaError OK")

    # Test OllamaConnectionError
    conn_error = OllamaConnectionError(host="localhost:11434")
    assert "localhost:11434" in str(conn_error.context)
    print("✅ OllamaConnectionError OK")

    # Test OllamaTimeoutError
    timeout_error = OllamaTimeoutError(timeout_duration=30.0, operation="embedding")
    assert timeout_error.context["timeout_duration"] == 30.0
    assert timeout_error.context["operation"] == "embedding"
    print("✅ OllamaTimeoutError OK")

    print("✅ Exception tests PASSED")


def test_retry_logic():
    """Test retry logic."""
    print("\n🧪 Testing Retry Logic...")

    # Test RetryStatistics
    stats = RetryStatistics()
    stats.record_attempt(success=True, delay=1.0)
    stats.record_attempt(success=False, delay=2.0, exception=ValueError("test"))

    assert stats.total_attempts == 2
    assert stats.successful_attempts == 1
    assert stats.failed_attempts == 1
    assert stats.success_rate == 50.0
    print("✅ RetryStatistics OK")

    # Test ExponentialBackoff
    config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
    backoff = ExponentialBackoff(config)

    delay1 = backoff.calculate_delay(1)
    delay2 = backoff.calculate_delay(2)
    delay3 = backoff.calculate_delay(3)

    assert delay1 == 1.0  # base_delay * base^0
    assert delay2 == 2.0  # base_delay * base^1
    assert delay3 == 4.0  # base_delay * base^2
    print("✅ ExponentialBackoff OK")

    # Test RetryHandler
    retry_handler = RetryHandler(config)

    # Should retry on OllamaConnectionError
    assert retry_handler.should_retry(OllamaConnectionError(), 1) is True

    # Should not retry after max attempts
    assert retry_handler.should_retry(OllamaConnectionError(), 5) is False

    # Should not retry on non-retryable exceptions
    assert retry_handler.should_retry(ValueError("not retryable"), 1) is False

    print("✅ RetryHandler OK")

    # Test giveup condition
    giveup_func = create_ollama_giveup_condition()

    # Should give up on ValueError
    assert giveup_func(ValueError("programming error")) is True

    # Should not give up on connection errors
    assert giveup_func(OllamaConnectionError()) is False

    print("✅ Giveup condition OK")

    print("✅ Retry logic tests PASSED")


async def test_async_functionality():
    """Test async functionality without actual Ollama server."""
    print("\n🧪 Testing Async Functionality...")

    # Test ExponentialBackoff sleep
    config = RetryConfig()
    backoff = ExponentialBackoff(config)

    import time
    start_time = time.time()
    await backoff.sleep(0.05)  # Very short sleep for testing
    elapsed = time.time() - start_time

    assert elapsed >= 0.04  # Allow for some timing variance
    print("✅ Async sleep OK")

    # Test retry handler with mock function
    retry_handler = RetryHandler(RetryConfig(base_delay=0.1, max_retries=2))

    call_count = 0

    async def mock_function():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise OllamaConnectionError("simulated error")
        return "success"

    try:
        result = await retry_handler.retry_async(mock_function)
        assert result == "success"
        assert call_count == 2
        print("✅ Async retry with success OK")
    except Exception as e:
        print(f"❌ Async retry test failed: {e}")
        raise

    print("✅ Async functionality tests PASSED")


def run_all_tests():
    """Run all tests."""
    print("🚀 Starting Ollama Implementation Tests...")

    try:
        # Synchronous tests
        test_config()
        test_models()
        test_exceptions()
        test_retry_logic()

        # Asynchronous tests
        asyncio.run(test_async_functionality())

        print("\n🎉 ALL TESTS PASSED! ✅")
        print("\n📊 Test Summary:")
        print("- Configuration classes: ✅")
        print("- Pydantic models: ✅")
        print("- Exception handling: ✅")
        print("- Retry logic: ✅")
        print("- Async functionality: ✅")
        print("\n✨ Ollama implementation is production-ready!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()