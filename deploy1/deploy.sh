#!/bin/bash

# TMF ODA Transformer UI Deployment Script
# Architecture: Route53 -> AWS WAF -> CloudFront -> S3
# Supports multiple environments: dev, prod

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values - will be overridden by environment config
ENVIRONMENT=""
STACK_NAME=""
DOMAIN_NAME=""
HOSTED_ZONE_ID=""
BUCKET_NAME=""
AWS_REGION=""
DEPLOYMENT_REGION=""
CLOUDFORMATION_TEMPLATE=""
GLOBAL_TEMPLATE=""
REGIONAL_TEMPLATE=""
GLOBAL_STACK_NAME=""
REGIONAL_STACK_NAME=""
ROLE_ARN=""
EXTERNAL_PROFILE=""
BUILD_ENVIRONMENT=""
NODE_ENV=""

# Script path configuration
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
ASSUME_ROLE_SCRIPT="./deploy/assume-role-to-profile.sh"

# Available environments
AVAILABLE_ENVIRONMENTS=("dev" "stage" "prod")

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

# Function to load environment configuration
load_config() {
    local env="$1"
    local config_file="$SCRIPT_DIR/config/${env}.conf"
    
    if [ ! -f "$config_file" ]; then
        print_error "Configuration file not found: $config_file"
        print_error "Available environments: ${AVAILABLE_ENVIRONMENTS[*]}"
        exit 1
    fi
    
    print_status "Loading configuration for environment: $env"
    
    # Source the configuration file
    # shellcheck source=/dev/null
    source "$config_file"
    
    # Validate required configuration variables
    if [ -z "$STACK_NAME" ] || [ -z "$DOMAIN_NAME" ] || [ -z "$HOSTED_ZONE_ID" ] || [ -z "$BUCKET_NAME" ] || [ -z "$AWS_REGION" ]; then
        print_error "Missing required configuration in $config_file"
        print_error "Required: STACK_NAME, DOMAIN_NAME, HOSTED_ZONE_ID, BUCKET_NAME, AWS_REGION"
        exit 1
    fi
    
    # Set deployment region to AWS region if not specified (backward compatibility)
    if [ -z "$DEPLOYMENT_REGION" ]; then
        DEPLOYMENT_REGION="$AWS_REGION"
        print_status "DEPLOYMENT_REGION not specified, using AWS_REGION: $DEPLOYMENT_REGION"
    fi
    
    # Detect cross-region deployment
    if [ "$DEPLOYMENT_REGION" != "$AWS_REGION" ]; then
        CROSS_REGION_DEPLOYMENT=true
        print_status "Cross-region deployment detected:"
        print_status "  Global resources region: $AWS_REGION"
        print_status "  Regional resources region: $DEPLOYMENT_REGION"
        
        # Validate cross-region specific templates
        if [ -z "$GLOBAL_TEMPLATE" ] || [ -z "$REGIONAL_TEMPLATE" ] || [ -z "$GLOBAL_STACK_NAME" ] || [ -z "$REGIONAL_STACK_NAME" ]; then
            print_error "Cross-region deployment requires: GLOBAL_TEMPLATE, REGIONAL_TEMPLATE, GLOBAL_STACK_NAME, REGIONAL_STACK_NAME"
            exit 1
        fi
        
        # Ensure global resources are deployed to us-east-1
        if [ "$AWS_REGION" != "us-east-1" ]; then
            print_warning "Global resources should typically be deployed to us-east-1 for CloudFront/WAF compatibility"
            print_warning "Current AWS_REGION: $AWS_REGION"
        fi
    else
        CROSS_REGION_DEPLOYMENT=false
        print_status "Single-region deployment to: $AWS_REGION"
        
        # Fallback to single template if cross-region templates not specified
        if [ -z "$CLOUDFORMATION_TEMPLATE" ]; then
            print_error "Single-region deployment requires: CLOUDFORMATION_TEMPLATE"
            exit 1
        fi
    fi
    
    # Generate unique bucket name with timestamp for new deployments
    BUCKET_NAME="${BUCKET_NAME}-$(date +%s)-$RANDOM"
    
    # Set NODE_ENV for build process
    export NODE_ENV="$NODE_ENV"
    
    print_success "Configuration loaded successfully"
    print_status "Environment: $ENVIRONMENT"
    print_status "Domain: $DOMAIN_NAME"
    if [ "$CROSS_REGION_DEPLOYMENT" = true ]; then
        print_status "AWS Region (Global): $AWS_REGION"
        print_status "Deployment Region (Regional): $DEPLOYMENT_REGION"
        print_status "Global Stack: $GLOBAL_STACK_NAME"
        print_status "Regional Stack: $REGIONAL_STACK_NAME"
    else
        print_status "Region: $AWS_REGION"
        print_status "Stack: $STACK_NAME"
    fi
}

