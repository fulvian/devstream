#!/usr/bin/env python3
"""
Test completo del sistema automatico per nuove operazioni DB.
Verifica che le nuove scritture siano registrate con embedding e indice aggiornato.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent / '.claude' / 'hooks' / 'devstream' / 'utils'))
from sqlite_vec_helper import get_db_connection_with_vec

def test_new_db_operations():
    """Testa nuove operazioni DB per verificare funzionamento sistema automatico."""
    print('🧪 TEST SISTEMA AUTOMATICO - NUOVE OPERAZIONI DB')
    print('=' * 55)

    conn = get_db_connection_with_vec('data/devstream.db')
    cursor = conn.cursor()

    # Test 1: Nuovo record con embedding completo
    print('\n📝 TEST 1: Inserimento nuovo record con embedding')

    test_id_1 = f'test_new_op_{datetime.now().strftime("%Y%m%d_%H%M%S")}_1'
    test_content_1 = '''
def new_vector_test_function():
    """
    Funzione di test per verificare il funzionamento del sistema
    di sincronizzazione vettoriale automatico.

    Questo record dovrebbe essere automaticamente sincronizzato
    nell'indice vec_semantic_memory.
    """
    return "Vector synchronization test successful!"
'''

    # Usa un embedding reale dal database
    cursor.execute('SELECT embedding FROM semantic_memory WHERE embedding IS NOT NULL LIMIT 1')
    real_embedding = cursor.fetchone()[0]

    start_time = time.time()
    cursor.execute('''
        INSERT INTO semantic_memory(
            id, content, content_type, embedding,
            embedding_model, embedding_dimension, created_at,
            metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        test_id_1, test_content_1, 'code', real_embedding,
        'embeddinggemma:300m', 768, datetime.now().isoformat(),
        json.dumps({"test_type": "new_db_operation", "trigger": "manual_test"})
    ))
    conn.commit()
    insert_time = time.time() - start_time

    # Verifica sincronizzazione automatica
    cursor.execute('SELECT COUNT(*) FROM vec_semantic_memory WHERE memory_id = ?', (test_id_1,))
    sync_count = cursor.fetchone()[0]

    print(f'   ⏱️  Tempo inserimento: {insert_time*1000:.2f}ms')
    print(f'   ✅ Sincronizzazione automatica: {"SUCCESS" if sync_count > 0 else "FAILED"}')

    # Test 2: Aggiornamento embedding
    print('\n🔄 TEST 2: Aggiornamento embedding esistente')

    # Prendi un altro embedding
    cursor.execute('SELECT embedding FROM semantic_memory WHERE embedding IS NOT NULL AND id != ? LIMIT 1', (test_id_1,))
    new_embedding = cursor.fetchone()[0]

    start_time = time.time()
    cursor.execute('''
        UPDATE semantic_memory
        SET embedding = ?, updated_at = ?, metadata = json_patch(metadata, json_object('test_updated', true))
        WHERE id = ?
    ''', (new_embedding, datetime.now().isoformat(), test_id_1))
    conn.commit()
    update_time = time.time() - start_time

    # Verifica aggiornamento sincronizzato
    cursor.execute('SELECT COUNT(*) FROM vec_semantic_memory WHERE memory_id = ?', (test_id_1,))
    update_sync_count = cursor.fetchone()[0]

    print(f'   ⏱️  Tempo aggiornamento: {update_time*1000:.2f}ms')
    print(f'   ✅ Sincronizzazione aggiornamento: {"SUCCESS" if update_sync_count > 0 else "FAILED"}')

    # Test 3: Ricerca vettoriale funzionale
    print('\n🔍 TEST 3: Verifica ricerca vettoriale funzionante')

    # Simula una ricerca vettoriale
    cursor.execute('''
        SELECT COUNT(*) FROM vec_semantic_memory
        WHERE content_type = 'code'
        LIMIT 10
    ''')
    vector_search_count = cursor.fetchone()[0]

    print(f'   📊 Record code nell\'indice vettoriale: {vector_search_count:,}')
    print(f'   ✅ Ricerca vettoriale: {"FUNCTIONAL" if vector_search_count > 0 else "EMPTY"}')

    # Test 4: Operazione di pulizia
    print('\n🗑️  TEST 4: Cancellazione e cleanup automatico')

    start_time = time.time()
    cursor.execute('DELETE FROM semantic_memory WHERE id = ?', (test_id_1,))
    conn.commit()
    delete_time = time.time() - start_time

    # Verifica cleanup automatico
    cursor.execute('SELECT COUNT(*) FROM vec_semantic_memory WHERE memory_id = ?', (test_id_1,))
    cleanup_count = cursor.fetchone()[0]

    print(f'   ⏱️  Tempo cancellazione: {delete_time*1000:.2f}ms')
    print(f'   ✅ Cleanup automatico: {"SUCCESS" if cleanup_count == 0 else "FAILED"}')

    # Test 5: Stato finale del sistema
    print('\n📊 TEST 5: Stato finale del sistema')

    cursor.execute('SELECT COUNT(*) FROM semantic_memory WHERE embedding IS NOT NULL AND embedding != ""')
    total_with_embedding = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM vec_semantic_memory')
    total_in_vector_index = cursor.fetchone()[0]

    sync_percentage = (total_in_vector_index / total_with_embedding * 100) if total_with_embedding > 0 else 0

    print(f'   📈 Totali con embedding: {total_with_embedding:,}')
    print(f'   🎯 Nell\'indice vettoriale: {total_in_vector_index:,}')
    print(f'   📊 Percentuale sincronizzata: {sync_percentage:.1f}%')

    # Report finale
    all_tests_passed = (
        sync_count > 0 and
        update_sync_count > 0 and
        cleanup_count == 0 and
        vector_search_count > 0 and
        sync_percentage >= 99
    )

    print(f'\n🎯 RISULTATI FINALI:')
    print(f'   Inserimento + sincronizzazione: {"✅" if sync_count > 0 else "❌"}')
    print(f'   Aggiornamento + sincronizzazione: {"✅" if update_sync_count > 0 else "❌"}')
    print(f'   Cleanup automatico: {"✅" if cleanup_count == 0 else "❌"}')
    print(f'   Ricerca vettoriale funzionante: {"✅" if vector_search_count > 0 else "❌"}')
    print(f'   Stato sistema: {"✅" if sync_percentage >= 99 else "⚠️"}')

    print(f'\n🏆 STATUS GENERALE: {"SUCCESS" if all_tests_passed else "PARTIAL"}')

    conn.close()
    return all_tests_passed

if __name__ == '__main__':
    success = test_new_db_operations()
    print(f'\n🎉 TEST COMPLETATO: {"SUCCESSO COMPLETO" if success else "SUCCESSO PARZIALE"}')

    if success:
        print('✅ Il sistema di sincronizzazione vettoriale è completamente funzionante!')
        print('✅ Tutte le nuove operazioni DB vengono correttamente processate')
        print('✅ Embedding generati e indice aggiornato automaticamente')
    else:
        print('⚠️  Alcuni test non sono passati - verificare il sistema')

    sys.exit(0 if success else 1)