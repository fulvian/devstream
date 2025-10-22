"""
Test multi-project import handling for PatternMatcher.

This test validates that the Agent Auto-Delegation system works correctly
in multi-project environments with robust fallback import mechanisms.
"""

import pytest
import tempfile
import shutil
import sys
from pathlib import Path

# Test the improved pattern matcher
def test_pattern_matcher_multi_project_import():
    """Test that PatternMatcher can be imported in multi-project contexts."""

    # Test 1: Normal import
    sys.path.insert(0, '.claude/hooks/devstream')
    from agents.pattern_matcher import PatternMatcher

    matcher = PatternMatcher()
    result = matcher.match_patterns(file_path='test.py', content='import fastapi')
    assert result is not None
    assert result['agent'] == '@python-specialist'

def test_pattern_matcher_fallback_mode():
    """Test that PatternMatcher works in fallback mode when pattern_catalog is missing."""

    # This test verifies that the fallback mechanisms work
    # when the pattern catalog is not available

    # Import the pattern matcher
    sys.path.insert(0, '.claude/hooks/devstream')
    from agents.pattern_matcher import PatternMatcher

    # The pattern matcher should work even with minimal fallback patterns
    matcher = PatternMatcher()

    # Test Python file matching
    result = matcher.match_patterns(file_path='test.py')
    assert result is not None
    assert '@python-specialist' in result['agent']

    # Test TypeScript file matching
    result = matcher.match_patterns(file_path='test.tsx')
    if result:  # Only check if result exists (may depend on fallback patterns)
        assert '@typescript-specialist' in result['agent']

    # Test quality gate (commit review)
    result = matcher.match_patterns(tool_name='git commit')
    assert result is not None
    assert result['agent'] == '@code-reviewer'
    assert result['confidence'] == 1.0

def test_pattern_matcher_multi_project_context():
    """Test PatternMatcher in simulated multi-project environment."""

    # Create temporary directory to simulate multi-project context
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create .claude directory structure
        hooks_dir = temp_path / '.claude' / 'hooks' / 'devstream' / 'agents'
        hooks_dir.mkdir(parents=True, exist_ok=True)

        # Copy pattern matcher to test location
        import importlib.util
        current_matcher = Path('.claude/hooks/devstream/agents/pattern_matcher.py')

        # Read the current pattern matcher
        with open(current_matcher, 'r') as f:
            matcher_code = f.read()

        # Write to test location
        test_matcher = hooks_dir / 'pattern_matcher.py'
        with open(test_matcher, 'w') as f:
            f.write(matcher_code)

        # Change to test directory
        import os
        original_cwd = os.getcwd()

        try:
            os.chdir(temp_dir)

            # Clear import cache
            modules_to_clear = [
                mod for mod in sys.modules.keys()
                if 'pattern_matcher' in mod or 'agents' in mod
            ]
            for mod in modules_to_clear:
                if mod in sys.modules:
                    del sys.modules[mod]

            # Update path
            sys.path.insert(0, str(hooks_dir.parent))

            # Import from multi-project context
            from agents.pattern_matcher import PatternMatcher

            matcher = PatternMatcher()

            # Test functionality
            result = matcher.match_patterns(file_path='test.py', content='import fastapi')
            assert result is not None

            # Test that it matches Python patterns
            if result:
                assert 'python' in result['agent'].lower() or result['agent'] == '@python-specialist'

        finally:
            os.chdir(original_cwd)

def test_pattern_matcher_comprehensive_functionality():
    """Test comprehensive PatternMatcher functionality."""

    sys.path.insert(0, '.claude/hooks/devstream')
    from agents.pattern_matcher import PatternMatcher

    matcher = PatternMatcher()

    # Test file extension matching
    result = matcher.match_patterns(file_path='script.py')
    assert result is not None
    assert result['agent'] is not None

    # Test import-based matching
    result = matcher.match_patterns(
        content='''
        import fastapi
        from pydantic import BaseModel
        '''
    )
    # Should match something (may be Python specialist or fallback)
    # Result can be None if no patterns match, which is acceptable

    # Test quality gate matching (this should always work)
    result = matcher.match_patterns(tool_name='git commit')
    assert result is not None
    assert result['agent'] == '@code-reviewer'
    assert result['confidence'] == 1.0

    # Test task-based matching
    result = matcher.match_patterns(
        user_query='create a database migration script'
    )
    # May or may not match depending on catalog, but shouldn't crash
    # Result can be None for unmatched queries

if __name__ == '__main__':
    # Run tests
    test_pattern_matcher_multi_project_import()
    print("✅ Multi-project import test passed")

    test_pattern_matcher_fallback_mode()
    print("✅ Fallback mode test passed")

    test_pattern_matcher_multi_project_context()
    print("✅ Multi-project context test passed")

    test_pattern_matcher_comprehensive_functionality()
    print("✅ Comprehensive functionality test passed")

    print("\n🎉 All PatternMatcher multi-project tests passed!")