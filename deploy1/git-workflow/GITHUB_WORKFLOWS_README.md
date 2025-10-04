# Alert Engine UI GitHub Actions Integration

This guide explains how to set up and use GitHub Actions for automated deployment of the Alert Engine UI React application to AWS S3 and CloudFront.

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

The Alert Engine UI project uses GitHub Actions for:
- **Automated CloudFormation deployments** across multiple environments
- **Static website hosting** on S3 with CloudFront CDN
- **React application deployment** with build optimization
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
- **Features**: React build, S3 deployment, CloudFront invalidation

### Staging Workflow (`deploy-stage.yml`)
- **Trigger**: Push to `stage` branch or manual dispatch
- **Environment**: Staging
- **Approval**: None required  
- **Features**: Production build, linting, deployment verification

### Production Workflow (`deploy-prod.yml`)
- **Trigger**: Published releases or manual dispatch
- **Environment**: Production
- **Approval**: Manual confirmation required (`DEPLOY_TO_PRODUCTION`)
- **Features**: Security scans, health checks, deployment protection

### PR Validation (`pr-validation.yml`)
- **Trigger**: Pull requests to `main` or `stage`
- **Purpose**: React build validation, linting, TypeScript compilation
- **Features**: No deployment, validation only

## 🚀 Quick Setup

### Prerequisites
- AWS CLI configured with appropriate permissions
- GitHub repository for alert-engine-ui
- Access to AWS account for IAM role creation
- Node.js and npm for local testing

### Option 1: Automated Setup (Recommended)

```bash
cd /opt/mycode/trilogy/alert-engine-ui/deploy/git-workflow

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
     --template-file ./git-workflow/github-role-only.yml \
     --stack-name github-actions-role-alert-engine-ui-dev \
     --parameter-overrides \
       GitHubOrganization=YOUR_GITHUB_ORG \
       GitHubRepository=alert-engine-ui \
       BranchName=dev \
     --capabilities CAPABILITY_NAMED_IAM
   ```

2. **Get Role ARN**:
   ```bash
   aws cloudformation describe-stacks \
     --stack-name github-actions-role-alert-engine-ui-dev \
     --query "Stacks[0].Outputs[?OutputKey=='GitHubActionsRoleArn'].OutputValue" \
     --output text
   ```

3. **Add to GitHub Secrets** (see next section)

## 🔐 GitHub Secrets Configuration

Go to your GitHub repository: `https://github.com/YOUR_ORG/alert-engine-ui/settings/secrets/actions`

### Required Secrets

| Secret Name | Environment | Description |
|-------------|-------------|-------------|
| `AWS_ROLE_TO_ASSUME_DEV` | Development | IAM role ARN for dev deployments |
| `AWS_ROLE_TO_ASSUME_STAGE` | Staging | IAM role ARN for stage deployments |
| `AWS_ROLE_TO_ASSUME_PROD` | Production | IAM role ARN for prod deployments |

### Example Secret Values

```bash
# AWS_ROLE_TO_ASSUME_DEV
arn:aws:iam::764119721991:role/GitHubActions-alert-engine-ui-dev

# AWS_ROLE_TO_ASSUME_STAGE
arn:aws:iam::764119721991:role/GitHubActions-alert-engine-ui-stage

# AWS_ROLE_TO_ASSUME_PROD
arn:aws:iam::764119721991:role/GitHubActions-alert-engine-ui-prod
```

## ⚙️ Environment Configuration

Each environment has specific configuration:

### Development Environment
```yaml
ENVIRONMENT: dev
STACK_NAME: econet-ui-dev-stack
DOMAIN_NAME: dev.econet.totogicore.com
BUILD_ENVIRONMENT: development
NODE_ENV: development
```

**Features:**
- Development build optimizations
- Fast build times
- Debug-friendly source maps
- Automatic deployment on push

### Staging Environment
```yaml
ENVIRONMENT: stage
STACK_NAME: econet-ui-stage-stack
DOMAIN_NAME: stage.econet.totogicore.com
BUILD_ENVIRONMENT: staging
NODE_ENV: production
```

**Features:**
- Production-like configuration
- Optimized build for testing
- SSL/TLS certificate validation
- Deployment verification

### Production Environment
```yaml
ENVIRONMENT: prod
STACK_NAME: econet-ui-prod-stack
DOMAIN_NAME: econet.totogicore.com
BUILD_ENVIRONMENT: production
NODE_ENV: production
```

**Features:**
- High availability configuration
- Full optimization enabled
- Security scanning
- Performance monitoring
- Manual deployment approval

## 🔄 Deployment Process

### Development Deployment

```bash
# Create/switch to dev branch
git checkout -b dev

# Make your changes
git add .
git commit -m "feat: add new UI component"
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
aws iam get-role --role-name GitHubActions-alert-engine-ui-dev

# Check GitHub secrets in repository settings
```

#### ❌ "CloudFormation stack deployment failed"

**Cause**: CloudFormation template issues or resource conflicts

**Solution**:
```bash
# Check stack status
aws cloudformation describe-stacks --stack-name econet-ui-dev-stack

# Review stack events for errors
aws cloudformation describe-stack-events --stack-name econet-ui-dev-stack
```

#### ❌ "Permission denied" during deployment

**Cause**: IAM role missing required permissions

**Solution**: Add permissions from `cdk-permissions-policy.json`

```bash
# Update role policy
aws iam put-role-policy \
  --role-name GitHubActions-alert-engine-ui-dev \
  --policy-name UIDeploymentPolicy \
  --policy-document file://iam-github-permissions.json
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

#### ❌ "React build failed"

**Cause**: TypeScript errors, dependency issues, or build configuration problems

**Solution**:
1. Check for TypeScript compilation errors
2. Verify all dependencies are installed (`npm ci`)
3. Run `npm run build` locally to reproduce the issue
4. Check for missing environment variables

### Debug Steps

1. **Check workflow logs**: GitHub Actions tab → Failed workflow → View logs
2. **Verify AWS credentials**: Look for authentication step in logs
3. **Check React build**: Ensure `npm run build` works locally
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
    # Custom health endpoints for static website
    curl -f "https://dev.econet.totogicore.com/"
    curl -f "https://dev.econet.totogicore.com/health" # if you have a health endpoint
```

### Blue/Green Deployments

For production zero-downtime deployments:

```yaml
- name: Blue/Green Deploy
  run: |
    # Deploy to alternate S3 bucket
    ./deploy/deploy.sh prod deploy-only
    
    # Health check new deployment
    curl -f https://econet.totogicore.com/
    
    # CloudFront automatically serves from new S3 content
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
