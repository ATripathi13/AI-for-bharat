"""
Property-based tests for data model serialization

**Feature: retailmind-ai, Property 15: Data Persistence and Ingestion**
**Validates: Requirements 1.5, 8.1**
"""
import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timezone
from typing import Any

from src.models.agent_decision import AgentDecision, Recommendation
from src.models.workflow_instance import (
    WorkflowInstance, WorkflowStep, WorkflowPerformance,
    WorkflowStatus, WorkflowStepType
)
from src.models.business_intelligence import (
    BusinessIntelligence, Insights, ActionRecommendation,
    EntityType, Priority
)


# Custom strategies for generating test data
@st.composite
def recommendation_strategy(draw):
    """Generate random Recommendation instances"""
    action = draw(st.text(min_size=1, max_size=100))
    confidence = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    reasoning = draw(st.text(min_size=1, max_size=500))
    supporting_data = draw(st.lists(
        st.one_of(
            st.none(),
            st.booleans(),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.text(),
            st.dictionaries(st.text(min_size=1, max_size=20), st.integers())
        ),
        max_size=10
    ))
    return Recommendation(
        action=action,
        confidence=confidence,
        reasoning=reasoning,
        supporting_data=supporting_data
    )


@st.composite
def agent_decision_strategy(draw):
    """Generate random AgentDecision instances"""
    agent_id = draw(st.text(min_size=1, max_size=50))
    decision_id = draw(st.text(min_size=1, max_size=50))
    # Generate naive datetime and add UTC timezone
    naive_timestamp = draw(st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2030, 12, 31)
    ))
    timestamp = naive_timestamp.replace(tzinfo=timezone.utc)
    input_data = draw(st.one_of(
        st.none(),
        st.booleans(),
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.text(),
        st.dictionaries(st.text(min_size=1, max_size=20), st.integers(), max_size=10)
    ))
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


@st.composite
def workflow_step_strategy(draw):
    """Generate random WorkflowStep instances"""
    step_id = draw(st.text(min_size=1, max_size=50))
    step_type = draw(st.sampled_from(list(WorkflowStepType)))
    configuration = draw(st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.one_of(st.integers(), st.text(), st.booleans()),
        max_size=10
    ))
    conditions = draw(st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.one_of(st.integers(), st.text(), st.booleans()),
        max_size=10
    ))
    
    return WorkflowStep(
        step_id=step_id,
        type=step_type,
        configuration=configuration,
        conditions=conditions
    )


@st.composite
def workflow_performance_strategy(draw):
    """Generate random WorkflowPerformance instances"""
    execution_time = draw(st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
    success_rate = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    business_impact = draw(st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False))
    
    return WorkflowPerformance(
        execution_time=execution_time,
        success_rate=success_rate,
        business_impact=business_impact
    )


@st.composite
def workflow_instance_strategy(draw):
    """Generate random WorkflowInstance instances"""
    workflow_id = draw(st.text(min_size=1, max_size=50))
    instance_id = draw(st.text(min_size=1, max_size=50))
    status = draw(st.sampled_from(list(WorkflowStatus)))
    steps = draw(st.lists(workflow_step_strategy(), min_size=0, max_size=10))
    created_by = draw(st.sampled_from(['system', 'human']))
    generated_by = draw(st.text(min_size=1, max_size=50))
    performance = draw(workflow_performance_strategy())
    
    return WorkflowInstance(
        workflow_id=workflow_id,
        instance_id=instance_id,
        status=status,
        steps=steps,
        created_by=created_by,
        generated_by=generated_by,
        performance=performance
    )


@st.composite
def insights_strategy(draw):
    """Generate random Insights instances"""
    trend = draw(st.text(min_size=1, max_size=100))
    prediction = draw(st.one_of(
        st.none(),
        st.booleans(),
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.text(),
        st.dictionaries(st.text(min_size=1, max_size=20), st.integers(), max_size=10)
    ))
    confidence = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    timeframe = draw(st.text(min_size=1, max_size=50))
    
    return Insights(
        trend=trend,
        prediction=prediction,
        confidence=confidence,
        timeframe=timeframe
    )


@st.composite
def action_recommendation_strategy(draw):
    """Generate random ActionRecommendation instances"""
    action = draw(st.text(min_size=1, max_size=100))
    priority = draw(st.sampled_from(list(Priority)))
    expected_impact = draw(st.text(min_size=1, max_size=200))
    
    return ActionRecommendation(
        action=action,
        priority=priority,
        expected_impact=expected_impact
    )


