"""
Grainchain client for sandboxing and snapshot management
"""
import asyncio
import json
from typing import Dict, Any, List, Optional
import structlog
import httpx
from datetime import datetime

from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class GrainchainClient:
    """Client for interacting with Grainchain service"""
    
    def __init__(self):
        self.base_url = settings.grainchain_url or "http://localhost:8001"
        self.timeout = 300  # 5 minutes timeout for operations
    
    async def create_snapshot(self, name: str, environment_vars: Dict[str, str], services: List[str]) -> Optional[str]:
        """Create a new snapshot with specified environment and services"""
        try:
            logger.info("Creating Grainchain snapshot", name=name, services=services)
            
            snapshot_config = {
                "name": name,
                "environment": environment_vars,
                "services": services,
                "base_image": "ubuntu:22.04",
                "packages": [
                    "python3",
                    "python3-pip",
                    "nodejs",
                    "npm",
                    "git",
                    "curl",
                    "wget"
                ],
                "setup_commands": [
                    "pip3 install --upgrade pip",
                    "npm install -g yarn"
                ]
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/snapshots",
                    json=snapshot_config,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 201:
                    result = response.json()
                    snapshot_id = result.get("snapshot_id")
                    logger.info("Snapshot created successfully", 
                               name=name, 
                               snapshot_id=snapshot_id)
                    return snapshot_id
                else:
                    logger.error("Failed to create snapshot", 
                               name=name,
                               status_code=response.status_code,
                               response=response.text)
                    return None
                    
        except Exception as e:
            logger.error("Snapshot creation failed", name=name, error=str(e))
            return None
    
    async def clone_repository(self, repo_url: str, branch: str, target_dir: str) -> bool:
        """Clone a repository in the sandbox"""
        try:
            logger.info("Cloning repository", repo_url=repo_url, branch=branch)
            
            clone_config = {
                "repo_url": repo_url,
                "branch": branch,
                "target_directory": target_dir,
                "depth": 1  # Shallow clone for faster operation
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/git/clone",
                    json=clone_config,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    logger.info("Repository cloned successfully", repo_url=repo_url)
                    return True
                else:
                    logger.error("Failed to clone repository", 
                               repo_url=repo_url,
                               status_code=response.status_code,
                               response=response.text)
                    return False
                    
        except Exception as e:
            logger.error("Repository cloning failed", repo_url=repo_url, error=str(e))
            return False
    
    async def execute_commands(self, commands: List[str], working_dir: str, timeout: int = 300) -> Dict[str, Any]:
        """Execute a list of commands in the sandbox"""
        try:
            logger.info("Executing commands", command_count=len(commands), working_dir=working_dir)
            
            execution_config = {
                "commands": commands,
                "working_directory": working_dir,
                "timeout": timeout,
                "capture_output": True,
                "environment": "inherit"
            }
            
            async with httpx.AsyncClient(timeout=timeout + 30) as client:
                response = await client.post(
                    f"{self.base_url}/api/execute",
                    json=execution_config,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("Commands executed", 
                               success=result.get("success"),
                               exit_code=result.get("exit_code"))
                    return result
                else:
                    logger.error("Command execution failed", 
                               status_code=response.status_code,
                               response=response.text)
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "logs": []
                    }
                    
        except Exception as e:
            logger.error("Command execution failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "logs": []
            }
    
    async def get_snapshot_status(self, snapshot_id: str) -> Dict[str, Any]:
        """Get the status of a snapshot"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(f"{self.base_url}/api/snapshots/{snapshot_id}")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error("Failed to get snapshot status", 
                               snapshot_id=snapshot_id,
                               status_code=response.status_code)
                    return {"status": "error", "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            logger.error("Failed to get snapshot status", snapshot_id=snapshot_id, error=str(e))
            return {"status": "error", "error": str(e)}
    
    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot"""
        try:
            logger.info("Deleting snapshot", snapshot_id=snapshot_id)
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.delete(f"{self.base_url}/api/snapshots/{snapshot_id}")
                
                if response.status_code == 200:
                    logger.info("Snapshot deleted successfully", snapshot_id=snapshot_id)
                    return True
                else:
                    logger.error("Failed to delete snapshot", 
                               snapshot_id=snapshot_id,
                               status_code=response.status_code)
                    return False
                    
        except Exception as e:
            logger.error("Snapshot deletion failed", snapshot_id=snapshot_id, error=str(e))
            return False
    
    async def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all snapshots"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(f"{self.base_url}/api/snapshots")
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("snapshots", [])
                else:
                    logger.error("Failed to list snapshots", status_code=response.status_code)
                    return []
                    
        except Exception as e:
            logger.error("Failed to list snapshots", error=str(e))
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if Grainchain service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "service": "grainchain",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "service": "grainchain",
                        "error": f"HTTP {response.status_code}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            logger.error("Grainchain health check failed", error=str(e))
            return {
                "status": "error",
                "service": "grainchain",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_service_info(self) -> Dict[str, Any]:
        """Get Grainchain service information"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(f"{self.base_url}/api/info")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "error": f"HTTP {response.status_code}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            logger.error("Failed to get Grainchain service info", error=str(e))
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

