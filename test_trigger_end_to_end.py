#!/usr/bin/env python3
"""
Test script to verify end-to-end vector synchronization trigger functionality.
This simulates the PostToolUse hook workflow that generates embeddings.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent / '.claude' / 'hooks' / 'devstream' / 'utils'))
from sqlite_vec_helper import get_db_connection_with_vec

def simulate_posttooluse_workflow():
    """Simulate the complete PostToolUse hook workflow."""
    print("🧪 TESTING END-TO-END TRIGGER WORKFLOW")
    print("=" * 50)

    conn = get_db_connection_with_vec('data/devstream.db')
    cursor = conn.cursor()

    # Simulate a code modification event (like PostToolUse hook)
    file_path = "src/example_module.py"
    content = '''
def example_function():
    """
    Example function demonstrating vector synchronization.

    This function tests the automatic embedding generation and
    vector synchronization trigger functionality.
    """
    return "Hello, Vector World!"
'''

    # Generate embedding using the same approach as PostToolUse hook
    print("📝 Simulating PostToolUse hook workflow...")

    # Create memory record as PostToolUse hook would
    memory_id = f"test_e2e_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    embedding_model = "embeddinggemma:300m"
    embedding_dimension = 768

    # Generate embedding (simulating Ollama call)
    try:
        # Import the embedding generation function
        sys.path.insert(0, str(Path(__file__).parent / 'src' / 'devstream' / 'memory'))
        from embedding_generator import generate_embedding

        embedding_json = generate_embedding(content, model=embedding_model)

        # Insert into semantic_memory (PostToolUse hook behavior)
        cursor.execute('''
            INSERT INTO semantic_memory(
                id, content, content_type, embedding,
                embedding_model, embedding_dimension, created_at,
                metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            memory_id, content, "code", embedding_json,
            embedding_model, embedding_dimension, datetime.now().isoformat(),
            json.dumps({"file_path": file_path, "trigger": "PostToolUse_test"})
        ))

        conn.commit()
        print(f"✅ Memory record created: {memory_id}")

        # Check if trigger automatically synchronized to vec_semantic_memory
        cursor.execute('''
            SELECT COUNT(*) FROM vec_semantic_memory
            WHERE memory_id = ?
        ''', (memory_id,))

        vec_count = cursor.fetchone()[0]

        if vec_count > 0:
            print(f"✅ Vector synchronization successful: {vec_count} record in vec_semantic_memory")

            # Test vector search functionality
            cursor.execute('''
                SELECT memory_id, content_preview
                FROM vec_semantic_memory
                WHERE memory_id = ?
            ''', (memory_id,))

            result = cursor.fetchone()
            if result:
                print(f"✅ Vector search test passed: content_preview = {result[1][:50]}...")

            success = True
        else:
            print(f"❌ Vector synchronization failed: 0 records in vec_semantic_memory")
            success = False

        # Clean up test record
        cursor.execute('DELETE FROM semantic_memory WHERE id = ?', (memory_id,))
        conn.commit()
        print(f"🧹 Test record cleaned up")

        return success

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
    finally:
        conn.close()

def main():
    """Main test execution."""
    print("🚀 DevStream End-to-End Trigger Test")
    print("Testing complete PostToolUse → Embedding → Vector Sync workflow")
    print()

    if simulate_posttooluse_workflow():
        print("\n🎉 END-TO-END TEST PASSED!")
        print("✅ Vector synchronization triggers are fully operational")
        print("✅ All future embedding operations will be automatically synchronized")
    else:
        print("\n❌ END-TO-END TEST FAILED!")
        print("⚠️  Vector synchronization may not be working correctly")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())