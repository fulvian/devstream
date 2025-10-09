"""
Unit tests for Project Detection Framework

Tests comprehensive project type detection logic, confidence scoring,
and multi-factor analysis for various programming languages and frameworks.
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from devstream.installation.project_detector import (
    ProjectDetector,
    ProjectType,
    ProjectAnalysis,
    ProjectIndicator,
    detect_project_type,
    calculate_project_score,
)


class TestProjectType:
    """Test ProjectType enum functionality."""

    def test_project_type_values(self) -> None:
        """Test that all project types have valid string values."""
        for project_type in ProjectType:
            assert isinstance(project_type.value, str)
            assert len(project_type.value) > 0

    def test_project_type_comparison(self) -> None:
        """Test project type comparison operations."""
        assert ProjectType.PYTHON == ProjectType.PYTHON
        assert ProjectType.PYTHON != ProjectType.JAVASCRIPT
        assert ProjectType.UNKNOWN.value == "unknown"


class TestProjectIndicator:
    """Test ProjectIndicator dataclass."""

    def test_valid_indicator_creation(self) -> None:
        """Test creating valid project indicators."""
        indicator = ProjectIndicator(
            name="test_indicator",
            value="test_value",
            weight=0.8,
            confidence=0.9
        )
        assert indicator.name == "test_indicator"
        assert indicator.value == "test_value"
        assert indicator.weight == 0.8
        assert indicator.confidence == 0.9

    def test_invalid_weight_validation(self) -> None:
        """Test validation of invalid weight values."""
        with pytest.raises(ValueError, match="Weight must be between 0 and 1.0"):
            ProjectIndicator("test", "value", -0.1)

        with pytest.raises(ValueError, match="Weight must be between 0 and 1.0"):
            ProjectIndicator("test", "value", 1.1)

    def test_invalid_confidence_validation(self) -> None:
        """Test validation of invalid confidence values."""
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1.0"):
            ProjectIndicator("test", "value", 0.5, -0.1)

        with pytest.raises(ValueError, match="Confidence must be between 0 and 1.0"):
            ProjectIndicator("test", "value", 0.5, 1.1)


class TestProjectAnalysis:
    """Test ProjectAnalysis dataclass."""

    def test_project_analysis_creation(self) -> None:
        """Test creating project analysis."""
        analysis = ProjectAnalysis(
            project_path="/test/path",
            project_type=ProjectType.PYTHON
        )
        assert analysis.project_path == "/test/path"
        assert analysis.project_type == ProjectType.PYTHON
        assert analysis.confidence_score == 0.0
        assert len(analysis.indicators) == 0
        assert len(analysis.detected_languages) == 0

    def test_to_dict_conversion(self) -> None:
        """Test conversion to dictionary."""
        analysis = ProjectAnalysis(
            project_path="/test/path",
            project_type=ProjectType.PYTHON,
            confidence_score=0.85,
            detected_languages={"python", "javascript"}
        )
        analysis.indicators.append(
            ProjectIndicator("test", "value", 0.8)
        )

        result = analysis.to_dict()
        assert result["project_path"] == "/test/path"
        assert result["project_type"] == "python"
        assert result["confidence_score"] == 0.85
        assert "python" in result["detected_languages"]
        assert "javascript" in result["detected_languages"]
        assert len(result["indicators"]) == 1


class TestProjectDetector:
    """Test ProjectDetector class functionality."""

    def test_detector_initialization(self) -> None:
        """Test ProjectDetector initialization."""
        detector = ProjectDetector()
        assert detector.min_confidence == 0.3

        detector_custom = ProjectDetector(min_confidence=0.5)
        assert detector_custom.min_confidence == 0.5

    def test_invalid_project_path(self) -> None:
        """Test handling of invalid project paths."""
        detector = ProjectDetector()

        with pytest.raises(ValueError, match="Project path does not exist"):
            detector.detect_project_type("/nonexistent/path")

        # Create a temporary file and try to treat it as a directory
        with tempfile.NamedTemporaryFile() as tmp_file:
            with pytest.raises(ValueError, match="Project path is not a directory"):
                detector.detect_project_type(tmp_file.name)

    def test_empty_directory_detection(self) -> None:
        """Test detection of empty directories."""
        detector = ProjectDetector()

        with tempfile.TemporaryDirectory() as tmp_dir:
            analysis = detector.detect_project_type(tmp_dir)

            assert analysis.project_type == ProjectType.EMPTY
            assert analysis.confidence_score == 1.0
            assert analysis.is_empty is True
            assert analysis.file_count == 0
            assert analysis.directory_count == 0

    def test_python_project_detection(self) -> None:
        """Test detection of Python projects."""
        detector = ProjectDetector()

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create Python project files
            Path(tmp_dir).joinpath("main.py").write_text("print('Hello')")
            Path(tmp_dir).joinpath("requirements.txt").write_text("requests==2.28.0")
            Path(tmp_dir).joinpath("README.md").write_text("# Test Project")

            analysis = detector.detect_project_type(tmp_dir)

            assert ProjectType.PYTHON in analysis.detected_languages
            assert "pip" in analysis.package_managers
            assert analysis.has_documentation is True
            assert analysis.project_type != ProjectType.UNKNOWN
            assert analysis.confidence_score > 0.5

    def test_poetry_project_detection(self) -> None:
        """Test detection of Poetry-based Python projects."""
        detector = ProjectDetector()

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create pyproject.toml for Poetry
            pyproject_content = """
