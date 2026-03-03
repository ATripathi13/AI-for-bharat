# Incident Response Runbook

## Overview

This runbook provides step-by-step procedures for responding to incidents in the RetailMind AI platform.

## Severity Levels

| Severity | Description | Response Time | Examples |
|----------|-------------|---------------|----------|
| P0 - Critical | Complete system outage | 15 minutes | API down, data loss |
| P1 - High | Major functionality impaired | 1 hour | Agent failures, high error rates |
| P2 - Medium | Degraded performance | 4 hours | Slow responses, partial failures |
| P3 - Low | Minor issues | 24 hours | UI glitches, non-critical bugs |

## Incident Response Process

### 1. Detection and Alert

**Automated Alerts**:
- CloudWatch Alarms
- API Gateway error rates
- Lambda function failures
- DynamoDB throttling

**Manual Detection**:
- User reports
- Monitoring dashboard anomalies
- Scheduled health checks

### 2. Initial Response (First 15 minutes)

**Step 1: Acknowledge the Incident**
```bash
# Update incident status
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:incident-notifications \
  --message "Incident acknowledged: [INCIDENT_ID]"
```

**Step 2: Assess Severity**
- Check CloudWatch dashboards
- Review error logs
- Determine user impact
- Assign severity level

**Step 3: Assemble Response Team**
- P0/P1: Page on-call engineer immediately
- P2: Notify team via Slack
- P3: Create ticket for next business day

**Step 4: Create Incident Channel**
```
# Slack command
/incident create [INCIDENT_ID] [SEVERITY] [DESCRIPTION]
```

### 3. Investigation (15-60 minutes)

**Check System Health**:
```bash
# Check API health
curl https://api.retailmind.ai/health

# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace RetailMind/API \
  --metric-name ErrorRate \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

**Review Recent Changes**:
```bash
# Check recent deployments
aws cloudformation describe-stack-events \
  --stack-name RetailMindComputeStack \
  --max-items 20

# Check recent Lambda updates
aws lambda list-versions-by-function \
  --function-name market-intelligence-agent \
  --max-items 5
```

**Analyze Logs**:
```bash
# Query CloudWatch Logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/retailmind \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR"
```

### 4. Mitigation

#### API Gateway Issues

**Symptom**: High error rates, timeouts

**Diagnosis**:
```bash
# Check API Gateway metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name 5XXError \
  --dimensions Name=ApiName,Value=RetailMindAPI \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

**Mitigation**:
1. Check throttling limits
2. Review Lambda function errors
3. Increase Lambda concurrency if needed
4. Enable API caching

```bash
# Increase Lambda reserved concurrency
aws lambda put-function-concurrency \
  --function-name market-intelligence-agent \
  --reserved-concurrent-executions 50
```

#### Lambda Function Failures

**Symptom**: Function timeouts, errors

**Diagnosis**:
```bash
# Get function configuration
aws lambda get-function-configuration \
  --function-name market-intelligence-agent

# Check recent invocations
aws lambda get-function \
  --function-name market-intelligence-agent
```

**Mitigation**:
1. Check function logs for errors
2. Verify IAM permissions
3. Check memory/timeout settings
4. Rollback to previous version if needed

```bash
# Rollback Lambda function
python scripts/rollback.py \
  --environment production \
  --stack RetailMindComputeStack
```

#### DynamoDB Throttling

**Symptom**: ProvisionedThroughputExceededException

**Diagnosis**:
```bash
# Check DynamoDB metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name UserErrors \
  --dimensions Name=TableName,Value=AgentDecisions \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

**Mitigation**:
1. Switch to on-demand capacity mode
2. Increase provisioned capacity
3. Implement exponential backoff in code

```bash
# Update table to on-demand
aws dynamodb update-table \
  --table-name AgentDecisions \
  --billing-mode PAY_PER_REQUEST
```

#### Agent Decision Failures

**Symptom**: Agents not responding, low confidence scores

**Diagnosis**:
```bash
# Check agent metrics
aws cloudwatch get-metric-statistics \
  --namespace RetailMind/Agents \
  --metric-name DecisionConfidence \
  --dimensions Name=AgentId,Value=pricing-optimization-agent \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

**Mitigation**:
1. Check agent configuration
2. Verify data source availability
3. Review model performance
4. Enable manual escalation

```python
# Update agent configuration
from src.repositories.agent_config_repository import AgentConfigRepository

config_repo = AgentConfigRepository()
config_repo.update_parameter(
    agent_id="pricing-optimization-agent",
    parameter_path="escalationThreshold",
    value=0.5  # Lower threshold to escalate more
)
```

### 5. Communication

**Internal Communication**:
- Update incident channel every 30 minutes
- Post status updates in #incidents Slack channel
- Notify stakeholders of progress

**External Communication** (for P0/P1):
- Update status page: https://status.retailmind.ai
- Send email to affected customers
- Post on social media if widespread

