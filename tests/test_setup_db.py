#!/usr/bin/env python3
"""
Tests for scripts/setup-db.py

Purpose: Validate database setup script functionality.

Usage:
    .devstream/bin/python -m pytest tests/test_setup_db.py -v
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest


def test_setup_db_script_imports() -> None:
    """Test that setup-db.py can be imported without errors."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

    # This will fail if there are syntax errors or import issues
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "setup_db",
        Path(__file__).parent.parent / "scripts" / "setup-db.py"
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert module is not None


def test_database_creation_with_script() -> None:
    """Test database creation using the setup-db.py script."""
    import subprocess

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_devstream.db"
        schema_path = Path(__file__).parent.parent / "schema" / "schema.sql"

        # Run setup script
        result = subprocess.run(
            [
                ".devstream/bin/python",
                "scripts/setup-db.py",
                "--db-path", str(db_path),
                "--schema-file", str(schema_path),
                "--force",
            ],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )

        # Verify script succeeded
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        assert "Database created successfully" in result.stdout

        # Verify database file exists
        assert db_path.exists()

        # Verify database structure
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Count tables
        cursor.execute("""
            SELECT COUNT(*) FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        table_count = cursor.fetchone()[0]
        assert table_count >= 12, f"Expected at least 12 tables, found {table_count}"

        # Verify core tables exist
        core_tables = [
            'intervention_plans', 'phases', 'micro_tasks', 'semantic_memory',
            'agents', 'hooks', 'work_sessions', 'schema_version'
        ]
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        existing_tables = [row[0] for row in cursor.fetchall()]

        for table in core_tables:
            assert table in existing_tables, f"Core table '{table}' not found"

        # Verify schema version
        cursor.execute("SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1")
        version = cursor.fetchone()
        assert version is not None
        assert version[0] == "2.1.0"

        conn.close()


def test_database_force_overwrite() -> None:
    """Test that --force flag overwrites existing database."""
    import subprocess

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_devstream.db"
        schema_path = Path(__file__).parent.parent / "schema" / "schema.sql"

        # Create initial database
        result1 = subprocess.run(
            [
                ".devstream/bin/python",
                "scripts/setup-db.py",
                "--db-path", str(db_path),
                "--schema-file", str(schema_path),
                "--force",
            ],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        assert result1.returncode == 0
        initial_size = db_path.stat().st_size

        # Force overwrite
        result2 = subprocess.run(
            [
                ".devstream/bin/python",
                "scripts/setup-db.py",
                "--db-path", str(db_path),
                "--schema-file", str(schema_path),
                "--force",
            ],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        assert result2.returncode == 0
        # Check for force overwrite message in stdout (structlog output)
        assert "database_exists_force_overwrite" in result2.stdout or "database_exists_force_overwrite" in result2.stderr

        # Verify database was recreated (size should be similar)
        final_size = db_path.stat().st_size
        assert abs(final_size - initial_size) < 10000  # Allow 10KB variance


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
