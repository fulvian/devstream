# Getting Started with DevStream

**Version**: 0.1.0-beta
**Audience**: New users
**Time to Complete**: 15 minutes

This guide walks you through your first experience with DevStream, from creating tasks to leveraging semantic memory and specialized agents.

## Table of Contents

- [What is DevStream?](#what-is-devstream)
- [First Steps](#first-steps)
- [Basic Workflow](#basic-workflow)
- [Working with Agents](#working-with-agents)
- [Using Semantic Memory](#using-semantic-memory)
- [Best Practices](#best-practices)
- [Next Steps](#next-steps)

---

## What is DevStream?

DevStream is an integrated task management and cross-session memory system that transforms Claude Code into a proactive development assistant with:

- **Structured Task Management** - Break work into micro-tasks (10-15 min max)
- **Semantic Memory** - Automatic storage and retrieval of code, decisions, and context
- **Intelligent Context Injection** - Context7 library docs + DevStream memory before every tool use
- **Specialized Agents** - 17 domain and task specialists for multi-stack development
- **Auto-Delegation** - Pattern-based intelligent agent routing

### Key Benefits

**For Solo Developers**:
- Never lose context between sessions
- Automatic research-backed best practices (Context7)
- Quality gates before every commit (@code-reviewer)

**For Teams**:
- Shared semantic memory across team members
- Consistent development patterns
- Automated code review and documentation

**For Complex Projects**:
- Multi-stack coordination (@tech-lead orchestration)
- Cross-language refactoring support
- Performance optimization workflows

---

## First Steps

### Verify Installation

Before starting, ensure DevStream is properly installed:

```bash
# Run verification script
.devstream/bin/python scripts/verify-install.py

# Expected: All checks PASS (warnings acceptable for optional components)
```

If verification fails, see [INSTALLATION.md](../../INSTALLATION.md#troubleshooting).

### Start MCP Server

DevStream requires the MCP server for task management:

```bash
# In separate terminal
cd mcp-devstream-server
npm start

# Expected output:
# MCP DevStream Server listening on port 3000
```

**Keep this terminal open** while using DevStream.

### Verify Hook System

Create a test file to verify hooks are working:

```
In Claude Code session:
"Create a test file: src/hello.py with content 'print(\"Hello DevStream\")'"
```

Check logs to confirm hooks executed:

```bash
# PreToolUse hook (before Write tool)
tail -20 ~/.claude/logs/devstream/pre_tool_use.log
# Look for: "PreToolUse triggered for file: src/hello.py"

# PostToolUse hook (after Write tool)
tail -20 ~/.claude/logs/devstream/post_tool_use.log
# Look for: "Memory stored successfully: src/hello.py"
```

---

## Basic Workflow

DevStream enforces a structured 7-step workflow for every task:

```
1. DISCUSSION → 2. ANALYSIS → 3. RESEARCH → 4. PLANNING → 5. APPROVAL → 6. IMPLEMENTATION → 7. VERIFICATION
```

### Example: Simple Python Function

Let's walk through creating a FastAPI endpoint.

#### Step 1: Discussion

```
User: "I need a FastAPI endpoint to list users from the database"

Claude (DevStream): "Let's discuss the requirements:
- Should we paginate results? (recommended for large datasets)
- Do we need filtering (by email, role, etc.)?
- What user fields should be exposed (exclude password/tokens)?
- Expected response time SLA?"

User: "Yes to pagination (default 10, max 100), filter by email, exclude sensitive fields"
```

**What happened**: DevStream registers discussion as `content_type: "decision"` in memory.

#### Step 2: Analysis

```
Claude (DevStream): "Analyzing codebase for similar patterns...

Found:
- Existing FastAPI setup in src/api/main.py
- User model in src/models/user.py (has password field - will exclude)
- Pagination pattern in src/api/posts.py (we can reuse)
- No email filtering exists (new feature)

Estimated complexity: Medium (15-20 minutes split into 2 micro-tasks)"
```

**What happened**: DevStream searches memory for similar code, identifies patterns, estimates effort.

#### Step 3: Research (Context7)

```
Claude (DevStream): "Researching FastAPI best practices via Context7...

📚 Context7 Documentation Retrieved:
Library: /tiangolo/fastapi
Topics: query parameters, pagination, response models, filtering

Key findings:
✓ Use Query() for validation and defaults
✓ Pydantic BaseModel for response serialization
✓ SQLAlchemy offset/limit for pagination
✓ Optional[str] for filter parameters
```

**What happened**: PreToolUse hook detected FastAPI context, retrieved official docs.

#### Step 4: Planning (TodoWrite)

```
Claude (DevStream): "Creating implementation plan...

TodoWrite Tasks:
[pending] 1. Create UserResponse Pydantic model (exclude password)
[pending] 2. Implement GET /users endpoint with pagination
[pending] 3. Add email filter with partial match
[pending] 4. Write unit tests (95%+ coverage)
[pending] 5. Run tests and validate

Approve plan?"

User: "Approved"
```

**What happened**: DevStream creates granular micro-tasks, each 10-15 min max.

#### Step 5: Approval

```
Claude (DevStream): "Plan approved. Ready to implement.

Context Assembly:
✓ Context7 FastAPI docs (3500 tokens)
✓ DevStream memory: User model, pagination pattern (1200 tokens)
✓ Current file context (remaining budget)

Proceeding with implementation..."
```

**What happened**: DevStream waits for explicit approval before any code changes.

#### Step 6: Implementation (Guided)

```
[in_progress] 1. Create UserResponse Pydantic model
   → Implementation: src/models/user.py
   → Mark completed
[completed] 1. Create UserResponse Pydantic model

[in_progress] 2. Implement GET /users endpoint
   → Implementation: src/api/users.py
   → Mark completed
[completed] 2. Implement GET /users endpoint

... (continues for all micro-tasks)
```

**What happened**:
- PostToolUse hook stores each file modification in memory
- Embeddings generated for semantic search
- One task "in_progress" at a time (enforced by TodoWrite)

#### Step 7: Verification/Testing

```
[in_progress] 4. Write unit tests
   → Implementation: tests/api/test_users.py
   → Running: .devstream/bin/python -m pytest tests/api/test_users.py -v
   → Result: 8 passed, 95% coverage ✓
[completed] 4. Write unit tests

Task completion validation:
✓ All TodoWrite tasks completed
✓ Tests 100% pass rate
✓ Coverage 95%+ achieved
✓ No errors in implementation

Ready for commit. Invoking @code-reviewer for quality gate...
```

**What happened**: DevStream validates all completion criteria before marking task done.

---

## Working with Agents

DevStream provides 17 specialized agents across 4 levels:

### Agent Hierarchy

```
Level 1: ORCHESTRATOR
  └── @tech-lead (multi-stack coordination)

Level 2: DOMAIN SPECIALISTS
  ├── @python-specialist (Python, FastAPI, async)
  ├── @typescript-specialist (TypeScript, React, Next.js)
  ├── @rust-specialist (Rust, memory safety)
  ├── @go-specialist (Go, goroutines)
  ├── @database-specialist (SQL, schema, optimization)
  └── @devops-specialist (Docker, Kubernetes, CI/CD)

Level 3: TASK SPECIALISTS
  ├── @api-architect (API design, OpenAPI)
  ├── @performance-optimizer (profiling, optimization)
  ├── @testing-specialist (test strategy, coverage)
  └── @documentation-specialist (technical writing)

Level 4: QUALITY ASSURANCE
  └── @code-reviewer (MANDATORY before commits)
```

### Agent Invocation Patterns

#### Direct Invocation (Single Language)

For tasks in a single language/stack:

```
User: "@python-specialist Create a user authentication service with JWT tokens"

Claude (python-specialist): "I'll implement JWT authentication for Python/FastAPI.

Context Assembly:
✓ Context7: PyJWT library docs
✓ Memory: Existing user model, API structure
✓ Best practices: Token expiration, refresh tokens, secure storage

Implementation plan:
1. Install PyJWT and python-jose
2. Create token generation/validation functions
3. Add authentication middleware
4. Create login/logout endpoints
5. Write comprehensive tests

Proceeding..."
```

**When to use**: Python-only tasks, TypeScript-only tasks, pure database work.

#### Orchestrated Workflow (Multi-Stack)

For features spanning multiple languages:

```
User: "@tech-lead Build a user dashboard with Python backend and React frontend"

Claude (tech-lead): "Analyzing requirements for multi-stack feature...

Architecture:
- Backend: Python/FastAPI REST API
- Frontend: TypeScript/React dashboard
- Integration: OpenAPI client generation

Delegation plan:
1. Delegate @api-architect: Design REST API contract
2. Delegate @python-specialist: Implement backend endpoints
3. Delegate @typescript-specialist: Build React dashboard
4. Delegate @code-reviewer: Validate integration

Invoking @api-architect..."

Claude (api-architect): "Designing API contract...
[Creates OpenAPI specification]"

Claude (tech-lead): "API design complete. Delegating backend implementation...

Task(@python-specialist): 'Implement backend API from OpenAPI spec'"

Claude (python-specialist): "[Implements FastAPI endpoints]"

Claude (tech-lead): "Backend complete. Delegating frontend...

Task(@typescript-specialist): 'Build React dashboard consuming /api/users'"

Claude (typescript-specialist): "[Implements React components]"

Claude (tech-lead): "Full-stack implementation complete. Final validation...

Task(@code-reviewer): 'Review full-stack integration'"

Claude (code-reviewer): "Reviewing integration...
✓ API contract matches implementation
✓ CORS configured correctly
✓ Error handling consistent
✓ Authentication tokens secure
⚠️  Warning: Consider rate limiting on /api/users
✅ PASS - Ready for commit"
```

**When to use**: Multi-language features, architectural decisions, complex refactoring.

### Agent Auto-Delegation (Phase 3)

DevStream can automatically route tasks based on file patterns:

```
User: "Update src/api/users.py to add email validation"

DevStream (auto-delegation):
  Pattern detected: src/api/users.py → *.py
  Confidence: 0.95 (≥ auto-approve threshold)
  Decision: AUTOMATIC delegation
  → Task(@python-specialist)

Claude (python-specialist): "[Implements email validation]"
```

**Configuration**:
```bash
# .env.devstream
DEVSTREAM_AUTO_DELEGATION_ENABLED=true          # Enable auto-delegation
DEVSTREAM_AUTO_DELEGATION_AUTO_APPROVE=0.95     # Confidence threshold for automatic delegation
```

**Confidence Levels**:
- **≥ 0.95**: Automatic delegation (no approval needed)
- **0.85 - 0.94**: Advisory (suggest agent, request approval)
- **< 0.85**: Authorization required (@tech-lead coordination)

---

## Using Semantic Memory

DevStream automatically stores and retrieves context across sessions.

### Automatic Memory Storage

**When**: After EVERY tool execution (Write, Edit, Bash, etc.)

**What gets stored**:
- Code files (with embeddings for semantic search)
- Documentation (architecture decisions, API docs)
- Decisions (discussion outcomes, trade-off analysis)
- Learnings (lessons from debugging, optimization)
- Outputs (test results, build logs)

**Example**:
```
User: "Create src/utils/logger.py with structured logging"

Claude: "[Implements logger.py using structlog]"

PostToolUse Hook (automatic):
  ✓ Content extracted: "import structlog, def get_logger()..."
  ✓ Keywords: ["logging", "structlog", "utils"]
  ✓ Embedding generated (Ollama)
  ✓ Stored in semantic_memory table
  ✓ Indexed for hybrid search (vector + FTS5)
```

### Automatic Memory Retrieval

**When**: Before EVERY tool execution (PreToolUse hook)

**What gets retrieved**:
1. **Context7 Docs** (5000 token budget) - Official library documentation
2. **DevStream Memory** (2000 token budget) - Related code, decisions, learnings
3. **Current File Context** (remaining budget) - File being edited

**Example**:
```
User: "Add error handling to the logger utility"

PreToolUse Hook (automatic):
  Searching DevStream memory for "logger error handling"...

  Results (hybrid search):
  1. src/utils/logger.py (relevance: 0.95)
     Content: "import structlog, def get_logger()..."
  2. Decision: "Use structlog for all logging" (relevance: 0.82)
  3. Learning: "Always log exceptions with context" (relevance: 0.78)

  Searching Context7 for "structlog error handling"...

  Results:
  Library: /hynek/structlog
  Topics: exception logging, context binding, error formatters

  Context assembled (7200 tokens):
  ✓ Context7: structlog docs (3500 tokens)
  ✓ Memory: logger implementation + decisions (2000 tokens)
  ✓ Current: src/utils/logger.py (1700 tokens)

  Injecting context into Claude...
```

### Manual Memory Operations (Advanced)

#### Store Critical Context

For important context that may not trigger automatic storage:

```python
mcp__devstream__devstream_store_memory:
  content: "Decision: Use SQLite with WAL mode for concurrent writes. Tested with 95%+ success rate under load."
  content_type: "decision"
  keywords: ["sqlite", "wal", "concurrency", "performance"]
```

#### Search Memory

To query memory explicitly:

```python
mcp__devstream__devstream_search_memory:
  query: "authentication JWT implementation"
  content_type: "code"  # Optional filter
  limit: 10
```

**Returns**:
```json
[
  {
    "content": "def generate_jwt_token(user_id: int, expires_delta: timedelta = None) -> str...",
    "content_type": "code",
    "keywords": ["jwt", "authentication", "token"],
    "relevance_score": 0.94,
    "created_at": "2025-09-30T10:00:00Z"
  }
]
```

### Memory Search Algorithm

DevStream uses **Reciprocal Rank Fusion (RRF)** hybrid search:

```python
# Combined score from semantic + keyword search
combined_score = (
    (1 / (k + semantic_rank)) * 0.6 +  # 60% weight
    (1 / (k + keyword_rank)) * 0.4     # 40% weight
)
```

**Why hybrid?**
- **Semantic** (vector): Captures meaning ("fast API" ≈ "FastAPI")
- **Keyword** (FTS5): Exact term matches ("pytest" finds "pytest", not "unittest")
- **RRF**: Proven fusion method from sqlite-vec examples

---

## Best Practices

### Task Granularity

**DO**:
✅ Break features into 10-15 minute micro-tasks
✅ One clear objective per micro-task
✅ Mark "in_progress" → work → "completed" immediately

**DON'T**:
❌ Create tasks > 30 minutes
❌ Work on multiple tasks simultaneously
❌ Mark "completed" with pending sub-tasks

### Approval Workflow

**DO**:
✅ Discuss requirements before implementation
✅ Present research findings (Context7)
✅ Get explicit approval ("OK", "Approved", "Proceed")
✅ Document decision rationale

**DON'T**:
❌ Start implementation without approval
❌ Skip research step for new technologies
❌ Assume requirements without discussion

### Agent Usage

**DO**:
✅ Use @tech-lead for multi-stack features
✅ Direct invoke for single-language tasks
✅ ALWAYS invoke @code-reviewer before commits
✅ Trust auto-delegation for clear patterns

**DON'T**:
❌ Skip @code-reviewer quality gate
❌ Manually coordinate multi-agent workflows (use @tech-lead)
❌ Override auto-delegation without reason

### Memory Management

**DO**:
✅ Trust automatic memory storage/retrieval
✅ Use specific keywords for critical context
✅ Store decisions and learnings explicitly
✅ Review memory before major refactoring

**DON'T**:
❌ Manually store code (automatic via PostToolUse)
❌ Store sensitive data (passwords, keys)
❌ Store temporary notes or obvious information

---

## Next Steps

Now that you understand the basics:

1. **Deep Dive into Concepts**:
   - [Core Concepts](core-concepts.md) - Task lifecycle, memory system, hooks
   - [Configuration Guide](configuration.md) - Advanced settings

2. **Learn Agent System**:
   - [Agents Guide](agents-guide.md) - When to use each agent
   - Agent delegation patterns
   - Multi-stack workflows

3. **Advanced Features**:
   - [Troubleshooting Guide](troubleshooting.md) - Common issues
   - [FAQ](faq.md) - Frequently asked questions

4. **Real-World Examples**:
   - Study DevStream's own development
   - Review memory of completed tasks
   - Analyze agent delegation patterns

---

**Congratulations!** You now understand DevStream's workflow and can start building with automated context, specialized agents, and semantic memory.

For questions: [FAQ](faq.md) | [Troubleshooting](troubleshooting.md) | [GitHub Issues](https://github.com/yourusername/devstream/issues)
