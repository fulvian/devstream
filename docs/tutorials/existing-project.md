# Tutorial: Adding DevStream to an Existing Project

## What You'll Learn

In this tutorial, you'll integrate DevStream into an existing codebase and experience:

- Analyzing existing project structure for DevStream compatibility
- Migrating to DevStream without disrupting current workflows
- Scanning codebase for automatic semantic memory population
- Creating first intervention plan for existing code
- Validating DevStream integration with existing tests

**Time**: ~60 minutes
**Difficulty**: Intermediate

## Prerequisites

Before starting, ensure you have:

- ✅ Existing project with git repository
- ✅ Python 3.11+ installed (for Python projects)
- ✅ Node.js 18+ (for TypeScript projects)
- ✅ Claude Code installed
- ✅ Understanding of your project's architecture
- ✅ Backup of your project (just in case)

**Verification**:
```bash
# In your project directory
git status  # Should show clean working tree or known changes
ls -la      # Verify project files present
```

## Example Project

For this tutorial, we'll use a real-world scenario: **A Flask web application with SQLite database**

**Project Structure** (before DevStream):
```
my-flask-app/
├── app/
│   ├── __init__.py
│   ├── routes.py
│   ├── models.py
│   └── utils.py
├── tests/
│   └── test_routes.py
├── requirements.txt
├── config.py
└── run.py
```

---

## Part 1: Pre-Integration Analysis (10 minutes)

### Step 1.1: Assess Project Compatibility

**Checklist for DevStream Integration**:

✅ **Git Repository**: DevStream requires git for branch management
```bash
git status  # Must show valid git repo
```

✅ **Python Version**: Check Python compatibility
```bash
python --version  # 3.11+ required for DevStream
```

✅ **Project Structure**: DevStream works best with modular codebases
```bash
tree -L 2  # Review directory structure
```

✅ **Existing Virtual Environment**: Identify current venv (will be replaced)
```bash
which python  # Note current venv path
pip list      # Document installed packages
```

✅ **Test Suite**: Existing tests help validate integration
```bash
pytest tests/ --collect-only  # Count existing tests
```

**Compatibility Assessment**:

| Factor | Requirement | Your Project | Status |
|--------|-------------|--------------|--------|
| Git Repository | Yes | ✅ Yes | ✅ Compatible |
| Python Version | 3.11+ | ✅ 3.11.5 | ✅ Compatible |
| Modular Structure | Recommended | ✅ app/ directory | ✅ Compatible |
| Virtual Environment | Any | ✅ venv/ | ⚠️ Will migrate |
| Test Suite | Optional | ✅ 15 tests | ✅ Bonus |

### Step 1.2: Document Current State

```bash
# Create snapshot of current state
git add -A
git commit -m "Snapshot before DevStream integration"

# Export current dependencies
pip freeze > requirements-pre-devstream.txt

# Run existing tests and save results
pytest tests/ -v > test-results-pre-devstream.txt
```

**Expected Output**:
```
[main abc1234] Snapshot before DevStream integration
 3 files changed, 245 insertions(+)
```

**Verification**: Clean git status, documented dependencies, baseline test results

### Step 1.3: Identify Integration Points

**Questions to Answer**:

1. **Where should DevStream hooks live?**
   - Recommended: `.claude/hooks/devstream/`

2. **What should be stored in semantic memory?**
   - Existing code patterns (e.g., Flask route decorators)
   - Database models and schemas
   - Common utilities and helpers
   - Architectural decisions

3. **Which parts need Context7 integration?**
   - Framework-specific code (Flask, SQLAlchemy)
   - Testing patterns (pytest fixtures)
   - Deployment configurations

**Document Answers**:
```bash
# Create integration plan document
cat > DEVSTREAM_INTEGRATION_PLAN.md << 'EOF'
# DevStream Integration Plan

## Current State
- Framework: Flask 2.3.0
- Database: SQLite with SQLAlchemy
- Tests: pytest (15 tests, 87% coverage)
- Python: 3.11.5

## Integration Goals
1. Add semantic memory for existing code patterns
2. Enable Context7 for Flask/SQLAlchemy best practices
3. Maintain 100% test compatibility
4. Preserve existing git history

## Risk Mitigation
- Create snapshot commit before integration
- Test each integration step incrementally
- Keep requirements-pre-devstream.txt as rollback reference

## Success Criteria
- All 15 existing tests pass
- DevStream MCP server responds to health checks
- Semantic memory contains ≥20 code patterns from existing codebase
EOF
```

