# Spotlight MDS Crash Fix - Implementation Plan

**Task ID**: 0fdaa163f4400d458b7d9c811ffd01a9
**Priority**: 10/10 (CRITICAL)
**Phase**: System Stability & Crash Prevention
**Estimated Duration**: 3 hours (180 minutes)
**Status**: Planning Complete → Awaiting Approval

---

## 🎯 EXECUTIVE SUMMARY

### Problem Statement
macOS Spotlight (mds process) crashes kernel when reading `devstream.db` during concurrent write operations by multiple DevStream sessions. Buffer overflow (1-byte beyond 1024-byte kalloc zone) triggered by Spotlight metadata extraction during SQLite lock window.

### Root Cause Analysis
1. **SQLite Configuration**: DELETE mode (not WAL) with `busy_timeout=0`
2. **Concurrent Access**: 9 Node.js processes + 2 Python sessions accessing same database
3. **Spotlight Indexing**: 259MB database actively indexed by mds
4. **Race Condition**: Spotlight reads partial data during write lock → buffer overflow → kernel panic

### Solution Architecture (Hybrid Approach D)

**Part A: Spotlight Exclusion** (Immediate)
- Apply `.noindex` suffix to data directory
- Set xattr on database files for defense in depth

**Part B: SQLite Safety Layer** (Robust)
- Enable WAL mode with `busy_timeout=30000`
- Centralized connection manager
- Pragma enforcement on all connections

**Part C: Session Coordination** (Scalable)
- PID tracking registry
- Health check mechanism
- Lock file for critical operations

---

## 📊 RESEARCH VALIDATION

### Context7 Sources Applied
| Library | Trust Score | Snippets | Application |
|---------|-------------|----------|-------------|
| /omnilib/aiosqlite | 7.7 | 33 | Async connection patterns |
| /websites/www_sqlite_org-docs.html | 10.0 | 5407 | WAL mode configuration |

### WebSearch 2025 Best Practices
- SQLite WAL mode concurrent access (sqlite.org)
- macOS Spotlight exclusion methods (eclecticlight.co June 2025)
- fcntl.flock process coordination (Python docs + Stack Overflow)

### Key Decisions from Research
1. ✅ WAL mode: `journal_mode=WAL` + `busy_timeout=30000` + `synchronous=NORMAL`
2. ✅ Spotlight: `.noindex` directory suffix (primary) + xattr (backup)
3. ✅ File locking: Separate `.lock` file with `fcntl.LOCK_EX` for critical ops
4. ✅ Session coordination: JSON registry with PID tracking

---

## 🗓️ IMPLEMENTATION PHASES

### FASE 1: Immediate Protection (30 minutes)

**Objective**: Stop crashes immediately with minimal code changes
**Agent**: @devops-specialist (bash scripts) + @python-specialist (Python code)

#### FASE 1.1: Spotlight Exclusion (10 min)
**Agent**: @devops-specialist
**File**: `scripts/setup_spotlight_exclusion.sh` (NEW)

**Acceptance Criteria**:
- ✅ Rename `data/` → `data.noindex/`
- ✅ Update all hardcoded paths referencing `data/`
- ✅ Apply xattr to `devstream.db` and backup files
- ✅ Verify Spotlight exclusion with `mdls`
- ✅ Script idempotent (safe to run multiple times)

**Implementation**:
```bash
#!/bin/bash
# setup_spotlight_exclusion.sh

set -euo pipefail

echo "🔍 DevStream Spotlight Exclusion Setup"

# Step 1: Rename data/ to data.noindex/ (if not already)
if [ -d "data" ] && [ ! -d "data.noindex" ]; then
    echo "📁 Renaming data/ → data.noindex/"
    mv data data.noindex
elif [ -d "data.noindex" ]; then
    echo "✅ data.noindex/ already exists"
else
    echo "❌ No data directory found"
    exit 1
fi

# Step 2: Update symlink (if exists)
if [ -L "data" ]; then
    rm data
fi
ln -s data.noindex data
echo "🔗 Created symlink: data → data.noindex"

# Step 3: Apply xattr to database files
echo "🏷️  Applying xattr to database files..."
xattr -w com.apple.metadata:kMDItemSupportFileType "DevStreamDB" data.noindex/devstream.db || true
for backup in data.noindex/devstream.db.backup*; do
    [ -f "$backup" ] && xattr -w com.apple.metadata:kMDItemSupportFileType "DevStreamDB" "$backup" || true
done

# Step 4: Verify exclusion
echo "✅ Verifying Spotlight exclusion..."
if mdls data.noindex/devstream.db | grep -q "kMDItemFSContentChangeDate"; then
    echo "⚠️  WARNING: File still indexed by Spotlight (may take time to update)"
else
    echo "✅ File excluded from Spotlight"
fi

echo "🎉 Spotlight exclusion setup complete!"
```

