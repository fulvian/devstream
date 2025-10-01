# DevStream Agents Guide

**Version**: 0.1.0-beta
**Audience**: All users
**Time to Read**: 20 minutes

This guide helps you choose the right agent for your task and understand how agents work together.

## Table of Contents

- [Agent Overview](#agent-overview)
- [When to Use Which Agent](#when-to-use-which-agent)
- [Domain Specialists](#domain-specialists)
- [Task Specialists](#task-specialists)
- [Quality Assurance](#quality-assurance)
- [Multi-Agent Workflows](#multi-agent-workflows)
- [Agent Auto-Delegation](#agent-auto-delegation)

---

## Agent Overview

DevStream provides **17 specialized agents** across **4 hierarchical levels**:

```
Level 1: ORCHESTRATOR (1 agent)
  └── @tech-lead - Multi-stack coordination

Level 2: DOMAIN SPECIALISTS (6 agents)
  ├── @python-specialist
  ├── @typescript-specialist
  ├── @rust-specialist
  ├── @go-specialist
  ├── @database-specialist
  └── @devops-specialist

Level 3: TASK SPECIALISTS (4 agents)
  ├── @api-architect
  ├── @performance-optimizer
  ├── @testing-specialist
  └── @documentation-specialist

Level 4: QUALITY ASSURANCE (1 agent)
  └── @code-reviewer (MANDATORY before commits)
```

### Agent Capabilities Matrix

| Agent | Languages | Frameworks | Use Case | Tools |
|-------|-----------|------------|----------|-------|
| **@tech-lead** | All | All | Multi-stack coordination | Task, Read, Glob, Grep |
| **@python-specialist** | Python 3.11+ | FastAPI, Django | Backend, async, testing | Full |
| **@typescript-specialist** | TypeScript | React, Next.js | Frontend, SSR | Full |
| **@rust-specialist** | Rust | Tokio, Actix | Systems, performance | Full |
| **@go-specialist** | Go | Gin, Echo | Cloud-native services | Full |
| **@database-specialist** | SQL | PostgreSQL, MySQL | Schema, optimization | Full |
| **@devops-specialist** | YAML, Shell | Docker, K8s | Deployment, IaC | Full |
| **@api-architect** | Language-agnostic | REST, GraphQL | API design | Full |
| **@performance-optimizer** | Language-agnostic | Profilers | Optimization | Full |
| **@testing-specialist** | Language-agnostic | Test frameworks | Test strategy | Full |
| **@documentation-specialist** | Markdown | Docusaurus, MkDocs | Technical writing | Full |
| **@code-reviewer** | All | All | Quality gates | Read, Grep, Glob, Bash |

---

## When to Use Which Agent

### Decision Tree

```
User Task
  │
  ├─ Single language? ─ YES ─> Direct invoke specialist
  │                            (@python-specialist, @typescript-specialist, etc.)
  │
  ├─ Multi-stack? ─ YES ─> Invoke @tech-lead
  │                         (orchestrates domain specialists)
  │
  ├─ API design? ─ YES ─> Invoke @api-architect
  │                        (creates OpenAPI spec)
  │
  ├─ Performance issue? ─ YES ─> Invoke @performance-optimizer
  │                               (profiles and optimizes)
  │
  ├─ Testing strategy? ─ YES ─> Invoke @testing-specialist
  │                               (test architecture)
  │
  ├─ Documentation? ─ YES ─> Invoke @documentation-specialist
  │                           (technical writing)
  │
  └─ Ready to commit? ─ YES ─> ALWAYS invoke @code-reviewer
                                (MANDATORY quality gate)
```

### Quick Reference

| Your Goal | Recommended Agent | Alternative |
|-----------|-------------------|-------------|
| Python backend API | `@python-specialist` | `@tech-lead` if multi-stack |
| React component | `@typescript-specialist` | `@tech-lead` if backend needed |
| Database schema | `@database-specialist` | `@tech-lead` for multi-DB |
| Docker deployment | `@devops-specialist` | `@tech-lead` for full stack |
| REST API design | `@api-architect` | `@tech-lead` for implementation |
| Slow endpoint | `@performance-optimizer` | Specialist + optimizer |
| Test coverage | `@testing-specialist` | Specialist + testing |
| API documentation | `@documentation-specialist` | `@api-architect` + docs |
| Pre-commit review | `@code-reviewer` | **MANDATORY** |
| Full-stack feature | `@tech-lead` | **Required** for multi-language |

---

## Domain Specialists

### @python-specialist

**Expertise**:
- Python 3.11+ features (match/case, ExceptionGroups, TypedDict)
- Async/await patterns with asyncio
- FastAPI for REST APIs
- Django for full-featured applications
- pytest with 95%+ coverage
- Pydantic v2 data validation
- mypy --strict type checking

**When to use**:
- Pure Python development
- Backend API implementation
- Data processing pipelines
- Testing Python code
- Python optimization

**Example invocations**:
```
@python-specialist Create a FastAPI endpoint for user CRUD operations

@python-specialist Refactor src/api/users.py to use async/await

@python-specialist Write comprehensive tests for authentication module
```

**Strengths**:
- Type-safe Python with mypy validation
- Async patterns for high performance
- Comprehensive testing (95%+ coverage)
- Structured error handling

**Limitations**:
- Python only (delegate to @tech-lead for multi-language)
- Does not handle frontend (delegate to @typescript-specialist)

### @typescript-specialist

**Expertise**:
- TypeScript 5+ with strict mode
- React 18+ with hooks (useState, useEffect, etc.)
- Next.js 14+ with App Router
- Server Components and Server Actions
- TailwindCSS for styling
- React Testing Library
- Performance optimization (useMemo, useCallback, lazy loading)

**When to use**:
- Frontend development
- React component creation
- Next.js application development
- TypeScript refactoring
- Frontend testing

**Example invocations**:
```
@typescript-specialist Build a user dashboard with charts in React

@typescript-specialist Convert class components to functional components with hooks

@typescript-specialist Optimize React app performance (reduce re-renders)
```

**Strengths**:
- Modern React patterns (hooks, suspense)
- TypeScript type safety
- Next.js SSR/SSG expertise
- Responsive design with TailwindCSS

**Limitations**:
- Frontend only (delegate to @tech-lead for backend)
- Does not handle API implementation (delegate to @python-specialist)

### @rust-specialist

**Expertise**:
- Ownership and borrowing
- Async/await with Tokio
- Error handling with Result<T, E>
- Zero-cost abstractions
- cargo ecosystem
- Performance-critical systems
- Memory safety without garbage collection

**When to use**:
- Systems programming
- Performance-critical components
- Memory-safe low-level code
- Concurrent systems
- WebAssembly modules

**Example invocations**:
```
@rust-specialist Implement a high-performance HTTP server with Actix

@rust-specialist Refactor C++ code to Rust with memory safety

@rust-specialist Create a WebAssembly module for browser-based computation
```

**Strengths**:
- Memory safety guarantees
- Zero-cost concurrency
- Fearless parallelism
- Excellent performance

**Limitations**:
- Steeper learning curve
- Not suitable for rapid prototyping
- Delegate to @tech-lead for multi-language integration

### @go-specialist

**Expertise**:
- Goroutines and channels
- Simple, readable code
- Cloud-native services
- Standard library proficiency
- Table-driven tests
- Docker and Kubernetes integration

**When to use**:
- Microservices development
- Cloud-native applications
- Concurrent systems
- Simple, maintainable code
- Docker/Kubernetes deployments

**Example invocations**:
```
@go-specialist Build a microservice for payment processing

@go-specialist Refactor monolith to microservices architecture

@go-specialist Implement concurrent data processing with goroutines
```

**Strengths**:
- Simple, readable syntax
- Built-in concurrency
- Fast compilation
- Excellent standard library

**Limitations**:
- Limited ecosystem compared to Python/JS
- Delegate to @tech-lead for frontend integration

### @database-specialist

**Expertise**:
- SQL (PostgreSQL, MySQL, SQLite)
- Schema design (normalization, indexing)
- Query optimization
- Database migrations
- Performance tuning
- ORM integration (SQLAlchemy, Prisma)

**When to use**:
- Database schema design
- Query optimization
- Migration planning
- Index strategy
- Database performance tuning

**Example invocations**:
```
@database-specialist Design a database schema for user management

@database-specialist Optimize slow query in users table (response time > 1s)

@database-specialist Create migration to add email verification
```

**Strengths**:
- Deep SQL expertise
- Performance optimization
- Scalability planning
- Multi-database support

**Limitations**:
- Database only (delegate to @tech-lead for application code)

### @devops-specialist

**Expertise**:
- Docker and Docker Compose
- Kubernetes (deployment, services, ingress)
- CI/CD pipelines (GitHub Actions, GitLab CI)
- Infrastructure as Code (Terraform, Ansible)
- Monitoring and logging
- Cloud platforms (AWS, GCP, Azure)

**When to use**:
- Containerization
- Kubernetes deployments
- CI/CD pipeline setup
- Infrastructure automation
- Production deployment

**Example invocations**:
```
@devops-specialist Create Dockerfile for FastAPI application

@devops-specialist Set up Kubernetes deployment with autoscaling

@devops-specialist Build CI/CD pipeline for automated testing and deployment
```

**Strengths**:
- Docker and Kubernetes expertise
- CI/CD automation
- Cloud platform knowledge
- Infrastructure as Code

**Limitations**:
- DevOps only (delegate to @tech-lead for application code)

---

## Task Specialists

### @api-architect

**Expertise**:
- REST API design principles
- OpenAPI/Swagger specifications
- GraphQL schema design
- API versioning strategies
- Authentication/authorization patterns
- Rate limiting and caching
- API documentation

**When to use**:
- Designing new APIs
- Creating OpenAPI specifications
- API versioning strategy
- Cross-service API contracts
- API documentation

**Example invocations**:
```
@api-architect Design REST API for user management system

@api-architect Create OpenAPI spec for existing endpoints

@api-architect Recommend versioning strategy for breaking changes
```

**Strengths**:
- Language-agnostic API design
- OpenAPI expertise
- REST/GraphQL patterns
- Comprehensive documentation

**Workflow**:
1. Analyze requirements
2. Design API contract (OpenAPI)
3. Delegate implementation to @python-specialist or @typescript-specialist
4. Review with @code-reviewer

### @performance-optimizer

**Expertise**:
- Profiling (py-spy, pprof, perf)
- Bottleneck identification
- Memory optimization
- Query optimization
- Caching strategies
- Algorithmic optimization
- Load testing

**When to use**:
- Slow endpoints (> 1s response time)
- High memory usage
- Scaling issues
- Performance regression
- Optimization opportunities

**Example invocations**:
```
@performance-optimizer Analyze slow GET /users endpoint (2.5s response)

@performance-optimizer Reduce memory usage in data processing pipeline

@performance-optimizer Optimize algorithm for sorting 1M records
```

**Strengths**:
- Language-agnostic optimization
- Systematic profiling
- Data-driven recommendations
- Measurable improvements

**Workflow**:
1. Profile current performance (baseline)
2. Identify bottlenecks
3. Recommend optimizations
4. Delegate implementation to specialist
5. Validate improvements (benchmarks)

### @testing-specialist

**Expertise**:
- Test strategy (unit, integration, E2E)
- TDD/BDD methodologies
- Test coverage analysis
- Mocking and fixtures
- Performance testing
- Cross-browser testing
- Test automation

**When to use**:
- Designing test strategy
- Improving test coverage
- Test architecture review
- Performance testing
- E2E test implementation

**Example invocations**:
```
@testing-specialist Design test strategy for authentication module

@testing-specialist Improve test coverage to 95%+ in src/api/

@testing-specialist Create E2E tests for user registration flow
```

**Strengths**:
- Language-agnostic testing
- Comprehensive coverage
- TDD/BDD expertise
- Test automation

**Workflow**:
1. Analyze current test coverage
2. Design test strategy
3. Delegate test implementation to specialist
4. Validate coverage (pytest-cov, jest --coverage)
5. Review with @code-reviewer

### @documentation-specialist

**Expertise**:
- Technical writing
- API documentation
- Architecture diagrams (Mermaid)
- User guides and tutorials
- OpenAPI documentation
- Markdown expertise
- Documentation-as-code

**When to use**:
- Creating user guides
- Documenting APIs
- Architecture documentation
- Writing tutorials
- Improving existing docs

**Example invocations**:
```
@documentation-specialist Document REST API with examples

@documentation-specialist Create user guide for authentication flow

@documentation-specialist Write architecture documentation with Mermaid diagrams
```

**Strengths**:
- Clear, concise writing
- Multiple documentation types
- Mermaid diagram expertise
- OpenAPI integration

**Workflow**:
1. Analyze existing code/APIs
2. Create documentation structure
3. Write content with examples
4. Review with @code-reviewer
5. Integrate into project docs

---

## Quality Assurance

### @code-reviewer (MANDATORY)

**Expertise**:
- OWASP Top 10 security checks
- Performance analysis
- Code quality validation
- Architecture review
- Test coverage validation
- Best practices enforcement

**When to use**:
- **ALWAYS** before git commit (enforced by auto-delegation)
- Security-sensitive code
- Performance-critical paths
- Major refactoring
- Pre-production validation

**What it checks**:

```
Security:
✓ SQL injection vulnerabilities
✓ XSS prevention
✓ CSRF protection
✓ Authentication/authorization
✓ Sensitive data exposure
✓ Insecure dependencies

Performance:
✓ N+1 query detection
✓ Unnecessary database calls
✓ Memory leaks
✓ Inefficient algorithms
✓ Missing indexes

Code Quality:
✓ Type safety (mypy, TypeScript strict)
✓ Error handling
✓ Code duplication
✓ Naming conventions
✓ Documentation completeness

Testing:
✓ Test coverage (95%+ for new code)
✓ Test quality
✓ Edge case coverage
✓ Integration tests
```

**Example invocations**:
```
@code-reviewer Review authentication implementation in src/auth/

@code-reviewer Validate security of JWT token handling

@code-reviewer Review full-stack user management feature
```

**Output Format**:
```
Code Review Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files Reviewed:
- src/api/auth.py (234 lines)
- src/models/user.py (156 lines)
- tests/api/test_auth.py (89 lines)

Security: ✅ PASS
✓ No SQL injection vulnerabilities
✓ Passwords hashed with bcrypt
✓ JWT tokens signed with HS256
⚠️  Warning: Consider adding rate limiting to login endpoint

Performance: ✅ PASS
✓ No N+1 queries detected
✓ Database queries optimized
✓ Caching implemented

Code Quality: ✅ PASS
✓ Complete type hints (mypy clean)
✓ Comprehensive error handling
✓ Clean code structure
✓ Well-documented

Testing: ✅ PASS
✓ Test coverage: 96% (target: 95%+)
✓ Edge cases covered
✓ Integration tests present

Overall: ✅ APPROVED
Ready for commit with 1 warning.

Recommendations:
1. Add rate limiting to prevent brute force attacks
2. Consider adding refresh token mechanism
3. Log authentication failures for monitoring
```

---

## Multi-Agent Workflows

### Pattern: Full-Stack Feature Development

**Scenario**: Build user management with Python backend + React frontend

**Workflow**:
```
User: "@tech-lead Build full-stack user management system"

@tech-lead:
  Analysis: Multi-stack feature (Python + TypeScript)
  Delegation Strategy:
    1. @api-architect: Design REST API contract
    2. @python-specialist: Implement backend
    3. @typescript-specialist: Implement frontend
    4. @testing-specialist: Design E2E tests
    5. @code-reviewer: Final validation

Step 1: API Design
  @tech-lead → Task(@api-architect): "Design user management REST API"
  @api-architect:
    - Creates OpenAPI specification
    - Defines endpoints (GET/POST/PUT/DELETE /users)
    - Returns API contract

Step 2: Backend Implementation
  @tech-lead → Task(@python-specialist): "Implement backend from OpenAPI spec"
  @python-specialist:
    - Implements FastAPI endpoints
    - Creates Pydantic models
    - Writes unit tests (95%+ coverage)

Step 3: Frontend Implementation
  @tech-lead → Task(@typescript-specialist): "Build React dashboard for users"
  @typescript-specialist:
    - Creates React components
    - Implements API client
    - Adds state management

Step 4: E2E Testing
  @tech-lead → Task(@testing-specialist): "Create E2E tests for user flow"
  @testing-specialist:
    - Designs E2E test scenarios
    - Delegates implementation to @typescript-specialist
    - Validates coverage

Step 5: Quality Review
  @tech-lead → Task(@code-reviewer): "Review full-stack implementation"
  @code-reviewer:
    - Security validation (OWASP Top 10)
    - Performance checks (API response times)
    - Architecture review (clean separation)
    - ✅ APPROVED

@tech-lead: "Full-stack user management complete. Ready for commit."
```

### Pattern: Performance Optimization

**Scenario**: Slow API endpoint (2.5s response time)

**Workflow**:
```
User: "@performance-optimizer Optimize slow GET /users endpoint"

@performance-optimizer:
  Step 1: Profile Current Performance
    - Baseline: 2.5s p95 response time
    - Bottleneck: N+1 query (100 queries for 100 users)

  Step 2: Design Optimization
    - Use SQLAlchemy joinedload() for eager loading
    - Add database index on user.email
    - Implement Redis caching for frequent queries

  Step 3: Delegate Implementation
    Task(@database-specialist): "Add index on users.email"
    Task(@python-specialist): "Refactor query to use joinedload()"

  Step 4: Validate Improvements
    - New benchmark: 150ms p95 response time
    - Improvement: 94% reduction (2.5s → 150ms)
    - ✅ Target achieved

@performance-optimizer: "Optimization complete. Response time: 150ms (-94%)"
```

---

## Agent Auto-Delegation

DevStream can automatically route tasks to the right agent based on file patterns.

### How Auto-Delegation Works

```mermaid
graph TD
    UserRequest[User Request] --> TechLead[@tech-lead receives]
    TechLead --> PatternMatcher[Pattern Matcher Analysis]

    PatternMatcher --> Confidence{Confidence Level}

    Confidence -->|≥ 0.95| AutoDelegate[AUTOMATIC Delegation]
    Confidence -->|0.85-0.94| Advisory[ADVISORY Suggestion]
    Confidence -->|< 0.85| Coordination[AUTHORIZATION Required]

    AutoDelegate --> Specialist[Invoke Specialist]
    Advisory --> UserApproval{User Approves?}
    Coordination --> TechLeadAnalysis[@tech-lead Full Analysis]

    UserApproval -->|Yes| Specialist
    UserApproval -->|No| TechLeadAnalysis

    Specialist --> Implementation[Implementation]
    TechLeadAnalysis --> MultiAgent[Multi-Agent Orchestration]
```

### File Pattern Matching

```python
# Pattern → Agent Mapping
FILE_PATTERNS = {
    "*.py": "python-specialist",        # Confidence: 0.95
    "*.ts, *.tsx": "typescript-specialist",  # Confidence: 0.95
    "*.rs": "rust-specialist",          # Confidence: 0.95
    "*.go": "go-specialist",            # Confidence: 0.95
    "**/schema.sql": "database-specialist",  # Confidence: 0.90
    "Dockerfile": "devops-specialist",  # Confidence: 0.90
}
```

### Auto-Delegation Examples

**Example 1: Automatic Delegation** (Confidence 0.95):
```
User: "Update src/api/users.py to add email validation"

DevStream (auto-delegation):
  Pattern: src/api/users.py → *.py
  Confidence: 0.95 (≥ auto-approve threshold)
  Decision: AUTOMATIC delegation
  → Task(@python-specialist)

@python-specialist: "[Implements email validation]"
```

**Example 2: Advisory Delegation** (Confidence 0.87):
```
User: "Refactor authentication in src/api/auth.py and src/models/user.py"

DevStream (auto-delegation):
  Pattern: Multiple *.py files
  Confidence: 0.87 (advisory range)
  Decision: ADVISORY delegation

  Suggestion: "@python-specialist is recommended for this task.
  Files: src/api/auth.py, src/models/user.py
  Approve delegation? [y/N]"

User: "y"

DevStream: "Task(@python-specialist): '[Refactor authentication]'"
```

**Example 3: Authorization Required** (Confidence 0.70):
```
User: "Build user dashboard with Python backend and React frontend"

DevStream (auto-delegation):
  Pattern: Mixed (*.py + *.tsx)
  Confidence: 0.70 (< min threshold)
  Decision: AUTHORIZATION REQUIRED
  → @tech-lead coordination

@tech-lead: "Analyzing multi-stack feature...
Delegation plan:
1. @api-architect: API design
2. @python-specialist: Backend
3. @typescript-specialist: Frontend
4. @code-reviewer: Validation

Proceeding with orchestration..."
```

### Configuration

```bash
# .env.devstream
DEVSTREAM_AUTO_DELEGATION_ENABLED=true          # Enable auto-delegation
DEVSTREAM_AUTO_DELEGATION_AUTO_APPROVE=0.95     # Automatic threshold
DEVSTREAM_AUTO_DELEGATION_MIN_CONFIDENCE=0.85   # Advisory threshold
DEVSTREAM_AUTO_DELEGATION_QUALITY_GATE=true     # Enforce @code-reviewer
```

---

## Summary

**Key Takeaways**:

1. **Direct Invocation**: Single-language tasks → domain specialist
2. **Orchestration**: Multi-stack tasks → @tech-lead
3. **Quality Gate**: ALWAYS @code-reviewer before commit
4. **Auto-Delegation**: Trust pattern matching for clear files
5. **Task Specialists**: Cross-language expertise (API design, testing, docs)

**Agent Selection Flowchart**:
```
Single Language? → Domain Specialist
Multi-Stack? → @tech-lead
API Design? → @api-architect
Performance? → @performance-optimizer
Testing? → @testing-specialist
Documentation? → @documentation-specialist
Pre-Commit? → @code-reviewer (MANDATORY)
```

**Next Steps**:
- [Configuration](configuration.md) - Customize agent settings
- [Troubleshooting](troubleshooting.md) - Common agent issues
- [FAQ](faq.md) - Frequently asked questions

For questions: [GitHub Issues](https://github.com/yourusername/devstream/issues)
