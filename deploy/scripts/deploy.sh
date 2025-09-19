#!/bin/bash

# Deploy script for CDK stacks
# Usage: ./scripts/deploy.sh [environment] [options]

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

# Function to check if required tools are installed
check_requirements() {
    print_color $YELLOW "Checking requirements..."
    
    if ! command -v aws &> /dev/null; then
        print_color $RED "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! command -v npm &> /dev/null; then
        print_color $RED "npm is not installed. Please install Node.js and npm first."
        exit 1
    fi
    
    print_color $GREEN "✓ All requirements met"
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
        print_color $YELLOW "Please create $env_file from .env.example"
        exit 1
    fi
}

# Function to validate AWS credentials
validate_aws_credentials() {
    print_color $YELLOW "Validating AWS credentials..."
    
    # Set AWS profile if specified
    if [ -n "$AWS_PROFILE" ]; then
        export AWS_PROFILE="$AWS_PROFILE"
        print_color $YELLOW "Using AWS profile: $AWS_PROFILE"
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        print_color $RED "AWS credentials are not configured properly."
        print_color $YELLOW "Please configure AWS credentials using 'aws configure' or environment variables."
        exit 1
    fi
    
    AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION=${CDK_DEFAULT_REGION:-$(aws configure get region)}
    
    print_color $GREEN "✓ AWS Account: $AWS_ACCOUNT"
    print_color $GREEN "✓ AWS Region: $AWS_REGION"
}

# Function to install dependencies
install_dependencies() {
    print_color $YELLOW "Installing dependencies..."
    npm install
    print_color $GREEN "✓ Dependencies installed"
}

# Function to build TypeScript
build_typescript() {
    print_color $YELLOW "Building TypeScript..."
    npm run build
    print_color $GREEN "✓ TypeScript built"
}

# Function to synthesize CDK
synth_cdk() {
    print_color $YELLOW "Synthesizing CDK stacks..."
    npm run cdk synth
    print_color $GREEN "✓ CDK synthesized"
}

# Function to deploy CDK stacks
deploy_cdk() {
    local extra_args="$@"
    
    print_color $YELLOW "Deploying CDK stacks..."
    print_color $YELLOW "Environment: $CDK_ENV"
    
    # Deploy with confirmation prompt
    npm run cdk -- deploy --all --require-approval=never $extra_args
    
    print_color $GREEN "✓ Deployment complete!"
}

# Function to show deployment info
show_deployment_info() {
    local env=$1
    
    print_color $GREEN "\n=== Deployment Information ==="
    print_color $YELLOW "Environment: $env"
    print_color $YELLOW "Project: ${PROJECT_NAME:-alert-engine}"
    
    if [[ "$env" == "dev" ]]; then
        print_color $YELLOW "MCP Server API URL: https://api.dev-alert-engine.totogicore.com"
    elif [[ "$env" == "stage" ]]; then
        print_color $YELLOW "MCP Server API URL: https://api.stage-alert-engine.totogicore.com"
    else
        print_color $YELLOW "MCP Server API URL: https://api.alert-engine.totogicore.com"
    fi
    
    print_color $GREEN "================================\n"
}

# Main script
main() {
    # Get environment from first argument
    ENVIRONMENT=${1:-dev}
    shift || true  # Remove first argument
    
    # Change to infrastructure directory
    cd "$(dirname "$0")/.."
    
    print_color $GREEN "\n=== CDK Deployment Script ==="
    print_color $YELLOW "Environment: $ENVIRONMENT\n"
    
    # Run checks and deployment
    check_requirements
    validate_environment $ENVIRONMENT
    load_env_file $ENVIRONMENT
    validate_aws_credentials
    install_dependencies
    build_typescript
    synth_cdk
    deploy_cdk "$@"
    show_deployment_info $ENVIRONMENT
}

# Run main function
main "$@"