# Troubleshooting Guide

## Overview

This guide provides systematic troubleshooting procedures for common issues in the RetailMind AI platform. Use this guide to diagnose and resolve problems quickly.

## Quick Diagnostic Checklist

Before diving into specific issues, run this quick health check:

```bash
# 1. Check API health
curl https://api.retailmind.ai/health

# 2. Check CloudWatch dashboard
aws cloudwatch get-dashboard --dashboard-name RetailMind-Overview

# 3. Check recent errors
aws logs tail /aws/lambda/retailmind --follow --since 10m

# 4. Check agent status
python scripts/check_agent_status.py --all
```

## Troubleshooting by Component

### 1. API Gateway Issues

#### Problem: API Returns 502 Bad Gateway

**Symptoms**:
- Users receive 502 errors
- API Gateway logs show "Execution failed due to configuration error"

**Diagnosis**:
```bash
# Check API Gateway configuration
aws apigateway get-rest-api --rest-api-id YOUR_API_ID

# Check integration with Lambda
aws apigateway get-integration \
  --rest-api-id YOUR_API_ID \
  --resource-id YOUR_RESOURCE_ID \
  --http-method GET
```

**Common Causes**:
1. Lambda function not responding
2. IAM permissions missing
3. Lambda timeout exceeded
4. Invalid response format from Lambda

**Solutions**:

```bash
# Solution 1: Check Lambda function
aws lambda get-function --function-name YOUR_FUNCTION_NAME

# Solution 2: Verify IAM role
aws iam get-role --role-name APIGatewayLambdaRole

# Solution 3: Increase Lambda timeout
aws lambda update-function-configuration \
  --function-name YOUR_FUNCTION_NAME \
  --timeout 30

# Solution 4: Check Lambda logs for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/YOUR_FUNCTION_NAME \
  --filter-pattern "ERROR"
```

#### Problem: API Returns 429 Too Many Requests

**Symptoms**:
- Users receive 429 errors during peak times
- CloudWatch shows throttling metrics

**Diagnosis**:
```bash
# Check throttling metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=RetailMindAPI \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

**Solutions**:
```bash
# Increase throttle limits
aws apigateway update-stage \
  --rest-api-id YOUR_API_ID \
  --stage-name production \
  --patch-operations \
    op=replace,path=/throttle/rateLimit,value=1000 \
    op=replace,path=/throttle/burstLimit,value=2000

# Enable API caching
aws apigateway update-stage \
  --rest-api-id YOUR_API_ID \
  --stage-name production \
  --patch-operations op=replace,path=/cacheClusterEnabled,value=true
```

### 2. Lambda Function Issues

#### Problem: Lambda Function Timeout

**Symptoms**:
- Functions timing out after 30 seconds
- CloudWatch logs show "Task timed out after X seconds"

**Diagnosis**:
```bash
# Check function configuration
aws lambda get-function-configuration \
  --function-name market-intelligence-agent

# Check execution duration metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=market-intelligence-agent \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum
```

**Common Causes**:
1. Slow external API calls
2. Large data processing
3. Cold start issues
4. Insufficient memory

**Solutions**:
```bash
# Increase timeout
aws lambda update-function-configuration \
  --function-name market-intelligence-agent \
  --timeout 60

# Increase memory (also increases CPU)
aws lambda update-function-configuration \
  --function-name market-intelligence-agent \
  --memory-size 1024

# Enable provisioned concurrency to reduce cold starts
aws lambda put-provisioned-concurrency-config \
  --function-name market-intelligence-agent \
  --provisioned-concurrent-executions 5 \
  --qualifier production
```

#### Problem: Lambda Out of Memory

**Symptoms**:
- "Runtime exited with error: signal: killed"
- Memory usage approaching limit in CloudWatch

**Diagnosis**:
```bash
# Check memory usage
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name MemoryUtilization \
  --dimensions Name=FunctionName,Value=demand-forecast-agent \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Maximum
```

**Solutions**:
```bash
# Increase memory allocation
aws lambda update-function-configuration \
  --function-name demand-forecast-agent \
  --memory-size 2048

