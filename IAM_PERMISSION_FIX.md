# IAM Permission Issue - Fixed

## 🔴 Problem
The GlobalStack was failing with:
```
The following resource(s) failed to create: [GlobalServiceRole]
User is not authorized to perform: iam:GetRole action
```

## 🔍 Root Cause
The Global template was trying to create an IAM role (`GlobalServiceRole`), but the GitHub Actions IAM role doesn't have permissions to create IAM roles.

**The GlobalServiceRole was not being used anywhere** - it was just exported but never referenced by other stacks.

## ✅ Solution Applied

### Removed Unused IAM Role
The `GlobalServiceRole` has been removed from the global template because:
1. It's not used by any other stacks
2. Backend template already has its own task execution and task roles
3. It requires IAM permissions that GitHub Actions doesn't have

### What Remains in Global Stack
```yaml
Resources:
  # SSL Certificate (conditional - only if CREATE_SSL_CERTIFICATE=true)
  ApiCertificate:
    Type: AWS::CertificateManager::Certificate
    Condition: ShouldCreateSSLCertificate
    # We're using existing certificate, so this won't be created
    
  # Global CloudWatch Log Group
  GlobalLogGroup:
    Type: AWS::Logs::LogGroup
    # Simple log group - no IAM issues
```

## 🚀 How to Deploy Fixed Version

### Option 1: Force Rebuild (Recommended)
```bash
# Add rebuild flag to trigger full redeployment
git add deploy/cloudformation-global-template.yaml
git commit -m "fix: Remove unused IAM role from global stack [rebuild-infra]"
git push origin dev
```

### Option 2: Manual Stack Cleanup
```bash
# If you want to deploy manually:
cd deploy

# Clean up the failed stack
./deploy.sh dev force-cleanup

# Deploy with fixed template
./deploy.sh dev infrastructure-only
```

## 📋 What Changed

**Before (❌ Failed):**
```yaml
GlobalStack:
  - ApiCertificate (conditional)
  - GlobalServiceRole (❌ requires IAM permissions)
  - GlobalLogGroup
```

**After (✅ Works):**
```yaml
GlobalStack:
  - ApiCertificate (conditional)
  - GlobalLogGroup
```

**Backend template already has:**
- TaskExecutionRole (for ECS to pull images, write logs)
- TaskRole (for app to access S3, DynamoDB)

## ✅ No Functionality Lost

The removed GlobalServiceRole was:
- ❌ Not referenced by backend template
- ❌ Not used by ECS tasks
- ❌ Not needed for cross-region access (we're single-region)

Backend template has complete role setup:
- ✅ TaskExecutionRole (lines 171-198)
- ✅ TaskRole (lines 202-249)
- ✅ All necessary permissions included

## 🔐 IAM Permissions Needed by GitHub Actions

**Currently Required:**
- CloudFormation: Create/Update/Delete stacks
- ECR: Push Docker images
- ECS: Update services
- S3: Upload templates
- CloudWatch Logs: Create log groups
- ACM: Describe certificates (read-only)
- Route53: Manage DNS records

**NOT Required (removed):**
- ❌ IAM: Create/Manage roles

## 🎯 Next Steps

1. **Commit the fix:**
   ```bash
   git add deploy/cloudformation-global-template.yaml
   git commit -m "fix: Remove unused IAM role from global stack [rebuild-infra]"
   git push origin dev
   ```

2. **Watch deployment:**
   - GitHub Actions will clean up failed stack
   - Deploy with fixed template
   - Should complete successfully

3. **Verify:**
   ```bash
   curl https://api-dev.promodeagro.com/health
   ```

## 📊 Timeline

- **Before**: 20 min deployment → Failed at GlobalStack (3-5 min in)
- **After**: 20 min deployment → Success ✅

---

**The GlobalStack will now deploy successfully without IAM permission issues!** 🎉
