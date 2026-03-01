"""
Audit Trail Service for RetailMind AI
Maintains comprehensive audit logs for all decisions and system changes
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
import uuid
import json

from ..models.agent_decision import AgentDecision
from ..services.ai_council import CouncilDecision


class AuditEventType(Enum):
    """Types of audit events"""
    AGENT_DECISION = "agent_decision"
    COUNCIL_DECISION = "council_decision"
    WORKFLOW_EXECUTION = "workflow_execution"
    WORKFLOW_MODIFICATION = "workflow_modification"
    ESCALATION_CREATED = "escalation_created"
    ESCALATION_RESOLVED = "escalation_resolved"
    SYSTEM_CONFIGURATION = "system_configuration"
    DATA_ACCESS = "data_access"


@dataclass
class AuditEntry:
    """Audit trail entry"""
    audit_id: str
    timestamp: datetime
    event_type: AuditEventType
    actor_id: str  # Agent ID, user ID, or system component
    actor_type: str  # 'agent', 'user', 'system'
    action: str
    resource_id: str
    resource_type: str
    details: Dict[str, Any]
    data_sources: List[str]
    reasoning: Optional[str] = None
    outcome: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'auditId': self.audit_id,
            'timestamp': self.timestamp.isoformat(),
            'eventType': self.event_type.value,
            'actorId': self.actor_id,
            'actorType': self.actor_type,
            'action': self.action,
            'resourceId': self.resource_id,
            'resourceType': self.resource_type,
            'details': self.details,
            'dataSources': self.data_sources,
            'reasoning': self.reasoning,
            'outcome': self.outcome
        }


class AuditService:
    """
    Service for maintaining comprehensive audit trails
    Logs all agent inputs, reasoning, decisions, and system modifications
    """
    
    def __init__(self, dynamodb_table_name: str = "retailmind-audit-trail"):
        """
        Initialize audit service
        
        Args:
            dynamodb_table_name: Name of the DynamoDB table for audit logs
        """
        self.table_name = dynamodb_table_name
        
        from ..utils.aws_clients import aws_clients
        self.dynamodb = aws_clients.dynamodb_resource
        self.table = self.dynamodb.Table(self.table_name)
    
    def log_agent_decision(self, decision: AgentDecision) -> AuditEntry:
        """
        Log an agent decision to the audit trail
        
        Args:
            decision: Agent decision to log
            
        Returns:
            AuditEntry that was created
        """
        audit_entry = AuditEntry(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.AGENT_DECISION,
            actor_id=decision.agent_id,
            actor_type='agent',
            action=decision.recommendation.action,
            resource_id=decision.decision_id,
            resource_type='agent_decision',
            details={
                'confidence': decision.recommendation.confidence,
                'inputData': decision.input_data,
                'supportingData': decision.recommendation.supporting_data,
                'escalationRequired': decision.escalation_required
            },
            data_sources=self._extract_data_sources(decision.recommendation.supporting_data),
            reasoning=decision.recommendation.reasoning,
            outcome='pending'
        )
        
        self._store_audit_entry(audit_entry)
        return audit_entry
    
    def log_council_decision(self, council_decision: CouncilDecision) -> AuditEntry:
        """
        Log a council decision to the audit trail
        
        Args:
            council_decision: Council decision to log
            
        Returns:
            AuditEntry that was created
        """
        audit_entry = AuditEntry(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.COUNCIL_DECISION,
            actor_id='ai_council',
            actor_type='system',
            action=council_decision.aggregated_recommendation.action,
            resource_id=council_decision.decision_id,
            resource_type='council_decision',
            details={
                'participatingAgents': council_decision.participating_agents,
                'confidence': council_decision.aggregated_recommendation.confidence,
                'conflictDetected': council_decision.conflict_detected,
                'resolutionMethod': council_decision.resolution_method,
                'escalationRequired': council_decision.escalation_required,
                'agentDecisions': [d.to_dict() for d in council_decision.agent_decisions]
            },
            data_sources=self._extract_data_sources(council_decision.aggregated_recommendation.supporting_data),
            reasoning=council_decision.aggregated_recommendation.reasoning,
            outcome='pending'
        )
        
        self._store_audit_entry(audit_entry)
        return audit_entry
    
    def log_workflow_execution(
        self,
        workflow_id: str,
        instance_id: str,
        action: str,
        details: Dict[str, Any]
    ) -> AuditEntry:
        """
        Log a workflow execution event
        
        Args:
            workflow_id: ID of the workflow
            instance_id: ID of the workflow instance
            action: Action being performed
            details: Additional details about the execution
            
        Returns:
            AuditEntry that was created
        """
        audit_entry = AuditEntry(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.WORKFLOW_EXECUTION,
            actor_id='workflow_engine',
            actor_type='system',
            action=action,
            resource_id=instance_id,
            resource_type='workflow_instance',
            details={
                'workflowId': workflow_id,
                **details
            },
            data_sources=[],
            reasoning=details.get('reasoning'),
            outcome=details.get('status', 'pending')
        )
        
        self._store_audit_entry(audit_entry)
        return audit_entry
    
    def log_workflow_modification(
        self,
        workflow_id: str,
        modified_by: str,
        modification_type: str,
        details: Dict[str, Any]
    ) -> AuditEntry:
        """
        Log a workflow modification event
        
        Args:
            workflow_id: ID of the workflow
            modified_by: ID of the agent or user who modified the workflow
            modification_type: Type of modification
            details: Additional details about the modification
            
        Returns:
            AuditEntry that was created
        """
        audit_entry = AuditEntry(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.WORKFLOW_MODIFICATION,
            actor_id=modified_by,
            actor_type='agent' if modified_by.startswith('agent_') else 'user',
            action=modification_type,
            resource_id=workflow_id,
            resource_type='workflow',
            details=details,
            data_sources=[],
            reasoning=details.get('reasoning'),
            outcome='completed'
        )
        
        self._store_audit_entry(audit_entry)
        return audit_entry
    
    def log_escalation_event(
        self,
        escalation_id: str,
        event_type: str,
        actor_id: str,
        details: Dict[str, Any]
    ) -> AuditEntry:
        """
        Log an escalation-related event
        
        Args:
            escalation_id: ID of the escalation
            event_type: Type of escalation event ('created' or 'resolved')
            actor_id: ID of the actor
            details: Additional details
            
        Returns:
            AuditEntry that was created
        """
        audit_entry = AuditEntry(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.ESCALATION_CREATED if event_type == 'created' else AuditEventType.ESCALATION_RESOLVED,
            actor_id=actor_id,
            actor_type='system' if event_type == 'created' else 'user',
            action=event_type,
            resource_id=escalation_id,
            resource_type='escalation',
            details=details,
            data_sources=[],
            reasoning=details.get('reason'),
            outcome=details.get('status', 'pending')
        )
        
        self._store_audit_entry(audit_entry)
        return audit_entry
    
    def _extract_data_sources(self, supporting_data: List[Any]) -> List[str]:
        """
        Extract data source identifiers from supporting data
        
        Args:
            supporting_data: List of supporting data items
            
        Returns:
            List of data source identifiers
        """
        sources = []
        for item in supporting_data:
            if isinstance(item, dict) and 'source' in item:
                sources.append(item['source'])
        return sources
    
    def _store_audit_entry(self, audit_entry: AuditEntry) -> Dict[str, Any]:
        """
        Store audit entry in DynamoDB
        
        Args:
            audit_entry: Audit entry to store
            
        Returns:
            Response from DynamoDB
        """
        try:
            response = self.table.put_item(Item=audit_entry.to_dict())
            return response
        except Exception as e:
            raise AuditError(f"Failed to store audit entry: {str(e)}")
    
    def get_audit_entry(self, audit_id: str) -> Optional[AuditEntry]:
        """
        Get audit entry by ID
        
        Args:
            audit_id: ID of the audit entry
            
        Returns:
            AuditEntry if found, None otherwise
        """
        try:
            response = self.table.get_item(Key={'auditId': audit_id})
            if 'Item' in response:
                item = response['Item']
                return AuditEntry(
                    audit_id=item['auditId'],
                    timestamp=datetime.fromisoformat(item['timestamp']),
                    event_type=AuditEventType(item['eventType']),
                    actor_id=item['actorId'],
                    actor_type=item['actorType'],
                    action=item['action'],
                    resource_id=item['resourceId'],
                    resource_type=item['resourceType'],
                    details=item['details'],
                    data_sources=item['dataSources'],
                    reasoning=item.get('reasoning'),
                    outcome=item.get('outcome')
                )
            return None
        except Exception as e:
            raise AuditError(f"Failed to get audit entry: {str(e)}")
    
    def query_audit_trail(
        self,
        event_type: Optional[AuditEventType] = None,
        actor_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[AuditEntry]:
        """
        Query audit trail with filters
        
        Args:
            event_type: Optional event type filter
            actor_id: Optional actor ID filter
            resource_id: Optional resource ID filter
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            List of matching AuditEntry objects
        """
        try:
            # Build filter expression
            filter_expressions = []
            expr_attr_values = {}
            expr_attr_names = {}
            
            if event_type:
                filter_expressions.append('#eventType = :eventType')
                expr_attr_names['#eventType'] = 'eventType'
                expr_attr_values[':eventType'] = event_type.value
            
            if actor_id:
                filter_expressions.append('actorId = :actorId')
                expr_attr_values[':actorId'] = actor_id
            
            if resource_id:
                filter_expressions.append('resourceId = :resourceId')
                expr_attr_values[':resourceId'] = resource_id
            
            if start_time:
                filter_expressions.append('#timestamp >= :startTime')
                expr_attr_names['#timestamp'] = 'timestamp'
                expr_attr_values[':startTime'] = start_time.isoformat()
            
            if end_time:
                filter_expressions.append('#timestamp <= :endTime')
                expr_attr_names['#timestamp'] = 'timestamp'
                expr_attr_values[':endTime'] = end_time.isoformat()
            
            # Execute scan with filters
            scan_kwargs = {}
            if filter_expressions:
                scan_kwargs['FilterExpression'] = ' AND '.join(filter_expressions)
            if expr_attr_names:
                scan_kwargs['ExpressionAttributeNames'] = expr_attr_names
            if expr_attr_values:
                scan_kwargs['ExpressionAttributeValues'] = expr_attr_values
            
            response = self.table.scan(**scan_kwargs)
            
            # Convert to AuditEntry objects
            entries = []
            for item in response.get('Items', []):
                entries.append(AuditEntry(
                    audit_id=item['auditId'],
                    timestamp=datetime.fromisoformat(item['timestamp']),
                    event_type=AuditEventType(item['eventType']),
                    actor_id=item['actorId'],
                    actor_type=item['actorType'],
                    action=item['action'],
                    resource_id=item['resourceId'],
                    resource_type=item['resourceType'],
                    details=item['details'],
                    data_sources=item['dataSources'],
                    reasoning=item.get('reasoning'),
                    outcome=item.get('outcome')
                ))
            
            return entries
        except Exception as e:
            raise AuditError(f"Failed to query audit trail: {str(e)}")
    
    def update_outcome(self, audit_id: str, outcome: str) -> Dict[str, Any]:
        """
        Update the outcome of an audit entry
        
        Args:
            audit_id: ID of the audit entry
            outcome: New outcome value
            
        Returns:
            Response from DynamoDB
        """
        try:
            response = self.table.update_item(
                Key={'auditId': audit_id},
                UpdateExpression='SET outcome = :outcome',
                ExpressionAttributeValues={':outcome': outcome}
            )
            return response
        except Exception as e:
            raise AuditError(f"Failed to update audit outcome: {str(e)}")


class AuditError(Exception):
    """Exception raised for audit errors"""
    pass
