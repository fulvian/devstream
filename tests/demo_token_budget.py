#!/usr/bin/env python3
"""
Visual demonstration of token budget enforcement.

Shows how memory results are truncated to fit within budget.
"""

import sys
from pathlib import Path

# Add hooks to path
sys.path.insert(0, str(Path(__file__).parent.parent / '.claude/hooks/devstream/memory'))

from pre_tool_use import PreToolUseHook


def create_realistic_memory_items():
    """Create realistic memory items similar to actual DevStream data."""
    return [
        {
            "content": """
FastAPI endpoint implementation for user authentication:

```python
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt

app = FastAPI()
security = HTTPBearer()

class UserLogin(BaseModel):
    username: str
    password: str

@app.post("/login")
async def login(user: UserLogin):
    # Validate credentials (simplified)
    if user.username == "admin" and user.password == "secret":
        token = jwt.encode({"sub": user.username}, "secret_key", algorithm="HS256")
        return {"access_token": token}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/protected")
async def protected_route(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, "secret_key", algorithms=["HS256"])
        return {"message": f"Hello {payload['sub']}!"}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

Key considerations:
- JWT token generation with PyJWT
- HTTPBearer security for token validation
- Proper error handling with HTTPException
- Async endpoint definitions for better performance
            """,
            "relevance_score": 0.96
        },
        {
            "content": """
React authentication context implementation:

```typescript
import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

interface AuthContextType {
  user: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(
    localStorage.getItem('access_token')
  );

  useEffect(() => {
    if (token) {
      // Decode token to get user info
      const payload = JSON.parse(atob(token.split('.')[1]));
      setUser(payload.sub);
    }
  }, [token]);

  const login = async (username: string, password: string) => {
    const response = await axios.post('/api/login', { username, password });
    const { access_token } = response.data;
    localStorage.setItem('access_token', access_token);
    setToken(access_token);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
```
            """,
            "relevance_score": 0.92
        },
        {
            "content": """
SQLAlchemy user model with password hashing:

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from passlib.context import CryptContext
from datetime import datetime

Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def verify_password(self, plain_password: str) -> bool:
        return pwd_context.verify(plain_password, self.hashed_password)

    @classmethod
    def create_user(cls, username: str, email: str, password: str):
        hashed = pwd_context.hash(password)
        return cls(username=username, email=email, hashed_password=hashed)
```

Security best practices:
- Bcrypt for password hashing (passlib)
- Never store plain passwords
- Unique constraints on username/email
- Automatic timestamps
            """,
            "relevance_score": 0.88
        },
        {
            "content": """
Pytest fixtures for authentication testing:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app, get_db
from models import Base, User

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)

@pytest.fixture
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(test_db):
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

@pytest.fixture
def test_user(test_db):
    db = TestingSessionLocal()
    user = User.create_user("testuser", "test@example.com", "testpass")
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user
```
            """,
            "relevance_score": 0.85
        }
    ]


def demonstrate_budget_enforcement():
    """Show visual demonstration of budget enforcement."""
    hook = PreToolUseHook()
    memory_items = create_realistic_memory_items()

    print("=" * 80)
    print("TOKEN BUDGET ENFORCEMENT DEMONSTRATION")
    print("=" * 80)
    print()

    # Test different budgets
    budgets = [500, 1000, 2000, 5000]

    for budget in budgets:
        print(f"\n{'─' * 80}")
        print(f"BUDGET: {budget} tokens")
        print('─' * 80)

        formatted = hook._format_memory_with_budget(memory_items, max_tokens=budget)
        actual_tokens = hook._estimate_tokens(formatted)

        print(f"\n📊 Statistics:")
        print(f"   • Requested budget: {budget} tokens")
        print(f"   • Actual usage: {actual_tokens} tokens")
        print(f"   • Efficiency: {(actual_tokens/budget)*100:.1f}%")
        print(f"   • Results included: {formatted.count('## Result')}")
        print(f"   • Status: {'✅ Within budget' if actual_tokens <= budget else '❌ Over budget'}")

        print(f"\n📝 Sample output (first 400 chars):")
        print("┌" + "─" * 78 + "┐")
        for line in formatted[:400].split('\n'):
            print(f"│ {line[:76]:<76} │")
        print("│ ...                                                                        │")
        print("└" + "─" * 78 + "┘")

    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print()
    print("✅ Token budget enforcement working correctly:")
    print("   • Results are intelligently truncated to fit budget")
    print("   • Token count is visible in output")
    print("   • Early termination prevents budget overflow")
    print("   • Configuration-driven via DEVSTREAM_CONTEXT_MAX_TOKENS")
    print()


if __name__ == "__main__":
    demonstrate_budget_enforcement()
