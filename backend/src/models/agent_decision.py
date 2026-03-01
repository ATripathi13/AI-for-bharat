"""
Agent Decision data model for RetailMind AI
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Dict
from enum import Enum


@dataclass
class Recommendation:
    """Recommendation from an AI agent"""
    action: str
    confidence: float
    reasoning: str
    supporting_data: List[Any] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'action': self.action,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'supportingData': self.supporting_data
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Recommendation':
        """Create from dictionary"""
        return cls(
            action=data['action'],
            confidence=data['confidence'],
            reasoning=data['reasoning'],
            supporting_data=data.get('supportingData', [])
        )


@dataclass
class AgentDecision:
    """Decision made by an AI agent"""
    agent_id: str
    decision_id: str
    timestamp: datetime
    input_data: Any
    recommendation: Recommendation
    escalation_required: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        return {
            'agentId': self.agent_id,
            'decisionId': self.decision_id,
            'timestamp': self.timestamp.isoformat(),
            'inputData': self.input_data,
            'recommendation': self.recommendation.to_dict(),
            'escalationRequired': self.escalation_required
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentDecision':
        """Create from dictionary"""
        return cls(
            agent_id=data['agentId'],
            decision_id=data['decisionId'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            input_data=data['inputData'],
            recommendation=Recommendation.from_dict(data['recommendation']),
            escalation_required=data['escalationRequired']
        )
