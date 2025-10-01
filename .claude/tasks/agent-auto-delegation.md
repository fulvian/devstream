# Agent Auto-Delegation System

**Status**: 🔵 Planning
**Priority**: High
**Created**: 2025-10-01
**Type**: Architecture + Implementation

## Objective

Design and implement an intelligent agent auto-delegation system that automatically invokes the most appropriate specialist agent based on context, file patterns, and task characteristics.

## Problem Statement

Currently, agents must be invoked manually (`@agent-name`) or coordinated explicitly via `@tech-lead`. This creates friction:

❌ **Manual Overhead**: User must remember which agent to invoke
❌ **Context Switching**: User must identify correct specialist
❌ **Missed Opportunities**: Proactive agent suggestions not always actioned
❌ **Inconsistent Quality**: Pre-commit reviews (@code-reviewer) may be skipped

**Goal**: Automate agent delegation while maintaining user control and transparency.

## Success Criteria

✅ **Accuracy**: 90%+ correct agent selection based on context
✅ **Transparency**: User sees which agent was auto-invoked and why
✅ **Control**: User can override/disable auto-delegation
✅ **Performance**: < 100ms agent selection latency
✅ **DevStream Compliance**: Follows 7-step methodology

## Proposed Approaches

### Approach 1: Pattern-Based Auto-Delegation (Hook System)
**Trigger**: File path/content patterns in tool calls (Write, Edit, Read)

```python
# Example: PreToolUse hook detects patterns
if tool == "Write" and file_path.endswith("_test.py"):
    auto_invoke("@testing-specialist")

if tool == "Edit" and "password" in file_content:
    auto_invoke("@security-auditor")

if tool == "Write" and "alembic/versions/" in file_path:
    auto_invoke("@migration-specialist")
```

**Pros**:
- Fast (pattern matching)
- Deterministic (predictable behavior)
- Easy to configure (rules-based)

**Cons**:
- Brittle (may miss nuanced cases)
- Requires manual rule maintenance
- Limited context understanding

### Approach 2: LLM-Based Agent Router (Intelligent Selection)
**Trigger**: Analyze user request + current context → select agent

```python
# Example: Router analyzes user request
user_request = "Fix memory leak in production API"
context = {
    "recent_files": ["api.py", "cache.py"],
    "recent_errors": ["MemoryError", "Heap exhausted"],
    "git_branch": "hotfix/memory-leak"
}

router_llm_response = analyze_and_route(user_request, context)
# Output: "@debugger (reason: production issue + memory leak keywords)"

auto_invoke("@debugger", context=context)
```

**Pros**:
- Intelligent (understands nuance)
- Context-aware (considers multiple signals)
- Adaptive (learns from patterns)

**Cons**:
- Slower (LLM inference ~500ms)
- Non-deterministic (may vary)
- Requires token budget management

### Approach 3: Hybrid (Pattern + LLM Fallback)
**Trigger**: Try pattern matching first, fallback to LLM for ambiguous cases

```python
# Fast path: Pattern-based rules (90% of cases)
if matches_pattern(tool, file_path, content):
    return pattern_based_agent

# Slow path: LLM analysis (10% ambiguous cases)
else:
    return llm_based_agent_selection(context)
```

**Pros**:
- Best of both worlds (fast + intelligent)
- Fallback safety (LLM catches edge cases)
- Cost-efficient (LLM only when needed)

**Cons**:
- Complex implementation
- Requires pattern catalog maintenance
- LLM fallback tuning needed

### Approach 4: User-Trained Auto-Delegation (Learning System)
**Trigger**: Learn from user's explicit agent invocations over time

```python
# Track user patterns
user_history = {
    "when 'authentication' in task": "@security-auditor (80% of time)",
    "when '.sql' file": "@database-specialist (95% of time)",
    "when 'bug' + 'production'": "@debugger (100% of time)"
}

# Suggest based on learned patterns
if confidence > 0.8:
    auto_invoke(predicted_agent)
else:
    suggest_agent(predicted_agent, confidence)
```

**Pros**:
- Personalized (adapts to user style)
- Improves over time (learning)
- High confidence predictions

