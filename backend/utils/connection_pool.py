"""
Advanced connection pooling and performance optimization for HTTP clients
"""
import asyncio
import aiohttp
import time
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class PoolStatus(Enum):
    """Connection pool status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CLOSED = "closed"


@dataclass
class ConnectionPoolConfig:
    """Configuration for connection pool"""
    max_connections: int = 100
    max_connections_per_host: int = 30
    connection_timeout: float = 30.0
    read_timeout: float = 60.0
    keepalive_timeout: float = 30.0
    enable_cleanup_closed: bool = True
    cleanup_interval: float = 60.0
    max_idle_time: float = 300.0  # 5 minutes
    health_check_interval: float = 120.0  # 2 minutes
    retry_attempts: int = 3
    retry_delay: float = 1.0


@dataclass
class ConnectionMetrics:
    """Connection pool metrics"""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    last_activity: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RequestMetrics:
    """Individual request metrics"""
    start_time: float
    end_time: Optional[float] = None
    status_code: Optional[int] = None
    error: Optional[str] = None
    
    @property
    def duration(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time


class EnhancedConnectionPool:
    """Enhanced connection pool with monitoring and optimization"""
    
    def __init__(self, config: ConnectionPoolConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.status = PoolStatus.CLOSED
        self.metrics = ConnectionMetrics()
        self.request_history: List[RequestMetrics] = []
        self.max_history = 1000
        
        # Background tasks
        self.cleanup_task: Optional[asyncio.Task] = None
        self.health_check_task: Optional[asyncio.Task] = None
        
        self.logger = logger.bind(component="connection_pool")
        
        # Performance tracking
        self.response_times: List[float] = []
        self.max_response_times = 100
    
    async def start(self):
        """Initialize and start the connection pool"""
        if self.session is not None:
            await self.close()
        
        # Create connector with optimized settings
        connector = aiohttp.TCPConnector(
            limit=self.config.max_connections,
            limit_per_host=self.config.max_connections_per_host,
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
            keepalive_timeout=self.config.keepalive_timeout,
            enable_cleanup_closed=self.config.enable_cleanup_closed,
            force_close=False,
            ssl=False  # Can be configured per request
        )
        
        # Create timeout configuration
        timeout = aiohttp.ClientTimeout(
            total=None,  # No total timeout, handle per request
            connect=self.config.connection_timeout,
            sock_read=self.config.read_timeout
        )
        
        # Create session
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'CodegenCICD-Enhanced-Client/1.0',
                'Connection': 'keep-alive'
            }
        )
        
        self.status = PoolStatus.HEALTHY
        self.metrics.last_activity = datetime.utcnow()
        
        # Start background tasks
        await self._start_background_tasks()
        
        self.logger.info("Connection pool started",
                        max_connections=self.config.max_connections,
                        max_per_host=self.config.max_connections_per_host)
    
    async def close(self):
        """Close the connection pool and cleanup resources"""
        self.status = PoolStatus.CLOSED
        
        # Stop background tasks
        await self._stop_background_tasks()
        
        # Close session
        if self.session:
            await self.session.close()
            self.session = None
        
        self.logger.info("Connection pool closed")
    
    async def request(self,
                     method: str,
                     url: str,
                     timeout: Optional[float] = None,
                     **kwargs) -> aiohttp.ClientResponse:
        """Make an HTTP request with enhanced monitoring"""
        if self.session is None or self.status == PoolStatus.CLOSED:
            raise RuntimeError("Connection pool is not started")
        
        # Create request metrics
        request_metrics = RequestMetrics(start_time=time.time())
        
        # Set timeout for this request
        if timeout:
            request_timeout = aiohttp.ClientTimeout(total=timeout)
            kwargs['timeout'] = request_timeout
        
        try:
            self.metrics.total_requests += 1
            
            # Make the request
            response = await self.session.request(method, url, **kwargs)
            
            # Update metrics
            request_metrics.end_time = time.time()
            request_metrics.status_code = response.status
            
            self.metrics.successful_requests += 1
            self.metrics.last_activity = datetime.utcnow()
            
            # Track response time
            response_time = request_metrics.duration
            self.response_times.append(response_time)
            if len(self.response_times) > self.max_response_times:
                self.response_times.pop(0)
            
            # Update average response time
            self.metrics.average_response_time = sum(self.response_times) / len(self.response_times)
            
            self.logger.debug("Request completed successfully",
                            method=method,
                            url=url,
                            status_code=response.status,
                            response_time=response_time)
            
            return response
            
        except Exception as e:
            # Update error metrics
            request_metrics.end_time = time.time()
            request_metrics.error = str(e)
            
            self.metrics.failed_requests += 1
            
            self.logger.error("Request failed",
                            method=method,
                            url=url,
                            error=str(e),
                            duration=request_metrics.duration)
            
            raise
        
        finally:
            # Store request metrics
            self.request_history.append(request_metrics)
            if len(self.request_history) > self.max_history:
                self.request_history.pop(0)
    
    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make a GET request"""
        return await self.request('GET', url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make a POST request"""
        return await self.request('POST', url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make a PUT request"""
        return await self.request('PUT', url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make a DELETE request"""
        return await self.request('DELETE', url, **kwargs)
    
    async def patch(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make a PATCH request"""
        return await self.request('PATCH', url, **kwargs)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive pool metrics"""
        connector_info = {}
        if self.session and self.session.connector:
            connector = self.session.connector
            connector_info = {
                "total_connections": len(connector._conns),
                "available_connections": sum(len(conns) for conns in connector._conns.values()),
                "acquired_connections": connector._acquired_per_host,
            }
        
        # Calculate success rate
        success_rate = 0.0
        if self.metrics.total_requests > 0:
            success_rate = self.metrics.successful_requests / self.metrics.total_requests
        
        # Recent performance metrics
        recent_requests = self.request_history[-50:] if len(self.request_history) >= 50 else self.request_history
        recent_success_rate = 0.0
        recent_avg_time = 0.0
        
        if recent_requests:
            successful_recent = sum(1 for r in recent_requests if r.error is None)
            recent_success_rate = successful_recent / len(recent_requests)
            
            completed_recent = [r for r in recent_requests if r.end_time is not None]
            if completed_recent:
                recent_avg_time = sum(r.duration for r in completed_recent) / len(completed_recent)
        
        return {
            "status": self.status.value,
            "pool_config": {
                "max_connections": self.config.max_connections,
                "max_connections_per_host": self.config.max_connections_per_host,
                "connection_timeout": self.config.connection_timeout,
                "read_timeout": self.config.read_timeout
            },
            "connection_info": connector_info,
            "request_metrics": {
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "success_rate": success_rate,
                "average_response_time": self.metrics.average_response_time
            },
            "recent_performance": {
                "recent_success_rate": recent_success_rate,
                "recent_average_time": recent_avg_time,
                "sample_size": len(recent_requests)
            },
            "last_activity": self.metrics.last_activity.isoformat()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the connection pool"""
        metrics = self.get_metrics()
        
        # Determine health status
        health_score = 100
        issues = []
        
        # Check success rate
        success_rate = metrics["request_metrics"]["success_rate"]
        if success_rate < 0.5:
            health_score -= 40
            issues.append(f"Low success rate: {success_rate:.2%}")
        elif success_rate < 0.8:
            health_score -= 20
            issues.append(f"Moderate success rate: {success_rate:.2%}")
        
        # Check response time
        avg_time = metrics["request_metrics"]["average_response_time"]
        if avg_time > 10.0:
            health_score -= 30
            issues.append(f"High response time: {avg_time:.2f}s")
        elif avg_time > 5.0:
            health_score -= 15
            issues.append(f"Elevated response time: {avg_time:.2f}s")
        
        # Check recent performance
        recent_success = metrics["recent_performance"]["recent_success_rate"]
        if recent_success < 0.7:
            health_score -= 20
            issues.append(f"Recent performance degraded: {recent_success:.2%}")
        
        # Determine status
        if health_score >= 80:
            status = PoolStatus.HEALTHY
        elif health_score >= 50:
            status = PoolStatus.DEGRADED
        else:
            status = PoolStatus.UNHEALTHY
        
        return {
            "status": status.value,
            "health_score": max(0, health_score),
            "issues": issues,
            "metrics": metrics
        }
    
    async def _start_background_tasks(self):
        """Start background maintenance tasks"""
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        if self.health_check_task is None or self.health_check_task.done():
            self.health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def _stop_background_tasks(self):
        """Stop background maintenance tasks"""
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self.health_check_task and not self.health_check_task.done():
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
    
    async def _cleanup_loop(self):
        """Background task for connection cleanup"""
        while self.status != PoolStatus.CLOSED:
            try:
                # Clean up old request history
                cutoff_time = time.time() - self.config.max_idle_time
                self.request_history = [
                    r for r in self.request_history 
                    if r.start_time > cutoff_time
                ]
                
                # Clean up old response times
                if len(self.response_times) > self.max_response_times:
                    self.response_times = self.response_times[-self.max_response_times:]
                
                self.logger.debug("Connection pool cleanup completed",
                                request_history_size=len(self.request_history),
                                response_times_size=len(self.response_times))
                
            except Exception as e:
                self.logger.error("Error in cleanup loop", error=str(e))
            
            await asyncio.sleep(self.config.cleanup_interval)
    
    async def _health_check_loop(self):
        """Background task for health monitoring"""
        while self.status != PoolStatus.CLOSED:
            try:
                health_status = self.get_health_status()
                
                # Update pool status based on health
                new_status = PoolStatus(health_status["status"])
                if new_status != self.status:
                    self.logger.warning("Connection pool status changed",
                                      old_status=self.status.value,
                                      new_status=new_status.value,
                                      health_score=health_status["health_score"],
                                      issues=health_status["issues"])
                    self.status = new_status
                
                # Log health report
                if health_status["health_score"] < 80:
                    self.logger.warning("Connection pool health degraded",
                                      health_score=health_status["health_score"],
                                      issues=health_status["issues"])
                
            except Exception as e:
                self.logger.error("Error in health check loop", error=str(e))
            
            await asyncio.sleep(self.config.health_check_interval)


class ConnectionPoolManager:
    """Manager for multiple connection pools"""
    
    def __init__(self):
        self.pools: Dict[str, EnhancedConnectionPool] = {}
        self.logger = logger.bind(component="connection_pool_manager")
    
    async def get_pool(self, 
                      name: str, 
                      config: Optional[ConnectionPoolConfig] = None) -> EnhancedConnectionPool:
        """Get or create a connection pool"""
        if name not in self.pools:
            if config is None:
                config = ConnectionPoolConfig()
            
            pool = EnhancedConnectionPool(config)
            await pool.start()
            
            self.pools[name] = pool
            self.logger.info("Created new connection pool", name=name)
        
        return self.pools[name]
    
    async def close_pool(self, name: str):
        """Close a specific connection pool"""
        if name in self.pools:
            await self.pools[name].close()
            del self.pools[name]
            self.logger.info("Closed connection pool", name=name)
    
    async def close_all_pools(self):
        """Close all connection pools"""
        for name, pool in list(self.pools.items()):
            await pool.close()
        
        self.pools.clear()
        self.logger.info("Closed all connection pools")
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all pools"""
        return {name: pool.get_metrics() for name, pool in self.pools.items()}
    
    def get_all_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get health status for all pools"""
        return {name: pool.get_health_status() for name, pool in self.pools.items()}


# Global connection pool manager
connection_pool_manager = ConnectionPoolManager()
