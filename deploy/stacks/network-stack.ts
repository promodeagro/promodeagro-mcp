import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import { NetworkStackConfig } from './types';

export class NetworkStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;
  public readonly cluster: ecs.Cluster;

  constructor(scope: Construct, id: string, props: NetworkStackConfig) {
    super(scope, id, props);

    // Create VPC with appropriate subnet configuration based on NAT Gateway count
    const subnetConfig = props.envConfig.resources.network.natGateways === 0 
      ? [
          // For environments with no NAT Gateways (like staging), use only public subnets
          {
            cidrMask: 24,
            name: 'Public',
            subnetType: ec2.SubnetType.PUBLIC,
          },
        ]
      : [
          // For environments with NAT Gateways, use full subnet configuration
          {
            cidrMask: 24,
            name: 'Public',
            subnetType: ec2.SubnetType.PUBLIC,
          },
          {
            cidrMask: 24,
            name: 'Private',
            subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          },
          {
            cidrMask: 28,
            name: 'Database',
            subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
          },
        ];

    this.vpc = new ec2.Vpc(this, 'Vpc', {
      vpcName: `${props.projectName}-vpc-${props.environment}`,
      maxAzs: props.envConfig.resources.network.maxAzs,
      natGateways: props.envConfig.resources.network.natGateways,
      subnetConfiguration: subnetConfig,
      enableDnsHostnames: true,
      enableDnsSupport: true,
    });

    // Create ECS Cluster
    this.cluster = new ecs.Cluster(this, 'Cluster', {
      clusterName: `${props.projectName}-cluster-${props.environment}`,
      vpc: this.vpc,
      containerInsightsV2: ecs.ContainerInsights.ENHANCED,
    });

    // Add CloudWatch log group for ECS
    new logs.LogGroup(this, 'EcsLogGroup', {
      logGroupName: `/aws/ecs/${props.projectName}-${props.environment}`,
      retention: props.envConfig.resources.cloudwatch.logRetentionDays,
      removalPolicy: props.environment === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });

    // Output important values
    new cdk.CfnOutput(this, 'VpcId', {
      value: this.vpc.vpcId,
      description: 'VPC ID',
      exportName: `${props.projectName}-vpc-id-${props.environment}`,
    });

    new cdk.CfnOutput(this, 'ClusterName', {
      value: this.cluster.clusterName,
      description: 'ECS Cluster Name',
      exportName: `${props.projectName}-cluster-name-${props.environment}`,
    });

    // Tag all resources
    cdk.Tags.of(this).add('Project', props.projectName);
    cdk.Tags.of(this).add('Environment', props.environment);
    cdk.Tags.of(this).add('Stack', 'Network');
  }
} 