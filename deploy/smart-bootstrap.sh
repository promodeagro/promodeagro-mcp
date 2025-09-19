#!/bin/bash

echo "🔍 Checking if CDK resources already exist..."

# Ensure we're using the correct AWS profile
if [ -z "$AWS_PROFILE" ]; then
    echo "⚠️  AWS_PROFILE not set. Make sure to set it to 'external-access'"
    echo "Run: export AWS_PROFILE=external-access"
    exit 1
fi

echo "📋 Using AWS Profile: $AWS_PROFILE"

# Get current AWS account and region dynamically
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "764119721991")
REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")
QUALIFIER="alerteng"  # Project-specific CDK qualifier (alphanumeric, max 10 chars)

# Build resource names dynamically
S3_BUCKET="cdk-${QUALIFIER}-assets-${ACCOUNT_ID}-${REGION}"
ECR_REPO="cdk-${QUALIFIER}-container-assets-${ACCOUNT_ID}-${REGION}"

echo "📍 Account: ${ACCOUNT_ID}, Region: ${REGION}"
echo "📦 S3 Bucket: ${S3_BUCKET}"
echo "🐳 ECR Repo: ${ECR_REPO}"

# Check if S3 bucket exists
if aws s3 ls "s3://${S3_BUCKET}" 2>/dev/null; then
    echo "✅ S3 bucket already exists"
    S3_EXISTS=true
else
    echo "❌ S3 bucket needs to be created"
    S3_EXISTS=false
fi

# Check if ECR repository exists
if aws ecr describe-repositories --repository-names "${ECR_REPO}" 2>/dev/null; then
    echo "✅ ECR repository already exists"
    ECR_EXISTS=true
else
    echo "❌ ECR repository needs to be created"
    ECR_EXISTS=false
fi

# Check if CDKToolkit stack exists and is usable
if aws cloudformation describe-stacks --stack-name CDKToolkit 2>/dev/null | grep -q "CREATE_COMPLETE\|UPDATE_COMPLETE"; then
    echo "✅ CDKToolkit stack is healthy"
    echo "🎉 Bootstrap not needed - ready to deploy!"
    exit 0
fi

# If we get here, we need to bootstrap
if [ "$S3_EXISTS" = true ] && [ "$ECR_EXISTS" = true ]; then
    echo "🔧 Resources exist but stack is broken. Using existing resources..."
    # Try deployment without bootstrap
    echo "✨ Attempting deployment with existing resources..."
else
    echo "❌ Bootstrap required but permissions insufficient"
    echo "💡 Deploy non-Docker stacks first, or fix IAM permissions"
    exit 1
fi
