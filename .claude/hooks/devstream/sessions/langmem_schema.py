#!/usr/bin/env python3
"""
DevStream LangMem-Enhanced Schema - Episodic & Semantic Memory Structures

Implements LangMem/LangGraph memory patterns for AI coding agents:
- Episodic Memory: observation → thoughts → action → result (retrospective learning)
- Semantic Memory: structured facts, preferences, and technical decisions
- Importance Scoring: explicit priority levels for memory retrieval

Research Sources:
- LangMem (/langchain-ai/langmem): Memory extraction patterns
- LangGraph (/websites/python_langchain-langgraph): Persistent state management
- Industry Research: Windsurf Cascade Memories, Anthropic Claude memory

Context7 Patterns:
- Pydantic BaseModel for structured memory extraction
- Explicit importance scoring (critical/high/medium/low)
- Retrospective reasoning capture ("what worked, what could improve")
"""

from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class ImportanceLevel(str, Enum):
    """
    Memory importance level for retrieval prioritization.

    Based on LangMem importance scoring and Windsurf Cascade Memories patterns.
    """
    CRITICAL = "critical"  # 🔴 Critical: Core bugs, architectural decisions, blocking issues
    HIGH = "high"          # 🟡 High: Significant features, important patterns, quality improvements
    MEDIUM = "medium"      # 🟢 Medium: Standard implementations, minor fixes, documentation
    LOW = "low"            # ⚪ Low: Routine tasks, trivial changes, formatting


class EpisodicMemory(BaseModel):
    """
    Episodic memory for AI agents: captures learning from experience.

    LangMem Pattern: Record episodes from the agent's perspective with
    the benefit of hindsight, saving key internal thought processes for
    learning over time.

    Structure:
    - observation: What happened (context and setup)
    - thoughts: Internal reasoning ("I noticed X, so I reasoned Y...")
    - action: What was done, how, and in what format
    - result: Outcome + retrospective ("What worked well, what could improve")
    - importance: Explicit priority for retrieval

    Example:
        EpisodicMemory(
            observation="SessionEnd generated empty summaries despite having extraction logic",
            thoughts="I analyzed the data flow and realized NO DATA was being written. "
                     "I searched for WorkSessionManager.update_session_progress() calls and found NONE.",
            action="Used Grep to search all hooks, identified PostToolUse had tracking code "
                   "but did direct DB writes instead of calling WorkSessionManager.",
            result="Root cause identified. Works well for debugging. Next time: always trace "
                   "full data flow (write → read) when debugging empty queries.",
            importance=ImportanceLevel.CRITICAL,
            tags=["debugging", "root-cause-analysis", "data-flow"]
        )
    """

    observation: str = Field(
        ...,
        description="The context and setup - what happened in this episode"
    )

    thoughts: str = Field(
        ...,
        description="Internal reasoning process. What did the agent notice? "
                   "What logic led to the action? Written in first person: 'I noticed..., so I...'"
    )

    action: str = Field(
        ...,
        description="What was done, how, and in what format. Include whatever is "
                   "salient to the success of the action. Written in first person: 'I implemented...'"
    )

    result: str = Field(
        ...,
        description="Outcome and retrospective. What worked well? What could be improved "
                   "next time? Written in first person: 'This worked because... Next time I should...'"
    )

    importance: ImportanceLevel = Field(
        ...,
        description="Importance level for retrieval prioritization (critical/high/medium/low)"
    )

    tags: List[str] = Field(
        default_factory=list,
        description="Searchable tags for this episode (e.g., 'debugging', 'context7', 'performance')"
    )

    timestamp: Optional[datetime] = Field(
        default_factory=datetime.now,
        description="When this episode occurred"
    )


