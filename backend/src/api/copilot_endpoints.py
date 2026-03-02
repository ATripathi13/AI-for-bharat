"""
Business Copilot Chat API Endpoints
Provides REST and WebSocket APIs for real-time chat with Business Copilot
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import json
import uuid

from ..agents.business_copilot_agent import BusinessCopilotAgent, ConversationContext
from ..repositories.dynamodb_repository import ConversationRepository, MessageRepository
from .auth import CognitoAuthenticator, AuthToken
from .agent_endpoints import APIResponse


@dataclass
class ChatMessage:
    """Chat message structure"""
    message_id: str
    conversation_id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "messageId": self.message_id,
            "conversationId": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class Conversation:
    """Conversation structure"""
    conversation_id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    status: str  # 'active', 'archived'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversationId": self.conversation_id,
            "userId": self.user_id,
            "title": self.title,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
            "messageCount": self.message_count,
            "status": self.status
        }


class CopilotChatAPI:
    """
    API handler for Business Copilot chat endpoints
    Provides methods for query submission, conversation management,
    and real-time chat via WebSocket
    """
    
    def __init__(
        self,
        authenticator: CognitoAuthenticator,
        copilot_agent: BusinessCopilotAgent
    ):
        """
        Initialize Copilot Chat API
        
        Args:
            authenticator: Cognito authenticator instance
            copilot_agent: Business Copilot agent instance
        """
        self.authenticator = authenticator
        self.copilot_agent = copilot_agent
        
        # Initialize repositories
        self.conversation_repo = ConversationRepository("retailmind-conversations")
        self.message_repo = MessageRepository("retailmind-messages")
    
    def submit_query(
        self,
        headers: Dict[str, str],
        request_body: Dict[str, Any]
    ) -> APIResponse:
        """
        Submit a query to Business Copilot
        
        Args:
            headers: Request headers (for authentication)
            request_body: Request body containing:
                - query: User's natural language query
                - conversation_id: Optional conversation ID (creates new if not provided)
                - context: Optional additional context
        
        Returns:
            APIResponse with copilot response
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
            query = request_body.get("query")
            if not query:
                return APIResponse(
                    success=False,
                    data=None,
                    error="query is required"
                )
            
            conversation_id = request_body.get("conversation_id")
            if not conversation_id:
                # Create new conversation
                conversation_id = str(uuid.uuid4())
                self._create_conversation(
                    conversation_id=conversation_id,
                    user_id=auth_token.user_id,
                    title=query[:50] + "..." if len(query) > 50 else query
                )
            
            # Process query with copilot
            input_data = {
                'query': query,
                'conversation_id': conversation_id,
                'user_id': auth_token.user_id,
                'context': request_body.get('context', {})
            }
            
            decision = self.copilot_agent.process(input_data)
            response_data = json.loads(decision.recommendation.action)
            
            # Save messages to repository
            self._save_message(
                conversation_id=conversation_id,
                role='user',
                content=query,
                metadata={}
            )
            
            self._save_message(
                conversation_id=conversation_id,
                role='assistant',
                content=response_data['responseText'],
                metadata={
                    'decisionId': decision.decision_id,
                    'reasoningTrace': response_data['reasoningTrace'],
                    'dataSources': response_data['dataSources'],
                    'confidence': response_data['confidence']
                }
            )
            
            # Update conversation
            self._update_conversation(conversation_id)
            
            return APIResponse(
                success=True,
                data={
                    "conversationId": conversation_id,
                    "decisionId": decision.decision_id,
                    "response": response_data['responseText'],
                    "reasoningTrace": response_data['reasoningTrace'],
                    "dataSources": response_data['dataSources'],
                    "recommendations": response_data['recommendations'],
                    "confidence": response_data['confidence'],
                    "requiresFollowup": response_data['requiresFollowup']
                },
                message="Query processed successfully"
            )
        
        except Exception as e:
            return APIResponse(
                success=False,
                data=None,
                error=f"Failed to process query: {str(e)}"
            )
    
    def get_conversations(
        self,
        headers: Dict[str, str],
        query_params: Dict[str, Any]
    ) -> APIResponse:
        """
        Get conversation history for the authenticated user
        
        Args:
            headers: Request headers (for authentication)
            query_params: Query parameters:
                - status: Filter by status ('active', 'archived')
                - limit: Maximum number of conversations (default 20)
                - offset: Pagination offset (default 0)
        
        Returns:
            APIResponse with list of conversations
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
            status = query_params.get("status", "active")
            limit = int(query_params.get("limit", 20))
            offset = int(query_params.get("offset", 0))
            
            # Query conversations for user
            conversations = self.conversation_repo.query_with_filter(
                filter_expression="userId = :user_id AND #status = :status",
                expression_values={
                    ":user_id": auth_token.user_id,
                    ":status": status
                },
                expression_names={"#status": "status"},
                limit=limit,
                offset=offset
            )
            
            return APIResponse(
                success=True,
                data={
                    "conversations": conversations,
                    "count": len(conversations),
                    "limit": limit,
                    "offset": offset
                },
                message=f"Retrieved {len(conversations)} conversations"
            )
        
        except Exception as e:
            return APIResponse(
                success=False,
                data=None,
                error=f"Failed to get conversations: {str(e)}"
            )
    
    def get_conversation(
        self,
        headers: Dict[str, str],
        conversation_id: str,
        query_params: Dict[str, Any]
    ) -> APIResponse:
        """
        Get a specific conversation with its messages
        
        Args:
            headers: Request headers (for authentication)
            conversation_id: ID of the conversation
            query_params: Query parameters:
                - limit: Maximum number of messages (default 50)
                - offset: Pagination offset (default 0)
        
        Returns:
            APIResponse with conversation details and messages
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
            # Get conversation
            conversation = self.conversation_repo.get(conversation_id)
            if not conversation:
                return APIResponse(
                    success=False,
                    data=None,
                    error=f"Conversation not found: {conversation_id}"
                )
            
            # Verify user owns this conversation
            if conversation.get('userId') != auth_token.user_id:
                return APIResponse(
                    success=False,
                    data=None,
                    error="Unauthorized access to conversation"
                )
            
            # Get messages
            limit = int(query_params.get("limit", 50))
            offset = int(query_params.get("offset", 0))
            
            messages = self.message_repo.query_with_filter(
                filter_expression="conversationId = :conversation_id",
                expression_values={":conversation_id": conversation_id},
                limit=limit,
                offset=offset
            )
            
            # Sort messages by timestamp
            messages.sort(key=lambda m: m.get('timestamp', ''))
            
            return APIResponse(
                success=True,
                data={
                    "conversation": conversation,
                    "messages": messages,
                    "messageCount": len(messages)
                },
                message="Conversation retrieved successfully"
            )
        
        except Exception as e:
            return APIResponse(
                success=False,
                data=None,
                error=f"Failed to get conversation: {str(e)}"
            )
    
    def delete_conversation(
        self,
        headers: Dict[str, str],
        conversation_id: str
    ) -> APIResponse:
        """
        Delete (archive) a conversation
        
        Args:
            headers: Request headers (for authentication)
            conversation_id: ID of the conversation to delete
        
        Returns:
            APIResponse with deletion confirmation
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
            # Get conversation
            conversation = self.conversation_repo.get(conversation_id)
            if not conversation:
                return APIResponse(
                    success=False,
                    data=None,
                    error=f"Conversation not found: {conversation_id}"
                )
            
            # Verify user owns this conversation
            if conversation.get('userId') != auth_token.user_id:
                return APIResponse(
                    success=False,
                    data=None,
                    error="Unauthorized access to conversation"
                )
            
            # Archive conversation (soft delete)
            self.conversation_repo.update(
                conversation_id,
                {
                    'status': 'archived',
                    'updatedAt': datetime.utcnow().isoformat()
                }
            )
            
            return APIResponse(
                success=True,
                data={"conversationId": conversation_id},
                message="Conversation archived successfully"
            )
        
        except Exception as e:
            return APIResponse(
                success=False,
                data=None,
                error=f"Failed to delete conversation: {str(e)}"
            )
    
    def submit_feedback(
        self,
        headers: Dict[str, str],
        request_body: Dict[str, Any]
    ) -> APIResponse:
        """
        Submit feedback on a copilot response
        
        Args:
            headers: Request headers (for authentication)
            request_body: Request body containing:
                - decision_id: ID of the decision being rated
                - feedback_type: Type of feedback ('positive', 'negative', 'correction', 'suggestion')
                - category: Category ('accuracy', 'relevance', 'completeness', 'clarity', 'actionability')
                - rating: Optional rating (1-5)
                - comment: Optional comment
                - correction: Optional correction text
        
        Returns:
            APIResponse with feedback confirmation
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
            decision_id = request_body.get("decision_id")
            feedback_type = request_body.get("feedback_type")
            category = request_body.get("category")
            
            if not all([decision_id, feedback_type, category]):
                return APIResponse(
                    success=False,
                    data=None,
                    error="decision_id, feedback_type, and category are required"
                )
            
            # Submit feedback to copilot agent
            feedback_result = self.copilot_agent.submit_feedback(
                decision_id=decision_id,
                user_id=auth_token.user_id,
                feedback_type=feedback_type,
                category=category,
                rating=request_body.get("rating"),
                comment=request_body.get("comment"),
                correction=request_body.get("correction")
            )
            
            return APIResponse(
                success=True,
                data=feedback_result,
                message="Feedback submitted successfully"
            )
        
        except Exception as e:
            return APIResponse(
                success=False,
                data=None,
                error=f"Failed to submit feedback: {str(e)}"
            )
    
    def get_quality_metrics(
        self,
        headers: Dict[str, str]
    ) -> APIResponse:
        """
        Get quality metrics for copilot responses (admin only)
        
        Args:
            headers: Request headers (for authentication)
        
        Returns:
            APIResponse with quality metrics
        """
        # Authenticate request
        auth_token = self.authenticator.validate_request(headers)
        if not auth_token:
            return APIResponse(
                success=False,
                data=None,
                error="Authentication failed"
            )
        
        # Check if user has admin permissions
        if not auth_token.has_permission("admin"):
            return APIResponse(
                success=False,
                data=None,
                error="Unauthorized: Admin access required"
            )
        
        try:
            metrics = self.copilot_agent.get_quality_metrics()
            
            return APIResponse(
                success=True,
                data=metrics,
                message="Quality metrics retrieved successfully"
            )
        
        except Exception as e:
            return APIResponse(
                success=False,
                data=None,
                error=f"Failed to get quality metrics: {str(e)}"
            )
    
    def _create_conversation(
        self,
        conversation_id: str,
        user_id: str,
        title: str
    ):
        """Create a new conversation record"""
        conversation = {
            'conversationId': conversation_id,
            'userId': user_id,
            'title': title,
            'createdAt': datetime.utcnow().isoformat(),
            'updatedAt': datetime.utcnow().isoformat(),
            'messageCount': 0,
            'status': 'active'
        }
        self.conversation_repo.create(conversation)
    
    def _save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any]
    ):
        """Save a message to the repository"""
        message = {
            'messageId': str(uuid.uuid4()),
            'conversationId': conversation_id,
            'role': role,
            'content': content,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata
        }
        self.message_repo.create(message)
    
    def _update_conversation(self, conversation_id: str):
        """Update conversation metadata"""
        conversation = self.conversation_repo.get(conversation_id)
        if conversation:
            self.conversation_repo.update(
                conversation_id,
                {
                    'updatedAt': datetime.utcnow().isoformat(),
                    'messageCount': conversation.get('messageCount', 0) + 2  # user + assistant
                }
            )


