"""
Monitoring, metrics, and observability for CodegenCICD
"""
import time
import os
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import structlog
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from fastapi.responses import PlainTextResponse
import psutil
import json

logger = structlog.get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_CONNECTIONS = Gauge(
    'active_connections',
    'Number of active connections'
)

AGENT_RUNS_TOTAL = Counter(
    'agent_runs_total',
    'Total number of agent runs',
    ['status', 'project']
)

AGENT_RUNS_DURATION = Histogram(
    'agent_runs_duration_seconds',
    'Agent run duration in seconds',
    ['status', 'project']
)

AGENT_RUNS_ACTIVE = Gauge(
    'agent_runs_active',
    'Number of currently active agent runs'
)

DATABASE_CONNECTIONS = Gauge(
    'database_connections_active',
    'Number of active database connections'
)

REDIS_CONNECTIONS = Gauge(
    'redis_connections_active',
    'Number of active Redis connections'
)

SYSTEM_CPU_USAGE = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage'
)

SYSTEM_MEMORY_USAGE = Gauge(
    'system_memory_usage_bytes',
    'System memory usage in bytes'
)

SYSTEM_DISK_USAGE = Gauge(
    'system_disk_usage_bytes',
    'System disk usage in bytes',
    ['path']
)

ERROR_COUNT = Counter(
    'errors_total',
    'Total number of errors',
    ['error_type', 'component']
)

EXTERNAL_API_CALLS = Counter(
    'external_api_calls_total',
    'Total external API calls',
    ['service', 'status']
)

EXTERNAL_API_DURATION = Histogram(
    'external_api_duration_seconds',
    'External API call duration',
    ['service']
)

# Application info
APP_INFO = Info('codegencd_app', 'CodegenCICD application information')
APP_INFO.info({
    'version': os.environ.get('APP_VERSION', '1.0.0'),
    'environment': os.environ.get('ENVIRONMENT', 'development'),
    'build_date': os.environ.get('BUILD_DATE', datetime.utcnow().isoformat())
})


class MetricsCollector:
    """Centralized metrics collection and management"""
    
    def __init__(self):
        self.start_time = time.time()
        self.system_metrics_task: Optional[asyncio.Task] = None
        self.metrics_enabled = os.environ.get('ENABLE_METRICS', 'true').lower() == 'true'
        
    async def start_system_metrics_collection(self):
        """Start background system metrics collection"""
        if not self.metrics_enabled:
            return
            
        self.system_metrics_task = asyncio.create_task(self._collect_system_metrics())
        logger.info("System metrics collection started")
    
    async def stop_system_metrics_collection(self):
        """Stop background system metrics collection"""
        if self.system_metrics_task:
            self.system_metrics_task.cancel()
            try:
                await self.system_metrics_task
            except asyncio.CancelledError:
                pass
            logger.info("System metrics collection stopped")
    
    async def _collect_system_metrics(self):
        """Background task to collect system metrics"""
        while True:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                SYSTEM_CPU_USAGE.set(cpu_percent)
                
                # Memory usage
                memory = psutil.virtual_memory()
                SYSTEM_MEMORY_USAGE.set(memory.used)
                
                # Disk usage
                for path in ['/app/logs', '/app/data', '/tmp']:
                    if os.path.exists(path):
                        disk_usage = psutil.disk_usage(path)
                        SYSTEM_DISK_USAGE.labels(path=path).set(disk_usage.used)
                
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                logger.error("Error collecting system metrics", error=str(e))
                await asyncio.sleep(60)  # Wait longer on error
    
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        if not self.metrics_enabled:
            return
            
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        REQUEST_DURATION.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_agent_run(self, status: str, project: str, duration: Optional[float] = None):
        """Record agent run metrics"""
        if not self.metrics_enabled:
            return
            
        AGENT_RUNS_TOTAL.labels(status=status, project=project).inc()
        
        if duration is not None:
            AGENT_RUNS_DURATION.labels(status=status, project=project).observe(duration)
    
    def set_active_agent_runs(self, count: int):
        """Set number of active agent runs"""
        if self.metrics_enabled:
            AGENT_RUNS_ACTIVE.set(count)
    
    def record_error(self, error_type: str, component: str):
        """Record error occurrence"""
        if self.metrics_enabled:
            ERROR_COUNT.labels(error_type=error_type, component=component).inc()
    
    def record_external_api_call(self, service: str, status: str, duration: float):
        """Record external API call metrics"""
        if not self.metrics_enabled:
            return
            
        EXTERNAL_API_CALLS.labels(service=service, status=status).inc()
        EXTERNAL_API_DURATION.labels(service=service).observe(duration)
    
    def get_uptime(self) -> float:
        """Get application uptime in seconds"""
        return time.time() - self.start_time


