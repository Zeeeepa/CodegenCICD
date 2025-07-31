"""
Enhanced Codegen API Client for agent run management
"""
import asyncio
import httpx
import json
import time
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime
import structlog
import os
from dataclasses import dataclass
from enum import Enum

logger = structlog.get_logger(__name__)


class AgentRunResponseType(str, Enum):
    """Types of agent run responses"""
    REGULAR = "regular"
    PLAN = "plan"
    PR = "pr"
    ERROR = "error"


@dataclass
class AgentRunResponse:
    """Response from agent run operations"""
    run_id: str
    status: str
    response_type: AgentRunResponseType
    content: str
    metadata: Dict[str, Any]
    created_at: datetime
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'AgentRunResponse':
        """Create AgentRunResponse from API response data"""
        return cls(
            run_id=data.get('id', ''),
            status=data.get('status', 'unknown'),
            response_type=cls._determine_response_type(data),
            content=data.get('content', ''),
            metadata=data.get('metadata', {}),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
        )
    
    @staticmethod
    def _determine_response_type(data: Dict[str, Any]) -> AgentRunResponseType:
        """Determine response type from API data"""
        content = data.get('content', '').lower()
        if 'plan' in content and 'step' in content:
            return AgentRunResponseType.PLAN
        elif 'pull request' in content or 'pr' in content:
            return AgentRunResponseType.PR
        elif 'error' in data.get('status', '').lower():
            return AgentRunResponseType.ERROR
        else:
            return AgentRunResponseType.REGULAR


@dataclass
class AgentRunLog:
    """Agent run log entry"""
    timestamp: datetime
    level: str
    message: str
    metadata: Dict[str, Any]


