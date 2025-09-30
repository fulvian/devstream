# CLAUDE.md - DevStream Project Rules

**Version**: 2.0.0 (Prescriptive Rules)
**Date**: 2025-09-30
**Status**: Production Ready

Questo file definisce le **regole prescrittive obbligatorie** per lo sviluppo del progetto DevStream - Sistema Integrato Task Management & Memoria Cross-Session per Claude Code.

⚠️ **CRITICAL**: Queste regole sono **OBBLIGATORIE** e integrate nel sistema DevStream tramite hook automatici. La loro violazione può causare malfunzionamenti del sistema.

---

## 🎯 DevStream System Architecture

DevStream è un sistema integrato che combina:

1. **Task Lifecycle Management** - Orchestrazione automatica del ciclo di vita dei task
2. **Semantic Memory System** - Storage e retrieval automatico di conoscenza progettuale
3. **Context Injection** - Iniezione automatica di contesto rilevante (Context7 + DevStream Memory)
4. **Hook Automation** - PreToolUse, PostToolUse, UserPromptSubmit hooks via cchooks

**🔄 Sistema Automatico**: I hook eseguono automaticamente le operazioni di memory storage e context injection senza intervento manuale.

---

## 📋 REGOLE PRESCRITTIVE - Metodologia DevStream

### 🚨 Workflow Obbligatorio

**OGNI task DEVE seguire questo workflow in ordine sequenziale:**

```
1. DISCUSSIONE → 2. ANALISI → 3. RICERCA → 4. PIANIFICAZIONE →
5. APPROVAZIONE → 6. IMPLEMENTAZIONE → 7. VERIFICA/TEST
```

Saltare step o eseguire fuori ordine viola il protocollo DevStream.

### 🔄 Workflow di Sviluppo: 7 Step Obbligatori

#### Step 1: DISCUSSIONE (MANDATORY)
```
🎯 OBIETTIVO: Allineamento su obiettivi e aspettative
📋 REGOLE OBBLIGATORIE:
  ✅ MUST: Presentare il problema/obiettivo chiaramente
  ✅ MUST: Discutere trade-offs architetturali
  ✅ MUST: Identificare vincoli e dipendenze
  ✅ MUST: Ottenere consensus su approccio generale
  ❌ FORBIDDEN: Iniziare implementazione senza discussione

🔒 ENFORCEMENT: Hook system registra discussioni in memory (content_type: "decision")
📊 VALIDATION: Ogni task deve avere almeno 1 discussion record in memory
```

#### Step 2: ANALISI (MANDATORY)
```
🎯 OBIETTIVO: Analisi tecnica dettagliata
📋 REGOLE OBBLIGATORIE:
  ✅ MUST: Analizzare codebase esistente per pattern simili
  ✅ MUST: Identificare moduli/file da modificare
  ✅ MUST: Stimare complessità e rischi
  ✅ MUST: Definire acceptance criteria chiari
  ❌ FORBIDDEN: Procedere senza analisi tecnica completa

🔒 ENFORCEMENT: Hook system richiede context injection da memory
📊 VALIDATION: Verificare che codebase patterns siano stati analizzati
```

#### Step 3: RICERCA (MANDATORY - Context7)
```
🎯 OBIETTIVO: Best practice research-backed
📋 REGOLE OBBLIGATORIE:
  ✅ MUST: Usare Context7 per ogni decisione tecnica maggiore
  ✅ MUST: Ricercare pattern e best practice validate
  ✅ MUST: Documentare findings e rationale
  ✅ MUST: Validare approccio con research esterna
  ❌ FORBIDDEN: Implementare senza Context7 research per nuove tecnologie

🔒 ENFORCEMENT: Context7 integration automatica via PreToolUse hook
📊 VALIDATION: Verificare presence di Context7 docs in context injection log
```

#### Step 4: PIANIFICAZIONE (MANDATORY - TodoWrite)
```
🎯 OBIETTIVO: Breakdown granulare e tracciabile
📋 REGOLE OBBLIGATORIE:
  ✅ MUST: Creare TodoWrite list per OGNI task non-triviale
  ✅ MUST: Micro-task da MAX 10-15 minuti ciascuno
  ✅ MUST: Definire dipendenze tra task
  ✅ MUST: Stabilire clear completion criteria per ogni task
  ❌ FORBIDDEN: Iniziare implementazione complessa senza TodoWrite list

🔒 ENFORCEMENT: TodoWrite tool integrato in Claude Code
📊 VALIDATION: Task list deve esistere prima di implementazione
```

