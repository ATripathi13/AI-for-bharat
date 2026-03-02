"""
Comprehensive Audit Trail System for RetailMind AI

Provides decision history tracking, workflow modification logs,
and compliance reporting capabilities.

Requirements: 10.2, 10.4
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
import json

from .audit import AuditService, AuditEntry, AuditEventType


class ComplianceReportType(Enum):
    """Types of compliance reports"""
    DECISION_HISTORY = "decision_history"
    WORKFLOW_CHANGES = "workflow_changes"
    ESCALATION_SUMMARY = "escalation_summary"
    DATA_ACCESS_LOG = "data_access_log"
    AGENT_ACTIVITY = "agent_activity"
    SYSTEM_CHANGES = "system_changes"


@dataclass
class DecisionHistoryEntry:
    """Represents a decision in the history"""
    decision_id: str
    timestamp: datetime
    agent_id: str
    decision_type: str
    action: str
    confidence: float
    reasoning: str
    data_sources: List[str]
    outcome: str
    escalated: bool


@dataclass
class WorkflowModificationEntry:
    """Represents a workflow modification"""
    modification_id: str
    timestamp: datetime
    workflow_id: str
    modified_by: str
    modification_type: str
    changes: Dict[str, Any]
    reason: str
    previous_version: Optional[str]
    new_version: str


@dataclass
class ComplianceReport:
    """Compliance report structure"""
    report_id: str
    report_type: ComplianceReportType
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    summary: Dict[str, Any]
    entries: List[Dict[str, Any]]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'reportId': self.report_id,
            'reportType': self.report_type.value,
            'generatedAt': self.generated_at.isoformat(),
            'periodStart': self.period_start.isoformat(),
            'periodEnd': self.period_end.isoformat(),
            'summary': self.summary,
            'entries': self.entries,
            'metadata': self.metadata
        }

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


class DecisionHistoryTracker:
    """
    Tracks and retrieves decision history for audit and analysis.
    Provides comprehensive view of all decisions made by agents.
    """

    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service

    def get_decision_history(
        self,
        agent_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        decision_type: Optional[str] = None
    ) -> List[DecisionHistoryEntry]:
        """
        Get decision history with optional filters
        
        Args:
            agent_id: Optional filter by agent ID
            start_time: Optional start time
            end_time: Optional end time
            decision_type: Optional filter by decision type
            
        Returns:
            List of DecisionHistoryEntry objects
        """
        # Query audit trail for agent decisions
        audit_entries = self.audit_service.query_audit_trail(
            event_type=AuditEventType.AGENT_DECISION,
            actor_id=agent_id,
            start_time=start_time,
            end_time=end_time
        )

        # Convert to DecisionHistoryEntry objects
        history = []
        for entry in audit_entries:
            details = entry.details
            
            # Apply decision type filter if specified
            if decision_type and details.get('decisionType') != decision_type:
                continue

            history_entry = DecisionHistoryEntry(
                decision_id=entry.resource_id,
                timestamp=entry.timestamp,
                agent_id=entry.actor_id,
                decision_type=details.get('decisionType', 'unknown'),
                action=entry.action,
                confidence=details.get('confidence', 0.0),
                reasoning=entry.reasoning or '',
                data_sources=entry.data_sources,
                outcome=entry.outcome or 'pending',
                escalated=details.get('escalationRequired', False)
            )
            history.append(history_entry)

        # Sort by timestamp descending
        history.sort(key=lambda x: x.timestamp, reverse=True)
        return history

    def get_decision_by_id(self, decision_id: str) -> Optional[DecisionHistoryEntry]:
        """
        Get a specific decision by ID
        
        Args:
            decision_id: Decision ID to retrieve
            
        Returns:
            DecisionHistoryEntry if found, None otherwise
        """
        audit_entries = self.audit_service.query_audit_trail(
            event_type=AuditEventType.AGENT_DECISION,
            resource_id=decision_id
        )

        if not audit_entries:
            return None

        entry = audit_entries[0]
        details = entry.details

        return DecisionHistoryEntry(
            decision_id=entry.resource_id,
            timestamp=entry.timestamp,
            agent_id=entry.actor_id,
            decision_type=details.get('decisionType', 'unknown'),
            action=entry.action,
            confidence=details.get('confidence', 0.0),
            reasoning=entry.reasoning or '',
            data_sources=entry.data_sources,
            outcome=entry.outcome or 'pending',
            escalated=details.get('escalationRequired', False)
        )

    def get_decision_statistics(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Get statistics about decisions in a time period
        
        Args:
            start_time: Start of period
            end_time: End of period
            
        Returns:
            Dictionary with decision statistics
        """
        history = self.get_decision_history(
            start_time=start_time,
            end_time=end_time
        )

        total_decisions = len(history)
        escalated_count = sum(1 for h in history if h.escalated)
        
        # Calculate average confidence
        avg_confidence = (
            sum(h.confidence for h in history) / total_decisions
            if total_decisions > 0 else 0.0
        )

        # Count by agent
        by_agent: Dict[str, int] = {}
        for h in history:
            by_agent[h.agent_id] = by_agent.get(h.agent_id, 0) + 1

        # Count by outcome
        by_outcome: Dict[str, int] = {}
        for h in history:
            by_outcome[h.outcome] = by_outcome.get(h.outcome, 0) + 1

        return {
            'totalDecisions': total_decisions,
            'escalatedCount': escalated_count,
            'escalationRate': escalated_count / total_decisions if total_decisions > 0 else 0.0,
            'averageConfidence': avg_confidence,
            'decisionsByAgent': by_agent,
            'decisionsByOutcome': by_outcome
        }


