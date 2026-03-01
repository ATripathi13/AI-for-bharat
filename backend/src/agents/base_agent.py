"""
Base Agent class for RetailMind AI
Provides common functionality for all AI agents
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
import uuid

from ..models.agent_decision import AgentDecision, Recommendation


class AgentStatus:
    """Agent status constants"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


@dataclass
class AgentMetadata:
    """Metadata for an AI agent"""
    agent_id: str
    agent_type: str
    version: str
    capabilities: list[str]
    status: str = AgentStatus.ACTIVE
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'agentId': self.agent_id,
            'agentType': self.agent_type,
            'version': self.version,
            'capabilities': self.capabilities,
            'status': self.status
        }


class BaseAgent(ABC):
    """
    Base class for all AI agents in RetailMind AI
    Provides common functionality for agent communication and decision-making
    """
    
    def __init__(self, agent_id: str, agent_type: str, version: str = "1.0.0"):
        """
        Initialize base agent
        
        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type of agent (e.g., 'market_intelligence', 'demand_forecast')
            version: Agent version
        """
        self.metadata = AgentMetadata(
            agent_id=agent_id,
            agent_type=agent_type,
            version=version,
            capabilities=self.get_capabilities()
        )
    
    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """
        Return list of capabilities this agent provides
        
        Returns:
            List of capability strings
        """
        pass
    
    @abstractmethod
    def process(self, input_data: Any) -> AgentDecision:
        """
        Process input data and make a decision
        
        Args:
            input_data: Input data for the agent to process
            
        Returns:
            AgentDecision with recommendation
        """
        pass
    
    def create_decision(
        self,
        input_data: Any,
        action: str,
        confidence: float,
        reasoning: str,
        supporting_data: list[Any] = None,
        escalation_threshold: float = 0.8
    ) -> AgentDecision:
        """
        Create an AgentDecision with recommendation
        
        Args:
            input_data: Input data that was processed
            action: Recommended action
            confidence: Confidence level (0.0 to 1.0)
            reasoning: Explanation of the decision
            supporting_data: Supporting data for the decision
            escalation_threshold: Threshold below which escalation is required
            
        Returns:
            AgentDecision object
        """
        recommendation = Recommendation(
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            supporting_data=supporting_data or []
        )
        
        return AgentDecision(
            agent_id=self.metadata.agent_id,
            decision_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            input_data=input_data,
            recommendation=recommendation,
            escalation_required=confidence < escalation_threshold
        )
    
    def get_metadata(self) -> AgentMetadata:
        """Get agent metadata"""
        return self.metadata
    
    def set_status(self, status: str):
        """Update agent status"""
        self.metadata.status = status