#### Step 5: APPROVAZIONE (MANDATORY)
```
🎯 OBIETTIVO: Consenso esplicito prima di procedere
📋 REGOLE OBBLIGATORIE:
  ✅ MUST: Presentare piano di implementazione completo
  ✅ MUST: Mostrare Context7 research findings
  ✅ MUST: Ottenere approvazione esplicita dall'utente
  ✅ MUST: Confermare comprensione di acceptance criteria
  ❌ FORBIDDEN: Procedere senza "OK", "procedi", "approvato" esplicito

🔒 ENFORCEMENT: Memory system registra approval come "decision"
📊 VALIDATION: Verificare approval record prima di commit
```

#### Step 6: IMPLEMENTAZIONE (MANDATORY - Guided)
```
🎯 OBIETTIVO: Sviluppo incrementale con verifica continua
📋 REGOLE OBBLIGATORIE:
  ✅ MUST: Implementare un micro-task alla volta
  ✅ MUST: Mark TodoWrite task "in_progress" prima di iniziare
  ✅ MUST: Mark TodoWrite task "completed" immediatamente dopo finish
  ✅ MUST: Documentare codice con docstrings e type hints
  ✅ MUST: Seguire DevStream code quality standards
  ❌ FORBIDDEN: Implementare multiple task in parallelo senza approval

🔒 ENFORCEMENT: PostToolUse hook registra automaticamente codice in memory
📊 VALIDATION: Verificare che ogni file scritto sia registrato in memory
```

#### Step 7: VERIFICA/TEST (MANDATORY)
```
🎯 OBIETTIVO: Validazione severa e completa
📋 REGOLE OBBLIGATORIE:
  ✅ MUST: Scrivere test per OGNI nuova feature
  ✅ MUST: Raggiungere 95%+ test coverage per nuovo codice
  ✅ MUST: Validare performance e scalability
  ✅ MUST: Eseguire integration tests end-to-end
  ✅ MUST: Verificare error handling e edge cases
  ❌ FORBIDDEN: Commit senza test o con test failing

🔒 ENFORCEMENT: Hook system richiede test validation prima di completion
📊 VALIDATION: Test results devono essere documentati in memory
```

---

## 🔄 REGOLE PRESCRITTIVE - Task Lifecycle Management

### Task Creation (MANDATORY Rules)

**WHEN**: Quando si identifica lavoro che richiede > 30 minuti

**RULES**:
```bash
✅ MUST: Use mcp__devstream__devstream_create_task
✅ MUST: Definire title chiaro e description dettagliata
✅ MUST: Specificare task_type corretto (analysis/coding/documentation/testing/review/research)
✅ MUST: Assegnare priority realistica (1-10 scale)
✅ MUST: Associare a phase_name appropriata
✅ MUST: Registrare in DevStream MCP server
❌ FORBIDDEN: Creare task manualmente senza MCP tool
```

**ENFORCEMENT**: Task non registrati in MCP non sono tracciati dal sistema

### Task Execution (MANDATORY Rules)

**WHEN**: Durante implementazione di task esistente

**RULES**:
```bash
✅ MUST: Mark task "active" via mcp__devstream__devstream_update_task
✅ MUST: Seguire 7-step workflow (Discussione → Verifica/Test)
✅ MUST: Update progress con notes dettagliate
✅ MUST: Registrare decisions e learnings in memory
✅ MUST: Mantenere TodoWrite list aggiornata in real-time
❌ FORBIDDEN: Lavorare su multiple task simultaneously senza explicit approval
```

**ENFORCEMENT**: Hook system monitora task status e tool usage

### Task Completion (MANDATORY Rules)

**WHEN**: Al completamento di tutti acceptance criteria

**RULES**:
```bash
✅ MUST: Verificare che tutti TodoWrite task siano "completed"
✅ MUST: Verificare che tutti test passino (100% pass rate)
✅ MUST: Mark task "completed" via mcp__devstream__devstream_update_task
✅ MUST: Registrare lessons learned in memory
✅ MUST: Commit codice con messaggio descrittivo
✅ MUST: Push su GitHub se richiesto
❌ FORBIDDEN: Mark "completed" con test failing o TodoWrite pending
```

**ENFORCEMENT**: Hook system valida completion criteria automaticamente

---

## 💾 REGOLE PRESCRITTIVE - Memory System

### Automatic Memory Storage (ENFORCED by PostToolUse Hook)

**WHEN**: Automatico dopo OGNI tool execution (Write, Edit, Bash, etc.)

**WHAT Gets Stored**:
```python
Content Types (MANDATORY):
- "code"          → Source code scritto/modificato
- "documentation" → Markdown, docs, comments
- "context"       → Project context, decisions
- "output"        → Tool execution results
- "error"         → Error messages e resolutions
- "decision"      → Architectural/technical decisions
- "learning"      → Lessons learned, insights
```

