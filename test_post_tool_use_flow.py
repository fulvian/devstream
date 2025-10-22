#!/usr/bin/env .devstream/bin/python
"""
Test completo del flusso PostToolUse per identificare perché gli embedding non vengono generati.
"""

import sys
import asyncio
import json
from pathlib import Path

# Add path per import
sys.path.insert(0, str(Path('.claude/hooks/devstream/memory')))
sys.path.insert(0, str(Path('.claude/hooks/devstream/utils')))

from cchooks import PostToolUseContext
from post_tool_use import PostToolUseHook

async def test_post_tool_use_flow():
    """Test completo del flusso PostToolUse con un Write operation."""

    print("🧪 TEST COMPLETO POSTTOOLUSE FLOW")
    print("=" * 60)

    # 1. Inizializza hook
    hook = PostToolUseHook()
    print("✅ Hook inizializzato")

    # 2. Simula un PostToolUseContext per Write operation
    from unittest.mock import MagicMock
    mock_context = MagicMock()
    mock_context.tool_name = "Write"
    mock_context.tool_input = {
        "file_path": "/tmp/test_embedding_file.py",
        "content": '''#!/usr/bin/env python3
"""
Test file per embedding generation.
Questa è una funzione di test per verificare che il sistema di embedding funzioni correttamente.
"""

def test_function():
    """Funzione di test."""
    return "embedding test"

class TestClass:
    """Classe di test."""

    def method(self):
        return "test method"
'''
    }
    mock_context.tool_response = {"success": True}
    mock_context.output = MagicMock()

    print("✅ Mock context creato")
    print(f"   Tool: {mock_context.tool_name}")
    print(f"   File: {mock_context.tool_input['file_path']}")
    print(f"   Content length: {len(mock_context.tool_input['content'])} chars")

    # 3. Test should_capture logic
    file_path = mock_context.tool_input["file_path"]
    content = mock_context.tool_input["content"]

    # Test exclude paths
    excluded_paths = [".git/", "node_modules/", ".venv/", ".devstream/", "__pycache__/"]
    should_exclude = any(excluded in file_path for excluded in excluded_paths)
    print(f"   Path exclusion: {should_exclude}")

    # Test content classification
    content_type = hook.classify_content_type(
        mock_context.tool_name,
        mock_context.tool_response,
        content
    )
    print(f"   Content type: {content_type}")

    # Test topics extraction
    topics = hook.extract_topics(content, file_path)
    print(f"   Topics: {topics}")

    # Test entities extraction
    entities = hook.extract_entities(content)
    print(f"   Entities: {entities}")

    # 4. Esegui il processo completo
    print("\n🔄 ESECUZIONE COMPLETA HOOK...")
    try:
        await hook.process(mock_context)
        print("✅ Hook process completato")
    except Exception as e:
        print(f"❌ Errore durante process: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 5. Verifica se il memory storage è abilitato
    memory_enabled = hook.base.is_memory_store_enabled()
    print(f"   Memory store enabled: {memory_enabled}")

    # 6. Verifica se hook dovrebbe runnare
    should_run = hook.base.should_run()
    print(f"   Should run: {should_run}")

    print("\n📊 RISULTATI TEST:")
    print(f"   Memory enabled: {memory_enabled}")
    print(f"   Should run: {should_run}")
    print(f"   Path excluded: {should_exclude}")

    return memory_enabled and should_run and not should_exclude

async def test_manual_embedding_flow():
    """Test del flusso di embedding manuale per confronto."""

    print("\n🧪 TEST MANUALE EMBEDDING FLOW")
    print("=" * 60)

    hook = PostToolUseHook()

    # Test diretto store_in_memory
    test_content = """# Test File for Embedding

This is a test file to verify embedding generation works correctly.

## Function Definitions

```python
def test_function():
    return "test"
```

## Class Definitions

```python
class TestClass:
    def method(self):
        return "method"
```
"""

    try:
        memory_id = await hook.store_in_memory(
            file_path="/tmp/test_manual_embedding.py",
            content=test_content,
            operation="Write",
            topics=["python", "testing"],
            entities=["pytest"],
            content_type="code"
        )

        if memory_id:
            print(f"✅ Memory storage successful: {memory_id[:8]}...")
            return True
        else:
            print("❌ Memory storage failed")
            return False

    except Exception as e:
        print(f"❌ Manual embedding test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test execution."""

    print("🔍 DIAGNOSI COMPLETA EMBEDDING SYSTEM")
    print("=" * 60)

    # Test 1: Flusso completo
    test1_result = await test_post_tool_use_flow()

    # Test 2: Flusso manuale
    test2_result = await test_manual_embedding_flow()

    print("\n📋 RIEPILOGO RISULTATI:")
    print("=" * 60)
    print(f"Test 1 (PostToolUse flow): {'✅ PASS' if test1_result else '❌ FAIL'}")
    print(f"Test 2 (Manual flow): {'✅ PASS' if test2_result else '❌ FAIL'}")

    if not test1_result and test2_result:
        print("\n🔍 DIAGNOSI: Il sistema di embedding funziona, ma il flusso PostToolUse ha problemi.")
        print("   Possibili cause:")
        print("   1. Configurazione hook disabilitata")
        print("   2. Memory store disabilitato")
        print("   3. Filtro percorsi che esclude i file")
        print("   4. Problemi nel flusso di esecuzione dell'hook")
    elif test1_result and test2_result:
        print("\n✅ Entrambi i test passati - il sistema funziona correttamente")
    else:
        print("\n❌ Entrambi i test falliti - problema fondamentale nel sistema")

if __name__ == "__main__":
    asyncio.run(main())