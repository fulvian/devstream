"""
Test file for debugging embedding generation.

This file should be captured by PostToolUse hook because it's a .py file.
"""

def test_embedding():
    """Test function to verify PostToolUse hook captures this file."""
    print("Testing embedding generation with debug logging - EDITED")
    print("This edit should trigger PostToolUse hook")
    return True

if __name__ == "__main__":
    test_embedding()