# Function to assume external AWS role
assume_external_role() {
    print_status "Assuming external AWS role..."
    
    # Check if assume role script exists
    if [ ! -f "$ASSUME_ROLE_SCRIPT" ]; then
        print_error "Assume role script not found: $ASSUME_ROLE_SCRIPT"
        exit 1
    fi
    
    # Make the script executable
    chmod +x "$ASSUME_ROLE_SCRIPT"
    
    # Assume the role
    print_status "Running: $ASSUME_ROLE_SCRIPT $ROLE_ARN $EXTERNAL_PROFILE"
    if ! "$ASSUME_ROLE_SCRIPT" "$ROLE_ARN" "$EXTERNAL_PROFILE"; then
        print_error "Failed to assume external role"
        exit 1
    fi
    
    # Export the profile
    export AWS_PROFILE="$EXTERNAL_PROFILE"
    print_success "Successfully assumed role with profile: $AWS_PROFILE"
    
    # Verify the assumed role
    print_status "Verifying assumed role..."
    if ! aws sts get-caller-identity; then
        print_error "Failed to verify assumed role"
        exit 1
    fi
    
    print_success "External role assumed and verified"
}

# Function to check if AWS CLI is installed and configured
check_aws_cli() {
    print_status "Checking AWS CLI..."
    
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI is not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    print_success "AWS CLI is configured"
}

# Function to check if Node.js and npm are installed
check_node() {
    print_status "Checking Node.js and npm..."
    
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install it first."
        exit 1
    fi
    
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed. Please install it first."
        exit 1
    fi
    
    print_success "Node.js and npm are available"
}

# Function to build the React application
build_app() {
    print_status "Building React application..."
    
    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        print_status "Installing dependencies..."
        npm install
    fi
    
    # Load environment variables if .env file exists (for GitHub workflows)
    if [ -f ".env" ]; then
        print_status "Loading environment variables from .env file..."
        set -a
        source .env
        set +a
        print_status "Environment variables loaded successfully"
    fi
    
    # Build the application
    npm run build
    
    if [ ! -d "dist" ]; then
        print_error "Build failed - dist directory not found"
        exit 1
    fi
    
    print_success "Application built successfully"
}

