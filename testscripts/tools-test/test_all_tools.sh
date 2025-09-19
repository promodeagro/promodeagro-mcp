#!/bin/bash

# E-commerce MCP Server - Comprehensive Test Script for All E-commerce Tools  
# This script tests all available e-commerce tools with realistic parameters

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
    echo -e "${CYAN}${BOLD}E-commerce MCP Server - Comprehensive Tool Testing${NC}"
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
    echo -e "  $0 http://192.168.1.100                               # Test on IP address"
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

# Parse command line arguments first
parse_arguments "$@"

# Initialize logging for this test script  
init_logging "test_all_ecommerce_tools"
log_environment

echo -e "${CYAN}🌐 Testing e-commerce server at: $SERVER_URL${NC}"
echo ""

# Check for required tools
command -v jq >/dev/null 2>&1 || { print_warning "jq not found, JSON formatting may be limited"; }

# Test execution tracking
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0
TEST_START_TIME=$(date +%s)

check_server() {
    echo -e "${BLUE}🔍 Checking server availability...${NC}"
    
    if curl -s --connect-timeout 3 --max-time 5 "$SERVER_URL/health" > /dev/null 2>&1; then
        print_success "E-commerce MCP server is running at $SERVER_URL"
        return 0
    else
        print_error "E-commerce MCP server is not accessible at $SERVER_URL"
        echo -e "${YELLOW}💡 Start the server with: python mcp_http_server.py${NC}"
        return 1
    fi
}

# Function to make API call and validate response
api_test() {
    local test_name="$1"
    local endpoint="$2"
    local test_data="$3"
    local expected_fields="$4"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    print_test_start "$test_name"
    
    local start_time=$(date +%s.%N)
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
    local status_code="${response##*$'\n'}"
    local response_body="${response%$'\n'*}"
    
    print_request "$endpoint" "$test_data"
    print_response "$response_body"
    log_performance "$test_name" "$duration" "$status_code" "${#response_body}"
    
    # Validate response
    if [ "$status_code" = "200" ]; then
        if echo "$response_body" | jq empty 2>/dev/null; then
            local all_fields_present=true
            for field in $expected_fields; do
                if ! echo "$response_body" | jq -e "$field" >/dev/null 2>&1; then
                    all_fields_present=false
                    break
                fi
            done
            
            if [ "$all_fields_present" = "true" ]; then
                print_success "Test passed - Duration: ${duration}s"
                TESTS_PASSED=$((TESTS_PASSED + 1))
                log_test_result "$test_name" "PASS" "$duration" "Valid response with all expected fields" "200 status with proper JSON structure"
                return 0
            else
                print_error "Test failed - Missing expected fields"
                TESTS_FAILED=$((TESTS_FAILED + 1))
                log_test_result "$test_name" "FAIL" "$duration" "Missing expected fields" "All expected fields should be present"
                return 1
            fi
        else
            print_error "Test failed - Invalid JSON response"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            log_test_result "$test_name" "FAIL" "$duration" "Invalid JSON" "Valid JSON response expected"
            return 1
        fi
    else
        print_error "Test failed - HTTP Status: $status_code"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        log_test_result "$test_name" "FAIL" "$duration" "HTTP Status: $status_code" "200 status expected"
        return 1
    fi
}

# Browse Products Tool Tests
test_browse_products() {
    print_header "🛍️  BROWSE PRODUCTS TOOL TESTS"
    
    local endpoint="$SERVER_URL/tools/browse-products"
    local expected_fields=".result .result.products .result.status .result.returned_count"
    
    # Test 1: Basic product browsing
    api_test "Browse Products - Basic" "$endpoint" '{}' "$expected_fields"
    
    # Test 2: Browse by category
    api_test "Browse Products - By Category" "$endpoint" '{"category": "vegetables"}' "$expected_fields"
    
    # Test 3: Search by term
    api_test "Browse Products - Search Term" "$endpoint" '{"search_term": "apple"}' "$expected_fields"
    
    # Test 4: Price range filter
    api_test "Browse Products - Price Range" "$endpoint" '{"min_price": 10, "max_price": 50}' "$expected_fields"
    
    # Test 5: Limited results
    api_test "Browse Products - Limited Results" "$endpoint" '{"max_results": 5}' "$expected_fields"
    
    # Test 6: Complex filter
    api_test "Browse Products - Complex Filter" "$endpoint" \
        '{"category": "fruits", "search_term": "fresh", "min_price": 5, "max_price": 25, "max_results": 10}' \
        "$expected_fields"
    
    # Test 7: Out of stock handling
    api_test "Browse Products - Include Out of Stock" "$endpoint" '{"include_out_of_stock": true}' "$expected_fields"
    
    # Test 8: Exclude out of stock
    api_test "Browse Products - Exclude Out of Stock" "$endpoint" '{"include_out_of_stock": false}' "$expected_fields"
    
    echo ""
}

