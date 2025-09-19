# Alert Engine GitHub Actions Integration

This guide explains how to set up and use GitHub Actions for automated deployment of the Alert Engine MCP server infrastructure.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Workflow Structure](#workflow-structure)
3. [Quick Setup](#quick-setup)
4. [Manual Setup](#manual-setup)
5. [GitHub Secrets Configuration](#github-secrets-configuration)
6. [Environment Configuration](#environment-configuration)
7. [Deployment Process](#deployment-process)
8. [Troubleshooting](#troubleshooting)
9. [Advanced Configuration](#advanced-configuration)

## 🎯 Overview

The Alert Engine project uses GitHub Actions for:
- **Automated CDK deployments** across multiple environments
- **Infrastructure as Code** management
- **MCP server deployment** with health checks
- **Multi-environment support** (dev/stage/prod)
- **Security through OIDC** authentication

### Workflow Files

```
.github/workflows/
├── deploy-dev.yml        # Development environment (dev branch)
├── deploy-stage.yml      # Staging environment (stage branch)  
├── deploy-prod.yml       # Production environment (main/production branch)
├── deploy.yml           # Main branch integration deployment
└── pr-validation.yml    # Pull request validation
```

## 🏗️ Workflow Structure

### Development Workflow (`deploy-dev.yml`)
- **Trigger**: Push to `dev` branch or manual dispatch
- **Environment**: Development
- **Approval**: None required
- **Features**: Debug logging, relaxed health checks, auto-bootstrap

### Staging Workflow (`deploy-stage.yml`)
- **Trigger**: Push to `stage` branch or manual dispatch
- **Environment**: Staging
- **Approval**: None required  
- **Features**: Standard health checks, production-like configuration

### Production Workflow (`deploy-prod.yml`)
- **Trigger**: Push to `main`/`production` branch or manual dispatch
- **Environment**: Production
- **Approval**: Manual confirmation required (`DEPLOY` keyword)
- **Features**: Strict health checks, deployment protection, rollback capabilities

### PR Validation (`pr-validation.yml`)
- **Trigger**: Pull requests to `main` or `stage`
- **Purpose**: CDK synthesis validation, TypeScript compilation
- **Features**: No deployment, validation only

## 🚀 Quick Setup

### Prerequisites
- AWS CLI configured with appropriate permissions
- GitHub repository for alert-engine
- Access to AWS account for IAM role creation

### Option 1: Automated Setup (Recommended)

```bash
cd /opt/mycode/trilogy/alert-engine/deploy

# For simplified setup (uses existing OIDC provider)
./setup-github-integration-simple.sh

# For complete setup (creates OIDC provider + roles)
./setup-github-integration.sh
```

The script will:
1. Deploy IAM roles via CloudFormation
2. Generate the exact GitHub secrets you need
3. Provide step-by-step instructions

### Option 2: Quick Manual Setup

1. **Deploy IAM Role**:
   ```bash
   aws cloudformation deploy \
     --template-file github-role-only.yml \
     --stack-name github-actions-role-alert-engine-dev \
     --parameter-overrides \
       GitHubOrganization=YOUR_GITHUB_ORG \
       GitHubRepository=alert-engine \
       BranchName=dev \
     --capabilities CAPABILITY_NAMED_IAM
   ```

2. **Get Role ARN**:
   ```bash
   aws cloudformation describe-stacks \
     --stack-name github-actions-role-alert-engine-dev \
     --query "Stacks[0].Outputs[?OutputKey=='GitHubActionsRoleArn'].OutputValue" \
     --output text
   ```

3. **Add to GitHub Secrets** (see next section)

## 🔐 GitHub Secrets Configuration

Go to your GitHub repository: `https://github.com/YOUR_ORG/alert-engine/settings/secrets/actions`

### Required Secrets

| Secret Name | Environment | Description |
|-------------|-------------|-------------|
| `AWS_ROLE_TO_ASSUME_DEV` | Development | IAM role ARN for dev deployments |
| `SECRETS_ARN_DEV` | Development | AWS Secrets Manager ARN for dev config |
| `AWS_ROLE_TO_ASSUME_STAGE` | Staging | IAM role ARN for stage deployments |
| `SECRETS_ARN_STAGE` | Staging | AWS Secrets Manager ARN for stage config |
| `AWS_ROLE_TO_ASSUME_PROD` | Production | IAM role ARN for prod deployments |
| `SECRETS_ARN_PROD` | Production | AWS Secrets Manager ARN for prod config |

### Example Secret Values

```bash
# AWS_ROLE_TO_ASSUME_DEV
arn:aws:iam::764119721991:role/GitHubActionsRole-alert-engine-dev

# SECRETS_ARN_DEV  
arn:aws:secretsmanager:us-east-1:764119721991:secret:alert-engine-dev-secrets-AbCdEf
```

## ⚙️ Environment Configuration

Each environment has specific configuration:

### Development Environment
```yaml
CDK_ENV: dev
PROJECT_NAME: alert-engine
BASE_DOMAIN: totogicore.com
LOG_LEVEL: DEBUG           # Debug logging
MCP_SERVER_PORT: 8000
MCP_SERVER_HOST: 0.0.0.0
```

**Features:**
- Debug logging enabled
- Relaxed health check timeouts
- Cost-optimized resources
- Automatic CDK bootstrap

### Staging Environment
```yaml
CDK_ENV: stage
PROJECT_NAME: alert-engine
BASE_DOMAIN: totogicore.com
LOG_LEVEL: INFO            # Standard logging
MCP_SERVER_PORT: 8000
MCP_SERVER_HOST: 0.0.0.0
```

**Features:**
- Production-like configuration
- Standard health checks
- Moderate resource allocation
- Auto-scaling enabled

### Production Environment
```yaml
CDK_ENV: prod
PROJECT_NAME: alert-engine
BASE_DOMAIN: totogicore.com
LOG_LEVEL: INFO            # Standard logging
MCP_SERVER_PORT: 8000
MCP_SERVER_HOST: 0.0.0.0
```

**Features:**
- High availability configuration
- Strict health checks
- Full resource allocation
- Enhanced monitoring
- Manual deployment approval

## 🔄 Deployment Process

### Development Deployment

```bash
# Create/switch to dev branch
git checkout -b dev

# Make your changes
git add .
git commit -m "feat: add new MCP server feature"
git push origin dev
```

**Result**: Automatic deployment to dev environment

### Staging Deployment

```bash
# Merge dev to stage
git checkout stage
git merge dev
git push origin stage
```

**Result**: Automatic deployment to staging environment

### Production Deployment

```bash
# Create production branch or push to main
git checkout main
git merge stage
git push origin main

# OR trigger manual deployment
```

**Result**: Manual approval required, then deployment to production

### Manual Deployment

1. Go to **Actions** tab in GitHub
2. Select the appropriate workflow
3. Click **Run workflow**
4. For production: Type `DEPLOY` when prompted

## 🔧 Troubleshooting

### Common Issues

#### ❌ "Could not load credentials from any providers"

**Cause**: Missing or incorrect AWS role configuration

**Solution**:
1. Verify GitHub secrets are set correctly
2. Check IAM role exists and has proper trust policy
3. Ensure role ARN is correct in secrets

```bash
# Verify role exists
aws iam get-role --role-name GitHubActionsRole-alert-engine-dev

# Check GitHub secrets in repository settings
```

#### ❌ "CDK bootstrap required"

**Cause**: CDK toolkit not bootstrapped in target account

**Solution**:
```bash
# Manual bootstrap (with correct AWS profile)
export AWS_PROFILE=external-access
cd /opt/mycode/trilogy/alert-engine/deploy
npm run bootstrap
```

#### ❌ "Permission denied" during deployment

**Cause**: IAM role missing required permissions

**Solution**: Add permissions from `cdk-permissions-policy.json`

```bash
# Update role policy
aws iam put-role-policy \
  --role-name GitHubActionsRole-alert-engine-dev \
  --policy-name CDKDeploymentPolicy \
  --policy-document file://cdk-permissions-policy.json
```

#### ❌ "Stack name already exists"

**Cause**: CloudFormation stack naming conflict

**Solution**: Use environment-specific stack names
```bash
# Check existing stacks
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE

# Delete conflicting stack if needed
aws cloudformation delete-stack --stack-name OLD_STACK_NAME
```

#### ❌ "Container image build failed"

**Cause**: Docker build issues or asset bundling problems

**Solution**:
1. Check `.dockerignore` excludes CDK output
2. Verify Docker file exists and is correct
3. Check asset exclusions in `backend-stack.ts`

### Debug Steps

1. **Check workflow logs**: GitHub Actions tab → Failed workflow → View logs
2. **Verify AWS credentials**: Look for authentication step in logs
3. **Check CDK synthesis**: Ensure `cdk synth` works locally
4. **Validate secrets**: Ensure all required secrets are set
5. **Test local deployment**: Run deployment scripts locally first

## 🎛️ Advanced Configuration

### Custom Branch Protection

Add branch protection rules in GitHub:

```
Settings → Branches → Add rule
- Branch name pattern: main
- Require status checks: ✓
- Require review: ✓ 
- Restrict pushes: ✓
```

### Notification Setup

Add to workflow files:

```yaml
- name: Notify Slack on failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: failure
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### Custom Health Checks

Modify health check URLs in workflows:

```yaml
- name: Advanced Health Check
  run: |
    # Custom health endpoints
    curl -f "${{ steps.outputs.outputs.backend_url }}/health/detailed"
    curl -f "${{ steps.outputs.outputs.backend_url }}/metrics"
```

### Blue/Green Deployments

For production zero-downtime deployments:

```yaml
- name: Blue/Green Deploy
  run: |
    # Deploy to green environment
    cdk deploy --parameters BlueGreen=green
    
    # Health check green
    # Switch traffic
    # Cleanup blue
```

## 📚 Additional Resources

- [CDK Bootstrap Guide](../README.md#bootstrap)
- [AWS OIDC Setup](./github-oidc-setup.yml)
- [IAM Role Template](./github-role-only.yml)
- [Permission Policies](./cdk-permissions-policy.json)
- [Smart Bootstrap Script](./smart-bootstrap.sh)

## 🎯 Best Practices

### Security
- Use OIDC instead of long-lived AWS keys
- Limit IAM role permissions to minimum required
- Use environment-specific secrets
- Enable branch protection for production branches

### Deployment
- Always deploy dev → stage → prod
- Use pull requests for code review
- Test deployments in dev/stage before prod
- Monitor deployment health checks

### Maintenance
- Regularly update workflow dependencies
- Review and rotate AWS credentials
- Monitor CloudFormation stack costs
- Keep CDK and dependencies updated

---

## 🆘 Support

If you encounter issues:

1. **Check this README** for common solutions
2. **Review GitHub Actions logs** for specific errors
3. **Run setup scripts** to verify configuration
4. **Test locally** before pushing to GitHub
5. **Check AWS CloudFormation** console for stack status

**Happy Deploying! 🚀**