**RULES**:
```bash
✅ AUTOMATIC: PostToolUse hook registra automaticamente
✅ AUTOMATIC: Content preview estratto (primi 300 chars)
✅ AUTOMATIC: Keywords estratti da content
✅ AUTOMATIC: Vector embeddings generati via Ollama
✅ AUTOMATIC: Storage in SQLite + sqlite-vec
❌ NO ACTION REQUIRED: Sistema completamente automatico
```

**USER ACTION**: Nessuna - completamente automatico

### Memory Search & Retrieval (ENFORCED by PreToolUse Hook)

**WHEN**: Automatico prima di OGNI tool execution

**HOW It Works**:
```python
PreToolUse Hook:
1. Detect relevant libraries (Context7 detection)
2. Search DevStream memory for related content
3. Assemble hybrid context (Context7 + Memory)
4. Inject into Claude context window
5. Respect token budget limits
```

**RULES**:
```bash
✅ AUTOMATIC: PreToolUse hook cerca automaticamente
✅ AUTOMATIC: Hybrid search (semantic + keyword) via RRF algorithm
✅ AUTOMATIC: Token budget management (max 5000 tokens Context7, 2000 tokens Memory)
✅ AUTOMATIC: Context priority ordering (Context7 > Memory > Project)
✅ AUTOMATIC: Relevance filtering (threshold 0.5)
❌ NO ACTION REQUIRED: Sistema completamente automatico
```

**USER ACTION**: Nessuna - completamente automatico

### Manual Memory Operations (OPTIONAL)

**WHEN**: Per operazioni avanzate o query specifiche

**TOOLS**:
```bash
# Store custom memory
mcp__devstream__devstream_store_memory:
  content: "Important decision or context"
  content_type: "decision" | "learning" | ...
  keywords: ["keyword1", "keyword2"]

# Search memory
mcp__devstream__devstream_search_memory:
  query: "search query"
  content_type: "code" | "documentation" | ...  # optional filter
  limit: 10  # default
```

**RULES**:
```bash
✅ OPTIONAL: Manual operations per query avanzate
✅ USE CASE: Ricerca specifica di decisions/learnings passati
✅ USE CASE: Store di context critico prima di session end
❌ NOT REQUIRED: Sistema automatico gestisce 99% dei casi
```

---

## 🔍 REGOLE PRESCRITTIVE - Context Injection

### Context7 Integration (ENFORCED by PreToolUse Hook)

**WHEN**: Automatico quando si lavora con librerie/framework

**TRIGGERS** (Automatic Detection):
```python
✅ Import statements: import pytest, from fastapi import ...
✅ Library mentions: "how to use FastAPI", "pytest async testing"
✅ Code patterns: async/await, decorators, @pytest.mark.asyncio
✅ Documentation requests: "show me pytest docs"
```

**RULES**:
```bash
✅ AUTOMATIC: Context7 detect libraries automaticamente
✅ AUTOMATIC: Retrieve docs via mcp__context7__get-library-docs
✅ AUTOMATIC: Inject in context window (max 5000 tokens)
✅ AUTOMATIC: Priority ordering (official docs > examples > best practices)
❌ NO ACTION REQUIRED: Completamente automatico
```

**USER ACTION**: Nessuna - sistema automatico

**CONFIGURATION**:
```bash
# .env.devstream (Optional tuning)
DEVSTREAM_CONTEXT7_ENABLED=true                 # Enable/disable
DEVSTREAM_CONTEXT7_AUTO_DETECT=true             # Auto-detection
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=5000            # Max tokens
```

### DevStream Memory Context (ENFORCED by PreToolUse Hook)

**WHEN**: Automatico per OGNI tool execution

**WHAT Gets Injected**:
```python
Priority Order (MANDATORY):
1. Context7 Documentation (highest priority, 5000 tokens max)
2. DevStream Memory (medium priority, 2000 tokens max)
   - Related code from previous sessions
   - Relevant decisions and learnings
   - Project-specific context
3. Current File Context (lowest priority, remaining budget)
```

**RULES**:
```bash
✅ AUTOMATIC: Hybrid search in DevStream memory
✅ AUTOMATIC: Semantic + keyword search via RRF
✅ AUTOMATIC: Relevance filtering (threshold 0.5)
✅ AUTOMATIC: Token budget enforcement
✅ AUTOMATIC: Context assembly and injection
❌ NO ACTION REQUIRED: Completamente automatico
```

**USER ACTION**: Nessuna - sistema automatico

**CONFIGURATION**:
```bash
# .env.devstream (Optional tuning)
DEVSTREAM_CONTEXT_INJECTION_ENABLED=true        # Enable/disable
DEVSTREAM_CONTEXT_MAX_TOKENS=2000               # Max tokens
DEVSTREAM_CONTEXT_RELEVANCE_THRESHOLD=0.5       # Min relevance
```

