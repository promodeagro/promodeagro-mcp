#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Load configuration
if [ $# -eq 0 ]; then
    print_error "Usage: $0 <environment>"
    print_error "Example: $0 dev"
    exit 1
fi

ENVIRONMENT="$1"
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
CONFIG_FILE="$SCRIPT_DIR/config/${ENVIRONMENT}.conf"

if [ ! -f "$CONFIG_FILE" ]; then
    print_error "Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# Source the configuration
source "$CONFIG_FILE"

print_status "Cleaning up cross-region deployment for environment: $ENVIRONMENT"

# Delete global stack first (it depends on regional)
if aws cloudformation describe-stacks --stack-name "$GLOBAL_STACK_NAME" --region "$AWS_REGION" &>/dev/null; then
    print_status "Deleting global stack: $GLOBAL_STACK_NAME (region: $AWS_REGION)"
    aws cloudformation delete-stack --stack-name "$GLOBAL_STACK_NAME" --region "$AWS_REGION"
    
    print_status "Waiting for global stack deletion to complete..."
    aws cloudformation wait stack-delete-complete --stack-name "$GLOBAL_STACK_NAME" --region "$AWS_REGION"
    print_success "Global stack deleted successfully"
else
    print_warning "Global stack $GLOBAL_STACK_NAME not found in region $AWS_REGION"
fi

# Delete regional stack
if aws cloudformation describe-stacks --stack-name "$REGIONAL_STACK_NAME" --region "$DEPLOYMENT_REGION" &>/dev/null; then
    print_status "Deleting regional stack: $REGIONAL_STACK_NAME (region: $DEPLOYMENT_REGION)"
    aws cloudformation delete-stack --stack-name "$REGIONAL_STACK_NAME" --region "$DEPLOYMENT_REGION"
    
    print_status "Waiting for regional stack deletion to complete..."
    aws cloudformation wait stack-delete-complete --stack-name "$REGIONAL_STACK_NAME" --region "$DEPLOYMENT_REGION"
    print_success "Regional stack deleted successfully"
else
    print_warning "Regional stack $REGIONAL_STACK_NAME not found in region $DEPLOYMENT_REGION"
fi

# Also check for single-region stack
if [ -n "$STACK_NAME" ] && aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" &>/dev/null; then
    print_status "Deleting single-region stack: $STACK_NAME (region: $AWS_REGION)"
    aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$AWS_REGION"
    
    print_status "Waiting for single-region stack deletion to complete..."
    aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$AWS_REGION"
    print_success "Single-region stack deleted successfully"
fi

print_success "Cleanup completed for environment: $ENVIRONMENT"
print_status "You can now redeploy using: ./deploy/deploy.sh $ENVIRONMENT"