[tool.poetry]
name = "test-project"
version = "0.1.0"
description = "Test project"

[tool.poetry.dependencies]
python = "^3.11"
requests = "^2.28.0"
"""
            Path(tmp_dir).joinpath("pyproject.toml").write_text(pyproject_content)
            Path(tmp_dir).joinpath("main.py").write_text("def main(): pass")

            analysis = detector.detect_project_type(tmp_dir)

            assert ProjectType.PYTHON in analysis.detected_languages
            assert "poetry" in analysis.package_managers
            assert analysis.confidence_score > 0.7

    def test_javascript_project_detection(self) -> None:
        """Test detection of JavaScript projects."""
        detector = ProjectDetector()

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create JavaScript project files
            package_json = {
                "name": "test-project",
                "version": "1.0.0",
                "scripts": {
                    "start": "node index.js"
                },
                "dependencies": {
                    "express": "^4.18.0"
                }
            }

            Path(tmp_dir).joinpath("package.json").write_text(
                json.dumps(package_json, indent=2)
            )
            Path(tmp_dir).joinpath("index.js").write_text("console.log('Hello')")

            analysis = detector.detect_project_type(tmp_dir)

            assert ProjectType.NODE_JS in analysis.detected_languages
            assert "npm" in analysis.package_managers
            assert analysis.confidence_score > 0.5

    def test_typescript_project_detection(self) -> None:
        """Test detection of TypeScript projects."""
        detector = ProjectDetector()

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create TypeScript project files
            package_json = {
                "name": "test-ts-project",
                "version": "1.0.0",
                "devDependencies": {
                    "typescript": "^4.9.0"
                }
            }

            Path(tmp_dir).joinpath("package.json").write_text(
                json.dumps(package_json, indent=2)
            )
            Path(tmp_dir).joinpath("tsconfig.json").write_text(
                json.dumps({"compilerOptions": {"target": "ES2020"}})
            )
            Path(tmp_dir).joinpath("index.ts").write_text("console.log('Hello TS')")

            analysis = detector.detect_project_type(tmp_dir)

            assert ProjectType.TYPESCRIPT in analysis.detected_languages
            assert "npm" in analysis.package_managers
            assert analysis.confidence_score > 0.6

    def test_go_project_detection(self) -> None:
        """Test detection of Go projects."""
        detector = ProjectDetector()

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create Go project files
            go_mod_content = """
module github.com/example/test-project

go 1.19

require github.com/gin-gonic/gin v1.9.0
"""
            Path(tmp_dir).joinpath("go.mod").write_text(go_mod_content)
            Path(tmp_dir).joinpath("main.go").write_text("package main\n\nfunc main() {}")

            analysis = detector.detect_project_type(tmp_dir)

            assert ProjectType.GO in analysis.detected_languages
            assert "go" in analysis.package_managers
            assert analysis.confidence_score > 0.7

    def test_rust_project_detection(self) -> None:
        """Test detection of Rust projects."""
        detector = ProjectDetector()

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create Rust project files
            cargo_toml_content = """