**Checkpoint**: Project assessed, state documented, integration plan defined!

---

## Part 2: DevStream Installation (15 minutes)

### Step 2.1: Install DevStream Core

```bash
# Download DevStream installation script
curl -O https://raw.githubusercontent.com/yourusername/devstream/main/scripts/install-devstream.sh
chmod +x install-devstream.sh

# Run installation (preserves existing code)
./install-devstream.sh --existing-project
```

**Installation Process**:

1. ✅ Detect existing project structure
2. ✅ Create `.devstream/` virtual environment
3. ✅ Merge `requirements.txt` + DevStream dependencies
4. ✅ Install all dependencies in `.devstream/`
5. ✅ Set up `.claude/` directory structure
6. ✅ Configure `.env.devstream`
7. ✅ Initialize `data/devstream.db`

**Expected Output**:
```
🔍 Existing project detected
✅ Found requirements.txt (23 packages)
✅ Creating DevStream virtual environment (.devstream)
✅ Merging dependencies:
   - Existing: Flask, SQLAlchemy, pytest, ...
   - DevStream: cchooks, aiohttp, structlog, ...
✅ Installing merged dependencies (35 total)
✅ Setting up DevStream directories
✅ Configuring environment (.env.devstream)
✅ Initializing semantic memory database
✅ DevStream installation complete!

📝 Next Steps:
   1. Review .env.devstream configuration
   2. Run existing tests: .devstream/bin/python -m pytest tests/
   3. Start MCP server: ./start-devstream.sh
```

**Verification**:
```bash
# Check new venv
ls -la .devstream

# Verify dependencies merged
.devstream/bin/python -m pip list | grep -E "(Flask|cchooks|aiohttp)"
# Should show both existing (Flask) and DevStream (cchooks) packages

# Check directory structure
tree -L 3 .claude data
```

**Expected Structure**:
```
.claude/
├── hooks/
│   └── devstream/
│       ├── memory/
│       └── context/
├── agents/
│   ├── orchestrator/
│   ├── domain/
│   └── qa/
└── state/
    └── current_task.json

data/
├── devstream.db
└── (your existing data files)
```

### Step 2.2: Configure Environment for Existing Project

```bash
# Open .env.devstream for customization
cat .env.devstream
```

**Key Configuration for Existing Projects**:

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

# Codebase Scanning (IMPORTANT for existing projects)
DEVSTREAM_CODEBASE_SCAN_ENABLED=true
DEVSTREAM_CODEBASE_SCAN_DIRECTORIES=app,tests  # Customize to your structure
DEVSTREAM_CODEBASE_SCAN_EXCLUDE=venv,.git,__pycache__

# Database (MANDATORY)
DEVSTREAM_DB_PATH=data/devstream.db

# Existing Project Settings (NEW)
DEVSTREAM_EXISTING_PROJECT=true
DEVSTREAM_PRESERVE_VENV=false  # Set to true to keep old venv
DEVSTREAM_MERGE_REQUIREMENTS=true
```

**Important for Existing Projects**:

- `DEVSTREAM_CODEBASE_SCAN_DIRECTORIES`: List YOUR app directories
- `DEVSTREAM_CODEBASE_SCAN_EXCLUDE`: Add your ignore patterns
- `DEVSTREAM_EXISTING_PROJECT=true`: Enables compatibility mode

### Step 2.3: Verify Existing Tests Still Pass

```bash
# Run tests with NEW virtual environment
.devstream/bin/python -m pytest tests/ -v

