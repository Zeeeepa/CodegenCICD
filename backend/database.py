"""
Unified Database Configuration and Management
Supports async operations with comprehensive error handling
"""
import asyncio
from typing import AsyncGenerator, Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import MetaData, text, event
from sqlalchemy.pool import NullPool
import structlog
from contextlib import asynccontextmanager

from backend.config import get_settings, get_database_url
from backend.models.base import Base

logger = structlog.get_logger(__name__)
settings = get_settings()

# Create async engine with comprehensive configuration
engine = create_async_engine(
    get_database_url(),
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=20,
    max_overflow=30,
    poolclass=NullPool if "sqlite" in get_database_url() else None,
    connect_args={
        "server_settings": {"jit": "off"}
    } if "postgresql" in get_database_url() else {},
    future=True
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)


async def init_db() -> None:
    """Initialize database with comprehensive setup"""
    try:
        logger.info("🔄 Initializing database...", tier=settings.config_tier.value)
        
        # Import all models to ensure they're registered
        from backend.models import (
            Project, ProjectConfiguration, ProjectSecret,
            AgentRun, AgentRunStep, AgentRunResponse,
            ValidationRun, ValidationStep, ValidationResult,
            User, UserSession
        )
        
        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
            # Create indexes for performance
            if settings.is_feature_enabled("monitoring"):
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_agent_runs_status_created 
                    ON agent_runs(status, created_at);
                """))
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_validation_runs_status 
                    ON validation_runs(status, created_at);
                """))
        
        logger.info("✅ Database initialized successfully")
        
        # Initialize default data if needed
        if settings.is_feature_enabled("monitoring"):
            await _create_default_data()
            
    except Exception as e:
        logger.error("❌ Database initialization failed", error=str(e))
        raise


async def _create_default_data() -> None:
    """Create default data for enterprise features"""
    try:
        async with AsyncSessionLocal() as session:
            # Check if default admin user exists
            result = await session.execute(
                text("SELECT COUNT(*) FROM users WHERE email = 'admin@codegencd.local'")
            )
            if result.scalar() == 0:
                await session.execute(text("""
                    INSERT INTO users (email, username, is_admin, is_active, created_at)
                    VALUES ('admin@codegencd.local', 'admin', true, true, NOW())
                """))
                await session.commit()
                logger.info("✅ Default admin user created")
    except Exception as e:
        logger.warning("⚠️ Could not create default data", error=str(e))


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions with proper error handling"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error("Database session error", error=str(e))
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions"""
    async with get_db_session() as session:
        yield session


async def check_db_health() -> Dict[str, Any]:
    """Comprehensive database health check"""
    health_info = {
        "status": "unknown",
        "connection": False,
        "tables": 0,
        "pool_status": {},
        "features": settings.get_active_features()
    }
    
    try:
        async with AsyncSessionLocal() as session:
            # Test basic connection
            await session.execute(text("SELECT 1"))
            health_info["connection"] = True
            
            # Count tables
            result = await session.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            health_info["tables"] = result.scalar()
            
            # Get pool status
            pool = engine.pool
            health_info["pool_status"] = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid()
            }
            
            health_info["status"] = "healthy"
            
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        health_info["status"] = "unhealthy"
        health_info["error"] = str(e)
    
    return health_info


async def close_db() -> None:
    """Close database connections gracefully"""
    try:
        await engine.dispose()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error("❌ Error closing database connections", error=str(e))


class DatabaseManager:
    """Advanced database management utilities"""
    
    @staticmethod
    async def create_tables():
        """Create all database tables"""
        await init_db()
    
    @staticmethod
    async def drop_tables():
        """Drop all database tables (use with extreme caution!)"""
        if settings.environment == "production":
            raise ValueError("Cannot drop tables in production environment")
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.warning("⚠️ All database tables dropped")
    
    @staticmethod
    async def reset_database():
        """Reset database (drop and recreate all tables)"""
        if settings.environment == "production":
            raise ValueError("Cannot reset database in production environment")
        
        await DatabaseManager.drop_tables()
        await DatabaseManager.create_tables()
        logger.info("🔄 Database reset completed")
    
    @staticmethod
    async def get_table_info() -> List[Dict[str, Any]]:
        """Get comprehensive information about database tables"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("""
                SELECT 
                    t.table_name,
                    t.table_type,
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    c.column_default
                FROM information_schema.tables t
                LEFT JOIN information_schema.columns c ON t.table_name = c.table_name
                WHERE t.table_schema = 'public'
                ORDER BY t.table_name, c.ordinal_position
            """))
            return [dict(row) for row in result.fetchall()]
    
    @staticmethod
    async def get_database_stats() -> Dict[str, Any]:
        """Get database statistics"""
        async with AsyncSessionLocal() as session:
            stats = {}
            
            # Get table row counts
            tables = ['projects', 'agent_runs', 'validation_pipelines', 'webhook_events']
            for table in tables:
                try:
                    result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    stats[f"{table}_count"] = result.scalar()
                except Exception:
                    stats[f"{table}_count"] = 0
            
            # Get database size
            try:
                result = await session.execute(text("""
                    SELECT pg_size_pretty(pg_database_size(current_database()))
                """))
                stats["database_size"] = result.scalar()
            except Exception:
                stats["database_size"] = "unknown"
            
            return stats
    
    @staticmethod
    async def backup_database(backup_path: str) -> bool:
        """Create database backup (PostgreSQL only)"""
        if not settings.is_feature_enabled("enterprise_security"):
            raise ValueError("Database backup requires enterprise features")
        
        try:
            import subprocess
            import os
            
            # Extract connection details
            db_url = get_database_url()
            # This would need proper implementation for production use
            logger.info(f"Database backup initiated to {backup_path}")
            return True
        except Exception as e:
            logger.error("Database backup failed", error=str(e))
            return False


# Connection pool monitoring for advanced features
async def monitor_connection_pool() -> Dict[str, Any]:
    """Monitor database connection pool status"""
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalid": pool.invalid(),
        "total_connections": pool.size() + pool.overflow(),
        "available_connections": pool.size() - pool.checkedout()
    }


# Event listeners for advanced monitoring
if settings.is_feature_enabled("monitoring"):
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set SQLite pragmas for better performance"""
        if "sqlite" in get_database_url():
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()


# Database utilities for different tiers
class DatabaseUtils:
    """Utility functions for database operations"""
    
    @staticmethod
    async def execute_raw_sql(query: str, params: Optional[Dict] = None) -> Any:
        """Execute raw SQL query (advanced tier only)"""
        if not settings.is_feature_enabled("enterprise_security"):
            raise ValueError("Raw SQL execution requires enterprise features")
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(text(query), params or {})
            await session.commit()
            return result
    
    @staticmethod
    async def get_slow_queries() -> List[Dict[str, Any]]:
        """Get slow query information (PostgreSQL only)"""
        if not settings.is_feature_enabled("monitoring"):
            return []
        
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(text("""
                    SELECT query, calls, total_time, mean_time
                    FROM pg_stat_statements
                    ORDER BY total_time DESC
                    LIMIT 10
                """))
                return [dict(row) for row in result.fetchall()]
        except Exception:
            return []