# Optimize code to process data in batches
# Review code for memory leaks
```

### 3. DynamoDB Issues

#### Problem: ProvisionedThroughputExceededException

**Symptoms**:
- Write/read operations failing
- "Request rate is too high" errors

**Diagnosis**:
```bash
# Check consumed capacity
aws dynamodb describe-table --table-name AgentDecisions

# Check throttled requests
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name UserErrors \
  --dimensions Name=TableName,Value=AgentDecisions \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

**Solutions**:
```bash
# Switch to on-demand billing
aws dynamodb update-table \
  --table-name AgentDecisions \
  --billing-mode PAY_PER_REQUEST

# Or increase provisioned capacity
aws dynamodb update-table \
  --table-name AgentDecisions \
  --provisioned-throughput ReadCapacityUnits=100,WriteCapacityUnits=100

# Enable auto-scaling
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/AgentDecisions \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --min-capacity 5 \
  --max-capacity 100
```

#### Problem: Hot Partition

**Symptoms**:
- Some operations slow while others fast
- Uneven distribution of requests

**Diagnosis**:
```bash
# Check partition metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=AgentDecisions \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

**Solutions**:
1. Review partition key design
2. Add random suffix to partition key
3. Use composite keys for better distribution
4. Consider using Global Secondary Index (GSI)

```python
# Example: Add random suffix to distribute load
import random

def generate_partition_key(base_key):
    suffix = random.randint(0, 9)
    return f"{base_key}#{suffix}"
```

### 4. Agent-Specific Issues

#### Problem: Market Intelligence Agent Not Updating

**Symptoms**:
- Stale pricing data
- No new competitor analysis
- Dashboard shows old data

**Diagnosis**:
```bash
# Check agent Lambda logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/market-intelligence-agent \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR"

# Check data ingestion
aws s3 ls s3://retailmind-data/market-intelligence/ --recursive

# Check EventBridge rule
aws events describe-rule --name market-intelligence-trigger
```

**Common Causes**:
1. Data source API down
2. EventBridge rule disabled
3. Lambda function error
4. S3 bucket permissions

**Solutions**:
```bash
# Enable EventBridge rule
aws events enable-rule --name market-intelligence-trigger

# Manually trigger agent
aws lambda invoke \
  --function-name market-intelligence-agent \
  --payload '{"source": "manual-trigger"}' \
  response.json

# Check S3 permissions
aws s3api get-bucket-policy --bucket retailmind-data
```

#### Problem: Demand Forecast Agent Low Accuracy

**Symptoms**:
- Forecast accuracy below 85%
- High prediction errors
- Business complaints about forecasts

**Diagnosis**:
```bash
# Check model metrics
aws sagemaker describe-model --model-name demand-forecast-model

# Check training job status
aws sagemaker list-training-jobs \
  --name-contains demand-forecast \
  --max-results 5

# Query accuracy metrics
python scripts/check_forecast_accuracy.py --days 30
```

**Solutions**:
```python
# Retrain model with recent data
from src.services.ml_training import retrain_demand_model

retrain_demand_model(
    training_data_path="s3://retailmind-data/training/demand/",
    model_name="demand-forecast-model-v2"
)

# Adjust model parameters
update_model_config(
    model_name="demand-forecast-model",
    hyperparameters={
        "epochs": 100,
        "learning_rate": 0.001,
        "batch_size": 64
    }
)
```

#### Problem: Pricing Optimization Agent Recommendations Rejected

**Symptoms**:
- High rejection rate of pricing recommendations
- Business users not trusting suggestions
- Low confidence scores

**Diagnosis**:
```bash
# Check recommendation history
aws dynamodb query \
  --table-name AgentDecisions \
  --key-condition-expression "agentId = :agent" \
  --expression-attribute-values '{":agent":{"S":"pricing-optimization-agent"}}'

# Check confidence scores
python scripts/analyze_agent_confidence.py \
  --agent pricing-optimization-agent \
  --days 7
```

**Solutions**:
```python
# Adjust confidence threshold
from src.repositories.agent_config_repository import AgentConfigRepository

config_repo = AgentConfigRepository()
config_repo.update_parameter(
    agent_id="pricing-optimization-agent",
    parameter_path="confidenceThreshold",
    value=0.75  # Lower threshold
)

