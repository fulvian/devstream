#!/bin/bash

# MCP Server Performance Load Testing Script
#
# Performs load testing on MCP server health endpoints to validate
# performance characteristics and stability under concurrent load.
#
# Usage: ./scripts/load-test-mcp.sh [options]
#   --concurrent N  Number of concurrent requests (default: 10)
#   --duration N    Test duration in seconds (default: 60)
#   --host HOST     Health server host (default: localhost)
#   --port PORT     Health server port (default: 9090)
#   --endpoint EP   Endpoint to test (default: health)
#   --output DIR    Output directory for results (default: ./load-test-results)
#   --help          Show this help

set -euo pipefail

# Default configuration
CONCURRENT_REQUESTS=10
TEST_DURATION=60
HOST="localhost"
PORT="9090"
ENDPOINT="health"
OUTPUT_DIR="./load-test-results"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --concurrent)
            CONCURRENT_REQUESTS="$2"
            shift 2
            ;;
        --duration)
            TEST_DURATION="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --endpoint)
            ENDPOINT="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --help)
            cat << EOF
MCP Server Performance Load Testing Script

Usage: $0 [options]

Options:
  --concurrent N  Number of concurrent requests (default: 10)
  --duration N    Test duration in seconds (default: 60)
  --host HOST     Health server host (default: localhost)
  --port PORT     Health server port (default: 9090)
  --endpoint EP   Endpoint to test (health|metrics|both) (default: health)
  --output DIR    Output directory for results (default: ./load-test-results)
  --help          Show this help

Examples:
  $0                                    # Basic load test (10 concurrent, 60s)
  $0 --concurrent 50 --duration 120    # Heavy load test (50 concurrent, 2min)
  $0 --endpoint both                   # Test both health and metrics endpoints
  $0 --host 192.168.1.100 --port 9090 # Test remote server

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

# Test configuration
BASE_URL="http://${HOST}:${PORT}"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
RESULT_DIR="${OUTPUT_DIR}/load-test-${TIMESTAMP}"

# Function to log messages
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $1${NC}"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  $1${NC}"
}

log_info() {
    echo -e "${CYAN}[$(date '+%Y-%m-%d %H:%M:%S')] ℹ️  $1${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    # Check if curl is available
    if ! command -v curl &> /dev/null; then
        log_error "curl is required but not found"
        exit 1
    fi

    # Check if bc is available (for calculations)
    if ! command -v bc &> /dev/null; then
        log_error "bc is required for calculations but not found"
        exit 1
    fi

    # Check if jq is available (for JSON parsing)
    if ! command -v jq &> /dev/null; then
        log_warning "jq is not available, some JSON parsing features will be limited"
    fi

    log_success "Prerequisites check completed"
}

# Function to create result directory
setup_result_directory() {
    mkdir -p "$RESULT_DIR"

    # Create test metadata
    cat > "$RESULT_DIR/test-config.json" << EOF
{
  "test_timestamp": "$(date -Iseconds)",
  "test_duration_seconds": $TEST_DURATION,
  "concurrent_requests": $CONCURRENT_REQUESTS,
  "target_url": "$BASE_URL",
  "endpoint": "$ENDPOINT",
  "hostname": "$(hostname)",
  "system_info": {
    "platform": "$(uname -s)",
    "architecture": "$(uname -m)",
    "node_version": "$(node --version 2>/dev/null || echo 'N/A')"
  }
}
EOF

    log "Results will be saved to: $RESULT_DIR"
}

# Function to test server connectivity
test_connectivity() {
    log "Testing server connectivity..."

    if ! curl -s --max-time 5 --connect-timeout 3 "${BASE_URL}/health" > /dev/null; then
        log_error "Cannot connect to server at $BASE_URL"
        log_error "Make sure the MCP server is running and the health endpoint is accessible"
        exit 1
    fi

    log_success "Server connectivity verified"
}

# Function to generate random delay
random_delay() {
    local max_delay=${1:-0.1}
    local delay
    delay=$(echo "scale=3; $RANDOM / 32767 * $max_delay" | bc -l)
    sleep "$delay"
}

