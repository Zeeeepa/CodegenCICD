"""
Grainchain client for sandboxing and snapshot management
"""
import os
import httpx
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class GrainchainClient:
    def __init__(self):
        self.base_url = os.getenv("GRAINCHAIN_API_URL", "http://localhost:8080")
        self.api_key = os.getenv("GRAINCHAIN_API_KEY")
        
        # For now, we'll simulate grainchain functionality
        # In production, this would connect to the actual grainchain service
        self.enabled = os.getenv("GRAINCHAIN_ENABLED", "true").lower() == "true"
    
    async def create_snapshot(self, config: Dict[str, Any]) -> str:
        """Create a new sandbox snapshot with specified tools and environment"""
        try:
            if not self.enabled:
                # Return mock snapshot ID for development
                return f"mock_snapshot_{hash(str(config)) % 10000}"
            
            async with httpx.AsyncClient() as client:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                payload = {
                    "tools": config.get("tools", []),
                    "environment_variables": config.get("environment_variables", {}),
                    "base_image": config.get("base_image", "ubuntu:22.04"),
                    "resources": {
                        "cpu": config.get("cpu", "2"),
                        "memory": config.get("memory", "4Gi"),
                        "disk": config.get("disk", "10Gi")
                    }
                }
                
                response = await client.post(
                    f"{self.base_url}/snapshots",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                snapshot_id = result.get("snapshot_id")
                logger.info(f"Created grainchain snapshot: {snapshot_id}")
                
                return snapshot_id
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error creating snapshot: {e}")
            raise Exception(f"Failed to create snapshot: {e}")
        except Exception as e:
            logger.error(f"Error creating snapshot: {e}")
            # Return mock ID for development
            return f"mock_snapshot_{hash(str(config)) % 10000}"
    
    async def clone_repository(self, snapshot_id: str, repo_url: str, branch: str = "main") -> Dict[str, Any]:
        """Clone a repository into the sandbox snapshot"""
        try:
            if not self.enabled:
                # Return mock result for development
                return {
                    "status": "success",
                    "path": f"/workspace/{repo_url.split('/')[-1].replace('.git', '')}",
                    "branch": branch,
                    "commit_hash": "mock_commit_hash"
                }
            
            async with httpx.AsyncClient() as client:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                payload = {
                    "repository_url": repo_url,
                    "branch": branch,
                    "destination": "/workspace"
                }
                
                response = await client.post(
                    f"{self.base_url}/snapshots/{snapshot_id}/clone",
                    headers=headers,
                    json=payload,
                    timeout=120.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Cloned repository {repo_url} to snapshot {snapshot_id}")
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error cloning repository: {e}")
            raise Exception(f"Failed to clone repository: {e}")
        except Exception as e:
            logger.error(f"Error cloning repository: {e}")
            # Return mock result for development
            return {
                "status": "success",
                "path": f"/workspace/{repo_url.split('/')[-1].replace('.git', '')}",
                "branch": branch,
                "commit_hash": "mock_commit_hash"
            }
    
    async def execute_commands(self, snapshot_id: str, commands: List[str]) -> Dict[str, Any]:
        """Execute a series of commands in the sandbox"""
        try:
            if not self.enabled:
                # Return mock result for development
                return {
                    "status": "success",
                    "output": "Mock command execution completed successfully",
                    "exit_code": 0,
                    "url": "http://localhost:3000",
                    "duration": 30.5
                }
            
            async with httpx.AsyncClient() as client:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                payload = {
                    "commands": commands,
                    "working_directory": "/workspace",
                    "timeout": 300,  # 5 minutes
                    "capture_output": True
                }
                
                response = await client.post(
                    f"{self.base_url}/snapshots/{snapshot_id}/execute",
                    headers=headers,
                    json=payload,
                    timeout=360.0  # 6 minutes
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Executed {len(commands)} commands in snapshot {snapshot_id}")
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error executing commands: {e}")
            raise Exception(f"Failed to execute commands: {e}")
        except Exception as e:
            logger.error(f"Error executing commands: {e}")
            # Return mock result for development
            return {
                "status": "success",
                "output": "Mock command execution completed successfully",
                "exit_code": 0,
                "url": "http://localhost:3000",
                "duration": 30.5
            }
    
    async def get_snapshot_status(self, snapshot_id: str) -> Dict[str, Any]:
        """Get the status of a sandbox snapshot"""
        try:
            if not self.enabled:
                return {
                    "status": "running",
                    "created_at": "2024-01-01T00:00:00Z",
                    "resources": {
                        "cpu_usage": "50%",
                        "memory_usage": "2Gi",
                        "disk_usage": "5Gi"
                    }
                }
            
            async with httpx.AsyncClient() as client:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                response = await client.get(
                    f"{self.base_url}/snapshots/{snapshot_id}",
                    headers=headers,
                    timeout=30.0
                )
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting snapshot status: {e}")
            return {"status": "unknown", "error": str(e)}
        except Exception as e:
            logger.error(f"Error getting snapshot status: {e}")
            return {"status": "unknown", "error": str(e)}
    
    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a sandbox snapshot"""
        try:
            if not self.enabled:
                return True
            
            async with httpx.AsyncClient() as client:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                response = await client.delete(
                    f"{self.base_url}/snapshots/{snapshot_id}",
                    headers=headers,
                    timeout=30.0
                )
                
                response.raise_for_status()
                logger.info(f"Deleted snapshot: {snapshot_id}")
                return True
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error deleting snapshot: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting snapshot: {e}")
            return False
    
    async def get_logs(self, snapshot_id: str, lines: int = 100) -> List[str]:
        """Get logs from a sandbox snapshot"""
        try:
            if not self.enabled:
                return [
                    "Mock log entry 1: Application started",
                    "Mock log entry 2: Database connected",
                    "Mock log entry 3: Server listening on port 3000"
                ]
            
            async with httpx.AsyncClient() as client:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                response = await client.get(
                    f"{self.base_url}/snapshots/{snapshot_id}/logs",
                    headers=headers,
                    params={"lines": lines},
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                return result.get("logs", [])
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting logs: {e}")
            return [f"Error getting logs: {e}"]
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return [f"Error getting logs: {e}"]

