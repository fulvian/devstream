#!/usr/bin/env python3
"""
DevStream Work Session Manager - Session Lifecycle Management

Context7-compliant session state management using aiosqlite async patterns
and structlog context binding for automatic session context inheritance.

Research Sources:
- aiosqlite: async with context managers, row_factory, explicit commits
- structlog: bind_contextvars() for thread-local context propagation
"""

import sys
import os
import aiosqlite
import structlog
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass

# Import DevStream utilities
sys.path.append(str(Path(__file__).parent.parent / 'utils'))
from common import DevStreamHookBase, get_project_context
from logger import get_devstream_logger


@dataclass
class WorkSession:
    """
    Work session data model.

    Represents a complete work session with all tracking data.
    """
    id: str
    plan_id: Optional[str]
    user_id: Optional[str]
    session_name: Optional[str]
    context_window_size: Optional[int]
    tokens_used: int
    status: str
    context_summary: Optional[str]
    active_tasks: List[str]
    completed_tasks: List[str]
    started_at: datetime
    last_activity_at: datetime
    ended_at: Optional[datetime]


class WorkSessionManager:
    """
    Work Session Manager for DevStream session lifecycle management.

    Manages work_sessions table CRUD operations using Context7-validated
    aiosqlite async patterns and structlog context binding.

    Key Features:
    - Async connection management with context managers
    - Session state tracking in work_sessions table
    - Automatic context binding for log inheritance
    - Graceful error handling with structured logging

    Context7 Patterns Applied:
    - aiosqlite: async with connect(), row_factory, explicit commits
    - structlog: bind_contextvars() for automatic context propagation
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize WorkSessionManager.

        Args:
            db_path: Path to DevStream database (defaults to data/devstream.db)
        """
        self.structured_logger = get_devstream_logger('work_session_manager')
        self.logger = self.structured_logger.logger  # Compatibility

        # Database configuration
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent.parent.parent
            self.db_path = str(project_root / 'data' / 'devstream.db')
        else:
            self.db_path = db_path

        self.logger.info(f"WorkSessionManager initialized with DB: {self.db_path}")

    def _get_connection(self) -> aiosqlite.Connection:
        """
        Get database connection with Context7 aiosqlite pattern.

        Uses async context manager pattern from Context7 research:
        - Returns aiosqlite.connect() directly (Connection object with __aenter__/__aexit__)
        - row_factory set after connection established
        - Caller uses: async with manager._get_connection() as db:

        Returns:
            aiosqlite.Connection: Database connection (not awaited - has async context manager protocol)

        Raises:
            aiosqlite.Error: If connection fails
        """
        # Context7 pattern: Return connection object directly, don't await here
        # The Connection object implements __aenter__/__aexit__ for async with
        conn = aiosqlite.connect(self.db_path)
        # Note: row_factory must be set after await in __aenter__
        return conn

    async def get_session(self, session_id: str) -> Optional[WorkSession]:
        """
        Get session by ID from database.

        Args:
            session_id: Session identifier

        Returns:
            WorkSession if found, None otherwise

        Raises:
            aiosqlite.Error: If database query fails
        """
        async with self._get_connection() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT id, plan_id, user_id, session_name, context_window_size,
                       tokens_used, status, context_summary, active_tasks,
                       completed_tasks, started_at, last_activity_at, ended_at
                FROM work_sessions
                WHERE id = ?
                """,
                (session_id,)
            ) as cursor:
                row = await cursor.fetchone()

                if row is None:
                    return None

                # Parse JSON fields
                import json
                active_tasks = json.loads(row['active_tasks']) if row['active_tasks'] else []
                completed_tasks = json.loads(row['completed_tasks']) if row['completed_tasks'] else []

                return WorkSession(
                    id=row['id'],
                    plan_id=row['plan_id'],
                    user_id=row['user_id'],
                    session_name=row['session_name'],
                    context_window_size=row['context_window_size'],
                    tokens_used=row['tokens_used'],
                    status=row['status'],
                    context_summary=row['context_summary'],
                    active_tasks=active_tasks,
                    completed_tasks=completed_tasks,
                    started_at=datetime.fromisoformat(row['started_at']),
                    last_activity_at=datetime.fromisoformat(row['last_activity_at']),
                    ended_at=datetime.fromisoformat(row['ended_at']) if row['ended_at'] else None
                )

    # Session lifecycle methods will be implemented in next tasks
    async def create_session(
        self,
        session_id: str,
        plan_id: Optional[str] = None,
        session_name: Optional[str] = None,
        context_window_size: Optional[int] = None
    ) -> WorkSession:
        """
        Create new work session in database.

        Args:
            session_id: Unique session identifier
            plan_id: Optional intervention plan ID
            session_name: Optional human-readable session name
            context_window_size: Optional context window size

        Returns:
            WorkSession: Created session object

        Raises:
            aiosqlite.Error: If database operation fails
            ValueError: If session_id is invalid
        """
        if not session_id or not session_id.strip():
            raise ValueError("session_id cannot be empty")

        import json

        try:
            # Prepare data
            now = datetime.now().isoformat()
            active_tasks_json = json.dumps([])
            completed_tasks_json = json.dumps([])

            # Context7 pattern: async with for connection management + explicit commit
            # NOTE: Don't use "await" here - __aenter__ handles await internally
            async with self._get_connection() as db:
                await db.execute(
                    """
                    INSERT INTO work_sessions (
                        id, plan_id, user_id, session_name, context_window_size,
                        tokens_used, status, context_summary, active_tasks,
                        completed_tasks, started_at, last_activity_at, ended_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        plan_id,
                        None,  # user_id (can be set later)
                        session_name,
                        context_window_size,
                        0,  # tokens_used starts at 0
                        'active',
                        None,  # context_summary (populated on end)
                        active_tasks_json,
                        completed_tasks_json,
                        now,  # started_at
                        now,  # last_activity_at
                        None  # ended_at (NULL until session ends)
                    )
                )
                await db.commit()  # Explicit commit (Context7 pattern)

            self.logger.info(f"Created work session: {session_id}")

            # Return created session
            return WorkSession(
                id=session_id,
                plan_id=plan_id,
                user_id=None,
                session_name=session_name,
                context_window_size=context_window_size,
                tokens_used=0,
                status='active',
                context_summary=None,
                active_tasks=[],
                completed_tasks=[],
                started_at=datetime.fromisoformat(now),
                last_activity_at=datetime.fromisoformat(now),
                ended_at=None
            )

        except aiosqlite.IntegrityError as e:
            self.logger.error(f"Session already exists: {session_id}")
            raise ValueError(f"Session {session_id} already exists") from e
        except Exception as e:
            self.logger.error(f"Failed to create session {session_id}: {e}")
            raise

    async def resume_session(self, session_id: str) -> WorkSession:
        """
        Resume existing session or create new one.

        Logic:
        1. Try to get existing session from database
        2. If found: UPDATE last_activity_at to NOW()
        3. If not found: Call create_session() to create new one

        Args:
            session_id: Session identifier to resume

        Returns:
            WorkSession: Resumed or newly created session

        Raises:
            aiosqlite.Error: If database operation fails
        """
        # Try to get existing session
        existing_session = await self.get_session(session_id)

        if existing_session is not None:
            # Session exists - update last_activity_at
            now = datetime.now().isoformat()

            async with self._get_connection() as db:
                await db.execute(
                    """
                    UPDATE work_sessions
                    SET last_activity_at = ?
                    WHERE id = ?
                    """,
                    (now, session_id)
                )
                await db.commit()

            self.logger.info(f"Resumed existing work session: {session_id}")

            # Update last_activity_at in returned object
            existing_session.last_activity_at = datetime.fromisoformat(now)
            return existing_session

        else:
            # Session doesn't exist - create new one
            self.logger.info(f"Session {session_id} not found, creating new session")
            return await self.create_session(
                session_id=session_id,
                session_name=f"Session {session_id[:8]}"
            )

    async def update_session_progress(
        self,
        session_id: str,
        tokens_delta: int = 0,
        active_tasks: Optional[List[str]] = None,
        completed_tasks: Optional[List[str]] = None
    ) -> bool:
        """
        Update session progress metrics.

        Args:
            session_id: Session to update
            tokens_delta: Token count increment (added to existing tokens_used)
            active_tasks: Current active tasks list (replaces existing)
            completed_tasks: Current completed tasks list (replaces existing)

        Returns:
            bool: True if update successful

        Raises:
            aiosqlite.Error: If database operation fails
        """
        import json

        now = datetime.now().isoformat()

        # Build UPDATE query dynamically based on what's provided
        updates = ["last_activity_at = ?"]
        params = [now]

        if tokens_delta != 0:
            updates.append("tokens_used = tokens_used + ?")
            params.append(tokens_delta)

        if active_tasks is not None:
            updates.append("active_tasks = ?")
            params.append(json.dumps(active_tasks))

        if completed_tasks is not None:
            updates.append("completed_tasks = ?")
            params.append(json.dumps(completed_tasks))

        # Add session_id for WHERE clause
        params.append(session_id)

        query = f"UPDATE work_sessions SET {', '.join(updates)} WHERE id = ?"

        async with self._get_connection() as db:
            cursor = await db.execute(query, params)
            await db.commit()

            # Check if any row was updated
            if cursor.rowcount == 0:
                self.logger.warning(f"No session found to update: {session_id}")
                return False

        self.logger.debug(f"Updated session progress: {session_id}, tokens_delta={tokens_delta}")
        return True

    async def end_session(
        self,
        session_id: str,
        context_summary: Optional[str] = None
    ) -> bool:
        """
        End work session and mark as completed.

        Updates status='completed', sets ended_at timestamp,
        and optionally stores context summary.

        Args:
            session_id: Session to end
            context_summary: Optional session summary

        Returns:
            bool: True if session ended successfully

        Raises:
            aiosqlite.Error: If database operation fails
        """
        now = datetime.now().isoformat()

        async with self._get_connection() as db:
            cursor = await db.execute(
                """
                UPDATE work_sessions
                SET status = ?,
                    ended_at = ?,
                    context_summary = ?,
                    last_activity_at = ?
                WHERE id = ?
                """,
                ('completed', now, context_summary, now, session_id)
            )
            await db.commit()

            if cursor.rowcount == 0:
                self.logger.warning(f"No session found to end: {session_id}")
                return False

        self.logger.info(f"Ended work session: {session_id}")
        return True

    def bind_session_context(
        self,
        session_id: str,
        session_name: Optional[str] = None
    ) -> None:
        """
        Bind session context using structlog contextvars.

        Context7 Pattern: structlog.contextvars.bind_contextvars()
        Automatically propagates context to all subsequent log messages
        in the current thread/async context.

        This makes session_id available in ALL log messages without
        explicitly passing it to every log call.

        Args:
            session_id: Session ID to bind
            session_name: Optional session name

        Example:
            manager.bind_session_context("sess-123", "Phase 1")
            # All subsequent logs will include session_id="sess-123"
        """
        context_data = {"session_id": session_id}
        if session_name:
            context_data["session_name"] = session_name

        structlog.contextvars.bind_contextvars(**context_data)
        self.logger.debug(f"Bound session context: {session_id}")

    def clear_session_context(self) -> None:
        """
        Clear session context from structlog contextvars.

        Context7 Pattern: structlog.contextvars.clear_contextvars()
        Removes all bound context variables from current context.

        Should be called at session end to prevent context leakage
        into subsequent sessions.
        """
        structlog.contextvars.clear_contextvars()
        self.logger.debug("Cleared session context")


# Convenience functions for hook integration
async def create_or_resume_session(
    session_id: str,
    plan_id: Optional[str] = None,
    session_name: Optional[str] = None
) -> WorkSession:
    """
    Convenience function to create or resume session.

    Args:
        session_id: Session identifier
        plan_id: Optional plan ID
        session_name: Optional session name

    Returns:
        WorkSession: Created or resumed session
    """
    manager = WorkSessionManager()
    return await manager.resume_session(session_id)


if __name__ == "__main__":
    print("WorkSessionManager - DevStream Session Lifecycle Management")
    print("Context7-compliant implementation using aiosqlite + structlog")