# Compare with baseline
diff test-results-pre-devstream.txt <(.devstream/bin/python -m pytest tests/ -v 2>&1)
```

**Expected Output**:
```
tests/test_routes.py::test_home_page PASSED                     [  6%]
tests/test_routes.py::test_about_page PASSED                    [ 13%]
tests/test_routes.py::test_user_creation PASSED                 [ 20%]
...
tests/test_models.py::test_user_model PASSED                    [100%]

========================== 15 passed in 2.3s ==========================
```

**Verification**: All existing tests pass with DevStream environment ✅

**If Tests Fail**:
```bash
# Check missing dependencies
.devstream/bin/python -m pip list > current-packages.txt
diff requirements-pre-devstream.txt current-packages.txt

# Install missing packages
.devstream/bin/python -m pip install <missing-package>

# Re-run tests
.devstream/bin/python -m pytest tests/ -v
```

**Checkpoint**: DevStream installed, tests passing, environment configured!

---

## Part 3: Codebase Scanning and Memory Population (15 minutes)

### Step 3.1: Start MCP Server

```bash
# Start DevStream MCP server
./start-devstream.sh

# Verify health
curl http://localhost:3000/health
```

**Expected Output**:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "services": ["memory", "tasks", "context"],
  "existing_project": true
}
```

### Step 3.2: Scan Existing Codebase

**In Claude Code**:

```
Scan the existing codebase and populate semantic memory with code patterns
```

**What Happens Behind the Scenes**:

1. **Directory Traversal**: Scans `app/` and `tests/` (configured in `.env.devstream`)
2. **Pattern Extraction**:
   - Flask route decorators (`@app.route(...)`)
   - SQLAlchemy models (`db.Model` subclasses)
   - Pytest fixtures (`@pytest.fixture`)
   - Utility functions
3. **Memory Storage**: Each pattern stored via `devstream_store_memory`
4. **Embedding Generation**: Ollama generates vector embeddings
5. **Index Building**: sqlite-vec indexes created for fast retrieval

**Expected Response**:
```
📁 Scanning Existing Codebase...

✅ Scanned app/routes.py:
   - Found 8 Flask route patterns
   - Found 3 error handling patterns
   - Found 2 authentication decorators

✅ Scanned app/models.py:
   - Found 4 SQLAlchemy models
   - Found 6 relationship definitions
   - Found 2 database constraints

✅ Scanned app/utils.py:
   - Found 5 utility functions
   - Found 1 decorator pattern
   - Found 3 validation functions

✅ Scanned tests/test_routes.py:
   - Found 7 pytest fixtures
   - Found 15 test patterns
   - Found 3 mock configurations

📊 Codebase Scan Summary:
   - Files scanned: 8
   - Patterns extracted: 47
   - Memory records created: 47
   - Embeddings generated: 47
   - Index build time: 3.2s

✅ Semantic memory populated with existing code patterns!
```

### Step 3.3: Verify Memory Population

```bash
# Check memory database
.devstream/bin/python -c "
from utils import SemanticMemory
memory = SemanticMemory('data/devstream.db')

# Count total records
import sqlite3
conn = sqlite3.connect('data/devstream.db')
count = conn.execute('SELECT COUNT(*) FROM semantic_memory').fetchone()[0]
print(f'Total memory records: {count}')

# Sample Flask patterns
results = memory.search('Flask route decorator', limit=3)
print(f'\nFlask Route Patterns:')
for r in results:
    print(f'  - {r[\"content\"][:80]}...')
"
```

**Expected Output**:
```
Total memory records: 47

Flask Route Patterns:
  - @app.route('/users', methods=['GET', 'POST']) def users(): """List or cre...
  - @app.route('/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE']) def...
  - @login_required @app.route('/dashboard') def dashboard(): """User dashbo...
```

**Verification**: Semantic memory contains your existing code patterns!

### Step 3.4: Test Context Injection with Existing Patterns

**In Claude Code**:

```
Search DevStream memory for "SQLAlchemy model definition" to verify context injection works
```

**Expected Response**:
```
📝 Relevant Context from DevStream Memory:

1. **Code Pattern** (Relevance: 0.96):
```python
class User(db.Model):
    """User model with authentication."""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
