"""
Authentication middleware for CodegenCICD API
"""
import structlog
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()
security = HTTPBearer()


async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Verify API key authentication
    For now, we'll use a simple token-based auth
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authentication")
    
    # For development, accept any token that starts with 'sk-'
    # In production, implement proper token validation
    if not credentials.credentials.startswith('sk-'):
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    logger.info("API key verified", token_prefix=credentials.credentials[:10])
    return credentials.credentials


async def get_current_user(token: str = Depends(verify_api_key)) -> dict:
    """
    Get current user from token
    For now, return a mock user
    """
    return {
        "id": "user_123",
        "email": "user@example.com",
        "org_id": settings.codegen_org_id
    }

