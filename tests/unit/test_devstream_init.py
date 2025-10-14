"""
Unit tests for DevStream project initialization script.
Tests project detection, initialization, and codebase scanning functionality.
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

# Import the module directly
import importlib.util
spec = importlib.util.spec_from_file_location("devstream_init", os.path.join(scripts_dir, "devstream-init.py"))
devstream_init_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(devstream_init_module)

# Extract classes and functions from the module
ProjectExistsError = devstream_init_module.ProjectExistsError
CodebaseScanError = devstream_init_module.CodebaseScanError
detect_project_type = devstream_init_module.detect_project_type
scan_and_populate_codebase = devstream_init_module.scan_and_populate_codebase
basic_codebase_scan = devstream_init_module.basic_codebase_scan
create_project_structure = devstream_init_module.create_project_structure
initialize_project = devstream_init_module.initialize_project


class TestDevstreamInit(unittest.TestCase):
    """Test cases for DevStream project initialization functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "test_project"
        self.project_dir.mkdir()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detect_project_type_python(self):
        """Test detecting a Python project."""
        # Create Python project structure
        (self.project_dir / "requirements.txt").write_text("flask==2.0.0")
        (self.project_dir / "setup.py").write_text("from setuptools import setup")
        (self.project_dir / "src" / "app.py").write_text("print('hello')")
        (self.project_dir / "tests" / "test_app.py").write_text("def test(): pass")

        result = detect_project_type(str(self.project_dir))

        self.assertEqual(result["primary_type"], "python")
        self.assertGreater(result["confidence"], 0.5)
        self.assertIn("directory src", result["indicators"])
        self.assertIn("directory tests", result["indicators"])
        self.assertEqual(result["languages"][0]["language"], "python")

    def test_detect_project_type_typescript(self):
        """Test detecting a TypeScript project."""
        # Create TypeScript project structure
        (self.project_dir / "package.json").write_text('{"name": "test"}')
        (self.project_dir / "tsconfig.json").write_text("{}")
        (self.project_dir / "src" / "app.ts").write_text("console.log('hello');")
        (self.project_dir / "src" / "app.tsx").write_text("export default () => <div>test</div>;")

        result = detect_project_type(str(self.project_dir))

        self.assertEqual(result["primary_type"], "typescript")
        self.assertGreater(result["confidence"], 0.5)
        self.assertIn("config tsconfig.json", result["indicators"])

    def test_detect_project_type_generic(self):
        """Test detecting a generic project (no specific type)."""
        # Create only a readme file
        (self.project_dir / "README.md").write_text("# Test Project")

        result = detect_project_type(str(self.project_dir))

        self.assertEqual(result["primary_type"], "generic")
        self.assertEqual(result["confidence"], 0.0)
        self.assertEqual(len(result["languages"]), 0)

    def test_detect_project_type_empty_directory(self):
        """Test detecting project type in empty directory."""
        empty_dir = Path(self.temp_dir) / "empty"
        empty_dir.mkdir()

        result = detect_project_type(str(empty_dir))

        self.assertEqual(result["primary_type"], "generic")
        self.assertEqual(result["confidence"], 0.0)

    def test_basic_codebase_scan_python(self):
        """Test basic codebase scanning for Python project."""
        # Create Python files
        (self.project_dir / "app.py").write_text("def main(): pass")
        (self.project_dir / "utils.py").write_text("def helper(): pass")
        (self.project_dir / "README.md").write_text("# Test")

        # Create subdirectory with more Python files
        subdir = self.project_dir / "src"
        subdir.mkdir()
        (subdir / "module.py").write_text("class Test: pass")

        result = basic_codebase_scan(str(self.project_dir))

        self.assertEqual(result["files_scanned"], 3)
        self.assertEqual(result["file_types"][".py"], 3)
        self.assertGreater(result["scan_duration"], 0)

    def test_basic_codebase_scan_mixed_languages(self):
        """Test basic codebase scanning with multiple languages."""
        # Create files in different languages
        (self.project_dir / "app.py").write_text("def main(): pass")
        (self.project_dir / "script.js").write_text("console.log('test');")
        (self.project_dir / "main.go").write_text("package main")
        (self.project_dir / "README.md").write_text("# Test")

        result = basic_codebase_scan(str(self.project_dir))

        self.assertEqual(result["files_scanned"], 3)
        self.assertEqual(result["file_types"][".py"], 1)
        self.assertEqual(result["file_types"][".js"], 1)
        self.assertEqual(result["file_types"][".go"], 1)

    def test_basic_codebase_scan_empty_directory(self):
        """Test basic codebase scanning in empty directory."""
        empty_dir = Path(self.temp_dir) / "empty"
        empty_dir.mkdir()

        result = basic_codebase_scan(str(empty_dir))

        self.assertEqual(result["files_scanned"], 0)
        self.assertEqual(len(result["file_types"]), 0)

    @patch('devstream_init_module.CONTEXT7_AVAILABLE', False)
    def test_scan_and_populate_codebase_context7_unavailable(self):
        """Test codebase scanning when Context7 is not available."""
        (self.project_dir / "app.py").write_text("def main(): pass")

        result = scan_and_populate_codebase(str(self.project_dir))

        # Should fall back to basic scanning
        self.assertEqual(result["files_scanned"], 1)
        self.assertEqual(result["file_types"][".py"], 1)

    def test_create_project_structure_new_project(self):
        """Test creating project structure for new project."""
        create_project_structure(str(self.project_dir))

        devstream_dir = self.project_dir / ".devstream"
        self.assertTrue(devstream_dir.exists())
        self.assertTrue((devstream_dir / "db").exists())
        self.assertTrue((devstream_dir / "logs").exists())
        self.assertTrue((devstream_dir / "cache").exists())
        self.assertTrue((devstream_dir / "config").exists())
        self.assertTrue((devstream_dir / "templates").exists())
        self.assertTrue((devstream_dir / "workspace.json").exists())

        # Check workspace.json content
        workspace_file = devstream_dir / "workspace.json"
        with open(workspace_file) as f:
            workspace_data = json.load(f)

        self.assertEqual(workspace_data["name"], self.project_dir.name)
        self.assertEqual(workspace_data["project_type"], "unknown")
        self.assertFalse(workspace_data["scan_completed"])

    def test_create_project_structure_existing_devstream(self):
        """Test creating project structure when .devstream already exists."""
        # Create existing .devstream directory
        devstream_dir = self.project_dir / ".devstream"
        devstream_dir.mkdir()
        (devstream_dir / "existing_file.txt").write_text("test")

        create_project_structure(str(self.project_dir))

        # Should not remove existing directory
        self.assertTrue((devstream_dir / "existing_file.txt").exists())
        self.assertTrue((devstream_dir / "workspace.json").exists())

    def test_initialize_project_new_project(self):
        """Test initializing a new project."""
        # Create a Python file for detection
        (self.project_dir / "app.py").write_text("def main(): pass")

        result = initialize_project(str(self.project_dir))

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["project_name"], self.project_dir.name)
        self.assertEqual(result["project_type"], "python")  # Should detect Python
        self.assertIsNotNone(result["scan_results"])
        self.assertTrue((self.project_dir / ".devstream" / "workspace.json").exists())

        # Check workspace was updated
        workspace_file = self.project_dir / ".devstream" / "workspace.json"
        with open(workspace_file) as f:
            workspace_data = json.load(f)

        self.assertEqual(workspace_data["project_type"], "python")
        self.assertTrue(workspace_data["scan_completed"])
        self.assertGreater(workspace_data["files_count"], 0)

    def test_initialize_project_force_reinit(self):
        """Test force reinitialization of existing project."""
        # Create existing DevStream project
        devstream_dir = self.project_dir / ".devstream"
        devstream_dir.mkdir()
        (devstream_dir / "existing_file.txt").write_text("old")

        result = initialize_project(str(self.project_dir), force_reinit=True)

        self.assertEqual(result["status"], "success")
        # Old file should be gone due to force reinit
        self.assertFalse((devstream_dir / "existing_file.txt").exists())

    def test_initialize_project_already_exists_no_force(self):
        """Test initializing project that already exists without force."""
        # Create existing DevStream project
        devstream_dir = self.project_dir / ".devstream"
        devstream_dir.mkdir()
        (devstream_dir / "workspace.json").write_text("{}")

        with self.assertRaises(ProjectExistsError):
            initialize_project(str(self.project_dir), force_reinit=False)

    def test_initialize_project_no_scan(self):
        """Test initializing project without codebase scanning."""
        (self.project_dir / "app.py").write_text("def main(): pass")

        result = initialize_project(str(self.project_dir), scan_existing_codebase=False)

        self.assertEqual(result["status"], "success")
        self.assertIsNone(result["scan_results"])

        # Check workspace was not marked as scanned
        workspace_file = self.project_dir / ".devstream" / "workspace.json"
        with open(workspace_file) as f:
            workspace_data = json.load(f)

        self.assertFalse(workspace_data["scan_completed"])
        self.assertEqual(workspace_data["files_count"], 0)

    def test_initialize_project_nonexistent_path(self):
        """Test initializing project in nonexistent path."""
        nonexistent_path = "/path/that/does/not/exist"

        result = initialize_project(nonexistent_path)

        self.assertEqual(result["status"], "failed")
        self.assertIn("error", result)

    @patch('devstream_init_module.scan_and_populate_codebase')
    def test_initialize_project_scan_failure(self, mock_scan):
        """Test handling of codebase scan failure."""
        mock_scan.side_effect = CodebaseScanError("Scan failed")

        (self.project_dir / "app.py").write_text("def main(): pass")

        result = initialize_project(str(self.project_dir), scan_existing_codebase=True)

        self.assertEqual(result["status"], "failed")
        self.assertIn("error", result)


if __name__ == '__main__':
    unittest.main()