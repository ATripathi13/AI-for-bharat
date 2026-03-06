# Monitoring and Alerting Runbook

## Overview

This runbook describes the monitoring and alerting setup for RetailMind AI platform. It covers CloudWatch metrics, logs, alarms, dashboards, and incident response procedures.

## Table of Contents

1. [Monitoring Architecture](#monitoring-architecture)
2. [CloudWatch Metrics](#cloudwatch-metrics)
3. [CloudWatch Logs](#cloudwatch-logs)
4. [CloudWatch Alarms](#cloudwatch-alarms)
5. [CloudWatch Dashboards](#cloudwatch-dashboards)
6. [X-Ray Tracing](#x-ray-tracing)
7. [Alert Channels](#alert-channels)
8. [Monitoring Best Practices](#monitoring-best-practices)
9. [Troubleshooting Monitoring Issues](#troubleshooting-monitoring-issues)

---

## 1. Monitoring Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  Lambda Functions | API Gateway | Step Functions            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    CloudWatch Metrics                        │
│  - Invocations  - Duration  - Errors  - Throttles          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    CloudWatch Logs                           │
│  - Application Logs  - Access Logs  - Error Logs           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    CloudWatch Alarms                         │
│  - Threshold Alarms  - Anomaly Detection  - Composite       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Alert Channels                            │
│  - SNS Topics  - Email  - Slack  - PagerDuty               │
└─────────────────────────────────────────────────────────────┘
```

### Monitoring Layers

1. **Infrastructure Monitoring**: AWS service health and performance
2. **Application Monitoring**: Business logic and agent performance
3. **Business Monitoring**: KPIs and business metrics
4. **Security Monitoring**: Access patterns and security events

---

## 2. CloudWatch Metrics

### Lambda Function Metrics


#### Standard Metrics (Automatic)

| Metric | Description | Unit | Threshold |
|--------|-------------|------|-----------|
| `Invocations` | Number of function invocations | Count | Monitor trends |
| `Duration` | Execution time | Milliseconds | < 30000ms (timeout) |
| `Errors` | Number of errors | Count | < 1% of invocations |
| `Throttles` | Number of throttled invocations | Count | 0 |
| `ConcurrentExecutions` | Concurrent executions | Count | < 900 (reserve buffer) |
| `DeadLetterErrors` | DLQ delivery failures | Count | 0 |

#### Custom Metrics (Application-Level)

```python
# Example: Publishing custom metrics from Lambda
import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch')

def publish_agent_decision_metric(agent_name, confidence_score):
    cloudwatch.put_metric_data(
        Namespace='RetailMind/Agents',
        MetricData=[
            {
                'MetricName': 'DecisionConfidence',
                'Dimensions': [
                    {'Name': 'AgentName', 'Value': agent_name}
                ],
                'Value': confidence_score,
                'Unit': 'None',
                'Timestamp': datetime.utcnow()
            }
        ]
    )
```

**Custom Metrics to Track**:
- `DecisionConfidence`: Agent decision confidence scores
- `WorkflowExecutionTime`: End-to-end workflow duration
- `DataProcessingLatency`: Time to process incoming data
- `AgentAgreementRate`: Percentage of agent consensus
- `BusinessRuleViolations`: Number of rule violations detected

### API Gateway Metrics

| Metric | Description | Unit | Threshold |
|--------|-------------|------|-----------|
| `Count` | Total API requests | Count | Monitor trends |
| `4XXError` | Client errors | Count | < 5% of requests |
| `5XXError` | Server errors | Count | < 1% of requests |
| `Latency` | Request latency | Milliseconds | < 1000ms (p99) |
| `IntegrationLatency` | Backend latency | Milliseconds | < 500ms (p99) |
| `CacheHitCount` | Cache hits | Count | > 50% of requests |
| `CacheMissCount` | Cache misses | Count | < 50% of requests |

### DynamoDB Metrics

| Metric | Description | Unit | Threshold |
|--------|-------------|------|-----------|
| `ConsumedReadCapacityUnits` | Read capacity used | Count | < 80% of provisioned |
| `ConsumedWriteCapacityUnits` | Write capacity used | Count | < 80% of provisioned |
| `UserErrors` | Client-side errors | Count | < 1% of requests |
| `SystemErrors` | Server-side errors | Count | 0 |
| `ThrottledRequests` | Throttled requests | Count | 0 |
| `ConditionalCheckFailedRequests` | Failed conditional writes | Count | Monitor trends |

### Step Functions Metrics

| Metric | Description | Unit | Threshold |
|--------|-------------|------|-----------|
| `ExecutionsStarted` | Workflow executions started | Count | Monitor trends |
| `ExecutionsSucceeded` | Successful executions | Count | > 95% of started |
| `ExecutionsFailed` | Failed executions | Count | < 5% of started |
| `ExecutionsTimedOut` | Timed out executions | Count | < 1% of started |
| `ExecutionTime` | Execution duration | Milliseconds | < 300000ms (5 min) |

### S3 Metrics

| Metric | Description | Unit | Threshold |
|--------|-------------|------|-----------|
| `NumberOfObjects` | Total objects | Count | Monitor trends |
| `BucketSizeBytes` | Total bucket size | Bytes | Monitor costs |
| `AllRequests` | Total requests | Count | Monitor trends |
| `4xxErrors` | Client errors | Count | < 1% of requests |
| `5xxErrors` | Server errors | Count | 0 |

### EventBridge Metrics

| Metric | Description | Unit | Threshold |
|--------|-------------|------|-----------|
| `Invocations` | Events published | Count | Monitor trends |
| `FailedInvocations` | Failed event deliveries | Count | < 1% of invocations |
| `ThrottledRules` | Throttled rules | Count | 0 |
| `TriggeredRules` | Rules triggered | Count | Monitor trends |

---

## 3. CloudWatch Logs

### Log Groups

| Log Group | Source | Retention | Purpose |
|-----------|--------|-----------|---------|
| `/aws/lambda/retailmind-market-intelligence` | Market Intelligence Agent | 30 days | Agent decisions and analysis |
| `/aws/lambda/retailmind-demand-forecast` | Demand Forecast Agent | 30 days | Forecasting operations |
| `/aws/lambda/retailmind-pricing-optimization` | Pricing Agent | 30 days | Pricing decisions |
| `/aws/lambda/retailmind-inventory-planning` | Inventory Agent | 30 days | Inventory recommendations |
| `/aws/lambda/retailmind-risk-compliance` | Risk & Compliance Agent | 90 days | Compliance checks (audit) |
| `/aws/lambda/retailmind-business-copilot` | Business Copilot | 30 days | User interactions |
| `/aws/apigateway/retailmind-api` | API Gateway | 30 days | API access logs |
| `/aws/stepfunctions/retailmind-workflows` | Step Functions | 30 days | Workflow executions |
| `/aws/retailmind/audit` | Audit Trail | 365 days | Security and compliance |

### Log Insights Queries

#### Query 1: Error Analysis
```sql
fields @timestamp, @message, @logStream
| filter @message like /ERROR/
| stats count() by @logStream
| sort count desc
```

#### Query 2: Slow Lambda Executions
```sql
fields @timestamp, @duration, @requestId
| filter @type = "REPORT"
| filter @duration > 5000
| sort @duration desc
| limit 20
```

#### Query 3: API Error Rate
```sql
fields @timestamp, status, @message
| filter status >= 400
| stats count() by status
| sort count desc
```

#### Query 4: Agent Decision Confidence
```sql
fields @timestamp, agent_name, confidence_score
| filter @message like /decision_made/
| stats avg(confidence_score) by agent_name
```

#### Query 5: Workflow Failures
```sql
fields @timestamp, workflow_id, error_message
| filter status = "FAILED"
| sort @timestamp desc
| limit 50
```

### Log Retention Policies

```bash
# Set log retention via AWS CLI
aws logs put-retention-policy \
  --log-group-name /aws/lambda/retailmind-market-intelligence \
  --retention-in-days 30

# For audit logs (compliance requirement)
aws logs put-retention-policy \
  --log-group-name /aws/retailmind/audit \
  --retention-in-days 365
```

### Log Encryption

All log groups should be encrypted using AWS KMS:

```bash
# Enable encryption on log group
aws logs associate-kms-key \
  --log-group-name /aws/lambda/retailmind-market-intelligence \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012
```

---

## 4. CloudWatch Alarms

### Critical Alarms (P1 - Immediate Response)

#### Alarm 1: Lambda Error Rate High
```yaml
AlarmName: RetailMind-Lambda-ErrorRate-Critical
MetricName: Errors
Namespace: AWS/Lambda
Statistic: Sum
Period: 300  # 5 minutes
EvaluationPeriods: 2
Threshold: 10
ComparisonOperator: GreaterThanThreshold
TreatMissingData: notBreaching
AlarmActions:
  - arn:aws:sns:us-east-1:123456789012:retailmind-critical-alerts
```

#### Alarm 2: API Gateway 5XX Errors
```yaml
AlarmName: RetailMind-API-5XXErrors-Critical
MetricName: 5XXError
Namespace: AWS/ApiGateway
Dimensions:
  - Name: ApiName
    Value: RetailMindApi
Statistic: Sum
Period: 60  # 1 minute
EvaluationPeriods: 2
Threshold: 5
ComparisonOperator: GreaterThanThreshold
AlarmActions:
  - arn:aws:sns:us-east-1:123456789012:retailmind-critical-alerts
```

#### Alarm 3: DynamoDB Throttling
```yaml
AlarmName: RetailMind-DynamoDB-Throttling-Critical
MetricName: ThrottledRequests
Namespace: AWS/DynamoDB
Dimensions:
  - Name: TableName
    Value: retailmind-transactions
Statistic: Sum
Period: 60
EvaluationPeriods: 1
Threshold: 1
ComparisonOperator: GreaterThanOrEqualToThreshold
AlarmActions:
  - arn:aws:sns:us-east-1:123456789012:retailmind-critical-alerts
```

### High Priority Alarms (P2 - Response within 1 hour)

#### Alarm 4: Lambda Duration High
```yaml
AlarmName: RetailMind-Lambda-Duration-High
MetricName: Duration
Namespace: AWS/Lambda
Statistic: Average
Period: 300
EvaluationPeriods: 3
Threshold: 10000  # 10 seconds
ComparisonOperator: GreaterThanThreshold
AlarmActions:
  - arn:aws:sns:us-east-1:123456789012:retailmind-high-priority-alerts
```

#### Alarm 5: API Latency High
```yaml
AlarmName: RetailMind-API-Latency-High
MetricName: Latency
Namespace: AWS/ApiGateway
Statistic: Average
Period: 300
EvaluationPeriods: 2
Threshold: 1000  # 1 second
ComparisonOperator: GreaterThanThreshold
AlarmActions:
  - arn:aws:sns:us-east-1:123456789012:retailmind-high-priority-alerts
```

### Medium Priority Alarms (P3 - Response within 4 hours)

#### Alarm 6: Lambda Concurrent Executions High
```yaml
AlarmName: RetailMind-Lambda-Concurrency-High
MetricName: ConcurrentExecutions
Namespace: AWS/Lambda
Statistic: Maximum
Period: 300
EvaluationPeriods: 2
Threshold: 800  # 80% of 1000 limit
ComparisonOperator: GreaterThanThreshold
AlarmActions:
  - arn:aws:sns:us-east-1:123456789012:retailmind-medium-priority-alerts
```

#### Alarm 7: S3 4XX Errors
```yaml
AlarmName: RetailMind-S3-4XXErrors-Medium
MetricName: 4xxErrors
Namespace: AWS/S3
Dimensions:
  - Name: BucketName
    Value: retailmind-raw-data
Statistic: Sum
Period: 300
EvaluationPeriods: 2
Threshold: 50
ComparisonOperator: GreaterThanThreshold
AlarmActions:
  - arn:aws:sns:us-east-1:123456789012:retailmind-medium-priority-alerts
```

### Business Metric Alarms

#### Alarm 8: Low Agent Confidence
```yaml
AlarmName: RetailMind-Agent-LowConfidence
MetricName: DecisionConfidence
Namespace: RetailMind/Agents
Statistic: Average
Period: 3600  # 1 hour
EvaluationPeriods: 1
Threshold: 0.7  # 70% confidence
ComparisonOperator: LessThanThreshold
AlarmActions:
  - arn:aws:sns:us-east-1:123456789012:retailmind-business-alerts
```

#### Alarm 9: Workflow Failure Rate High
```yaml
AlarmName: RetailMind-Workflow-FailureRate-High
MetricName: ExecutionsFailed
Namespace: AWS/States
Statistic: Sum
Period: 3600
EvaluationPeriods: 1
Threshold: 5  # 5 failures per hour
ComparisonOperator: GreaterThanThreshold
AlarmActions:
  - arn:aws:sns:us-east-1:123456789012:retailmind-business-alerts
```

### Cost Alarms

#### Alarm 10: Daily Cost Exceeds Budget
```yaml
AlarmName: RetailMind-DailyCost-ExceedsBudget
MetricName: EstimatedCharges
Namespace: AWS/Billing
Dimensions:
  - Name: Currency
    Value: USD
Statistic: Maximum
Period: 86400  # 24 hours
EvaluationPeriods: 1
Threshold: 100  # $100 per day
ComparisonOperator: GreaterThanThreshold
AlarmActions:
  - arn:aws:sns:us-east-1:123456789012:retailmind-cost-alerts
```

### Creating Alarms via AWS CLI

```bash
# Create Lambda error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name RetailMind-Lambda-ErrorRate-Critical \
  --alarm-description "Alert when Lambda error rate is high" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:retailmind-critical-alerts
```

---

## 5. CloudWatch Dashboards

### Main Operations Dashboard

Create a comprehensive dashboard showing all key metrics:

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Invocations", {"stat": "Sum"}],
          [".", "Errors", {"stat": "Sum"}],
          [".", "Duration", {"stat": "Average"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Lambda Overview"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/ApiGateway", "Count", {"stat": "Sum"}],
          [".", "4XXError", {"stat": "Sum"}],
          [".", "5XXError", {"stat": "Sum"}],
          [".", "Latency", {"stat": "Average"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "API Gateway Overview"
      }
    }
  ]
}
```

### Dashboard Sections

1. **System Health**
   - Lambda invocations and errors
   - API Gateway requests and errors
   - DynamoDB read/write capacity
   - Step Functions execution status

2. **Performance Metrics**
   - Lambda duration (p50, p95, p99)
   - API latency (p50, p95, p99)
   - DynamoDB latency
   - Workflow execution time

3. **Business Metrics**
   - Agent decision confidence
   - Workflow success rate
   - Data processing throughput
   - User activity

4. **Cost Metrics**
   - Lambda invocation costs
   - DynamoDB costs
   - S3 storage costs
   - Data transfer costs

### Creating Dashboard via AWS CLI

```bash
# Create dashboard
aws cloudwatch put-dashboard \
  --dashboard-name RetailMind-Operations \
  --dashboard-body file://dashboard-config.json
```

---

## 6. X-Ray Tracing

### Enable X-Ray Tracing

#### For Lambda Functions
```python
# In Lambda function code
import aws_xray_sdk.core
from aws_xray_sdk.core import xray_recorder

# Patch libraries
aws_xray_sdk.core.patch_all()

@xray_recorder.capture('process_agent_decision')
def process_agent_decision(event):
    # Function logic
    pass
```

#### For API Gateway
Enable X-Ray tracing in API Gateway settings:
```bash
aws apigateway update-stage \
  --rest-api-id <api-id> \
  --stage-name dev \
  --patch-operations op=replace,path=/tracingEnabled,value=true
```

### X-Ray Service Map

View the service map to understand:
- Request flow through services
- Latency at each hop
- Error rates per service
- Dependencies between services

### X-Ray Traces

Analyze individual traces to:
- Identify bottlenecks
- Debug errors
- Optimize performance
- Understand request flow

---

## 7. Alert Channels

### SNS Topics

Create SNS topics for different alert priorities:

```bash
# Critical alerts (P1)
aws sns create-topic --name retailmind-critical-alerts

# High priority alerts (P2)
aws sns create-topic --name retailmind-high-priority-alerts

# Medium priority alerts (P3)
aws sns create-topic --name retailmind-medium-priority-alerts

# Business alerts
aws sns create-topic --name retailmind-business-alerts

# Cost alerts
aws sns create-topic --name retailmind-cost-alerts
```

### Email Subscriptions

```bash
# Subscribe email to critical alerts
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:retailmind-critical-alerts \
  --protocol email \
  --notification-endpoint ops-team@example.com
```

### Slack Integration

Use AWS Chatbot to send alerts to Slack:

1. Go to AWS Chatbot console
2. Configure Slack workspace
3. Create Slack channel (e.g., #retailmind-alerts)
4. Link SNS topics to Slack channel

### PagerDuty Integration

```bash
# Create SNS subscription to PagerDuty endpoint
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:retailmind-critical-alerts \
  --protocol https \
  --notification-endpoint https://events.pagerduty.com/integration/<integration-key>/enqueue
```

### Alert Routing

| Priority | Channel | Response Time | Escalation |
|----------|---------|---------------|------------|
| P1 (Critical) | PagerDuty + Slack + Email | Immediate | After 15 min |
| P2 (High) | Slack + Email | 1 hour | After 2 hours |
| P3 (Medium) | Email | 4 hours | After 8 hours |
| Business | Email | Next business day | N/A |
| Cost | Email | Weekly review | N/A |

---

## 8. Monitoring Best Practices

### 1. Set Meaningful Thresholds
- Base thresholds on historical data
- Use percentiles (p95, p99) for latency
- Account for normal variance
- Adjust thresholds seasonally

### 2. Avoid Alert Fatigue
- Don't alert on every anomaly
- Use composite alarms for related metrics
- Implement alert suppression during maintenance
- Review and tune alarms regularly

### 3. Use Anomaly Detection
```bash
# Create anomaly detection alarm
aws cloudwatch put-metric-alarm \
  --alarm-name RetailMind-Lambda-Duration-Anomaly \
  --comparison-operator LessThanLowerOrGreaterThanUpperThreshold \
  --evaluation-periods 2 \
  --metrics file://anomaly-detection-config.json \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:retailmind-high-priority-alerts
```

### 4. Implement Composite Alarms
```bash
# Create composite alarm (alert only if multiple conditions met)
aws cloudwatch put-composite-alarm \
  --alarm-name RetailMind-System-Degraded \
  --alarm-rule "ALARM(RetailMind-Lambda-ErrorRate-Critical) AND ALARM(RetailMind-API-Latency-High)" \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:retailmind-critical-alerts
```

### 5. Tag Resources
```bash
# Tag resources for better organization
aws lambda tag-resource \
  --resource arn:aws:lambda:us-east-1:123456789012:function:retailmind-market-intelligence \
  --tags Environment=production,Application=RetailMind,Component=Agent
```

### 6. Regular Reviews
- Weekly: Review alert frequency and false positives
- Monthly: Analyze trends and adjust thresholds
- Quarterly: Review monitoring coverage
- Annually: Audit monitoring strategy

---

## 9. Troubleshooting Monitoring Issues

### Issue 1: Missing Metrics

**Symptoms**: Metrics not appearing in CloudWatch

**Diagnosis**:
```bash
# Check if metrics are being published
aws cloudwatch list-metrics --namespace RetailMind/Agents

# Check IAM permissions
aws iam get-role-policy --role-name LambdaExecutionRole --policy-name CloudWatchPolicy
```

**Resolution**:
- Verify IAM permissions for CloudWatch PutMetricData
- Check metric namespace and dimensions
- Verify application is publishing metrics

### Issue 2: Alarms Not Triggering

**Symptoms**: Expected alarms not firing

**Diagnosis**:
```bash
# Check alarm state
aws cloudwatch describe-alarms --alarm-names RetailMind-Lambda-ErrorRate-Critical

# Check alarm history
aws cloudwatch describe-alarm-history --alarm-name RetailMind-Lambda-ErrorRate-Critical
```

**Resolution**:
- Verify threshold values
- Check evaluation periods
- Verify metric data is available
- Check alarm actions are configured

### Issue 3: Too Many False Positives

**Symptoms**: Alarms triggering unnecessarily

**Resolution**:
- Increase threshold values
- Increase evaluation periods
- Use anomaly detection instead of static thresholds
- Implement composite alarms

### Issue 4: Logs Not Appearing

**Symptoms**: CloudWatch Logs not showing application logs

**Diagnosis**:
```bash
# Check log group exists
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/retailmind

# Check log streams
aws logs describe-log-streams --log-group-name /aws/lambda/retailmind-market-intelligence
```

**Resolution**:
- Verify IAM permissions for CloudWatch Logs
- Check log group retention policy
- Verify application logging configuration
- Check Lambda execution role

### Issue 5: High CloudWatch Costs

**Symptoms**: Unexpected CloudWatch charges

**Diagnosis**:
```bash
# Check log ingestion
aws cloudwatch get-metric-statistics \
  --namespace AWS/Logs \
  --metric-name IncomingBytes \
  --start-time 2026-03-01T00:00:00Z \
  --end-time 2026-03-06T00:00:00Z \
  --period 86400 \
  --statistics Sum
```

**Resolution**:
- Reduce log verbosity
- Implement log sampling
- Adjust log retention policies
- Use metric filters instead of storing all logs

---

## Quick Reference Commands

### View Recent Alarms
```bash
aws cloudwatch describe-alarms --state-value ALARM
```

### Get Metric Statistics
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --start-time 2026-03-06T00:00:00Z \
  --end-time 2026-03-06T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

### Tail Lambda Logs
```bash
aws logs tail /aws/lambda/retailmind-market-intelligence --follow
```

### Search Logs
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/retailmind-market-intelligence \
  --filter-pattern "ERROR"
```

### Disable Alarm
```bash
aws cloudwatch disable-alarm-actions --alarm-names RetailMind-Lambda-ErrorRate-Critical
```

### Enable Alarm
```bash
aws cloudwatch enable-alarm-actions --alarm-names RetailMind-Lambda-ErrorRate-Critical
```

---

## Monitoring Checklist

- [ ] All Lambda functions have CloudWatch Logs enabled
- [ ] Log retention policies configured
- [ ] Critical alarms created and tested
- [ ] SNS topics created for alerts
- [ ] Email subscriptions configured
- [ ] Slack integration set up (optional)
- [ ] PagerDuty integration set up (optional)
- [ ] CloudWatch dashboard created
- [ ] X-Ray tracing enabled
- [ ] Custom metrics being published
- [ ] Alarm thresholds tuned based on baseline
- [ ] Alert routing documented
- [ ] On-call rotation established
- [ ] Monitoring runbook reviewed by team

---

**Document Version**: 1.0  
**Last Updated**: 2026-03-06  
**Maintained By**: RetailMind AI Operations Team  
**Review Frequency**: Monthly