---

## 🐍 REGOLE PRESCRITTIVE - Python Environment

### 🚨 MANDATORY: Virtual Environment Usage

**CRITICAL RULE**: SEMPRE utilizzare `.devstream` venv per TUTTI i comandi Python.

**ENFORCEMENT**: Hook system richiede `.devstream/bin/python` in settings.json

#### Configuration Standard (MANDATORY)
```bash
Venv Name:      .devstream
Python Version: 3.11.x
Location:       /Users/fulvioventura/devstream/.devstream/
Interpreter:    .devstream/bin/python
```

#### Session Start Checklist (MANDATORY)

**MUST Execute at Start of EVERY Session**:
```bash
# 1. Verify venv exists
if [ ! -d ".devstream" ]; then
  echo "❌ CRITICAL: Venv missing - creating..."
  python3.11 -m venv .devstream
fi

# 2. Verify Python version (MUST be 3.11.x)
.devstream/bin/python --version

# 3. Verify critical dependencies
.devstream/bin/python -m pip list | grep -E "(cchooks|aiohttp|structlog)"
```

**FORBIDDEN**:
```bash
❌ python script.py           # Global Python
❌ python3 script.py          # Global Python
❌ uv run script.py           # Isolated environment (non-persistent)
```

**REQUIRED**:
```bash
✅ .devstream/bin/python script.py
✅ .devstream/bin/python -m pytest
✅ .devstream/bin/python -m pip install package
```

#### First-Time Setup (MANDATORY when venv missing)

**EXECUTE in order**:
```bash
# 1. Create venv with Python 3.11
python3.11 -m venv .devstream

# 2. Upgrade pip (MANDATORY)
.devstream/bin/python -m pip install --upgrade pip

# 3. Install base dependencies
.devstream/bin/python -m pip install -r requirements.txt

# 4. Install hook system dependencies (CRITICAL)
.devstream/bin/python -m pip install \
  "cchooks>=0.1.4" \
  "aiohttp>=3.8.0" \
  "structlog>=23.0.0" \
  "python-dotenv>=1.0.0"

# 5. Verify installation
.devstream/bin/python -m pip list | head -20
```

#### Hook System Configuration (MANDATORY)

**settings.json MUST use venv interpreter**:
```json
{
  "hooks": {
    "PreToolUse": [{
      "hooks": [{
        "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/memory/pre_tool_use.py"
      }]
    }],
    "PostToolUse": [{
      "hooks": [{
        "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/memory/post_tool_use.py"
      }]
    }],
    "UserPromptSubmit": [{
      "hooks": [{
        "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/context/user_query_context_enhancer.py"
      }]
    }]
  }
}
```

**CRITICAL**: Hooks MUST use `.devstream/bin/python`, NOT system Python

---

## 🛠 REGOLE PRESCRITTIVE - Tools & Configuration

### Context7 Usage (MANDATORY for Research)

**WHEN**: Per ogni decisione tecnica maggiore o nuova tecnologia

**WORKFLOW (MANDATORY)**:
```bash
1. ✅ MUST: Use mcp__context7__resolve-library-id
   → Input: Nome libreria/framework
   → Output: Context7-compatible library ID

2. ✅ MUST: Use mcp__context7__get-library-docs
   → Input: Library ID da step 1
   → Output: Documentation (max 5000 tokens)

3. ✅ MUST: Analyze findings and document rationale

4. ✅ MUST: Apply research-backed patterns

5. ❌ FORBIDDEN: Skip Context7 per nuove tecnologie
```

**ENFORCEMENT**: PreToolUse hook abilita Context7 automaticamente

### TodoWrite Usage (MANDATORY for Planning)

**WHEN**: Per OGNI task non-triviale (> 15 minuti stimati)

**RULES (MANDATORY)**:
```bash
✅ MUST: Create TodoWrite list BEFORE implementation
✅ MUST: Micro-task breakdown (10-15 min each)
✅ MUST: Mark "in_progress" when starting task
✅ MUST: Mark "completed" IMMEDIATELY after finishing
✅ MUST: Keep ONE task "in_progress" at a time
❌ FORBIDDEN: Start implementation without TodoWrite list
❌ FORBIDDEN: Mark "completed" con pending sub-tasks
```

**FORMAT (MANDATORY)**:
```json
{
  "content": "Imperative form (e.g., Run tests)",
  "activeForm": "Present continuous (e.g., Running tests)",
  "status": "pending" | "in_progress" | "completed"
}
```

**ENFORCEMENT**: System tracks TodoWrite compliance