# Enable more conservative pricing
config_repo.update_parameter(
    agent_id="pricing-optimization-agent",
    parameter_path="pricingStrategy",
    value="conservative"
)

# Add human review for large price changes
config_repo.update_parameter(
    agent_id="pricing-optimization-agent",
    parameter_path="humanReviewThreshold",
    value=0.10  # Review if price change > 10%
)
```

#### Problem: Business Copilot Slow Responses

**Symptoms**:
- Response time > 10 seconds
- Users complaining about lag
- Timeout errors

**Diagnosis**:
```bash
# Check response time metrics
aws cloudwatch get-metric-statistics \
  --namespace RetailMind/BusinessCopilot \
  --metric-name ResponseTime \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum

# Check Bedrock API latency
aws logs filter-log-events \
  --log-group-name /aws/lambda/business-copilot-agent \
  --filter-pattern "bedrock_latency"
```

**Solutions**:
```bash
# Enable response caching
aws elasticache create-cache-cluster \
  --cache-cluster-id retailmind-cache \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1

# Optimize Bedrock prompts
# Reduce context window size
# Use streaming responses for better UX
```

```python
# Implement caching
from src.services.cache_service import CacheService

cache = CacheService()

def get_copilot_response(query):
    cache_key = f"copilot:{hash(query)}"
    cached_response = cache.get(cache_key)
    
    if cached_response:
        return cached_response
    
    response = generate_response(query)
    cache.set(cache_key, response, ttl=3600)
    return response
```

### 5. Workflow Engine Issues

#### Problem: Workflow Execution Stuck

**Symptoms**:
- Step Functions execution not progressing
- Workflow status shows "Running" for hours
- No error messages

**Diagnosis**:
```bash
# Check execution status
aws stepfunctions describe-execution \
  --execution-arn YOUR_EXECUTION_ARN

# Get execution history
aws stepfunctions get-execution-history \
  --execution-arn YOUR_EXECUTION_ARN \
  --max-results 100

# Check for stuck Lambda
aws lambda list-functions --query 'Functions[?State==`Pending`]'
```

**Solutions**:
```bash
# Stop stuck execution
aws stepfunctions stop-execution \
  --execution-arn YOUR_EXECUTION_ARN \
  --error "ManualStop" \
  --cause "Execution stuck, manually stopped"

# Restart workflow
python scripts/restart_workflow.py \
  --workflow-id YOUR_WORKFLOW_ID \
  --from-step LAST_SUCCESSFUL_STEP
```

#### Problem: Workflow Regeneration Not Adapting

**Symptoms**:
- Same workflows generated repeatedly
- No improvement in performance
- Learning loop not working

**Diagnosis**:
```bash
# Check workflow versions
aws dynamodb query \
  --table-name WorkflowInstances \
  --key-condition-expression "workflowId = :wid" \
  --expression-attribute-values '{":wid":{"S":"pricing-workflow"}}'

# Check learning metrics
python scripts/check_learning_metrics.py --workflow pricing-workflow
```

**Solutions**:
```python
# Force workflow regeneration
from src.agents.workflow_regeneration_agent import WorkflowRegenerationAgent

agent = WorkflowRegenerationAgent()
agent.force_regenerate(
    workflow_id="pricing-workflow",
    reason="manual_trigger",
    performance_threshold=0.8
)

# Reset learning state
agent.reset_learning_state(workflow_id="pricing-workflow")
```

### 6. Data Pipeline Issues

#### Problem: Data Not Being Ingested

**Symptoms**:
- No new data in S3
- Agents using stale data
- Dashboard not updating

**Diagnosis**:
```bash
# Check S3 bucket for recent files
aws s3 ls s3://retailmind-data/raw/ --recursive | tail -20

# Check Lambda triggers
aws lambda list-event-source-mappings \
  --function-name data-ingestion-handler

# Check EventBridge rules
aws events list-rules --name-prefix data-ingestion
```

**Solutions**:
```bash
# Manually trigger ingestion
aws lambda invoke \
  --function-name data-ingestion-handler \
  --payload '{"source": "manual", "data_type": "market_intelligence"}' \
  response.json

