"""
Pytest configuration for agent delegation tests.

Provides fixtures and setup specific to agent delegation testing.
"""

import pytest
import sys
from pathlib import Path

# Add .claude/hooks to sys.path for importing devstream modules
project_root = Path(__file__).parent.parent.parent.parent
hooks_dir = project_root / ".claude" / "hooks"
if str(hooks_dir) not in sys.path:
    sys.path.insert(0, str(hooks_dir))
