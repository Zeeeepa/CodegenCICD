"""
Comprehensive Codegen API client with advanced features
Supports all Codegen API operations with robust error handling
"""
import asyncio
from typing import Optional, Dict, Any, List, Union
import httpx
import structlog
from datetime import datetime
import json

from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class CodegenTask:
    """Enhanced Codegen task representation with comprehensive functionality"""
    
    def __init__(self, client: "CodegenClient", task_data: Dict[str, Any]):
        self.client = client
        self.id = task_data.get("id")
        self.status = task_data.get("status", "pending")
        self.result = task_data.get("result")
        self.error = task_data.get("error")
        self.metadata = task_data.get("metadata", {})
        self.created_at = task_data.get("created_at")
        self.updated_at = task_data.get("updated_at")
        self.web_url = task_data.get("web_url")
        self._raw_data = task_data
        self._logs_cache = None
    
    async def refresh(self) -> None:
        """Refresh task status from API with enhanced error handling"""
        if not self.id:
            logger.warning("Cannot refresh task without ID")
            return
        
        try:
            updated_data = await self.client.get_task_status(self.id)
            self._update_from_data(updated_data)
            logger.debug("Task refreshed", task_id=self.id, status=self.status)
        except Exception as e:
            logger.error("Failed to refresh task", task_id=self.id, error=str(e))
            raise
    
    def _update_from_data(self, data: Dict[str, Any]) -> None:
        """Update task from API data"""
        self.status = data.get("status", self.status)
        self.result = data.get("result", self.result)
        self.error = data.get("error", self.error)
        self.metadata = data.get("metadata", self.metadata)
        self.updated_at = data.get("updated_at", self.updated_at)
        self.web_url = data.get("web_url", self.web_url)
        self._raw_data.update(data)
        self._logs_cache = None  # Invalidate logs cache
    
    async def wait_for_completion(self, timeout: int = 300, poll_interval: int = 5) -> bool:
        """Wait for task completion with configurable timeout and polling"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < timeout:
            await self.refresh()
            
            if self.is_completed:
                return self.is_successful
            
            await asyncio.sleep(poll_interval)
        
        logger.warning("Task wait timeout", task_id=self.id, timeout=timeout)
        return False
    
    async def get_logs(self, refresh: bool = False) -> List[Dict[str, Any]]:
        """Get task execution logs with caching"""
        if self._logs_cache is None or refresh:
            try:
                self._logs_cache = await self.client.get_agent_run_logs(self.id)
            except Exception as e:
                logger.error("Failed to get task logs", task_id=self.id, error=str(e))
                self._logs_cache = []
        
        return self._logs_cache
    
    async def continue_with_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> "CodegenTask":
        """Continue task with additional prompt"""
        return await self.client.continue_agent_run(self.id, prompt, context)
    
    async def cancel(self) -> bool:
        """Cancel the task"""
        return await self.client.cancel_agent_run(self.id)
    
    @property
    def is_completed(self) -> bool:
        """Check if task is completed"""
        return self.status in ["completed", "failed", "cancelled"]
    
    @property
    def is_successful(self) -> bool:
        """Check if task completed successfully"""
        return self.status == "completed"
    
    @property
    def is_failed(self) -> bool:
        """Check if task failed"""
        return self.status == "failed"
    
    @property
    def is_running(self) -> bool:
        """Check if task is running"""
        return self.status in ["running", "pending"]
    
    @property
    def response_type(self) -> str:
        """Determine response type: regular, plan, or pr"""
        if not self.result:
            return "unknown"
        
        result_lower = str(self.result).lower()
        
        # Check for PR creation
        if any(keyword in result_lower for keyword in ["pull request", "pr created", "github.com", "/pull/"]):
            return "pr"
        
        # Check for plan response
        if any(keyword in result_lower for keyword in ["plan:", "steps:", "1.", "2.", "3.", "propose", "approach"]):
            return "plan"
        
        # Default to regular response
        return "regular"
    
    def extract_pr_info(self) -> Optional[Dict[str, Any]]:
        """Extract PR information from result if available"""
        if self.response_type != "pr" or not self.result:
            return None
        
        result_str = str(self.result)
        pr_info = {}
        
        # Extract PR URL
        import re
        pr_url_match = re.search(r'https://github\.com/[^/]+/[^/]+/pull/(\d+)', result_str)
        if pr_url_match:
            pr_info["url"] = pr_url_match.group(0)
            pr_info["number"] = int(pr_url_match.group(1))
        
        # Extract branch name
        branch_match = re.search(r'branch[:\s]+([^\s\n]+)', result_str, re.IGNORECASE)
        if branch_match:
            pr_info["branch"] = branch_match.group(1)
        
        return pr_info if pr_info else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary with enhanced information"""
        pr_info = self.extract_pr_info()
        
        return {
            "id": self.id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
            "response_type": self.response_type,
            "pr_info": pr_info,
            "web_url": self.web_url,
            "is_completed": self.is_completed,
            "is_successful": self.is_successful,
            "is_failed": self.is_failed,
            "is_running": self.is_running,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "raw_data": self._raw_data
        }


