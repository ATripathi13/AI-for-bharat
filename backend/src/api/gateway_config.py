"""
API Gateway Configuration
Defines REST API endpoints, authentication, rate limiting, and throttling
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum


class AuthType(Enum):
    """Authentication types for API endpoints"""
    COGNITO = "cognito"
    API_KEY = "api_key"
    IAM = "iam"
    NONE = "none"


class HTTPMethod(Enum):
    """HTTP methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_second: int = 100
    burst_limit: int = 200
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "requests_per_second": self.requests_per_second,
            "burst_limit": self.burst_limit
        }


@dataclass
class EndpointConfig:
    """Configuration for a single API endpoint"""
    path: str
    method: HTTPMethod
    auth_type: AuthType
    rate_limit: RateLimitConfig
    description: str
    request_schema: Dict[str, Any] = field(default_factory=dict)
    response_schema: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "method": self.method.value,
            "auth_type": self.auth_type.value,
            "rate_limit": self.rate_limit.to_dict(),
            "description": self.description,
            "request_schema": self.request_schema,
            "response_schema": self.response_schema
        }


@dataclass
class APIGatewayConfig:
    """Complete API Gateway configuration"""
    api_name: str = "RetailMind-AI-API"
    api_version: str = "v1"
    stage: str = "prod"
    endpoints: List[EndpointConfig] = field(default_factory=list)
    cognito_user_pool_arn: str = ""
    api_key_required: bool = True
    
    def add_endpoint(self, endpoint: EndpointConfig) -> None:
        """Add an endpoint to the configuration"""
        self.endpoints.append(endpoint)
    
    def get_endpoint(self, path: str, method: HTTPMethod) -> EndpointConfig:
        """Get endpoint configuration by path and method"""
        for endpoint in self.endpoints:
            if endpoint.path == path and endpoint.method == method:
                return endpoint
        raise ValueError(f"Endpoint not found: {method.value} {path}")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "api_name": self.api_name,
            "api_version": self.api_version,
            "stage": self.stage,
            "endpoints": [e.to_dict() for e in self.endpoints],
            "cognito_user_pool_arn": self.cognito_user_pool_arn,
            "api_key_required": self.api_key_required
        }


def create_default_gateway_config() -> APIGatewayConfig:
    """Create default API Gateway configuration with all endpoints"""
    config = APIGatewayConfig()
    
    # Agent interaction endpoints
    config.add_endpoint(EndpointConfig(
        path="/agents/decisions",
        method=HTTPMethod.GET,
        auth_type=AuthType.COGNITO,
        rate_limit=RateLimitConfig(requests_per_second=50, burst_limit=100),
        description="Query agent decisions"
    ))
    
    config.add_endpoint(EndpointConfig(
        path="/agents/decisions/{decision_id}",
        method=HTTPMethod.GET,
        auth_type=AuthType.COGNITO,
        rate_limit=RateLimitConfig(requests_per_second=100, burst_limit=200),
        description="Get specific agent decision"
    ))
    
    # Workflow endpoints
    config.add_endpoint(EndpointConfig(
        path="/workflows/trigger",
        method=HTTPMethod.POST,
        auth_type=AuthType.COGNITO,
        rate_limit=RateLimitConfig(requests_per_second=20, burst_limit=40),
        description="Trigger workflow execution"
    ))
    
    config.add_endpoint(EndpointConfig(
        path="/workflows/{workflow_id}",
        method=HTTPMethod.GET,
        auth_type=AuthType.COGNITO,
        rate_limit=RateLimitConfig(requests_per_second=100, burst_limit=200),
        description="Get workflow status"
    ))
    
    # Business intelligence endpoints
    config.add_endpoint(EndpointConfig(
        path="/intelligence",
        method=HTTPMethod.GET,
        auth_type=AuthType.COGNITO,
        rate_limit=RateLimitConfig(requests_per_second=50, burst_limit=100),
        description="Access business intelligence"
    ))
    
    config.add_endpoint(EndpointConfig(
        path="/intelligence/{entity_type}/{entity_id}",
        method=HTTPMethod.GET,
        auth_type=AuthType.COGNITO,
        rate_limit=RateLimitConfig(requests_per_second=100, burst_limit=200),
        description="Get specific business intelligence"
    ))
    
    # Business Copilot endpoints
    config.add_endpoint(EndpointConfig(
        path="/copilot/query",
        method=HTTPMethod.POST,
        auth_type=AuthType.COGNITO,
        rate_limit=RateLimitConfig(requests_per_second=30, burst_limit=60),
        description="Submit query to Business Copilot"
    ))
    
    config.add_endpoint(EndpointConfig(
        path="/copilot/conversations",
        method=HTTPMethod.GET,
        auth_type=AuthType.COGNITO,
        rate_limit=RateLimitConfig(requests_per_second=50, burst_limit=100),
        description="Get conversation history"
    ))
    
    config.add_endpoint(EndpointConfig(
        path="/copilot/conversations/{conversation_id}",
        method=HTTPMethod.GET,
        auth_type=AuthType.COGNITO,
        rate_limit=RateLimitConfig(requests_per_second=100, burst_limit=200),
        description="Get specific conversation"
    ))
    
    return config
