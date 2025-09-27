#!/bin/bash
# Test script for deliver-order MCP tool
# Tests delivery operations including successful deliveries, failed deliveries, and returns

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Default server URL
SERVER_URL="${1:-http://localhost:8000}"

print_header() {
    echo -e "${BOLD}${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    DELIVER ORDER TOOL TEST                   ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo -e "${BLUE}Testing server: ${SERVER_URL}${NC}"
    echo ""
}

print_test() {
    echo -e "${BOLD}🧪 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

test_successful_delivery() {
    print_test "Test 1: Successful Delivery (Online Payment)"
    
    local response=$(curl -s -X POST "${SERVER_URL}/tools/call" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "deliver-order",
            "arguments": {
                "order_id": "test-order-001",
                "delivery_status": "successful",
                "customer_verified": true,
                "payment_collected": true,
                "signature_obtained": true,
                "photo_taken": true,
                "customer_feedback": "Excellent service, very quick delivery!",
                "delivered_by": "emp-del-001"
            }
        }')
    
    if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
        local success=$(echo "$response" | jq -r '.success')
        if [ "$success" = "true" ]; then
            print_success "Successful delivery test passed"
            echo "   📦 Order ID: $(echo "$response" | jq -r '.delivery_result.order_id')"
            echo "   ✅ Status: $(echo "$response" | jq -r '.delivery_result.status')"
            echo "   💰 Payment: $(echo "$response" | jq -r '.delivery_result.payment_collected // "N/A"')"
        else
            print_error "Successful delivery test failed"
            echo "   Error: $(echo "$response" | jq -r '.message')"
        fi
    else
        print_error "Invalid response format for successful delivery test"
        echo "   Response: $response"
    fi
    echo ""
}

test_successful_cod_delivery() {
    print_test "Test 2: Successful COD Delivery with Payment Collection"
    
    local response=$(curl -s -X POST "${SERVER_URL}/tools/call" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "deliver-order",
            "arguments": {
                "order_id": "test-order-cod-001",
                "delivery_status": "successful",
                "customer_verified": true,
                "payment_collected": true,
                "signature_obtained": true,
                "photo_taken": false,
                "customer_feedback": "Happy with the product quality",
                "delivered_by": "emp-del-002"
            }
        }')
    
    if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
        local success=$(echo "$response" | jq -r '.success')
        if [ "$success" = "true" ]; then
            print_success "COD delivery test passed"
            echo "   📦 Order ID: $(echo "$response" | jq -r '.delivery_result.order_id')"
            echo "   💰 Payment Collected: $(echo "$response" | jq -r '.delivery_result.payment_collected // "N/A"')"
        else
            print_error "COD delivery test failed"
            echo "   Error: $(echo "$response" | jq -r '.message')"
        fi
    else
        print_error "Invalid response format for COD delivery test"
    fi
    echo ""
}

test_failed_delivery() {
    print_test "Test 3: Failed Delivery"
    
    local response=$(curl -s -X POST "${SERVER_URL}/tools/call" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "deliver-order",
            "arguments": {
                "order_id": "test-order-failed-001",
                "delivery_status": "failed",
                "customer_verified": false,
                "failure_reason": "Customer not available at delivery address after multiple attempts",
                "delivery_notes": "Tried calling customer phone but no response",
                "delivered_by": "emp-del-003"
            }
        }')
    
    if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
        local success=$(echo "$response" | jq -r '.success')
        if [ "$success" = "true" ]; then
            print_success "Failed delivery test passed"
            echo "   📦 Order ID: $(echo "$response" | jq -r '.delivery_result.order_id')"
            echo "   ❌ Status: $(echo "$response" | jq -r '.delivery_result.status')"
            echo "   📝 Reason: $(echo "$response" | jq -r '.delivery_result.message')"
        else
            print_error "Failed delivery test failed"
            echo "   Error: $(echo "$response" | jq -r '.message')"
        fi
    else
        print_error "Invalid response format for failed delivery test"
    fi
    echo ""
}

test_returned_delivery() {
    print_test "Test 4: Returned to Warehouse"
    
    local response=$(curl -s -X POST "${SERVER_URL}/tools/call" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "deliver-order",
            "arguments": {
                "order_id": "test-order-return-001",
                "delivery_status": "returned",
                "customer_verified": false,
                "failure_reason": "Incorrect delivery address provided by customer",
                "delivery_notes": "Customer requested address change, returning to warehouse for reprocessing",
                "delivered_by": "emp-del-004"
            }
        }')
    
    if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
        local success=$(echo "$response" | jq -r '.success')
        if [ "$success" = "true" ]; then
            print_success "Return delivery test passed"
            echo "   📦 Order ID: $(echo "$response" | jq -r '.delivery_result.order_id')"
            echo "   ↩️ Status: $(echo "$response" | jq -r '.delivery_result.status')"
        else
            print_error "Return delivery test failed"
            echo "   Error: $(echo "$response" | jq -r '.message')"
        fi
    else
        print_error "Invalid response format for return delivery test"
    fi
    echo ""
}

test_delivery_status() {
    print_test "Test 5: Get Delivery Status"
    
    local response=$(curl -s -X POST "${SERVER_URL}/tools/call" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "get-delivery-status",
            "arguments": {
                "order_id": "test-order-001"
            }
        }')
    
    if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
        local success=$(echo "$response" | jq -r '.success')
        if [ "$success" = "true" ]; then
            print_success "Delivery status test passed"
            echo "   📦 Order ID: $(echo "$response" | jq -r '.order_id')"
            echo "   📊 Status: $(echo "$response" | jq -r '.current_status')"
            echo "   👤 Customer: $(echo "$response" | jq -r '.order_info.customer_info.name // "N/A"')"
        else
            print_error "Delivery status test failed"
            echo "   Error: $(echo "$response" | jq -r '.message')"
        fi
    else
        print_error "Invalid response format for delivery status test"
    fi
    echo ""
}

test_invalid_delivery_status() {
    print_test "Test 6: Invalid Delivery Status (Error Handling)"
    
    local response=$(curl -s -X POST "${SERVER_URL}/tools/call" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "deliver-order",
            "arguments": {
                "order_id": "test-order-invalid",
                "delivery_status": "invalid_status",
                "customer_verified": true
            }
        }')
    
    if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
        local success=$(echo "$response" | jq -r '.success')
        if [ "$success" = "false" ]; then
            print_success "Invalid status error handling test passed"
            echo "   ❌ Expected error: $(echo "$response" | jq -r '.message')"
        else
            print_error "Invalid status should have failed"
        fi
    else
        print_error "Invalid response format for error handling test"
    fi
    echo ""
}

test_missing_failure_reason() {
    print_test "Test 7: Failed Delivery without Failure Reason (Validation Error)"
    
    local response=$(curl -s -X POST "${SERVER_URL}/tools/call" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "deliver-order",
            "arguments": {
                "order_id": "test-order-no-reason",
                "delivery_status": "failed",
                "customer_verified": false
            }
        }')
    
    if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
        local success=$(echo "$response" | jq -r '.success')
        if [ "$success" = "false" ]; then
            print_success "Missing failure reason validation test passed"
            echo "   ❌ Expected validation error: $(echo "$response" | jq -r '.message')"
        else
            print_error "Missing failure reason should have failed validation"
        fi
    else
        print_error "Invalid response format for validation test"
    fi
    echo ""
}

run_all_tests() {
    print_header
    
    echo -e "${BOLD}🚀 Running Deliver Order Tool Tests${NC}"
    echo "Testing comprehensive delivery operations..."
    echo ""
    
    # Check if server is accessible
    if ! curl -s --max-time 5 "${SERVER_URL}/health" >/dev/null 2>&1; then
        print_warning "Server health check failed, but continuing with tests..."
    fi
    
    # Run all tests
    test_successful_delivery
    test_successful_cod_delivery
    test_failed_delivery
    test_returned_delivery
    test_delivery_status
    test_invalid_delivery_status
    test_missing_failure_reason
    
    echo -e "${BOLD}${BLUE}📊 Test Summary${NC}"
    echo "All delivery tool tests completed."
    echo "Check individual test results above for detailed information."
    echo ""
    echo -e "${BOLD}🔧 Tool Capabilities Tested:${NC}"
    echo "✅ Successful delivery processing"
    echo "✅ COD payment collection"
    echo "✅ Failed delivery handling"
    echo "✅ Return to warehouse processing"
    echo "✅ Delivery status retrieval"
    echo "✅ Error validation and handling"
    echo ""
}

# Show usage if help requested
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "Usage: $0 [SERVER_URL]"
    echo ""
    echo "Examples:"
    echo "  $0                              # Test localhost:8000"
    echo "  $0 http://192.168.1.100:9000    # Test remote server"
    echo "  $0 https://api.example.com:8080  # Test HTTPS server"
    echo ""
    echo "Tests:"
    echo "  - Successful delivery (online payment)"
    echo "  - Successful COD delivery"
    echo "  - Failed delivery"
    echo "  - Returned to warehouse"
    echo "  - Delivery status retrieval"
    echo "  - Error handling and validation"
    exit 0
fi

# Run all tests
run_all_tests
