"""
Agent Registry and Discovery Mechanism for RetailMind AI
Manages registration and discovery of AI agents
"""
from typing import Dict, List, Optional
from datetime import datetime
import json

from .base_agent import AgentMetadata, AgentStatus


class AgentRegistry:
    """
    Registry for managing and discovering AI agents
    Provides centralized agent registration and lookup
    """
    
    def __init__(self, dynamodb_table_name: str = "retailmind-agent-registry"):
        """
        Initialize agent registry
        
        Args:
            dynamodb_table_name: Name of the DynamoDB table for agent registry
        """
        self.table_name = dynamodb_table_name
        from ..utils.aws_clients import aws_clients
        self.dynamodb = aws_clients.dynamodb_resource
        self.table = self.dynamodb.Table(self.table_name)
    
    def register_agent(self, metadata: AgentMetadata) -> Dict:
        """
        Register an agent in the registry
        
        Args:
            metadata: Agent metadata to register
            
        Returns:
            Response from DynamoDB
        """
        item = {
            **metadata.to_dict(),
            'registeredAt': datetime.utcnow().isoformat(),
            'lastHeartbeat': datetime.utcnow().isoformat()
        }
        
        try:
            response = self.table.put_item(Item=item)
            return response
        except Exception as e:
            raise RegistryError(f"Failed to register agent: {str(e)}")
    
    def unregister_agent(self, agent_id: str) -> Dict:
        """
        Unregister an agent from the registry
        
        Args:
            agent_id: ID of the agent to unregister
            
        Returns:
            Response from DynamoDB
        """
        try:
            response = self.table.delete_item(
                Key={'agentId': agent_id}
            )
            return response
        except Exception as e:
            raise RegistryError(f"Failed to unregister agent: {str(e)}")
    
    def get_agent(self, agent_id: str) -> Optional[AgentMetadata]:
        """
        Get agent metadata by ID
        
        Args:
            agent_id: ID of the agent to retrieve
            
        Returns:
            AgentMetadata if found, None otherwise
        """
        try:
            response = self.table.get_item(Key={'agentId': agent_id})
            if 'Item' in response:
                item = response['Item']
                return AgentMetadata(
                    agent_id=item['agentId'],
                    agent_type=item['agentType'],
                    version=item['version'],
                    capabilities=item['capabilities'],
                    status=item['status']
                )
            return None
        except Exception as e:
            raise RegistryError(f"Failed to get agent: {str(e)}")
    
    def list_agents(self, status: Optional[str] = None) -> List[AgentMetadata]:
        """
        List all registered agents, optionally filtered by status
        
        Args:
            status: Optional status filter (e.g., 'active', 'inactive')
            
        Returns:
            List of AgentMetadata objects
        """
        try:
            if status:
                response = self.table.scan(
                    FilterExpression='#status = :status',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={':status': status}
                )
            else:
                response = self.table.scan()
            
            agents = []
            for item in response.get('Items', []):
                agents.append(AgentMetadata(
                    agent_id=item['agentId'],
                    agent_type=item['agentType'],
                    version=item['version'],
                    capabilities=item['capabilities'],
                    status=item['status']
                ))
            
            return agents
        except Exception as e:
            raise RegistryError(f"Failed to list agents: {str(e)}")
    
    def find_agents_by_capability(self, capability: str) -> List[AgentMetadata]:
        """
        Find agents that have a specific capability
        
        Args:
            capability: Capability to search for
            
        Returns:
            List of AgentMetadata objects with the capability
        """
        try:
            response = self.table.scan(
                FilterExpression='contains(capabilities, :capability)',
                ExpressionAttributeValues={':capability': capability}
            )
            
            agents = []
            for item in response.get('Items', []):
                agents.append(AgentMetadata(
                    agent_id=item['agentId'],
                    agent_type=item['agentType'],
                    version=item['version'],
                    capabilities=item['capabilities'],
                    status=item['status']
                ))
            
            return agents
        except Exception as e:
            raise RegistryError(f"Failed to find agents by capability: {str(e)}")
    
    def update_agent_status(self, agent_id: str, status: str) -> Dict:
        """
        Update the status of an agent
        
        Args:
            agent_id: ID of the agent
            status: New status
            
        Returns:
            Response from DynamoDB
        """
        try:
            response = self.table.update_item(
                Key={'agentId': agent_id},
                UpdateExpression='SET #status = :status, lastHeartbeat = :heartbeat',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': status,
                    ':heartbeat': datetime.utcnow().isoformat()
                }
            )
            return response
        except Exception as e:
            raise RegistryError(f"Failed to update agent status: {str(e)}")
    
    def heartbeat(self, agent_id: str) -> Dict:
        """
        Update the last heartbeat timestamp for an agent
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Response from DynamoDB
        """
        try:
            response = self.table.update_item(
                Key={'agentId': agent_id},
                UpdateExpression='SET lastHeartbeat = :heartbeat',
                ExpressionAttributeValues={
                    ':heartbeat': datetime.utcnow().isoformat()
                }
            )
            return response
        except Exception as e:
            raise RegistryError(f"Failed to update heartbeat: {str(e)}")


class RegistryError(Exception):
    """Exception raised for registry errors"""
    pass
