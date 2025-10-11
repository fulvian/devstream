#!/usr/bin/env python3
"""
DevStream Sequential Tool Executor
===================================

Utility for executing MCP tools sequentially to prevent concurrency conflicts.
Implements Context7 best practices for ordered execution with dependencies.

Features:
- Sequential tool execution with configurable delays
- Dependency management between tools
- Resource cleanup and error handling
- Progress tracking and logging
- Integration with concurrency guard and retry handler

Based on Claude Code MCP Enhanced sequential execution patterns.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

class ToolStatus(Enum):
    """Status of tool execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class ToolPriority(Enum):
    """Priority levels for tool execution"""
    CRITICAL = 1  # Essential tools (e.g., memory operations)
    HIGH = 2      # Important tools (e.g., context injection)
    NORMAL = 3    # Regular tools (e.g., documentation)
    LOW = 4       # Optional tools (e.g., analytics)

@dataclass
class ToolExecution:
    """Definition of a tool to execute"""
    tool_name: str
    tool_args: Dict[str, Any]
    priority: ToolPriority = ToolPriority.NORMAL
    dependencies: List[str] = None  # List of tool names this depends on
    timeout: float = 30.0
    retry_count: int = 0
    max_retries: int = 3
    delay_before: float = 0.0  # Delay before execution
    delay_after: float = 0.1   # Delay after execution
    status: ToolStatus = ToolStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

@dataclass
class ExecutionPlan:
    """Plan for executing tools in sequence"""
    tools: List[ToolExecution]
    max_parallel_tools: int = 1  # For future expansion
    default_timeout: float = 30.0
    default_delay: float = 0.1
    cleanup_on_failure: bool = True

@dataclass
class ExecutionResult:
    """Result of sequential tool execution"""
    success: bool
    total_tools: int
    completed_tools: int
    failed_tools: int
    skipped_tools: int
    total_duration: float
    tool_results: List[ToolExecution]
    errors: List[str]

