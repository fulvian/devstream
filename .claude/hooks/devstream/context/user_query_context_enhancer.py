#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cchooks>=0.1.4",
#     "aiohttp>=3.8.0",
#     "structlog>=23.0.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
DevStream UserPromptSubmit Hook - Context Enhancement before User Query
Combines Context7 library docs, DevStream memory, and task detection.
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))

from cchooks import safe_create_context, UserPromptSubmitContext
from devstream_base import DevStreamHookBase
from context7_client import Context7Client
from mcp_client import get_mcp_client


class UserPromptSubmitHook:
    """
    UserPromptSubmit hook for intelligent query enhancement.
    Combines Context7 research + DevStream memory + task lifecycle detection.
    """

    def __init__(self):
        self.base = DevStreamHookBase("user_prompt_submit")
        self.mcp_client = get_mcp_client()
        self.context7 = Context7Client(self.mcp_client)

    async def detect_context7_trigger(self, user_input: str) -> bool:
        """
        Detect if Context7 should be triggered for this query.

        Args:
            user_input: User input text

        Returns:
            True if Context7 should search for library docs
        """
        return await self.context7.should_trigger_context7(user_input)

    async def get_context7_research(self, user_input: str) -> Optional[str]:
        """
        Get Context7 research for user query.

        Args:
            user_input: User input text

        Returns:
            Formatted Context7 docs or None
        """
        try:
            self.base.debug_log("Context7 triggered - searching for docs")

            # Search and retrieve documentation
            result = await self.context7.search_and_retrieve(user_input)

            if result.success and result.docs:
                self.base.success_feedback(f"Context7 docs: {result.library_id}")
                return self.context7.format_docs_for_context(result)
            else:
                self.base.debug_log(f"Context7 search failed: {result.error}")
                return None

        except Exception as e:
            self.base.debug_log(f"Context7 error: {e}")
            return None

    async def search_devstream_memory(self, user_input: str) -> Optional[str]:
        """
        Search DevStream memory for relevant context.

        Args:
            user_input: User input text

        Returns:
            Formatted memory context or None
        """
        try:
            self.base.debug_log(f"Searching DevStream memory: {user_input[:50]}...")

            # Search memory via MCP
            result = await self.base.safe_mcp_call(
                self.mcp_client,
                "devstream_search_memory",
                {
                    "query": user_input,
                    "limit": 3
                }
            )

            if not result or not result.get("results"):
                self.base.debug_log("No relevant memory found")
                return None

            # Format memory results
            memory_items = result.get("results", [])
            if not memory_items:
                return None

            formatted = "# DevStream Memory Context\n\n"
            for i, item in enumerate(memory_items[:3], 1):
                content = item.get("content", "")[:300]
                score = item.get("relevance_score", 0.0)
                formatted += f"## Result {i} (relevance: {score:.2f})\n{content}\n\n"

            self.base.success_feedback(f"Found {len(memory_items)} relevant memories")
            return formatted

        except Exception as e:
            self.base.debug_log(f"Memory search error: {e}")
            return None

    def estimate_task_complexity(self, user_input: str) -> Dict[str, Any]:
        """
        Estimate task complexity to determine if protocol enforcement is needed.

        Args:
            user_input: User input text

        Returns:
            Dict with complexity analysis and enforcement decision
        """
        input_lower = user_input.lower()
        triggers = []

        # Trigger 1: Duration estimation (keywords indicating complexity)
        duration_keywords = [
            "implement", "build", "create", "refactor", "migrate",
            "integrate", "optimize", "design", "architect"
        ]
        if any(kw in input_lower for kw in duration_keywords):
            triggers.append("estimated_duration_>15min")

        # Trigger 2: Code implementation (explicit tool mentions)
        implementation_keywords = [
            "write code", "edit file", "modify", "update code",
            "add function", "create class", "implement feature"
        ]
        if any(kw in input_lower for kw in implementation_keywords):
            triggers.append("code_implementation_required")

        # Trigger 3: Architectural decisions
        architecture_keywords = [
            "architecture", "design pattern", "system design",
            "api design", "database schema", "integration"
        ]
        if any(kw in input_lower for kw in architecture_keywords):
            triggers.append("architectural_decisions_required")

        # Trigger 4: Multiple files/components
        multi_file_keywords = [
            "files", "components", "modules", "services",
            "multi-", "across", "integrate"
        ]
        if any(kw in input_lower for kw in multi_file_keywords):
            triggers.append("multiple_files_or_components")

        # Trigger 5: Research requirement
        research_keywords = [
            "research", "best practices", "how to", "documentation",
            "library", "framework", "pattern"
        ]
        if any(kw in input_lower for kw in research_keywords):
            triggers.append("context7_research_required")

        # Decision: Enforce if ANY trigger detected
        enforce = len(triggers) > 0

        return {
            "enforce_protocol": enforce,
            "triggers": triggers,
            "complexity_score": len(triggers),
            "user_input_preview": user_input[:100]
        }

    def generate_enforcement_prompt(self, complexity: Dict[str, Any]) -> str:
        """
        Generate enforcement gate prompt for user.

        Args:
            complexity: Complexity analysis from estimate_task_complexity

        Returns:
            Formatted enforcement prompt
        """
        triggers_formatted = "\n".join([f"  - {t.replace('_', ' ').title()}" for t in complexity["triggers"]])

        prompt = f"""⚠️ DevStream Protocol Required

**Detected Complexity Triggers**:
{triggers_formatted}

This task requires following the DevStream 7-step workflow:
DISCUSSION → ANALYSIS → RESEARCH → PLANNING → APPROVAL → IMPLEMENTATION → VERIFICATION

**OPTIONS**:
✅ [RECOMMENDED] Follow DevStream protocol (research-driven, quality-assured)
   - Context7 research for best practices
   - @code-reviewer validation (OWASP Top 10 security)
   - 95%+ test coverage requirement
   - Approval workflow (decisions documented)

⚠️  [OVERRIDE] Skip protocol (quick fix, NO quality assurance)
   - ❌ No Context7 research (potential outdated/incorrect patterns)
   - ❌ No @code-reviewer validation (security gaps)
   - ❌ No testing requirements (95%+ coverage waived)
   - ❌ No approval workflow (decisions undocumented)

**Choose**:
1. Follow Protocol (RECOMMENDED)
2. Override (explicit risk acknowledgment required)
Cancel"""

        return prompt

    async def check_protocol_enforcement(self, user_input: str) -> Optional[str]:
        """
        Check if protocol enforcement is required and return prompt if needed.

        Args:
            user_input: User input text

        Returns:
            Enforcement prompt if required, None otherwise
        """
        # Estimate complexity
        complexity = self.estimate_task_complexity(user_input)

        if not complexity["enforce_protocol"]:
            self.base.debug_log("Protocol enforcement not required (simple task)")
            return None

        self.base.debug_log(f"Protocol enforcement triggered: {complexity['triggers']}")

        # Generate enforcement prompt
        enforcement_prompt = self.generate_enforcement_prompt(complexity)

        # Store enforcement event in memory
        try:
            await self.base.safe_mcp_call(
                self.mcp_client,
                "devstream_store_memory",
                {
                    "content": f"Protocol enforcement triggered: {complexity['triggers']}. User input: {user_input[:200]}",
                    "content_type": "decision",
                    "keywords": ["protocol-enforcement", "complexity-analysis", "workflow-gate"]
                }
            )
        except Exception as e:
            self.base.debug_log(f"Failed to log enforcement event: {e}")

        return enforcement_prompt

    async def detect_task_lifecycle_event(self, user_input: str) -> Optional[Dict[str, str]]:
        """
        Detect task lifecycle events from user input.

        Args:
            user_input: User input text

        Returns:
            Event data if detected, None otherwise
        """
        input_lower = user_input.lower()

        # Task creation patterns
        if any(pattern in input_lower for pattern in [
            "create task",
            "new task",
            "add task",
            "start working on"
        ]):
            return {
                "event_type": "task_creation",
                "pattern": "User initiated new task",
                "query": user_input[:100]
            }

        # Task completion patterns
        elif any(pattern in input_lower for pattern in [
            "complete",
            "finished",
            "done with",
            "completed the",
            "task complete"
        ]):
            return {
                "event_type": "task_completion",
                "pattern": "User indicated task completion",
                "query": user_input[:100]
            }

        # Implementation progress patterns
        elif any(pattern in input_lower for pattern in [
            "implement",
            "build",
            "create",
            "working on"
        ]):
            return {
                "event_type": "implementation_progress",
                "pattern": "User starting implementation work",
                "query": user_input[:100]
            }

        return None

    async def assemble_enhanced_context(
        self,
        user_input: str
    ) -> Optional[str]:
        """
        Assemble enhanced context from multiple sources.

        Args:
            user_input: User input text

        Returns:
            Assembled enhanced context or None
        """
        context_parts = []

        # PRIORITY 1: Check protocol enforcement (MANDATORY)
        enforcement_prompt = await self.check_protocol_enforcement(user_input)
        if enforcement_prompt:
            context_parts.append(f"# Protocol Enforcement Gate\n\n{enforcement_prompt}")
            self.base.success_feedback("Protocol enforcement gate activated")

        # PRIORITY 2: Check if Context7 should trigger
        if await self.detect_context7_trigger(user_input):
            context7_docs = await self.get_context7_research(user_input)
            if context7_docs:
                context_parts.append(context7_docs)

        # PRIORITY 3: Search DevStream memory
        memory_context = await self.search_devstream_memory(user_input)
        if memory_context:
            context_parts.append(memory_context)

        # PRIORITY 4: Detect task lifecycle events
        task_event = await self.detect_task_lifecycle_event(user_input)
        if task_event:
            event_context = f"""# Task Lifecycle Event Detected

**Event Type**: {task_event['event_type']}
**Pattern**: {task_event['pattern']}

This query appears to be related to task management. Consider using TodoWrite for tracking progress.
"""
            context_parts.append(event_context)

        if not context_parts:
            return None

        # Assemble final context
        assembled = "\n\n---\n\n".join(context_parts)
        return f"# Enhanced Context for Query\n\n{assembled}"

    async def process(self, context: UserPromptSubmitContext) -> None:
        """
        Main hook processing logic.

        Args:
            context: UserPromptSubmit context from cchooks
        """
        # Check if hook should run
        if not self.base.should_run():
            self.base.debug_log("Hook disabled via config")
            context.output.exit_success()
            return

        # Extract user input
        user_input = context.user_input

        if not user_input or len(user_input) < 10:
            self.base.debug_log("User input too short for enhancement")
            context.output.exit_success()
            return

        self.base.debug_log(f"Processing user query: {len(user_input)} chars")

        try:
            # Assemble enhanced context
            enhanced_context = await self.assemble_enhanced_context(user_input)

            if enhanced_context:
                # Inject context
                self.base.inject_context(enhanced_context)
                self.base.success_feedback("Query context enhanced")
            else:
                self.base.debug_log("No relevant context found")

            # Always allow the operation to proceed
            context.output.exit_success()

        except Exception as e:
            # Non-blocking error - log and continue
            self.base.warning_feedback(f"Context enhancement failed: {str(e)[:50]}")
            context.output.exit_success()


def main():
    """Main entry point for UserPromptSubmit hook."""
    # Create context using cchooks
    ctx = safe_create_context()

    # Verify it's UserPromptSubmit context
    if not isinstance(ctx, UserPromptSubmitContext):
        print(f"Error: Expected UserPromptSubmitContext, got {type(ctx)}", file=sys.stderr)
        sys.exit(1)

    # Create and run hook
    hook = UserPromptSubmitHook()

    try:
        # Run async processing
        asyncio.run(hook.process(ctx))
    except Exception as e:
        # Graceful failure - non-blocking
        print(f"⚠️  DevStream: UserPromptSubmit error", file=sys.stderr)
        ctx.output.exit_non_block(f"Hook error: {str(e)[:100]}")


if __name__ == "__main__":
    main()