```

2. **Code Pattern** (Relevance: 0.92):
```python
class Post(db.Model):
    """Blog post model with foreign key to User."""
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', backref='posts')
```

✅ PreToolUse hook successfully retrieved existing patterns from memory!
```

**Checkpoint**: Codebase scanned, semantic memory populated, context injection working!

---

## Part 4: Create First Intervention Plan (10 minutes)

### Step 4.1: Analyze Codebase for Improvements

**In Claude Code**:

```
Analyze the existing Flask application and suggest an intervention plan for improvements
```

**Expected Response**:
```
📊 Codebase Analysis Complete

**Current State**:
- Framework: Flask 2.3.0
- Test Coverage: 87% (target: 95%+)
- Code Quality: Good structure, some missing type hints
- Performance: No async operations (potential bottleneck)
- Security: Basic authentication, needs rate limiting

**Recommended Intervention Plan**:

Phase 1: Quality Improvements (Priority: High)
  └─ Add type hints to all functions
  └─ Increase test coverage to 95%+
  └─ Add docstrings to models and routes

Phase 2: Security Hardening (Priority: High)
  └─ Implement rate limiting on API endpoints
  └─ Add CSRF protection for forms
  └─ Secure session management

Phase 3: Performance Optimization (Priority: Medium)
  └─ Add database query optimization (lazy loading)
  └─ Implement caching for frequently accessed data
  └─ Consider async operations for I/O

Phase 4: Feature Enhancements (Priority: Low)
  └─ Add API documentation (OpenAPI/Swagger)
  └─ Implement pagination for list endpoints
  └─ Add search functionality

Would you like me to create tasks for these phases?
```

### Step 4.2: Create Intervention Plan via MCP

```
Create an intervention plan with Phase 1 and Phase 2 tasks
```

**Expected MCP Calls**:
```
mcp__devstream__devstream_create_task:
  title: "Add type hints to all Flask routes and models"
  description: "Improve code quality by adding full type hints for maintainability"
  task_type: "coding"
  priority: 9
  phase_name: "Quality Improvements"

mcp__devstream__devstream_create_task:
  title: "Increase test coverage to 95%+"
  description: "Add tests for edge cases and error handling"
  task_type: "testing"
  priority: 9
  phase_name: "Quality Improvements"

mcp__devstream__devstream_create_task:
  title: "Implement rate limiting on API endpoints"
  description: "Add Flask-Limiter for DDoS protection"
  task_type: "coding"
  priority: 10
  phase_name: "Security Hardening"

mcp__devstream__devstream_create_task:
  title: "Add CSRF protection for forms"
  description: "Implement Flask-WTF CSRF tokens"
  task_type: "coding"
  priority: 10
  phase_name: "Security Hardening"
```

**Expected Output**:
```
✅ Created 4 tasks in intervention plan:

DEVSTREAM-001: Add type hints to all Flask routes and models (Priority: 9)
DEVSTREAM-002: Increase test coverage to 95%+ (Priority: 9)
DEVSTREAM-003: Implement rate limiting on API endpoints (Priority: 10)
DEVSTREAM-004: Add CSRF protection for forms (Priority: 10)

📋 View plan:
   curl http://localhost:3000/plans | jq
```

### Step 4.3: Verify Intervention Plan

```bash
# List all tasks
curl http://localhost:3000/tasks | jq '.tasks[] | {id, title, priority}'
```

**Expected Output**:
```json
[
  {
    "id": "DEVSTREAM-001",
    "title": "Add type hints to all Flask routes and models",
    "priority": 9
  },
  {
    "id": "DEVSTREAM-002",
    "title": "Increase test coverage to 95%+",
    "priority": 9
  },
  {
    "id": "DEVSTREAM-003",
    "title": "Implement rate limiting on API endpoints",
    "priority": 10
  },
  {
    "id": "DEVSTREAM-004",
    "title": "Add CSRF protection for forms",
    "priority": 10
  }
]
```

**Checkpoint**: Intervention plan created with prioritized tasks!

---

## Part 5: Execute First Intervention Task (10 minutes)

### Step 5.1: Start Highest Priority Task

