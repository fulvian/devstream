"""
Integration tests for DevStream multi-project architecture.
Tests complete functionality including project initialization, codebase scanning,
isolation testing, and parallel session capability.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open
import shutil
import sqlite3
import time


class TestDevstreamMultiProjectIntegration(unittest.TestCase):
    """Integration tests for DevStream multi-project architecture."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.devstream_home = Path(self.temp_dir) / ".devstream"
        self.project1_dir = Path(self.temp_dir) / "accountabilly"
        self.project2_dir = Path(self.temp_dir) / "another-project"

        # Create project directories
        self.project1_dir.mkdir()
        self.project2_dir.mkdir()

        # Mock accountabilly project structure
        (self.project1_dir / "package.json").write_text(json.dumps({
            "name": "accountabilly",
            "version": "1.0.0",
            "description": "Accountability application"
        }))
        (self.project1_dir / "tsconfig.json").write_text("{}")
        src_dir = self.project1_dir / "src"
        src_dir.mkdir()
        (src_dir / "index.ts").write_text("export function main() { console.log('Hello'); }")
        (src_dir / "app.tsx").write_text("export default function App() { return <div>App</div>; }")

        # Create another project
        (self.project2_dir / "main.py").write_text("def hello(): pass")
        (self.project2_dir / "requirements.txt").write_text("flask==2.0.0")

        # Set environment variables
        os.environ["DEVSTREAM_HOME"] = str(self.devstream_home)

        # Add scripts to path
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        os.environ["PATH"] = f"{scripts_dir}:{os.environ.get('PATH', '')}"

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run_devstream_command(self, cmd: str, cwd: str = None) -> subprocess.CompletedProcess:
        """Run a devstream command and return the result."""
        full_cmd = ["python3", str(Path(__file__).parent.parent.parent / "scripts" / "devstream")] + cmd.split()
        return subprocess.run(
            full_cmd,
            cwd=cwd or self.temp_dir,
            capture_output=True,
            text=True
        )

    def run_devstream_init_command(self, cwd: str = None) -> subprocess.CompletedProcess:
        """Run devstream-init command."""
        init_script = Path(__file__).parent.parent.parent / "scripts" / "devstream-init.py"
        return subprocess.run(
            ["python3", str(init_script), cwd or str(self.project1_dir)],
            capture_output=True,
            text=True
        )

    def test_01_global_installation_and_setup(self):
        """Test global installation and initial setup."""
        # Run global installation
        install_script = Path(__file__).parent.parent.parent / "scripts" / "install-devstream-global.sh"

        # Mock the installation to avoid system-wide changes
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Installation successful"

            result = subprocess.run(["bash", str(install_script)],
                                  capture_output=True, text=True)

            # Verify installation script exists and is executable
            self.assertTrue(install_script.exists())
            self.assertTrue(os.access(install_script, os.X_OK))

    def test_02_project_detection_cli(self):
        """Test project detection via CLI."""
        # First initialize project
        self.run_devstream_init_command(str(self.project1_dir))

        # Test detection command
        result = self.run_devstream_command("detect", str(self.project1_dir))

        self.assertEqual(result.returncode, 0)
        self.assertIn("DevStream project detected", result.stdout)

    def test_03_project_initialization_accountabilly(self):
        """Test initializing the accountabilly project."""
        result = self.run_devstream_init_command(str(self.project1_dir))

        self.assertEqual(result.returncode, 0)

        # Verify .devstream directory was created
        devstream_dir = self.project1_dir / ".devstream"
        self.assertTrue(devstream_dir.exists())

        # Verify workspace.json exists and has correct content
        workspace_file = devstream_dir / "workspace.json"
        self.assertTrue(workspace_file.exists())

        with open(workspace_file) as f:
            workspace_data = json.load(f)

        self.assertEqual(workspace_data["name"], "accountabilly")
        self.assertEqual(workspace_data["project_type"], "typescript")
        self.assertTrue(workspace_data["scan_completed"])
        self.assertGreater(workspace_data["files_count"], 0)

        # Verify database was created
        db_file = devstream_dir / "db" / "devstream.db"
        self.assertTrue(db_file.exists())

    def test_04_codebase_scanning_and_analysis(self):
        """Test codebase scanning functionality."""
        # Initialize project
        self.run_devstream_init_command(str(self.project1_dir))

        # Check workspace data for scan results
        workspace_file = self.project1_dir / ".devstream" / "workspace.json"
        with open(workspace_file) as f:
            workspace_data = json.load(f)

        # Verify scanning completed successfully
        self.assertTrue(workspace_data["scan_completed"])
        self.assertGreater(workspace_data["files_count"], 2)  # Should find at least 2 TypeScript files

        # Verify database has memory entries
        db_file = self.project1_dir / ".devstream" / "db" / "devstream.db"
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()

        # Check if memory table exists and has entries
        cursor.execute("SELECT COUNT(*) FROM memory")
        memory_count = cursor.fetchone()[0]
        self.assertGreater(memory_count, 0)

        conn.close()

    def test_05_project_isolation(self):
        """Test project isolation between different projects."""
        # Initialize both projects
        self.run_devstream_init_command(str(self.project1_dir))
        self.run_devstream_init_command(str(self.project2_dir))

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

    def test_06_startup_script_multi_project_mode(self):
        """Test startup script in multi-project mode."""
        # Initialize project
        self.run_devstream_init_command(str(self.project1_dir))

        # Test database configuration validation
        startup_script = Path(__file__).parent.parent.parent / "start-devstream.sh"

        # Mock the startup script to test the validate_database_config function
        with patch.dict(os.environ, {"PROJECT_ROOT": str(self.project1_dir)}):
            # Create a test script to validate database config
            test_script_content = f"""
#!/bin/bash
source {startup_script}
validate_database_config
echo "Database validation exit code: $?"
"""
            test_script = Path(self.temp_dir) / "test_db_validation.sh"
            test_script.write_text(test_script_content)
            test_script.chmod(0o755)

            result = subprocess.run(["bash", str(test_script)],
                                  capture_output=True, text=True)

            # Should succeed in multi-project mode
            self.assertEqual(result.returncode, 0)

    def test_07_project_registration_and_listing(self):
        """Test project registration and listing functionality."""
        # Initialize project
        self.run_devstream_init_command(str(self.project1_dir))

        # Register project
        result = self.run_devstream_command(f"register {self.project1_dir}")
        self.assertEqual(result.returncode, 0)

        # List projects
        result = self.run_devstream_command("list")
        self.assertEqual(result.returncode, 0)
        self.assertIn("accountabilly", result.stdout)

    def test_08_status_command(self):
        """Test status command functionality."""
        # Initialize project
        self.run_devstream_init_command(str(self.project1_dir))

        # Check status
        result = self.run_devstream_command("status", str(self.project1_dir))
        self.assertEqual(result.returncode, 0)
        self.assertIn("Current Project: accountabilly", result.stdout)
        self.assertIn("Type: typescript", result.stdout)

    def test_09_backward_compatibility_legacy_mode(self):
        """Test backward compatibility with legacy single-project mode."""
        # Create a legacy-style project (no .devstream directory, just data/)
        legacy_dir = Path(self.temp_dir) / "legacy-project"
        legacy_dir.mkdir()

        data_dir = legacy_dir / "data"
        data_dir.mkdir()

        # Create legacy database
        legacy_db = data_dir / "devstream.db"
        conn = sqlite3.connect(str(legacy_db))
        conn.close()

        # Test that startup script handles legacy mode
        with patch.dict(os.environ, {"PROJECT_ROOT": str(legacy_dir)}):
            test_script_content = f"""
#!/bin/bash
source {Path(__file__).parent.parent.parent / "start-devstream.sh"}
validate_database_config
echo "Legacy mode database validation exit code: $?"
"""
            test_script = Path(self.temp_dir) / "test_legacy_validation.sh"
            test_script.write_text(test_script_content)
            test_script.chmod(0o755)

            result = subprocess.run(["bash", str(test_script)],
                                  capture_output=True, text=True)

            # Should succeed in legacy mode
            self.assertEqual(result.returncode, 0)

    def test_10_error_handling_and_recovery(self):
        """Test error handling and recovery scenarios."""
        # Test initialization of non-existent directory
        nonexistent_path = Path(self.temp_dir) / "does-not-exist"
        result = self.run_devstream_init_command(str(nonexistent_path))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not exist", result.stderr)

        # Test initialization of directory without permissions (mock)
        restricted_dir = Path(self.temp_dir) / "restricted"
        restricted_dir.mkdir()

        with patch('os.chmod') as mock_chmod:
            mock_chmod.side_effect = PermissionError("Permission denied")
            result = self.run_devstream_init_command(str(restricted_dir))

            # Should handle permission errors gracefully
            self.assertNotEqual(result.returncode, 0)

    def test_11_parallel_session_simulation(self):
        """Test simulation of parallel sessions on same project."""
        # Initialize project
        self.run_devstream_init_command(str(self.project1_dir))

        # Simulate multiple operations that could happen in parallel
        operations = []

        # Operation 1: Store memory
        operations.append(subprocess.Popen([
            "python3", "-c", f"""
import sqlite3
import json
conn = sqlite3.connect('{self.project1_dir}/.devstream/db/devstream.db')
conn.execute('INSERT INTO memory (content, content_type, keywords) VALUES (?, ?, ?)',
             ('test content 1', 'test', 'test1'))
conn.commit()
conn.close()
"""
        ]))

        # Operation 2: Update workspace
        operations.append(subprocess.Popen([
            "python3", "-c", f"""
import json
workspace_file = '{self.project1_dir}/.devstream/workspace.json'
with open(workspace_file, 'r') as f:
    data = json.load(f)
data['last_updated'] = '2025-10-14T23:00:00Z'
with open(workspace_file, 'w') as f:
    json.dump(data, f)
"""
        ]))

        # Wait for all operations to complete
        for op in operations:
            op.wait()

        # Verify all operations completed successfully
        for op in operations:
            self.assertEqual(op.returncode, 0)

        # Verify database consistency
        db_file = self.project1_dir / ".devstream" / "db" / "devstream.db"
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM memory WHERE content_type = 'test'")
        test_count = cursor.fetchone()[0]
        self.assertEqual(test_count, 1)

        conn.close()

    def test_12_database_migration_simulation(self):
        """Test simulation of database migration from legacy to multi-project."""
        # Create legacy project structure
        legacy_dir = Path(self.temp_dir) / "migrate-project"
        legacy_dir.mkdir()

        # Create legacy data directory with database
        data_dir = legacy_dir / "data"
        data_dir.mkdir()
        legacy_db = data_dir / "devstream.db"

        # Initialize legacy database with some data
        conn = sqlite3.connect(str(legacy_db))
        conn.execute('''
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL,
                keywords TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            INSERT INTO memory (content, content_type, keywords)
            VALUES (?, ?, ?)
        ''', ('legacy content', 'legacy', 'migration-test'))
        conn.commit()
        conn.close()

        # Now initialize as multi-project (should migrate)
        result = self.run_devstream_init_command(str(legacy_dir))
        self.assertEqual(result.returncode, 0)

        # Verify new .devstream structure was created
        devstream_dir = legacy_dir / ".devstream"
        self.assertTrue(devstream_dir.exists())

        new_db = devstream_dir / "db" / "devstream.db"
        self.assertTrue(new_db.exists())

        # Legacy database should still exist (backup)
        self.assertTrue(legacy_db.exists())


if __name__ == '__main__':
    unittest.main()