class SequentialExecutor:
    """
    Sequential executor for MCP tools with dependency management.
    Implements Context7 best practices for ordered execution.
    """

    def __init__(self):
        self.execution_history: List[ExecutionResult] = []
        self.active_executions: Dict[str, ToolExecution] = {}

    def create_execution_plan(
        self,
        tools_data: List[Dict[str, Any]],
        priorities: Optional[Dict[str, ToolPriority]] = None,
        dependencies: Optional[Dict[str, List[str]]] = None
    ) -> ExecutionPlan:
        """
        Create execution plan from tool data.

        Args:
            tools_data: List of tool definitions with name and args
            priorities: Optional priority mapping for tools
            dependencies: Optional dependency mapping for tools

        Returns:
            ExecutionPlan with ordered tools
        """
        tools = []

        for tool_data in tools_data:
            tool_name = tool_data.get("tool_name") or tool_data.get("name", "unknown")
            tool_args = tool_data.get("tool_args", tool_data.get("args", {}))

            execution = ToolExecution(
                tool_name=tool_name,
                tool_args=tool_args,
                priority=priorities.get(tool_name, ToolPriority.NORMAL) if priorities else ToolPriority.NORMAL,
                dependencies=dependencies.get(tool_name, []) if dependencies else [],
                timeout=tool_data.get("timeout", 30.0),
                delay_before=tool_data.get("delay_before", 0.0),
                delay_after=tool_data.get("delay_after", 0.1)
            )
            tools.append(execution)

        # Sort by priority and dependencies
        sorted_tools = self._sort_tools_by_priority_and_dependencies(tools)

        return ExecutionPlan(
            tools=sorted_tools,
            cleanup_on_failure=True
        )

    def _sort_tools_by_priority_and_dependencies(self, tools: List[ToolExecution]) -> List[ToolExecution]:
        """
        Sort tools by priority and resolve dependencies.
        Implements topological sort for dependency resolution.
        """
        # Group by priority
        priority_groups = {}
        for tool in tools:
            priority = tool.priority.value
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(tool)

        # Sort within each priority group by dependencies
        sorted_tools = []
        for priority in sorted(priority_groups.keys()):
            group_tools = priority_groups[priority]
            sorted_group = self._topological_sort(group_tools)
            sorted_tools.extend(sorted_group)

        return sorted_tools

    def _topological_sort(self, tools: List[ToolExecution]) -> List[ToolExecution]:
        """
        Perform topological sort to respect dependencies.
        Returns tools in order where dependencies come first.
        """
        # Create mapping of tool name to tool
        tool_map = {tool.tool_name: tool for tool in tools}

        # Track visited and temporarily marked tools
        visited = set()
        temp_marked = set()
        result = []

        def visit(tool: ToolExecution):
            if tool.tool_name in temp_marked:
                raise ValueError(f"Circular dependency detected involving {tool.tool_name}")

            if tool.tool_name in visited:
                return

            temp_marked.add(tool.tool_name)

            # Visit dependencies first
            for dep_name in tool.dependencies:
                if dep_name in tool_map:
                    visit(tool_map[dep_name])
                else:
                    logger.warning(
                        "Dependency not found in tool list",
                        tool=tool.tool_name,
                        dependency=dep_name
                    )

            temp_marked.remove(tool.tool_name)
            visited.add(tool.tool_name)
            result.append(tool)

        for tool in tools:
            if tool.tool_name not in visited:
                visit(tool)

        return result

    async def execute_tool(self, tool: ToolExecution, tool_executor: Callable) -> bool:
        """
        Execute a single tool with error handling and logging.
        """
        logger.info(
            "Executing tool",
            tool=tool.tool_name,
            priority=tool.priority.name,
            dependencies=tool.dependencies,
            delay_before=tool.delay_before
        )

        # Add delay before execution
        if tool.delay_before > 0:
            await asyncio.sleep(tool.delay_before)

        tool.status = ToolStatus.RUNNING
        tool.started_at = datetime.utcnow()
        self.active_executions[tool.tool_name] = tool

        try:
            # Execute the tool
            result = await asyncio.wait_for(
                tool_executor(tool.tool_name, tool.tool_args),
                timeout=tool.timeout
            )

            tool.result = result
            tool.status = ToolStatus.COMPLETED
            tool.completed_at = datetime.utcnow()

            duration = (tool.completed_at - tool.started_at).total_seconds()

            logger.info(
                "Tool executed successfully",
                tool=tool.tool_name,
                duration=duration,
                delay_after=tool.delay_after
            )

            # Add delay after execution
            if tool.delay_after > 0:
                await asyncio.sleep(tool.delay_after)

            return True

        except asyncio.TimeoutError:
            tool.error = f"Tool execution timed out after {tool.timeout}s"
            tool.status = ToolStatus.FAILED
            tool.completed_at = datetime.utcnow()

            logger.error(
                "Tool execution timed out",
                tool=tool.tool_name,
                timeout=tool.timeout
            )
            return False

        except Exception as e:
            tool.error = str(e)
            tool.status = ToolStatus.FAILED
            tool.completed_at = datetime.utcnow()

            logger.error(
                "Tool execution failed",
                tool=tool.tool_name,
                error=str(e),
                retry_count=tool.retry_count,
                max_retries=tool.max_retries
            )
            return False

        finally:
            # Remove from active executions
            self.active_executions.pop(tool.tool_name, None)

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        tool_executor: Callable
    ) -> ExecutionResult:
        """
        Execute all tools in the plan sequentially.
        """
        logger.info(
            "Starting sequential tool execution",
            total_tools=len(plan.tools),
            max_parallel_tools=plan.max_parallel_tools
        )

        start_time = time.time()
        completed_count = 0
        failed_count = 0
        skipped_count = 0
        errors = []

        for tool in plan.tools:
            # Check if dependencies were satisfied
            if tool.dependencies:
                dependencies_satisfied = True
                for dep_name in tool.dependencies:
                    dep_tool = next((t for t in plan.tools if t.tool_name == dep_name), None)
                    if dep_tool and dep_tool.status != ToolStatus.COMPLETED:
                        dependencies_satisfied = False
                        tool.status = ToolStatus.SKIPPED
                        tool.error = f"Dependency {dep_name} was not completed"
                        skipped_count += 1

                        logger.warning(
                            "Tool skipped due to failed dependency",
                            tool=tool.tool_name,
                            dependency=dep_name
                        )
                        break

                if not dependencies_satisfied:
                    continue

            # Execute the tool
            success = await self.execute_tool(tool, tool_executor)

            if success:
                completed_count += 1
            else:
                failed_count += 1
                errors.append(f"{tool.tool_name}: {tool.error}")

                # Stop execution on critical tool failure if cleanup is enabled
                if plan.cleanup_on_failure and tool.priority == ToolPriority.CRITICAL:
                    logger.error(
                        "Critical tool failed, stopping execution",
                        tool=tool.tool_name,
                        error=tool.error
                    )
                    break

        total_duration = time.time() - start_time

        result = ExecutionResult(
            success=failed_count == 0,
            total_tools=len(plan.tools),
            completed_tools=completed_count,
            failed_tools=failed_count,
            skipped_tools=skipped_count,
            total_duration=total_duration,
            tool_results=plan.tools,
            errors=errors
        )

        self.execution_history.append(result)

        logger.info(
            "Sequential execution completed",
            success=result.success,
            completed=completed_count,
            failed=failed_count,
            skipped=skipped_count,
            duration=total_duration
        )

        return result

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of all executions"""
        if not self.execution_history:
            return {"total_executions": 0}

        total_executions = len(self.execution_history)
        total_tools = sum(r.total_tools for r in self.execution_history)
        total_completed = sum(r.completed_tools for r in self.execution_history)
        total_failed = sum(r.failed_tools for r in self.execution_history)
        total_duration = sum(r.total_duration for r in self.execution_history)

        success_rate = (total_completed / total_tools * 100) if total_tools > 0 else 0
        avg_duration = total_duration / total_executions if total_executions > 0 else 0

        return {
            "total_executions": total_executions,
            "total_tools_processed": total_tools,
            "total_completed": total_completed,
            "total_failed": total_failed,
            "success_rate_percent": round(success_rate, 2),
            "total_duration_seconds": round(total_duration, 2),
            "average_duration_seconds": round(avg_duration, 2),
            "active_executions": len(self.active_executions)
        }

# Convenience functions for common use cases
async def execute_mcp_tools_sequentially(
    tools_data: List[Dict[str, Any]],
    tool_executor: Callable,
    priorities: Optional[Dict[str, ToolPriority]] = None,
    dependencies: Optional[Dict[str, List[str]]] = None
) -> ExecutionResult:
    """
    Execute MCP tools sequentially with dependency management.
    Main entry point for sequential tool execution.
    """
    executor = SequentialExecutor()
    plan = executor.create_execution_plan(tools_data, priorities, dependencies)
    return await executor.execute_plan(plan, tool_executor)

# Example usage
if __name__ == "__main__":
    async def mock_tool_executor(tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """Mock tool executor for testing"""
        await asyncio.sleep(0.1)  # Simulate work
        if tool_name == "failing_tool":
            raise Exception("Mock failure for testing")
        return f"Mock result for {tool_name}"

    async def main():
        """Test the sequential executor"""
        tools_data = [
            {"tool_name": "memory_store", "args": {"content": "test"}},
            {"tool_name": "context_search", "args": {"query": "test"}, "dependencies": ["memory_store"]},
            {"tool_name": "failing_tool", "args": {}, "priority": "HIGH"},
            {"tool_name": "cleanup", "args": {}}
        ]

        priorities = {
            "memory_store": ToolPriority.CRITICAL,
            "context_search": ToolPriority.HIGH,
            "cleanup": ToolPriority.NORMAL
        }

        result = await execute_mcp_tools_sequentially(
            tools_data, mock_tool_executor, priorities
        )

        print(f"Success: {result.success}")
        print(f"Completed: {result.completed_tools}/{result.total_tools}")
        print(f"Duration: {result.total_duration:.2f}s")

        if result.errors:
            print("Errors:")
            for error in result.errors:
                print(f"  - {error}")

    asyncio.run(main())