#!/usr/bin/env python3
"""
Unit Tests for Path Validator - Database Path Security
Tests path traversal attack prevention (CWE-22, OWASP A03:2021).

Test Coverage:
1. Legitimate paths (relative, absolute, nested directories)
2. Path traversal attacks (../, ../../etc/passwd)
3. Arbitrary write attempts (/tmp/evil.db)
4. Symbolic link attacks (symlink → outside project)
5. Edge cases (empty path, invalid extension)
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

# Add utils to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'utils'))

from path_validator import validate_db_path, get_validated_db_path, PathValidationError


class TestPathValidator:
    """Test suite for database path validation security."""
    
    @pytest.fixture
    def project_root(self, tmp_path):
        """
        Create temporary project root for testing.
        
        Structure:
        /tmp/project/
        ├── data/
        │   └── devstream.db
        └── subdir/
            └── nested.db
        """
        project = tmp_path / "project"
        project.mkdir()
        
        # Create data directory
        data_dir = project / "data"
        data_dir.mkdir()
        
        # Create subdirectory
        subdir = project / "subdir"
        subdir.mkdir()
        
        return str(project)
    
    def test_legitimate_relative_path(self, project_root):
        """Test legitimate relative path validation."""
        result = validate_db_path("data/devstream.db", project_root)
        
        assert result == os.path.join(project_root, "data", "devstream.db")
        assert result.endswith(".db")
        assert result.startswith(project_root)
    
    def test_legitimate_absolute_path(self, project_root):
        """Test legitimate absolute path validation."""
        absolute_path = os.path.join(project_root, "data", "devstream.db")
        result = validate_db_path(absolute_path, project_root)
        
        assert result == absolute_path
        assert result.endswith(".db")
        assert result.startswith(project_root)
    
    def test_nested_directory_path(self, project_root):
        """Test nested directory path validation."""
        result = validate_db_path("subdir/nested.db", project_root)
        
        assert result == os.path.join(project_root, "subdir", "nested.db")
        assert result.endswith(".db")
        assert result.startswith(project_root)
    
    def test_path_traversal_attack_relative(self, project_root):
        """Test path traversal attack with relative ../ sequences."""
        with pytest.raises(PathValidationError) as exc_info:
            validate_db_path("../../etc/passwd", project_root)
        
        assert "Path traversal detected" in str(exc_info.value)
        assert ".." in str(exc_info.value)
    
    def test_path_traversal_attack_absolute(self, project_root):
        """Test path traversal attack with absolute path outside project."""
        with pytest.raises(PathValidationError) as exc_info:
            validate_db_path("/etc/passwd", project_root)
        
        assert "Path outside project directory" in str(exc_info.value)
    
    def test_arbitrary_write_tmp(self, project_root):
        """Test arbitrary write attempt to /tmp."""
        with pytest.raises(PathValidationError) as exc_info:
            validate_db_path("/tmp/evil.db", project_root)
        
        assert "Path outside project directory" in str(exc_info.value)
        assert "/tmp/evil.db" in str(exc_info.value)
    
    def test_directory_traversal_canonicalization(self, project_root):
        """Test directory traversal via canonicalization."""
        with pytest.raises(PathValidationError) as exc_info:
            validate_db_path("data/../../../etc/passwd", project_root)
        
        assert "Path traversal detected" in str(exc_info.value)
    
    def test_invalid_extension(self, project_root):
        """Test invalid file extension rejection."""
        with pytest.raises(PathValidationError) as exc_info:
            validate_db_path("data/file.txt", project_root)
        
        assert "Invalid file extension" in str(exc_info.value)
        assert "extension:" in str(exc_info.value).lower()
    
    def test_empty_path(self, project_root):
        """Test empty path rejection."""
        with pytest.raises(PathValidationError) as exc_info:
            validate_db_path("", project_root)
        
        assert "cannot be empty" in str(exc_info.value).lower()
    
    def test_symbolic_link_within_project(self, project_root):
        """Test symbolic link pointing within project (allowed)."""
        # Create target file
        target = os.path.join(project_root, "data", "target.db")
        Path(target).touch()
        
        # Create symbolic link
        link = os.path.join(project_root, "data", "link.db")
        os.symlink(target, link)
        
        try:
            result = validate_db_path(link, project_root)
            
            # Should resolve to target within project
            assert result == target
            assert result.startswith(project_root)
        finally:
            # Cleanup
            if os.path.exists(link):
                os.unlink(link)
            if os.path.exists(target):
                os.unlink(target)
    
    def test_symbolic_link_outside_project(self, project_root, tmp_path):
        """Test symbolic link pointing outside project (blocked)."""
        # Create target outside project
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        target = outside_dir / "evil.db"
        target.touch()
        
        # Create symbolic link inside project
        link = os.path.join(project_root, "data", "link.db")
        os.symlink(str(target), link)
        
        try:
            with pytest.raises(PathValidationError) as exc_info:
                validate_db_path(link, project_root)
            
            assert "Path outside project directory" in str(exc_info.value)
        finally:
            # Cleanup
            if os.path.exists(link):
                os.unlink(link)
            if target.exists():
                target.unlink()
    
    def test_get_validated_db_path_from_env(self, project_root, monkeypatch):
        """Test getting validated path from environment variable."""
        monkeypatch.setenv("DEVSTREAM_DB_PATH", "data/devstream.db")
        
        result = get_validated_db_path(project_root=project_root)
        
        assert result == os.path.join(project_root, "data", "devstream.db")
        assert result.endswith(".db")
    
    def test_get_validated_db_path_default(self, project_root, monkeypatch):
        """Test getting validated path from default."""
        monkeypatch.delenv("DEVSTREAM_DB_PATH", raising=False)
        
        result = get_validated_db_path(project_root=project_root)
        
        assert result == os.path.join(project_root, "data", "devstream.db")
        assert result.endswith(".db")
    
    def test_get_validated_db_path_attack_blocked(self, project_root, monkeypatch):
        """Test attack attempt via environment variable blocked."""
        monkeypatch.setenv("DEVSTREAM_DB_PATH", "../../etc/passwd")
        
        with pytest.raises(PathValidationError) as exc_info:
            get_validated_db_path(project_root=project_root)
        
        assert "Path traversal detected" in str(exc_info.value)
    
    def test_parent_directory_validation(self, project_root):
        """Test parent directory must be within project."""
        with pytest.raises(PathValidationError) as exc_info:
            validate_db_path("data/../../outside/evil.db", project_root)
        
        assert "Path traversal detected" in str(exc_info.value)
    
    def test_nonexistent_parent_directory_within_project(self, project_root):
        """Test nonexistent parent directory within project (allowed)."""
        result = validate_db_path("newdir/database.db", project_root)
        
        # Should validate successfully (directory will be created later)
        assert result == os.path.join(project_root, "newdir", "database.db")
        assert result.startswith(project_root)
    
    def test_windows_path_validation(self, project_root):
        """Test Windows-style path validation (cross-platform)."""
        if os.name == 'nt':
            # Windows-specific test
            result = validate_db_path("data\\devstream.db", project_root)
            assert result.endswith(".db")
            assert project_root in result
        else:
            # On Unix, backslashes are valid filename characters
            # This test documents the behavior difference
            pass
    
    def test_path_with_spaces(self, project_root):
        """Test path with spaces (legitimate use case)."""
        result = validate_db_path("data dir/my database.db", project_root)
        
        assert result == os.path.join(project_root, "data dir", "my database.db")
        assert result.endswith(".db")
    
    def test_case_sensitive_extension(self, project_root):
        """Test case-sensitive extension validation."""
        # .DB (uppercase) should fail with default .db requirement
        with pytest.raises(PathValidationError) as exc_info:
            validate_db_path("data/devstream.DB", project_root)
        
        assert "Invalid file extension" in str(exc_info.value)
    
    def test_custom_extension_requirement(self, project_root):
        """Test custom extension requirement."""
        result = validate_db_path(
            "data/database.sqlite",
            project_root,
            require_extension=".sqlite"
        )
        
        assert result.endswith(".sqlite")
        assert result.startswith(project_root)
    
    def test_no_extension_requirement(self, project_root):
        """Test disabling extension requirement."""
        result = validate_db_path(
            "data/database",
            project_root,
            require_extension=None
        )
        
        assert result == os.path.join(project_root, "data", "database")
        assert result.startswith(project_root)


class TestPathValidatorIntegration:
    """Integration tests for path validator with MCP client and hook base."""
    
    def test_mcp_client_integration(self, tmp_path, monkeypatch):
        """Test path validator integration with MCP client."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        
        # Set environment
        monkeypatch.setenv("DEVSTREAM_DB_PATH", "data/devstream.db")
        monkeypatch.chdir(str(project_root))
        
        # Import MCP client (will trigger validation)
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'utils'))
        from mcp_client import DevStreamMCPClient
        
        # Should initialize successfully
        client = DevStreamMCPClient()
        assert client.db_path.endswith(".db")
        assert str(project_root) in client.db_path
    
    def test_mcp_client_attack_blocked(self, tmp_path, monkeypatch):
        """Test MCP client blocks path traversal attack."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        
        # Set malicious path
        monkeypatch.setenv("DEVSTREAM_DB_PATH", "../../etc/passwd")
        monkeypatch.chdir(str(project_root))
        
        # Import MCP client
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'utils'))
        from mcp_client import DevStreamMCPClient
        
        # Should raise PathValidationError
        with pytest.raises(Exception) as exc_info:  # PathValidationError or import error
            client = DevStreamMCPClient()
        
        # Verify security error
        assert "path" in str(exc_info.value).lower() or "traversal" in str(exc_info.value).lower()


class TestSecurityDocumentation:
    """Test security documentation and error messages."""
    
    def test_error_messages_provide_guidance(self, tmp_path):
        """Test error messages provide clear security guidance."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        
        with pytest.raises(PathValidationError) as exc_info:
            validate_db_path("../../etc/passwd", str(project_root))
        
        error_message = str(exc_info.value)
        
        # Verify error message contains:
        assert "Path traversal" in error_message  # Attack type
        assert ".." in error_message  # Problematic sequence
        assert "Valid example:" in error_message  # Guidance
    
    def test_docstring_security_notes(self):
        """Test function docstrings include security notes."""
        import inspect
        
        # Check validate_db_path docstring
        docstring = inspect.getdoc(validate_db_path)
        
        assert "Security" in docstring or "security" in docstring
        assert "attack" in docstring.lower()
        assert "traversal" in docstring.lower()
    
    def test_pathvalidationerror_docstring(self):
        """Test PathValidationError has security documentation."""
        import inspect
        
        docstring = inspect.getdoc(PathValidationError)
        
        assert "security" in docstring.lower()
        assert "attack" in docstring.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
