#!/bin/bash

# Alert Engine MCP Server - Deployment Verification Script
# Verifies that all components are deployed and working correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script path configuration
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check stack status
check_stack_status() {
    local stack_name="$1"
    local status
    
    print_status "Checking stack: $stack_name"
    
    if ! status=$(aws cloudformation describe-stacks --stack-name "$stack_name" --region "$AWS_REGION" --query 'Stacks[0].StackStatus' --output text 2>/dev/null); then
        print_error "Stack not found: $stack_name"
        return 1
    fi
    
    case "$status" in
        "CREATE_COMPLETE"|"UPDATE_COMPLETE")
            print_success "Stack $stack_name: $status ✓"
            return 0
            ;;
        "CREATE_IN_PROGRESS"|"UPDATE_IN_PROGRESS")
            print_warning "Stack $stack_name: $status (in progress)"
            return 1
            ;;
        "ROLLBACK_COMPLETE"|"UPDATE_ROLLBACK_COMPLETE")
            print_warning "Stack $stack_name: $status (rolled back)"
            return 1
            ;;
        *)
            print_error "Stack $stack_name: $status ✗"
            return 1
            ;;
    esac
}

# Function to check ECS service status
check_ecs_service() {
    local cluster_name="$1"
    local service_name="$2"
    
    print_status "Checking ECS service: $service_name in cluster: $cluster_name"
    
    local service_info
    if ! service_info=$(aws ecs describe-services --cluster "$cluster_name" --services "$service_name" --region "$AWS_REGION" 2>/dev/null); then
        print_error "ECS service not found: $service_name"
        return 1
    fi
    
    local running_count desired_count status
    running_count=$(echo "$service_info" | jq -r '.services[0].runningCount')
    desired_count=$(echo "$service_info" | jq -r '.services[0].desiredCount')
    status=$(echo "$service_info" | jq -r '.services[0].status')
    
    print_status "Service status: $status"
    print_status "Running tasks: $running_count/$desired_count"
    
    if [ "$status" = "ACTIVE" ] && [ "$running_count" -eq "$desired_count" ]; then
        print_success "ECS service is healthy ✓"
        return 0
    else
        print_error "ECS service is not healthy ✗"
        return 1
    fi
}

# Function to check health endpoint
check_health_endpoint() {
    local url="$1"
    
    print_status "Checking health endpoint: $url"
    
    if ! response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null); then
        print_error "Failed to connect to health endpoint"
        return 1
    fi
    
    if [ "$response" -eq 200 ]; then
        print_success "Health endpoint responded with HTTP $response ✓"
        return 0
    else
        print_error "Health endpoint responded with HTTP $response ✗"
        return 1
    fi
}

# Function to check ALB targets
check_alb_targets() {
    local target_group_arn="$1"
    
    print_status "Checking ALB target group health"
    
    local targets
    if ! targets=$(aws elbv2 describe-target-health --target-group-arn "$target_group_arn" --region "$AWS_REGION" 2>/dev/null); then
        print_error "Failed to describe target health"
        return 1
    fi
    
    local healthy_count total_count
    healthy_count=$(echo "$targets" | jq '[.TargetHealthDescriptions[] | select(.TargetHealth.State == "healthy")] | length')
    total_count=$(echo "$targets" | jq '.TargetHealthDescriptions | length')
    
    print_status "Healthy targets: $healthy_count/$total_count"
    
    if [ "$healthy_count" -gt 0 ] && [ "$healthy_count" -eq "$total_count" ]; then
        print_success "All ALB targets are healthy ✓"
        return 0
    else
        print_error "Some ALB targets are unhealthy ✗"
        return 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 <environment>"
    echo ""
    echo "Environments:"
    echo "  dev   - Development environment"
    echo "  stage - Staging environment"
    echo "  prod  - Production environment"
    echo ""
    echo "Examples:"
    echo "  $0 dev    # Verify dev environment deployment"
    echo "  $0 prod   # Verify prod environment deployment"
}

# Validate arguments
if [ $# -eq 0 ]; then
    show_usage
    exit 1
fi

ENVIRONMENT="$1"

# Validate environment
case "$ENVIRONMENT" in
    "dev"|"stage"|"prod")
        ;;
    *)
        print_error "Invalid environment: $ENVIRONMENT"
        show_usage
        exit 1
        ;;
esac

