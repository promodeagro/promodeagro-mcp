#!/bin/bash

# Alert Engine GitHub Actions CDK Integration Setup (Minimal Permissions Version)
# This version works with limited IAM permissions

set -e

echo "=== Alert Engine GitHub Actions CDK Integration Setup (Minimal) ==="
echo

# Configuration
DEFAULT_REGION="us-east-1"
DEFAULT_ACCOUNT_ID="764119721991"
DEFAULT_GITHUB_ORG="yourgithuborg"
DEFAULT_REPO="alert-engine"
DEFAULT_BRANCH="dev"

# Check if we're in the right directory
if [[ ! -f "cdk.json" ]]; then
    echo "❌ Error: cdk.json not found. Please run this script from the deploy directory."
    exit 1
fi

echo "📋 This script will provide you with the CloudFormation templates and instructions"
echo "   to manually set up GitHub Actions integration for the Alert Engine project."
echo

# Get user input
read -p "🔧 GitHub Organization (default: $DEFAULT_GITHUB_ORG): " GITHUB_ORG
GITHUB_ORG=${GITHUB_ORG:-$DEFAULT_GITHUB_ORG}

read -p "🔧 Repository name (default: $DEFAULT_REPO): " REPO_NAME
REPO_NAME=${REPO_NAME:-$DEFAULT_REPO}

read -p "🔧 AWS Account ID (default: $DEFAULT_ACCOUNT_ID): " ACCOUNT_ID
ACCOUNT_ID=${ACCOUNT_ID:-$DEFAULT_ACCOUNT_ID}

read -p "🔧 AWS Region (default: $DEFAULT_REGION): " AWS_REGION
AWS_REGION=${AWS_REGION:-$DEFAULT_REGION}

echo
echo "📝 Configuration:"
echo "   GitHub: $GITHUB_ORG/$REPO_NAME"
echo "   AWS Account: $ACCOUNT_ID"
echo "   AWS Region: $AWS_REGION"
echo

# Create CloudFormation template for GitHub role (assumes OIDC provider exists)
cat > "github-role-minimal.yml" << EOF
AWSTemplateFormatVersion: '2010-09-09'
Description: 'GitHub Actions Role for Alert Engine (assumes OIDC provider exists)'

Parameters:
  GitHubOrganization:
    Type: String
    Default: "$GITHUB_ORG"
    Description: GitHub organization name
  
  GitHubRepository:
    Type: String
    Default: "$REPO_NAME" 
    Description: GitHub repository name
    
  BranchName:
    Type: String
    Default: "$DEFAULT_BRANCH"
    Description: GitHub branch name
    
  Environment:
    Type: String
    Default: "dev"
    Description: Environment name (dev/stage/prod)

Resources:
  GitHubActionsRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub 'GitHubActionsRole-\${GitHubRepository}-\${Environment}'
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Federated: !Sub 'arn:aws:iam::\${AWS::AccountId}:oidc-provider/token.actions.githubusercontent.com'
            Action: sts:AssumeRoleWithWebIdentity
            Condition:
              StringEquals:
                'token.actions.githubusercontent.com:aud': sts.amazonaws.com
              StringLike:
                'token.actions.githubusercontent.com:sub': 
                  - !Sub 'repo:\${GitHubOrganization}/\${GitHubRepository}:ref:refs/heads/\${BranchName}'
                  - !Sub 'repo:\${GitHubOrganization}/\${GitHubRepository}:ref:refs/heads/main'
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/AdministratorAccess
      Tags:
        - Key: Purpose
          Value: GitHubActions
        - Key: Repository
          Value: !Ref GitHubRepository
        - Key: Environment 
          Value: !Ref Environment

Outputs:
  GitHubActionsRoleArn:
    Description: ARN of the GitHub Actions Role
    Value: !GetAtt GitHubActionsRole.Arn
    Export:
      Name: !Sub '\${AWS::StackName}-GitHubActionsRoleArn'
EOF

echo "✅ Created CloudFormation template: github-role-minimal.yml"
echo

# Create deployment instructions
cat > "MANUAL_SETUP_INSTRUCTIONS.md" << EOF
# Manual GitHub Actions Setup Instructions

## Step 1: Deploy IAM Role for Each Environment