# Category Counts Tool Tests
test_category_counts() {
    print_header "📊 CATEGORY COUNTS TOOL TESTS"
    
    local endpoint="$SERVER_URL/tools/get-category-counts"
    local expected_fields=".result .result.categories .result.status .result.total_categories"
    
    # Test 1: Basic category counts
    api_test "Category Counts - Basic" "$endpoint" '{}' "$expected_fields"
    
    # Test 2: Verify response consistency (multiple calls)
    print_test_start "Category Counts - Consistency Test"
    local consistency_test_passed=true
    local first_response=""
    
    for i in {1..3}; do
        local response=$(curl -s -X POST -H "Content-Type: application/json" -d '{}' "$endpoint" 2>/dev/null)
        if [ $i -eq 1 ]; then
            first_response="$response"
        else
            # Compare total_categories field
            local first_total=$(echo "$first_response" | jq -r '.result.total_categories // 0' 2>/dev/null)
            local current_total=$(echo "$response" | jq -r '.result.total_categories // 0' 2>/dev/null)
            
            if [ "$first_total" != "$current_total" ]; then
                consistency_test_passed=false
                break
            fi
        fi
    done
    
    if [ "$consistency_test_passed" = "true" ]; then
        print_success "Consistency test passed - Multiple calls return same category counts"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_error "Consistency test failed - Different category counts in multiple calls"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    echo ""
}

# Error Handling Tests
test_error_handling() {
    print_header "⚠️  ERROR HANDLING TESTS"
    
    # Test invalid tool endpoint
    print_test_start "Invalid Tool Endpoint"
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    local invalid_response=$(curl -s -X POST -H "Content-Type: application/json" -d '{}' \
        "$SERVER_URL/tools/invalid-tool" -w "%{http_code}" 2>/dev/null)
    local invalid_status="${invalid_response##*$'\n'}"
    
    if [ "$invalid_status" = "404" ]; then
        print_success "Invalid endpoint correctly returns 404"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_error "Invalid endpoint should return 404, got: $invalid_status"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    
    # Test malformed JSON
    print_test_start "Malformed JSON Handling"
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    local malformed_response=$(curl -s -X POST -H "Content-Type: application/json" -d '{invalid json}' \
        "$SERVER_URL/tools/browse-products" -w "%{http_code}" 2>/dev/null)
    local malformed_status="${malformed_response##*$'\n'}"
    
    if [ "$malformed_status" = "400" ] || [ "$malformed_status" = "422" ]; then
        print_success "Malformed JSON correctly handled with status: $malformed_status"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_error "Malformed JSON should return 400 or 422, got: $malformed_status"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    
    echo ""
}

# Performance Tests
test_performance() {
    print_header "⚡ PERFORMANCE TESTS"
    
    print_test_start "Browse Products - Performance Test"
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    local total_requests=10
    local successful_requests=0
    local total_time=0
    local max_acceptable_time=2.0
    
    print_info "Running $total_requests concurrent requests to browse-products..."
    
    for i in $(seq 1 $total_requests); do
        local start_time=$(date +%s.%N)
        local response=$(curl -s -X POST -H "Content-Type: application/json" -d '{"max_results": 5}' \
            "$SERVER_URL/tools/browse-products" -w "%{http_code}" 2>/dev/null)
        local end_time=$(date +%s.%N)
        
        local duration=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0")
        total_time=$(echo "$total_time + $duration" | bc -l 2>/dev/null || echo "$total_time")
        
        local status="${response##*$'\n'}"
        if [ "$status" = "200" ]; then
            successful_requests=$((successful_requests + 1))
        fi
    done
    
    local avg_time=$(echo "scale=3; $total_time / $total_requests" | bc -l 2>/dev/null || echo "0")
    local success_rate=$(echo "scale=1; $successful_requests * 100 / $total_requests" | bc -l 2>/dev/null || echo "0")
    
    print_info "Performance Results:"
    print_info "  • Success Rate: ${success_rate}%"
    print_info "  • Average Response Time: ${avg_time}s"
    print_info "  • Total Requests: $total_requests"
    print_info "  • Successful Requests: $successful_requests"
    
    # Check if performance is acceptable
    local time_acceptable=$(echo "$avg_time <= $max_acceptable_time" | bc -l 2>/dev/null || echo "0")
    if [ "$successful_requests" = "$total_requests" ] && [ "$time_acceptable" = "1" ]; then
        print_success "Performance test passed - All requests successful with acceptable response time"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_error "Performance test failed - Either some requests failed or response time too slow"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    
    echo ""
}

