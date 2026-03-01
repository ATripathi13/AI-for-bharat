"""
Property-based tests for agent coordination

**Feature: retailmind-ai, Property 8: Agent Coordination Protocol**
**Validates: Requirements 6.1, 6.2, 6.3, 8.2, 8.3**
"""
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime, timezone
from typing import Any, List

from src.agents.base_agent import BaseAgent, AgentMetadata
from src.models.agent_decision import AgentDecision, Recommendation
from src.services.ai_council import AICouncil, CouncilDecision


# Mock agent for testing
class MockAgent(BaseAgent):
    """Mock agent for testing purposes"""
    
    def __init__(self, agent_id: str, agent_type: str, decision_action: str, decision_confidence: float):
        super().__init__(agent_id, agent_type)
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


# Custom strategies for generating test data
@st.composite
def mock_agent_strategy(draw):
    """Generate random MockAgent instances"""
    agent_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=97, max_codepoint=122)))
    agent_type = draw(st.sampled_from(['market_intelligence', 'demand_forecast', 'pricing', 'inventory', 'risk']))
    action = draw(st.text(min_size=1, max_size=20))
    confidence = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    
    return MockAgent(agent_id, agent_type, action, confidence)


@st.composite
def agent_list_strategy(draw, min_agents=2, max_agents=5):
    """Generate a list of unique mock agents"""
    num_agents = draw(st.integers(min_value=min_agents, max_value=max_agents))
    agents = []
    used_ids = set()
    
    for i in range(num_agents):
        agent = draw(mock_agent_strategy())
        # Ensure unique agent IDs
        while agent.metadata.agent_id in used_ids:
            agent = draw(mock_agent_strategy())
        used_ids.add(agent.metadata.agent_id)
        agents.append(agent)
    
    return agents


@st.composite
def agent_weights_strategy(draw, agent_ids: List[str]):
    """Generate agent weights for given agent IDs"""
    weights = {}
    for agent_id in agent_ids:
        weight = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
        weights[agent_id] = weight
    return weights


# Property-based tests
@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example], deadline=None)
@given(
    agents=agent_list_strategy(min_agents=2, max_agents=5),
    input_data=st.one_of(st.none(), st.integers(), st.text(max_size=20))
)
def test_council_coordinates_all_agents(agents: List[MockAgent], input_data: Any):
    """
    Property: For any list of agents, the AI Council should coordinate all agents and collect their decisions
    
    **Feature: retailmind-ai, Property 8: Agent Coordination Protocol**
    **Validates: Requirements 6.1, 6.2, 8.2, 8.3**
    """
    council = AICouncil()
    
    # Coordinate decision
    council_decision = council.coordinate_decision(agents, input_data)
    
    # Verify all agents participated
    assert len(council_decision.participating_agents) == len(agents)
    assert len(council_decision.agent_decisions) == len(agents)
    
    # Verify each agent's decision is included
    agent_ids = {agent.metadata.agent_id for agent in agents}
    participating_ids = set(council_decision.participating_agents)
    assert agent_ids == participating_ids


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example], deadline=None)
@given(
    agents=agent_list_strategy(min_agents=2, max_agents=5),
    input_data=st.one_of(st.none(), st.integers(), st.text(max_size=20))
)
def test_council_produces_aggregated_recommendation(agents: List[MockAgent], input_data: Any):
    """
    Property: For any multi-agent decision, the Council should produce an aggregated recommendation
    
    **Feature: retailmind-ai, Property 8: Agent Coordination Protocol**
    **Validates: Requirements 6.1, 6.2, 8.3**
    """
    council = AICouncil()
    
    # Coordinate decision
    council_decision = council.coordinate_decision(agents, input_data)
    
    # Verify aggregated recommendation exists
    assert council_decision.aggregated_recommendation is not None
    assert isinstance(council_decision.aggregated_recommendation, Recommendation)
    assert council_decision.aggregated_recommendation.action is not None
    assert 0.0 <= council_decision.aggregated_recommendation.confidence <= 1.0
    assert council_decision.aggregated_recommendation.reasoning is not None


