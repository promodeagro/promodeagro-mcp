# Smart Deployment Strategy Guide

## 🚀 Intelligent Dev Deployment

The dev workflow now uses an intelligent deployment strategy that automatically decides whether to update just the application or rebuild the entire infrastructure.

---

## 📊 Deployment Modes

### 1. ⚡ **Fast App Update** (Default - 2-3 minutes)

**When:** Regular commits without special flags
**What happens:**
- Checks if infrastructure exists ✅
- If exists → Only updates Docker image + ECS tasks
- Infrastructure unchanged (VPC, ALB, etc. untouched)
- **~85% faster** than full deployment

**Example:**
```bash
git commit -m "fix: Update MCP tool logic"
git push origin dev
# Result: Fast app-only update
```

**Process:**
```
Build Docker → Push to ECR → Update ECS Service → Rolling deployment
Total time: ~2-3 minutes
```

---

### 2. 🆕 **Create Infrastructure** (15-20 minutes)

**When:** Infrastructure doesn't exist or is in failed state
**What happens:**
- Detects missing or failed infrastructure
- Automatically deploys full stack
- Creates all CloudFormation stacks
- Deploys application

**Triggers:**
- First deployment to environment
- Stack in `ROLLBACK_COMPLETE` state
- Stack in `DELETE_FAILED` state
- Stack completely deleted

**Process:**
```
Build Docker → Push to ECR → Deploy CloudFormation → Deploy App
Total time: ~15-20 minutes
```

---

### 3. 🔄 **Force Rebuild** (15-20 minutes)

**When:** You need to change infrastructure
**What happens:**
- Deletes existing infrastructure
- Recreates everything from scratch
- Deploys new application

**How to trigger:**

#### Option 1: Commit Message Flag
Add one of these to your commit message:
```bash
git commit -m "feat: New feature [rebuild-infra]"
# or
git commit -m "fix: Update VPC settings [redeploy]"
# or
git commit -m "chore: Infrastructure changes [rebuild]"
```

#### Option 2: Manual Workflow Dispatch
1. Go to GitHub → Actions tab
2. Select "Deploy E-commerce MCP to Development"
3. Click "Run workflow"
4. Set `rebuild_infrastructure` to `true`

**Process:**
```
Build Docker → Push to ECR → Delete old stack → Deploy CloudFormation → Deploy App
Total time: ~15-20 minutes
```

---

## 🎯 Decision Flow

```
┌─────────────────────────────────────┐
│   Push to dev branch                │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│ Check commit message                │
│ for rebuild flags                   │
└───────────────┬─────────────────────┘
                │
        ┌───────┴───────┐
        │ Has flag?     │
        └───────┬───────┘
                │
        ┌───────┴───────┐
        │               │
       YES              NO
        │               │
        ▼               ▼
    [REBUILD]    [CHECK STACK EXISTS]
        │               │
        │       ┌───────┴───────┐
        │       │ Exists?       │
        │       └───────┬───────┘
        │               │
        │       ┌───────┴───────┐
        │       │               │
        │      YES              NO
        │       │               │
        │       ▼               ▼
        │  [UPDATE-APP]    [CREATE]
        │       │               │
        └───────┴───────────────┘
                │
                ▼
        [Deploy & Verify]
```

---

## 📝 Examples

### Example 1: Regular Feature Update (Fast)
```bash
# Make changes to your code
vim src/tools/my_tool.py

# Commit normally
git add .
git commit -m "feat: Add new product search feature"
git push origin dev

# ⚡ Result: Fast app-only update (~2-3 min)
# - Infrastructure: Unchanged
# - Application: Updated
# - Downtime: ~30 seconds (rolling update)
```

### Example 2: Infrastructure Change (Full Rebuild)
```bash
# Made changes to CloudFormation or config
vim deploy/cloudformation-backend-template.yaml

# Commit with rebuild flag
git add .
git commit -m "feat: Increase ECS memory [rebuild-infra]"
git push origin dev

# 🔄 Result: Full rebuild (~15-20 min)
# - Infrastructure: Deleted and recreated
# - Application: Deployed fresh
# - Downtime: ~5-10 minutes
```

### Example 3: Bug Fix (Fast)
```bash
# Fix a bug
vim mcp_http_server.py

# Regular commit
git commit -am "fix: Correct health check response"
git push origin dev

# ⚡ Result: Fast app-only update (~2-3 min)
```

### Example 4: First Deployment (Auto-Create)
```bash
# First time deploying
git push origin dev

# 🆕 Result: Automatic full deployment (~15-20 min)
# - Infrastructure: Created from scratch
# - Application: Deployed
# - No flag needed (detected automatically)
```

---

## ⏱️ Performance Comparison