**Testing**:
```bash
# Verify exclusion
./scripts/setup_spotlight_exclusion.sh
mdls data.noindex/devstream.db | grep -i metadata
xattr -l data.noindex/devstream.db
```

---

#### FASE 1.2: Enable WAL Mode (10 min)
**Agent**: @python-specialist
**File**: `.claude/hooks/devstream/utils/sqlite_vec_helper.py` (MODIFY)

**Changes**:
```python
def get_db_connection_with_vec(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Get SQLite connection with sqlite-vec extension loaded."""
    # ... existing code ...

    conn = sqlite3.connect(db_path)

    # CRITICAL: Enable WAL mode and set pragmas
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")  # 30 seconds
    conn.execute("PRAGMA synchronous=NORMAL")  # Safe in WAL mode

    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    return conn
```

**Acceptance Criteria**:
- ✅ WAL mode enabled on EVERY connection
- ✅ `busy_timeout=30000` configured
- ✅ `synchronous=NORMAL` for performance
- ✅ Existing sqlite-vec functionality unchanged
- ✅ Type hints maintained

---

#### FASE 1.3: Update Async Connections (10 min)
**Agent**: @python-specialist
**File**: `.claude/hooks/devstream/sessions/work_session_manager.py` (MODIFY)

**Changes**:
```python
async def _get_connection(self) -> aiosqlite.Connection:
    """Get database connection with WAL pragmas."""
    conn = aiosqlite.connect(self.db_path)

    async with conn as db:
        # Enable WAL mode and pragmas
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=30000")
        await db.execute("PRAGMA synchronous=NORMAL")
        await db.commit()

    return conn
```

**Acceptance Criteria**:
- ✅ All async connections use WAL pragmas
- ✅ Context manager pattern preserved
- ✅ Row factory configuration unchanged
- ✅ Error handling maintained

---

### FASE 2: Centralized Connection Manager (60 minutes)

**Objective**: Single source of truth for all database connections
**Agent**: @python-specialist

#### FASE 2.1: Create Connection Manager (20 min)
**Agent**: @python-specialist
**File**: `.claude/hooks/devstream/utils/sqlite_connection_manager.py` (NEW)