### Testing Requirements (MANDATORY)

**COVERAGE (MANDATORY)**:
```bash
✅ MUST: 95%+ coverage for NEW code
✅ MUST: 100% test pass rate before commit
✅ MUST: Integration tests for E2E workflows
✅ MUST: Performance validation con metrics
✅ MUST: Error handling validation
❌ FORBIDDEN: Commit con failing tests
❌ FORBIDDEN: Commit senza test per new features
```

**TEST STRUCTURE (MANDATORY)**:
```bash
tests/
├── unit/              ← Fast, isolated tests
│   ├── hooks/
│   ├── memory/
│   └── tasks/
├── integration/       ← Integration tests
│   ├── hooks/
│   ├── memory/
│   └── context/
└── fixtures/          ← Test data and fixtures
```

**EXECUTION (MANDATORY)**:
```bash
# Use venv interpreter
.devstream/bin/python -m pytest tests/ -v

# With coverage
.devstream/bin/python -m pytest tests/ --cov=.claude/hooks/devstream --cov-report=html
```

---

## 📖 REGOLE PRESCRITTIVE - Documentation

### Code Documentation (MANDATORY)

**EVERY function/class MUST have**:
```python
✅ MUST: Docstring con description, params, returns, raises
✅ MUST: Type hints per ALL parameters e return values
✅ MUST: Inline comments per logica complessa (> 5 righe)
✅ MUST: Architecture decisions documentate in-code
❌ FORBIDDEN: Codice senza docstring
❌ FORBIDDEN: Missing type hints

# Example (MANDATORY format):
def hybrid_search(
    self,
    query: str,
    limit: int = 10,
    content_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Perform hybrid search combining semantic and keyword search.

    Uses Reciprocal Rank Fusion (RRF) algorithm to combine results
    from both semantic (vector) and keyword (FTS5) searches.

    Args:
        query: Search query string
        limit: Maximum results to return (default: 10)
        content_type: Optional filter by content type

    Returns:
        List of memory records sorted by relevance score

    Raises:
        DatabaseError: If database query fails

    Note:
        RRF weights: semantic 60%, keyword 40%
    """
    # Implementation...
```

**ENFORCEMENT**: Code review richiede docstrings complete

### Project Documentation (MANDATORY)

**docs/ Structure (MANDATORY)**:
```bash
docs/
├── architecture/     ← System design, technical decisions (MANDATORY for new systems)
├── api/             ← API reference, schemas (MANDATORY for APIs)
├── deployment/      ← Deployment guides, validation (MANDATORY for production)
├── guides/          ← User guides, how-tos (MANDATORY for user-facing features)
├── development/     ← Developer guides, roadmap (MANDATORY for complex features)
└── tutorials/       ← Hands-on tutorials (OPTIONAL)
```

**RULES (MANDATORY)**:
```bash
✅ MUST: Create docs for EVERY major feature
✅ MUST: Update docs BEFORE marking task complete
✅ MUST: Include code examples in guides
✅ MUST: Keep docs in sync with code
❌ FORBIDDEN: .md files in project root (except README.md, CLAUDE.md, PROJECT_STRUCTURE.md)
❌ FORBIDDEN: Outdated documentation
```

**ENFORCEMENT**: Task completion richiede documentation update

### Progress Documentation (MANDATORY)

**MUST Document**:
```bash
✅ TodoWrite tracking per OGNI task
✅ Implementation notes per OGNI phase
✅ Lessons learned per OGNI completed task
✅ Decision rationale per OGNI architectural choice
✅ Test results e validation reports
```

**STORAGE**: Automatico via PostToolUse hook in memory (content_type: "learning", "decision")

---

## 🎯 REGOLE PRESCRITTIVE - Quality Standards

### Code Quality (MANDATORY)

**Type Safety (MANDATORY)**:
```bash
✅ MUST: Full type hints per ALL functions/methods
✅ MUST: mypy compliance (zero errors)
✅ MUST: Use strict mode: mypy --strict
❌ FORBIDDEN: Any type hints (use specific types)
❌ FORBIDDEN: mypy errors in production code
```

**Error Handling (MANDATORY)**:
```bash
✅ MUST: Structured exception hierarchy
✅ MUST: Logging per OGNI exception
✅ MUST: Graceful degradation per external dependencies
✅ MUST: User-friendly error messages
✅ MUST: Error context in exceptions
❌ FORBIDDEN: Bare except: clauses
❌ FORBIDDEN: Silent failures (always log)
```

**Performance (MANDATORY)**:
```bash
✅ MUST: async/await per I/O operations
✅ MUST: Connection pooling per database
✅ MUST: Token budget enforcement per Context7
✅ MUST: Performance testing con metrics
❌ FORBIDDEN: Blocking I/O in async context
❌ FORBIDDEN: No performance validation
```

