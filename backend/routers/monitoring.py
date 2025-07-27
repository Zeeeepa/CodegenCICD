"""
Monitoring router for CodegenCICD Dashboard
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import structlog
import psutil
import time
from datetime import datetime, timedelta

from backend.config import get_settings
from backend.database import check_db_health

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter()


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get system metrics for monitoring"""
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Database health
        db_health = await check_db_health()
        
        # Application metrics
        uptime = time.time() - psutil.boot_time()
        
        metrics = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "uptime_seconds": uptime
            },
            "database": db_health,
            "application": {
                "version": settings.version,
                "environment": settings.environment,
                "config_tier": settings.config_tier.value,
                "features_enabled": settings.get_active_features()
            }
        }
        
        # Add service-specific metrics if enabled
        if settings.is_feature_enabled("websocket_updates"):
            # TODO: Add WebSocket metrics
            metrics["websocket"] = {
                "active_connections": 0,
                "messages_sent": 0,
                "messages_received": 0
            }
        
        if settings.is_feature_enabled("background_tasks"):
            # TODO: Add Celery metrics
            metrics["background_tasks"] = {
                "active_workers": 0,
                "pending_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0
            }
        
        return metrics
        
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check for all components"""
    try:
        health_checks = {}
        overall_status = "healthy"
        
        # Database health
        db_health = await check_db_health()
        health_checks["database"] = db_health
        if db_health["status"] != "healthy":
            overall_status = "degraded"
        
        # External services health
        health_checks["external_services"] = {}
        
        # Codegen API
        try:
            from backend.integrations import CodegenClient
            async with CodegenClient() as client:
                codegen_health = await client.health_check()
                health_checks["external_services"]["codegen_api"] = codegen_health
                if codegen_health["status"] != "healthy":
                    overall_status = "degraded"
        except Exception as e:
            health_checks["external_services"]["codegen_api"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            overall_status = "degraded"
        
        # GitHub API
        try:
            from backend.integrations import GitHubClient
            async with GitHubClient() as client:
                github_health = await client.health_check()
                health_checks["external_services"]["github_api"] = github_health
                if github_health["status"] != "healthy":
                    overall_status = "degraded"
        except Exception as e:
            health_checks["external_services"]["github_api"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            overall_status = "degraded"
        
        # Gemini API
        if settings.gemini_api_key:
            try:
                from backend.integrations import GeminiClient
                async with GeminiClient() as client:
                    gemini_health = await client.health_check()
                    health_checks["external_services"]["gemini_api"] = gemini_health
                    if gemini_health["status"] != "healthy":
                        overall_status = "degraded"
            except Exception as e:
                health_checks["external_services"]["gemini_api"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                overall_status = "degraded"
        
        # Internal services health
        health_checks["internal_services"] = {}
        
        # WebSocket service
        if settings.is_feature_enabled("websocket_updates"):
            try:
                # TODO: Add actual WebSocket service health check
                health_checks["internal_services"]["websocket"] = {
                    "status": "healthy",
                    "active_connections": 0
                }
            except Exception as e:
                health_checks["internal_services"]["websocket"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                overall_status = "degraded"
        
        # Notification service
        if settings.is_feature_enabled("email_notifications"):
            try:
                # TODO: Add actual notification service health check
                health_checks["internal_services"]["notifications"] = {
                    "status": "healthy",
                    "queue_size": 0
                }
            except Exception as e:
                health_checks["internal_services"]["notifications"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                overall_status = "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": health_checks
        }
        
    except Exception as e:
        logger.error("Detailed health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e)
        }


@router.get("/stats")
async def get_application_stats() -> Dict[str, Any]:
    """Get application statistics"""
    try:
        # TODO: Implement actual statistics from database
        # For now, return placeholder data
        
        stats = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "projects": {
                "total": 0,
                "active": 0,
                "inactive": 0
            },
            "agent_runs": {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "running": 0,
                "pending": 0
            },
            "validation_runs": {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "running": 0,
                "pending": 0
            },
            "performance": {
                "average_agent_run_duration": 0,
                "average_validation_duration": 0,
                "success_rate": 0.0
            },
            "usage": {
                "total_tokens_used": 0,
                "total_cost_usd": "0.00",
                "prs_created": 0,
                "prs_merged": 0
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error("Failed to get application stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve application statistics")


@router.get("/logs")
async def get_recent_logs(
    level: str = "INFO",
    limit: int = 100,
    service: str = None
) -> List[Dict[str, Any]]:
    """Get recent application logs"""
    try:
        # TODO: Implement actual log retrieval from structured logging
        # For now, return placeholder data
        
        logs = []
        for i in range(min(limit, 10)):  # Return up to 10 placeholder logs
            logs.append({
                "timestamp": (datetime.utcnow() - timedelta(minutes=i)).isoformat() + "Z",
                "level": level,
                "service": service or "backend",
                "message": f"Sample log message {i}",
                "metadata": {
                    "request_id": f"req_{i}",
                    "user_id": None
                }
            })
        
        return logs
        
    except Exception as e:
        logger.error("Failed to get recent logs", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve logs")


@router.get("/alerts")
async def get_active_alerts() -> List[Dict[str, Any]]:
    """Get active system alerts"""
    try:
        alerts = []
        
        # Check system resources
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            alerts.append({
                "id": "high_memory_usage",
                "severity": "warning",
                "title": "High Memory Usage",
                "message": f"Memory usage is at {memory.percent:.1f}%",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metadata": {
                    "memory_percent": memory.percent,
                    "memory_available": memory.available
                }
            })
        
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 90:
            alerts.append({
                "id": "high_cpu_usage",
                "severity": "warning",
                "title": "High CPU Usage",
                "message": f"CPU usage is at {cpu_percent:.1f}%",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metadata": {
                    "cpu_percent": cpu_percent
                }
            })
        
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        if disk_percent > 90:
            alerts.append({
                "id": "high_disk_usage",
                "severity": "critical",
                "title": "High Disk Usage",
                "message": f"Disk usage is at {disk_percent:.1f}%",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metadata": {
                    "disk_percent": disk_percent,
                    "disk_free": disk.free
                }
            })
        
        # Check database health
        db_health = await check_db_health()
        if db_health["status"] != "healthy":
            alerts.append({
                "id": "database_unhealthy",
                "severity": "critical",
                "title": "Database Health Issue",
                "message": "Database health check failed",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metadata": db_health
            })
        
        return alerts
        
    except Exception as e:
        logger.error("Failed to get active alerts", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")