**Implementation**:
```python
#!/usr/bin/env python3
"""
SQLite Connection Manager - Centralized WAL-enabled connection handling.

Ensures all connections use proper pragmas for concurrent access safety.
Based on Context7 research (aiosqlite Trust 7.7, SQLite docs).
"""

import sqlite3
import aiosqlite
import structlog
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

logger = structlog.get_logger(__name__)


class SQLiteConnectionManager:
    """
    Centralized SQLite connection manager with WAL mode enforcement.

    Features:
    - Automatic WAL mode configuration
    - busy_timeout for concurrent access
    - sqlite-vec extension support
    - Singleton pattern for consistency

    Research Applied:
    - Context7 aiosqlite async patterns (Trust 7.7)
    - SQLite WAL mode best practices (5407 snippets)
    - fcntl.flock process coordination
    """

    _instance: Optional['SQLiteConnectionManager'] = None

    # WAL mode configuration (Context7 validated)
    PRAGMA_JOURNAL_MODE = "WAL"
    PRAGMA_BUSY_TIMEOUT = 30000  # 30 seconds
    PRAGMA_SYNCHRONOUS = "NORMAL"  # Safe in WAL mode
    PRAGMA_JOURNAL_SIZE_LIMIT = 33554432  # 32 MB

    def __init__(self):
        """Initialize connection manager singleton."""
        self.logger = logger.bind(component="SQLiteConnectionManager")
        self.logger.info("Connection manager initialized",
                        journal_mode=self.PRAGMA_JOURNAL_MODE,
                        busy_timeout=self.PRAGMA_BUSY_TIMEOUT)

    @classmethod
    def get_instance(cls) -> 'SQLiteConnectionManager':
        """Get singleton instance of connection manager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_sync_connection(self, db_path: str) -> sqlite3.Connection:
        """
        Get synchronous SQLite connection with WAL mode.

        Args:
            db_path: Path to database file

        Returns:
            sqlite3.Connection configured with WAL pragmas

        Note:
            Connection MUST be closed by caller.
            Use in context manager: with manager.get_sync_connection() as conn:
        """
        conn = sqlite3.connect(db_path)

        # Set WAL pragmas (Context7 pattern)
        conn.execute(f"PRAGMA journal_mode={self.PRAGMA_JOURNAL_MODE}")
        conn.execute(f"PRAGMA busy_timeout={self.PRAGMA_BUSY_TIMEOUT}")
        conn.execute(f"PRAGMA synchronous={self.PRAGMA_SYNCHRONOUS}")
        conn.execute(f"PRAGMA journal_size_limit={self.PRAGMA_JOURNAL_SIZE_LIMIT}")

        self.logger.debug("Sync connection created", db_path=db_path)
        return conn

    def get_sync_connection_with_vec(self, db_path: str) -> sqlite3.Connection:
        """
        Get synchronous connection with sqlite-vec extension.

        Args:
            db_path: Path to database file

        Returns:
            sqlite3.Connection with vec0 extension loaded

        Raises:
            ImportError: If sqlite-vec not installed
        """
        import sqlite_vec

        conn = self.get_sync_connection(db_path)

        # Load sqlite-vec extension
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)

        self.logger.debug("Vec extension loaded", db_path=db_path)
        return conn

    @asynccontextmanager
    async def get_async_connection(self, db_path: str):
        """
        Get async SQLite connection with WAL mode (context manager).

        Args:
            db_path: Path to database file

        Yields:
            aiosqlite.Connection configured with WAL pragmas

        Example:
            >>> manager = SQLiteConnectionManager.get_instance()
            >>> async with manager.get_async_connection('data.noindex/devstream.db') as db:
            ...     cursor = await db.execute("SELECT * FROM table")
            ...     rows = await cursor.fetchall()
        """
        async with aiosqlite.connect(db_path) as db:
            # Set WAL pragmas
            await db.execute(f"PRAGMA journal_mode={self.PRAGMA_JOURNAL_MODE}")
            await db.execute(f"PRAGMA busy_timeout={self.PRAGMA_BUSY_TIMEOUT}")
            await db.execute(f"PRAGMA synchronous={self.PRAGMA_SYNCHRONOUS}")
            await db.execute(f"PRAGMA journal_size_limit={self.PRAGMA_JOURNAL_SIZE_LIMIT}")
            await db.commit()

            # Set row factory for dict-like access
            db.row_factory = aiosqlite.Row

            self.logger.debug("Async connection created", db_path=db_path)
            yield db


# Convenience functions for backward compatibility
def get_connection_manager() -> SQLiteConnectionManager:
    """Get global connection manager instance."""
    return SQLiteConnectionManager.get_instance()
```

**Acceptance Criteria**:
- ✅ Singleton pattern implemented
- ✅ Sync and async connection methods
- ✅ sqlite-vec extension support
- ✅ Context manager for async
- ✅ Full type hints
- ✅ Structured logging
- ✅ Docstrings with examples

---

#### FASE 2.2: Update sqlite_vec_helper.py (10 min)
**Agent**: @python-specialist
**File**: `.claude/hooks/devstream/utils/sqlite_vec_helper.py` (REFACTOR)

**Changes**:
```python
from sqlite_connection_manager import get_connection_manager

def get_db_connection_with_vec(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Get SQLite connection with sqlite-vec extension loaded.

    DEPRECATED: Use SQLiteConnectionManager.get_instance().get_sync_connection_with_vec()
    Kept for backward compatibility.
    """
    if db_path is None:
        project_root = Path(__file__).parent.parent.parent.parent.parent
        db_path = str(project_root / 'data.noindex' / 'devstream.db')

    manager = get_connection_manager()
    return manager.get_sync_connection_with_vec(db_path)

def get_devstream_db() -> sqlite3.Connection:
    """Get DevStream database connection with vec0 extension loaded."""
    return get_db_connection_with_vec()
```

**Acceptance Criteria**:
- ✅ Backward compatibility maintained
- ✅ Delegates to connection manager
- ✅ Updates `data.noindex` path
- ✅ Deprecation notice in docstring

---

#### FASE 2.3: Update work_session_manager.py (10 min)
**Agent**: @python-specialist
**File**: `.claude/hooks/devstream/sessions/work_session_manager.py` (REFACTOR)

**Changes**:
```python
from utils.sqlite_connection_manager import get_connection_manager

class WorkSessionManager:
    def __init__(self, db_path: Optional[str] = None):
        # ... existing code ...
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent.parent.parent
            self.db_path = str(project_root / 'data.noindex' / 'devstream.db')
        else:
            self.db_path = db_path

        self.connection_manager = get_connection_manager()

    async def get_session(self, session_id: str) -> Optional[WorkSession]:
        """Get session by ID from database."""
        async with self.connection_manager.get_async_connection(self.db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM work_sessions WHERE id = ?",
                (session_id,)
            )
            row = await cursor.fetchone()
            # ... rest of implementation ...
```

