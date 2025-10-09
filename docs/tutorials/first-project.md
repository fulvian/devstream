# Tutorial: Your First DevStream Project

## What You'll Learn

In this tutorial, you'll create your first DevStream-powered project from scratch and experience the complete workflow:

- Setting up DevStream for a new project
- Creating and executing your first task
- Understanding semantic memory automatic storage
- Using Context7 for research-driven development
- Completing tasks with quality validation

**Time**: ~45 minutes
**Difficulty**: Beginner

## Prerequisites

Before starting, ensure you have:

- ✅ Python 3.11+ installed
- ✅ Node.js 18+ installed
- ✅ Git installed and configured
- ✅ Claude Code installed
- ✅ Basic understanding of REST APIs
- ✅ Basic terminal/command line knowledge

**Verification**:
```bash
python3.11 --version  # Should show 3.11.x
node --version        # Should show v18.x or higher
git --version         # Should show git version 2.x
```

## What We'll Build

A simple REST API endpoint for managing tasks with:
- FastAPI backend
- SQLite database
- Full test coverage
- Automatic documentation
- DevStream integration throughout

---

## Part 1: Project Setup (5 minutes)

### Step 1.1: Clone DevStream Template

```bash
# Create project directory
mkdir my-first-devstream-project
cd my-first-devstream-project

# Initialize git repository
git init
git branch -M main
```

**Expected Output**:
```
Initialized empty Git repository in /path/to/my-first-devstream-project/.git/
```

**Verification**: `git status` should show "On branch main"

### Step 1.2: Install DevStream

```bash
# Download DevStream setup script
curl -O https://raw.githubusercontent.com/yourusername/devstream/main/scripts/setup-devstream.sh
chmod +x setup-devstream.sh

# Run setup
./setup-devstream.sh
```

**Expected Output**:
```
✅ Creating Python virtual environment (.devstream)...
✅ Installing DevStream dependencies...
✅ Setting up MCP server...
✅ Configuring hooks...
✅ Creating directory structure...
✅ DevStream setup complete!
```

**Verification**:
```bash
# Check venv exists
ls -la .devstream

# Check Python version
.devstream/bin/python --version

# Check DevStream database
ls -la data/devstream.db
```

### Step 1.3: Configure Environment

```bash
# Create .env.devstream from template
cp .env.example .env.devstream

# Open and verify configuration
cat .env.devstream
```

**Expected Configuration**:
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
```

**Verification**: All `ENABLED` flags should be `true`

### Step 1.4: Start DevStream Services

```bash
# Start MCP server in background
./start-devstream.sh

# Verify MCP server running
curl http://localhost:3000/health
```

**Expected Output**:
```json
{"status": "healthy", "version": "2.0.0", "services": ["memory", "tasks", "context"]}
```

**Checkpoint**: You now have DevStream fully configured and running!

---

## Part 2: Create Your First Task (10 minutes)

### Step 2.1: Define Task Goals

Open Claude Code and start a new session:

```
Create a task for building a FastAPI endpoint to manage tasks (CRUD operations)
```

**Expected Response**: DevStream will invoke `mcp__devstream__devstream_create_task`

### Step 2.2: Review Task Creation

Claude Code will create a task with:

```json
{
  "title": "Build FastAPI CRUD endpoint for task management",
  "description": "Implement REST API with GET, POST, PUT, DELETE operations for tasks",
  "task_type": "coding",
  "priority": 8,
  "phase_name": "Core Backend Development"
}
```

**Verification**:
```bash
# List tasks via MCP
curl http://localhost:3000/tasks | jq
```

**Expected Output**:
```json
{
  "tasks": [
    {
      "id": "DEVSTREAM-001",
      "title": "Build FastAPI CRUD endpoint for task management",
      "status": "pending",
      "priority": 8,
      "created_at": "2025-10-01T10:00:00Z"
    }
  ]
}
```

### Step 2.3: Activate Task

```
Start working on task DEVSTREAM-001
```

Claude Code will:
1. Mark task as "active"
2. Create git branch (if needed)
3. Initialize working directory

**Expected Output**:
```
✅ Task DEVSTREAM-001 activated
✅ Git branch: feature/task-crud-endpoint
✅ Working directory ready
```

**Verification**:
```bash
git branch --show-current  # Should show feature/task-crud-endpoint
```

**Checkpoint**: Your first DevStream task is active and ready for work!

---

## Part 3: Research with Context7 (5 minutes)

### Step 3.1: Request FastAPI Documentation

```
Use Context7 to research FastAPI best practices for CRUD endpoints
```

**What Happens Behind the Scenes**:

1. **PreToolUse Hook Triggers**: Detects "FastAPI" keyword
2. **Context7 Resolve**: `mcp__context7__resolve-library-id` → `/fastapi/fastapi`
3. **Context7 Fetch**: `mcp__context7__get-library-docs` → 5000 tokens of docs
4. **Context Injection**: FastAPI docs injected into Claude context

**Expected Response**:
```
📚 Context7 Documentation Retrieved:

FastAPI CRUD Best Practices:
- Use Pydantic models for request/response validation
- Implement async endpoints for I/O operations
- Use dependency injection for database connections
- Follow RESTful conventions (GET /tasks, POST /tasks, etc.)
- Include OpenAPI documentation automatically

Example endpoint structure:
```python
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List

app = FastAPI()

class TaskCreate(BaseModel):
    title: str
    description: str

class TaskResponse(BaseModel):
    id: int
    title: str
    description: str
    completed: bool

@app.get("/tasks", response_model=List[TaskResponse])
async def list_tasks():
    # Implementation
    pass
```
```

**Verification**: Claude response includes FastAPI code examples and best practices

### Step 3.2: Verify Context7 Storage

```bash
# Check DevStream memory for Context7 docs
.devstream/bin/python -c "
from utils import SemanticMemory
memory = SemanticMemory('data/devstream.db')
results = memory.search('FastAPI CRUD', limit=5)
for r in results:
    print(f'{r[\"content_type\"]}: {r[\"content\"][:100]}...')
"
```

**Expected Output**:
```
context: FastAPI CRUD Best Practices: Use Pydantic models for request/response validation...
documentation: Example endpoint structure from Context7...
```

**Checkpoint**: Context7 has provided research-backed FastAPI patterns!

---

## Part 4: Implementation with Semantic Memory (15 minutes)

### Step 4.1: Create Project Structure

```
Create the basic FastAPI project structure:
- app/main.py (FastAPI app)
- app/models.py (Pydantic models)
- app/database.py (SQLite connection)
- tests/test_tasks.py (pytest tests)
```

**Expected Output**: Claude Code will create files using `Write` tool

**What Happens Behind the Scenes**:

1. **PreToolUse Hook**: Searches DevStream memory for relevant code patterns
2. **Tool Execution**: `Write` tool creates files
3. **PostToolUse Hook**: Stores created files in semantic memory

**Verification**:
```bash
tree app tests
```

**Expected Structure**:
```
app/
├── __init__.py
├── main.py
├── models.py
└── database.py
tests/
├── __init__.py
└── test_tasks.py
```

### Step 4.2: Implement Database Layer

```
Implement the database layer in app/database.py with SQLite connection and CRUD operations
```

**Expected Output**: Claude Code will write:

```python
# app/database.py
import sqlite3
from typing import List, Optional
from contextlib import contextmanager

DATABASE_URL = "data/tasks.db"

