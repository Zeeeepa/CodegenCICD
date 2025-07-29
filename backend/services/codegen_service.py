"""
Codegen API service for managing agent runs
"""
import os
import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class CodegenService:
    def __init__(self):
        self.api_token = os.getenv("CODEGEN_API_TOKEN")
        self.org_id = os.getenv("CODEGEN_ORG_ID", "323")
        self.base_url = "https://api.codegen.com/v1"
        
        if not self.api_token:
            raise ValueError("CODEGEN_API_TOKEN environment variable is required")
    
    async def create_agent_run(self, prompt: str, project_context: str = "") -> Dict[str, Any]:
        """Create a new agent run via Codegen API"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "org_id": int(self.org_id),
                    "prompt": prompt,
                    "context": project_context,
                    "stream": False
                }
                
                response = await client.post(
                    f"{self.base_url}/agents/runs",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Created Codegen agent run: {result.get('id')}")
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error creating agent run: {e}")
            raise Exception(f"Failed to create agent run: {e}")
        except Exception as e:
            logger.error(f"Error creating agent run: {e}")
            raise
    
    async def get_agent_run_status(self, run_id: int) -> Dict[str, Any]:
        """Get the status of an agent run"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json"
                }
                
                response = await client.get(
                    f"{self.base_url}/agents/runs/{run_id}",
                    headers=headers,
                    timeout=30.0
                )
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting agent run status: {e}")
            raise Exception(f"Failed to get agent run status: {e}")
        except Exception as e:
            logger.error(f"Error getting agent run status: {e}")
            raise
    
    async def continue_agent_run(self, run_id: int, message: str) -> Dict[str, Any]:
        """Continue an existing agent run with additional input"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "message": message
                }
                
                response = await client.post(
                    f"{self.base_url}/agents/runs/{run_id}/continue",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Continued Codegen agent run: {run_id}")
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error continuing agent run: {e}")
            raise Exception(f"Failed to continue agent run: {e}")
        except Exception as e:
            logger.error(f"Error continuing agent run: {e}")
            raise
    
    async def cancel_agent_run(self, run_id: int) -> Dict[str, Any]:
        """Cancel a running agent run"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json"
                }
                
                response = await client.post(
                    f"{self.base_url}/agents/runs/{run_id}/cancel",
                    headers=headers,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Cancelled Codegen agent run: {run_id}")
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error cancelling agent run: {e}")
            raise Exception(f"Failed to cancel agent run: {e}")
        except Exception as e:
            logger.error(f"Error cancelling agent run: {e}")
            raise
    
    async def get_agent_run_logs(self, run_id: int) -> Dict[str, Any]:
        """Get logs for an agent run"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json"
                }
                
                response = await client.get(
                    f"{self.base_url}/agents/runs/{run_id}/logs",
                    headers=headers,
                    timeout=30.0
                )
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting agent run logs: {e}")
            raise Exception(f"Failed to get agent run logs: {e}")
        except Exception as e:
            logger.error(f"Error getting agent run logs: {e}")
            raise