### Development Environment
\`\`\`bash
aws cloudformation deploy \\
  --template-file github-role-minimal.yml \\
  --stack-name github-actions-role-alert-engine-dev \\
  --parameter-overrides \\
    GitHubOrganization=$GITHUB_ORG \\
    GitHubRepository=$REPO_NAME \\
    BranchName=dev \\
    Environment=dev \\
  --capabilities CAPABILITY_NAMED_IAM \\
  --region $AWS_REGION
\`\`\`

### Staging Environment (Optional)
\`\`\`bash
aws cloudformation deploy \\
  --template-file github-role-minimal.yml \\
  --stack-name github-actions-role-alert-engine-stage \\
  --parameter-overrides \\
    GitHubOrganization=$GITHUB_ORG \\
    GitHubRepository=$REPO_NAME \\
    BranchName=stage \\
    Environment=stage \\
  --capabilities CAPABILITY_NAMED_IAM \\
  --region $AWS_REGION
\`\`\`

### Production Environment (Optional)
\`\`\`bash
aws cloudformation deploy \\
  --template-file github-role-minimal.yml \\
  --stack-name github-actions-role-alert-engine-prod \\
  --parameter-overrides \\
    GitHubOrganization=$GITHUB_ORG \\
    GitHubRepository=$REPO_NAME \\
    BranchName=main \\
    Environment=prod \\
  --capabilities CAPABILITY_NAMED_IAM \\
  --region $AWS_REGION
\`\`\`

## Step 2: Get Role ARNs

\`\`\`bash
# Development
DEV_ROLE_ARN=\$(aws cloudformation describe-stacks \\
  --stack-name github-actions-role-alert-engine-dev \\
  --query "Stacks[0].Outputs[?OutputKey=='GitHubActionsRoleArn'].OutputValue" \\
  --output text \\
  --region $AWS_REGION)

# Staging  
STAGE_ROLE_ARN=\$(aws cloudformation describe-stacks \\
  --stack-name github-actions-role-alert-engine-stage \\
  --query "Stacks[0].Outputs[?OutputKey=='GitHubActionsRoleArn'].OutputValue" \\
  --output text \\
  --region $AWS_REGION)

# Production
PROD_ROLE_ARN=\$(aws cloudformation describe-stacks \\
  --stack-name github-actions-role-alert-engine-prod \\
  --query "Stacks[0].Outputs[?OutputKey=='GitHubActionsRoleArn'].OutputValue" \\
  --output text \\
  --region $AWS_REGION)

echo "Development Role ARN: \$DEV_ROLE_ARN"
echo "Staging Role ARN: \$STAGE_ROLE_ARN" 
echo "Production Role ARN: \$PROD_ROLE_ARN"
\`\`\`

## Step 3: Create AWS Secrets Manager Secrets

\`\`\`bash
# Development secrets
aws secretsmanager create-secret \\
  --name "alert-engine-dev-secrets" \\
  --description "Alert Engine Development Environment Secrets" \\
  --secret-string '{"DATABASE_URL":"your-dev-db-url","API_KEY":"your-dev-api-key"}' \\
  --region $AWS_REGION

# Get secrets ARN
DEV_SECRETS_ARN=\$(aws secretsmanager describe-secret \\
  --secret-id "alert-engine-dev-secrets" \\
  --query "ARN" \\
  --output text \\
  --region $AWS_REGION)

echo "Development Secrets ARN: \$DEV_SECRETS_ARN"
\`\`\`

## Step 4: Add GitHub Secrets

Go to: https://github.com/$GITHUB_ORG/$REPO_NAME/settings/secrets/actions

Add these secrets:

| Secret Name | Value |
|-------------|-------|
| AWS_ROLE_TO_ASSUME_DEV | [DEV_ROLE_ARN from Step 2] |
| SECRETS_ARN_DEV | [DEV_SECRETS_ARN from Step 3] |
| AWS_ROLE_TO_ASSUME_STAGE | [STAGE_ROLE_ARN from Step 2] |
| SECRETS_ARN_STAGE | [STAGE_SECRETS_ARN from Step 3] |
| AWS_ROLE_TO_ASSUME_PROD | [PROD_ROLE_ARN from Step 2] |
| SECRETS_ARN_PROD | [PROD_SECRETS_ARN from Step 3] |

## Step 5: Test GitHub Actions

1. Push to dev branch to trigger development deployment
2. Check Actions tab in GitHub repository
3. Review logs for any issues

## Prerequisites

This setup assumes:
- GitHub OIDC provider already exists: token.actions.githubusercontent.com
- Your AWS account has this OIDC provider configured
- You have permissions to create IAM roles and CloudFormation stacks

If the OIDC provider doesn't exist, you'll need to create it first or ask your AWS administrator to create it.
EOF

echo "✅ Created setup instructions: MANUAL_SETUP_INSTRUCTIONS.md"
echo

echo "🎯 NEXT STEPS:"
echo
echo "1. 📖 Read MANUAL_SETUP_INSTRUCTIONS.md for detailed steps"
echo "2. 🔐 If you get permission errors, ask your AWS admin to:"
echo "   - Add the permissions from iam-github-permissions.json to your role"
echo "   - Or run the CloudFormation commands for you"
echo "3. 🚀 Follow the instructions to deploy the IAM roles"
echo "4. 🔑 Add the secrets to GitHub repository settings"
echo
echo "📁 Files created:"
echo "   - github-role-minimal.yml (CloudFormation template)"
echo "   - MANUAL_SETUP_INSTRUCTIONS.md (Step-by-step guide)"  
echo "   - iam-github-permissions.json (Required IAM permissions)"
echo

read -p "🤔 Do you want to try deploying the development role now? (y/N): " DEPLOY_NOW
if [[ $DEPLOY_NOW =~ ^[Yy]$ ]]; then
    echo
    echo "🚀 Deploying development role..."
    aws cloudformation deploy \
      --template-file github-role-minimal.yml \
      --stack-name github-actions-role-alert-engine-dev \
      --parameter-overrides \
        GitHubOrganization=$GITHUB_ORG \
        GitHubRepository=$REPO_NAME \
        BranchName=dev \
        Environment=dev \
      --capabilities CAPABILITY_NAMED_IAM \
      --region $AWS_REGION
    
    if [ $? -eq 0 ]; then
        echo "✅ Development role deployed successfully!"
        
        DEV_ROLE_ARN=$(aws cloudformation describe-stacks \
          --stack-name github-actions-role-alert-engine-dev \
          --query "Stacks[0].Outputs[?OutputKey=='GitHubActionsRoleArn'].OutputValue" \
          --output text \
          --region $AWS_REGION)
        
        echo
        echo "🔑 Add this to GitHub secrets:"
        echo "   AWS_ROLE_TO_ASSUME_DEV = $DEV_ROLE_ARN"
        echo
    else
        echo "❌ Deployment failed. Check the error above."
    fi
else
    echo "👍 No problem! Follow MANUAL_SETUP_INSTRUCTIONS.md when you're ready."
fi

echo
echo "✨ Setup complete! Check GITHUB_WORKFLOWS_README.md for usage instructions."
