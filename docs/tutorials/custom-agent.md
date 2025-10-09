# Tutorial: Creating a Custom DevStream Agent

## What You'll Learn

In this tutorial, you'll create a custom DevStream agent from scratch:

- Understanding agent architecture and hierarchy
- Designing agent capabilities and tool access
- Writing agent configuration files
- Testing agent behavior and delegation
- Integrating custom agent into DevStream workflows
- Best practices for agent specialization

**Time**: ~50 minutes
**Difficulty**: Advanced

## Prerequisites

Before starting, ensure you have:

- ✅ DevStream v2.0+ installed and configured
- ✅ Completed "Your First DevStream Project" tutorial
- ✅ Understanding of DevStream agent system (Phase 1-3)
- ✅ Basic understanding of Claude Code agent mechanics
- ✅ Familiarity with your target domain (for specialization)

**Verification**:
```bash
# Check DevStream agents directory
ls -la .claude/agents/

# Verify agent hierarchy
tree -L 2 .claude/agents/
```

## What We'll Build

**Custom Agent**: **@flask-specialist**

A domain-specific agent for Flask development with Flask best practices, SQLAlchemy integration, Flask extensions, security focus, and performance optimization.

---

## Part 1: Agent Design (10 minutes)

### Step 1.1: Define Agent Identity

**Agent Profile**:
- **Name**: @flask-specialist
- **Level**: Domain Specialist (Level 2)
- **Purpose**: Flask ecosystem expertise
- **Tool Access**: Full (inherits all tools)

Create design document:
```bash
cat > .claude/agents/domain/flask-specialist-design.md << 'EOF'
# Flask Specialist Agent Design

## Agent Identity
- Name: @flask-specialist
- Level: Domain Specialist (Level 2)
- Inheritance: Base domain specialist template

## Purpose
Expert Flask development guidance with focus on production-ready applications, security-first development, performance optimization, and Flask ecosystem integration.

## Core Capabilities
1. Flask Application Architecture (factory pattern, blueprints)
2. SQLAlchemy Integration (models, queries, migrations)
3. Flask Extensions (Flask-Login, Flask-WTF, Flask-Limiter)
4. Security (CSRF, XSS, SQL injection prevention)
5. Testing (pytest, Flask test client)
6. Performance (caching, query optimization)

## Tool Access
Full tool access (inherits all tools from domain specialist base)

## Delegation Patterns
- Orchestrated by @tech-lead for multi-stack projects
- Delegates to @database-specialist for complex queries
- Works with @testing-specialist for test strategies
EOF
```

**Checkpoint**: Agent design documented!

---

## Part 2: Create Agent Configuration (15 minutes)

### Step 2.1: Write Agent File

Create the complete agent configuration:

```bash
cat > .claude/agents/domain/flask-specialist.md << 'EOF'
# @flask-specialist - Flask Domain Specialist

You are a Flask development expert with deep knowledge of the Flask ecosystem, security best practices, and production-ready application development.

## Core Expertise

### Flask Application Architecture

**Application Factory Pattern**:
```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app(config_class='config.Config'):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)
    
    from app.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    return app
```

### SQLAlchemy Integration

**Model Definition**:
```python
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
```

### Security Best Practices

**CSRF Protection (Flask-WTF)**:
```python
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
```

**SQL Injection Prevention**:
```python
# Good: Use SQLAlchemy ORM (automatic parameterization)
user = User.query.filter_by(username=user_input).first()

# Good: Parameterized raw SQL if needed
from sqlalchemy import text
query = text("SELECT * FROM users WHERE username = :username")
result = db.session.execute(query, {'username': user_input})
```

### Testing

**pytest Fixtures**:
```python
@pytest.fixture
def app():
    app = create_app('config.TestConfig')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()