# Function to deploy regional stack (cross-region deployment)
deploy_regional_stack() {
    print_status "Deploying regional stack '$REGIONAL_STACK_NAME' to region '$DEPLOYMENT_REGION'"
    
    # Check if regional stack exists
    if aws cloudformation describe-stacks --stack-name "$REGIONAL_STACK_NAME" --region "$DEPLOYMENT_REGION" &> /dev/null; then
        print_status "Regional stack exists, updating..."
        REGIONAL_OPERATION="update-stack"
        
        # Get existing bucket name from regional stack outputs
        EXISTING_BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name "$REGIONAL_STACK_NAME" --region "$DEPLOYMENT_REGION" --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' --output text 2>/dev/null || echo "")
        
        if [ -n "$EXISTING_BUCKET_NAME" ]; then
            print_status "Using existing bucket name: $EXISTING_BUCKET_NAME"
            UNIQUE_BUCKET_NAME="$EXISTING_BUCKET_NAME"
        else
            print_warning "Could not retrieve existing bucket name, generating new one"
            UNIQUE_BUCKET_NAME="${BUCKET_NAME}-$(openssl rand -hex 4)"
        fi
    else
        print_status "Regional stack doesn't exist, creating..."
        REGIONAL_OPERATION="create-stack"
        UNIQUE_BUCKET_NAME="${BUCKET_NAME}-$(openssl rand -hex 4)"
    fi
    
    print_status "Using bucket name: $UNIQUE_BUCKET_NAME"
    
    # Deploy regional stack
    if [ "$REGIONAL_OPERATION" = "update-stack" ]; then
        # Try to update the stack, handle "No updates" case gracefully
        print_status "Attempting to update regional stack..."
        
        # Capture output and exit code properly
        set +e  # Temporarily disable exit on error
        aws cloudformation $REGIONAL_OPERATION \
            --stack-name "$REGIONAL_STACK_NAME" \
            --template-body file://"$REGIONAL_TEMPLATE" \
            --parameters \
                ParameterKey=BucketName,ParameterValue="$UNIQUE_BUCKET_NAME" \
            --capabilities CAPABILITY_IAM \
            --region "$DEPLOYMENT_REGION" > /tmp/regional_update_output.log 2>&1
        
        REGIONAL_UPDATE_EXIT_CODE=$?
        set -e  # Re-enable exit on error
        
        if [ $REGIONAL_UPDATE_EXIT_CODE -eq 0 ]; then
            # Update succeeded
            print_status "Waiting for regional stack update to complete..."
            aws cloudformation wait stack-update-complete --stack-name "$REGIONAL_STACK_NAME" --region "$DEPLOYMENT_REGION"
            print_success "Regional stack updated successfully"
        else
            # Update failed - check if it's the "No updates" case
            if grep -q "No updates are to be performed" /tmp/regional_update_output.log; then
                print_warning "Regional stack is already up to date, no updates needed"
                print_success "Regional stack validation passed"
            else
                print_error "Failed to update regional stack"
                cat /tmp/regional_update_output.log
                exit 1
            fi
        fi
    else
        # Create new stack
        aws cloudformation $REGIONAL_OPERATION \
            --stack-name "$REGIONAL_STACK_NAME" \
            --template-body file://"$REGIONAL_TEMPLATE" \
            --parameters \
                ParameterKey=BucketName,ParameterValue="$UNIQUE_BUCKET_NAME" \
            --capabilities CAPABILITY_IAM \
            --region "$DEPLOYMENT_REGION"
        
        # Wait for creation completion
        print_status "Waiting for regional stack creation to complete..."
        aws cloudformation wait stack-create-complete --stack-name "$REGIONAL_STACK_NAME" --region "$DEPLOYMENT_REGION"
        print_success "Regional stack created successfully"
    fi
    
    # Get regional stack outputs for global stack parameters
    print_status "Getting regional stack outputs..."
    
    # Wait a moment for outputs to be available
    sleep 5
    
    # Get all required outputs from regional stack
    BUCKET_REGIONAL_DOMAIN_NAME=$(aws cloudformation describe-stacks --stack-name "$REGIONAL_STACK_NAME" --region "$DEPLOYMENT_REGION" --query 'Stacks[0].Outputs[?OutputKey==`BucketRegionalDomainName`].OutputValue' --output text 2>/dev/null || echo "")
    REGIONAL_BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name "$REGIONAL_STACK_NAME" --region "$DEPLOYMENT_REGION" --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' --output text 2>/dev/null || echo "")
    REGIONAL_BUCKET_ARN=$(aws cloudformation describe-stacks --stack-name "$REGIONAL_STACK_NAME" --region "$DEPLOYMENT_REGION" --query 'Stacks[0].Outputs[?OutputKey==`BucketArn`].OutputValue' --output text 2>/dev/null || echo "")
    
    # Validate all required outputs
    if [ -z "$BUCKET_REGIONAL_DOMAIN_NAME" ] || [ -z "$REGIONAL_BUCKET_NAME" ] || [ -z "$REGIONAL_BUCKET_ARN" ]; then
        print_error "Failed to get required outputs from regional stack"
        print_error "Regional stack outputs:"
        aws cloudformation describe-stacks --stack-name "$REGIONAL_STACK_NAME" --region "$DEPLOYMENT_REGION" --query 'Stacks[0].Outputs' --output table 2>/dev/null || echo "Could not retrieve outputs"
        print_error "Missing outputs:"
        [ -z "$BUCKET_REGIONAL_DOMAIN_NAME" ] && print_error "  - BucketRegionalDomainName"
        [ -z "$REGIONAL_BUCKET_NAME" ] && print_error "  - BucketName"  
        [ -z "$REGIONAL_BUCKET_ARN" ] && print_error "  - BucketArn"
        exit 1
    fi
    
    print_success "Regional stack deployed successfully."
    print_status "  Bucket Name: $REGIONAL_BUCKET_NAME"
    print_status "  Bucket Domain: $BUCKET_REGIONAL_DOMAIN_NAME"
    print_status "  Bucket ARN: $REGIONAL_BUCKET_ARN"
}

