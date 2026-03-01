"""
Property-based tests for escalation and audit

**Feature: retailmind-ai, Property 12: Escalation and Audit Consistency**
**Validates: Requirements 6.4, 6.5, 10.1, 10.2, 10.4**
"""
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime, timezone
from typing import Any, List
from unittest.mock import Mock, MagicMock, patch

from src.models.agent_decision import AgentDecision, Recommendation
from src.services.ai_council import AICouncil, CouncilDecision
from src.services.escalation import (
    EscalationService,
    EscalationRequest,
    EscalationPriority,
    EscalationStatus
)
from src.services.audit import AuditService, AuditEntry, AuditEventType
from src.agents.base_agent import BaseAgent


# Mock agent for testing
class MockAgent(BaseAgent):
    """Mock agent for testing purposes"""
    
    def __init__(self, agent_id: str, decision_action: str, decision_confidence: float):
        super().__init__(agent_id, "test_agent")
        self.decision_action = decision_action
        self.decision_confidence = decision_confidence
    
    def get_capabilities(self) -> list[str]:
        return ["test_capability"]
    
    def process(self, input_data: Any) -> AgentDecision:
        return self.create_decision(
            input_data=input_data,
            action=self.decision_action,
            confidence=self.decision_confidence,
            reasoning=f"Mock decision from {self.metadata.agent_id}"
        )


# Custom strategies
@st.composite
def recommendation_strategy(draw):
    """Generate random Recommendation instances"""
    action = draw(st.text(min_size=1, max_size=20))
    confidence = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    reasoning = draw(st.text(min_size=1, max_size=100))
    supporting_data = draw(st.lists(st.integers(), max_size=5))
    return Recommendation(action, confidence, reasoning, supporting_data)


@st.composite
def agent_decision_strategy(draw):
    """Generate random AgentDecision instances"""
    agent_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=97, max_codepoint=122)))
    decision_id = draw(st.text(min_size=1, max_size=20))
    naive_timestamp = draw(st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2030, 12, 31)
    ))
    timestamp = naive_timestamp.replace(tzinfo=timezone.utc)
    input_data = draw(st.one_of(st.none(), st.integers(), st.text(max_size=20)))
    recommendation = draw(recommendation_strategy())
    escalation_required = draw(st.booleans())
    
    return AgentDecision(
        agent_id=agent_id,
        decision_id=decision_id,
        timestamp=timestamp,
        input_data=input_data,
        recommendation=recommendation,
        escalation_required=escalation_required
    )


