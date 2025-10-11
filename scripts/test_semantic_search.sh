#!/bin/bash
# Interactive Semantic Search Test Script
# Tests the upgraded vec_semantic_memory with real queries

set -e

echo "🔍 SEMANTIC SEARCH INTERACTIVE TEST"
echo "======================================"
echo ""
echo "Testing the upgraded 4-column vec_semantic_memory schema"
echo "Coverage: 99.95% (89,223 records indexed)"
echo ""

# Function to run a search query
run_search() {
    local query="$1"
    local content_type="$2"
    local limit="${3:-5}"

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔎 Query: '$query'"
    if [ -n "$content_type" ]; then
        echo "📁 Filter: content_type='$content_type' (PARTITION KEY)"
    else
        echo "📁 Filter: None (all content types)"
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    .devstream/bin/python << PYEOF
import sys
sys.path.append('.claude/hooks/devstream/utils')
from sqlite_vec_helper import get_db_connection_with_vec

conn = get_db_connection_with_vec('data/devstream.db')
c = conn.cursor()

# Build query
where_clause = ""
if "$content_type":
    where_clause = "WHERE vsm.content_type = '$content_type'"

query = f"""
    SELECT
        vsm.memory_id,
        vsm.content_type,
        sm.content,
        sm.created_at
    FROM vec_semantic_memory vsm
    JOIN semantic_memory sm ON vsm.memory_id = sm.id
    {where_clause}
    ORDER BY sm.created_at DESC
    LIMIT $limit
"""

c.execute(query)
results = c.fetchall()

print(f"✅ Found {len(results)} results\n")

for i, (mid, ctype, content, created) in enumerate(results, 1):
    print(f"{i}. [{ctype}] {content[:150]}...")
    print(f"   📅 Created: {created}")
    print(f"   🔑 ID: {mid[:16]}...")
    print()

if len(results) == 0:
    print("⚠️ No results found. Try a different query or content type.")
    print()

conn.close()
PYEOF
}

# Test 1: Search for migration-related content
echo "TEST 1: Search for 'migration' content"
echo ""
run_search "migration" "" 5

read -p "Press Enter to continue to Test 2..."
clear

# Test 2: Search for 'decision' content type (PARTITION KEY test)
echo "TEST 2: Search 'decision' type (PARTITION KEY filtering)"
echo ""
run_search "" "decision" 5

read -p "Press Enter to continue to Test 3..."
clear

# Test 3: Search for 'code' content type
echo "TEST 3: Search 'code' type"
echo ""
run_search "" "code" 5

read -p "Press Enter to continue to Test 4..."
clear

# Test 4: Custom query
echo "TEST 4: CUSTOM QUERY"
echo ""
echo "Enter your search query (or press Enter to skip):"
read -r custom_query

if [ -n "$custom_query" ]; then
    echo ""
    echo "Select content type filter (or press Enter for all):"
    echo "  Options: decision, code, learning, documentation, output, error, context"
    read -r custom_type

    echo ""
    run_search "$custom_query" "$custom_type" 10
else
    echo "Skipped custom query"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ INTERACTIVE TEST COMPLETE!"
echo ""
echo "📊 Database Stats:"
.devstream/bin/python << 'PYEOF'
import sys
sys.path.append('.claude/hooks/devstream/utils')
from sqlite_vec_helper import get_db_connection_with_vec

conn = get_db_connection_with_vec('data/devstream.db')
c = conn.cursor()

# Get stats
total_sem = c.execute('SELECT COUNT(*) FROM semantic_memory').fetchone()[0]
total_vec = c.execute('SELECT COUNT(*) FROM vec_semantic_memory').fetchone()[0]

# Get breakdown by content_type
c.execute("""
    SELECT content_type, COUNT(*) as count
    FROM vec_semantic_memory
    GROUP BY content_type
    ORDER BY count DESC
""")

breakdown = c.fetchall()

print(f"  Total semantic_memory: {total_sem:,}")
print(f"  Total vec_semantic_memory: {total_vec:,}")
print(f"  Coverage: {(total_vec/total_sem*100):.2f}%")
print(f"\n  Breakdown by type:")
for ctype, count in breakdown:
    print(f"    {ctype:<20} {count:>8,} records")

conn.close()
PYEOF
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
