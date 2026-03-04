# RetailMind AI

A self-evolving, multi-agent decision intelligence platform for retail, commerce, and marketplace ecosystems.

## Overview

RetailMind AI implements an autonomous Intelligence Loop (Observe → Analyze → Decide → Act → Learn → Regenerate) that continuously improves business outcomes through AI-driven decision-making and dynamic workflow generation.

## Key Features

- **Multi-Agent AI Council**: Specialized agents for market intelligence, demand forecasting, pricing optimization, inventory planning, and risk & compliance
- **Workflow Regeneration Engine**: Dynamically generates and optimizes business workflows without manual intervention
- **Business Copilot**: Natural language interface for data-backed business insights
- **AWS-Native Architecture**: Built on AWS services for scalability and reliability
- **Property-Based Testing**: Comprehensive testing with Hypothesis (Python) and fast-check (TypeScript)

## Quick Start

See [SETUP.md](SETUP.md) for detailed setup instructions.

### Prerequisites
- Python 3.11+
- Node.js 18+
- AWS CLI configured
- AWS CDK CLI

### Basic Setup
```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate  # On Windows
pip install -r requirements.txt

# Frontend
cd frontend
npm install

# Infrastructure
cd infrastructure/cdk
pip install -r requirements.txt
cdk deploy --all
```

## Project Structure

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed project organization.

```
retailmind-ai/
├── backend/          # Python backend with AI agents
├── frontend/         # TypeScript/React dashboard
├── infrastructure/   # AWS CDK infrastructure
└── .kiro/specs/     # Feature specifications
```

## Documentation

- [Requirements](.kiro/specs/retailmind-ai/requirements.md)
- [Design](.kiro/specs/retailmind-ai/design.md)
- [Implementation Tasks](.kiro/specs/retailmind-ai/tasks.md)
- [Setup Guide](SETUP.md)
- [Project Structure](PROJECT_STRUCTURE.md)

## Technology Stack

### Backend
- Python 3.11+
- boto3 (AWS SDK)
- FastAPI
- Hypothesis (Property-based testing)

### Frontend
- TypeScript
- React
- AWS Amplify
- fast-check (Property-based testing)

### Infrastructure
- AWS CDK
- S3, DynamoDB, Redshift
- Lambda, Step Functions
- Bedrock, SageMaker, OpenSearch
- API Gateway, Cognito
- EventBridge, CloudWatch

## Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

