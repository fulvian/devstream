#!/usr/bin/env python3
"""
Test completo del sistema di sincronizzazione in tempo reale.
Simula il flusso completo: INSERT → embedding generation → trigger sync.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent / '.claude' / 'hooks' / 'devstream' / 'utils'))
from sqlite_vec_helper import get_db_connection_with_vec

def test_realtime_synchronization():
    """Test completo del sistema di sincronizzazione in tempo reale."""
    print('🧪 TEST SISTEMA SINCRONIZZAZIONE TEMPO REALE')
    print('=' * 50)

    conn = get_db_connection_with_vec('data/devstream.db')
    cursor = conn.cursor()

    results = []

    # Test 1: Insert con embedding esistente
    print('\n📝 TEST 1: INSERT CON EMBEDDING ESISTENTE')
    test_id_1 = f'realtime_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}_1'
    test_content = '''
def realtime_test_function():
    """
    Test function for real-time vector synchronization.
    This should be automatically synchronized to vec_semantic_memory.
    """
    return "Real-time sync test successful!"
'''

    # Usa un embedding esistente dal database
    cursor.execute('SELECT embedding FROM semantic_memory WHERE embedding IS NOT NULL LIMIT 1')
    existing_embedding = cursor.fetchone()[0]

    start_time = time.time()
    cursor.execute('''
        INSERT INTO semantic_memory(
            id, content, content_type, embedding,
            embedding_model, embedding_dimension, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        test_id_1, test_content, 'code', existing_embedding,
        'embeddinggemma:300m', 768, datetime.now().isoformat()
    ))
    conn.commit()
    insert_time = time.time() - start_time

    # Verifica sincronizzazione immediata
    cursor.execute('SELECT COUNT(*) FROM vec_semantic_memory WHERE memory_id = ?', (test_id_1,))
    sync_count = cursor.fetchone()[0]

    result_1 = {
        'test': 'INSERT_CONTO_ESISTENTE',
        'success': sync_count > 0,
        'time_ms': insert_time * 1000,
        'sync_count': sync_count
    }

    print(f'   ⏱️  Tempo inserimento: {insert_time*1000:.2f}ms')
    print(f'   ✅ Sincronizzazione: {"SUCCESS" if sync_count > 0 else "FAILED"}')
    results.append(result_1)

    # Test 2: UPDATE di embedding
    print('\n🔄 TEST 2: UPDATE EMBEDDING')
    cursor.execute('SELECT embedding FROM semantic_memory WHERE embedding IS NOT NULL AND id != ? LIMIT 1', (test_id_1,))
    new_embedding = cursor.fetchone()[0]

    start_time = time.time()
    cursor.execute('''
        UPDATE semantic_memory
        SET embedding = ?, updated_at = ?
        WHERE id = ?
    ''', (new_embedding, datetime.now().isoformat(), test_id_1))
    conn.commit()
    update_time = time.time() - start_time

    # Verifica che l'aggiornamento sia sincronizzato
    cursor.execute('SELECT COUNT(*) FROM vec_semantic_memory WHERE memory_id = ?', (test_id_1,))
    update_sync_count = cursor.fetchone()[0]

    result_2 = {
        'test': 'UPDATE_EMBEDDING',
        'success': update_sync_count > 0,
        'time_ms': update_time * 1000,
        'sync_count': update_sync_count
    }

    print(f'   ⏱️  Tempo aggiornamento: {update_time*1000:.2f}ms')
    print(f'   ✅ Sincronizzazione: {"SUCCESS" if update_sync_count > 0 else "FAILED"}')
    results.append(result_2)

    # Test 3: DELETE operation
    print('\n🗑️  TEST 3: DELETE OPERATION')
    start_time = time.time()
    cursor.execute('DELETE FROM semantic_memory WHERE id = ?', (test_id_1,))
    conn.commit()
    delete_time = time.time() - start_time

    # Verifica cleanup automatico
    cursor.execute('SELECT COUNT(*) FROM vec_semantic_memory WHERE memory_id = ?', (test_id_1,))
    cleanup_count = cursor.fetchone()[0]

    result_3 = {
        'test': 'DELETE_CLEANUP',
        'success': cleanup_count == 0,
        'time_ms': delete_time * 1000,
        'sync_count': cleanup_count
    }

    print(f'   ⏱️  Tempo cancellazione: {delete_time*1000:.2f}ms')
    print(f'   ✅ Cleanup: {"SUCCESS" if cleanup_count == 0 else "FAILED"}')
    results.append(result_3)

    # Test 4: Batch insert (simula PostToolUse multiplo)
    print('\n📦 TEST 4: BATCH INSERT (simula PostToolUse multiplo)')
    batch_size = 5
    batch_ids = []
    batch_start = time.time()

    for i in range(batch_size):
        test_id = f'batch_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}_{i}'
        batch_ids.append(test_id)

        batch_content = f'''
def batch_test_function_{i}():
    \"\"\"Batch test function {i} for real-time sync.\"\"\"
    return "Batch sync test {i} successful!"
'''

        cursor.execute('''
            INSERT INTO semantic_memory(
                id, content, content_type, embedding,
                embedding_model, embedding_dimension, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            test_id, batch_content, 'code', existing_embedding,
            'embeddinggemma:300m', 768, datetime.now().isoformat()
        ))

    conn.commit()
    batch_time = time.time() - batch_start

    # Verifica sincronizzazione batch
    placeholders = ','.join(['?'] * len(batch_ids))
    cursor.execute(f'''
        SELECT COUNT(*) FROM vec_semantic_memory
        WHERE memory_id IN ({placeholders})
    ''', batch_ids)

    batch_sync_count = cursor.fetchone()[0]

    result_4 = {
        'test': 'BATCH_INSERT',
        'success': batch_sync_count == batch_size,
        'time_ms': batch_time * 1000,
        'sync_count': batch_sync_count,
        'expected': batch_size
    }

    print(f'   ⏱️  Tempo batch ({batch_size} records): {batch_time*1000:.2f}ms')
    print(f'   ⏱️  Tempo medio per record: {(batch_time*1000)/batch_size:.2f}ms')
    print(f'   ✅ Sincronizzazione: {"SUCCESS" if batch_sync_count == batch_size else f"PARTIAL ({batch_sync_count}/{batch_size})"}')
    results.append(result_4)

    # Cleanup batch test records
    placeholders = ','.join(['?'] * len(batch_ids))
    cursor.execute(f'DELETE FROM semantic_memory WHERE id IN ({placeholders})', batch_ids)
    conn.commit()

    # Report finale
    print('\n📊 REPORT FINALE TEST TEMPO REALE:')
    print('=' * 50)

    success_count = sum(1 for r in results if r['success'])
    total_tests = len(results)
    overall_success = success_count == total_tests

    avg_time = sum(r['time_ms'] for r in results) / total_tests

    print(f'✅ Test superati: {success_count}/{total_tests}')
    print(f'⏱️  Tempo medio operazione: {avg_time:.2f}ms')
    print(f'🎯 Status complessivo: {"SUCCESS" if overall_success else "FAILED"}')

    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f'   {status} {result["test"]}: {result["time_ms"]:.2f}ms')

    # Performance check
    if avg_time < 50:  # Sotto 50ms per operazione
        perf_status = "🟢 ECCELLENTE"
    elif avg_time < 100:  # Sotto 100ms
        perf_status = "🟡 BUONO"
    else:
        perf_status = "🔴 LENTO"

    print(f'\n⚡ Performance: {perf_status}')

    conn.close()
    return overall_success and avg_time < 100

if __name__ == '__main__':
    success = test_realtime_synchronization()
    print(f'\n🎉 RISULTATO FINALE: {"SUCCESSO" if success else "FALLIMENTO"}')
    sys.exit(0 if success else 1)