@st.composite
def business_intelligence_strategy(draw):
    """Generate random BusinessIntelligence instances"""
    entity_type = draw(st.sampled_from(list(EntityType)))
    entity_id = draw(st.text(min_size=1, max_size=50))
    insights = draw(insights_strategy())
    recommendations = draw(st.lists(action_recommendation_strategy(), min_size=0, max_size=10))
    data_source = draw(st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10))
    
    return BusinessIntelligence(
        entity_type=entity_type,
        entity_id=entity_id,
        insights=insights,
        recommendations=recommendations,
        data_source=data_source
    )


# Property-based tests
@pytest.mark.property
@settings(max_examples=100)
@given(recommendation_strategy())
def test_recommendation_serialization_round_trip(recommendation: Recommendation):
    """
    Property: For any Recommendation, serializing then deserializing should produce an equivalent object
    
    **Feature: retailmind-ai, Property 15: Data Persistence and Ingestion**
    **Validates: Requirements 1.5, 8.1**
    """
    # Serialize to dict
    serialized = recommendation.to_dict()
    
    # Deserialize back to object
    deserialized = Recommendation.from_dict(serialized)
    
    # Verify round-trip preserves all fields
    assert deserialized.action == recommendation.action
    assert deserialized.confidence == recommendation.confidence
    assert deserialized.reasoning == recommendation.reasoning
    assert deserialized.supporting_data == recommendation.supporting_data


@pytest.mark.property
@settings(max_examples=100)
@given(agent_decision_strategy())
def test_agent_decision_serialization_round_trip(decision: AgentDecision):
    """
    Property: For any AgentDecision, serializing then deserializing should produce an equivalent object
    
    **Feature: retailmind-ai, Property 15: Data Persistence and Ingestion**
    **Validates: Requirements 1.5, 8.1**
    """
    # Serialize to dict
    serialized = decision.to_dict()
    
    # Deserialize back to object
    deserialized = AgentDecision.from_dict(serialized)
    
    # Verify round-trip preserves all fields
    assert deserialized.agent_id == decision.agent_id
    assert deserialized.decision_id == decision.decision_id
    assert deserialized.timestamp == decision.timestamp
    assert deserialized.input_data == decision.input_data
    assert deserialized.escalation_required == decision.escalation_required
    
    # Verify nested recommendation
    assert deserialized.recommendation.action == decision.recommendation.action
    assert deserialized.recommendation.confidence == decision.recommendation.confidence
    assert deserialized.recommendation.reasoning == decision.recommendation.reasoning
    assert deserialized.recommendation.supporting_data == decision.recommendation.supporting_data


@pytest.mark.property
@settings(max_examples=100)
@given(workflow_step_strategy())
def test_workflow_step_serialization_round_trip(step: WorkflowStep):
    """
    Property: For any WorkflowStep, serializing then deserializing should produce an equivalent object
    
    **Feature: retailmind-ai, Property 15: Data Persistence and Ingestion**
    **Validates: Requirements 1.5, 8.1**
    """
    # Serialize to dict
    serialized = step.to_dict()
    
    # Deserialize back to object
    deserialized = WorkflowStep.from_dict(serialized)
    
    # Verify round-trip preserves all fields
    assert deserialized.step_id == step.step_id
    assert deserialized.type == step.type
    assert deserialized.configuration == step.configuration
    assert deserialized.conditions == step.conditions


@pytest.mark.property
@settings(max_examples=100)
@given(workflow_performance_strategy())
def test_workflow_performance_serialization_round_trip(performance: WorkflowPerformance):
    """
    Property: For any WorkflowPerformance, serializing then deserializing should produce an equivalent object
    
    **Feature: retailmind-ai, Property 15: Data Persistence and Ingestion**
    **Validates: Requirements 1.5, 8.1**
    """
    # Serialize to dict
    serialized = performance.to_dict()
    
    # Deserialize back to object
    deserialized = WorkflowPerformance.from_dict(serialized)
    
    # Verify round-trip preserves all fields
    assert deserialized.execution_time == performance.execution_time
    assert deserialized.success_rate == performance.success_rate
    assert deserialized.business_impact == performance.business_impact


