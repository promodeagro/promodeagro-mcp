import * as cdk from 'aws-cdk-lib';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecsPatterns from 'aws-cdk-lib/aws-ecs-patterns';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
//import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as path from 'path';
import { Platform } from 'aws-cdk-lib/aws-ecr-assets';
import { Construct } from 'constructs';
import { BackendStackConfig } from './types';

export class BackendStack extends cdk.Stack {
  public readonly service: ecsPatterns.ApplicationLoadBalancedFargateService;
  public readonly backendUrl: string;

  constructor(scope: Construct, id: string, props: BackendStackConfig) {
    super(scope, id, props);

    // Create log group for the application
    const logGroup = new logs.LogGroup(this, 'BackendLogGroup', {
      logGroupName: `/aws/ecs/${props.projectName}-backend-${props.environment}`,
      retention: props.envConfig.resources.cloudwatch.logRetentionDays,
      removalPolicy: props.environment === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });

    // Reference the secrets manager secret (update ARN to match your actual secrets)
    const appSecret = secretsmanager.Secret.fromSecretCompleteArn(this, 'AppSecret', props.envConfig.application.secretsArn);

    // Create task execution role
    const executionRole = new iam.Role(this, 'TaskExecutionRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy'),
      ],
    });

    // Grant permission to read secrets
    appSecret.grantRead(executionRole);

    // Create task role for S3 and other AWS service permissions
    const taskRole = new iam.Role(this, 'TaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });

    // // Grant IAM permissions for Aurora DSQL authentication
    // taskRole.addToPolicy(new iam.PolicyStatement({
    //   effect: iam.Effect.ALLOW,
    //   actions: [
    //     'dsql:DbConnect',
    //     'dsql:DbConnectAdmin',
    //   ],
    //   resources: [
    //     `arn:aws:dsql:${props.env?.region || 'us-east-1'}:${props.env?.account || '*'}:cluster/${props.auroraClusterId}`,
    //   ],
    // }));

    // Grant S3 permissions for alert engine data
    taskRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:ListBucket',
        's3:GetObjectVersion',
      ],
      resources: [
        props.s3BucketArn,
        `${props.s3BucketArn}/*`,
      ],
    }));

    // Grant S3 bucket metadata permissions
    taskRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        's3:GetBucketLocation',
        's3:ListBucketVersions',
      ],
      resources: [
        props.s3BucketArn,
      ],
    }));

    // Grant Cognito permissions for MCP server authentication if needed
    taskRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'cognito-idp:AdminCreateUser',
        'cognito-idp:AdminDeleteUser',
        'cognito-idp:AdminGetUser',
        'cognito-idp:AdminUpdateUserAttributes',
        'cognito-idp:AdminSetUserPassword',
        'cognito-idp:AdminInitiateAuth',
        'cognito-idp:AdminRespondToAuthChallenge',
        'cognito-idp:AdminConfirmSignUp',
        'cognito-idp:ListUsers',
        'cognito-idp:GetUser',
      ],
      resources: [
        props.cognitoUserPoolArn,
      ],
    }));

    // Temporarily disable SSL completely to get app deployed
    // const hostedZone = route53.HostedZone.fromHostedZoneAttributes(this, 'HostedZone', {
    //   zoneName: props.baseDomain,
    //   hostedZoneId: 'Z084963222P42TKL91TRW',
    // });

    // const certificate = acm.Certificate.fromCertificateArn(
    //   this,
    //   'BackendCertificate', 
    //   'arn:aws:acm:us-east-1:764119721991:certificate/1e855b56-ba56-4830-8995-1cf79fd42106'
    // );

    // Create Fargate service with ALB (HTTP only)
    this.service = new ecsPatterns.ApplicationLoadBalancedFargateService(this, 'BackendService', {
      serviceName: `${props.projectName}-backend-${props.environment}`,
      cluster: props.cluster,
      // No SSL certificate - HTTP only
      
      // Task configuration
      cpu: props.envConfig.resources.ecs.cpu,
      memoryLimitMiB: props.envConfig.resources.ecs.memory,
      desiredCount: props.envConfig.resources.ecs.desiredCount,
      
      // Container configuration
      taskImageOptions: {
        image: ecs.ContainerImage.fromAsset(path.join(__dirname, '../../'), {
          exclude: [
            'infrastructure',
            'frontend',
            'venv',
            'logs',
            'recordings',
            'transcripts',
            'deploy/cdk.out',
            'deploy/node_modules',
            'deploy/*.d.ts',
            'deploy/*.js',
            'deploy/*.js.map',
            'cdk.out',
            '**/*.pyc',
            '**/__pycache__',
            '.git',
            '*.log'
          ],
          buildArgs: {
            // Add build args if needed
            BUILDPLATFORM: 'linux/amd64',
            TARGETPLATFORM: 'linux/amd64'
          },
          platform: Platform.LINUX_AMD64
        }),
        containerName: `${props.projectName}-mcp-server`,
        containerPort: 8000,
        logDriver: ecs.LogDrivers.awsLogs({
          streamPrefix: 'backend',
          logGroup,
        }),
        environment: {
          ENVIRONMENT: props.environment,
          PROJECT_NAME: props.projectName,
          ENV: props.environment,
          DEBUG: props.environment !== 'prod' ? 'true' : 'false',
          API_HOST: props.envConfig.application.mcpServerHost,
          API_PORT: props.envConfig.application.mcpServerPort,
          LOG_LEVEL: props.envConfig.application.logLevel,
          AWS_REGION: props.env?.region || 'us-east-1',
          // S3 Configuration
          S3_BUCKET_NAME: props.s3BucketName,
          S3_BUCKET_REGION: props.env?.region || 'us-east-1',
          ALERT_DATA_PATH: '/app/data',
          // Health Check Configuration
          PYTHONPATH: '/app/src',
          // Cognito Configuration (if authentication is needed)
          COGNITO_USER_POOL_ID: props.cognitoUserPoolId,
          COGNITO_APP_CLIENT_ID: props.cognitoAppClientId,
          COGNITO_IDENTITY_POOL_ID: props.cognitoIdentityPoolId,
          COGNITO_REGION: props.env?.region || 'us-east-1',
          COGNITO_DOMAIN: props.cognitoUserPoolDomain,
        },
        secrets: {
          // Add any secrets required by the MCP server here
          // Example: DATABASE_PASSWORD: ecs.Secret.fromSecretsManager(appSecret, 'DATABASE_PASSWORD'),
          // Example: API_KEY: ecs.Secret.fromSecretsManager(appSecret, 'API_KEY'),
        },
        executionRole,
        taskRole,
      },
      
      // Load balancer configuration (HTTP only)
      publicLoadBalancer: true,
      protocol: elbv2.ApplicationProtocol.HTTP,
      listenerPort: 80,
      
      // Network configuration
      assignPublicIp: props.envConfig.resources.network.natGateways === 0, // Assign public IP when no NAT gateways
      platformVersion: ecs.FargatePlatformVersion.LATEST,
    });

    // Configure deployment circuit breaker
    const cfnService = this.service.service.node.defaultChild as ecs.CfnService;
    cfnService.deploymentConfiguration = {
      maximumPercent: 200,
      minimumHealthyPercent: 100,
      deploymentCircuitBreaker: {
        enable: true,
        rollback: true
      }
    };

    // Configure health check
    this.service.targetGroup.configureHealthCheck({
      path: '/health',
      healthyHttpCodes: '200',
      interval: cdk.Duration.seconds(30),
      timeout: cdk.Duration.seconds(5),
      healthyThresholdCount: 2,
      unhealthyThresholdCount: 3,
    });

    // Configure auto scaling
    const scalableTarget = this.service.service.autoScaleTaskCount({
      minCapacity: props.envConfig.resources.ecs.minCapacity,
      maxCapacity: props.envConfig.resources.ecs.maxCapacity,
    });

    // Only enable auto-scaling if configured
    if (props.envConfig.features.autoScaling) {
      scalableTarget.scaleOnCpuUtilization('CpuScaling', {
        targetUtilizationPercent: 70,
        scaleInCooldown: cdk.Duration.minutes(5),
        scaleOutCooldown: cdk.Duration.minutes(2),
      });

      scalableTarget.scaleOnMemoryUtilization('MemoryScaling', {
        targetUtilizationPercent: 80,
        scaleInCooldown: cdk.Duration.minutes(5),
        scaleOutCooldown: cdk.Duration.minutes(2),
      });
    }

    // Set backend URL (HTTP only since SSL is disabled)
    this.backendUrl = `http://${this.service.loadBalancer.loadBalancerDnsName}`;

    // Output important values
    new cdk.CfnOutput(this, 'BackendUrl', {
      value: this.backendUrl,
      description: 'Backend service URL',
      exportName: `${props.projectName}-backend-url-${props.environment}`,
    });

    new cdk.CfnOutput(this, 'LoadBalancerDns', {
      value: this.service.loadBalancer.loadBalancerDnsName,
      description: 'Load balancer DNS name',
      exportName: `${props.projectName}-alb-dns-${props.environment}`,
    });

    new cdk.CfnOutput(this, 'ServiceName', {
      value: this.service.service.serviceName,
      description: 'ECS service name',
      exportName: `${props.projectName}-service-name-${props.environment}`,
    });

    // Tag all resources
    cdk.Tags.of(this).add('Project', props.projectName);
    cdk.Tags.of(this).add('Environment', props.environment);
    cdk.Tags.of(this).add('Stack', 'Backend');
  }
} 