#!/bin/bash

# MCP Server Health Monitoring Script
#
# Monitors DevStream MCP Server health endpoints and provides status updates.
# Uses curl to query /health and /metrics endpoints with proper error handling.
#
# Usage: ./scripts/monitor-mcp.sh [options]
#   --host HOST    Health server host (default: localhost)
#   --port PORT    Health server port (default: 9090)
#   --interval N   Check interval in seconds (default: 30)
#   --once         Run once and exit (default: continuous monitoring)
#   --quiet        Suppress regular output, only show errors
#   --help         Show this help

set -euo pipefail

# Default configuration
HOST="localhost"
PORT="9090"
INTERVAL="30"
ONCE_ONLY=false
QUIET=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        --once)
            ONCE_ONLY=true
            shift
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        --help)
            cat << EOF
MCP Server Health Monitoring Script

Usage: $0 [options]

Options:
  --host HOST    Health server host (default: localhost)
  --port PORT    Health server port (default: 9090)
  --interval N   Check interval in seconds (default: 30)
  --once         Run once and exit (default: continuous monitoring)
  --quiet        Suppress regular output, only show errors
  --help         Show this help

Examples:
  $0                           # Monitor localhost:9090 every 30s
  $0 --port 9091 --interval 10 # Monitor port 9091 every 10s
  $0 --once                    # Run single health check
  $0 --quiet                   # Only show errors

EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Use --help for usage information" >&2
            exit 1
            ;;
    esac
done

# Base URL for health endpoints
BASE_URL="http://${HOST}:${PORT}"

# Function to get current timestamp
get_timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# Function to check health endpoint
check_health() {
    local timestamp
    timestamp=$(get_timestamp)

    # Check if server is responding
    if ! curl_output=$(curl -s --max-time 5 --connect-timeout 3 "${BASE_URL}/health" 2>/dev/null); then
        echo -e "${RED}[${timestamp}] ❌ ERROR: Health server not responding at ${BASE_URL}${NC}" >&2
        return 1
    fi

    # Parse health status
    if ! status=$(echo "${curl_output}" | jq -r '.status' 2>/dev/null); then
        echo -e "${RED}[${timestamp}] ❌ ERROR: Invalid JSON response from health endpoint${NC}" >&2
        echo -e "${RED}Response: ${curl_output}${NC}" >&2
        return 1
    fi

    # Get additional details
    local uptime database_status ollama_status
    uptime=$(echo "${curl_output}" | jq -r '.uptime // "unknown"' 2>/dev/null || echo "unknown")
    database_status=$(echo "${curl_output}" | jq -r '.components.database.status // "unknown"' 2>/dev/null || echo "unknown")
    ollama_status=$(echo "${curl_output}" | jq -r '.components.ollama.status // "unknown"' 2>/dev/null || echo "unknown")

    # Format uptime nicely
    local uptime_formatted
    if [[ "${uptime}" != "unknown" && "${uptime}" =~ ^[0-9]+$ ]]; then
        uptime_formatted="$(printf '%dd %02dh %02dm %02ds' $((uptime/86400)) $((uptime%86400/3600)) $((uptime%3600/60)) $((uptime%60)))"
    else
        uptime_formatted="${uptime}"
    fi

    # Display status based on health condition
    case "${status}" in
        "healthy")
            if [[ "${QUIET}" != "true" ]]; then
                echo -e "${GREEN}[${timestamp}] ✅ HEALTHY${NC}"
                echo -e "   Status: ${status}"
                echo -e "   Uptime: ${uptime_formatted}"
                echo -e "   Database: ${database_status}"
                echo -e "   Ollama: ${ollama_status}"
                echo
            fi
            ;;
        "degraded")
            echo -e "${YELLOW}[${timestamp}] ⚠️  DEGRADED${NC}"
            echo -e "   Status: ${status}"
            echo -e "   Uptime: ${uptime_formatted}"
            echo -e "   Database: ${database_status}"
            echo -e "   Ollama: ${ollama_status}"
            echo
            ;;
        "unhealthy")
            echo -e "${RED}[${timestamp}] ❌ UNHEALTHY${NC}"
            echo -e "   Status: ${status}"
            echo -e "   Uptime: ${uptime_formatted}"
            echo -e "   Database: ${database_status}"
            echo -e "   Ollama: ${ollama_status}"
            echo
            ;;
        *)
            echo -e "${RED}[${timestamp}] ❌ UNKNOWN STATUS: ${status}${NC}"
            echo -e "   Full response: ${curl_output}"
            echo
            return 1
            ;;
    esac

    return 0
}

