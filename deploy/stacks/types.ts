import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { EnvironmentConfig } from '../config/environments';

/**
 * Base configuration for all stacks
 */
export interface BaseStackConfig extends cdk.StackProps {
  projectName: string;
  subdomain: string;
  environment: string;
  baseDomain: string; // totogicore.com
  envConfig: EnvironmentConfig;
  description?: string;
}

/**
 * Network stack configuration
 */
export interface NetworkStackConfig extends BaseStackConfig {}

/**
 * Backend stack configuration
 */
export interface BackendStackConfig extends BaseStackConfig {
  vpc: ec2.Vpc;
  cluster: ecs.Cluster;
  // Aurora DSQL configuration
  auroraClusterId: string;
  auroraEndpoint: string;
  auroraUsername?: string;
  // S3 Bucket configuration
  s3Bucket: s3.Bucket;
  s3BucketName: string;
  s3BucketArn: string;
  // Cognito configuration
  cognitoUserPoolId: string;
  cognitoUserPoolArn: string;
  cognitoAppClientId: string;
  cognitoIdentityPoolId: string;
  cognitoUserPoolDomain: string;
}

/**
 * Frontend stack configuration
 */
export interface FrontendStackConfig extends BaseStackConfig {
  backendUrl: string;
  // Cognito configuration
  // cognitoUserPoolId: string;
  // cognitoAppClientId: string;
  // cognitoIdentityPoolId: string;
  // cognitoUserPoolDomain: string;
  // cognitoRegion: string;
} 