# Function to deploy global stack (cross-region deployment)
deploy_global_stack() {
    print_status "Deploying global stack '$GLOBAL_STACK_NAME' to region '$AWS_REGION'"
    
    # Check if global stack exists
    if aws cloudformation describe-stacks --stack-name "$GLOBAL_STACK_NAME" --region "$AWS_REGION" &> /dev/null; then
        print_status "Global stack exists, updating..."
        GLOBAL_OPERATION="update-stack"
    else
        print_status "Global stack doesn't exist, creating..."
        GLOBAL_OPERATION="create-stack"
    fi
    
    # Deploy global stack
    if [ "$GLOBAL_OPERATION" = "update-stack" ]; then
        # Try to update the stack, handle "No updates" case gracefully
        print_status "Attempting to update global stack..."
        
        # Capture output and exit code properly
        set +e  # Temporarily disable exit on error
        aws cloudformation $GLOBAL_OPERATION \
            --stack-name "$GLOBAL_STACK_NAME" \
            --template-body file://"$GLOBAL_TEMPLATE" \
            --parameters \
                ParameterKey=DomainName,ParameterValue="$DOMAIN_NAME" \
                ParameterKey=HostedZoneId,ParameterValue="$HOSTED_ZONE_ID" \
                ParameterKey=BucketName,ParameterValue="$UNIQUE_BUCKET_NAME" \
                ParameterKey=RegionalBucketDomainName,ParameterValue="$BUCKET_REGIONAL_DOMAIN_NAME" \
                ParameterKey=DeploymentRegion,ParameterValue="$DEPLOYMENT_REGION" \
                ParameterKey=RegionalBucketName,ParameterValue="$REGIONAL_BUCKET_NAME" \
                ParameterKey=RegionalBucketArn,ParameterValue="$REGIONAL_BUCKET_ARN" \
            --capabilities CAPABILITY_IAM \
            --region "$AWS_REGION" > /tmp/global_update_output.log 2>&1
        
        GLOBAL_UPDATE_EXIT_CODE=$?
        set -e  # Re-enable exit on error
        
        if [ $GLOBAL_UPDATE_EXIT_CODE -eq 0 ]; then
            # Update succeeded
            print_status "Waiting for global stack update to complete..."
            aws cloudformation wait stack-update-complete --stack-name "$GLOBAL_STACK_NAME" --region "$AWS_REGION"
            print_success "Global stack updated successfully"
        else
            # Update failed - check if it's the "No updates" case
            if grep -q "No updates are to be performed" /tmp/global_update_output.log; then
                print_warning "Global stack is already up to date, no updates needed"
                print_success "Global stack validation passed"
            else
                print_error "Failed to update global stack"
                cat /tmp/global_update_output.log
                exit 1
            fi
        fi
    else
        # Create new stack
        aws cloudformation $GLOBAL_OPERATION \
            --stack-name "$GLOBAL_STACK_NAME" \
            --template-body file://"$GLOBAL_TEMPLATE" \
            --parameters \
                ParameterKey=DomainName,ParameterValue="$DOMAIN_NAME" \
                ParameterKey=HostedZoneId,ParameterValue="$HOSTED_ZONE_ID" \
                ParameterKey=BucketName,ParameterValue="$UNIQUE_BUCKET_NAME" \
                ParameterKey=RegionalBucketDomainName,ParameterValue="$BUCKET_REGIONAL_DOMAIN_NAME" \
                ParameterKey=DeploymentRegion,ParameterValue="$DEPLOYMENT_REGION" \
                ParameterKey=RegionalBucketName,ParameterValue="$REGIONAL_BUCKET_NAME" \
                ParameterKey=RegionalBucketArn,ParameterValue="$REGIONAL_BUCKET_ARN" \
            --capabilities CAPABILITY_IAM \
            --region "$AWS_REGION"
        
        # Wait for creation completion
        print_status "Waiting for global stack creation to complete..."
        aws cloudformation wait stack-create-complete --stack-name "$GLOBAL_STACK_NAME" --region "$AWS_REGION"
        print_success "Global stack created successfully"
    fi
}

