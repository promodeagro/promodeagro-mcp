#!/bin/bash

# Destroy script for CDK stacks
# Usage: ./scripts/destroy.sh [environment]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# Function to validate environment
validate_environment() {
    local env=$1
    if [[ "$env" != "dev" && "$env" != "stage" && "$env" != "prod" ]]; then
        print_color $RED "Invalid environment: $env"
        print_color $YELLOW "Valid environments are: dev, stage, prod"
        exit 1
    fi
}

# Function to load environment file
load_env_file() {
    local env=$1
    local env_file=".env.${env}"
    
    if [ -f "$env_file" ]; then
        print_color $YELLOW "Loading environment from $env_file"
        # Export variables from env file
        export $(grep -v '^#' $env_file | xargs)
    else
        print_color $RED "Environment file $env_file not found!"
        exit 1
    fi
}

# Function to confirm destruction
confirm_destruction() {
    local env=$1
    
    print_color $RED "\n⚠️  WARNING: You are about to destroy all stacks for environment: $env"
    print_color $RED "This action cannot be undone!"
    
    if [[ "$env" == "prod" ]]; then
        print_color $RED "\n⚠️  PRODUCTION ENVIRONMENT DETECTED!"
        print_color $RED "Please type 'destroy-production' to confirm: "
        read confirmation
        if [[ "$confirmation" != "destroy-production" ]]; then
            print_color $YELLOW "Destruction cancelled."
            exit 0
        fi
    else
        print_color $YELLOW "\nType 'yes' to confirm destruction: "
        read confirmation
        if [[ "$confirmation" != "yes" ]]; then
            print_color $YELLOW "Destruction cancelled."
            exit 0
        fi
    fi
}

# Function to destroy CDK stacks
destroy_cdk() {
    print_color $YELLOW "\nDestroying CDK stacks..."
    
    # Destroy all stacks for the environment
    npm run cdk -- destroy --all --force
    
    print_color $GREEN "✓ All stacks destroyed!"
}

# Main script
main() {
    # Get environment from first argument
    ENVIRONMENT=${1:-dev}
    
    # Change to infrastructure directory
    cd "$(dirname "$0")/.."
    
    print_color $RED "\n=== CDK Destruction Script ==="
    print_color $YELLOW "Environment: $ENVIRONMENT\n"
    
    # Run checks and destruction
    validate_environment $ENVIRONMENT
    load_env_file $ENVIRONMENT
    confirm_destruction $ENVIRONMENT
    destroy_cdk
}

# Run main function
main "$@"