class WorkflowModificationLogger:
    """
    Logs and tracks all workflow modifications for audit purposes.
    Maintains version history and change tracking.
    """

    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service

    def log_modification(
        self,
        workflow_id: str,
        modified_by: str,
        modification_type: str,
        changes: Dict[str, Any],
        reason: str,
        previous_version: Optional[str] = None,
        new_version: str = "1.0"
    ) -> WorkflowModificationEntry:
        """
        Log a workflow modification
        
        Args:
            workflow_id: ID of the workflow
            modified_by: ID of the modifier
            modification_type: Type of modification
            changes: Dictionary of changes made
            reason: Reason for modification
            previous_version: Previous version identifier
            new_version: New version identifier
            
        Returns:
            WorkflowModificationEntry that was created
        """
        import uuid
        modification_id = str(uuid.uuid4())

        details = {
            'modificationId': modification_id,
            'changes': changes,
            'reasoning': reason,
            'previousVersion': previous_version,
            'newVersion': new_version
        }

        # Log to audit service
        self.audit_service.log_workflow_modification(
            workflow_id=workflow_id,
            modified_by=modified_by,
            modification_type=modification_type,
            details=details
        )

        return WorkflowModificationEntry(
            modification_id=modification_id,
            timestamp=datetime.utcnow(),
            workflow_id=workflow_id,
            modified_by=modified_by,
            modification_type=modification_type,
            changes=changes,
            reason=reason,
            previous_version=previous_version,
            new_version=new_version
        )

    def get_modification_history(
        self,
        workflow_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[WorkflowModificationEntry]:
        """
        Get workflow modification history
        
        Args:
            workflow_id: Optional filter by workflow ID
            start_time: Optional start time
            end_time: Optional end time
            
        Returns:
            List of WorkflowModificationEntry objects
        """
        audit_entries = self.audit_service.query_audit_trail(
            event_type=AuditEventType.WORKFLOW_MODIFICATION,
            resource_id=workflow_id,
            start_time=start_time,
            end_time=end_time
        )

        modifications = []
        for entry in audit_entries:
            details = entry.details
            modifications.append(WorkflowModificationEntry(
                modification_id=details.get('modificationId', entry.audit_id),
                timestamp=entry.timestamp,
                workflow_id=details.get('workflowId', entry.resource_id),
                modified_by=entry.actor_id,
                modification_type=entry.action,
                changes=details.get('changes', {}),
                reason=details.get('reasoning', ''),
                previous_version=details.get('previousVersion'),
                new_version=details.get('newVersion', 'unknown')
            ))

        # Sort by timestamp descending
        modifications.sort(key=lambda x: x.timestamp, reverse=True)
        return modifications

    def get_workflow_version_history(self, workflow_id: str) -> List[str]:
        """
        Get version history for a workflow
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            List of version identifiers in chronological order
        """
        modifications = self.get_modification_history(workflow_id=workflow_id)
        
        versions = []
        for mod in reversed(modifications):  # Reverse to get chronological order
            if mod.new_version and mod.new_version not in versions:
                versions.append(mod.new_version)

        return versions


class ComplianceReportingService:
    """
    Generates compliance reports for audit and regulatory purposes.
    Provides various report types for different compliance needs.
    """

    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service
        self.decision_tracker = DecisionHistoryTracker(audit_service)
        self.workflow_logger = WorkflowModificationLogger(audit_service)

    def generate_decision_history_report(
        self,
        start_time: datetime,
        end_time: datetime,
        agent_id: Optional[str] = None
    ) -> ComplianceReport:
        """
        Generate decision history compliance report
        
        Args:
            start_time: Start of reporting period
            end_time: End of reporting period
            agent_id: Optional filter by agent
            
        Returns:
            ComplianceReport with decision history
        """
        import uuid

        history = self.decision_tracker.get_decision_history(
            agent_id=agent_id,
            start_time=start_time,
            end_time=end_time
        )

        statistics = self.decision_tracker.get_decision_statistics(
            start_time=start_time,
            end_time=end_time
        )

        entries = [asdict(h) for h in history]
        # Convert datetime objects to ISO format strings
        for entry in entries:
            entry['timestamp'] = entry['timestamp'].isoformat()

        return ComplianceReport(
            report_id=str(uuid.uuid4()),
            report_type=ComplianceReportType.DECISION_HISTORY,
            generated_at=datetime.utcnow(),
            period_start=start_time,
            period_end=end_time,
            summary=statistics,
            entries=entries,
            metadata={
                'agentFilter': agent_id,
                'totalEntries': len(entries)
            }
        )

    def generate_workflow_changes_report(
        self,
        start_time: datetime,
        end_time: datetime,
        workflow_id: Optional[str] = None
    ) -> ComplianceReport:
        """
        Generate workflow changes compliance report
        
        Args:
            start_time: Start of reporting period
            end_time: End of reporting period
            workflow_id: Optional filter by workflow
            
        Returns:
            ComplianceReport with workflow modifications
        """
        import uuid

        modifications = self.workflow_logger.get_modification_history(
            workflow_id=workflow_id,
            start_time=start_time,
            end_time=end_time
        )

        # Calculate summary statistics
        total_modifications = len(modifications)
        by_type: Dict[str, int] = {}
        by_workflow: Dict[str, int] = {}

        for mod in modifications:
            by_type[mod.modification_type] = by_type.get(mod.modification_type, 0) + 1
            by_workflow[mod.workflow_id] = by_workflow.get(mod.workflow_id, 0) + 1

        entries = [asdict(m) for m in modifications]
        # Convert datetime objects to ISO format strings
        for entry in entries:
            entry['timestamp'] = entry['timestamp'].isoformat()

        return ComplianceReport(
            report_id=str(uuid.uuid4()),
            report_type=ComplianceReportType.WORKFLOW_CHANGES,
            generated_at=datetime.utcnow(),
            period_start=start_time,
            period_end=end_time,
            summary={
                'totalModifications': total_modifications,
                'modificationsByType': by_type,
                'modificationsByWorkflow': by_workflow
            },
            entries=entries,
            metadata={
                'workflowFilter': workflow_id,
                'totalEntries': len(entries)
            }
        )

    def generate_escalation_summary_report(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> ComplianceReport:
        """
        Generate escalation summary compliance report
        
        Args:
            start_time: Start of reporting period
            end_time: End of reporting period
            
        Returns:
            ComplianceReport with escalation summary
        """
        import uuid

        # Query escalation events
        created_entries = self.audit_service.query_audit_trail(
            event_type=AuditEventType.ESCALATION_CREATED,
            start_time=start_time,
            end_time=end_time
        )

        resolved_entries = self.audit_service.query_audit_trail(
            event_type=AuditEventType.ESCALATION_RESOLVED,
            start_time=start_time,
            end_time=end_time
        )

        # Calculate statistics
        total_created = len(created_entries)
        total_resolved = len(resolved_entries)
        pending = total_created - total_resolved

        # Calculate average resolution time
        resolution_times = []
        for resolved in resolved_entries:
            escalation_id = resolved.resource_id
            # Find corresponding creation entry
            created = next(
                (e for e in created_entries if e.resource_id == escalation_id),
                None
            )
            if created:
                resolution_time = (resolved.timestamp - created.timestamp).total_seconds()
                resolution_times.append(resolution_time)

        avg_resolution_time = (
            sum(resolution_times) / len(resolution_times)
            if resolution_times else 0.0
        )

        entries = []
        for entry in created_entries + resolved_entries:
            entries.append({
                'escalationId': entry.resource_id,
                'timestamp': entry.timestamp.isoformat(),
                'eventType': entry.event_type.value,
                'actorId': entry.actor_id,
                'details': entry.details
            })

        return ComplianceReport(
            report_id=str(uuid.uuid4()),
            report_type=ComplianceReportType.ESCALATION_SUMMARY,
            generated_at=datetime.utcnow(),
            period_start=start_time,
            period_end=end_time,
            summary={
                'totalCreated': total_created,
                'totalResolved': total_resolved,
                'pending': pending,
                'averageResolutionTimeSeconds': avg_resolution_time
            },
            entries=entries,
            metadata={
                'totalEntries': len(entries)
            }
        )

    def generate_agent_activity_report(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> ComplianceReport:
        """
        Generate agent activity compliance report
        
        Args:
            start_time: Start of reporting period
            end_time: End of reporting period
            
        Returns:
            ComplianceReport with agent activity
        """
        import uuid

        # Get all agent decisions
        history = self.decision_tracker.get_decision_history(
            start_time=start_time,
            end_time=end_time
        )

        # Calculate per-agent statistics
        agent_stats: Dict[str, Dict[str, Any]] = {}
        for h in history:
            if h.agent_id not in agent_stats:
                agent_stats[h.agent_id] = {
                    'totalDecisions': 0,
                    'escalatedCount': 0,
                    'confidenceSum': 0.0,
                    'outcomes': {}
                }

            stats = agent_stats[h.agent_id]
            stats['totalDecisions'] += 1
            if h.escalated:
                stats['escalatedCount'] += 1
            stats['confidenceSum'] += h.confidence
            stats['outcomes'][h.outcome] = stats['outcomes'].get(h.outcome, 0) + 1

        # Calculate averages
        for agent_id, stats in agent_stats.items():
            stats['averageConfidence'] = (
                stats['confidenceSum'] / stats['totalDecisions']
                if stats['totalDecisions'] > 0 else 0.0
            )
            stats['escalationRate'] = (
                stats['escalatedCount'] / stats['totalDecisions']
                if stats['totalDecisions'] > 0 else 0.0
            )
            del stats['confidenceSum']  # Remove intermediate calculation

        entries = [
            {'agentId': agent_id, **stats}
            for agent_id, stats in agent_stats.items()
        ]

        return ComplianceReport(
            report_id=str(uuid.uuid4()),
            report_type=ComplianceReportType.AGENT_ACTIVITY,
            generated_at=datetime.utcnow(),
            period_start=start_time,
            period_end=end_time,
            summary={
                'totalAgents': len(agent_stats),
                'totalDecisions': sum(s['totalDecisions'] for s in agent_stats.values())
            },
            entries=entries,
            metadata={
                'totalEntries': len(entries)
            }
        )


class AuditTrailSystem:
    """
    Main audit trail system that coordinates all audit functionality.
    Provides unified interface for decision tracking, workflow logging,
    and compliance reporting.
    """

    def __init__(self, dynamodb_table_name: str = "retailmind-audit-trail"):
        self.audit_service = AuditService(dynamodb_table_name)
        self.decision_tracker = DecisionHistoryTracker(self.audit_service)
        self.workflow_logger = WorkflowModificationLogger(self.audit_service)
        self.compliance_reporting = ComplianceReportingService(self.audit_service)

    def get_audit_service(self) -> AuditService:
        """Get the underlying audit service"""
        return self.audit_service

    def get_decision_tracker(self) -> DecisionHistoryTracker:
        """Get the decision history tracker"""
        return self.decision_tracker

    def get_workflow_logger(self) -> WorkflowModificationLogger:
        """Get the workflow modification logger"""
        return self.workflow_logger

    def get_compliance_reporting(self) -> ComplianceReportingService:
        """Get the compliance reporting service"""
        return self.compliance_reporting


# Global audit trail system instance
_audit_trail_system: Optional[AuditTrailSystem] = None


def get_audit_trail_system() -> AuditTrailSystem:
    """Get or create the global audit trail system instance"""
    global _audit_trail_system
    if _audit_trail_system is None:
        _audit_trail_system = AuditTrailSystem()
    return _audit_trail_system