[package]
name = "test-project"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = "1.0"
"""
            Path(tmp_dir).joinpath("Cargo.toml").write_text(cargo_toml_content)
            Path(tmp_dir).joinpath("src/main.rs").write_text("fn main() { println!(\"Hello\"); }")

            analysis = detector.detect_project_type(tmp_dir)

            assert ProjectType.RUST in analysis.detected_languages
            assert "cargo" in analysis.package_managers
            assert analysis.confidence_score > 0.7

    def test_docker_project_detection(self) -> None:
        """Test detection of Docker projects."""
        detector = ProjectDetector()

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create Docker files
            dockerfile_content = """
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "main.py"]
"""
            Path(tmp_dir).joinpath("Dockerfile").write_text(dockerfile_content)

            docker_compose_content = """
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
"""
            Path(tmp_dir).joinpath("docker-compose.yml").write_text(docker_compose_content)

            analysis = detector.detect_project_type(tmp_dir)

            assert ProjectType.DOCKER in analysis.detected_languages
            assert "docker" in analysis.package_managers
            assert analysis.confidence_score > 0.5

    def test_git_repository_detection(self) -> None:
        """Test Git repository detection."""
        detector = ProjectDetector()

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a git repository
            git_dir = Path(tmp_dir) / ".git"
            git_dir.mkdir()

            # Create some git structure
            (git_dir / "HEAD").write_text("ref: refs/heads/main")
            (git_dir / "refs").mkdir()
            (git_dir / "refs" / "heads").mkdir()
            (git_dir / "refs" / "heads" / "main").write_text("commit hash")

            Path(tmp_dir).joinpath("main.py").write_text("print('Hello')")

            analysis = detector.detect_project_type(tmp_dir)

            assert analysis.has_git_repo is True
            assert any(ind.name == "git_repository" for ind in analysis.indicators)

    def test_framework_detection(self) -> None:
        """Test framework-specific detection."""
        detector = ProjectDetector()

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create Django project structure
            Path(tmp_dir).joinpath("manage.py").write_text("#!/usr/bin/env python")
            Path(tmp_dir).joinpath("wsgi.py").write_text("WSGI config")
            Path(tmp_dir).joinpath("requirements.txt").write_text("Django==4.2")

            analysis = detector.detect_project_type(tmp_dir)

            assert "django" in analysis.detected_frameworks
            assert analysis.confidence_score > 0.7

    def test_mixed_project_detection(self) -> None:
        """Test detection of mixed-language projects."""
        detector = ProjectDetector()

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create mixed project files
            Path(tmp_dir).joinpath("package.json").write_text('{"name": "test"}')
            Path(tmp_dir).joinpath("requirements.txt").write_text("requests==2.28.0")
            Path(tmp_dir).joinpath("main.py").write_text("print('Python')")
            Path(tmp_dir).joinpath("app.js").write_text("console.log('JavaScript')")
            Path(tmp_dir).joinpath("script.go").write_text("package main")

            analysis = detector.detect_project_type(tmp_dir)

            # Should detect multiple languages
            assert len(analysis.detected_languages) > 2
            assert analysis.project_type == ProjectType.MIXED or analysis.confidence_score > 0.3

    def test_permission_denied_handling(self) -> None:
        """Test handling of permission denied errors."""
        detector = ProjectDetector()

        with patch('pathlib.Path.iterdir') as mock_iterdir:
            mock_iterdir.side_effect = PermissionError("Access denied")

            with tempfile.TemporaryDirectory() as tmp_dir:
                analysis = detector.detect_project_type(tmp_dir)

                # Should handle gracefully
                assert analysis.is_empty is True  # Will default to empty due to permission error

    def test_confidence_score_calculation(self) -> None:
        """Test confidence score calculation edge cases."""
        # Test empty project
        empty_analysis = ProjectAnalysis(
            project_path="/test",
            project_type=ProjectType.EMPTY,
            is_empty=True
        )
        score = calculate_project_score(empty_analysis)
        assert score == 1.0

        # Test project with no indicators
        no_indicators_analysis = ProjectAnalysis(
            project_path="/test",
            project_type=ProjectType.UNKNOWN,
            indicators=[]
        )
        score = calculate_project_score(no_indicators_analysis)
        assert score >= 0.0

    def test_primary_type_determination(self) -> None:
        """Test primary project type determination logic."""
        detector = ProjectDetector()

        # Create analysis with Python indicators
        analysis = ProjectAnalysis(
            project_path="/test",
            project_type=ProjectType.UNKNOWN
        )
        analysis.indicators.append(ProjectIndicator(
            name="config_file",
            value="requirements.txt",
            weight=0.8
        ))

        primary_type = detector._determine_primary_type(analysis)
        assert primary_type == ProjectType.PYTHON


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_detect_project_type_function(self) -> None:
        """Test the detect_project_type convenience function."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            Path(tmp_dir).joinpath("main.py").write_text("print('Hello')")

            analysis = detect_project_type(tmp_dir)

            assert isinstance(analysis, ProjectAnalysis)
            assert analysis.project_path == str(Path(tmp_dir).resolve())

    def test_calculate_project_score_function(self) -> None:
        """Test the calculate_project_score convenience function."""
        indicators = {
            "project_path": "/test",
            "has_git_repo": True,
            "has_documentation": False,
            "config_files": ["requirements.txt"]
        }

        score = calculate_project_score(indicators)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])