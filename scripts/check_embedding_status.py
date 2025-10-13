#!/usr/bin/env python3
import sys
sys.path.append('.claude/hooks/devstream/utils')
from sqlite_vec_helper import get_db_connection_with_vec

conn = get_db_connection_with_vec('data/devstream.db')
c = conn.cursor()

total_sem = c.execute('SELECT COUNT(*) FROM semantic_memory').fetchone()[0]
total_vec = c.execute('SELECT COUNT(*) FROM vec_semantic_memory').fetchone()[0]
with_json = c.execute("SELECT COUNT(*) FROM semantic_memory WHERE embedding IS NOT NULL AND embedding != ''").fetchone()[0]

print(f"semantic_memory: {total_sem:,}")
print(f"vec_semantic_memory: {total_vec:,}")
print(f"with_json_embedding: {with_json:,}")
print(f"")
print(f"Missing from vec: {total_sem - total_vec:,}")
print(f"Coverage: {(total_vec/total_sem*100):.2f}%")

conn.close()
