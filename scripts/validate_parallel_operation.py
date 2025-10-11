#!/usr/bin/env -S .devstream/bin/python
# -*- coding: utf-8 -*-

"""
Validate Parallel Operation of SessionEnd Hooks (Old vs New)

This script compares the outputs of the legacy session_end.py and the new
session_end_v2.py Event Sourcing implementation to ensure compatibility
and validate accuracy during the parallel operation phase.

Usage:
    python scripts/validate_parallel_operation.py [--session-id <id>]

The script will:
1. Create test events in the event log
2. Run both SessionEnd hooks
3. Compare the generated summaries
4. Report differences and accuracy metrics
"""

import argparse
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / '.claude' / 'hooks' / 'devstream'))
sys.path.insert(0, str(Path(__file__).parent.parent / '.claude' / 'hooks' / 'devstream' / 'sessions'))

from sessions.session_event_log import get_session_log, close_session_log
from sessions.session_end import SessionEndHook as OldSessionEndHook
from sessions.session_end_v2 import SessionEndHookV2


class ParallelOperationValidator:
    """Validates parallel operation of old and new SessionEnd hooks."""

    def __init__(self):
        self.old_hook = OldSessionEndHook()
        self.new_hook = SessionEndHookV2()

    async def create_test_events(self, session_id: str) -> None:
        """Create test events for validation."""
        print(f"📝 Creating test events for session: {session_id}")

        event_log = await get_session_hook_log(session_id)

        # File modification events
        await event_log.record_event("file_modified", {
            "path": "/tmp/validate_test.py",
            "tool": "Write",
            "size_bytes": 256,
            "session_id": session_id
        })

        await event_log.record_event("file_modified", {
            "path": "/tmp/validate_test_utils.py",
            "tool": "Edit",
            "size_bytes": 128,
            "session_id": session_id
        })

        # Task events
        await event_log.record_event("task_started", {
            "task_id": "task-001",
            "title": "Implement validation test",
            "session_id": session_id
        })

        await event_log.record_event("task_completed", {
            "task_id": "task-001",
            "title": "Implement validation test",
            "session_id": session_id
        })

        await event_log.record_event("task_completed", {
            "task_id": "task-002",
            "title": "Write unit tests",
            "session_id": session_id
        })

        # Decision event (for old system)
        await event_log.record_event("decision", {
            "content": "Use Event Sourcing for session summaries",
            "category": "architecture",
            "session_id": session_id
        })

        # Learning event (for old system)
        await event_log.record_event("learning", {
            "content": "Event sourcing simplifies session state management",
            "importance": "high",
            "session_id": session_id
        })

        print(f"✅ Created 7 test events")

    async def run_old_session_end(self, session_id: str) -> Optional[str]:
        """Run legacy SessionEnd hook."""
        print("🔄 Running legacy SessionEnd hook...")

        try:
            # Set up environment
            os.environ["CLAUDE_SESSION_ID"] = session_id

            # Run the old hook
            success = await self.old_hook.process_session_end()

            if success:
                # Read the marker file
                marker_file = Path.home() / ".claude" / "state" / f"devstream_session_{session_id}.txt"
                if marker_file.exists():
                    with open(marker_file, "r") as f:
                        content = f.read()
                    print("✅ Legacy SessionEnd completed")
                    return content
                else:
                    print("❌ Legacy SessionEnd: No marker file found")
                    return None
            else:
                print("❌ Legacy SessionEnd failed")
                return None

        except Exception as e:
            print(f"❌ Legacy SessionEnd error: {e}")
            return None

    async def run_new_session_end(self, session_id: str) -> Optional[str]:
        """Run new SessionEnd v2 hook."""
        print("🔄 Running new SessionEnd v2 hook...")

        try:
            # Run the new hook
            success = await self.new_hook.process_session_end(session_id)

            if success:
                # Read the marker file
                marker_file = Path.home() / ".claude" / "state" / f"devstream_session_{session_id}.txt"
                if marker_file.exists():
                    with open(marker_file, "r") as f:
                        content = f.read()
                    print("✅ New SessionEnd v2 completed")
                    return content
                else:
                    print("❌ New SessionEnd v2: No marker file found")
                    return None
            else:
                print("❌ New SessionEnd v2 failed")
                return None

        except Exception as e:
            print(f"❌ New SessionEnd v2 error: {e}")
            return None

    def extract_metrics(self, content: str) -> Dict[str, Any]:
        """Extract metrics from session summary content."""
        metrics = {}

        lines = content.split('\n')
        for line in lines:
            line = line.strip()

            # Extract files modified
            if "Files Modified:" in line:
                try:
                    metrics["files_modified"] = int(line.split(":")[1].strip())
                except (IndexError, ValueError):
                    pass

            # Extract tasks completed
            elif "Tasks Completed:" in line:
                try:
                    metrics["tasks_completed"] = int(line.split(":")[1].strip())
                except (IndexError, ValueError):
                    pass

            # Extract decisions
            elif "Decisions Made:" in line:
                try:
                    metrics["decisions_made"] = int(line.split(":")[1].strip())
                except (IndexError, ValueError):
                    pass

            # Extract learnings
            elif "Learnings Captured:" in line:
                try:
                    metrics["learnings_captured"] = int(line.split(":")[1].strip())
                except (IndexError, ValueError):
                    pass

            # Extract total events (new system)
            elif "Total Events:" in line:
                try:
                    metrics["total_events"] = int(line.split(":")[1].strip())
                except (IndexError, ValueError):
                    pass

        return metrics

    def compare_summaries(self, old_content: str, new_content: str) -> Dict[str, Any]:
        """Compare old and new session summaries."""
        print("📊 Comparing summaries...")

        old_metrics = self.extract_metrics(old_content)
        new_metrics = self.extract_metrics(new_content)

        comparison = {
            "old_metrics": old_metrics,
            "new_metrics": new_metrics,
            "differences": {},
            "accuracy_score": 0.0,
            "summary": ""
        }

        # Compare metrics
        for key in ["files_modified", "tasks_completed"]:
            if key in old_metrics and key in new_metrics:
                if old_metrics[key] != new_metrics[key]:
                    comparison["differences"][key] = {
                        "old": old_metrics[key],
                        "new": new_metrics[key],
                        "difference": new_metrics[key] - old_metrics[key]
                    }

        # Calculate accuracy score
        comparable_metrics = 0
        matching_metrics = 0

        for key in ["files_modified", "tasks_completed"]:
            if key in old_metrics and key in new_metrics:
                comparable_metrics += 1
                if old_metrics[key] == new_metrics[key]:
                    matching_metrics += 1

        if comparable_metrics > 0:
            comparison["accuracy_score"] = (matching_metrics / comparable_metrics) * 100

        # Generate summary
        if comparison["accuracy_score"] >= 95:
            comparison["summary"] = "✅ Excellent accuracy - systems are highly compatible"
        elif comparison["accuracy_score"] >= 80:
            comparison["summary"] = "⚠️ Good accuracy - minor differences detected"
        else:
            comparison["summary"] = "❌ Poor accuracy - significant differences detected"

        return comparison

    def cleanup_marker_files(self, session_id: str) -> None:
        """Clean up marker files after validation."""
        marker_files = [
            Path.home() / ".claude" / "state" / f"devstream_session_{session_id}.txt"
        ]

        for marker_file in marker_files:
            if marker_file.exists():
                try:
                    marker_file.unlink()
                    print(f"🧹 Cleaned up: {marker_file}")
                except Exception as e:
                    print(f"⚠️ Failed to cleanup {marker_file}: {e}")

    async def validate_parallel_operation(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Perform complete parallel operation validation."""
        if not session_id:
            session_id = f"validation-{int(time.time())}"

        print(f"🧪 Starting parallel operation validation for session: {session_id}")
        print("=" * 60)

        try:
            # Step 1: Create test events
            await self.create_test_events(session_id)

            # Step 2: Run both hooks
            old_content = await self.run_old_session_end(session_id)
            new_content = await self.run_new_session_end(session_id)

            # Step 3: Compare results
            if old_content and new_content:
                comparison = self.compare_summaries(old_content, new_content)

                print("\n📈 Validation Results:")
                print(f"   Accuracy Score: {comparison['accuracy_score']:.1f}%")
                print(f"   Summary: {comparison['summary']}")

                if comparison["differences"]:
                    print("\n🔍 Differences Found:")
                    for metric, diff in comparison["differences"].items():
                        print(f"   {metric}: old={diff['old']}, new={diff['new']} (diff={diff['difference']})")

                # Save detailed comparison
                comparison_file = Path("session_end_comparison.json")
                with open(comparison_file, "w") as f:
                    json.dump(comparison, f, indent=2)
                print(f"\n💾 Detailed comparison saved to: {comparison_file}")

                return comparison
            else:
                print("❌ Validation failed - one or both hooks didn't produce output")
                return {"success": False, "error": "Missing hook outputs"}

        except Exception as e:
            print(f"❌ Validation error: {e}")
            return {"success": False, "error": str(e)}

        finally:
            # Step 4: Cleanup
            await close_session_log(session_id)
            self.cleanup_marker_files(session_id)
            print(f"\n🧹 Validation completed for session: {session_id}")


async def get_session_hook_log(session_id: str):
    """Get session event log (workaround for import issues)."""
    try:
        return await get_session_log(session_id)
    except NameError:
        # Fallback if session_event_log import fails
        print("⚠️ Warning: session_event_log not available, creating mock log")

        class MockEventLog:
            def __init__(self, session_id):
                self.session_id = session_id
                self.events = []

            async def record_event(self, event_type, data):
                from sessions.session_event_log import SessionEvent
                import time
                event = SessionEvent(time.time(), event_type, data)
                self.events.append(event)
                return event

            def get_all_events(self):
                return self.events.copy()

        return MockEventLog(session_id)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate parallel SessionEnd operation")
    parser.add_argument("--session-id", help="Specific session ID to validate")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    validator = ParallelOperationValidator()

    # Run validation
    result = asyncio.run(validator.validate_parallel_operation(args.session_id))

    if result.get("success", True):
        print("\n🎉 Parallel operation validation completed successfully!")
        exit(0)
    else:
        print(f"\n❌ Validation failed: {result.get('error', 'Unknown error')}")
        exit(1)


if __name__ == "__main__":
    main()