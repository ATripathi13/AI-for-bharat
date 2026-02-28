# RetailMind AI - Setup Guide

## Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- AWS CLI configured with appropriate credentials
- AWS CDK CLI installed (`npm install -g aws-cdk`)
- Git

## Backend Setup

### 1. Navigate to Backend Directory
```bash
cd backend
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Configure Environment
```bash
# Copy example environment file
copy .env.example .env

# Edit .env with your AWS configuration
```

### 5. Run Tests
```bash
pytest
```

## Frontend Setup

### 1. Navigate to Frontend Directory
```bash
cd frontend
```

### 2. Install Dependencies
```bash
npm install
```

### 3. Configure Environment
```bash
# Copy example environment file
copy .env.example .env

# Edit .env with your AWS configuration
```

### 4. Run Development Server
```bash
npm run dev
```

### 5. Run Tests
```bash
npm test
```

## Infrastructure Setup

### 1. Navigate to Infrastructure Directory
```bash
cd infrastructure/cdk
```

### 2. Install CDK Dependencies
```bash
pip install -r requirements.txt
```

### 3. Bootstrap CDK (First Time Only)
```bash
cdk bootstrap aws://ACCOUNT-ID/REGION
```

### 4. Deploy Infrastructure
```bash
# Deploy all stacks
cdk deploy --all

# Or deploy individual stacks
cdk deploy RetailMindDataStack
cdk deploy RetailMindComputeStack
cdk deploy RetailMindApiStack
cdk deploy RetailMindMonitoringStack
```

### 5. View Stack Outputs
```bash
cdk outputs
```

## AWS Configuration

### Required AWS Services

Ensure the following services are enabled in your AWS account:
- Amazon S3
- Amazon DynamoDB
- Amazon Redshift (optional for analytics)
- AWS Lambda
- AWS Step Functions
- Amazon EventBridge
- Amazon API Gateway
- Amazon Cognito
- Amazon Bedrock
- Amazon SageMaker
- Amazon OpenSearch
- Amazon Textract
- Amazon CloudWatch

### IAM Permissions

The deployment requires permissions for:
- Creating and managing S3 buckets
- Creating and managing DynamoDB tables
- Creating and managing Lambda functions
- Creating and managing Step Functions state machines
- Creating and managing EventBridge rules
- Creating and managing API Gateway APIs
- Creating and managing Cognito user pools
- Creating and managing CloudWatch log groups

## Development Workflow

### Backend Development
```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
pytest  # Run tests
```

### Frontend Development
```bash
cd frontend
npm run dev  # Start development server
npm test    # Run tests
```

### Infrastructure Changes
```bash
cd infrastructure/cdk
cdk diff    # Preview changes
cdk deploy  # Deploy changes
```

## Testing

### Backend Property-Based Tests
```bash
cd backend
pytest -m property  # Run only property-based tests
```

### Frontend Property-Based Tests
```bash
cd frontend
npm test -- --grep "property"  # Run only property-based tests
```

## Troubleshooting

### Backend Issues
- Ensure Python virtual environment is activated
- Check AWS credentials: `aws sts get-caller-identity`
- Verify environment variables in `.env`

### Frontend Issues
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Check environment variables in `.env`

### Infrastructure Issues
- Verify CDK bootstrap: `cdk bootstrap`
- Check AWS credentials and permissions
- Review CloudFormation stack events in AWS Console

## Next Steps

After setup is complete:
1. Review the requirements document: `.kiro/specs/retailmind-ai/requirements.md`
2. Review the design document: `.kiro/specs/retailmind-ai/design.md`
3. Start implementing tasks from: `.kiro/specs/retailmind-ai/tasks.md`

## Support

For issues or questions, refer to:
- AWS CDK Documentation: https://docs.aws.amazon.com/cdk/
- Hypothesis Documentation: https://hypothesis.readthedocs.io/
- fast-check Documentation: https://fast-check.dev/