class WebSocketChatHandler:
    """
    WebSocket handler for real-time chat with Business Copilot
    Provides bidirectional communication for streaming responses
    """
    
    def __init__(
        self,
        authenticator: CognitoAuthenticator,
        copilot_agent: BusinessCopilotAgent
    ):
        """
        Initialize WebSocket chat handler
        
        Args:
            authenticator: Cognito authenticator instance
            copilot_agent: Business Copilot agent instance
        """
        self.authenticator = authenticator
        self.copilot_agent = copilot_agent
        self.active_connections: Dict[str, Any] = {}
    
    async def connect(
        self,
        connection_id: str,
        auth_token: str
    ) -> Dict[str, Any]:
        """
        Handle WebSocket connection
        
        Args:
            connection_id: Unique connection identifier
            auth_token: Authentication token
        
        Returns:
            Connection response
        """
        # Verify authentication
        token = self.authenticator.verify_token(auth_token)
        if not token:
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Authentication failed'})
            }
        
        # Store connection
        self.active_connections[connection_id] = {
            'user_id': token.user_id,
            'connected_at': datetime.utcnow(),
            'conversation_id': None
        }
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Connected to Business Copilot',
                'connectionId': connection_id
            })
        }
    
    async def disconnect(self, connection_id: str) -> Dict[str, Any]:
        """
        Handle WebSocket disconnection
        
        Args:
            connection_id: Connection identifier
        
        Returns:
            Disconnection response
        """
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Disconnected'})
        }
    
    async def handle_message(
        self,
        connection_id: str,
        message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle incoming WebSocket message
        
        Args:
            connection_id: Connection identifier
            message: Message data
        
        Returns:
            Response to send back
        """
        if connection_id not in self.active_connections:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid connection'})
            }
        
        connection = self.active_connections[connection_id]
        message_type = message.get('type', 'query')
        
        if message_type == 'query':
            # Process query
            query = message.get('query', '')
            conversation_id = message.get('conversationId') or str(uuid.uuid4())
            
            # Update connection with conversation ID
            connection['conversation_id'] = conversation_id
            
            # Process with copilot
            input_data = {
                'query': query,
                'conversation_id': conversation_id,
                'user_id': connection['user_id']
            }
            
            decision = self.copilot_agent.process(input_data)
            response_data = json.loads(decision.recommendation.action)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'type': 'response',
                    'conversationId': conversation_id,
                    'decisionId': decision.decision_id,
                    'response': response_data['responseText'],
                    'reasoningTrace': response_data['reasoningTrace'],
                    'recommendations': response_data['recommendations'],
                    'confidence': response_data['confidence']
                })
            }
        
        elif message_type == 'ping':
            return {
                'statusCode': 200,
                'body': json.dumps({'type': 'pong'})
            }
        
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Unknown message type: {message_type}'})
            }
