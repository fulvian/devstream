#!/usr/bin/env python3
"""
Unit tests for Context7 Configuration.

Tests configuration loading, validation, and feature flag logic.
"""

import pytest
import os
from unittest.mock import patch
from typing import Dict, Any

# Add path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'config'))

from context7_config import Context7Config, get_context7_config, reload_context7_config


class TestContext7Config:
    """Test Context7 configuration functionality."""

    def test_config_initialization(self):
        """Test configuration initialization with defaults."""
        config = Context7Config()

        assert config.direct_enabled is False
        assert config.cache_size == 100
        assert config.timeout == 30
        assert config.circuit_breaker_threshold == 3
        assert config.metrics_enabled is True
        assert config.mcp_fallback is True

    def test_config_initialization_with_values(self):
        """Test configuration initialization with custom values."""
        config = Context7Config(
            direct_enabled=True,
            cache_size=200,
            timeout=60,
            circuit_breaker_threshold=5,
            metrics_enabled=False,
            mcp_fallback=False
        )

        assert config.direct_enabled is True
        assert config.cache_size == 200
        assert config.timeout == 60
        assert config.circuit_breaker_threshold == 5
        assert config.metrics_enabled is False
        assert config.mcp_fallback is False

    @patch.dict(os.environ, {
        "DEVSTREAM_CONTEXT7_DIRECT_ENABLED": "true",
        "DEVSTREAM_CONTEXT7_DIRECT_CACHE_SIZE": "200",
        "DEVSTREAM_CONTEXT7_DIRECT_TIMEOUT": "60",
        "DEVSTREAM_CONTEXT7_DIRECT_CB_THRESHOLD": "5",
        "DEVSTREAM_CONTEXT7_METRICS_ENABLED": "false",
        "DEVSTREAM_CONTEXT7_MCP_FALLBACK": "false"
    })
    def test_from_env(self):
        """Test loading configuration from environment variables."""
        config = Context7Config.from_env()

        assert config.direct_enabled == "true"
        assert config.cache_size == 200
        assert config.timeout == 60
        assert config.circuit_breaker_threshold == 5
        assert config.metrics_enabled is False
        assert config.mcp_fallback is False

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_defaults(self):
        """Test loading configuration with default environment values."""
        config = Context7Config.from_env()

        assert config.direct_enabled == "false"
        assert config.cache_size == 100
        assert config.timeout == 30
        assert config.circuit_breaker_threshold == 3
        assert config.metrics_enabled is True
        assert config.mcp_fallback is True

    def test_should_use_direct_mode_bool_true(self):
        """Test direct mode selection with boolean true."""
        config = Context7Config(direct_enabled=True)
        assert config.should_use_direct_mode() is True

    def test_should_use_direct_mode_bool_false(self):
        """Test direct mode selection with boolean false."""
        config = Context7Config(direct_enabled=False)
        assert config.should_use_direct_mode() is False

    def test_should_use_direct_mode_rollout_with_library(self):
        """Test direct mode selection with rollout and library name."""
        config = Context7Config(direct_enabled="rollout")

        # Test with different library names - should be deterministic
        result1 = config.should_use_direct_mode("test-library")
        result2 = config.should_use_direct_mode("test-library")
        assert result1 == result2  # Should be consistent

        # Test with different libraries
        all_results = [config.should_use_direct_mode(f"lib-{i}") for i in range(100)]
        # Should be approximately 10% true (allowing for hash distribution)
        true_count = sum(all_results)
        assert 5 <= true_count <= 15  # Allow some variance

    def test_should_use_direct_mode_rollout_without_library(self):
        """Test direct mode selection with rollout but no library name."""
        config = Context7Config(direct_enabled="rollout")
        assert config.should_use_direct_mode() is False

    def test_get_mode_description_bool_true(self):
        """Test mode description with boolean true."""
        config = Context7Config(direct_enabled=True)
        assert config.get_mode_description() == "Direct mode"

    def test_get_mode_description_bool_false(self):
        """Test mode description with boolean false."""
        config = Context7Config(direct_enabled=False)
        assert config.get_mode_description() == "MCP mode"

    def test_get_mode_description_rollout(self):
        """Test mode description with rollout."""
        config = Context7Config(direct_enabled="rollout")
        assert "Gradual rollout" in config.get_mode_description()

    def test_validate_valid_config(self):
        """Test validation of valid configuration."""
        config = Context7Config(
            cache_size=100,
            timeout=30,
            circuit_breaker_threshold=3,
            direct_enabled=True
        )

        errors = config.validate()
        assert errors == []

    def test_validate_invalid_cache_size(self):
        """Test validation with invalid cache size."""
        config = Context7Config(cache_size=0)
        errors = config.validate()
        assert len(errors) == 1
        assert "Invalid cache_size" in errors[0]

    def test_validate_invalid_timeout(self):
        """Test validation with invalid timeout."""
        config = Context7Config(timeout=0)
        errors = config.validate()
        assert len(errors) == 1
        assert "Invalid timeout" in errors[0]

    def test_validate_invalid_circuit_breaker_threshold(self):
        """Test validation with invalid circuit breaker threshold."""
        config = Context7Config(circuit_breaker_threshold=0)
        errors = config.validate()
        assert len(errors) == 1
        assert "Invalid circuit_breaker_threshold" in errors[0]

    def test_validate_invalid_direct_enabled(self):
        """Test validation with invalid direct enabled value."""
        config = Context7Config(direct_enabled="invalid")
        errors = config.validate()
        assert len(errors) == 1
        assert "Invalid direct_enabled" in errors[0]

    def test_validate_multiple_errors(self):
        """Test validation with multiple errors."""
        config = Context7Config(
            cache_size=0,
            timeout=0,
            circuit_breaker_threshold=0,
            direct_enabled="invalid"
        )

        errors = config.validate()
        assert len(errors) == 4

    def test_to_dict(self):
        """Test converting configuration to dictionary."""
        config = Context7Config(
            direct_enabled="rollout",
            cache_size=200,
            timeout=60,
            metrics_enabled=False
        )

        result = config.to_dict()

        assert result["direct_enabled"] == "rollout"
        assert result["cache_size"] == 200
        assert result["timeout"] == 60
        assert result["metrics_enabled"] is False
        assert "mode_description" in result
        assert "Gradual rollout" in result["mode_description"]


