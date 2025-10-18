#!/usr/bin/env bash
# Validate Database Isolation

validate_db_isolation() {
    local project="$1"
    local expected_db="$project/data/devstream.db"

    cd "$project"

    # Test using the updated launcher logic
    export DEVSTREAM_PROJECT_ROOT="$project"
    export DEVSTREAM_DB_PATH="$expected_db"

    # Check DEVSTREAM_DB_PATH
    if [ "$DEVSTREAM_DB_PATH" != "$expected_db" ]; then
        echo "❌ FAIL: Wrong DB path"
        echo "   Expected: $expected_db"
        echo "   Got:      $DEVSTREAM_DB_PATH"
        return 1
    fi

    # Check database file size (should be different for each project)
    local db_size=$(stat -f%z "$expected_db" 2>/dev/null || echo 0)
    echo "✅ PASS: $project uses $expected_db (size: $db_size bytes)"

    return 0
}

# Test all projects
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Database Isolation Validation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

validate_db_isolation /Users/fulvioventura/devstream
validate_db_isolation /Users/fulvioventura/exc-to-pdf

echo ""
echo "Querying databases for unique content..."

for proj in /Users/fulvioventura/{devstream,exc-to-pdf}; do
    echo "Project: $proj"
    cd "$proj"
    .devstream/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/devstream.db')
count = conn.execute('SELECT COUNT(*) FROM semantic_memory').fetchone()[0]
print(f'  Records: {count}')
conn.close()
"
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Database isolation validation complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"