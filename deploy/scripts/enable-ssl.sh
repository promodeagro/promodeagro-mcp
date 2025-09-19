#!/bin/bash

# Script to enable SSL certificate and custom domain for alert-engine backend
# Usage: ./enable-ssl.sh <environment> <certificate-arn> [hosted-zone-id]

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

print_color $BLUE "🔐 Alert Engine SSL Configuration Script"
echo "========================================="

# Check arguments
if [ $# -lt 2 ]; then
    print_color $RED "Usage: $0 <environment> <certificate-arn> [hosted-zone-id]"
    print_color $YELLOW "Example: $0 dev arn:aws:acm:us-east-1:123456789012:certificate/abcd-1234-5678-9012 Z084963222P42TKL91TRW"
    exit 1
fi

ENVIRONMENT=$1
CERTIFICATE_ARN=$2
HOSTED_ZONE_ID=${3:-"Z084963222P42TKL91TRW"}  # Default hosted zone ID

# Validate inputs
if [[ ! "$CERTIFICATE_ARN" =~ ^arn:aws:acm: ]]; then
    print_color $RED "Error: Certificate ARN must start with 'arn:aws:acm:'"
    exit 1
fi

if [[ ! "$ENVIRONMENT" =~ ^(dev|stage|prod)$ ]]; then
    print_color $RED "Error: Environment must be 'dev', 'stage', or 'prod'"
    exit 1
fi

print_color $GREEN "Configuration:"
echo "  Environment: $ENVIRONMENT"
echo "  Certificate ARN: $CERTIFICATE_ARN" 
echo "  Hosted Zone ID: $HOSTED_ZONE_ID"

# Navigate to project root
cd "$(dirname "$0")/../.."

# Backup current backend-stack.ts
cp deploy/stacks/backend-stack.ts deploy/stacks/backend-stack.ts.backup
print_color $YELLOW "📋 Backed up backend-stack.ts"

# Function to update backend-stack.ts with SSL configuration
update_backend_stack() {
    local BACKEND_STACK="deploy/stacks/backend-stack.ts"
    
    print_color $YELLOW "🔧 Updating backend-stack.ts with SSL configuration..."
    
    # Replace commented SSL configuration with active configuration
    sed -i 's|    // Temporarily disable SSL completely to get app deployed|    // SSL Certificate and Route53 Configuration|g' "$BACKEND_STACK"
    
    # Uncomment and update hosted zone configuration
    sed -i 's|    // const hostedZone = route53.HostedZone.fromHostedZoneAttributes(this, '\''HostedZone'\'', {|    const hostedZone = route53.HostedZone.fromHostedZoneAttributes(this, '\''HostedZone'\'', {|g' "$BACKEND_STACK"
    sed -i 's|    //   zoneName: props.baseDomain,|      zoneName: props.baseDomain,|g' "$BACKEND_STACK"
    sed -i "s|    //   hostedZoneId: 'Z084963222P42TKL91TRW',|      hostedZoneId: '$HOSTED_ZONE_ID',|g" "$BACKEND_STACK"
    sed -i 's|    // });|    });|g' "$BACKEND_STACK"
    
    # Uncomment and update certificate configuration
    sed -i 's|    // const certificate = acm.Certificate.fromCertificateArn(|    const certificate = acm.Certificate.fromCertificateArn(|g' "$BACKEND_STACK"
    sed -i 's|    //   this,|      this,|g' "$BACKEND_STACK"
    sed -i 's|    //   '\''BackendCertificate'\'',|      '\''BackendCertificate'\'',|g' "$BACKEND_STACK"
    sed -i "s|    //   'arn:aws:acm:us-east-1:764119721991:certificate/.*'|      '$CERTIFICATE_ARN'|g" "$BACKEND_STACK"
    sed -i 's|    // );|    );|g' "$BACKEND_STACK"
    
    # Update service configuration to include domain and certificate
    sed -i 's|    // Create Fargate service with ALB (HTTP only)|    // Create Fargate service with ALB (HTTPS with custom domain)|g' "$BACKEND_STACK"
    sed -i 's|      // No SSL certificate - HTTP only|      domainName: `api.${props.subdomain}.${props.baseDomain}`,\n      domainZone: hostedZone,\n      certificate: certificate,|g' "$BACKEND_STACK"
    
    # Update backend URL to use HTTPS
    if [[ "$ENVIRONMENT" == "dev" ]]; then
        sed -i 's|    this.backendUrl = `http://${this.service.loadBalancer.loadBalancerDnsName}`;|    this.backendUrl = `https://api.dev-alert-engine.totogicore.com`;|g' "$BACKEND_STACK"
    elif [[ "$ENVIRONMENT" == "stage" ]]; then
        sed -i 's|    this.backendUrl = `http://${this.service.loadBalancer.loadBalancerDnsName}`;|    this.backendUrl = `https://api.stage-alert-engine.totogicore.com`;|g' "$BACKEND_STACK"
    else
        sed -i 's|    this.backendUrl = `http://${this.service.loadBalancer.loadBalancerDnsName}`;|    this.backendUrl = `https://api.alert-engine.totogicore.com`;|g' "$BACKEND_STACK"
    fi
    
    # Update comment
    sed -i 's|    // Set backend URL (HTTP only since SSL is disabled)|    // Set backend URL (HTTPS with custom domain)|g' "$BACKEND_STACK"
}

# Function to add Route53 permissions
add_route53_permissions() {
    print_color $YELLOW "🔐 Adding Route53 permissions to CDK CloudFormation role..."
    
    export AWS_PROFILE=external-access
    
    aws iam put-role-policy \
      --role-name cdk-alerteng-cfn-exec-role-764119721991-us-east-1 \
      --policy-name Route53SSLPermissions \
      --policy-document "{
        \"Version\": \"2012-10-17\",
        \"Statement\": [
          {
            \"Effect\": \"Allow\",
            \"Action\": [
              \"route53:GetHostedZone\",
              \"route53:ListHostedZones\", 
              \"route53:ChangeResourceRecordSets\",
              \"route53:ListResourceRecordSets\",
              \"route53:GetChange\"
            ],
            \"Resource\": [
              \"arn:aws:route53:::hostedzone/$HOSTED_ZONE_ID\",
              \"arn:aws:route53:::change/*\"
            ]
          },
          {
            \"Effect\": \"Allow\",
            \"Action\": [
              \"route53:GetHostedZone\",
              \"route53:ListHostedZones\"
            ],
            \"Resource\": \"*\"
          }
        ]
      }"
      
    print_color $GREEN "✅ Route53 permissions added successfully"
}

