import * as cdk from 'aws-cdk-lib';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import { BaseStackConfig } from './types';

export interface AuthStackConfig extends BaseStackConfig {}

export class AuthStack extends cdk.Stack {
  public readonly userPool: cognito.UserPool;
  public readonly userPoolClient: cognito.UserPoolClient;
  public readonly identityPool: cognito.CfnIdentityPool;
  public readonly authenticatedRole: iam.Role;
  public readonly unauthenticatedRole: iam.Role;

  constructor(scope: Construct, id: string, props: AuthStackConfig) {
    super(scope, id, props);

    // Create Cognito User Pool
    this.userPool = new cognito.UserPool(this, 'UserPool', {
      userPoolName: `${props.projectName}-user-pool-${props.environment}`,
      
      // Sign-in configuration
      signInAliases: {
        email: true,
        username: false,
      },
      
      // Auto verification
      autoVerify: {
        email: true,
      },
      
      // Self sign-up configuration
      selfSignUpEnabled: true,
      
      // User invitation settings
      userInvitation: {
        emailSubject: `Welcome to ${props.projectName}!`,
        emailBody: 'Hello {username}, your temporary password is {####}',
      },
      
      // Password policy
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: false,
      },
      
      // Account recovery
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      
      // Custom attributes
      customAttributes: {
        full_name: new cognito.StringAttribute({
          minLen: 1,
          maxLen: 100,
          mutable: true,
        }),
      },
      
      // Standard attributes
      standardAttributes: {
        email: {
          required: true,
          mutable: true,
        },
        preferredUsername: {
          required: false,
          mutable: true,
        },
      },
      
      // Email configuration
      email: cognito.UserPoolEmail.withCognito(`noreply@${props.subdomain}.${props.baseDomain}`),
      
      // MFA configuration (optional)
      mfa: cognito.Mfa.OPTIONAL,
      mfaSecondFactor: {
        sms: false,
        otp: true,
      },
      
      // Device tracking
      deviceTracking: {
        challengeRequiredOnNewDevice: true,
        deviceOnlyRememberedOnUserPrompt: true,
      },
      
      // Deletion protection for production
      deletionProtection: props.environment === 'prod',
      
      // Removal policy
      removalPolicy: props.environment === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });

    // Create User Pool Client
    this.userPoolClient = new cognito.UserPoolClient(this, 'UserPoolClient', {
      userPool: this.userPool,
      userPoolClientName: `${props.projectName}-client-${props.environment}`,
      
      // Authentication flows
      authFlows: {
        adminUserPassword: true,
        userSrp: true,
        userPassword: false, // Disable for security
        custom: false,
      },
      
      // OAuth configuration
      oAuth: {
        flows: {
          authorizationCodeGrant: true,
          implicitCodeGrant: false,
        },
        scopes: [
          cognito.OAuthScope.EMAIL,
          cognito.OAuthScope.OPENID,
          cognito.OAuthScope.PROFILE,
        ],
        callbackUrls: [
          `https://api.${props.subdomain}.${props.baseDomain}`,
          `https://api.${props.subdomain}.${props.baseDomain}/auth/callback`,
          ...(props.environment !== 'prod' ? [
            'http://localhost:8000',
            'http://localhost:8000/auth/callback',
          ] : []),
        ],
        logoutUrls: [
          `https://api.${props.subdomain}.${props.baseDomain}`,
          `https://api.${props.subdomain}.${props.baseDomain}/auth/logout`,
          ...(props.environment !== 'prod' ? [
            'http://localhost:8000',
            'http://localhost:8000/auth/logout',
          ] : []),
        ],
      },
      
      // Token configuration
      generateSecret: false, // For SPA applications
      accessTokenValidity: cdk.Duration.hours(1),
      idTokenValidity: cdk.Duration.hours(1),
      refreshTokenValidity: cdk.Duration.days(30),
      
      // Prevent user existence errors
      preventUserExistenceErrors: true,
      
      // Read and write attributes
      readAttributes: new cognito.ClientAttributes()
        .withStandardAttributes({
          email: true,
          preferredUsername: true,
        })
        .withCustomAttributes('full_name'),
      
      writeAttributes: new cognito.ClientAttributes()
        .withStandardAttributes({
          email: true,
          preferredUsername: true,
        })
        .withCustomAttributes('full_name'),
    });

    // Create User Pool Domain
    const userPoolDomain = new cognito.UserPoolDomain(this, 'UserPoolDomain', {
      userPool: this.userPool,
      cognitoDomain: {
        domainPrefix: `${props.projectName.toLowerCase()}-${props.environment}`,
      },
    });

