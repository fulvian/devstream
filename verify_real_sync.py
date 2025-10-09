#!/usr/bin/env python3
"""
Verifica reale della sincronizzazione degli embedding esistenti
nell'indice specializzato vec_semantic_memory.
"""

import sys
from pathlib import Path

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent / '.claude' / 'hooks' / 'devstream' / 'utils'))
from sqlite_vec_helper import get_db_connection_with_vec

def verify_real_synchronization():
    """Verifica se il trigger sincronizza davvero gli embedding esistenti."""
    print('🔍 VERIFICA REALE: SINCRONIZZAZIONE EMBEDDING ESISTENTI')
    print('=' * 55)

    conn = get_db_connection_with_vec('data/devstream.db')
    cursor = conn.cursor()

    # 1. Trova record con embedding che non sono in vec_semantic_memory
    cursor.execute('''
        SELECT s.id, s.content_type, LENGTH(s.embedding) as embed_length
        FROM semantic_memory s
        LEFT JOIN vec_semantic_memory v ON s.id = v.memory_id
        WHERE s.embedding IS NOT NULL AND s.embedding != ''
          AND v.memory_id IS NULL
        LIMIT 5
    ''')

    missing_records = cursor.fetchall()

    print(f'📊 Record con embedding non sincronizzati: {len(missing_records)} di 5 mostrati')

    if not missing_records:
        print('✅ Tutti gli embedding sono già sincronizzati!')
        return True
    else:
        for i, (record_id, content_type, embed_length) in enumerate(missing_records, 1):
            print(f'{i}. ID: {record_id} | Tipo: {content_type} | Embedding: {embed_length} bytes')

            # Forza la sincronizzazione aggiornando il record
            print(f'   🔄 Aggiornando record {record_id}...')

            # Aggiorna solo il timestamp per attivare il trigger
            cursor.execute('''
                UPDATE semantic_memory
                SET updated_at = datetime('now')
                WHERE id = ?
            ''', (record_id,))

            # Verifica se il trigger ha sincronizzato
            cursor.execute('''
                SELECT COUNT(*) FROM vec_semantic_memory
                WHERE memory_id = ?
            ''', (record_id,))

            sync_count = cursor.fetchone()[0]

            if sync_count > 0:
                print(f'   ✅ SUCCESS: Record sincronizzato nell indice vettoriale')
            else:
                print(f'   ❌ FALLITO: Record non sincronizzato')

            print()

    # 2. Report finale
    cursor.execute('SELECT COUNT(*) FROM semantic_memory WHERE embedding IS NOT NULL AND embedding != ""')
    total_with_embedding = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM vec_semantic_memory')
    total_in_vec_index = cursor.fetchone()[0]

    sync_percentage = (total_in_vec_index / total_with_embedding * 100) if total_with_embedding > 0 else 0

    print(f'📈 REPORT FINALE DI SINCRONIZZAZIONE:')
    print(f'   Totali con embedding: {total_with_embedding:,}')
    print(f'   Nell indice vettoriale: {total_in_vec_index:,}')
    print(f'   Percentuale sincronizzata: {sync_percentage:.1f}%')

    conn.close()
    return sync_percentage > 90  # Success if >90% synchronized

if __name__ == "__main__":
    success = verify_real_synchronization()
    if success:
        print("\n🎉 VERIFICA SUPERATA!")
        print("✅ Il sistema di sincronizzazione funziona correttamente")
    else:
        print("\n⚠️  VERIFICA PARZIALE!")
        print("❌ Il sistema potrebbe necessitare di sincronizzazione manuale")