import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import { BaseStackConfig } from './types';

export interface StorageStackConfig extends BaseStackConfig {
  // Additional storage-specific configuration can be added here
}

export class StorageStack extends cdk.Stack {
  public readonly bucket: s3.Bucket;
  public readonly bucketName: string;
  public readonly bucketArn: string;

  constructor(scope: Construct, id: string, props: StorageStackConfig) {
    super(scope, id, props);

    // Create S3 bucket for alert engine data
    this.bucket = new s3.Bucket(this, 'AlertEngineDataBucket', {
      bucketName: `${props.projectName}-data-${props.environment}-${props.env?.account}`,
      
      // Enable versioning for data protection
      versioned: props.envConfig.resources.s3.versioning,
      
      // Encryption at rest
      encryption: s3.BucketEncryption.S3_MANAGED,
      
      // Block public access for security
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      
      // Lifecycle rules
      lifecycleRules: [
        {
          id: 'delete-old-versions',
          noncurrentVersionExpiration: cdk.Duration.days(30),
          enabled: true,
        },
        {
          id: 'transition-to-glacier',
          transitions: [
            {
              storageClass: s3.StorageClass.INFREQUENT_ACCESS,
              transitionAfter: cdk.Duration.days(30),
            },
            {
              storageClass: s3.StorageClass.GLACIER_INSTANT_RETRIEVAL,
              transitionAfter: cdk.Duration.days(90),
            },
          ],
          enabled: props.envConfig.resources.s3.lifecycleRules,
        },
      ],
      
      // CORS configuration for web access
      cors: [
        {
          allowedHeaders: ['*'],
          allowedMethods: [
            s3.HttpMethods.GET,
            s3.HttpMethods.PUT,
            s3.HttpMethods.POST,
            s3.HttpMethods.DELETE,
            s3.HttpMethods.HEAD,
          ],
          allowedOrigins: [
            `https://${props.subdomain}.${props.baseDomain}`,
            'http://localhost:3000', // For local development
            'http://localhost:8000',
          ],
          exposedHeaders: ['ETag'],
          maxAge: 3000,
        },
      ],
      
      // Removal policy
      removalPolicy: props.environment === 'prod' 
        ? cdk.RemovalPolicy.RETAIN 
        : cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: props.environment !== 'prod',
    });

    // Create folder structure by adding lifecycle rules for each prefix
    const folderPrefixes = [
      'alerts/',
      'logs/',
      'configs/',
      'data/',
      'temp/',
    ];

    // Store bucket reference
    this.bucketName = this.bucket.bucketName;
    this.bucketArn = this.bucket.bucketArn;

    // Create IAM policy for bucket access
    const bucketAccessPolicy = new iam.PolicyDocument({
      statements: [
        new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: [
            's3:GetObject',
            's3:PutObject',
            's3:DeleteObject',
            's3:ListBucket',
            's3:GetObjectVersion',
          ],
          resources: [
            this.bucket.bucketArn,
            `${this.bucket.bucketArn}/*`,
          ],
        }),
        new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: [
            's3:GetBucketLocation',
            's3:ListBucketVersions',
          ],
          resources: [
            this.bucket.bucketArn,
          ],
        }),
      ],
    });

    // Export policy document for use in other stacks
    new cdk.CfnOutput(this, 'BucketAccessPolicyDocument', {
      value: JSON.stringify(bucketAccessPolicy.toJSON()),
      description: 'IAM policy document for S3 bucket access',
      exportName: `${props.projectName}-bucket-policy-${props.environment}`,
    });

    // Output bucket information
    new cdk.CfnOutput(this, 'BucketName', {
      value: this.bucket.bucketName,
      description: 'S3 bucket name for alert engine data',
      exportName: `${props.projectName}-bucket-name-${props.environment}`,
    });

    new cdk.CfnOutput(this, 'BucketArn', {
      value: this.bucket.bucketArn,
      description: 'S3 bucket ARN for alert engine data',
      exportName: `${props.projectName}-bucket-arn-${props.environment}`,
    });

    new cdk.CfnOutput(this, 'BucketRegionalDomainName', {
      value: this.bucket.bucketRegionalDomainName,
      description: 'S3 bucket regional domain name',
      exportName: `${props.projectName}-bucket-domain-${props.environment}`,
    });

    // Tag all resources
    cdk.Tags.of(this).add('Project', props.projectName);
    cdk.Tags.of(this).add('Environment', props.environment);
    cdk.Tags.of(this).add('Stack', 'Storage');
  }
}