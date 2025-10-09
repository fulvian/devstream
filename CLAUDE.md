# CLAUDE.md - DevStream Project Rules

**Version**: 2.2.0 | **Date**: 2025-10-09 | **Status**: Production Ready - Protocol v2.2.0 (Strategic Choice Gate)

⚠️ **CRITICAL**: These rules are **MANDATORY** and integrated into the DevStream system through automatic hooks. Violating them may cause system malfunctions.

---

## 🎯 DevStream System Architecture

DevStream combines: (1) Task Lifecycle Management, (2) Semantic Memory System, (3) Context Injection (Context7 + DevStream Memory), (4) Hook Automation (PreToolUse, PostToolUse, UserPromptSubmit via cchooks).

**🔄 Automatic System**: Hooks automatically execute memory storage and context injection without manual intervention.

---

## 🤖 Custom Agent System - Multi-Stack Development

**Status**: Phase 3 Complete ✅ | 8 Agents + Auto-Delegation Production Ready

### Agent Architecture (4-Level Hierarchy)

```
Level 1: ORCHESTRATOR (@tech-lead) - Task decomposition, multi-agent coordination, architectural decisions
         └── TIER-BASED DELEGATION (Protocol v2.2.0 ✅) - Complexity-based intelligent routing
Level 2: DOMAIN SPECIALISTS (6 agents ✅)
  @python-specialist     - Python 3.11+, FastAPI, Django, async, pytest, type-safe
  @typescript-specialist - TypeScript, React, Next.js, Server Components, hooks, optimization
  @rust-specialist       - Ownership, async/await, zero-cost abstractions, cargo, memory safety
  @go-specialist         - Goroutines, channels, cloud-native, idiomatic Go, table-driven tests
  @database-specialist   - PostgreSQL/MySQL/SQLite, schema design, indexing, query tuning
  @devops-specialist     - Docker, Kubernetes, CI/CD, IaC, GitOps, production deployment
Level 3: TASK SPECIALISTS (Phase 3+) - @api-architect, @performance-optimizer, @testing-specialist
Level 4: QUALITY ASSURANCE - @code-reviewer (OWASP Top 10, performance, architecture - MANDATORY before commits)
```

### Agent Usage Patterns

**Direct Invocation** (single-language): `@python-specialist Create FastAPI endpoint for user auth`
**Orchestrated Workflow** (multi-stack): `@tech-lead Build full-stack user management system` → tech-lead delegates @python-specialist (backend) → @typescript-specialist (frontend) → @code-reviewer (validation)
**Quality Gate** (MANDATORY): `@code-reviewer Review implementation in src/api/users.py:45-120`

### Agent Capabilities

| Agent | Use Case | Capability | Tools |
|-------|----------|------------|-------|
| **@tech-lead** | Multi-stack features, architectural decisions | Task decomposition, agent delegation, coordination | Task, Read, Glob, Grep (restricted) |
| **@python-specialist** | Python 3.11+, FastAPI, async development | Type-safe Python, async patterns, pytest testing | Full tool access |
| **@typescript-specialist** | TypeScript, React, Next.js APIs | Server Components, hooks, performance optimization | Full tool access |
| **@rust-specialist** | Rust systems programming | Ownership, async/await, zero-cost abstractions | Full tool access |
| **@go-specialist** | Go cloud-native services | Goroutines, channels, simplicity-first design | Full tool access |
| **@database-specialist** | Database design, optimization | PostgreSQL/MySQL/SQLite, schema, query tuning | Full tool access |
| **@devops-specialist** | Containerization, CI/CD | Docker, Kubernetes, IaC, GitOps | Full tool access |
| **@code-reviewer** | Quality, security validation | OWASP Top 10, performance, architecture review | Read, Grep, Glob, Bash (restricted) |

### When to Use Which Agent

- **@tech-lead**: Feature spans Python + TypeScript, architectural decisions, multi-specialist coordination
- **@python-specialist**: Pure Python (FastAPI, async, testing), backend API, database models
- **@typescript-specialist**: Pure TypeScript/React, frontend components, Next.js Server Components
- **@code-reviewer**: BEFORE every git commit (MANDATORY), security-sensitive code, performance-critical paths

### Example Workflow: JWT Authentication

```bash
# Step 1: Orchestration
@tech-lead Analyze requirements and delegate implementation
# Output: Python backend (JWT auth, password hashing) + TypeScript frontend (login form, auth context)

# Step 2: Backend → Task(@python-specialist): Implement FastAPI JWT auth (endpoints, token generation, user model)
# Step 3: Frontend → Task(@typescript-specialist): Implement React auth UI (LoginForm, AuthContext, ProtectedRoute)
# Step 4: Quality Review → @code-reviewer Review auth implementation (OWASP checks, JWT secret management)
```

### Agent Configuration

**Location**: `.claude/agents/` → `orchestrator/tech-lead.md`, `domain/{python,typescript,rust,go,database,devops}-specialist.md`, `qa/code-reviewer.md`

### Agent Principles (MANDATORY)

1. **Isolated Context**: Each agent has independent context window
2. **Tool Inheritance**: Domain specialists have full tool access (omit `tools:` field)
3. **Tool Restriction**: Orchestrators/QA restrict tools for focus (specify `tools:` field)
4. **Delegation Pattern**: Use `Task` tool for orchestrator → specialist invocation
5. **Quality First**: ALWAYS invoke @code-reviewer before task completion

### Memory Optimization

**Problem Solved**: JavaScript heap exhaustion during agent execution
**Fix**: `node --max-old-space-size=8192 --expose-gc start-production.js` (8GB heap, explicit GC, memory cleanup)
**Status**: Production stable ✅

