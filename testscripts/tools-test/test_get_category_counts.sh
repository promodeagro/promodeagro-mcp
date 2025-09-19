#!/bin/bash

# E-commerce MCP Server - Test Script for get-category-counts tool
# This script tests the get-category-counts endpoint for e-commerce catalog statistics

set -e

# Get script directory and source logging library
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test_logging_lib.sh"

# Default configuration
DEFAULT_URL="http://localhost:8000"
SERVER_URL="$DEFAULT_URL"

# Function to parse URL and extract components
parse_url() {
    local url="$1"
    
    # Remove protocol (http:// or https://)
    local url_no_protocol="${url#http://}"
    url_no_protocol="${url_no_protocol#https://}"
    
    # Extract host and port
    if [[ "$url_no_protocol" == *":"* ]]; then
        HOST="${url_no_protocol%:*}"
        PORT="${url_no_protocol#*:}"
        # Remove any path after port
        PORT="${PORT%%/*}"
        # Port explicitly specified, use as-is
        if [[ "$url" == https://* ]]; then
            SERVER_URL="https://$HOST:$PORT"
        else
            SERVER_URL="http://$HOST:$PORT"
        fi
    else
        HOST="$url_no_protocol"
        # Remove any path after host
        HOST="${HOST%%/*}"
        
        # Smart port detection based on URL pattern
        if [[ "$HOST" == *".elb."* ]] || [[ "$HOST" == *".amazonaws.com" ]]; then
            # AWS Load Balancer - use standard ports without explicit specification
            if [[ "$url" == https://* ]]; then
                SERVER_URL="https://$HOST"  # Port 443 implicit
            else
                SERVER_URL="http://$HOST"   # Port 80 implicit
            fi
        elif [[ "$HOST" == "localhost" ]] || [[ "$HOST" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
            # Localhost or IP address - use development port 8000
            if [[ "$url" == https://* ]]; then
                SERVER_URL="https://$HOST:8000"
            else
                SERVER_URL="http://$HOST:8000"
            fi
        else
            # Other domains - use standard ports
            if [[ "$url" == https://* ]]; then
                SERVER_URL="https://$HOST"  # Port 443 implicit
            else
                SERVER_URL="http://$HOST"   # Port 80 implicit
            fi
        fi
    fi
}

# Function to show usage
show_usage() {
    echo -e "${CYAN}${BOLD}E-commerce MCP Server - Category Counts Tool Test${NC}"
    echo ""
    echo -e "${YELLOW}Usage:${NC} $0 [URL]"
    echo ""
    echo -e "${YELLOW}Arguments:${NC}"
    echo -e "  URL                    MCP server URL (default: $DEFAULT_URL)"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo -e "  $0                                                    # Test on localhost:8000"
    echo -e "  $0 http://localhost:3000                              # Test on localhost:3000"
    echo -e "  $0 http://ecommerce-server.example.com               # Test on remote server"
    echo ""
}

# Function to parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                show_usage
                exit 0
                ;;
            http://*|https://*)  
                parse_url "$1"
                shift
                ;;
            -*)
                echo -e "${RED}❌ Unknown option: $1${NC}"
                echo -e "${YELLOW}💡 Use URL format instead: $0 http://host:port${NC}"
                show_usage
                exit 1
                ;;
            *)
                echo -e "${RED}❌ Unknown argument: $1${NC}"
                echo -e "${YELLOW}💡 Use URL format: $0 http://host:port${NC}"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Test tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run a test and track results
run_test() {
    local test_name="$1"
    local test_data="$2"
    local expected_result="$3"
    
    print_test_start "Testing: $test_name"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    local start_time=$(date +%s.%N)
    local endpoint="$SERVER_URL/tools/get-category-counts"
    
    print_request "$endpoint" "$test_data"
    
    # Make the API request
    local response=$(curl -s \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$test_data" \
        --connect-timeout 10 \
        --max-time 30 \
        -w "\n%{http_code}" \
        "$endpoint" 2>/dev/null)
    
    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0")
    
    # Parse response and status code
    local status_code="${response##*$'\n'}"
    local response_body="${response%$'\n'*}"
    
    print_response "$response_body"
    log_performance "$test_name" "$duration" "$status_code" "${#response_body}"
    
    # Validate response
    if [ "$status_code" = "200" ]; then
        # Check if response is valid JSON
        if echo "$response_body" | jq empty 2>/dev/null; then
            # Check for expected fields
            local has_result=$(echo "$response_body" | jq -e '.result' >/dev/null 2>&1 && echo "true" || echo "false")
            local has_categories=$(echo "$response_body" | jq -e '.result.categories' >/dev/null 2>&1 && echo "true" || echo "false")
            local has_status=$(echo "$response_body" | jq -e '.result.status' >/dev/null 2>&1 && echo "true" || echo "false")
            local has_total=$(echo "$response_body" | jq -e '.result.total_categories' >/dev/null 2>&1 && echo "true" || echo "false")
            
            if [ "$has_result" = "true" ] && [ "$has_categories" = "true" ] && [ "$has_status" = "true" ] && [ "$has_total" = "true" ]; then
                local category_count=$(echo "$response_body" | jq -r '.result.total_categories // 0' 2>/dev/null)
                local total_products=$(echo "$response_body" | jq -r '.result.total_products // 0' 2>/dev/null)
                print_success "Test passed - Status: $status_code, Categories: $category_count, Total Products: $total_products, Duration: ${duration}s"
                PASSED_TESTS=$((PASSED_TESTS + 1))
                log_test_result "$test_name" "PASS" "$duration" "Valid JSON response with expected structure" "$expected_result"
            else
                print_error "Test failed - Missing required fields in response"
                FAILED_TESTS=$((FAILED_TESTS + 1))
                log_test_result "$test_name" "FAIL" "$duration" "Missing required fields: result=$has_result, categories=$has_categories, status=$has_status, total=$has_total" "$expected_result"
            fi
        else
            print_error "Test failed - Invalid JSON response"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            log_test_result "$test_name" "FAIL" "$duration" "Invalid JSON response" "$expected_result"
        fi
    else
        print_error "Test failed - HTTP Status: $status_code"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_test_result "$test_name" "FAIL" "$duration" "HTTP Status: $status_code" "$expected_result"
    fi
    
    echo ""
}

# Function to check server connectivity
check_server_health() {
    print_test_start "Server Health Check"
    
    if curl -s --connect-timeout 5 --max-time 10 "$SERVER_URL" > /dev/null; then
        print_success "E-commerce MCP server is accessible at $SERVER_URL"
        return 0
    else
        print_error "E-commerce MCP server is not accessible at $SERVER_URL"
        print_info "Make sure the server is running: python mcp_http_server.py"
        return 1
    fi
}

# Function to run detailed analysis of category counts response
analyze_category_counts_response() {
    local response_body="$1"
    
    print_info "🔍 Analyzing category counts response..."
    
    # Extract and display category information
    local categories=$(echo "$response_body" | jq -r '.result.categories[]? | "\(.name): \(.count) products"' 2>/dev/null || echo "No categories found")
    
    if [ "$categories" != "No categories found" ]; then
        print_info "📊 Category breakdown:"
        echo "$categories" | while read -r line; do
            if [ -n "$line" ]; then
                print_info "  • $line"
            fi
        done
        
        # Check for common e-commerce categories
        local common_categories=("vegetables" "fruits" "dairy" "grains" "spices" "beverages" "snacks" "frozen" "organic" "household")
        local found_categories=""
        
        for category in "${common_categories[@]}"; do
            local count=$(echo "$response_body" | jq -r ".result.categories[]? | select(.name | ascii_downcase == \"$category\") | .count" 2>/dev/null || echo "0")
            if [ "$count" != "0" ] && [ -n "$count" ] && [ "$count" != "null" ]; then
                found_categories="$found_categories $category($count)"
            fi
        done
        
        if [ -n "$found_categories" ]; then
            print_success "Common e-commerce categories found:$found_categories"
        else
            print_warning "No common e-commerce categories found in response"
        fi
    else
        print_warning "No category data found in response"
    fi
}

# Function to run all category counts tests
run_category_counts_tests() {
    print_header "📊 CATEGORY COUNTS TOOL TESTS"
    
    # Test 1: Basic category counts request
    print_test_start "Basic Category Counts Request"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    local start_time=$(date +%s.%N)
    local endpoint="$SERVER_URL/tools/get-category-counts"
    local test_data='{}'
    
    print_request "$endpoint" "$test_data"
    
    # Make the API request
    local response=$(curl -s \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$test_data" \
        --connect-timeout 10 \
        --max-time 30 \
        -w "\n%{http_code}" \
        "$endpoint" 2>/dev/null)
    
    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0")
    
    # Parse response and status code
    local status_code="${response##*$'\n'}"
    local response_body="${response%$'\n'*}"
    
    print_response "$response_body"
    log_performance "Basic Category Counts" "$duration" "$status_code" "${#response_body}"
    
    # Validate response and perform detailed analysis
    if [ "$status_code" = "200" ]; then
        if echo "$response_body" | jq empty 2>/dev/null; then
            local has_result=$(echo "$response_body" | jq -e '.result' >/dev/null 2>&1 && echo "true" || echo "false")
            local has_categories=$(echo "$response_body" | jq -e '.result.categories' >/dev/null 2>&1 && echo "true" || echo "false")
            local has_status=$(echo "$response_body" | jq -e '.result.status' >/dev/null 2>&1 && echo "true" || echo "false")
            
            if [ "$has_result" = "true" ] && [ "$has_categories" = "true" ] && [ "$has_status" = "true" ]; then
                print_success "Test passed - Valid category counts response received"
                PASSED_TESTS=$((PASSED_TESTS + 1))
                
                # Perform detailed analysis
                analyze_category_counts_response "$response_body"
                
                log_test_result "Basic Category Counts" "PASS" "$duration" "Valid JSON response with category data" "Should return category counts with product totals"
            else
                print_error "Test failed - Missing required fields in response"
                FAILED_TESTS=$((FAILED_TESTS + 1))
                log_test_result "Basic Category Counts" "FAIL" "$duration" "Missing required fields" "Should return category counts"
            fi
        else
            print_error "Test failed - Invalid JSON response"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            log_test_result "Basic Category Counts" "FAIL" "$duration" "Invalid JSON response" "Should return valid JSON"
        fi
    else
        print_error "Test failed - HTTP Status: $status_code"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_test_result "Basic Category Counts" "FAIL" "$duration" "HTTP Status: $status_code" "Should return 200 status"
    fi
    
    echo ""
    
    # Test 2: Verify response structure consistency
    run_test "Response Structure Validation" \
        '{}' \
        "Should return consistent response structure with all required fields"
    
    # Test 3: Performance test with multiple requests
    print_test_start "Performance Test - Multiple Requests"
    local perf_test_name="Performance Test"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    local total_requests=5
    local successful_requests=0
    local total_time=0
    
    print_info "Running $total_requests consecutive requests..."
    
    for i in $(seq 1 $total_requests); do
        local req_start=$(date +%s.%N)
        local perf_response=$(curl -s \
            -X POST \
            -H "Content-Type: application/json" \
            -d '{}' \
            --connect-timeout 5 \
            --max-time 15 \
            -w "\n%{http_code}" \
            "$endpoint" 2>/dev/null)
        local req_end=$(date +%s.%N)
        local req_duration=$(echo "$req_end - $req_start" | bc -l 2>/dev/null || echo "0")
        total_time=$(echo "$total_time + $req_duration" | bc -l 2>/dev/null || echo "$total_time")
        
        local req_status="${perf_response##*$'\n'}"
        local req_body="${perf_response%$'\n'*}"
        if [ "$req_status" = "200" ]; then
            successful_requests=$((successful_requests + 1))
        fi
        
        print_info "  Request $i: Status $req_status, Duration: ${req_duration}s"
    done
    
    local avg_time=$(echo "scale=3; $total_time / $total_requests" | bc -l 2>/dev/null || echo "0")
    local success_rate=$(echo "scale=1; $successful_requests * 100 / $total_requests" | bc -l 2>/dev/null || echo "0")
    
    if [ "$successful_requests" = "$total_requests" ]; then
        print_success "Performance test passed - All $total_requests requests successful, Average time: ${avg_time}s"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        log_test_result "$perf_test_name" "PASS" "$avg_time" "Success rate: ${success_rate}%, Average response time: ${avg_time}s" "All requests should be successful with reasonable response time"
    else
        print_error "Performance test failed - Only $successful_requests/$total_requests requests successful"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_test_result "$perf_test_name" "FAIL" "$avg_time" "Success rate: ${success_rate}%" "All requests should be successful"
    fi
    
    echo ""
}

# Main function
main() {
    # Initialize logging
    init_logging "test_get_category_counts"
    
    # Parse command line arguments
    parse_arguments "$@"
    
    print_header "📊 E-COMMERCE CATEGORY COUNTS TOOL TEST"
    print_info "Server URL: $SERVER_URL"
    print_info "Test started at: $(date)"
    
    # Log environment information
    log_environment
    
    # Check server health
    if ! check_server_health; then
        finalize_logging 1 "Server health check failed"
        exit 1
    fi
    
    echo ""
    
    # Run all tests
    local test_start_time=$(date +%s)
    run_category_counts_tests
    local test_end_time=$(date +%s)
    local total_duration=$((test_end_time - test_start_time))
    
    # Print summary
    print_header "🏁 TEST EXECUTION SUMMARY"
    
    echo -e "${BOLD}Test Results:${NC}"
    echo -e "  Total Tests: ${CYAN}$TOTAL_TESTS${NC}"
    echo -e "  Passed: ${GREEN}$PASSED_TESTS${NC}"
    echo -e "  Failed: ${RED}$FAILED_TESTS${NC}"
    echo -e "  Success Rate: ${CYAN}$(( PASSED_TESTS * 100 / TOTAL_TESTS ))%${NC}"
    echo -e "  Total Duration: ${CYAN}${total_duration}s${NC}"
    
    # Log test summary
    log_test_summary "$TOTAL_TESTS" "$PASSED_TESTS" "$FAILED_TESTS" "$total_duration"
    
    # Determine exit code
    local exit_code=0
    if [ $FAILED_TESTS -gt 0 ]; then
        exit_code=1
        print_error "Some category counts tests failed!"
    else
        print_success "All category counts tests passed!"
    fi
    
    # Finalize logging
    finalize_logging $exit_code "Category counts tool test completed"
    
    exit $exit_code
}

# Cleanup old logs
cleanup_old_logs "test_get_category_counts"

# Run main function
main "$@"