    // Create IAM roles for Identity Pool
    this.authenticatedRole = new iam.Role(this, 'AuthenticatedRole', {
      roleName: `${props.projectName}-authenticated-role-${props.environment}`,
      assumedBy: new iam.FederatedPrincipal(
        'cognito-identity.amazonaws.com',
        {
          StringEquals: {
            'cognito-identity.amazonaws.com:aud': '', // Will be set after identity pool creation
          },
          'ForAnyValue:StringLike': {
            'cognito-identity.amazonaws.com:amr': 'authenticated',
          },
        },
        'sts:AssumeRoleWithWebIdentity'
      ),
    });

    this.unauthenticatedRole = new iam.Role(this, 'UnauthenticatedRole', {
      roleName: `${props.projectName}-unauthenticated-role-${props.environment}`,
      assumedBy: new iam.FederatedPrincipal(
        'cognito-identity.amazonaws.com',
        {
          StringEquals: {
            'cognito-identity.amazonaws.com:aud': '', // Will be set after identity pool creation
          },
          'ForAnyValue:StringLike': {
            'cognito-identity.amazonaws.com:amr': 'unauthenticated',
          },
        },
        'sts:AssumeRoleWithWebIdentity'
      ),
    });

    // Add basic permissions to authenticated role
    this.authenticatedRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'cognito-identity:GetCredentialsForIdentity',
        'cognito-identity:GetId',
      ],
      resources: ['*'],
    }));

    // Create Identity Pool
    this.identityPool = new cognito.CfnIdentityPool(this, 'IdentityPool', {
      identityPoolName: `${props.projectName}_identity_pool_${props.environment}`,
      allowUnauthenticatedIdentities: false,
      cognitoIdentityProviders: [
        {
          clientId: this.userPoolClient.userPoolClientId,
          providerName: this.userPool.userPoolProviderName,
          serverSideTokenCheck: false,
        },
      ],
    });

    // Attach roles to Identity Pool
    new cognito.CfnIdentityPoolRoleAttachment(this, 'IdentityPoolRoleAttachment', {
      identityPoolId: this.identityPool.ref,
      roles: {
        authenticated: this.authenticatedRole.roleArn,
        unauthenticated: this.unauthenticatedRole.roleArn,
      },
    });

    // Update role trust policies with the actual identity pool ID
    const authenticatedRoleAssumeRolePolicy = this.authenticatedRole.assumeRolePolicy!;
    authenticatedRoleAssumeRolePolicy.addStatements(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        principals: [new iam.FederatedPrincipal('cognito-identity.amazonaws.com')],
        actions: ['sts:AssumeRoleWithWebIdentity'],
        conditions: {
          StringEquals: {
            'cognito-identity.amazonaws.com:aud': this.identityPool.ref,
          },
          'ForAnyValue:StringLike': {
            'cognito-identity.amazonaws.com:amr': 'authenticated',
          },
        },
      })
    );

    const unauthenticatedRoleAssumeRolePolicy = this.unauthenticatedRole.assumeRolePolicy!;
    unauthenticatedRoleAssumeRolePolicy.addStatements(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        principals: [new iam.FederatedPrincipal('cognito-identity.amazonaws.com')],
        actions: ['sts:AssumeRoleWithWebIdentity'],
        conditions: {
          StringEquals: {
            'cognito-identity.amazonaws.com:aud': this.identityPool.ref,
          },
          'ForAnyValue:StringLike': {
            'cognito-identity.amazonaws.com:amr': 'unauthenticated',
          },
        },
      })
    );

    // Outputs
    new cdk.CfnOutput(this, 'UserPoolId', {
      value: this.userPool.userPoolId,
      description: 'Cognito User Pool ID',
      exportName: `${props.projectName}-user-pool-id-${props.environment}`,
    });

    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: this.userPoolClient.userPoolClientId,
      description: 'Cognito User Pool Client ID',
      exportName: `${props.projectName}-user-pool-client-id-${props.environment}`,
    });

    new cdk.CfnOutput(this, 'IdentityPoolId', {
      value: this.identityPool.ref,
      description: 'Cognito Identity Pool ID',
      exportName: `${props.projectName}-identity-pool-id-${props.environment}`,
    });

    new cdk.CfnOutput(this, 'UserPoolDomainOutput', {
      value: userPoolDomain.domainName,
      description: 'Cognito User Pool Domain',
      exportName: `${props.projectName.toLowerCase()}-user-pool-domain-${props.environment}`,
    });

    new cdk.CfnOutput(this, 'Region', {
      value: props.env?.region || 'us-east-1',
      description: 'AWS Region',
      exportName: `${props.projectName}-region-${props.environment}`,
    });

    // Tag all resources
    cdk.Tags.of(this).add('Project', props.projectName);
    cdk.Tags.of(this).add('Environment', props.environment);
    cdk.Tags.of(this).add('Stack', 'Auth');
  }
} 