### Tier-Based Delegation Policy (Protocol v2.2.0 - Token Optimization)

**Purpose**: Optimize token consumption while preserving all 17 agents via strategic tier-based delegation.

**Status**: ✅ Production Ready | **Impact**: -70% token overhead average (-5700 tokens/task)

#### Policy Structure (4 Tiers)

**TIER 1: Monolithic First** (60% of tasks - 0 overhead)
- **Trigger**: Single file, <50K tokens, <1h duration, straightforward implementation
- **Agent**: NONE (Sonnet 4.5 solo, no delegation)
- **Token Overhead**: 0 tokens
- **Examples**: Bug fixes, single endpoint implementation, documentation updates, config changes
- **Decision**: Default for simple, well-defined tasks

**TIER 2: Single Specialist** (30% of tasks - 2K overhead)
- **Trigger**: File pattern match (*.py → @python-specialist) + single-language focus
- **Agent**: 1 specialist ONLY (no @tech-lead coordination)
- **Token Overhead**: ~2K tokens (Context7 + Memory for 1 specialist)
- **File Pattern Mapping**:
  - `.py` → @python-specialist
  - `.ts/.tsx` → @typescript-specialist
  - `.sql` schema → @database-specialist
  - `.md` docs → @documentation-specialist
  - `.rs` → @rust-specialist
  - `.go` → @go-specialist
- **Decision**: Clear language-specific task, no multi-stack coordination

**TIER 3: Multi-Agent Orchestration** (5% of tasks - 7K overhead)
- **Trigger**: Multi-stack (Python + TypeScript + DB) OR >100K context OR architectural decisions
- **Agent**: @tech-lead → delegates N specialists
- **Token Overhead**: ~7K tokens (Context7 5K + Memory 2K)
- **Examples**: Full-stack features, system-wide refactoring, cross-component changes
- **Decision**: Requires coordination across multiple languages/domains

**TIER 4: Quality Gate** (5% of tasks - MANDATORY - 1K overhead)
- **Trigger**: `git commit` command (automatic detection)
- **Agent**: @code-reviewer (ALWAYS, non-negotiable)
- **Token Overhead**: ~1K tokens (code analysis only)
- **Examples**: EVERY commit, EVERY security-sensitive change
- **Decision**: Mandatory quality gate (cannot be skipped)

#### Configuration (.env.devstream)

```bash
# Tier-Based Delegation (Protocol v2.2.0)
DEVSTREAM_AUTO_DELEGATION_TIER1_ENABLED=true   # Monolithic first (default)
DEVSTREAM_AUTO_DELEGATION_TIER2_THRESHOLD=0.95 # Single specialist confidence
DEVSTREAM_AUTO_DELEGATION_TIER3_THRESHOLD=0.70 # Multi-agent coordination
DEVSTREAM_AUTO_DELEGATION_QUALITY_GATE=true    # Mandatory @code-reviewer
```

#### Decision Algorithm

```python
def get_delegation_tier(context: Dict[str, Any]) -> Tuple[int, Optional[str], float]:
    """
    Determine delegation tier based on task context.

    Returns:
        (tier_number, agent_name, confidence)
    """
    # Tier 1: Monolithic (no delegation)
    if is_simple_task(context):
        # Single file, <50K tokens, <1h, straightforward
        return (1, None, 1.0)

    # Tier 2: Single specialist
    if has_clear_file_pattern(context) and is_single_language(context):
        # File pattern match: *.py → @python-specialist
        agent = match_specialist_by_file(context["file_path"])
        return (2, agent, 0.95)

    # Tier 3: Multi-agent orchestration
    if is_multi_stack(context) or context.get("context_size", 0) > 100_000:
        # Python + TypeScript + DB OR >100K tokens
        return (3, "@tech-lead", 0.70)

    # Tier 4: Quality gate (MANDATORY)
    if is_commit_operation(context):
        # Every git commit triggers @code-reviewer
        return (4, "@code-reviewer", 1.0)

    # Default: Tier 1 (monolithic)
    return (1, None, 1.0)
```

#### Token Optimization Impact

**Before (Always Multi-Agent)**:
- Average task: 7K tokens overhead per task
- Claude Code Max limit: 28 tasks/5h
- Token budget: 200K tokens
- Overhead: ~28% of context (56K/200K)

**After (Tier-Based)**:
- Tier 1 (60%): 0 tokens × 60% = 0 tokens
- Tier 2 (30%): 2K tokens × 30% = 600 tokens
- Tier 3 (5%): 7K tokens × 5% = 350 tokens
- Tier 4 (5%): 1K tokens × 5% = 50 tokens
- **Average**: 1000 tokens/task (-86% reduction)
- **Claude Code Max**: 28 → 100 tasks/5h (3.5x improvement)
- **Token budget**: 5K → 1K overhead (-70% average)

#### Usage Examples

**Example 1: Tier 1 (Monolithic - Bug Fix)**
```bash
# User request
"Fix typo in error message in src/utils/logger.py line 42"

# Delegation Decision
Context Analysis:
  - Single file: ✅
  - <50K tokens: ✅
  - <1h duration: ✅ (~5 min)
  - Straightforward: ✅

Decision: TIER 1 (Monolithic)
Agent: None (Sonnet 4.5 solo)
Token Overhead: 0 tokens
Execution: Direct implementation, no agent delegation
```

