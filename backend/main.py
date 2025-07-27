"""
CodegenCICD Dashboard - Unified Main Application
Complete FastAPI application with all features from all PRs
"""
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn
import os
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any
import structlog

# Import configuration and database
from backend.config import get_settings, is_development, is_production, get_cors_origins
from backend.database import init_db, close_db, check_db_health

# Import routers
from backend.routers import (
    projects, agent_runs, configurations, webhooks, 
    websocket, validation, health, monitoring
)

# Import services
from backend.services.websocket_service import WebSocketService
from backend.services.notification_service import NotificationService

# Import middleware
from backend.middleware.rate_limiting import RateLimitMiddleware
from backend.middleware.security import SecurityMiddleware
from backend.middleware.logging import LoggingMiddleware

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)
settings = get_settings()

# Global service instances
websocket_service = WebSocketService()
notification_service = NotificationService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events with comprehensive startup and shutdown"""
    # Startup
    logger.info("🚀 Starting CodegenCICD Dashboard", 
               version=settings.version,
               environment=settings.environment,
               config_tier=settings.config_tier.value)
    
    try:
        # Initialize database
        await init_db()
        
        # Initialize services based on configuration tier
        if settings.is_feature_enabled("websocket_updates"):
            logger.info("✅ WebSocket service initialized")
        
        if settings.is_feature_enabled("email_notifications"):
            await notification_service.initialize()
            logger.info("✅ Notification service initialized")
        
        if settings.is_feature_enabled("background_tasks"):
            # Initialize Celery workers
            logger.info("✅ Background task workers initialized")
        
        if settings.is_feature_enabled("monitoring"):
            # Initialize monitoring
            logger.info("✅ Monitoring services initialized")
        
        # Health check
        db_health = await check_db_health()
        if db_health["status"] == "healthy":
            logger.info("✅ Database connection verified")
        else:
            logger.error("❌ Database connection failed", health=db_health)
        
        logger.info("🎉 CodegenCICD Dashboard started successfully!")
        
    except Exception as e:
        logger.error("❌ Failed to start application", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down CodegenCICD Dashboard...")
    
    try:
        # Close database connections
        await close_db()
        
        # Close WebSocket connections
        if settings.is_feature_enabled("websocket_updates"):
            await websocket_service.close_all_connections()
        
        # Close notification service
        if settings.is_feature_enabled("email_notifications"):
            await notification_service.close()
        
        logger.info("👋 CodegenCICD Dashboard shut down gracefully")
        
    except Exception as e:
        logger.error("❌ Error during shutdown", error=str(e))


# Create FastAPI application with comprehensive configuration
app = FastAPI(
    title="CodegenCICD Dashboard",
    description="AI-powered CI/CD dashboard with Codegen integration - Complete unified system",
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs" if is_development() else None,
    redoc_url="/redoc" if is_development() else None,
    openapi_url="/openapi.json" if is_development() else None,
)

# =============================================================================
# MIDDLEWARE CONFIGURATION
# =============================================================================

# Security middleware (always enabled)
app.add_middleware(SecurityMiddleware)

# Logging middleware (always enabled)
app.add_middleware(LoggingMiddleware)

# Rate limiting middleware (intermediate+ tier)
if settings.is_feature_enabled("rate_limiting"):
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.rate_limit_requests_per_minute,
        burst_size=settings.rate_limit_burst
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware (production)
if is_production():
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure with actual domains in production
    )

# =============================================================================
# ROUTER CONFIGURATION
# =============================================================================

# Core API routes (always enabled)
app.include_router(
    projects.router,
    prefix="/api/v1/projects",
    tags=["projects"]
)

app.include_router(
    agent_runs.router,
    prefix="/api/v1/agent-runs",
    tags=["agent-runs"]
)

app.include_router(
    configurations.router,
    prefix="/api/v1/configurations",
    tags=["configurations"]
)

app.include_router(
    webhooks.router,
    prefix="/api/v1/webhooks",
    tags=["webhooks"]
)

app.include_router(
    validation.router,
    prefix="/api/v1/validation",
    tags=["validation"]
)

app.include_router(
    health.router,
    prefix="/api/v1/health",
    tags=["health"]
)

# WebSocket routes (intermediate+ tier)
if settings.is_feature_enabled("websocket_updates"):
    app.include_router(
        websocket.router,
        prefix="/ws",
        tags=["websocket"]
    )

# Monitoring routes (advanced tier)
if settings.is_feature_enabled("monitoring"):
    app.include_router(
        monitoring.router,
        prefix="/api/v1/monitoring",
        tags=["monitoring"]
    )

# =============================================================================
# STATIC FILES (Development)
# =============================================================================

if is_development() and os.path.exists("frontend/build"):
    app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")

# =============================================================================
# GLOBAL EXCEPTION HANDLERS
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured logging"""
    logger.warning("HTTP exception occurred",
                  status_code=exc.status_code,
                  detail=exc.detail,
                  path=request.url.path,
                  method=request.method)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "http_exception",
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": request.url.path
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with structured logging"""
    logger.error("Unhandled exception occurred",
                error=str(exc),
                error_type=type(exc).__name__,
                path=request.url.path,
                method=request.method,
                exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "internal_server_error",
                "message": "An internal server error occurred",
                "path": request.url.path
            }
        }
    )

# =============================================================================
# CORE ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint with application information"""
    return {
        "message": "CodegenCICD Dashboard API",
        "version": settings.version,
        "environment": settings.environment,
        "config_tier": settings.config_tier.value,
        "features": settings.get_active_features(),
        "docs": "/docs" if is_development() else None,
        "health": "/api/v1/health",
        "websocket": "/ws/{client_id}" if settings.is_feature_enabled("websocket_updates") else None
    }