class TestContext7ConfigSingleton:
    """Test Context7 configuration singleton."""

    def test_get_context7_config(self):
        """Test getting singleton configuration instance."""
        config1 = get_context7_config()
        config2 = get_context7_config()

        assert config1 is config2  # Same instance
        assert isinstance(config1, Context7Config)

    @patch.dict(os.environ, {"DEVSTREAM_CONTEXT7_DIRECT_ENABLED": "true"})
    def test_get_context7_config_with_env(self):
        """Test getting configuration with environment override."""
        # Reload to pick up environment change
        config = reload_context7_config()
        assert config.direct_enabled == "true"

    @patch.dict(os.environ, {"DEVSTREAM_CONTEXT7_DIRECT_CACHE_SIZE": "invalid"})
    def test_get_context7_config_with_invalid_env(self):
        """Test getting configuration with invalid environment value."""
        # Should not raise exception, but will print warning
        config = get_context7_config()
        # Should fall back to default
        assert config.cache_size == 100  # Default value

    def test_reload_context7_config(self):
        """Test reloading configuration."""
        config1 = get_context7_config()
        config2 = reload_context7_config()

        assert config1 is not config2  # Different instances
        assert isinstance(config2, Context7Config)

    @patch.dict(os.environ, {"DEVSTREAM_CONTEXT7_DIRECT_ENABLED": "rollout"})
    def test_reload_context7_config_with_env_change(self):
        """Test reloading configuration after environment change."""
        # Initial config
        config1 = get_context7_config()
        original_enabled = config1.direct_enabled

        # Change environment and reload
        os.environ["DEVSTREAM_CONTEXT7_DIRECT_ENABLED"] = "true"
        config2 = reload_context7_config()

        assert config1 is not config2  # Different instances
        assert config2.direct_enabled == "true"
        assert config2.direct_enabled != original_enabled


class TestContext7ConfigIntegration:
    """Integration tests for Context7 configuration."""

    def test_end_to_end_configuration_flow(self):
        """Test complete configuration flow."""
        # Create configuration
        config = Context7Config(
            direct_enabled="rollout",
            cache_size=150,
            timeout=45,
            circuit_breaker_threshold=4,
            metrics_enabled=True,
            mcp_fallback=True
        )

        # Validate
        errors = config.validate()
        assert errors == []

        # Test mode selection
        test_cases = ["fastapi", "django", "react", "unknown-lib"]
        results = [config.should_use_direct_mode(lib) for lib in test_cases]

        # Should have mixed results for rollout
        assert any(results) and any(not r for r in results)

        # Test mode description
        description = config.get_mode_description()
        assert "Gradual rollout" in description

        # Test dict conversion
        config_dict = config.to_dict()
        assert config_dict["cache_size"] == 150
        assert config_dict["timeout"] == 45
        assert "mode_description" in config_dict

    @patch.dict(os.environ, {
        "DEVSTREAM_CONTEXT7_DIRECT_ENABLED": "rollout",
        "DEVSTREAM_CONTEXT7_DIRECT_CACHE_SIZE": "200",
        "DEVSTREAM_CONTEXT7_METRICS_ENABLED": "false"
    })
    def test_environment_override_integration(self):
        """Test environment variable override integration."""
        config = Context7Config.from_env()

        assert config.direct_enabled == "rollout"
        assert config.cache_size == 200
        assert config.metrics_enabled is False

        # Test that environment values are used consistently
        assert config.should_use_direct_mode("test-lib") in [True, False]  # Should not crash

        description = config.get_mode_description()
        assert "Gradual rollout" in description

        config_dict = config.to_dict()
        assert config_dict["direct_enabled"] == "rollout"
        assert config_dict["cache_size"] == 200
        assert config_dict["metrics_enabled"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])