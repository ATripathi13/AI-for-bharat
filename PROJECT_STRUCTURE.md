# RetailMind AI - Project Structure

## Overview

RetailMind AI is a multi-agent decision intelligence platform built on AWS. This document describes the project structure and organization.

## Directory Structure

```
retailmind-ai/
├── backend/                    # Python backend services
│   ├── src/
│   │   ├── agents/            # AI Agent implementations
│   │   ├── services/          # Business logic services
│   │   ├── workflows/         # Workflow definitions
│   │   ├── api/               # API endpoints
│   │   ├── models/            # Data models
│   │   └── utils/             # Utility functions
│   ├── tests/                 # Backend tests
│   ├── requirements.txt       # Python dependencies
│   └── pytest.ini            # Pytest configuration
│
├── frontend/                  # TypeScript/React frontend
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── config/           # Configuration files
│   │   ├── types/            # TypeScript type definitions
│   │   ├── utils/            # Utility functions
│   │   └── test/             # Frontend tests
│   ├── package.json          # Node dependencies
│   └── tsconfig.json         # TypeScript configuration
│
├── infrastructure/            # Infrastructure as Code
│   └── cdk/                  # AWS CDK stacks
│       ├── stacks/
│       │   ├── data_stack.py        # S3, DynamoDB, Redshift
│       │   ├── compute_stack.py     # Lambda, Step Functions
│       │   ├── api_stack.py         # API Gateway, Cognito
│       │   └── monitoring_stack.py  # CloudWatch
│       ├── app.py            # CDK app entry point
│       └── cdk.json          # CDK configuration
│
└── .kiro/specs/              # Feature specifications
    └── retailmind-ai/
        ├── requirements.md   # Requirements document
        ├── design.md         # Design document
        └── tasks.md          # Implementation tasks
```

## Key Components

### Backend (Python)

- **Agents**: Specialized AI agents (Market Intelligence, Demand Forecast, Pricing, Inventory, Risk & Compliance, Business Copilot, Workflow Regeneration)
- **Services**: Business logic and orchestration
- **Workflows**: Dynamic workflow definitions
- **API**: REST API endpoints
- **Models**: Data models and schemas
- **Utils**: AWS clients, configuration, helpers

### Frontend (TypeScript/React)

- **Components**: UI components for dashboards and interfaces
- **Config**: AWS Amplify and application configuration
- **Types**: TypeScript type definitions
- **Utils**: Helper functions and utilities
- **Test**: Frontend test suites

### Infrastructure (AWS CDK)

- **Data Stack**: S3 buckets, DynamoDB tables, Redshift cluster
- **Compute Stack**: Lambda functions, Step Functions, EventBridge
- **API Stack**: API Gateway, Cognito authentication
- **Monitoring Stack**: CloudWatch logs and metrics

## Testing Strategy

### Backend Testing
- **Framework**: pytest with Hypothesis for property-based testing
- **Location**: `backend/tests/`
- **Run**: `pytest` from backend directory

### Frontend Testing
- **Framework**: Vitest with fast-check for property-based testing
- **Location**: `frontend/src/test/`
- **Run**: `npm test` from frontend directory

## AWS Services Used

- **Storage**: S3, DynamoDB, Redshift
- **Compute**: Lambda, Step Functions
- **AI/ML**: Bedrock, SageMaker, OpenSearch, Textract
- **Integration**: EventBridge, API Gateway
- **Auth**: Cognito
- **Monitoring**: CloudWatch

## Getting Started

See SETUP.md for detailed setup instructions.
