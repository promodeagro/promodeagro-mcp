#!/bin/bash
#
# Common Logging Library for E-commerce MCP Server Test Scripts
# This library provides logging functionality for all test scripts
#

# Base configuration
LOGS_BASE_DIR="/opt/mycode/promode/promodeagro-mcp/logs/test-scripts"
LOG_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Ensure logs directory exists
mkdir -p "$LOGS_BASE_DIR"

# Colors for output (maintained for console visibility)
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Global log file variables (to be set by each script)
LOG_FILE=""
SCRIPT_NAME=""
TEST_START_TIME=""

# Initialize logging for a specific test script
init_logging() {
    local script_name="$1"
    SCRIPT_NAME="$script_name"
    TEST_START_TIME=$(date +"%Y-%m-%d %H:%M:%S")
    
    # Create log file with timestamp
    LOG_FILE="$LOGS_BASE_DIR/${script_name}_${LOG_TIMESTAMP}.log"
    
    # Create session log header
    cat > "$LOG_FILE" << EOF
================================================================================
E-commerce MCP Server - Test Script Log
================================================================================
Script Name: $SCRIPT_NAME
Start Time: $TEST_START_TIME
Log File: $LOG_FILE
Server URL: ${SERVER_URL:-"Not specified"}
================================================================================

EOF
    
    echo "📋 Log initialized: $LOG_FILE"
}

# Log function that writes to both console and file
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S.%3N")
    
    # Write to log file (without colors)
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Enhanced print functions with logging
print_header() {
    local message="$1"
    echo -e "${PURPLE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${PURPLE}${BOLD}$message${NC}"
    echo -e "${PURPLE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    log_message "HEADER" "$message"
}

print_success() {
    local message="✅ $1"
    echo -e "${GREEN}$message${NC}"
    log_message "SUCCESS" "$1"
}

print_info() {
    local message="ℹ️ $1"
    echo -e "${CYAN}$message${NC}"
    log_message "INFO" "$1"
}

print_warning() {
    local message="⚠️ $1"
    echo -e "${YELLOW}$message${NC}"
    log_message "WARNING" "$1"
}

print_error() {
    local message="❌ $1"
    echo -e "${RED}$message${NC}"
    log_message "ERROR" "$1"
}

print_test_start() {
    local test_name="$1"
    echo -e "${BLUE}🧪 $test_name${NC}"
    log_message "TEST_START" "$test_name"
}

print_request() {
    local url="$1"
    local data="$2"
    echo -e "${BLUE}📤 Sending request to: $url${NC}"
    echo -e "${BLUE}📋 Test data: $data${NC}"
    log_message "REQUEST" "URL: $url"
    log_message "REQUEST_DATA" "$data"
}

print_response() {
    local response="$1"
    echo -e "${BLUE}📥 Response received:${NC}"
    echo "$response"
    log_message "RESPONSE" "$response"
}

# Function to log API test results with detailed analysis
log_test_result() {
    local test_name="$1"
    local status="$2"
    local response_time="$3"
    local response_data="$4"
    local expected_result="$5"
    
    log_message "TEST_RESULT" "Test: $test_name"
    log_message "TEST_STATUS" "$status"
    log_message "RESPONSE_TIME" "${response_time}s"
    
    if [ -n "$response_data" ]; then
        log_message "RESPONSE_ANALYSIS" "$response_data"
    fi
    
    if [ -n "$expected_result" ]; then
        log_message "EXPECTED_VS_ACTUAL" "$expected_result"
    fi
}

# Function to log performance metrics
log_performance() {
    local test_name="$1"
    local response_time="$2"
    local status_code="$3"
    local data_size="$4"
    
    log_message "PERFORMANCE" "Test: $test_name, Time: ${response_time}s, Status: $status_code, Size: ${data_size:-"unknown"} bytes"
}

# Function to log test summary at the end
log_test_summary() {
    local total_tests="$1"
    local passed_tests="$2"
    local failed_tests="$3"
    local test_duration="$4"
    
    local summary="Test Summary - Total: $total_tests, Passed: $passed_tests, Failed: $failed_tests, Duration: ${test_duration}s"
    
    cat >> "$LOG_FILE" << EOF

================================================================================
TEST EXECUTION SUMMARY
================================================================================
$summary
End Time: $(date +"%Y-%m-%d %H:%M:%S")
================================================================================
EOF
    
    print_info "$summary"
}

# Function to capture and log curl command details
log_curl_request() {
    local method="$1"
    local url="$2"
    local headers="$3"
    local data="$4"
    
    log_message "CURL_REQUEST" "Method: $method, URL: $url"
    if [ -n "$headers" ]; then
        log_message "CURL_HEADERS" "$headers"
    fi
    if [ -n "$data" ]; then
        log_message "CURL_DATA" "$data"
    fi
}

# Function to capture server response details
log_server_response() {
    local status_code="$1"
    local response_headers="$2"
    local response_body="$3"
    local response_time="$4"
    
    log_message "SERVER_RESPONSE" "Status: $status_code, Time: ${response_time}s"
    if [ -n "$response_headers" ]; then
        log_message "RESPONSE_HEADERS" "$response_headers"
    fi
    if [ -n "$response_body" ]; then
        log_message "RESPONSE_BODY" "$response_body"
    fi
}

# Function to log environment information
log_environment() {
    cat >> "$LOG_FILE" << EOF

================================================================================
ENVIRONMENT INFORMATION
================================================================================
Hostname: $(hostname)
User: $(whoami)
Working Directory: $(pwd)
Date: $(date)
Python Version: $(python3 --version 2>/dev/null || echo "Not available")
Curl Version: $(curl --version | head -1 2>/dev/null || echo "Not available")
JQ Version: $(jq --version 2>/dev/null || echo "Not available")
================================================================================
EOF
}

# Function to create a detailed error report
log_error_details() {
    local error_context="$1"
    local error_message="$2"
    local debug_info="$3"
    
    cat >> "$LOG_FILE" << EOF

================================================================================
ERROR DETAILS
================================================================================
Context: $error_context
Error: $error_message
Debug Information: $debug_info
Timestamp: $(date +"%Y-%m-%d %H:%M:%S")
================================================================================
EOF
}

# Function to cleanup and finalize logging
finalize_logging() {
    local exit_code="$1"
    local final_message="$2"
    
    if [ "$exit_code" -eq 0 ]; then
        print_success "All tests completed successfully!"
        log_message "FINAL_STATUS" "SUCCESS - All tests completed"
    else
        print_error "Some tests failed or encountered errors"
        log_message "FINAL_STATUS" "FAILURE - Tests completed with errors"
    fi
    
    if [ -n "$final_message" ]; then
        log_message "FINAL_MESSAGE" "$final_message"
    fi
    
    log_message "LOG_END" "Test execution completed at $(date +"%Y-%m-%d %H:%M:%S")"
    
    # Print log file location for reference
    echo -e "${CYAN}📋 Complete test log saved to: $LOG_FILE${NC}"
}

# Function to archive old logs (keep last 10 runs per script)
cleanup_old_logs() {
    local script_name="$1"
    
    # Keep only the 10 most recent log files for this script
    ls -t "$LOGS_BASE_DIR/${script_name}_"*.log 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
}

# Export functions for use in test scripts
export -f init_logging log_message print_header print_success print_info print_warning print_error
export -f print_test_start print_request print_response log_test_result log_performance
export -f log_test_summary log_curl_request log_server_response log_environment
export -f log_error_details finalize_logging cleanup_old_logs