@pytest.mark.property
@settings(max_examples=100)
@given(workflow_instance_strategy())
def test_workflow_instance_serialization_round_trip(workflow: WorkflowInstance):
    """
    Property: For any WorkflowInstance, serializing then deserializing should produce an equivalent object
    
    **Feature: retailmind-ai, Property 15: Data Persistence and Ingestion**
    **Validates: Requirements 1.5, 8.1**
    """
    # Serialize to dict
    serialized = workflow.to_dict()
    
    # Deserialize back to object
    deserialized = WorkflowInstance.from_dict(serialized)
    
    # Verify round-trip preserves all fields
    assert deserialized.workflow_id == workflow.workflow_id
    assert deserialized.instance_id == workflow.instance_id
    assert deserialized.status == workflow.status
    assert deserialized.created_by == workflow.created_by
    assert deserialized.generated_by == workflow.generated_by
    
    # Verify nested steps
    assert len(deserialized.steps) == len(workflow.steps)
    for orig_step, deser_step in zip(workflow.steps, deserialized.steps):
        assert deser_step.step_id == orig_step.step_id
        assert deser_step.type == orig_step.type
        assert deser_step.configuration == orig_step.configuration
        assert deser_step.conditions == orig_step.conditions
    
    # Verify nested performance
    assert deserialized.performance.execution_time == workflow.performance.execution_time
    assert deserialized.performance.success_rate == workflow.performance.success_rate
    assert deserialized.performance.business_impact == workflow.performance.business_impact


@pytest.mark.property
@settings(max_examples=100)
@given(insights_strategy())
def test_insights_serialization_round_trip(insights: Insights):
    """
    Property: For any Insights, serializing then deserializing should produce an equivalent object
    
    **Feature: retailmind-ai, Property 15: Data Persistence and Ingestion**
    **Validates: Requirements 1.5, 8.1**
    """
    # Serialize to dict
    serialized = insights.to_dict()
    
    # Deserialize back to object
    deserialized = Insights.from_dict(serialized)
    
    # Verify round-trip preserves all fields
    assert deserialized.trend == insights.trend
    assert deserialized.prediction == insights.prediction
    assert deserialized.confidence == insights.confidence
    assert deserialized.timeframe == insights.timeframe


@pytest.mark.property
@settings(max_examples=100)
@given(action_recommendation_strategy())
def test_action_recommendation_serialization_round_trip(recommendation: ActionRecommendation):
    """
    Property: For any ActionRecommendation, serializing then deserializing should produce an equivalent object
    
    **Feature: retailmind-ai, Property 15: Data Persistence and Ingestion**
    **Validates: Requirements 1.5, 8.1**
    """
    # Serialize to dict
    serialized = recommendation.to_dict()
    
    # Deserialize back to object
    deserialized = ActionRecommendation.from_dict(serialized)
    
    # Verify round-trip preserves all fields
    assert deserialized.action == recommendation.action
    assert deserialized.priority == recommendation.priority
    assert deserialized.expected_impact == recommendation.expected_impact


@pytest.mark.property
@settings(max_examples=100)
@given(business_intelligence_strategy())
def test_business_intelligence_serialization_round_trip(bi: BusinessIntelligence):
    """
    Property: For any BusinessIntelligence, serializing then deserializing should produce an equivalent object
    
    **Feature: retailmind-ai, Property 15: Data Persistence and Ingestion**
    **Validates: Requirements 1.5, 8.1**
    """
    # Serialize to dict
    serialized = bi.to_dict()
    
    # Deserialize back to object
    deserialized = BusinessIntelligence.from_dict(serialized)
    
    # Verify round-trip preserves all fields
    assert deserialized.entity_type == bi.entity_type
    assert deserialized.entity_id == bi.entity_id
    assert deserialized.data_source == bi.data_source
    
    # Verify nested insights
    assert deserialized.insights.trend == bi.insights.trend
    assert deserialized.insights.prediction == bi.insights.prediction
    assert deserialized.insights.confidence == bi.insights.confidence
    assert deserialized.insights.timeframe == bi.insights.timeframe
    
    # Verify nested recommendations
    assert len(deserialized.recommendations) == len(bi.recommendations)
    for orig_rec, deser_rec in zip(bi.recommendations, deserialized.recommendations):
        assert deser_rec.action == orig_rec.action
        assert deser_rec.priority == orig_rec.priority
        assert deser_rec.expected_impact == orig_rec.expected_impact
