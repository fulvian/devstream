#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cchooks>=0.1.4",
#     "structlog>=23.0.0",
#     "aiosqlite>=0.19.0",
# ]
# ///
"""Task hook entry point delegating to the shared SessionStart adapter."""

from __future__ import annotations

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / ".claude"))

from hooks.devstream.sessions.session_start import run_main


if __name__ == "__main__":
    run_main()

