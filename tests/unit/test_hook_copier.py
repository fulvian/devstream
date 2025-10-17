"""
Tests for Copier library integration in DevStream hook copying system.
"""

import pytest
import sys
from pathlib import Path


def test_copier_installation():
    """Test that Copier library is properly installed and importable."""
    try:
        import copier
        assert hasattr(copier, '__version__'), "Copier should have __version__ attribute"
        assert copier.__version__ >= "9.0.0", f"Copier version should be >= 9.0.0, got {copier.__version__}"
    except ImportError as e:
        pytest.fail(f"Copier library import failed: {e}")


def test_copier_basic_functionality():
    """Test basic Copier functionality is available."""
    try:
        import copier
        # Test that key functions exist
        assert hasattr(copier, 'run_copy'), "Copier should have run_copy function"
        assert hasattr(copier, 'errors'), "Copier should have errors module"

        # Test version validation
        version_parts = copier.__version__.split('.')
        assert len(version_parts) >= 2, "Version should have at least major.minor parts"
        assert version_parts[0] == '9', f"Major version should be 9, got {version_parts[0]}"

    except ImportError as e:
        pytest.fail(f"Copier library import failed: {e}")
    except Exception as e:
        pytest.fail(f"Copier functionality test failed: {e}")


def test_copier_error_classes():
    """Test that Copier error classes are available for proper error handling."""
    try:
        import copier
        from copier.errors import CopierError

        # Test error class hierarchy
        assert issubclass(CopierError, Exception), "CopierError should be an Exception subclass"

        # Check for other common error types
        assert hasattr(copier.errors, 'CopierError'), "copier.errors should have CopierError"
        assert hasattr(copier.errors, 'ExtensionNotFoundError'), "copier.errors should have ExtensionNotFoundError"

    except ImportError as e:
        pytest.fail(f"Copier library import failed: {e}")
    except Exception as e:
        pytest.fail(f"Copier error class test failed: {e}")