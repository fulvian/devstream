#!/usr/bin/env python3
"""
Verifica completa dello stato del database: presenza embedding e indicizzazione.
"""

import sys
from pathlib import Path

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent / '.claude' / 'hooks' / 'devstream' / 'utils'))
from sqlite_vec_helper import get_db_connection_with_vec

def verify_complete_database():
    """Verifica completa di tutti i records nel database."""
    print('📊 VERIFICA COMPLETA RECORDS DATABASE')
    print('=' * 40)

    conn = get_db_connection_with_vec('data/devstream.db')
    cursor = conn.cursor()

    # Statistiche generali database
    cursor.execute('SELECT COUNT(*) FROM semantic_memory')
    total_records = cursor.fetchone()[0]

    print(f'🗃️  STATISTICHE GENERALI DATABASE:')
    print(f'   Totali record semantic_memory: {total_records:,}')

    # Verifica dettagliata embedding
    cursor.execute('''
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN embedding IS NULL OR embedding = '' THEN 1 END) as missing_embeddings,
            COUNT(CASE WHEN embedding IS NOT NULL AND embedding != '' THEN 1 END) as has_embeddings,
            COUNT(CASE WHEN embedding_model IS NOT NULL THEN 1 END) as has_model_info
        FROM semantic_memory
    ''')

    stats = cursor.fetchone()
    total, missing, has_embeddings, has_model_info = stats

    embedding_percentage = (has_embeddings / total * 100) if total > 0 else 0

    print(f'\n📈 STATISTICHE EMBEDDING:')
    print(f'   Con embedding: {has_embeddings:,} ({embedding_percentage:.1f}%)')
    print(f'   Senza embedding: {missing:,}')
    print(f'   Con info modello: {has_model_info:,}')

    # Verifica indice vettoriale
    cursor.execute('SELECT COUNT(*) FROM vec_semantic_memory')
    vec_count = cursor.fetchone()[0]

    sync_percentage = (vec_count / has_embeddings * 100) if has_embeddings > 0 else 0

    print(f'\n🎯 INDICE VETTORIALE:')
    print(f'   Record in vec_semantic_memory: {vec_count:,}')
    print(f'   Percentuale sincronizzata: {sync_percentage:.1f}%')

    # Analisi per content type
    cursor.execute('''
        SELECT
            s.content_type,
            COUNT(*) as total_type,
            COUNT(CASE WHEN s.embedding IS NOT NULL AND s.embedding != '' THEN 1 END) as with_embedding_type,
            COUNT(CASE WHEN v.memory_id IS NOT NULL THEN 1 END) as indexed_type
        FROM semantic_memory s
        LEFT JOIN vec_semantic_memory v ON s.id = v.memory_id
        GROUP BY s.content_type
        ORDER BY total_type DESC
    ''')

    type_stats = cursor.fetchall()

    print(f'\n📋 ANALISI PER CONTENT TYPE:')
    for content_type, total_type, with_emb_type, indexed_type in type_stats:
        emb_perc = (with_emb_type / total_type * 100) if total_type > 0 else 0
        idx_perc = (indexed_type / with_emb_type * 100) if with_emb_type > 0 else 0
        print(f'   {content_type:12} | Total: {total_type:6,} | Embed: {with_emb_type:5,} ({emb_perc:5.1f}%) | Index: {indexed_type:5,} ({idx_perc:5.1f}%)')

    # Identifica problemi specifici
    print(f'\n🔍 ANALISI DETTAGLIATA:')

    # 1. Records senza embedding
    if missing > 0:
        print(f'   ⚠️  {missing:,} records senza embedding da generare')

        cursor.execute('''
            SELECT content_type, COUNT(*)
            FROM semantic_memory
            WHERE embedding IS NULL OR embedding = ''
            GROUP BY content_type
            ORDER BY COUNT(*) DESC
        ''')
        missing_by_type = cursor.fetchall()
        for ct, count in missing_by_type:
            print(f'      - {ct}: {count:,} records')
    else:
        print(f'   ✅ Tutti i records hanno embedding')

    # 2. Records con embedding non sincronizzati
    not_synced = has_embeddings - vec_count
    if not_synced > 0:
        print(f'   ⚠️  {not_synced:,} records con embedding non sincronizzati')
        print(f'      - Eseguire: python scripts/sync_existing_embeddings.py')
    else:
        print(f'   ✅ Tutti gli embedding sono sincronizzati')

    # Riepilogo stati
    if embedding_percentage >= 95 and sync_percentage >= 90:
        status = '✅ ECCELLENTE'
        color = '🟢'
        recommendation = 'Sistema completo e funzionante'
    elif embedding_percentage >= 85 and sync_percentage >= 75:
        status = '✅ BUONO'
        color = '🟡'
        recommendation = 'Completare sincronizzazione manuale'
    else:
        status = '⚠️  MIGLIORABILE'
        color = '🔴'
        recommendation = 'Generare embedding mancanti e sincronizzare'

    print(f'\n{color} RIEPILOGO STATO: {status}')
    print(f'   Embedding coverage: {embedding_percentage:.1f}%')
    print(f'   Indice sincronizzato: {sync_percentage:.1f}%')
    print(f'   Raccomandazione: {recommendation}')

    conn.close()

    return {
        'total_records': total,
        'has_embeddings': has_embeddings,
        'embedding_percentage': embedding_percentage,
        'vec_count': vec_count,
        'sync_percentage': sync_percentage,
        'missing_embeddings': missing,
        'not_synced': not_synced
    }

if __name__ == '__main__':
    results = verify_complete_database()