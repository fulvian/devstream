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
DevStream PreToolUse Hook - Context Injection before Write/Edit
Context7 + DevStream hybrid context assembly con graceful fallback.
Agent Auto-Delegation System integration for intelligent agent routing.
"""

import sys
import asyncio
import os
from pathlib import Path
from typing import Optional, Dict, Any

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
sys.path.insert(0, str(Path(__file__).parent.parent))  # Add devstream hooks dir to path

from cchooks import safe_create_context, PreToolUseContext
from devstream_base import DevStreamHookBase
from context7_client import Context7Client
from mcp_client import get_mcp_client

# Agent Auto-Delegation imports (with graceful degradation)
try:
    from agents.pattern_matcher import PatternMatcher
    from agents.agent_router import AgentRouter, TaskAssessment
    AGENT_DELEGATION_AVAILABLE = True
except ImportError as e:
    AGENT_DELEGATION_AVAILABLE = False
    _IMPORT_ERROR = str(e)
    # Provide fallback type for type hints when delegation unavailable
    TaskAssessment = Any  # type: ignore


class PreToolUseHook:
    """
    PreToolUse hook for intelligent context injection.
    Combines Context7 library docs + DevStream semantic memory + Agent Auto-Delegation.
    """

    def __init__(self):
        self.base = DevStreamHookBase("pre_tool_use")
        self.mcp_client = get_mcp_client()
        self.context7 = Context7Client(self.mcp_client)

        # Agent Auto-Delegation components (graceful degradation)
        self.pattern_matcher: Optional[PatternMatcher] = None
        self.agent_router: Optional[AgentRouter] = None

        if AGENT_DELEGATION_AVAILABLE:
            try:
                self.pattern_matcher = PatternMatcher()
                self.agent_router = AgentRouter()
                self.base.debug_log("Agent Auto-Delegation enabled")
            except Exception as e:
                self.base.debug_log(f"Agent Auto-Delegation init failed: {e}")
        else:
            self.base.debug_log(f"Agent Auto-Delegation unavailable: {_IMPORT_ERROR}")

    async def get_context7_docs(self, file_path: str, content: str) -> Optional[str]:
        """
        Get Context7 documentation if relevant library detected.

        Args:
            file_path: Path to file being edited
            content: File content

        Returns:
            Formatted Context7 docs or None
        """
        try:
            # Build query from file path and content preview
            query = f"{file_path} {content[:500]}"

            # Check if Context7 should trigger
            if not await self.context7.should_trigger_context7(query):
                self.base.debug_log("Context7 not triggered for this file")
                return None

            self.base.debug_log("Context7 triggered - searching for docs")

            # Search and retrieve documentation
            result = await self.context7.search_and_retrieve(query)

            if result.success and result.docs:
                self.base.success_feedback(f"Context7 docs retrieved: {result.library_id}")
                return self.context7.format_docs_for_context(result)
            else:
                self.base.debug_log(f"Context7 search failed: {result.error}")
                return None

        except Exception as e:
            self.base.debug_log(f"Context7 error: {e}")
            return None

    async def get_devstream_memory(self, file_path: str, content: str) -> Optional[str]:
        """
        Search DevStream memory for relevant context.

        Args:
            file_path: Path to file being edited
            content: File content preview

        Returns:
            Formatted memory context or None
        """
        try:
            # Build search query
            query = f"{Path(file_path).name} {content[:300]}"

            self.base.debug_log(f"Searching DevStream memory: {query[:50]}...")

            # Search memory via MCP
            result = await self.base.safe_mcp_call(
                self.mcp_client,
                "devstream_search_memory",
                {
                    "query": query,
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

    async def check_agent_delegation(
        self,
        file_path: Optional[str],
        content: Optional[str],
        tool_name: Optional[str],
        user_query: Optional[str] = None
    ) -> Optional[TaskAssessment]:
        """
        Check if task should be delegated to specialized agent.

        Args:
            file_path: Optional file path being worked on
            content: Optional file content
            tool_name: Optional tool name (e.g., 'Write', 'Edit')
            user_query: Optional user query string

        Returns:
            TaskAssessment if delegation match found, None otherwise

        Note:
            Gracefully degrades if Agent Auto-Delegation unavailable
        """
        # Check if Agent Auto-Delegation is enabled via config
        if not os.getenv("DEVSTREAM_AGENT_AUTO_DELEGATION_ENABLED", "true").lower() == "true":
            self.base.debug_log("Agent Auto-Delegation disabled via config")
            return None

        # Check if components available
        if not self.pattern_matcher or not self.agent_router:
            return None

        try:
            # Match patterns
            pattern_match = self.pattern_matcher.match_patterns(
                file_path=file_path,
                content=content,
                user_query=user_query,
                tool_name=tool_name
            )

            if not pattern_match:
                self.base.debug_log("No agent pattern match found")
                return None

            # Assess task complexity
            context = {
                "file_path": file_path,
                "content": content,
                "user_query": user_query or "",
                "tool_name": tool_name,
                "affected_files": [file_path] if file_path else []
            }

            assessment = await self.agent_router.assess_task_complexity(
                pattern_match=pattern_match,
                context=context
            )

            self.base.debug_log(
                f"Agent delegation assessment: {assessment.recommendation} "
                f"({assessment.suggested_agent}, confidence={assessment.confidence:.2f})"
            )

            # Log delegation decision to DevStream memory (non-blocking)
            await self._log_delegation_decision(assessment, pattern_match)

            return assessment

        except Exception as e:
            # Non-blocking error - log and continue
            self.base.debug_log(f"Agent delegation check failed: {e}")
            return None

    async def _log_delegation_decision(
        self,
        assessment: TaskAssessment,
        pattern_match: Dict[str, Any]
    ) -> None:
        """
        Log delegation decision to DevStream memory.

        Args:
            assessment: Task assessment with delegation recommendation
            pattern_match: Pattern match information

        Note:
            Non-blocking - errors are logged but do not interrupt execution
        """
        # Check if memory is enabled
        if not os.getenv("DEVSTREAM_MEMORY_ENABLED", "true").lower() == "true":
            return

        try:
            # Format delegation decision log
            agent = assessment.suggested_agent
            confidence = assessment.confidence
            recommendation = assessment.recommendation
            reason = assessment.reason
            complexity = assessment.complexity
            impact = assessment.architectural_impact

            content = (
                f"Agent Delegation: @{agent} (confidence {confidence:.2f}, {recommendation})\n"
                f"Reason: {reason}\n"
                f"Complexity: {complexity} | Impact: {impact}"
            )

            # Extract keywords
            keywords = [
                "agent-delegation",
                agent,
                recommendation.lower(),
                complexity.lower()
            ]

            # Store in memory via MCP
            await self.base.safe_mcp_call(
                self.mcp_client,
                "devstream_store_memory",
                {
                    "content": content,
                    "content_type": "decision",
                    "keywords": keywords
                }
            )

            self.base.debug_log(f"Delegation decision logged to memory: @{agent}")

        except Exception as e:
            # Non-blocking error - log and continue
            self.base.debug_log(f"Failed to log delegation decision: {e}")

    async def assemble_context(
        self,
        file_path: str,
        content: str
    ) -> Optional[str]:
        """
        Assemble hybrid context from Context7 + DevStream memory.

        Args:
            file_path: File being edited
            content: File content

        Returns:
            Assembled context string or None
        """
        context_parts = []

        # Get Context7 docs (if relevant)
        context7_docs = await self.get_context7_docs(file_path, content)
        if context7_docs:
            context_parts.append(context7_docs)

        # Get DevStream memory
        memory_context = await self.get_devstream_memory(file_path, content)
        if memory_context:
            context_parts.append(memory_context)

        if not context_parts:
            return None

        # Assemble final context
        assembled = "\n\n---\n\n".join(context_parts)
        return f"# Enhanced Context for {Path(file_path).name}\n\n{assembled}"

    async def process(self, context: PreToolUseContext) -> None:
        """
        Main hook processing logic.
        Integrates Agent Auto-Delegation + Context7 + DevStream memory.

        Args:
            context: PreToolUse context from cchooks
        """
        # Check if hook should run
        if not self.base.should_run():
            self.base.debug_log("Hook disabled via config")
            context.output.exit_success()
            return

        # Extract tool information
        tool_name = context.tool_name
        tool_input = context.tool_input

        self.base.debug_log(f"Processing {tool_name} for {tool_input.get('file_path', 'unknown')}")

        # Only process Write/Edit operations
        if tool_name not in ["Write", "Edit", "MultiEdit"]:
            context.output.exit_success()
            return

        # Extract file information
        file_path = tool_input.get("file_path", "")
        content = tool_input.get("content", "") or tool_input.get("new_string", "")

        if not file_path:
            self.base.debug_log("No file path in tool input")
            context.output.exit_success()
            return

        try:
            context_parts = []

            # PHASE 1: Agent Auto-Delegation (BEFORE Context7/memory injection)
            try:
                assessment = await self.check_agent_delegation(
                    file_path=file_path,
                    content=content,
                    tool_name=tool_name,
                    user_query=None  # user_query not available in PreToolUse context
                )

                if assessment and self.agent_router:
                    # Format advisory message
                    advisory_message = self.agent_router.format_advisory_message(assessment)

                    # Prepend advisory to context injection
                    advisory_header = (
                        "# Agent Auto-Delegation Advisory\n\n"
                        f"{advisory_message}\n\n"
                        "---\n\n"
                    )
                    context_parts.append(advisory_header)

                    self.base.success_feedback(
                        f"Agent delegation: {assessment.recommendation} "
                        f"({assessment.suggested_agent})"
                    )

            except Exception as e:
                # Non-blocking error - log and continue
                self.base.debug_log(f"Agent delegation failed: {e}")

            # PHASE 2: Context7 + DevStream memory injection
            enhanced_context = await self.assemble_context(file_path, content)
            if enhanced_context:
                context_parts.append(enhanced_context)

            # PHASE 3: Inject assembled context
            if context_parts:
                final_context = "\n".join(context_parts)
                self.base.inject_context(final_context)
                self.base.success_feedback(f"Context injected for {Path(file_path).name}")
            else:
                self.base.debug_log("No relevant context found")

            # Always allow the operation to proceed
            context.output.exit_success()

        except Exception as e:
            # Non-blocking error - log and continue
            self.base.warning_feedback(f"Context injection failed: {str(e)[:50]}")
            context.output.exit_success()


def main():
    """Main entry point for PreToolUse hook."""
    # Create context using cchooks
    ctx = safe_create_context()

    # Verify it's PreToolUse context
    if not isinstance(ctx, PreToolUseContext):
        print(f"Error: Expected PreToolUseContext, got {type(ctx)}", file=sys.stderr)
        sys.exit(1)

    # Create and run hook
    hook = PreToolUseHook()

    try:
        # Run async processing
        asyncio.run(hook.process(ctx))
    except Exception as e:
        # Graceful failure - non-blocking
        print(f"⚠️  DevStream: PreToolUse error", file=sys.stderr)
        ctx.output.exit_non_block(f"Hook error: {str(e)[:100]}")


if __name__ == "__main__":
    main()