@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize database schema."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                completed BOOLEAN DEFAULT FALSE
            )
        """)
        conn.commit()

# CRUD operations implementation...
```

**PostToolUse Hook Action**:
- ✅ Code stored in semantic memory (content_type: "code")
- ✅ Keywords: ["database", "sqlite", "crud", "connection"]
- ✅ Vector embeddings generated via Ollama

**Verification**:
```bash
# Check semantic memory storage
.devstream/bin/python -c "
from utils import SemanticMemory
memory = SemanticMemory('data/devstream.db')
results = memory.search('SQLite database connection', limit=3)
print(f'Found {len(results)} related memories')
"
```

**Expected Output**: `Found 3 related memories` (database.py code stored)

### Step 4.3: Implement API Endpoints

```
Implement FastAPI endpoints in app/main.py following the Context7 best practices
```

**Expected Output**: Claude Code will implement:

```python
# app/main.py
from fastapi import FastAPI, HTTPException, status
from typing import List
from .models import TaskCreate, TaskResponse
from .database import init_db, create_task, get_tasks, get_task, update_task, delete_task

app = FastAPI(
    title="Task Management API",
    version="1.0.0",
    description="Simple CRUD API for task management"
)

@app.on_event("startup")
async def startup():
    init_db()

@app.get("/tasks", response_model=List[TaskResponse])
async def list_tasks():
    """List all tasks."""
    tasks = get_tasks()
    return tasks

@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task_endpoint(task: TaskCreate):
    """Create a new task."""
    task_id = create_task(task.title, task.description)
    return get_task(task_id)

# Additional endpoints (GET /tasks/{id}, PUT /tasks/{id}, DELETE /tasks/{id})...
```

**Automatic Memory Storage**: PostToolUse hook stores:
- ✅ FastAPI endpoint implementations
- ✅ Pydantic model usage patterns
- ✅ Error handling examples

**Checkpoint**: Backend implementation complete with automatic memory tracking!

---

## Part 5: Testing and Validation (10 minutes)

### Step 5.1: Write Tests

```
Create comprehensive pytest tests for all endpoints in tests/test_tasks.py
```

**Expected Output**: Claude Code will implement:

```python
# tests/test_tasks.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    """Initialize test database before each test."""
    init_db()
    yield

def test_create_task():
    """Test POST /tasks creates new task."""
    response = client.post("/tasks", json={
        "title": "Test Task",
        "description": "Test Description"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["completed"] is False

def test_list_tasks():
    """Test GET /tasks returns all tasks."""
    # Create test task
    client.post("/tasks", json={"title": "Task 1", "description": "Desc 1"})

    response = client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1

# Additional tests...
```

### Step 5.2: Run Tests

```bash
# Install test dependencies
.devstream/bin/python -m pip install pytest pytest-cov httpx

# Run tests with coverage
.devstream/bin/python -m pytest tests/ -v --cov=app --cov-report=term-missing
```

**Expected Output**:
```
tests/test_tasks.py::test_create_task PASSED                    [ 20%]
tests/test_tasks.py::test_list_tasks PASSED                     [ 40%]
tests/test_tasks.py::test_get_task PASSED                       [ 60%]
tests/test_tasks.py::test_update_task PASSED                    [ 80%]
tests/test_tasks.py::test_delete_task PASSED                    [100%]

----------- coverage: platform darwin, python 3.11.x -----------
Name                  Stmts   Miss  Cover   Missing
---------------------------------------------------
app/__init__.py           0      0   100%
app/database.py          45      2    96%   23, 67
app/main.py              38      1    97%   89
app/models.py            12      0   100%
---------------------------------------------------
TOTAL                    95      3    97%
```

**Verification**: Coverage ≥ 95% for new code ✅

### Step 5.3: Manual Testing

```bash
# Start FastAPI server
.devstream/bin/python -m uvicorn app.main:app --reload

# In another terminal, test endpoints
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "My First Task", "description": "Created via DevStream"}'

curl http://localhost:8000/tasks
```

**Expected Output**:
```json
[
  {
    "id": 1,
    "title": "My First Task",
    "description": "Created via DevStream",
    "completed": false
  }
]
```

**Checkpoint**: All tests passing, API working correctly!

---

## Part 6: Task Completion (5 minutes)

### Step 6.1: Review Implementation

```
Review the implementation and verify all acceptance criteria are met
```

**Expected Response**: Claude Code will summarize:

```
✅ Acceptance Criteria Review:

1. ✅ FastAPI endpoints implemented (GET, POST, PUT, DELETE)
2. ✅ Pydantic models for validation
3. ✅ SQLite database with CRUD operations
4. ✅ Test coverage: 97% (exceeds 95% requirement)
5. ✅ All tests passing (5/5)
6. ✅ Error handling implemented
7. ✅ OpenAPI documentation auto-generated

Implementation follows Context7 FastAPI best practices ✅
```

### Step 6.2: Complete Task

```
Mark task DEVSTREAM-001 as completed
```

**What Happens Behind the Scenes**:

1. **Task Status Update**: `mcp__devstream__devstream_update_task` → "completed"
2. **Lessons Learned Storage**: Automatic memory storage of implementation insights
3. **Git Operations**: Commit changes to feature branch

**Expected Output**:
```
✅ Task DEVSTREAM-001 marked as completed
✅ Lessons learned stored in semantic memory
✅ Implementation committed to git

Summary:
- Files created: 8
- Tests written: 5
- Test coverage: 97%
- Memory records: 15 (code, documentation, decisions)
```

**Verification**:
```bash
# Check task status
curl http://localhost:3000/tasks/DEVSTREAM-001 | jq '.status'
# Output: "completed"

# Check git commits
git log --oneline
```

**Expected Git Log**:
```
a1b2c3d Complete task DEVSTREAM-001: Task CRUD API
```

### Step 6.3: Review Semantic Memory

```
Search DevStream memory for what we learned during this task
```

**Expected Response**:
```
📝 Relevant Memories from Task DEVSTREAM-001:

1. **Code Pattern** (Relevance: 0.98):
   "FastAPI endpoint structure with async/await and Pydantic validation..."

2. **Decision** (Relevance: 0.95):
   "Chose SQLite for simplicity in tutorial, production would use PostgreSQL..."

3. **Learning** (Relevance: 0.92):
   "Context7 FastAPI docs significantly improved code quality and reduced errors..."

4. **Context** (Relevance: 0.88):
   "CRUD operations follow RESTful conventions: GET /tasks, POST /tasks, etc..."
```

**Verification**: Memory system has automatically captured all implementation details!

**Checkpoint**: Task complete with full audit trail in semantic memory!

---

## What You Learned

Congratulations! You've completed your first DevStream project. Here's what you experienced:

### Core Concepts

✅ **Task Lifecycle Management**
- Creating tasks via MCP (`devstream_create_task`)
- Activating and tracking task status
- Completing tasks with validation

✅ **Semantic Memory System**
- Automatic code storage (PostToolUse hook)
- Context injection (PreToolUse hook)
- Hybrid search (semantic + keyword)

✅ **Context7 Integration**
- Research-driven development
- Automatic library documentation retrieval
- Best practices injection (FastAPI patterns)

✅ **Quality Standards**
- 95%+ test coverage requirement
- Type-safe Python with full type hints
- Comprehensive error handling

### DevStream Workflow

You followed the complete 7-step workflow:

1. ✅ **DISCUSSIONE**: Defined task goals and acceptance criteria
2. ✅ **ANALISI**: Analyzed project structure and requirements
3. ✅ **RICERCA**: Used Context7 for FastAPI best practices
4. ✅ **PIANIFICAZIONE**: Created implementation plan
5. ✅ **APPROVAZIONE**: Reviewed and approved approach
6. ✅ **IMPLEMENTAZIONE**: Built API with automatic memory tracking
7. ✅ **VERIFICA/TEST**: Validated with 97% test coverage

### Key Takeaways

🎯 **DevStream Automation**: Hooks automatically handle memory storage and context injection - you focus on coding

🎯 **Research-Driven**: Context7 provides authoritative documentation, reducing errors and improving code quality

🎯 **Quality First**: 95%+ test coverage and comprehensive validation are built into the workflow

🎯 **Audit Trail**: Semantic memory captures all decisions, code patterns, and learnings automatically

---

## Next Steps

### Immediate Actions

1. **Explore Semantic Memory**:
   ```
   Search DevStream memory for "FastAPI" to see all stored patterns
   ```

2. **Try Multi-Agent Workflow**:
   ```
   Create a TypeScript frontend for this API using @tech-lead orchestration
   ```

3. **Experiment with Context7**:
   ```
   Research pytest best practices via Context7 for advanced testing
   ```

### Advanced Tutorials

- **[Adding DevStream to Existing Project](existing-project.md)** - Integrate DevStream into your codebase
- **[Creating Custom Agents](custom-agent.md)** - Build domain-specific specialists
- **[Multi-Stack Workflow](multi-stack-workflow.md)** - Full-stack development with agent orchestration

### Related Documentation

- **User Guide**: [DevStream Automatic Features](../user-guide/devstream-automatic-features.md)
- **Architecture**: [Hook System Design](../developer-guide/hook-system-design.md)
- **API Reference**: [MCP Server API](../developer-guide/mcp-server-api.md)

---

## Troubleshooting

### Issue: MCP Server Not Starting

**Symptom**: `curl http://localhost:3000/health` fails

**Solution**:
```bash
# Check MCP server logs
cat ~/.claude/logs/devstream/mcp-server.log

# Restart MCP server
./start-devstream.sh restart

# Verify Node.js version
node --version  # Must be v18+
```

### Issue: Memory Not Storing Automatically

**Symptom**: `devstream_search_memory` returns no results after implementation

**Solution**:
```bash
# 1. Verify PostToolUse hook enabled
grep "DEVSTREAM_MEMORY_ENABLED" .env.devstream
# Should be: DEVSTREAM_MEMORY_ENABLED=true

# 2. Check hook execution logs
cat ~/.claude/logs/devstream/hooks/post_tool_use.log

# 3. Verify database exists and has data
.devstream/bin/python -c "
from utils import SemanticMemory
memory = SemanticMemory('data/devstream.db')
import sqlite3
conn = sqlite3.connect('data/devstream.db')
count = conn.execute('SELECT COUNT(*) FROM semantic_memory').fetchone()[0]
print(f'Memory records: {count}')
"
```

### Issue: Context7 Documentation Not Injecting

**Symptom**: Claude responses don't include library documentation

**Solution**:
```bash
# 1. Verify Context7 enabled
grep "DEVSTREAM_CONTEXT7_ENABLED" .env.devstream
# Should be: DEVSTREAM_CONTEXT7_ENABLED=true

# 2. Test Context7 MCP manually
# In Claude Code:
mcp__context7__resolve-library-id:
  libraryName: "fastapi"

# 3. Check PreToolUse hook logs
cat ~/.claude/logs/devstream/hooks/pre_tool_use.log
```

### Issue: Tests Failing with Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'app'`

**Solution**:
```bash
# 1. Verify virtual environment active
which python
# Should show: /path/to/project/.devstream/bin/python

# 2. Install app package in editable mode
.devstream/bin/python -m pip install -e .

# 3. Verify PYTHONPATH includes project root
export PYTHONPATH=/path/to/project:$PYTHONPATH
.devstream/bin/python -m pytest tests/ -v
```

### Issue: High Memory Usage During Task Execution

**Symptom**: System slowdown, JavaScript heap out of memory errors

**Solution**:
```bash
# Increase Node.js heap size in start-devstream.sh
node --max-old-space-size=8192 --expose-gc mcp-devstream-server/dist/index.js

# Monitor memory usage
top -pid $(pgrep -f mcp-devstream-server)
```

---

## Summary

You've successfully:

✅ Set up DevStream for a new project
✅ Created and completed your first task
✅ Experienced automatic semantic memory storage
✅ Used Context7 for research-driven development
✅ Built a production-quality FastAPI CRUD API
✅ Achieved 97% test coverage
✅ Understood the complete DevStream workflow

**Time Spent**: ~45 minutes
**Lines of Code**: ~300
**Test Coverage**: 97%
**Memory Records**: 15+ automatically stored
**Quality**: Production-ready with comprehensive testing

Welcome to DevStream! You're now ready to build complex projects with AI-augmented development workflows.

---

**Tutorial Version**: 1.0.0
**Last Updated**: 2025-10-01
**Tested With**: DevStream v2.0.0, Python 3.11, FastAPI 0.104.1