**In Claude Code**:

```
Start working on task DEVSTREAM-003 (rate limiting) using Context7 for Flask-Limiter research
```

**Expected Response**:
```
✅ Task DEVSTREAM-003 activated

📚 Context7 Research: Flask-Limiter

Best Practices:
- Use Flask-Limiter extension for rate limiting
- Configure limits based on endpoint sensitivity
- Store limits in configuration (not hardcoded)
- Implement proper error responses (429 Too Many Requests)

Example Implementation:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/api/users', methods=['POST'])
@limiter.limit("10 per minute")
def create_user():
    # Implementation
    pass
```

Shall I proceed with implementation?
```

### Step 5.2: Implement Rate Limiting

```
Yes, proceed with implementing rate limiting following Context7 best practices
```

**Expected Implementation**:

```python
# app/__init__.py (updated)
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
app.config.from_object('config')

# Initialize rate limiter
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"  # Use Redis in production
)

from app import routes


# app/routes.py (updated)
from app import app, limiter
from flask import jsonify

@app.route('/api/users', methods=['POST'])
@limiter.limit("10 per minute")  # Stricter limit for write operations
def create_user():
    """Create new user (rate limited)."""
    # Existing implementation
    pass

@app.route('/api/users', methods=['GET'])
@limiter.limit("100 per minute")  # More permissive for reads
def list_users():
    """List users (rate limited)."""
    # Existing implementation
    pass

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded."""
    return jsonify(error="Rate limit exceeded. Try again later."), 429
```

**PostToolUse Hook Action**:
- ✅ Rate limiting implementation stored in semantic memory
- ✅ Flask-Limiter patterns extracted
- ✅ Keywords: ["rate-limiting", "flask-limiter", "ddos-protection"]

### Step 5.3: Test Rate Limiting

```
Create tests for rate limiting functionality
```

**Expected Test Implementation**:

```python
# tests/test_rate_limiting.py (new file)
import pytest
from app import app, limiter

@pytest.fixture
def client():
    """Test client with rate limiting enabled."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_rate_limit_enforced(client):
    """Test that rate limit is enforced after threshold."""
    # Make 11 requests (limit is 10 per minute)
    for i in range(11):
        response = client.post('/api/users', json={'username': f'user{i}'})
        if i < 10:
            assert response.status_code in [200, 201]
        else:
            assert response.status_code == 429  # Rate limit exceeded

def test_rate_limit_error_message(client):
    """Test rate limit error returns proper message."""
    # Exceed rate limit
    for _ in range(11):
        response = client.post('/api/users', json={'username': 'test'})

    # Check error message
    data = response.get_json()
    assert 'error' in data
    assert 'rate limit' in data['error'].lower()

def test_rate_limit_different_endpoints(client):
    """Test rate limits are independent per endpoint."""
    # Exhaust POST limit
    for _ in range(10):
        client.post('/api/users', json={'username': 'test'})

    # GET should still work (different limit)
    response = client.get('/api/users')
    assert response.status_code == 200
```

**Run Tests**:
```bash
# Install Flask-Limiter
.devstream/bin/python -m pip install Flask-Limiter

# Run new tests
.devstream/bin/python -m pytest tests/test_rate_limiting.py -v

# Run all tests to ensure no regression
.devstream/bin/python -m pytest tests/ -v --cov=app
```

**Expected Output**:
```
tests/test_rate_limiting.py::test_rate_limit_enforced PASSED       [ 33%]
tests/test_rate_limiting.py::test_rate_limit_error_message PASSED  [ 66%]
tests/test_rate_limiting.py::test_rate_limit_different_endpoints PASSED [100%]

tests/test_routes.py::test_home_page PASSED                        [100%]
(... all existing tests also pass)

---------- coverage: platform darwin, python 3.11.x ----------
Name                    Stmts   Miss  Cover
-------------------------------------------
app/__init__.py            15      0   100%
app/routes.py              42      1    98%
app/models.py              25      0   100%
tests/test_rate_limiting.py 28      0   100%
-------------------------------------------
TOTAL                     110      1    99%
```

**Verification**: New feature implemented, tests passing, coverage increased to 99% ✅

### Step 5.4: Complete Task

```
Mark task DEVSTREAM-003 as completed
```

**Expected Output**:
```
✅ Task DEVSTREAM-003 completed

