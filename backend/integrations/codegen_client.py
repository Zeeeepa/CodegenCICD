"""
Codegen API client for agent runs and task management
"""
import asyncio
import httpx
import structlog
from typing import Dict, Any, Optional, List, AsyncGenerator
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class CodegenClient:
    """Client for interacting with Codegen API"""
    
    def __init__(self):
        self.base_url = "https://api.codegen.com"
        self.org_id = settings.codegen_org_id
        self.api_token = settings.codegen_api_token
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "User-Agent": "CodegenCICD/1.0.0"
        }
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to Codegen API"""
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
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
                    "Codegen API HTTP error",
                    status_code=e.response.status_code,
                    response_text=e.response.text,
                    endpoint=endpoint
                )
                raise
            except Exception as e:
                logger.error("Codegen API request failed", error=str(e), endpoint=endpoint)
                raise
    
    async def create_agent_run(self, prompt: str, repository: str = None, 
                              planning_statement: str = None) -> Dict[str, Any]:
        """Create a new agent run"""
        payload = {
            "org_id": self.org_id,
            "prompt": prompt
        }
        
        if repository:
            payload["repository"] = repository
        
        if planning_statement:
            # Prepend planning statement to the prompt
            payload["prompt"] = f"{planning_statement}\n\n{prompt}"
        
        logger.info("Creating agent run", prompt_length=len(prompt), repository=repository)
        
        try:
            response = await self._make_request("POST", "/v1/agent-runs", json=payload)
            logger.info("Agent run created", run_id=response.get("id"))
            return response
        except Exception as e:
            logger.error("Failed to create agent run", error=str(e))
            raise
    
    async def get_agent_run(self, run_id: int) -> Dict[str, Any]:
        """Get agent run details"""
        try:
            response = await self._make_request("GET", f"/v1/agent-runs/{run_id}")
            return response
        except Exception as e:
            logger.error("Failed to get agent run", run_id=run_id, error=str(e))
            raise
    
    async def get_agent_run_status(self, run_id: int) -> str:
        """Get agent run status"""
        try:
            response = await self.get_agent_run(run_id)
            return response.get("status", "unknown")
        except Exception as e:
            logger.error("Failed to get agent run status", run_id=run_id, error=str(e))
            return "error"
    
    async def continue_agent_run(self, run_id: int, message: str) -> Dict[str, Any]:
        """Continue an existing agent run with additional input"""
        payload = {
            "message": message
        }
        
        logger.info("Continuing agent run", run_id=run_id, message_length=len(message))
        
        try:
            response = await self._make_request("POST", f"/v1/agent-runs/{run_id}/continue", json=payload)
            logger.info("Agent run continued", run_id=run_id)
            return response
        except Exception as e:
            logger.error("Failed to continue agent run", run_id=run_id, error=str(e))
            raise
    
    async def cancel_agent_run(self, run_id: int) -> Dict[str, Any]:
        """Cancel an agent run"""
        try:
            response = await self._make_request("POST", f"/v1/agent-runs/{run_id}/cancel")
            logger.info("Agent run cancelled", run_id=run_id)
            return response
        except Exception as e:
            logger.error("Failed to cancel agent run", run_id=run_id, error=str(e))
            raise
    
    async def get_agent_run_logs(self, run_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Get agent run logs"""
        try:
            response = await self._make_request(
                "GET", 
                f"/v1/agent-runs/{run_id}/logs",
                params={"limit": limit}
            )
            return response.get("logs", [])
        except Exception as e:
            logger.error("Failed to get agent run logs", run_id=run_id, error=str(e))
            return []
    
    async def stream_agent_run_logs(self, run_id: int) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream agent run logs in real-time"""
        url = f"{self.base_url}/v1/agent-runs/{run_id}/logs/stream"
        
        async with httpx.AsyncClient(timeout=None) as client:
            try:
                async with client.stream(
                    "GET",
                    url,
                    headers=self.headers
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                import json
                                data = json.loads(line[6:])  # Remove "data: " prefix
                                yield data
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logger.error("Failed to stream agent run logs", run_id=run_id, error=str(e))
                raise
    
    async def get_agent_run_result(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get agent run final result"""
        try:
            response = await self.get_agent_run(run_id)
            
            if response.get("status") == "completed":
                return {
                    "type": response.get("result_type", "regular"),
                    "content": response.get("result", ""),
                    "pr_url": response.get("pr_url"),
                    "pr_number": response.get("pr_number"),
                    "metadata": response.get("metadata", {})
                }
            
            return None
        except Exception as e:
            logger.error("Failed to get agent run result", run_id=run_id, error=str(e))
            return None
    
    async def confirm_plan(self, run_id: int, confirmation: str = "Proceed") -> Dict[str, Any]:
        """Confirm a proposed plan"""
        payload = {
            "confirmation": confirmation
        }
        
        logger.info("Confirming plan", run_id=run_id, confirmation=confirmation)
        
        try:
            response = await self._make_request("POST", f"/v1/agent-runs/{run_id}/confirm-plan", json=payload)
            logger.info("Plan confirmed", run_id=run_id)
            return response
        except Exception as e:
            logger.error("Failed to confirm plan", run_id=run_id, error=str(e))
            raise
    
    async def modify_plan(self, run_id: int, modifications: str) -> Dict[str, Any]:
        """Modify a proposed plan"""
        payload = {
            "modifications": modifications
        }
        
        logger.info("Modifying plan", run_id=run_id, modifications_length=len(modifications))
        
        try:
            response = await self._make_request("POST", f"/v1/agent-runs/{run_id}/modify-plan", json=payload)
            logger.info("Plan modified", run_id=run_id)
            return response
        except Exception as e:
            logger.error("Failed to modify plan", run_id=run_id, error=str(e))
            raise
    
    async def health_check(self) -> bool:
        """Check if Codegen API is accessible"""
        try:
            await self._make_request("GET", "/health")
            return True
        except Exception as e:
            logger.error("Codegen API health check failed", error=str(e))
            return False
    
    async def get_organization_info(self) -> Dict[str, Any]:
        """Get organization information"""
        try:
            response = await self._make_request("GET", f"/v1/organizations/{self.org_id}")
            return response
        except Exception as e:
            logger.error("Failed to get organization info", error=str(e))
            raise
    
    async def list_agent_runs(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List agent runs for the organization"""
        try:
            response = await self._make_request(
                "GET",
                f"/v1/organizations/{self.org_id}/agent-runs",
                params={"limit": limit, "offset": offset}
            )
            return response.get("agent_runs", [])
        except Exception as e:
            logger.error("Failed to list agent runs", error=str(e))
            return []

