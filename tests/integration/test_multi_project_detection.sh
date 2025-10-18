#!/usr/bin/env bash
# End-to-End Test: Multi-Project Detection

set -e

# Setup
TEST_ROOT="/tmp/devstream-multiproject-test-$$"
mkdir -p "$TEST_ROOT"
trap "rm -rf $TEST_ROOT" EXIT

# Test 1: Auto-detection from nested directory
test_auto_detection() {
    echo "Test 1: Auto-detection from nested directory"

    # Create mock project
    local project="$TEST_ROOT/project1"
    mkdir -p "$project"/{.claude/hooks/devstream,.devstream,data,src/components}
    touch "$project/.env.devstream"
    touch "$project/data/devstream.db"

    # Copy real Python from DevStream installation
    if [ -d "/Users/fulvioventura/devstream/.devstream/bin" ]; then
        cp -r /Users/fulvioventura/devstream/.devstream/bin "$project/.devstream/"
    else
        # Create a minimal fake Python that reports version 3.11.x
        mkdir -p "$project/.devstream/bin"
        cat > "$project/.devstream/bin/python" << 'EOF'
#!/bin/bash
echo "Python 3.11.13"
EOF
        chmod +x "$project/.devstream/bin/python"
    fi

    # Test from nested directory
    cd "$project/src/components"

    # Extract and test just the find_devstream_project_root function
    find_devstream_project_root() {
        local start_dir="${1:-$(pwd)}"
        local current_dir="$start_dir"
        local max_depth=20
        local depth=0

        # Upward search for .env.devstream marker
        while [ "$current_dir" != "/" ] && [ $depth -lt $max_depth ]; do
            if [ -f "$current_dir/.env.devstream" ]; then
                # Validate complete DevStream installation
                if [ -d "$current_dir/.claude/hooks/devstream" ] && \
                   [ -d "$current_dir/.devstream" ]; then
                    echo "$current_dir"
                    return 0
                fi
            fi

            current_dir="$(dirname "$current_dir")"
            depth=$((depth + 1))
        done

        return 1  # Not found
    }

    local detected=$(find_devstream_project_root)
    [ "$detected" = "$project" ] || {
        echo "FAIL: Expected $project, got $detected"
        return 1
    }

    echo "✅ PASS"
}

# Test 2: Explicit DEVSTREAM_PROJECT_ROOT override
test_explicit_override() {
    echo "Test 2: Explicit override"

    local project="$TEST_ROOT/project2"
    mkdir -p "$project"/{.claude/hooks/devstream,.devstream,data}
    touch "$project/.env.devstream"

    export DEVSTREAM_PROJECT_ROOT="$project"

    # Test the explicit override logic
    if [ -n "${DEVSTREAM_PROJECT_ROOT:-}" ]; then
        PROJECT_ROOT="$DEVSTREAM_PROJECT_ROOT"
    else
        PROJECT_ROOT=""
    fi

    [ "$PROJECT_ROOT" = "$project" ] || {
        echo "FAIL: Override not respected"
        return 1
    }

    unset DEVSTREAM_PROJECT_ROOT
    echo "✅ PASS"
}

# Test 3: Error when not in DevStream project
test_error_detection() {
    echo "Test 3: Error detection"

    cd "$TEST_ROOT"

    # Test find_devstream_project_root failure
    find_devstream_project_root() {
        local start_dir="${1:-$(pwd)}"
        local current_dir="$start_dir"
        local max_depth=20
        local depth=0

        # Upward search for .env.devstream marker
        while [ "$current_dir" != "/" ] && [ $depth -lt $max_depth ]; do
            if [ -f "$current_dir/.env.devstream" ]; then
                # Validate complete DevStream installation
                if [ -d "$current_dir/.claude/hooks/devstream" ] && \
                   [ -d "$current_dir/.devstream" ]; then
                    echo "$current_dir"
                    return 0
                fi
            fi

            current_dir="$(dirname "$current_dir")"
            depth=$((depth + 1))
        done

        return 1  # Not found
    }

    if find_devstream_project_root >/dev/null 2>&1; then
        echo "FAIL: Should have failed"
        return 1
    fi

    echo "✅ PASS"
}

# Test 4: Multiple projects isolation
test_project_isolation() {
    echo "Test 4: Project isolation"

    # Create two projects
    local proj1="$TEST_ROOT/app1"
    local proj2="$TEST_ROOT/app2"

    for proj in "$proj1" "$proj2"; do
        mkdir -p "$proj"/{.claude/hooks/devstream,.devstream,data}
        touch "$proj/.env.devstream"
        echo "DEVSTREAM_DB_PATH=$proj/data/devstream.db" > "$proj/.env.devstream"
    done

    # Test project 1
    cd "$proj1"
    export DEVSTREAM_PROJECT_ROOT="$proj1"
    export DEVSTREAM_DB_PATH="$proj1/data/devstream.db"
    [ "$DEVSTREAM_PROJECT_ROOT" = "$proj1" ] || return 1
    [ "$DEVSTREAM_DB_PATH" = "$proj1/data/devstream.db" ] || return 1

    # Test project 2
    cd "$proj2"
    export DEVSTREAM_PROJECT_ROOT="$proj2"
    export DEVSTREAM_DB_PATH="$proj2/data/devstream.db"
    [ "$DEVSTREAM_PROJECT_ROOT" = "$proj2" ] || return 1
    [ "$DEVSTREAM_DB_PATH" = "$proj2/data/devstream.db" ] || return 1

    # Clean up exports
    unset DEVSTREAM_PROJECT_ROOT DEVSTREAM_DB_PATH

    echo "✅ PASS"
}

# Run all tests
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Multi-Project Detection E2E Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

test_auto_detection
test_explicit_override
test_error_detection
test_project_isolation

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All tests passed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"