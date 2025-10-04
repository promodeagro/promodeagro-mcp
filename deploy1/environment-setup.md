# Environment Variables Setup for Cloud Deployment

## Security Note
⚠️ **NEVER commit actual API keys to git repositories!**

## Required Environment Variables

### For Production/Staging Deployment:

```bash
# OpenAI Configuration (REQUIRED)
VITE_OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx

# MCP Tools Configuration
VITE_MCP_HOST_URL=http://alert--Backe-J3vD6CohaowE-1847151533.us-east-1.elb.amazonaws.com

# Application Configuration
VITE_APP_ENV=production
```

## Cloud Deployment Setup

### AWS/CloudFormation
Add environment variables to your deployment configuration:

```yaml
Environment:
  Variables:
    VITE_OPENAI_API_KEY: !Ref OpenAIAPIKeyParameter
    VITE_MCP_HOST_URL: http://alert--Backe-J3vD6CohaowE-1847151533.us-east-1.elb.amazonaws.com
    VITE_APP_ENV: production
```

### GitHub Actions
Set secrets in repository settings:
- `OPENAI_API_KEY` - Your OpenAI API key
- `MCP_HOST_URL` - The MCP server URL

### Build Process
Environment variables with `VITE_` prefix are embedded at build time.
Make sure they are available during the build process.

## Local Development
1. Copy `.env.example` to `.env`
2. Replace `your_openai_api_key_here` with your actual API key
3. Never commit the `.env` file

## Troubleshooting Cloud Deployment

### Common Issues:
1. **Missing environment variables**: Ensure all `VITE_*` vars are set during build
2. **Build-time vs Runtime**: Vite embeds env vars at build time, not runtime
3. **Case sensitivity**: Environment variable names are case-sensitive
4. **Quotes**: Don't wrap values in quotes in environment files

### Debug Steps:
1. Check build logs for environment variable availability
2. Verify the built files contain the correct values
3. Test with temporary dummy values first
