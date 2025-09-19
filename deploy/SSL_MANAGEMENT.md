# SSL Management Scripts

This guide explains how to manage SSL certificates and HTTPS configuration for the alert-engine backend service.

## 🎯 **Two-Phase Deployment Strategy**

1. **Phase 1**: Deploy HTTP-only backend (fast, reliable)
2. **Phase 2**: Add SSL certificate and custom domain (when needed)

## 📋 **Scripts Overview**

| Script | Purpose | Usage |
|--------|---------|-------|
| `enable-ssl.sh` | Add HTTPS + custom domain | `./enable-ssl.sh dev <cert-arn>` |
| `disable-ssl.sh` | Remove HTTPS, use HTTP only | `./disable-ssl.sh dev` |

## 🚀 **Step-by-Step Process**

### **Step 1: Deploy HTTP Version First**

The current configuration deploys an HTTP-only backend service:
- ✅ **Fast deployment** (no SSL complications)
- ✅ **Reliable** (no Route53 permission issues)
- ✅ **Testable** (verify app functionality)
- 📍 **Endpoint**: `http://alert-engine-backend-dev-xxxx.us-east-1.elb.amazonaws.com`

```bash
# Current state - already deployed as HTTP
git push origin dev
```

### **Step 2: Create SSL Certificate Manually**

**Before enabling HTTPS, create the certificate in AWS Console:**

1. **Go to**: AWS Certificate Manager (ACM) in `us-east-1`
2. **Click**: "Request certificate"
3. **Domain**: `api.dev-alert-engine.totogicore.com`
4. **Validation**: DNS validation
5. **Create Route53 records** when prompted
6. **Wait** for certificate status = "Issued"
7. **Copy certificate ARN** (e.g., `arn:aws:acm:us-east-1:123456789012:certificate/abcd-1234-...`)

### **Step 3: Enable HTTPS with Script**

```bash
cd deploy/scripts

# Enable SSL for development environment
./enable-ssl.sh dev arn:aws:acm:us-east-1:764119721991:certificate/1e855b56-ba56-4830-8995-1cf79fd42106

# The script will:
# ✅ Verify certificate exists and is issued
# ✅ Add Route53 permissions to CDK CloudFormation role
# ✅ Update backend-stack.ts with SSL configuration
# ✅ Commit changes with descriptive message
```

### **Step 4: Deploy HTTPS Version**

```bash
# Push the SSL-enabled configuration
git push origin dev

# Monitor deployment
# https://github.com/trilogy-group/alert-engine/actions
```

### **Step 5: Test HTTPS Endpoint**

```bash
# Test the HTTPS endpoint
curl -I https://api.dev-alert-engine.totogicore.com/health

# Verify SSL certificate
openssl s_client -connect api.dev-alert-engine.totogicore.com:443 -servername api.dev-alert-engine.totogicore.com
```

## 🔄 **Rollback to HTTP**

If SSL deployment fails, quickly rollback:

```bash
cd deploy/scripts

# Disable SSL and revert to HTTP
./disable-ssl.sh dev

# Deploy HTTP version
git push origin dev
```

## 🌍 **Multi-Environment Usage**

### **Development**
```bash
# Certificate for: api.dev-alert-engine.totogicore.com
./enable-ssl.sh dev arn:aws:acm:us-east-1:123456:certificate/dev-cert-id
```

### **Staging**
```bash
# Certificate for: api.stage-alert-engine.totogicore.com  
./enable-ssl.sh stage arn:aws:acm:us-east-1:123456:certificate/stage-cert-id
```

### **Production**
```bash
# Certificate for: api.alert-engine.totogicore.com
./enable-ssl.sh prod arn:aws:acm:us-east-1:123456:certificate/prod-cert-id
```

## 🔧 **Script Details**

### **enable-ssl.sh Features:**
- ✅ **Validates** certificate ARN format and existence
- ✅ **Adds Route53 permissions** to CDK CloudFormation role
- ✅ **Updates backend-stack.ts** with SSL configuration
- ✅ **Creates backup** of current configuration
- ✅ **Shows diff** of changes made
- ✅ **Commits with descriptive message**

### **disable-ssl.sh Features:**  
- ✅ **Reverts to HTTP-only** configuration
- ✅ **Removes custom domain** configuration
- ✅ **Creates backup** of SSL configuration
- ✅ **Shows diff** of changes made
- ✅ **Commits with descriptive message**

## 🛠️ **Troubleshooting**

### **Certificate Issues**
```bash
# List all certificates
aws acm list-certificates --region us-east-1 --output table

# Check certificate status
aws acm describe-certificate --certificate-arn <arn> --region us-east-1
```

### **Route53 Issues**
```bash
# Check hosted zones
aws route53 list-hosted-zones --output table

# Verify CDK role permissions
aws iam list-role-policies --role-name cdk-alerteng-cfn-exec-role-764119721991-us-east-1
```

### **Deployment Issues**
```bash
# Check CloudFormation stack events
aws cloudformation describe-stack-events --stack-name alert-engine-backend-dev --region us-east-1

# Check GitHub Actions
# https://github.com/trilogy-group/alert-engine/actions
```

## 📝 **Current Certificate ARN**

**Development Environment:**
- **Certificate ARN**: `arn:aws:acm:us-east-1:764119721991:certificate/1e855b56-ba56-4830-8995-1cf79fd42106`
- **Domain**: `api.dev-alert-engine.totogicore.com`
- **Status**: Manually created and validated ✅

## 🎉 **Benefits of This Approach**

1. **🚀 Fast Initial Deployment**: Get app working with HTTP first
2. **🔄 Easy Rollback**: Quick revert if SSL issues arise  
3. **🧪 Testable**: Verify app functionality before adding SSL complexity
4. **📦 Automated**: Scripts handle all configuration changes
5. **🌍 Multi-Environment**: Works for dev/stage/prod
6. **📋 Documented**: Clear process and troubleshooting steps