**Maintainability (MANDATORY)**:
```bash
✅ MUST: Follow SOLID principles
✅ MUST: Single responsibility per function/class
✅ MUST: Max function length: 50 lines
✅ MUST: Max cyclomatic complexity: 10
✅ MUST: Descriptive variable/function names
❌ FORBIDDEN: God objects/functions
❌ FORBIDDEN: Cryptic abbreviations
```

### Architecture Quality (MANDATORY)

**Separation of Concerns (MANDATORY)**:
```bash
✅ MUST: Clear module boundaries
✅ MUST: Layered architecture (hooks → utils → core)
✅ MUST: Interface segregation
❌ FORBIDDEN: Circular dependencies
❌ FORBIDDEN: Tight coupling
```

**Configuration Management (MANDATORY)**:
```bash
✅ MUST: Environment-based config (.env.devstream)
✅ MUST: Validation per ALL config values
✅ MUST: Defaults per ALL optional configs
✅ MUST: Documentation per OGNI config option
❌ FORBIDDEN: Hardcoded values
❌ FORBIDDEN: Config in code
```

**Logging (MANDATORY)**:
```bash
✅ MUST: Structured logging con structlog
✅ MUST: Context in ALL log messages
✅ MUST: Appropriate log levels (DEBUG, INFO, WARNING, ERROR)
✅ MUST: Log rotation configuration
❌ FORBIDDEN: print() statements (use logger)
❌ FORBIDDEN: Logging sensitive data
```

---

## 🚀 REGOLE PRESCRITTIVE - Implementation Patterns

### Research-Driven Development Pattern (MANDATORY)

**WHEN**: Per OGNI nuova feature o tecnologia

**PATTERN (MANDATORY sequence)**:
```python
Step 1: RESEARCH (Context7)
  ✅ MUST: Use Context7 per best practices
  ✅ MUST: Document findings e rationale
  → Output: Research-backed approach

Step 2: DESIGN
  ✅ MUST: Create architecture basata su research
  ✅ MUST: Define clear interfaces
  → Output: Design document/diagram

Step 3: IMPLEMENT
  ✅ MUST: Follow validated patterns da research
  ✅ MUST: One micro-task at a time
  → Output: Production-ready code

Step 4: TEST
  ✅ MUST: Comprehensive testing (95%+ coverage)
  ✅ MUST: Validate assumptions da research
  → Output: Test suite passing

Step 5: DOCUMENT
  ✅ MUST: Capture lessons learned
  ✅ MUST: Update project documentation
  → Output: Complete documentation

❌ FORBIDDEN: Skip research step
❌ FORBIDDEN: Implement before design
❌ FORBIDDEN: Deploy without testing
```

**ENFORCEMENT**: Hook system registra research findings in memory

### Micro-Task Execution Pattern (MANDATORY)

**WHEN**: Per implementazione di ANY complex feature

**PATTERN (MANDATORY sequence)**:
```python
Step 1: ANALYZE
  ✅ MUST: Break down feature in micro-tasks (10-15 min each)
  ✅ MUST: Identify dependencies
  → Output: Task breakdown

Step 2: PLAN (TodoWrite)
  ✅ MUST: Create TodoWrite list
  ✅ MUST: Define completion criteria per task
  → Output: Tracked task list

Step 3: EXECUTE
  ✅ MUST: One task at a time
  ✅ MUST: Mark "in_progress" → work → mark "completed"
  → Output: Completed micro-task

Step 4: VERIFY
  ✅ MUST: Test dopo OGNI task completion
  ✅ MUST: Verify integration con existing code
  → Output: Validated integration

Step 5: INTEGRATE
  ✅ MUST: Merge con existing codebase
  ✅ MUST: Update documentation
  → Output: Integrated feature

❌ FORBIDDEN: Multiple tasks in parallelo senza approval
❌ FORBIDDEN: Skip testing after task
```

**ENFORCEMENT**: TodoWrite tool tracks compliance

### Approval Workflow Pattern (MANDATORY)

**WHEN**: BEFORE implementazione di ANY significant change

**PATTERN (MANDATORY sequence)**:
```python
Step 1: DISCUSS
  ✅ MUST: Present approach e trade-offs
  ✅ MUST: Identify risks e assumptions
  → Output: Documented discussion

Step 2: RESEARCH
  ✅ MUST: Use Context7 per validation
  ✅ MUST: Research alternative approaches
  → Output: Research-backed recommendation

Step 3: APPROVE
  ✅ MUST: Get explicit approval dall'utente
  ✅ MUST: Confirm acceptance criteria
  → Output: Documented approval

Step 4: IMPLEMENT
  ✅ MUST: Follow approved approach exactly
  ✅ MUST: No deviations senza approval
  → Output: Implementation matching approval

Step 5: REVIEW
  ✅ MUST: Validate results insieme
  ✅ MUST: Document learnings
  → Output: Validated completion

❌ FORBIDDEN: Implement without approval
❌ FORBIDDEN: Deviate from approved approach senza discussion
```