**Example 2: Tier 2 (Single Specialist - Python)**
```bash
# User request
"Refactor src/api/users.py to use async/await patterns"

# Delegation Decision
Context Analysis:
  - File pattern: *.py → @python-specialist
  - Single language: ✅ (Python only)
  - Confidence: 0.95

Decision: TIER 2 (Single Specialist)
Agent: @python-specialist
Token Overhead: 2K tokens
Execution: Direct specialist delegation, no @tech-lead
```

**Example 3: Tier 3 (Multi-Agent - Full-Stack)**
```bash
# User request
"Build user dashboard with Python backend, React frontend, and PostgreSQL"

# Delegation Decision
Context Analysis:
  - Multi-stack: ✅ (Python + TypeScript + SQL)
  - Languages: 3 (Python, TypeScript, SQL)
  - Coordination required: ✅

Decision: TIER 3 (Multi-Agent Orchestration)
Agent: @tech-lead → delegates @python-specialist, @typescript-specialist, @database-specialist
Token Overhead: 7K tokens
Execution: @tech-lead coordinates sequential delegation
```

**Example 4: Tier 4 (Quality Gate - MANDATORY)**
```bash
# User request
"Commit the authentication changes"

# Delegation Decision
Context Analysis:
  - Git commit detected: ✅
  - Mandatory quality gate: ✅

Decision: TIER 4 (Quality Gate)
Agent: @code-reviewer (MANDATORY)
Token Overhead: 1K tokens
Execution: OWASP Top 10 + performance + architecture review
Bypass: FORBIDDEN (enforced by hook system)
```

#### All 17 Agents Preserved

**CRITICAL**: This policy does NOT reduce the number of agents. All 17 agents remain available:

**Level 1 - Orchestrator**: @tech-lead
**Level 2 - Domain Specialists** (6 agents):
- @python-specialist
- @typescript-specialist
- @rust-specialist
- @go-specialist
- @database-specialist
- @devops-specialist

**Level 3 - Task Specialists** (5 agents):
- @api-architect
- @performance-optimizer
- @testing-specialist
- @documentation-specialist
- @refactoring-specialist

**Level 4 - QA Specialists** (5 agents):
- @code-reviewer (MANDATORY quality gate)
- @security-auditor
- @debugger
- @integration-specialist
- @migration-specialist

**Optimization Strategy**: Use agents *strategically* based on task complexity, not *always*.

#### Cost Analysis (Claude Code Pro Max $100/month)

**Token Budget**: 200K tokens/session

**Before Optimization**:
- Task overhead: 7K tokens (always multi-agent)
- Tasks per session: 200K / 7K ≈ 28 tasks
- Tasks per 5h: 28 tasks
- Monthly capacity: ~28 × 30 = 840 tasks

**After Optimization**:
- Task overhead: 1K tokens average (tier-based)
- Tasks per session: 200K / 1K ≈ 200 tasks
- Tasks per 5h: 100 tasks (3.5x improvement)
- Monthly capacity: ~100 × 30 = 3000 tasks (3.5x increase)

**Cost Savings**: $100 now covers 3.5x more work (equivalent to $280 value at old rate)

### Future Phases

**Phase 4** (Advanced): @security-auditor, @debugger, @refactoring-specialist, @integration-specialist
**Phase 5** (Specialization): Fine-tuning pattern matcher, learning from delegation history

---

## 📋 PRESCRIPTIVE RULES - DevStream Methodology

### 🚨 ENFORCEMENT GATE - Protocol Compliance (MANDATORY)

**CRITICAL**: DevStream protocol is MANDATORY for all non-trivial tasks. Claude Code will STOP and request confirmation before proceeding.

#### Enforcement Trigger Criteria

Protocol enforcement triggers when **ANY** of these conditions are met:
1. Estimated task duration > 15 minutes
2. Task requires code implementation (Write, Edit tools)
3. Task requires architectural decisions
4. Task involves multiple files or components
5. Task requires Context7 research

#### Enforcement Flow

```
User Request
    ↓
Claude Code Complexity Analysis
    ↓
┌────────────────────────────────────────────┐
│ IF task meets enforcement criteria         │
└────────────────────────────────────────────┘
    ↓
🔒 MANDATORY PROTOCOL GATE (STOP EXECUTION)
    ↓
"⚠️ DevStream Protocol Required

This task requires following the DevStream 7-step workflow:
DISCUSSION → ANALYSIS → RESEARCH → PLANNING → APPROVAL → IMPLEMENTATION → VERIFICATION

OPTIONS:
✅ [RECOMMENDED] Follow DevStream protocol (research-driven, quality-assured)
⚠️  [OVERRIDE] Skip protocol (quick fix, NO quality assurance, NO Context7, NO testing)

Risks of override:
- ❌ No Context7 research (potential outdated/incorrect patterns)
- ❌ No @code-reviewer validation (OWASP Top 10 security gaps)
- ❌ No testing requirements (95%+ coverage waived)
- ❌ No approval workflow (decisions undocumented)

Choose: [1] Protocol  [2] Override  [Cancel]"
    ↓
┌──────────────────┬─────────────────────────┐
│ User: Protocol   │ User: Override          │
├──────────────────┼─────────────────────────┤
│ → Execute 7-step │ → Log override decision │
│ → Create task    │ → Warn about risks      │
│ → TodoWrite plan │ → Disable quality gates │
│ → Quality gates  │ → Execute directly      │
└──────────────────┴─────────────────────────┘
```

#### Override Tracking

**EVERY override is logged** in DevStream memory with:
- Timestamp
- User justification
- Disabled quality gates
- Risk acknowledgment
- Outcome tracking (for learning)

**Override Audit Trail**: Query with `mcp__devstream__devstream_search_memory` using keyword "protocol-override"

#### Violation Consequences

