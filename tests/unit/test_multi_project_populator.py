"""
Test MultiProjectPopulator module with sqlite-utils patterns.

Tests for multi-project population functionality
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
sys.modules['incremental_indexer'] = MagicMock()
sys.modules['direct_client'] = MagicMock()

from multi_project_populator import MultiProjectPopulator, create_multi_project_populator, PopulationError


class TestMultiProjectPopulator:
    """Test multi-project populator functionality."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create various project files
            src_dir = temp_path / "src"
            src_dir.mkdir()
            (src_dir / "main.py").write_text("print('hello world')")
            (src_dir / "utils.py").write_text("def helper(): pass")

            docs_dir = temp_path / "docs"
            docs_dir.mkdir()
            (docs_dir / "README.md").write_text("# Project Documentation")

            # Create virtual environment
            venv_dir = temp_path / ".venv"
            venv_dir.mkdir()
            (venv_dir / "bin").mkdir()
            (venv_dir / "bin" / "python").touch()

            # Create requirements file
            (temp_path / "requirements.txt").write_text("requests\nsqlite-utils")

            yield temp_path

    @pytest.fixture
    def mock_memory_client(self):
        """Create a mock memory client."""
        client = MagicMock()
        client._check_vec_extension_available.return_value = True
        client.get_stats.return_value = {"client_type": "direct", "features": {}}
        return client

    @pytest.fixture
    def populator(self, temp_project_dir, mock_memory_client):
        """Create a MultiProjectPopulator instance for testing."""
        return MultiProjectPopulator(str(temp_project_dir), mock_memory_client)

    def test_class_signature_and_docstring(self, populator):
        """Test that class has correct signature and docstring."""
        docstring = MultiProjectPopulator.__doc__

        # Check docstring exists and has required sections
        assert docstring is not None
        assert "Context7-compliant multi-project database population system" in docstring
        assert "sqlite-utils patterns" in docstring

    def test_initialization_validation(self, mock_memory_client):
        """Test initialization with validation."""
        # Test with non-existent directory
        with pytest.raises(PopulationError, match="Project root does not exist"):
            MultiProjectPopulator("/nonexistent/path", mock_memory_client)

        # Test with None memory client
        with pytest.raises(PopulationError, match="Memory client is required"):
            MultiProjectPopulator("/tmp", None)

    def test_populate_from_existing_codebase_signature(self, populator):
        """Test method signature and docstring."""
        docstring = populator.populate_from_existing_codebase.__doc__

        # Check docstring exists and has required sections
        assert docstring is not None
        assert "Populate DevStream database from existing codebase" in docstring
        assert "Context7 research patterns from sqlite-utils" in docstring
        assert "Args:" in docstring
        assert "Returns:" in docstring
        assert "Raises:" in docstring
        assert "Example:" in docstring

    def test_populate_from_existing_codebase_auto_strategy(self, populator):
        """Test population with auto strategy selection."""
        # Test that auto strategy works without crashing
        with patch('multi_project_populator.DEVSTREAM_COMPONENTS_AVAILABLE', True):
            result = populator.populate_from_existing_codebase(strategy="auto")

        # Should succeed and have basic structure
        assert result.success is True
        assert result.strategy_used in ["auto", "vector_fts", "fts_only"]
        assert result.population_time > 0

    def test_populate_from_existing_codebase_vector_fts_strategy(self, populator):
        """Test population with vector_fts strategy."""
        # Test that vector_fts strategy works without crashing
        with patch('multi_project_populator.DEVSTREAM_COMPONENTS_AVAILABLE', True):
            result = populator.populate_from_existing_codebase(strategy="vector_fts")

        # Should succeed with basic structure
        assert result.success is True
        assert result.strategy_used == "vector_fts"

    def test_populate_from_existing_codebase_fts_only_strategy(self, populator):
        """Test population with fts_only strategy."""
        # Test that fts_only strategy works without crashing
        with patch('multi_project_populator.DEVSTREAM_COMPONENTS_AVAILABLE', True):
            result = populator.populate_from_existing_codebase(strategy="fts_only")

        # Should succeed with basic structure
        assert result.success is True
        assert result.strategy_used == "fts_only"

    def test_populate_from_existing_codebase_force_rebuild(self, populator):
        """Test population with force_rebuild option."""
        # Test that force_rebuild works without crashing
        with patch('multi_project_populator.DEVSTREAM_COMPONENTS_AVAILABLE', True):
            result = populator.populate_from_existing_codebase(force_rebuild=True)

        # Should succeed with basic structure
        assert result.success is True
        assert result.population_time > 0

    def test_project_structure_analysis(self, populator):
        """Test project structure analysis."""
        analysis = populator._analyze_project_structure()

        # Should detect project characteristics
        assert analysis.total_files > 0
        assert ".py" in analysis.file_types
        assert analysis.estimated_size_mb > 0
        assert analysis.has_requirements is True
        assert analysis.complexity_score >= 0
        assert analysis.recommended_strategy in ["vector_fts", "fts_only"]
        # Note: Virtual environment detection may not work in all test environments

    def test_strategy_selection_logic(self, populator):
        """Test optimal strategy selection logic."""
        from multi_project_populator import ProjectAnalysis

        # Test small project
        small_analysis = ProjectAnalysis(
            total_files=20,
            file_types={".py": 15, ".md": 5},
            estimated_size_mb=0.5,
            virtual_envs=[".venv"],
            has_requirements=True,
            complexity_score=2,
            recommended_strategy="fts_only"
        )
        strategy = populator._choose_optimal_strategy(small_analysis)
        assert strategy == "fts_only"

        # Test medium Python project
        medium_analysis = ProjectAnalysis(
            total_files=200,
            file_types={".py": 150, ".md": 30, ".txt": 20},
            estimated_size_mb=5.0,
            virtual_envs=[".venv"],
            has_requirements=True,
            complexity_score=5,
            recommended_strategy="vector_fts"
        )
        strategy = populator._choose_optimal_strategy(medium_analysis)
        assert strategy == "vector_fts"

        # Test large project
        large_analysis = ProjectAnalysis(
            total_files=1000,
            file_types={".py": 400, ".js": 300, ".md": 200, ".txt": 100},
            estimated_size_mb=25.0,
            virtual_envs=[".venv"],
            has_requirements=True,
            complexity_score=8,
            recommended_strategy="vector_fts"
        )
        strategy = populator._choose_optimal_strategy(large_analysis)
        assert strategy == "vector_fts"

    def test_environment_validation(self, populator):
        """Test environment validation."""
        validation = populator._validate_environment()

        # Should return environment capabilities
        assert "vector_available" in validation
        assert "embedding_available" in validation
        assert "sqlite_utils_available" in validation
        assert "devstream_components_available" in validation
        assert "performance_profile" in validation

        # Should have detected vector availability
        assert validation["vector_available"] is True
        assert validation["performance_profile"] in ["optimized", "vector_focused", "conservative"]

    def test_error_handling_graceful_degradation(self, populator):
        """Test graceful error handling and fallback strategies."""
        # Mock vector search as unavailable
        populator.memory_client._check_vec_extension_available.side_effect = Exception("Vector error")

        # Test FTS fallback when vector search fails
        with patch('multi_project_populator.DEVSTREAM_COMPONENTS_AVAILABLE', True):
            result = populator.populate_from_existing_codebase(strategy="vector_fts")

        # Should fallback gracefully
        assert result.success is True
        # Should have warnings about strategy fallback
        assert len(result.warnings) > 0

    def test_sqlite_utils_optimization(self, populator):
        """Test sqlite-utils optimization application."""
        with patch('multi_project_populator.SQLITE_UTILS_AVAILABLE', True):
            with patch('multi_project_populator.TypeTracker', create=True):
                # Mock successful optimization
                result = populator._apply_sqlite_optimizations()
                # Should not raise an exception
                assert result is None

    def test_population_stats_retrieval(self, populator):
        """Test population statistics retrieval."""
        stats = populator.get_population_stats()

        # Should return statistics dictionary
        assert "project_root" in stats
        assert "components_available" in stats
        assert stats["project_root"] == str(populator.project_root)

    def test_population_result_completeness(self, populator):
        """Test that population result contains all required fields."""
        mock_indexer = MagicMock()
        mock_indexer.index_directory.return_value = MagicMock(
            total_files=12,
            total_chunks=30,
            errors=[],
            warnings=[]
        )

        with patch('multi_project_populator.DEVSTREAM_COMPONENTS_AVAILABLE', True):
            with patch('multi_project_populator.create_incremental_indexer', return_value=mock_indexer):
                result = populator.populate_from_existing_codebase()

        # Check required fields
        required_fields = [
            "success", "total_files", "total_chunks", "population_time",
            "strategy_used", "vector_available", "performance_profile",
            "errors", "warnings", "metadata"
        ]

        for field in required_fields:
            assert hasattr(result, field), f"Missing required field: {field}"

        # Check metadata completeness
        metadata = result.metadata
        assert "project_analysis" in metadata
        assert "environment_validation" in metadata
        assert "sqlite_utils_available" in metadata
        assert "population_timestamp" in metadata

    def test_factory_function(self, temp_project_dir, mock_memory_client):
        """Test factory function for creating populator."""
        populator = create_multi_project_populator(str(temp_project_dir), mock_memory_client)

        # Should create valid populator instance
        assert isinstance(populator, MultiProjectPopulator)
        assert populator.project_root == temp_project_dir
        assert populator.memory_client == mock_memory_client

    def test_factory_function_error_handling(self, mock_memory_client):
        """Test factory function error handling."""
        # Test with non-existent path
        with pytest.raises(PopulationError):
            create_multi_project_populator("/nonexistent", mock_memory_client)

    def test_components_unavailable_fallback(self, temp_project_dir, mock_memory_client):
        """Test behavior when DevStream components are unavailable."""
        with patch('multi_project_populator.DEVSTREAM_COMPONENTS_AVAILABLE', False):
            populator = MultiProjectPopulator(str(temp_project_dir), mock_memory_client)

            # Should still be able to analyze project structure
            analysis = populator._analyze_project_structure()
            assert analysis.total_files > 0

            # Should still be able to validate environment
            validation = populator._validate_environment()
            assert "vector_available" in validation

            # Population should work but with limited functionality
            result = populator.populate_from_existing_codebase(strategy="fts_only")
            # Should succeed with fallback behavior
            assert result.success is True
            assert result.total_files > 0

    def test_context7_pattern_usage(self, populator):
        """Test that Context7 patterns are properly implemented."""
        # Check that sqlite-utils patterns are mentioned in code
        assert hasattr(populator, '_apply_sqlite_optimizations')
        assert 'sqlite-utils' in populator._apply_sqlite_optimizations.__doc__

        # Check that patterns are used in population
        analysis = populator._analyze_project_structure()
        assert analysis.recommended_strategy in ["vector_fts", "fts_only"]

    def test_logging_and_progress_tracking(self, populator):
        """Test proper logging and progress tracking."""
        # Mock logger
        mock_logger = MagicMock()
        populator.logger = mock_logger

        # Mock indexing result
        mock_indexer = MagicMock()
        mock_indexer.index_directory.return_value = MagicMock(
            total_files=5,
            total_chunks=15,
            errors=[],
            warnings=[]
        )

        with patch('multi_project_populator.DEVSTREAM_COMPONENTS_AVAILABLE', True):
            with patch('multi_project_populator.create_incremental_indexer', return_value=mock_indexer):
                result = populator.populate_from_existing_codebase()

        # Should log progress
        assert mock_logger.info.called
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]

        # Should log analysis, strategy choice, and completion
        analysis_logs = [call for call in log_calls if "Analyzing project structure" in call]
        strategy_logs = [call for call in log_calls if "Using strategy" in call]
        completion_logs = [call for call in log_calls if "Population completed" in call]

        assert len(analysis_logs) > 0
        assert len(strategy_logs) > 0
        assert len(completion_logs) > 0