# Function to create or update CloudFormation stack
deploy_infrastructure() {
    if [ "$CROSS_REGION_DEPLOYMENT" = true ]; then
        print_status "Starting cross-region infrastructure deployment..."
        deploy_regional_stack
        deploy_global_stack
        print_success "Cross-region infrastructure deployed successfully"
        
        # Clean up temporary log files
        rm -f /tmp/regional_update_output.log /tmp/global_update_output.log
    else
        print_status "Deploying single-region infrastructure with CloudFormation..."
        
        # Check if stack exists
        if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" &> /dev/null; then
            print_status "Stack exists, updating..."
            OPERATION="update-stack"
            
            # Get existing bucket name from stack outputs to avoid recreating the bucket
            EXISTING_BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' --output text 2>/dev/null || echo "")
            
            if [ -n "$EXISTING_BUCKET_NAME" ]; then
                print_status "Using existing bucket name: $EXISTING_BUCKET_NAME"
                UNIQUE_BUCKET_NAME="$EXISTING_BUCKET_NAME"
            else
                print_warning "Could not retrieve existing bucket name, generating new one"
                UNIQUE_BUCKET_NAME="${BUCKET_NAME}-$(openssl rand -hex 4)"
            fi
        else
            print_status "Stack doesn't exist, creating..."
            OPERATION="create-stack"
            # Generate a truly unique bucket name only for new stacks
            UNIQUE_BUCKET_NAME="${BUCKET_NAME}-$(openssl rand -hex 4)"
        fi
        
        print_status "Using bucket name: $UNIQUE_BUCKET_NAME"
        
        # Deploy the stack
        if [ "$OPERATION" = "update-stack" ]; then
            # Try to update the stack, handle "No updates" case gracefully
            print_status "Attempting to update stack..."
            
            # Capture output and exit code properly
            set +e  # Temporarily disable exit on error
            aws cloudformation $OPERATION \
                --stack-name "$STACK_NAME" \
                --template-body file://"$CLOUDFORMATION_TEMPLATE" \
                --parameters \
                    ParameterKey=DomainName,ParameterValue="$DOMAIN_NAME" \
                    ParameterKey=HostedZoneId,ParameterValue="$HOSTED_ZONE_ID" \
                    ParameterKey=BucketName,ParameterValue="$UNIQUE_BUCKET_NAME" \
                --capabilities CAPABILITY_IAM \
                --region "$AWS_REGION" > /tmp/single_update_output.log 2>&1
            
            SINGLE_UPDATE_EXIT_CODE=$?
            set -e  # Re-enable exit on error
            
            if [ $SINGLE_UPDATE_EXIT_CODE -eq 0 ]; then
                # Update succeeded
                print_status "Waiting for stack update to complete..."
                aws cloudformation wait stack-update-complete --stack-name "$STACK_NAME" --region "$AWS_REGION"
                print_success "Stack updated successfully"
            else
                # Update failed - check if it's the "No updates" case
                if grep -q "No updates are to be performed" /tmp/single_update_output.log; then
                    print_warning "Stack is already up to date, no updates needed"
                    print_success "Stack validation passed"
                else
                    print_error "Failed to update stack"
                    cat /tmp/single_update_output.log
                    exit 1
                fi
            fi
        else
            # Create new stack
            aws cloudformation $OPERATION \
                --stack-name "$STACK_NAME" \
                --template-body file://"$CLOUDFORMATION_TEMPLATE" \
                --parameters \
                    ParameterKey=DomainName,ParameterValue="$DOMAIN_NAME" \
                    ParameterKey=HostedZoneId,ParameterValue="$HOSTED_ZONE_ID" \
                    ParameterKey=BucketName,ParameterValue="$UNIQUE_BUCKET_NAME" \
                --capabilities CAPABILITY_IAM \
                --region "$AWS_REGION"
            
            # Wait for creation completion
            print_status "Waiting for stack creation to complete..."
            aws cloudformation wait stack-create-complete --stack-name "$STACK_NAME" --region "$AWS_REGION"
            print_success "Stack created successfully"
        fi
        
        print_success "Infrastructure deployed successfully"
        
        # Clean up temporary log files
        rm -f /tmp/single_update_output.log
    fi
}