@pytest.mark.property
@settings(max_examples=100, deadline=None)
@given(
    num_agents=st.integers(min_value=2, max_value=5),
    action=st.text(min_size=1, max_size=20),
    confidences=st.lists(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False), min_size=2, max_size=5),
    input_data=st.one_of(st.none(), st.integers(), st.text(max_size=20))
)
def test_consensus_decisions_not_marked_as_conflict(num_agents: int, action: str, confidences: List[float], input_data: Any):
    """
    Property: For any set of agents with the same action, the Council should not detect a conflict
    
    **Feature: retailmind-ai, Property 8: Agent Coordination Protocol**
    **Validates: Requirements 6.3**
    """
    # Ensure we have the right number of confidences
    assume(len(confidences) >= num_agents)
    confidences = confidences[:num_agents]
    
    # Create agents with same action but different confidences
    agents = []
    for i in range(num_agents):
        agent = MockAgent(
            agent_id=f"agent_{i}",
            agent_type="test",
            decision_action=action,
            decision_confidence=confidences[i]
        )
        agents.append(agent)
    
    council = AICouncil()
    
    # Coordinate decision
    council_decision = council.coordinate_decision(agents, input_data)
    
    # If confidence variance is small, should not be marked as conflict
    confidence_variance = max(confidences) - min(confidences)
    if confidence_variance <= 0.3:
        assert not council_decision.conflict_detected
        assert council_decision.resolution_method == "consensus"