**Protocol violations** (proceeding without gate approval):
1. ⚠️ Automatic detection via hook monitoring
2. 🔄 Rollback to last checkpoint
3. 📝 Log violation in memory
4. 🚨 Restart with protocol enforcement

**BYPASS FORBIDDEN**: Cannot disable enforcement via configuration. Only user explicit override allowed.

### 🚨 Mandatory Workflow: 7 Sequential Steps

**EVERY task MUST follow**: DISCUSSION → ANALYSIS → RESEARCH → PLANNING → APPROVAL → IMPLEMENTATION → VERIFICATION/TEST

#### Step 1: DISCUSSION (MANDATORY)
- ✅ Present problem/objective, discuss trade-offs, identify constraints, obtain consensus
- 🔒 Hook registers discussions in memory (content_type: "decision")
- 📊 Validation: Every task must have ≥1 discussion record

#### Step 2: ANALYSIS (MANDATORY)
- ✅ Analyze codebase for similar patterns, identify files to modify, estimate complexity, define acceptance criteria
- 🔒 Hook requires context injection from memory
- 📊 Validation: Verify codebase pattern analysis

#### Step 3: RESEARCH (MANDATORY - Context7)
- ✅ Use Context7 for technical decisions, research best practices, document findings, validate approach
- 🔒 Context7 integration automatic via PreToolUse hook
- 📊 Validation: Verify Context7 docs in context injection log

#### Step 4: PLANNING (MANDATORY - TodoWrite + Implementation Plan)
- ✅ Create TodoWrite list for non-trivial tasks, micro-tasks MAX 10-15 min, define dependencies, establish completion criteria
- ✅ **Protocol v2.2.0**: Generate implementation plan with model-specific template (GLM-4.6 or Sonnet 4.5)
- ✅ **Dual Storage**: Plan saved to DevStream DB + filesystem (`docs/development/plan/piano_[task-slug].md`)
- 🔒 TodoWrite tool integrated in Claude Code
- 🔒 **NEW**: `implementation_plan_generator.py` hook automates plan creation at Step 4
- 📊 Validation: Task list + implementation plan must exist before implementation

#### Step 5: APPROVAL (MANDATORY + Strategic Choice Gate)
- ✅ Present complete plan, show Context7 findings, obtain explicit approval ("OK", "proceed", "approved")
- ✅ **Protocol v2.2.0 - Strategic Choice Gate**: After approval, choose implementation model:
  - **Option A**: Continue with **Sonnet 4.5** (architectural work, complex reasoning, 30+ hour focus)
  - **Option B**: Handoff to **GLM-4.6** (precise execution, cost-optimized ~70% savings, tool calling 90.6%)
- ✅ **GLM Handoff Workflow** (if Option B selected):
  1. Generate GLM handoff prompt with complete context transfer
  2. Save plan + handoff to DB and filesystem
  3. Display handoff instructions for manual session switch
  4. Close Sonnet session, start new GLM session with handoff prompt
- 🔒 Memory registers approval as "decision"
- 🔒 **NEW**: Strategic Choice Gate logs model selection decision
- 📊 Validation: Verify approval record + model choice before commit

#### Step 6: IMPLEMENTATION (MANDATORY - Guided)
- ✅ One micro-task at a time, mark "in_progress" → work → mark "completed", document with docstrings + type hints
- 🔒 PostToolUse hook registers code in memory automatically
- 📊 Validation: Verify every written file registered in memory

#### Step 7: VERIFICATION/TEST (MANDATORY)
- ✅ Tests for EVERY feature, 95%+ coverage, validate performance, E2E integration tests, error handling
- 🔒 Hook requires test validation before completion
- 📊 Validation: Test results documented in memory

---

## 🔄 PRESCRIPTIVE RULES - Task Lifecycle Management

### Task Creation (Protocol v2.2.0 - Step 1 MANDATORY)
**WHEN**: Work > 15 minutes OR involves code/architecture/research
**CRITICAL CHANGE**: Task creation moved from Step 5 (APPROVAL) to Step 1 (DISCUSSION) to prevent data loss
**RULES**:
- ✅ **AUTOMATIC**: `task_first_handler.py` hook enforces task creation at Step 1 before DISCUSSION
- ✅ **Complexity Analysis**: Automatic detection based on duration, code involvement, architecture decisions, file count, Context7 requirement
- ✅ **Interactive Enforcement Gate**: User presented with Protocol/Override/Cancel options via PyInquirer
- ✅ Use `mcp__devstream__devstream_create_task` for task registration
- ✅ Define title/description, task_type (analysis/coding/documentation/testing/review/research), priority (1-10), phase_name
- ✅ **Draft Task Cleanup**: Tasks in "pending" status >7 days auto-archived (configurable)
- ❌ Manual tasks without MCP | ❌ Creating tasks at Step 5 (old protocol)
**ENFORCEMENT**: `task_first_handler.py` + `enforcement_gate.py` (blocking validation)

### Task Execution
**WHEN**: During implementation
**RULES**: ✅ Mark "active" via `mcp__devstream__devstream_update_task`, follow 7-step workflow, update progress, register decisions/learnings, TodoWrite real-time | ❌ Multiple tasks simultaneously without approval
**ENFORCEMENT**: Hook monitors task status and tool usage

### Task Completion
**WHEN**: All acceptance criteria completed
**RULES**: ✅ Verify TodoWrite "completed", tests 100% pass, mark "completed", register lessons learned, commit, push if requested | ❌ Mark "completed" with failing tests or pending TodoWrite
**ENFORCEMENT**: Hook validates completion criteria automatically

---

