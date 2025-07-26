"""
Grainchain client for sandboxing and snapshotting
"""
import httpx
import structlog
from typing import Dict, Any, Optional, List
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class GrainchainClient:
    """Client for interacting with Grainchain sandboxing service"""
    
    def __init__(self):
        self.base_url = settings.grainchain_api_url
        self.enabled = settings.grainchain_enabled
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "CodegenCICD/1.0.0"
        }
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to Grainchain API"""
        if not self.enabled:
            raise Exception("Grainchain is disabled")
        
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(
                    "Grainchain API HTTP error",
                    status_code=e.response.status_code,
                    response_text=e.response.text,
                    endpoint=endpoint
                )
                raise
            except Exception as e:
                logger.error("Grainchain API request failed", error=str(e), endpoint=endpoint)
                raise
    
    async def create_snapshot(self, name: str, description: str = None, 
                             base_image: str = "ubuntu:22.04") -> Dict[str, Any]:
        """Create a new sandbox snapshot"""
        payload = {
            "name": name,
            "base_image": base_image,
            "description": description or f"Snapshot for {name}"
        }
        
        try:
            response = await self._make_request("POST", "/snapshots", json=payload)
            logger.info("Snapshot created", snapshot_id=response.get("id"), name=name)
            return response
        except Exception as e:
            logger.error("Failed to create snapshot", name=name, error=str(e))
            raise
    
    async def get_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        """Get snapshot information"""
        try:
            response = await self._make_request("GET", f"/snapshots/{snapshot_id}")
            return response
        except Exception as e:
            logger.error("Failed to get snapshot", snapshot_id=snapshot_id, error=str(e))
            raise
    
    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot"""
        try:
            await self._make_request("DELETE", f"/snapshots/{snapshot_id}")
            logger.info("Snapshot deleted", snapshot_id=snapshot_id)
            return True
        except Exception as e:
            logger.error("Failed to delete snapshot", snapshot_id=snapshot_id, error=str(e))
            return False
    
    async def clone_repository(self, snapshot_id: str, repo_url: str, branch: str = "main",
                              target_dir: str = "/workspace") -> Dict[str, Any]:
        """Clone a repository into the snapshot"""
        payload = {
            "repo_url": repo_url,
            "branch": branch,
            "target_dir": target_dir
        }
        
        try:
            response = await self._make_request("POST", f"/snapshots/{snapshot_id}/clone", json=payload)
            logger.info("Repository cloned", snapshot_id=snapshot_id, repo_url=repo_url, branch=branch)
            return response
        except Exception as e:
            logger.error("Failed to clone repository", snapshot_id=snapshot_id, repo_url=repo_url, error=str(e))
            raise
    
    async def execute_command(self, snapshot_id: str, command: str, 
                             working_dir: str = "/workspace", timeout: int = 300) -> Dict[str, Any]:
        """Execute a command in the snapshot"""
        payload = {
            "command": command,
            "working_dir": working_dir,
            "timeout": timeout
        }
        
        try:
            response = await self._make_request("POST", f"/snapshots/{snapshot_id}/execute", json=payload)
            logger.info(
                "Command executed",
                snapshot_id=snapshot_id,
                command=command[:50] + "..." if len(command) > 50 else command,
                exit_code=response.get("exit_code")
            )
            return response
        except Exception as e:
            logger.error("Failed to execute command", snapshot_id=snapshot_id, command=command, error=str(e))
            raise
    
    async def execute_setup_commands(self, snapshot_id: str, commands: List[str],
                                   working_dir: str = "/workspace") -> List[Dict[str, Any]]:
        """Execute multiple setup commands sequentially"""
        results = []
        
        for i, command in enumerate(commands):
            try:
                result = await self.execute_command(snapshot_id, command, working_dir)
                results.append({
                    "command": command,
                    "order": i + 1,
                    "success": result.get("exit_code") == 0,
                    "result": result
                })
                
                # Stop on first failure
                if result.get("exit_code") != 0:
                    logger.warning(
                        "Setup command failed, stopping execution",
                        snapshot_id=snapshot_id,
                        command=command,
                        exit_code=result.get("exit_code")
                    )
                    break
                    
            except Exception as e:
                logger.error("Setup command execution failed", command=command, error=str(e))
                results.append({
                    "command": command,
                    "order": i + 1,
                    "success": False,
                    "error": str(e)
                })
                break
        
        return results
    
    async def get_file_content(self, snapshot_id: str, file_path: str) -> str:
        """Get content of a file from the snapshot"""
        try:
            response = await self._make_request("GET", f"/snapshots/{snapshot_id}/files", 
                                              params={"path": file_path})
            return response.get("content", "")
        except Exception as e:
            logger.error("Failed to get file content", snapshot_id=snapshot_id, file_path=file_path, error=str(e))
            raise
    
    async def write_file(self, snapshot_id: str, file_path: str, content: str) -> bool:
        """Write content to a file in the snapshot"""
        payload = {
            "path": file_path,
            "content": content
        }
        
        try:
            await self._make_request("POST", f"/snapshots/{snapshot_id}/files", json=payload)
            logger.info("File written", snapshot_id=snapshot_id, file_path=file_path)
            return True
        except Exception as e:
            logger.error("Failed to write file", snapshot_id=snapshot_id, file_path=file_path, error=str(e))
            return False
    
    async def get_snapshot_logs(self, snapshot_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get logs from the snapshot"""
        try:
            response = await self._make_request("GET", f"/snapshots/{snapshot_id}/logs",
                                              params={"limit": limit})
            return response.get("logs", [])
        except Exception as e:
            logger.error("Failed to get snapshot logs", snapshot_id=snapshot_id, error=str(e))
            return []
    
    async def get_running_processes(self, snapshot_id: str) -> List[Dict[str, Any]]:
        """Get running processes in the snapshot"""
        try:
            response = await self._make_request("GET", f"/snapshots/{snapshot_id}/processes")
            return response.get("processes", [])
        except Exception as e:
            logger.error("Failed to get running processes", snapshot_id=snapshot_id, error=str(e))
            return []
    
    async def health_check(self) -> bool:
        """Check if Grainchain service is accessible"""
        if not self.enabled:
            return False
        
        try:
            await self._make_request("GET", "/health")
            return True
        except Exception as e:
            logger.error("Grainchain health check failed", error=str(e))
            return False
    
    async def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all snapshots"""
        try:
            response = await self._make_request("GET", "/snapshots")
            return response.get("snapshots", [])
        except Exception as e:
            logger.error("Failed to list snapshots", error=str(e))
            return []

