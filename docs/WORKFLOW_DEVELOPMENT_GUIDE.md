# RetailMind AI - Workflow Development Guide

## Table of Contents
1. [Overview](#overview)
2. [Workflow Definition Language (WDL)](#workflow-definition-language-wdl)
3. [Creating Workflows](#creating-workflows)
4. [Workflow Patterns](#workflow-patterns)
5. [Testing Workflows](#testing-workflows)
6. [Deploying Workflows](#deploying-workflows)
7. [Monitoring and Debugging](#monitoring-and-debugging)
8. [Best Practices](#best-practices)

## Overview

RetailMind AI uses a Workflow Definition Language (WDL) to define business processes that can be dynamically generated, modified, and optimized by the Workflow Regeneration Engine.

### Key Concepts

- **Workflow**: A sequence of steps that accomplish a business goal
- **Step**: An individual action (agent invocation, decision point, data transformation)
- **Trigger**: Event or schedule that initiates workflow execution
- **State**: Data passed between workflow steps
- **Decision Point**: Conditional logic that determines workflow path

### Workflow Lifecycle

```
Define → Validate → Deploy → Execute → Monitor → Learn → Regenerate
```

## Workflow Definition Language (WDL)

### Basic Structure

```json
{
  "workflowId": "unique-workflow-id",
  "name": "Human-readable workflow name",
  "version": "1.0.0",
  "description": "Workflow description",
  "trigger": {
    "type": "scheduled|event|manual",
    "configuration": {}
  },
  "input": {
    "schema": {}
  },
  "steps": [],
  "output": {
    "schema": {}
  },
  "errorHandling": {},
  "metadata": {}
}
```

### Step Types

#### 1. Agent Step

Invoke an AI agent:

```json
{
  "stepId": "analyze-market",
  "name": "Analyze Market Conditions",
  "type": "agent",
  "agentId": "market-intelligence-agent",
  "input": {
    "region": "$.input.region",
    "category": "$.input.category"
  },
  "timeout": 30,
  "retry": {
    "maxAttempts": 3,
    "backoffRate": 2.0
  },
  "next": "forecast-demand"
}
```

#### 2. Lambda Step

Execute custom Lambda function:

```json
{
  "stepId": "transform-data",
  "name": "Transform Data",
  "type": "lambda",
  "functionName": "data-transformer",
  "input": {
    "data": "$.previous-step.output"
  },
  "next": "next-step"
}
```

#### 3. Choice Step

Conditional branching:

```json
{
  "stepId": "check-confidence",
  "name": "Check Decision Confidence",
  "type": "choice",
  "choices": [
    {
      "condition": "$.confidence >= 0.8",
      "next": "auto-approve"
    },
    {
      "condition": "$.confidence >= 0.6",
      "next": "human-review"
    }
  ],
  "default": "reject"
}
```

#### 4. Parallel Step

Execute multiple steps concurrently:

```json
{
  "stepId": "parallel-analysis",
  "name": "Run Parallel Analysis",
  "type": "parallel",
  "branches": [
    {
      "name": "market-analysis",
      "steps": [
        {
          "stepId": "analyze-market",
          "type": "agent",
          "agentId": "market-intelligence-agent"
        }
      ]
    },
    {
      "name": "demand-forecast",
      "steps": [
        {
          "stepId": "forecast-demand",
          "type": "agent",
          "agentId": "demand-forecast-agent"
        }
      ]
    }
  ],
  "next": "aggregate-results"
}
```

#### 5. Wait Step

Pause workflow execution:

```json
{
  "stepId": "wait-for-approval",
  "name": "Wait for Human Approval",
  "type": "wait",
  "waitType": "event|duration",
  "duration": 3600,  // seconds
  "eventPattern": {
    "source": "approval-system",
    "detailType": "approval-received"
  },
  "next": "process-approval"
}
```

#### 6. Council Step

AI Council decision-making:

```json
{
  "stepId": "council-decision",
  "name": "AI Council Review",
  "type": "council",
  "agents": [
    "market-intelligence-agent",
    "demand-forecast-agent",
    "pricing-optimization-agent"
  ],
  "decisionType": "weighted_voting",
  "escalationPolicy": {
    "confidenceThreshold": 0.7,
    "humanReview": true
  },
  "next": "execute-decision"
}
```

### Input/Output References

Use JSONPath to reference data:

```json
{
  "input": {
    "sku": "$.input.sku",                    // From workflow input
    "marketData": "$.analyze-market.output", // From previous step
    "config": "$.context.configuration"      // From workflow context
  }
}
```

### Error Handling

```json
{
  "errorHandling": {
    "retryStrategy": {
      "maxAttempts": 3,
      "backoffRate": 2.0,
      "retryableErrors": [
        "ServiceUnavailable",
        "ThrottlingException"
      ]
    },
    "catchErrors": [
      {
        "errorType": "AgentTimeout",
        "next": "timeout-handler"
      },
      {
        "errorType": "InsufficientConfidence",
        "next": "escalate-to-human"
      }
    ],
    "fallbackWorkflow": "manual-process-workflow"
  }
}
```

## Creating Workflows

### Example 1: Simple Price Optimization Workflow

```json
{
  "workflowId": "simple-price-optimization",
  "name": "Simple Price Optimization",
  "version": "1.0.0",
  "description": "Optimize pricing for a single SKU",
  "trigger": {
    "type": "event",
    "eventPattern": {
      "source": "retailmind.pricing",
      "detailType": "price-review-requested"
    }
  },
  "input": {
    "schema": {
      "type": "object",
      "properties": {
        "sku": {"type": "string"},
        "region": {"type": "string"}
      },
      "required": ["sku"]
    }
  },
  "steps": [
    {
      "stepId": "get-current-price",
      "name": "Get Current Price",
      "type": "lambda",
      "functionName": "get-product-price",
      "input": {
        "sku": "$.input.sku"
      },
      "next": "analyze-market"
    },
    {
      "stepId": "analyze-market",
      "name": "Analyze Market",
      "type": "agent",
      "agentId": "market-intelligence-agent",
      "input": {
        "sku": "$.input.sku",
        "region": "$.input.region"
      },
      "next": "optimize-price"
    },
    {
      "stepId": "optimize-price",
      "name": "Optimize Price",
      "type": "agent",
      "agentId": "pricing-optimization-agent",
      "input": {
        "sku": "$.input.sku",
        "currentPrice": "$.get-current-price.output.price",
        "marketData": "$.analyze-market.output"
      },
      "next": "check-confidence"
    },
    {
      "stepId": "check-confidence",
      "name": "Check Confidence",
      "type": "choice",
      "choices": [
        {
          "condition": "$.optimize-price.output.confidence >= 0.85",
          "next": "update-price"
        }
      ],
      "default": "escalate"
    },
    {
      "stepId": "update-price",
      "name": "Update Price",
      "type": "lambda",
      "functionName": "update-product-price",
      "input": {
        "sku": "$.input.sku",
        "newPrice": "$.optimize-price.output.recommendedPrice"
      },
      "end": true
    },
    {
      "stepId": "escalate",
      "name": "Escalate to Human",
      "type": "lambda",
      "functionName": "create-escalation",
      "input": {
        "reason": "Low confidence",
        "data": "$.optimize-price.output"
      },
      "end": true
    }
  ]
}
```

### Example 2: Complex Inventory Rebalancing Workflow

```json
{
  "workflowId": "inventory-rebalancing",
  "name": "Multi-Region Inventory Rebalancing",
  "version": "1.0.0",
  "description": "Rebalance inventory across multiple regions",
  "trigger": {
    "type": "scheduled",
    "schedule": "rate(1 day)"
  },
  "steps": [
    {
      "stepId": "get-inventory-status",
      "name": "Get Inventory Status",
      "type": "lambda",
      "functionName": "get-inventory-status",
      "next": "parallel-analysis"
    },
    {
      "stepId": "parallel-analysis",
      "name": "Parallel Analysis",
      "type": "parallel",
      "branches": [
        {
          "name": "demand-forecast",
          "steps": [
            {
              "stepId": "forecast-demand",
              "type": "agent",
              "agentId": "demand-forecast-agent",
              "input": {
                "regions": "$.get-inventory-status.output.regions"
              }
            }
          ]
        },
        {
          "name": "market-analysis",
          "steps": [
            {
              "stepId": "analyze-market",
              "type": "agent",
              "agentId": "market-intelligence-agent",
              "input": {
                "regions": "$.get-inventory-status.output.regions"
              }
            }
          ]
        }
      ],
      "next": "plan-rebalancing"
    },
    {
      "stepId": "plan-rebalancing",
      "name": "Plan Rebalancing",
      "type": "agent",
      "agentId": "inventory-planning-agent",
      "input": {
        "currentInventory": "$.get-inventory-status.output",
        "demandForecast": "$.parallel-analysis.forecast-demand.output",
        "marketData": "$.parallel-analysis.analyze-market.output"
      },
      "next": "council-review"
    },
    {
      "stepId": "council-review",
      "name": "AI Council Review",
      "type": "council",
      "agents": [
        "inventory-planning-agent",
        "demand-forecast-agent",
        "risk-compliance-agent"
      ],
      "decisionType": "weighted_voting",
      "next": "execute-rebalancing"
    },
    {
      "stepId": "execute-rebalancing",
      "name": "Execute Rebalancing",
      "type": "lambda",
      "functionName": "execute-inventory-transfer",
      "input": {
        "plan": "$.plan-rebalancing.output",
        "approval": "$.council-review.output"
      },
      "end": true
    }
  ],
  "errorHandling": {
    "retryStrategy": {
      "maxAttempts": 2,
      "backoffRate": 1.5
    },
    "fallbackWorkflow": "manual-inventory-review"
  }
}
```

## Workflow Patterns

### 1. Sequential Processing

```json
{
  "steps": [
    {"stepId": "step1", "next": "step2"},
    {"stepId": "step2", "next": "step3"},
    {"stepId": "step3", "end": true}
  ]
}
```

### 2. Parallel Processing

```json
{
  "steps": [
    {
      "stepId": "parallel-step",
      "type": "parallel",
      "branches": [
        {"name": "branch1", "steps": [...]},
        {"name": "branch2", "steps": [...]}
      ],
      "next": "aggregate"
    }
  ]
}
```

### 3. Conditional Branching

```json
{
  "steps": [
    {
      "stepId": "decision",
      "type": "choice",
      "choices": [
        {"condition": "$.value > 100", "next": "high-value"},
        {"condition": "$.value > 50", "next": "medium-value"}
      ],
      "default": "low-value"
    }
  ]
}
```

### 4. Loop Pattern

```json
{
  "steps": [
    {
      "stepId": "process-item",
      "type": "lambda",
      "functionName": "process-single-item",
      "next": "check-more-items"
    },
    {
      "stepId": "check-more-items",
      "type": "choice",
      "choices": [
        {"condition": "$.hasMoreItems == true", "next": "process-item"}
      ],
      "default": "complete"
    }
  ]
}
```

### 5. Human-in-the-Loop

```json
{
  "steps": [
    {
      "stepId": "agent-decision",
      "type": "agent",
      "next": "check-confidence"
    },
    {
      "stepId": "check-confidence",
      "type": "choice",
      "choices": [
        {"condition": "$.confidence < 0.7", "next": "request-approval"}
      ],
      "default": "auto-execute"
    },
    {
      "stepId": "request-approval",
      "type": "wait",
      "waitType": "event",
      "eventPattern": {
        "source": "approval-system"
      },
      "next": "process-approval"
    }
  ]
}
```

## Testing Workflows

### Unit Testing Individual Steps

```python
from src.workflows.workflow_engine import WorkflowEngine
from src.workflows.workflow_parser import WorkflowParser

def test_price_optimization_step():
    # Load workflow definition
    parser = WorkflowParser()
    workflow = parser.parse_file("workflows/price-optimization.json")
    
    # Get specific step
    step = workflow.get_step("optimize-price")
    
    # Test with mock data
    input_data = {
        "sku": "SKU123",
        "currentPrice": 999.99,
        "marketData": {...}
    }
    
    result = step.execute(input_data)
    
    assert result.confidence >= 0.75
    assert result.recommendedPrice > 0
```

### Integration Testing Complete Workflows

```python
def test_complete_workflow():
    engine = WorkflowEngine()
    
    # Execute workflow
    execution = engine.start_execution(
        workflow_id="simple-price-optimization",
        input_data={
            "sku": "SKU123",
            "region": "North"
        }
    )
    
    # Wait for completion
    result = execution.wait_for_completion(timeout=60)
    
    assert result.status == "SUCCESS"
    assert "newPrice" in result.output
```

### Property-Based Testing

```python
from hypothesis import given, strategies as st

@given(
    sku=st.text(min_size=1, max_size=20),
    region=st.sampled_from(["North", "South", "East", "West"])
)
def test_workflow_handles_all_inputs(sku, region):
    """
    Feature: retailmind-ai, Property 9: Workflow Regeneration Adaptability
    Validates: Requirements 7.1, 7.2, 7.3
    """
    engine = WorkflowEngine()
    
    execution = engine.start_execution(
        workflow_id="simple-price-optimization",
        input_data={"sku": sku, "region": region}
    )
    
    result = execution.wait_for_completion(timeout=60)
    
    # Workflow should complete without errors
    assert result.status in ["SUCCESS", "ESCALATED"]
```

### Simulation Testing

```python
from src.workflows.workflow_simulator import WorkflowSimulator

def test_workflow_simulation():
    simulator = WorkflowSimulator()
    
    # Simulate 100 executions
    results = simulator.simulate(
        workflow_id="simple-price-optimization",
        iterations=100,
        input_generator=lambda: {
            "sku": f"SKU{random.randint(1, 1000)}",
            "region": random.choice(["North", "South"])
        }
    )
    
    # Analyze results
    assert results.success_rate >= 0.95
    assert results.avg_execution_time < 60
```

## Deploying Workflows

### Deployment Process

1. **Validate Workflow Definition**

```python
from src.workflows.workflow_validator import WorkflowValidator

validator = WorkflowValidator()
result = validator.validate_file("workflows/my-workflow.json")

if not result.is_valid:
    print(f"Validation errors: {result.errors}")
else:
    print("Workflow is valid")
```

2. **Deploy to Environment**

```python
from src.workflows.workflow_deployer import WorkflowDeployer

deployer = WorkflowDeployer()

# Deploy to staging
deployer.deploy(
    workflow_file="workflows/my-workflow.json",
    environment="staging"
)

# After testing, deploy to production
deployer.deploy(
    workflow_file="workflows/my-workflow.json",
    environment="production"
)
```

3. **Version Management**

```python
# Create new version
deployer.create_version(
    workflow_id="simple-price-optimization",
    version="1.1.0",
    changes="Improved confidence threshold logic"
)

# Rollback if needed
deployer.rollback(
    workflow_id="simple-price-optimization",
    to_version="1.0.0"
)
```

### CI/CD Integration

```yaml
# .github/workflows/deploy-workflows.yml
name: Deploy Workflows

on:
  push:
    branches: [main]
    paths:
      - 'workflows/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Validate Workflows
        run: |
          python scripts/validate_workflows.py
      
      - name: Run Tests
        run: |
          pytest tests/workflows/
      
      - name: Deploy to Staging
        run: |
          python scripts/deploy_workflows.py --env staging
      
      - name: Run Integration Tests
        run: |
          pytest tests/integration/
      
      - name: Deploy to Production
        if: success()
        run: |
          python scripts/deploy_workflows.py --env production
```

## Monitoring and Debugging

### CloudWatch Metrics

```python
from src.utils.metrics import MetricsPublisher

metrics = MetricsPublisher()

# Workflow execution metrics
metrics.put_metric(
    namespace="RetailMind/Workflows",
    metric_name="ExecutionDuration",
    value=execution_time,
    dimensions={
        "WorkflowId": workflow_id,
        "Status": "SUCCESS"
    }
)

# Step-level metrics
metrics.put_metric(
    namespace="RetailMind/Workflows/Steps",
    metric_name="StepDuration",
    value=step_duration,
    dimensions={
        "WorkflowId": workflow_id,
        "StepId": step_id
    }
)
```

### Logging

```python
import logging
import json

logger = logging.getLogger('workflow-engine')

# Structured logging
logger.info(json.dumps({
    "event": "workflow_started",
    "workflow_id": workflow_id,
    "execution_id": execution_id,
    "input": input_data
}))

logger.info(json.dumps({
    "event": "step_completed",
    "workflow_id": workflow_id,
    "step_id": step_id,
    "duration": duration,
    "output": output_data
}))
```

### Debugging Failed Workflows

```python
from src.workflows.workflow_debugger import WorkflowDebugger

debugger = WorkflowDebugger()

# Get execution details
execution = debugger.get_execution(execution_id)

print(f"Status: {execution.status}")
print(f"Failed Step: {execution.failed_step}")
print(f"Error: {execution.error}")

# Get step history
history = debugger.get_step_history(execution_id)
for step in history:
    print(f"{step.step_id}: {step.status} ({step.duration}s)")

# Replay execution with debug mode
debugger.replay_execution(
    execution_id=execution_id,
    debug=True,
    breakpoints=["optimize-price"]
)
```

## Best Practices

### 1. Keep Workflows Simple

- Limit workflows to 10-15 steps
- Break complex workflows into sub-workflows
- Use clear, descriptive step names

### 2. Handle Errors Gracefully

```json
{
  "errorHandling": {
    "retryStrategy": {
      "maxAttempts": 3,
      "backoffRate": 2.0
    },
    "catchErrors": [
      {
        "errorType": "AgentTimeout",
        "next": "timeout-handler"
      }
    ],
    "fallbackWorkflow": "manual-process"
  }
}
```

### 3. Use Timeouts

```json
{
  "stepId": "long-running-step",
  "timeout": 300,  // 5 minutes
  "onTimeout": "escalate-to-human"
}
```

### 4. Implement Idempotency

Ensure steps can be safely retried:

```python
def process_order(order_id):
    # Check if already processed
    if is_already_processed(order_id):
        return get_existing_result(order_id)
    
    # Process order
    result = do_processing(order_id)
    
    # Mark as processed
    mark_as_processed(order_id, result)
    
    return result
```

### 5. Version Control Workflows

- Use semantic versioning (1.0.0, 1.1.0, 2.0.0)
- Maintain changelog
- Test before deploying new versions

### 6. Monitor Performance

- Track execution time
- Monitor success rate
- Alert on anomalies

### 7. Document Workflows

Include comprehensive metadata:

```json
{
  "metadata": {
    "author": "team@retailmind.ai",
    "created": "2026-03-01",
    "lastModified": "2026-03-03",
    "purpose": "Optimize pricing based on market conditions",
    "businessOwner": "pricing-team",
    "sla": {
      "maxExecutionTime": 60,
      "targetSuccessRate": 0.95
    }
  }
}
```

### 8. Test Thoroughly

- Unit test individual steps
- Integration test complete workflows
- Property-based test with varied inputs
- Simulate production scenarios

---

**Document Version**: 1.0  
**Last Updated**: 2026-03-03  
**Maintained By**: RetailMind AI Workflow Team
