# Alert Engine MCP Server Infrastructure

This directory contains the AWS CDK infrastructure code for the Alert Engine MCP (Model Context Protocol) Server with support for multiple environments (dev/stage/prod).

## Project Overview

The Alert Engine MCP Server is deployed as a containerized service on AWS ECS Fargate, providing alert management and monitoring capabilities through the Model Context Protocol interface.

## Environment Configuration

The infrastructure supports three environments with different configurations:

### Development Environment
- **API**: `https://api.dev-alert-engine.totogicore.com`
- Cost-optimized resources (512 CPU, 1GB RAM, 1 instance)
- Single NAT gateway for cost savings
- 7-day log retention
- Auto-scaling disabled

### Staging Environment  
- **API**: `https://api.stage-alert-engine.totogicore.com`
- Moderate resources (1024 CPU, 2GB RAM, 1 instance)
- No NAT gateways (public subnets only)
- 14-day log retention
- Auto-scaling enabled (1-3 instances)

### Production Environment
- **API**: `https://api.alert-engine.totogicore.com`
- High-performance resources (1024 CPU, 2GB RAM, 2+ instances)
- Multiple NAT gateways for high availability
- 30-day log retention  
- Auto-scaling enabled (2-10 instances)

### SSL Certificates

The CDK automatically creates SSL certificates for the API domains using AWS Certificate Manager, validated via DNS through the existing Route53 hosted zone.

## Stack Architecture

The infrastructure consists of five separate stacks:

### 1. NetworkStack
- VPC with public, private, and database subnets across 2 AZs
- Environment-specific NAT gateway configuration
- ECS Cluster for container workloads
- CloudWatch log groups with environment-specific retention

### 2. StorageStack
- S3 bucket for alert engine data storage
- Organized folder structure: `alerts/`, `logs/`, `configs/`, `data/`, `temp/`
- Environment-specific versioning and lifecycle rules
- Encryption at rest with S3-managed keys
- CORS configuration for API access

### 3. AuthStack
- Cognito User Pool for MCP server authentication
- User Pool Client for API access
- Identity Pool for AWS credential access
- IAM roles for authenticated and unauthenticated users

### 4. BackendStack (MCP Server)
- ECS Fargate service running the Python MCP server
- Application Load Balancer with SSL termination
- Container running on port 8000 (matches Dockerfile)
- Auto-scaling based on CPU and memory utilization
- Custom domain: `api.{environment}-alert-engine.totogicore.com`
- Health check endpoint at `/health`
- Comprehensive IAM permissions for S3 and Cognito

### 5. DomainStack
- Route53 DNS records for API endpoints
- SSL certificate management
- Domain routing configuration

## Container Configuration

The MCP server runs in a Docker container with the following configuration:

- **Base Image**: Python 3.12 slim
- **Port**: 8000 (HTTP)
- **Health Check**: `/health` endpoint
- **Environment Variables**:
  - `API_HOST`: 0.0.0.0
  - `API_PORT`: 8000
  - `LOG_LEVEL`: INFO/DEBUG based on environment
  - `ALERT_DATA_PATH`: /app/data
  - `PYTHONPATH`: /app/src
  - AWS and S3 configuration
  - Cognito authentication settings

## Deployment

### Prerequisites

1. AWS CLI configured with appropriate credentials
2. Node.js and npm installed
3. Docker installed (for container builds)
4. Secrets Manager secrets created for each environment

### Environment Setup

1. Install dependencies:
   ```bash
   cd /opt/mycode/trilogy/alert-engine/deploy
   npm install
   ```

2. Set up environment variables:
   ```bash
   export CDK_ENV=dev  # or stage/prod
   export PROJECT_NAME=alert-engine
   export BASE_DOMAIN=totogicore.com
   ```

3. **Update Secrets Manager ARNs** in `config/environments.ts`:
   ```typescript
   // Replace XXXXXX with actual secret suffixes
   secretsArn: arn:aws:secretsmanager:us-east-2:764119721991:secret:dsql/tmf-6vgxCr
   ```

### Deploy Commands

```bash
# First time setup - bootstrap CDK (if not already done)
npm run bootstrap

# Deploy to development
npm run deploy:dev

# Deploy to staging
npm run deploy:stage

# Deploy to production
npm run deploy:prod

# View changes before deployment
npm run diff:dev
npm run diff:stage
npm run diff:prod

# Destroy stacks (be careful!)
npm run destroy:dev
npm run destroy:stage
npm run destroy:prod

# Manual deployment with custom options
./scripts/deploy.sh dev --hotswap
./scripts/deploy.sh prod --require-approval never
```