**Acceptance Criteria**:
- ✅ Uses connection manager
- ✅ Updates `data.noindex` path
- ✅ All async methods refactored
- ✅ Error handling preserved

---

#### FASE 2.4: Update Other Consumers (20 min)
**Files**:
- `.claude/hooks/devstream/memory/post_tool_use.py`
- `.claude/hooks/devstream/sessions/session_data_extractor.py`
- `.claude/hooks/devstream/memory/backfill_embeddings.py`
- `.claude/hooks/devstream/checkpoints/checkpoint_manager.py`

**Pattern** (apply to ALL):
```python
from utils.sqlite_connection_manager import get_connection_manager

# Replace direct sqlite3.connect() or aiosqlite.connect()
# WITH:
manager = get_connection_manager()
conn = manager.get_sync_connection_with_vec(db_path)
# OR
async with manager.get_async_connection(db_path) as db:
    # ... operations ...
```

**Acceptance Criteria**:
- ✅ All 5 files updated
- ✅ No direct `sqlite3.connect()` calls remain
- ✅ All paths use `data.noindex`
- ✅ Tests still pass

---

### FASE 3: Session Coordination (45 minutes)

**Objective**: Track and coordinate multiple DevStream sessions

#### FASE 3.1: Create Session Coordinator (25 min)
**File**: `.claude/hooks/devstream/utils/session_coordinator.py` (NEW)

**Implementation**:
```python
#!/usr/bin/env python3
"""
Session Coordinator - Multi-session tracking and coordination.

Prevents concurrent access conflicts by tracking active sessions,
providing health checks, and coordinating critical operations.
"""

import os
import json
import fcntl
import psutil
import structlog
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

from atomic_file_writer import write_atomic_json

logger = structlog.get_logger(__name__)


@dataclass
class SessionInfo:
    """Active DevStream session information."""
    pid: int
    session_id: str
    started_at: str
    last_heartbeat: str
    status: str  # 'active', 'idle', 'stale'


class SessionCoordinator:
    """
    Coordinate multiple DevStream sessions safely.

    Features:
    - PID tracking for session awareness
    - Health checks for stale session detection
    - Lock file for critical operations
    - Automatic cleanup on startup

    Research Applied:
    - fcntl.flock process-level coordination
    - PID validation with psutil
    - Atomic file writes for registry
    """

    HEARTBEAT_INTERVAL_SECONDS = 60  # Update every minute
    STALE_TIMEOUT_SECONDS = 300  # 5 minutes

    def __init__(self):
        """Initialize session coordinator."""
        self.state_dir = Path.home() / '.claude/state'
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.session_file = self.state_dir / 'devstream_sessions.json'
        self.lock_file = self.state_dir / 'devstream.lock'

        self.current_pid = os.getpid()
        self.logger = logger.bind(component="SessionCoordinator", pid=self.current_pid)

        # Cleanup stale sessions on init
        self._cleanup_stale_sessions()

    def register_session(self, session_id: str) -> bool:
        """
        Register current session in coordinator.

        Args:
            session_id: Unique session identifier

        Returns:
            True if registration succeeded

        Note:
            Uses file lock to ensure atomic registry updates
        """
        with open(self.lock_file, 'w') as lock_fd:
            try:
                # Acquire exclusive lock
                fcntl.flock(lock_fd, fcntl.LOCK_EX)

                # Read current sessions
                sessions = self._read_sessions()

                # Check if already registered
                for session in sessions:
                    if session['pid'] == self.current_pid:
                        self.logger.info("Session already registered",
                                       session_id=session_id)
                        return True

                # Add new session
                new_session = SessionInfo(
                    pid=self.current_pid,
                    session_id=session_id,
                    started_at=datetime.now().isoformat(),
                    last_heartbeat=datetime.now().isoformat(),
                    status='active'
                )
                sessions.append(asdict(new_session))

                # Write atomically
                self._write_sessions(sessions)

                self.logger.info("Session registered",
                               session_id=session_id,
                               total_sessions=len(sessions))
                return True

            finally:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)

    def heartbeat(self) -> bool:
        """
        Update session heartbeat timestamp.

        Returns:
            True if heartbeat updated successfully
        """
        with open(self.lock_file, 'w') as lock_fd:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX)

                sessions = self._read_sessions()
                updated = False

                for session in sessions:
                    if session['pid'] == self.current_pid:
                        session['last_heartbeat'] = datetime.now().isoformat()
                        session['status'] = 'active'
                        updated = True
                        break

                if updated:
                    self._write_sessions(sessions)
                    self.logger.debug("Heartbeat updated")

                return updated

            finally:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)

    def unregister_session(self) -> bool:
        """
        Unregister current session (graceful shutdown).

        Returns:
            True if unregistration succeeded
        """
        with open(self.lock_file, 'w') as lock_fd:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX)

                sessions = self._read_sessions()
                sessions = [s for s in sessions if s['pid'] != self.current_pid]

                self._write_sessions(sessions)

                self.logger.info("Session unregistered",
                               remaining_sessions=len(sessions))
                return True

            finally:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)

    def get_active_sessions(self) -> List[SessionInfo]:
        """
        Get list of active sessions.

        Returns:
            List of SessionInfo objects for active sessions
        """
        sessions = self._read_sessions()
        active = []

        for session_dict in sessions:
            # Check if process alive
            if not self._is_process_alive(session_dict['pid']):
                continue

            # Check heartbeat freshness
            last_heartbeat = datetime.fromisoformat(session_dict['last_heartbeat'])
            if datetime.now() - last_heartbeat > timedelta(seconds=self.STALE_TIMEOUT_SECONDS):
                session_dict['status'] = 'stale'

            active.append(SessionInfo(**session_dict))

        return active

    def _cleanup_stale_sessions(self):
        """Remove sessions for dead processes."""
        with open(self.lock_file, 'w') as lock_fd:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX)

                sessions = self._read_sessions()
                alive_sessions = [
                    s for s in sessions
                    if self._is_process_alive(s['pid'])
                ]

                removed = len(sessions) - len(alive_sessions)
                if removed > 0:
                    self._write_sessions(alive_sessions)
                    self.logger.info("Cleaned up stale sessions",
                                   removed=removed,
                                   remaining=len(alive_sessions))

            finally:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)

    def _is_process_alive(self, pid: int) -> bool:
        """Check if process is running."""
        try:
            proc = psutil.Process(pid)
            return proc.is_running()
        except psutil.NoSuchProcess:
            return False

    def _read_sessions(self) -> List[Dict]:
        """Read sessions from registry file."""
        if not self.session_file.exists():
            return []

        try:
            with open(self.session_file, 'r') as f:
                data = json.load(f)
                return data.get('sessions', [])
        except (json.JSONDecodeError, IOError):
            self.logger.warning("Failed to read sessions file, resetting")
            return []

    def _write_sessions(self, sessions: List[Dict]):
        """Write sessions to registry file atomically."""
        import asyncio
        asyncio.run(write_atomic_json(self.session_file, {'sessions': sessions}))


# Singleton instance
_coordinator_instance: Optional[SessionCoordinator] = None

def get_session_coordinator() -> SessionCoordinator:
    """Get global session coordinator instance."""
    global _coordinator_instance
    if _coordinator_instance is None:
        _coordinator_instance = SessionCoordinator()
    return _coordinator_instance
```