class SemanticMemory(BaseModel):
    """
    Semantic memory for AI agents: structured facts and relationships.

    LangMem Pattern: Store facts, preferences, and relationships as structured
    triples (subject, predicate, object) for efficient retrieval.

    Structure:
    - subject: The entity (e.g., "WorkSessionManager", "Context7 pattern", "DevStream")
    - predicate: The relationship (e.g., "provides", "requires", "implements")
    - object: The value or related entity (e.g., "session tracking", "async with", "memory system")
    - context: Additional context (optional)
    - importance: Explicit priority for retrieval

    Examples:
        SemanticMemory(
            subject="WorkSessionManager",
            predicate="provides_method",
            object="update_session_progress(tokens_delta, active_tasks, active_files)",
            context="Single source of truth for session updates - use this instead of direct DB writes",
            importance=ImportanceLevel.HIGH,
            category="architecture"
        )

        SemanticMemory(
            subject="Context7 aiosqlite pattern",
            predicate="requires",
            object="async with aiosqlite.connect() + explicit commits",
            context="Prevents connection leaks and ensures proper transaction handling",
            importance=ImportanceLevel.MEDIUM,
            category="best-practice"
        )
    """

    subject: str = Field(
        ...,
        description="The entity or concept this fact is about"
    )

    predicate: str = Field(
        ...,
        description="The relationship or property (verb or property name)"
    )

    object: str = Field(
        ...,
        description="The value, related entity, or object of the relationship"
    )

    context: Optional[str] = Field(
        None,
        description="Additional context or explanation for this fact"
    )

    importance: ImportanceLevel = Field(
        ...,
        description="Importance level for retrieval prioritization (critical/high/medium/low)"
    )

    category: Literal[
        "architecture",      # System design, patterns, abstractions
        "decision",          # Technical decisions, trade-offs
        "preference",        # User preferences, coding style
        "best-practice",     # Context7 patterns, industry standards
        "anti-pattern",      # Things to avoid, common mistakes
        "tool",              # Libraries, frameworks, CLI tools
        "fact"               # General facts, relationships
    ] = Field(
        default="fact",
        description="Category of this semantic memory for filtering"
    )

    tags: List[str] = Field(
        default_factory=list,
        description="Searchable tags for this fact"
    )

    timestamp: Optional[datetime] = Field(
        default_factory=datetime.now,
        description="When this fact was learned"
    )


class CrossSessionContext(BaseModel):
    """
    Cross-session context: pending work and recommendations for next session.

    Enables continuity between sessions by capturing:
    - What's pending (incomplete work, verification needed)
    - What should be done next (immediate actions, follow-ups)
    - What patterns emerged (architecture insights, anti-patterns)

    Structure:
    - pending_work: List of incomplete items with priority
    - recommendations: List of suggested next actions
    - patterns_observed: List of patterns noticed during session
    """

    pending_work: List[str] = Field(
        default_factory=list,
        description="Incomplete work items (e.g., 'Test token tracking on next prompt', "
                   "'Verify SessionEnd summary after restart')"
    )

    immediate_actions: List[str] = Field(
        default_factory=list,
        description="Recommended immediate actions for next session "
                   "(e.g., 'Exit and restart to test enhanced summary', "
                   "'Add integration test for hook execution')"
    )

    follow_up_tasks: List[str] = Field(
        default_factory=list,
        description="Non-urgent follow-up tasks "
                   "(e.g., 'Replace ~4 chars/token with tiktoken for precision', "
                   "'Add structlog.contextvars.bind_contextvars for session logging')"
    )

    patterns_observed: List[str] = Field(
        default_factory=list,
        description="Patterns noticed during session "
                   "(e.g., 'Memory Bank active context tracking pattern', "
                   "'Presence of code != automatic execution - explicit calls required')"
    )

    anti_patterns_avoided: List[str] = Field(
        default_factory=list,
        description="Anti-patterns identified and avoided "
                   "(e.g., 'Direct DB writes bypass abstraction layer', "
                   "'Async context managers without explicit commits leak connections')"
    )


class ImpactMetrics(BaseModel):
    """
    Impact metrics: before/after comparison for measurable outcomes.

    Quantifies session impact with concrete metrics:
    - Tasks completed
    - Files modified
    - Code quality improvements
    - Performance gains
    - Test coverage changes

    Structure:
    - before: State before changes
    - after: State after changes
    - improvement: Calculated improvement (percentage or delta)
    """

    metric_name: str = Field(
        ...,
        description="Name of the metric (e.g., 'Tasks Completed', 'Test Coverage', 'Response Time')"
    )

    before: str = Field(
        ...,
        description="State before changes (e.g., '0 tasks', '75% coverage', '500ms')"
    )

    after: str = Field(
        ...,
        description="State after changes (e.g., '6 tasks', '95% coverage', '200ms')"
    )

    improvement: Optional[str] = Field(
        None,
        description="Calculated improvement (e.g., '+600%', '+20 percentage points', '-60% latency')"
    )

    description: Optional[str] = Field(
        None,
        description="Brief explanation of the impact"
    )