# Integration Tests
test_integration() {
    print_header "🔗 INTEGRATION TESTS"
    
    print_test_start "Category Counts + Browse Products Integration"
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    # First get category counts
    local category_response=$(curl -s -X POST -H "Content-Type: application/json" -d '{}' \
        "$SERVER_URL/tools/get-category-counts" 2>/dev/null)
    
    if echo "$category_response" | jq empty 2>/dev/null; then
        local categories=$(echo "$category_response" | jq -r '.result.categories[].name' 2>/dev/null | head -3)
        local integration_success=true
        
        # Test browsing for each category found
        while IFS= read -r category; do
            if [ -n "$category" ] && [ "$category" != "null" ]; then
                local browse_response=$(curl -s -X POST -H "Content-Type: application/json" \
                    -d "{\"category\": \"$category\"}" \
                    "$SERVER_URL/tools/browse-products" 2>/dev/null)
                
                if ! echo "$browse_response" | jq empty 2>/dev/null; then
                    integration_success=false
                    break
                fi
            fi
        done <<< "$categories"
        
        if [ "$integration_success" = "true" ]; then
            print_success "Integration test passed - Category counts integrate well with browse products"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            print_error "Integration test failed - Issues browsing products by discovered categories"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
    else
        print_error "Integration test failed - Could not get category counts"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    
    echo ""
}

# Main test execution
main() {
    print_header "🛍️  E-COMMERCE MCP SERVER - COMPREHENSIVE TOOL TESTING"
    print_info "Server URL: $SERVER_URL"
    print_info "Test started at: $(date)"
    
    # Check server availability
    if ! check_server; then
        finalize_logging 1 "Server health check failed"
        exit 1
    fi
    
    echo ""
    
    # Run all test suites
    test_browse_products
    test_category_counts
    test_error_handling
    test_performance
    test_integration
    
    # Calculate test execution time
    local test_end_time=$(date +%s)
    local total_test_time=$((test_end_time - TEST_START_TIME))
    
    # Print final summary
    print_header "🏁 COMPREHENSIVE TEST EXECUTION SUMMARY"
    
    local success_rate=0
    if [ $TESTS_TOTAL -gt 0 ]; then
        success_rate=$(( TESTS_PASSED * 100 / TESTS_TOTAL ))
    fi
    
    echo -e "${BOLD}📊 Final Test Results:${NC}"
    echo -e "  🎯 Total Tests: ${CYAN}$TESTS_TOTAL${NC}"
    echo -e "  ✅ Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "  ❌ Failed: ${RED}$TESTS_FAILED${NC}"
    echo -e "  📈 Success Rate: ${CYAN}${success_rate}%${NC}"
    echo -e "  ⏱️  Total Duration: ${CYAN}${total_test_time}s${NC}"
    echo ""
    
    echo -e "${BOLD}🛍️  E-commerce Tools Tested:${NC}"
    echo -e "  • ${CYAN}browse-products${NC} - Product catalog browsing and filtering"
    echo -e "  • ${CYAN}get-category-counts${NC} - Product category statistics"
    echo ""
    
    echo -e "${BOLD}🧪 Test Categories Covered:${NC}"
    echo -e "  • ${CYAN}Functional Tests${NC} - Core tool functionality"
    echo -e "  • ${CYAN}Error Handling${NC} - Invalid inputs and edge cases"
    echo -e "  • ${CYAN}Performance Tests${NC} - Response time and throughput"
    echo -e "  • ${CYAN}Integration Tests${NC} - Cross-tool functionality"
    echo ""
    
    # Log comprehensive summary
    log_test_summary "$TESTS_TOTAL" "$TESTS_PASSED" "$TESTS_FAILED" "$total_test_time"
    
    # Determine final result
    local exit_code=0
    if [ $TESTS_FAILED -gt 0 ]; then
        exit_code=1
        print_error "Some e-commerce tool tests failed!"
        print_info "Check the detailed log for specific failure information"
    else
        print_success "All e-commerce tool tests passed successfully! 🎉"
        print_info "E-commerce MCP server is working correctly with all tools functional"
    fi
    
    # Finalize logging
    finalize_logging $exit_code "Comprehensive e-commerce tools test completed"
    
    exit $exit_code
}

# Cleanup old logs
cleanup_old_logs "test_all_ecommerce_tools"

# Run main function
main "$@"
