"""
Resource monitoring and lifecycle management for Grainchain operations
"""
import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class ResourceType(Enum):
    """Types of resources to monitor"""
    SNAPSHOT = "snapshot"
    PROCESS = "process"
    FILE_HANDLE = "file_handle"
    NETWORK_CONNECTION = "network_connection"
    MEMORY_ALLOCATION = "memory_allocation"


class ResourceStatus(Enum):
    """Resource lifecycle status"""
    ACTIVE = "active"
    IDLE = "idle"
    CLEANUP_PENDING = "cleanup_pending"
    CLEANUP_FAILED = "cleanup_failed"
    DESTROYED = "destroyed"


@dataclass
class ResourceMetrics:
    """Resource usage metrics"""
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    disk_mb: float = 0.0
    network_connections: int = 0
    file_handles: int = 0
    uptime_seconds: float = 0.0
    last_activity: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ResourceQuota:
    """Resource usage quotas"""
    max_cpu_percent: float = 80.0
    max_memory_mb: float = 2048.0
    max_disk_mb: float = 10240.0
    max_network_connections: int = 100
    max_file_handles: int = 1000
    max_uptime_hours: float = 24.0
    max_idle_minutes: float = 30.0


@dataclass
class ManagedResource:
    """Managed resource with lifecycle tracking"""
    resource_id: str
    resource_type: ResourceType
    status: ResourceStatus
    created_at: datetime
    last_accessed: datetime
    metadata: Dict[str, Any]
    metrics: ResourceMetrics
    cleanup_callbacks: List[callable] = field(default_factory=list)
    
    def is_expired(self, quota: ResourceQuota) -> bool:
        """Check if resource has exceeded its lifetime"""
        age_hours = (datetime.utcnow() - self.created_at).total_seconds() / 3600
        return age_hours > quota.max_uptime_hours
    
    def is_idle(self, quota: ResourceQuota) -> bool:
        """Check if resource has been idle too long"""
        idle_minutes = (datetime.utcnow() - self.last_accessed).total_seconds() / 60
        return idle_minutes > quota.max_idle_minutes
    
    def exceeds_quota(self, quota: ResourceQuota) -> List[str]:
        """Check which quotas are exceeded"""
        violations = []
        
        if self.metrics.cpu_percent > quota.max_cpu_percent:
            violations.append(f"CPU usage {self.metrics.cpu_percent}% > {quota.max_cpu_percent}%")
        
        if self.metrics.memory_mb > quota.max_memory_mb:
            violations.append(f"Memory usage {self.metrics.memory_mb}MB > {quota.max_memory_mb}MB")
        
        if self.metrics.disk_mb > quota.max_disk_mb:
            violations.append(f"Disk usage {self.metrics.disk_mb}MB > {quota.max_disk_mb}MB")
        
        if self.metrics.network_connections > quota.max_network_connections:
            violations.append(f"Network connections {self.metrics.network_connections} > {quota.max_network_connections}")
        
        if self.metrics.file_handles > quota.max_file_handles:
            violations.append(f"File handles {self.metrics.file_handles} > {quota.max_file_handles}")
        
        return violations


