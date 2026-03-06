# RetailMind AI - Quick Start Guide

This is a condensed guide to get RetailMind AI up and running quickly.

## Prerequisites

- Python 3.11+
- Node.js 18+
- AWS CLI configured
- AWS CDK CLI installed

## Step 1: Install Dependencies

```powershell
# Backend
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cd ..

# Frontend
cd frontend
npm install
cd ..

# Infrastructure
cd infrastructure\cdk
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cd ..\..
```

## Step 2: Configure AWS

```powershell
# Configure AWS CLI
aws configure

# Bootstrap CDK (replace with your account ID and region)
cd infrastructure\cdk
cdk bootstrap aws://060002399377/us-east-1
```

## Step 3: Deploy Infrastructure

```powershell
# Deploy all stacks (from infrastructure/cdk directory)
cdk deploy --all

# Or deploy individually
cdk deploy RetailMindDataStack
cdk deploy RetailMindComputeStack
cdk deploy RetailMindApiStack
cdk deploy RetailMindMonitoringStack
```

## Step 4: Update Frontend Configuration

```powershell
# Navigate to project root
cd ..\..

# Run the auto-update script
.\scripts\update-frontend-env.ps1
```

## Step 5: Run the Application

```powershell
# Backend (if you have Lambda functions locally)
cd backend
venv\Scripts\activate
# Your backend commands here

# Frontend
cd frontend
npm run dev
```

## Useful Commands

### CDK Commands
```powershell
cdk synth              # Synthesize CloudFormation templates
cdk diff               # Show differences
cdk deploy --all       # Deploy all stacks
cdk destroy --all      # Destroy all stacks
cdk list               # List all stacks
```

### AWS CLI Commands
```powershell
# Check AWS identity
aws sts get-caller-identity

# List S3 buckets
aws s3 ls

# List DynamoDB tables
aws dynamodb list-tables

# Get stack outputs
aws cloudformation describe-stacks --stack-name RetailMindApiStack
```

### View Stack Outputs
```powershell
# Get all outputs
cdk outputs --all

# Get specific stack outputs
aws cloudformation describe-stacks --stack-name RetailMindApiStack --query "Stacks[0].Outputs"
```

## Troubleshooting

### Issue: Bucket Already Exists
**Solution**: Bucket names are now account-specific (e.g., `retailmind-raw-data-060002399377`)

### Issue: CDK Bootstrap Failed
**Solution**: 
```powershell
aws sts get-caller-identity  # Verify credentials
cdk bootstrap aws://ACCOUNT-ID/REGION
```

### Issue: Import Errors
**Solution**: Make sure virtual environment is activated
```powershell
venv\Scripts\activate
```

### Issue: Frontend Can't Connect
**Solution**: Run the update script after deploying API stack
```powershell
.\scripts\update-frontend-env.ps1
```

## Project Structure

```
retailmind-ai/
├── backend/              # Python backend with AI agents
│   ├── src/             # Source code
│   ├── tests/           # Tests
│   └── requirements.txt # Python dependencies
├── frontend/            # TypeScript/React dashboard
│   ├── src/            # Source code
│   └── package.json    # Node dependencies
├── infrastructure/      # AWS CDK infrastructure
│   └── cdk/
│       ├── stacks/     # CDK stack definitions
│       ├── app.py      # CDK app entry point
│       └── cdk.json    # CDK configuration
├── scripts/            # Utility scripts
│   ├── deploy.py       # Deployment automation
│   └── update-frontend-env.ps1  # Update frontend config
└── docs/               # Documentation
```

## Important Files

- `backend/.env` - Backend environment variables
- `frontend/.env` - Frontend environment variables
- `infrastructure/cdk/cdk.json` - CDK configuration
- `AWS_DEPLOYMENT_GUIDE.md` - Detailed deployment guide
- `DEPLOYMENT_CHECKLIST.md` - Deployment checklist

## Next Steps

1. Create Cognito users for testing
2. Upload sample data to S3
3. Test API endpoints
4. Configure monitoring and alerts
5. Set up CI/CD pipeline

## Support

- Full deployment guide: `AWS_DEPLOYMENT_GUIDE.md`
- Architecture documentation: `docs/ARCHITECTURE.md`
- API documentation: `docs/API_DOCUMENTATION.md`
- Troubleshooting: `docs/runbooks/TROUBLESHOOTING_GUIDE.md`

---

**Quick Reference**: For detailed instructions, see `AWS_DEPLOYMENT_GUIDE.md`