## 💾 PRESCRIPTIVE RULES - Memory System

### Automatic Memory Storage (PostToolUse Hook)
**WHEN**: Automatic after EVERY tool execution (Write, Edit, Bash, etc.)
**CONTENT TYPES**: code, documentation, context, output, error, decision, learning
**PROCESS**: ✅ AUTOMATIC - PostToolUse hook → content preview (300 chars) → keywords extraction → vector embeddings (Ollama) → SQLite + sqlite-vec storage
**USER ACTION**: None - completely automatic

### Memory Search & Retrieval (PreToolUse Hook)
**WHEN**: Automatic before EVERY tool execution
**FLOW**: (1) Detect libraries (Context7) → (2) Search DevStream memory → (3) Assemble hybrid context → (4) Inject in Claude context → (5) Token budget management
**ALGORITHM**: Hybrid search (semantic + keyword) via RRF (Reciprocal Rank Fusion), threshold 0.5, token budget: Context7 5000 + Memory 2000
**USER ACTION**: None - completely automatic

### Manual Memory Operations (OPTIONAL)
**TOOLS**: `mcp__devstream__devstream_store_memory` (content, content_type, keywords), `mcp__devstream__devstream_search_memory` (query, content_type, limit)
**USE CASE**: Advanced queries, store critical context pre-session end
**NOTE**: Automatic system handles 99% of cases

---

## 🔍 PRESCRIPTIVE RULES - Context Injection

### Context7 Integration (PreToolUse Hook)
**TRIGGERS**: Import statements, library mentions, code patterns (async/await, decorators), documentation requests
**PROCESS**: ✅ AUTOMATIC - Context7 detect → retrieve docs via `mcp__context7__get-library-docs` → inject (max 5000 tokens) → priority ordering (official docs > examples > best practices)
**CONFIG**: `.env.devstream` → `DEVSTREAM_CONTEXT7_ENABLED=true`, `DEVSTREAM_CONTEXT7_AUTO_DETECT=true`, `DEVSTREAM_CONTEXT7_TOKEN_BUDGET=5000`

### DevStream Memory Context (PreToolUse Hook)
**PRIORITY ORDER**: (1) Context7 Documentation (5000 tokens), (2) DevStream Memory (2000 tokens - related code, decisions, learnings), (3) Current File Context (remaining budget)
**PROCESS**: ✅ AUTOMATIC - Hybrid search (RRF) → relevance filtering (threshold 0.5) → token budget enforcement → context assembly → injection
**CONFIG**: `.env.devstream` → `DEVSTREAM_CONTEXT_INJECTION_ENABLED=true`, `DEVSTREAM_CONTEXT_MAX_TOKENS=2000`, `DEVSTREAM_CONTEXT_RELEVANCE_THRESHOLD=0.5`

### Context Injection Quality Optimizations (2025-10-02)

**Status**: ✅ Production Ready (Phases 1-5 Complete) | **Tested**: 2025-10-02 | **Coverage**: 100%

**Improvements**:
1. **Code-Aware Queries**: Extracts imports, classes, functions, decorators (83% size reduction - 313→50 chars)
2. **Relevance Filtering**: min_relevance=0.03 (3% RRF score threshold - 50% noise reduction)
3. **Token Budget Enforcement**: 2000 token max for DevStream memory (strict enforcement)
4. **Context7 Advisory Pattern**: Emits recommendations instead of direct MCP calls (no blocking)
5. **Library Name Normalization**: Lowercase for Context7 compatibility (sqlalchemy, fastapi)

**Configuration (.env.devstream)**:
- `DEVSTREAM_CONTEXT_MAX_TOKENS=2000` (DevStream memory budget)
- `DEVSTREAM_CONTEXT7_TOKEN_BUDGET=5000` (Context7 library docs budget)
- `min_relevance=0.03` (memory.ts search threshold - 3% RRF minimum)

**Performance Validated** (2025-10-02):
- Query construction: <1ms average (83% size reduction)
- Token estimation: ±1 token accuracy (100% tests passed)
- Memory search: +25% relevance improvement (RRF hybrid search)
- False positives: -30% reduction (relevance filtering)
- Context7 advisory: 100% success rate (non-blocking pattern)

**Test Results**: All component tests passed (code-aware queries, library detection, token estimation, relevance filtering)

**Documentation**: See [Context Injection Optimization Summary](docs/implementation/context-injection-optimization-summary.md)

---

## 🐍 PRESCRIPTIVE RULES - Python Environment

### 🚨 MANDATORY: Virtual Environment Usage

**CRITICAL RULE**: ALWAYS use `.devstream` venv for ALL Python commands.

**Configuration**: Venv: `.devstream` | Python: 3.11.x | Interpreter: `.devstream/bin/python`

#### Session Start Checklist (MANDATORY at Start of EVERY Session)
```bash
# 1. Verify venv exists
if [ ! -d ".devstream" ]; then python3.11 -m venv .devstream; fi
# 2. Verify Python version (MUST be 3.11.x)
.devstream/bin/python --version
# 3. Verify critical dependencies
.devstream/bin/python -m pip list | grep -E "(cchooks|aiohttp|structlog)"
```

**FORBIDDEN**: ❌ `python script.py`, `python3 script.py`, `uv run script.py` (non-persistent)
**REQUIRED**: ✅ `.devstream/bin/python script.py`, `.devstream/bin/python -m pytest`, `.devstream/bin/python -m pip install package`

#### First-Time Setup (when venv missing)
```bash
# 1. Create venv → 2. Upgrade pip → 3. Install requirements.txt
# 4. Install hook dependencies: cchooks>=0.1.4, aiohttp>=3.8.0, structlog>=23.0.0, python-dotenv>=1.0.0
# 5. Verify: .devstream/bin/python -m pip list | head -20
```

