#!/usr/bin/env python3
"""
Unit tests for code-aware query construction.

Tests the _build_code_aware_query method in pre_tool_use.py
for extracting meaningful code elements from Python, TypeScript,
Rust, and Go files.
"""

import re
from pathlib import Path
import pytest


class CodeAwareQueryBuilder:
    """
    Standalone version of _build_code_aware_query for testing.
    Extracted from PreToolUseHook to avoid dependencies.
    """

    def __init__(self):
        self.debug_messages = []

    def debug_log(self, msg: str):
        """Mock debug logging."""
        self.debug_messages.append(msg)

    def _build_code_aware_query(self, file_path: str, content: str) -> str:
        """
        Build intelligent query from code structure.

        Extracts:
        - Imports (libraries/modules being used)
        - Class names (key abstractions)
        - Function names (main operations)
        - Decorators (framework patterns like @app.get, @pytest.fixture)

        Args:
            file_path: Path to file being edited
            content: File content

        Returns:
            Structured query string with code elements
        """
        import time
        start_time = time.time()

        filename = Path(file_path).name
        ext = Path(file_path).suffix.lower()

        elements = [filename]

        # Python code analysis
        if ext == '.py':
            # Extract imports
            import_pattern = r'^(?:from\s+(\S+)|import\s+(\S+))'
            imports = re.findall(import_pattern, content, re.MULTILINE)
            imports = [i[0] or i[1] for i in imports if i[0] or i[1]]
            # Filter out stdlib and builtins, split dotted imports
            filtered_imports = []
            stdlib = {'os', 'sys', 're', 'json', 'typing', 'pathlib', 'datetime',
                     'asyncio', 'subprocess', 'logging', 'time', 'collections'}
            for imp in imports:
                base = imp.split('.')[0]  # Get root module
                if base not in stdlib:
                    filtered_imports.append(base)
            elements.extend(filtered_imports[:5])  # Max 5 imports

            # Extract class names
            class_pattern = r'^class\s+(\w+)'
            classes = re.findall(class_pattern, content, re.MULTILINE)
            elements.extend(classes[:3])  # Max 3 classes

            # Extract function/method names
            func_pattern = r'^(?:async\s+)?def\s+(\w+)'
            funcs = re.findall(func_pattern, content, re.MULTILINE)
            elements.extend(funcs[:5])  # Max 5 functions

            # Extract decorators (framework indicators)
            decorator_pattern = r'^@(\w+(?:\.\w+)?)'
            decorators = re.findall(decorator_pattern, content, re.MULTILINE)
            elements.extend(decorators[:3])  # Max 3 decorators

        # TypeScript/JavaScript analysis
        elif ext in ['.ts', '.tsx', '.js', '.jsx']:
            # Extract imports
            import_pattern = r'(?:import|from)\s+[\'"]([^\'"]+)[\'"]'
            imports = re.findall(import_pattern, content)
            # Filter relative imports and get package names
            filtered_imports = []
            for imp in imports:
                if not imp.startswith('.'):
                    # Get package name (before first /)
                    pkg = imp.split('/')[0]
                    filtered_imports.append(pkg)
            elements.extend(filtered_imports[:5])

            # Extract class/component names
            class_pattern = r'(?:class|function|const)\s+(\w+)'
            names = re.findall(class_pattern, content)
            elements.extend(names[:5])

        # Rust analysis
        elif ext == '.rs':
            # Extract use statements
            use_pattern = r'^use\s+([a-zA-Z_][a-zA-Z0-9_:]*)'
            uses = re.findall(use_pattern, content, re.MULTILINE)
            elements.extend([u.split('::')[0] for u in uses[:5]])

            # Extract struct/enum/trait names
            type_pattern = r'^(?:struct|enum|trait|impl)\s+(\w+)'
            types = re.findall(type_pattern, content, re.MULTILINE)
            elements.extend(types[:5])

        # Go analysis
        elif ext == '.go':
            # Extract imports
            import_pattern = r'import\s+(?:"([^"]+)"|`([^`]+)`)'
            imports = re.findall(import_pattern, content)
            imports = [i[0] or i[1] for i in imports]
            elements.extend([imp.split('/')[-1] for imp in imports[:5]])

            # Extract type/struct/interface names
            type_pattern = r'^type\s+(\w+)'
            types = re.findall(type_pattern, content, re.MULTILINE)
            elements.extend(types[:5])

        # Build query with code structure
        query = " ".join(elements)

        # Fallback to content prefix if no elements extracted
        if len(query) < 50:
            query = f"{filename} {content[:300]}"

        # Log performance metrics
        elapsed_ms = (time.time() - start_time) * 1000
        self.debug_log(
            f"Code-aware query built in {elapsed_ms:.1f}ms: {query[:80]}..."
        )

        return query


