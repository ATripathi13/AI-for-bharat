# RetailMind AI - Complete AWS Deployment Guide

This guide walks you through every step needed to connect your RetailMind AI project with AWS Console and deploy it successfully.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [AWS Account Setup](#aws-account-setup)
3. [Local Environment Setup](#local-environment-setup)
4. [AWS CLI Configuration](#aws-cli-configuration)
5. [AWS Service Enablement](#aws-service-enablement)
6. [IAM Permissions Setup](#iam-permissions-setup)
7. [CDK Bootstrap](#cdk-bootstrap)
8. [Environment Configuration](#environment-configuration)
9. [Infrastructure Deployment](#infrastructure-deployment)
10. [Application Deployment](#application-deployment)
11. [Post-Deployment Verification](#post-deployment-verification)
12. [Troubleshooting](#troubleshooting)

---

## 1. Prerequisites

### Required Software
- **Python 3.11+**: [Download Python](https://www.python.org/downloads/)
- **Node.js 18+**: [Download Node.js](https://nodejs.org/)
- **Git**: [Download Git](https://git-scm.com/downloads)
- **AWS CLI v2**: [Download AWS CLI](https://aws.amazon.com/cli/)
- **AWS CDK CLI**: Install via npm (covered below)

### Verify Installations
```bash
# Check Python version
python --version

# Check Node.js version
node --version

# Check npm version
npm --version

# Check Git version
git --version
```

---

## 2. AWS Account Setup

### Step 2.1: Create AWS Account
1. Go to [AWS Console](https://aws.amazon.com/)
2. Click "Create an AWS Account"
3. Follow the registration process
4. Add payment method (required even for free tier)
5. Verify your identity

### Step 2.2: Sign in to AWS Console
1. Go to [AWS Console](https://console.aws.amazon.com/)
2. Sign in with your root account credentials
3. **Important**: Enable MFA (Multi-Factor Authentication) for security

### Step 2.3: Note Your Account Information
1. In AWS Console, click on your account name (top right)
2. Click "Account"
3. Note down your **Account ID** (12-digit number)
4. Choose your preferred **AWS Region** (e.g., `us-east-1`)

---

## 3. Local Environment Setup

### Step 3.1: Clone the Repository
```bash
# Navigate to your projects directory
cd C:\Users\YourUsername\Projects

# Clone the repository (if not already done)
git clone <your-repo-url>
cd retailmind-ai
```

### Step 3.2: Install AWS CDK CLI
```bash
# Install AWS CDK globally
npm install -g aws-cdk

# Verify installation
cdk --version
```

### Step 3.3: Setup Backend Environment
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Return to root directory
cd ..
```

### Step 3.4: Setup Frontend Environment
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Return to root directory
cd ..
```

### Step 3.5: Setup Infrastructure Environment
```bash
# Navigate to infrastructure/cdk directory
cd infrastructure\cdk

# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Install CDK dependencies
pip install -r requirements.txt

# Return to root directory
cd ..\..
```

---

## 4. AWS CLI Configuration

### Step 4.1: Create IAM User for Deployment
1. Go to [IAM Console](https://console.aws.amazon.com/iam/)
2. Click "Users" → "Add users"
3. User name: `retailmind-deployer`
4. Select "Programmatic access"
5. Click "Next: Permissions"

### Step 4.2: Attach Policies to User
Attach the following AWS managed policies:
- `AdministratorAccess` (for initial setup; restrict later)

Or create a custom policy with these permissions:
- S3 full access
- DynamoDB full access
- Lambda full access
- API Gateway full access
- CloudFormation full access
- IAM limited access (create roles)
- EventBridge full access
- Step Functions full access
- CloudWatch full access
- Cognito full access
- SageMaker full access
- Bedrock full access
- OpenSearch full access
- Textract full access

### Step 4.3: Download Access Keys
1. After creating user, click "Download .csv"
2. Save the file securely
3. Note down:
   - **Access Key ID**
   - **Secret Access Key**

### Step 4.4: Configure AWS CLI
```bash
# Configure AWS CLI
aws configure

# Enter the following when prompted:
# AWS Access Key ID: <your-access-key-id>
# AWS Secret Access Key: <your-secret-access-key>
# Default region name: us-east-1 (or your preferred region)
# Default output format: json
```

### Step 4.5: Verify AWS CLI Configuration
```bash
# Test AWS CLI
aws sts get-caller-identity

# Expected output:
# {
#     "UserId": "AIDAXXXXXXXXXXXXXXXXX",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/retailmind-deployer"
# }
```

---

## 5. AWS Service Enablement

### Step 5.1: Enable Required AWS Services

Most AWS services are enabled by default, but some require explicit enablement:

#### Enable Amazon Bedrock
1. Go to [Amazon Bedrock Console](https://console.aws.amazon.com/bedrock/)
2. Click "Get started"
3. Request access to foundation models:
   - Click "Model access" in left sidebar
   - Click "Manage model access"
   - Select models you need (e.g., Claude, Titan)
   - Click "Request model access"
   - Wait for approval (usually instant for most models)

#### Enable Amazon SageMaker
1. Go to [SageMaker Console](https://console.aws.amazon.com/sagemaker/)
2. Service is automatically enabled when you access it
3. No additional setup required

#### Enable Amazon OpenSearch
1. Go to [OpenSearch Console](https://console.aws.amazon.com/aos/)
2. Service is automatically enabled when you access it

#### Enable Amazon Textract
1. Go to [Textract Console](https://console.aws.amazon.com/textract/)
2. Service is automatically enabled when you access it

### Step 5.2: Check Service Quotas
1. Go to [Service Quotas Console](https://console.aws.amazon.com/servicequotas/)
2. Check quotas for:
   - Lambda concurrent executions (default: 1000)
   - DynamoDB tables per region (default: 256)
   - S3 buckets (default: 100)
3. Request increases if needed

---

## 6. IAM Permissions Setup

### Step 6.1: Create Execution Role for Lambda
This will be created automatically by CDK, but you can verify:

1. Go to [IAM Roles Console](https://console.aws.amazon.com/iam/home#/roles)
2. After deployment, you'll see roles like:
   - `RetailMindComputeStack-AgentExecutionRole-XXXXX`
   - `RetailMindComputeStack-WorkflowExecutionRole-XXXXX`

### Step 6.2: Verify CDK Execution Role
CDK will create necessary roles during bootstrap. No manual action needed.

---

## 7. CDK Bootstrap

### Step 7.1: Bootstrap CDK in Your AWS Account
```bash
# Navigate to infrastructure/cdk directory
cd infrastructure\cdk

# Activate virtual environment
venv\Scripts\activate

# Bootstrap CDK (replace with your account ID and region)
cdk bootstrap aws://123456789012/us-east-1

# Expected output:
# ⏳  Bootstrapping environment aws://123456789012/us-east-1...
# ✅  Environment aws://123456789012/us-east-1 bootstrapped
```

### Step 7.2: Verify Bootstrap
```bash
# List CloudFormation stacks
aws cloudformation describe-stacks --stack-name CDKToolkit

# You should see the CDKToolkit stack in CREATE_COMPLETE status
```

---

## 8. Environment Configuration

### Step 8.1: Configure Backend Environment
```bash
# Navigate to backend directory
cd backend

# Copy example environment file
copy .env.example .env

# Edit .env file with your AWS details
notepad .env
```

Update the following in `.env`:
```bash
# AWS Configuration
AWS_REGION=us-east-1  # Your chosen region
AWS_ACCOUNT_ID=123456789012  # Your AWS account ID

# S3 Configuration (these will be created by CDK)
S3_RAW_DATA_BUCKET=retailmind-raw-data-<account-id>
S3_ML_ARTIFACTS_BUCKET=retailmind-ml-artifacts-<account-id>

# DynamoDB Configuration (these will be created by CDK)
DYNAMODB_TRANSACTIONS_TABLE=retailmind-transactions
DYNAMODB_AGENT_STATES_TABLE=retailmind-agent-states
DYNAMODB_WORKFLOW_INSTANCES_TABLE=retailmind-workflow-instances

# EventBridge Configuration
EVENTBRIDGE_BUS_NAME=retailmind-event-bus

# API Configuration
API_GATEWAY_STAGE=dev

# CloudWatch Configuration
CLOUDWATCH_LOG_GROUP=/aws/retailmind
```

### Step 8.2: Configure Frontend Environment
```bash
# Navigate to frontend directory
cd ..\frontend

# Copy example environment file
copy .env.example .env

# Edit .env file (we'll update this after deployment)
notepad .env
```

For now, set the region:
```bash
VITE_AWS_REGION=us-east-1
```

We'll update the other values after infrastructure deployment.

### Step 8.3: Set CDK Context
```bash
# Navigate to infrastructure/cdk directory
cd ..\infrastructure\cdk

# Edit cdk.json to add context
notepad cdk.json
```

Add your account and region to `cdk.json`:
```json
{
  "app": "python app.py",
  "context": {
    "@aws-cdk/core:enableStackNameDuplicates": "true",
    "aws-cdk:enableDiffNoFail": "true",
    "@aws-cdk/core:stackRelativeExports": "true",
    "environment": "dev",
    "region": "us-east-1",
    "account": "123456789012"
  }
}
```

---

## 9. Infrastructure Deployment

### Step 9.1: Synthesize CDK Stacks
```bash
# Navigate to infrastructure/cdk directory
cd infrastructure\cdk

# Activate virtual environment
venv\Scripts\activate

# Synthesize CloudFormation templates
cdk synth

# This generates CloudFormation templates in cdk.out/
```

### Step 9.2: Review Changes
```bash
# See what will be deployed
cdk diff

# Review the changes carefully
```

### Step 9.3: Deploy Data Stack First
```bash
# Deploy data layer (S3, DynamoDB, Redshift)
cdk deploy RetailMindDataStack

# Confirm deployment when prompted
# Type 'y' and press Enter
```

Wait for deployment to complete (5-10 minutes).

### Step 9.4: Deploy Compute Stack
```bash
# Deploy compute layer (Lambda, Step Functions, SageMaker)
cdk deploy RetailMindComputeStack

# Confirm deployment when prompted
```

Wait for deployment to complete (10-15 minutes).

### Step 9.5: Deploy API Stack
```bash
# Deploy API layer (API Gateway, Cognito)
cdk deploy RetailMindApiStack

# Confirm deployment when prompted
```

Wait for deployment to complete (5-10 minutes).

### Step 9.6: Deploy Monitoring Stack
```bash
# Deploy monitoring layer (CloudWatch)
cdk deploy RetailMindMonitoringStack

# Confirm deployment when prompted
```

Wait for deployment to complete (3-5 minutes).

### Step 9.7: Deploy All Stacks at Once (Alternative)
```bash
# Deploy all stacks in one command
cdk deploy --all --require-approval never

# This will deploy all stacks sequentially
```

### Step 9.8: Capture Stack Outputs
```bash
# Get outputs from all stacks
cdk outputs --all > deployment-outputs.txt

# View the outputs
type deployment-outputs.txt
```

Save these outputs - you'll need them for configuration.

---

## 10. Application Deployment

### Step 10.1: Update Frontend Configuration
```bash
# Navigate to frontend directory
cd ..\..\frontend

# Edit .env file with deployment outputs
notepad .env
```

Update with values from `deployment-outputs.txt`:
```bash
VITE_AWS_REGION=us-east-1
VITE_USER_POOL_ID=<from RetailMindApiStack.UserPoolId>
VITE_USER_POOL_CLIENT_ID=<from RetailMindApiStack.UserPoolClientId>
VITE_API_GATEWAY_URL=<from RetailMindApiStack.ApiEndpoint>
```

### Step 10.2: Deploy Backend Lambda Functions
```bash
# Navigate to root directory
cd ..

# Run package script
python scripts\package_lambda.py

# This packages and uploads Lambda functions
```

### Step 10.3: Build and Deploy Frontend
```bash
# Navigate to frontend directory
cd frontend

# Build frontend
npm run build

# Deploy to S3 (if using S3 hosting)
aws s3 sync dist\ s3://<frontend-bucket-name> --delete

# Or deploy to Amplify (if configured)
# aws amplify start-deployment --app-id <app-id> --branch-name main
```

### Step 10.4: Run Deployment Script (Automated)
```bash
# Navigate to root directory
cd ..

# Run full deployment script
python scripts\deploy.py --environment dev --region us-east-1

# This will:
# 1. Validate environment
# 2. Run tests
# 3. Deploy infrastructure
# 4. Deploy backend
# 5. Deploy frontend
# 6. Run smoke tests
```

---

## 11. Post-Deployment Verification

### Step 11.1: Verify CloudFormation Stacks
1. Go to [CloudFormation Console](https://console.aws.amazon.com/cloudformation/)
2. Verify all stacks show `CREATE_COMPLETE` status:
   - `RetailMindDataStack`
   - `RetailMindComputeStack`
   - `RetailMindApiStack`
   - `RetailMindMonitoringStack`

### Step 11.2: Verify S3 Buckets
1. Go to [S3 Console](https://console.aws.amazon.com/s3/)
2. Verify buckets exist:
   - `retailmind-raw-data-<account-id>`
   - `retailmind-ml-artifacts-<account-id>`
   - `retailmind-documents-<account-id>`

### Step 11.3: Verify DynamoDB Tables
1. Go to [DynamoDB Console](https://console.aws.amazon.com/dynamodb/)
2. Verify tables exist:
   - `retailmind-transactions`
   - `retailmind-agent-states`
   - `retailmind-workflow-instances`
   - `retailmind-audit-trail`

### Step 11.4: Verify Lambda Functions
1. Go to [Lambda Console](https://console.aws.amazon.com/lambda/)
2. Verify functions exist:
   - `retailmind-market-intelligence-agent`
   - `retailmind-demand-forecast-agent`
   - `retailmind-pricing-optimization-agent`
   - `retailmind-inventory-planning-agent`
   - `retailmind-risk-compliance-agent`
   - `retailmind-business-copilot-agent`

### Step 11.5: Verify API Gateway
1. Go to [API Gateway Console](https://console.aws.amazon.com/apigateway/)
2. Find `RetailMindApi`
3. Note the Invoke URL
4. Test health endpoint:
```bash
curl https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/health
```

### Step 11.6: Verify Cognito User Pool
1. Go to [Cognito Console](https://console.aws.amazon.com/cognito/)
2. Find `RetailMindUserPool`
3. Create a test user:
   - Click "Users" tab
   - Click "Create user"
   - Enter email and temporary password

### Step 11.7: Test API Endpoints
```bash
# Test health endpoint
curl https://<api-endpoint>/health

# Expected response:
# {"status": "healthy", "timestamp": "2026-03-06T..."}
```

### Step 11.8: Access Frontend
1. Open browser
2. Navigate to frontend URL (from stack outputs)
3. Sign in with test user credentials
4. Verify dashboard loads

---

## 12. Troubleshooting

### Issue: CDK Bootstrap Fails
**Error**: `Unable to resolve AWS account to use`

**Solution**:
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Re-configure AWS CLI
aws configure

# Try bootstrap again with explicit account/region
cdk bootstrap aws://123456789012/us-east-1
```

### Issue: Stack Deployment Fails
**Error**: `Stack RetailMindDataStack failed to deploy`

**Solution**:
```bash
# Check CloudFormation events
aws cloudformation describe-stack-events --stack-name RetailMindDataStack

# Check for specific error messages
# Common issues:
# - Insufficient permissions
# - Resource limits exceeded
# - Resource name conflicts

# Rollback and retry
cdk destroy RetailMindDataStack
cdk deploy RetailMindDataStack
```

### Issue: Lambda Function Fails
**Error**: `Function execution failed`

**Solution**:
```bash
# Check Lambda logs
aws logs tail /aws/lambda/retailmind-market-intelligence-agent --follow

# Check IAM role permissions
aws iam get-role --role-name <lambda-execution-role>

# Verify environment variables
aws lambda get-function-configuration --function-name retailmind-market-intelligence-agent
```

### Issue: API Gateway Returns 403
**Error**: `{"message": "Forbidden"}`

**Solution**:
```bash
# Check Cognito authentication
# Ensure you're passing valid JWT token in Authorization header

# Test without authentication (if endpoint is public)
curl -X GET https://<api-endpoint>/health

# Check API Gateway logs
aws logs tail /aws/apigateway/RetailMindApi --follow
```

### Issue: Frontend Can't Connect to API
**Error**: `Network Error` or `CORS Error`

**Solution**:
1. Verify API endpoint URL in `.env`
2. Check CORS configuration in API Gateway
3. Verify Cognito configuration
4. Check browser console for specific errors

### Issue: Bedrock Access Denied
**Error**: `AccessDeniedException: You don't have access to the model`

**Solution**:
1. Go to [Bedrock Console](https://console.aws.amazon.com/bedrock/)
2. Click "Model access"
3. Request access to required models
4. Wait for approval (usually instant)

### Issue: Service Quota Exceeded
**Error**: `LimitExceededException`

**Solution**:
1. Go to [Service Quotas Console](https://console.aws.amazon.com/servicequotas/)
2. Find the service and quota
3. Request quota increase
4. Wait for approval (1-2 business days)

### Issue: High AWS Costs
**Problem**: Unexpected charges

**Solution**:
```bash
# Check current costs
aws ce get-cost-and-usage --time-period Start=2026-03-01,End=2026-03-06 --granularity DAILY --metrics BlendedCost

# Set up billing alerts
# 1. Go to CloudWatch Console
# 2. Create billing alarm
# 3. Set threshold (e.g., $50/month)

# Destroy unused resources
cdk destroy --all
```

---

## Next Steps

After successful deployment:

1. **Create Users**: Set up Cognito users for your team
2. **Upload Data**: Upload sample data to S3 for testing
3. **Configure Agents**: Customize agent parameters
4. **Set Up Monitoring**: Configure CloudWatch alarms
5. **Run Tests**: Execute end-to-end tests
6. **Documentation**: Review all documentation in `docs/`

## Important Security Notes

1. **Never commit `.env` files** to version control
2. **Rotate access keys** regularly (every 90 days)
3. **Enable MFA** on all AWS accounts
4. **Use least privilege** IAM policies
5. **Enable CloudTrail** for audit logging
6. **Encrypt sensitive data** at rest and in transit
7. **Regular security audits** using AWS Security Hub

## Cost Optimization Tips

1. **Use on-demand DynamoDB** for variable workloads
2. **Set S3 lifecycle policies** to move old data to Glacier
3. **Use Lambda reserved concurrency** for predictable workloads
4. **Enable CloudWatch Logs retention** policies
5. **Delete unused resources** regularly
6. **Use AWS Cost Explorer** to track spending

## Support and Resources

- **AWS Documentation**: https://docs.aws.amazon.com/
- **AWS CDK Documentation**: https://docs.aws.amazon.com/cdk/
- **Project Documentation**: See `docs/` directory
- **AWS Support**: https://console.aws.amazon.com/support/

---

**Document Version**: 1.0  
**Last Updated**: 2026-03-06  
**Maintained By**: RetailMind AI Team