#### Hook System Configuration (settings.json)
```json
{
  "hooks": {
    "PreToolUse": [{"hooks": [{"command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/memory/pre_tool_use.py"}]}],
    "PostToolUse": [{"hooks": [{"command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/memory/post_tool_use.py"}]}],
    "UserPromptSubmit": [{"hooks": [{"command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/context/user_query_context_enhancer.py"}]}]
  }
}
```
**CRITICAL**: Hooks MUST use `.devstream/bin/python`, NOT system Python

---

## 🛠 PRESCRIPTIVE RULES - Tools & Configuration

### Context7 Usage (MANDATORY for Research)
**WORKFLOW**: (1) `mcp__context7__resolve-library-id` (library name → Context7 ID) → (2) `mcp__context7__get-library-docs` (ID → docs max 5000 tokens) → (3) Analyze findings → (4) Apply research-backed patterns | ❌ Skip Context7 for new technologies

### TodoWrite Usage (MANDATORY for Planning)
**WHEN**: Non-trivial tasks (>15 min)
**RULES**: ✅ Create TodoWrite BEFORE implementation, micro-tasks 10-15 min, mark "in_progress" → work → "completed", ONE task "in_progress" at a time | ❌ Start without TodoWrite, mark "completed" with pending sub-tasks
**FORMAT**: `{"content": "Imperative form", "activeForm": "Present continuous", "status": "pending|in_progress|completed"}`

### Testing Requirements (MANDATORY)
**COVERAGE**: ✅ 95%+ for NEW code, 100% pass rate before commit, E2E integration tests, performance validation, error handling | ❌ Commit with failing tests, commit without tests
**STRUCTURE**: `tests/unit/` (fast <1s), `tests/integration/` (E2E <10s), `tests/fixtures/` (test data)
**EXECUTION**: `.devstream/bin/python -m pytest tests/ -v --cov=.claude/hooks/devstream --cov-report=html`

---

## 📖 PRESCRIPTIVE RULES - Documentation

### Code Documentation (MANDATORY)
**EVERY function/class MUST have**: Docstring (description, Args, Returns, Raises, Note), full type hints, inline comments for complex logic (>5 lines) | ❌ Missing docstrings, missing type hints

**Example**:
```python
def hybrid_search(self, query: str, limit: int = 10, content_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Perform hybrid search combining semantic and keyword search.
    Uses Reciprocal Rank Fusion (RRF) algorithm.

    Args:
        query: Search query string
        limit: Maximum results (default: 10)
        content_type: Optional filter by content type

    Returns:
        List of memory records sorted by relevance score

    Raises:
        DatabaseError: If database query fails

    Note:
        RRF weights: semantic 60%, keyword 40%
    """
```

### Project Documentation (MANDATORY)
**Structure**: `docs/architecture/` (system design - MANDATORY new systems), `docs/api/` (API reference - MANDATORY APIs), `docs/deployment/` (MANDATORY production), `docs/guides/` (MANDATORY user-facing features), `docs/development/` (MANDATORY complex features), `docs/tutorials/` (OPTIONAL)
**RULES**: ✅ Create docs for EVERY major feature, update BEFORE task complete, include code examples, keep in sync | ❌ .md files in root (except README.md, CLAUDE.md, PROJECT_STRUCTURE.md), outdated docs

### Progress Documentation (MANDATORY)
**MUST Document**: TodoWrite tracking, implementation notes per phase, lessons learned per completed task, decision rationale, test results
**STORAGE**: Automatic via PostToolUse hook in memory (content_type: "learning", "decision")

---

## 🎯 PRESCRIPTIVE RULES - Quality Standards

### Code Quality (MANDATORY)
**Type Safety**: ✅ Full type hints ALL functions/methods, mypy --strict (zero errors) | ❌ Any type hints, mypy errors in production
**Error Handling**: ✅ Structured exception hierarchy, logging for EVERY exception, graceful degradation, user-friendly messages | ❌ Bare except:, silent failures
**Performance**: ✅ async/await for I/O, connection pooling, token budget enforcement, performance testing | ❌ Blocking I/O in async, no performance validation
**Maintainability**: ✅ SOLID principles, single responsibility, max function length 50 lines, max cyclomatic complexity 10 | ❌ God objects, cryptic abbreviations

### Architecture Quality (MANDATORY)
**Separation**: ✅ Clear module boundaries, layered architecture (hooks → utils → core), interface segregation | ❌ Circular dependencies, tight coupling
**Configuration**: ✅ Environment-based (.env.devstream), validate ALL config, defaults, documentation | ❌ Hardcoded values, config in code
**Logging**: ✅ Structured logging (structlog), context ALL log messages, appropriate levels (DEBUG/INFO/WARNING/ERROR), log rotation | ❌ print() statements, logging sensitive data

---

## 🚀 PRESCRIPTIVE RULES - Implementation Patterns

### Research-Driven Development (MANDATORY)
**SEQUENCE**: (1) RESEARCH (Context7 → best practices → document findings) → (2) DESIGN (research-based architecture → clear interfaces) → (3) IMPLEMENT (validated patterns → one micro-task at a time) → (4) TEST (95%+ coverage → validate assumptions) → (5) DOCUMENT (lessons learned → update docs)
**ENFORCEMENT**: Hook registers research findings in memory

