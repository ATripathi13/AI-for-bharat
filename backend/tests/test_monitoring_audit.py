"""
Unit tests for CloudWatch monitoring and audit trail system

Tests log generation, metric collection, and audit trail completeness.

Requirements: 9.5, 10.2
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.services.cloudwatch_monitoring import (
    CloudWatchLogger,
    AgentPerformanceMetrics,
    WorkflowExecutionMetrics,
    SystemHealthMetrics,
    CloudWatchMonitoringService,
    MetricUnit,
    MetricNamespace,
    MetricData,
    LogEntry
)

from src.services.audit_trail_system import (
    AuditTrailSystem,
    DecisionHistoryTracker,
    WorkflowModificationLogger,
    ComplianceReportingService,
    DecisionHistoryEntry,
    WorkflowModificationEntry,
    ComplianceReportType
)

from src.services.audit import (
    AuditService,
    AuditEntry,
    AuditEventType
)

from src.models.agent_decision import AgentDecision, Recommendation


class TestCloudWatchLogger:
    """Test CloudWatch logging functionality"""

    def test_log_info_message(self):
        """Test logging info level message"""
        logger = CloudWatchLogger("/aws/test", "test-stream")
        
        with patch.object(logger.logger, 'info') as mock_info:
            logger.info("Test message", {"key": "value"}, "corr-123")
            
            # Verify info was called
            assert mock_info.called
            call_args = mock_info.call_args[0][0]
            assert "Test message" in call_args
            assert "INFO" in call_args

    def test_log_error_message(self):
        """Test logging error level message"""
        logger = CloudWatchLogger("/aws/test", "test-stream")
        
        with patch.object(logger.logger, 'error') as mock_error:
            logger.error("Error occurred", {"error": "details"})
            
            assert mock_error.called
            call_args = mock_error.call_args[0][0]
            assert "Error occurred" in call_args
            assert "ERROR" in call_args

    def test_structured_log_format(self):
        """Test that logs are properly structured as JSON"""
        logger = CloudWatchLogger("/aws/test", "test-stream")
        
        with patch.object(logger.logger, 'info') as mock_info:
            context = {"userId": "user123", "action": "login"}
            logger.info("User action", context, "corr-456")
            
            call_args = mock_info.call_args[0][0]
            # Verify JSON structure
            assert '"level": "INFO"' in call_args
            assert '"message": "User action"' in call_args
            assert '"correlation_id": "corr-456"' in call_args


class TestAgentPerformanceMetrics:
    """Test agent performance metrics tracking"""

    def test_record_decision_latency(self):
        """Test recording agent decision latency"""
        metrics = AgentPerformanceMetrics()
        
        metrics.record_decision_latency("agent_market_intel", 150.5)
        
        recorded = metrics.get_metrics()
        assert len(recorded) == 1
        assert recorded[0].metric_name == 'DecisionLatency'
        assert recorded[0].value == 150.5
        assert recorded[0].unit == MetricUnit.MILLISECONDS
        assert recorded[0].dimensions['AgentId'] == 'agent_market_intel'

    def test_record_confidence_score(self):
        """Test recording agent confidence score"""
        metrics = AgentPerformanceMetrics()
        
        metrics.record_confidence_score("agent_pricing", 0.85)
        
        recorded = metrics.get_metrics()
        assert len(recorded) == 1
        assert recorded[0].metric_name == 'ConfidenceScore'
        assert recorded[0].value == 85.0  # Converted to percentage
        assert recorded[0].unit == MetricUnit.PERCENT

    def test_record_multiple_metrics(self):
        """Test recording multiple metrics"""
        metrics = AgentPerformanceMetrics()
        
        metrics.record_decision_latency("agent1", 100.0)
        metrics.record_confidence_score("agent1", 0.9)
        metrics.record_decision_count("agent1", 5)
        metrics.record_escalation("agent1")
        
        recorded = metrics.get_metrics()
        assert len(recorded) == 4

    def test_clear_metrics(self):
        """Test clearing recorded metrics"""
        metrics = AgentPerformanceMetrics()
        
        metrics.record_decision_latency("agent1", 100.0)
        assert len(metrics.get_metrics()) == 1
        
        metrics.clear_metrics()
        assert len(metrics.get_metrics()) == 0


class TestWorkflowExecutionMetrics:
    """Test workflow execution metrics tracking"""

    def test_record_execution_time(self):
        """Test recording workflow execution time"""
        metrics = WorkflowExecutionMetrics()
        
        metrics.record_execution_time("workflow_123", 2500.0)
        
        recorded = metrics.get_metrics()
        assert len(recorded) == 1
        assert recorded[0].metric_name == 'ExecutionTime'
        assert recorded[0].value == 2500.0
        assert recorded[0].dimensions['WorkflowId'] == 'workflow_123'

    def test_record_workflow_success(self):
        """Test recording successful workflow execution"""
        metrics = WorkflowExecutionMetrics()
        
        metrics.record_workflow_success("workflow_123")
        
        recorded = metrics.get_metrics()
        assert len(recorded) == 1
        assert recorded[0].metric_name == 'SuccessCount'
        assert recorded[0].value == 1.0

    def test_record_workflow_failure(self):
        """Test recording failed workflow execution"""
        metrics = WorkflowExecutionMetrics()
        
        metrics.record_workflow_failure("workflow_123")
        
        recorded = metrics.get_metrics()
        assert len(recorded) == 1
        assert recorded[0].metric_name == 'FailureCount'

    def test_record_step_execution(self):
        """Test recording individual step execution"""
        metrics = WorkflowExecutionMetrics()
        
        metrics.record_step_execution("workflow_123", "step_1", 500.0)
        
        recorded = metrics.get_metrics()
        assert len(recorded) == 1
        assert recorded[0].metric_name == 'StepExecutionTime'
        assert recorded[0].dimensions['WorkflowId'] == 'workflow_123'
        assert recorded[0].dimensions['StepId'] == 'step_1'

    def test_record_rollback(self):
        """Test recording workflow rollback"""
        metrics = WorkflowExecutionMetrics()
        
        metrics.record_rollback("workflow_123")
        
        recorded = metrics.get_metrics()
        assert len(recorded) == 1
        assert recorded[0].metric_name == 'RollbackCount'


class TestSystemHealthMetrics:
    """Test system health metrics tracking"""

    def test_record_api_latency(self):
        """Test recording API endpoint latency"""
        metrics = SystemHealthMetrics()
        
        metrics.record_api_latency("/api/agents/decisions", 75.5)
        
        recorded = metrics.get_metrics()
        assert len(recorded) == 1
        assert recorded[0].metric_name == 'APILatency'
        assert recorded[0].dimensions['Endpoint'] == '/api/agents/decisions'

    def test_record_error_rate(self):
        """Test recording error count"""
        metrics = SystemHealthMetrics()
        
        metrics.record_error_rate("agent_communication", 3)
        
        recorded = metrics.get_metrics()
        assert len(recorded) == 1
        assert recorded[0].metric_name == 'ErrorCount'
        assert recorded[0].value == 3.0

    def test_record_intelligence_loop_cycle(self):
        """Test recording intelligence loop phase duration"""
        metrics = SystemHealthMetrics()
        
        metrics.record_intelligence_loop_cycle("analyze", 1500.0)
        
        recorded = metrics.get_metrics()
        assert len(recorded) == 1
        assert recorded[0].metric_name == 'LoopPhaseDuration'
        assert recorded[0].dimensions['Phase'] == 'analyze'

    def test_record_active_agents(self):
        """Test recording active agent count"""
        metrics = SystemHealthMetrics()
        
        metrics.record_active_agents(7)
        
        recorded = metrics.get_metrics()
        assert len(recorded) == 1
        assert recorded[0].metric_name == 'ActiveAgents'
        assert recorded[0].value == 7.0


class TestCloudWatchMonitoringService:
    """Test main monitoring service"""

    def test_service_initialization(self):
        """Test monitoring service initialization"""
        service = CloudWatchMonitoringService()
        
        assert service.get_logger() is not None
        assert service.get_agent_metrics() is not None
        assert service.get_workflow_metrics() is not None
        assert service.get_system_metrics() is not None

    def test_publish_all_metrics(self):
        """Test publishing all collected metrics"""
        service = CloudWatchMonitoringService()
        
        # Record some metrics
        service.get_agent_metrics().record_decision_latency("agent1", 100.0)
        service.get_workflow_metrics().record_execution_time("wf1", 2000.0)
        service.get_system_metrics().record_api_latency("/api/test", 50.0)
        
        # Publish metrics
        result = service.publish_all_metrics()
        
        # Verify metrics were grouped by namespace
        assert isinstance(result, dict)
        assert len(result) > 0
        
        # Verify metrics were cleared after publishing
        assert len(service.get_agent_metrics().get_metrics()) == 0
        assert len(service.get_workflow_metrics().get_metrics()) == 0
        assert len(service.get_system_metrics().get_metrics()) == 0


class TestDecisionHistoryTracker:
    """Test decision history tracking"""

    @patch('src.services.audit.AuditService')
    def test_get_decision_history(self, mock_audit_service):
        """Test retrieving decision history"""
        # Setup mock
        mock_audit = Mock()
        mock_audit.query_audit_trail.return_value = [
            AuditEntry(
                audit_id="audit1",
                timestamp=datetime.utcnow(),
                event_type=AuditEventType.AGENT_DECISION,
                actor_id="agent_pricing",
                actor_type="agent",
                action="optimize_price",
                resource_id="decision1",
                resource_type="agent_decision",
                details={
                    "confidence": 0.85,
                    "decisionType": "pricing"
                },
                data_sources=["market_data"],
                reasoning="Based on competitor analysis",
                outcome="success"
            )
        ]
        
        tracker = DecisionHistoryTracker(mock_audit)
        history = tracker.get_decision_history(agent_id="agent_pricing")
        
        assert len(history) == 1
        assert history[0].agent_id == "agent_pricing"
        assert history[0].confidence == 0.85
        assert history[0].outcome == "success"

    @patch('src.services.audit.AuditService')
    def test_get_decision_statistics(self, mock_audit_service):
        """Test calculating decision statistics"""
        mock_audit = Mock()
        mock_audit.query_audit_trail.return_value = [
            AuditEntry(
                audit_id=f"audit{i}",
                timestamp=datetime.utcnow(),
                event_type=AuditEventType.AGENT_DECISION,
                actor_id=f"agent{i % 2}",
                actor_type="agent",
                action="decide",
                resource_id=f"decision{i}",
                resource_type="agent_decision",
                details={
                    "confidence": 0.8 + (i * 0.05),
                    "escalationRequired": i % 3 == 0
                },
                data_sources=[],
                reasoning="",
                outcome="success" if i % 2 == 0 else "pending"
            )
            for i in range(10)
        ]
        
        tracker = DecisionHistoryTracker(mock_audit)
        stats = tracker.get_decision_statistics(
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow()
        )
        
        assert stats['totalDecisions'] == 10
        assert 'averageConfidence' in stats
        assert 'escalationRate' in stats
        assert 'decisionsByAgent' in stats
        assert 'decisionsByOutcome' in stats


class TestWorkflowModificationLogger:
    """Test workflow modification logging"""

    @patch('src.services.audit.AuditService')
    def test_log_modification(self, mock_audit_service):
        """Test logging a workflow modification"""
        mock_audit = Mock()
        mock_audit.log_workflow_modification.return_value = None
        
        logger = WorkflowModificationLogger(mock_audit)
        
        modification = logger.log_modification(
            workflow_id="wf_123",
            modified_by="agent_regen",
            modification_type="optimization",
            changes={"step1": "updated"},
            reason="Performance improvement",
            previous_version="1.0",
            new_version="1.1"
        )
        
        assert modification.workflow_id == "wf_123"
        assert modification.modification_type == "optimization"
        assert modification.new_version == "1.1"
        assert mock_audit.log_workflow_modification.called

    @patch('src.services.audit.AuditService')
    def test_get_modification_history(self, mock_audit_service):
        """Test retrieving workflow modification history"""
        mock_audit = Mock()
        mock_audit.query_audit_trail.return_value = [
            AuditEntry(
                audit_id="audit1",
                timestamp=datetime.utcnow(),
                event_type=AuditEventType.WORKFLOW_MODIFICATION,
                actor_id="agent_regen",
                actor_type="agent",
                action="optimization",
                resource_id="wf_123",
                resource_type="workflow",
                details={
                    "workflowId": "wf_123",
                    "modificationId": "mod1",
                    "changes": {"step1": "updated"},
                    "reasoning": "Performance",
                    "newVersion": "1.1"
                },
                data_sources=[],
                reasoning="Performance"
            )
        ]
        
        logger = WorkflowModificationLogger(mock_audit)
        history = logger.get_modification_history(workflow_id="wf_123")
        
        assert len(history) == 1
        assert history[0].workflow_id == "wf_123"
        assert history[0].modification_type == "optimization"


class TestComplianceReportingService:
    """Test compliance reporting"""

    @patch('src.services.audit.AuditService')
    def test_generate_decision_history_report(self, mock_audit_service):
        """Test generating decision history report"""
        mock_audit = Mock()
        mock_audit.query_audit_trail.return_value = []
        
        reporting = ComplianceReportingService(mock_audit)
        
        start_time = datetime.utcnow() - timedelta(days=7)
        end_time = datetime.utcnow()
        
        report = reporting.generate_decision_history_report(
            start_time=start_time,
            end_time=end_time
        )
        
        assert report.report_type == ComplianceReportType.DECISION_HISTORY
        assert report.period_start == start_time
        assert report.period_end == end_time
        assert 'totalDecisions' in report.summary

    @patch('src.services.audit.AuditService')
    def test_generate_workflow_changes_report(self, mock_audit_service):
        """Test generating workflow changes report"""
        mock_audit = Mock()
        mock_audit.query_audit_trail.return_value = []
        
        reporting = ComplianceReportingService(mock_audit)
        
        start_time = datetime.utcnow() - timedelta(days=7)
        end_time = datetime.utcnow()
        
        report = reporting.generate_workflow_changes_report(
            start_time=start_time,
            end_time=end_time
        )
        
        assert report.report_type == ComplianceReportType.WORKFLOW_CHANGES
        assert 'totalModifications' in report.summary

    @patch('src.services.audit.AuditService')
    def test_generate_escalation_summary_report(self, mock_audit_service):
        """Test generating escalation summary report"""
        mock_audit = Mock()
        
        # Mock escalation events
        def query_side_effect(event_type=None, **kwargs):
            if event_type == AuditEventType.ESCALATION_CREATED:
                return [
                    AuditEntry(
                        audit_id="audit1",
                        timestamp=datetime.utcnow() - timedelta(hours=2),
                        event_type=AuditEventType.ESCALATION_CREATED,
                        actor_id="system",
                        actor_type="system",
                        action="created",
                        resource_id="esc1",
                        resource_type="escalation",
                        details={},
                        data_sources=[]
                    )
                ]
            elif event_type == AuditEventType.ESCALATION_RESOLVED:
                return [
                    AuditEntry(
                        audit_id="audit2",
                        timestamp=datetime.utcnow(),
                        event_type=AuditEventType.ESCALATION_RESOLVED,
                        actor_id="user1",
                        actor_type="user",
                        action="resolved",
                        resource_id="esc1",
                        resource_type="escalation",
                        details={},
                        data_sources=[]
                    )
                ]
            return []
        
        mock_audit.query_audit_trail.side_effect = query_side_effect
        
        reporting = ComplianceReportingService(mock_audit)
        
        report = reporting.generate_escalation_summary_report(
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow()
        )
        
        assert report.report_type == ComplianceReportType.ESCALATION_SUMMARY
        assert 'totalCreated' in report.summary
        assert 'totalResolved' in report.summary
        assert 'pending' in report.summary

    @patch('src.services.audit.AuditService')
    def test_report_to_json(self, mock_audit_service):
        """Test converting report to JSON"""
        mock_audit = Mock()
        mock_audit.query_audit_trail.return_value = []
        
        reporting = ComplianceReportingService(mock_audit)
        
        report = reporting.generate_decision_history_report(
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow()
        )
        
        json_str = report.to_json()
        assert isinstance(json_str, str)
        assert 'reportId' in json_str
        assert 'reportType' in json_str


class TestAuditTrailSystem:
    """Test main audit trail system"""

    def test_system_initialization(self):
        """Test audit trail system initialization"""
        with patch('src.services.audit.AuditService'):
            system = AuditTrailSystem()
            
            assert system.get_audit_service() is not None
            assert system.get_decision_tracker() is not None
            assert system.get_workflow_logger() is not None
            assert system.get_compliance_reporting() is not None

    def test_integrated_workflow(self):
        """Test integrated audit trail workflow"""
        with patch('src.services.audit.AuditService') as mock_service:
            mock_audit = Mock()
            mock_service.return_value = mock_audit
            mock_audit.query_audit_trail.return_value = []
            
            # Mock the table attribute to prevent AWS calls
            mock_audit.table = Mock()
            
            system = AuditTrailSystem()
            
            # Inject the mocked audit service
            system.audit_service = mock_audit
            system.decision_tracker = DecisionHistoryTracker(mock_audit)
            system.workflow_logger = WorkflowModificationLogger(mock_audit)
            system.compliance_reporting = ComplianceReportingService(mock_audit)
            
            # Test decision tracking
            tracker = system.get_decision_tracker()
            history = tracker.get_decision_history()
            assert isinstance(history, list)
            
            # Test compliance reporting
            reporting = system.get_compliance_reporting()
            report = reporting.generate_decision_history_report(
                start_time=datetime.utcnow() - timedelta(days=1),
                end_time=datetime.utcnow()
            )
            assert report is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
