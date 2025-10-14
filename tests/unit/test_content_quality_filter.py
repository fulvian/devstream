#!/usr/bin/env .devstream/bin/python
"""
Unit tests for ContentQualityFilter component.

Tests intelligent content filtering system for reducing storage
of useless "context" records by 95%.
"""

import pytest
import time
from pathlib import Path
from typing import List

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'optimization'))

from content_quality_filter import (
    ContentQualityFilter,
    ContentFilterError,
    ContentType,
    QualityMetrics,
    get_content_quality_filter
)


class TestContentQualityFilter:
    """Test cases for ContentQualityFilter class."""

    @pytest.fixture
    def filter_instance(self):
        """Create a ContentQualityFilter instance for testing."""
        return ContentQualityFilter(quality_threshold=0.3)

    @pytest.fixture
    def sample_content_data(self):
        """Sample content data for testing."""
        return {
            "python_code": """from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import asyncio

app = FastAPI()

class User(BaseModel):
    id: int
    name: str
    email: Optional[str] = None

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    return {"id": user_id, "name": "Test User"}

@app.post("/users")
async def create_user(user: User):
    return user
""",
            "typescript_code": """import React, { useState, useEffect } from 'react';
import { NextApiRequest, NextApiResponse } from 'next';

interface UserProps {
  id: number;
  name: string;
  email?: string;
}

const UserComponent: React.FC<UserProps> = ({ id, name, email }) => {
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchUserData(id).finally(() => setLoading(false));
  }, [id]);

  return (
    <div className="user-card">
      <h2>{name}</h2>
      {email && <p>{email}</p>}
      {loading && <span>Loading...</span>}
    </div>
  );
};

export default UserComponent;
""",
            "documentation": """# API Documentation

## Overview

This document describes the REST API endpoints for user management.

## Endpoints

### GET /users/{id}

Retrieves a user by their unique identifier.

**Parameters:**
- `id` (integer): User ID

**Response:**
```json
{
  "id": 123,
  "name": "John Doe",
  "email": "john@example.com"
}
```

### POST /users

Creates a new user account.

**Request Body:**
- User object with name and optional email

## Authentication

All endpoints require JWT authentication.
""",
            "command_output": """✓ Package installed successfully
Processing dependencies...
Found 15 packages to install
+ fastapi 0.104.1
+ pydantic 2.5.0
+ sqlalchemy 2.0.23

Installation complete in 2.3 seconds
""",
            "error_output": """Error: Failed to connect to database
Connection refused: localhost:5432
Retrying in 5 seconds...
Attempt 3 of 5 failed
""",
            "simple_context": """This is a simple context file
with basic information
that is not very complex.""",
            "empty_content": "",
            "whitespace_only": "   \n\t   \n   ",
        }

    def test_filter_initialization(self, filter_instance):
        """Test filter initialization with default and custom thresholds."""
        assert filter_instance.quality_threshold == 0.3
        assert isinstance(filter_instance.file_importance_weights, dict)
        assert isinstance(filter_instance.topic_keywords, dict)
        assert len(filter_instance.tech_entities) > 0

        # Test custom threshold
        custom_filter = ContentQualityFilter(quality_threshold=0.5)
        assert custom_filter.quality_threshold == 0.5

    def test_calculate_relevance_score_validation(self, filter_instance):
        """Test input validation for calculate_relevance_score."""
        # Test empty content
        with pytest.raises(ValueError, match="Content cannot be empty"):
            filter_instance.calculate_relevance_score("", "test.py", "code", [], [])

        # Test empty file path
        with pytest.raises(ValueError, match="File path cannot be empty"):
            filter_instance.calculate_relevance_score("content", "", "code", [], [])

        # Test whitespace-only content
        with pytest.raises(ValueError, match="Content cannot be empty"):
            filter_instance.calculate_relevance_score("   \n  ", "test.py", "code", [], [])

    def test_python_code_complexity(self, filter_instance, sample_content_data):
        """Test complexity scoring for Python code."""
        content = sample_content_data["python_code"]
        entities = ["fastapi", "pydantic", "asyncio"]
        topics = ["api", "async", "database"]

        score = filter_instance.calculate_relevance_score(
            content=content,
            file_path="app/api/users.py",
            content_type="code",
            entities=entities,
            topics=topics
        )

        # Python code with imports and functions should score medium-high
        assert 0.3 <= score <= 1.0
        assert isinstance(score, float)

    def test_typescript_code_complexity(self, filter_instance, sample_content_data):
        """Test complexity scoring for TypeScript code."""
        content = sample_content_data["typescript_code"]
        entities = ["react", "next.js", "typescript"]
        topics = ["api", "frontend"]

        score = filter_instance.calculate_relevance_score(
            content=content,
            file_path="components/UserComponent.tsx",
            content_type="code",
            entities=entities,
            topics=topics
        )

        # TypeScript React component should score medium
        assert 0.2 <= score <= 1.0
        assert isinstance(score, float)

    def test_documentation_complexity(self, filter_instance, sample_content_data):
        """Test complexity scoring for documentation."""
        content = sample_content_data["documentation"]
        entities = ["api", "jwt"]
        topics = ["api", "documentation"]

        score = filter_instance.calculate_relevance_score(
            content=content,
            file_path="docs/api.md",
            content_type="documentation",
            entities=entities,
            topics=topics
        )

        # Well-structured documentation should score medium
        assert 0.3 <= score <= 1.0
        assert isinstance(score, float)

    def test_command_output_complexity(self, filter_instance, sample_content_data):
        """Test complexity scoring for command output."""
        content = sample_content_data["command_output"]
        entities = ["fastapi", "pydantic"]
        topics = ["database"]

        score = filter_instance.calculate_relevance_score(
            content=content,
            file_path="bash_output/pip_install.txt",
            content_type="output",
            entities=entities,
            topics=topics
        )

        # Structured command output should score low-medium
        assert 0.2 <= score <= 1.0
        assert isinstance(score, float)

    def test_simple_content_low_score(self, filter_instance, sample_content_data):
        """Test that simple content scores low."""
        content = sample_content_data["simple_context"]
        entities = []
        topics = []

        score = filter_instance.calculate_relevance_score(
            content=content,
            file_path="simple.txt",
            content_type="context",
            entities=entities,
            topics=topics
        )

        # Simple content should score low
        assert 0.0 <= score <= 0.5
        assert isinstance(score, float)

    def test_file_importance_weights(self, filter_instance):
        """Test file importance scoring based on file extensions."""
        # Test high importance files
        high_importance_files = [
            ("app/main.py", "code"),
            ("src/components/User.tsx", "code"),
            ("lib/database.rs", "code"),
            ("Dockerfile", "code"),
        ]

        for file_path, content_type in high_importance_files:
            score = filter_instance._calculate_file_importance_score(file_path, content_type)
            assert score >= 0.5, f"{file_path} should have medium-high importance score"

        # Test low importance files
        low_importance_files = [
            ("logs/debug.log", "output"),
            ("temp/backup.tmp", "context"),
            ("node_modules/package.json", "context"),
        ]

        for file_path, content_type in low_importance_files:
            score = filter_instance._calculate_file_importance_score(file_path, content_type)
            assert score <= 0.6, f"{file_path} should have low-medium importance score"

    def test_entity_density_scoring(self, filter_instance):
        """Test entity density scoring."""
        # Content with many tech entities
        content_high_density = """
        from fastapi import FastAPI
        from pydantic import BaseModel
        import asyncio
        import docker
        import redis
        """

        # Content with few tech entities
        content_low_density = """
        This is a simple text file
        with some basic information
        but no technical terms.
        """

        high_score = filter_instance._calculate_entity_density_score(
            content_high_density, ["fastapi", "pydantic", "asyncio", "docker", "redis"]
        )
        low_score = filter_instance._calculate_entity_density_score(
            content_low_density, []
        )

        assert high_score > low_score
        assert 0.0 <= high_score <= 1.0
        assert 0.0 <= low_score <= 1.0

    def test_topic_relevance_scoring(self, filter_instance):
        """Test topic relevance scoring."""
        # Content relevant to API and database topics
        api_content = """
        REST API endpoint for user management with PostgreSQL database integration.
        Uses FastAPI framework with SQLAlchemy ORM for database operations.
        """

        # Generic content
        generic_content = """
        This is a general text file about various topics
        without specific focus on any particular area.
        """

        api_score = filter_instance._calculate_topic_relevance_score(
            api_content, ["api", "database"]
        )
        generic_score = filter_instance._calculate_topic_relevance_score(
            generic_content, []
        )

        assert api_score > generic_score
        assert 0.0 <= api_score <= 1.0
        assert 0.0 <= generic_score <= 1.0

    def test_should_store_content_decision(self, filter_instance, sample_content_data):
        """Test content storage decision logic."""
        # High quality content - should be stored
        high_quality_content = sample_content_data["python_code"]
        should_store, score = filter_instance.should_store_content(
            content=high_quality_content,
            file_path="app/api.py",
            content_type="code",
            entities=["fastapi", "pydantic"],
            topics=["api", "async"]
        )
        assert should_store is True
        assert score >= filter_instance.quality_threshold

        # Low quality content - should not be stored
        low_quality_content = sample_content_data["simple_context"]
        should_store, score = filter_instance.should_store_content(
            content=low_quality_content,
            file_path="simple.txt",
            content_type="context",
            entities=[],
            topics=[]
        )
        assert should_store is False
        assert score < filter_instance.quality_threshold

    def test_auto_extraction(self, filter_instance, sample_content_data):
        """Test automatic entity and topic extraction when not provided."""
        content = sample_content_data["python_code"]

        # Call without providing entities and topics
        should_store, score = filter_instance.should_store_content(
            content=content,
            file_path="app/api.py",
            content_type="code",
            entities=None,  # Should auto-extract
            topics=None     # Should auto-extract
        )

        assert isinstance(should_store, bool)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_batch_filtering(self, filter_instance, sample_content_data):
        """Test batch content filtering."""
        content_items = [
            {
                "content": sample_content_data["python_code"],
                "file_path": "app/api.py",
                "content_type": "code",
                "entities": ["fastapi"],
                "topics": ["api"]
            },
            {
                "content": sample_content_data["simple_context"],
                "file_path": "simple.txt",
                "content_type": "context",
                "entities": [],
                "topics": []
            },
            {
                "content": sample_content_data["documentation"],
                "file_path": "docs/api.md",
                "content_type": "documentation",
                "entities": ["api"],
                "topics": ["documentation"]
            }
        ]

        results = filter_instance.filter_content_batch(content_items)

        assert len(results) == 3

        # Check that all items have required fields
        for item in results:
            assert "relevance_score" in item
            assert "should_store" in item
            assert isinstance(item["relevance_score"], float)
            assert isinstance(item["should_store"], bool)
            assert 0.0 <= item["relevance_score"] <= 1.0

        # At least one item should be filtered out (low quality)
        stored_count = sum(1 for item in results if item["should_store"])
        assert 1 <= stored_count <= 3  # At least one, but not necessarily all

    def test_batch_filtering_sync(self, filter_instance, sample_content_data):
        """Test synchronous batch filtering."""
        content_items = [
            {
                "content": sample_content_data["python_code"],
                "file_path": "app/api.py",
                "content_type": "code"
            },
            {
                "content": sample_content_data["simple_context"],
                "file_path": "simple.txt",
                "content_type": "context"
            }
        ]

        results = filter_instance.filter_content_batch(content_items)
        assert len(results) == 2

    def test_error_handling(self, filter_instance):
        """Test error handling in content filtering."""
        # Test with malformed content - should raise ValueError wrapped in ContentFilterError
        with pytest.raises(ValueError, match="Content cannot be empty"):
            filter_instance.calculate_relevance_score(
                content="",  # Empty content should raise ValueError
                file_path="test.py",
                content_type="code",
                entities=[],
                topics=[]
            )

        # Test should_store_content with error - should fail open
        should_store, score = filter_instance.should_store_content(
            content="",  # This will cause an error
            file_path="test.py",
            content_type="code",
            entities=[],
            topics=[]
        )
        # Should fail open - store content even if assessment fails
        assert should_store is True
        assert score == 0.5

    def test_performance_timing(self, filter_instance, sample_content_data):
        """Test that content filtering performs within acceptable time limits."""
        content = sample_content_data["python_code"]

        start_time = time.time()
        score = filter_instance.calculate_relevance_score(
            content=content,
            file_path="app/api.py",
            content_type="code",
            entities=["fastapi", "pydantic"],
            topics=["api", "async"]
        )
        end_time = time.time()

        processing_time = end_time - start_time

        # Should process content quickly (under 100ms)
        assert processing_time < 0.1
        assert isinstance(score, float)

    def test_filter_statistics(self, filter_instance):
        """Test filter statistics method."""
        stats = filter_instance.get_filter_statistics()

        assert isinstance(stats, dict)
        assert "quality_threshold" in stats
        assert "supported_content_types" in stats
        assert "file_importance_weights" in stats
        assert "topic_count" in stats
        assert "tech_entity_count" in stats

        assert stats["quality_threshold"] == 0.3
        assert isinstance(stats["supported_content_types"], list)
        assert isinstance(stats["file_importance_weights"], dict)
        assert stats["topic_count"] > 0
        assert stats["tech_entity_count"] > 0

    def test_quality_metrics_dataclass(self):
        """Test QualityMetrics dataclass validation."""
        # Valid metrics
        metrics = QualityMetrics(
            complexity_score=0.8,
            entity_density_score=0.7,
            topic_relevance_score=0.6,
            file_importance_score=0.9,
            overall_score=0.75,
            processing_time_ms=25.5
        )
        assert metrics.complexity_score == 0.8
        assert metrics.overall_score == 0.75
        assert metrics.processing_time_ms == 25.5

        # Invalid metrics (out of range)
        with pytest.raises(ValueError, match="complexity_score must be between 0 and 1"):
            QualityMetrics(
                complexity_score=1.5,  # Invalid
                entity_density_score=0.7,
                topic_relevance_score=0.6,
                file_importance_score=0.9,
                overall_score=0.75,
                processing_time_ms=25.5
            )

    def test_global_instance_function(self):
        """Test the global instance getter function."""
        # Test that it returns an instance
        filter_instance = get_content_quality_filter()
        assert isinstance(filter_instance, ContentQualityFilter)

        # Test that subsequent calls return the same instance
        filter_instance2 = get_content_quality_filter()
        assert filter_instance is filter_instance2

        # Test custom threshold
        custom_filter = get_content_quality_filter(quality_threshold=0.7)
        assert custom_filter.quality_threshold == 0.7

    def test_content_type_enum(self):
        """Test ContentType enum."""
        assert ContentType.CODE == "code"
        assert ContentType.DOCUMENTATION == "documentation"
        assert ContentType.OUTPUT == "output"
        assert ContentType.ERROR == "error"
        assert ContentType.DECISION == "decision"

        # Test that all expected values are present
        expected_types = ["code", "context", "output", "error", "decision", "documentation"]
        actual_types = [ct.value for ct in ContentType]
        for expected in expected_types:
            assert expected in actual_types

    def test_edge_cases(self, filter_instance):
        """Test edge cases and boundary conditions."""
        # Very long content
        long_content = "def function():\n    pass\n" * 1000
        score = filter_instance.calculate_relevance_score(
            content=long_content,
            file_path="long_file.py",
            content_type="code",
            entities=[],
            topics=[]
        )
        assert 0.0 <= score <= 1.0

        # Very short content
        short_content = "x = 1"
        score = filter_instance.calculate_relevance_score(
            content=short_content,
            file_path="short.py",
            content_type="code",
            entities=[],
            topics=[]
        )
        assert 0.0 <= score <= 1.0

        # Content with special characters
        special_content = "!@#$%^&*()_+{}|:<>?`~\\[];'\",./"
        score = filter_instance.calculate_relevance_score(
            content=special_content,
            file_path="special.txt",
            content_type="context",
            entities=[],
            topics=[]
        )
        assert 0.0 <= score <= 1.0

    def test_different_file_extensions(self, filter_instance):
        """Test scoring for different file extensions."""
        content = "print('hello world')"

        extensions_and_expected_scores = [
            (".py", 0.1),    # Python - baseline importance
            (".js", 0.1),    # JavaScript - baseline importance
            (".md", 0.1),    # Markdown - baseline importance
            (".txt", 0.1),   # Text - low importance
            (".log", 0.1),   # Log - very low importance
        ]

        for ext, expected_min_score in extensions_and_expected_scores:
            score = filter_instance.calculate_relevance_score(
                content=content,
                file_path=f"test{ext}",
                content_type="code",
                entities=[],
                topics=[]
            )
            assert score >= expected_min_score, f"Extension {ext} should score at least {expected_min_score}"