## Generated Infrastructure

After deployment, the following resources will be created:

### Development Environment
- **VPC**: Custom VPC with 1 NAT gateway
- **ECS Service**: 512 CPU, 1GB RAM, 1 instance
- **Storage**: S3 bucket without versioning
- **Load Balancer**: Application Load Balancer with SSL
- **Logs**: 7-day CloudWatch retention

### Staging Environment  
- **VPC**: Public subnets only (no NAT gateways)
- **ECS Service**: 1024 CPU, 2GB RAM, 1-3 instances
- **Storage**: S3 bucket with versioning
- **Load Balancer**: Application Load Balancer with SSL  
- **Logs**: 14-day CloudWatch retention

### Production Environment
- **VPC**: Custom VPC with 2 NAT gateways for HA
- **ECS Service**: 1024 CPU, 2GB RAM, 2-10 instances with auto-scaling
- **Storage**: S3 bucket with versioning and lifecycle rules
- **Load Balancer**: Application Load Balancer with SSL
- **Logs**: 30-day CloudWatch retention

## MCP Server Endpoints

Once deployed, your MCP server will be available at:

- **Development**: `https://api.dev-alert-engine.totogicore.com`
- **Staging**: `https://api.stage-alert-engine.totogicore.com`  
- **Production**: `https://api.alert-engine.totogicore.com`

Key endpoints:
- `/health` - Health check (used by load balancer)
- MCP protocol endpoints as defined in your server implementation

## Security Features

### Authentication
- Cognito User Pool for user management
- JWT token-based authentication
- IAM roles for fine-grained AWS access

### Network Security
- Private subnets for ECS tasks (where NAT gateways exist)
- Security groups restricting access
- Load balancer SSL termination

### Data Security
- S3 bucket encryption at rest
- VPC endpoints for AWS service communication
- Secrets Manager for sensitive configuration

## Environment-Specific Features

### Cost Optimization (Dev)
- Single NAT gateway
- Smaller compute resources (512 CPU/1GB RAM)
- No auto-scaling
- Shorter log retention (7 days)
- S3 without versioning

### High Availability (Prod)
- Multiple NAT gateways across AZs
- Auto-scaling enabled (2-10 instances)
- Versioned S3 buckets with lifecycle rules
- Longer log retention (30 days)
- Circuit breaker deployment configuration

### Balanced Staging
- No NAT gateways (cost optimization)
- Moderate auto-scaling (1-3 instances)
- S3 with versioning
- Moderate log retention (14 days)

## Monitoring and Logging

### CloudWatch Integration
- Container logs automatically sent to CloudWatch
- Environment-specific log groups
- Configurable retention periods

### Health Monitoring
- ECS service health checks
- Load balancer target group health checks
- Auto-scaling metrics (CPU/Memory utilization)

## Troubleshooting

### Common Issues

1. **Container fails to start**: Check CloudWatch logs for the ECS service
2. **Health check failures**: Ensure `/health` endpoint returns HTTP 200
3. **Domain resolution issues**: Verify Route53 hosted zone configuration
4. **Authentication errors**: Check Cognito User Pool configuration
5. **S3 access denied**: Verify IAM role permissions for ECS tasks

### Debug Commands

```bash
# View ECS service logs
aws logs describe-log-groups --log-group-name-prefix "/aws/ecs/alert-engine"

# Check ECS service status  
aws ecs describe-services --cluster alert-engine-cluster-{env} --services alert-engine-backend-{env}

# View load balancer health
aws elbv2 describe-target-health --target-group-arn {target-group-arn}
```

## Customization

### Adding Secrets
Update `stacks/backend-stack.ts` to add new secrets:
```typescript
secrets: {
  DATABASE_PASSWORD: ecs.Secret.fromSecretsManager(appSecret, 'DATABASE_PASSWORD'),
  API_KEY: ecs.Secret.fromSecretsManager(appSecret, 'API_KEY'),
}
```

### Modifying Resources
- CPU/Memory: Update `config/environments.ts` 
- Auto-scaling: Modify min/max capacity in environment configs
- S3 structure: Update folder prefixes in `stacks/storage-stack.ts`

## Support

For deployment issues or questions, refer to:
- AWS ECS documentation for container troubleshooting
- CDK documentation for infrastructure changes  
- CloudWatch logs for application debugging