# Global metrics collector
metrics_collector = MetricsCollector()


class RequestMetricsMiddleware:
    """Middleware to collect HTTP request metrics"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Record metrics when response starts
                duration = time.time() - start_time
                method = scope["method"]
                path = scope["path"]
                status_code = message["status"]
                
                # Normalize endpoint for metrics (remove IDs, etc.)
                normalized_path = self._normalize_path(path)
                
                metrics_collector.record_request(method, normalized_path, status_code, duration)
            
            await send(message)
        
        await self.app(scope, receive, send_wrapper)
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path for metrics (replace IDs with placeholders)"""
        import re
        
        # Replace UUIDs with {id}
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}', path)
        
        # Replace numeric IDs with {id}
        path = re.sub(r'/\d+', '/{id}', path)
        
        return path


@asynccontextmanager
async def external_api_call_metrics(service: str):
    """Context manager to track external API calls"""
    start_time = time.time()
    status = "success"
    
    try:
        yield
    except Exception as e:
        status = "error"
        metrics_collector.record_error("external_api_error", service)
        raise
    finally:
        duration = time.time() - start_time
        metrics_collector.record_external_api_call(service, status, duration)


class HealthChecker:
    """Application health checking"""
    
    def __init__(self):
        self.checks = {}
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            from backend.database import get_db_session
            async with get_db_session() as session:
                await session.execute("SELECT 1")
                return {"status": "healthy", "component": "database"}
        except Exception as e:
            return {"status": "unhealthy", "component": "database", "error": str(e)}
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        try:
            import redis
            import os
            from urllib.parse import urlparse
            
            redis_url = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
            parsed = urlparse(redis_url)
            
            r = redis.Redis(
                host=parsed.hostname,
                port=parsed.port or 6379,
                db=int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0
            )
            r.ping()
            return {"status": "healthy", "component": "redis"}
        except Exception as e:
            return {"status": "unhealthy", "component": "redis", "error": str(e)}
    
    async def check_external_services(self) -> Dict[str, Any]:
        """Check external service connectivity"""
        services = {}
        
        # Check Codegen API
        try:
            from backend.services.codegen_api_client import CodegenAPIClient
            async with CodegenAPIClient() as client:
                is_valid = await client.validate_connection()
                services["codegen_api"] = {
                    "status": "healthy" if is_valid else "degraded",
                    "validated": is_valid
                }
        except Exception as e:
            services["codegen_api"] = {"status": "unhealthy", "error": str(e)}
        
        return services
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        checks = {
            "database": await self.check_database(),
            "redis": await self.check_redis(),
            "external_services": await self.check_external_services()
        }
        
        # Determine overall status
        unhealthy_components = []
        degraded_components = []
        
        for component, result in checks.items():
            if isinstance(result, dict):
                if result.get("status") == "unhealthy":
                    unhealthy_components.append(component)
                elif result.get("status") == "degraded":
                    degraded_components.append(component)
            elif isinstance(result, dict) and component == "external_services":
                for service_name, service_result in result.items():
                    if service_result.get("status") == "unhealthy":
                        unhealthy_components.append(f"external_services.{service_name}")
                    elif service_result.get("status") == "degraded":
                        degraded_components.append(f"external_services.{service_name}")
        
        if unhealthy_components:
            overall_status = "unhealthy"
        elif degraded_components:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": metrics_collector.get_uptime(),
            "checks": checks,
            "unhealthy_components": unhealthy_components,
            "degraded_components": degraded_components
        }


# Global health checker
health_checker = HealthChecker()


async def get_metrics_response() -> PlainTextResponse:
    """Get Prometheus metrics response"""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


class StructuredLogger:
    """Enhanced structured logging with correlation IDs"""
    
    def __init__(self):
        self.correlation_id_header = "X-Correlation-ID"
    
    def get_correlation_id(self, request: Request) -> str:
        """Get or generate correlation ID for request"""
        correlation_id = request.headers.get(self.correlation_id_header)
        if not correlation_id:
            import uuid
            correlation_id = str(uuid.uuid4())
        return correlation_id
    
    def log_request(self, request: Request, correlation_id: str):
        """Log incoming request"""
        logger.info("Request received",
                   method=request.method,
                   path=request.url.path,
                   correlation_id=correlation_id,
                   client_ip=request.client.host,
                   user_agent=request.headers.get("user-agent"))
    
    def log_response(self, request: Request, response: Response, 
                    correlation_id: str, duration: float):
        """Log outgoing response"""
        logger.info("Request completed",
                   method=request.method,
                   path=request.url.path,
                   status_code=response.status_code,
                   correlation_id=correlation_id,
                   duration_ms=round(duration * 1000, 2))


# Global structured logger
structured_logger = StructuredLogger()

