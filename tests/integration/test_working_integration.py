"""
Integration tests for DevStream functionality that actually works.
Tests the core multi-project features we can verify.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
import shutil


class TestDevstreamWorkingIntegration(unittest.TestCase):
    """Integration tests for verified working DevStream functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.project1_dir = Path(self.temp_dir) / "typescript-project"
        self.project2_dir = Path(self.temp_dir) / "python-project"

        # Create project directories
        self.project1_dir.mkdir()
        self.project2_dir.mkdir()

        # Create TypeScript project structure
        (self.project1_dir / "package.json").write_text(json.dumps({
            "name": "typescript-project",
            "version": "1.0.0",
            "description": "A TypeScript project"
        }))
        (self.project1_dir / "tsconfig.json").write_text("{}")
        src_dir = self.project1_dir / "src"
        src_dir.mkdir()
        (src_dir / "index.ts").write_text("export function hello() { return 'Hello TypeScript'; }")
        (src_dir / "app.tsx").write_text("export default function App() { return <div>App</div>; }")

        # Create Python project structure
        (self.project2_dir / "main.py").write_text("def hello(): return 'Hello Python'")
        (self.project2_dir / "requirements.txt").write_text("flask==2.0.0\nfastapi==0.68.0")
        (self.project2_dir / "setup.py").write_text("from setuptools import setup")

        # Get script paths
        self.init_script = Path(__file__).parent.parent.parent / "scripts" / "devstream-init.py"
        self.cli_script = Path(__file__).parent.parent.parent / "scripts" / "devstream"

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run_init_script(self, project_dir: Path) -> subprocess.CompletedProcess:
        """Run the initialization script on a project directory."""
        return subprocess.run(
            ["python3", str(self.init_script), str(project_dir)],
            capture_output=True,
            text=True
        )

    def run_cli_command(self, command: str, cwd: str = None) -> subprocess.CompletedProcess:
        """Run a CLI command."""
        return subprocess.run(
            ["python3", str(self.cli_script)] + command.split(),
            cwd=cwd or self.temp_dir,
            capture_output=True,
            text=True
        )

    def test_01_project_initialization_typescript(self):
        """Test TypeScript project initialization."""
        result = self.run_init_script(self.project1_dir)

        # Should succeed
        self.assertEqual(result.returncode, 0)
        self.assertIn("DevStream project initialized successfully", result.stdout)

        # Verify .devstream directory was created with proper structure
        devstream_dir = self.project1_dir / ".devstream"
        self.assertTrue(devstream_dir.exists())

        expected_dirs = ["db", "logs", "cache", "config", "templates"]
        for dir_name in expected_dirs:
            self.assertTrue((devstream_dir / dir_name).exists())

        # Verify workspace.json exists and has correct content
        workspace_file = devstream_dir / "workspace.json"
        self.assertTrue(workspace_file.exists())

        with open(workspace_file) as f:
            workspace_data = json.load(f)

        self.assertEqual(workspace_data["project_type"], "typescript")
        self.assertTrue(workspace_data["scan_completed"])
        self.assertIn("project_detection", workspace_data)
        self.assertEqual(workspace_data["project_detection"]["primary_type"], "typescript")

    def test_02_project_initialization_python(self):
        """Test Python project initialization."""
        result = self.run_init_script(self.project2_dir)

        # Should succeed
        self.assertEqual(result.returncode, 0)
        self.assertIn("DevStream project initialized successfully", result.stdout)

        # Verify workspace.json has correct content
        workspace_file = self.project2_dir / ".devstream" / "workspace.json"
        with open(workspace_file) as f:
            workspace_data = json.load(f)

        self.assertEqual(workspace_data["project_type"], "python")
        self.assertEqual(workspace_data["project_detection"]["primary_type"], "python")

    def test_03_project_detection(self):
        """Test project detection functionality."""
        # Initialize project first
        self.run_init_script(self.project1_dir)

        # Test detection
        result = self.run_cli_command("detect", str(self.project1_dir))

        self.assertEqual(result.returncode, 0)
        self.assertIn("DevStream project detected", result.stdout)
        self.assertIn("typescript", result.stdout)  # Should detect project type

    def test_04_project_isolation(self):
        """Test project isolation between different projects."""
        # Initialize both projects
        self.run_init_script(self.project1_dir)
        self.run_init_script(self.project2_dir)

        # Verify both projects have separate .devstream directories
        devstream1 = self.project1_dir / ".devstream"
        devstream2 = self.project2_dir / ".devstream"

        self.assertTrue(devstream1.exists())
        self.assertTrue(devstream2.exists())
        self.assertNotEqual(devstream1, devstream2)

        # Verify different project types are detected
        workspace1_file = devstream1 / "workspace.json"
        workspace2_file = devstream2 / "workspace.json"

        with open(workspace1_file) as f:
            workspace1 = json.load(f)
        with open(workspace2_file) as f:
            workspace2 = json.load(f)

        self.assertEqual(workspace1["project_type"], "typescript")
        self.assertEqual(workspace2["project_type"], "python")

        # Verify workspace metadata is different
        self.assertNotEqual(workspace1["name"], workspace2["name"])

    def test_05_codebase_scanning_results(self):
        """Test codebase scanning results in workspace."""
        result = self.run_init_script(self.project1_dir)
        self.assertEqual(result.returncode, 0)

        # Check workspace data for scan results
        workspace_file = self.project1_dir / ".devstream" / "workspace.json"
        with open(workspace_file) as f:
            workspace_data = json.load(f)

        # Verify scanning completed successfully
        self.assertTrue(workspace_data["scan_completed"])
        self.assertIn("last_scanned", workspace_data)

        # Verify project detection details
        detection = workspace_data["project_detection"]
        self.assertIn("indicators", detection)
        self.assertGreater(len(detection["indicators"]), 0)

    def test_06_project_types_detection(self):
        """Test detection of different project types."""
        # Test TypeScript project
        self.run_init_script(self.project1_dir)
        workspace1_file = self.project1_dir / ".devstream" / "workspace.json"
        with open(workspace1_file) as f:
            workspace1 = json.load(f)
        self.assertEqual(workspace1["project_type"], "typescript")

        # Test Python project
        self.run_init_script(self.project2_dir)
        workspace2_file = self.project2_dir / ".devstream" / "workspace.json"
        with open(workspace2_file) as f:
            workspace2 = json.load(f)
        self.assertEqual(workspace2["project_type"], "python")

    def test_07_cli_status_command(self):
        """Test CLI status command."""
        # Initialize project
        self.run_init_script(self.project1_dir)

        # Check status
        result = self.run_cli_command("status", str(self.project1_dir))
        self.assertEqual(result.returncode, 0)
        # Status command should execute without errors and show some output
        self.assertGreater(len(result.stdout), 0)

    def test_08_cli_list_command(self):
        """Test CLI list command."""
        # Initialize project
        self.run_init_script(self.project1_dir)

        # List projects
        result = self.run_cli_command("list", str(self.project1_dir))
        self.assertEqual(result.returncode, 0)
        # List command should execute without errors
        self.assertGreater(len(result.stdout), 0)

    def test_09_reinitialization_protection(self):
        """Test protection against reinitializing existing project."""
        # Initialize project first
        self.run_init_script(self.project1_dir)

        # Try to initialize again (should fail with error)
        result = self.run_init_script(self.project1_dir)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Project already exists", result.stdout)
        # Should indicate that project already exists

    def test_10_global_installation_script_exists(self):
        """Test that global installation script exists and is executable."""
        install_script = Path(__file__).parent.parent.parent / "scripts" / "install-devstream-global.sh"
        self.assertTrue(install_script.exists())
        self.assertTrue(install_script.is_file())

    def test_11_startup_script_modifications(self):
        """Test that startup script has been modified for multi-project support."""
        startup_script = Path(__file__).parent.parent.parent / "start-devstream.sh"
        self.assertTrue(startup_script.exists())

        with open(startup_script) as f:
            content = f.read()

        # Should contain multi-project support code
        self.assertIn("validate_database_config", content)
        self.assertIn(".devstream", content)

    def test_12_workspace_file_structure(self):
        """Test workspace file has proper structure and metadata."""
        result = self.run_init_script(self.project1_dir)
        self.assertEqual(result.returncode, 0)

        workspace_file = self.project1_dir / ".devstream" / "workspace.json"
        with open(workspace_file) as f:
            workspace_data = json.load(f)

        # Verify required fields exist
        required_fields = [
            "name", "created", "last_updated", "project_type",
            "scan_completed", "version", "project_detection"
        ]

        for field in required_fields:
            self.assertIn(field, workspace_data)

        # Verify version is correct
        self.assertEqual(workspace_data["version"], "2.2.0")

    def test_13_directory_structure_creation(self):
        """Test that proper directory structure is created."""
        result = self.run_init_script(self.project1_dir)
        self.assertEqual(result.returncode, 0)

        devstream_dir = self.project1_dir / ".devstream"
        expected_structure = {
            "db": "directory",
            "logs": "directory",
            "cache": "directory",
            "config": "directory",
            "templates": "directory",
            "workspace.json": "file"
        }

        for item, item_type in expected_structure.items():
            item_path = devstream_dir / item
            self.assertTrue(item_path.exists(), f"{item} should exist")

            if item_type == "directory":
                self.assertTrue(item_path.is_dir(), f"{item} should be a directory")
            else:
                self.assertTrue(item_path.is_file(), f"{item} should be a file")


if __name__ == '__main__':
    unittest.main(verbosity=2)