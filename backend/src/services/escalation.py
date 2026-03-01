"""
Escalation Service for RetailMind AI
Handles escalation of decisions to human oversight based on confidence thresholds
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
import uuid

from ..services.ai_council import CouncilDecision
from ..models.agent_decision import AgentDecision


class EscalationPriority(Enum):
    """Priority levels for escalations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EscalationStatus(Enum):
    """Status of an escalation"""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    REJECTED = "rejected"


@dataclass
class EscalationRequest:
    """Request for human oversight escalation"""
    escalation_id: str
    timestamp: datetime
    priority: EscalationPriority
    status: EscalationStatus
    decision_id: str
    decision_type: str  # 'agent' or 'council'
    confidence: float
    reason: str
    context: Dict[str, Any]
    assigned_to: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'escalationId': self.escalation_id,
            'timestamp': self.timestamp.isoformat(),
            'priority': self.priority.value,
            'status': self.status.value,
            'decisionId': self.decision_id,
            'decisionType': self.decision_type,
            'confidence': self.confidence,
            'reason': self.reason,
            'context': self.context,
            'assignedTo': self.assigned_to,
            'resolvedAt': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolutionNotes': self.resolution_notes
        }


class EscalationService:
    """
    Service for managing decision escalations
    Handles confidence threshold checking and human-in-the-loop notifications
    """
    
    def __init__(
        self,
        dynamodb_table_name: str = "retailmind-escalations",
        sns_topic_arn: Optional[str] = None
    ):
        """
        Initialize escalation service
        
        Args:
            dynamodb_table_name: Name of the DynamoDB table for escalations
            sns_topic_arn: Optional SNS topic ARN for notifications
        """
        self.table_name = dynamodb_table_name
        self.sns_topic_arn = sns_topic_arn
        
        from ..utils.aws_clients import aws_clients
        self.dynamodb = aws_clients.dynamodb_resource
        self.table = self.dynamodb.Table(self.table_name)
        
        if sns_topic_arn:
            import boto3
            self.sns = boto3.client('sns')
        else:
            self.sns = None
    
    def check_and_escalate_agent_decision(
        self,
        decision: AgentDecision,
        confidence_threshold: float = 0.8
    ) -> Optional[EscalationRequest]:
        """
        Check if an agent decision requires escalation
        
        Args:
            decision: Agent decision to check
            confidence_threshold: Threshold below which escalation is required
            
        Returns:
            EscalationRequest if escalation is needed, None otherwise
        """
        if decision.recommendation.confidence < confidence_threshold or decision.escalation_required:
            priority = self._determine_priority(decision.recommendation.confidence)
            
            escalation = EscalationRequest(
                escalation_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                priority=priority,
                status=EscalationStatus.PENDING,
                decision_id=decision.decision_id,
                decision_type='agent',
                confidence=decision.recommendation.confidence,
                reason=f"Confidence {decision.recommendation.confidence:.2f} below threshold {confidence_threshold}",
                context={
                    'agentId': decision.agent_id,
                    'action': decision.recommendation.action,
                    'reasoning': decision.recommendation.reasoning,
                    'inputData': decision.input_data
                }
            )
            
            # Store escalation
            self._store_escalation(escalation)
            
            # Send notification
            self._send_notification(escalation)
            
            return escalation
        
        return None
    
    def check_and_escalate_council_decision(
        self,
        council_decision: CouncilDecision,
        confidence_threshold: float = 0.8
    ) -> Optional[EscalationRequest]:
        """
        Check if a council decision requires escalation
        
        Args:
            council_decision: Council decision to check
            confidence_threshold: Threshold below which escalation is required
            
        Returns:
            EscalationRequest if escalation is needed, None otherwise
        """
        if council_decision.escalation_required:
            priority = self._determine_priority(council_decision.aggregated_recommendation.confidence)
            
            escalation = EscalationRequest(
                escalation_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                priority=priority,
                status=EscalationStatus.PENDING,
                decision_id=council_decision.decision_id,
                decision_type='council',
                confidence=council_decision.aggregated_recommendation.confidence,
                reason=f"Council decision requires escalation (confidence: {council_decision.aggregated_recommendation.confidence:.2f})",
                context={
                    'participatingAgents': council_decision.participating_agents,
                    'action': council_decision.aggregated_recommendation.action,
                    'reasoning': council_decision.aggregated_recommendation.reasoning,
                    'conflictDetected': council_decision.conflict_detected,
                    'resolutionMethod': council_decision.resolution_method
                }
            )
            
            # Store escalation
            self._store_escalation(escalation)
            
            # Send notification
            self._send_notification(escalation)
            
            return escalation
        
        return None
    
    def _determine_priority(self, confidence: float) -> EscalationPriority:
        """
        Determine escalation priority based on confidence level
        
        Args:
            confidence: Confidence level
            
        Returns:
            EscalationPriority
        """
        if confidence < 0.3:
            return EscalationPriority.CRITICAL
        elif confidence < 0.5:
            return EscalationPriority.HIGH
        elif confidence < 0.7:
            return EscalationPriority.MEDIUM
        else:
            return EscalationPriority.LOW
    
    def _store_escalation(self, escalation: EscalationRequest) -> Dict[str, Any]:
        """
        Store escalation request in DynamoDB
        
        Args:
            escalation: Escalation request to store
            
        Returns:
            Response from DynamoDB
        """
        try:
            response = self.table.put_item(Item=escalation.to_dict())
            return response
        except Exception as e:
            raise EscalationError(f"Failed to store escalation: {str(e)}")
    
    def _send_notification(self, escalation: EscalationRequest):
        """
        Send notification about escalation via SNS
        
        Args:
            escalation: Escalation request to notify about
        """
        if not self.sns or not self.sns_topic_arn:
            return
        
        try:
            message = f"""
Escalation Required - Priority: {escalation.priority.value.upper()}

Decision ID: {escalation.decision_id}
Decision Type: {escalation.decision_type}
Confidence: {escalation.confidence:.2f}
Reason: {escalation.reason}

Please review this decision in the RetailMind AI dashboard.
            """.strip()
            
            self.sns.publish(
                TopicArn=self.sns_topic_arn,
                Subject=f"RetailMind AI Escalation - {escalation.priority.value.upper()}",
                Message=message
            )
        except Exception as e:
            # Log error but don't fail the escalation
            print(f"Failed to send notification: {str(e)}")
    
    def get_escalation(self, escalation_id: str) -> Optional[EscalationRequest]:
        """
        Get escalation by ID
        
        Args:
            escalation_id: ID of the escalation
            
        Returns:
            EscalationRequest if found, None otherwise
        """
        try:
            response = self.table.get_item(Key={'escalationId': escalation_id})
            if 'Item' in response:
                item = response['Item']
                return EscalationRequest(
                    escalation_id=item['escalationId'],
                    timestamp=datetime.fromisoformat(item['timestamp']),
                    priority=EscalationPriority(item['priority']),
                    status=EscalationStatus(item['status']),
                    decision_id=item['decisionId'],
                    decision_type=item['decisionType'],
                    confidence=item['confidence'],
                    reason=item['reason'],
                    context=item['context'],
                    assigned_to=item.get('assignedTo'),
                    resolved_at=datetime.fromisoformat(item['resolvedAt']) if item.get('resolvedAt') else None,
                    resolution_notes=item.get('resolutionNotes')
                )
            return None
        except Exception as e:
            raise EscalationError(f"Failed to get escalation: {str(e)}")
    
    def update_escalation_status(
        self,
        escalation_id: str,
        status: EscalationStatus,
        assigned_to: Optional[str] = None,
        resolution_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update the status of an escalation
        
        Args:
            escalation_id: ID of the escalation
            status: New status
            assigned_to: Optional user assigned to the escalation
            resolution_notes: Optional resolution notes
            
        Returns:
            Response from DynamoDB
        """
        try:
            update_expr = "SET #status = :status"
            expr_attr_names = {'#status': 'status'}
            expr_attr_values = {':status': status.value}
            
            if assigned_to:
                update_expr += ", assignedTo = :assigned_to"
                expr_attr_values[':assigned_to'] = assigned_to
            
            if status == EscalationStatus.RESOLVED:
                update_expr += ", resolvedAt = :resolved_at"
                expr_attr_values[':resolved_at'] = datetime.utcnow().isoformat()
            
            if resolution_notes:
                update_expr += ", resolutionNotes = :notes"
                expr_attr_values[':notes'] = resolution_notes
            
            response = self.table.update_item(
                Key={'escalationId': escalation_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_attr_names,
                ExpressionAttributeValues=expr_attr_values
            )
            return response
        except Exception as e:
            raise EscalationError(f"Failed to update escalation status: {str(e)}")
    
    def list_pending_escalations(self) -> list[EscalationRequest]:
        """
        List all pending escalations
        
        Returns:
            List of pending EscalationRequest objects
        """
        try:
            response = self.table.scan(
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': EscalationStatus.PENDING.value}
            )
            
            escalations = []
            for item in response.get('Items', []):
                escalations.append(EscalationRequest(
                    escalation_id=item['escalationId'],
                    timestamp=datetime.fromisoformat(item['timestamp']),
                    priority=EscalationPriority(item['priority']),
                    status=EscalationStatus(item['status']),
                    decision_id=item['decisionId'],
                    decision_type=item['decisionType'],
                    confidence=item['confidence'],
                    reason=item['reason'],
                    context=item['context'],
                    assigned_to=item.get('assignedTo'),
                    resolved_at=datetime.fromisoformat(item['resolvedAt']) if item.get('resolvedAt') else None,
                    resolution_notes=item.get('resolutionNotes')
                ))
            
            return escalations
        except Exception as e:
            raise EscalationError(f"Failed to list pending escalations: {str(e)}")


class EscalationError(Exception):
    """Exception raised for escalation errors"""
    pass