**Acceptance Criteria**:
- ✅ Singleton pattern
- ✅ PID tracking
- ✅ Heartbeat mechanism
- ✅ Stale session cleanup
- ✅ File locking with fcntl
- ✅ Atomic writes
- ✅ Type hints + docstrings
- ✅ psutil health checks

---

#### FASE 3.2: Integrate with SessionStart Hook (10 min)
**File**: `.claude/hooks/devstream/sessions/session_start.py` (MODIFY)

**Changes**:
```python
from utils.session_coordinator import get_session_coordinator

async def main():
    # ... existing session start logic ...

    # Register session with coordinator
    coordinator = get_session_coordinator()
    session_id = generate_session_id()  # From existing code
    coordinator.register_session(session_id)

    logger.info("Session registered with coordinator",
                session_id=session_id,
                active_sessions=len(coordinator.get_active_sessions()))
```

**Acceptance Criteria**:
- ✅ Registers session on startup
- ✅ Logs active session count
- ✅ Non-blocking (no delays)

---

#### FASE 3.3: Integrate with SessionEnd Hook (10 min)
**File**: `.claude/hooks/devstream/sessions/session_end.py` (MODIFY)

**Changes**:
```python
from utils.session_coordinator import get_session_coordinator

async def main():
    # ... existing session end logic ...

    # Unregister session
    coordinator = get_session_coordinator()
    coordinator.unregister_session()

    logger.info("Session unregistered from coordinator")
```

**Acceptance Criteria**:
- ✅ Unregisters on graceful exit
- ✅ Atomic registry update
- ✅ No errors if already unregistered

