"""
FastAPI dependency injection for database services
"""
from typing import Generator, Dict, Any
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from database.connection_manager import DatabaseManager, get_database_manager
from services.database_service import DatabaseService, get_database_service
from repositories import RepositoryFactory, get_repository_factory
from errors.exceptions import DatabaseError, ValidationError, SecurityError
from config.settings import get_settings

logger = logging.getLogger(__name__)

# Security scheme for API authentication
security = HTTPBearer(auto_error=False)


def get_db_manager() -> DatabaseManager:
    """Dependency to get database manager"""
    try:
        return get_database_manager()
    except Exception as e:
        logger.error(f"Failed to get database manager: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )


def get_db_service(db_manager: DatabaseManager = Depends(get_db_manager)) -> DatabaseService:
    """Dependency to get database service"""
    try:
        return get_database_service()
    except Exception as e:
        logger.error(f"Failed to get database service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )


def get_repository_factory_dep(db_manager: DatabaseManager = Depends(get_db_manager)) -> RepositoryFactory:
    """Dependency to get repository factory"""
    try:
        return get_repository_factory()
    except Exception as e:
        logger.error(f"Failed to get repository factory: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Repository service unavailable"
        )


async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Verify API key authentication (optional for now)"""
    # For now, we'll make authentication optional
    # In production, implement proper API key validation
    if credentials is None:
        # Allow unauthenticated access for development
        return {"authenticated": False, "user_id": None}
    
    try:
        settings = get_settings()
        # Simple API key validation (enhance in production)
        if credentials.credentials == settings.api_secret_key:
            return {"authenticated": True, "user_id": "admin"}
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except Exception as e:
        logger.error(f"API key verification failed: {str(e)}")
        # For development, allow access even if verification fails
        return {"authenticated": False, "user_id": None}


def handle_database_errors(func):
    """Decorator to handle database errors and convert to HTTP exceptions"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except SecurityError as e:
            logger.error(f"Security error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security error occurred"
            )
        except DatabaseError as e:
            logger.error(f"Database error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database operation failed"
            )
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    return wrapper


class DatabaseDependency:
    """Class-based dependency for database operations with error handling"""
    
    def __init__(self):
        self.db_service = None
    
    async def __call__(self, db_service: DatabaseService = Depends(get_db_service)) -> DatabaseService:
        """Get database service with error handling"""
        try:
            # Perform health check
            health = await db_service.health_check()
            if health['status'] != 'healthy':
                logger.error(f"Database health check failed: {health}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database service unhealthy"
                )
            
            return db_service
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Database dependency failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable"
            )


# Create dependency instances
get_healthy_db_service = DatabaseDependency()


def validate_project_id(project_id: int) -> int:
    """Validate project ID parameter"""
    if project_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID"
        )
    return project_id


def validate_pagination(skip: int = 0, limit: int = 100) -> Dict[str, int]:
    """Validate pagination parameters"""
    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skip parameter must be >= 0"
        )
    
    if limit <= 0 or limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit parameter must be between 1 and 1000"
        )
    
    return {"skip": skip, "limit": limit}


async def get_project_or_404(
    project_id: int,
    db_service: DatabaseService = Depends(get_healthy_db_service)
):
    """Get project by ID or raise 404"""
    try:
        project = db_service.projects.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )
        return project
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project"
        )


# Middleware for request logging and correlation IDs
async def log_request_middleware(request, call_next):
    """Middleware to log requests with correlation IDs"""
    import uuid
    import time
    
    # Generate correlation ID
    correlation_id = str(uuid.uuid4())
    
    # Add correlation ID to request state
    request.state.correlation_id = correlation_id
    
    # Log request start
    start_time = time.time()
    logger.info(
        f"Request started",
        extra={
            "correlation_id": correlation_id,
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host if request.client else None
        }
    )
    
    try:
        # Process request
        response = await call_next(request)
        
        # Log request completion
        duration = time.time() - start_time
        logger.info(
            f"Request completed",
            extra={
                "correlation_id": correlation_id,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2)
            }
        )
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
        
    except Exception as e:
        # Log request error
        duration = time.time() - start_time
        logger.error(
            f"Request failed",
            extra={
                "correlation_id": correlation_id,
                "error": str(e),
                "duration_ms": round(duration * 1000, 2)
            }
        )
        raise


# Export commonly used dependencies
__all__ = [
    'get_db_manager',
    'get_db_service', 
    'get_healthy_db_service',
    'get_repository_factory_dep',
    'verify_api_key',
    'handle_database_errors',
    'validate_project_id',
    'validate_pagination',
    'get_project_or_404',
    'log_request_middleware'
]