**Status Update Template**:
```
Incident Update - [TIMESTAMP]
Severity: [P0/P1/P2/P3]
Status: [Investigating/Identified/Monitoring/Resolved]
Impact: [Description of user impact]
Next Update: [Timestamp]
```

### 6. Resolution

**Verify Fix**:
```bash
# Run smoke tests
pytest tests/smoke/ -v

# Check metrics
aws cloudwatch get-metric-statistics \
  --namespace RetailMind/API \
  --metric-name ErrorRate \
  --start-time $(date -u -d '15 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

**Monitor for Recurrence**:
- Watch metrics for 1 hour after resolution
- Set up additional alerts if needed
- Document workarounds

### 7. Post-Incident Review

**Within 48 hours of resolution**:

1. **Create Post-Mortem Document**
   - Timeline of events
   - Root cause analysis
   - Impact assessment
   - Action items

2. **Schedule Post-Mortem Meeting**
   - Review incident timeline
   - Discuss what went well
   - Identify improvements
   - Assign action items

3. **Update Runbooks**
   - Document new procedures
   - Update troubleshooting steps
   - Add preventive measures

**Post-Mortem Template**:
```markdown
# Post-Mortem: [INCIDENT_ID]

## Summary
- Date: [DATE]
- Duration: [DURATION]
- Severity: [P0/P1/P2/P3]
- Impact: [USER_IMPACT]

## Timeline
- [TIME]: Incident detected
- [TIME]: Response team assembled
- [TIME]: Root cause identified
- [TIME]: Fix deployed
- [TIME]: Incident resolved

## Root Cause
[Detailed explanation]

## Resolution
[How it was fixed]

## Action Items
- [ ] [ACTION_ITEM_1] - Owner: [NAME] - Due: [DATE]
- [ ] [ACTION_ITEM_2] - Owner: [NAME] - Due: [DATE]

## Lessons Learned
- What went well
- What could be improved
- Preventive measures
```

## Common Incident Scenarios

### Scenario 1: Complete API Outage

**Symptoms**:
- All API requests returning 5XX errors
- CloudWatch alarm: API error rate > 50%

**Response**:
1. Check API Gateway status
2. Verify Lambda functions are running
3. Check DynamoDB table status
4. Review recent deployments
5. Rollback if recent deployment caused issue

**Resolution Time**: 15-30 minutes

### Scenario 2: Agent Not Responding

**Symptoms**:
- Specific agent timing out
- No decisions being made
- High escalation rate

**Response**:
1. Check agent Lambda function logs
2. Verify agent configuration
3. Check data source availability
4. Restart agent if needed
5. Enable manual fallback

**Resolution Time**: 30-60 minutes

### Scenario 3: Data Pipeline Failure

**Symptoms**:
- No new data being ingested
- Stale market intelligence
- Forecast accuracy declining

**Response**:
1. Check S3 bucket for new files
2. Verify Lambda triggers
3. Check EventBridge rules
4. Review data source APIs
5. Manually trigger pipeline if needed

**Resolution Time**: 1-2 hours

### Scenario 4: High Latency

**Symptoms**:
- API response times > 5 seconds
- User complaints about slow dashboard
- CloudWatch alarm: P99 latency > 3s

**Response**:
1. Check Lambda cold starts
2. Review DynamoDB query patterns
3. Check for throttling
4. Enable caching
5. Increase Lambda memory

**Resolution Time**: 1-2 hours

## Escalation Paths

### Level 1: On-Call Engineer
- Initial response
- Basic troubleshooting
- Escalate if needed

### Level 2: Senior Engineer
- Complex issues
- Architecture decisions
- Escalate to Level 3 if needed

### Level 3: Engineering Manager
- Critical incidents
- Business impact decisions
- External communication

### Level 4: CTO/VP Engineering
- Major outages
- Data breaches
- Legal/compliance issues

## Contact Information

**On-Call Rotation**:
- PagerDuty: https://retailmind.pagerduty.com
- Slack: #on-call

**Key Contacts**:
- Engineering Manager: [EMAIL]
- DevOps Lead: [EMAIL]
- Security Team: [EMAIL]
- Customer Success: [EMAIL]

## Tools and Resources

**Monitoring**:
- CloudWatch Dashboard: https://console.aws.amazon.com/cloudwatch
- Status Page: https://status.retailmind.ai
- Grafana: https://grafana.retailmind.ai

**Communication**:
- Slack: #incidents
- PagerDuty: https://retailmind.pagerduty.com
- Email: incidents@retailmind.ai

**Documentation**:
- Architecture Docs: docs/ARCHITECTURE.md
- API Docs: docs/API_DOCUMENTATION.md
- Runbooks: docs/runbooks/

---

**Document Version**: 1.0  
**Last Updated**: 2026-03-03  
**Maintained By**: RetailMind AI Operations Team