# Function to check metrics endpoint
check_metrics() {
    local timestamp
    timestamp=$(get_timestamp)

    # Check metrics endpoint
    if ! curl_output=$(curl -s --max-time 5 --connect-timeout 3 "${BASE_URL}/metrics" 2>/dev/null); then
        if [[ "${QUIET}" != "true" ]]; then
            echo -e "${YELLOW}[${timestamp}] ⚠️  WARNING: Metrics endpoint not available${NC}"
        fi
        return 1
    fi

    # Extract key metrics (basic parsing, not full Prometheus parsing)
    local process_uptime heap_used
    process_uptime=$(echo "${curl_output}" | grep '^devstream_process_uptime_seconds' | tail -1 | cut -d' ' -f2 || echo "N/A")
    heap_used=$(echo "${curl_output}" | grep '^devstream_heap_used_bytes' | tail -1 | cut -d' ' -f2 || echo "N/A")

    if [[ "${QUIET}" != "true" ]]; then
        echo -e "${BLUE}[${timestamp}] 📊 METRICS SNAPSHOT${NC}"
        if [[ "${process_uptime}" != "N/A" ]]; then
            local uptime_formatted
            uptime_formatted="$(printf '%dd %02dh %02dm %02ds' ${process_uptime%.*} 0 0 0 | sed 's/00d //; s/00h //; s/00m //')"
            echo -e "   Process Uptime: ${uptime_formatted}"
        fi
        if [[ "${heap_used}" != "N/A" ]]; then
            local heap_mb
            heap_mb=$(echo "scale=1; ${heap_used} / 1024 / 1024" | bc -l 2>/dev/null || echo "N/A")
            echo -e "   Heap Memory: ${heap_mb} MB"
        fi
        echo
    fi

    return 0
}

# Function to check if jq is available
check_dependencies() {
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}❌ ERROR: jq is required for JSON parsing but not found in PATH${NC}" >&2
        echo -e "${RED}Install jq with: brew install jq (macOS) or apt-get install jq (Linux)${NC}" >&2
        exit 1
    fi

    if ! command -v curl &> /dev/null; then
        echo -e "${RED}❌ ERROR: curl is required but not found in PATH${NC}" >&2
        exit 1
    fi
}

# Main monitoring loop
main() {
    # Check dependencies
    check_dependencies

    echo -e "${BLUE}🔍 MCP Server Health Monitor${NC}"
    echo -e "   Target: ${BASE_URL}"
    echo -e "   Interval: ${INTERVAL}s"
    if [[ "${ONCE_ONLY}" == "true" ]]; then
        echo -e "   Mode: Single check"
    else
        echo -e "   Mode: Continuous monitoring (Ctrl+C to stop)"
    fi
    echo

    # Trap SIGINT and SIGTERM for graceful shutdown
    trap 'echo -e "\n${YELLOW}📋 Monitoring stopped by user${NC}"; exit 0' INT TERM

    if [[ "${ONCE_ONLY}" == "true" ]]; then
        # Single check mode
        check_health
        check_metrics
    else
        # Continuous monitoring mode
        while true; do
            check_health
            check_metrics
            sleep "${INTERVAL}"
        done
    fi
}

# Run main function
main "$@"