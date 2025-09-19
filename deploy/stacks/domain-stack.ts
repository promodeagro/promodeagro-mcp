import * as cdk from 'aws-cdk-lib';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as route53Targets from 'aws-cdk-lib/aws-route53-targets';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import { Construct } from 'constructs';
import { BaseStackConfig } from './types';

export interface DomainStackConfig extends BaseStackConfig {
  distribution?: cloudfront.Distribution;
  loadBalancer?: elbv2.ApplicationLoadBalancer;
}

/**
 * Stack for managing domain configurations, SSL certificates, and Route53 records
 */
export class DomainStack extends cdk.Stack {
  public readonly hostedZone: route53.IHostedZone;
  public readonly frontendCertificate: acm.Certificate;
  public readonly apiCertificate: acm.Certificate;
  
  constructor(scope: Construct, id: string, props: DomainStackConfig) {
    super(scope, id, props);
    
    // Look up existing hosted zone
    this.hostedZone = route53.HostedZone.fromLookup(this, 'HostedZone', {
      domainName: props.baseDomain,
    });
    
    // Create SSL certificate for frontend (CloudFront requires us-east-1)
    this.frontendCertificate = new acm.Certificate(this, 'FrontendCertificate', {
      domainName: `${props.subdomain}.${props.baseDomain}`,
      certificateName: `${props.projectName}-frontend-${props.environment}`,
      validation: acm.CertificateValidation.fromDns(this.hostedZone),
    });
    
    // Create SSL certificate for API (in the stack's region)
    this.apiCertificate = new acm.Certificate(this, 'ApiCertificate', {
      domainName: `api.${props.subdomain}.${props.baseDomain}`,
      certificateName: `${props.projectName}-api-${props.environment}`,
      validation: acm.CertificateValidation.fromDns(this.hostedZone),
    });
    
    // Create Route53 records if distribution and load balancer are provided
    if (props.distribution) {
      new route53.ARecord(this, 'FrontendRecord', {
        zone: this.hostedZone,
        recordName: props.subdomain,
        target: route53.RecordTarget.fromAlias(
          new route53Targets.CloudFrontTarget(props.distribution)
        ),
        comment: `Frontend for ${props.projectName} (${props.environment})`,
      });
    }
    
    if (props.loadBalancer) {
      new route53.ARecord(this, 'ApiRecord', {
        zone: this.hostedZone,
        recordName: `api.${props.subdomain}`,
        target: route53.RecordTarget.fromAlias(
          new route53Targets.LoadBalancerTarget(props.loadBalancer)
        ),
        comment: `API for ${props.projectName} (${props.environment})`,
      });
    }
    
    // Outputs
    new cdk.CfnOutput(this, 'FrontendDomain', {
      value: `${props.subdomain}.${props.baseDomain}`,
      description: 'Frontend domain',
      exportName: `${props.projectName}-frontend-domain-${props.environment}`,
    });
    
    new cdk.CfnOutput(this, 'ApiDomain', {
      value: `api.${props.subdomain}.${props.baseDomain}`,
      description: 'API domain',
      exportName: `${props.projectName}-api-domain-${props.environment}`,
    });
    
    new cdk.CfnOutput(this, 'FrontendCertificateArn', {
      value: this.frontendCertificate.certificateArn,
      description: 'Frontend SSL certificate ARN',
      exportName: `${props.projectName}-frontend-cert-${props.environment}`,
    });
    
    new cdk.CfnOutput(this, 'ApiCertificateArn', {
      value: this.apiCertificate.certificateArn,
      description: 'API SSL certificate ARN',
      exportName: `${props.projectName}-api-cert-${props.environment}`,
    });
    
    // Tag all resources
    cdk.Tags.of(this).add('Project', props.projectName);
    cdk.Tags.of(this).add('Environment', props.environment);
    cdk.Tags.of(this).add('Stack', 'Domain');
  }
}