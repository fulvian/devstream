# Contributing to DevStream

Thank you for your interest in contributing to DevStream! This document provides guidelines for contributing to the project.

## Table of Contents

- [How to Contribute](#how-to-contribute)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Commit Conventions](#commit-conventions)
- [Pull Request Process](#pull-request-process)
- [Documentation Requirements](#documentation-requirements)
- [Getting Help](#getting-help)

## How to Contribute

### Ways to Contribute

- **Bug Reports**: Submit detailed bug reports with reproducible steps
- **Feature Requests**: Propose new features with clear use cases
- **Code Contributions**: Submit pull requests for bug fixes or new features
- **Documentation**: Improve documentation, tutorials, or examples
- **Testing**: Add test coverage or improve existing tests
- **Community**: Help answer questions and review pull requests

### Before You Start

1. Check existing issues and pull requests to avoid duplicates
2. Read the [Architecture Guide](docs/developer-guide/architecture.md)
3. Understand DevStream's [7-Step Workflow](CLAUDE.md#mandatory-workflow)
4. Review [Code Standards](#code-standards)

## Development Workflow

### 1. Setup Development Environment

Follow the [Development Setup Guide](docs/developer-guide/setup-development.md):

```bash
# Clone repository
git clone https://github.com/yourusername/devstream.git
cd devstream

# Create virtual environment
python3.11 -m venv .devstream
source .devstream/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Build MCP server
cd mcp-devstream-server
npm install
npm run build
```

### 2. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `test/` - Test improvements
- `refactor/` - Code refactoring

### 3. Follow DevStream Methodology

DevStream uses a **7-Step Mandatory Workflow** (see [CLAUDE.md](CLAUDE.md)):

1. **DISCUSSION**: Present problem, discuss trade-offs, identify constraints
2. **ANALYSIS**: Analyze codebase patterns, identify files to modify
3. **RESEARCH**: Use Context7 for best practices, document findings
4. **PLANNING**: Create TodoWrite list, define micro-tasks (10-15 min each)
5. **APPROVAL**: Present plan, get explicit approval
6. **IMPLEMENTATION**: One micro-task at a time, mark progress
7. **VERIFICATION/TEST**: Test every feature, 95%+ coverage

### 4. Development Best Practices

- **One task at a time**: Complete and test each micro-task before moving to next
- **Incremental commits**: Commit after each completed micro-task
- **Test-driven development**: Write tests first when possible
- **Documentation first**: Update docs before marking task complete
- **Code review ready**: Self-review code before submitting PR

## Code Standards

### Python Code Standards

**Type Safety** (MANDATORY):
```python
from typing import Optional, List, Dict, Any

def hybrid_search(
    self,
    query: str,
    limit: int = 10,
    content_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Perform hybrid search combining semantic and keyword search.

    Args:
        query: Search query string
        limit: Maximum results (default: 10)
        content_type: Optional filter by content type

    Returns:
        List of memory records sorted by relevance score

    Raises:
        DatabaseError: If database query fails
    """
    pass
```

**Code Quality Requirements**:
- ✅ Full type hints for all functions/methods
- ✅ Docstrings (Google style) for all public APIs
- ✅ `mypy --strict` compliance (zero errors)
- ✅ Max function length: 50 lines
- ✅ Max cyclomatic complexity: 10
- ✅ SOLID principles
- ❌ No `Any` type hints without justification
- ❌ No bare `except:` clauses
- ❌ No print() statements (use structured logging)

**Error Handling**:
```python
import structlog

logger = structlog.get_logger()

try:
    result = await operation()
except SpecificError as e:
    logger.error("operation_failed", error=str(e), context={"key": "value"})
    raise
```

### TypeScript Code Standards

**Type Safety**:
```typescript
interface TaskCreateParams {
  title: string;
  description: string;
  task_type: TaskType;
  priority: number;
  phase_name: string;
}

export async function createTask(params: TaskCreateParams): Promise<Task> {
  // Implementation
}
```

**Code Quality**:
- ✅ Strict TypeScript configuration
- ✅ ESLint + Prettier compliance
- ✅ Async/await for asynchronous operations
- ✅ Error handling with try/catch
- ❌ No `any` types without justification

### Code Formatting

**Python**: Use `black` with default settings
```bash
black .
```

**TypeScript**: Use `prettier` with project config
```bash
npm run format
```

## Testing Requirements

### Test Coverage

**MANDATORY Requirements**:
- ✅ 95%+ coverage for NEW code
- ✅ 100% pass rate before PR submission
- ✅ Integration tests for E2E workflows
- ✅ Performance validation for critical paths
- ✅ Error handling tests

### Test Structure

```
tests/
├── unit/              # Fast (<1s), isolated tests
│   ├── test_memory.py
│   └── test_hooks.py
├── integration/       # E2E tests (<10s)
│   ├── test_mcp_server.py
│   └── test_workflow.py
└── fixtures/          # Test data and mocks
    └── sample_data.py
```

### Running Tests

```bash
# Run all tests
.devstream/bin/python -m pytest tests/ -v

# Run with coverage
.devstream/bin/python -m pytest tests/ --cov=.claude/hooks/devstream --cov-report=html

# Run specific test file
.devstream/bin/python -m pytest tests/unit/test_memory.py -v

# Run specific test
.devstream/bin/python -m pytest tests/unit/test_memory.py::test_hybrid_search -v
```

### Test Examples

**Unit Test**:
```python
import pytest
from devstream.memory import MemoryManager

def test_hybrid_search_returns_results():
    """Test hybrid search returns relevant results."""
    manager = MemoryManager(db_path=":memory:")

    # Insert test data
    manager.store("Python async programming", content_type="documentation")

    # Search
    results = manager.hybrid_search("async Python", limit=5)

    # Verify
    assert len(results) > 0
    assert "async" in results[0]["content"].lower()
```

**Integration Test**:
```python
@pytest.mark.asyncio
async def test_end_to_end_workflow():
    """Test complete task creation → execution → completion workflow."""
    # Create task
    task_id = await create_task(title="Test Task", ...)

    # Execute
    await update_task(task_id, status="active")

    # Complete
    await update_task(task_id, status="completed")

    # Verify
    task = await get_task(task_id)
    assert task["status"] == "completed"
```

## Commit Conventions

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions or modifications
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Build process, dependencies, etc.

**Examples**:
```
feat(memory): Add hybrid search with RRF algorithm

Implements Reciprocal Rank Fusion combining semantic and keyword search.
Improves search relevance by 35% based on benchmark tests.

Closes #123
```

```
fix(hooks): Graceful degradation when Ollama unavailable

Hook now continues execution when Ollama is not running,
logging warning instead of failing.

Fixes #456
```

### Commit Best Practices

- ✅ Atomic commits (one logical change per commit)
- ✅ Clear, descriptive commit messages
- ✅ Reference related issues
- ✅ Include co-author attribution when pair programming
- ❌ Don't commit broken code
- ❌ Don't mix unrelated changes

## Pull Request Process

### 1. Before Submitting PR

**Checklist**:
- [ ] All tests pass (`pytest tests/`)
- [ ] Code coverage ≥ 95% for new code
- [ ] Type checking passes (`mypy --strict`)
- [ ] Code formatting applied (`black .`, `npm run format`)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if user-facing)
- [ ] Commit messages follow conventions
- [ ] No merge conflicts with `main`

### 2. Create Pull Request

**PR Title**: Use commit message format
```
feat(memory): Add hybrid search with RRF algorithm
```

**PR Description Template**:
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update

## How Has This Been Tested?
Describe tests performed

## Checklist
- [ ] Tests pass locally
- [ ] Code coverage ≥ 95%
- [ ] Documentation updated
- [ ] CHANGELOG.md updated

## Related Issues
Closes #123
```

### 3. Code Review Process

**What Reviewers Check**:
- Code correctness and logic
- Test coverage and quality
- Performance implications
- Security considerations
- Documentation completeness
- Adherence to code standards

**Response Time**:
- Initial review: Within 3 business days
- Follow-up reviews: Within 2 business days

**Addressing Feedback**:
- Respond to all review comments
- Make requested changes in new commits (don't force push)
- Mark conversations as resolved when addressed
- Request re-review when ready

### 4. Merge Requirements

**Before Merge**:
- ✅ At least 1 approving review from maintainer
- ✅ All CI checks passing
- ✅ All conversations resolved
- ✅ Branch up to date with `main`

**Merge Strategy**:
- Use "Squash and merge" for feature branches
- Preserve detailed commit history in PR description

## Documentation Requirements

### When to Update Documentation

**MANDATORY Updates**:
- New features → Update user guide + API reference
- API changes → Update API reference
- Workflow changes → Update developer guide
- Breaking changes → Update migration guide + CHANGELOG

### Documentation Standards

**User-Facing Documentation**:
- Clear, concise language (international audience)
- Code examples for every feature
- Screenshots/diagrams where helpful
- Cross-references to related docs

**API Documentation**:
- Complete parameter documentation (types, required/optional, defaults)
- Return type specifications
- Error codes and handling
- Usage examples

**Developer Documentation**:
- Architecture diagrams (Mermaid)
- Design decisions and rationale
- Testing strategies
- Performance considerations

### Documentation Structure

Follow [Diátaxis Framework](https://diataxis.fr/):
- **Tutorials**: Learning-oriented (`docs/tutorials/`)
- **How-To Guides**: Task-oriented (`docs/user-guide/`)
- **Reference**: Information-oriented (`docs/api/`)
- **Explanation**: Understanding-oriented (`docs/developer-guide/`)

## Getting Help

### Resources

- **Documentation**: [docs/](docs/)
- **User Guide**: [docs/user-guide/](docs/user-guide/)
- **Developer Guide**: [docs/developer-guide/](docs/developer-guide/)
- **API Reference**: [docs/api/](docs/api/)
- **Tutorials**: [docs/tutorials/](docs/tutorials/)

### Communication

- **Questions**: Open a GitHub Discussion
- **Bug Reports**: Open a GitHub Issue
- **Feature Requests**: Open a GitHub Issue
- **Security Issues**: See [SECURITY.md](SECURITY.md)

### Maintainers

For questions about contributing:
- Open a GitHub Discussion in "Contributing" category
- Tag maintainers in relevant issues/PRs

---

## License

By contributing to DevStream, you agree that your contributions will be licensed under the MIT License.

## Thank You!

Your contributions make DevStream better for everyone. We appreciate your time and effort! 🙏
