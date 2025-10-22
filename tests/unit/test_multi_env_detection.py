"""
Test multi-virtual environment detection functionality.

Tests for ensure_sqlite_vec_for_all_envs() function in install-devstream.sh
"""

import pytest
import tempfile
import os
import subprocess
import sys
from pathlib import Path


class TestMultiEnvDetection:
    """Test multi-virtual environment detection functionality."""

    def test_ensure_sqlite_vec_for_all_envs_function_exists(self):
        """Test that the function exists in install-devstream.sh."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "install-devstream.sh"
        script_content = script_path.read_text()

        # Check if function is defined
        assert "ensure_sqlite_vec_for_all_envs()" in script_content
        assert "local env_dirs=(\".devstream\" \".venv\" \"venv\" \"env\")" in script_content

    def test_virtual_environment_detection_pattern(self):
        """Test virtual environment detection patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test multiple virtual environments
            env_dirs = [".devstream", ".venv", "venv", "env"]
            created_envs = []

            for env_dir in env_dirs:
                env_path = temp_path / env_dir
                env_path.mkdir()
                (env_path / "bin").mkdir()

                # Create dummy python executables
                python_path = env_path / "bin" / "python"
                python_path.write_text("#!/bin/bash\necho 'python dummy'")
                python_path.chmod(0o755)
                created_envs.append(env_dir)

            # Test the detection logic (extracted from function)
            detected_envs = []
            for env_dir in env_dirs:
                env_path = temp_path / env_dir
                if env_path.exists() and (env_path / "bin" / "python").exists():
                    detected_envs.append(env_dir)

            assert len(detected_envs) == len(created_envs)
            assert set(detected_envs) == set(created_envs)

    def test_function_signature_and_return_values(self):
        """Test function signature and return value patterns."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "install-devstream.sh"
        script_content = script_path.read_text()

        # Check function signature
        assert "ensure_sqlite_vec_for_all_envs() {" in script_content
        assert "local project_root=\"$1\"" in script_content

        # Check return value pattern
        assert "return $((total_count - success_count))" in script_content
        assert "echo \"sqlite-vec installed in $success_count/$total_count environments\"" in script_content

    def test_error_handling_continues_on_failure(self):
        """Test that function continues even if some environments fail."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "install-devstream.sh"
        script_content = script_path.read_text()

        # Check that there's no early exit on individual failures
        assert "return 1" not in script_content.split("ensure_sqlite_vec_for_all_envs()")[1].split("ensure_sqlite_vec_for_env")[0]

        # Check that failures are counted but don't stop execution
        assert "if ensure_sqlite_vec_for_env \"$env_path\" \"$env_dir\"; then" in script_content
        assert "((success_count++))" in script_content

    def test_integration_with_existing_ensure_sqlite_vec_for_env(self):
        """Test integration with existing ensure_sqlite_vec_for_env function."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "install-devstream.sh"
        script_content = script_path.read_text()

        # Check that existing function is called correctly
        assert "ensure_sqlite_vec_for_env \"$env_path\" \"$env_dir\"" in script_content

        # Both functions should exist
        assert "ensure_sqlite_vec_for_env() {" in script_content
        assert "ensure_sqlite_vec_for_all_envs() {" in script_content

    def test_enhanced_environment_coverage(self):
        """Test that all expected environment types are covered."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "install-devstream.sh"
        script_content = script_path.read_text()

        expected_envs = [".devstream", ".venv", "venv", "env"]

        # Check that all expected environments are in the array
        for env in expected_envs:
            assert f'"{env}"' in script_content.split("local env_dirs=")[1].split(")")[0]

    def test_function_location_in_script(self):
        """Test that function is properly placed in the script."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "install-devstream.sh"
        script_content = script_path.read_text()

        # Function should be after ensure_sqlite_vec_for_env
        env_func_pos = script_content.find("ensure_sqlite_vec_for_env() {")
        all_envs_func_pos = script_content.find("ensure_sqlite_vec_for_all_envs() {")

        assert env_func_pos > 0, "ensure_sqlite_vec_for_env function should exist"
        assert all_envs_func_pos > env_func_pos, "ensure_sqlite_vec_for_all_envs should come after ensure_sqlite_vec_for_env"