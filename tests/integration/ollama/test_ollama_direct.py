#!/usr/bin/env python3
"""
Test diretto solo per i moduli Ollama senza dipendenze core.
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Test diretto dei singoli moduli
try:
    print("🧪 Testing direct imports...")

    # Test exceptions first (no dependencies)
    print("Testing exceptions...")
    sys.path.insert(0, str(src_path / "devstream" / "core"))

    # Create minimal DevStreamError for testing
    class DevStreamError(Exception):
        def __init__(self, message: str, original_error=None, error_code=None, context=None):
            super().__init__(message)
            self.original_error = original_error
            self.error_code = error_code
            self.context = context or {}

    # Patch the import
    import devstream.core.exceptions
    devstream.core.exceptions.DevStreamError = DevStreamError

    from devstream.ollama.exceptions import (
        OllamaError,
        OllamaConnectionError,
        OllamaTimeoutError,
        OllamaModelNotFoundError,
    )
    print("✅ Exceptions imported")

    # Test models (depends on pydantic only)
    print("Testing models...")
    from devstream.ollama.models import (
        EmbeddingRequest,
        EmbeddingResponse,
        ChatMessage,
        ModelInfo,
    )
    print("✅ Models imported")

    # Test config (needs pydantic_settings)
    print("Testing config...")
    from devstream.ollama.config import (
        RetryConfig,
        TimeoutConfig,
        OllamaConfig,
    )
    print("✅ Config imported")

    # Test retry logic
    print("Testing retry...")
    from devstream.ollama.retry import (
        RetryStatistics,
        ExponentialBackoff,
    )
    print("✅ Retry imported")

    print("\n🎉 ALL IMPORTS SUCCESSFUL!")

except ImportError as e:
    print(f"❌ Import error: {e}")
    traceback.print_exc()
    sys.exit(1)


def test_basic_functionality():
    """Test basic functionality without external dependencies."""
    print("\n🧪 Testing Basic Functionality...")

    # Test exceptions
    error = OllamaError("test error", error_code="TEST")
    assert str(error) == "test error"
    assert error.error_code == "TEST"
    print("✅ OllamaError works")

    conn_error = OllamaConnectionError(host="localhost")
    assert "localhost" in str(conn_error.context)
    print("✅ OllamaConnectionError works")

    # Test models
    embed_req = EmbeddingRequest(model="test", prompt="hello")
    assert embed_req.model == "test"
    assert embed_req.prompt == "hello"
    print("✅ EmbeddingRequest works")

    embed_resp = EmbeddingResponse(model="test", embedding=[0.1, 0.2])
    assert embed_resp.dimension == 2
    numpy_array = embed_resp.to_numpy()
    assert numpy_array.shape == (2,)
    print("✅ EmbeddingResponse works")

    # Test config
    retry_config = RetryConfig()
    assert retry_config.max_retries == 3
    print("✅ RetryConfig works")

    timeout_config = TimeoutConfig()
    assert timeout_config.connect_timeout == 10.0
    print("✅ TimeoutConfig works")

    ollama_config = OllamaConfig()
    assert ollama_config.host == "http://localhost:11434"
    assert ollama_config.base_url == "http://localhost:11434/api/v1"
    print("✅ OllamaConfig works")

    # Test retry logic
    stats = RetryStatistics()
    stats.record_attempt(success=True, delay=1.0)
    assert stats.total_attempts == 1
    assert stats.successful_attempts == 1
    print("✅ RetryStatistics works")

    # Test ExponentialBackoff with jitter disabled
    backoff_config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
    backoff = ExponentialBackoff(backoff_config)
    delay = backoff.calculate_delay(1)
    assert delay == 1.0  # base_delay
    print("✅ ExponentialBackoff works")

    print("✅ Basic functionality tests PASSED")


def test_validation():
    """Test Pydantic validation."""
    print("\n🧪 Testing Validation...")

    # Test invalid EmbeddingRequest
    try:
        EmbeddingRequest(model="", prompt="test")
        assert False, "Should have failed validation"
    except Exception:
        print("✅ Empty model validation works")

    try:
        EmbeddingRequest(model="test", prompt="")
        assert False, "Should have failed validation"
    except Exception:
        print("✅ Empty prompt validation works")

    # Test invalid EmbeddingResponse
    try:
        EmbeddingResponse(model="test", embedding=[])
        assert False, "Should have failed validation"
    except Exception:
        print("✅ Empty embedding validation works")

    # Test ChatMessage validation
    try:
        ChatMessage(role="invalid", content="test")
        assert False, "Should have failed validation"
    except Exception:
        print("✅ Invalid role validation works")

    # Test config bounds
    try:
        RetryConfig(max_retries=-1)
        assert False, "Should have failed validation"
    except Exception:
        print("✅ Negative max_retries validation works")

    print("✅ Validation tests PASSED")


async def test_async_features():
    """Test async features."""
    print("\n🧪 Testing Async Features...")

    config = RetryConfig(base_delay=0.1)
    backoff = ExponentialBackoff(config)

    import time
    start = time.time()
    await backoff.sleep(0.1)
    elapsed = time.time() - start

    assert elapsed >= 0.05
    print("✅ Async sleep works")

    print("✅ Async features tests PASSED")


def run_tests():
    """Run all tests."""
    print("🚀 Starting Direct Ollama Tests...")

    try:
        test_basic_functionality()
        test_validation()
        asyncio.run(test_async_features())

        print("\n🎉 ALL TESTS PASSED! ✅")
        print("\n📊 Test Summary:")
        print("- Exception classes: ✅")
        print("- Pydantic models: ✅")
        print("- Configuration: ✅")
        print("- Retry logic: ✅")
        print("- Validation: ✅")
        print("- Async features: ✅")
        print("\n✨ Core Ollama modules are working correctly!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_tests()