```

## Best Practices (MANDATORY)

### Security
- ✅ ALWAYS use CSRF protection (Flask-WTF)
- ✅ NEVER store passwords in plain text
- ✅ Use HTTPS in production (secure cookies)
- ✅ Validate ALL user input

### Database
- ✅ Use migrations (Flask-Migrate)
- ✅ Index frequently queried columns
- ✅ Prevent N+1 queries with joinedload

### Testing
- ✅ Test coverage ≥95% for new code
- ✅ Use pytest fixtures for setup/teardown

## When to Use

Use @flask-specialist when building Flask applications, integrating Flask extensions, implementing authentication, optimizing performance, or security hardening.

Delegate to @database-specialist for complex database design, @testing-specialist for comprehensive test strategies.

---

This agent has full tool access (inherits all tools from domain specialist base).
EOF
```

**Verification**:
```bash
cat .claude/agents/domain/flask-specialist.md | head -50
```

**Checkpoint**: Agent configuration created!

---

## Part 3: Test Agent Behavior (10 minutes)

### Step 3.1: Test Direct Invocation

**In Claude Code**:
```
@flask-specialist Create a Flask login route with CSRF protection using Flask-WTF
```

**Expected Response**:
```python
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email
from flask_login import login_user
from app.models import User

auth_bp = Blueprint('auth', __name__)

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('Invalid email or password', 'danger')
    return render_template('auth/login.html', form=form)
```

**Validation**:
- ✅ Uses Flask-WTF for CSRF protection
- ✅ Proper validators (DataRequired, Email)
- ✅ Password verification with check_password
- ✅ Flash messages for feedback
- ✅ Security-first approach

### Step 3.2: Test Agent Delegation

**In Claude Code**:
```
@tech-lead Create Flask authentication system (login, registration, password reset)
```

**Expected Delegation**:
```
✅ Task decomposition by @tech-lead:

1. Task(@flask-specialist): Implement login route with CSRF protection
2. Task(@flask-specialist): Implement registration route with validation
3. Task(@flask-specialist): Implement password reset flow
4. Task(@testing-specialist): Create comprehensive auth tests
5. Task(@code-reviewer): Security validation of auth system
```

**Checkpoint**: Agent responds correctly to invocations and delegation!

---

## Part 4: Integration Testing (10 minutes)

### Step 4.1: Test Context7 Integration

```
@flask-specialist Research Flask-Limiter best practices via Context7 and implement rate limiting
```

**Expected Behavior**:
1. PreToolUse hook detects "Flask-Limiter"
2. Context7 retrieves Flask-Limiter documentation
3. Agent implements rate limiting with best practices

**Expected Implementation**:
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

### Step 4.2: Test Memory Integration

```bash
# Verify agent implementation stored in semantic memory
.devstream/bin/python -c "
from utils import SemanticMemory
memory = SemanticMemory('data/devstream.db')
results = memory.search('Flask-Limiter rate limiting', limit=3)
for r in results:
    print(f'Found: {r[\"content\"][:80]}...')
"
```

**Expected Output**:
```
Found: from flask_limiter import Limiter\nfrom flask_limiter.util import get_remote...
```

**Checkpoint**: Agent integrates with Context7 and semantic memory!

---

## Part 5: Production Usage (5 minutes)

### Step 5.1: Register Agent in README

Update .claude/agents/README.md:

```markdown
## Domain Specialists (7 agents)

- @python-specialist - Python 3.11+, FastAPI, Django
- @typescript-specialist - TypeScript, React, Next.js
- @rust-specialist - Rust, async/await, cargo
- @go-specialist - Go, goroutines, cloud-native
- @database-specialist - PostgreSQL, MySQL, SQLite
- @devops-specialist - Docker, Kubernetes, CI/CD
- **@flask-specialist** - Flask, SQLAlchemy, Flask extensions ✨ NEW
```

### Step 5.2: Update Auto-Delegation Patterns

If using auto-delegation system, add pattern matching:

```python
# In pattern matcher configuration
AGENT_PATTERNS = {
    "**/*.py": {
        "flask_app": "@flask-specialist",  # If contains Flask patterns
        "default": "@python-specialist"
    }
}
```

