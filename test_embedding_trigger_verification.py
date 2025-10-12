#!/usr/bin/env python3
"""
Test Embedding Trigger Verification
Verifica se i trigger SQLite funzionano correttamente quando si inserisce un embedding
"""

import sqlite3
import json
import requests
from datetime import datetime

DB_PATH = './data/devstream.db'
OLLAMA_URL = 'http://localhost:11434/api/embed'

def test_embedding_storage():
    """Test completo della pipeline di embedding storage"""
    print('🧪 Testing Embedding Storage Pipeline\n')

    # 1. Genera embedding via Ollama
    print('1️⃣ Generating embedding with Ollama...')
    response = requests.post(OLLAMA_URL, json={
        'model': 'embeddinggemma:300m',
        'input': 'Test embedding storage verification'
    })
    embedding = response.json()['embeddings'][0]
    print(f'✅ Generated embedding: {len(embedding)} dimensions\n')

    # 2. Connect to database and load vec0 extension
    conn = sqlite3.connect(DB_PATH)
    conn.enable_load_extension(True)
    conn.load_extension('./sqlite-extensions/vec0')
    cursor = conn.cursor()
    print('✅ Loaded vec0 extension\n')

    # 3. Inserisci record con embedding
    test_id = f'test-{int(datetime.now().timestamp() * 1000)}'
    embedding_json = json.dumps(embedding)

    print('2️⃣ Inserting test record with embedding...')
    cursor.execute('''
        INSERT INTO semantic_memory (
            id, content, content_type, keywords,
            embedding, embedding_dimension, embedding_model,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    ''', (
        test_id,
        'Test embedding storage verification',
        'test',
        'test,embedding,storage',
        embedding_json,
        len(embedding),
        'embeddinggemma:300m'
    ))
    conn.commit()
    print(f'✅ Inserted record with id: {test_id}\n')

    # 4. Verifica embedding in semantic_memory
    print('3️⃣ Checking semantic_memory table...')
    cursor.execute('''
        SELECT id, content_type,
               CASE WHEN embedding IS NULL THEN 'NULL'
                    WHEN embedding = '' THEN 'EMPTY'
                    ELSE 'HAS_DATA'
               END as embedding_status,
               length(embedding) as embedding_length,
               embedding_dimension
        FROM semantic_memory
        WHERE id = ?
    ''', (test_id,))
    semantic_record = cursor.fetchone()
    print(f'📊 semantic_memory record:')
    print(f'   id: {semantic_record[0]}')
    print(f'   content_type: {semantic_record[1]}')
    print(f'   embedding_status: {semantic_record[2]}')
    print(f'   embedding_length: {semantic_record[3]}')
    print(f'   embedding_dimension: {semantic_record[4]}\n')

    # 5. Verifica trigger activation in vec_semantic_memory
    print('4️⃣ Checking vec_semantic_memory table (trigger activation)...')
    cursor.execute('''
        SELECT memory_id, content_type,
               length(content_preview) as preview_length,
               vec_length(embedding) as vec_dimensions
        FROM vec_semantic_memory
        WHERE memory_id = ?
    ''', (test_id,))
    vec_record = cursor.fetchone()

    if vec_record:
        print(f'✅ Trigger activated! vec_semantic_memory record:')
        print(f'   memory_id: {vec_record[0]}')
        print(f'   content_type: {vec_record[1]}')
        print(f'   preview_length: {vec_record[2]}')
        print(f'   vec_dimensions: {vec_record[3]}\n')
    else:
        print(f'❌ Trigger NOT activated - no record in vec_semantic_memory\n')

    # 6. Re-check semantic_memory after trigger
    print('5️⃣ Re-checking semantic_memory after trigger (should be NULL)...')
    cursor.execute('''
        SELECT id,
               CASE WHEN embedding IS NULL THEN 'NULL'
                    WHEN embedding = '' THEN 'EMPTY'
                    ELSE 'STILL_HAS_DATA'
               END as embedding_status
        FROM semantic_memory
        WHERE id = ?
    ''', (test_id,))
    cleaned_record = cursor.fetchone()
    print(f'📊 semantic_memory embedding after trigger:')
    print(f'   id: {cleaned_record[0]}')
    print(f'   embedding_status: {cleaned_record[1]}\n')

    # 7. Cleanup
    print('6️⃣ Cleaning up test records...')
    cursor.execute('DELETE FROM semantic_memory WHERE id = ?', (test_id,))
    cursor.execute('DELETE FROM vec_semantic_memory WHERE memory_id = ?', (test_id,))
    conn.commit()
    print(f'✅ Test records cleaned up\n')

    # 8. Results
    print('═' * 50)
    print('📊 TEST RESULTS')
    print('═' * 50)
    print(f'Embedding Generated: {len(embedding)} dimensions')
    print(f'Saved to semantic_memory: {semantic_record[2]}')
    print(f'Trigger Activated: {"YES ✅" if vec_record else "NO ❌"}')
    print(f'Embedding Cleaned: {"YES ✅" if cleaned_record[1] == "NULL" else "NO ❌"}')
    print('═' * 50)

    conn.close()

if __name__ == '__main__':
    test_embedding_storage()
