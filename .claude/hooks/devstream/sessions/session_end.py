#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cchooks>=0.1.4",
#     "aiohttp>=3.8.0",
#     "structlog>=23.0.0",
#     "python-dotenv>=1.0.0",
#     "ollama>=0.1.0",
#     "aiosqlite>=0.19.0",
# ]
# ///

"""
DevStream SessionEnd Hook - Context7 Compliant

Captures comprehensive session summaries using triple-source data extraction.
Implements Context7 async patterns for data extraction and aggregation.

Workflow:
1. Detect session end trigger (Claude Code SessionEnd event)
2. Extract session data from work_sessions table
3. Extract memory stats from semantic_memory (time-range query)
4. Extract task stats from micro_tasks (time-range query)
5. Aggregate into unified summary
6. Generate markdown-formatted summary
7. Store summary in memory with embedding
8. Update session status to "completed"

Triple Sources:
- work_sessions → Session metadata, timestamps, tokens
- semantic_memory → Files modified, decisions, learnings
- micro_tasks → Task completion, status changes

Context7 Patterns:
- aiosqlite: async with context managers, row_factory
- Structured logging with context
- Graceful degradation on errors
"""

import sys
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
sys.path.insert(0, str(Path(__file__).parent))

from cchooks import safe_create_context, SessionEndContext
from devstream_base import DevStreamHookBase
from mcp_client import get_mcp_client
from ollama_client import OllamaEmbeddingClient

# Import session components
from session_data_extractor import SessionDataExtractor
from session_summary_generator import SessionSummaryGenerator, format_session_for_storage
from work_session_manager import WorkSessionManager
from atomic_file_writer import write_atomic


