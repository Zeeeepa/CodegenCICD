"""
FastAPI dependency injection for database services
"""

from functools import lru_cache
from .services.database_service import DatabaseService


@lru_cache()
def get_database_service() -> DatabaseService:
    """Get database service instance (singleton)"""
    return DatabaseService()


# Dependency for FastAPI routes
async def get_db_service() -> DatabaseService:
    """FastAPI dependency for database service"""
    return get_database_service()