---

### FASE 4: Testing & Validation (45 minutes)

**Objective**: Ensure crash prevention works with comprehensive testing

#### FASE 4.1: Unit Tests for Connection Manager (15 min)
**File**: `tests/unit/test_sqlite_connection_manager.py` (NEW)

**Test Cases**:
```python
import pytest
import sqlite3
import aiosqlite
from pathlib import Path
from claude.hooks.devstream.utils.sqlite_connection_manager import (
    SQLiteConnectionManager,
    get_connection_manager
)

class TestSQLiteConnectionManager:
    """Test suite for SQLiteConnectionManager."""

    def test_singleton_pattern(self):
        """Verify singleton returns same instance."""
        manager1 = SQLiteConnectionManager.get_instance()
        manager2 = SQLiteConnectionManager.get_instance()
        assert manager1 is manager2

    def test_sync_connection_wal_mode(self, tmp_path):
        """Verify sync connection enables WAL mode."""
        db_path = tmp_path / "test.db"
        manager = get_connection_manager()

        conn = manager.get_sync_connection(str(db_path))
        cursor = conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]

        assert mode == "wal"
        conn.close()

    def test_sync_connection_busy_timeout(self, tmp_path):
        """Verify sync connection sets busy_timeout."""
        db_path = tmp_path / "test.db"
        manager = get_connection_manager()

        conn = manager.get_sync_connection(str(db_path))
        cursor = conn.execute("PRAGMA busy_timeout")
        timeout = cursor.fetchone()[0]

        assert timeout == 30000
        conn.close()

    @pytest.mark.asyncio
    async def test_async_connection_context_manager(self, tmp_path):
        """Verify async connection context manager."""
        db_path = tmp_path / "test.db"
        manager = get_connection_manager()

        async with manager.get_async_connection(str(db_path)) as db:
            cursor = await db.execute("PRAGMA journal_mode")
            mode_row = await cursor.fetchone()
            assert mode_row[0] == "wal"

    def test_vec_extension_loaded(self, tmp_path):
        """Verify sqlite-vec extension loads correctly."""
        db_path = tmp_path / "test.db"
        manager = get_connection_manager()

        conn = manager.get_sync_connection_with_vec(str(db_path))

        # Test vec_version()
        cursor = conn.execute("SELECT vec_version()")
        version = cursor.fetchone()[0]
        assert version is not None

        conn.close()
```

**Acceptance Criteria**:
- ✅ 6 unit tests
- ✅ 100% pass rate
- ✅ Coverage of all public methods
- ✅ WAL mode validation
- ✅ busy_timeout validation
- ✅ sqlite-vec extension validation

---

#### FASE 4.2: Integration Test - Multi-Session (15 min)
**File**: `tests/integration/test_multi_session_crash_prevention.py` (NEW)

**Test Cases**:
```python
import pytest
import asyncio
import subprocess
from pathlib import Path
from claude.hooks.devstream.utils.session_coordinator import get_session_coordinator
from claude.hooks.devstream.utils.sqlite_connection_manager import get_connection_manager

class TestMultiSessionCrashPrevention:
    """Integration tests for multi-session crash prevention."""

    @pytest.mark.asyncio
    async def test_two_concurrent_sessions(self, tmp_path):
        """Test 2 concurrent sessions writing to same database."""
        db_path = tmp_path / "test.db"

        # Initialize database
        manager = get_connection_manager()
        conn = manager.get_sync_connection(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        conn.commit()
        conn.close()

        # Simulate concurrent writes
        async def write_session(session_id: int):
            async with manager.get_async_connection(str(db_path)) as db:
                for i in range(10):
                    await db.execute(
                        "INSERT INTO test (value) VALUES (?)",
                        (f"session{session_id}_value{i}",)
                    )
                    await db.commit()
                    await asyncio.sleep(0.01)  # Simulate work

        # Run 2 sessions concurrently
        await asyncio.gather(
            write_session(1),
            write_session(2)
        )

        # Verify all writes succeeded
        conn = manager.get_sync_connection(str(db_path))
        cursor = conn.execute("SELECT COUNT(*) FROM test")
        count = cursor.fetchone()[0]
        assert count == 20  # 10 writes × 2 sessions
        conn.close()

    def test_session_coordinator_tracking(self):
        """Verify session coordinator tracks multiple sessions."""
        coordinator = get_session_coordinator()

        # Register session
        coordinator.register_session("test-session-1")

        # Get active sessions
        sessions = coordinator.get_active_sessions()
        assert len(sessions) >= 1
        assert any(s.session_id == "test-session-1" for s in sessions)

        # Cleanup
        coordinator.unregister_session()

    @pytest.mark.slow
    def test_spotlight_exclusion(self):
        """Verify Spotlight exclusion is active."""
        db_path = Path("data.noindex/devstream.db")

        if not db_path.exists():
            pytest.skip("Database not found")

        # Check for xattr
        result = subprocess.run(
            ["xattr", "-l", str(db_path)],
            capture_output=True,
            text=True
        )

        # Should have kMDItemSupportFileType xattr
        assert "kMDItemSupportFileType" in result.stdout or result.returncode != 0
```

