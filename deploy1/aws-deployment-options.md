# AWS S3/CDN Deployment Options for Secure API Key Management

## The Problem
With S3/CloudFront deployments, `VITE_*` environment variables are embedded at **build-time** and visible in the browser. This exposes API keys to anyone who inspects the JavaScript files.

## 🏆 Recommended Solutions (Most to Least Secure)

### Option 1: Lambda@Edge + CloudFront (Most Secure)
**Best for production deployments**

```typescript
// Lambda@Edge function (CloudFront origin request)
exports.handler = async (event) => {
    const request = event.Records[0].cf.request;
    
    if (request.uri === '/api/config') {
        const config = {
            openaiApiKey: process.env.OPENAI_API_KEY, // From Lambda environment
            mcpHostUrl: process.env.MCP_HOST_URL,
            appEnv: 'production'
        };
        
        return {
            status: '200',
            statusDescription: 'OK',
            headers: {
                'content-type': [{ key: 'Content-Type', value: 'application/json' }],
                'cache-control': [{ key: 'Cache-Control', value: 'no-cache' }]
            },
            body: JSON.stringify(config)
        };
    }
    
    return request; // Pass through other requests
};
```

**CloudFormation:**
```yaml
Resources:
  ConfigLambdaEdge:
    Type: AWS::Lambda::Function
    Properties:
      Runtime: nodejs18.x
      Handler: index.handler
      Code:
        ZipFile: |
          # Lambda code above
      Environment:
        Variables:
          OPENAI_API_KEY: !Ref OpenAIAPIKeyParameter
          MCP_HOST_URL: !Ref MCPHostURL

  CloudFrontDistribution:
    Type: AWS::CloudFront::Distribution
    Properties:
      DistributionConfig:
        DefaultCacheBehavior:
          LambdaFunctionAssociations:
            - EventType: origin-request
              LambdaFunctionARN: !GetAtt ConfigLambdaEdge.Arn
```

### Option 2: API Gateway + Lambda Proxy (Very Secure)
**Keeps API key completely server-side**

Create a Lambda function that acts as a proxy for OpenAI:

```typescript
// Lambda function: openai-proxy
export const handler = async (event) => {
    const { messages, model = 'gpt-3.5-turbo' } = JSON.parse(event.body);
    
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ messages, model })
    });
    
    return {
        statusCode: response.status,
        headers: {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        },
        body: await response.text()
    };
};
```

**Update chatbotService.ts:**
```typescript
// Use your API Gateway endpoint instead of OpenAI directly
private baseUrl: string = 'https://your-api-id.execute-api.region.amazonaws.com/prod/openai-proxy';

// Remove API key from frontend entirely
constructor() {
    // No API key needed in frontend!
}
```

### Option 3: Runtime Config from S3 (Moderate Security)
**Store config in private S3 object, fetch at runtime**

```typescript
// In your deployment, upload config to private S3 bucket
{
    "openaiApiKey": "sk-...",
    "mcpHostUrl": "http://...",
    "appEnv": "production"
}
```

**CloudFormation:**
```yaml
Resources:
  ConfigBucket:
    Type: AWS::S3::Bucket
    Properties:
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true

  ConfigLambda:
    Type: AWS::Lambda::Function
    Properties:
      Handler: index.handler
      Runtime: nodejs18.x
      Code:
        ZipFile: |
          const AWS = require('aws-sdk');
          const s3 = new AWS.S3();
          
          exports.handler = async () => {
              const params = {
                  Bucket: process.env.CONFIG_BUCKET,
                  Key: 'app-config.json'
              };
              
              const data = await s3.getObject(params).promise();
              return {
                  statusCode: 200,
                  headers: {
                      'Content-Type': 'application/json',
                      'Access-Control-Allow-Origin': '*'
                  },
                  body: data.Body.toString()
              };
          };
```

### Option 4: AWS Systems Manager Parameter Store
**Fetch parameters at runtime via Lambda**

```typescript
// Lambda function to fetch from Parameter Store
const AWS = require('aws-sdk');
const ssm = new AWS.SSM();

exports.handler = async () => {
    const params = {
        Names: [
            '/alert-engine/openai-api-key',
            '/alert-engine/mcp-host-url'
        ],
        WithDecryption: true
    };
    
    const data = await ssm.getParameters(params).promise();
    const config = {};
    
    data.Parameters.forEach(param => {
        const key = param.Name.split('/').pop();
        config[key] = param.Value;
    });
    
    return {
        statusCode: 200,
        headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        body: JSON.stringify(config)
    };
};
```

## Implementation Steps

### 1. Update Frontend Code
```bash
# The configService.ts is already created above
# Update chatbotService.ts to use configService
```

### 2. Choose Your Deployment Method
- **Most Secure**: Option 2 (API Gateway Proxy) - API key never leaves AWS
- **Best Balance**: Option 1 (Lambda@Edge) - Config served securely
- **Simplest**: Option 3 (S3 Config) - Easy to implement

### 3. Update Build Process
```yaml
# GitHub Actions example
- name: Deploy to S3
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  run: |
    # Don't use VITE_ prefix anymore for sensitive keys
    npm run build
    aws s3 sync dist/ s3://${{ env.S3_BUCKET }}
```

## Security Benefits

✅ **API keys not embedded in JavaScript**  
✅ **Keys stored in AWS services (encrypted)**  
✅ **Runtime configuration loading**  
✅ **Proper access controls**  
✅ **Easy key rotation without rebuild**  

## Next Steps
1. Choose your preferred option
2. Set up the AWS infrastructure
3. Update the frontend to use configService
4. Test the deployment
