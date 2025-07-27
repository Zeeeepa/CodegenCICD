"""
Grainchain client for CodegenCICD Dashboard
"""
from typing import Dict, Any, Optional, List
import structlog

from .base_client import BaseClient, APIError
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class GrainchainClient(BaseClient):
    """Client for interacting with Grainchain sandboxing service"""
    
    def __init__(self, base_url: Optional[str] = None):
        # Use configured grainchain URL or default
        self.grainchain_url = base_url or getattr(settings, 'grainchain_url', 'http://localhost:8080')
        
        super().__init__(
            service_name="grainchain",
            base_url=self.grainchain_url,
            timeout=120,  # Longer timeout for sandbox operations
            max_retries=3
        )
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for Grainchain requests"""
        return {
            "Content-Type": "application/json",
            "User-Agent": "CodegenCICD-Dashboard/1.0"
        }
    
    async def _health_check_request(self) -> None:
        """Health check by getting service status"""
        await self.get("/health")
    
    # Snapshot Management
    async def create_snapshot(self,
                            project_name: str,
                            github_url: str,
                            branch: str = "main") -> Dict[str, Any]:
        """Create a new sandbox snapshot"""
        try:
            payload = {
                "project_name": project_name,
                "github_url": github_url,
                "branch": branch,
                "snapshot_type": "validation"
            }
            
            self.logger.info("Creating grainchain snapshot",
                           project_name=project_name,
                           github_url=github_url,
                           branch=branch)
            
            response = await self.post("/snapshots", data=payload)
            
            snapshot_id = response.get("snapshot_id")
            self.logger.info("Grainchain snapshot created successfully",
                           snapshot_id=snapshot_id,
                           project_name=project_name)
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to create grainchain snapshot",
                            project_name=project_name,
                            error=str(e))
            raise
    
    async def get_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        """Get snapshot details"""
        try:
            response = await self.get(f"/snapshots/{snapshot_id}")
            return response
        except Exception as e:
            self.logger.error("Failed to get snapshot",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
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
        try:
            response = await self.get(f"/snapshots/{snapshot_id}/metrics")
            return response
        except Exception as e:
            self.logger.error("Failed to get snapshot metrics",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise

