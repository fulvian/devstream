# CLAUDE.md - DevStream Project Rules

**Version**: 2.0.0 | **Date**: 2025-09-30 | **Status**: Production Ready

⚠️ **CRITICAL**: Queste regole sono **OBBLIGATORIE** e integrate nel sistema DevStream tramite hook automatici. La loro violazione può causare malfunzionamenti del sistema.

---

## 🎯 DevStream System Architecture

DevStream combina: (1) Task Lifecycle Management, (2) Semantic Memory System, (3) Context Injection (Context7 + DevStream Memory), (4) Hook Automation (PreToolUse, PostToolUse, UserPromptSubmit via cchooks).

**🔄 Sistema Automatico**: I hook eseguono automaticamente memory storage e context injection senza intervento manuale.

---

## 🤖 Custom Agent System - Multi-Stack Development

**Status**: Phase 2 Complete ✅ | 8 Agents Production Ready

### Agent Architecture (4-Level Hierarchy)

```
Level 1: ORCHESTRATOR (@tech-lead) - Task decomposition, multi-agent coordination, architectural decisions
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

### Future Phases

**Phase 3** (Task Specialists): @api-architect, @performance-optimizer, @testing-specialist, @documentation-specialist
**Phase 4** (Advanced): @security-auditor, @debugger, @refactoring-specialist, @integration-specialist

---

## 📋 REGOLE PRESCRITTIVE - Metodologia DevStream

### 🚨 Workflow Obbligatorio: 7 Step Sequenziali

**OGNI task DEVE seguire**: DISCUSSIONE → ANALISI → RICERCA → PIANIFICAZIONE → APPROVAZIONE → IMPLEMENTAZIONE → VERIFICA/TEST

#### Step 1: DISCUSSIONE (MANDATORY)
- ✅ Presentare problema/obiettivo, discutere trade-offs, identificare vincoli, ottenere consensus
- 🔒 Hook registra discussioni in memory (content_type: "decision")
- 📊 Validation: Ogni task deve avere ≥1 discussion record

#### Step 2: ANALISI (MANDATORY)
- ✅ Analizzare codebase per pattern simili, identificare file da modificare, stimare complessità, definire acceptance criteria
- 🔒 Hook richiede context injection da memory
- 📊 Validation: Verificare analisi codebase patterns

#### Step 3: RICERCA (MANDATORY - Context7)
- ✅ Usare Context7 per decisioni tecniche, ricercare best practices, documentare findings, validare approccio
- 🔒 Context7 integration automatica via PreToolUse hook
- 📊 Validation: Verificare Context7 docs in context injection log

#### Step 4: PIANIFICAZIONE (MANDATORY - TodoWrite)
- ✅ Creare TodoWrite list per task non-triviali, micro-task MAX 10-15 min, definire dipendenze, stabilire completion criteria
- 🔒 TodoWrite tool integrato in Claude Code
- 📊 Validation: Task list deve esistere prima di implementazione

#### Step 5: APPROVAZIONE (MANDATORY)
- ✅ Presentare piano completo, mostrare Context7 findings, ottenere approvazione esplicita ("OK", "procedi", "approvato")
- 🔒 Memory registra approval come "decision"
- 📊 Validation: Verificare approval record prima di commit

#### Step 6: IMPLEMENTAZIONE (MANDATORY - Guided)
- ✅ Un micro-task alla volta, mark "in_progress" → work → mark "completed", documentare con docstrings + type hints
- 🔒 PostToolUse hook registra codice in memory automaticamente
- 📊 Validation: Verificare ogni file scritto registrato in memory

#### Step 7: VERIFICA/TEST (MANDATORY)
- ✅ Test per OGNI feature, 95%+ coverage, validare performance, integration tests E2E, error handling
- 🔒 Hook richiede test validation prima di completion
- 📊 Validation: Test results documentati in memory

---

## 🔄 REGOLE PRESCRITTIVE - Task Lifecycle Management

### Task Creation
**WHEN**: Lavoro > 30 minuti
**RULES**: ✅ Use `mcp__devstream__devstream_create_task`, definire title/description, task_type (analysis/coding/documentation/testing/review/research), priority (1-10), phase_name, registrare in MCP | ❌ Task manuali senza MCP
**ENFORCEMENT**: Task non MCP non tracciati

### Task Execution
**WHEN**: Durante implementazione
**RULES**: ✅ Mark "active" via `mcp__devstream__devstream_update_task`, seguire 7-step workflow, update progress, registrare decisions/learnings, TodoWrite real-time | ❌ Multiple task simultaneously senza approval
**ENFORCEMENT**: Hook monitora task status e tool usage

### Task Completion
**WHEN**: Tutti acceptance criteria completati
**RULES**: ✅ Verificare TodoWrite "completed", test 100% pass, mark "completed", registrare lessons learned, commit, push se richiesto | ❌ Mark "completed" con test failing o TodoWrite pending
**ENFORCEMENT**: Hook valida completion criteria automaticamente

---

## 💾 REGOLE PRESCRITTIVE - Memory System

### Automatic Memory Storage (PostToolUse Hook)
**WHEN**: Automatico dopo OGNI tool execution (Write, Edit, Bash, etc.)
**CONTENT TYPES**: code, documentation, context, output, error, decision, learning
**PROCESS**: ✅ AUTOMATIC - PostToolUse hook → content preview (300 chars) → keywords extraction → vector embeddings (Ollama) → SQLite + sqlite-vec storage
**USER ACTION**: Nessuna - completamente automatico

### Memory Search & Retrieval (PreToolUse Hook)
**WHEN**: Automatico prima di OGNI tool execution
**FLOW**: (1) Detect libraries (Context7) → (2) Search DevStream memory → (3) Assemble hybrid context → (4) Inject in Claude context → (5) Token budget management
**ALGORITHM**: Hybrid search (semantic + keyword) via RRF (Reciprocal Rank Fusion), threshold 0.5, token budget: Context7 5000 + Memory 2000
**USER ACTION**: Nessuna - completamente automatico

### Manual Memory Operations (OPTIONAL)
**TOOLS**: `mcp__devstream__devstream_store_memory` (content, content_type, keywords), `mcp__devstream__devstream_search_memory` (query, content_type, limit)
**USE CASE**: Query avanzate, store context critico pre-session end
**NOTE**: Sistema automatico gestisce 99% dei casi

---

## 🔍 REGOLE PRESCRITTIVE - Context Injection

### Context7 Integration (PreToolUse Hook)
**TRIGGERS**: Import statements, library mentions, code patterns (async/await, decorators), documentation requests
**PROCESS**: ✅ AUTOMATIC - Context7 detect → retrieve docs via `mcp__context7__get-library-docs` → inject (max 5000 tokens) → priority ordering (official docs > examples > best practices)
**CONFIG**: `.env.devstream` → `DEVSTREAM_CONTEXT7_ENABLED=true`, `DEVSTREAM_CONTEXT7_AUTO_DETECT=true`, `DEVSTREAM_CONTEXT7_TOKEN_BUDGET=5000`

### DevStream Memory Context (PreToolUse Hook)
**PRIORITY ORDER**: (1) Context7 Documentation (5000 tokens), (2) DevStream Memory (2000 tokens - related code, decisions, learnings), (3) Current File Context (remaining budget)
**PROCESS**: ✅ AUTOMATIC - Hybrid search (RRF) → relevance filtering (threshold 0.5) → token budget enforcement → context assembly → injection
**CONFIG**: `.env.devstream` → `DEVSTREAM_CONTEXT_INJECTION_ENABLED=true`, `DEVSTREAM_CONTEXT_MAX_TOKENS=2000`, `DEVSTREAM_CONTEXT_RELEVANCE_THRESHOLD=0.5`

---

## 🐍 REGOLE PRESCRITTIVE - Python Environment

### 🚨 MANDATORY: Virtual Environment Usage

**CRITICAL RULE**: SEMPRE utilizzare `.devstream` venv per TUTTI i comandi Python.

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

## 🛠 REGOLE PRESCRITTIVE - Tools & Configuration

### Context7 Usage (MANDATORY for Research)
**WORKFLOW**: (1) `mcp__context7__resolve-library-id` (library name → Context7 ID) → (2) `mcp__context7__get-library-docs` (ID → docs max 5000 tokens) → (3) Analyze findings → (4) Apply research-backed patterns | ❌ Skip Context7 per nuove tecnologie

### TodoWrite Usage (MANDATORY for Planning)
**WHEN**: Task non-triviali (>15 min)
**RULES**: ✅ Create TodoWrite BEFORE implementation, micro-task 10-15 min, mark "in_progress" → work → "completed", ONE task "in_progress" at a time | ❌ Start without TodoWrite, mark "completed" con pending sub-tasks
**FORMAT**: `{"content": "Imperative form", "activeForm": "Present continuous", "status": "pending|in_progress|completed"}`

### Testing Requirements (MANDATORY)
**COVERAGE**: ✅ 95%+ for NEW code, 100% pass rate before commit, integration tests E2E, performance validation, error handling | ❌ Commit con failing tests, commit senza test
**STRUCTURE**: `tests/unit/` (fast <1s), `tests/integration/` (E2E <10s), `tests/fixtures/` (test data)
**EXECUTION**: `.devstream/bin/python -m pytest tests/ -v --cov=.claude/hooks/devstream --cov-report=html`

---

## 📖 REGOLE PRESCRITTIVE - Documentation

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
**STORAGE**: Automatico via PostToolUse hook in memory (content_type: "learning", "decision")

---

## 🎯 REGOLE PRESCRITTIVE - Quality Standards

### Code Quality (MANDATORY)
**Type Safety**: ✅ Full type hints ALL functions/methods, mypy --strict (zero errors) | ❌ Any type hints, mypy errors in production
**Error Handling**: ✅ Structured exception hierarchy, logging per OGNI exception, graceful degradation, user-friendly messages | ❌ Bare except:, silent failures
**Performance**: ✅ async/await per I/O, connection pooling, token budget enforcement, performance testing | ❌ Blocking I/O in async, no performance validation
**Maintainability**: ✅ SOLID principles, single responsibility, max function length 50 lines, max cyclomatic complexity 10 | ❌ God objects, cryptic abbreviations

### Architecture Quality (MANDATORY)
**Separation**: ✅ Clear module boundaries, layered architecture (hooks → utils → core), interface segregation | ❌ Circular dependencies, tight coupling
**Configuration**: ✅ Environment-based (.env.devstream), validation ALL config, defaults, documentation | ❌ Hardcoded values, config in code
**Logging**: ✅ Structured logging (structlog), context ALL log messages, appropriate levels (DEBUG/INFO/WARNING/ERROR), log rotation | ❌ print() statements, logging sensitive data

---

## 🚀 REGOLE PRESCRITTIVE - Implementation Patterns

### Research-Driven Development (MANDATORY)
**SEQUENCE**: (1) RESEARCH (Context7 → best practices → document findings) → (2) DESIGN (architecture basata su research → clear interfaces) → (3) IMPLEMENT (validated patterns → one micro-task at a time) → (4) TEST (95%+ coverage → validate assumptions) → (5) DOCUMENT (lessons learned → update docs)
**ENFORCEMENT**: Hook registra research findings in memory

### Micro-Task Execution (MANDATORY)
**SEQUENCE**: (1) ANALYZE (break down feature → 10-15 min micro-tasks → dependencies) → (2) PLAN (TodoWrite list → completion criteria) → (3) EXECUTE (one task at a time → mark "in_progress" → work → "completed") → (4) VERIFY (test after OGNI task → verify integration) → (5) INTEGRATE (merge codebase → update docs)
**ENFORCEMENT**: TodoWrite tool tracks compliance

### Approval Workflow (MANDATORY)
**SEQUENCE**: (1) DISCUSS (present approach + trade-offs → identify risks) → (2) RESEARCH (Context7 validation → alternative approaches) → (3) APPROVE (explicit approval → confirm acceptance criteria) → (4) IMPLEMENT (follow approved approach → no deviations senza approval) → (5) REVIEW (validate results → document learnings)
**ENFORCEMENT**: Memory registra approval as "decision"

---

## 📊 REGOLE PRESCRITTIVE - Success Metrics

### Development Metrics (MANDATORY Targets)
✅ Task Completion: 100% | Test Coverage: 95%+ NEW code | Test Pass Rate: 100% | Code Quality: Zero mypy errors | Cyclomatic Complexity: Max 10 | Documentation Coverage: 100% docstrings | Performance: Meet/exceed targets

### Process Metrics (MANDATORY Tracking)
✅ Research Quality: Context7 usage OGNI major decision | Collaboration: 100% approval workflow adherence | Learning: Documented lessons learned per phase | Innovation: Research-backed technology choices | Delivery: On-time (planned vs actual) | Memory Usage: Automatic storage tracking | Context Injection: Automatic injection rate

**STORAGE**: Automatico via DevStream memory system

---

## 🔧 REGOLE PRESCRITTIVE - File Organization

### 📁 Project Structure (MANDATORY)
**CRITICAL**: SEMPRE seguire PROJECT_STRUCTURE.md

**Documentation**: ✅ `docs/{architecture,api,deployment,guides,development,tutorials}/` | ❌ .md files in root (except README.md, CLAUDE.md, PROJECT_STRUCTURE.md)
**Tests**: ✅ `tests/{unit,integration,fixtures}/` | ❌ Test files in root, tests mixed with source
**Naming**: Documentation → kebab-case (devstream-guide.md) | Code → snake_case (pre_tool_use.py)

**File Creation Checklist**: (1) Check PROJECT_STRUCTURE.md → (2) Identify correct directory → (3) Use naming convention → (4) Verify directory exists → (5) Create file

---

## 🚨 REGOLA FONDAMENTALE - Problem Solving

### ⚡⚡⚡ USE CONTEXT7 TO SOLVE - NEVER SIMPLIFY ⚡⚡⚡

**MANDATORY**: ✅ Use Context7 per research solution, ricerca best practices, implement research-backed solution, maintain ALL features functional, test thoroughly
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

# Database (MANDATORY)
DEVSTREAM_DB_PATH=data/devstream.db

# Logging (RECOMMENDED)
DEVSTREAM_LOG_LEVEL=INFO
DEVSTREAM_LOG_PATH=~/.claude/logs/devstream/
```

---

**Document Version**: 2.0.0 (Prescriptive Rules)
**Last Updated**: 2025-09-30
**Status**: ✅ Production Ready - Integrated with DevStream Automatic Features
**Methodology**: Research-Driven Development con Context7
**Enforcement**: Automatic via Hook System + MCP Integration

---

*Queste regole sono parte integrante e fondamento del sistema DevStream. La loro violazione può causare malfunzionamenti del sistema automatico.*