### Micro-Task Execution (MANDATORY)
**SEQUENCE**: (1) ANALYZE (break down feature → 10-15 min micro-tasks → dependencies) → (2) PLAN (TodoWrite list → completion criteria) → (3) EXECUTE (one task at a time → mark "in_progress" → work → "completed") → (4) VERIFY (test after EVERY task → verify integration) → (5) INTEGRATE (merge codebase → update docs)
**ENFORCEMENT**: TodoWrite tool tracks compliance

### Approval Workflow (MANDATORY)
**SEQUENCE**: (1) DISCUSS (present approach + trade-offs → identify risks) → (2) RESEARCH (Context7 validation → alternative approaches) → (3) APPROVE (explicit approval → confirm acceptance criteria) → (4) IMPLEMENT (follow approved approach → no deviations without approval) → (5) REVIEW (validate results → document learnings)
**ENFORCEMENT**: Memory registers approval as "decision"

---

## 📊 PRESCRIPTIVE RULES - Success Metrics

### Development Metrics (MANDATORY Targets)
✅ Task Completion: 100% | Test Coverage: 95%+ NEW code | Test Pass Rate: 100% | Code Quality: Zero mypy errors | Cyclomatic Complexity: Max 10 | Documentation Coverage: 100% docstrings | Performance: Meet/exceed targets

### Process Metrics (MANDATORY Tracking)
✅ Research Quality: Context7 usage for EVERY major decision | Collaboration: 100% approval workflow adherence | Learning: Documented lessons learned per phase | Innovation: Research-backed technology choices | Delivery: On-time (planned vs actual) | Memory Usage: Automatic storage tracking | Context Injection: Automatic injection rate

**STORAGE**: Automatic via DevStream memory system

---

## 🔧 PRESCRIPTIVE RULES - File Organization

### 📁 Project Structure (MANDATORY)
**CRITICAL**: ALWAYS follow PROJECT_STRUCTURE.md

**Documentation**: ✅ `docs/{architecture,api,deployment,guides,development,tutorials}/` | ❌ .md files in root (except README.md, CLAUDE.md, PROJECT_STRUCTURE.md)
**Tests**: ✅ `tests/{unit,integration,fixtures}/` | ❌ Test files in root, tests mixed with source
**Naming**: Documentation → kebab-case (devstream-guide.md) | Code → snake_case (pre_tool_use.py)

**File Creation Checklist**: (1) Check PROJECT_STRUCTURE.md → (2) Identify correct directory → (3) Use naming convention → (4) Verify directory exists → (5) Create file

---

## 🚨 FUNDAMENTAL RULE - Problem Solving

### ⚡⚡⚡ USE CONTEXT7 TO SOLVE - NEVER SIMPLIFY ⚡⚡⚡

**MANDATORY**: ✅ Use Context7 to research solution, research best practices, implement research-backed solution, maintain ALL features functional, test thoroughly
**FORBIDDEN**: ❌ Disable features to "fix" problem, remove functionality as workaround, create temporary workarounds, simplify to avoid complexity, skip research step

**ENFORCEMENT**: Code review rejects workarounds and feature disabling

---

## 📚 APPENDIX - System Integration Reference

### Hook Integration Points
| Hook | Location | Trigger | Purpose | Config |
|------|----------|---------|---------|--------|
| PreToolUse | `.claude/hooks/devstream/memory/pre_tool_use.py` | Before EVERY tool execution | Inject Context7 + DevStream memory | `DEVSTREAM_CONTEXT_INJECTION_ENABLED` |
| PostToolUse | `.claude/hooks/devstream/memory/post_tool_use.py` | After EVERY tool execution | Store code/docs/context | `DEVSTREAM_MEMORY_ENABLED` |
| UserPromptSubmit | `.claude/hooks/devstream/context/user_query_context_enhancer.py` | On EVERY user prompt | Enhance query with context | `DEVSTREAM_QUERY_ENHANCEMENT_ENABLED` |
| SessionEnd | `.claude/hooks/devstream/sessions/session_end.py` | Session exit/logout | Generate and save session summary | `DEVSTREAM_SESSION_TRACKING_ENABLED` |
| PreCompact | `.claude/hooks/devstream/sessions/pre_compact.py` | Before /compact command | Save summary before compaction | `DEVSTREAM_SESSION_TRACKING_ENABLED` |
| SessionStart | `.claude/hooks/devstream/sessions/session_start.py` | Session startup | Display previous session summary | `DEVSTREAM_SESSION_TRACKING_ENABLED` |

### Cross-Session Summary Preservation

**Pattern**: Atomic Marker File Write (Production Ready - 2025-10-02)

**Implementation**:
- **Utility**: `.claude/hooks/devstream/utils/atomic_file_writer.py`
- **Hooks**: SessionEnd + PreCompact (dual-write strategy for 90% coverage)
- **Marker File**: `~/.claude/state/devstream_last_session.txt`
- **Pattern**: Write-Rename (temp file + os.replace atomic operation)

**Workflow**:
1. **SessionEnd/PreCompact** → Generate summary → Atomic write to marker file
2. **Claude Code restart** → SessionStart → Display summary → Delete marker file
3. **Marker file consumed once** (one-time display, prevents re-display)

**Atomic Write Guarantees**:
- ✅ No partial writes (temp file + atomic rename)
- ✅ No race conditions (OS-level atomicity via os.replace)
- ✅ Crash recovery (fsync durability guarantee)
- ✅ Cross-platform (macOS, Linux, Windows)

**Quality Metrics**:
- ✅ Atomic writes (no partial data, no race conditions)
- ✅ Async I/O (aiofiles, non-blocking event loop)
- ✅ 100% test pass rate (24 tests: 15 unit + 9 integration)
- ✅ 83% coverage (critical paths 100% covered)
- ✅ Performance: <10ms for typical summary (2KB)

