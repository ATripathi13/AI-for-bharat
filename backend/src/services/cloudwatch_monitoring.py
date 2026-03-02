"""
CloudWatch Monitoring Service

Provides comprehensive logging and metrics for the RetailMind AI platform.
Implements Lambda function logging, custom metrics for agent performance,
workflow execution metrics, and system health monitoring.

Requirements: 9.5
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, asdict


class MetricUnit(Enum):
    """CloudWatch metric units"""
    SECONDS = "Seconds"
    MILLISECONDS = "Milliseconds"
    COUNT = "Count"
    PERCENT = "Percent"
    BYTES = "Bytes"


class MetricNamespace(Enum):
    """CloudWatch metric namespaces"""
    AGENTS = "RetailMindAI/Agents"
    WORKFLOWS = "RetailMindAI/Workflows"
    INTELLIGENCE_LOOP = "RetailMindAI/IntelligenceLoop"
    API = "RetailMindAI/API"
    SYSTEM = "RetailMindAI/System"


@dataclass
class MetricData:
    """Represents a CloudWatch metric data point"""
    metric_name: str
    value: float
    unit: MetricUnit
    timestamp: datetime
    dimensions: Dict[str, str]
    namespace: MetricNamespace

    def to_cloudwatch_format(self) -> Dict[str, Any]:
        """Convert to CloudWatch PutMetricData format"""
        return {
            'MetricName': self.metric_name,
            'Value': self.value,
            'Unit': self.unit.value,
            'Timestamp': self.timestamp.isoformat(),
            'Dimensions': [
                {'Name': k, 'Value': v} for k, v in self.dimensions.items()
            ]
        }


@dataclass
class LogEntry:
    """Structured log entry"""
    level: str
    message: str
    timestamp: datetime
    context: Dict[str, Any]
    correlation_id: Optional[str] = None

    def to_json(self) -> str:
        """Convert to JSON format for CloudWatch Logs"""
        return json.dumps({
            'level': self.level,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context,
            'correlation_id': self.correlation_id
        })


class CloudWatchLogger:
    """
    Structured logging service for CloudWatch Logs.
    Provides Lambda function logging with structured JSON format.
    """

    def __init__(self, log_group: str, log_stream: str):
        self.log_group = log_group
        self.log_stream = log_stream
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def log(self, level: str, message: str, context: Dict[str, Any],
            correlation_id: Optional[str] = None):
        """Log a structured message"""
        entry = LogEntry(
            level=level,
            message=message,
            timestamp=datetime.utcnow(),
            context=context,
            correlation_id=correlation_id
        )

        log_json = entry.to_json()

        if level == 'ERROR':
            self.logger.error(log_json)
        elif level == 'WARNING':
            self.logger.warning(log_json)
        elif level == 'INFO':
            self.logger.info(log_json)
        elif level == 'DEBUG':
            self.logger.debug(log_json)

    def info(self, message: str, context: Dict[str, Any] = None,
             correlation_id: Optional[str] = None):
        """Log info level message"""
        self.log('INFO', message, context or {}, correlation_id)

    def error(self, message: str, context: Dict[str, Any] = None,
              correlation_id: Optional[str] = None):
        """Log error level message"""
        self.log('ERROR', message, context or {}, correlation_id)

    def warning(self, message: str, context: Dict[str, Any] = None,
                correlation_id: Optional[str] = None):
        """Log warning level message"""
        self.log('WARNING', message, context or {}, correlation_id)

    def debug(self, message: str, context: Dict[str, Any] = None,
              correlation_id: Optional[str] = None):
        """Log debug level message"""
        self.log('DEBUG', message, context or {}, correlation_id)


class AgentPerformanceMetrics:
    """
    Tracks and publishes agent performance metrics to CloudWatch.
    Monitors decision latency, confidence scores, and success rates.
    """

    def __init__(self):
        self.metrics: List[MetricData] = []

    def record_decision_latency(self, agent_id: str, latency_ms: float):
        """Record agent decision latency"""
        metric = MetricData(
            metric_name='DecisionLatency',
            value=latency_ms,
            unit=MetricUnit.MILLISECONDS,
            timestamp=datetime.utcnow(),
            dimensions={'AgentId': agent_id},
            namespace=MetricNamespace.AGENTS
        )
        self.metrics.append(metric)

    def record_confidence_score(self, agent_id: str, confidence: float):
        """Record agent confidence score"""
        metric = MetricData(
            metric_name='ConfidenceScore',
            value=confidence * 100,  # Convert to percentage
            unit=MetricUnit.PERCENT,
            timestamp=datetime.utcnow(),
            dimensions={'AgentId': agent_id},
            namespace=MetricNamespace.AGENTS
        )
        self.metrics.append(metric)

    def record_decision_count(self, agent_id: str, count: int = 1):
        """Record number of decisions made"""
        metric = MetricData(
            metric_name='DecisionCount',
            value=float(count),
            unit=MetricUnit.COUNT,
            timestamp=datetime.utcnow(),
            dimensions={'AgentId': agent_id},
            namespace=MetricNamespace.AGENTS
        )
        self.metrics.append(metric)

    def record_escalation(self, agent_id: str):
        """Record escalation event"""
        metric = MetricData(
            metric_name='EscalationCount',
            value=1.0,
            unit=MetricUnit.COUNT,
            timestamp=datetime.utcnow(),
            dimensions={'AgentId': agent_id},
            namespace=MetricNamespace.AGENTS
        )
        self.metrics.append(metric)

    def get_metrics(self) -> List[MetricData]:
        """Get all recorded metrics"""
        return self.metrics

    def clear_metrics(self):
        """Clear recorded metrics"""
        self.metrics = []


class WorkflowExecutionMetrics:
    """
    Tracks and publishes workflow execution metrics to CloudWatch.
    Monitors execution time, success rates, and step performance.
    """

    def __init__(self):
        self.metrics: List[MetricData] = []

    def record_execution_time(self, workflow_id: str, execution_time_ms: float):
        """Record workflow execution time"""
        metric = MetricData(
            metric_name='ExecutionTime',
            value=execution_time_ms,
            unit=MetricUnit.MILLISECONDS,
            timestamp=datetime.utcnow(),
            dimensions={'WorkflowId': workflow_id},
            namespace=MetricNamespace.WORKFLOWS
        )
        self.metrics.append(metric)

    def record_workflow_success(self, workflow_id: str):
        """Record successful workflow execution"""
        metric = MetricData(
            metric_name='SuccessCount',
            value=1.0,
            unit=MetricUnit.COUNT,
            timestamp=datetime.utcnow(),
            dimensions={'WorkflowId': workflow_id},
            namespace=MetricNamespace.WORKFLOWS
        )
        self.metrics.append(metric)

    def record_workflow_failure(self, workflow_id: str):
        """Record failed workflow execution"""
        metric = MetricData(
            metric_name='FailureCount',
            value=1.0,
            unit=MetricUnit.COUNT,
            timestamp=datetime.utcnow(),
            dimensions={'WorkflowId': workflow_id},
            namespace=MetricNamespace.WORKFLOWS
        )
        self.metrics.append(metric)

    def record_step_execution(self, workflow_id: str, step_id: str,
                             execution_time_ms: float):
        """Record individual step execution time"""
        metric = MetricData(
            metric_name='StepExecutionTime',
            value=execution_time_ms,
            unit=MetricUnit.MILLISECONDS,
            timestamp=datetime.utcnow(),
            dimensions={
                'WorkflowId': workflow_id,
                'StepId': step_id
            },
            namespace=MetricNamespace.WORKFLOWS
        )
        self.metrics.append(metric)

    def record_rollback(self, workflow_id: str):
        """Record workflow rollback event"""
        metric = MetricData(
            metric_name='RollbackCount',
            value=1.0,
            unit=MetricUnit.COUNT,
            timestamp=datetime.utcnow(),
            dimensions={'WorkflowId': workflow_id},
            namespace=MetricNamespace.WORKFLOWS
        )
        self.metrics.append(metric)

    def get_metrics(self) -> List[MetricData]:
        """Get all recorded metrics"""
        return self.metrics

    def clear_metrics(self):
        """Clear recorded metrics"""
        self.metrics = []


class SystemHealthMetrics:
    """
    Tracks system-wide health metrics for monitoring dashboard.
    Monitors API latency, error rates, and resource utilization.
    """

    def __init__(self):
        self.metrics: List[MetricData] = []

    def record_api_latency(self, endpoint: str, latency_ms: float):
        """Record API endpoint latency"""
        metric = MetricData(
            metric_name='APILatency',
            value=latency_ms,
            unit=MetricUnit.MILLISECONDS,
            timestamp=datetime.utcnow(),
            dimensions={'Endpoint': endpoint},
            namespace=MetricNamespace.API
        )
        self.metrics.append(metric)

    def record_error_rate(self, component: str, error_count: int):
        """Record error count for a component"""
        metric = MetricData(
            metric_name='ErrorCount',
            value=float(error_count),
            unit=MetricUnit.COUNT,
            timestamp=datetime.utcnow(),
            dimensions={'Component': component},
            namespace=MetricNamespace.SYSTEM
        )
        self.metrics.append(metric)

    def record_intelligence_loop_cycle(self, phase: str, duration_ms: float):
        """Record intelligence loop phase duration"""
        metric = MetricData(
            metric_name='LoopPhaseDuration',
            value=duration_ms,
            unit=MetricUnit.MILLISECONDS,
            timestamp=datetime.utcnow(),
            dimensions={'Phase': phase},
            namespace=MetricNamespace.INTELLIGENCE_LOOP
        )
        self.metrics.append(metric)

    def record_active_agents(self, count: int):
        """Record number of active agents"""
        metric = MetricData(
            metric_name='ActiveAgents',
            value=float(count),
            unit=MetricUnit.COUNT,
            timestamp=datetime.utcnow(),
            dimensions={},
            namespace=MetricNamespace.SYSTEM
        )
        self.metrics.append(metric)

    def get_metrics(self) -> List[MetricData]:
        """Get all recorded metrics"""
        return self.metrics

    def clear_metrics(self):
        """Clear recorded metrics"""
        self.metrics = []


class CloudWatchMonitoringService:
    """
    Main monitoring service that coordinates logging and metrics.
    Provides unified interface for all CloudWatch operations.
    """

    def __init__(self, log_group: str = "/aws/retailmind-ai",
                 log_stream: str = "application"):
        self.logger = CloudWatchLogger(log_group, log_stream)
        self.agent_metrics = AgentPerformanceMetrics()
        self.workflow_metrics = WorkflowExecutionMetrics()
        self.system_metrics = SystemHealthMetrics()

    def get_logger(self) -> CloudWatchLogger:
        """Get the CloudWatch logger instance"""
        return self.logger

    def get_agent_metrics(self) -> AgentPerformanceMetrics:
        """Get agent performance metrics tracker"""
        return self.agent_metrics

    def get_workflow_metrics(self) -> WorkflowExecutionMetrics:
        """Get workflow execution metrics tracker"""
        return self.workflow_metrics

    def get_system_metrics(self) -> SystemHealthMetrics:
        """Get system health metrics tracker"""
        return self.system_metrics

    def publish_all_metrics(self) -> Dict[str, int]:
        """
        Publish all collected metrics to CloudWatch.
        In production, this would use boto3 CloudWatch client.
        Returns count of metrics published by namespace.
        """
        all_metrics = (
            self.agent_metrics.get_metrics() +
            self.workflow_metrics.get_metrics() +
            self.system_metrics.get_metrics()
        )

        # Group by namespace
        metrics_by_namespace: Dict[str, List[MetricData]] = {}
        for metric in all_metrics:
            namespace = metric.namespace.value
            if namespace not in metrics_by_namespace:
                metrics_by_namespace[namespace] = []
            metrics_by_namespace[namespace].append(metric)

        # In production, publish to CloudWatch using boto3
        # cloudwatch = boto3.client('cloudwatch')
        # for namespace, metrics in metrics_by_namespace.items():
        #     cloudwatch.put_metric_data(
        #         Namespace=namespace,
        #         MetricData=[m.to_cloudwatch_format() for m in metrics]
        #     )

        # Clear metrics after publishing
        self.agent_metrics.clear_metrics()
        self.workflow_metrics.clear_metrics()
        self.system_metrics.clear_metrics()

        return {ns: len(ms) for ns, ms in metrics_by_namespace.items()}


# Global monitoring service instance
_monitoring_service: Optional[CloudWatchMonitoringService] = None


def get_monitoring_service() -> CloudWatchMonitoringService:
    """Get or create the global monitoring service instance"""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = CloudWatchMonitoringService()
    return _monitoring_service
