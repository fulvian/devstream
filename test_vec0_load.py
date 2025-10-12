#!/usr/bin/env python3
"""Test vec0 extension loading"""

import sqlite3

print('Testing vec0 extension loading...')

try:
    conn = sqlite3.connect('./data/devstream.db')
    print('✅ Connected to database')

    conn.enable_load_extension(True)
    print('✅ Enabled extension loading')

    conn.load_extension('./sqlite-extensions/vec0')
    print('✅ Loaded vec0 extension')

    cursor = conn.cursor()
    cursor.execute("SELECT vec_version()")
    version = cursor.fetchone()[0]
    print(f'✅ vec0 version: {version}')

    conn.close()
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