# Function to perform single request
perform_request() {
    local endpoint="$1"
    local request_id="$2"
    local result_file="$3"

    local start_time end_time duration status_code response_size error_msg

    start_time=$(date +%s.%N)

    # Perform request with timeout
    if response=$(curl -s --max-time 10 --connect-timeout 5 -w "%{http_code}|%{size_download}" "${BASE_URL}/${endpoint}" 2>/dev/null); then
        end_time=$(date +%s.%N)

        # Parse response
        status_code=$(echo "$response" | tail -c 100 | grep -o '[0-9]*$' | tail -1)
        response_size=$(echo "$response" | tail -c 100 | grep -o '[0-9]*' | tail -1)

        # Extract actual response (remove status info)
        response_body=$(echo "$response" | sed 's/|[0-9]*|[0-9]*$//')

        duration=$(echo "$end_time - $start_time" | bc -l)

        # Parse response time from body if JSON and available
        if [[ "$endpoint" == "health" ]] && command -v jq &> /dev/null; then
            local uptime=$(echo "$response_body" | jq -r '.uptime // 0' 2>/dev/null || echo "0")
            echo "{\"request_id\":$request_id,\"endpoint\":\"$endpoint\",\"status_code\":$status_code,\"duration\":$duration,\"response_size\":$response_size,\"uptime\":$uptime,\"success\":true,\"timestamp\":\"$(date -Iseconds)\"}" >> "$result_file"
        else
            echo "{\"request_id\":$request_id,\"endpoint\":\"$endpoint\",\"status_code\":$status_code,\"duration\":$duration,\"response_size\":$response_size,\"success\":true,\"timestamp\":\"$(date -Iseconds)\"}" >> "$result_file"
        fi
    else
        end_time=$(date +%s.%N)
        duration=$(echo "$end_time - $start_time" | bc -l)
        echo "{\"request_id\":$request_id,\"endpoint\":\"$endpoint\",\"status_code\":0,\"duration\":$duration,\"response_size\":0,\"success\":false,\"error\":\"connection_failed\",\"timestamp\":\"$(date -Iseconds)\"}" >> "$result_file"
    fi
}

# Function to run concurrent load test
run_load_test() {
    local endpoint="$1"
    local test_file="$RESULT_DIR/${endpoint}-requests.jsonl"
    local pids=()

    log "Starting load test for /$endpoint endpoint..."
    log_info "Concurrent requests: $CONCURRENT_REQUESTS"
    log_info "Test duration: ${TEST_DURATION}s"
    log_info "Request log: $test_file"

    # Initialize request counter
    local request_counter=1

    # Calculate test end time
    local end_time
    end_time=$(($(date +%s) + TEST_DURATION))

    # Start concurrent workers
    for ((i=1; i<=CONCURRENT_REQUESTS; i++)); do
        (
            while [[ $(date +%s) -lt $end_time ]]; do
                perform_request "$endpoint" "$request_counter" "$test_file"
                request_counter=$((request_counter + 1))
                random_delay 0.05  # Small random delay to simulate real traffic
            done
        ) &
        pids+=($!)
    done

    # Monitor progress
    log "Load test in progress... (Press Ctrl+C to stop early)"

    local start_time=$(date +%s)
    while [[ $(date +%s) -lt $end_time ]]; do
        local elapsed=$(($(date +%s) - start_time))
        local remaining=$((TEST_DURATION - elapsed))

        # Count completed requests
        local completed=0
        if [[ -f "$test_file" ]]; then
            completed=$(wc -l < "$test_file" 2>/dev/null || echo "0")
        fi

        log_info "Progress: ${elapsed}s/${TEST_DURATION}s | Requests: $completed | Workers: ${#pids[@]}"
        sleep 5
    done

    # Wait for all workers to complete
    log "Waiting for workers to complete..."
    for pid in "${pids[@]}"; do
        wait "$pid" 2>/dev/null || true
    done

    log_success "Load test for /$endpoint endpoint completed"
}