**ENFORCEMENT**: Memory system registra approval as "decision"

---

## 📊 REGOLE PRESCRITTIVE - Success Metrics

### Development Metrics (MANDATORY Targets)

**MUST Achieve**:
```bash
✅ Task Completion Rate:    100% (all tasks marked completed)
✅ Test Coverage:            95%+ per NUOVO codice
✅ Test Pass Rate:           100% (zero failing tests)
✅ Code Quality:             Zero mypy errors
✅ Cyclomatic Complexity:    Max 10 per function
✅ Documentation Coverage:   100% docstrings
✅ Performance:              Meet/exceed targets
```

**VALIDATION**: Verificare prima di OGNI commit

### Process Metrics (MANDATORY Tracking)

**MUST Track**:
```bash
✅ Research Quality:         Context7 usage per OGNI major decision
✅ Collaboration:            Approval workflow adherence (100%)
✅ Learning:                 Documented lessons learned per phase
✅ Innovation:               Research-backed technology choices
✅ Delivery:                 On-time delivery (planned vs actual)
✅ Memory Usage:             Automatic storage tracking
✅ Context Injection:        Automatic injection rate
```

**STORAGE**: Automatico via DevStream memory system

---

## 🔧 REGOLE PRESCRITTIVE - File Organization

### 📁 Project Structure (MANDATORY)

**CRITICAL**: SEMPRE seguire la struttura definita in PROJECT_STRUCTURE.md

#### Documentation Files (MANDATORY Rules)

**FORBIDDEN**:
```bash
❌ .md files in project root (except README.md, CLAUDE.md, PROJECT_STRUCTURE.md)
❌ Random documentation locations
❌ Temporary doc files
```

**REQUIRED**:
```bash
✅ USE docs/ directory con struttura categorizzata:

docs/
├── architecture/     ← System design, decisions (MANDATORY per new systems)
├── api/             ← API reference, schemas (MANDATORY per APIs)
├── development/     ← Developer guides, roadmap
├── deployment/      ← Production deployment, validation
├── guides/          ← User guides, how-tos (MANDATORY per features)
└── tutorials/       ← Hands-on tutorials

Examples CORRECT:
✅ docs/deployment/production-deployment-guide.md
✅ docs/architecture/hook-system-design.md
✅ docs/guides/devstream-automatic-features-guide.md

Examples WRONG:
❌ production_deployment.md (root)
❌ hook_design.md (root)
❌ feature_guide.md (root)
```

**ENFORCEMENT**: File creation validata da PROJECT_STRUCTURE.md

#### Test Files (MANDATORY Rules)

**FORBIDDEN**:
```bash
❌ Test files in project root
❌ Tests mixed with source code
❌ Unorganized test structure
```

**REQUIRED**:
```bash
✅ USE tests/ directory con struttura per tipo:

tests/
├── unit/           ← Fast, isolated (< 1s per test)
│   ├── hooks/
│   ├── memory/
│   └── tasks/
├── integration/    ← Integration tests (< 10s per test)
│   ├── hooks/
│   ├── memory/
│   └── context/
└── fixtures/       ← Test data and fixtures

Examples CORRECT:
✅ tests/unit/hooks/test_pre_tool_use.py
✅ tests/integration/memory/test_hybrid_search.py
✅ tests/fixtures/sample_memory_data.json

Examples WRONG:
❌ test_hooks.py (root)
❌ validation_test.py (root)
❌ .claude/hooks/test_hook.py (mixed with source)
```

**ENFORCEMENT**: pytest.ini configuration enforces structure

#### File Creation Checklist (MANDATORY)

**BEFORE creating ANY file**:
```bash
1. ✅ Check PROJECT_STRUCTURE.md per correct location
2. ✅ Identify correct directory based on file type
3. ✅ Use naming convention (kebab-case=docs, snake_case=code)
4. ✅ Verify directory exists (create if needed)
5. ✅ Create file in correct location
```

**NAMING CONVENTIONS (MANDATORY)**:
```bash
Documentation: kebab-case
  ✅ devstream-automatic-features-guide.md
  ✅ hook-system-validation-report.md
  ❌ devstream_guide.md (snake_case)
  ❌ HookSystemReport.md (PascalCase)

Code: snake_case
  ✅ pre_tool_use.py
  ✅ hybrid_search_manager.py
  ❌ PreToolUse.py (PascalCase for classes inside only)
  ❌ pre-tool-use.py (kebab-case)
```