# Load configuration
CONFIG_FILE="$SCRIPT_DIR/config/${ENVIRONMENT}.conf"
if [ ! -f "$CONFIG_FILE" ]; then
    print_error "Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# Source the configuration file
source "$CONFIG_FILE"

echo "🔍 Starting deployment verification for environment: $ENVIRONMENT"
echo "=============================================================="

# Check if required tools are available
if ! command -v jq &> /dev/null; then
    print_error "jq is required but not installed. Please install jq."
    exit 1
fi

if ! command -v curl &> /dev/null; then
    print_error "curl is required but not installed. Please install curl."
    exit 1
fi

# Verify stacks
verification_failed=false

print_status "Phase 1: Verifying CloudFormation stacks..."
check_stack_status "$NETWORK_STACK_NAME" || verification_failed=true
check_stack_status "$STORAGE_STACK_NAME" || verification_failed=true

if [ "$ENABLE_AUTHENTICATION" = "true" ]; then
    check_stack_status "$AUTH_STACK_NAME" || verification_failed=true
fi

check_stack_status "$BACKEND_STACK_NAME" || verification_failed=true

if [ "$ENABLE_DOMAIN_SETUP" = "true" ]; then
    check_stack_status "$DOMAIN_STACK_NAME" || verification_failed=true
fi

echo ""
print_status "Phase 2: Verifying ECS service..."

# Get cluster and service names from stack outputs
CLUSTER_NAME=$(aws cloudformation describe-stacks --stack-name "$NETWORK_STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`ClusterName`].OutputValue' --output text 2>/dev/null || echo "")
SERVICE_NAME=$(aws cloudformation describe-stacks --stack-name "$BACKEND_STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`ServiceName`].OutputValue' --output text 2>/dev/null || echo "")

if [ -n "$CLUSTER_NAME" ] && [ -n "$SERVICE_NAME" ]; then
    check_ecs_service "$CLUSTER_NAME" "$SERVICE_NAME" || verification_failed=true
else
    print_error "Could not retrieve cluster or service name from stack outputs"
    verification_failed=true
fi

echo ""
print_status "Phase 3: Verifying load balancer targets..."

# Get target group ARN from stack outputs
TARGET_GROUP_ARN=$(aws cloudformation describe-stacks --stack-name "$BACKEND_STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`TargetGroupArn`].OutputValue' --output text 2>/dev/null || echo "")

if [ -n "$TARGET_GROUP_ARN" ]; then
    check_alb_targets "$TARGET_GROUP_ARN" || verification_failed=true
else
    print_error "Could not retrieve target group ARN from stack outputs"
    verification_failed=true
fi

echo ""
print_status "Phase 4: Verifying health endpoints..."

# Get backend URL from stack outputs
BACKEND_URL=$(aws cloudformation describe-stacks --stack-name "$BACKEND_STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`BackendUrl`].OutputValue' --output text 2>/dev/null || echo "")

if [ -n "$BACKEND_URL" ]; then
    health_url="${BACKEND_URL}/health"
    check_health_endpoint "$health_url" || verification_failed=true
else
    print_error "Could not retrieve backend URL from stack outputs"
    verification_failed=true
fi

# Check domain URL if domain setup is enabled
if [ "$ENABLE_DOMAIN_SETUP" = "true" ]; then
    API_URL=$(aws cloudformation describe-stacks --stack-name "$DOMAIN_STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text 2>/dev/null || echo "")
    if [ -n "$API_URL" ]; then
        domain_health_url="${API_URL}/health"
        check_health_endpoint "$domain_health_url" || verification_failed=true
    fi
fi

echo ""
echo "=============================================================="

if [ "$verification_failed" = true ]; then
    print_error "❌ Deployment verification FAILED"
    echo ""
    print_error "Some components are not working correctly. Please check the logs and resolve any issues."
    exit 1
else
    print_success "✅ Deployment verification PASSED"
    echo ""
    print_success "All components are deployed and working correctly!"
    echo ""
    echo "🌐 Service URLs:"
    if [ -n "$BACKEND_URL" ]; then
        echo "   Backend Service: $BACKEND_URL"
        echo "   Health Check: ${BACKEND_URL}/health"
    fi
    if [ -n "$API_URL" ]; then
        echo "   API Endpoint: $API_URL"
        echo "   Health Check: ${API_URL}/health"
    fi
    exit 0
fi

