"""
OpenAPI Specification Generator
Generates OpenAPI 3.0 specification for the RetailMind AI API
"""

from typing import Dict, Any
from .gateway_config import APIGatewayConfig, create_default_gateway_config


def generate_openapi_spec(config: APIGatewayConfig = None) -> Dict[str, Any]:
    """Generate OpenAPI 3.0 specification from API Gateway configuration"""
    if config is None:
        config = create_default_gateway_config()
    
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": config.api_name,
            "version": config.api_version,
            "description": "RetailMind AI - Multi-Agent Decision Intelligence Platform API",
            "contact": {
                "name": "RetailMind AI Support",
                "email": "support@retailmind.ai"
            }
        },
        "servers": [
            {
                "url": f"https://api.retailmind.ai/{config.stage}",
                "description": f"{config.stage.capitalize()} environment"
            }
        ],
        "security": [
            {"CognitoAuth": []},
            {"ApiKeyAuth": []}
        ],
        "paths": {},
        "components": {
            "securitySchemes": {
                "CognitoAuth": {
                    "type": "oauth2",
                    "flows": {
                        "authorizationCode": {
                            "authorizationUrl": "https://auth.retailmind.ai/oauth2/authorize",
                            "tokenUrl": "https://auth.retailmind.ai/oauth2/token",
                            "scopes": {
                                "read": "Read access",
                                "write": "Write access"
                            }
                        }
                    }
                },
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key"
                }
            },
            "schemas": {
                "AgentDecision": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string"},
                        "decision_id": {"type": "string"},
                        "timestamp": {"type": "string", "format": "date-time"},
                        "recommendation": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string"},
                                "confidence": {"type": "number"},
                                "reasoning": {"type": "string"}
                            }
                        }
                    }
                },
                "WorkflowTrigger": {
                    "type": "object",
                    "properties": {
                        "workflow_type": {"type": "string"},
                        "parameters": {"type": "object"}
                    },
                    "required": ["workflow_type"]
                },
                "BusinessIntelligence": {
                    "type": "object",
                    "properties": {
                        "entity_type": {"type": "string"},
                        "entity_id": {"type": "string"},
                        "insights": {"type": "object"},
                        "recommendations": {"type": "array"}
                    }
                },
                "CopilotQuery": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "conversation_id": {"type": "string"},
                        "context": {"type": "object"}
                    },
                    "required": ["query"]
                },
                "CopilotResponse": {
                    "type": "object",
                    "properties": {
                        "response": {"type": "string"},
                        "conversation_id": {"type": "string"},
                        "reasoning": {"type": "string"},
                        "recommendations": {"type": "array"}
                    }
                },
                "Error": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string"},
                        "message": {"type": "string"},
                        "details": {"type": "object"}
                    }
                }
            }
        }
    }
    
    # Add paths from configuration
    for endpoint in config.endpoints:
        path = endpoint.path
        if path not in spec["paths"]:
            spec["paths"][path] = {}
        
        method = endpoint.method.value.lower()
        spec["paths"][path][method] = {
            "summary": endpoint.description,
            "security": _get_security_for_auth_type(endpoint.auth_type),
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": endpoint.response_schema or {"type": "object"}
                        }
                    }
                },
                "400": {
                    "description": "Bad request",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    }
                },
                "401": {
                    "description": "Unauthorized",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    }
                },
                "429": {
                    "description": "Too many requests",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    }
                },
                "500": {
                    "description": "Internal server error",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    }
                }
            }
        }
        
        # Add request body for POST/PUT/PATCH methods
        if method in ["post", "put", "patch"]:
            spec["paths"][path][method]["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": endpoint.request_schema or {"type": "object"}
                    }
                }
            }
    
    return spec


def _get_security_for_auth_type(auth_type) -> list:
    """Get security requirements based on auth type"""
    from .gateway_config import AuthType
    
    if auth_type == AuthType.COGNITO:
        return [{"CognitoAuth": []}]
    elif auth_type == AuthType.API_KEY:
        return [{"ApiKeyAuth": []}]
    elif auth_type == AuthType.NONE:
        return []
    else:
        return [{"CognitoAuth": []}]


def save_openapi_spec(filename: str = "openapi.json", config: APIGatewayConfig = None) -> None:
    """Save OpenAPI specification to a JSON file"""
    import json
    
    spec = generate_openapi_spec(config)
    with open(filename, 'w') as f:
        json.dump(spec, f, indent=2)
