"""
Codegen API client for agent run management
"""
import asyncio
from typing import Optional, Dict, Any, List
import httpx
import structlog
from datetime import datetime

from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class CodegenTask:
    """Represents a Codegen agent task"""
    
    def __init__(self, client: "CodegenClient", task_data: Dict[str, Any]):
        self.client = client
        self.id = task_data.get("id")
        self.status = task_data.get("status", "pending")
        self.result = task_data.get("result")
        self.error = task_data.get("error")
        self.metadata = task_data.get("metadata", {})
        self.created_at = task_data.get("created_at")
        self.updated_at = task_data.get("updated_at")
        self._raw_data = task_data
    
    async def refresh(self) -> None:
        """Refresh task status from API"""
        if not self.id:
            return
        
        try:
            updated_data = await self.client.get_task_status(self.id)
            self.status = updated_data.get("status", self.status)
            self.result = updated_data.get("result", self.result)
            self.error = updated_data.get("error", self.error)
            self.metadata = updated_data.get("metadata", self.metadata)
            self.updated_at = updated_data.get("updated_at", self.updated_at)
            self._raw_data.update(updated_data)
        except Exception as e:
            logger.error("Failed to refresh task", task_id=self.id, error=str(e))
    
    async def wait_for_completion(self, timeout: int = 300, poll_interval: int = 5) -> bool:
        """Wait for task completion with timeout"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < timeout:
            await self.refresh()
            
            if self.status in ["completed", "failed", "cancelled"]:
                return self.status == "completed"
            
            await asyncio.sleep(poll_interval)
        
        logger.warning("Task wait timeout", task_id=self.id, timeout=timeout)
        return False
    
    @property
    def is_completed(self) -> bool:
        """Check if task is completed"""
        return self.status == "completed"
    
    @property
    def is_failed(self) -> bool:
        """Check if task failed"""
        return self.status == "failed"
    
    @property
    def is_running(self) -> bool:
        """Check if task is running"""
        return self.status in ["running", "pending"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            "id": self.id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_completed": self.is_completed,
            "is_failed": self.is_failed,
            "is_running": self.is_running
        }


class CodegenClient:
    """Client for interacting with Codegen API"""
    
    def __init__(self, org_id: Optional[int] = None, api_token: Optional[str] = None):
        self.org_id = org_id or settings.codegen_org_id
        self.api_token = api_token or settings.codegen_api_token
        self.base_url = "https://api.codegen.com/v1"
        
        if not self.org_id or not self.api_token:
            raise ValueError("Codegen org_id and api_token must be provided")
        
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "User-Agent": "CodegenCICD/1.0.0"
            },
            timeout=httpx.Timeout(30.0)
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def create_agent_run(self, prompt: str, context: Optional[Dict[str, Any]] = None,
                              repository: Optional[str] = None, branch: Optional[str] = None,
                              planning_statement: Optional[str] = None) -> CodegenTask:
        """Create a new agent run"""
        try:
            payload = {
                "org_id": self.org_id,
                "prompt": prompt,
                "context": context or {},
                "repository": repository,
                "branch": branch
            }
            
            if planning_statement:
                payload["planning_statement"] = planning_statement
            
            logger.info("Creating agent run", prompt=prompt[:100], repository=repository)
            
            response = await self.client.post(f"{self.base_url}/agent-runs", json=payload)
            response.raise_for_status()
            
            task_data = response.json()
            task = CodegenTask(self, task_data)
            
            logger.info("Agent run created", task_id=task.id, status=task.status)
            return task
            
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error creating agent run", status_code=e.response.status_code, 
                        response=e.response.text)
            raise
        except Exception as e:
            logger.error("Failed to create agent run", error=str(e))
            raise
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status by ID"""
        try:
            response = await self.client.get(f"{self.base_url}/agent-runs/{task_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error getting task status", task_id=task_id, 
                        status_code=e.response.status_code)
            raise
        except Exception as e:
            logger.error("Failed to get task status", task_id=task_id, error=str(e))
            raise
    
    async def continue_agent_run(self, task_id: str, prompt: str, 
                                context: Optional[Dict[str, Any]] = None) -> CodegenTask:
        """Continue an existing agent run with additional prompt"""
        try:
            payload = {
                "prompt": prompt,
                "context": context or {}
            }
            
            logger.info("Continuing agent run", task_id=task_id, prompt=prompt[:100])
            
            response = await self.client.post(f"{self.base_url}/agent-runs/{task_id}/continue", 
                                            json=payload)
            response.raise_for_status()
            
            task_data = response.json()
            task = CodegenTask(self, task_data)
            
            logger.info("Agent run continued", task_id=task.id, status=task.status)
            return task
            
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error continuing agent run", task_id=task_id,
                        status_code=e.response.status_code, response=e.response.text)
            raise
        except Exception as e:
            logger.error("Failed to continue agent run", task_id=task_id, error=str(e))
            raise
    
    async def cancel_agent_run(self, task_id: str) -> bool:
        """Cancel an agent run"""
        try:
            response = await self.client.post(f"{self.base_url}/agent-runs/{task_id}/cancel")
            response.raise_for_status()
            
            logger.info("Agent run cancelled", task_id=task_id)
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error cancelling agent run", task_id=task_id,
                        status_code=e.response.status_code)
            return False
        except Exception as e:
            logger.error("Failed to cancel agent run", task_id=task_id, error=str(e))
            return False
    
    async def list_agent_runs(self, limit: int = 50, offset: int = 0,
                             status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List agent runs for the organization"""
        try:
            params = {
                "org_id": self.org_id,
                "limit": limit,
                "offset": offset
            }
            
            if status:
                params["status"] = status
            
            response = await self.client.get(f"{self.base_url}/agent-runs", params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get("runs", [])
            
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error listing agent runs", status_code=e.response.status_code)
            raise
        except Exception as e:
            logger.error("Failed to list agent runs", error=str(e))
            raise
    
    async def get_agent_run_logs(self, task_id: str) -> List[Dict[str, Any]]:
        """Get logs for an agent run"""
        try:
            response = await self.client.get(f"{self.base_url}/agent-runs/{task_id}/logs")
            response.raise_for_status()
            
            data = response.json()
            return data.get("logs", [])
            
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error getting agent run logs", task_id=task_id,
                        status_code=e.response.status_code)
            raise
        except Exception as e:
            logger.error("Failed to get agent run logs", task_id=task_id, error=str(e))
            raise
    
    async def health_check(self) -> bool:
        """Check if Codegen API is accessible"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error("Codegen API health check failed", error=str(e))
            return False
    
    async def get_organization_info(self) -> Dict[str, Any]:
        """Get organization information"""
        try:
            response = await self.client.get(f"{self.base_url}/organizations/{self.org_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to get organization info", error=str(e))
            raise


# Global client instance
_codegen_client: Optional[CodegenClient] = None


async def get_codegen_client() -> CodegenClient:
    """Get global Codegen client instance"""
    global _codegen_client
    if _codegen_client is None:
        _codegen_client = CodegenClient()
    return _codegen_client


async def create_agent_run(prompt: str, context: Optional[Dict[str, Any]] = None,
                          repository: Optional[str] = None, branch: Optional[str] = None,
                          planning_statement: Optional[str] = None) -> CodegenTask:
    """Convenience function to create agent run"""
    client = await get_codegen_client()
    return await client.create_agent_run(prompt, context, repository, branch, planning_statement)


async def continue_agent_run(task_id: str, prompt: str, 
                           context: Optional[Dict[str, Any]] = None) -> CodegenTask:
    """Convenience function to continue agent run"""
    client = await get_codegen_client()
    return await client.continue_agent_run(task_id, prompt, context)

