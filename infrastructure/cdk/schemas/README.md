# RetailMind AI - Data Schemas Documentation

This directory contains all data model schemas and infrastructure definitions for the RetailMind AI platform.

## Overview

The RetailMind AI platform uses a multi-tier data architecture:

1. **Application Layer**: Python/TypeScript data models for business logic
2. **Transactional Layer**: DynamoDB tables for real-time operations
3. **Storage Layer**: S3 buckets for raw data and ML artifacts
4. **Analytics Layer**: Redshift warehouse for business intelligence

## Files

### Data Models

#### Backend (Python)
- `backend/src/models/agent_decision.py` - Agent decision data model
- `backend/src/models/workflow_instance.py` - Workflow execution data model
- `backend/src/models/business_intelligence.py` - Business intelligence data model

#### Frontend (TypeScript)
- `frontend/src/types/index.ts` - TypeScript type definitions

### Infrastructure Schemas

#### DynamoDB
- `dynamodb_schemas.py` - DynamoDB table definitions using AWS CDK
  - AgentDecisions table
  - WorkflowInstances table
  - BusinessIntelligence table
  - AgentStates table
  - Transactions table

#### S3
- `s3_structure.py` - S3 bucket structure definitions using AWS CDK
  - Raw Data bucket
  - ML Artifacts bucket
  - Processed Data bucket
  - Workflow Definitions bucket

#### Redshift
- `redshift_schema.sql` - Complete Redshift DDL for analytics warehouse
- `redshift_schema.py` - Python utilities for Redshift schema management

## Data Model Details

### AgentDecision

Represents a decision made by an AI agent.

**Python Model**: `backend/src/models/agent_decision.py`
**TypeScript Model**: `frontend/src/types/index.ts`
**DynamoDB Table**: `AgentDecisions`

**Key Fields**:
- `agentId` (partition key) - Unique identifier for the agent
- `decisionId` (sort key) - Unique identifier for the decision
- `timestamp` - When the decision was made
- `recommendation` - The agent's recommendation with confidence score
- `escalationRequired` - Whether human oversight is needed

**Indexes**:
- `timestamp-index` - Query decisions by time
- `escalation-index` - Query decisions requiring escalation

### WorkflowInstance

Represents an execution instance of a workflow.

**Python Model**: `backend/src/models/workflow_instance.py`
**TypeScript Model**: `frontend/src/types/index.ts`
**DynamoDB Table**: `WorkflowInstances`

**Key Fields**:
- `workflowId` (partition key) - Workflow template identifier
- `instanceId` (sort key) - Unique execution instance identifier
- `status` - Current execution status (running, completed, failed, rolled_back)
- `steps` - Array of workflow steps
- `performance` - Execution metrics

**Indexes**:
- `status-index` - Query workflows by status
- `creator-index` - Query workflows by creator

### BusinessIntelligence

Represents business intelligence insights and recommendations.

**Python Model**: `backend/src/models/business_intelligence.py`
**TypeScript Model**: `frontend/src/types/index.ts`
**DynamoDB Table**: `BusinessIntelligence`

**Key Fields**:
- `entityType` (partition key) - Type of entity (pricing, demand, inventory, risk)
- `entityId` (sort key) - Unique identifier for the entity
- `insights` - Analysis results with confidence scores
- `recommendations` - Action recommendations with priorities
- `dataSource` - Sources used for analysis

**Indexes**:
- `confidence-index` - Query insights by confidence level

## S3 Bucket Structure

### Raw Data Bucket (`retailmind-raw-data`)

Stores raw ingested data from various sources.

**Structure**:
```
/market-intelligence/
  /pricing/YYYY/MM/DD/
  /competitor-data/YYYY/MM/DD/
  /demand-patterns/YYYY/MM/DD/
/sales-data/
  /transactions/YYYY/MM/DD/
  /inventory/YYYY/MM/DD/
/documents/
  /invoices/YYYY/MM/DD/
  /contracts/YYYY/MM/DD/
  /gst-documents/YYYY/MM/DD/
```

**Lifecycle**: 90 days → Infrequent Access, 365 days → Glacier

### ML Artifacts Bucket (`retailmind-ml-artifacts`)

Stores ML models, training data, and evaluation results.

**Structure**:
```
/models/
  /demand-forecast/versions/
  /pricing-optimization/versions/
  /fraud-detection/versions/
/training-data/
/evaluation-results/
/feature-store/
```

**Lifecycle**: Old versions expire after 90 days

### Processed Data Bucket (`retailmind-processed-data`)

