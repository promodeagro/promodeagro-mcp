#!/bin/bash

# Diff script for CDK stacks - shows what changes will be made
# Usage: ./scripts/diff.sh [environment]

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

# Main script
main() {
    # Get environment from first argument
    ENVIRONMENT=${1:-dev}
    
    # Change to infrastructure directory
    cd "$(dirname "$0")/.."
    
    print_color $GREEN "\n=== CDK Diff Script ==="
    print_color $YELLOW "Environment: $ENVIRONMENT"
    print_color $YELLOW "Showing changes that will be made...\n"
    
    # Run checks and diff
    validate_environment $ENVIRONMENT
    load_env_file $ENVIRONMENT
    
    # Build TypeScript
    print_color $YELLOW "Building TypeScript..."
    npm run build
    
    # Run diff
    npm run cdk diff --all
}

# Run main function
main "$@"