if __name__ == "__main__":
    # Test script - validate schema
    print("LangMem-Enhanced Schema Test")
    print("=" * 60)

    # Test 1: EpisodicMemory
    print("\n1. Testing EpisodicMemory schema...")
    episode = EpisodicMemory(
        observation="SessionEnd generated empty summaries despite having extraction logic",
        thoughts="I analyzed the data flow: SessionEnd → SessionDataExtractor → work_sessions query. "
                 "The query returned 0 values. This meant NO DATA was being written. "
                 "I searched for who calls WorkSessionManager.update_session_progress() and found NOBODY.",
        action="Used Grep to search all hooks for update_session_progress calls. "
               "Found it defined in WorkSessionManager but never invoked. "
               "Refactored PostToolUse to use WorkSessionManager abstraction.",
        result="Root cause identified and fixed. Abstraction layer pattern works well for maintainability. "
               "Next time: Always trace full data flow (write → read) when debugging empty queries.",
        importance=ImportanceLevel.CRITICAL,
        tags=["debugging", "root-cause-analysis", "abstraction-layer"]
    )
    print(f"   ✅ EpisodicMemory created: {episode.importance.value}")
    print(f"   Tags: {', '.join(episode.tags)}")

    # Test 2: SemanticMemory
    print("\n2. Testing SemanticMemory schema...")
    fact1 = SemanticMemory(
        subject="WorkSessionManager",
        predicate="provides_method",
        object="update_session_progress(tokens_delta, active_tasks, active_files)",
        context="Single source of truth for session updates",
        importance=ImportanceLevel.HIGH,
        category="architecture",
        tags=["session-tracking", "abstraction"]
    )
    print(f"   ✅ SemanticMemory created: {fact1.subject} {fact1.predicate} {fact1.object}")
    print(f"   Category: {fact1.category}, Importance: {fact1.importance.value}")

    fact2 = SemanticMemory(
        subject="Context7 aiosqlite pattern",
        predicate="requires",
        object="async with aiosqlite.connect() + explicit commits",
        context="Prevents connection leaks",
        importance=ImportanceLevel.MEDIUM,
        category="best-practice",
        tags=["context7", "aiosqlite", "async"]
    )
    print(f"   ✅ SemanticMemory created: {fact2.subject}")

    # Test 3: CrossSessionContext
    print("\n3. Testing CrossSessionContext schema...")
    context = CrossSessionContext(
        pending_work=[
            "Test token tracking with next user prompt",
            "Verify SessionEnd summary after restart"
        ],
        immediate_actions=[
            "Exit and restart Claude Code to test enhanced summary",
            "Send a message to trigger UserPromptSubmit hook"
        ],
        follow_up_tasks=[
            "Replace ~4 chars/token estimation with tiktoken library",
            "Add integration test for hook execution verification"
        ],
        patterns_observed=[
            "Memory Bank active context tracking (not time-based)",
            "Context7 async with pattern for database operations"
        ],
        anti_patterns_avoided=[
            "Direct DB writes bypass abstraction layer",
            "Presence of code != automatic execution"
        ]
    )
    print(f"   ✅ CrossSessionContext created")
    print(f"   Pending work: {len(context.pending_work)} items")
    print(f"   Immediate actions: {len(context.immediate_actions)} items")

    # Test 4: ImpactMetrics
    print("\n4. Testing ImpactMetrics schema...")
    metric1 = ImpactMetrics(
        metric_name="Tasks Completed",
        before="0 tasks",
        after="6 tasks",
        improvement="+600%",
        description="Session tracking now captures active TodoWrite tasks"
    )
    print(f"   ✅ ImpactMetrics created: {metric1.metric_name}")
    print(f"   {metric1.before} → {metric1.after} ({metric1.improvement})")

    metric2 = ImpactMetrics(
        metric_name="Summary Usefulness",
        before="0% (empty data)",
        after="95% (actionable context)",
        improvement="+95 percentage points",
        description="Cross-session context preservation now functional"
    )
    print(f"   ✅ ImpactMetrics created: {metric2.metric_name}")
    print(f"   {metric2.before} → {metric2.after}")

    print("\n" + "=" * 60)
    print("Schema validation complete! ✅")
    print("\nKey Features:")
    print("  - LangMem episodic memory (observation/thoughts/action/result)")
    print("  - Semantic memory with structured triples")
    print("  - Importance scoring (critical/high/medium/low)")
    print("  - Cross-session context and recommendations")
    print("  - Impact metrics with before/after comparison")
