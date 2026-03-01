"""
AI Council Orchestrator Service for RetailMind AI
Coordinates multiple AI agents for collaborative decision-making
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from ..models.agent_decision import AgentDecision, Recommendation
from ..agents.base_agent import BaseAgent
from ..agents.communication import AgentCommunicationInterface, ACPMessage, MessageType


@dataclass
class AgentWeight:
    """Weight configuration for an agent in decision-making"""
    agent_id: str
    weight: float  # 0.0 to 1.0
    
    def __post_init__(self):
        """Validate weight is in valid range"""
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"Weight must be between 0.0 and 1.0, got {self.weight}")


@dataclass
class CouncilDecision:
    """Aggregated decision from the AI Council"""
    decision_id: str
    timestamp: datetime
    participating_agents: List[str]
    agent_decisions: List[AgentDecision]
    aggregated_recommendation: Recommendation
    conflict_detected: bool
    resolution_method: str
    escalation_required: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'decisionId': self.decision_id,
            'timestamp': self.timestamp.isoformat(),
            'participatingAgents': self.participating_agents,
            'agentDecisions': [d.to_dict() for d in self.agent_decisions],
            'aggregatedRecommendation': self.aggregated_recommendation.to_dict(),
            'conflictDetected': self.conflict_detected,
            'resolutionMethod': self.resolution_method,
            'escalationRequired': self.escalation_required
        }


class AICouncil:
    """
    AI Council orchestrator for multi-agent coordination
    Manages agent collaboration and decision aggregation
    """
    
    def __init__(
        self,
        agent_weights: Optional[Dict[str, float]] = None,
        confidence_threshold: float = 0.8
    ):
        """
        Initialize AI Council
        
        Args:
            agent_weights: Optional dictionary mapping agent_id to weight
            confidence_threshold: Threshold for escalation (default 0.8)
        """
        self.agent_weights = agent_weights or {}
        self.confidence_threshold = confidence_threshold
        self.communication = AgentCommunicationInterface()
    
    def coordinate_decision(
        self,
        agents: List[BaseAgent],
        input_data: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> CouncilDecision:
        """
        Coordinate multiple agents to make a collaborative decision
        
        Args:
            agents: List of agents to participate in decision
            input_data: Input data for agents to process
            context: Optional context information
            
        Returns:
            CouncilDecision with aggregated recommendation
        """
        # Collect decisions from all agents
        agent_decisions = []
        for agent in agents:
            try:
                decision = agent.process(input_data)
                agent_decisions.append(decision)
            except Exception as e:
                # Log error but continue with other agents
                print(f"Error processing with agent {agent.metadata.agent_id}: {str(e)}")
        
        if not agent_decisions:
            raise CoordinationError("No agent decisions were collected")
        
        # Detect conflicts
        conflict_detected = self._detect_conflicts(agent_decisions)
        
        # Aggregate decisions
        if conflict_detected:
            aggregated_recommendation, resolution_method = self._resolve_conflicts(
                agent_decisions
            )
        else:
            aggregated_recommendation, resolution_method = self._aggregate_decisions(
                agent_decisions
            )
        
        # Determine if escalation is required
        escalation_required = (
            aggregated_recommendation.confidence < self.confidence_threshold or
            any(d.escalation_required for d in agent_decisions)
        )
        
        return CouncilDecision(
            decision_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            participating_agents=[d.agent_id for d in agent_decisions],
            agent_decisions=agent_decisions,
            aggregated_recommendation=aggregated_recommendation,
            conflict_detected=conflict_detected,
            resolution_method=resolution_method,
            escalation_required=escalation_required
        )
    
    def _detect_conflicts(self, decisions: List[AgentDecision]) -> bool:
        """
        Detect if there are conflicts between agent decisions
        
        Args:
            decisions: List of agent decisions
            
        Returns:
            True if conflicts detected, False otherwise
        """
        if len(decisions) < 2:
            return False
        
        # Check if actions differ significantly
        actions = [d.recommendation.action for d in decisions]
        unique_actions = set(actions)
        
        # If more than one unique action, there's a conflict
        if len(unique_actions) > 1:
            return True
        
        # Check if confidence levels vary significantly
        confidences = [d.recommendation.confidence for d in decisions]
        confidence_variance = max(confidences) - min(confidences)
        
        # If variance is greater than 0.3, consider it a conflict
        return confidence_variance > 0.3
    
    def _resolve_conflicts(
        self,
        decisions: List[AgentDecision]
    ) -> tuple[Recommendation, str]:
        """
        Resolve conflicts between agent decisions using weighted voting
        
        Args:
            decisions: List of conflicting agent decisions
            
        Returns:
            Tuple of (aggregated recommendation, resolution method)
        """
        # Use weighted voting to resolve conflicts
        action_scores: Dict[str, float] = {}
        action_reasonings: Dict[str, List[str]] = {}
        action_data: Dict[str, List[Any]] = {}
        
        total_weight = 0.0
        
        for decision in decisions:
            agent_id = decision.agent_id
            action = decision.recommendation.action
            confidence = decision.recommendation.confidence
            
            # Get agent weight (default to 1.0 if not specified)
            weight = self.agent_weights.get(agent_id, 1.0)
            total_weight += weight
            
            # Calculate weighted score
            score = confidence * weight
            
            if action not in action_scores:
                action_scores[action] = 0.0
                action_reasonings[action] = []
                action_data[action] = []
            
            action_scores[action] += score
            action_reasonings[action].append(decision.recommendation.reasoning)
            action_data[action].extend(decision.recommendation.supporting_data)
        
        # Select action with highest weighted score
        best_action = max(action_scores, key=action_scores.get)
        normalized_confidence = action_scores[best_action] / total_weight if total_weight > 0 else 0.0
        
        # Combine reasonings
        combined_reasoning = f"Weighted decision from {len(decisions)} agents: " + \
                           "; ".join(action_reasonings[best_action])
        
        recommendation = Recommendation(
            action=best_action,
            confidence=normalized_confidence,
            reasoning=combined_reasoning,
            supporting_data=action_data[best_action]
        )
        
        return recommendation, "weighted_voting"
    
    def _aggregate_decisions(
        self,
        decisions: List[AgentDecision]
    ) -> tuple[Recommendation, str]:
        """
        Aggregate non-conflicting decisions
        
        Args:
            decisions: List of agent decisions
            
        Returns:
            Tuple of (aggregated recommendation, resolution method)
        """
        # Calculate weighted average confidence
        total_confidence = 0.0
        total_weight = 0.0
        all_reasonings = []
        all_supporting_data = []
        
        # Use the action from the first decision (they should all agree)
        action = decisions[0].recommendation.action
        
        for decision in decisions:
            agent_id = decision.agent_id
            weight = self.agent_weights.get(agent_id, 1.0)
            
            total_confidence += decision.recommendation.confidence * weight
            total_weight += weight
            all_reasonings.append(decision.recommendation.reasoning)
            all_supporting_data.extend(decision.recommendation.supporting_data)
        
        avg_confidence = total_confidence / total_weight if total_weight > 0 else 0.0
        combined_reasoning = f"Consensus from {len(decisions)} agents: " + \
                           "; ".join(all_reasonings)
        
        recommendation = Recommendation(
            action=action,
            confidence=avg_confidence,
            reasoning=combined_reasoning,
            supporting_data=all_supporting_data
        )
        
        return recommendation, "consensus"
    
    def broadcast_decision(
        self,
        council_decision: CouncilDecision,
        correlation_id: str
    ) -> Dict[str, Any]:
        """
        Broadcast council decision to all participating agents
        
        Args:
            council_decision: The council decision to broadcast
            correlation_id: Correlation ID for tracking
            
        Returns:
            Response from communication interface
        """
        payload = council_decision.to_dict()
        return self.communication.broadcast(
            from_agent_id="ai_council",
            payload=payload,
            correlation_id=correlation_id
        )
    
    def set_agent_weight(self, agent_id: str, weight: float):
        """
        Set the weight for an agent in decision-making
        
        Args:
            agent_id: ID of the agent
            weight: Weight value (0.0 to 1.0)
        """
        if not 0.0 <= weight <= 1.0:
            raise ValueError(f"Weight must be between 0.0 and 1.0, got {weight}")
        self.agent_weights[agent_id] = weight
    
    def get_agent_weight(self, agent_id: str) -> float:
        """
        Get the weight for an agent
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Weight value (default 1.0 if not set)
        """
        return self.agent_weights.get(agent_id, 1.0)


class CoordinationError(Exception):
    """Exception raised for coordination errors"""
    pass
