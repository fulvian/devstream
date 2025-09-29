#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.0.0",
#     "python-dotenv>=1.0.0",
#     "aiohttp>=3.8.0",
#     "structlog>=23.0.0",
# ]
# ///

"""
DevStream User Query Context Enhancer - Enhanced UserPromptSubmit Hook
Context7-compliant intelligent context enhancement per user queries con semantic memory.
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

# Import Intelligent Context Injector
sys.path.append(str(Path(__file__).parent))
from intelligent_context_injector import IntelligentContextInjector

# Import Task Lifecycle Manager
sys.path.append(str(Path(__file__).parent.parent / 'tasks'))
from task_lifecycle_manager import TaskLifecycleManager, TaskLifecycleEvent

class UserQueryContextEnhancer(DevStreamHookBase):
    """
    Enhanced UserPromptSubmit hook con intelligent context injection.
    Combina memory storage, context enhancement e task lifecycle management.
    """

    def __init__(self):
        super().__init__('user_query_context_enhancer')
        self.structured_logger = get_devstream_logger('user_query_context_enhancer')
        self.mcp_client = get_mcp_client()
        self.start_time = time.time()

        # Initialize intelligent systems
        self.context_injector = IntelligentContextInjector()
        self.lifecycle_manager = TaskLifecycleManager()

        # Enhanced processing configuration
        self.enable_context_enhancement = True
        self.enable_task_lifecycle = True
        self.min_query_length = 10
        self.context_injection_threshold = 0.5

    async def process_enhanced_user_prompt(self, input_data: dict) -> None:
        """
        Process user prompt con enhanced context injection e task lifecycle management.

        Args:
            input_data: JSON input from Claude Code UserPromptSubmit
        """
        self.structured_logger.log_hook_start(input_data, {
            "phase": "enhanced_user_prompt_processing"
        })

        try:
            # Extract user input
            user_input = input_data.get('user_input', '')
            session_id = input_data.get('session_id', 'unknown')

            if len(user_input) < self.min_query_length:
                self.logger.debug("User input too short for enhancement")
                self.success_exit()
                return

            self.logger.info(f"Processing enhanced user prompt: {len(user_input)} chars")

            # 1. Store user prompt in memory (always)
            await self.store_user_prompt(user_input, session_id)

            # 2. Intelligent context enhancement
            enhanced_context = None
            if self.enable_context_enhancement:
                enhanced_context = await self.enhance_query_context(user_input, session_id)

            # 3. Task lifecycle management
            if self.enable_task_lifecycle:
                await self.handle_task_lifecycle_implications(user_input, session_id)

            # 4. Inject enhanced context if significant
            if enhanced_context and self.should_inject_context(enhanced_context, user_input):
                await self.inject_enhanced_context(enhanced_context)
                self.logger.info("Enhanced context injected for user query")

            # 5. Generate continuation hints if applicable
            continuation_hints = await self.generate_continuation_hints(user_input)
            if continuation_hints:
                await self.inject_continuation_hints(continuation_hints)

            # Log performance metrics
            execution_time = (time.time() - self.start_time) * 1000
            self.structured_logger.log_performance_metrics(execution_time)

            self.logger.info(f"Enhanced user prompt processing completed")

        except Exception as e:
            self.structured_logger.log_hook_error(e, {"user_input": user_input})
            raise

    async def store_user_prompt(self, user_input: str, session_id: str) -> None:
        """
        Store user prompt in DevStream memory.

        Args:
            user_input: User input text
            session_id: Session ID
        """
        # Classify prompt type
        prompt_type = self.classify_prompt_type(user_input)

        # Extract keywords
        keywords = self.extract_keywords(user_input)

        # Create memory content
        memory_content = (
            f"USER QUERY [{session_id}]: {user_input}. "
            f"Type: {prompt_type}, Keywords: {', '.join(keywords[:5])}, "
            f"Timestamp: {datetime.now().isoformat()}"
        )

        # Store in memory
        await self.mcp_client.store_memory(
            content=memory_content,
            content_type="context",
            keywords=keywords + ["user-query", prompt_type, session_id[:8]]
        )

        # Log memory operation
        self.structured_logger.log_memory_operation(
            operation="store",
            content_type="context",
            content_size=len(memory_content),
            keywords=keywords[:3]
        )

    def classify_prompt_type(self, user_input: str) -> str:
        """
        Classify user prompt type.

        Args:
            user_input: User input

        Returns:
            Prompt classification
        """
        input_lower = user_input.lower()

        # Implementation requests
        if any(keyword in input_lower for keyword in [
            'implement', 'create', 'build', 'develop', 'make', 'add'
        ]):
            return 'implementation'

        # Debug/fix requests
        elif any(keyword in input_lower for keyword in [
            'fix', 'debug', 'error', 'problem', 'issue', 'bug'
        ]):
            return 'debugging'

        # Questions/explanation requests
        elif any(keyword in input_lower for keyword in [
            'what', 'how', 'why', 'explain', 'show', 'tell'
        ]):
            return 'question'

        # Analysis requests
        elif any(keyword in input_lower for keyword in [
            'analyze', 'review', 'check', 'examine', 'look'
        ]):
            return 'analysis'

        # Task management
        elif any(keyword in input_lower for keyword in [
            'task', 'todo', 'complete', 'finish', 'done'
        ]):
            return 'task_management'

        # General conversation
        else:
            return 'general'

    def extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from user input.

        Args:
            text: Input text

        Returns:
            List of keywords
        """
        # Use the same extraction method as intelligent context injector
        from intelligent_context_injector import IntelligentContextInjector
        injector = IntelligentContextInjector()
        return injector.extract_key_terms(text)

    async def enhance_query_context(self, user_input: str, session_id: str) -> Optional[str]:
        """
        Enhance user query with intelligent context.

        Args:
            user_input: User input
            session_id: Session ID

        Returns:
            Enhanced context or None
        """
        query_context = {
            'user_input': user_input,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        }

        # Use intelligent context injector
        enhanced_context = await self.context_injector.inject_intelligent_context(
            query_context=query_context,
            tool_context=None
        )

        return enhanced_context

    async def handle_task_lifecycle_implications(self, user_input: str, session_id: str) -> None:
        """
        Handle task lifecycle implications of user query.

        Args:
            user_input: User input
            session_id: Session ID
        """
        input_lower = user_input.lower()

        # Check for task-related implications
        event_data = {
            'user_input': user_input,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        }

        # Task creation implications
        if any(keyword in input_lower for keyword in [
            'new task', 'create task', 'add task'
        ]):
            await self.lifecycle_manager.handle_lifecycle_event(
                TaskLifecycleEvent.TASK_CREATED,
                event_data
            )

        # Task completion implications
        elif any(keyword in input_lower for keyword in [
            'complete', 'finished', 'done with'
        ]):
            await self.lifecycle_manager.handle_lifecycle_event(
                TaskLifecycleEvent.TASK_COMPLETED,
                event_data
            )

        # General task progress implications
        elif any(keyword in input_lower for keyword in [
            'working on', 'implementing', 'building'
        ]):
            await self.lifecycle_manager.handle_lifecycle_event(
                TaskLifecycleEvent.PROGRESS_UPDATE,
                event_data
            )

    def should_inject_context(self, context: str, user_input: str) -> bool:
        """
        Determine if context should be injected.

        Args:
            context: Enhanced context
            user_input: User input

        Returns:
            True if context should be injected
        """
        # Don't inject for very short contexts
        if len(context) < 200:
            return False

        # Always inject for implementation and debugging queries
        input_lower = user_input.lower()
        high_value_patterns = [
            'implement', 'create', 'build', 'fix', 'debug', 'error',
            'devstream', 'hook', 'memory', 'task'
        ]

        if any(pattern in input_lower for pattern in high_value_patterns):
            return True

        # Check context relevance
        context_lower = context.lower()
        query_terms = set(user_input.lower().split())
        context_terms = set(context_lower.split())

        # Calculate overlap
        overlap = len(query_terms.intersection(context_terms))
        if overlap >= 3:  # Significant term overlap
            return True

        return False

    async def inject_enhanced_context(self, context: str) -> None:
        """
        Inject enhanced context.

        Args:
            context: Context to inject
        """
        # Enhance context with user-friendly formatting
        enhanced_context = f"""
🔍 DevStream Context Enhancement

{context}

💡 This enhanced context was assembled from your previous work and DevStream's semantic memory to help provide more relevant and informed responses.

---
"""

        # Output enhanced context
        self.output_context(enhanced_context)

        # Log injection
        self.structured_logger.log_context_injection(
            context_type="enhanced_user_context",
            content_size=len(enhanced_context),
            keywords=["user-query", "enhancement", "devstream"]
        )

    async def generate_continuation_hints(self, user_input: str) -> Optional[str]:
        """
        Generate continuation hints for user query.

        Args:
            user_input: User input

        Returns:
            Continuation hints or None
        """
        input_lower = user_input.lower()

        # Implementation hints
        if any(keyword in input_lower for keyword in ['implement', 'create', 'build']):
            # Check if this relates to current active tasks
            current_tasks = await self.get_current_active_tasks()

            if current_tasks:
                task_titles = [task.get('title', '') for task in current_tasks[:3]]
                hints = [
                    "💼 Active DevStream Tasks:",
                    *[f"   • {title}" for title in task_titles if title],
                    "",
                    "Consider breaking implementation into TodoWrite tasks for better tracking."
                ]
                return '\n'.join(hints)

        # Task management hints
        elif 'task' in input_lower and any(keyword in input_lower for keyword in ['complete', 'done', 'finish']):
            return """
📋 Task Completion Tips:
   • Use TodoWrite to mark tasks as completed
   • The DevStream system will auto-detect completion patterns
   • Progress is automatically tracked and stored in memory
"""

        # Hook development hints
        elif 'hook' in input_lower:
            return """
🔗 DevStream Hook Development:
   • All hooks are located in .claude/hooks/devstream/
   • Follow Context7-compliant UV script patterns
   • Include structured logging and error handling
   • Test hooks individually before integration
"""

        return None

    async def inject_continuation_hints(self, hints: str) -> None:
        """
        Inject continuation hints.

        Args:
            hints: Hints to inject
        """
        hint_context = f"""
{hints}

---
"""

        self.output_context(hint_context)

    async def get_current_active_tasks(self) -> List[Dict[str, Any]]:
        """
        Get current active tasks.

        Returns:
            List of active tasks
        """
        try:
            tasks_response = await self.mcp_client.list_tasks(status="active")

            if tasks_response and tasks_response.get('content'):
                content = tasks_response.get('content', [])
                if content and len(content) > 0:
                    text_content = content[0].get('text', '')
                    # Parse tasks from response (simplified)
                    if "Task ID:" in text_content:
                        return [{"title": "Hook System Implementation", "id": "active-1"}]

        except Exception as e:
            self.logger.warning(f"Failed to get active tasks: {e}")

        return []

async def main():
    """Main hook execution following Context7 patterns."""
    enhancer = UserQueryContextEnhancer()

    try:
        # Read JSON input from stdin (Context7 pattern)
        input_data = enhancer.read_stdin_json()

        # Process enhanced user prompt
        await enhancer.process_enhanced_user_prompt(input_data)

        # Success exit
        enhancer.success_exit()

    except Exception as e:
        enhancer.error_exit(f"User query context enhancer failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())