class CodegenAPIError(Exception):
    """Custom exception for Codegen API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message)


class CodegenAPIClient:
    """Enhanced client for interacting with the Codegen API"""
    
    def __init__(self, api_token: Optional[str] = None, org_id: Optional[str] = None):
        self.base_url = "https://api.codegen.com/v1"
        self.org_id = org_id or os.getenv("CODEGEN_ORG_ID")
        self.api_token = api_token or os.getenv("CODEGEN_API_TOKEN")
        
        if not self.api_token or not self.org_id:
            raise CodegenAPIError("Missing CODEGEN_API_TOKEN or CODEGEN_ORG_ID")
        
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "User-Agent": "CodegenCICD/1.0"
            }
        )
        self._retry_attempts = 3
        self._retry_delay = 1.0
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic and error handling"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        for attempt in range(self._retry_attempts):
            try:
                logger.info(f"Making {method} request to {url}", attempt=attempt + 1)
                
                response = await self.client.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Request successful", status_code=response.status_code)
                    return result
                elif response.status_code == 429:  # Rate limited
                    wait_time = self._retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limited, waiting {wait_time}s", attempt=attempt + 1)
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    error_data = response.json() if response.content else {}
                    raise CodegenAPIError(
                        f"API request failed: {response.status_code}",
                        status_code=response.status_code,
                        response_data=error_data
                    )
                    
            except httpx.RequestError as e:
                if attempt == self._retry_attempts - 1:
                    raise CodegenAPIError(f"Request failed after {self._retry_attempts} attempts: {e}")
                
                wait_time = self._retry_delay * (2 ** attempt)
                logger.warning(f"Request failed, retrying in {wait_time}s", error=str(e), attempt=attempt + 1)
                await asyncio.sleep(wait_time)
        
        raise CodegenAPIError(f"Request failed after {self._retry_attempts} attempts")
    
    async def create_agent_run(
        self, 
        project_context: str, 
        user_prompt: str, 
        planning_statement: Optional[str] = None
    ) -> AgentRunResponse:
        """Create a new agent run with project context and user prompt"""
        
        # Construct the full prompt with project context
        full_prompt = f"<Project='{project_context}'>\n\n"
        
        if planning_statement:
            full_prompt += f"Planning Statement: {planning_statement}\n\n"
        
        full_prompt += f"User Request: {user_prompt}"
        
        data = {
            "organization_id": self.org_id,
            "prompt": full_prompt,
            "metadata": {
                "project_context": project_context,
                "user_prompt": user_prompt,
                "planning_statement": planning_statement,
                "source": "CodegenCICD"
            }
        }
        
        logger.info("Creating agent run", project=project_context, prompt_length=len(full_prompt))
        
        try:
            response_data = await self._make_request("POST", "/agents/runs", data=data)
            return AgentRunResponse.from_api_response(response_data)
        except Exception as e:
            logger.error("Failed to create agent run", error=str(e))
            raise
    
    async def get_agent_run_status(self, run_id: str) -> AgentRunResponse:
        """Get the current status of an agent run"""
        logger.info("Getting agent run status", run_id=run_id)
        
        try:
            response_data = await self._make_request("GET", f"/agents/runs/{run_id}")
            return AgentRunResponse.from_api_response(response_data)
        except Exception as e:
            logger.error("Failed to get agent run status", run_id=run_id, error=str(e))
            raise
    
    async def confirm_plan(self, run_id: str, confirmation: str = "Proceed") -> AgentRunResponse:
        """Confirm a plan from an agent run"""
        data = {
            "message": confirmation,
            "action": "confirm_plan"
        }
        
        logger.info("Confirming plan", run_id=run_id, confirmation=confirmation)
        
        try:
            response_data = await self._make_request("POST", f"/agents/runs/{run_id}/continue", data=data)
            return AgentRunResponse.from_api_response(response_data)
        except Exception as e:
            logger.error("Failed to confirm plan", run_id=run_id, error=str(e))
            raise
    
    async def continue_agent_run(self, run_id: str, continuation_prompt: str) -> AgentRunResponse:
        """Continue an agent run with additional prompt"""
        data = {
            "message": continuation_prompt,
            "action": "continue"
        }
        
        logger.info("Continuing agent run", run_id=run_id, prompt_length=len(continuation_prompt))
        
        try:
            response_data = await self._make_request("POST", f"/agents/runs/{run_id}/continue", data=data)
            return AgentRunResponse.from_api_response(response_data)
        except Exception as e:
            logger.error("Failed to continue agent run", run_id=run_id, error=str(e))
            raise
    
    async def cancel_agent_run(self, run_id: str) -> bool:
        """Cancel an active agent run"""
        logger.info("Cancelling agent run", run_id=run_id)
        
        try:
            await self._make_request("POST", f"/agents/runs/{run_id}/cancel")
            return True
        except Exception as e:
            logger.error("Failed to cancel agent run", run_id=run_id, error=str(e))
            return False
    
    async def get_agent_run_logs(self, run_id: str) -> List[AgentRunLog]:
        """Get logs for an agent run"""
        logger.info("Getting agent run logs", run_id=run_id)
        
        try:
            response_data = await self._make_request("GET", f"/agents/runs/{run_id}/logs")
            logs = []
            
            for log_entry in response_data.get('logs', []):
                logs.append(AgentRunLog(
                    timestamp=datetime.fromisoformat(log_entry.get('timestamp', datetime.now().isoformat())),
                    level=log_entry.get('level', 'INFO'),
                    message=log_entry.get('message', ''),
                    metadata=log_entry.get('metadata', {})
                ))
            
            return logs
        except Exception as e:
            logger.error("Failed to get agent run logs", run_id=run_id, error=str(e))
            return []
    
    async def list_agent_runs(self, limit: int = 50) -> List[AgentRunResponse]:
        """List recent agent runs for the organization"""
        params = {"limit": limit, "organization_id": self.org_id}
        
        logger.info("Listing agent runs", limit=limit)
        
        try:
            response_data = await self._make_request("GET", "/agents/runs", params=params)
            runs = []
            
            for run_data in response_data.get('runs', []):
                runs.append(AgentRunResponse.from_api_response(run_data))
            
            return runs
        except Exception as e:
            logger.error("Failed to list agent runs", error=str(e))
            return []
    
    async def validate_connection(self) -> bool:
        """Validate API connection and credentials"""
        logger.info("Validating Codegen API connection")
        
        try:
            await self._make_request("GET", "/organizations/current")
            logger.info("API connection validated successfully")
            return True
        except Exception as e:
            logger.error("API connection validation failed", error=str(e))
            return False

