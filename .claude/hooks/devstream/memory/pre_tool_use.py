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
DevStream PreToolUse Hook - Context Injection dalla Memoria
Context7-compliant intelligent context injection da DevStream semantic memory.
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

# Import Intelligent Context Injector
sys.path.append(str(Path(__file__).parent.parent / 'context'))
from intelligent_context_injector import IntelligentContextInjector

class PreToolUseHook(DevStreamHookBase):
    """
    PreToolUse hook per intelligent context injection da memoria semantica.
    Implementa Context7-validated patterns per context assembly.
    """

    def __init__(self):
        super().__init__('pre_tool_use')
        self.structured_logger = get_devstream_logger('pre_tool_use')
        self.start_time = time.time()

        # Initialize intelligent context injector
        self.context_injector = IntelligentContextInjector()

        # Legacy fallback thresholds (for compatibility)
        self.min_relevance_threshold = 0.3
        self.max_context_tokens = 1000
        self.max_memories = 5

    async def process_tool_call(self, input_data: dict) -> None:
        """
        Process tool call e inject relevant context.

        Args:
            input_data: JSON input from Claude Code PreToolUse
        """
        self.structured_logger.log_hook_start(input_data, {"phase": "pre_tool_use"})

        try:
            # Extract tool information
            tool_name = input_data.get('tool_name', 'unknown')
            tool_input = input_data.get('tool_input', {})
            session_id = input_data.get('session_id', 'unknown')

            # Determine if context injection is needed
            injection_needed = await self.should_inject_context(tool_name, tool_input)

            if not injection_needed:
                self.logger.debug(f"No context injection needed for {tool_name}")
                self.success_exit()
                return

            # Generate context query from tool call
            context_query = await self.generate_context_query(tool_name, tool_input)

            # Use intelligent context injection
            tool_context = {
                'tool_name': tool_name,
                'tool_input': tool_input,
                'session_id': session_id
            }

            intelligent_context = await self.context_injector.inject_intelligent_context(
                query_context={},  # Empty query context for tool-driven injection
                tool_context=tool_context
            )

            # Inject intelligent context if found
            if intelligent_context:
                await self.inject_context(intelligent_context)
                self.logger.info(f"Injected intelligent context for {tool_name}")
            else:
                # Fallback to legacy context retrieval
                context_query = await self.generate_context_query(tool_name, tool_input)
                legacy_context = await self.retrieve_context(context_query, session_id)

                if legacy_context:
                    await self.inject_context(legacy_context)
                    self.logger.info(f"Injected legacy context for {tool_name}")
                else:
                    self.logger.debug(f"No relevant context found for {tool_name}")

            # Log performance metrics
            execution_time = (time.time() - self.start_time) * 1000
            self.structured_logger.log_performance_metrics(execution_time)

        except Exception as e:
            self.structured_logger.log_hook_error(e, {"tool_name": tool_name})
            raise

    async def should_inject_context(self, tool_name: str, tool_input: Dict[str, Any]) -> bool:
        """
        Determine if context injection is beneficial per questo tool call.

        Args:
            tool_name: Name of tool being called
            tool_input: Tool input parameters

        Returns:
            True if context injection should be performed
        """
        # Always inject for MCP DevStream tools
        if tool_name.startswith('mcp__devstream__'):
            return True

        # Inject for code editing operations
        if tool_name in ['Edit', 'MultiEdit', 'Write', 'NotebookEdit']:
            # Check if working on DevStream-related files
            file_path = tool_input.get('file_path', '')
            if any(keyword in file_path.lower() for keyword in [
                'devstream', 'hook', 'memory', 'task', 'claude'
            ]):
                return True

        # Inject for search operations that might benefit from context
        if tool_name in ['Grep', 'Glob', 'WebSearch']:
            pattern_or_query = tool_input.get('pattern', tool_input.get('query', ''))
            if any(keyword in pattern_or_query.lower() for keyword in [
                'devstream', 'memory', 'hook', 'task', 'claude', 'mcp'
            ]):
                return True

        # Inject for bash commands related to DevStream
        if tool_name == 'Bash':
            command = tool_input.get('command', '')
            if any(keyword in command.lower() for keyword in [
                'devstream', 'uv run', '.claude', 'hook', 'mcp'
            ]):
                return True

        return False

    async def generate_context_query(
        self,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """
        Generate search query per context retrieval.

        Args:
            tool_name: Tool name
            tool_input: Tool input parameters

        Returns:
            Context search query
        """
        query_parts = [tool_name]

        # Add specific query parts based on tool type
        if tool_name in ['Edit', 'MultiEdit', 'Write']:
            file_path = tool_input.get('file_path', '')
            if file_path:
                # Add file extension and directory
                path_obj = Path(file_path)
                query_parts.append(path_obj.suffix.lstrip('.'))
                query_parts.extend(path_obj.parts[-2:])  # Last 2 path components

            # Add content keywords if available
            content = tool_input.get('new_string', tool_input.get('content', ''))
            if content:
                # Extract key terms from content
                content_words = content.split()[:10]  # First 10 words
                query_parts.extend([w for w in content_words if len(w) > 3])

        elif tool_name == 'Bash':
            command = tool_input.get('command', '')
            command_words = command.split()[:5]  # First 5 command words
            query_parts.extend(command_words)

        elif tool_name in ['Grep', 'Glob']:
            pattern = tool_input.get('pattern', '')
            query_parts.append(pattern)

        elif tool_name.startswith('mcp__devstream__'):
            # Extract MCP operation
            operation = tool_name.replace('mcp__devstream__', '')
            query_parts.append(operation)

            # Add specific parameters
            if 'query' in tool_input:
                query_parts.append(tool_input['query'])
            if 'content_type' in tool_input:
                query_parts.append(tool_input['content_type'])

        # Clean and join query parts
        query_parts = [part.strip() for part in query_parts if part.strip()]
        return ' '.join(query_parts[:8])  # Limit query length

    async def retrieve_context(
        self,
        query: str,
        session_id: str
    ) -> Optional[str]:
        """
        Retrieve relevant context from DevStream memory.

        Args:
            query: Context search query
            session_id: Current session ID

        Returns:
            Assembled context string or None
        """
        # Search DevStream memory via MCP
        search_params = {
            'query': query,
            'limit': self.max_memories,
            'content_type': None  # Search all types
        }

        search_response = await self.call_devstream_mcp(
            'devstream_search_memory',
            search_params
        )

        if not search_response:
            self.logger.warning("Failed to search DevStream memory")
            return None

        # Extract and process search results
        memories = self.extract_memory_results(search_response)

        if not memories:
            return None

        # Assemble context with token budget
        assembled_context = await self.assemble_context(memories, query)

        # Log context retrieval
        self.structured_logger.log_context_injection(
            context_type="memory_retrieval",
            content_size=len(assembled_context) if assembled_context else 0,
            keywords=query.split()[:5]
        )

        return assembled_context

    def extract_memory_results(self, search_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract memory results from MCP response.

        Args:
            search_response: MCP search response

        Returns:
            List of memory entries
        """
        # This would need to parse actual MCP response format
        # For now, simulate the structure
        memories = []

        # Extract from response content (placeholder logic)
        content = search_response.get('content', [])
        if content and len(content) > 0:
            text_content = content[0].get('text', '')

            # Simple parsing - in real implementation would parse structured results
            if 'Memory ID' in text_content and 'Content Preview' in text_content:
                # Simulate extracted memory
                memories.append({
                    'id': 'simulated-memory-id',
                    'content': text_content[:500],
                    'relevance_score': 0.8,
                    'content_type': 'context',
                    'keywords': []
                })

        return memories

    async def assemble_context(
        self,
        memories: List[Dict[str, Any]],
        query: str
    ) -> str:
        """
        Assemble context from memories con token budget management.

        Args:
            memories: List of memory entries
            query: Original query

        Returns:
            Assembled context string
        """
        if not memories:
            return ""

        context_parts = [
            "📋 DevStream Context (from memory):",
            f"🔍 Query: {query}",
            ""
        ]

        current_tokens = self.estimate_tokens(' '.join(context_parts))

        for i, memory in enumerate(memories[:self.max_memories]):
            memory_content = memory.get('content', '')
            memory_tokens = self.estimate_tokens(memory_content)

            # Check token budget
            if current_tokens + memory_tokens > self.max_context_tokens:
                break

            # Add memory to context
            relevance = memory.get('relevance_score', 0.0)
            memory_preview = memory_content[:200] + "..." if len(memory_content) > 200 else memory_content

            context_parts.extend([
                f"💾 Memory {i+1} (relevance: {relevance:.2f}):",
                memory_preview,
                ""
            ])

            current_tokens += memory_tokens

        # Add footer
        context_parts.extend([
            "---",
            "🎯 Use this context to inform your approach and maintain consistency with DevStream patterns."
        ])

        return '\n'.join(context_parts)

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        # Simple estimation: ~4 characters per token
        return len(text) // 4

    async def inject_context(self, context: str) -> None:
        """
        Inject context into Claude Code stream.

        Args:
            context: Context string to inject
        """
        # Output context (Context7 pattern)
        self.output_context(context)

        # Log injection
        self.structured_logger.log_context_injection(
            context_type="devstream_memory",
            content_size=len(context),
            keywords=context.split()[:10]
        )

    def should_approve_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Optional[str]:
        """
        Determine if tool should be auto-approved con context.

        Args:
            tool_name: Tool name
            tool_input: Tool input

        Returns:
            Approval reason or None
        """
        # Auto-approve DevStream MCP tools
        if tool_name.startswith('mcp__devstream__'):
            return "DevStream MCP operation - auto-approved with context"

        # Auto-approve DevStream-related file operations
        if tool_name in ['Edit', 'MultiEdit', 'Write']:
            file_path = tool_input.get('file_path', '')
            if 'devstream' in file_path.lower() or '.claude' in file_path:
                return "DevStream file operation - auto-approved with context"

        return None

async def main():
    """Main hook execution following Context7 patterns."""
    hook = PreToolUseHook()

    try:
        # Read JSON input from stdin (Context7 pattern)
        input_data = hook.read_stdin_json()

        # Process the tool call
        await hook.process_tool_call(input_data)

        # Check for auto-approval
        tool_name = input_data.get('tool_name', 'unknown')
        tool_input = input_data.get('tool_input', {})

        approval_reason = hook.should_approve_tool(tool_name, tool_input)
        if approval_reason:
            hook.approve_with_reason(approval_reason)
        else:
            # Success exit without approval
            hook.success_exit()

    except Exception as e:
        hook.error_exit(f"PreToolUse hook failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())