**Cons**:
- Requires training period (cold start)
- May reinforce bad habits
- Privacy concerns (tracking)

## Implementation Phases

### Phase 1: Pattern-Based Auto-Delegation (Week 1-2)
**Deliverables**:
- Hook: `agent_auto_delegator.py` (PreToolUse integration)
- Pattern rules: File patterns, content keywords, tool types
- Configuration: `.env.devstream` flags for enable/disable
- Testing: 50+ pattern test cases

**Patterns to Implement**:
```yaml
# Security patterns
- pattern: "auth|password|jwt|oauth|security|crypto"
  agent: "@security-auditor"
  confidence: high

# Testing patterns
- pattern: "_test.py$|test_.*\\.py$|tests/"
  agent: "@testing-specialist"
  confidence: high

# Migration patterns
- pattern: "alembic/versions/|migrations/|schema\\.sql"
  agent: "@migration-specialist"
  confidence: high

# Debugging patterns
- pattern: "bug|error|crash|leak|debug|production.*issue"
  agent: "@debugger"
  confidence: medium

# Integration patterns
- pattern: "stripe|twilio|aws|oauth2|webhook|api.*integration"
  agent: "@integration-specialist"
  confidence: high

# Refactoring patterns
- pattern: "refactor|legacy|technical.*debt|code.*smell"
  agent: "@refactoring-specialist"
  confidence: high
```

### Phase 2: LLM Router (Week 3-4)
**Deliverables**:
- LLM router service (Claude API integration)
- Context aggregation (files, errors, git state)
- Confidence scoring (0-1 scale)
- Fallback logic (pattern → LLM)

**Router Architecture**:
```python
class AgentRouter:
    def route(self, user_request: str, context: dict) -> AgentSelection:
        # Fast path: Pattern matching
        pattern_match = self.pattern_matcher.match(user_request, context)
        if pattern_match.confidence > 0.9:
            return pattern_match.agent

        # Slow path: LLM analysis
        llm_selection = self.llm_router.analyze(user_request, context)
        return llm_selection.agent
```

### Phase 3: Quality Gate Automation (Week 5)
**Deliverables**:
- Auto-invoke @code-reviewer before commits (MANDATORY)
- Auto-invoke @security-auditor for auth/crypto code
- Auto-invoke @testing-specialist when coverage drops
- Pre-commit hook integration

### Phase 4: User Control & Transparency (Week 6)
**Deliverables**:
- User approval prompts (opt-in/opt-out per agent)
- Delegation reasoning display ("Why this agent?")
- Override mechanism (user can reject/change agent)
- Analytics dashboard (delegation accuracy tracking)

## Technical Design

### Hook Integration Points

**1. PreToolUse Hook** (Before tool execution)
```python
# .claude/hooks/devstream/agents/agent_auto_delegator.py
def pre_tool_use(tool_name: str, tool_input: dict, context: dict):
    """Auto-delegate to specialist agent based on context."""

    # Analyze context
    agent_selection = router.route(
        tool_name=tool_name,
        tool_input=tool_input,
        recent_history=context.get("recent_tools", []),
        file_patterns=extract_file_patterns(tool_input),
        keywords=extract_keywords(tool_input)
    )

    if agent_selection.confidence > CONFIDENCE_THRESHOLD:
        if should_auto_invoke(agent_selection.agent):
            inject_agent_invocation(agent_selection.agent, context)
            log_delegation(agent_selection, reason="auto")
        else:
            suggest_agent(agent_selection.agent, agent_selection.reason)
```

**2. UserPromptSubmit Hook** (User query analysis)
```python
# Analyze user query for agent keywords
if "security audit" in user_query:
    suggest_agent("@security-auditor")

if "debug" in user_query and "production" in user_query:
    suggest_agent("@debugger")
```

**3. Pre-Commit Hook** (Quality gate - MANDATORY)
```python
# Always invoke @code-reviewer before commit
if git_action == "commit":
    auto_invoke("@code-reviewer", files=staged_files)
```

### Configuration Schema