Summary:
- Rate limiting implemented with Flask-Limiter
- 3 new tests added (100% coverage for rate limiting)
- Overall coverage: 99% (up from 87%)
- Security hardening: DDoS protection enabled

Lessons Learned (stored in memory):
- Flask-Limiter integrates seamlessly with existing Flask app
- Different rate limits per endpoint allow fine-grained control
- Memory storage works for development, Redis recommended for production

✅ Committed to git: feature/rate-limiting
```

**Checkpoint**: First intervention task complete with improved security!

---

## Part 6: Validation and Verification (5 minutes)

### Step 6.1: Verify DevStream Integration Health

```bash
# 1. Check MCP server health
curl http://localhost:3000/health

# 2. Verify semantic memory has new patterns
.devstream/bin/python -c "
from utils import SemanticMemory
memory = SemanticMemory('data/devstream.db')
import sqlite3
conn = sqlite3.connect('data/devstream.db')
count = conn.execute('SELECT COUNT(*) FROM semantic_memory').fetchone()[0]
print(f'Total memory records: {count}')

# Search for rate limiting patterns
results = memory.search('rate limiting', limit=3)
print(f'\nRate Limiting Patterns: {len(results)} found')
"

# 3. Run full test suite
.devstream/bin/python -m pytest tests/ -v --cov=app

# 4. Check git status
git status
git log --oneline -5
```

**Expected Outputs**:

**MCP Health**:
```json
{"status": "healthy", "services": ["memory", "tasks", "context"]}
```

**Memory Records**:
```
Total memory records: 52  # 47 from scan + 5 from rate limiting implementation
Rate Limiting Patterns: 3 found
```

**Test Suite**:
```
========================== 18 passed in 3.1s ==========================
---------- coverage: 99% ----------
```

**Git Status**:
```
On branch feature/rate-limiting
Your branch is ahead of 'main' by 1 commit.

nothing to commit, working tree clean
```

### Step 6.2: Compare Before vs After

**Create Comparison Report**:

```bash
cat > DEVSTREAM_INTEGRATION_REPORT.md << 'EOF'
# DevStream Integration Report

## Before DevStream
- Test Coverage: 87%
- Memory Records: 0
- Active Tasks: 0
- Context Injection: Manual research
- Security: Basic authentication only

## After DevStream
- Test Coverage: 99% (+12%)
- Memory Records: 52 (47 scanned + 5 new)
- Active Tasks: 3 remaining
- Context Injection: Automatic (Context7 + DevStream memory)
- Security: Authentication + Rate Limiting

## Integration Success Metrics
✅ All 15 existing tests still pass
✅ 3 new tests added for rate limiting
✅ Semantic memory populated with existing code patterns
✅ First intervention task completed successfully
✅ No disruption to existing workflows

## Next Steps
1. Complete remaining security tasks (DEVSTREAM-004: CSRF protection)
2. Move to Phase 2: Quality Improvements
3. Explore multi-agent workflows for complex refactoring

## Lessons Learned
- Codebase scanning accelerates DevStream adoption (47 patterns in minutes)
- Context7 integration provides immediate value (Flask-Limiter best practices)
- Existing tests provide safety net for integration validation
EOF