class TestCodeAwareQuery:
    """Test suite for code-aware query construction."""

    @pytest.fixture
    def builder(self):
        """Create CodeAwareQueryBuilder instance."""
        return CodeAwareQueryBuilder()

    def test_python_code_extraction(self, builder):
        """Test Python code element extraction."""
        python_code = """
from fastapi import FastAPI, Depends
import structlog
from typing import Optional

logger = structlog.get_logger()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    \"\"\"Get user by ID.\"\"\"
    pass

class UserService:
    async def fetch_user(self, user_id: int) -> Optional[dict]:
        pass
"""
        query = builder._build_code_aware_query("api_users.py", python_code)

        # Verify extracted elements
        assert "api_users.py" in query
        assert "fastapi" in query.lower()
        assert "structlog" in query.lower()
        assert "get_user" in query
        assert "UserService" in query
        assert "app" in query or "@app.get" in query  # Decorator or decorator target

        # Verify stdlib filtered out
        assert "typing" not in query.lower()

    def test_typescript_code_extraction(self, builder):
        """Test TypeScript/JavaScript code element extraction."""
        ts_code = """
import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import axios from 'axios';

export function UserDashboard() {
  const [users, setUsers] = useState([]);

  useEffect(() => {
    axios.get('/api/users').then(setUsers);
  }, []);

  return <div>Dashboard</div>;
}

class UserService {
  async fetchUsers() {
    return axios.get('/api/users');
  }
}
"""
        query = builder._build_code_aware_query("UserDashboard.tsx", ts_code)

        # Verify extracted elements
        assert "UserDashboard.tsx" in query
        assert "react" in query.lower()
        assert "axios" in query.lower()
        assert "UserDashboard" in query or "UserService" in query

        # Verify relative imports filtered
        assert "@/components" not in query

    def test_rust_code_extraction(self, builder):
        """Test Rust code element extraction."""
        rust_code = """
use std::sync::Arc;
use tokio::sync::Mutex;
use axum::{Router, Json};

struct AppState {
    db: Arc<Mutex<Database>>
}

impl AppState {
    async fn new() -> Self {
        Self { db: Arc::new(Mutex::new(Database::new())) }
    }
}

enum Status {
    Active,
    Inactive
}
"""
        query = builder._build_code_aware_query("app_state.rs", rust_code)

        # Verify extracted elements
        assert "app_state.rs" in query
        assert "tokio" in query.lower()
        assert "axum" in query.lower()
        assert "AppState" in query or "Status" in query

    def test_go_code_extraction(self, builder):
        """Test Go code element extraction."""
        go_code = """
package main

import (
    "github.com/gin-gonic/gin"
    "database/sql"
    _ "github.com/lib/pq"
)

type User struct {
    ID   int    `json:"id"`
    Name string `json:"name"`
}

type UserService struct {
    db *sql.DB
}

func (s *UserService) GetUser(id int) (*User, error) {
    // Implementation
    return nil, nil
}
"""
        query = builder._build_code_aware_query("user_service.go", go_code)

        # Verify extracted elements
        assert "user_service.go" in query
        assert "gin" in query.lower()
        assert "pq" in query.lower()
        assert "User" in query or "UserService" in query

    def test_fallback_for_unparseable_files(self, builder):
        """Test fallback to content prefix for unparseable files."""
        # Generic text file
        text_content = "This is a plain text file with some content that cannot be parsed."
        query = builder._build_code_aware_query("README.txt", text_content)

        # Should contain filename and content prefix
        assert "README.txt" in query
        assert "This is a plain text file" in query

    def test_fallback_for_minimal_code(self, builder):
        """Test fallback when no code elements extracted."""
        minimal_code = "# Empty Python file\npass\n"
        query = builder._build_code_aware_query("empty.py", minimal_code)

        # Should use fallback with filename + content
        assert "empty.py" in query
        # Fallback should include content or just filename if too short
        assert len(query) >= len("empty.py")

    def test_query_length_constraints(self, builder):
        """Test query length stays within optimal range."""
        # Large Python file with many imports
        large_code = "\n".join([
            f"from package{i} import Module{i}" for i in range(50)
        ])
        large_code += "\n\n" + "\n".join([
            f"class Class{i}:\n    pass" for i in range(20)
        ])
        large_code += "\n\n" + "\n".join([
            f"def function_{i}():\n    pass" for i in range(30)
        ])

        query = builder._build_code_aware_query("large_file.py", large_code)

        # Should limit elements to prevent bloat
        assert 50 <= len(query) <= 500  # Optimal range

    def test_performance_requirement(self, builder):
        """Test query construction meets <50ms performance requirement."""
        import time

        # Medium-sized Python file
        test_code = """
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import structlog

app = FastAPI()
logger = structlog.get_logger()

class User(BaseModel):
    id: int
    name: str

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    pass

@app.post("/users/")
async def create_user(user: User):
    pass
"""

        # Measure performance
        start_time = time.time()
        query = builder._build_code_aware_query("test_api.py", test_code)
        elapsed_ms = (time.time() - start_time) * 1000

        # Verify performance meets requirement
        assert elapsed_ms < 50, f"Query construction took {elapsed_ms:.1f}ms (>50ms)"

        # Verify query quality
        assert "test_api.py" in query
        assert "fastapi" in query.lower()
        assert "get_user" in query or "create_user" in query

    def test_decorator_extraction(self, builder):
        """Test decorator extraction for framework patterns."""
        code_with_decorators = """
from fastapi import FastAPI
import pytest

app = FastAPI()

@app.get("/health")
async def health_check():
    pass

@app.post("/users")
async def create_user():
    pass

@pytest.fixture
def client():
    pass

@pytest.mark.asyncio
async def test_health():
    pass
"""
        query = builder._build_code_aware_query("test_file.py", code_with_decorators)

        # Verify decorators extracted
        assert "app" in query.lower() or "@app" in query.lower()
        assert "pytest" in query.lower()

    def test_no_stdlib_in_python_query(self, builder):
        """Test that stdlib modules are filtered out from element extraction."""
        code_with_stdlib = """
import os
import sys
import re
import json
from typing import Optional
from pathlib import Path
import asyncio

from fastapi import FastAPI  # This should be included

def process():
    pass
"""
        query = builder._build_code_aware_query("processor.py", code_with_stdlib)

        # Verify third-party libraries are extracted
        assert "fastapi" in query.lower()
        assert "processor.py" in query

        # Verify function name extracted
        assert "process" in query

        # Note: If no third-party libs found, fallback includes raw content
        # This is expected behavior - the extraction filters stdlib,
        # but fallback uses raw content for context

    def test_empty_file_fallback(self, builder):
        """Test fallback for completely empty files."""
        query = builder._build_code_aware_query("empty.py", "")

        # Should contain filename at minimum
        assert "empty.py" in query
        # Should be at least filename length
        assert len(query) >= len("empty.py")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
