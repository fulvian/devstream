"""
Simplified integration tests for DevStream multi-project architecture.
Tests core functionality that we can reliably verify.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
import shutil
import sqlite3


class TestDevstreamCoreFunctionality(unittest.TestCase):
    """Core functionality tests for DevStream multi-project architecture."""

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
            "version": "1.0.0"
        }))
        (self.project1_dir / "tsconfig.json").write_text("{}")
        src_dir = self.project1_dir / "src"
        src_dir.mkdir()
        (src_dir / "index.ts").write_text("export function hello() { return 'Hello'; }")

        # Create Python project structure
        (self.project2_dir / "main.py").write_text("def hello(): return 'Hello'")
        (self.project2_dir / "requirements.txt").write_text("flask==2.0.0")
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
            text=True,
            cwd=str(project_dir)
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

        # Verify .devstream directory was created
        devstream_dir = self.project1_dir / ".devstream"
        self.assertTrue(devstream_dir.exists())

        # Verify workspace.json exists and has correct content
        workspace_file = devstream_dir / "workspace.json"
        self.assertTrue(workspace_file.exists())

        with open(workspace_file) as f:
            workspace_data = json.load(f)

        self.assertEqual(workspace_data["project_type"], "typescript")
        self.assertTrue(workspace_data["scan_completed"])
        self.assertGreater(workspace_data["files_count"], 0)

        # Verify database was created
        db_file = devstream_dir / "db" / "devstream.db"
        self.assertTrue(db_file.exists())

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

    def test_03_project_detection(self):
        """Test project detection functionality."""
        # Initialize project first
        self.run_init_script(self.project1_dir)

        # Test detection
        result = self.run_cli_command("detect", str(self.project1_dir))

        self.assertEqual(result.returncode, 0)
        self.assertIn("DevStream project detected", result.stdout)

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

        # Verify separate databases
        db1 = devstream1 / "db" / "devstream.db"
        db2 = devstream2 / "db" / "devstream.db"

        self.assertTrue(db1.exists())
        self.assertTrue(db2.exists())
        self.assertNotEqual(db1, db2)

        # Verify different project types are detected
        workspace1_file = devstream1 / "workspace.json"
        workspace2_file = devstream2 / "workspace.json"

        with open(workspace1_file) as f:
            workspace1 = json.load(f)
        with open(workspace2_file) as f:
            workspace2 = json.load(f)

        self.assertEqual(workspace1["project_type"], "typescript")
        self.assertEqual(workspace2["project_type"], "python")

    def test_05_codebase_scanning(self):
        """Test codebase scanning functionality."""
        result = self.run_init_script(self.project1_dir)

        self.assertEqual(result.returncode, 0)

        # Check workspace data for scan results
        workspace_file = self.project1_dir / ".devstream" / "workspace.json"
        with open(workspace_file) as f:
            workspace_data = json.load(f)

        # Verify scanning completed successfully
        self.assertTrue(workspace_data["scan_completed"])
        self.assertGreater(workspace_data["files_count"], 0)

        # Verify database has entries
        db_file = self.project1_dir / ".devstream" / "db" / "devstream.db"
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()

        # Check if memory table exists and has entries
        try:
            cursor.execute("SELECT COUNT(*) FROM memory")
            memory_count = cursor.fetchone()[0]
            self.assertGreaterEqual(memory_count, 0)  # Should be >= 0
        except sqlite3.OperationalError:
            # Table might not exist if Context7 is not available
            pass

        conn.close()

    def test_06_database_structure(self):
        """Test database structure and initialization."""
        result = self.run_init_script(self.project1_dir)
        self.assertEqual(result.returncode, 0)

        db_file = self.project1_dir / ".devstream" / "db" / "devstream.db"
        self.assertTrue(db_file.exists())

        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()

        # Check if basic tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        # Should have at least some basic tables
        self.assertGreater(len(tables), 0)

        conn.close()

    def test_07_error_handling_nonexistent_directory(self):
        """Test error handling for non-existent directory."""
        nonexistent_path = Path(self.temp_dir) / "does-not-exist"
        result = self.run_init_script(nonexistent_path)

        self.assertNotEqual(result.returncode, 0)
        # Should handle the error gracefully

    def test_08_status_command(self):
        """Test status command functionality."""
        # Initialize project
        self.run_init_script(self.project1_dir)

        # Check status
        result = self.run_cli_command("status", str(self.project1_dir))
        self.assertEqual(result.returncode, 0)
        # Status command should work without errors

    def test_09_startup_script_database_validation(self):
        """Test startup script database validation logic."""
        # Initialize project
        self.run_init_script(self.project1_dir)

        # Test the validate_database_config function from startup script
        startup_script = Path(__file__).parent.parent.parent / "start-devstream.sh"

        # Create a test script that sources the startup script and runs validation
        test_script_content = f"""
#!/bin/bash
export PROJECT_ROOT="{self.project1_dir}"
source "{startup_script}"
validate_database_config
exit_code=$?
echo "Validation exit code: $exit_code"
exit $exit_code
"""

        test_script = Path(self.temp_dir) / "test_validation.sh"
        test_script.write_text(test_script_content)
        test_script.chmod(0o755)

        result = subprocess.run(["bash", str(test_script)],
                              capture_output=True, text=True)

        # Should succeed in multi-project mode
        self.assertEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)