---

## 🚨 REGOLA FONDAMENTALE - Problem Solving

### ⚡⚡⚡ USE CONTEXT7 TO SOLVE - NEVER SIMPLIFY ⚡⚡⚡

**CRITICAL PRINCIPLE**: When encountering complex technical problems:

**MANDATORY Approach**:
```bash
✅ MUST: Use Context7 per research solution
✅ MUST: Ricerca best practices e patterns
✅ MUST: Implement research-backed solution
✅ MUST: Maintain ALL features functional
✅ MUST: Test solution thoroughly
```

**FORBIDDEN Approaches**:
```bash
❌ FORBIDDEN: Disable features to "fix" problem
❌ FORBIDDEN: Remove functionality as workaround
❌ FORBIDDEN: Create temporary workarounds
❌ FORBIDDEN: Simplify to avoid complexity
❌ FORBIDDEN: Skip research step
```

**ENFORCEMENT**: Code review rejects workarounds and feature disabling

---

## 🎉 REGOLE PRESCRITTIVE - Success Tracking

### Production-Ready Deliverables (EXAMPLES)

**Phase 2: Testing Implementation** (2025-09-30)
```bash
✅ RISULTATO: 100% test pass rate (23/23 tests)
📊 METRICS: 30% coverage, < 2s execution time
🎯 METODOLOGIA: Research → Test-First → Validation
⏱️ TIMELINE: Completato in anticipo (-11 min vs plan)
🔧 TOOLS: pytest, pytest-asyncio, Context7, TodoWrite

LESSONS LEARNED (stored in memory):
- Integration tests validate user workflows effectively
- Non-blocking design critical for production reliability
- Context7 research patterns accelerate implementation
- Micro-task breakdown maintains focus and momentum
```

**Phase 3: Documentation & Validation** (2025-09-30)
```bash
✅ RISULTATO: Production-ready documentation suite
📊 METRICS: 3 major docs (600+ lines user guide, 700+ lines validation)
🎯 METODOLOGIA: User-first documentation approach
⏱️ TIMELINE: On schedule
🔧 TOOLS: Markdown, validation checklists, Context7 research

PRODUCTION STATUS: ✅ APPROVED FOR DEPLOYMENT
- All functional requirements validated
- All quality metrics exceeded
- Zero critical issues identified
- Complete documentation provided
```

**STORAGE**: ALL learnings automatically stored in memory (content_type: "learning")

---

## 📚 APPENDIX - System Integration Reference

### Hook System Integration Points

**PreToolUse Hook** (Automatic Context Injection):
```python
Location: .claude/hooks/devstream/memory/pre_tool_use.py
Trigger: Before EVERY tool execution
Purpose: Inject Context7 + DevStream memory context
Config: .env.devstream (DEVSTREAM_CONTEXT_INJECTION_ENABLED)
```

**PostToolUse Hook** (Automatic Memory Storage):
```python
Location: .claude/hooks/devstream/memory/post_tool_use.py
Trigger: After EVERY tool execution
Purpose: Store code/docs/context in memory
Config: .env.devstream (DEVSTREAM_MEMORY_ENABLED)
```

**UserPromptSubmit Hook** (Query Enhancement):
```python
Location: .claude/hooks/devstream/context/user_query_context_enhancer.py
Trigger: On EVERY user prompt submit
Purpose: Enhance query with project context
Config: .env.devstream (DEVSTREAM_QUERY_ENHANCEMENT_ENABLED)
```

### MCP Server Integration

**DevStream MCP Server**:
```bash
Location: mcp-devstream-server/
Port: 3000
Tools:
  - devstream_create_task
  - devstream_update_task
  - devstream_list_tasks
  - devstream_store_memory
  - devstream_search_memory
  - devstream_list_plans
```

**Configuration**:
```json
// .claude/mcp_servers.json
{
  "devstream": {
    "command": "node",
    "args": ["mcp-devstream-server/dist/index.js"],
    "env": {
      "DEVSTREAM_DB_PATH": "data/devstream.db"
    }
  }
}
```

### Environment Configuration Reference

**Critical Variables (.env.devstream)**:
```bash
# Memory System (MANDATORY for automatic features)
DEVSTREAM_MEMORY_ENABLED=true
DEVSTREAM_MEMORY_FEEDBACK_LEVEL=minimal

# Context7 Integration (MANDATORY for library detection)
DEVSTREAM_CONTEXT7_ENABLED=true
DEVSTREAM_CONTEXT7_AUTO_DETECT=true
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=5000

# Context Injection (MANDATORY for automatic context)
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