class SessionEndHook:
    """
    SessionEnd hook for comprehensive session summary capture.

    Orchestrates triple-source data extraction and summary generation.
    Stores summaries in semantic memory with embeddings for future retrieval.

    Context7 Pattern: Clear separation of concerns across components:
    - SessionDataExtractor: Data extraction layer
    - SessionSummaryGenerator: Aggregation and formatting layer
    - SessionEnd: Orchestration and storage layer
    """

    def __init__(self):
        self.base = DevStreamHookBase("session_end")
        self.mcp_client = get_mcp_client()

        # Initialize components
        self.data_extractor = SessionDataExtractor()
        self.summary_generator = SessionSummaryGenerator()
        self.session_manager = WorkSessionManager()
        self.ollama_client = OllamaEmbeddingClient()

        # Database path
        project_root = Path(__file__).parent.parent.parent.parent.parent
        self.db_path = str(project_root / 'data' / 'devstream.db')

    def cleanup_ollama_models(self) -> bool:
        """
        Force unload Ollama models on session end.

        Executes `ollama stop embeddinggemma:300m` to immediately release
        model from memory (~1.21GB).

        Returns:
            True if cleanup successful, False otherwise

        Note:
            Non-blocking. Logs errors but doesn't raise exceptions to
            prevent session end failure.
        """
        try:
            result = subprocess.run(
                ['ollama', 'stop', 'embeddinggemma:300m'],
                capture_output=True,
                timeout=5,  # 5-second timeout
                text=True,
                check=False  # Don't raise on non-zero exit
            )

            if result.returncode == 0:
                self.base.debug_log(
                    "Ollama models unloaded successfully "
                    "(model=embeddinggemma:300m, memory_freed_mb=1210)"
                )
                return True
            else:
                self.base.debug_log(
                    f"Ollama cleanup non-zero exit: returncode={result.returncode}, "
                    f"stderr={result.stderr.strip()}"
                )
                return False

        except subprocess.TimeoutExpired:
            self.base.debug_log(
                "Ollama cleanup timeout after 5s (command='ollama stop embeddinggemma:300m')"
            )
            return False

        except FileNotFoundError:
            self.base.debug_log(
                "Ollama CLI not found - skip cleanup (note: Ollama may not be installed or not in PATH)"
            )
            return False

        except Exception as e:
            self.base.debug_log(
                f"Ollama cleanup unexpected error: {str(e)} (error_type={type(e).__name__})"
            )
            return False

    async def get_active_session_id(self) -> Optional[str]:
        """
        Get currently active session ID.

        Returns:
            Active session ID or None if no active session
        """
        try:
            # Query work_sessions for active session
            import aiosqlite

            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row

                async with db.execute(
                    """
                    SELECT id FROM work_sessions
                    WHERE status = 'active'
                    ORDER BY started_at DESC
                    LIMIT 1
                    """
                ) as cursor:
                    row = await cursor.fetchone()

                    if row:
                        return row['id']
                    else:
                        self.base.debug_log("No active session found")
                        return None

        except Exception as e:
            self.base.debug_log(f"Failed to get active session: {e}")
            return None

    async def store_summary_in_memory(
        self,
        summary_markdown: str,
        session_id: str
    ) -> Optional[str]:
        """
        Store session summary in DevStream memory with embedding.

        Args:
            summary_markdown: Markdown-formatted summary
            session_id: Session identifier

        Returns:
            Memory ID if storage successful, None otherwise
        """
        try:
            self.base.debug_log(
                f"Storing summary in memory: {len(summary_markdown)} chars"
            )

            # Store via MCP
            result = await self.base.safe_mcp_call(
                self.mcp_client,
                "devstream_store_memory",
                {
                    "content": summary_markdown,
                    "content_type": "context",
                    "keywords": [
                        "session",
                        "summary",
                        session_id,
                        "session-end"
                    ]
                }
            )

            if not result:
                self.base.debug_log("Memory storage returned no result")
                return None

            # Context7 pattern: Extract memory_id from structuredContent (MCP 2025-06-18)
            memory_id = None
            embedding_generated = False

            if isinstance(result, dict):
                # Modern MCP clients: use structuredContent if available
                if 'structuredContent' in result:
                    structured = result['structuredContent']
                    memory_id = structured.get('memory_id')
                    embedding_generated = structured.get('embedding_generated', False)
                    self.base.debug_log(
                        f"✅ Structured response: memory_id={memory_id[:8] if memory_id else 'None'}, "
                        f"embedding={embedding_generated}"
                    )
                # Fallback: legacy text parsing for backwards compatibility
                elif 'content' in result and isinstance(result['content'], list):
                    for content_item in result['content']:
                        if isinstance(content_item, dict) and content_item.get('type') == 'text':
                            import re
                            text = content_item.get('text', '')
                            match = re.search(r'Memory ID: `([a-f0-9]+)`', text)
                            if match:
                                memory_id = match.group(1)
                                # Check if embedding was generated (legacy parsing)
                                embedding_generated = '✅ Generated' in text
                                self.base.debug_log(
                                    f"⚠️ Legacy text parsing: memory_id={memory_id[:8]}, "
                                    f"embedding={embedding_generated}"
                                )
                                break

            if not memory_id:
                self.base.debug_log("No memory_id in MCP response (checked both structured and text)")
                return None

            self.base.debug_log(
                f"✅ Summary stored successfully: {memory_id[:8]}... "
                f"(embedding {'already generated by MCP server' if embedding_generated else 'not available'})"
            )

            # Note: Embedding generation is handled by MCP server (Context7-compliant)
            # No need to re-generate here - MCP server already does it during storage

            return memory_id

        except Exception as e:
            self.base.debug_log(f"Failed to store summary in memory: {e}")
            return None

    async def process_session_end(self, session_id: str) -> bool:
        """
        Process session end workflow.

        Main orchestration method that coordinates all components.

        Args:
            session_id: Session identifier to process

        Returns:
            True if successful, False otherwise
        """
        try:
            self.base.debug_log(f"Processing session end: {session_id}")

            # Step 1: Extract session metadata
            self.base.debug_log("Step 1: Extracting session metadata...")
            session_data = await self.data_extractor.get_session_metadata(session_id)

            if not session_data:
                self.base.debug_log(f"Session not found: {session_id}")
                return False

            self.base.debug_log(
                f"Session metadata extracted: {session_data.session_name or session_id}"
            )

            # Step 2: Extract memory stats (time-range query)
            self.base.debug_log("Step 2: Extracting memory stats...")

            if session_data.started_at:
                memory_stats = await self.data_extractor.get_memory_stats(
                    session_data.started_at,
                    session_data.ended_at or datetime.now()
                )
                self.base.debug_log(
                    f"Memory stats: {memory_stats.total_records} records, "
                    f"{memory_stats.files_modified} files"
                )
            else:
                self.base.debug_log("No start time - skipping memory stats")
                from session_data_extractor import MemoryStats
                memory_stats = MemoryStats()

            # Step 3: Extract task stats (FASE 3: tracking-based with time fallback)
            self.base.debug_log("Step 3: Extracting task stats...")

            if session_data.started_at:
                task_stats = await self.data_extractor.get_task_stats(
                    session_data.started_at,
                    session_data.ended_at or datetime.now(),
                    session_data=session_data  # FASE 3: Pass session_data for tracking
                )
                self.base.debug_log(
                    f"Task stats: {task_stats.total_tasks} total, "
                    f"{task_stats.completed} completed"
                )
            else:
                self.base.debug_log("No start time - skipping task stats")
                from session_data_extractor import TaskStats
                task_stats = TaskStats()

            # Step 4: Generate summary
            self.base.debug_log("Step 4: Generating summary...")

            summary_markdown = self.summary_generator.generate_summary(
                session_data,
                memory_stats,
                task_stats
            )

            self.base.debug_log(
                f"Summary generated: {len(summary_markdown)} chars"
            )

            # Step 5: Store summary in memory with embedding
            self.base.debug_log("Step 5: Storing summary in memory...")

            memory_id = await self.store_summary_in_memory(
                summary_markdown,
                session_id
            )

            if memory_id:
                self.base.debug_log(f"Summary stored: {memory_id[:8]}...")
            else:
                self.base.warning_feedback("Summary storage failed (non-blocking)")

            # Step 5.5: Write summary to file for SessionStart hook (ATOMIC)
            self.base.debug_log("Step 5.5: Writing summary to marker file (atomic)...")

            summary_file = Path.home() / ".claude" / "state" / "devstream_last_session.txt"

            # Ensure parent directory exists
            summary_file.parent.mkdir(parents=True, exist_ok=True)

            # Atomic write with logging
            write_success = await write_atomic(summary_file, summary_markdown)

            if write_success:
                self.base.debug_log(
                    f"✅ Marker file written atomically: {summary_file} "
                    f"(source=session_end, size={len(summary_markdown)} chars)"
                )

                # Log marker file creation for telemetry
                self.base.debug_log(
                    f"📊 Marker file telemetry: "
                    f"exists={summary_file.exists()}, "
                    f"size={summary_file.stat().st_size if summary_file.exists() else 0}, "
                    f"source=session_end"
                )
            else:
                self.base.debug_log(
                    f"❌ Marker file write failed: {summary_file} (source=session_end)"
                )

            # Step 6: Update session status to "completed"
            self.base.debug_log("Step 6: Updating session status...")

            # Use WorkSessionManager to end session properly
            session_ended = await self.session_manager.end_session(
                session_id=session_id,
                context_summary=summary_markdown[:500]  # First 500 chars as summary
            )

            if session_ended:
                self.base.debug_log("Session status updated to completed")
            else:
                self.base.warning_feedback("Session status update failed")

            # Step 7: Cleanup Ollama models (non-blocking, best-effort)
            self.base.debug_log("Step 7: Cleaning up Ollama models...")

            cleanup_success = self.cleanup_ollama_models()
            if cleanup_success:
                self.base.debug_log("Ollama cleanup complete - models unloaded")
            else:
                self.base.debug_log("Ollama cleanup failed (non-critical, session end continues)")

            # Success feedback
            self.base.success_feedback(
                f"Session ended: {task_stats.completed} tasks, "
                f"{memory_stats.files_modified} files"
            )

            return True

        except Exception as e:
            self.base.debug_log(f"Session end processing error: {e}")
            return False

    async def process(self, context: Optional[SessionEndContext]) -> None:
        """
        Main hook processing logic.

        Args:
            context: SessionEnd context from cchooks (or None if stdin empty)
        """
        # Check if hook should run
        if not self.base.should_run():
            self.base.debug_log("Hook disabled via config")
            if context:
                context.output.exit_success()
            return

        try:
            # Get active session ID
            session_id = await self.get_active_session_id()

            if not session_id:
                self.base.debug_log("No active session to end")
                if context:
                    context.output.exit_success()
                return

            # Process session end
            success = await self.process_session_end(session_id)

            if not success:
                # Non-blocking warning
                self.base.warning_feedback("Session end processing failed")

            # Always allow session to end (graceful degradation)
            if context:
                context.output.exit_success()

        except Exception as e:
            # Non-blocking error - log and continue
            self.base.warning_feedback(f"SessionEnd error: {str(e)[:50]}")
            if context:
                context.output.exit_success()


def main():
    """Main entry point for SessionEnd hook."""
    # Try to create context using cchooks
    ctx = None
    try:
        ctx = safe_create_context()
    except (Exception, SystemExit) as e:
        # stdin empty or invalid JSON - fallback to manual session lookup
        print(f"⚠️  DevStream: No hook input, using fallback mode", file=sys.stderr)
        ctx = None  # Explicitly set to None for fallback mode

    # Verify it's SessionEnd context (if available)
    if ctx and not isinstance(ctx, SessionEndContext):
        print(f"Error: Expected SessionEndContext, got {type(ctx)}", file=sys.stderr)
        sys.exit(1)

    # Create and run hook
    hook = SessionEndHook()

    try:
        # Run async processing (hook will handle missing context internally)
        asyncio.run(hook.process(ctx))
    except Exception as e:
        # Graceful failure - non-blocking
        print(f"⚠️  DevStream: SessionEnd error: {str(e)}", file=sys.stderr)
        if ctx:
            ctx.output.exit_non_block(f"Hook error: {str(e)[:100]}")
        else:
            # No ctx - just exit gracefully
            print("Summary generation attempted despite missing context", file=sys.stderr)
            sys.exit(0)


if __name__ == "__main__":
    main()