#!/bin/bash

# E-commerce MCP Server - Test Script for browse-products tool
# This script tests the browse-products endpoint with realistic e-commerce parameters

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
    echo -e "${CYAN}${BOLD}E-commerce MCP Server - Browse Products Tool Test${NC}"
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
    local endpoint="$SERVER_URL/tools/browse-products"
    
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
            local has_products=$(echo "$response_body" | jq -e '.result.products' >/dev/null 2>&1 && echo "true" || echo "false")
            local has_status=$(echo "$response_body" | jq -e '.result.status' >/dev/null 2>&1 && echo "true" || echo "false")
            
            if [ "$has_result" = "true" ] && [ "$has_products" = "true" ] && [ "$has_status" = "true" ]; then
                local product_count=$(echo "$response_body" | jq -r '.result.returned_count // 0' 2>/dev/null)
                print_success "Test passed - Status: $status_code, Products found: $product_count, Duration: ${duration}s"
                PASSED_TESTS=$((PASSED_TESTS + 1))
                log_test_result "$test_name" "PASS" "$duration" "Valid JSON response with expected structure" "$expected_result"
            else
                print_error "Test failed - Missing required fields in response"
                FAILED_TESTS=$((FAILED_TESTS + 1))
                log_test_result "$test_name" "FAIL" "$duration" "Missing required fields: result=$has_result, products=$has_products, status=$has_status" "$expected_result"
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

# Function to run all browse-products tests
run_browse_products_tests() {
    print_header "🛍️  BROWSE PRODUCTS TOOL TESTS"
    
    # Test 1: Basic product browsing (no filters)
    run_test "Basic Product Browse" \
        '{}' \
        "Should return list of products without filters"
    
    # Test 2: Browse by category
    run_test "Browse by Category - Vegetables" \
        '{"category": "vegetables"}' \
        "Should return products in vegetables category"
    
    # Test 3: Browse by category - Fruits
    run_test "Browse by Category - Fruits" \
        '{"category": "fruits"}' \
        "Should return products in fruits category"
    
    # Test 4: Search by product name
    run_test "Search by Product Name" \
        '{"search_term": "apple"}' \
        "Should return products containing 'apple' in name or description"
    
    # Test 5: Combined category and search
    run_test "Category + Search Filter" \
        '{"category": "vegetables", "search_term": "organic"}' \
        "Should return organic vegetables"
    
    # Test 6: Price range filtering
    run_test "Price Range Filter" \
        '{"min_price": 10, "max_price": 50}' \
        "Should return products in price range 10-50"
    
    # Test 7: Limit results
    run_test "Limited Results" \
        '{"max_results": 5}' \
        "Should return maximum 5 products"
    
    # Test 8: Include out of stock
    run_test "Include Out of Stock" \
        '{"include_out_of_stock": true}' \
        "Should return all products including out of stock"
    
    # Test 9: Exclude out of stock
    run_test "Exclude Out of Stock" \
        '{"include_out_of_stock": false}' \
        "Should return only products in stock"
    
    # Test 10: Complex filter combination
    run_test "Complex Filter Combination" \
        '{"category": "fruits", "search_term": "fresh", "min_price": 5, "max_price": 25, "max_results": 10, "include_out_of_stock": true}' \
        "Should apply all filters: fruits category, 'fresh' search, price 5-25, max 10 results, include out of stock"
}

# Main function
main() {
    # Initialize logging
    init_logging "test_browse_products"
    
    # Parse command line arguments
    parse_arguments "$@"
    
    print_header "🛍️  E-COMMERCE BROWSE PRODUCTS TOOL TEST"
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
    run_browse_products_tests
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
        print_error "Some browse-products tests failed!"
    else
        print_success "All browse-products tests passed!"
    fi
    
    # Finalize logging
    finalize_logging $exit_code "Browse products tool test completed"
    
    exit $exit_code
}

# Cleanup old logs
cleanup_old_logs "test_browse_products"

# Run main function
main "$@"
