# Security Policy

## Supported Versions

The following versions of DevStream are currently supported with security updates:

| Version | Supported          | End of Support |
|---------|--------------------|----------------|
| 0.1.x   | :white_check_mark: | TBD            |

**Note**: DevStream is currently in beta (v0.1.0-beta). Security updates will be provided for the 0.1.x series until the first stable release.

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in DevStream, please follow responsible disclosure practices:

### Where to Report

**DO NOT** create public GitHub issues for security vulnerabilities.

Instead, report security issues via:
- **Email**: security@devstream.dev (preferred)
- **GitHub Security Advisories**: [Create a private security advisory](https://github.com/yourusername/devstream/security/advisories/new)

### What to Include

Please provide the following information:
- **Description**: Clear description of the vulnerability
- **Impact**: Potential impact and severity assessment
- **Reproduction**: Step-by-step instructions to reproduce
- **Affected Versions**: DevStream versions affected
- **Suggested Fix**: If you have one (optional)
- **Disclosure Timeline**: Your preferred disclosure timeline

### Example Report

```
Subject: [SECURITY] SQL Injection in Memory Search

Description:
The semantic memory search function is vulnerable to SQL injection
when using user-supplied content_type parameter.

Impact:
An attacker could execute arbitrary SQL queries, potentially
accessing or modifying database contents.

Reproduction:
1. Call devstream_search_memory with content_type: "'; DROP TABLE--"
2. Observe SQL injection execution

Affected Versions: 0.1.0-beta

Suggested Fix:
Use parameterized queries instead of string concatenation
in memory_manager.py:245
```

## Response Timeline

We are committed to responding quickly to security reports:

| Timeline | Action |
|----------|--------|
| **24 hours** | Initial acknowledgment |
| **3 business days** | Preliminary assessment and severity classification |
| **7 business days** | Detailed response with investigation findings |
| **30 days** | Security patch release (for critical vulnerabilities) |
| **90 days** | Public disclosure (coordinated with reporter) |

**Critical Vulnerabilities**: We aim to release patches within 48 hours for critical issues (e.g., remote code execution, data exfiltration).

## Security Best Practices

### For Users

#### Secure Installation

1. **Verify Installation**:
```bash
# Always verify installation integrity
./scripts/verify-install.py --verbose
```

2. **Secure Database**:
```bash
# Ensure database has correct permissions
chmod 600 data/devstream.db

# Database should NOT be world-readable
ls -l data/devstream.db
# Expected: -rw------- (600)
```

3. **Environment Variables**:
```bash
# NEVER commit .env.devstream to version control
echo ".env.devstream" >> .gitignore

# Protect environment file
chmod 600 .env.devstream
```

#### Secure Configuration

**Hook Security**:
```json
{
  "hooks": {
    "PreToolUse": [{
      "hooks": [{
        "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/memory/pre_tool_use.py"
      }]
    }]
  }
}
```

**NEVER** run hooks with elevated privileges:
```bash
# ❌ DANGEROUS - Never do this
sudo claude code

# ✅ SAFE - Run as normal user
claude code
```

#### Secure Ollama Integration

**Local Ollama Only**:
```bash
# .env.devstream
DEVSTREAM_OLLAMA_BASE_URL=http://localhost:11434  # Local only, no remote endpoints
```

**Network Isolation**:
```bash
# Ollama should listen on localhost only
ollama serve --host 127.0.0.1:11434
```

### For Developers

#### Secure Coding Practices

**1. Input Validation**:
```python
from typing import Literal

def update_task(
    task_id: str,
    status: Literal["pending", "active", "completed", "failed"]
) -> None:
    """
    Update task status with validated input.

    Args:
        task_id: Task UUID (validated)
        status: Task status (validated against enum)
    """
    if not is_valid_uuid(task_id):
        raise ValueError("Invalid task_id format")

    # Safe - status is validated by type system
    db.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
```

**2. Parameterized Queries**:
```python
# ✅ SAFE - Parameterized query
cursor.execute(
    "SELECT * FROM semantic_memory WHERE content_type = ?",
    (content_type,)
)

# ❌ DANGEROUS - String concatenation (SQL injection risk)
cursor.execute(
    f"SELECT * FROM semantic_memory WHERE content_type = '{content_type}'"
)
```

**3. Secure Secrets Handling**:
```python
# ✅ SAFE - Environment variables
import os
from pathlib import Path

def load_config() -> dict:
    api_key = os.getenv("DEVSTREAM_API_KEY")
    if not api_key:
        raise ValueError("DEVSTREAM_API_KEY not set")
    return {"api_key": api_key}

# ❌ DANGEROUS - Hardcoded secrets
api_key = "sk-1234567890abcdef"  # Never do this!
```

**4. Path Traversal Prevention**:
```python
from pathlib import Path

def safe_file_access(relative_path: str) -> Path:
    """
    Safely resolve file path within project directory.

    Args:
        relative_path: User-supplied relative path

    Returns:
        Resolved absolute path

    Raises:
        SecurityError: If path escapes project directory
    """
    project_root = Path("/Users/fulvioventura/devstream").resolve()
    target = (project_root / relative_path).resolve()

    if not target.is_relative_to(project_root):
        raise SecurityError("Path traversal detected")

    return target
```

#### Security Testing

**Test for Common Vulnerabilities**:
```python
import pytest

def test_sql_injection_prevention():
    """Test that SQL injection is prevented in memory search."""
    malicious_input = "'; DROP TABLE semantic_memory; --"

    # Should safely handle malicious input
    results = memory_manager.hybrid_search(
        query=malicious_input,
        limit=10
    )

    # Verify table still exists
    assert memory_manager.table_exists("semantic_memory")

def test_path_traversal_prevention():
    """Test that path traversal is prevented in file operations."""
    malicious_path = "../../etc/passwd"

    with pytest.raises(SecurityError):
        safe_file_access(malicious_path)
```

## Known Security Considerations

### 1. Local Execution Model

**Design**: DevStream runs locally with full file system access.

**Implications**:
- ✅ No remote API exposure
- ✅ No cloud data transmission
- ⚠️ User responsible for file system security
- ⚠️ Hooks execute with user's permissions

**Recommendation**: Run DevStream with minimal necessary permissions.

### 2. Database Security

**Design**: SQLite database with file-based storage.

**Implications**:
- ✅ No network exposure
- ⚠️ File permissions critical
- ⚠️ No built-in encryption

**Recommendation**:
```bash
# Secure database file
chmod 600 data/devstream.db

# For sensitive projects, use disk encryption
# (FileVault on macOS, LUKS on Linux)
```

### 3. Hook Execution

**Design**: Hooks execute Python scripts with user permissions.

**Implications**:
- ✅ Sandboxed to user account
- ⚠️ Can access all files user can access
- ⚠️ Hook scripts must be trusted

**Recommendation**:
- Only install hooks from trusted sources
- Review hook code before enabling
- Use `.env.devstream` to disable hooks if needed

### 4. Ollama Integration

**Design**: Optional local Ollama integration for embeddings.

**Implications**:
- ✅ Local-only by default
- ✅ No external API calls
- ⚠️ Ollama server security is user's responsibility

**Recommendation**:
```bash
# Ensure Ollama is localhost-only
DEVSTREAM_OLLAMA_BASE_URL=http://localhost:11434
```

### 5. Context7 Integration

**Design**: Retrieves public documentation from Context7 API.

**Implications**:
- ⚠️ Network requests to external API
- ⚠️ Library names are transmitted
- ✅ No code or sensitive data transmitted

**Recommendation**:
```bash
# Disable Context7 for sensitive projects
DEVSTREAM_CONTEXT7_ENABLED=false
```

## Security Updates

### Notification Channels

Stay informed about security updates:
- **GitHub Security Advisories**: [Watch repository](https://github.com/yourusername/devstream)
- **Release Notes**: Check CHANGELOG.md for security fixes
- **GitHub Releases**: Security patches are tagged with `security` label

### Update Process

**Check for Updates**:
```bash
# Check current version
claude code --version

# Check for updates (manual for now)
git fetch origin
git log HEAD..origin/main --oneline
```

**Apply Security Updates**:
```bash
# 1. Backup your database
cp data/devstream.db data/devstream.db.backup

# 2. Pull latest version
git pull origin main

# 3. Reinstall dependencies
.devstream/bin/pip install -r requirements.txt --upgrade

# 4. Rebuild MCP server
cd mcp-devstream-server
npm install
npm run build

# 5. Verify installation
cd ..
./scripts/verify-install.py
```

## Security Audit

DevStream is currently in beta and has not undergone a formal security audit. We welcome security researchers to review the codebase and report findings.

### Scope

**In Scope**:
- SQL injection vulnerabilities
- Path traversal vulnerabilities
- Command injection vulnerabilities
- Insecure file permissions
- Sensitive data exposure
- Authentication/authorization issues (if applicable)

**Out of Scope**:
- Social engineering attacks
- Physical access attacks
- Denial of service (local tool)
- Issues in third-party dependencies (report to upstream)

## Contact

For security concerns:
- **Email**: security@devstream.dev
- **GitHub Security Advisories**: [Create advisory](https://github.com/yourusername/devstream/security/advisories/new)

For general questions:
- **GitHub Discussions**: [Security category](https://github.com/yourusername/devstream/discussions/categories/security)

---

**Last Updated**: 2025-10-01
**Version**: 0.1.0-beta
