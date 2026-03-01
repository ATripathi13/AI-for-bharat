"""
Agent Communication Protocol (ACP) for RetailMind AI
Defines message formats and communication interfaces for agent messaging
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum
import json


class MessageType(Enum):
    """Types of messages in the Agent Communication Protocol"""
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    NOTIFICATION = "notification"


@dataclass
class ACPMessage:
    """
    Agent Communication Protocol Message
    Standard message format for inter-agent communication
    """
    agent_id: str
    message_type: MessageType
    payload: Dict[str, Any]
    timestamp: datetime
    correlation_id: str
    target_agent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for transmission"""
        return {
            'agentId': self.agent_id,
            'messageType': self.message_type.value,
            'payload': self.payload,
            'timestamp': self.timestamp.isoformat(),
            'correlationId': self.correlation_id,
            'targetAgentId': self.target_agent_id,
            'metadata': self.metadata
        }
    
    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ACPMessage':
        """Create message from dictionary"""
        return cls(
            agent_id=data['agentId'],
            message_type=MessageType(data['messageType']),
            payload=data['payload'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            correlation_id=data['correlationId'],
            target_agent_id=data.get('targetAgentId'),
            metadata=data.get('metadata', {})
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ACPMessage':
        """Create message from JSON string"""
        return cls.from_dict(json.loads(json_str))


@dataclass
class DecisionPayload:
    """Payload for decision-related messages"""
    data: Any
    confidence: float
    reasoning: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'data': self.data,
            'confidence': self.confidence,
            'reasoning': self.reasoning
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DecisionPayload':
        """Create from dictionary"""
        return cls(
            data=data['data'],
            confidence=data['confidence'],
            reasoning=data['reasoning']
        )


class AgentCommunicationInterface:
    """
    Interface for agent communication
    Handles sending and receiving messages between agents
    """
    
    def __init__(self, event_bus_name: str = "retailmind-ai-events"):
        """
        Initialize communication interface
        
        Args:
            event_bus_name: Name of the EventBridge event bus
        """
        self.event_bus_name = event_bus_name
        from ..utils.aws_clients import aws_clients
        self.events_client = aws_clients.events
    
    def send_message(self, message: ACPMessage) -> Dict[str, Any]:
        """
        Send a message via EventBridge
        
        Args:
            message: ACPMessage to send
            
        Returns:
            Response from EventBridge
        """
        try:
            response = self.events_client.put_events(
                Entries=[
                    {
                        'Source': f'retailmind.agent.{message.agent_id}',
                        'DetailType': message.message_type.value,
                        'Detail': message.to_json(),
                        'EventBusName': self.event_bus_name
                    }
                ]
            )
            return response
        except Exception as e:
            raise CommunicationError(f"Failed to send message: {str(e)}")
    
    def send_request(
        self,
        from_agent_id: str,
        to_agent_id: str,
        payload: Dict[str, Any],
        correlation_id: str
    ) -> Dict[str, Any]:
        """
        Send a request message to another agent
        
        Args:
            from_agent_id: ID of the sending agent
            to_agent_id: ID of the target agent
            payload: Message payload
            correlation_id: Correlation ID for tracking
            
        Returns:
            Response from EventBridge
        """
        message = ACPMessage(
            agent_id=from_agent_id,
            message_type=MessageType.REQUEST,
            payload=payload,
            timestamp=datetime.utcnow(),
            correlation_id=correlation_id,
            target_agent_id=to_agent_id
        )
        return self.send_message(message)
    
    def send_response(
        self,
        from_agent_id: str,
        to_agent_id: str,
        payload: Dict[str, Any],
        correlation_id: str
    ) -> Dict[str, Any]:
        """
        Send a response message to another agent
        
        Args:
            from_agent_id: ID of the sending agent
            to_agent_id: ID of the target agent
            payload: Message payload
            correlation_id: Correlation ID from the original request
            
        Returns:
            Response from EventBridge
        """
        message = ACPMessage(
            agent_id=from_agent_id,
            message_type=MessageType.RESPONSE,
            payload=payload,
            timestamp=datetime.utcnow(),
            correlation_id=correlation_id,
            target_agent_id=to_agent_id
        )
        return self.send_message(message)
    
    def broadcast(
        self,
        from_agent_id: str,
        payload: Dict[str, Any],
        correlation_id: str
    ) -> Dict[str, Any]:
        """
        Broadcast a message to all agents
        
        Args:
            from_agent_id: ID of the sending agent
            payload: Message payload
            correlation_id: Correlation ID for tracking
            
        Returns:
            Response from EventBridge
        """
        message = ACPMessage(
            agent_id=from_agent_id,
            message_type=MessageType.BROADCAST,
            payload=payload,
            timestamp=datetime.utcnow(),
            correlation_id=correlation_id
        )
        return self.send_message(message)


class CommunicationError(Exception):
    """Exception raised for communication errors"""
    pass