class CodegenClient:
    """Enhanced Codegen API client with comprehensive functionality"""
    
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
                "User-Agent": f"CodegenCICD/{settings.version}",
                "X-Organization-ID": str(self.org_id)
            },
            timeout=httpx.Timeout(60.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )
        
        logger.info("Codegen client initialized", org_id=self.org_id)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def create_agent_run(self, prompt: str, context: Optional[Dict[str, Any]] = None,
                              repository: Optional[str] = None, branch: Optional[str] = None,
                              planning_statement: Optional[str] = None,
                              images: Optional[List[str]] = None) -> CodegenTask:
        """Create a new agent run with enhanced parameters"""
        try:
            # Prepare the full prompt with planning statement
            full_prompt = prompt
            if planning_statement:
                full_prompt = f"{planning_statement}\n\n{prompt}"
            
            payload = {
                "prompt": full_prompt,
                "images": images or [],
                "metadata": {
                    "repository": repository,
                    "branch": branch,
                    "context": context or {},
                    "planning_statement": planning_statement,
                    "original_prompt": prompt,
                    "created_by": "CodegenCICD Dashboard"
                }
            }
            
            logger.info("Creating agent run", 
                       prompt_length=len(prompt),
                       has_planning_statement=bool(planning_statement),
                       repository=repository,
                       branch=branch)
            
            response = await self.client.post(
                f"{self.base_url}/organizations/{self.org_id}/agent/run",
                json=payload
            )
            response.raise_for_status()
            
            task_data = response.json()
            task = CodegenTask(self, task_data)
            
            logger.info("Agent run created", 
                       task_id=task.id, 
                       status=task.status,
                       web_url=task.web_url)
            return task
            
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error creating agent run", 
                        status_code=e.response.status_code,
                        response_text=e.response.text)
            raise
        except Exception as e:
            logger.error("Failed to create agent run", error=str(e))
            raise
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status with enhanced error handling"""
        try:
            response = await self.client.get(
                f"{self.base_url}/organizations/{self.org_id}/agent/run/{task_id}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Task {task_id} not found")
            logger.error("HTTP error getting task status", 
                        task_id=task_id,
                        status_code=e.response.status_code)
            raise
        except Exception as e:
            logger.error("Failed to get task status", task_id=task_id, error=str(e))
            raise
    
    async def continue_agent_run(self, task_id: str, prompt: str, 
                                context: Optional[Dict[str, Any]] = None,
                                images: Optional[List[str]] = None) -> CodegenTask:
        """Continue an existing agent run with additional prompt"""
        try:
            payload = {
                "agent_run_id": int(task_id),
                "prompt": prompt,
                "images": images or []
            }
            
            logger.info("Continuing agent run", 
                       task_id=task_id, 
                       prompt_length=len(prompt))
            
            response = await self.client.post(
                f"{self.base_url}/organizations/{self.org_id}/agent/run/resume",
                json=payload
            )
            response.raise_for_status()
            
            task_data = response.json()
            task = CodegenTask(self, task_data)
            
            logger.info("Agent run continued", 
                       task_id=task.id, 
                       status=task.status)
            return task
            
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error continuing agent run", 
                        task_id=task_id,
                        status_code=e.response.status_code,
                        response_text=e.response.text)
            raise
        except Exception as e:
            logger.error("Failed to continue agent run", task_id=task_id, error=str(e))
            raise
    
    async def cancel_agent_run(self, task_id: str) -> bool:
        """Cancel an agent run"""
        try:
            response = await self.client.post(
                f"{self.base_url}/organizations/{self.org_id}/agent/run/{task_id}/cancel"
            )
            response.raise_for_status()
            
            logger.info("Agent run cancelled", task_id=task_id)
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error cancelling agent run", 
                        task_id=task_id,
                        status_code=e.response.status_code)
            return False
        except Exception as e:
            logger.error("Failed to cancel agent run", task_id=task_id, error=str(e))
            return False
    
    async def get_agent_run_logs(self, task_id: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get agent run logs with pagination"""
        try:
            params = {"skip": skip, "limit": limit}
            response = await self.client.get(
                f"{self.base_url}/alpha/organizations/{self.org_id}/agent/run/{task_id}/logs",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("logs", [])
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("Logs not found for task", task_id=task_id)
                return []
            logger.error("HTTP error getting agent run logs", 
                        task_id=task_id,
                        status_code=e.response.status_code)
            raise
        except Exception as e:
            logger.error("Failed to get agent run logs", task_id=task_id, error=str(e))
            raise
    
    async def list_agent_runs(self, limit: int = 50, offset: int = 0,
                             status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List agent runs for the organization"""
        try:
            params = {"limit": limit, "offset": offset}
            if status:
                params["status"] = status
            
            response = await self.client.get(
                f"{self.base_url}/organizations/{self.org_id}/agent/runs",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("runs", [])
            
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error listing agent runs", 
                        status_code=e.response.status_code)
            raise
        except Exception as e:
            logger.error("Failed to list agent runs", error=str(e))
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
            response = await self.client.get(
                f"{self.base_url}/organizations/{self.org_id}"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to get organization info", error=str(e))
            raise


# Global client instance management
_codegen_client: Optional[CodegenClient] = None


async def get_codegen_client() -> CodegenClient:
    """Get global Codegen client instance"""
    global _codegen_client
    if _codegen_client is None:
        _codegen_client = CodegenClient()
    return _codegen_client


async def close_codegen_client() -> None:
    """Close global Codegen client"""
    global _codegen_client
    if _codegen_client is not None:
        await _codegen_client.client.aclose()
        _codegen_client = None


# Convenience functions
async def create_agent_run(prompt: str, context: Optional[Dict[str, Any]] = None,
                          repository: Optional[str] = None, branch: Optional[str] = None,
                          planning_statement: Optional[str] = None,
                          images: Optional[List[str]] = None) -> CodegenTask:
    """Convenience function to create agent run"""
    client = await get_codegen_client()
    return await client.create_agent_run(prompt, context, repository, branch, planning_statement, images)


async def continue_agent_run(task_id: str, prompt: str, 
                           context: Optional[Dict[str, Any]] = None,
                           images: Optional[List[str]] = None) -> CodegenTask:
    """Convenience function to continue agent run"""
    client = await get_codegen_client()
    return await client.continue_agent_run(task_id, prompt, context, images)

