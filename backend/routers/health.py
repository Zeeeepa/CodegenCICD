"""
Health check router for CodegenCICD Dashboard
"""
from fastapi import APIRouter, Depends
from typing import Dict, Any
import structlog

from backend.config import get_settings
from backend.database import check_db_health

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter()


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Comprehensive health check endpoint"""
    try:
        # Check database health
        db_health = await check_db_health()
        
        # Basic health status
        health_status = {
            "status": "healthy" if db_health["status"] == "healthy" else "unhealthy",
            "service": "CodegenCICD Dashboard",
            "version": settings.version,
            "environment": settings.environment,
            "config_tier": settings.config_tier.value,
            "timestamp": _get_timestamp(),
            "database": db_health,
            "features": settings.get_active_features()
        }
        
        # Add service-specific health checks based on enabled features
        if settings.is_feature_enabled("websocket_updates"):
            # TODO: Add WebSocket service health check
            health_status["websocket"] = {
                "status": "healthy",
                "active_connections": 0  # Placeholder
            }
        
        if settings.is_feature_enabled("background_tasks"):
            # TODO: Add Celery health check
            health_status["background_tasks"] = {
                "status": "healthy",
                "active_workers": 0  # Placeholder
            }
        
        if settings.is_feature_enabled("monitoring"):
            # TODO: Add monitoring service health check
            health_status["monitoring"] = {
                "status": "healthy",
                "metrics_enabled": True
            }
        
        return health_status
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "service": "CodegenCICD Dashboard",
            "error": str(e),
            "timestamp": _get_timestamp()
        }


@router.get("/database")
async def database_health() -> Dict[str, Any]:
    """Database-specific health check"""
    try:
        db_health = await check_db_health()
        return {
            "timestamp": _get_timestamp(),
            **db_health
        }
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": _get_timestamp()
        }


@router.get("/services")
async def services_health() -> Dict[str, Any]:
    """Health check for all services"""
    services_status = {}
    
    try:
        # Database
        db_health = await check_db_health()
        services_status["database"] = db_health
        
        # External services health checks
        services_status["codegen_api"] = await _check_codegen_api_health()
        services_status["github_api"] = await _check_github_api_health()
        
        if settings.gemini_api_key:
            services_status["gemini_api"] = await _check_gemini_api_health()
        
        # Validation tools
        if settings.grainchain_enabled:
            services_status["grainchain"] = await _check_grainchain_health()
        
        if settings.web_eval_enabled:
            services_status["web_eval_agent"] = await _check_web_eval_health()
        
        if settings.graph_sitter_enabled:
            services_status["graph_sitter"] = await _check_graph_sitter_health()
        
        # Overall status
        all_healthy = all(
            service.get("status") == "healthy" 
            for service in services_status.values()
        )
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": _get_timestamp(),
            "services": services_status
        }
        
    except Exception as e:
        logger.error("Services health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": _get_timestamp(),
            "services": services_status
        }


async def _check_codegen_api_health() -> Dict[str, Any]:
    """Check Codegen API health"""
    try:
        # TODO: Implement actual Codegen API health check
        return {
            "status": "healthy",
            "response_time_ms": 0,
            "api_key_configured": bool(settings.codegen_api_token)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def _check_github_api_health() -> Dict[str, Any]:
    """Check GitHub API health"""
    try:
        # TODO: Implement actual GitHub API health check
        return {
            "status": "healthy",
            "response_time_ms": 0,
            "token_configured": bool(settings.github_token)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def _check_gemini_api_health() -> Dict[str, Any]:
    """Check Gemini API health"""
    try:
        # TODO: Implement actual Gemini API health check
        return {
            "status": "healthy",
            "response_time_ms": 0,
            "api_key_configured": bool(settings.gemini_api_key)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def _check_grainchain_health() -> Dict[str, Any]:
    """Check grainchain service health"""
    try:
        # TODO: Implement actual grainchain health check
        return {
            "status": "healthy",
            "response_time_ms": 0,
            "enabled": settings.grainchain_enabled
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def _check_web_eval_health() -> Dict[str, Any]:
    """Check web-eval-agent service health"""
    try:
        # TODO: Implement actual web-eval-agent health check
        return {
            "status": "healthy",
            "response_time_ms": 0,
            "enabled": settings.web_eval_enabled
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def _check_graph_sitter_health() -> Dict[str, Any]:
    """Check graph-sitter service health"""
    try:
        # TODO: Implement actual graph-sitter health check
        return {
            "status": "healthy",
            "response_time_ms": 0,
            "enabled": settings.graph_sitter_enabled
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def _get_timestamp() -> str:
    """Get current timestamp in ISO format"""
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"

