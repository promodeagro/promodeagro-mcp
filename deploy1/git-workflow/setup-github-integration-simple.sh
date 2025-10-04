#!/bin/bash

# Alert Engine UI GitHub Actions Integration Setup Script
# Uses the existing OIDC provider and creates only the IAM role

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

print_header "Alert Engine UI GitHub Actions Integration Setup"

# Check if we're in the right directory
if [ ! -f "cloudformation-template.yaml" ]; then
    print_color $RED "Error: Please run this script from the deploy directory"
    exit 1
fi

# Verify OIDC provider exists
print_color $YELLOW "Checking for existing GitHub OIDC provider..."
OIDC_PROVIDER_ARN=$(aws iam list-open-id-connect-providers --query "OpenIDConnectProviderList[?contains(Arn, 'token.actions.githubusercontent.com')].Arn" --output text)

if [ -z "$OIDC_PROVIDER_ARN" ]; then
    print_color $RED "GitHub OIDC provider not found. Please create it first or use the full setup."
    exit 1
fi

print_color $GREEN "✓ Found existing GitHub OIDC provider: $OIDC_PROVIDER_ARN"

# Get GitHub repository information
print_color $YELLOW "Please provide your GitHub repository information:"
read -p "GitHub username/organization [trilogy-group]: " GITHUB_ORG
GITHUB_ORG=${GITHUB_ORG:-trilogy-group}

read -p "Repository name [alert-engine-ui]: " GITHUB_REPO
GITHUB_REPO=${GITHUB_REPO:-alert-engine-ui}

read -p "Branch for deployment [dev]: " BRANCH_NAME
BRANCH_NAME=${BRANCH_NAME:-dev}

print_header "Step 1: Deploy IAM Role CloudFormation Stack"

print_color $YELLOW "Deploying CloudFormation stack for GitHub Actions IAM role..."

# Deploy the role-only stack
aws cloudformation deploy \
    --template-file ./git-workflow/github-role-only.yml \
    --stack-name github-actions-role-alert-engine-ui-${BRANCH_NAME} \
    --parameter-overrides \
        GitHubOrganization=$GITHUB_ORG \
        GitHubRepository=$GITHUB_REPO \
        BranchName=$BRANCH_NAME \
    --capabilities CAPABILITY_NAMED_IAM \
    --region ${AWS_REGION:-us-east-1}

if [ $? -eq 0 ]; then
    print_color $GREEN "✓ IAM role deployed successfully"
else
    print_color $RED "✗ IAM role deployment failed"
    exit 1
fi

# Get the role ARN
ROLE_ARN=$(aws cloudformation describe-stacks \
    --stack-name github-actions-role-alert-engine-ui-${BRANCH_NAME} \
    --query "Stacks[0].Outputs[?OutputKey=='GitHubActionsRoleArn'].OutputValue" \
    --output text \
    --region ${AWS_REGION:-us-east-1})

print_header "Step 2: Configure GitHub Secrets"

print_color $GREEN "GitHub Actions Role ARN: $ROLE_ARN"
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

# Create additional roles for other environments if requested
print_color $YELLOW "Do you want to create roles for other environments? (y/N)"
read -p "Create additional environment roles: " CREATE_MORE

if [[ $CREATE_MORE =~ ^[Yy]$ ]]; then
    for ENV in "stage" "prod"; do
        ENV_BRANCH="stage"
        if [ "$ENV" = "prod" ]; then
            ENV_BRANCH="main"
        fi
        
        print_color $YELLOW "Creating $ENV environment role (branch: $ENV_BRANCH)..."
        
        aws cloudformation deploy \
            --template-file ./git-workflow/github-role-only.yml \
            --stack-name github-actions-role-alert-engine-ui-${ENV} \
            --parameter-overrides \
                GitHubOrganization=$GITHUB_ORG \
                GitHubRepository=$GITHUB_REPO \
                BranchName=$ENV_BRANCH \
            --capabilities CAPABILITY_NAMED_IAM \
            --region ${AWS_REGION:-us-east-1}
        
        ENV_ROLE_ARN=$(aws cloudformation describe-stacks \
            --stack-name github-actions-role-alert-engine-ui-${ENV} \
            --query "Stacks[0].Outputs[?OutputKey=='GitHubActionsRoleArn'].OutputValue" \
            --output text \
            --region ${AWS_REGION:-us-east-1})
        
        ENV_SUFFIX=""
        if [ "$ENV" = "stage" ]; then
            ENV_SUFFIX="_STAGE"
        elif [ "$ENV" = "prod" ]; then
            ENV_SUFFIX="_PROD"
        fi
        
        print_color $GREEN "✓ $ENV Role ARN: $ENV_ROLE_ARN"
        echo "  Add as: AWS_ROLE_TO_ASSUME${ENV_SUFFIX}"
        echo "  Also add: SECRETS_ARN${ENV_SUFFIX}"
        echo
    done
fi

print_header "Step 3: Test the Integration"

print_color $YELLOW "To test the GitHub Actions integration:"
echo "1. Push code to the '$BRANCH_NAME' branch"
echo "2. Check the Actions tab in your GitHub repository"
echo "3. Monitor the deployment progress"
echo

print_color $GREEN "✓ GitHub Actions integration setup complete!"

print_header "Next Steps"

print_color $YELLOW "1. Add the secrets to GitHub (see table above)"
print_color $YELLOW "2. Create a '$BRANCH_NAME' branch if it doesn't exist" 
print_color $YELLOW "3. Ensure your domain and SSL certificate are configured in AWS"
print_color $YELLOW "4. Push your code to trigger the first deployment"
echo

print_header "Alert Engine UI Specific Configuration"
print_color $BLUE "Your alert-engine-ui project is now configured for:"
echo "• React application deployment to S3/CloudFront"
echo "• Multi-environment support (dev/stage/prod)"
echo "• Automatic CloudFormation stack management"
echo "• Health checks for static website endpoints"
echo "• SSL/TLS certificate management"
echo

print_color $GREEN "Alert Engine UI deployment ready! 🚀"