cat DEVSTREAM_INTEGRATION_REPORT.md
```

**Checkpoint**: DevStream successfully integrated, existing project enhanced!

---

## What You Learned

Congratulations! You've successfully integrated DevStream into an existing project. Here's what you accomplished:

### Integration Skills

✅ **Assessment and Planning**
- Analyzed existing project for DevStream compatibility
- Created integration plan with risk mitigation
- Documented current state for rollback safety

✅ **Non-Disruptive Installation**
- Installed DevStream without breaking existing workflows
- Merged dependencies (existing + DevStream)
- Verified all existing tests still pass

✅ **Codebase Scanning**
- Automatically populated semantic memory with 47 existing patterns
- Extracted Flask routes, SQLAlchemy models, pytest fixtures
- Built searchable knowledge base from existing code

✅ **Context7 Integration**
- Used Context7 for Flask-Limiter research
- Applied research-backed patterns to existing codebase
- Enhanced security with DDoS protection

✅ **Task-Driven Improvements**
- Created intervention plan with prioritized tasks
- Completed first security hardening task
- Increased test coverage from 87% to 99%

### Key Differences: New vs Existing Projects

| Aspect | New Project | Existing Project |
|--------|-------------|------------------|
| **Memory Population** | Gradual (as you code) | Immediate (codebase scan) |
| **Context Injection** | Framework docs | Framework + your patterns |
| **Integration Risk** | Low (clean slate) | Medium (existing code) |
| **Validation** | Write new tests | Existing tests must pass |
| **Learning Curve** | Steep (new patterns) | Gentle (familiar code) |

### DevStream Benefits for Existing Projects

🎯 **Instant Knowledge Base**: Codebase scan creates searchable memory of your patterns

🎯 **Context-Aware Suggestions**: DevStream learns YOUR coding style from existing code

🎯 **Safe Refactoring**: Semantic memory preserves architectural decisions during changes

🎯 **Incremental Adoption**: Intervention plans allow gradual improvement without rewrites

---

## Next Steps

### Immediate Actions

1. **Complete Security Phase**:
   ```
   Start task DEVSTREAM-004 to add CSRF protection
   ```

2. **Explore Memory**:
   ```
   Search DevStream memory for "SQLAlchemy relationship" to see what patterns were captured
   ```

3. **Add Custom Patterns**:
   ```
   Store architectural decisions in memory for future reference
   ```

### Advanced Integration

- **Multi-Agent Refactoring**: Use @tech-lead to orchestrate large-scale refactoring
- **Custom Agent**: Create domain-specific agent for your framework (Flask specialist)
- **Continuous Memory**: Set up pre-commit hooks for automatic memory updates

### Related Tutorials

- **[Your First DevStream Project](first-project.md)** - Start from scratch experience
- **[Creating Custom Agents](custom-agent.md)** - Build Flask-specific agent
- **[Multi-Stack Workflow](multi-stack-workflow.md)** - Add frontend to Flask backend

### Related Documentation

- **User Guide**: [Codebase Scanning](../user-guide/codebase-scanning.md)
- **Developer Guide**: [Memory System Architecture](../developer-guide/memory-system-architecture.md)
- **How-To**: [Migrating from Flask to FastAPI](../guides/migration-flask-to-fastapi.md)

---

## Troubleshooting

### Issue: Codebase Scan Missing Patterns

**Symptom**: Expected patterns not in semantic memory after scan

**Solution**:
```bash
# 1. Check scan configuration
grep "DEVSTREAM_CODEBASE_SCAN" .env.devstream

# 2. Verify directories are correct
ls -la app/  # Should show your application files

# 3. Manual pattern extraction
# In Claude Code:
Analyze app/routes.py and store Flask route patterns in semantic memory

# 4. Check memory for stored patterns
.devstream/bin/python -c "
from utils import SemanticMemory
memory = SemanticMemory('data/devstream.db')
results = memory.search('Flask route', limit=10)
print(f'Found {len(results)} Flask route patterns')
"
```

### Issue: Dependency Conflicts After Installation

**Symptom**: `pip install` errors or version conflicts

**Solution**:
```bash
# 1. Check conflicting packages
.devstream/bin/python -m pip check

# 2. View all installed versions
.devstream/bin/python -m pip list > installed-packages.txt
cat installed-packages.txt

# 3. Resolve conflicts manually
.devstream/bin/python -m pip install --upgrade <conflicting-package>

# 4. If needed, create fresh venv
rm -rf .devstream
./install-devstream.sh --existing-project --force
```

### Issue: Existing Tests Fail After Integration

**Symptom**: Tests that passed before DevStream now fail

**Solution**:
```bash
# 1. Compare dependency versions
diff requirements-pre-devstream.txt <(.devstream/bin/python -m pip freeze)