# Function to verify certificate exists and is valid
verify_certificate() {
    print_color $YELLOW "🔍 Verifying SSL certificate..."
    
    export AWS_PROFILE=external-access
    
    local CERT_STATUS=$(aws acm describe-certificate --certificate-arn "$CERTIFICATE_ARN" --region us-east-1 --query "Certificate.Status" --output text 2>/dev/null || echo "NOT_FOUND")
    
    if [[ "$CERT_STATUS" == "NOT_FOUND" ]]; then
        print_color $RED "❌ Certificate not found: $CERTIFICATE_ARN"
        exit 1
    elif [[ "$CERT_STATUS" != "ISSUED" ]]; then
        print_color $YELLOW "⚠️  Certificate status: $CERT_STATUS (should be ISSUED)"
        print_color $YELLOW "   The certificate may still be validating. Continue anyway? [y/N]"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_color $GREEN "✅ Certificate is valid and issued"
    fi
}

# Main execution
print_color $BLUE "\n🚀 Starting SSL configuration process..."

# Step 1: Verify certificate
verify_certificate

# Step 2: Add Route53 permissions
add_route53_permissions

# Step 3: Update backend stack configuration
update_backend_stack

# Step 4: Show diff of changes
print_color $YELLOW "\n📋 Changes made to backend-stack.ts:"
git diff --no-index deploy/stacks/backend-stack.ts.backup deploy/stacks/backend-stack.ts || true

# Step 5: Commit and deploy
print_color $BLUE "\n📝 Committing changes..."
git add deploy/stacks/backend-stack.ts
git commit -m "Enable SSL certificate and custom domain for $ENVIRONMENT

- Add SSL certificate: $CERTIFICATE_ARN
- Enable custom domain: api.$([ "$ENVIRONMENT" = "prod" ] && echo "" || echo "$ENVIRONMENT-")alert-engine.totogicore.com
- Configure Route53 hosted zone: $HOSTED_ZONE_ID
- Update backend URL to use HTTPS
- Add Route53 permissions to CDK role"

print_color $GREEN "\n🎉 SSL configuration complete!"
print_color $YELLOW "📋 Next steps:"
echo "  1. Run 'git push origin dev' to deploy HTTPS version"
echo "  2. Monitor deployment at: https://github.com/trilogy-group/alert-engine/actions"
echo "  3. Test endpoint: https://api.$([ "$ENVIRONMENT" = "prod" ] && echo "" || echo "$ENVIRONMENT-")alert-engine.totogicore.com"

print_color $BLUE "\n🔄 To rollback to HTTP:"
echo "  git checkout HEAD~1 -- deploy/stacks/backend-stack.ts"
echo "  git commit -m 'Rollback to HTTP configuration'"
echo "  git push origin dev"
