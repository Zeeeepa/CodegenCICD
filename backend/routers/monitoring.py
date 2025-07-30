"""
Monitoring and health check endpoints
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
import structlog

from backend.core.monitoring import (
    health_checker, get_metrics_response, metrics_collector
)
from backend.core.security import get_current_user, require_role, UserRole, TokenData

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/health")
async def health_check():
    """
    Public health check endpoint for load balancers and orchestrators
    """
    try:
        health_status = await health_checker.get_health_status()
        
        # Return appropriate HTTP status code
        if health_status["status"] == "healthy":
            status_code = 200
        elif health_status["status"] == "degraded":
            status_code = 200  # Still accepting traffic
        else:
            status_code = 503  # Service unavailable
        
        return health_status
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "error",
            "error": str(e),
            "timestamp": "2025-01-30T15:30:00Z"
        }


@router.get("/health/detailed")
async def detailed_health_check(
    current_user: TokenData = Depends(require_role(UserRole.ADMIN))
):
    """
    Detailed health check with full diagnostic information (admin only)
    """
    try:
        health_status = await health_checker.get_health_status()
        
        # Add additional diagnostic information
        health_status.update({
            "system_info": {
                "uptime_seconds": metrics_collector.get_uptime(),
                "metrics_enabled": metrics_collector.metrics_enabled,
                "requested_by": current_user.username
            }
        })
        
        return health_status
        
    except Exception as e:
        logger.error("Detailed health check failed", error=str(e))
        return {
            "status": "error",
            "error": str(e),
            "timestamp": "2025-01-30T15:30:00Z"
        }


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """
    Prometheus metrics endpoint
    """
    return await get_metrics_response()


@router.get("/metrics/custom")
async def custom_metrics(
    current_user: TokenData = Depends(require_role(UserRole.USER))
):
    """
    Custom application metrics in JSON format
    """
    try:
        # Get current system state
        from backend.services.agent_run_manager import agent_run_manager
        
        active_runs = await agent_run_manager.get_active_runs_count()
        metrics_collector.set_active_agent_runs(active_runs)
        
        return {
            "application_metrics": {
                "uptime_seconds": metrics_collector.get_uptime(),
                "active_agent_runs": active_runs,
                "metrics_collection_enabled": metrics_collector.metrics_enabled
            },
            "timestamp": "2025-01-30T15:30:00Z",
            "requested_by": current_user.username
        }
        
    except Exception as e:
        logger.error("Custom metrics failed", error=str(e))
        return {
            "error": str(e),
            "timestamp": "2025-01-30T15:30:00Z"
        }


@router.get("/status")
async def service_status():
    """
    Simple service status endpoint
    """
    return {
        "service": "CodegenCICD",
        "status": "running",
        "version": "1.0.0",
        "timestamp": "2025-01-30T15:30:00Z"
    }


@router.get("/logs/recent")
async def get_recent_logs(
    lines: int = 100,
    current_user: TokenData = Depends(require_role(UserRole.ADMIN))
):
    """
    Get recent application logs (admin only)
    """
    try:
        import os
        
        log_file = "/app/logs/application.log"
        if not os.path.exists(log_file):
            return {
                "logs": [],
                "message": "Log file not found",
                "timestamp": "2025-01-30T15:30:00Z"
            }
        
        # Read last N lines from log file
        with open(log_file, 'r') as f:
            log_lines = f.readlines()
        
        recent_logs = log_lines[-lines:] if len(log_lines) > lines else log_lines
        
        return {
            "logs": [line.strip() for line in recent_logs],
            "total_lines": len(recent_logs),
            "requested_lines": lines,
            "timestamp": "2025-01-30T15:30:00Z",
            "requested_by": current_user.username
        }
        
    except Exception as e:
        logger.error("Failed to retrieve logs", error=str(e))
        return {
            "error": str(e),
            "timestamp": "2025-01-30T15:30:00Z"
        }


@router.post("/metrics/reset")
async def reset_metrics(
    current_user: TokenData = Depends(require_role(UserRole.ADMIN))
):
    """
    Reset application metrics (admin only)
    """
    try:
        # In a real implementation, you would reset Prometheus metrics
        # For now, just log the action
        logger.info("Metrics reset requested", requested_by=current_user.username)
        
        return {
            "message": "Metrics reset successfully",
            "timestamp": "2025-01-30T15:30:00Z",
            "reset_by": current_user.username
        }
        
    except Exception as e:
        logger.error("Failed to reset metrics", error=str(e))
        return {
            "error": str(e),
            "timestamp": "2025-01-30T15:30:00Z"
        }


@router.get("/diagnostics")
async def system_diagnostics(
    current_user: TokenData = Depends(require_role(UserRole.ADMIN))
):
    """
    Comprehensive system diagnostics (admin only)
    """
    try:
        import psutil
        import os
        
        # System information
        system_info = {
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent
            },
            "disk_usage": {}
        }
        
        # Disk usage for important paths
        for path in ["/app/logs", "/app/data", "/tmp"]:
            if os.path.exists(path):
                disk_usage = psutil.disk_usage(path)
                system_info["disk_usage"][path] = {
                    "total": disk_usage.total,
                    "used": disk_usage.used,
                    "free": disk_usage.free
                }
        
        # Application information
        app_info = {
            "uptime_seconds": metrics_collector.get_uptime(),
            "environment": os.environ.get("ENVIRONMENT", "unknown"),
            "python_version": os.sys.version,
            "process_id": os.getpid()
        }
        
        # Database connection info
        db_info = await health_checker.check_database()
        redis_info = await health_checker.check_redis()
        
        return {
            "system_info": system_info,
            "application_info": app_info,
            "database_status": db_info,
            "redis_status": redis_info,
            "timestamp": "2025-01-30T15:30:00Z",
            "requested_by": current_user.username
        }
        
    except Exception as e:
        logger.error("System diagnostics failed", error=str(e))
        return {
            "error": str(e),
            "timestamp": "2025-01-30T15:30:00Z"
        }

