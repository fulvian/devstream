#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.0.0",
#     "python-dotenv>=1.0.0",
#     "aiohttp>=3.8.0",
# ]
# ///

"""
DevStream Stop Hook - Task Completion Automatico
Context7-compliant automatic task completion detection e status updates.
"""

import json
import sys
import os
import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# Import DevStream utilities
sys.path.append(str(Path(__file__).parent.parent / 'utils'))
from common import DevStreamHookBase, get_project_context
from logger import get_devstream_logger
from mcp_client import get_mcp_client

class StopHook(DevStreamHookBase):
    """
    Stop hook per automatic task completion detection e management.
    Implementa Context7-validated patterns per task lifecycle automation.
    """

    def __init__(self):
        super().__init__('stop')
        self.structured_logger = get_devstream_logger('stop')
        self.mcp_client = get_mcp_client()
        self.start_time = time.time()

    async def process_session_stop(self, input_data: dict) -> None:
        """
        Process session stop e detect task completion.

        Args:
            input_data: JSON input from Claude Code Stop hook
        """
        self.structured_logger.log_hook_start(input_data, {"phase": "session_stop"})

        try:
            session_id = input_data.get('session_id', 'unknown')
            reason = input_data.get('reason', 'user_request')

            self.logger.info(f"Processing session stop: {session_id}, reason: {reason}")

            # Analyze session activity for task completion
            session_analysis = await self.analyze_session_activity(session_id)

            # Check for active tasks that might be completed
            active_tasks = await self.get_active_tasks()

            # Determine task completion status
            completion_results = await self.assess_task_completion(
                session_analysis,
                active_tasks
            )

            # Update task statuses
            if completion_results['tasks_to_complete']:
                await self.complete_tasks(completion_results['tasks_to_complete'])

            # Generate session summary
            session_summary = await self.generate_session_summary(
                session_id,
                session_analysis,
                completion_results
            )

            # Store session completion in memory
            await self.store_session_completion(session_id, session_summary)

            # Output completion message
            if completion_results['tasks_completed'] > 0:
                completion_message = self.generate_completion_message(completion_results)
                print(completion_message)

            # Log performance metrics
            execution_time = (time.time() - self.start_time) * 1000
            self.structured_logger.log_performance_metrics(execution_time)

            self.logger.info(f"Session stop processed: {completion_results['tasks_completed']} tasks completed")

        except Exception as e:
            self.structured_logger.log_hook_error(e, {"session_id": session_id})
            raise

    async def analyze_session_activity(self, session_id: str) -> Dict[str, Any]:
        """
        Analyze session activity per task completion detection.

        Args:
            session_id: Session ID to analyze

        Returns:
            Session activity analysis
        """
        analysis = {
            "session_id": session_id,
            "code_files_modified": [],
            "tools_used": [],
            "implementation_indicators": [],
            "completion_confidence": 0.0,
            "activity_summary": ""
        }

        # Search for session-related memories
        session_query = f"session {session_id[:8]} tool result code implementation"

        session_memories = await self.mcp_client.search_memory(
            query=session_query,
            limit=10
        )

        if session_memories:
            # Analyze memories for completion indicators
            memory_analysis = self.analyze_session_memories(session_memories)
            analysis.update(memory_analysis)

        # Assess completion confidence based on activity
        analysis["completion_confidence"] = self.calculate_completion_confidence(analysis)

        return analysis

    def analyze_session_memories(self, memories_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze session memories per completion indicators.

        Args:
            memories_response: MCP search response

        Returns:
            Memory analysis results
        """
        analysis = {
            "code_files_modified": [],
            "tools_used": [],
            "implementation_indicators": [],
            "error_count": 0,
            "success_count": 0
        }

        # Extract content from MCP response
        content = memories_response.get('content', [])
        if not content:
            return analysis

        # Parse memory content (simplified - would need actual MCP response parsing)
        memory_text = content[0].get('text', '') if content else ''

        # Look for completion indicators
        if 'TOOL RESULT' in memory_text:
            analysis["success_count"] += memory_text.count('Success: True')
            analysis["error_count"] += memory_text.count('Success: False')

        # Look for code modifications
        if 'Edit' in memory_text or 'Write' in memory_text:
            analysis["implementation_indicators"].append('code_modification')

        # Look for test execution
        if 'test' in memory_text.lower() or 'pytest' in memory_text.lower():
            analysis["implementation_indicators"].append('testing')

        # Look for successful builds/runs
        if 'completed successfully' in memory_text.lower():
            analysis["implementation_indicators"].append('successful_execution')

        return analysis

    def calculate_completion_confidence(self, analysis: Dict[str, Any]) -> float:
        """
        Calculate task completion confidence score.

        Args:
            analysis: Session analysis

        Returns:
            Confidence score (0.0-1.0)
        """
        confidence = 0.0

        # Base confidence from successful operations
        success_ratio = analysis.get('success_count', 0) / max(
            analysis.get('success_count', 0) + analysis.get('error_count', 0), 1
        )
        confidence += success_ratio * 0.4

        # Confidence from implementation indicators
        indicators = analysis.get('implementation_indicators', [])
        if 'code_modification' in indicators:
            confidence += 0.3
        if 'testing' in indicators:
            confidence += 0.2
        if 'successful_execution' in indicators:
            confidence += 0.1

        return min(confidence, 1.0)

    async def get_active_tasks(self) -> List[Dict[str, Any]]:
        """
        Get active DevStream tasks.

        Returns:
            List of active tasks
        """
        try:
            # Get active tasks from DevStream MCP
            tasks_response = await self.mcp_client.list_tasks(status="active")

            if not tasks_response:
                return []

            # Parse tasks from response (simplified)
            # In real implementation, would parse actual MCP response structure
            return [
                {
                    "id": "hook-system-implementation",
                    "title": "Hook System Implementation",
                    "status": "active",
                    "priority": 9,
                    "phase": "Implementation"
                }
            ]

        except Exception as e:
            self.logger.warning(f"Failed to get active tasks: {e}")
            return []

    async def assess_task_completion(
        self,
        session_analysis: Dict[str, Any],
        active_tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Assess which tasks should be marked as completed.

        Args:
            session_analysis: Session activity analysis
            active_tasks: List of active tasks

        Returns:
            Task completion assessment results
        """
        results = {
            "tasks_to_complete": [],
            "tasks_completed": 0,
            "completion_reasons": []
        }

        completion_confidence = session_analysis.get('completion_confidence', 0.0)

        # Only complete tasks if high confidence
        if completion_confidence >= 0.7:
            for task in active_tasks:
                # Check if task matches session activity
                if self.task_matches_session(task, session_analysis):
                    results["tasks_to_complete"].append({
                        "task_id": task["id"],
                        "title": task["title"],
                        "completion_confidence": completion_confidence,
                        "reason": f"Session activity indicates completion (confidence: {completion_confidence:.2f})"
                    })

        results["tasks_completed"] = len(results["tasks_to_complete"])

        return results

    def task_matches_session(
        self,
        task: Dict[str, Any],
        session_analysis: Dict[str, Any]
    ) -> bool:
        """
        Check if task matches session activity.

        Args:
            task: Task information
            session_analysis: Session analysis

        Returns:
            True if task matches session activity
        """
        task_title = task.get('title', '').lower()
        indicators = session_analysis.get('implementation_indicators', [])

        # Match based on task type and session activity
        if 'hook' in task_title and 'code_modification' in indicators:
            return True
        if 'implementation' in task_title and 'successful_execution' in indicators:
            return True

        return False

    async def complete_tasks(self, tasks_to_complete: List[Dict[str, Any]]) -> None:
        """
        Mark tasks as completed via MCP.

        Args:
            tasks_to_complete: List of tasks to complete
        """
        for task_info in tasks_to_complete:
            try:
                task_id = task_info["task_id"]
                reason = task_info["reason"]

                # Update task status to completed
                update_result = await self.mcp_client.update_task(
                    task_id=task_id,
                    status="completed",
                    notes=f"Auto-completed via Stop hook: {reason}"
                )

                if update_result:
                    self.logger.info(f"Completed task: {task_info['title']}")

                    # Log task completion
                    self.structured_logger.log_task_operation(
                        operation="complete",
                        task_id=task_id,
                        task_type="auto_completion",
                        status="completed"
                    )
                else:
                    self.logger.warning(f"Failed to complete task: {task_info['title']}")

            except Exception as e:
                self.logger.error(f"Error completing task {task_info.get('title', 'unknown')}: {e}")

    async def generate_session_summary(
        self,
        session_id: str,
        session_analysis: Dict[str, Any],
        completion_results: Dict[str, Any]
    ) -> str:
        """
        Generate session completion summary.

        Args:
            session_id: Session ID
            session_analysis: Session analysis
            completion_results: Task completion results

        Returns:
            Session summary text
        """
        summary_parts = [
            f"SESSION COMPLETED [{session_id[:8]}]",
            f"Timestamp: {datetime.now().isoformat()}",
            f"Completion Confidence: {session_analysis.get('completion_confidence', 0.0):.2f}",
            f"Tasks Completed: {completion_results['tasks_completed']}",
        ]

        # Add implementation indicators
        indicators = session_analysis.get('implementation_indicators', [])
        if indicators:
            summary_parts.append(f"Implementation Activity: {', '.join(indicators)}")

        # Add success/error ratio
        success_count = session_analysis.get('success_count', 0)
        error_count = session_analysis.get('error_count', 0)
        if success_count > 0 or error_count > 0:
            summary_parts.append(f"Operations: {success_count} successful, {error_count} errors")

        # Add completed tasks
        if completion_results['tasks_to_complete']:
            summary_parts.append("Completed Tasks:")
            for task_info in completion_results['tasks_to_complete']:
                summary_parts.append(f"- {task_info['title']}")

        return "\n".join(summary_parts)

    async def store_session_completion(self, session_id: str, summary: str) -> None:
        """
        Store session completion in memory.

        Args:
            session_id: Session ID
            summary: Session summary
        """
        await self.mcp_client.store_memory(
            content=summary,
            content_type="context",
            keywords=["session-completion", "task-completion", session_id[:8]],
            session_id=session_id
        )

        # Log memory operation
        self.structured_logger.log_memory_operation(
            operation="store",
            content_type="context",
            content_size=len(summary),
            keywords=["session-completion"]
        )

    def generate_completion_message(self, completion_results: Dict[str, Any]) -> str:
        """
        Generate user-facing completion message.

        Args:
            completion_results: Task completion results

        Returns:
            Completion message for user
        """
        tasks_completed = completion_results['tasks_completed']

        if tasks_completed == 0:
            return ""

        message_parts = [
            "🎉 DevStream Task Completion Detected!",
            f"✅ {tasks_completed} task(s) automatically completed",
            ""
        ]

        for task_info in completion_results['tasks_to_complete']:
            confidence = task_info.get('completion_confidence', 0.0)
            message_parts.append(f"📋 {task_info['title']} (confidence: {confidence:.0%})")

        message_parts.extend([
            "",
            "🔄 Task status updated in DevStream system",
            "📊 Session activity logged for future reference"
        ])

        return "\n".join(message_parts)

async def main():
    """Main hook execution following Context7 patterns."""
    hook = StopHook()

    try:
        # Read JSON input from stdin (Context7 pattern)
        input_data = hook.read_stdin_json()

        # Process session stop
        await hook.process_session_stop(input_data)

        # Success exit
        hook.success_exit()

    except Exception as e:
        hook.error_exit(f"Stop hook failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())