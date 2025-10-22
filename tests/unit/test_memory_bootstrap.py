"""
Test intelligent bootstrap with environment validation in memory_bootstrap.py.

Tests for _validate_environment_and_choose_strategy() method
"""

import pytest
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the memory bootstrap directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "hooks" / "devstream" / "memory"))

# Mock the imports that might not be available
sys.modules['document_processor'] = MagicMock()
sys.modules['codebase_scanner'] = MagicMock()
sys.modules['incremental_indexer'] = MagicMock()
sys.modules['direct_client'] = MagicMock()

from memory_bootstrap import MemoryBootstrap, BootstrapConfig


class TestEnvironmentValidation:
    """Test environment validation functionality."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create some virtual environment directories
            devstream_env = temp_path / ".devstream"
            devstream_env.mkdir()
            (devstream_env / "bin").mkdir()
            (devstream_env / "bin" / "python").touch()

            venv_env = temp_path / ".venv"
            venv_env.mkdir()
            (venv_env / "bin").mkdir()
            (venv_env / "bin" / "python").touch()

            # Create some source files
            src_dir = temp_path / "src"
            src_dir.mkdir()
            (src_dir / "main.py").write_text("print('hello world')")

            yield temp_path

    @pytest.fixture
    def config(self, temp_project_dir):
        """Create a BootstrapConfig for testing."""
        return BootstrapConfig(
            project_root=temp_project_dir,
            mode="full",
            batch_size=500,
            verbose=True
        )

    @pytest.fixture
    def bootstrap(self, config):
        """Create a MemoryBootstrap instance for testing."""
        # Mock the memory client
        with patch('memory_bootstrap.MEMORY_CLIENT_AVAILABLE', True):
            mock_memory_client = MagicMock()
            mock_memory_client._check_vec_extension_available.return_value = True

            with patch('memory_bootstrap.get_direct_client', return_value=mock_memory_client):
                bootstrap = MemoryBootstrap(config)
                bootstrap.memory_client = mock_memory_client
                yield bootstrap

    def test_method_signature_and_return_type(self, bootstrap):
        """Test that method signature matches specification."""
        # Check method exists
        assert hasattr(bootstrap, '_validate_environment_and_choose_strategy')

        # Check method is callable
        assert callable(getattr(bootstrap, '_validate_environment_and_choose_strategy'))

        # Check return type annotation (should be Dict[str, Any])
        import inspect
        from typing import Dict, Any
        sig = inspect.signature(bootstrap._validate_environment_and_choose_strategy)
        assert sig.return_annotation == Dict[str, Any]

    def test_method_docstring_complete(self, bootstrap):
        """Test that method has complete docstring with example."""
        docstring = bootstrap._validate_environment_and_choose_strategy.__doc__

        # Check docstring exists and has required sections
        assert docstring is not None
        assert "Validate environment and choose optimal population strategy" in docstring
        assert "Context7-compliant environment validation" in docstring
        assert "Args:" in docstring
        assert "Returns:" in docstring
        assert "Raises:" in docstring
        assert "Example:" in docstring

    def test_vector_strategy_selection(self, bootstrap):
        """Test vector strategy selection when vector search is available."""
        # Mock vector extension available
        bootstrap.memory_client._check_vec_extension_available.return_value = True

        with patch('memory_bootstrap.YAML_AVAILABLE', True):
            strategy = bootstrap._validate_environment_and_choose_strategy()

        # Should select vector+fts hybrid strategy
        assert strategy["mode"] == "vector_fts"
        assert strategy["vector_available"] is True
        assert strategy["sqlite_optimization"] is True
        assert strategy["recommended_chunk_size"] == 1000
        assert strategy["performance_profile"] == "optimized"

    def test_fts_only_fallback_strategy(self, bootstrap):
        """Test FTS-only fallback when vector search not available."""
        # Mock vector extension not available
        bootstrap.memory_client._check_vec_extension_available.return_value = False

        strategy = bootstrap._validate_environment_and_choose_strategy()

        # Should select FTS-only strategy
        assert strategy["mode"] == "fts_only"
        assert strategy["vector_available"] is False
        assert strategy["sqlite_optimization"] is True
        assert strategy["recommended_chunk_size"] == 500
        assert strategy["performance_profile"] == "conservative"

    def test_multi_environment_detection(self, bootstrap):
        """Test detection of multiple virtual environments."""
        strategy = bootstrap._validate_environment_and_choose_strategy()

        # Should detect multiple environments
        assert strategy["multi_env_detected"] is True
        assert strategy["environment_summary"]["env_count"] == 2
        assert ".devstream" in strategy["environment_summary"]["detected_envs"]
        assert ".venv" in strategy["environment_summary"]["detected_envs"]

    def test_single_environment_detection(self, temp_project_dir):
        """Test detection of single virtual environment."""
        # Create config with only one environment
        config = BootstrapConfig(project_root=temp_project_dir, mode="full")

        # Remove one environment
        import shutil
        shutil.rmtree(temp_project_dir / ".venv")

        with patch('memory_bootstrap.MEMORY_CLIENT_AVAILABLE', True):
            mock_memory_client = MagicMock()
            mock_memory_client._check_vec_extension_available.return_value = False

            with patch('memory_bootstrap.get_direct_client', return_value=mock_memory_client):
                bootstrap = MemoryBootstrap(config)
                bootstrap.memory_client = mock_memory_client

                strategy = bootstrap._validate_environment_and_choose_strategy()

        # Should detect single environment
        assert strategy["multi_env_detected"] is False
        assert strategy["environment_summary"]["env_count"] == 1
        assert ".devstream" in strategy["environment_summary"]["detected_envs"]

    def test_environment_summary_completeness(self, bootstrap):
        """Test that environment summary contains all required fields."""
        strategy = bootstrap._validate_environment_and_choose_strategy()

        summary = strategy["environment_summary"]

        # Check required fields
        assert "project_root" in summary
        assert "detected_envs" in summary
        assert "env_count" in summary
        assert "memory_client_available" in summary
        assert "components_available" in summary
        assert "yaml_available" in summary

        # Check values are reasonable
        assert summary["env_count"] == len(summary["detected_envs"])
        assert summary["project_root"] == str(bootstrap.config.project_root)

    def test_vector_extension_check_error_handling(self, bootstrap):
        """Test graceful handling when vector extension check fails."""
        # Mock vector extension check to raise exception
        bootstrap.memory_client._check_vec_extension_available.side_effect = Exception("Extension check failed")

        strategy = bootstrap._validate_environment_and_choose_strategy()

        # Should fallback to FTS-only mode
        assert strategy["mode"] == "fts_only"
        assert strategy["vector_available"] is False

    def test_memory_client_unavailable_handling(self, config):
        """Test handling when memory client is not available."""
        with patch('memory_bootstrap.MEMORY_CLIENT_AVAILABLE', False):
            bootstrap = MemoryBootstrap(config)

            strategy = bootstrap._validate_environment_and_choose_strategy()

        # Should fallback to FTS-only mode
        assert strategy["mode"] == "fts_only"
        assert strategy["vector_available"] is False

    def test_embedding_service_check(self, bootstrap):
        """Test embedding service availability check."""
        strategy = bootstrap._validate_environment_and_choose_strategy()

        # Should check embedding availability
        assert "embedding_available" in strategy

    def test_strategy_configuration_completeness(self, bootstrap):
        """Test that strategy configuration contains all required fields."""
        strategy = bootstrap._validate_environment_and_choose_strategy()

        # Check required strategy fields
        required_fields = [
            "mode", "vector_available", "embedding_available",
            "sqlite_optimization", "multi_env_detected",
            "recommended_chunk_size", "performance_profile",
            "environment_summary"
        ]

        for field in required_fields:
            assert field in strategy, f"Missing required field: {field}"

    def test_performance_profiles(self, bootstrap):
        """Test different performance profiles based on capabilities."""
        # Test optimized profile (vector + embedding)
        bootstrap.memory_client._check_vec_extension_available.return_value = True
        strategy = bootstrap._validate_environment_and_choose_strategy()

        assert strategy["performance_profile"] in ["optimized", "vector_focused", "conservative", "fallback"]

        # Test conservative profile (FTS-only)
        bootstrap.memory_client._check_vec_extension_available.return_value = False
        strategy = bootstrap._validate_environment_and_choose_strategy()

        assert strategy["performance_profile"] == "conservative"

    def test_chunk_size_recommendations(self, bootstrap):
        """Test chunk size recommendations based on strategy."""
        # Vector strategy should recommend larger chunks
        bootstrap.memory_client._check_vec_extension_available.return_value = True
        strategy = bootstrap._validate_environment_and_choose_strategy()

        assert strategy["recommended_chunk_size"] >= 750

        # FTS-only strategy should recommend smaller chunks
        bootstrap.memory_client._check_vec_extension_available.return_value = False
        strategy = bootstrap._validate_environment_and_choose_strategy()

        assert strategy["recommended_chunk_size"] == 500

    def test_validation_error_fallback(self, bootstrap):
        """Test fallback strategy when validation fails."""
        # Mock the memory client to raise an exception during vector check
        bootstrap.memory_client._check_vec_extension_available.side_effect = Exception("Validation failed")

        # Call the actual method - it should handle the error gracefully
        strategy = bootstrap._validate_environment_and_choose_strategy()

        # Should return fallback strategy even on error
        assert strategy["mode"] == "fts_only"
        assert strategy["vector_available"] is False

    def test_logging_on_strategy_selection(self, bootstrap):
        """Test proper logging when strategy is selected."""
        # Mock logger
        mock_logger = MagicMock()
        bootstrap.logger = mock_logger

        strategy = bootstrap._validate_environment_and_choose_strategy()

        # Verify strategy selection was logged
        assert mock_logger.info.called
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]

        # Should log environment validation completion
        validation_logs = [call for call in log_calls if "Environment validation complete" in call]
        assert len(validation_logs) > 0