```bash
# .env.devstream additions

# Agent Auto-Delegation
DEVSTREAM_AGENT_AUTO_DELEGATION_ENABLED=true
DEVSTREAM_AGENT_CONFIDENCE_THRESHOLD=0.8
DEVSTREAM_AGENT_AUTO_INVOKE_ENABLED=true  # false = suggest only
DEVSTREAM_AGENT_ROUTER_MODE=hybrid  # pattern|llm|hybrid

# Per-Agent Controls
DEVSTREAM_AUTO_DELEGATE_SECURITY_AUDITOR=true
DEVSTREAM_AUTO_DELEGATE_DEBUGGER=true
DEVSTREAM_AUTO_DELEGATE_REFACTORING_SPECIALIST=true
DEVSTREAM_AUTO_DELEGATE_INTEGRATION_SPECIALIST=true
DEVSTREAM_AUTO_DELEGATE_MIGRATION_SPECIALIST=true

# Quality Gates (MANDATORY overrides)
DEVSTREAM_MANDATORY_CODE_REVIEW_ON_COMMIT=true
DEVSTREAM_MANDATORY_SECURITY_AUDIT_ON_AUTH=true
```

## Research Questions (Context7)

1. **Agent Orchestration Patterns**: Research existing multi-agent systems (AutoGPT, LangChain agents)
2. **LLM Routing**: Best practices for LLM-based task routing
3. **Hook Performance**: Claude Code hook system performance characteristics
4. **User Experience**: Optimal UX for auto-delegation (transparency vs automation)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Incorrect Agent Selection** | User frustration, wasted time | Confidence threshold tuning, user override |
| **Performance Overhead** | Slow tool execution | Pattern-first (fast path), LLM fallback only |
| **User Confusion** | "Why was this agent invoked?" | Clear reasoning display, delegation logs |
| **Over-Automation** | Loss of user control | Opt-in/opt-out per agent, approval prompts |
| **Token Budget** | LLM routing costs | Pattern matching for 90% of cases |

## Acceptance Criteria

### Functional Requirements
- ✅ Pattern-based delegation working for 10+ file/content patterns
- ✅ LLM router fallback for ambiguous cases
- ✅ @code-reviewer auto-invoked before every commit
- ✅ User can override agent selection
- ✅ Delegation reasoning displayed to user

### Non-Functional Requirements
- ✅ < 100ms pattern matching latency
- ✅ < 500ms LLM routing latency (fallback only)
- ✅ 90%+ delegation accuracy (user satisfaction)
- ✅ Zero false negatives for security/testing agents
- ✅ Graceful degradation if routing fails

### DevStream Compliance
- ✅ Follows 7-step methodology (DISCUSSIONE → VERIFICA)
- ✅ Context7 research for agent orchestration patterns
- ✅ TodoWrite breakdown for implementation phases
- ✅ Memory storage for delegation analytics
- ✅ Testing: 95%+ coverage for routing logic

## Timeline Estimate

- **Week 1**: Phase 1 - Pattern-based delegation (hook implementation)
- **Week 2**: Phase 1 - Testing & refinement (50+ test cases)
- **Week 3**: Phase 2 - LLM router (Claude API integration)
- **Week 4**: Phase 2 - Hybrid routing (pattern + LLM fallback)
- **Week 5**: Phase 3 - Quality gate automation (pre-commit)
- **Week 6**: Phase 4 - User controls & analytics

**Total**: ~6 weeks (with Context7 research and testing)

## Next Steps

1. **DISCUSSIONE**: Review approaches with user, select optimal strategy
2. **ANALISI**: Analyze current hook system capabilities
3. **RICERCA**: Context7 research on multi-agent orchestration
4. **PIANIFICAZIONE**: Detailed task breakdown (TodoWrite)
5. **APPROVAZIONE**: User approval on technical design
6. **IMPLEMENTAZIONE**: Phase 1 implementation
7. **VERIFICA**: Testing & validation

## Related Documentation

- `.claude/agents/README.md` - Agent system overview
- `.claude/agents/orchestrator/tech-lead.md` - Current orchestration patterns
- `.claude/hooks/devstream/memory/pre_tool_use.py` - Hook system reference
- `CLAUDE.md` - Agent usage patterns

---

**Task Type**: Architecture + Research + Implementation
**Methodology**: Research-Driven Development (Context7)
**Status**: Ready for DISCUSSIONE phase
