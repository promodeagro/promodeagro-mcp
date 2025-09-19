#!/bin/bash

# Script to disable SSL and revert to HTTP-only configuration
# Usage: ./disable-ssl.sh <environment>

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_color() {
    echo -e "${1}${2}${NC}"
}

print_color $BLUE "🔓 Alert Engine SSL Disable Script"
echo "=================================="

if [ $# -lt 1 ]; then
    print_color $RED "Usage: $0 <environment>"
    print_color $YELLOW "Example: $0 dev"
    exit 1
fi

ENVIRONMENT=$1

if [[ ! "$ENVIRONMENT" =~ ^(dev|stage|prod)$ ]]; then
    print_color $RED "Error: Environment must be 'dev', 'stage', or 'prod'"
    exit 1
fi

# Navigate to project root
cd "$(dirname "$0")/../.."

# Backup current backend-stack.ts
cp deploy/stacks/backend-stack.ts deploy/stacks/backend-stack.ts.ssl-backup
print_color $YELLOW "📋 Backed up current SSL configuration"

# Function to disable SSL in backend-stack.ts
disable_ssl() {
    local BACKEND_STACK="deploy/stacks/backend-stack.ts"
    
    print_color $YELLOW "🔧 Disabling SSL configuration..."
    
    # Comment out hosted zone configuration
    sed -i 's|    const hostedZone = route53.HostedZone.fromHostedZoneAttributes|    // const hostedZone = route53.HostedZone.fromHostedZoneAttributes|g' "$BACKEND_STACK"
    sed -i 's|      zoneName: props.baseDomain,|      // zoneName: props.baseDomain,|g' "$BACKEND_STACK"
    sed -i 's|      hostedZoneId:.*,|      // hostedZoneId: '\''Z084963222P42TKL91TRW'\'',|g' "$BACKEND_STACK"
    sed -i 's|    });|    // });|g' "$BACKEND_STACK"
    
    # Comment out certificate configuration
    sed -i 's|    const certificate = acm.Certificate.fromCertificateArn|    // const certificate = acm.Certificate.fromCertificateArn|g' "$BACKEND_STACK"
    sed -i 's|      this,|      // this,|g' "$BACKEND_STACK"
    sed -i 's|      '\''BackendCertificate'\'',|      // '\''BackendCertificate'\'',|g' "$BACKEND_STACK"
    sed -i 's|      '\''arn:aws:acm:.*'\''|      // '\''arn:aws:acm:us-east-1:764119721991:certificate/CERT-ARN'\''|g' "$BACKEND_STACK"
    sed -i 's|    );|    // );|g' "$BACKEND_STACK"
    
    # Remove domain and certificate from service configuration
    sed -i 's|      domainName: `api.${props.subdomain}.${props.baseDomain}`,||g' "$BACKEND_STACK"
    sed -i 's|      domainZone: hostedZone,||g' "$BACKEND_STACK"
    sed -i 's|      certificate: certificate,||g' "$BACKEND_STACK"
    sed -i 's|    // Create Fargate service with ALB (HTTPS with custom domain)|    // Create Fargate service with ALB (HTTP only)|g' "$BACKEND_STACK"
    
    # Update backend URL to use HTTP load balancer DNS
    sed -i 's|    this.backendUrl = `https://api\..*totogicore\.com`;|    this.backendUrl = `http://${this.service.loadBalancer.loadBalancerDnsName}`;|g' "$BACKEND_STACK"
    sed -i 's|    // Set backend URL (HTTPS with custom domain)|    // Set backend URL (HTTP only since SSL is disabled)|g' "$BACKEND_STACK"
}

# Main execution
print_color $BLUE "\n🚀 Starting SSL disable process..."

# Update backend stack configuration
disable_ssl

# Show diff of changes
print_color $YELLOW "\n📋 Changes made to backend-stack.ts:"
git diff --no-index deploy/stacks/backend-stack.ts.ssl-backup deploy/stacks/backend-stack.ts || true

# Commit changes
print_color $BLUE "\n📝 Committing changes..."
git add deploy/stacks/backend-stack.ts
git commit -m "Disable SSL and revert to HTTP-only configuration for $ENVIRONMENT

- Remove SSL certificate and custom domain configuration
- Use HTTP load balancer endpoint only  
- Simplified deployment without Route53 dependencies"

print_color $GREEN "\n🎉 SSL disabled successfully!"
print_color $YELLOW "📋 Next steps:"
echo "  1. Run 'git push origin dev' to deploy HTTP-only version"
echo "  2. Monitor deployment at: https://github.com/trilogy-group/alert-engine/actions" 
echo "  3. Access endpoint via HTTP load balancer DNS (check CloudFormation outputs)"

print_color $BLUE "\n🔄 To re-enable SSL:"
echo "  ./deploy/scripts/enable-ssl.sh $ENVIRONMENT <certificate-arn>"
