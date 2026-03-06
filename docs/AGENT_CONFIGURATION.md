# RetailMind AI - Agent Configuration Guide

## Table of Contents
1. [Overview](#overview)
2. [Agent Architecture](#agent-architecture)
3. [Configuration Basics](#configuration-basics)
4. [Agent-Specific Configuration](#agent-specific-configuration)
5. [AI Council Configuration](#ai-council-configuration)
6. [Workflow Configuration](#workflow-configuration)
7. [Performance Tuning](#performance-tuning)
8. [Monitoring and Debugging](#monitoring-and-debugging)

## Overview

This guide provides comprehensive instructions for configuring and customizing the AI agents in RetailMind AI. Each agent can be configured to meet specific business requirements, adjust decision thresholds, and optimize performance.

### Configuration Hierarchy

```
Global Configuration
├── Agent-Specific Configuration
│   ├── Market Intelligence Agent
│   ├── Demand Forecast Agent
│   ├── Pricing Optimization Agent
│   ├── Inventory Planning Agent
│   ├── Risk & Compliance Agent
│   └── Business Copilot Agent
├── AI Council Configuration
└── Workflow Configuration
```

## Agent Architecture

### Base Agent Structure

All agents inherit from a base `Agent` class that provides common functionality:

```python
class Agent:
    def __init__(self, config: AgentConfig):
        self.agent_id = config.agent_id
        self.config = config
        self.event_bus = EventBridge()
        self.logger = CloudWatchLogger()
    
    def process(self, input_data: dict) -> AgentDecision:
        """Process input and generate decision"""
        pass
    
    def publish_decision(self, decision: AgentDecision):
        """Publish decision to event bus"""
        pass
```

### Agent Lifecycle

1. **Initialization**: Load configuration and connect to AWS services
2. **Event Reception**: Receive events from EventBridge
3. **Processing**: Analyze data and generate recommendations
4. **Decision Publishing**: Publish decisions to AI Council
5. **Learning**: Update models based on outcomes

## Configuration Basics

### Configuration File Structure

Agent configurations are stored in DynamoDB table `AgentConfigurations`:

```json
{
  "agentId": "market-intelligence-agent",
  "version": "1.0.0",
  "enabled": true,
  "parameters": {
    "confidenceThreshold": 0.75,
    "escalationThreshold": 0.5,
    "processingTimeout": 30,
    "retryAttempts": 3
  },
  "resources": {
    "lambdaMemory": 1024,
    "lambdaTimeout": 60,
    "concurrency": 10
  },
  "integrations": {
    "dataSources": ["s3://retailmind-raw-data"],
    "eventBus": "retailmind-event-bus"
  }
}
```

### Environment Variables

Common environment variables for all agents:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

# Agent Configuration
AGENT_ID=market-intelligence-agent
AGENT_VERSION=1.0.0
CONFIDENCE_THRESHOLD=0.75
ESCALATION_THRESHOLD=0.5

# Data Sources
S3_BUCKET=retailmind-raw-data
DYNAMODB_TABLE=AgentDecisions
REDSHIFT_CLUSTER=retailmind-analytics

# Event Bus
EVENT_BUS_NAME=retailmind-event-bus

# Monitoring
LOG_LEVEL=INFO
CLOUDWATCH_LOG_GROUP=/aws/lambda/retailmind
```

## Agent-Specific Configuration

### 1. Market Intelligence Agent

**Purpose**: Track pricing trends, competitor analysis, and demand patterns

**Configuration Parameters**:

```json
{
  "agentId": "market-intelligence-agent",
  "parameters": {
    "confidenceThreshold": 0.75,
    "pricingAnalysis": {
      "updateFrequency": "hourly",
      "competitorCount": 5,
      "priceChangeThreshold": 0.05,
      "trendWindowDays": 30
    },
    "demandAnalysis": {
      "heatmapResolution": "regional",
      "seasonalityDetection": true,
      "festivalTracking": true
    },
    "dataSources": {
      "marketplaceAPIs": [
        "amazon",
        "flipkart",
        "myntra"
      ],
      "webScraping": {
        "enabled": true,
        "frequency": "daily"
      }
    }
  }
}
```

**Tunable Parameters**:

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `confidenceThreshold` | 0.75 | 0.5-0.95 | Minimum confidence for decisions |
| `updateFrequency` | hourly | hourly/daily | Data refresh frequency |
| `competitorCount` | 5 | 1-20 | Number of competitors to track |
| `priceChangeThreshold` | 0.05 | 0.01-0.20 | Minimum price change to trigger alert |
| `trendWindowDays` | 30 | 7-90 | Historical window for trend analysis |

**Example Configuration Update**:

```python
from src.repositories.agent_config_repository import AgentConfigRepository

config_repo = AgentConfigRepository()
config_repo.update_parameter(
    agent_id="market-intelligence-agent",
    parameter_path="pricingAnalysis.updateFrequency",
    value="daily"
)
```

### 2. Demand Forecast Agent

**Purpose**: Predict future demand using ML models

**Configuration Parameters**:

```json
{
  "agentId": "demand-forecast-agent",
  "parameters": {
    "confidenceThreshold": 0.80,
    "forecastHorizon": 30,
    "modelConfig": {
      "algorithm": "prophet",
      "seasonality": "auto",
      "holidays": true,
      "changepoints": 25
    },
    "retrainingTriggers": {
      "accuracyThreshold": 0.85,
      "dataPointsThreshold": 1000,
      "timeBasedDays": 7
    },
    "sagemakerConfig": {
      "instanceType": "ml.m5.xlarge",
      "endpointName": "demand-forecast-endpoint",
      "modelVersion": "v2.3.1"
    }
  }
}
```

**Tunable Parameters**:

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `confidenceThreshold` | 0.80 | 0.7-0.95 | Minimum confidence for forecasts |
| `forecastHorizon` | 30 | 7-90 | Days to forecast ahead |
| `accuracyThreshold` | 0.85 | 0.7-0.95 | Minimum accuracy before retraining |
| `changepoints` | 25 | 10-50 | Number of potential trend changes |

**Model Selection**:

Available algorithms:
- `prophet`: Facebook Prophet (default)
- `arima`: ARIMA time series
- `lstm`: LSTM neural network
- `xgboost`: XGBoost regression

### 3. Pricing Optimization Agent

**Purpose**: Generate optimal pricing recommendations

**Configuration Parameters**:

```json
{
  "agentId": "pricing-optimization-agent",
  "parameters": {
    "confidenceThreshold": 0.85,
    "pricingStrategy": "margin_aware",
    "constraints": {
      "minMarginPercent": 15,
      "maxDiscountPercent": 30,
      "competitivePriceBuffer": 0.05
    },
    "elasticityModel": {
      "enabled": true,
      "updateFrequency": "weekly",
      "historicalWindowDays": 90
    },
    "simulationConfig": {
      "scenarioCount": 100,
      "confidenceInterval": 0.95
    }
  }
}
```

**Tunable Parameters**:

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `confidenceThreshold` | 0.85 | 0.7-0.95 | Minimum confidence for price changes |
| `minMarginPercent` | 15 | 5-50 | Minimum acceptable margin |
| `maxDiscountPercent` | 30 | 5-70 | Maximum discount allowed |
| `competitivePriceBuffer` | 0.05 | 0.01-0.20 | Price buffer vs competitors |

**Pricing Strategies**:

- `margin_aware`: Prioritize margin maintenance
- `competitive`: Match competitor pricing
- `demand_based`: Price based on demand elasticity
- `hybrid`: Balanced approach

### 4. Inventory Planning Agent

**Purpose**: Optimize inventory levels and prevent stockouts

**Configuration Parameters**:

```json
{
  "agentId": "inventory-planning-agent",
  "parameters": {
    "confidenceThreshold": 0.80,
    "safetyStockDays": 7,
    "reorderPointCalculation": "dynamic",
    "overstockThreshold": {
      "daysOfStock": 60,
      "valueThreshold": 100000
    },
    "stockoutRiskThreshold": {
      "daysOfStock": 7,
      "demandVolatility": 0.3
    },
    "rebalancingConfig": {
      "enabled": true,
      "costThreshold": 1000,
      "frequencyDays": 7
    }
  }
}
```

**Tunable Parameters**:

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `confidenceThreshold` | 0.80 | 0.7-0.95 | Minimum confidence for recommendations |
| `safetyStockDays` | 7 | 3-30 | Days of safety stock to maintain |
| `overstockThreshold` | 60 | 30-180 | Days of stock indicating overstock |
| `stockoutRiskThreshold` | 7 | 3-14 | Days before stockout to trigger alert |

**Reorder Point Calculation Methods**:

- `static`: Fixed reorder point
- `dynamic`: Based on demand forecast
- `seasonal`: Adjusted for seasonality

### 5. Risk & Compliance Agent

**Purpose**: Document processing, fraud detection, and compliance monitoring

**Configuration Parameters**:

```json
{
  "agentId": "risk-compliance-agent",
  "parameters": {
    "confidenceThreshold": 0.90,
    "documentProcessing": {
      "textractConfig": {
        "featureTypes": ["TABLES", "FORMS"],
        "confidenceThreshold": 0.85
      },
      "validationRules": {
        "gstFormat": "^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$",
        "invoiceNumberFormat": "^INV-[0-9]{4}-[0-9]{3}$"
      }
    },
    "fraudDetection": {
      "anomalyThreshold": 0.85,
      "patternMatchingEnabled": true,
      "realTimeScoring": true,
      "historicalWindowDays": 90
    },
    "riskScoring": {
      "supplierRiskWeights": {
        "paymentHistory": 0.3,
        "deliveryPerformance": 0.25,
        "qualityScore": 0.25,
        "complianceRecord": 0.2
      }
    }
  }
}
```

**Tunable Parameters**:

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `confidenceThreshold` | 0.90 | 0.8-0.99 | Minimum confidence for compliance decisions |
| `anomalyThreshold` | 0.85 | 0.7-0.95 | Threshold for fraud detection |
| `textractConfidence` | 0.85 | 0.7-0.95 | Minimum OCR confidence |

### 6. Business Copilot Agent

**Purpose**: Natural language interface for business insights

**Configuration Parameters**:

```json
{
  "agentId": "business-copilot-agent",
  "parameters": {
    "confidenceThreshold": 0.75,
    "nlpConfig": {
      "bedrockModel": "anthropic.claude-v2",
      "temperature": 0.7,
      "maxTokens": 2000,
      "contextWindow": 10
    },
    "queryRouting": {
      "intentClassification": true,
      "multiAgentCoordination": true,
      "fallbackToHuman": true
    },
    "responseGeneration": {
      "explainabilityLevel": "detailed",
      "dataSourceAttribution": true,
      "actionableRecommendations": true
    },
    "learningConfig": {
      "feedbackCollection": true,
      "responseImprovement": true,
      "conversationHistory": 30
    }
  }
}
```

**Tunable Parameters**:

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `confidenceThreshold` | 0.75 | 0.6-0.95 | Minimum confidence for responses |
| `temperature` | 0.7 | 0.0-1.0 | LLM creativity (lower = more focused) |
| `maxTokens` | 2000 | 500-4000 | Maximum response length |
| `contextWindow` | 10 | 5-50 | Number of previous messages to consider |

**Bedrock Model Options**:

- `anthropic.claude-v2`: Claude 2 (default)
- `anthropic.claude-instant-v1`: Claude Instant
- `amazon.titan-text-express-v1`: Titan Text

## AI Council Configuration

### Council Decision-Making

The AI Council coordinates multiple agents for collaborative decision-making.

**Configuration**:

```json
{
  "councilId": "ai-council",
  "parameters": {
    "decisionAggregation": "weighted_voting",
    "conflictResolution": "confidence_based",
    "escalationPolicy": {
      "enabled": true,
      "confidenceThreshold": 0.6,
      "disagreementThreshold": 0.3
    },
    "agentWeights": {
      "market-intelligence-agent": 0.2,
      "demand-forecast-agent": 0.25,
      "pricing-optimization-agent": 0.25,
      "inventory-planning-agent": 0.2,
      "risk-compliance-agent": 0.1
    },
    "votingRules": {
      "minimumParticipants": 3,
      "quorumPercentage": 0.6,
      "unanimityRequired": false
    }
  }
}
```

**Decision Aggregation Methods**:

- `weighted_voting`: Weighted by agent confidence and importance
- `consensus`: Require agreement from all agents
- `majority`: Simple majority vote
- `confidence_based`: Highest confidence wins

**Conflict Resolution Strategies**:

- `confidence_based`: Trust agent with highest confidence
- `domain_expert`: Defer to domain-specific agent
- `human_escalation`: Escalate to human decision-maker
- `simulation`: Run simulations to determine best option

## Workflow Configuration

### Workflow Definition Language (WDL)

Workflows are defined using a JSON-based DSL:

```json
{
  "workflowId": "price-optimization-workflow",
  "version": "1.0.0",
  "trigger": {
    "type": "scheduled",
    "schedule": "rate(1 hour)"
  },
  "steps": [
    {
      "stepId": "analyze-market",
      "type": "agent",
      "agentId": "market-intelligence-agent",
      "input": {
        "region": "$.input.region",
        "category": "$.input.category"
      },
      "next": "forecast-demand"
    },
    {
      "stepId": "forecast-demand",
      "type": "agent",
      "agentId": "demand-forecast-agent",
      "input": {
        "sku": "$.input.sku",
        "marketData": "$.analyze-market.output"
      },
      "next": "optimize-price"
    },
    {
      "stepId": "optimize-price",
      "type": "agent",
      "agentId": "pricing-optimization-agent",
      "input": {
        "sku": "$.input.sku",
        "demandForecast": "$.forecast-demand.output",
        "marketData": "$.analyze-market.output"
      },
      "next": "council-review"
    },
    {
      "stepId": "council-review",
      "type": "council",
      "decision": "approve_price_change",
      "escalationPolicy": {
        "confidenceThreshold": 0.8,
        "humanReview": true
      },
      "end": true
    }
  ],
  "errorHandling": {
    "retryStrategy": {
      "maxAttempts": 3,
      "backoffRate": 2.0
    },
    "fallbackWorkflow": "manual-price-review"
  }
}
```

### Workflow Regeneration Configuration

```json
{
  "regenerationEngine": {
    "enabled": true,
    "triggers": {
      "performanceThreshold": 0.85,
      "executionFailureRate": 0.1,
      "businessRuleChange": true,
      "scheduledReview": "weekly"
    },
    "optimizationGoals": {
      "executionTime": "minimize",
      "successRate": "maximize",
      "businessImpact": "maximize"
    },
    "constraints": {
      "maxSteps": 10,
      "maxExecutionTime": 300,
      "requiredApprovals": ["human"]
    }
  }
}
```

## Performance Tuning

### Lambda Function Optimization

**Memory Allocation**:

| Agent | Recommended Memory | Typical Duration |
|-------|-------------------|------------------|
| Market Intelligence | 1024 MB | 10-30s |
| Demand Forecast | 2048 MB | 30-60s |
| Pricing Optimization | 1536 MB | 20-45s |
| Inventory Planning | 1024 MB | 15-30s |
| Risk & Compliance | 2048 MB | 30-90s |
| Business Copilot | 1536 MB | 5-15s |

**Concurrency Settings**:

```json
{
  "concurrency": {
    "reserved": 10,
    "provisioned": 5,
    "burstLimit": 50
  }
}
```

### DynamoDB Optimization

**Capacity Planning**:

```json
{
  "tables": {
    "AgentDecisions": {
      "capacityMode": "on-demand",
      "gsi": [
        {
          "indexName": "timestamp-index",
          "projectionType": "ALL"
        }
      ]
    }
  }
}
```

### SageMaker Endpoint Optimization

**Instance Configuration**:

```json
{
  "endpoints": {
    "demand-forecast": {
      "instanceType": "ml.m5.xlarge",
      "initialInstanceCount": 2,
      "autoScaling": {
        "minCapacity": 1,
        "maxCapacity": 10,
        "targetValue": 70.0,
        "scaleInCooldown": 300,
        "scaleOutCooldown": 60
      }
    }
  }
}
```

## Monitoring and Debugging

### CloudWatch Metrics

**Custom Metrics**:

```python
from src.utils.metrics import MetricsPublisher

metrics = MetricsPublisher()

# Agent performance metrics
metrics.put_metric(
    namespace="RetailMind/Agents",
    metric_name="DecisionConfidence",
    value=0.92,
    dimensions={
        "AgentId": "pricing-optimization-agent",
        "Environment": "production"
    }
)

# Workflow metrics
metrics.put_metric(
    namespace="RetailMind/Workflows",
    metric_name="ExecutionTime",
    value=45.2,
    dimensions={
        "WorkflowId": "price-optimization-workflow",
        "Status": "success"
    }
)
```

### Logging Configuration

**Log Levels**:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Agent-specific logger
logger = logging.getLogger('market-intelligence-agent')
logger.setLevel(logging.DEBUG)
```

**Structured Logging**:

```python
import json

logger.info(json.dumps({
    "event": "agent_decision",
    "agent_id": "pricing-optimization-agent",
    "decision_id": "DEC123",
    "confidence": 0.92,
    "recommendation": "price_decrease",
    "reasoning": "Competitive pressure"
}))
```

### Debugging Tools

**Agent Testing**:

```python
from src.agents.pricing_optimization_agent import PricingOptimizationAgent

# Initialize agent with test configuration
agent = PricingOptimizationAgent(config={
    "confidenceThreshold": 0.75,
    "debug": True
})

# Test with sample data
result = agent.process({
    "sku": "SKU123",
    "currentPrice": 999.99,
    "competitorPrices": [989.99, 979.99, 1009.99]
})

print(f"Recommendation: {result.recommendation}")
print(f"Confidence: {result.confidence}")
print(f"Reasoning: {result.reasoning}")
```

**Workflow Simulation**:

```python
from src.workflows.workflow_simulator import WorkflowSimulator

simulator = WorkflowSimulator()

# Simulate workflow execution
result = simulator.simulate(
    workflow_id="price-optimization-workflow",
    input_data={"sku": "SKU123", "region": "North"},
    dry_run=True
)

print(f"Estimated execution time: {result.execution_time}s")
print(f"Predicted outcome: {result.outcome}")
```

### Performance Profiling

**Lambda Profiling**:

```python
import time
from functools import wraps

def profile(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        
        logger.info(f"{func.__name__} took {duration:.2f}s")
        return result
    return wrapper

@profile
def process_market_data(data):
    # Processing logic
    pass
```

## Configuration Best Practices

### 1. Start Conservative

Begin with higher confidence thresholds and gradually lower them as you gain confidence in agent performance:

```json
{
  "confidenceThreshold": 0.85,  // Start high
  "escalationThreshold": 0.70   // Escalate more often initially
}
```

### 2. Monitor and Adjust

Regularly review agent performance metrics and adjust configurations:

- Decision accuracy
- Escalation rate
- Processing time
- Business impact

### 3. A/B Testing

Test configuration changes with a subset of data before full deployment:

```python
from src.utils.ab_testing import ABTest

test = ABTest(
    control_config={"confidenceThreshold": 0.80},
    treatment_config={"confidenceThreshold": 0.75},
    split_ratio=0.1  # 10% treatment, 90% control
)

result = test.run(duration_days=7)
print(f"Winner: {result.winner}")
```

### 4. Version Control

Maintain version history of all configuration changes:

```json
{
  "configVersion": "1.2.0",
  "changeLog": [
    {
      "version": "1.2.0",
      "date": "2026-03-03",
      "changes": "Increased confidence threshold to 0.85",
      "author": "admin@retailmind.ai"
    }
  ]
}
```

### 5. Environment-Specific Configs

Use different configurations for dev, staging, and production:

```python
import os

env = os.getenv("ENVIRONMENT", "dev")

configs = {
    "dev": {"confidenceThreshold": 0.70},
    "staging": {"confidenceThreshold": 0.75},
    "production": {"confidenceThreshold": 0.85}
}

config = configs[env]
```

## Troubleshooting

### Common Issues

**Low Confidence Decisions**:
- Review input data quality
- Check model performance metrics
- Adjust confidence thresholds
- Retrain models if needed

**High Escalation Rate**:
- Lower escalation threshold
- Improve agent training
- Review conflict resolution strategy

**Slow Performance**:
- Increase Lambda memory
- Optimize database queries
- Enable caching
- Use provisioned concurrency

**Inconsistent Decisions**:
- Review agent weights in AI Council
- Check for data quality issues
- Verify conflict resolution logic

---

**Document Version**: 1.0  
**Last Updated**: 2026-03-03  
**Maintained By**: RetailMind AI Configuration Team