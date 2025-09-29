"""
Unit tests for Ollama configuration.

Tests all configuration classes and validation logic.
"""

import pytest
from pydantic import ValidationError

from devstream.ollama.config import (
    RetryConfig,
    TimeoutConfig,
    BatchConfig,
    FallbackConfig,
    PerformanceConfig,
    OllamaConfig,
)


class TestRetryConfig:
    """Test retry configuration validation and behavior."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert config.retry_on_status_codes == [429, 502, 503, 504]
        assert config.retry_on_timeout is True
        assert config.retry_on_connection_error is True

    def test_valid_custom_values(self):
        """Test valid custom configuration."""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=1.5,
            jitter=False,
            retry_on_status_codes=[503, 504],
        )
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 1.5
        assert config.jitter is False
        assert config.retry_on_status_codes == [503, 504]

    def test_invalid_max_retries(self):
        """Test validation of max_retries bounds."""
        with pytest.raises(ValidationError):
            RetryConfig(max_retries=-1)

        with pytest.raises(ValidationError):
            RetryConfig(max_retries=11)

    def test_invalid_delays(self):
        """Test validation of delay values."""
        with pytest.raises(ValidationError):
            RetryConfig(base_delay=0.05)  # Too small

        with pytest.raises(ValidationError):
            RetryConfig(base_delay=61.0)  # Too large

        with pytest.raises(ValidationError):
            RetryConfig(max_delay=0.5)  # Too small

    def test_max_delay_validation(self):
        """Test that max_delay must be greater than base_delay."""
        # This should work
        config = RetryConfig(base_delay=2.0, max_delay=5.0)
        assert config.max_delay == 5.0

        # This should fail - max_delay must be greater than base_delay
        with pytest.raises(ValidationError):
            RetryConfig(base_delay=2.0, max_delay=1.0)


class TestTimeoutConfig:
    """Test timeout configuration validation."""

    def test_default_values(self):
        """Test default timeout values."""
        config = TimeoutConfig()
        assert config.connect_timeout == 10.0
        assert config.read_timeout == 120.0
        assert config.write_timeout == 60.0
        assert config.pool_timeout == 10.0

    def test_total_timeout_property(self):
        """Test total timeout calculation."""
        config = TimeoutConfig(
            connect_timeout=5.0,
            read_timeout=30.0,
            write_timeout=20.0,
        )
        # Should be connect + max(read, write)
        assert config.total_timeout == 5.0 + 30.0

    def test_timeout_bounds(self):
        """Test timeout value bounds."""
        with pytest.raises(ValidationError):
            TimeoutConfig(connect_timeout=0.5)  # Too small

        with pytest.raises(ValidationError):
            TimeoutConfig(read_timeout=700.0)  # Too large


class TestBatchConfig:
    """Test batch configuration validation."""

    def test_default_values(self):
        """Test default batch values."""
        config = BatchConfig()
        assert config.default_batch_size == 10
        assert config.max_batch_size == 50
        assert config.max_concurrent_batches == 3
        assert config.memory_limit_mb == 512
        assert config.enable_streaming is True

    def test_batch_size_validation(self):
        """Test batch size validation."""
        # Valid configuration
        config = BatchConfig(default_batch_size=5, max_batch_size=20)
        assert config.default_batch_size == 5
        assert config.max_batch_size == 20

        # Invalid: max < default should fail validation
        with pytest.raises(ValidationError):
            BatchConfig(default_batch_size=20, max_batch_size=10)


class TestFallbackConfig:
    """Test fallback configuration."""

    def test_default_values(self):
        """Test default fallback values."""
        config = FallbackConfig()
        assert config.enable_fallback is True
        assert config.fallback_models == ["llama3.2", "gemma2"]
        assert config.fallback_on_model_not_found is True
        assert config.fallback_on_timeout is False
        assert config.auto_pull_missing_models is True
        assert config.max_auto_pull_attempts == 1


class TestPerformanceConfig:
    """Test performance configuration."""

    def test_default_values(self):
        """Test default performance values."""
        config = PerformanceConfig()
        assert config.connection_pool_size == 10
        assert config.connection_pool_max_keepalive == 5
        assert config.enable_http2 is True
        assert config.enable_compression is True
        assert config.trust_env is True
        assert config.verify_ssl is True


class TestOllamaConfig:
    """Test main Ollama configuration."""

    def test_default_values(self):
        """Test default configuration."""
        config = OllamaConfig()
        assert config.host == "http://localhost:11434"
        assert config.api_version == "v1"
        assert config.api_key is None
        assert config.default_embedding_model == "nomic-embed-text"
        assert config.default_chat_model == "llama3.2"

    def test_host_validation(self):
        """Test host URL validation and normalization."""
        # Valid URLs
        config = OllamaConfig(host="http://localhost:11434")
        assert config.host == "http://localhost:11434"

        config = OllamaConfig(host="https://api.example.com")
        assert config.host == "https://api.example.com"

        # URL without scheme (should be normalized)
        config = OllamaConfig(host="localhost:11434")
        assert config.host == "http://localhost:11434"

        # URL with trailing slash (should be removed)
        config = OllamaConfig(host="http://localhost:11434/")
        assert config.host == "http://localhost:11434"

    def test_base_url_property(self):
        """Test base URL property construction."""
        config = OllamaConfig(host="http://localhost:11434", api_version="v2")
        assert config.base_url == "http://localhost:11434/api/v2"

    def test_health_url_property(self):
        """Test health URL property construction."""
        config = OllamaConfig(host="http://localhost:11434")
        assert config.health_url == "http://localhost:11434/api/version"

    def test_component_configs(self):
        """Test that component configurations are properly initialized."""
        config = OllamaConfig()
        assert isinstance(config.timeout, TimeoutConfig)
        assert isinstance(config.retry, RetryConfig)
        assert isinstance(config.batch, BatchConfig)
        assert isinstance(config.fallback, FallbackConfig)
        assert isinstance(config.performance, PerformanceConfig)

    def test_get_model_options(self):
        """Test model options merging."""
        config = OllamaConfig(default_model_options={"temperature": 0.7, "top_p": 0.9})

        # No additional options
        options = config.get_model_options()
        assert options == {"temperature": 0.7, "top_p": 0.9}

        # With additional options
        options = config.get_model_options({"temperature": 0.5, "max_tokens": 100})
        assert options == {"temperature": 0.5, "top_p": 0.9, "max_tokens": 100}

    def test_to_httpx_timeout(self):
        """Test conversion to HTTPX timeout object."""
        config = OllamaConfig()
        timeout = config.to_httpx_timeout()

        # Should return an HTTPX timeout object
        import httpx
        assert isinstance(timeout, httpx.Timeout)

    def test_to_httpx_limits(self):
        """Test conversion to HTTPX limits object."""
        config = OllamaConfig()
        limits = config.to_httpx_limits()

        # Should return an HTTPX limits object
        import httpx
        assert isinstance(limits, httpx.Limits)

    def test_environment_variables(self):
        """Test environment variable loading."""
        import os

        # Set test environment variables
        os.environ["OLLAMA_HOST"] = "http://test-server:8080"
        os.environ["OLLAMA_DEFAULT_CHAT_MODEL"] = "test-model"

        try:
            config = OllamaConfig()
            assert config.host == "http://test-server:8080"
            assert config.default_chat_model == "test-model"
        finally:
            # Clean up
            os.environ.pop("OLLAMA_HOST", None)
            os.environ.pop("OLLAMA_DEFAULT_CHAT_MODEL", None)