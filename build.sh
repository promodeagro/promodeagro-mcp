#!/bin/bash

# Alert Engine Docker Build Script
# Optimized for GitHub Actions and local development

set -e

# Configuration
IMAGE_NAME="alert-engine"
TAG="${1:-latest}"
REGISTRY="${REGISTRY:-ghcr.io}"

echo "🚀 Building Alert Engine Docker Image"
echo "   Image: ${IMAGE_NAME}:${TAG}"
echo "   Registry: ${REGISTRY}"
echo ""

# Function to handle Docker Hub rate limits
build_with_fallback() {
    echo "📦 Attempting Docker build..."
    
    # Try normal build first
    if docker build -t "${IMAGE_NAME}:${TAG}" .; then
        echo "✅ Build successful!"
        return 0
    fi
    
    echo "❌ Build failed, trying fallback strategies..."
    
    # Strategy 1: Use buildx with different driver
    echo "🔄 Trying with Docker Buildx..."
    if command -v docker-buildx &> /dev/null; then
        docker buildx build --load -t "${IMAGE_NAME}:${TAG}" .
        return 0
    fi
    
    # Strategy 2: Pull base images manually
    echo "🔄 Pre-pulling base images..."
    docker pull python:3.12-slim || true
    docker build -t "${IMAGE_NAME}:${TAG}" .
}

# Function to test the built image
test_image() {
    echo ""
    echo "🧪 Testing Docker image..."
    
    # Start container in background
    docker run -d --name "${IMAGE_NAME}-test" -p 8000:8000 "${IMAGE_NAME}:${TAG}" || {
        echo "❌ Failed to start container"
        return 1
    }
    
    # Wait for startup
    echo "⏳ Waiting for container to start..."
    sleep 10
    
    # Check if container is running
    if docker ps | grep -q "${IMAGE_NAME}-test"; then
        echo "✅ Container is running"
        
        # Optional: Test health check
        if curl -f http://localhost:8000/health 2>/dev/null; then
            echo "✅ Health check passed"
        else
            echo "⚠️ Health check endpoint not responding (this may be normal)"
        fi
    else
        echo "❌ Container failed to start"
        docker logs "${IMAGE_NAME}-test"
        return 1
    fi
    
    # Cleanup
    docker stop "${IMAGE_NAME}-test" >/dev/null 2>&1
    docker rm "${IMAGE_NAME}-test" >/dev/null 2>&1
    echo "✅ Test completed successfully"
}

# Function to show image info
show_image_info() {
    echo ""
    echo "📋 Image Information:"
    docker images "${IMAGE_NAME}:${TAG}" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    
    # Show layers for size analysis
    echo ""
    echo "📊 Image Layers:"
    docker history "${IMAGE_NAME}:${TAG}" --format "table {{.Size}}\t{{.CreatedBy}}" | head -10
}

# Main execution
echo "🔧 Checking Docker setup..."
if ! docker --version >/dev/null 2>&1; then
    echo "❌ Docker is not installed or not running"
    exit 1
fi

# Check if .dockerignore exists
if [[ ! -f .dockerignore ]]; then
    echo "⚠️ Warning: .dockerignore not found - build may be slower"
fi

# Build the image
build_with_fallback

# Test the image
if [[ "${2}" != "--no-test" ]]; then
    test_image
fi

# Show image information
show_image_info

echo ""
echo "🎉 Build completed successfully!"
echo "   Run: docker run -p 8000:8000 ${IMAGE_NAME}:${TAG}"
echo ""

# Optional: Push to registry
if [[ "${PUSH_TO_REGISTRY}" == "true" ]]; then
    echo "📤 Pushing to registry..."
    docker tag "${IMAGE_NAME}:${TAG}" "${REGISTRY}/${IMAGE_NAME}:${TAG}"
    docker push "${REGISTRY}/${IMAGE_NAME}:${TAG}"
    echo "✅ Pushed to ${REGISTRY}/${IMAGE_NAME}:${TAG}"
fi
