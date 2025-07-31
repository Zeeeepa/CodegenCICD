"""
FastAPI dependency injection for database services
"""
from functools import lru_cache
from typing import Generator
import structlog

from backend.services.database_service import DatabaseService
from backend.repositories.project_repository import ProjectRepository
from backend.database import get_db_session

logger = structlog.get_logger(__name__)

@lru_cache()
def get_database_service() -> DatabaseService:
    """Get database service instance (cached)"""
    return DatabaseService()

def get_project_repository() -> ProjectRepository:
    """Get project repository instance"""
    return ProjectRepository()

def get_db_session_dependency() -> Generator:
    """FastAPI dependency for database session"""
    try:
        with get_db_session() as session:
            yield session
    except Exception as e:
        logger.error("Database session error", error=str(e))
        raise

# Dependency functions for FastAPI
async def get_database_service_dependency() -> DatabaseService:
    """FastAPI dependency for database service"""
    return get_database_service()

async def get_project_repository_dependency() -> ProjectRepository:
    """FastAPI dependency for project repository"""
    return get_project_repository()

