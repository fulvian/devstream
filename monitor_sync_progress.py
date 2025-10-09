#!/usr/bin/env python3
"""
Monitor del progresso della sincronizzazione in background.
"""

import sys
import time
from pathlib import Path

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent / '.claude' / 'hooks' / 'devstream' / 'utils'))
from sqlite_vec_helper import get_db_connection_with_vec

def monitor_sync_progress(interval=30, max_checks=10):
    """Monitora il progresso della sincronizzazione."""
    print('🔍 MONITOR SINCRONIZZAZIONE BACKGROUND')
    print('=' * 40)

    conn = get_db_connection_with_vec('data/devstream.db')
    cursor = conn.cursor()

    # Ottieni stato iniziale
    cursor.execute('SELECT COUNT(*) FROM semantic_memory WHERE embedding IS NOT NULL AND embedding != ""')
    total_emb = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM vec_semantic_memory')
    initial_vec = cursor.fetchone()[0]

    print(f'📊 Stato iniziale: {initial_vec:,}/{total_emb:,} ({initial_vec/total_emb*100:.1f}%)')

    for check in range(1, max_checks + 1):
        time.sleep(interval)

        cursor.execute('SELECT COUNT(*) FROM vec_semantic_memory')
        current_vec = cursor.fetchone()[0]

        progress = (current_vec / total_emb * 100) if total_emb > 0 else 0
        increase = current_vec - initial_vec
        rate = increase / (check * interval) if check > 0 else 0

        remaining = total_emb - current_vec
        eta_minutes = (remaining / rate / 60) if rate > 0 else float('inf')

        print(f'\\n📈 Check {check}: {current_vec:,}/{total_emb:,} ({progress:.1f}%)')
        print(f'   Aumento: +{increase:,} | Rate: {rate:.1f}/sec | ETA: {eta_minutes:.1f} min')

        if progress >= 95:
            print(f'\\n✅ QUASI COMPLETATO! {progress:.1f}% raggiunto')
            break
        elif progress >= 90:
            print(f'\\n🎉 OTTIMO PROGRESSO! {progress:.1f}% raggiunto')
        elif check == max_checks:
            print(f'\\n⏰ Monitoraggio terminato dopo {max_checks * interval} secondi')

    conn.close()

if __name__ == '__main__':
    monitor_sync_progress()