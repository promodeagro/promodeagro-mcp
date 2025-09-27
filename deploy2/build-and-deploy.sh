#!/bin/bash

# E-commerce MCP Server - Build, Push, and Deploy Script
set -e

# Load configuration
if [ -f "config/dev.conf" ]; then
    source config/dev.conf
else
    echo "❌ Configuration file config/dev.conf not found"
    exit 1
fi

# Extract ECR details from DOCKER_IMAGE_URI
ECR_REGISTRY=$(echo $DOCKER_IMAGE_URI | cut -d'/' -f1)
ECR_REPOSITORY=$(echo $DOCKER_IMAGE_URI | cut -d'/' -f2 | cut -d':' -f1)
IMAGE_TAG=$(echo $DOCKER_IMAGE_URI | cut -d':' -f2)

echo "🚀 E-commerce MCP Server - Build, Push, and Deploy"
echo "   Registry: $ECR_REGISTRY"
echo "   Repository: $ECR_REPOSITORY"
echo "   Tag: $IMAGE_TAG"
echo ""

# Step 1: Check if ECR repository exists
echo "🔍 Checking ECR repository..."
if ! aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION >/dev/null 2>&1; then
    echo "📦 Creating ECR repository: $ECR_REPOSITORY"
    aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION
else
    echo "✅ ECR repository exists"
fi

# Step 2: Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Step 3: Build Docker image
echo "🔨 Building Docker image..."
cd ..
docker build -t $ECR_REPOSITORY:$IMAGE_TAG .
docker tag $ECR_REPOSITORY:$IMAGE_TAG $DOCKER_IMAGE_URI

# Step 4: Push to ECR
echo "📤 Pushing image to ECR..."
docker push $DOCKER_IMAGE_URI

echo "✅ Container image pushed successfully!"
echo "   Image URI: $DOCKER_IMAGE_URI"

# Step 5: Deploy CloudFormation
echo ""
echo "🚀 Deploying CloudFormation stack..."
cd deploy2
./deploy.sh

echo ""
echo "🎉 Build and deployment completed successfully!"
echo "   Container: $DOCKER_IMAGE_URI"
echo "   Stack: $MAIN_STACK_NAME"
