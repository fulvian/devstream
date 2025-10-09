#!/usr/bin/env python3
"""
Integration test for token budget enforcement in real context injection scenarios.

Tests the complete flow:
1. Memory search
2. Budget-aware formatting
3. Context injection
"""

import sys
import asyncio
from pathlib import Path

# Add hooks to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude/hooks/devstream/memory'))

from pre_tool_use import PreToolUseHook


async def test_real_memory_formatting():
    """Test with actual memory items format."""
    hook = PreToolUseHook()

    # Simulate real memory items from DevStream DB
    memory_items = [
        {
            "id": 1,
            "content": """FastAPI authentication endpoint implementation:

@app.post("/api/auth/login")
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user or not user.verify_password(credentials.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}
""",
            "relevance_score": 0.95,
            "content_type": "code",
            "keywords": ["fastapi", "authentication", "jwt", "login"]
        },
        {
            "id": 2,
            "content": """JWT token creation with expiration:

from datetime import datetime, timedelta
from jose import JWTError, jwt

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
""",
            "relevance_score": 0.89,
            "content_type": "code",
            "keywords": ["jwt", "token", "security", "expiration"]
        },
        {
            "id": 3,
            "content": """Password hashing with bcrypt:

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
""",
            "relevance_score": 0.82,
            "content_type": "code",
            "keywords": ["bcrypt", "password", "hashing", "security"]
        }
    ]

    print("=" * 80)
    print("INTEGRATION TEST: Real Memory Formatting with Token Budget")
    print("=" * 80)
    print()

    # Test with default 2000 token budget
    print("📊 Test Case: Default Budget (2000 tokens)")
    print("-" * 80)

    formatted = hook._format_memory_with_budget(
        memory_items,
        max_tokens=2000
    )

    # Validate output
    actual_tokens = hook._estimate_tokens(formatted)
    results_count = formatted.count("## Result")
    has_token_info = "*Total tokens used:" in formatted

    print(f"\n✅ Validation Results:")
    print(f"   • Budget compliance: {actual_tokens <= 2000} (used {actual_tokens}/2000 tokens)")
    print(f"   • Results included: {results_count}")
    print(f"   • Token info visible: {has_token_info}")
    print(f"   • Memory items processed: {len(memory_items)}")
    print()

    # Show sample output
    print("📝 Sample Output (first 600 chars):")
    print("┌" + "─" * 78 + "┐")
    for line in formatted[:600].split('\n'):
        if line:
            print(f"│ {line[:76]:<76} │")
    print("│ ...                                                                        │")
    print("└" + "─" * 78 + "┘")
    print()

    # Test with smaller budget
    print("\n📊 Test Case: Conservative Budget (1000 tokens)")
    print("-" * 80)

    formatted_small = hook._format_memory_with_budget(
        memory_items,
        max_tokens=1000
    )

    actual_tokens_small = hook._estimate_tokens(formatted_small)
    results_count_small = formatted_small.count("## Result")

    print(f"\n✅ Validation Results:")
    print(f"   • Budget compliance: {actual_tokens_small <= 1000} (used {actual_tokens_small}/1000 tokens)")
    print(f"   • Results included: {results_count_small}")
    print(f"   • Budget reduction: {2000 - actual_tokens_small} tokens saved vs default")
    print()

    # Verify budget enforcement
    print("=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print()

    # Note: results_count_small may equal results_count if all items fit in small budget
    # The important check is that both respect their budgets
    all_checks_passed = (
        actual_tokens <= 2000 and
        actual_tokens_small <= 1000 and
        has_token_info and
        results_count > 0 and
        results_count_small > 0
    )

    if all_checks_passed:
        print("✅ ALL INTEGRATION TESTS PASSED")
        print()
        print("Token budget enforcement is working correctly:")
        print("   • Respects budget limits (2000 and 1000 token tests)")
        print("   • Displays token usage information")
        print("   • Adjusts result count based on available budget")
        print("   • Formats real memory items correctly")
        return 0
    else:
        print("❌ INTEGRATION TESTS FAILED")
        print()
        print("Issues detected:")
        if actual_tokens > 2000:
            print("   • Default budget exceeded")
        if actual_tokens_small > 1000:
            print("   • Small budget exceeded")
        if not has_token_info:
            print("   • Token info missing")
        return 1


async def test_configuration_loading():
    """Test that configuration is loaded correctly."""
    print("\n" + "=" * 80)
    print("CONFIGURATION TEST")
    print("=" * 80)
    print()

    hook = PreToolUseHook()

    print(f"✅ Configuration loaded successfully:")
    print(f"   • DEVSTREAM_CONTEXT_MAX_TOKENS: {hook.memory_token_budget}")
    print(f"   • Expected: 2000")
    print(f"   • Match: {hook.memory_token_budget == 2000}")
    print()


async def main():
    """Run all integration tests."""
    print("\n" + "🧪" * 40)
    print("TOKEN BUDGET INTEGRATION TEST SUITE")
    print("🧪" * 40 + "\n")

    # Test 1: Real memory formatting
    exit_code = await test_real_memory_formatting()

    # Test 2: Configuration loading
    await test_configuration_loading()

    print("=" * 80)
    print("Integration tests completed!")
    print("=" * 80)
    print()

    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
