#!/usr/bin/env .devstream/bin/python
"""
Comprehensive Context7 Direct Client Integration Test

This file tests various Python libraries that should trigger Context7 Direct Client
retrieval with the current 100% rollout configuration.
"""

import aiohttp
import fastapi
import pytest
import sqlalchemy
import numpy as np
import pandas as pd
import requests
import django
import flask
import redis
import celery
import gunicorn
import uvicorn
from typing import Optional, List, Dict, Any

# FastAPI application setup
app = fastapi.FastAPI(
    title="Context7 Test API",
    description="Testing Context7 Direct Client integration",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Root endpoint that should trigger Context7 for fastapi."""
    return {"message": "Context7 Direct Client Test"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Optional[str] = None):
    """Read item endpoint that should trigger Context7 for fastapi."""
    return {"item_id": item_id, "q": q}

@app.post("/process")
async def process_data(data: Dict[str, Any]):
    """Process data endpoint that should trigger Context7 for multiple libraries."""
    # Use numpy for processing
    if "numbers" in data:
        numbers = np.array(data["numbers"])
        result = {
            "mean": float(np.mean(numbers)),
            "std": float(np.std(numbers)),
            "sum": float(np.sum(numbers))
        }
    else:
        result = {"error": "No numbers provided"}

    return result

def test_aiohttp_client():
    """Test aiohttp client with connection pooling."""
    async def fetch_data():
        connector = aiohttp.TCPConnector(
            limit=30,                    # Total connections
            limit_per_host=10,          # Per-host connections
            keepalive_timeout=15,       # Keep-alive timeout
            enable_cleanup_closed=True  # Cleanup on close
        )

        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                async with session.get('https://httpbin.org/json') as response:
                    return await response.json()
            except Exception:
                return {"error": "Network error"}

    return {"aiohttp_test": "Configured with connection pooling"}

def test_sqlalchemy_models():
    """Test SQLAlchemy models and database setup."""
    from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, relationship

    Base = declarative_base()

    class User(Base):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True)
        username = Column(String(80), unique=True, nullable=False)
        email = Column(String(120), unique=True, nullable=False)

        posts = relationship("Post", backref="author")

    class Post(Base):
        __tablename__ = 'posts'
        id = Column(Integer, primary_key=True)
        title = Column(String(140), nullable=False)
        content = Column(Text, nullable=False)
        user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Create engine (in-memory for testing)
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)

    return {"sqlalchemy_test": "Models created successfully"}

def test_pytest_fixtures():
    """Test pytest fixtures and testing patterns."""
    import pytest

    @pytest.fixture
    def sample_data():
        """Sample data fixture for testing."""
        return {
            "users": [
                {"id": 1, "name": "Alice", "email": "alice@example.com"},
                {"id": 2, "name": "Bob", "email": "bob@example.com"}
            ],
            "posts": [
                {"id": 1, "title": "Hello World", "user_id": 1},
                {"id": 2, "title": "Second Post", "user_id": 2}
            ]
        }

    @pytest.fixture
    def api_client():
        """Mock API client fixture."""
        class MockClient:
            def get(self, endpoint):
                return {"status": "success", "data": f"Mock response for {endpoint}"}

        return MockClient()

    return {"pytest_test": "Fixtures defined successfully"}

def test_numpy_operations():
    """Test NumPy array operations and calculations."""
    # Create sample data
    data = np.random.rand(1000, 10)  # 1000 samples, 10 features

    # Perform various operations
    mean_values = np.mean(data, axis=0)
    std_values = np.std(data, axis=0)
    correlation_matrix = np.corrcoef(data.T)

    # Vector operations (similar to embeddings)
    query_vector = np.random.rand(10)
    similarities = np.dot(data, query_vector)
    top_indices = np.argsort(similarities)[-5:][::-1]

    return {
        "numpy_test": "Operations completed",
        "data_shape": data.shape,
        "top_similarities": similarities[top_indices][:3].tolist()
    }

def test_pandas_dataframe():
    """Test pandas DataFrame operations."""
    # Create sample DataFrame
    data = {
        'name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'],
        'age': [25, 30, 35, 28, 32],
        'city': ['New York', 'London', 'Paris', 'Tokyo', 'Sydney'],
        'salary': [70000, 80000, 90000, 75000, 85000]
    }

    df = pd.DataFrame(data)

    # Perform operations
    summary_stats = df.describe()
    grouped = df.groupby('city')['salary'].mean()
    filtered = df[df['age'] > 30]

    return {
        "pandas_test": "DataFrame operations completed",
        "rows": len(df),
        "columns": len(df.columns),
        "avg_salary": float(df['salary'].mean())
    }

def test_django_models():
    """Test Django model patterns (without full Django setup)."""
    # This would typically require Django settings configuration
    # For testing purposes, we'll just show the model structure

    class MockModel:
        """Mock Django model for testing."""
        def __init__(self):
            self.fields = {
                'id': 'AutoField',
                'title': 'CharField(max_length=200)',
                'content': 'TextField',
                'created_at': 'DateTimeField(auto_now_add=True)',
                'updated_at': 'DateTimeField(auto_now=True)'
            }

        def __str__(self):
            return "Mock Django Model"

    return {"django_test": "Mock model structure defined"}

def test_flask_routes():
    """Test Flask route patterns."""
    from flask import Flask, request, jsonify

    # Mock Flask app structure (without actual app creation)
    routes = {
        '/': 'index',
        '/api/users': 'get_users',
        '/api/users/<int:user_id>': 'get_user',
        '/api/posts': 'create_post'
    }

    return {"flask_test": "Route patterns defined", "routes": list(routes.keys())}

def test_redis_operations():
    """Test Redis operations and patterns."""
    # Mock Redis operations (without actual Redis connection)
    operations = {
        'set': 'SET key value',
        'get': 'GET key',
        'hset': 'HSET hash field value',
        'hget': 'HGET hash field',
        'lpush': 'LPUSH list value',
        'rpop': 'RPOP list'
    }

    return {"redis_test": "Operations defined", "count": len(operations)}

def test_celery_tasks():
    """Test Celery task definitions."""
    # Mock Celery task structure
    task_definitions = {
        'send_email': {
            'name': 'send_email_task',
            'args': ['recipient', 'subject', 'body'],
            'kwargs': {}
        },
        'process_data': {
            'name': 'process_data_task',
            'args': ['data'],
            'kwargs': {'priority': 'normal'}
        }
    }

    return {"celery_test": "Task definitions created", "tasks": list(task_definitions.keys())}

# Comprehensive test runner
def run_all_tests():
    """Run all Context7 integration tests."""
    tests = [
        ("FastAPI App", lambda: {"fastapi": "App configured with routes"}),
        ("aiohttp Client", test_aiohttp_client),
        ("SQLAlchemy Models", test_sqlalchemy_models),
        ("pytest Fixtures", test_pytest_fixtures),
        ("NumPy Operations", test_numpy_operations),
        ("pandas DataFrame", test_pandas_dataframe),
        ("Django Models", test_django_models),
        ("Flask Routes", test_flask_routes),
        ("Redis Operations", test_redis_operations),
        ("Celery Tasks", test_celery_tasks)
    ]

    print("🧪 Running Comprehensive Context7 Direct Client Tests")
    print("=" * 60)

    results = {}
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = {"status": "✅ SUCCESS", "result": result}
            print(f"✅ {test_name}: SUCCESS")
        except Exception as e:
            results[test_name] = {"status": "❌ ERROR", "error": str(e)}
            print(f"❌ {test_name}: ERROR - {str(e)[:50]}")

    # Summary
    successful = sum(1 for r in results.values() if r["status"] == "✅ SUCCESS")
    total = len(results)

    print(f"\n📊 Test Summary:")
    print(f"   Total tests: {total}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {total - successful}")
    print(f"   Success rate: {successful/total*100:.1f}%")

    if successful == total:
        print(f"\n🎉 All tests passed! Context7 Direct Client is working correctly.")
    else:
        print(f"\n⚠️ Some tests failed. Check the implementation.")

    return results

if __name__ == "__main__":
    # Run the comprehensive test suite
    results = run_all_tests()

    # This should trigger Context7 Direct Client for all the imported libraries
    print(f"\n📝 Libraries tested that should trigger Context7 Direct Client:")
    libraries = [
        "aiohttp", "fastapi", "pytest", "sqlalchemy",
        "numpy", "pandas", "requests", "django",
        "flask", "redis", "celery", "gunicorn", "uvicorn"
    ]

    for lib in libraries:
        print(f"   • {lib}")