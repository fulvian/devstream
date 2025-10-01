# CLAUDE.md - DevStream Project Rules

**Version**: 2.1.0 | **Date**: 2025-10-01 | **Status**: Production Ready - Phase 3 Complete

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
         └── AUTO-DELEGATION SYSTEM (Phase 3 ✅) - Pattern-based intelligent agent routing
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

### Agent Auto-Delegation System (Phase 3 ✅ - ALWAYS-ON)

**Purpose**: Intelligent, automatic agent selection based on file patterns and task context.

**STATUS**: ALWAYS-ON - Delegation analysis runs for EVERY user request automatically.

#### Default Ownership Model

**@tech-lead** owns ALL user requests by default and decides delegation strategy via automatic pattern analysis:

```
User Request
    ↓
@tech-lead (Default Owner)
    ↓
Pattern Matcher Analysis
    ↓
┌─────────────────────────────────────────────────────────┐
│ AUTOMATIC DELEGATION     │ AUTHORIZATION REQUIRED        │
├──────────────────────────┼───────────────────────────────┤
│ Confidence ≥ 0.95        │ Confidence < 0.95             │
│ Single-language task     │ Multi-stack coordination      │
│ Clear file patterns      │ Architectural decisions       │
│ Domain specialist match  │ Strategic planning            │
└──────────────────────────┴───────────────────────────────┘
    ↓                              ↓
Direct Delegation           @tech-lead Coordination
(e.g., @python-specialist)  (Multi-agent orchestration)
```

#### Pattern Matcher Logic

**File Pattern → Agent Mapping**:

| File Pattern | Agent | Confidence | Auto-Approve |
|--------------|-------|------------|--------------|
| `**/*.py` | @python-specialist | 0.95 | ✅ YES |
| `**/*.ts`, `**/*.tsx` | @typescript-specialist | 0.95 | ✅ YES |
| `**/*.rs` | @rust-specialist | 0.95 | ✅ YES |
| `**/*.go` | @go-specialist | 0.95 | ✅ YES |
| `**/schema.sql`, `**/migrations/*.sql` | @database-specialist | 0.90 | ✅ YES |
| `**/Dockerfile`, `**/*.yaml` (CI/CD) | @devops-specialist | 0.90 | ✅ YES |
| Mixed patterns | @tech-lead | 0.70 | ❌ AUTHORIZATION REQUIRED |

**Confidence Thresholds**:
- **≥ 0.95**: AUTOMATIC delegation (single language, clear context)
- **0.85 - 0.94**: ADVISORY delegation (suggest agent, request approval)
- **< 0.85**: AUTHORIZATION REQUIRED (@tech-lead coordination)

#### Quality Gate Enforcement (MANDATORY)

**Pre-Commit Trigger**: EVERY `git commit` command triggers automatic @code-reviewer delegation.

```bash
# User attempts commit
git commit -m "Add user authentication"
    ↓
Auto-Delegation Hook Detects Commit Intent
    ↓
MANDATORY @code-reviewer Invocation
    ↓
Quality Gate Validation:
  ✅ OWASP Top 10 security checks
  ✅ Performance analysis
  ✅ Architecture review
  ✅ Test coverage validation
    ↓
┌─────────────────┬─────────────────────┐
│ ✅ PASS         │ ❌ FAIL             │
├─────────────────┼─────────────────────┤
│ Commit proceeds │ Commit blocked      │
│                 │ Issues reported     │
│                 │ Fix required        │
└─────────────────┴─────────────────────┘
```

**Bypass FORBIDDEN**: Cannot skip @code-reviewer for commits (enforced by hook system).

#### Usage Examples

**Example 1: Python File Auto-Delegation**
```bash
# User request
"Update src/api/users.py to add email validation"

# Auto-Delegation Process
@tech-lead (receives request)
  → Pattern Matcher: src/api/users.py → *.py pattern
  → Confidence: 0.95 (single Python file)
  → Decision: AUTOMATIC delegation
  → Task(@python-specialist): "Update src/api/users.py to add email validation"

# Result: Direct specialist execution, no manual approval needed
```

**Example 2: Quality Gate Enforcement**
```bash
# User request
"Commit the authentication implementation"

# Auto-Delegation Process
@tech-lead (receives request)
  → Detects: git commit intent
  → Mandatory Quality Gate: Invoke @code-reviewer
  → Task(@code-reviewer): "Review authentication implementation in src/auth/"
  → @code-reviewer validates:
    ✅ JWT secret not hardcoded
    ✅ Password hashing uses bcrypt
    ✅ Rate limiting implemented
    ⚠️  Warning: Missing session timeout configuration
  → Reports findings to @tech-lead
  → @tech-lead decides: Proceed with commit + create follow-up task for session timeout

# Result: Commit allowed with actionable security feedback
```

**Example 3: Multi-Stack Task (Authorization Required)**
```bash
# User request
"Build full-stack user dashboard with Python backend and React frontend"

# Auto-Delegation Process
@tech-lead (receives request)
  → Pattern Matcher: Detects multiple languages (*.py + *.tsx)
  → Confidence: 0.70 (multi-stack coordination required)
  → Decision: AUTHORIZATION REQUIRED
  → @tech-lead analyzes:
    - Backend: User API endpoints (Python/FastAPI)
    - Frontend: Dashboard UI (TypeScript/React)
    - Integration: API client + state management
  → Orchestration Plan:
    1. Task(@python-specialist): "Implement backend user API"
    2. Task(@typescript-specialist): "Build React dashboard consuming /api/users"
    3. Task(@code-reviewer): "Review full-stack integration"

# Result: Coordinated multi-agent workflow with sequential delegation
```