| Deployment Type | Time | Infrastructure | Application | Use Case |
|----------------|------|----------------|-------------|----------|
| **Fast Update** | 2-3 min | Unchanged | Updated | Code changes only |
| **Create** | 15-20 min | Created | Deployed | First deployment |
| **Rebuild** | 15-20 min | Recreated | Deployed | Infrastructure changes |

**Typical Dev Workflow:**
- Initial deployment: ~20 min (create)
- Next 50 deployments: ~2-3 min each (fast updates)
- **Time saved:** ~15 hours over 50 deployments! 🎉

---

## 🔍 How It Works

### Stack Detection
```yaml
# Workflow checks if stack exists
aws cloudformation describe-stacks --stack-name ecommerce-mcp-main-dev

# If exists → Fast update
# If not exists → Full deployment
# If failed → Full deployment
```

### Fast App Update
```yaml
# Get ECS service details from CloudFormation outputs
CLUSTER_NAME=ecommerce-mcp-cluster-dev
SERVICE_NAME=ecommerce-mcp-backend-dev

# Force new deployment with latest image
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME \
  --force-new-deployment

# Wait for stability
aws ecs wait services-stable
```

### Rebuild Flags Detection
```yaml
# Checks commit message for:
[rebuild-infra]  # Full rebuild
[redeploy]       # Full rebuild
[rebuild]        # Full rebuild

# Or manual workflow input:
rebuild_infrastructure: true
```

---

## 💡 Best Practices

### ✅ DO

1. **Use fast updates for code changes**
   ```bash
   git commit -m "feat: Add new API endpoint"
   # No flag needed - will auto-update app
   ```

2. **Use rebuild flag for infrastructure changes**
   ```bash
   git commit -m "chore: Update ECS memory [rebuild-infra]"
   ```

3. **Let workflow auto-detect first deployment**
   ```bash
   # First push to dev - no flag needed
   git push origin dev
   ```

4. **Monitor GitHub Actions**
   - Check which strategy was used
   - Verify deployment time
   - Review health checks

### ❌ DON'T

1. **Don't add rebuild flag for code changes**
   ```bash
   # BAD: Wastes 15 minutes
   git commit -m "fix: Typo [rebuild-infra]"
   ```

2. **Don't forget rebuild flag for infra changes**
   ```bash
   # BAD: Infrastructure won't update
   git commit -m "chore: Changed VPC CIDR"
   # Should be: "chore: Changed VPC CIDR [rebuild-infra]"
   ```

3. **Don't manually delete stacks**
   - Use `[rebuild-infra]` flag instead
   - Workflow handles cleanup properly

---

## 🔧 Troubleshooting

### Problem: Stack in ROLLBACK_COMPLETE
**Solution:** Automatic - workflow will detect and recreate

### Problem: Need to force rebuild but forgot flag
**Solution:** Use manual workflow dispatch
1. GitHub → Actions → Deploy E-commerce MCP to Development
2. Run workflow → Set `rebuild_infrastructure: true`

### Problem: Fast update failed
**Solution:** Try full rebuild
```bash
git commit --allow-empty -m "chore: Force rebuild [rebuild-infra]"
git push origin dev
```

### Problem: Want to see what strategy will be used
**Solution:** Check GitHub Actions logs - strategy is announced early:
```
🔄 Strategy: REBUILD - Delete and recreate infrastructure + application
⚡ Strategy: UPDATE-APP - Only update application (faster)
🆕 Strategy: CREATE - Deploy new infrastructure + application
```

---

## 📊 Monitoring

### Check Deployment Strategy
```bash
# View recent workflow runs
gh run list --workflow deploy-dev.yml

# View specific run
gh run view <run-id>
```

### Verify Current Infrastructure
```bash
# Check if stack exists
aws cloudformation describe-stacks \
  --stack-name ecommerce-mcp-main-dev \
  --region us-east-1

# Check ECS service
aws ecs describe-services \
  --cluster ecommerce-mcp-cluster-dev \
  --services ecommerce-mcp-backend-dev \
  --region us-east-1
```

---

## 🎉 Benefits

| Benefit | Impact |
|---------|--------|
| **Faster deployments** | 85% time reduction for app updates |
| **Lower costs** | Less GitHub Actions minutes |
| **Safer** | Infrastructure only changes when needed |
| **Smarter** | Auto-detects what needs updating |
| **Flexible** | Easy override with commit flags |
| **Clear** | Strategy shown in deployment summary |

---

## 🚀 Quick Reference

```bash
# Fast app update (default)
git commit -m "feat: New feature"
git push origin dev
# Time: ~2-3 min

# Force full rebuild
git commit -m "feat: New feature [rebuild-infra]"
git push origin dev
# Time: ~15-20 min

# Empty commit with rebuild
git commit --allow-empty -m "chore: Rebuild [rebuild]"
git push origin dev
# Time: ~15-20 min
```

---

**Your dev deployments are now smart, fast, and efficient!** 🎉