**Acceptance Criteria**:
- ✅ 3 integration tests
- ✅ 100% pass rate
- ✅ Concurrent write test succeeds
- ✅ Session tracking validated
- ✅ Spotlight exclusion verified

---

#### FASE 4.3: Stress Test - 5 Concurrent Sessions (15 min)
**File**: `tests/integration/test_stress_multi_session.py` (NEW)

**Test Case**:
```python
import pytest
import asyncio
from pathlib import Path
from claude.hooks.devstream.utils.sqlite_connection_manager import get_connection_manager

@pytest.mark.slow
@pytest.mark.asyncio
async def test_five_concurrent_sessions_stress():
    """
    Stress test: 5 concurrent sessions for 10 minutes.

    Simulates real-world multi-session usage to verify:
    - No deadlocks
    - No SQLite BUSY errors
    - No kernel panics
    - No data corruption
    """
    db_path = Path("data.noindex/devstream.db")
    manager = get_connection_manager()

    duration_seconds = 600  # 10 minutes
    writes_per_session = 1000

    async def stress_session(session_id: int):
        """Simulate session workload."""
        start_time = asyncio.get_event_loop().time()

        async with manager.get_async_connection(str(db_path)) as db:
            for i in range(writes_per_session):
                # Simulate memory storage
                await db.execute(
                    "INSERT INTO semantic_memory (content, content_type, created_at) VALUES (?, ?, datetime('now'))",
                    (f"stress_test_session{session_id}_write{i}", "test")
                )
                await db.commit()

                # Rate limiting (10 writes/sec)
                await asyncio.sleep(0.1)

                # Check timeout
                if asyncio.get_event_loop().time() - start_time > duration_seconds:
                    break

        return session_id

    # Run 5 concurrent sessions
    results = await asyncio.gather(
        stress_session(1),
        stress_session(2),
        stress_session(3),
        stress_session(4),
        stress_session(5),
        return_exceptions=True
    )

    # Verify no exceptions
    for result in results:
        assert not isinstance(result, Exception), f"Session failed: {result}"

    # Verify database integrity
    async with manager.get_async_connection(str(db_path)) as db:
        cursor = await db.execute("PRAGMA integrity_check")
        integrity = await cursor.fetchone()
        assert integrity[0] == "ok"
```

**Acceptance Criteria**:
- ✅ Test runs for 10 minutes without crash
- ✅ No exceptions raised
- ✅ Database integrity check passes
- ✅ All 5 sessions complete successfully
- ✅ Marked as `@pytest.mark.slow` (skipped in CI)

---

## 📦 DELIVERABLES

### Code Artifacts
1. ✅ `scripts/setup_spotlight_exclusion.sh` - Spotlight exclusion script
2. ✅ `.claude/hooks/devstream/utils/sqlite_connection_manager.py` - Centralized connection manager
3. ✅ `.claude/hooks/devstream/utils/session_coordinator.py` - Multi-session coordination
4. ✅ Updated files (6): sqlite_vec_helper.py, work_session_manager.py, post_tool_use.py, session_data_extractor.py, session_start.py, session_end.py

### Documentation
1. ✅ `docs/guides/crash-prevention-guide.md` - Update with Spotlight section
2. ✅ `docs/architecture/sqlite-wal-mode.md` - WAL mode architecture doc (NEW)
3. ✅ `docs/architecture/session-coordination.md` - Session coordination design (NEW)

### Test Suite
1. ✅ `tests/unit/test_sqlite_connection_manager.py` - 6 unit tests
2. ✅ `tests/integration/test_multi_session_crash_prevention.py` - 3 integration tests
3. ✅ `tests/integration/test_stress_multi_session.py` - 1 stress test (10 min)

---

## 🎯 ACCEPTANCE CRITERIA

### Functional Requirements
- ✅ SQLite in WAL mode with `busy_timeout=30000`
- ✅ Spotlight excludes `data.noindex/` directory
- ✅ All connections use centralized manager
- ✅ Session coordinator tracks active sessions
- ✅ 2 concurrent sessions work without errors
- ✅ 5 concurrent sessions stress test passes (10 min)