Stores processed analytics and reports.

**Structure**:
```
/analytics/
  /market-intelligence/YYYY/MM/DD/
  /demand-forecasts/YYYY/MM/DD/
  /pricing-recommendations/YYYY/MM/DD/
  /inventory-insights/YYYY/MM/DD/
/reports/
  /daily/YYYY/MM/DD/
  /weekly/YYYY/WW/
  /monthly/YYYY/MM/
/exports/
```

**Lifecycle**: Reports expire after 730 days

### Workflow Definitions Bucket (`retailmind-workflows`)

Stores workflow templates and generated workflows.

**Structure**:
```
/templates/
/generated/YYYY/MM/DD/
/archived/YYYY/MM/DD/
```

**Lifecycle**: Versioned, no expiration

## Redshift Analytics Warehouse

### Schema: `retailmind_analytics`

#### Dimension Tables

1. **dim_products** - Product master data with SCD Type 2
2. **dim_regions** - Geographic regions
3. **dim_time** - Time dimension for date-based analysis
4. **dim_agents** - AI agents metadata

#### Fact Tables

1. **fact_sales** - Sales transactions
2. **fact_inventory** - Inventory snapshots
3. **fact_pricing** - Pricing history
4. **fact_demand_forecast** - Demand forecasts with accuracy tracking
5. **fact_agent_decisions** - Agent decision history
6. **fact_workflow_executions** - Workflow execution metrics
7. **fact_risk_compliance** - Risk and compliance events

#### Aggregate Tables

1. **agg_daily_product_performance** - Daily product metrics
2. **agg_monthly_agent_performance** - Monthly agent performance

#### Views

1. **v_current_inventory_status** - Current inventory across all products
2. **v_agent_decision_performance** - Agent performance metrics
3. **v_sales_vs_forecast** - Sales vs forecast comparison

## Data Flow

```
Raw Data (S3) 
  → DynamoDB (Real-time transactions)
  → Redshift (Analytics warehouse)
  → Business Intelligence (Insights & Recommendations)
```

## Usage Examples

### Python - Creating an Agent Decision

```python
from backend.src.models import AgentDecision, Recommendation
from datetime import datetime

recommendation = Recommendation(
    action="increase_price",
    confidence=0.92,
    reasoning="Market conditions favorable",
    supporting_data=[{"metric": "demand", "value": 1.2}]
)

decision = AgentDecision(
    agent_id="pricing-agent-001",
    decision_id="dec-12345",
    timestamp=datetime.now(),
    input_data={"product_id": "SKU-001"},
    recommendation=recommendation,
    escalation_required=False
)

# Convert to dict for DynamoDB
decision_dict = decision.to_dict()
```

### TypeScript - Using Type Definitions

```typescript
import { AgentDecision, WorkflowInstance } from './types';

const decision: AgentDecision = {
  agentId: 'pricing-agent-001',
  decisionId: 'dec-12345',
  timestamp: new Date(),
  inputData: { productId: 'SKU-001' },
  recommendation: {
    action: 'increase_price',
    confidence: 0.92,
    reasoning: 'Market conditions favorable',
    supportingData: []
  },
  escalationRequired: false
};
```

### CDK - Creating DynamoDB Tables

```python
from infrastructure.cdk.schemas import DynamoDBSchemas

# In your CDK stack
agent_decisions_table = DynamoDBSchemas.create_agent_decisions_table(
    self, 
    table_name="RetailMind-AgentDecisions"
)
```

### CDK - Creating S3 Buckets

```python
from infrastructure.cdk.schemas import S3BucketStructure

# In your CDK stack
raw_data_bucket = S3BucketStructure.create_raw_data_bucket(
    self,
    bucket_name="retailmind-raw-data-prod"
)
```

## Requirements Validation

This implementation satisfies **Requirement 9.1**:
- ✅ Amazon S3 for raw data storage
- ✅ DynamoDB for real-time transactions and agent states
- ✅ Redshift for analytics warehousing
- ✅ Proper data organization and lifecycle management
- ✅ Encryption and security best practices
- ✅ Scalable schema design for millions of transactions

## Next Steps

1. Deploy DynamoDB tables using CDK (Task 1 - Infrastructure)
2. Create S3 buckets using CDK (Task 1 - Infrastructure)
3. Provision Redshift cluster and execute schema DDL (Task 1 - Infrastructure)
4. Implement data access layer with repository pattern (Task 2.3)
5. Set up data ingestion pipelines (Task 5+)
