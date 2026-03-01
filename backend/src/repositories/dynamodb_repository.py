"""
DynamoDB repository implementations for RetailMind AI data models
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from ..models.agent_decision import AgentDecision
from ..models.workflow_instance import WorkflowInstance
from ..models.business_intelligence import BusinessIntelligence
from ..utils.aws_clients import aws_clients
from .base_repository import BaseRepository


class AgentDecisionRepository(BaseRepository[AgentDecision]):
    """Repository for AgentDecision entities in DynamoDB"""

    def __init__(self, table_name: str = "AgentDecisions"):
        self.table = aws_clients.get_dynamodb_table(table_name)

    def create(self, entity: AgentDecision) -> AgentDecision:
        """Create a new agent decision"""
        try:
            self.table.put_item(Item=entity.to_dict())
            return entity
        except ClientError as e:
            raise Exception(f"Failed to create agent decision: {e.response['Error']['Message']}")

    def get(self, agent_id: str, decision_id: str) -> Optional[AgentDecision]:
        """Get an agent decision by agent_id and decision_id"""
        try:
            response = self.table.get_item(
                Key={
                    'agentId': agent_id,
                    'decisionId': decision_id
                }
            )
            if 'Item' in response:
                return AgentDecision.from_dict(response['Item'])
            return None
        except ClientError as e:
            raise Exception(f"Failed to get agent decision: {e.response['Error']['Message']}")

    def update(self, entity: AgentDecision) -> AgentDecision:
        """Update an existing agent decision"""
        try:
            self.table.put_item(Item=entity.to_dict())
            return entity
        except ClientError as e:
            raise Exception(f"Failed to update agent decision: {e.response['Error']['Message']}")

    def delete(self, agent_id: str, decision_id: str) -> bool:
        """Delete an agent decision"""
        try:
            self.table.delete_item(
                Key={
                    'agentId': agent_id,
                    'decisionId': decision_id
                }
            )
            return True
        except ClientError as e:
            raise Exception(f"Failed to delete agent decision: {e.response['Error']['Message']}")

    def list(self, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[AgentDecision]:
        """List agent decisions with optional filters"""
        try:
            scan_kwargs = {}
            if limit:
                scan_kwargs['Limit'] = limit
            
            if filters:
                filter_expression = None
                for key, value in filters.items():
                    condition = Attr(key).eq(value)
                    filter_expression = condition if filter_expression is None else filter_expression & condition
                if filter_expression:
                    scan_kwargs['FilterExpression'] = filter_expression
            
            response = self.table.scan(**scan_kwargs)
            return [AgentDecision.from_dict(item) for item in response.get('Items', [])]
        except ClientError as e:
            raise Exception(f"Failed to list agent decisions: {e.response['Error']['Message']}")

    def get_by_agent(self, agent_id: str, limit: Optional[int] = None) -> List[AgentDecision]:
        """Get all decisions for a specific agent"""
        try:
            query_kwargs = {
                'KeyConditionExpression': Key('agentId').eq(agent_id)
            }
            if limit:
                query_kwargs['Limit'] = limit
            
            response = self.table.query(**query_kwargs)
            return [AgentDecision.from_dict(item) for item in response.get('Items', [])]
        except ClientError as e:
            raise Exception(f"Failed to get decisions by agent: {e.response['Error']['Message']}")

    def get_escalations(self, limit: Optional[int] = None) -> List[AgentDecision]:
        """Get all decisions requiring escalation"""
        try:
            query_kwargs = {
                'IndexName': 'escalation-index',
                'KeyConditionExpression': Key('escalationRequired').eq('true')
            }
            if limit:
                query_kwargs['Limit'] = limit
            
            response = self.table.query(**query_kwargs)
            return [AgentDecision.from_dict(item) for item in response.get('Items', [])]
        except ClientError as e:
            raise Exception(f"Failed to get escalations: {e.response['Error']['Message']}")


class WorkflowInstanceRepository(BaseRepository[WorkflowInstance]):
    """Repository for WorkflowInstance entities in DynamoDB"""

    def __init__(self, table_name: str = "WorkflowInstances"):
        self.table = aws_clients.get_dynamodb_table(table_name)

    def create(self, entity: WorkflowInstance) -> WorkflowInstance:
        """Create a new workflow instance"""
        try:
            self.table.put_item(Item=entity.to_dict())
            return entity
        except ClientError as e:
            raise Exception(f"Failed to create workflow instance: {e.response['Error']['Message']}")

    def get(self, workflow_id: str, instance_id: str) -> Optional[WorkflowInstance]:
        """Get a workflow instance by workflow_id and instance_id"""
        try:
            response = self.table.get_item(
                Key={
                    'workflowId': workflow_id,
                    'instanceId': instance_id
                }
            )
            if 'Item' in response:
                return WorkflowInstance.from_dict(response['Item'])
            return None
        except ClientError as e:
            raise Exception(f"Failed to get workflow instance: {e.response['Error']['Message']}")

    def update(self, entity: WorkflowInstance) -> WorkflowInstance:
        """Update an existing workflow instance"""
        try:
            self.table.put_item(Item=entity.to_dict())
            return entity
        except ClientError as e:
            raise Exception(f"Failed to update workflow instance: {e.response['Error']['Message']}")

    def delete(self, workflow_id: str, instance_id: str) -> bool:
        """Delete a workflow instance"""
        try:
            self.table.delete_item(
                Key={
                    'workflowId': workflow_id,
                    'instanceId': instance_id
                }
            )
            return True
        except ClientError as e:
            raise Exception(f"Failed to delete workflow instance: {e.response['Error']['Message']}")

    def list(self, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[WorkflowInstance]:
        """List workflow instances with optional filters"""
        try:
            scan_kwargs = {}
            if limit:
                scan_kwargs['Limit'] = limit
            
            if filters:
                filter_expression = None
                for key, value in filters.items():
                    condition = Attr(key).eq(value)
                    filter_expression = condition if filter_expression is None else filter_expression & condition
                if filter_expression:
                    scan_kwargs['FilterExpression'] = filter_expression
            
            response = self.table.scan(**scan_kwargs)
            return [WorkflowInstance.from_dict(item) for item in response.get('Items', [])]
        except ClientError as e:
            raise Exception(f"Failed to list workflow instances: {e.response['Error']['Message']}")

    def get_by_workflow(self, workflow_id: str, limit: Optional[int] = None) -> List[WorkflowInstance]:
        """Get all instances for a specific workflow"""
        try:
            query_kwargs = {
                'KeyConditionExpression': Key('workflowId').eq(workflow_id)
            }
            if limit:
                query_kwargs['Limit'] = limit
            
            response = self.table.query(**query_kwargs)
            return [WorkflowInstance.from_dict(item) for item in response.get('Items', [])]
        except ClientError as e:
            raise Exception(f"Failed to get instances by workflow: {e.response['Error']['Message']}")

    def get_by_status(self, status: str, limit: Optional[int] = None) -> List[WorkflowInstance]:
        """Get all workflow instances with a specific status"""
        try:
            query_kwargs = {
                'IndexName': 'status-index',
                'KeyConditionExpression': Key('status').eq(status)
            }
            if limit:
                query_kwargs['Limit'] = limit
            
            response = self.table.query(**query_kwargs)
            return [WorkflowInstance.from_dict(item) for item in response.get('Items', [])]
        except ClientError as e:
            raise Exception(f"Failed to get instances by status: {e.response['Error']['Message']}")


class BusinessIntelligenceRepository(BaseRepository[BusinessIntelligence]):
    """Repository for BusinessIntelligence entities in DynamoDB"""

    def __init__(self, table_name: str = "BusinessIntelligence"):
        self.table = aws_clients.get_dynamodb_table(table_name)

    def create(self, entity: BusinessIntelligence) -> BusinessIntelligence:
        """Create a new business intelligence entity"""
        try:
            self.table.put_item(Item=entity.to_dict())
            return entity
        except ClientError as e:
            raise Exception(f"Failed to create business intelligence: {e.response['Error']['Message']}")

    def get(self, entity_type: str, entity_id: str) -> Optional[BusinessIntelligence]:
        """Get a business intelligence entity by entity_type and entity_id"""
        try:
            response = self.table.get_item(
                Key={
                    'entityType': entity_type,
                    'entityId': entity_id
                }
            )
            if 'Item' in response:
                return BusinessIntelligence.from_dict(response['Item'])
            return None
        except ClientError as e:
            raise Exception(f"Failed to get business intelligence: {e.response['Error']['Message']}")

    def update(self, entity: BusinessIntelligence) -> BusinessIntelligence:
        """Update an existing business intelligence entity"""
        try:
            self.table.put_item(Item=entity.to_dict())
            return entity
        except ClientError as e:
            raise Exception(f"Failed to update business intelligence: {e.response['Error']['Message']}")

    def delete(self, entity_type: str, entity_id: str) -> bool:
        """Delete a business intelligence entity"""
        try:
            self.table.delete_item(
                Key={
                    'entityType': entity_type,
                    'entityId': entity_id
                }
            )
            return True
        except ClientError as e:
            raise Exception(f"Failed to delete business intelligence: {e.response['Error']['Message']}")

    def list(self, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[BusinessIntelligence]:
        """List business intelligence entities with optional filters"""
        try:
            scan_kwargs = {}
            if limit:
                scan_kwargs['Limit'] = limit
            
            if filters:
                filter_expression = None
                for key, value in filters.items():
                    condition = Attr(key).eq(value)
                    filter_expression = condition if filter_expression is None else filter_expression & condition
                if filter_expression:
                    scan_kwargs['FilterExpression'] = filter_expression
            
            response = self.table.scan(**scan_kwargs)
            return [BusinessIntelligence.from_dict(item) for item in response.get('Items', [])]
        except ClientError as e:
            raise Exception(f"Failed to list business intelligence: {e.response['Error']['Message']}")

    def get_by_type(self, entity_type: str, limit: Optional[int] = None) -> List[BusinessIntelligence]:
        """Get all business intelligence entities of a specific type"""
        try:
            query_kwargs = {
                'KeyConditionExpression': Key('entityType').eq(entity_type)
            }
            if limit:
                query_kwargs['Limit'] = limit
            
            response = self.table.query(**query_kwargs)
            return [BusinessIntelligence.from_dict(item) for item in response.get('Items', [])]
        except ClientError as e:
            raise Exception(f"Failed to get business intelligence by type: {e.response['Error']['Message']}")

    def get_high_confidence(self, entity_type: str, min_confidence: float, limit: Optional[int] = None) -> List[BusinessIntelligence]:
        """Get high-confidence business intelligence entities"""
        try:
            query_kwargs = {
                'IndexName': 'confidence-index',
                'KeyConditionExpression': Key('entityType').eq(entity_type) & Key('confidence').gte(min_confidence)
            }
            if limit:
                query_kwargs['Limit'] = limit
            
            response = self.table.query(**query_kwargs)
            return [BusinessIntelligence.from_dict(item) for item in response.get('Items', [])]
        except ClientError as e:
            raise Exception(f"Failed to get high-confidence business intelligence: {e.response['Error']['Message']}")
