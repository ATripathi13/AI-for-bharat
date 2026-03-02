"""
Authentication and Authorization
Handles Cognito authentication and API key validation
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import jwt
import hashlib
import secrets


@dataclass
class AuthToken:
    """Authentication token"""
    user_id: str
    email: str
    groups: list
    expires_at: datetime
    token_type: str = "Bearer"
    
    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.utcnow() > self.expires_at
    
    def has_permission(self, required_group: str) -> bool:
        """Check if user has required permission"""
        return required_group in self.groups


class CognitoAuthenticator:
    """Handles Cognito authentication"""
    
    def __init__(self, user_pool_id: str, region: str, client_id: str):
        self.user_pool_id = user_pool_id
        self.region = region
        self.client_id = client_id
        self.jwks_url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
    
    def verify_token(self, token: str) -> Optional[AuthToken]:
        """Verify Cognito JWT token"""
        try:
            # In production, this would verify against Cognito JWKS
            # For now, we'll decode without verification for testing
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            return AuthToken(
                user_id=decoded.get("sub", ""),
                email=decoded.get("email", ""),
                groups=decoded.get("cognito:groups", []),
                expires_at=datetime.fromtimestamp(decoded.get("exp", 0))
            )
        except Exception as e:
            return None
    
    def validate_request(self, headers: Dict[str, str]) -> Optional[AuthToken]:
        """Validate authentication from request headers"""
        auth_header = headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        return self.verify_token(token)


class APIKeyManager:
    """Manages API keys"""
    
    def __init__(self):
        self.api_keys: Dict[str, Dict[str, Any]] = {}
    
    def generate_api_key(self, user_id: str, description: str = "") -> str:
        """Generate a new API key"""
        api_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        self.api_keys[key_hash] = {
            "user_id": user_id,
            "description": description,
            "created_at": datetime.utcnow(),
            "last_used": None,
            "active": True
        }
        
        return api_key
    
    def validate_api_key(self, api_key: str) -> Optional[str]:
        """Validate API key and return user_id"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        if key_hash in self.api_keys:
            key_info = self.api_keys[key_hash]
            if key_info["active"]:
                key_info["last_used"] = datetime.utcnow()
                return key_info["user_id"]
        
        return None
    
    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        if key_hash in self.api_keys:
            self.api_keys[key_hash]["active"] = False
            return True
        
        return False
    
    def validate_request(self, headers: Dict[str, str]) -> Optional[str]:
        """Validate API key from request headers"""
        api_key = headers.get("X-API-Key", "")
        if not api_key:
            return None
        
        return self.validate_api_key(api_key)


class RateLimiter:
    """Rate limiting implementation"""
    
    def __init__(self, requests_per_second: int, burst_limit: int):
        self.requests_per_second = requests_per_second
        self.burst_limit = burst_limit
        self.requests: Dict[str, list] = {}
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed based on rate limits"""
        now = datetime.utcnow()
        
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Remove old requests (older than 1 second)
        cutoff = now - timedelta(seconds=1)
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > cutoff
        ]
        
        # Check burst limit
        if len(self.requests[client_id]) >= self.burst_limit:
            return False
        
        # Check rate limit
        if len(self.requests[client_id]) >= self.requests_per_second:
            return False
        
        # Add current request
        self.requests[client_id].append(now)
        return True
    
    def get_retry_after(self, client_id: str) -> int:
        """Get seconds until next request is allowed"""
        if client_id not in self.requests or not self.requests[client_id]:
            return 0
        
        oldest_request = min(self.requests[client_id])
        time_since_oldest = (datetime.utcnow() - oldest_request).total_seconds()
        
        if time_since_oldest < 1:
            return int(1 - time_since_oldest) + 1
        
        return 0