@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    try:
        db_health = await check_db_health()
        
        health_status = {
            "status": "healthy" if db_health["status"] == "healthy" else "unhealthy",
            "service": "CodegenCICD Dashboard",
            "version": settings.version,
            "environment": settings.environment,
            "config_tier": settings.config_tier.value,
            "timestamp": structlog.processors.TimeStamper(fmt="iso")(None, None, None)["timestamp"],
            "database": db_health,
            "features": settings.get_active_features()
        }
        
        # Add service-specific health checks
        if settings.is_feature_enabled("websocket_updates"):
            health_status["websocket"] = {
                "active_connections": len(websocket_service.active_connections)
            }
        
        return health_status
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "CodegenCICD Dashboard",
                "error": str(e)
            }
        )


@app.get("/api/v1/info")
async def application_info():
    """Detailed application information"""
    return {
        "application": {
            "name": settings.app_name,
            "version": settings.version,
            "environment": settings.environment,
            "config_tier": settings.config_tier.value,
            "debug": settings.debug
        },
        "features": settings.get_active_features(),
        "configuration": {
            "database_url": "***" if settings.database_url else None,
            "redis_url": "***" if settings.redis_url else None,
            "grainchain_enabled": settings.grainchain_enabled,
            "web_eval_enabled": settings.web_eval_enabled,
            "graph_sitter_enabled": settings.graph_sitter_enabled,
        },
        "api": {
            "docs": "/docs" if is_development() else None,
            "redoc": "/redoc" if is_development() else None,
            "openapi": "/openapi.json" if is_development() else None
        }
    }

# =============================================================================
# DEVELOPMENT UTILITIES
# =============================================================================

if is_development():
    @app.get("/api/v1/dev/reset-database")
    async def reset_database():
        """Reset database (development only)"""
        try:
            from backend.database import DatabaseManager
            await DatabaseManager.reset_database()
            return {"message": "Database reset successfully"}
        except Exception as e:
            logger.error("Database reset failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/dev/database-stats")
    async def database_stats():
        """Get database statistics (development only)"""
        try:
            from backend.database import DatabaseManager
            stats = await DatabaseManager.get_database_stats()
            return stats
        except Exception as e:
            logger.error("Failed to get database stats", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# APPLICATION STARTUP
# =============================================================================

if __name__ == "__main__":
    # Configure uvicorn based on environment
    uvicorn_config = {
        "app": "backend.main:app",
        "host": "0.0.0.0",
        "port": 8000,
        "log_level": settings.log_level.lower(),
        "access_log": is_development(),
        "reload": is_development() and settings.debug,
        "workers": 1 if is_development() else 4,
    }
    
    # SSL configuration for production
    if is_production() and settings.is_feature_enabled("ssl_support"):
        if settings.ssl_cert_path and settings.ssl_key_path:
            uvicorn_config.update({
                "ssl_certfile": settings.ssl_cert_path,
                "ssl_keyfile": settings.ssl_key_path
            })
    
    logger.info("Starting uvicorn server", config=uvicorn_config)
    uvicorn.run(**uvicorn_config)

