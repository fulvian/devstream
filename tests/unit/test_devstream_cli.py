"""
Unit tests for DevStream CLI tool.
Tests project detection, registration, and management functionality.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open

# Add the scripts directory to the path for testing
import sys
scripts_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts')
sys.path.insert(0, scripts_dir)

# Import the CLI module directly
import importlib.util
spec = importlib.util.spec_from_file_location("devstream_cli", os.path.join(scripts_dir, "devstream"))
devstream_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(devstream_module)

# Extract functions from the module
detect_devstream_project = devstream_module.detect_devstream_project
find_nearest_devstream_project = devstream_module.find_nearest_devstream_project
list_projects = devstream_module.list_projects
register_project = devstream_module.register_project


class TestDevstreamCLI(unittest.TestCase):
    """Test cases for DevStream CLI functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "test_project"
        self.project_dir.mkdir()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_devstream_project(self, project_dir: Path, **overrides):
        """Create a mock DevStream project structure."""
        devstream_dir = project_dir / ".devstream"
        devstream_dir.mkdir()

        workspace_data = {
            "name": "test-project",
            "created": "2025-10-14T23:00:00Z",
            "last_updated": "2025-10-14T23:00:00Z",
            "project_type": "python",
            "scan_completed": True,
            "files_count": 150
        }
        workspace_data.update(overrides)

        workspace_file = devstream_dir / "workspace.json"
        with open(workspace_file, 'w') as f:
            json.dump(workspace_data, f)

        return workspace_data

    def test_detect_devstream_project_found(self):
        """Test detecting a valid DevStream project."""
        # Create project structure
        self.create_devstream_project(self.project_dir)

        # Test detection
        result = detect_devstream_project(str(self.project_dir))

        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "test-project")
        self.assertEqual(result["path"], str(self.project_dir.absolute()))
        self.assertEqual(result["project_type"], "python")
        self.assertTrue(result["scan_completed"])
        self.assertEqual(result["files_count"], 150)

    def test_detect_devstream_project_no_devstream_dir(self):
        """Test detection when .devstream directory doesn't exist."""
        result = detect_devstream_project(str(self.project_dir))
        self.assertIsNone(result)

    def test_detect_devstream_project_no_workspace_file(self):
        """Test detection when workspace.json doesn't exist."""
        devstream_dir = self.project_dir / ".devstream"
        devstream_dir.mkdir()
        # Don't create workspace.json

        result = detect_devstream_project(str(self.project_dir))
        self.assertIsNone(result)

    def test_detect_devstream_project_invalid_json(self):
        """Test detection with invalid JSON in workspace.json."""
        devstream_dir = self.project_dir / ".devstream"
        devstream_dir.mkdir()

        workspace_file = devstream_dir / "workspace.json"
        with open(workspace_file, 'w') as f:
            f.write("invalid json content")

        result = detect_devstream_project(str(self.project_dir))
        self.assertIsNone(result)

    def test_detect_devstream_project_permission_error(self):
        """Test detection with permission error."""
        # This test would require more complex setup to simulate permission errors
        # For now, we'll test the error handling path
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            result = detect_devstream_project(str(self.project_dir))
            self.assertIsNone(result)

    def test_detect_devstream_project_custom_values(self):
        """Test detection with custom workspace values."""
        custom_data = {
            "name": "custom-project",
            "project_type": "typescript",
            "scan_completed": False,
            "files_count": 0
        }
        self.create_devstream_project(self.project_dir, **custom_data)

        result = detect_devstream_project(str(self.project_dir))

        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "custom-project")
        self.assertEqual(result["project_type"], "typescript")
        self.assertFalse(result["scan_completed"])
        self.assertEqual(result["files_count"], 0)

    def test_find_nearest_devstream_project_current_dir(self):
        """Test finding project in current directory."""
        self.create_devstream_project(self.project_dir)

        result = find_nearest_devstream_project(str(self.project_dir))
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "test-project")

    def test_find_nearest_devstream_project_parent_dir(self):
        """Test finding project in parent directory."""
        self.create_devstream_project(self.project_dir)

        # Create subdirectory
        subdir = self.project_dir / "subdir"
        subdir.mkdir()

        result = find_nearest_devstream_project(str(subdir))
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "test-project")

    def test_find_nearest_devstream_project_not_found(self):
        """Test finding project when none exists."""
        result = find_nearest_devstream_project(str(self.project_dir))
        self.assertIsNone(result)

    @patch('os.environ.get')
    def test_list_projects_registry_exists(self, mock_env_get):
        """Test listing projects when registry exists."""
        # Mock environment
        mock_env_get.return_value = self.temp_dir

        # Create mock registry
        registry_dir = Path(self.temp_dir) / "data"
        registry_dir.mkdir()
        registry_file = registry_dir / "registry.json"

        registry_data = {
            "version": "1.0.0",
            "projects": [
                {
                    "name": "project1",
                    "path": "/path/to/project1",
                    "project_type": "python"
                },
                {
                    "name": "project2",
                    "path": "/path/to/project2",
                    "project_type": "typescript"
                }
            ]
        }

        with open(registry_file, 'w') as f:
            json.dump(registry_data, f)

        result = list_projects()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "project1")
        self.assertEqual(result[1]["name"], "project2")

    @patch('os.environ.get')
    def test_list_projects_no_registry(self, mock_env_get):
        """Test listing projects when registry doesn't exist."""
        mock_env_get.return_value = self.temp_dir

        result = list_projects()
        self.assertEqual(len(result), 0)

    @patch('os.environ.get')
    def test_list_projects_invalid_json(self, mock_env_get):
        """Test listing projects with invalid registry JSON."""
        mock_env_get.return_value = self.temp_dir

        # Create invalid registry file
        registry_dir = Path(self.temp_dir) / "data"
        registry_dir.mkdir()
        registry_file = registry_dir / "registry.json"

        with open(registry_file, 'w') as f:
            f.write("invalid json")

        result = list_projects()
        self.assertEqual(len(result), 0)

    @patch('os.environ.get')
    @patch('os.chmod')
    def test_register_project_success(self, mock_chmod, mock_env_get):
        """Test successful project registration."""
        mock_env_get.return_value = self.temp_dir

        # Create a DevStream project
        self.create_devstream_project(self.project_dir)

        result = register_project(str(self.project_dir))
        self.assertTrue(result)

        # Verify registry was created
        registry_file = Path(self.temp_dir) / "data" / "registry.json"
        self.assertTrue(registry_file.exists())

        # Verify registry contents
        with open(registry_file, 'r') as f:
            registry_data = json.load(f)

        self.assertEqual(len(registry_data["projects"]), 1)
        self.assertEqual(registry_data["projects"][0]["name"], "test-project")
        self.assertEqual(registry_data["statistics"]["total_projects"], 1)

    def test_register_project_no_devstream_project(self):
        """Test registering non-DevStream project."""
        result = register_project(str(self.project_dir))
        self.assertFalse(result)

    def test_register_project_nonexistent_path(self):
        """Test registering nonexistent path."""
        nonexistent_path = "/path/that/does/not/exist"
        result = register_project(nonexistent_path)
        self.assertFalse(result)

    @patch('os.environ.get')
    def test_register_project_custom_name(self, mock_env_get):
        """Test registering project with custom name."""
        mock_env_get.return_value = self.temp_dir

        # Create a DevStream project
        self.create_devstream_project(self.project_dir)

        custom_name = "my-custom-project"
        result = register_project(str(self.project_dir), custom_name)
        self.assertTrue(result)

        # Verify registry contains custom name
        registry_file = Path(self.temp_dir) / "data" / "registry.json"
        with open(registry_file, 'r') as f:
            registry_data = json.load(f)

        # Note: The current implementation doesn't use the custom name parameter
        # This test documents the current behavior
        self.assertEqual(registry_data["projects"][0]["name"], "test-project")

    @patch('os.environ.get')
    def test_register_project_duplicate(self, mock_env_get):
        """Test registering the same project twice."""
        mock_env_get.return_value = self.temp_dir

        # Create a DevStream project
        self.create_devstream_project(self.project_dir)

        # Register first time
        result1 = register_project(str(self.project_dir))
        self.assertTrue(result1)

        # Modify project data
        modified_data = {"files_count": 200}
        self.create_devstream_project(self.project_dir, **modified_data)

        # Register second time
        result2 = register_project(str(self.project_dir))
        self.assertTrue(result2)

        # Verify only one project in registry with updated data
        registry_file = Path(self.temp_dir) / "data" / "registry.json"
        with open(registry_file, 'r') as f:
            registry_data = json.load(f)

        self.assertEqual(len(registry_data["projects"]), 1)
        self.assertEqual(registry_data["projects"][0]["files_count"], 200)


if __name__ == '__main__':
    unittest.main()