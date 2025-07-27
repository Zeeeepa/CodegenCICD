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
    """Check grainchain service health with enhanced monitoring"""
    try:
        from backend.integrations.grainchain_client import EnhancedGrainchainClient
        
        client = EnhancedGrainchainClient()
        
        # Perform comprehensive health check
        health_check_result = await client.perform_health_check()
        client_health = client.get_health_status()
        
        return {
            "status": "healthy" if health_check_result["service_available"] else "unhealthy",
            "response_time_ms": int(health_check_result["response_time"] * 1000),
            "enabled": settings.grainchain_enabled,
            "service_available": health_check_result["service_available"],
            "client_health_score": client_health["health_score"],
            "client_status": client_health["status"],
            "issues": client_health["issues"],
            "correlation_id": health_check_result["correlation_id"]
        }
    except Exception as e:
        logger.error("Enhanced grainchain health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "enabled": settings.grainchain_enabled
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


# Enhanced monitoring endpoints for production-ready features

@router.get("/enhanced")
async def enhanced_health_check() -> Dict[str, Any]:
    """Enhanced health check with comprehensive monitoring"""
    try:
        from backend.services.resource_manager import resource_manager
        from backend.utils.circuit_breaker import circuit_breaker_manager
        from backend.utils.connection_pool import connection_pool_manager
        
        # Get resource manager stats
        resource_stats = resource_manager.get_resource_stats()
        
        # Get circuit breaker states
        circuit_breaker_states = circuit_breaker_manager.get_all_states()
        
        # Get connection pool health
        pool_health = connection_pool_manager.get_all_health_status()
        
        # Calculate overall health score
        health_score = 100
        issues = []
        
        # Check resource management health
        if resource_stats["quota_violations"] > 0:
            health_score -= 20
            issues.append(f"Resource quota violations: {resource_stats['quota_violations']}")
        
        if resource_stats["expired_resources"] > 10:
            health_score -= 15
            issues.append(f"High number of expired resources: {resource_stats['expired_resources']}")
        
        # Check circuit breakers
        open_breakers = sum(1 for state in circuit_breaker_states.values() 
                           if state["state"] == "open")
        if open_breakers > 0:
            health_score -= 30
            issues.append(f"Open circuit breakers: {open_breakers}")
        
        # Check connection pools
        unhealthy_pools = sum(1 for health in pool_health.values() 
                             if health["status"] in ["unhealthy", "degraded"])
        if unhealthy_pools > 0:
            health_score -= 25
            issues.append(f"Unhealthy connection pools: {unhealthy_pools}")
        
        # Determine overall status
        if health_score >= 80:
            status = "healthy"
        elif health_score >= 50:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "health_score": max(0, health_score),
            "issues": issues,
            "timestamp": _get_timestamp(),
            "components": {
                "resource_manager": {
                    "status": "healthy" if resource_stats["quota_violations"] == 0 else "degraded",
                    "stats": resource_stats
                },
                "circuit_breakers": {
                    "status": "healthy" if open_breakers == 0 else "degraded",
                    "states": circuit_breaker_states
                },
                "connection_pools": {
                    "status": "healthy" if unhealthy_pools == 0 else "degraded",
                    "health": pool_health
                }
            }
        }
        
    except Exception as e:
        logger.error("Enhanced health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": _get_timestamp()
        }


@router.get("/grainchain/detailed")
async def grainchain_detailed_health() -> Dict[str, Any]:
    """Detailed Grainchain health check with metrics"""
    try:
        from backend.integrations.grainchain_client import EnhancedGrainchainClient
        
        client = EnhancedGrainchainClient()
        
        # Get comprehensive metrics
        client_metrics = client.get_client_metrics()
        client_health = client.get_health_status()
        service_health = await client.perform_health_check()
        
        return {
            "timestamp": _get_timestamp(),
            "overall_status": "healthy" if (
                client_health["status"] == "healthy" and 
                service_health["service_available"]
            ) else "unhealthy",
            "client_health": client_health,
            "service_health": service_health,
            "detailed_metrics": client_metrics
        }
        
    except Exception as e:
        logger.error("Detailed Grainchain health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": _get_timestamp()
        }


@router.get("/resources")
async def resource_health() -> Dict[str, Any]:
    """Resource management health and statistics"""
    try:
        from backend.services.resource_manager import resource_manager
        
        stats = resource_manager.get_resource_stats()
        
        return {
            "timestamp": _get_timestamp(),
            "status": "healthy" if stats["quota_violations"] == 0 else "degraded",
            "stats": stats
        }
        
    except Exception as e:
        logger.error("Resource health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": _get_timestamp()
        }


@router.get("/circuit-breakers")
async def circuit_breaker_health() -> Dict[str, Any]:
    """Circuit breaker health and states"""
    try:
        from backend.utils.circuit_breaker import circuit_breaker_manager
        
        states = circuit_breaker_manager.get_all_states()
        
        # Check for open breakers
        open_breakers = sum(1 for state in states.values() if state["state"] == "open")
        
        return {
            "timestamp": _get_timestamp(),
            "status": "healthy" if open_breakers == 0 else "degraded",
            "open_breakers": open_breakers,
            "total_breakers": len(states),
            "states": states
        }
        
    except Exception as e:
        logger.error("Circuit breaker health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": _get_timestamp()
        }


@router.get("/connection-pools")
async def connection_pool_health() -> Dict[str, Any]:
    """Connection pool health and metrics"""
    try:
        from backend.utils.connection_pool import connection_pool_manager
        
        metrics = connection_pool_manager.get_all_metrics()
        health = connection_pool_manager.get_all_health_status()
        
        # Count unhealthy pools
        unhealthy_pools = sum(1 for h in health.values() 
                             if h["status"] in ["unhealthy", "degraded"])
        
        return {
            "timestamp": _get_timestamp(),
            "status": "healthy" if unhealthy_pools == 0 else "degraded",
            "unhealthy_pools": unhealthy_pools,
            "total_pools": len(health),
            "metrics": metrics,
            "health": health
        }
        
    except Exception as e:
        logger.error("Connection pool health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": _get_timestamp()
        }


@router.get("/readiness")
async def readiness_probe() -> Dict[str, Any]:
    """Kubernetes readiness probe endpoint"""
    try:
        from backend.services.resource_manager import resource_manager
        
        # Check if resource manager is running
        resource_stats = resource_manager.get_resource_stats()
        
        # Basic readiness criteria
        ready = True
        issues = []
        
        # Check if we have too many failed resources
        if resource_stats["lifecycle_stats"]["cleanup_failures"] > 10:
            ready = False
            issues.append("High number of cleanup failures")
        
        return {
            "ready": ready,
            "issues": issues,
            "timestamp": _get_timestamp()
        }
        
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        return {
            "ready": False,
            "issues": [f"Readiness check error: {str(e)}"],
            "timestamp": _get_timestamp()
        }


@router.get("/liveness")
async def liveness_probe() -> Dict[str, Any]:
    """Kubernetes liveness probe endpoint"""
    try:
        # Basic liveness check - just ensure the service is responding
        return {
            "alive": True,
            "timestamp": _get_timestamp()
        }
    except Exception as e:
        logger.error("Liveness check failed", error=str(e))
        return {
            "alive": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }
