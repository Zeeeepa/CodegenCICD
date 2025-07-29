"""
Health check endpoints for CodegenCICD Dashboard
Provides comprehensive system health monitoring
"""
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import aiohttp
import asyncpg
import redis.asyncio as redis
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
import structlog

from backend.core.settings import get_settings
from backend.core.database import get_database

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


class HealthStatus(BaseModel):
    """Health check response model"""
    status: str
    timestamp: datetime
    version: str
    environment: str
    uptime_seconds: float
    checks: Dict[str, Any]


class ServiceCheck(BaseModel):
    """Individual service health check"""
    status: str  # "healthy", "unhealthy", "degraded"
    response_time_ms: Optional[float] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# Application start time for uptime calculation
_start_time = time.time()


async def check_database() -> ServiceCheck:
    """Check PostgreSQL database connectivity"""
    start_time = time.time()
    
    try:
        settings = get_settings()
        
        # Test database connection
        conn = await asyncpg.connect(settings.database_url)
        
        # Simple query to verify database is responsive
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        
        if result == 1:
            response_time = (time.time() - start_time) * 1000
            return ServiceCheck(
                status="healthy",
                response_time_ms=response_time,
                details={"connection": "successful", "query_result": result}
            )
        else:
            return ServiceCheck(
                status="unhealthy",
                error="Database query returned unexpected result"
            )
            
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return ServiceCheck(
            status="unhealthy",
            error=str(e)
        )


async def check_redis() -> ServiceCheck:
    """Check Redis connectivity"""
    start_time = time.time()
    
    try:
        settings = get_settings()
        
        # Create Redis connection
        redis_client = redis.from_url(settings.redis_url)
        
        # Test Redis with ping
        result = await redis_client.ping()
        await redis_client.close()
        
        if result:
            response_time = (time.time() - start_time) * 1000
            return ServiceCheck(
                status="healthy",
                response_time_ms=response_time,
                details={"ping": "successful"}
            )
        else:
            return ServiceCheck(
                status="unhealthy",
                error="Redis ping failed"
            )
            
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return ServiceCheck(
            status="unhealthy",
            error=str(e)
        )


async def check_external_service(name: str, url: str, timeout: int = 5) -> ServiceCheck:
    """Check external service connectivity"""
    start_time = time.time()
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(f"{url}/health") as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    return ServiceCheck(
                        status="healthy",
                        response_time_ms=response_time,
                        details={"http_status": response.status}
                    )
                else:
                    return ServiceCheck(
                        status="degraded",
                        response_time_ms=response_time,
                        error=f"HTTP {response.status}",
                        details={"http_status": response.status}
                    )
                    
    except asyncio.TimeoutError:
        return ServiceCheck(
            status="unhealthy",
            error=f"Timeout after {timeout}s"
        )
    except Exception as e:
        logger.error(f"{name} health check failed", error=str(e))
        return ServiceCheck(
            status="unhealthy",
            error=str(e)
        )


async def check_grainchain() -> ServiceCheck:
    """Check Grainchain service"""
    settings = get_settings()
    if not settings.grainchain_enabled:
        return ServiceCheck(status="disabled")
    
    return await check_external_service("grainchain", settings.grainchain_url)


async def check_web_eval() -> ServiceCheck:
    """Check Web-Eval-Agent service"""
    settings = get_settings()
    if not settings.web_eval_enabled:
        return ServiceCheck(status="disabled")
    
    return await check_external_service("web-eval-agent", settings.web_eval_url)


async def check_graph_sitter() -> ServiceCheck:
    """Check Graph-Sitter service"""
    settings = get_settings()
    if not settings.graph_sitter_enabled:
        return ServiceCheck(status="disabled")
    
    return await check_external_service("graph-sitter", settings.graph_sitter_url)


@router.get("/", response_model=HealthStatus)
async def health_check():
    """
    Comprehensive health check endpoint
    Returns overall system health and individual service status
    """
    settings = get_settings()
    current_time = datetime.now(timezone.utc)
    uptime = time.time() - _start_time
    
    # Run all health checks concurrently
    checks = await asyncio.gather(
        check_database(),
        check_redis(),
        check_grainchain(),
        check_web_eval(),
        check_graph_sitter(),
        return_exceptions=True
    )
    
    # Process results
    health_checks = {
        "database": checks[0] if not isinstance(checks[0], Exception) else ServiceCheck(status="unhealthy", error=str(checks[0])),
        "redis": checks[1] if not isinstance(checks[1], Exception) else ServiceCheck(status="unhealthy", error=str(checks[1])),
        "grainchain": checks[2] if not isinstance(checks[2], Exception) else ServiceCheck(status="unhealthy", error=str(checks[2])),
        "web_eval": checks[3] if not isinstance(checks[3], Exception) else ServiceCheck(status="unhealthy", error=str(checks[3])),
        "graph_sitter": checks[4] if not isinstance(checks[4], Exception) else ServiceCheck(status="unhealthy", error=str(checks[4])),
    }
    
    # Determine overall status
    critical_services = ["database", "redis"]
    overall_status = "healthy"
    
    for service_name, check in health_checks.items():
        if service_name in critical_services and check.status == "unhealthy":
            overall_status = "unhealthy"
            break
        elif check.status == "unhealthy":
            overall_status = "degraded"
    
    return HealthStatus(
        status=overall_status,
        timestamp=current_time,
        version=getattr(settings, 'version', '1.0.0'),
        environment=settings.environment,
        uptime_seconds=uptime,
        checks={name: check.dict() for name, check in health_checks.items()}
    )


@router.get("/liveness")
async def liveness_check():
    """
    Simple liveness check for monitoring systems
    Returns 200 if the application is running
    """
    return {"status": "alive", "timestamp": datetime.now(timezone.utc)}


@router.get("/readiness")
async def readiness_check():
    """
    Readiness check for monitoring systems
    Returns 200 only if critical services are available
    """
    try:
        # Check critical services only
        db_check = await check_database()
        redis_check = await check_redis()
        
        if db_check.status == "healthy" and redis_check.status == "healthy":
            return {
                "status": "ready",
                "timestamp": datetime.now(timezone.utc),
                "checks": {
                    "database": db_check.dict(),
                    "redis": redis_check.dict()
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Critical services not ready"
            )
            
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Readiness check failed: {str(e)}"
        )


@router.get("/metrics")
async def health_metrics():
    """
    Health metrics endpoint for monitoring systems
    Returns detailed metrics about system health
    """
    settings = get_settings()
    current_time = datetime.now(timezone.utc)
    uptime = time.time() - _start_time
    
    # Get detailed health information
    health_data = await health_check()
    
    # Calculate service availability
    total_services = len(health_data.checks)
    healthy_services = sum(1 for check in health_data.checks.values() if check["status"] == "healthy")
    availability_percentage = (healthy_services / total_services) * 100 if total_services > 0 else 0
    
    return {
        "timestamp": current_time,
        "uptime_seconds": uptime,
        "overall_status": health_data.status,
        "service_availability_percentage": availability_percentage,
        "healthy_services": healthy_services,
        "total_services": total_services,
        "environment": settings.environment,
        "config_tier": settings.config_tier,
        "version": getattr(settings, 'version', '1.0.0'),
        "checks": health_data.checks
    }
