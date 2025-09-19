import { Environment } from 'aws-cdk-lib';

/**
 * Environment-specific configuration
 */
export interface EnvironmentConfig {
  name: string;
  // AWS Environment
  env: Environment;
  // Domain configuration
  subdomain: string;
  baseDomain: string;
  // Resource sizing
  resources: {
    // ECS configuration
    ecs: {
      cpu: number;
      memory: number;
      desiredCount: number;
      minCapacity: number;
      maxCapacity: number;
    };
    // Network configuration
    network: {
      natGateways: number;
      maxAzs: number;
    };
    // CloudWatch configuration
    cloudwatch: {
      logRetentionDays: number;
    };
    // S3 configuration
    s3: {
      versioning: boolean;
      lifecycleRules: boolean;
    };
  };
  // Feature flags
  features: {
    authentication: boolean;
    monitoring: boolean;
    autoScaling: boolean;
  };
  // Cost optimization
  costOptimization: {
    useSpotInstances: boolean;
    cloudFrontPriceClass: string;
  };
  // Application configuration
  application: {
    mcpServerPort: string;
    mcpServerHost: string;
    logLevel: string;
    secretsArn: string;
  };
}

/**
 * Development environment configuration
 */
export const devConfig: EnvironmentConfig = {
  name: 'dev',
  env: {
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
    account: process.env.CDK_DEFAULT_ACCOUNT,
  },
  subdomain: 'dev-alert-engine',
  baseDomain: 'totogicore.com',
  resources: {
    ecs: {
      cpu: 512,
      memory: 1024,
      desiredCount: 1,
      minCapacity: 1,
      maxCapacity: 2,
    },
    network: {
      natGateways: 1, // Cost savings
      maxAzs: 2,
    },
    cloudwatch: {
      logRetentionDays: 7,
    },
    s3: {
      versioning: false,
      lifecycleRules: false,
    },
  },
  features: {
    authentication: false, // Currently disabled
    monitoring: true,
    autoScaling: false, // Fixed capacity in dev
  },
  costOptimization: {
    useSpotInstances: true,
    cloudFrontPriceClass: 'PriceClass_100', // US, Canada, Europe only
  },
  application: {
    // Alert Engine MCP Server configuration
    mcpServerPort: '8000',
    mcpServerHost: '0.0.0.0',
    logLevel: 'INFO',
    secretsArn: 'arn:aws:secretsmanager:us-east-2:764119721991:secret:dsql/tmf-6vgxCr', // Update with actual secrets ARN
  },
};

/**
 * Production environment configuration
 */
export const prodConfig: EnvironmentConfig = {
  name: 'prod',
  env: {
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
    account: process.env.CDK_DEFAULT_ACCOUNT,
  },
  subdomain: 'outbound-agent',
  baseDomain: 'totogicore.com',
  resources: {
    ecs: {
      cpu: 1024,
      memory: 2048,
      desiredCount: 2,
      minCapacity: 2,
      maxCapacity: 10,
    },
    network: {
      natGateways: 2, // High availability
      maxAzs: 2,
    },
    cloudwatch: {
      logRetentionDays: 30,
    },
    s3: {
      versioning: true,
      lifecycleRules: true,
    },
  },
  features: {
    authentication: false, // Currently disabled
    monitoring: true,
    autoScaling: true,
  },
  costOptimization: {
    useSpotInstances: false, // Stability over cost
    cloudFrontPriceClass: 'PriceClass_All', // Global coverage
  },
  application: {
    // Alert Engine MCP Server configuration
    mcpServerPort: '8000',
    mcpServerHost: '0.0.0.0',
    logLevel: 'INFO',
    secretsArn: 'arn:aws:secretsmanager:us-east-2:764119721991:secret:dsql/tmf-6vgxCr', // Update with actual secrets ARN
  },
};

/**
 * Staging environment configuration
 */
export const stageConfig: EnvironmentConfig = {
  name: 'stage',
  env: {
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
    account: process.env.CDK_DEFAULT_ACCOUNT,
  },
  subdomain: 'stage-alert-engine',
  baseDomain: 'totogicore.com',
  resources: {
    ecs: {
      cpu: 1024,
      memory: 2048,
      desiredCount: 1,
      minCapacity: 1,
      maxCapacity: 3,
    },
    network: {
      natGateways: 0, // No NAT Gateways - use public subnets only for staging
      maxAzs: 2,
    },
    cloudwatch: {
      logRetentionDays: 14,
    },
    s3: {
      versioning: true,
      lifecycleRules: true,
    },
  },
  features: {
    authentication: false, // Currently disabled
    monitoring: true,
    autoScaling: true,
  },
  costOptimization: {
    useSpotInstances: false, // Stability for staging
    cloudFrontPriceClass: 'PriceClass_100', // US, Canada, Europe only
  },
  application: {
    // Alert Engine MCP Server configuration
    mcpServerPort: '8000',
    mcpServerHost: '0.0.0.0',
    logLevel: 'INFO',
    secretsArn: 'arn:aws:secretsmanager:us-east-2:764119721991:secret:dsql/tmf-6vgxCr', // Update with actual secrets ARN
  },
};

/**
 * Get environment configuration
 */
export function getEnvironmentConfig(environmentName: string): EnvironmentConfig {
  switch (environmentName.toLowerCase()) {
    case 'dev':
    case 'development':
      return devConfig;
    case 'stage':
    case 'staging':
      return stageConfig;
    case 'prod':
    case 'production':
      return prodConfig;
    default:
      throw new Error(`Unknown environment: ${environmentName}. Valid environments are: dev, stage, prod`);
  }
}

/**
 * Environment-specific database configuration
 */
export interface DatabaseConfig {
  clusterEndpoint: string;
  clusterId: string;
  username: string;
  databaseName: string;
}

/**
 * Get database configuration for environment
 */
export function getDatabaseConfig(environment: string, projectName: string): DatabaseConfig {
  const envConfig = getEnvironmentConfig(environment);
  
  return {
    clusterEndpoint: process.env.DB_CLUSTER_ENDPOINT || '',
    clusterId: process.env.DB_CLUSTER_ID || '',
    username: process.env.DB_USERNAME || 'postgres',
    databaseName: `${projectName}_${envConfig.name}`.toLowerCase(),
  };
}
