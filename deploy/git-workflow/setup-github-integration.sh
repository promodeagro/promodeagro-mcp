#!/bin/bash

# Alert Engine GitHub Actions Integration Setup Script
# This script helps you set up the complete GitHub Actions integration

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

print_header "Alert Engine GitHub Actions CDK Integration Setup"

# Check if we're in the right directory
if [ ! -f "cdk.json" ]; then
    print_color $RED "Error: Please run this script from the deploy directory"
    exit 1
fi

# Get GitHub repository information
print_color $YELLOW "Please provide your GitHub repository information:"
read -p "GitHub username/organization [trilogy-group]: " GITHUB_ORG
GITHUB_ORG=${GITHUB_ORG:-trilogy-group}

read -p "Repository name [alert-engine]: " GITHUB_REPO
GITHUB_REPO=${GITHUB_REPO:-alert-engine}

read -p "Branch for deployment [dev]: " BRANCH_NAME
BRANCH_NAME=${BRANCH_NAME:-dev}

print_header "Step 1: Deploy OIDC CloudFormation Stack"

print_color $YELLOW "Deploying CloudFormation stack for GitHub OIDC integration..."

# Deploy the OIDC stack
aws cloudformation deploy \
    --template-file github-oidc-setup.yml \
    --stack-name github-actions-oidc-alert-engine \
    --parameter-overrides \
        GitHubOrganization=$GITHUB_ORG \
        GitHubRepository=$GITHUB_REPO \
        BranchName=$BRANCH_NAME \
    --capabilities CAPABILITY_NAMED_IAM \
    --region ${AWS_REGION:-us-east-1}

if [ $? -eq 0 ]; then
    print_color $GREEN "✓ OIDC stack deployed successfully"
else
    print_color $RED "✗ OIDC stack deployment failed"
    exit 1
fi

# Get the role ARN
ROLE_ARN=$(aws cloudformation describe-stacks \
    --stack-name github-actions-oidc-alert-engine \
    --query "Stacks[0].Outputs[?OutputKey=='GitHubActionsRoleArn'].OutputValue" \
    --output text \
    --region ${AWS_REGION:-us-east-1})

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
printf "│ %-30s │ %-57s │\n" "SECRETS_ARN${SECRET_SUFFIX}" "(your AWS Secrets Manager ARN for ${BRANCH_NAME})"
echo "└──────────────────────────────────────────────────────────────────────────────────────────┘"
echo

print_header "Step 3: Test the Integration"

print_color $YELLOW "To test the GitHub Actions integration:"
echo "1. Push code to the '$BRANCH_NAME' branch"
echo "2. Check the Actions tab in your GitHub repository"
echo "3. Monitor the deployment progress"
echo

print_color $GREEN "✓ GitHub Actions integration setup complete!"

print_header "Alert Engine Specific Configuration" 

print_color $BLUE "Your alert-engine project is now configured for:"
echo "• MCP Server deployment"
echo "• Multi-environment support (dev/stage/prod)"  
echo "• Automatic CDK bootstrap"
echo "• Health checks for MCP server endpoints"
echo "• Alert engine specific secrets management"
echo

print_header "Additional Recommendations"

print_color $YELLOW "Consider adding these optional enhancements:"
echo "• Branch protection rules for '$BRANCH_NAME'"
echo "• Required status checks before merging"
echo "• Deployment approvals for production"
echo "• Slack/Discord notifications for deployment status"
echo "• Cost monitoring alerts"
echo "• Set up AWS Secrets Manager for sensitive data"
echo

print_color $BLUE "For production deployments, also set up:"
echo "• A separate 'main' or 'production' branch workflow"
echo "• Manual approval steps for production deployments"
echo "• Blue/green deployment strategy"
echo "• Enhanced monitoring and alerting"
echo

print_color $GREEN "Alert Engine deployment ready! 🚀"
