"""
Grainchain API client for sandboxing and snapshotting
"""
from typing import Optional, Dict, Any, List
import httpx
import structlog

from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class GrainchainClient:
    """Client for interacting with Grainchain sandboxing service"""
    
    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or settings.grainchain_api_url
        self.enabled = settings.grainchain_enabled
        
        if not self.enabled:
            logger.warning("Grainchain is disabled in configuration")
            return
        
        self.client = httpx.AsyncClient(
            base_url=self.api_url,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "CodegenCICD/1.0.0"
            },
            timeout=httpx.Timeout(60.0)
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'client'):
            await self.client.aclose()
    
    async def create_snapshot(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new sandbox snapshot"""
        if not self.enabled:
            return {"snapshot_id": "disabled", "snapshot_url": None}
        
        try:
            payload = {
                "project_id": config.get("project_id"),
                "pr_branch": config.get("pr_branch"),
                "pr_number": config.get("pr_number"),
                "environment": "validation",
                "resources": {
                    "cpu": "2",
                    "memory": "4Gi",
                    "storage": "10Gi"
                },
                "timeout": 3600  # 1 hour
            }
            
            logger.info("Creating Grainchain snapshot", project_id=config.get("project_id"))
            
            response = await self.client.post("/snapshots", json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            logger.info("Grainchain snapshot created", 
                       snapshot_id=result.get("snapshot_id"))
            
            return {
                "snapshot_id": result.get("snapshot_id"),
                "snapshot_url": result.get("snapshot_url"),
                "status": result.get("status", "created"),
                "resources": result.get("resources"),
                "expires_at": result.get("expires_at")
            }
            
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error creating snapshot", 
                        status_code=e.response.status_code, 
                        response=e.response.text)
            raise
        except Exception as e:
            logger.error("Failed to create snapshot", error=str(e))
            raise
    
    async def get_snapshot_status(self, snapshot_id: str) -> Dict[str, Any]:
        """Get snapshot status"""
        if not self.enabled:
            return {"status": "disabled"}
        
        try:
            response = await self.client.get(f"/snapshots/{snapshot_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to get snapshot status", 
                        snapshot_id=snapshot_id, error=str(e))
            raise
    
    async def clone_repository(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Clone repository into snapshot"""
        if not self.enabled:
            return {"success": True, "message": "Grainchain disabled"}
        
        try:
            payload = {
                "snapshot_id": config.get("snapshot_id"),
                "repository": config.get("repository"),
                "branch": config.get("branch"),
                "commit_sha": config.get("commit_sha"),
                "clone_path": "/workspace"
            }
            
            logger.info("Cloning repository in snapshot", 
                       snapshot_id=config.get("snapshot_id"),
                       repository=config.get("repository"))
            
            response = await self.client.post("/snapshots/clone", json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            logger.info("Repository cloned successfully", 
                       snapshot_id=config.get("snapshot_id"))
            
            return {
                "success": result.get("success", True),
                "clone_path": result.get("clone_path"),
                "commit_sha": result.get("commit_sha"),
                "files_count": result.get("files_count"),
                "size_mb": result.get("size_mb")
            }
            
        except Exception as e:
            logger.error("Failed to clone repository", 
                        snapshot_id=config.get("snapshot_id"), error=str(e))
            raise
    
    async def execute_commands(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute commands in snapshot"""
        if not self.enabled:
            return {
                "success": True, 
                "logs": "Grainchain disabled - commands not executed",
                "deployment_url": "http://localhost:3000"
            }
        
        try:
            payload = {
                "snapshot_id": config.get("snapshot_id"),
                "commands": config.get("commands", []),
                "working_directory": "/workspace",
                "timeout": config.get("timeout", 300),
                "environment": config.get("environment", {})
            }
            
            logger.info("Executing commands in snapshot", 
                       snapshot_id=config.get("snapshot_id"),
                       commands_count=len(payload["commands"]))
            
            response = await self.client.post("/snapshots/execute", json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            success = result.get("exit_code", 0) == 0
            
            logger.info("Commands executed", 
                       snapshot_id=config.get("snapshot_id"),
                       success=success,
                       exit_code=result.get("exit_code"))
            
            return {
                "success": success,
                "exit_code": result.get("exit_code", 0),
                "logs": result.get("stdout", "") + result.get("stderr", ""),
                "stdout": result.get("stdout"),
                "stderr": result.get("stderr"),
                "duration": result.get("duration"),
                "deployment_url": result.get("deployment_url"),
                "exposed_ports": result.get("exposed_ports", [])
            }
            
        except Exception as e:
            logger.error("Failed to execute commands", 
                        snapshot_id=config.get("snapshot_id"), error=str(e))
            raise
    
    async def run_validation(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run security and isolation validation"""
        if not self.enabled:
            return {
                "passed": True,
                "score": 100,
                "details": {"message": "Grainchain disabled"},
                "issues_count": 0,
                "critical_issues": 0,
                "warning_issues": 0
            }
        
        try:
            payload = {
                "snapshot_id": config.get("snapshot_id"),
                "validation_type": config.get("validation_type", "security_and_isolation"),
                "deployment_url": config.get("deployment_url"),
                "checks": [
                    "container_security",
                    "network_isolation",
                    "resource_limits",
                    "file_permissions",
                    "process_isolation"
                ]
            }
            
            logger.info("Running Grainchain validation", 
                       snapshot_id=config.get("snapshot_id"))
            
            response = await self.client.post("/snapshots/validate", json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            passed = result.get("overall_score", 0) >= 80  # 80% threshold
            
            logger.info("Grainchain validation completed", 
                       snapshot_id=config.get("snapshot_id"),
                       passed=passed,
                       score=result.get("overall_score"))
            
            return {
                "passed": passed,
                "score": result.get("overall_score"),
                "details": result.get("validation_results"),
                "issues_count": result.get("total_issues", 0),
                "critical_issues": result.get("critical_issues", 0),
                "warning_issues": result.get("warning_issues", 0),
                "security_score": result.get("security_score"),
                "isolation_score": result.get("isolation_score")
            }
            
        except Exception as e:
            logger.error("Failed to run validation", 
                        snapshot_id=config.get("snapshot_id"), error=str(e))
            raise
    
    async def cleanup_snapshot(self, snapshot_id: str) -> bool:
        """Clean up snapshot resources"""
        if not self.enabled:
            return True
        
        try:
            response = await self.client.delete(f"/snapshots/{snapshot_id}")
            response.raise_for_status()
            
            logger.info("Snapshot cleaned up", snapshot_id=snapshot_id)
            return True
            
        except Exception as e:
            logger.error("Failed to cleanup snapshot", 
                        snapshot_id=snapshot_id, error=str(e))
            return False
    
    async def list_snapshots(self, project_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """List snapshots"""
        if not self.enabled:
            return []
        
        try:
            params = {}
            if project_id:
                params["project_id"] = project_id
            
            response = await self.client.get("/snapshots", params=params)
            response.raise_for_status()
            
            result = response.json()
            return result.get("snapshots", [])
            
        except Exception as e:
            logger.error("Failed to list snapshots", error=str(e))
            raise
    
    async def health_check(self) -> bool:
        """Check if Grainchain service is accessible"""
        if not self.enabled:
            return True
        
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception as e:
            logger.error("Grainchain health check failed", error=str(e))
            return False


# Global client instance
_grainchain_client: Optional[GrainchainClient] = None


async def get_grainchain_client() -> GrainchainClient:
    """Get global Grainchain client instance"""
    global _grainchain_client
    if _grainchain_client is None:
        _grainchain_client = GrainchainClient()
    return _grainchain_client

