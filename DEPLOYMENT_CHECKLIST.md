# RetailMind AI - Deployment Checklist

Quick reference checklist for deploying RetailMind AI to AWS.

## Pre-Deployment Checklist

### Local Setup
- [ ] Python 3.11+ installed and verified
- [ ] Node.js 18+ installed and verified
- [ ] Git installed and verified
- [ ] AWS CLI v2 installed
- [ ] AWS CDK CLI installed (`npm install -g aws-cdk`)
- [ ] Backend dependencies installed (`pip install -r requirements.txt`)
- [ ] Frontend dependencies installed (`npm install`)
- [ ] CDK dependencies installed

### AWS Account Setup
- [ ] AWS account created
- [ ] Root account MFA enabled
- [ ] Account ID noted down
- [ ] Preferred region selected (e.g., us-east-1)
- [ ] IAM user created (`retailmind-deployer`)
- [ ] Access keys downloaded and saved securely
- [ ] AWS CLI configured (`aws configure`)
- [ ] AWS credentials verified (`aws sts get-caller-identity`)

### AWS Services
- [ ] Amazon Bedrock enabled
- [ ] Bedrock model access requested (Claude, Titan, etc.)
- [ ] SageMaker accessed (auto-enabled)
- [ ] OpenSearch accessed (auto-enabled)
- [ ] Textract accessed (auto-enabled)
- [ ] Service quotas checked

## Deployment Checklist

### Environment Configuration
- [ ] Backend `.env` file created from `.env.example`
- [ ] Backend `.env` updated with AWS account ID and region
- [ ] Frontend `.env` file created from `.env.example`
- [ ] Frontend `.env` updated with region
- [ ] CDK `cdk.json` updated with account and region

### CDK Bootstrap
- [ ] CDK bootstrapped (`cdk bootstrap aws://ACCOUNT-ID/REGION`)
- [ ] CDKToolkit stack verified in CloudFormation

### Infrastructure Deployment
- [ ] CDK templates synthesized (`cdk synth`)
- [ ] Changes reviewed (`cdk diff`)
- [ ] Data stack deployed (`cdk deploy RetailMindDataStack`)
- [ ] Compute stack deployed (`cdk deploy RetailMindComputeStack`)
- [ ] API stack deployed (`cdk deploy RetailMindApiStack`)
- [ ] Monitoring stack deployed (`cdk deploy RetailMindMonitoringStack`)
- [ ] Stack outputs captured (`cdk outputs --all`)

### Application Deployment
- [ ] Frontend `.env` updated with Cognito and API Gateway values
- [ ] Backend Lambda functions packaged (`python scripts/package_lambda.py`)
- [ ] Frontend built (`npm run build`)
- [ ] Frontend deployed to S3 or Amplify

## Post-Deployment Verification

### CloudFormation
- [ ] All stacks show `CREATE_COMPLETE` status
- [ ] No failed resources in any stack

### S3 Buckets
- [ ] `retailmind-raw-data-*` bucket exists
- [ ] `retailmind-ml-artifacts-*` bucket exists
- [ ] `retailmind-documents-*` bucket exists

### DynamoDB Tables
- [ ] `retailmind-transactions` table exists
- [ ] `retailmind-agent-states` table exists
- [ ] `retailmind-workflow-instances` table exists
- [ ] `retailmind-audit-trail` table exists

### Lambda Functions
- [ ] All 6 agent Lambda functions exist
- [ ] Functions have correct IAM roles
- [ ] Environment variables configured

### API Gateway
- [ ] API Gateway created
- [ ] Invoke URL noted
- [ ] Health endpoint tested (`/health`)
- [ ] Returns 200 OK

### Cognito
- [ ] User pool created
- [ ] App client created
- [ ] Test user created
- [ ] User can sign in

### Frontend
- [ ] Frontend URL accessible
- [ ] Login page loads
- [ ] Can authenticate with test user
- [ ] Dashboard loads successfully

### Monitoring
- [ ] CloudWatch log groups created
- [ ] Logs appearing for Lambda functions
- [ ] No error logs present
- [ ] Metrics visible in CloudWatch

## Security Checklist

- [ ] Root account MFA enabled
- [ ] IAM user MFA enabled (recommended)
- [ ] Access keys rotated (set reminder for 90 days)
- [ ] `.env` files added to `.gitignore`
- [ ] No secrets committed to Git
- [ ] CloudTrail enabled
- [ ] S3 bucket encryption enabled
- [ ] DynamoDB encryption enabled
- [ ] API Gateway authentication configured

## Cost Management

- [ ] Billing alerts configured
- [ ] Budget set in AWS Budgets
- [ ] Cost Explorer reviewed
- [ ] Unused resources identified
- [ ] S3 lifecycle policies configured
- [ ] CloudWatch Logs retention set

## Testing Checklist

- [ ] Backend tests pass (`pytest`)
- [ ] Frontend tests pass (`npm test`)
- [ ] API health endpoint responds
- [ ] Can create test data
- [ ] Agents respond to events
- [ ] Workflows execute successfully
- [ ] Business Copilot responds to queries

## Documentation Review

- [ ] README.md reviewed
- [ ] SETUP.md reviewed
- [ ] AWS_DEPLOYMENT_GUIDE.md reviewed
- [ ] ARCHITECTURE.md reviewed
- [ ] API_DOCUMENTATION.md reviewed
- [ ] Requirements document reviewed
- [ ] Design document reviewed
- [ ] Tasks document reviewed

## Rollback Plan

In case of issues:
- [ ] Rollback commands documented
- [ ] Previous stack versions noted
- [ ] Backup of configuration files
- [ ] Contact information for support

### Rollback Commands
```bash
# Rollback specific stack
cdk destroy RetailMindApiStack

# Rollback all stacks
cdk destroy --all

# Or use CloudFormation console to rollback
```

## Next Steps After Deployment

- [ ] Create additional Cognito users for team
- [ ] Upload sample/test data to S3
- [ ] Configure agent parameters
- [ ] Set up additional CloudWatch alarms
- [ ] Run end-to-end integration tests
- [ ] Configure CI/CD pipeline (GitHub Actions)
- [ ] Set up staging environment
- [ ] Plan production deployment
- [ ] Document custom configurations
- [ ] Train team on system usage

## Emergency Contacts

- AWS Support: https://console.aws.amazon.com/support/
- Project Lead: [Add contact]
- DevOps Team: [Add contact]
- On-Call Engineer: [Add contact]

## Important URLs

After deployment, record these URLs:

- **API Gateway Endpoint**: ___________________________________
- **Frontend URL**: ___________________________________
- **Cognito User Pool ID**: ___________________________________
- **CloudWatch Dashboard**: ___________________________________
- **S3 Console**: https://console.aws.amazon.com/s3/
- **Lambda Console**: https://console.aws.amazon.com/lambda/
- **CloudFormation Console**: https://console.aws.amazon.com/cloudformation/

---

**Deployment Date**: _______________  
**Deployed By**: _______________  
**Environment**: _______________  
**Region**: _______________  
**Account ID**: _______________

