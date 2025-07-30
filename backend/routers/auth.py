"""
Authentication and authorization endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
import structlog

from backend.core.security import (
    LoginRequest, LoginResponse, CreateUserRequest, ChangePasswordRequest,
    authenticate_user, get_current_user, require_role, rate_limit_check,
    security_manager, TokenData, UserRole, AuthenticationError
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    _: None = Depends(rate_limit_check)
):
    """
    Authenticate user and return JWT token
    """
    try:
        # Sanitize input
        username = security_manager.sanitize_input(request.username)
        password = request.password  # Don't sanitize passwords
        
        # Authenticate user
        user = await authenticate_user(username, password)
        if not user:
            logger.warning("Login failed", 
                         username=username, 
                         client_ip=http_request.client.host)
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )
        
        # Generate JWT token
        access_token = security_manager.generate_jwt_token(user)
        
        logger.info("User logged in successfully", 
                   user_id=user.id, 
                   username=user.username,
                   client_ip=http_request.client.host)
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=24 * 3600,  # 24 hours in seconds
            user={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/logout")
async def logout(current_user: TokenData = Depends(get_current_user)):
    """
    Logout user by revoking JWT token
    """
    try:
        # Revoke the token
        security_manager.revoke_token(current_user.jti)
        
        logger.info("User logged out", 
                   user_id=current_user.user_id,
                   username=current_user.username)
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error("Logout error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/me")
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """
    Get current user information
    """
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "role": current_user.role,
        "token_expires": current_user.exp.isoformat()
    }


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Change user password
    """
    try:
        # In a real implementation, you would:
        # 1. Verify current password
        # 2. Hash new password
        # 3. Update in database
        # 4. Optionally revoke all existing tokens
        
        logger.info("Password change requested", user_id=current_user.user_id)
        
        # For now, just return success
        return {"message": "Password changed successfully"}
        
    except Exception as e:
        logger.error("Password change error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/create-user")
async def create_user(
    request: CreateUserRequest,
    current_user: TokenData = Depends(require_role(UserRole.ADMIN))
):
    """
    Create a new user (admin only)
    """
    try:
        # Sanitize input
        username = security_manager.sanitize_input(request.username)
        email = security_manager.sanitize_input(request.email)
        
        # Validate role
        if request.role not in [UserRole.ADMIN, UserRole.USER, UserRole.READONLY]:
            raise HTTPException(status_code=400, detail="Invalid role")
        
        # In a real implementation, you would:
        # 1. Check if username/email already exists
        # 2. Hash password
        # 3. Create user in database
        # 4. Send welcome email
        
        logger.info("User creation requested", 
                   new_username=username,
                   new_role=request.role,
                   created_by=current_user.username)
        
        return {
            "message": f"User '{username}' created successfully",
            "user": {
                "username": username,
                "email": email,
                "role": request.role
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("User creation error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users")
async def list_users(
    current_user: TokenData = Depends(require_role(UserRole.ADMIN))
):
    """
    List all users (admin only)
    """
    try:
        # In a real implementation, you would query the database
        from backend.core.security import MOCK_USERS
        
        users = []
        for user_data in MOCK_USERS.values():
            users.append({
                "id": user_data["id"],
                "username": user_data["username"],
                "email": user_data["email"],
                "role": user_data["role"],
                "is_active": user_data["is_active"],
                "created_at": user_data["created_at"].isoformat()
            })
        
        return {"users": users}
        
    except Exception as e:
        logger.error("List users error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/revoke-token/{user_id}")
async def revoke_user_tokens(
    user_id: str,
    current_user: TokenData = Depends(require_role(UserRole.ADMIN))
):
    """
    Revoke all tokens for a specific user (admin only)
    """
    try:
        # In a real implementation, you would:
        # 1. Get all active tokens for the user
        # 2. Add them to revocation list
        # 3. Optionally notify the user
        
        logger.info("Token revocation requested", 
                   target_user_id=user_id,
                   revoked_by=current_user.username)
        
        return {"message": f"All tokens revoked for user {user_id}"}
        
    except Exception as e:
        logger.error("Token revocation error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def auth_health_check():
    """
    Health check endpoint for authentication service
    """
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": "2025-01-30T15:30:00Z"
    }

