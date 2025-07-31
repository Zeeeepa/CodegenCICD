"""
Security and authentication system for CodegenCICD
"""
import os
import jwt
import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db_session

logger = structlog.get_logger(__name__)

# Security configuration
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.environ.get("JWT_EXPIRATION_HOURS", "24"))
BCRYPT_ROUNDS = int(os.environ.get("BCRYPT_ROUNDS", "12"))

# Rate limiting configuration
RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", "3600"))  # 1 hour

security = HTTPBearer()


class UserRole(str):
    """User roles for authorization"""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class TokenData(BaseModel):
    """JWT token data structure"""
    user_id: str
    username: str
    role: str
    exp: datetime
    iat: datetime
    jti: str  # JWT ID for token revocation


class User(BaseModel):
    """User model for authentication"""
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class AuthenticationError(HTTPException):
    """Custom authentication error"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=401, detail=detail)


class AuthorizationError(HTTPException):
    """Custom authorization error"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=403, detail=detail)


class RateLimitError(HTTPException):
    """Rate limit exceeded error"""
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(status_code=429, detail=detail)


class SecurityManager:
    """Central security management class"""
    
    def __init__(self):
        self.revoked_tokens: set = set()  # In production, use Redis
        self.rate_limit_cache: Dict[str, List[datetime]] = {}
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def generate_jwt_token(self, user: User) -> str:
        """Generate a JWT token for a user"""
        now = datetime.utcnow()
        exp = now + timedelta(hours=JWT_EXPIRATION_HOURS)
        jti = secrets.token_urlsafe(32)
        
        payload = {
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "exp": exp,
            "iat": now,
            "jti": jti
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        logger.info("JWT token generated", 
                   user_id=user.id, 
                   username=user.username,
                   expires_at=exp.isoformat())
        
        return token
    
    def verify_jwt_token(self, token: str) -> TokenData:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            
            # Check if token is revoked
            jti = payload.get("jti")
            if jti in self.revoked_tokens:
                raise AuthenticationError("Token has been revoked")
            
            token_data = TokenData(
                user_id=payload["user_id"],
                username=payload["username"],
                role=payload["role"],
                exp=datetime.fromtimestamp(payload["exp"]),
                iat=datetime.fromtimestamp(payload["iat"]),
                jti=jti
            )
            
            return token_data
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")
    
    def revoke_token(self, jti: str):
        """Revoke a JWT token"""
        self.revoked_tokens.add(jti)
        logger.info("Token revoked", jti=jti)
    
    def check_rate_limit(self, identifier: str, limit: int = RATE_LIMIT_REQUESTS, 
                        window: int = RATE_LIMIT_WINDOW) -> bool:
        """Check if request is within rate limit"""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window)
        
        # Clean old entries
        if identifier in self.rate_limit_cache:
            self.rate_limit_cache[identifier] = [
                timestamp for timestamp in self.rate_limit_cache[identifier]
                if timestamp > window_start
            ]
        else:
            self.rate_limit_cache[identifier] = []
        
        # Check limit
        if len(self.rate_limit_cache[identifier]) >= limit:
            return False
        
        # Add current request
        self.rate_limit_cache[identifier].append(now)
        return True
    
    def sanitize_input(self, input_data: Any) -> Any:
        """Sanitize input data to prevent injection attacks"""
        if isinstance(input_data, str):
            # Basic XSS prevention
            dangerous_chars = ['<', '>', '"', "'", '&', 'javascript:', 'data:', 'vbscript:']
            for char in dangerous_chars:
                if char in input_data.lower():
                    logger.warning("Potentially dangerous input detected", 
                                 input_preview=input_data[:100])
                    # In production, you might want to reject or escape
                    input_data = input_data.replace(char, '')
            
            # SQL injection prevention (basic)
            sql_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'SELECT', 'UNION', 'EXEC']
            for keyword in sql_keywords:
                if keyword in input_data.upper():
                    logger.warning("Potential SQL injection attempt", 
                                 input_preview=input_data[:100])
        
        elif isinstance(input_data, dict):
            return {key: self.sanitize_input(value) for key, value in input_data.items()}
        elif isinstance(input_data, list):
            return [self.sanitize_input(item) for item in input_data]
        
        return input_data
    
    def validate_permissions(self, user_role: str, required_role: str) -> bool:
        """Validate if user has required permissions"""
        role_hierarchy = {
            UserRole.READONLY: 1,
            UserRole.USER: 2,
            UserRole.ADMIN: 3
        }
        
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 999)
        
        return user_level >= required_level


# Global security manager instance
security_manager = SecurityManager()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Dependency to get current authenticated user"""
    try:
        token = credentials.credentials
        token_data = security_manager.verify_jwt_token(token)
        
        # Additional validation could be added here
        # e.g., check if user is still active in database
        
        return token_data
        
    except Exception as e:
        logger.warning("Authentication failed", error=str(e))
        raise AuthenticationError("Invalid authentication credentials")


def require_role(required_role: str):
    """Decorator to require specific role"""
    def role_checker(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if not security_manager.validate_permissions(current_user.role, required_role):
            logger.warning("Authorization failed", 
                         user_role=current_user.role, 
                         required_role=required_role,
                         user_id=current_user.user_id)
            raise AuthorizationError(f"Role '{required_role}' required")
        return current_user
    return role_checker


async def rate_limit_check(request: Request):
    """Rate limiting middleware"""
    # Use IP address as identifier (in production, consider user ID)
    client_ip = request.client.host
    
    if not security_manager.check_rate_limit(client_ip):
        logger.warning("Rate limit exceeded", client_ip=client_ip)
        raise RateLimitError("Too many requests. Please try again later.")


def sanitize_request_data(data: Any) -> Any:
    """Sanitize request data"""
    return security_manager.sanitize_input(data)


# Authentication endpoints models
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = UserRole.USER


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# Mock user database (in production, use real database)
MOCK_USERS = {
    "admin": {
        "id": "1",
        "username": "admin",
        "email": "admin@codegencd.com",
        "password_hash": security_manager.hash_password("admin123"),
        "role": UserRole.ADMIN,
        "is_active": True,
        "created_at": datetime.utcnow()
    },
    "user": {
        "id": "2", 
        "username": "user",
        "email": "user@codegencd.com",
        "password_hash": security_manager.hash_password("user123"),
        "role": UserRole.USER,
        "is_active": True,
        "created_at": datetime.utcnow()
    }
}


async def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate a user with username and password"""
    user_data = MOCK_USERS.get(username)
    if not user_data:
        return None
    
    if not security_manager.verify_password(password, user_data["password_hash"]):
        return None
    
    if not user_data["is_active"]:
        return None
    
    return User(
        id=user_data["id"],
        username=user_data["username"],
        email=user_data["email"],
        role=user_data["role"],
        is_active=user_data["is_active"],
        created_at=user_data["created_at"],
        last_login=datetime.utcnow()
    )


async def get_user_by_id(user_id: str) -> Optional[User]:
    """Get user by ID"""
    for user_data in MOCK_USERS.values():
        if user_data["id"] == user_id:
            return User(
                id=user_data["id"],
                username=user_data["username"],
                email=user_data["email"],
                role=user_data["role"],
                is_active=user_data["is_active"],
                created_at=user_data["created_at"]
            )
    return None