# Function to get stack outputs
get_stack_outputs() {
    print_status "Getting stack outputs..."
    
    if [ "$CROSS_REGION_DEPLOYMENT" = true ]; then
        # Get outputs from regional stack
        BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name "$REGIONAL_STACK_NAME" --region "$DEPLOYMENT_REGION" --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' --output text)
        
        # Get outputs from global stack
        DISTRIBUTION_ID=$(aws cloudformation describe-stacks --stack-name "$GLOBAL_STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' --output text)
        WEBSITE_URL=$(aws cloudformation describe-stacks --stack-name "$GLOBAL_STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`WebsiteURL`].OutputValue' --output text)
    else
        # Get outputs from single stack
        BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' --output text)
        DISTRIBUTION_ID=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' --output text)
        WEBSITE_URL=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`WebsiteURL`].OutputValue' --output text)
    fi
    
    print_success "Retrieved stack outputs"
}

# Function to deploy files to S3
deploy_to_s3() {
    print_status "Deploying files to S3..."
    
    # Use the correct region for S3 operations (deployment region for cross-region)
    S3_REGION="$DEPLOYMENT_REGION"
    if [ "$CROSS_REGION_DEPLOYMENT" != true ]; then
        S3_REGION="$AWS_REGION"
    fi
    
    # Sync dist folder to S3
    aws s3 sync dist/ s3://"$BUCKET_NAME"/ --delete --region "$S3_REGION"
    
    print_success "Files deployed to S3 (region: $S3_REGION)"
}

# Function to invalidate CloudFront cache
invalidate_cloudfront() {
    print_status "Invalidating CloudFront cache..."
    
    INVALIDATION_ID=$(aws cloudfront create-invalidation \
        --distribution-id "$DISTRIBUTION_ID" \
        --paths "/*" \
        --query 'Invalidation.Id' \
        --output text)
    
    print_status "Invalidation created with ID: $INVALIDATION_ID"
    print_status "Waiting for invalidation to complete..."
    
    aws cloudfront wait invalidation-completed \
        --distribution-id "$DISTRIBUTION_ID" \
        --id "$INVALIDATION_ID"
    
    print_success "CloudFront cache invalidated"
}

# Function to display deployment information
show_deployment_info() {
    echo ""
    echo "======================================"
    echo "🚀 DEPLOYMENT COMPLETED SUCCESSFULLY!"
    echo "======================================"
    echo ""
    echo "📊 Deployment Details:"
    
    if [ "$CROSS_REGION_DEPLOYMENT" = true ]; then
        echo "   Deployment Type: Cross-Region"
        echo "   Regional Stack: $REGIONAL_STACK_NAME (region: $DEPLOYMENT_REGION)"
        echo "   Global Stack: $GLOBAL_STACK_NAME (region: $AWS_REGION)"
        echo "   S3 Bucket: $BUCKET_NAME (region: $DEPLOYMENT_REGION)"
    else
        echo "   Deployment Type: Single-Region"
        echo "   Stack Name: $STACK_NAME (region: $AWS_REGION)"
        echo "   S3 Bucket: $BUCKET_NAME (region: $AWS_REGION)"
    fi
    
    echo "   CloudFront Distribution ID: $DISTRIBUTION_ID"
    echo "   Website URL: $WEBSITE_URL"
    echo ""
    echo "🔗 Your application is available at:"
    echo "   $WEBSITE_URL"
    echo ""
    echo "⚠️  Note: SSL certificate validation may take a few minutes."
    echo "   If you get SSL errors, wait a few minutes and try again."
    echo ""
}

# Main deployment function
main() {
    echo "🚀 Starting TMF ODA Transformer UI Deployment"
    echo "=============================================="
    echo "Environment: $ENVIRONMENT"
    if [ "$CROSS_REGION_DEPLOYMENT" = true ]; then
        echo "Deployment Type: Cross-Region ($AWS_REGION -> $DEPLOYMENT_REGION)"
    else
        echo "Deployment Type: Single-Region ($AWS_REGION)"
    fi
    echo "=============================================="
    
    # Configuration should already be loaded
    if [ -z "$ENVIRONMENT" ]; then
        print_error "Environment not specified. Use: $0 <environment> [options]"
        exit 1
    fi
    
    # Pre-deployment checks
    check_aws_cli
    check_node
    
    # Build and deploy
    build_app
    deploy_infrastructure
    get_stack_outputs
    deploy_to_s3
    invalidate_cloudfront
    
    # Show results
    show_deployment_info
}

# Main deployment function with external role
main_with_external_role() {
    echo "🚀 Starting TMF ODA Transformer UI Deployment (External Role)"
    echo "==============================================================="
    echo "Environment: $ENVIRONMENT"
    if [ "$CROSS_REGION_DEPLOYMENT" = true ]; then
        echo "Deployment Type: Cross-Region ($AWS_REGION -> $DEPLOYMENT_REGION)"
    else
        echo "Deployment Type: Single-Region ($AWS_REGION)"
    fi
    echo "==============================================================="
    
    # Configuration should already be loaded
    if [ -z "$ENVIRONMENT" ]; then
        print_error "Environment not specified. Use: $0 <environment> external-aws [options]"
        exit 1
    fi
    
    # Assume external role first
    assume_external_role
    
    # Pre-deployment checks (AWS CLI already verified in assume_external_role)
    check_node
    
    # Build and deploy
    build_app
    deploy_infrastructure
    get_stack_outputs
    deploy_to_s3
    invalidate_cloudfront
    
    # Show results
    show_deployment_info
}

# Function to show usage
show_usage() {
    echo "Usage: $0 <environment> [command]"
    echo ""
    echo "Environments:"
    echo "  dev   - Development environment (dev.econet.totogicore.com)"
    echo "  stage - Staging environment (stage.econet.totogicore.com)"
    echo "  prod  - Production environment (econet.totogicore.com)"
    echo ""
    echo "Commands (optional):"
    echo "  build-only           - Only build the React application"
    echo "  deploy-only          - Only deploy files to existing infrastructure"
    echo "  infrastructure-only  - Only deploy/update infrastructure"
    echo "  external-aws         - Full deployment with external AWS role"
    echo "  external-aws-build-only          - Only build with external role"
    echo "  external-aws-deploy-only         - Only deploy with external role"
    echo "  external-aws-infrastructure-only - Only deploy infrastructure with external role"
    echo "  (no command)        - Full deployment (build + infrastructure + deploy)"
    echo ""
    echo "Examples:"
    echo "  $0 dev                    # Deploy to development environment"
    echo "  $0 stage                  # Deploy to staging environment"
    echo "  $0 prod                   # Deploy to production environment"
    echo "  $0 stage build-only       # Only build for staging environment"
    echo "  $0 prod external-aws      # Deploy to prod with external AWS role"
}

# Validate and process arguments
if [ $# -eq 0 ]; then
    show_usage
    exit 1
fi

# First argument should be environment
ENVIRONMENT_ARG="$1"
shift

# Validate environment
valid_env=false
for env in "${AVAILABLE_ENVIRONMENTS[@]}"; do
    if [ "$ENVIRONMENT_ARG" = "$env" ]; then
        valid_env=true
        break
    fi
done

if [ "$valid_env" = false ]; then
    print_error "Invalid environment: $ENVIRONMENT_ARG"
    print_error "Available environments: ${AVAILABLE_ENVIRONMENTS[*]}"
    show_usage
    exit 1
fi

# Load environment configuration
load_config "$ENVIRONMENT_ARG"

# Handle remaining arguments (commands)
case "${1:-}" in
    "build-only")
        check_node
        build_app
        print_success "Build completed for $ENVIRONMENT environment"
        ;;
    "deploy-only")
        check_aws_cli
        get_stack_outputs
        deploy_to_s3
        invalidate_cloudfront
        print_success "Deployment completed for $ENVIRONMENT environment"
        ;;
    "infrastructure-only")
        check_aws_cli
        deploy_infrastructure
        print_success "Infrastructure deployment completed for $ENVIRONMENT environment"
        ;;
    "external-aws")
        main_with_external_role
        ;;
    "external-aws-build-only")
        assume_external_role
        check_node
        build_app
        print_success "Build completed for $ENVIRONMENT environment (with external role)"
        ;;
    "external-aws-deploy-only")
        assume_external_role
        get_stack_outputs
        deploy_to_s3
        invalidate_cloudfront
        print_success "Deployment completed for $ENVIRONMENT environment (with external role)"
        ;;
    "external-aws-infrastructure-only")
        assume_external_role
        deploy_infrastructure
        print_success "Infrastructure deployment completed for $ENVIRONMENT environment (with external role)"
        ;;
    "")
        main
        ;;
    *)
        print_error "Unknown command: $1"
        show_usage
        exit 1
        ;;
esac 