# Check data source API
curl -X GET https://data-source-api.example.com/health

# Verify S3 bucket permissions
aws s3api get-bucket-acl --bucket retailmind-data
```

#### Problem: OpenSearch Indexing Failures

**Symptoms**:
- Search not returning recent documents
- Indexing errors in logs
- Semantic search not working

**Diagnosis**:
```bash
# Check OpenSearch cluster health
aws opensearch describe-domain --domain-name retailmind-search

# Check index status
curl -X GET "https://YOUR_OPENSEARCH_ENDPOINT/_cat/indices?v"

# Check indexing errors
aws logs filter-log-events \
  --log-group-name /aws/opensearch/retailmind-search \
  --filter-pattern "indexing_error"
```

**Solutions**:
```bash
# Reindex documents
python scripts/reindex_opensearch.py \
  --index business-intelligence \
  --start-date 2026-03-01

# Increase cluster capacity
aws opensearch update-domain-config \
  --domain-name retailmind-search \
  --cluster-config InstanceType=r6g.large.search,InstanceCount=3

# Clear and rebuild index
curl -X DELETE "https://YOUR_OPENSEARCH_ENDPOINT/business-intelligence"
python scripts/rebuild_index.py --index business-intelligence
```

### 7. Authentication and Authorization Issues

#### Problem: Users Cannot Login

**Symptoms**:
- Login page shows errors
- "Invalid credentials" for valid users
- Cognito errors in logs

**Diagnosis**:
```bash
# Check Cognito user pool
aws cognito-idp describe-user-pool --user-pool-id YOUR_USER_POOL_ID

# Check user status
aws cognito-idp admin-get-user \
  --user-pool-id YOUR_USER_POOL_ID \
  --username user@example.com

# Check app client configuration
aws cognito-idp describe-user-pool-client \
  --user-pool-id YOUR_USER_POOL_ID \
  --client-id YOUR_CLIENT_ID
```

**Solutions**:
```bash
# Reset user password
aws cognito-idp admin-set-user-password \
  --user-pool-id YOUR_USER_POOL_ID \
  --username user@example.com \
  --password NewPassword123! \
  --permanent

# Enable user account
aws cognito-idp admin-enable-user \
  --user-pool-id YOUR_USER_POOL_ID \
  --username user@example.com

# Resend confirmation code
aws cognito-idp resend-confirmation-code \
  --client-id YOUR_CLIENT_ID \
  --username user@example.com
```

#### Problem: API Returns 403 Forbidden

**Symptoms**:
- Authenticated users getting 403 errors
- "Access Denied" messages
- IAM policy issues

**Diagnosis**:
```bash
# Check IAM role policies
aws iam get-role-policy \
  --role-name RetailMindAPIRole \
  --policy-name APIAccessPolicy

# Check API Gateway authorizer
aws apigateway get-authorizer \
  --rest-api-id YOUR_API_ID \
  --authorizer-id YOUR_AUTHORIZER_ID

# Test IAM policy
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::ACCOUNT_ID:role/RetailMindAPIRole \
  --action-names dynamodb:GetItem \
  --resource-arns arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/AgentDecisions
```

**Solutions**:
```bash
# Update IAM policy
aws iam put-role-policy \
  --role-name RetailMindAPIRole \
  --policy-name APIAccessPolicy \
  --policy-document file://policies/api-access-policy.json

# Verify Cognito token
python scripts/verify_cognito_token.py --token YOUR_JWT_TOKEN
```

### 8. Performance Issues

#### Problem: High Latency Across System

**Symptoms**:
- All operations slow
- P99 latency > 5 seconds
- User complaints

**Diagnosis**:
```bash
# Check X-Ray traces
aws xray get-trace-summaries \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s)

# Check all service metrics
python scripts/check_system_performance.py --comprehensive

# Check network latency
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

**Solutions**:
1. Enable caching at multiple layers
2. Optimize database queries
3. Increase Lambda memory
4. Use provisioned concurrency
5. Implement CDN for static assets

