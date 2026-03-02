"""
Agent Interaction API Endpoints
Provides REST API endpoints for querying agent decisions, triggering workflows,
and accessing business intelligence
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import json

from ..services.ai_council import AICouncil
from ..agents.registry import AgentRegistry
from ..repositories.dynamodb_repository import (
    AgentDecisionRepository,
    WorkflowInstanceRepository,
    BusinessIntelligenceRepository
)
from ..models.agent_decision import AgentDecision
from ..models.workflow_instance import WorkflowInstance
from ..models.business_intelligence import BusinessIntelligence
from .auth import CognitoAuthenticator, AuthToken


@dataclass
class APIResponse:
    """Standard API response format"""
    success: bool
    data: Any
    message: str = ""
    error: Optional[str] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        response = {
            "success": self.success,
            "data": self.data,
            "timestamp": self.timestamp
        }
        if self.message:
            response["message"] = self.message
        if self.error:
            response["error"] = self.error
        return response


class AgentInteractionAPI:
    """
    API handler for agent interaction endpoints
    Provides methods for querying agent decisions, triggering workflows,
    and accessing business intelligence
    """
    
    def __init__(
        self,
        authenticator: CognitoAuthenticator,
        agent_registry: AgentRegistry,
        ai_council: AICouncil
    ):
        """
        Initialize Agent Interaction API
        
        Args:
            authenticator: Cognito authenticator instance
            agent_registry: Agent registry instance
            ai_council: AI Council instance
        """
        self.authenticator = authenticator
        self.agent_registry = agent_registry
        self.ai_council = ai_council
        
        # Initialize repositories
        self.decision_repo = AgentDecisionRepository("retailmind-agent-decisions")
        self.workflow_repo = WorkflowInstanceRepository("retailmind-workflows")
        self.intelligence_repo = BusinessIntelligenceRepository("retailmind-business-intelligence")
    
    def query_agent_decisions(
        self,
        headers: Dict[str, str],
        query_params: Dict[str, Any]
    ) -> APIResponse:
        """
        Query agent decisions with optional filters
        
        Args:
            headers: Request headers (for authentication)
            query_params: Query parameters for filtering
                - agent_id: Filter by agent ID
                - start_date: Filter by start date (ISO format)
                - end_date: Filter by end date (ISO format)
                - limit: Maximum number of results (default 50)
                - offset: Pagination offset (default 0)
        
        Returns:
            APIResponse with list of agent decisions
        """
        # Authenticate request
        auth_token = self.authenticator.validate_request(headers)
        if not auth_token:
            return APIResponse(
                success=False,
                data=None,
                error="Authentication failed"
            )
        
        try:
            # Extract query parameters
            agent_id = query_params.get("agent_id")
            start_date = query_params.get("start_date")
            end_date = query_params.get("end_date")
            limit = int(query_params.get("limit", 50))
            offset = int(query_params.get("offset", 0))
            
            # Query decisions
            if agent_id:
                decisions_raw = self.decision_repo.get_by_agent(agent_id, limit=limit)
                decisions = [d.to_dict() for d in decisions_raw]
            else:
                decisions_raw = self.decision_repo.list(filters=None, limit=limit)
                decisions = [d.to_dict() for d in decisions_raw]
            
            # Apply date filters if provided (simplified)
            if start_date or end_date:
                filtered_decisions = []
                for d in decisions:
                    timestamp = d.get('timestamp', '')
                    if start_date and timestamp < start_date:
                        continue
                    if end_date and timestamp > end_date:
                        continue
                    filtered_decisions.append(d)
                decisions = filtered_decisions
            
            # Handle offset
            if offset:
                decisions = decisions[offset:]
            
            return APIResponse(
                success=True,
                data={
                    "decisions": decisions,
                    "count": len(decisions),
                    "limit": limit,
                    "offset": offset
                },
                message=f"Retrieved {len(decisions)} agent decisions"
            )
        
        except Exception as e:
            return APIResponse(
                success=False,
                data=None,
                error=f"Failed to query agent decisions: {str(e)}"
            )
    
    def get_agent_decision(
        self,
        headers: Dict[str, str],
        decision_id: str
    ) -> APIResponse:
        """
        Get a specific agent decision by ID
        
        Args:
            headers: Request headers (for authentication)
            decision_id: ID of the decision to retrieve
        
        Returns:
            APIResponse with agent decision details
        """
        # Authenticate request
        auth_token = self.authenticator.validate_request(headers)
        if not auth_token:
            return APIResponse(
                success=False,
                data=None,
                error="Authentication failed"
            )
        
        try:
            decision_obj = self.decision_repo.get(decision_id, decision_id)  # Using decision_id for both params
            
            if not decision_obj:
                return APIResponse(
                    success=False,
                    data=None,
                    error=f"Decision not found: {decision_id}"
                )
            
            decision = decision_obj.to_dict()
            
            return APIResponse(
                success=True,
                data=decision,
                message="Decision retrieved successfully"
            )
        
        except Exception as e:
            return APIResponse(
                success=False,
                data=None,
                error=f"Failed to get agent decision: {str(e)}"
            )
    
    def trigger_workflow(
        self,
        headers: Dict[str, str],
        request_body: Dict[str, Any]
    ) -> APIResponse:
        """
        Trigger a workflow execution
        
        Args:
            headers: Request headers (for authentication)
            request_body: Request body containing:
                - workflow_type: Type of workflow to trigger
                - input_data: Input data for the workflow
                - priority: Optional priority (default: normal)
        
        Returns:
            APIResponse with workflow instance details
        """
        # Authenticate request
        auth_token = self.authenticator.validate_request(headers)
        if not auth_token:
            return APIResponse(
                success=False,
                data=None,
                error="Authentication failed"
            )
        
        try:
            workflow_type = request_body.get("workflow_type")
            input_data = request_body.get("input_data", {})
            priority = request_body.get("priority", "normal")
            
            if not workflow_type:
                return APIResponse(
                    success=False,
                    data=None,
                    error="workflow_type is required"
                )
            
            # Create workflow instance
            from ..workflows.execution_engine import WorkflowExecutionEngine
            execution_engine = WorkflowExecutionEngine()
            
            workflow_instance = execution_engine.trigger_workflow(
                workflow_type=workflow_type,
                input_data=input_data,
                priority=priority,
                triggered_by=auth_token.user_id
            )
            
            return APIResponse(
                success=True,
                data={
                    "workflow_id": workflow_instance.workflow_id,
                    "instance_id": workflow_instance.instance_id,
                    "status": workflow_instance.status,
                    "created_at": workflow_instance.created_at.isoformat()
                },
                message=f"Workflow triggered successfully: {workflow_instance.instance_id}"
            )
        
        except Exception as e:
            return APIResponse(
                success=False,
                data=None,
                error=f"Failed to trigger workflow: {str(e)}"
            )
    
    def get_workflow_status(
        self,
        headers: Dict[str, str],
        workflow_id: str
    ) -> APIResponse:
        """
        Get the status of a workflow execution
        
        Args:
            headers: Request headers (for authentication)
            workflow_id: ID of the workflow to check
        
        Returns:
            APIResponse with workflow status details
        """
        # Authenticate request
        auth_token = self.authenticator.validate_request(headers)
        if not auth_token:
            return APIResponse(
                success=False,
                data=None,
                error="Authentication failed"
            )
        
        try:
            workflow_obj = self.workflow_repo.get(workflow_id, workflow_id)  # Using workflow_id for both params
            
            if not workflow_obj:
                return APIResponse(
                    success=False,
                    data=None,
                    error=f"Workflow not found: {workflow_id}"
                )
            
            workflow = workflow_obj.to_dict()
            
            return APIResponse(
                success=True,
                data=workflow,
                message="Workflow status retrieved successfully"
            )
        
        except Exception as e:
            return APIResponse(
                success=False,
                data=None,
                error=f"Failed to get workflow status: {str(e)}"
            )
    
    def get_business_intelligence(
        self,
        headers: Dict[str, str],
        query_params: Dict[str, Any]
    ) -> APIResponse:
        """
        Access business intelligence data
        
        Args:
            headers: Request headers (for authentication)
            query_params: Query parameters for filtering
                - entity_type: Type of intelligence (pricing, demand, inventory, risk)
                - start_date: Filter by start date
                - end_date: Filter by end date
                - limit: Maximum number of results
        
        Returns:
            APIResponse with business intelligence data
        """
        # Authenticate request
        auth_token = self.authenticator.validate_request(headers)
        if not auth_token:
            return APIResponse(
                success=False,
                data=None,
                error="Authentication failed"
            )
        
        try:
            entity_type = query_params.get("entity_type")
            start_date = query_params.get("start_date")
            end_date = query_params.get("end_date")
            limit = int(query_params.get("limit", 50))
            
            # Query intelligence data
            if entity_type:
                intelligence_data_raw = self.intelligence_repo.get_by_type(entity_type, limit=limit)
                intelligence_data = [i.to_dict() for i in intelligence_data_raw]
            else:
                intelligence_data_raw = self.intelligence_repo.list(filters=None, limit=limit)
                intelligence_data = [i.to_dict() for i in intelligence_data_raw]
            
            # Apply date filters if provided (simplified)
            if start_date or end_date:
                filtered_data = []
                for d in intelligence_data:
                    timestamp = d.get('timestamp', '')
                    if start_date and timestamp < start_date:
                        continue
                    if end_date and timestamp > end_date:
                        continue
                    filtered_data.append(d)
                intelligence_data = filtered_data
            
            return APIResponse(
                success=True,
                data={
                    "intelligence": intelligence_data,
                    "count": len(intelligence_data)
                },
                message=f"Retrieved {len(intelligence_data)} intelligence records"
            )
        
        except Exception as e:
            return APIResponse(
                success=False,
                data=None,
                error=f"Failed to get business intelligence: {str(e)}"
            )
    
    def get_specific_intelligence(
        self,
        headers: Dict[str, str],
        entity_type: str,
        entity_id: str
    ) -> APIResponse:
        """
        Get specific business intelligence by entity type and ID
        
        Args:
            headers: Request headers (for authentication)
            entity_type: Type of intelligence (pricing, demand, inventory, risk)
            entity_id: ID of the specific entity
        
        Returns:
            APIResponse with specific intelligence data
        """
        # Authenticate request
        auth_token = self.authenticator.validate_request(headers)
        if not auth_token:
            return APIResponse(
                success=False,
                data=None,
                error="Authentication failed"
            )
        
        try:
            # Query by composite key
            intelligence_obj = self.intelligence_repo.get(entity_type, entity_id)
            
            if not intelligence_obj:
                return APIResponse(
                    success=False,
                    data=None,
                    error=f"Intelligence not found for {entity_type}/{entity_id}"
                )
            
            intelligence = intelligence_obj.to_dict()
            
            return APIResponse(
                success=True,
                data=intelligence,
                message="Intelligence retrieved successfully"
            )
        
        except Exception as e:
            return APIResponse(
                success=False,
                data=None,
                error=f"Failed to get specific intelligence: {str(e)}"
            )