**Checkpoint**: Agent ready for production use!

---

## What You Learned

### Agent Development Skills

✅ **Architecture Understanding**: 4-level hierarchy (orchestrator, domain, task, QA)
✅ **Agent Design**: Purpose, capabilities, tool access, delegation patterns
✅ **Configuration Writing**: Markdown format with code examples
✅ **Testing Methodology**: Direct invocation, delegation testing, integration validation
✅ **Production Integration**: README updates, pattern matching configuration

### Key Principles

🎯 **Specialization**: Domain-specific agents provide deeper expertise than general agents
🎯 **Tool Inheritance**: Domain specialists inherit full tool access (omit `tools:` field)
🎯 **Example-Driven**: Code examples demonstrate expected patterns
🎯 **Quality Standards**: Mandatory best practices enforce quality
🎯 **Integration**: Agents work with Context7, semantic memory, and delegation system

---

## Next Steps

### Immediate Actions

1. **Test Real Workflow**:
   ```
   @flask-specialist Build Flask authentication system with email verification
   ```

2. **Create More Specialists**:
   - @django-specialist for Django projects
   - @nextjs-specialist for Next.js applications
   - @kubernetes-specialist for K8s deployments

3. **Enhance Existing Agent**:
   - Add more code examples
   - Document edge cases
   - Include troubleshooting section

### Advanced Topics

- **Multi-Agent Coordination**: Orchestrate @flask-specialist + @typescript-specialist
- **Agent Metrics**: Track agent usage and effectiveness
- **Agent Evolution**: Update agents based on project learnings

### Related Tutorials

- **[Your First DevStream Project](first-project.md)** - Foundation
- **[Existing Project Integration](existing-project.md)** - Add DevStream to Flask project
- **[Multi-Stack Workflow](multi-stack-workflow.md)** - Full-stack with multiple agents

---

## Troubleshooting

### Issue: Agent Not Found

**Symptom**: `@flask-specialist` not recognized

**Solution**:
```bash
# 1. Verify file exists
ls -la .claude/agents/domain/flask-specialist.md

# 2. Check file syntax (must be valid Markdown)
head -50 .claude/agents/domain/flask-specialist.md

# 3. Restart Claude Code session
# Exit and restart Claude Code
```

### Issue: Agent Provides Generic Python Response

**Symptom**: @flask-specialist responds with generic Python code, not Flask-specific

**Solution**:
```bash
# 1. Verify agent file has Flask examples
grep -A 10 "Flask Application" .claude/agents/domain/flask-specialist.md

# 2. Be explicit in prompt
# Instead of: "Create login route"
# Use: "@flask-specialist Create Flask login route with Flask-WTF CSRF protection"

# 3. Check Context7 integration
# Ensure DEVSTREAM_CONTEXT7_ENABLED=true in .env.devstream
```

### Issue: Tool Access Errors

**Symptom**: Agent cannot use Write or Edit tools

**Solution**:
```bash
# Domain specialists should NOT have 'tools:' field
# Check agent file:
grep "tools:" .claude/agents/domain/flask-specialist.md
# Should return nothing (no tools: field)

# If tools: field exists, remove it:
# Domain specialists inherit full tool access by default
```

---

## Summary

You've successfully:

✅ Designed custom Flask specialist agent
✅ Created agent configuration with expertise sections
✅ Tested agent direct invocation and delegation
✅ Validated Context7 and memory integration
✅ Registered agent for production use

**Agent Capabilities**:
- Flask application architecture
- SQLAlchemy integration
- Flask extensions expertise
- Security-first development
- Production-ready patterns

Your DevStream system now has a specialized Flask expert ready for Flask development tasks!

---

**Tutorial Version**: 1.0.0
**Last Updated**: 2025-10-01
**Tested With**: DevStream v2.0.0, Flask 2.3.0, Python 3.11