**Dual-Write Strategy**:
- **PRIMARY**: SessionEnd writes marker (covers 70-80% of sessions)
- **SECONDARY**: PreCompact writes marker (covers manual `/compact` + auto-compact)
- **PRIORITY**: Last write wins (PreCompact overwrites SessionEnd if both execute)
- **TOTAL COVERAGE**: 90-95% of sessions preserved

**Research Applied**:
- **aiofiles library** (Context7 Trust Score 9.4) - async file I/O
- **Redis persistence pattern** - write-rename for crash recovery
- **POSIX atomic operations** - os.replace() guaranteed atomic since Python 3.3

**Documentation**: See [Session Summary Atomic Write Architecture](docs/architecture/session-summary-atomic-write.md)

**Test Suite**:
- `tests/unit/test_atomic_file_writer.py` (15 tests - 83% coverage)
- `tests/integration/test_cross_session_summary_workflow.py` (9 E2E scenarios - 100% coverage)

**Troubleshooting**:
- **Marker file not created**: Check `~/.claude/logs/devstream/hook_execution.log` for "Step 5.5" execution
- **Summary not displayed**: Verify `~/.claude/state/devstream_last_session.txt` exists before restart
- **Partial writes**: Should NEVER occur (atomic write guarantee) - report as bug if observed

### MCP Server Integration
**Location**: `mcp-devstream-server/` | **Port**: 3000
**Tools**:
- Task Management: `devstream_create_task`, `devstream_update_task`, `devstream_list_tasks`
- Memory System: `devstream_store_memory`, `devstream_search_memory`
- **Protocol v2.2.0 NEW**: `devstream_create_implementation_plan`, `devstream_get_implementation_plan`, `devstream_update_implementation_plan`, `devstream_list_implementation_plans`
**Config**: `.claude/mcp_servers.json` → `{"devstream": {"command": "node", "args": ["mcp-devstream-server/dist/index.js"], "env": {"DEVSTREAM_DB_PATH": "data/devstream.db"}}}`

### Implementation Plans System (Protocol v2.2.0)
**Database Schema**: `implementation_plans` table with model-specific storage (GLM-4.6 vs Sonnet 4.5)
**Dual Storage Pattern**:
- **Database**: SQLite (`data/devstream.db`) with full metadata, task linkage, model type tracking
- **Filesystem**: Markdown files in `docs/development/plan/piano_[task-slug].md` for human readability
**Model-Specific Templates**:
- **GLM-4.6**: `templates/implementation-plan-glm46.md` (execution-focused, micro-task breakdown, syntax precision)
- **Sonnet 4.5**: `templates/implementation-plan-sonnet45.md` (architectural, ADRs, component-level, subagent delegation)
- **Handoff Prompt**: `templates/handoff-prompt-glm46.md` (Sonnet→GLM context transfer)
**Strategic Choice Gate**: Interactive model selection at Step 5 (APPROVAL) with automatic plan generation
**Hook Integration**: `implementation_plan_generator.py` automates plan creation at Step 4 (PLANNING)

### Environment Configuration (.env.devstream)
```bash
# Memory System (MANDATORY)
DEVSTREAM_MEMORY_ENABLED=true
DEVSTREAM_MEMORY_FEEDBACK_LEVEL=minimal

# Context7 (MANDATORY)
DEVSTREAM_CONTEXT7_ENABLED=true
DEVSTREAM_CONTEXT7_AUTO_DETECT=true
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=5000

# Context Injection (MANDATORY)
DEVSTREAM_CONTEXT_INJECTION_ENABLED=true
DEVSTREAM_CONTEXT_MAX_TOKENS=2000
DEVSTREAM_CONTEXT_RELEVANCE_THRESHOLD=0.5

# Tier-Based Delegation (Protocol v2.2.0 - MANDATORY)
DEVSTREAM_AUTO_DELEGATION_TIER1_ENABLED=true   # Monolithic first (default)
DEVSTREAM_AUTO_DELEGATION_TIER2_THRESHOLD=0.95 # Single specialist confidence
DEVSTREAM_AUTO_DELEGATION_TIER3_THRESHOLD=0.70 # Multi-agent coordination
DEVSTREAM_AUTO_DELEGATION_QUALITY_GATE=true    # Mandatory @code-reviewer

# Database (MANDATORY)
DEVSTREAM_DB_PATH=data/devstream.db

# Logging (RECOMMENDED)
DEVSTREAM_LOG_LEVEL=INFO
DEVSTREAM_LOG_PATH=~/.claude/logs/devstream/
```

---

**Document Version**: 2.2.0 (Protocol v2.2.0 - Strategic Choice Gate + Implementation Plans)
**Last Updated**: 2025-10-09
**Status**: ✅ Production Ready - Protocol v2.2.0 Complete
**Key Changes**:
- ✅ Task creation moved to Step 1 (DISCUSSION) - prevents data loss
- ✅ Implementation plans with model-specific templates (GLM-4.6 vs Sonnet 4.5)
- ✅ Strategic Choice Gate at Step 5 (APPROVAL) - cost optimization via hybrid workflow
- ✅ GLM-4.6 handoff workflow for Sonnet→GLM session switching
- ✅ Dual storage pattern (DB + filesystem) for plans
**Methodology**: Research-Driven Development with Context7
**Enforcement**: Automatic via Hook System + MCP Integration + Auto-Delegation + Strategic Choice Gate

---

*These rules are an integral part and foundation of the DevStream system. Violating them may cause automatic system malfunctions.*
