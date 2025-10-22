import aiohttp
import sqlalchemy
import numpy as np
from typing import Optional

# Test file designed to trigger Context7 Direct Client with libraries that should use Direct Client in 50% rollout

async def test_aiohttp_connection_pooling():
    """Test aiohttp with connection pooling configuration that should trigger Direct Client."""
    connector = aiohttp.TCPConnector(
        limit=30,                    # Total connections
        limit_per_host=10,          # Per-host connections
        keepalive_timeout=15,       # Keep-alive timeout
        enable_cleanup_closed=True  # Cleanup on close
    )

    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            async with session.get('https://httpbin.org/get') as response:
                data = await response.json()
                return data
        except Exception as e:
            return {"error": str(e)}

def test_sqlalchemy_database_setup():
    """Test SQLAlchemy database setup that should trigger Direct Client."""
    from sqlalchemy import create_engine, Column, Integer, String, Text
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker

    Base = declarative_base()

    class Document(Base):
        __tablename__ = 'documents'
        id = Column(Integer, primary_key=True)
        title = Column(String(200))
        content = Column(Text)
        embedding = Column(String(100))

    # In-memory SQLite for testing
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    return {"engine": str(engine), "session_created": True}

def test_numpy_array_operations():
    """Test NumPy array operations that should trigger Direct Client."""
    # Create arrays for vector embeddings (similar to what Context7 might use)
    query_vector = np.random.rand(512)
    document_vectors = np.random.rand(1000, 512)

    # Calculate cosine similarities
    similarities = np.dot(document_vectors, query_vector)
    top_indices = np.argsort(similarities)[-5:][::-1]

    return {
        "query_vector_shape": query_vector.shape,
        "document_vectors_shape": document_vectors.shape,
        "top_matches": top_indices.tolist(),
        "similarities": similarities[top_indices].tolist()
    }

async def main():
    """Run all tests to trigger Context7 Direct Client."""
    print("Testing Context7 Direct Client with libraries that should use Direct Client...")

    # Test aiohttp
    print("1. Testing aiohttp...")
    result1 = await test_aiohttp_connection_pooling()
    print(f"   Result: {result1}")

    # Test SQLAlchemy
    print("2. Testing SQLAlchemy...")
    result2 = test_sqlalchemy_database_setup()
    print(f"   Result: {result2}")

    # Test NumPy
    print("3. Testing NumPy...")
    result3 = test_numpy_array_operations()
    print(f"   Result: {result3}")

    return {
        "aiohttp": result1,
        "sqlalchemy": result2,
        "numpy": result3
    }

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())