#### Configuration Flags (.env.devstream)

```bash
# Auto-Delegation System (Phase 3)
DEVSTREAM_AUTO_DELEGATION_ENABLED=true          # Enable/disable auto-delegation
DEVSTREAM_AUTO_DELEGATION_MIN_CONFIDENCE=0.85   # Minimum confidence for suggestions
DEVSTREAM_AUTO_DELEGATION_AUTO_APPROVE=0.95     # Threshold for automatic approval
DEVSTREAM_AUTO_DELEGATION_QUALITY_GATE=true     # Enforce @code-reviewer for commits
```

**Flag Descriptions**:
- `ENABLED`: Master switch for auto-delegation system
- `MIN_CONFIDENCE`: Minimum confidence to suggest agent (below this → @tech-lead coordination)
- `AUTO_APPROVE`: Confidence threshold for automatic delegation (no approval needed)
- `QUALITY_GATE`: Enforce mandatory @code-reviewer before commits (RECOMMENDED: true)

#### Advisory vs Automatic Delegation (ALWAYS-ON)

**CRITICAL**: Delegation analysis runs for EVERY user request via UserPromptSubmit + PreToolUse hooks.

**AUTOMATIC** (Confidence ≥ 0.95):
- ✅ Single file, clear language pattern
- ✅ Direct specialist match
- ✅ No architectural decisions required
- ✅ Execution: Immediate delegation, no approval
- 🤖 **Always checked**: UserPromptSubmit hook analyzes BEFORE user works

**ADVISORY** (0.85 ≤ Confidence < 0.95):
- 🔔 Multiple related files, same language
- 🔔 Clear primary specialist, minor coordination
- 🔔 Execution: Suggest agent, request approval
- 🔔 User confirms: "Use @python-specialist" → Proceed
- 🤖 **Always checked**: Advisory shown in context injection

**AUTHORIZATION REQUIRED** (Confidence < 0.85):
- ⚠️ Multi-stack coordination
- ⚠️ Architectural decisions
- ⚠️ Strategic planning
- ⚠️ Execution: @tech-lead full analysis + orchestration
- 🤖 **Always checked**: Coordination advisory provided

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

#### Step 4: PLANNING (MANDATORY - TodoWrite)
- ✅ Create TodoWrite list for non-trivial tasks, micro-tasks MAX 10-15 min, define dependencies, establish completion criteria
- 🔒 TodoWrite tool integrated in Claude Code
- 📊 Validation: Task list must exist before implementation

#### Step 5: APPROVAL (MANDATORY)
- ✅ Present complete plan, show Context7 findings, obtain explicit approval ("OK", "proceed", "approved")
- 🔒 Memory registers approval as "decision"
- 📊 Validation: Verify approval record before commit

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

### Task Creation
**WHEN**: Work > 30 minutes
**RULES**: ✅ Use `mcp__devstream__devstream_create_task`, define title/description, task_type (analysis/coding/documentation/testing/review/research), priority (1-10), phase_name, register in MCP | ❌ Manual tasks without MCP
**ENFORCEMENT**: Non-MCP tasks not tracked

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

### MCP Server Integration
**Location**: `mcp-devstream-server/` | **Port**: 3000 | **Tools**: devstream_create_task, devstream_update_task, devstream_list_tasks, devstream_store_memory, devstream_search_memory, devstream_list_plans
**Config**: `.claude/mcp_servers.json` → `{"devstream": {"command": "node", "args": ["mcp-devstream-server/dist/index.js"], "env": {"DEVSTREAM_DB_PATH": "data/devstream.db"}}}`

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

# Auto-Delegation System (Phase 3 - MANDATORY)
DEVSTREAM_AUTO_DELEGATION_ENABLED=true          # Enable intelligent agent routing
DEVSTREAM_AUTO_DELEGATION_MIN_CONFIDENCE=0.85   # Minimum confidence for delegation suggestions
DEVSTREAM_AUTO_DELEGATION_AUTO_APPROVE=0.95     # Auto-approve threshold (≥0.95 = automatic)
DEVSTREAM_AUTO_DELEGATION_QUALITY_GATE=true     # Enforce @code-reviewer before commits (RECOMMENDED)

# Database (MANDATORY)
DEVSTREAM_DB_PATH=data/devstream.db

# Logging (RECOMMENDED)
DEVSTREAM_LOG_LEVEL=INFO
DEVSTREAM_LOG_PATH=~/.claude/logs/devstream/
```

---

**Document Version**: 2.1.0 (Prescriptive Rules + Auto-Delegation)
**Last Updated**: 2025-10-01
**Status**: ✅ Production Ready - Phase 3 Complete (Agent Auto-Delegation System)
**Methodology**: Research-Driven Development with Context7
**Enforcement**: Automatic via Hook System + MCP Integration + Auto-Delegation

---

*These rules are an integral part and foundation of the DevStream system. Violating them may cause automatic system malfunctions.*
