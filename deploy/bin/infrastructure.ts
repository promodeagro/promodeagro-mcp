#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { NetworkStack } from '../stacks/network-stack';
import { AuthStack } from '../stacks/auth-stack';
import { StorageStack } from '../stacks/storage-stack';
import { BackendStack } from '../stacks/backend-stack';
// import { FrontendStack } from '../stacks/frontend-stack'; // Removed - no frontend needed for MCP server
import { getEnvironmentConfig, getDatabaseConfig } from '../config/environments';
import * as dotenv from 'dotenv';

// Load environment variables from .env file
dotenv.config();

const app = new cdk.App();

// Validate required database configuration
// NOTE: Database configuration is currently not used in the stacks
// if (!process.env.DB_CLUSTER_ID) {
//   throw new Error('DB_CLUSTER_ID environment variable is required. Please set it to your Aurora cluster ID.');
// }

// if (!process.env.DB_CLUSTER_ENDPOINT) {
//   throw new Error('DB_CLUSTER_ENDPOINT environment variable is required. Please set it to your Aurora cluster endpoint.');
// }

// Get environment name
const environment = process.env.CDK_ENV || 'dev';

// Get environment-specific configuration
const envConfig = getEnvironmentConfig(environment);

// Project configuration
const projectName = process.env.PROJECT_NAME || 'alert-engine';
const baseDomain = process.env.BASE_DOMAIN || 'totogicore.com';

// Get database configuration
const dbConfig = getDatabaseConfig(environment, projectName);

// Build configuration object
const config = {
  projectName,
  subdomain: envConfig.subdomain,
  environment: envConfig.name,
  baseDomain,
  env: envConfig.env,
  // Aurora DSQL configuration
  auroraClusterId: dbConfig.clusterId,
  auroraEndpoint: dbConfig.clusterEndpoint,
  auroraUsername: dbConfig.username,
  // Environment-specific resources
  envConfig,
};

// Create stacks in dependency order
const networkStack = new NetworkStack(app, `${config.projectName}-network-${environment}`, {
  ...config,
  environment,
  description: `Network infrastructure for ${config.projectName} (${environment})`,
});

const storageStack = new StorageStack(app, `${config.projectName}-storage-${environment}`, {
  ...config,
  environment,
  description: `Storage infrastructure for ${config.projectName} (${environment})`,
});

const authStack = new AuthStack(app, `${config.projectName}-auth-${environment}`, {
  ...config,
  environment,
  description: `Authentication services for ${config.projectName} (${environment})`,
});

const backendStack = new BackendStack(app, `${config.projectName}-backend-${environment}`, {
  ...config,
  environment,
  vpc: networkStack.vpc,
  cluster: networkStack.cluster,
  s3Bucket: storageStack.bucket,
  s3BucketName: storageStack.bucketName,
  s3BucketArn: storageStack.bucketArn,
  cognitoUserPoolId: authStack.userPool.userPoolId,
  cognitoUserPoolArn: authStack.userPool.userPoolArn,
  cognitoAppClientId: authStack.userPoolClient.userPoolClientId,
  cognitoIdentityPoolId: authStack.identityPool.ref,
  cognitoUserPoolDomain: `${config.projectName}-${environment}.auth.${config.env.region}.amazoncognito.com`,
  description: `Backend services for ${config.projectName} (${environment})`,
});

// Frontend stack removed - MCP server doesn't need a frontend

// Add stack dependencies
storageStack.addDependency(networkStack);
authStack.addDependency(networkStack);
backendStack.addDependency(storageStack);
backendStack.addDependency(authStack);