```bash
# Enable CloudFront CDN
aws cloudfront create-distribution \
  --origin-domain-name api.retailmind.ai \
  --default-cache-behavior file://cloudfront-config.json

# Enable ElastiCache
aws elasticache create-replication-group \
  --replication-group-id retailmind-cache \
  --replication-group-description "RetailMind Cache" \
  --engine redis \
  --cache-node-type cache.r6g.large \
  --num-cache-clusters 2
```

## Common Error Messages

### Error: "Agent confidence below threshold"

**Meaning**: Agent decision confidence is too low for autonomous action

**Action**:
1. Review agent configuration
2. Check data quality
3. Enable human review
4. Retrain model if needed

### Error: "Workflow rollback initiated"

**Meaning**: Workflow execution failed and is being rolled back

**Action**:
1. Check Step Functions execution history
2. Review failed step logs
3. Fix underlying issue
4. Restart workflow

### Error: "Escalation to human required"

**Meaning**: Decision requires human oversight

**Action**:
1. Review escalation dashboard
2. Provide human decision
3. Update agent learning from decision

### Error: "Data source unavailable"

**Meaning**: External data source not responding

**Action**:
1. Check data source API status
2. Verify network connectivity
3. Use cached data if available
4. Enable fallback data source

## Diagnostic Scripts

### Check Overall System Health

```bash
#!/bin/bash
# scripts/check_system_health.sh

echo "Checking API Gateway..."
aws apigateway get-rest-apis

echo "Checking Lambda functions..."
aws lambda list-functions --query 'Functions[*].[FunctionName,State]'

echo "Checking DynamoDB tables..."
aws dynamodb list-tables

echo "Checking Step Functions..."
aws stepfunctions list-state-machines

echo "Checking recent errors..."
aws logs filter-log-events \
  --log-group-name /aws/lambda/retailmind \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR" \
  --max-items 10
```

### Check Agent Performance

```python
# scripts/check_agent_performance.py
import boto3
from datetime import datetime, timedelta

def check_agent_performance(agent_id, days=7):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('AgentDecisions')
    
    start_date = datetime.now() - timedelta(days=days)
    
    response = table.query(
        KeyConditionExpression='agentId = :agent AND timestamp > :start',
        ExpressionAttributeValues={
            ':agent': agent_id,
            ':start': start_date.isoformat()
        }
    )
    
    decisions = response['Items']
    avg_confidence = sum(d['recommendation']['confidence'] for d in decisions) / len(decisions)
    escalation_rate = sum(1 for d in decisions if d['escalationRequired']) / len(decisions)
    
    print(f"Agent: {agent_id}")
    print(f"Total Decisions: {len(decisions)}")
    print(f"Average Confidence: {avg_confidence:.2f}")
    print(f"Escalation Rate: {escalation_rate:.2%}")
    
    return {
        'total_decisions': len(decisions),
        'avg_confidence': avg_confidence,
        'escalation_rate': escalation_rate
    }

if __name__ == '__main__':
    import sys
    agent_id = sys.argv[1] if len(sys.argv) > 1 else 'market-intelligence-agent'
    check_agent_performance(agent_id)
```

## Best Practices for Troubleshooting

1. **Start with logs**: Always check CloudWatch logs first
2. **Check metrics**: Use CloudWatch metrics to identify patterns
3. **Isolate the issue**: Narrow down to specific component
4. **Test incrementally**: Make one change at a time
5. **Document findings**: Update this guide with new issues
6. **Monitor after fix**: Ensure issue doesn't recur

## Getting Help

If you cannot resolve an issue using this guide:

1. **Check documentation**: Review architecture and API docs
2. **Search logs**: Look for similar error patterns
3. **Contact team**: Reach out in #engineering Slack channel
4. **Create ticket**: File detailed bug report with logs
5. **Escalate**: Follow escalation path in incident response runbook

## Related Documentation

- [Incident Response Runbook](./INCIDENT_RESPONSE.md)
- [Monitoring and Alerting Guide](./MONITORING_ALERTING.md)
- [Architecture Documentation](../ARCHITECTURE.md)
- [API Documentation](../API_DOCUMENTATION.md)

---

**Document Version**: 1.0  
**Last Updated**: 2026-03-03  
**Maintained By**: RetailMind AI Operations Team