# Property-based tests
@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    decision=agent_decision_strategy(),
    confidence_threshold=st.floats(min_value=0.5, max_value=0.95, allow_nan=False, allow_infinity=False)
)
def test_escalation_triggered_for_low_confidence(decision: AgentDecision, confidence_threshold: float):
    """
    Property: For any decision with confidence below threshold, escalation should be created
    
    **Feature: retailmind-ai, Property 12: Escalation and Audit Consistency**
    **Validates: Requirements 6.4, 10.1**
    """
    # Mock DynamoDB table
    with patch('src.utils.aws_clients.aws_clients') as mock_aws:
        mock_table = MagicMock()
        mock_aws.dynamodb_resource.Table.return_value = mock_table
        
        service = EscalationService()
        
        # Check escalation
        escalation = service.check_and_escalate_agent_decision(decision, confidence_threshold)
        
        # If confidence is below threshold or escalation is explicitly required, escalation should be created
        if decision.recommendation.confidence < confidence_threshold or decision.escalation_required:
            assert escalation is not None
            assert isinstance(escalation, EscalationRequest)
            assert escalation.decision_id == decision.decision_id
            assert escalation.confidence == decision.recommendation.confidence
            assert escalation.status == EscalationStatus.PENDING
            # Verify it was stored
            assert mock_table.put_item.called
        else:
            assert escalation is None


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
)
def test_escalation_priority_matches_confidence(confidence: float):
    """
    Property: For any confidence level, escalation priority should be appropriately assigned
    
    **Feature: retailmind-ai, Property 12: Escalation and Audit Consistency**
    **Validates: Requirements 6.4, 10.1**
    """
    with patch('src.utils.aws_clients.aws_clients') as mock_aws:
        mock_table = MagicMock()
        mock_aws.dynamodb_resource.Table.return_value = mock_table
        
        service = EscalationService()
        priority = service._determine_priority(confidence)
        
        # Verify priority matches confidence level
        if confidence < 0.3:
            assert priority == EscalationPriority.CRITICAL
        elif confidence < 0.5:
            assert priority == EscalationPriority.HIGH
        elif confidence < 0.7:
            assert priority == EscalationPriority.MEDIUM
        else:
            assert priority == EscalationPriority.LOW


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(decision=agent_decision_strategy())
def test_audit_entry_created_for_agent_decision(decision: AgentDecision):
    """
    Property: For any agent decision, an audit entry should be created with all required fields
    
    **Feature: retailmind-ai, Property 12: Escalation and Audit Consistency**
    **Validates: Requirements 6.5, 10.2**
    """
    with patch('src.utils.aws_clients.aws_clients') as mock_aws:
        mock_table = MagicMock()
        mock_aws.dynamodb_resource.Table.return_value = mock_table
        
        service = AuditService()
        
        # Log decision
        audit_entry = service.log_agent_decision(decision)
        
        # Verify audit entry has all required fields
        assert audit_entry is not None
        assert isinstance(audit_entry, AuditEntry)
        assert audit_entry.audit_id is not None
        assert audit_entry.timestamp is not None
        assert audit_entry.event_type == AuditEventType.AGENT_DECISION
        assert audit_entry.actor_id == decision.agent_id
        assert audit_entry.actor_type == 'agent'
        assert audit_entry.action == decision.recommendation.action
        assert audit_entry.resource_id == decision.decision_id
        assert audit_entry.resource_type == 'agent_decision'
        assert audit_entry.reasoning == decision.recommendation.reasoning
        
        # Verify it was stored
        assert mock_table.put_item.called


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    num_agents=st.integers(min_value=2, max_value=5),
    action=st.text(min_size=1, max_size=20),
    confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    input_data=st.one_of(st.none(), st.integers(), st.text(max_size=20))
)
def test_audit_entry_created_for_council_decision(num_agents: int, action: str, confidence: float, input_data: Any):
    """
    Property: For any council decision, an audit entry should be created with all participating agents
    
    **Feature: retailmind-ai, Property 12: Escalation and Audit Consistency**
    **Validates: Requirements 6.5, 10.2**
    """
    # Create mock agents
    agents = []
    for i in range(num_agents):
        agent = MockAgent(f"agent_{i}", action, confidence)
        agents.append(agent)
    
    with patch('src.utils.aws_clients.aws_clients') as mock_aws:
        mock_table = MagicMock()
        mock_aws.dynamodb_resource.Table.return_value = mock_table
        
        # Create council decision
        council = AICouncil()
        council_decision = council.coordinate_decision(agents, input_data)
        
        # Log decision
        audit_service = AuditService()
        audit_entry = audit_service.log_council_decision(council_decision)
        
        # Verify audit entry
        assert audit_entry is not None
        assert audit_entry.event_type == AuditEventType.COUNCIL_DECISION
        assert audit_entry.actor_id == 'ai_council'
        assert audit_entry.actor_type == 'system'
        assert audit_entry.resource_id == council_decision.decision_id
        
        # Verify all participating agents are recorded
        assert 'participatingAgents' in audit_entry.details
        assert len(audit_entry.details['participatingAgents']) == num_agents
        
        # Verify it was stored
        assert mock_table.put_item.called


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(decision=agent_decision_strategy())
def test_audit_entry_serializable(decision: AgentDecision):
    """
    Property: For any audit entry, it should be serializable to dictionary for storage
    
    **Feature: retailmind-ai, Property 12: Escalation and Audit Consistency**
    **Validates: Requirements 10.2, 10.4**
    """
    with patch('src.utils.aws_clients.aws_clients') as mock_aws:
        mock_table = MagicMock()
        mock_aws.dynamodb_resource.Table.return_value = mock_table
        
        service = AuditService()
        audit_entry = service.log_agent_decision(decision)
        
        # Serialize to dict
        audit_dict = audit_entry.to_dict()
        
        # Verify all required fields are present
        assert isinstance(audit_dict, dict)
        assert 'auditId' in audit_dict
        assert 'timestamp' in audit_dict
        assert 'eventType' in audit_dict
        assert 'actorId' in audit_dict
        assert 'actorType' in audit_dict
        assert 'action' in audit_dict
        assert 'resourceId' in audit_dict
        assert 'resourceType' in audit_dict
        assert 'details' in audit_dict
        assert 'dataSources' in audit_dict
        assert 'reasoning' in audit_dict
        assert 'outcome' in audit_dict


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    decision=agent_decision_strategy(),
    confidence_threshold=st.floats(min_value=0.5, max_value=0.95, allow_nan=False, allow_infinity=False)
)
def test_escalation_and_audit_consistency(decision: AgentDecision, confidence_threshold: float):
    """
    Property: For any decision requiring escalation, both escalation and audit entries should be created
    
    **Feature: retailmind-ai, Property 12: Escalation and Audit Consistency**
    **Validates: Requirements 6.4, 6.5, 10.1, 10.2, 10.4**
    """
    with patch('src.utils.aws_clients.aws_clients') as mock_aws:
        
        mock_esc_table = MagicMock()
        mock_audit_table = MagicMock()
        
        # Configure mock to return different tables for different calls
        def get_table(name):
            if 'escalation' in name:
                return mock_esc_table
            else:
                return mock_audit_table
        
        mock_aws.dynamodb_resource.Table.side_effect = get_table
        
        escalation_service = EscalationService()
        audit_service = AuditService()
        
        # Check escalation
        escalation = escalation_service.check_and_escalate_agent_decision(decision, confidence_threshold)
        
        # Log to audit
        audit_entry = audit_service.log_agent_decision(decision)
        
        # If escalation was created, verify consistency
        if escalation is not None:
            assert audit_entry is not None
            assert escalation.decision_id == audit_entry.resource_id
            assert escalation.confidence == decision.recommendation.confidence
            
            # Both should be stored
            assert mock_esc_table.put_item.called
            assert mock_audit_table.put_item.called


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    workflow_id=st.text(min_size=1, max_size=20),
    instance_id=st.text(min_size=1, max_size=20),
    action=st.text(min_size=1, max_size=20)
)
def test_workflow_modifications_audited(workflow_id: str, instance_id: str, action: str):
    """
    Property: For any workflow modification, an audit entry should be created
    
    **Feature: retailmind-ai, Property 12: Escalation and Audit Consistency**
    **Validates: Requirements 10.2, 10.4**
    """
    with patch('src.utils.aws_clients.aws_clients') as mock_aws:
        mock_table = MagicMock()
        mock_aws.dynamodb_resource.Table.return_value = mock_table
        
        service = AuditService()
        
        # Log workflow modification
        audit_entry = service.log_workflow_modification(
            workflow_id=workflow_id,
            modified_by="test_agent",
            modification_type="update",
            details={'action': action}
        )
        
        # Verify audit entry
        assert audit_entry is not None
        assert audit_entry.event_type == AuditEventType.WORKFLOW_MODIFICATION
        assert audit_entry.resource_id == workflow_id
        assert audit_entry.resource_type == 'workflow'
        
        # Verify it was stored
        assert mock_table.put_item.called


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(decision=agent_decision_strategy())
def test_audit_trail_maintains_data_sources(decision: AgentDecision):
    """
    Property: For any decision, audit trail should maintain references to data sources
    
    **Feature: retailmind-ai, Property 12: Escalation and Audit Consistency**
    **Validates: Requirements 10.2, 10.3**
    """
    with patch('src.utils.aws_clients.aws_clients') as mock_aws:
        mock_table = MagicMock()
        mock_aws.dynamodb_resource.Table.return_value = mock_table
        
        service = AuditService()
        audit_entry = service.log_agent_decision(decision)
        
        # Verify data sources are tracked
        assert 'dataSources' in audit_entry.to_dict()
        assert isinstance(audit_entry.data_sources, list)