# 2. Run tests with verbose output
.devstream/bin/python -m pytest tests/ -vv --tb=long

# 3. Check for environment variable issues
# DevStream may set environment variables; ensure tests reset state

# 4. Rollback if needed
git checkout HEAD~1  # Revert to pre-DevStream commit
pip install -r requirements-pre-devstream.txt
pytest tests/ -v  # Verify tests pass

# Then retry integration with issue fix
```

### Issue: Hook Execution Errors During First Task

**Symptom**: PreToolUse or PostToolUse hooks fail

**Solution**:
```bash
# 1. Check hook logs
cat ~/.claude/logs/devstream/hooks/pre_tool_use.log
cat ~/.claude/logs/devstream/hooks/post_tool_use.log

# 2. Verify hook dependencies installed in .devstream venv
.devstream/bin/python -c "import cchooks, aiohttp, structlog; print('OK')"

# 3. Test hook execution manually
.devstream/bin/python .claude/hooks/devstream/memory/pre_tool_use.py

# 4. Disable hooks temporarily to isolate issue
# In .env.devstream:
DEVSTREAM_MEMORY_ENABLED=false
# Complete task, then re-enable and debug
```

### Issue: Codebase Scan Takes Too Long

**Symptom**: Scan exceeds 5 minutes for large codebase

**Solution**:
```bash
# 1. Exclude unnecessary directories
# In .env.devstream:
DEVSTREAM_CODEBASE_SCAN_EXCLUDE=venv,.git,__pycache__,node_modules,dist,build

# 2. Scan incrementally by directory
# In Claude Code:
Scan only app/routes.py and store patterns
# Then:
Scan only app/models.py and store patterns

# 3. Increase scan timeout
# In .env.devstream:
DEVSTREAM_CODEBASE_SCAN_TIMEOUT=300  # 5 minutes

# 4. Use file filtering
# In .env.devstream:
DEVSTREAM_CODEBASE_SCAN_FILE_PATTERNS=*.py,*.js  # Only scan specific extensions
```

### Issue: Memory Search Returns Irrelevant Results

**Symptom**: DevStream memory search doesn't find expected patterns

**Solution**:
```bash
# 1. Check relevance threshold
# In .env.devstream:
DEVSTREAM_CONTEXT_RELEVANCE_THRESHOLD=0.3  # Lower threshold (was 0.5)

# 2. Use more specific query
# Instead of: "database model"
# Try: "SQLAlchemy User model with foreign key"

# 3. Check keyword extraction
.devstream/bin/python -c "
from utils import SemanticMemory
memory = SemanticMemory('data/devstream.db')
import sqlite3
conn = sqlite3.connect('data/devstream.db')
cursor = conn.execute('SELECT keywords FROM semantic_memory LIMIT 10')
for row in cursor:
    print(row[0])
"

# 4. Manually add keywords to important patterns
# In Claude Code:
Store this pattern in memory with keywords: ["flask", "authentication", "decorator"]
```

---

## Summary

You've successfully:

✅ Assessed existing project for DevStream compatibility
✅ Installed DevStream without disrupting existing workflows
✅ Scanned codebase and populated semantic memory (47 patterns)
✅ Created intervention plan with prioritized tasks
✅ Completed first task using Context7 research
✅ Improved test coverage from 87% to 99%
✅ Enhanced security with rate limiting

**Time Spent**: ~60 minutes
**Memory Records**: 52 (47 scanned + 5 new)
**Test Coverage**: 99% (+12% improvement)
**Tasks Created**: 4 in intervention plan
**Remaining Work**: 3 tasks (security + quality improvements)

Your existing project is now DevStream-powered with:
- Automatic semantic memory for code patterns
- Context7 integration for research-driven development
- Task-based workflow for systematic improvements
- Quality validation throughout

Welcome to DevStream-enhanced development!

---

**Tutorial Version**: 1.0.0
**Last Updated**: 2025-10-01
**Tested With**: DevStream v2.0.0, Flask 2.3.0, Python 3.11, SQLAlchemy 2.0
