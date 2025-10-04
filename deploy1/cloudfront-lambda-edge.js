/**
 * Lambda@Edge function for CloudFront
 * Serves runtime configuration securely
 * 
 * Deploy this as a Lambda@Edge function attached to your CloudFront distribution
 */

exports.handler = async (event, context) => {
    const request = event.Records[0].cf.request;
    const uri = request.uri;
    
    console.log('Lambda@Edge request:', uri);
    
    // Handle config endpoint
    if (uri === '/api/config') {
        const config = {
            openaiApiKey: process.env.OPENAI_API_KEY,
            mcpHostUrl: process.env.MCP_HOST_URL || 'http://alert--Backe-J3vD6CohaowE-1847151533.us-east-1.elb.amazonaws.com',
            appEnv: process.env.APP_ENV || 'production'
        };
        
        return {
            status: '200',
            statusDescription: 'OK',
            headers: {
                'content-type': [{ 
                    key: 'Content-Type', 
                    value: 'application/json' 
                }],
                'cache-control': [{ 
                    key: 'Cache-Control', 
                    value: 'no-cache, no-store, must-revalidate' 
                }],
                'access-control-allow-origin': [{ 
                    key: 'Access-Control-Allow-Origin', 
                    value: '*' 
                }],
                'access-control-allow-headers': [{ 
                    key: 'Access-Control-Allow-Headers', 
                    value: 'Content-Type' 
                }],
                'access-control-allow-methods': [{ 
                    key: 'Access-Control-Allow-Methods', 
                    value: 'GET, OPTIONS' 
                }]
            },
            body: JSON.stringify(config)
        };
    }
    
    // Handle CORS preflight for config endpoint
    if (uri === '/api/config' && request.method === 'OPTIONS') {
        return {
            status: '200',
            statusDescription: 'OK',
            headers: {
                'access-control-allow-origin': [{ 
                    key: 'Access-Control-Allow-Origin', 
                    value: '*' 
                }],
                'access-control-allow-headers': [{ 
                    key: 'Access-Control-Allow-Headers', 
                    value: 'Content-Type' 
                }],
                'access-control-allow-methods': [{ 
                    key: 'Access-Control-Allow-Methods', 
                    value: 'GET, OPTIONS' 
                }]
            }
        };
    }
    
    // Pass through all other requests to S3
    return request;
};