# Function to generate performance report
generate_performance_report() {
    local endpoint="$1"
    local request_file="$RESULT_DIR/${endpoint}-requests.jsonl"
    local report_file="$RESULT_DIR/${endpoint}-performance-report.json"

    if [[ ! -f "$request_file" ]] || [[ ! -s "$request_file" ]]; then
        log_error "No request data found for $endpoint endpoint"
        return 1
    fi

    log "Generating performance report for /$endpoint endpoint..."

    # Calculate statistics using jq
    if command -v jq &> /dev/null; then
        local total_requests successful_requests failed_requests
        local avg_response_time min_response_time max_response_time
        local success_rate avg_response_size

        total_requests=$(wc -l < "$request_file")
        successful_requests=$(jq -r 'select(.success == true) | .request_id' "$request_file" | wc -l)
        failed_requests=$((total_requests - successful_requests))

        if [[ $successful_requests -gt 0 ]]; then
            avg_response_time=$(jq -r 'select(.success == true) | .duration' "$request_file" | awk '{sum+=$1; count++} END {print sum/count}')
            min_response_time=$(jq -r 'select(.success == true) | .duration' "$request_file" | sort -n | head -1)
            max_response_time=$(jq -r 'select(.success == true) | .duration' "$request_file" | sort -n | tail -1)
            avg_response_size=$(jq -r 'select(.success == true) | .response_size' "$request_file" | awk '{sum+=$1; count++} END {print sum/count}')
        else
            avg_response_time=0
            min_response_time=0
            max_response_time=0
            avg_response_size=0
        fi

        success_rate=$(echo "scale=2; $successful_requests * 100 / $total_requests" | bc -l)
        requests_per_second=$(echo "scale=2; $total_requests / $TEST_DURATION" | bc -l)

        # Generate JSON report
        cat > "$report_file" << EOF
{
  "endpoint": "/$endpoint",
  "test_duration_seconds": $TEST_DURATION,
  "total_requests": $total_requests,
  "successful_requests": $successful_requests,
  "failed_requests": $failed_requests,
  "success_rate_percent": $success_rate,
  "requests_per_second": $requests_per_second,
  "response_time": {
    "average_seconds": $avg_response_time,
    "minimum_seconds": $min_response_time,
    "maximum_seconds": $max_response_time
  },
  "response_size": {
    "average_bytes": $avg_response_size
  },
  "performance_grade": "$(calculate_grade "$success_rate" "$avg_response_time")"
}
EOF

        # Display summary
        log_info "Performance Summary for /$endpoint:"
        echo -e "  ${CYAN}Total Requests:${NC} $total_requests"
        echo -e "  ${CYAN}Success Rate:${NC} ${success_rate}%"
        echo -e "  ${CYAN}Requests/Second:${NC} $requests_per_second"
        echo -e "  ${CYAN}Avg Response Time:${NC} ${avg_response_time}s"
        echo -e "  ${CYAN}Min/Max Response Time:${NC} ${min_response_time}s / ${max_response_time}s"
        echo -e "  ${CYAN}Performance Grade:${NC} $(calculate_grade "$success_rate" "$avg_response_time")"
        echo

    else
        log_warning "jq not available, generating basic report"
        local total_requests
        total_requests=$(wc -l < "$request_file")

        cat > "$report_file" << EOF
{
  "endpoint": "/$endpoint",
  "total_requests": $total_requests,
  "requests_per_second": $(echo "scale=2; $total_requests / $TEST_DURATION" | bc -l),
  "note": "Detailed statistics require jq tool"
}
EOF
    fi

    log_success "Performance report saved: $report_file"
}

# Function to calculate performance grade
calculate_grade() {
    local success_rate="$1"
    local avg_response_time="$2"

    # Convert to integers for comparison
    local success_int=$(echo "$success_rate / 1" | bc)
    local response_int=$(echo "$avg_response_time * 1000" | bc)

    if [[ $success_int -ge 99 ]] && [[ $response_int -le 100 ]]; then
        echo "A+ (Excellent)"
    elif [[ $success_int -ge 95 ]] && [[ $response_int -le 200 ]]; then
        echo "A (Very Good)"
    elif [[ $success_int -ge 90 ]] && [[ $response_int -le 500 ]]; then
        echo "B (Good)"
    elif [[ $success_int -ge 80 ]] && [[ $response_int -le 1000 ]]; then
        echo "C (Fair)"
    elif [[ $success_int -ge 70 ]]; then
        echo "D (Poor)"
    else
        echo "F (Very Poor)"
    fi
}

