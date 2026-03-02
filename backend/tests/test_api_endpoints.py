"""
Unit Tests for API Endpoints
Tests authentication, authorization, request validation, and response formatting
for agent interaction and copilot chat APIs
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import json

from src.api.agent_endpoints import AgentInteractionAPI, APIResponse
from src.api.copilot_endpoints import CopilotChatAPI, WebSocketChatHandler
from src.api.auth import CognitoAuthenticator, AuthToken, APIKeyManager, RateLimiter
from src.api.gateway_config import create_default_gateway_config
from src.agents.business_copilot_agent import BusinessCopilotAgent
from src.agents.registry import AgentRegistry
from src.services.ai_council import AICouncil


class TestAuthentication:
    """Test authentication and authorization"""
    
    def test_cognito_authenticator_validates_valid_token(self):
        """Test that valid Cognito tokens are accepted"""
        authenticator = CognitoAuthenticator(
            user_pool_id='us-east-1_test',
            region='us-east-1',
            client_id='test-client'
        )
        
        # Mock valid token
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = {
                'sub': 'user-123',
                'email': 'test@example.com',
                'cognito:groups': ['users'],
                'exp': (datetime.utcnow() + timedelta(hours=1)).timestamp()
            }
            
            headers = {'Authorization': 'Bearer valid-token'}
            auth_token = authenticator.validate_request(headers)
            
            assert auth_token is not None
            assert auth_token.user_id == 'user-123'
            assert auth_token.email == 'test@example.com'
            assert 'users' in auth_token.groups
    
    def test_cognito_authenticator_rejects_invalid_token(self):
        """Test that invalid tokens are rejected"""
        authenticator = CognitoAuthenticator(
            user_pool_id='us-east-1_test',
            region='us-east-1',
            client_id='test-client'
        )
        
        headers = {'Authorization': 'Bearer invalid-token'}
        
        with patch('jwt.decode', side_effect=Exception('Invalid token')):
            auth_token = authenticator.validate_request(headers)
            assert auth_token is None
    
    def test_cognito_authenticator_rejects_missing_token(self):
        """Test that requests without tokens are rejected"""
        authenticator = CognitoAuthenticator(
            user_pool_id='us-east-1_test',
            region='us-east-1',
            client_id='test-client'
        )
        
        headers = {}
        auth_token = authenticator.validate_request(headers)
        assert auth_token is None
    
    def test_api_key_manager_generates_valid_keys(self):
        """Test API key generation"""
        manager = APIKeyManager()
        
        api_key = manager.generate_api_key('user-123', 'Test key')
        assert api_key is not None
        assert len(api_key) > 20
        
        # Validate the generated key
        user_id = manager.validate_api_key(api_key)
        assert user_id == 'user-123'
    
    def test_api_key_manager_validates_keys(self):
        """Test API key validation"""
        manager = APIKeyManager()
        
        api_key = manager.generate_api_key('user-123', 'Test key')
        
        # Valid key
        user_id = manager.validate_api_key(api_key)
        assert user_id == 'user-123'
        
        # Invalid key
        user_id = manager.validate_api_key('invalid-key')
        assert user_id is None
    
    def test_api_key_manager_revokes_keys(self):
        """Test API key revocation"""
        manager = APIKeyManager()
        
        api_key = manager.generate_api_key('user-123', 'Test key')
        
        # Key should work before revocation
        assert manager.validate_api_key(api_key) == 'user-123'
        
        # Revoke key
        result = manager.revoke_api_key(api_key)
        assert result is True
        
        # Key should not work after revocation
        assert manager.validate_api_key(api_key) is None
    
    def test_auth_token_expiration(self):
        """Test token expiration checking"""
        # Expired token
        expired_token = AuthToken(
            user_id='user-123',
            email='test@example.com',
            groups=['users'],
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        assert expired_token.is_expired() is True
        
        # Valid token
        valid_token = AuthToken(
            user_id='user-123',
            email='test@example.com',
            groups=['users'],
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        assert valid_token.is_expired() is False
    
    def test_auth_token_permissions(self):
        """Test permission checking"""
        token = AuthToken(
            user_id='user-123',
            email='test@example.com',
            groups=['users', 'admin'],
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        assert token.has_permission('users') is True
        assert token.has_permission('admin') is True
        assert token.has_permission('superadmin') is False


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_rate_limiter_allows_requests_within_limit(self):
        """Test that requests within limit are allowed"""
        limiter = RateLimiter(requests_per_second=10, burst_limit=20)
        
        # Should allow first 10 requests
        for i in range(10):
            assert limiter.is_allowed('client-1') is True
    
    def test_rate_limiter_blocks_requests_exceeding_limit(self):
        """Test that requests exceeding limit are blocked"""
        limiter = RateLimiter(requests_per_second=5, burst_limit=10)
        
        # Fill up the burst limit
        for i in range(10):
            limiter.is_allowed('client-1')
        
        # Next request should be blocked
        assert limiter.is_allowed('client-1') is False
    
    def test_rate_limiter_tracks_clients_separately(self):
        """Test that different clients have separate limits"""
        limiter = RateLimiter(requests_per_second=5, burst_limit=10)
        
        # Fill up limit for client-1
        for i in range(10):
            limiter.is_allowed('client-1')
        
        # client-2 should still be allowed
        assert limiter.is_allowed('client-2') is True
    
    def test_rate_limiter_calculates_retry_after(self):
        """Test retry-after calculation"""
        limiter = RateLimiter(requests_per_second=5, burst_limit=10)
        
        # Fill up the limit
        for i in range(10):
            limiter.is_allowed('client-1')
        
        # Should have a retry-after value
        retry_after = limiter.get_retry_after('client-1')
        assert retry_after >= 0


class TestAgentInteractionAPI:
    """Test agent interaction API endpoints"""
    
    @pytest.fixture
    def api(self):
        """Create API instance for testing"""
        authenticator = Mock(spec=CognitoAuthenticator)
        registry = Mock(spec=AgentRegistry)
        council = Mock(spec=AICouncil)
        
        return AgentInteractionAPI(authenticator, registry, council)
    
    @pytest.fixture
    def valid_auth_token(self):
        """Create valid auth token"""
        return AuthToken(
            user_id='user-123',
            email='test@example.com',
            groups=['users'],
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
    
    def test_query_agent_decisions_requires_authentication(self, api):
        """Test that querying decisions requires authentication"""
        api.authenticator.validate_request.return_value = None
        
        response = api.query_agent_decisions(
            headers={},
            query_params={}
        )
        
        assert response.success is False
        assert 'Authentication failed' in response.error
    
    def test_query_agent_decisions_with_valid_auth(self, api, valid_auth_token):
        """Test querying decisions with valid authentication"""
        api.authenticator.validate_request.return_value = valid_auth_token
        api.decision_repo.query_with_filter = Mock(return_value=[
            {'decisionId': 'dec-1', 'agentId': 'agent-1'},
            {'decisionId': 'dec-2', 'agentId': 'agent-2'}
        ])
        
        response = api.query_agent_decisions(
            headers={'Authorization': 'Bearer token'},
            query_params={'limit': '10'}
        )
        
        assert response.success is True
        assert response.data['count'] == 2
        assert len(response.data['decisions']) == 2
    
    def test_query_agent_decisions_with_filters(self, api, valid_auth_token):
        """Test querying decisions with filters"""
        api.authenticator.validate_request.return_value = valid_auth_token
        api.decision_repo.query_with_filter = Mock(return_value=[])
        
        response = api.query_agent_decisions(
            headers={'Authorization': 'Bearer token'},
            query_params={
                'agent_id': 'agent-1',
                'start_date': '2024-01-01',
                'limit': '50'
            }
        )
        
        assert response.success is True
        # Verify filter was applied
        api.decision_repo.query_with_filter.assert_called_once()
    
    def test_get_agent_decision_by_id(self, api, valid_auth_token):
        """Test getting specific decision by ID"""
        api.authenticator.validate_request.return_value = valid_auth_token
        api.decision_repo.get = Mock(return_value={
            'decisionId': 'dec-1',
            'agentId': 'agent-1',
            'confidence': 0.95
        })
        
        response = api.get_agent_decision(
            headers={'Authorization': 'Bearer token'},
            decision_id='dec-1'
        )
        
        assert response.success is True
        assert response.data['decisionId'] == 'dec-1'
    
    def test_get_agent_decision_not_found(self, api, valid_auth_token):
        """Test getting non-existent decision"""
        api.authenticator.validate_request.return_value = valid_auth_token
        api.decision_repo.get = Mock(return_value=None)
        
        response = api.get_agent_decision(
            headers={'Authorization': 'Bearer token'},
            decision_id='nonexistent'
        )
        
        assert response.success is False
        assert 'not found' in response.error.lower()
    
    def test_trigger_workflow_requires_workflow_type(self, api, valid_auth_token):
        """Test that triggering workflow requires workflow_type"""
        api.authenticator.validate_request.return_value = valid_auth_token
        
        response = api.trigger_workflow(
            headers={'Authorization': 'Bearer token'},
            request_body={}
        )
        
        assert response.success is False
        assert 'workflow_type is required' in response.error
    
    def test_trigger_workflow_success(self, api, valid_auth_token):
        """Test successful workflow triggering"""
        api.authenticator.validate_request.return_value = valid_auth_token
        
        with patch('src.api.agent_endpoints.WorkflowExecutionEngine') as mock_engine:
            mock_instance = Mock()
            mock_instance.trigger_workflow.return_value = Mock(
                workflow_id='wf-1',
                instance_id='inst-1',
                status='running',
                created_at=datetime.utcnow()
            )
            mock_engine.return_value = mock_instance
            
            response = api.trigger_workflow(
                headers={'Authorization': 'Bearer token'},
                request_body={
                    'workflow_type': 'pricing_optimization',
                    'input_data': {'sku': 'SKU-123'}
                }
            )
            
            assert response.success is True
            assert 'workflow_id' in response.data
    
    def test_get_business_intelligence_with_filters(self, api, valid_auth_token):
        """Test getting business intelligence with filters"""
        api.authenticator.validate_request.return_value = valid_auth_token
        api.intelligence_repo.query_with_filter = Mock(return_value=[
            {'entityType': 'pricing', 'entityId': 'sku-1'}
        ])
        
        response = api.get_business_intelligence(
            headers={'Authorization': 'Bearer token'},
            query_params={
                'entity_type': 'pricing',
                'limit': '10'
            }
        )
        
        assert response.success is True
        assert response.data['count'] == 1


class TestCopilotChatAPI:
    """Test Business Copilot chat API endpoints"""
    
    @pytest.fixture
    def api(self):
        """Create API instance for testing"""
        authenticator = Mock(spec=CognitoAuthenticator)
        copilot = Mock(spec=BusinessCopilotAgent)
        
        return CopilotChatAPI(authenticator, copilot)
    
    @pytest.fixture
    def valid_auth_token(self):
        """Create valid auth token"""
        return AuthToken(
            user_id='user-123',
            email='test@example.com',
            groups=['users'],
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
    
    def test_submit_query_requires_authentication(self, api):
        """Test that submitting query requires authentication"""
        api.authenticator.validate_request.return_value = None
        
        response = api.submit_query(
            headers={},
            request_body={'query': 'What is my inventory status?'}
        )
        
        assert response.success is False
        assert 'Authentication failed' in response.error
    
    def test_submit_query_requires_query_text(self, api, valid_auth_token):
        """Test that query text is required"""
        api.authenticator.validate_request.return_value = valid_auth_token
        
        response = api.submit_query(
            headers={'Authorization': 'Bearer token'},
            request_body={}
        )
        
        assert response.success is False
        assert 'query is required' in response.error
    
    def test_submit_query_creates_new_conversation(self, api, valid_auth_token):
        """Test that query creates new conversation if not provided"""
        api.authenticator.validate_request.return_value = valid_auth_token
        
        # Mock copilot response
        from src.models.agent_decision import AgentDecision, Recommendation
        mock_decision = AgentDecision(
            agent_id='copilot',
            decision_id='dec-1',
            timestamp=datetime.utcnow(),
            input_data={},
            recommendation=Recommendation(
                action=json.dumps({
                    'responseText': 'Test response',
                    'reasoningTrace': [],
                    'dataSources': [],
                    'recommendations': [],
                    'confidence': 0.9,
                    'requiresFollowup': False
                }),
                confidence=0.9,
                reasoning='Test',
                supporting_data=[]
            ),
            escalation_required=False
        )
        api.copilot_agent.process.return_value = mock_decision
        
        # Mock repository methods
        api.conversation_repo.get = Mock(return_value=None)
        api.conversation_repo.create = Mock()
        api.message_repo.create = Mock()
        api.conversation_repo.update = Mock()
        
        response = api.submit_query(
            headers={'Authorization': 'Bearer token'},
            request_body={'query': 'What is my inventory status?'}
        )
        
        assert response.success is True
        assert 'conversationId' in response.data
        assert 'response' in response.data
    
    def test_get_conversations_for_user(self, api, valid_auth_token):
        """Test getting conversations for authenticated user"""
        api.authenticator.validate_request.return_value = valid_auth_token
        api.conversation_repo.query_with_filter = Mock(return_value=[
            {'conversationId': 'conv-1', 'userId': 'user-123'},
            {'conversationId': 'conv-2', 'userId': 'user-123'}
        ])
        
        response = api.get_conversations(
            headers={'Authorization': 'Bearer token'},
            query_params={'status': 'active'}
        )
        
        assert response.success is True
        assert response.data['count'] == 2
    
    def test_get_conversation_with_messages(self, api, valid_auth_token):
        """Test getting specific conversation with messages"""
        api.authenticator.validate_request.return_value = valid_auth_token
        api.conversation_repo.get = Mock(return_value={
            'conversationId': 'conv-1',
            'userId': 'user-123'
        })
        api.message_repo.query_with_filter = Mock(return_value=[
            {'messageId': 'msg-1', 'role': 'user', 'content': 'Hello'},
            {'messageId': 'msg-2', 'role': 'assistant', 'content': 'Hi there'}
        ])
        
        response = api.get_conversation(
            headers={'Authorization': 'Bearer token'},
            conversation_id='conv-1',
            query_params={}
        )
        
        assert response.success is True
        assert 'conversation' in response.data
        assert 'messages' in response.data
        assert response.data['messageCount'] == 2
    
    def test_get_conversation_unauthorized_access(self, api, valid_auth_token):
        """Test that users cannot access other users' conversations"""
        api.authenticator.validate_request.return_value = valid_auth_token
        api.conversation_repo.get = Mock(return_value={
            'conversationId': 'conv-1',
            'userId': 'other-user'  # Different user
        })
        
        response = api.get_conversation(
            headers={'Authorization': 'Bearer token'},
            conversation_id='conv-1',
            query_params={}
        )
        
        assert response.success is False
        assert 'Unauthorized' in response.error
    
    def test_delete_conversation(self, api, valid_auth_token):
        """Test deleting (archiving) a conversation"""
        api.authenticator.validate_request.return_value = valid_auth_token
        api.conversation_repo.get = Mock(return_value={
            'conversationId': 'conv-1',
            'userId': 'user-123'
        })
        api.conversation_repo.update = Mock()
        
        response = api.delete_conversation(
            headers={'Authorization': 'Bearer token'},
            conversation_id='conv-1'
        )
        
        assert response.success is True
        # Verify conversation was archived
        api.conversation_repo.update.assert_called_once()
    
    def test_submit_feedback(self, api, valid_auth_token):
        """Test submitting feedback on copilot response"""
        api.authenticator.validate_request.return_value = valid_auth_token
        api.copilot_agent.submit_feedback = Mock(return_value={
            'feedbackId': 'fb-1',
            'status': 'received'
        })
        
        response = api.submit_feedback(
            headers={'Authorization': 'Bearer token'},
            request_body={
                'decision_id': 'dec-1',
                'feedback_type': 'positive',
                'category': 'accuracy',
                'rating': 5
            }
        )
        
        assert response.success is True
        assert 'feedbackId' in response.data


