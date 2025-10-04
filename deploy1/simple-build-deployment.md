# Simple Build-Time Deployment for S3/CDN (Demo Setup)

## 🚀 Quick Demo Deployment

For **demo purposes**, this approach embeds environment variables at build-time. Simple and fast to implement!

### ⚠️ Security Note
This approach embeds API keys in the built JavaScript files (visible to users). **Only use for demos/development!**

## Setup Steps

### 1. Environment Configuration

**Local `.env` file:**
```bash
# OpenAI Configuration (embedded at build-time)
VITE_OPENAI_API_KEY=sk-your-actual-api-key-here

# MCP Tools Configuration  
VITE_MCP_HOST_URL=http://alert--Backe-J3vD6CohaowE-1847151533.us-east-1.elb.amazonaws.com

# Application Configuration
VITE_APP_ENV=production
```

### 2. Build Process

**The `VITE_*` prefix ensures variables are embedded during build:**

```bash
# Build with environment variables
npm run build

# Variables are now embedded in dist/ files
# Ready for S3 upload!
```

### 3. S3/CloudFront Deployment

**GitHub Actions workflow:**
```yaml
name: Deploy to S3
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Build with environment variables
        env:
          VITE_OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          VITE_MCP_HOST_URL: ${{ secrets.MCP_HOST_URL }}
          VITE_APP_ENV: production
        run: npm run build
      
      - name: Deploy to S3
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: |
          aws s3 sync dist/ s3://your-bucket-name --delete
          aws cloudfront create-invalidation --distribution-id YOUR_DISTRIBUTION_ID --paths "/*"
```

### 4. Manual S3 Upload

**If using AWS CLI manually:**
```bash
# 1. Set environment variables
export VITE_OPENAI_API_KEY=sk-your-key-here
export VITE_MCP_HOST_URL=http://alert--Backe-J3vD6CohaowE-1847151533.us-east-1.elb.amazonaws.com
export VITE_APP_ENV=production

# 2. Build
npm run build

# 3. Upload to S3
aws s3 sync dist/ s3://your-bucket-name --delete

# 4. Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id YOUR_DISTRIBUTION_ID --paths "/*"
```

### 5. Verify Deployment

**Test that environment variables are embedded:**
```bash
# Check if variables are in built files
grep -r "sk-" dist/assets/*.js  # Should find your API key (demo only!)
```

## GitHub Secrets Setup

**Add these secrets to your GitHub repository:**

1. Go to Settings → Secrets and variables → Actions
2. Add these secrets:
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `MCP_HOST_URL` - Your MCP server URL  
   - `AWS_ACCESS_KEY_ID` - For S3 deployment
   - `AWS_SECRET_ACCESS_KEY` - For S3 deployment

## CloudFormation (Optional)

**If using CloudFormation for automated deployment:**
```yaml
Parameters:
  OpenAIAPIKey:
    Type: String
    NoEcho: true
    Description: OpenAI API Key

Resources:
  BuildLambda:
    Type: AWS::Lambda::Function
    Properties:
      Environment:
        Variables:
          VITE_OPENAI_API_KEY: !Ref OpenAIAPIKey
          VITE_MCP_HOST_URL: http://alert--Backe-J3vD6CohaowE-1847151533.us-east-1.elb.amazonaws.com
          VITE_APP_ENV: production
      Code:
        ZipFile: |
          # Build and deploy logic here
```

## ✅ Benefits for Demo

- **🚀 Simple**: No complex runtime loading
- **⚡ Fast**: Works immediately after build
- **🔧 Easy**: Standard Vite behavior
- **📦 Portable**: Built files work anywhere

## ⚠️ Important Notes

1. **API keys are visible** in built JavaScript files
2. **Rotate keys** after demo if needed
3. **Don't use in production** for sensitive applications
4. **Perfect for demos** and internal tools

**Ready for your demo! 🎯**