# Function to generate combined report
generate_combined_report() {
    local combined_file="$RESULT_DIR/combined-performance-report.md"

    cat > "$combined_file" << EOF
# MCP Server Load Test Results

**Test Date:** $(date)
**Test Duration:** ${TEST_DURATION}s
**Concurrent Requests:** $CONCURRENT_REQUESTS
**Target Server:** $BASE_URL

## Test Configuration

- **Endpoint(s) Tested:** $ENDPOINT
- **Test Environment:** $(uname -s) $(uname -r)
- **Node.js Version:** $(node --version 2>/dev/null || echo 'N/A')

## Performance Summary

EOF

    # Add individual endpoint results
    if [[ "$ENDPOINT" == "health" ]] || [[ "$ENDPOINT" == "both" ]]; then
        if [[ -f "$RESULT_DIR/health-performance-report.json" ]]; then
            echo "### Health Endpoint (/health)" >> "$combined_file"
            jq -r '"- **Total Requests:** " + (.total_requests | tostring) + "\n' +
               '"- **Success Rate:** " + (.success_rate_percent | tostring) + "%\n' +
               '"- **Requests/Second:** " + (.requests_per_second | tostring) + "\n' +
               '"- **Avg Response Time:** " + (.response_time.average_seconds | tostring) + "s\n' +
               '"- **Performance Grade:** " + .performance_grade + "\n"' \
               "$RESULT_DIR/health-performance-report.json" >> "$combined_file"
            echo >> "$combined_file"
        fi
    fi

    if [[ "$ENDPOINT" == "metrics" ]] || [[ "$ENDPOINT" == "both" ]]; then
        if [[ -f "$RESULT_DIR/metrics-performance-report.json" ]]; then
            echo "### Metrics Endpoint (/metrics)" >> "$combined_file"
            jq -r '"- **Total Requests:** " + (.total_requests | tostring) + "\n' +
               '"- **Success Rate:** " + (.success_rate_percent | tostring) + "%\n' +
               '"- **Requests/Second:** " + (.requests_per_second | tostring) + "\n' +
               '"- **Avg Response Time:** " + (.response_time.average_seconds | tostring) + "s\n' +
               '"- **Performance Grade:** " + .performance_grade + "\n"' \
               "$RESULT_DIR/metrics-performance-report.json" >> "$combined_file"
            echo >> "$combined_file"
        fi
    fi

    cat >> "$combined_file" << EOF
## Files Generated

- \`test-config.json\` - Test configuration and system info
- \`*-requests.jsonl\` - Raw request logs (one JSON object per line)
- \`*-performance-report.json\` - Detailed performance statistics

## Recommendations

EOF

    # Add recommendations based on performance
    if [[ -f "$RESULT_DIR/health-performance-report.json" ]]; then
        local success_rate=$(jq -r '.success_rate_percent' "$RESULT_DIR/health-performance-report.json" 2>/dev/null || echo "0")
        local avg_response=$(jq -r '.response_time.average_seconds' "$RESULT_DIR/health-performance-report.json" 2>/dev/null || echo "999")

        if (( $(echo "$success_rate >= 95" | bc -l) )) && (( $(echo "$avg_response <= 0.1" | bc -l) )); then
            echo "✅ **Excellent Performance:** Server shows excellent stability and response times" >> "$combined_file"
        elif (( $(echo "$success_rate >= 90" | bc -l) )) && (( $(echo "$avg_response <= 0.5" | bc -l) )); then
            echo "✅ **Good Performance:** Server performs well under normal load" >> "$combined_file"
        else
            echo "⚠️ **Performance Concerns:** Consider investigating response times and error rates" >> "$combined_file"
        fi
    fi

    log_success "Combined report generated: $combined_file"
}

# Main execution
main() {
    echo -e "${BLUE}🚀 MCP Server Performance Load Testing${NC}"
    echo

    # Change to script directory to handle relative paths
    cd "$(dirname "${BASH_SOURCE[0]}")/.."

    # Run test phases
    check_prerequisites
    setup_result_directory
    test_connectivity

    # Determine which endpoints to test
    local endpoints=()
    case "$ENDPOINT" in
        "health")
            endpoints+=("health")
            ;;
        "metrics")
            endpoints+=("metrics")
            ;;
        "both")
            endpoints+=("health" "metrics")
            ;;
        *)
            log_error "Invalid endpoint: $ENDPOINT. Use 'health', 'metrics', or 'both'"
            exit 1
            ;;
    esac

    # Run load tests for each endpoint
    for endpoint in "${endpoints[@]}"; do
        run_load_test "$endpoint"
        generate_performance_report "$endpoint"
    done

    # Generate combined report
    generate_combined_report

    echo
    log_success "Load testing completed successfully!"
    log "Results saved in: $RESULT_DIR"
    log "View combined report: $RESULT_DIR/combined-performance-report.md"

    # Display final summary
    if [[ -f "$RESULT_DIR/health-performance-report.json" ]]; then
        local grade=$(jq -r '.performance_grade' "$RESULT_DIR/health-performance-report.json" 2>/dev/null || echo "Unknown")
        log_info "Final Performance Grade: $grade"
    fi
}

# Handle interruption gracefully
trap 'echo -e "\n${YELLOW}⚠️ Load testing interrupted${NC}"; exit 130' INT TERM

# Run main function
main "$@"