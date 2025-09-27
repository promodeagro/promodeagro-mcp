#!/bin/bash

# E-commerce MCP Server GitHub Actions Integration Setup Script
# This script helps you set up the complete GitHub Actions integration for the MCP server project

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

print_header() {
    echo
    print_color $BLUE "=== $1 ==="
    echo
}

print_header "E-commerce MCP Server GitHub Actions Integration Setup"

# Check if we're in the right directory
if [ ! -f "github-oidc-setup.yml" ]; then
    print_color $RED "Error: Please run this script from the git-workflow directory"
    exit 1
fi

# Get GitHub repository information
print_color $YELLOW "Please provide your GitHub repository information:"
read -p "GitHub username/organization [promodeagro]: " GITHUB_ORG
GITHUB_ORG=${GITHUB_ORG:-promodeagro}

read -p "Repository name [promodeagro-mcp]: " GITHUB_REPO
GITHUB_REPO=${GITHUB_REPO:-promodeagro-mcp}

read -p "Branch for deployment [dev]: " BRANCH_NAME
BRANCH_NAME=${BRANCH_NAME:-dev}

print_header "Step 1: Check OIDC Provider and Deploy IAM Role"

# Check if OIDC provider already exists
print_color $YELLOW "Checking if GitHub OIDC provider already exists..."
OIDC_PROVIDER_ARN=$(aws iam list-open-id-connect-providers --query "OpenIDConnectProviderList[?contains(Arn, 'token.actions.githubusercontent.com')].Arn" --output text)

if [ -n "$OIDC_PROVIDER_ARN" ]; then
    print_color $GREEN "✓ Found existing GitHub OIDC provider: $OIDC_PROVIDER_ARN"
    print_color $YELLOW "Using existing OIDC provider and creating only the IAM role..."
    
    # Deploy only the IAM role using the role-only template
    aws cloudformation deploy \
        --template-file ./github-role-only.yml \
        --stack-name github-actions-role-promodeagro-mcp-${BRANCH_NAME} \
        --parameter-overrides \
            GitHubOrganization=$GITHUB_ORG \
            GitHubRepository=$GITHUB_REPO \
            BranchName=$BRANCH_NAME \
        --capabilities CAPABILITY_NAMED_IAM \
        --region us-east-1

    if [ $? -eq 0 ]; then
        print_color $GREEN "✓ IAM role deployed successfully"
    else
        print_color $RED "✗ IAM role deployment failed"
        exit 1
    fi

    # Get the role ARN from the role-only stack
    ROLE_ARN=$(aws cloudformation describe-stacks \
        --stack-name github-actions-role-promodeagro-mcp-${BRANCH_NAME} \
        --query "Stacks[0].Outputs[?OutputKey=='GitHubActionsRoleArn'].OutputValue" \
        --output text \
        --region us-east-1)
else
    print_color $YELLOW "OIDC provider not found. Deploying complete OIDC setup..."
    
    # Deploy the OIDC stack
    aws cloudformation deploy \
        --template-file ./github-oidc-setup.yml \
        --stack-name github-actions-oidc-promodeagro-mcp \
        --parameter-overrides \
            GitHubOrganization=$GITHUB_ORG \
            GitHubRepository=$GITHUB_REPO \
            BranchName=$BRANCH_NAME \
        --capabilities CAPABILITY_NAMED_IAM \
        --region us-east-1

    if [ $? -eq 0 ]; then
        print_color $GREEN "✓ OIDC stack deployed successfully"
    else
        print_color $RED "✗ OIDC stack deployment failed"
        print_color $YELLOW "This might be due to AWS CLI version or existing resources."
        print_color $YELLOW "Try using the simple setup script instead:"
        print_color $BLUE "./setup-github-integration-simple.sh"
        exit 1
    fi

    # Get the role ARN from the OIDC stack
    ROLE_ARN=$(aws cloudformation describe-stacks \
        --stack-name github-actions-oidc-promodeagro-mcp \
        --query "Stacks[0].Outputs[?OutputKey=='GitHubActionsRoleArn'].OutputValue" \
        --output text \
        --region us-east-1)
fi

print_header "Step 2: Configure GitHub Secrets"

print_color $GREEN "OIDC Role ARN: $ROLE_ARN"
echo

print_color $YELLOW "Now you need to add the following secrets to your GitHub repository:"
print_color $BLUE "Go to: https://github.com/$GITHUB_ORG/$GITHUB_REPO/settings/secrets/actions"
echo

# Determine secret suffix based on branch
SECRET_SUFFIX=""
case $BRANCH_NAME in
    "dev"|"development")
        SECRET_SUFFIX="_DEV"
        ;;
    "stage"|"staging")  
        SECRET_SUFFIX="_STAGE"
        ;;
    "main"|"production"|"prod")
        SECRET_SUFFIX="_PROD"
        ;;
esac

echo "Add these repository secrets:"
echo "┌──────────────────────────────────────────────────────────────────────────────────────────┐"
echo "│ Secret Name                    │ Value                                                     │"
echo "├──────────────────────────────────────────────────────────────────────────────────────────┤"
printf "│ %-30s │ %-57s │\n" "AWS_ROLE_TO_ASSUME${SECRET_SUFFIX}" "$ROLE_ARN"
echo "├──────────────────────────────────────────────────────────────────────────────────────────┤"
printf "│ %-30s │ %-57s │\n" "AWS_REGION" "${AWS_REGION:-us-east-1}"
echo "└──────────────────────────────────────────────────────────────────────────────────────────┘"
echo

print_header "Step 3: Test the Integration"

print_color $YELLOW "To test the GitHub Actions integration:"
echo "1. Push code to the '$BRANCH_NAME' branch"
echo "2. Check the Actions tab in your GitHub repository"
echo "3. Monitor the deployment progress"
echo

print_color $GREEN "✓ GitHub Actions integration setup complete!"

print_header "E-commerce MCP Server Specific Configuration" 

print_color $BLUE "Your promodeagro-mcp project is now configured for:"
echo "• MCP server deployment to AWS infrastructure"
echo "• Multi-environment support (dev/stage/prod)"  
echo "• Automatic CloudFormation stack management"
echo "• Health checks for MCP server endpoints"
echo "• SSL/TLS certificate management"
echo "• Container orchestration and scaling"
echo

print_header "Additional Recommendations"

print_color $YELLOW "Consider adding these optional enhancements:"
echo "• Branch protection rules for '$BRANCH_NAME'"
echo "• Required status checks before merging"
echo "• Deployment approvals for production"
echo "• Slack/Discord notifications for deployment status"
echo "• Cost monitoring alerts"
echo "• Performance monitoring for website"
echo

print_color $BLUE "For production deployments, also set up:"
echo "• A separate 'main' or 'production' branch workflow"
echo "• Manual approval steps for production deployments"
echo "• Blue/green deployment with container orchestration"
echo "• Enhanced monitoring and alerting"
echo "• Performance optimization and scaling"
echo

print_color $GREEN "E-commerce MCP Server deployment ready! 🚀"
