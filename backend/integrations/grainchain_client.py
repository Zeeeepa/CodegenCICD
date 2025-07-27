"""
Enhanced Grainchain client for CodegenCICD Dashboard with production-ready features
"""
import asyncio
import uuid
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import structlog

from .base_client import BaseClient, APIError
from backend.config import get_settings
from backend.utils.circuit_breaker import (
    circuit_breaker_manager, 
    CircuitBreakerConfig, 
    CircuitBreakerError
)
from backend.utils.retry_strategies import (
    RetryHandler, 
    RetryConfig, 
    RetryStrategy, 
    AdaptiveRetryHandler
)
from backend.utils.connection_pool import (
    connection_pool_manager, 
    ConnectionPoolConfig
)
from backend.services.resource_manager import (
    resource_manager, 
    ResourceType, 
    ResourceMetrics
)

logger = structlog.get_logger(__name__)
settings = get_settings()


class EnhancedGrainchainClient(BaseClient):
    """Enhanced client for interacting with Grainchain sandboxing service with production-ready features"""
    
    def __init__(self, base_url: Optional[str] = None):
        # Use configured grainchain URL or default
        self.grainchain_url = base_url or getattr(settings, 'grainchain_url', 'http://localhost:8080')
        
        super().__init__(
            service_name="grainchain",
            base_url=self.grainchain_url,
            timeout=120,  # Longer timeout for sandbox operations
            max_retries=3
        )
        
        # Enhanced features
        self.correlation_id = str(uuid.uuid4())
        self.logger = logger.bind(
            service="grainchain",
            correlation_id=self.correlation_id
        )
        
        # Circuit breaker configuration
        self.circuit_breaker_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            success_threshold=3,
            timeout=120
        )
        
        # Retry configuration
        self.retry_config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            jitter=True,
            backoff_multiplier=2.0,
            retryable_exceptions=[ConnectionError, TimeoutError, APIError]
        )
        
        # Connection pool configuration
        self.pool_config = ConnectionPoolConfig(
            max_connections=50,
            max_connections_per_host=20,
            connection_timeout=30.0,
            read_timeout=120.0,
            keepalive_timeout=30.0
        )
        
        # Initialize adaptive retry handler
        self.adaptive_retry = AdaptiveRetryHandler(self.retry_config)
        
        # Performance metrics
        self.operation_metrics = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "average_response_time": 0.0,
            "last_operation": None
        }
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for Grainchain requests"""
        return {
            "Content-Type": "application/json",
            "User-Agent": "CodegenCICD-Enhanced-Dashboard/2.0",
            "X-Correlation-ID": self.correlation_id,
            "X-Request-ID": str(uuid.uuid4())
        }
    
    async def _health_check_request(self) -> None:
        """Health check by getting service status"""
        await self._execute_with_enhancements(self.get, "/health")
    
    async def _execute_with_enhancements(self, 
                                       operation: Callable,
                                       *args, 
                                       **kwargs) -> Any:
        """Execute operation with circuit breaker, retry, and monitoring"""
        operation_start = datetime.utcnow()
        operation_name = f"{operation.__name__}_{args[0] if args else 'unknown'}"
        
        # Get circuit breaker
        circuit_breaker = circuit_breaker_manager.get_breaker(
            f"grainchain_{operation_name}",
            self.circuit_breaker_config
        )
        
        try:
            self.operation_metrics["total_operations"] += 1
            
            # Execute with circuit breaker and retry
            result = await circuit_breaker.call(
                self.adaptive_retry.execute,
                operation,
                *args,
                **kwargs
            )
            
            # Update success metrics
            self.operation_metrics["successful_operations"] += 1
            operation_duration = (datetime.utcnow() - operation_start).total_seconds()
            
            # Update average response time
            total_ops = self.operation_metrics["total_operations"]
            current_avg = self.operation_metrics["average_response_time"]
            self.operation_metrics["average_response_time"] = (
                (current_avg * (total_ops - 1) + operation_duration) / total_ops
            )
            
            self.operation_metrics["last_operation"] = operation_start.isoformat()
            
            self.logger.info("Operation completed successfully",
                           operation=operation_name,
                           duration=operation_duration,
                           correlation_id=self.correlation_id)
            
            return result
            
        except CircuitBreakerError as e:
            self.operation_metrics["failed_operations"] += 1
            self.logger.error("Operation failed due to circuit breaker",
                            operation=operation_name,
                            error=str(e),
                            correlation_id=self.correlation_id)
            raise APIError(f"Service temporarily unavailable: {str(e)}")
            
        except Exception as e:
            self.operation_metrics["failed_operations"] += 1
            operation_duration = (datetime.utcnow() - operation_start).total_seconds()
            
            self.logger.error("Operation failed",
                            operation=operation_name,
                            duration=operation_duration,
                            error=str(e),
                            correlation_id=self.correlation_id)
            raise
    
    # Snapshot Management
    async def create_snapshot(self,
                            project_name: str,
                            github_url: str,
                            branch: str = "main") -> Dict[str, Any]:
        """Create a new sandbox snapshot with enhanced reliability"""
        payload = {
            "project_name": project_name,
            "github_url": github_url,
            "branch": branch,
            "snapshot_type": "validation",
            "correlation_id": self.correlation_id
        }
        
        self.logger.info("Creating grainchain snapshot",
                       project_name=project_name,
                       github_url=github_url,
                       branch=branch,
                       correlation_id=self.correlation_id)
        
        response = await self._execute_with_enhancements(
            self.post, 
            "/snapshots", 
            data=payload
        )
        
        snapshot_id = response.get("snapshot_id")
        
        # Register snapshot with resource manager
        if snapshot_id:
            cleanup_callback = lambda sid: self._cleanup_snapshot_callback(sid)
            resource_manager.register_resource(
                resource_id=snapshot_id,
                resource_type=ResourceType.SNAPSHOT,
                metadata={
                    "project_name": project_name,
                    "github_url": github_url,
                    "branch": branch,
                    "created_by": "grainchain_client",
                    "correlation_id": self.correlation_id
                },
                cleanup_callbacks=[cleanup_callback]
            )
        
        self.logger.info("Grainchain snapshot created successfully",
                       snapshot_id=snapshot_id,
                       project_name=project_name,
                       correlation_id=self.correlation_id)
        
        return response
    
    async def _cleanup_snapshot_callback(self, snapshot_id: str):
        """Cleanup callback for snapshot resources"""
        try:
            await self.delete_snapshot(snapshot_id)
            self.logger.info("Snapshot cleaned up via callback",
                           snapshot_id=snapshot_id,
                           correlation_id=self.correlation_id)
        except Exception as e:
            self.logger.error("Failed to cleanup snapshot via callback",
                            snapshot_id=snapshot_id,
                            error=str(e),
                            correlation_id=self.correlation_id)
    
    async def get_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        """Get snapshot details with enhanced reliability"""
        # Mark resource as accessed
        resource_manager.access_resource(snapshot_id)
        
        response = await self._execute_with_enhancements(
            self.get, 
            f"/snapshots/{snapshot_id}"
        )
        
        # Update resource metrics if available
        if "metrics" in response:
            metrics_data = response["metrics"]
            metrics = ResourceMetrics(
                cpu_percent=metrics_data.get("cpu_percent", 0.0),
                memory_mb=metrics_data.get("memory_mb", 0.0),
                disk_mb=metrics_data.get("disk_mb", 0.0),
                network_connections=metrics_data.get("network_connections", 0),
                file_handles=metrics_data.get("file_handles", 0),
                uptime_seconds=metrics_data.get("uptime_seconds", 0.0)
            )
            resource_manager.update_resource_metrics(snapshot_id, metrics)
        
        return response
    
    async def delete_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        """Delete a snapshot"""
        try:
            response = await self.delete(f"/snapshots/{snapshot_id}")
            
            self.logger.info("Grainchain snapshot deleted",
                           snapshot_id=snapshot_id)
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to delete snapshot",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    async def list_snapshots(self,
                           project_name: Optional[str] = None,
                           limit: int = 50) -> List[Dict[str, Any]]:
        """List snapshots"""
        try:
            params = {"limit": limit}
            if project_name:
                params["project_name"] = project_name
            
            response = await self.get("/snapshots", params=params)
            return response.get("snapshots", [])
            
        except Exception as e:
            self.logger.error("Failed to list snapshots", error=str(e))
            raise
    
    # Repository Operations
    async def clone_repository(self,
                             snapshot_id: str,
                             repository_url: str,
                             branch: str = "main",
                             commit_sha: Optional[str] = None) -> Dict[str, Any]:
        """Clone repository into snapshot"""
        try:
            payload = {
                "repository_url": repository_url,
                "branch": branch
            }
            
            if commit_sha:
                payload["commit_sha"] = commit_sha
            
            self.logger.info("Cloning repository to grainchain snapshot",
                           snapshot_id=snapshot_id,
                           repository_url=repository_url,
                           branch=branch,
                           commit_sha=commit_sha)
            
            response = await self.post(f"/snapshots/{snapshot_id}/clone", data=payload)
            
            self.logger.info("Repository cloned successfully",
                           snapshot_id=snapshot_id,
                           status=response.get("status"))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to clone repository",
                            snapshot_id=snapshot_id,
                            repository_url=repository_url,
                            error=str(e))
            raise
    
    async def get_repository_status(self, snapshot_id: str) -> Dict[str, Any]:
        """Get repository status in snapshot"""
        try:
            response = await self.get(f"/snapshots/{snapshot_id}/repository")
            return response
        except Exception as e:
            self.logger.error("Failed to get repository status",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    # Command Execution
    async def execute_command(self,
                            snapshot_id: str,
                            command: str,
                            working_directory: str = "/workspace",
                            timeout: int = 300) -> Dict[str, Any]:
        """Execute command in snapshot"""
        try:
            payload = {
                "command": command,
                "working_directory": working_directory,
                "timeout": timeout
            }
            
            self.logger.info("Executing command in grainchain snapshot",
                           snapshot_id=snapshot_id,
                           command=command[:100],  # Truncate for logging
                           working_directory=working_directory)
            
            response = await self.post(f"/snapshots/{snapshot_id}/execute", data=payload)
            
            self.logger.info("Command executed",
                           snapshot_id=snapshot_id,
                           exit_code=response.get("exit_code"),
                           duration=response.get("duration_seconds"))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to execute command",
                            snapshot_id=snapshot_id,
                            command=command[:100],
                            error=str(e))
            raise
    
    async def execute_deployment(self,
                               snapshot_id: str,
                               setup_commands: List[str],
                               project_path: str = "/workspace") -> Dict[str, Any]:
        """Execute deployment commands"""
        try:
            payload = {
                "commands": setup_commands,
                "project_path": project_path,
                "deployment_type": "validation"
            }
            
            self.logger.info("Executing deployment in grainchain snapshot",
                           snapshot_id=snapshot_id,
                           command_count=len(setup_commands),
                           project_path=project_path)
            
            response = await self.post(f"/snapshots/{snapshot_id}/deploy", data=payload)
            
            success = response.get("success", False)
            self.logger.info("Deployment executed",
                           snapshot_id=snapshot_id,
                           success=success,
                           duration=response.get("duration_seconds"))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to execute deployment",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    async def get_deployment_logs(self, snapshot_id: str) -> str:
        """Get deployment logs from snapshot"""
        try:
            response = await self.get(f"/snapshots/{snapshot_id}/logs")
            return response.get("logs", "")
        except Exception as e:
            self.logger.error("Failed to get deployment logs",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    # File Operations
    async def read_file(self,
                       snapshot_id: str,
                       file_path: str) -> Dict[str, Any]:
        """Read file from snapshot"""
        try:
            params = {"file_path": file_path}
            response = await self.get(f"/snapshots/{snapshot_id}/files", params=params)
            return response
        except Exception as e:
            self.logger.error("Failed to read file",
                            snapshot_id=snapshot_id,
                            file_path=file_path,
                            error=str(e))
            raise
    
    async def write_file(self,
                        snapshot_id: str,
                        file_path: str,
                        content: str) -> Dict[str, Any]:
        """Write file to snapshot"""
        try:
            payload = {
                "file_path": file_path,
                "content": content
            }
            
            response = await self.post(f"/snapshots/{snapshot_id}/files", data=payload)
            
            self.logger.info("File written to snapshot",
                           snapshot_id=snapshot_id,
                           file_path=file_path,
                           content_length=len(content))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to write file",
                            snapshot_id=snapshot_id,
                            file_path=file_path,
                            error=str(e))
            raise
    
    async def list_files(self,
                        snapshot_id: str,
                        directory_path: str = "/workspace") -> List[Dict[str, Any]]:
        """List files in snapshot directory"""
        try:
            params = {"directory_path": directory_path}
            response = await self.get(f"/snapshots/{snapshot_id}/files/list", params=params)
            return response.get("files", [])
        except Exception as e:
            self.logger.error("Failed to list files",
                            snapshot_id=snapshot_id,
                            directory_path=directory_path,
                            error=str(e))
            raise
    
    # Network Operations
    async def check_port(self,
                        snapshot_id: str,
                        port: int,
                        timeout: int = 30) -> Dict[str, Any]:
        """Check if port is accessible in snapshot"""
        try:
            params = {
                "port": port,
                "timeout": timeout
            }
            
            response = await self.get(f"/snapshots/{snapshot_id}/ports", params=params)
            
            self.logger.info("Port check completed",
                           snapshot_id=snapshot_id,
                           port=port,
                           accessible=response.get("accessible"))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to check port",
                            snapshot_id=snapshot_id,
                            port=port,
                            error=str(e))
            raise
    
    async def get_service_url(self,
                            snapshot_id: str,
                            port: int = 8000) -> str:
        """Get service URL for snapshot"""
        try:
            response = await self.get(f"/snapshots/{snapshot_id}/url")
            base_url = response.get("base_url", f"http://localhost:{port}")
            return base_url
        except Exception as e:
            self.logger.error("Failed to get service URL",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    # Process Management
    async def list_processes(self, snapshot_id: str) -> List[Dict[str, Any]]:
        """List running processes in snapshot"""
        try:
            response = await self.get(f"/snapshots/{snapshot_id}/processes")
            return response.get("processes", [])
        except Exception as e:
            self.logger.error("Failed to list processes",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    async def kill_process(self,
                          snapshot_id: str,
                          process_id: int) -> Dict[str, Any]:
        """Kill process in snapshot"""
        try:
            payload = {"process_id": process_id}
            response = await self.post(f"/snapshots/{snapshot_id}/processes/kill", data=payload)
            
            self.logger.info("Process killed",
                           snapshot_id=snapshot_id,
                           process_id=process_id)
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to kill process",
                            snapshot_id=snapshot_id,
                            process_id=process_id,
                            error=str(e))
            raise
    
    # Monitoring
    async def get_resource_usage(self, snapshot_id: str) -> Dict[str, Any]:
        """Get resource usage for snapshot"""
        try:
            response = await self.get(f"/snapshots/{snapshot_id}/resources")
            return response
        except Exception as e:
            self.logger.error("Failed to get resource usage",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    async def get_snapshot_metrics(self, snapshot_id: str) -> Dict[str, Any]:
        """Get comprehensive metrics for snapshot"""
        resource_manager.access_resource(snapshot_id)
        
        response = await self._execute_with_enhancements(
            self.get, 
            f"/snapshots/{snapshot_id}/metrics"
        )
        
        # Update resource metrics
        if "metrics" in response:
            metrics_data = response["metrics"]
            metrics = ResourceMetrics(
                cpu_percent=metrics_data.get("cpu_percent", 0.0),
                memory_mb=metrics_data.get("memory_mb", 0.0),
                disk_mb=metrics_data.get("disk_mb", 0.0),
                network_connections=metrics_data.get("network_connections", 0),
                file_handles=metrics_data.get("file_handles", 0),
                uptime_seconds=metrics_data.get("uptime_seconds", 0.0)
            )
            resource_manager.update_resource_metrics(snapshot_id, metrics)
        
        return response
    
    # Enhanced Monitoring and Management Methods
    
    def get_client_metrics(self) -> Dict[str, Any]:
        """Get comprehensive client performance metrics"""
        # Get circuit breaker states
        circuit_breaker_states = circuit_breaker_manager.get_all_states()
        
        # Get retry statistics
        retry_stats = self.adaptive_retry.get_stats()
        
        # Get connection pool metrics
        pool_metrics = connection_pool_manager.get_all_metrics()
        
        # Get resource manager stats
        resource_stats = resource_manager.get_resource_stats()
        
        return {
            "client_info": {
                "service_name": self.service_name,
                "base_url": self.base_url,
                "correlation_id": self.correlation_id,
                "created_at": datetime.utcnow().isoformat()
            },
            "operation_metrics": self.operation_metrics.copy(),
            "circuit_breakers": circuit_breaker_states,
            "retry_statistics": retry_stats,
            "connection_pools": pool_metrics,
            "resource_management": resource_stats
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of the client"""
        metrics = self.get_client_metrics()
        
        health_score = 100
        issues = []
        
        # Check operation success rate
        total_ops = metrics["operation_metrics"]["total_operations"]
        if total_ops > 0:
            success_rate = metrics["operation_metrics"]["successful_operations"] / total_ops
            if success_rate < 0.5:
                health_score -= 40
                issues.append(f"Low operation success rate: {success_rate:.2%}")
            elif success_rate < 0.8:
                health_score -= 20
                issues.append(f"Moderate operation success rate: {success_rate:.2%}")
        
        # Check circuit breaker states
        for breaker_name, breaker_state in metrics["circuit_breakers"].items():
            if breaker_state["state"] == "open":
                health_score -= 30
                issues.append(f"Circuit breaker {breaker_name} is open")
            elif breaker_state["state"] == "half_open":
                health_score -= 15
                issues.append(f"Circuit breaker {breaker_name} is half-open")
        
        # Check retry statistics
        retry_stats = metrics["retry_statistics"]
        if retry_stats["total_attempts"] > 0:
            retry_success_rate = retry_stats["success_rate"]
            if retry_success_rate < 0.7:
                health_score -= 25
                issues.append(f"Low retry success rate: {retry_success_rate:.2%}")
        
        # Check resource management
        resource_stats = metrics["resource_management"]
        if resource_stats["quota_violations"] > 0:
            health_score -= 20
            issues.append(f"Resource quota violations: {resource_stats['quota_violations']}")
        
        if resource_stats["expired_resources"] > 5:
            health_score -= 15
            issues.append(f"High number of expired resources: {resource_stats['expired_resources']}")
        
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
            "last_check": datetime.utcnow().isoformat(),
            "detailed_metrics": metrics
        }
    
    async def perform_health_check(self) -> Dict[str, Any]:
        """Perform active health check against Grainchain service"""
        health_check_start = datetime.utcnow()
        
        try:
            # Test basic connectivity
            await self._health_check_request()
            
            # Test snapshot listing (lightweight operation)
            await self.list_snapshots(limit=1)
            
            health_check_duration = (datetime.utcnow() - health_check_start).total_seconds()
            
            return {
                "service_available": True,
                "response_time": health_check_duration,
                "timestamp": datetime.utcnow().isoformat(),
                "correlation_id": self.correlation_id
            }
            
        except Exception as e:
            health_check_duration = (datetime.utcnow() - health_check_start).total_seconds()
            
            return {
                "service_available": False,
                "error": str(e),
                "response_time": health_check_duration,
                "timestamp": datetime.utcnow().isoformat(),
                "correlation_id": self.correlation_id
            }
    
    async def cleanup_all_resources(self, force: bool = False) -> Dict[str, Any]:
        """Clean up all managed resources"""
        cleanup_start = datetime.utcnow()
        
        try:
            # Get all snapshots managed by this client
            snapshots = await self.list_snapshots()
            
            cleanup_results = {
                "total_snapshots": len(snapshots),
                "cleaned_up": 0,
                "failed": 0,
                "errors": []
            }
            
            for snapshot in snapshots:
                snapshot_id = snapshot.get("snapshot_id")
                if snapshot_id:
                    try:
                        await resource_manager.cleanup_resource(snapshot_id, force=force)
                        cleanup_results["cleaned_up"] += 1
                    except Exception as e:
                        cleanup_results["failed"] += 1
                        cleanup_results["errors"].append({
                            "snapshot_id": snapshot_id,
                            "error": str(e)
                        })
            
            cleanup_duration = (datetime.utcnow() - cleanup_start).total_seconds()
            
            self.logger.info("Resource cleanup completed",
                           duration=cleanup_duration,
                           results=cleanup_results,
                           correlation_id=self.correlation_id)
            
            return {
                "success": True,
                "duration": cleanup_duration,
                "results": cleanup_results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            cleanup_duration = (datetime.utcnow() - cleanup_start).total_seconds()
            
            self.logger.error("Resource cleanup failed",
                            duration=cleanup_duration,
                            error=str(e),
                            correlation_id=self.correlation_id)
            
            return {
                "success": False,
                "duration": cleanup_duration,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Maintain backward compatibility
GrainchainClient = EnhancedGrainchainClient