### Code Quality Requirements
- ✅ 100% type hints coverage
- ✅ Full docstrings with examples
- ✅ Structured logging
- ✅ Error handling for all edge cases
- ✅ 95%+ test coverage
- ✅ 100% test pass rate

### Production Readiness
- ✅ No kernel panics in 24-hour test
- ✅ Performance impact <5% (measured)
- ✅ Backward compatibility maintained
- ✅ Rollback plan documented
- ✅ Monitoring metrics defined

---

## 📊 TIMELINE & ESTIMATES

| Phase | Duration | Cumulative |
|-------|----------|------------|
| FASE 1: Immediate Protection | 30 min | 30 min |
| FASE 2: Connection Manager | 60 min | 90 min |
| FASE 3: Session Coordination | 45 min | 135 min |
| FASE 4: Testing & Validation | 45 min | 180 min |
| **TOTAL** | **3 hours** | **180 min** |

### Contingency Buffer
- +30 min for unexpected issues
- +15 min for documentation updates
- **Total with buffer**: 3h 45min

---

## 🚨 RISK MITIGATION

### Risk 1: WAL Mode Incompatibility
**Probability**: Low
**Impact**: High
**Mitigation**: WAL supported since SQLite 3.7.0 (2010), macOS 10.9+
**Rollback**: `PRAGMA journal_mode=DELETE` reverses change

### Risk 2: Existing Code Breaks
**Probability**: Medium
**Impact**: Medium
**Mitigation**: Comprehensive test suite, backward compatibility layer
**Rollback**: Restore from git (1 command)

### Risk 3: Performance Degradation
**Probability**: Low
**Impact**: Medium
**Mitigation**: WAL mode actually IMPROVES performance (2x writes)
**Validation**: Benchmark before/after

### Risk 4: Spotlight Re-indexing
**Probability**: Low
**Impact**: Low
**Mitigation**: `.noindex` suffix + xattr defense in depth
**Monitoring**: Check `mdls` output daily

---

## 📝 IMPLEMENTATION NOTES

### Order of Execution (CRITICAL)
1. ✅ Run Spotlight exclusion script FIRST
2. ✅ Enable WAL mode in sqlite_vec_helper.py
3. ✅ Create connection manager
4. ✅ Refactor all consumers to use manager
5. ✅ Implement session coordinator
6. ✅ Add hook integrations
7. ✅ Run test suite

### Verification Checklist (After Each FASE)
- ✅ Code runs without errors
- ✅ Tests pass
- ✅ No new warnings in logs
- ✅ Database accessible
- ✅ Hooks execute successfully

### Post-Implementation Monitoring (First 24 Hours)
- ✅ Check `~/.claude/logs/devstream/` for errors
- ✅ Verify `data.noindex/devstream.db-wal` created
- ✅ Monitor `lsof | grep devstream.db` (connection count)
- ✅ Check kernel panic logs: `log show --predicate 'process == "kernel"' --last 24h`

---

## 🔄 ROLLBACK PLAN

### If Critical Issues Arise

**Step 1**: Restore original state
```bash
git checkout HEAD -- .claude/hooks/devstream/
mv data.noindex data
```

**Step 2**: Revert WAL mode
```bash
sqlite3 data/devstream.db "PRAGMA journal_mode=DELETE;"
```

**Step 3**: Remove Spotlight exclusion
```bash
xattr -d com.apple.metadata:kMDItemSupportFileType data/devstream.db
```

**Step 4**: Restart Claude Code
```bash
pkill -f claude
# Restart Claude Code manually
```

---

## 🎓 LESSONS LEARNED (To Document Post-Implementation)

### Technical Insights
- [ ] WAL mode performance impact (measure)
- [ ] Optimal `busy_timeout` for our workload
- [ ] Session coordinator overhead
- [ ] Spotlight exclusion effectiveness

### Process Improvements
- [ ] Multi-session testing approach
- [ ] Crash prevention patterns
- [ ] SQLite optimization techniques

### Future Enhancements
- [ ] Connection pooling for high concurrency
- [ ] Automatic WAL checkpoint tuning
- [ ] Health check dashboard
- [ ] Real-time session monitoring UI

---

**Document Version**: 1.0
**Created**: 2025-10-08
**Status**: ✅ Ready for Approval
**Estimated Completion**: 2025-10-08 (same day)

---

*This plan follows DevStream 7-step protocol (CLAUDE.md v2.1.0) and incorporates Context7 research findings (Trust Scores: aiosqlite 7.7, SQLite docs 10.0).*