class TestAPIGatewayConfiguration:
    """Test API Gateway configuration"""
    
    def test_default_gateway_config_has_all_endpoints(self):
        """Test that default configuration includes all required endpoints"""
        config = create_default_gateway_config()
        
        # Verify basic configuration
        assert config.api_name == "RetailMind-AI-API"
        assert config.api_version == "v1"
        assert config.stage == "prod"
        
        # Verify endpoints exist
        endpoint_paths = [e.path for e in config.endpoints]
        
        # Agent interaction endpoints
        assert '/agents/decisions' in endpoint_paths
        assert '/workflows/trigger' in endpoint_paths
        assert '/intelligence' in endpoint_paths
        
        # Copilot endpoints
        assert '/copilot/query' in endpoint_paths
        assert '/copilot/conversations' in endpoint_paths
    
    def test_all_endpoints_have_rate_limiting(self):
        """Test that all endpoints have rate limiting configured"""
        config = create_default_gateway_config()
        
        for endpoint in config.endpoints:
            assert endpoint.rate_limit is not None
            assert endpoint.rate_limit.requests_per_second > 0
            assert endpoint.rate_limit.burst_limit > 0
    
    def test_all_endpoints_have_authentication(self):
        """Test that all endpoints require authentication"""
        config = create_default_gateway_config()
        
        for endpoint in config.endpoints:
            assert endpoint.auth_type is not None
            # Most endpoints should use Cognito
            assert endpoint.auth_type.value in ['cognito', 'api_key', 'iam']


class TestResponseFormatting:
    """Test API response formatting"""
    
    def test_api_response_success_format(self):
        """Test successful response format"""
        response = APIResponse(
            success=True,
            data={'key': 'value'},
            message='Operation successful'
        )
        
        response_dict = response.to_dict()
        
        assert response_dict['success'] is True
        assert response_dict['data'] == {'key': 'value'}
        assert response_dict['message'] == 'Operation successful'
        assert 'timestamp' in response_dict
    
    def test_api_response_error_format(self):
        """Test error response format"""
        response = APIResponse(
            success=False,
            data=None,
            error='Something went wrong'
        )
        
        response_dict = response.to_dict()
        
        assert response_dict['success'] is False
        assert response_dict['data'] is None
        assert response_dict['error'] == 'Something went wrong'
        assert 'timestamp' in response_dict
    
    def test_api_response_includes_timestamp(self):
        """Test that all responses include timestamp"""
        response = APIResponse(
            success=True,
            data={}
        )
        
        response_dict = response.to_dict()
        assert 'timestamp' in response_dict
        
        # Verify timestamp is valid ISO format
        timestamp = response_dict['timestamp']
        datetime.fromisoformat(timestamp)  # Should not raise exception


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
