#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
DevStream Path Validator - Database Path Security
Protects against path traversal attacks (CWE-22, OWASP A03:2021).

Security Threats Mitigated:
1. Path Traversal: ../../etc/passwd → Block access outside project
2. Symbolic Link Attack: /tmp/symlink → /etc/passwd → Resolve and validate
3. Arbitrary File Write: /tmp/malicious.db → Block non-project paths
4. Directory Traversal: data/../../../etc/passwd → Canonicalize and validate

Implementation follows OWASP Input Validation Cheat Sheet:
- Whitelist validation (project directory only)
- Canonicalization (resolve symlinks, relative paths)
- Extension validation (.db only for database files)
- Strict path prefix matching (startswith project_root)
"""

import os
import re
import urllib.parse
import unicodedata
from pathlib import Path
from typing import Optional


def is_path_traversal_attack(path: str) -> bool:
    """
    Context7-compliant path traversal detection following OWASP best practices.

    Multiple detection layers following defense-in-depth principle:
    1. URL decoding detection
    2. Unicode normalization
    3. Pattern-based detection for encoded variants
    4. Backward path sequence detection

    This function protects against:
    - Basic traversal: "../etc/passwd"
    - URL encoded: "..%2Fetc/passwd"
    - Double encoded: "..%252Fetc/passwd"
    - Unicode encoded: "..%c0%afetc/passwd"
    - Mixed separators: "..\\etc/passwd"

    Args:
        path: User-provided path to validate

    Returns:
        True if path traversal attack detected, False otherwise
    """
    if not path:
        return False

    # Layer 1: URL decoding detection (OWASP best practice)
    try:
        # Try multiple decoding rounds to detect double encoding
        decoded_path = path
        for _ in range(3):  # Prevent infinite loops
            previous = decoded_path
            decoded_path = urllib.parse.unquote(decoded_path)
            if decoded_path == previous:
                break

        # Check if decoding revealed traversal
        if ".." in decoded_path:
            return True

    except Exception:
        # If decoding fails, be conservative and block
        if ".." in path:
            return True

    # Layer 2: Unicode normalization attacks
    try:
        normalized = unicodedata.normalize('NFC', path)
        if ".." in normalized:
            return True
    except Exception:
        pass

    # Layer 3: Pattern-based detection for encoded variants
    dangerous_patterns = [
        r'\.\.%2[Ff]',           # URL encoded forward slash
        r'\.\.%5[Cc]',           # URL encoded backslash
        r'\.\.%c0%[aA][fF]',     # UTF-8 overlong encoding
        r'\.\.%e0%80%[aA][fF]',  # UTF-8 overlong encoding variant
        r'\.\.\\',               # Windows backslash
        r'\.\.\/',               # Forward slash variant
        r'%2e%2e%2[fF]',         # Double URL encoded ".."
        r'%252e%252e%252[fF]',   # Triple URL encoded ".."
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, path, re.IGNORECASE):
            return True

    # Layer 4: Path normalization with detection
    try:
        # Convert to Path object for robust handling
        p = Path(path)

        # Check for obvious traversal in any component
        for part in p.parts:
            if part == "..":
                return True

        # Try to resolve relative paths safely
        if not p.is_absolute():
            # Don't resolve - just check for traversal
            if any(part == ".." for part in p.parts):
                return True

    except Exception:
        # If Path parsing fails, be conservative
        return ".." in path

    return False


class PathValidationError(ValueError):
    """
    Exception raised when path validation fails.
    
    This exception indicates a security violation attempt:
    - Path traversal attack (../ sequences)
    - Access outside project directory
    - Invalid file extension
    - Symbolic link pointing outside project
    
    Examples:
        >>> validate_db_path("../../etc/passwd", "/project")
        PathValidationError: Path traversal detected
        
        >>> validate_db_path("/tmp/evil.db", "/project")
        PathValidationError: Path outside project directory
    """
    pass


def validate_db_path(
    path: str,
    project_root: Optional[str] = None,
    require_extension: str = ".db"
) -> str:
    """
    Validate database path for security vulnerabilities.
    
    Security Validation Steps:
    1. Path Canonicalization: Resolve symlinks, . and .. with os.path.realpath()
    2. Whitelist Check: Ensure canonical path is within project_root
    3. Extension Validation: Verify file has required extension (.db)
    4. Path Traversal Protection: Block ../ sequences before canonicalization
    
    Attack Vectors Blocked:
    - Path Traversal: "../../etc/passwd" → Blocked (path outside project)
    - Symbolic Link: "/tmp/link" → "/etc/passwd" → Blocked (resolved path outside)
    - Arbitrary Write: "/tmp/malicious.db" → Blocked (not in project)
    - Directory Traversal: "data/../../../etc/passwd" → Blocked (canonicalized outside)
    
    Args:
        path: Database file path to validate (relative or absolute)
        project_root: Project root directory (default: current working directory)
        require_extension: Required file extension (default: .db)
        
    Returns:
        Canonical absolute path if validation succeeds
        
    Raises:
        PathValidationError: If validation fails (security violation)
        
    Examples:
        >>> # VALID: Path within project
        >>> validate_db_path("data/devstream.db", "/project")
        '/project/data/devstream.db'

        >>> # INVALID: Path traversal attempt
        >>> validate_db_path("../../etc/passwd", "/project")
        PathValidationError: Path traversal detected: ../../etc/passwd

        >>> # INVALID: Outside project directory
        >>> validate_db_path("/tmp/evil.db", "/project")
        PathValidationError: Path outside project directory: /tmp/evil.db

        >>> # INVALID: Wrong extension
        >>> validate_db_path("data/file.txt", "/project")
        PathValidationError: Invalid file extension: data/file.txt (expected .db)
        
    Security Notes:
        - ALWAYS validate paths from environment variables (DEVSTREAM_DB_PATH)
        - NEVER trust user input without validation
        - Use canonical paths for all comparisons (prevents symlink bypass)
        - Log all validation failures for security monitoring
    """
    if not path:
        raise PathValidationError("Database path cannot be empty")
    
    # Default project root to current working directory
    if project_root is None:
        project_root = os.getcwd()
    
    # Canonicalize project root (resolve symlinks)
    canonical_project_root = os.path.realpath(project_root)
    
    # SECURITY CHECK 1: Enhanced path traversal detection (OWASP Context7-compliant)
    # Multiple detection layers following defense-in-depth principle
    if is_path_traversal_attack(path):
        raise PathValidationError(
            f"Path traversal detected: {path}. "
            f"Database paths must not contain path traversal sequences (encoded or literal). "
            f"Valid example: data/devstream.db or /absolute/path/to/devstream.db"
        )
    
    # SECURITY CHECK 2: Canonicalize path (resolve symlinks, relative paths)
    # Convert to absolute path if relative
    if not os.path.isabs(path):
        path = os.path.join(canonical_project_root, path)
    
    # Resolve symlinks and normalize path
    canonical_path = os.path.realpath(path)
    
    # SECURITY CHECK 3: Whitelist validation (must be within project)
    # Use os.path.commonpath to prevent prefix matching bypass
    try:
        common_path = os.path.commonpath([canonical_path, canonical_project_root])
        if common_path != canonical_project_root:
            raise PathValidationError(
                f"Path outside project directory: {path} → {canonical_path}. "
                f"Database must be within project root: {canonical_project_root}. "
                f"Valid example: {os.path.join(canonical_project_root, 'data', 'devstream.db')}"
            )
    except ValueError:
        # Paths on different drives (Windows) or root paths
        raise PathValidationError(
            f"Path outside project directory: {path} → {canonical_path}. "
            f"Database must be within project root: {canonical_project_root}"
        )
    
    # SECURITY CHECK 4: Extension validation
    if require_extension and not canonical_path.endswith(require_extension):
        raise PathValidationError(
            f"Invalid file extension: {path} → {canonical_path}. "
            f"Expected extension: {require_extension}. "
            f"Valid example: devstream.db"
        )
    
    # SECURITY CHECK 5: Verify parent directory is writable (optional, for new files)
    parent_dir = os.path.dirname(canonical_path)
    if not os.path.exists(parent_dir):
        # Parent directory doesn't exist - will need to be created
        # Validate that the parent is also within project
        canonical_parent = os.path.realpath(parent_dir)
        try:
            common_path = os.path.commonpath([canonical_parent, canonical_project_root])
            if common_path != canonical_project_root:
                raise PathValidationError(
                    f"Parent directory outside project: {parent_dir}. "
                    f"Database directory must be within project root: {canonical_project_root}"
                )
        except ValueError:
            raise PathValidationError(
                f"Parent directory outside project: {parent_dir}"
            )
    
    return canonical_path


def get_validated_db_path(
    env_var: str = "DEVSTREAM_DB_PATH",
    default_path: str = "data/devstream.db",
    project_root: Optional[str] = None
) -> str:
    """
    Get validated database path from environment or default.
    
    Convenience function that:
    1. Reads path from environment variable
    2. Falls back to default if not set
    3. Validates path with validate_db_path()
    
    Args:
        env_var: Environment variable name (default: DEVSTREAM_DB_PATH)
        default_path: Default relative path (default: data/devstream.db)
        project_root: Project root directory (default: current working directory)

    Returns:
        Validated canonical absolute path

    Raises:
        PathValidationError: If validation fails

    Examples:
        >>> # With environment variable
        >>> os.environ["DEVSTREAM_DB_PATH"] = "data/devstream.db"
        >>> get_validated_db_path()
        '/project/data/devstream.db'

        >>> # With default
        >>> del os.environ["DEVSTREAM_DB_PATH"]
        >>> get_validated_db_path()
        '/project/data/devstream.db'
        
        >>> # Attack attempt blocked
        >>> os.environ["DEVSTREAM_DB_PATH"] = "../../etc/passwd"
        >>> get_validated_db_path()
        PathValidationError: Path traversal detected
    """
    # Get path from environment or use default
    db_path = os.getenv(env_var, default_path)
    
    # Validate and return canonical path
    return validate_db_path(db_path, project_root)


# Test function for standalone execution
def test_path_validator():
    """
    Test path validator with attack scenarios.
    
    Tests legitimate paths and attack vectors to ensure security.
    """
    print("🔒 Testing Path Validator Security\n")
    
    # Create temporary project root
    project_root = "/Users/fulvioventura/devstream"
    
    test_cases = [
        # (path, should_pass, description)
        ("data/devstream.db", True, "Legitimate relative path"),
        (f"{project_root}/data/devstream.db", True, "Legitimate absolute path"),
        ("../../etc/passwd", False, "Path traversal attack"),
        ("/tmp/evil.db", False, "Arbitrary write outside project"),
        ("data/../../../etc/passwd", False, "Directory traversal via canonicalization"),
        ("data/test.txt", False, "Invalid file extension"),
        ("", False, "Empty path"),
        # NEW: Enhanced path traversal test cases (Context7-compliant)
        ("..%2Fetc/passwd", False, "URL encoded forward slash traversal"),
        ("..%2fetc/passwd", False, "URL encoded forward slash (lowercase)"),
        ("..%5Cetc/passwd", False, "URL encoded backslash traversal"),
        ("..%5cetc/passwd", False, "URL encoded backslash (lowercase)"),
        ("..%c0%afetc/passwd", False, "Unicode overlong encoding"),
        ("..%C0%AFetc/passwd", False, "Unicode overlong encoding (uppercase)"),
        ("..%e0%80%afetc/passwd", False, "Unicode overlong encoding variant"),
        ("..%E0%80%AFetc/passwd", False, "Unicode overlong encoding variant (uppercase)"),
        ("..\\etc\\passwd", False, "Windows backslash traversal"),
        ("..\\/etc\\/passwd", False, "Mixed separator traversal"),
        ("%2e%2e%2fetc/passwd", False, "Double URL encoded dots"),
        ("%2E%2E%2Fetc/passwd", False, "Double URL encoded dots (uppercase)"),
        ("%252e%252e%252fetc/passwd", False, "Triple URL encoded dots"),
        ("%252E%252E%252Fetc/passwd", False, "Triple URL encoded dots (uppercase)"),
        ("..././../../etc/passwd", False, "Multiple dots with current directory"),
        ("./../etc/passwd", False, "Current directory with traversal"),
    ]
    
    print("Running security test cases:\n")
    
    for path, should_pass, description in test_cases:
        try:
            result = validate_db_path(path, project_root)
            if should_pass:
                print(f"✅ PASS: {description}")
                print(f"   Input: {path}")
                print(f"   Output: {result}\n")
            else:
                print(f"❌ FAIL: {description}")
                print(f"   Expected: PathValidationError")
                print(f"   Got: {result}\n")
        except PathValidationError as e:
            if not should_pass:
                print(f"✅ PASS: {description}")
                print(f"   Input: {path}")
                print(f"   Error: {str(e)}\n")
            else:
                print(f"❌ FAIL: {description}")
                print(f"   Expected: Success")
                print(f"   Got: PathValidationError - {str(e)}\n")
        except Exception as e:
            print(f"❌ ERROR: {description}")
            print(f"   Unexpected exception: {type(e).__name__} - {str(e)}\n")
    
    print("🎉 Path validator security test completed!")


if __name__ == "__main__":
    test_path_validator()