@pytest.mark.property
@settings(max_examples=100, deadline=None)
@given(
    num_agents=st.integers(min_value=2, max_value=5),
    actions=st.lists(st.text(min_size=1, max_size=20), min_size=2, max_size=5, unique=True),
    confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    input_data=st.one_of(st.none(), st.integers(), st.text(max_size=20))
)
def test_conflicting_actions_detected_and_resolved(num_agents: int, actions: List[str], confidence: float, input_data: Any):
    """
    Property: For any set of agents with different actions, the Council should detect conflict and resolve it
    
    **Feature: retailmind-ai, Property 8: Agent Coordination Protocol**
    **Validates: Requirements 6.3**
    """
    # Ensure we have enough unique actions
    assume(len(actions) >= 2)
    assume(num_agents >= 2)
    
    # Create agents with different actions
    agents = []
    for i in range(num_agents):
        action = actions[i % len(actions)]
        agent = MockAgent(
            agent_id=f"agent_{i}",
            agent_type="test",
            decision_action=action,
            decision_confidence=confidence
        )
        agents.append(agent)
    
    council = AICouncil()
    
    # Coordinate decision
    council_decision = council.coordinate_decision(agents, input_data)
    
    # Should detect conflict and use weighted voting
    assert council_decision.conflict_detected
    assert council_decision.resolution_method == "weighted_voting"
    
    # Should still produce a valid recommendation
    assert council_decision.aggregated_recommendation is not None
    assert council_decision.aggregated_recommendation.action in actions


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example], deadline=None)
@given(
    agents=agent_list_strategy(min_agents=2, max_agents=5),
    confidence_threshold=st.floats(min_value=0.5, max_value=0.95, allow_nan=False, allow_infinity=False),
    input_data=st.one_of(st.none(), st.integers(), st.text(max_size=20))
)
def test_escalation_triggered_below_threshold(agents: List[MockAgent], confidence_threshold: float, input_data: Any):
    """
    Property: For any decision with confidence below threshold, escalation should be required
    
    **Feature: retailmind-ai, Property 8: Agent Coordination Protocol**
    **Validates: Requirements 6.4, 10.1**
    """
    council = AICouncil(confidence_threshold=confidence_threshold)
    
    # Coordinate decision
    council_decision = council.coordinate_decision(agents, input_data)
    
    # If aggregated confidence is below threshold, escalation should be required
    if council_decision.aggregated_recommendation.confidence < confidence_threshold:
        assert council_decision.escalation_required


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example], deadline=None)
@given(
    agents=agent_list_strategy(min_agents=2, max_agents=5),
    input_data=st.one_of(st.none(), st.integers(), st.text(max_size=20))
)
def test_weighted_voting_respects_agent_weights(agents: List[MockAgent], input_data: Any):
    """
    Property: For any conflicting decisions, weighted voting should respect agent weights
    
    **Feature: retailmind-ai, Property 8: Agent Coordination Protocol**
    **Validates: Requirements 6.3**
    """
    # Create agents with different actions to force conflict
    for i, agent in enumerate(agents):
        agent.decision_action = f"action_{i}"
    
    # Set up weights - give first agent very high weight
    agent_weights = {agent.metadata.agent_id: 0.1 for agent in agents}
    agent_weights[agents[0].metadata.agent_id] = 10.0
    
    council = AICouncil(agent_weights=agent_weights)
    
    # Coordinate decision
    council_decision = council.coordinate_decision(agents, input_data)
    
    # The action from the highest-weighted agent should be selected
    # (assuming all have similar confidence)
    if all(agent.decision_confidence > 0.5 for agent in agents):
        assert council_decision.aggregated_recommendation.action == agents[0].decision_action


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example], deadline=None)
@given(
    agents=agent_list_strategy(min_agents=2, max_agents=5),
    input_data=st.one_of(st.none(), st.integers(), st.text(max_size=20))
)
def test_council_decision_includes_all_metadata(agents: List[MockAgent], input_data: Any):
    """
    Property: For any council decision, all required metadata should be present
    
    **Feature: retailmind-ai, Property 8: Agent Coordination Protocol**
    **Validates: Requirements 6.5, 10.2**
    """
    council = AICouncil()
    
    # Coordinate decision
    council_decision = council.coordinate_decision(agents, input_data)
    
    # Verify all metadata fields are present
    assert council_decision.decision_id is not None
    assert council_decision.timestamp is not None
    assert isinstance(council_decision.timestamp, datetime)
    assert council_decision.participating_agents is not None
    assert council_decision.agent_decisions is not None
    assert council_decision.aggregated_recommendation is not None
    assert isinstance(council_decision.conflict_detected, bool)
    assert council_decision.resolution_method in ["consensus", "weighted_voting"]
    assert isinstance(council_decision.escalation_required, bool)
    
    # Verify decision can be serialized (for audit trails)
    decision_dict = council_decision.to_dict()
    assert isinstance(decision_dict, dict)
    assert 'decisionId' in decision_dict
    assert 'timestamp' in decision_dict
    assert 'participatingAgents' in decision_dict
    assert 'agentDecisions' in decision_dict
    assert 'aggregatedRecommendation' in decision_dict


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example], deadline=None)
@given(
    agents=agent_list_strategy(min_agents=2, max_agents=5),
    input_data=st.one_of(st.none(), st.integers(), st.text(max_size=20))
)
def test_agent_weights_can_be_set_and_retrieved(agents: List[MockAgent], input_data: Any):
    """
    Property: For any agent, weights can be set and retrieved correctly
    
    **Feature: retailmind-ai, Property 8: Agent Coordination Protocol**
    **Validates: Requirements 6.3**
    """
    council = AICouncil()
    
    # Generate random weights for each agent
    agent_ids = [agent.metadata.agent_id for agent in agents]
    weights = {}
    for agent_id in agent_ids:
        weight = 0.5  # Use a fixed weight for simplicity
        weights[agent_id] = weight
        council.set_agent_weight(agent_id, weight)
    
    # Verify weights can be retrieved
    for agent_id, expected_weight in weights.items():
        retrieved_weight = council.get_agent_weight(agent_id)
        assert retrieved_weight == expected_weight
    
    # Verify default weight for unknown agent
    unknown_weight = council.get_agent_weight("unknown_agent")
    assert unknown_weight == 1.0