class ResourceManager:
    """Comprehensive resource monitoring and lifecycle management"""
    
    def __init__(self, default_quota: Optional[ResourceQuota] = None):
        self.resources: Dict[str, ManagedResource] = {}
        self.default_quota = default_quota or ResourceQuota()
        self.cleanup_task: Optional[asyncio.Task] = None
        self.monitoring_task: Optional[asyncio.Task] = None
        self.cleanup_interval = 60  # seconds
        self.monitoring_interval = 30  # seconds
        self.logger = logger.bind(component="resource_manager")
        
        # Statistics
        self.stats = {
            "total_created": 0,
            "total_destroyed": 0,
            "cleanup_successes": 0,
            "cleanup_failures": 0,
            "quota_violations": 0
        }
    
    async def start(self):
        """Start resource monitoring and cleanup tasks"""
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            self.logger.info("Started resource cleanup task")
        
        if self.monitoring_task is None or self.monitoring_task.done():
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            self.logger.info("Started resource monitoring task")
    
    async def stop(self):
        """Stop resource monitoring and cleanup tasks"""
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.logger.info("Stopped resource cleanup task")
        
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.logger.info("Stopped resource monitoring task")
    
    def register_resource(self,
                         resource_id: str,
                         resource_type: ResourceType,
                         metadata: Optional[Dict[str, Any]] = None,
                         cleanup_callbacks: Optional[List[callable]] = None) -> ManagedResource:
        """Register a new resource for management"""
        resource = ManagedResource(
            resource_id=resource_id,
            resource_type=resource_type,
            status=ResourceStatus.ACTIVE,
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            metadata=metadata or {},
            metrics=ResourceMetrics(),
            cleanup_callbacks=cleanup_callbacks or []
        )
        
        self.resources[resource_id] = resource
        self.stats["total_created"] += 1
        
        self.logger.info("Registered new resource",
                        resource_id=resource_id,
                        resource_type=resource_type.value,
                        metadata=metadata)
        
        return resource
    
    def update_resource_metrics(self, resource_id: str, metrics: ResourceMetrics):
        """Update resource metrics"""
        if resource_id in self.resources:
            resource = self.resources[resource_id]
            resource.metrics = metrics
            resource.last_accessed = datetime.utcnow()
            
            # Check for quota violations
            violations = resource.exceeds_quota(self.default_quota)
            if violations:
                self.stats["quota_violations"] += 1
                self.logger.warning("Resource quota violations detected",
                                  resource_id=resource_id,
                                  violations=violations)
    
    def access_resource(self, resource_id: str):
        """Mark resource as accessed (updates last_accessed timestamp)"""
        if resource_id in self.resources:
            self.resources[resource_id].last_accessed = datetime.utcnow()
    
    async def cleanup_resource(self, resource_id: str, force: bool = False) -> bool:
        """Clean up a specific resource"""
        if resource_id not in self.resources:
            self.logger.warning("Attempted to cleanup non-existent resource",
                              resource_id=resource_id)
            return False
        
        resource = self.resources[resource_id]
        
        if resource.status == ResourceStatus.DESTROYED:
            self.logger.debug("Resource already destroyed", resource_id=resource_id)
            return True
        
        if not force and resource.status == ResourceStatus.ACTIVE:
            # Check if resource should be cleaned up
            if not (resource.is_expired(self.default_quota) or 
                   resource.is_idle(self.default_quota) or
                   resource.exceeds_quota(self.default_quota)):
                return False
        
        resource.status = ResourceStatus.CLEANUP_PENDING
        
        try:
            # Execute cleanup callbacks
            for callback in resource.cleanup_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(resource_id)
                    else:
                        callback(resource_id)
                except Exception as e:
                    self.logger.error("Cleanup callback failed",
                                    resource_id=resource_id,
                                    callback=str(callback),
                                    error=str(e))
            
            resource.status = ResourceStatus.DESTROYED
            self.stats["cleanup_successes"] += 1
            self.stats["total_destroyed"] += 1
            
            self.logger.info("Resource cleaned up successfully",
                           resource_id=resource_id,
                           resource_type=resource.resource_type.value)
            
            return True
            
        except Exception as e:
            resource.status = ResourceStatus.CLEANUP_FAILED
            self.stats["cleanup_failures"] += 1
            
            self.logger.error("Resource cleanup failed",
                            resource_id=resource_id,
                            error=str(e))
            
            return False
    
    async def cleanup_expired_resources(self) -> int:
        """Clean up all expired and idle resources"""
        cleanup_count = 0
        
        for resource_id, resource in list(self.resources.items()):
            if resource.status in [ResourceStatus.DESTROYED, ResourceStatus.CLEANUP_PENDING]:
                continue
            
            should_cleanup = (
                resource.is_expired(self.default_quota) or
                resource.is_idle(self.default_quota) or
                bool(resource.exceeds_quota(self.default_quota))
            )
            
            if should_cleanup:
                success = await self.cleanup_resource(resource_id)
                if success:
                    cleanup_count += 1
        
        if cleanup_count > 0:
            self.logger.info("Cleaned up expired resources", count=cleanup_count)
        
        return cleanup_count
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """Get comprehensive resource statistics"""
        active_resources = sum(1 for r in self.resources.values() 
                             if r.status == ResourceStatus.ACTIVE)
        
        idle_resources = sum(1 for r in self.resources.values() 
                           if r.status == ResourceStatus.ACTIVE and r.is_idle(self.default_quota))
        
        expired_resources = sum(1 for r in self.resources.values() 
                              if r.status == ResourceStatus.ACTIVE and r.is_expired(self.default_quota))
        
        quota_violations = sum(1 for r in self.resources.values() 
                             if r.status == ResourceStatus.ACTIVE and r.exceeds_quota(self.default_quota))
        
        # Resource type breakdown
        type_breakdown = {}
        for resource in self.resources.values():
            resource_type = resource.resource_type.value
            if resource_type not in type_breakdown:
                type_breakdown[resource_type] = {"active": 0, "total": 0}
            
            type_breakdown[resource_type]["total"] += 1
            if resource.status == ResourceStatus.ACTIVE:
                type_breakdown[resource_type]["active"] += 1
        
        # Aggregate metrics
        total_cpu = sum(r.metrics.cpu_percent for r in self.resources.values() 
                       if r.status == ResourceStatus.ACTIVE)
        total_memory = sum(r.metrics.memory_mb for r in self.resources.values() 
                          if r.status == ResourceStatus.ACTIVE)
        total_disk = sum(r.metrics.disk_mb for r in self.resources.values() 
                        if r.status == ResourceStatus.ACTIVE)
        
        return {
            "total_resources": len(self.resources),
            "active_resources": active_resources,
            "idle_resources": idle_resources,
            "expired_resources": expired_resources,
            "quota_violations": quota_violations,
            "type_breakdown": type_breakdown,
            "aggregate_metrics": {
                "total_cpu_percent": total_cpu,
                "total_memory_mb": total_memory,
                "total_disk_mb": total_disk
            },
            "lifecycle_stats": self.stats.copy()
        }
    
    def get_resource_details(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific resource"""
        if resource_id not in self.resources:
            return None
        
        resource = self.resources[resource_id]
        
        return {
            "resource_id": resource.resource_id,
            "resource_type": resource.resource_type.value,
            "status": resource.status.value,
            "created_at": resource.created_at.isoformat(),
            "last_accessed": resource.last_accessed.isoformat(),
            "age_hours": (datetime.utcnow() - resource.created_at).total_seconds() / 3600,
            "idle_minutes": (datetime.utcnow() - resource.last_accessed).total_seconds() / 60,
            "metadata": resource.metadata,
            "metrics": {
                "cpu_percent": resource.metrics.cpu_percent,
                "memory_mb": resource.metrics.memory_mb,
                "disk_mb": resource.metrics.disk_mb,
                "network_connections": resource.metrics.network_connections,
                "file_handles": resource.metrics.file_handles,
                "uptime_seconds": resource.metrics.uptime_seconds
            },
            "quota_violations": resource.exceeds_quota(self.default_quota),
            "is_expired": resource.is_expired(self.default_quota),
            "is_idle": resource.is_idle(self.default_quota)
        }
    
    async def _cleanup_loop(self):
        """Background task for periodic resource cleanup"""
        while True:
            try:
                await self.cleanup_expired_resources()
                
                # Remove destroyed resources from memory after some time
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                destroyed_resources = [
                    resource_id for resource_id, resource in self.resources.items()
                    if (resource.status == ResourceStatus.DESTROYED and 
                        resource.last_accessed < cutoff_time)
                ]
                
                for resource_id in destroyed_resources:
                    del self.resources[resource_id]
                
                if destroyed_resources:
                    self.logger.debug("Removed destroyed resources from memory",
                                    count=len(destroyed_resources))
                
            except Exception as e:
                self.logger.error("Error in cleanup loop", error=str(e))
            
            await asyncio.sleep(self.cleanup_interval)
    
    async def _monitoring_loop(self):
        """Background task for resource monitoring"""
        while True:
            try:
                # Log resource statistics periodically
                stats = self.get_resource_stats()
                
                if stats["active_resources"] > 0:
                    self.logger.info("Resource monitoring report",
                                   active_resources=stats["active_resources"],
                                   idle_resources=stats["idle_resources"],
                                   expired_resources=stats["expired_resources"],
                                   quota_violations=stats["quota_violations"])
                
                # Alert on high resource usage
                if stats["aggregate_metrics"]["total_cpu_percent"] > 500:  # 5 cores worth
                    self.logger.warning("High aggregate CPU usage detected",
                                      total_cpu=stats["aggregate_metrics"]["total_cpu_percent"])
                
                if stats["aggregate_metrics"]["total_memory_mb"] > 8192:  # 8GB
                    self.logger.warning("High aggregate memory usage detected",
                                      total_memory=stats["aggregate_metrics"]["total_memory_mb"])
                
            except Exception as e:
                self.logger.error("Error in monitoring loop", error=str(e))
            
            await asyncio.sleep(self.monitoring_interval)


# Global resource manager instance
resource_manager = ResourceManager()
