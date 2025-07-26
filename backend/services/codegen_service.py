"""
Codegen API Service Integration
Handles communication with the Codegen Agent API for AI-powered code generation
"""

import os
import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class CodegenAPIService:
    """Service for interacting with Codegen Agent API"""
    
    def __init__(self):
        self.org_id = os.getenv("CODEGEN_ORG_ID", "323")
        self.api_token = os.getenv("CODEGEN_API_TOKEN")
        self.base_url = "https://api.codegen.com/v1"
        
        if not self.api_token:
            raise ValueError("CODEGEN_API_TOKEN environment variable is required")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "User-Agent": "CodegenCICD-Dashboard/1.0"
        }
        
        logger.info(f"Initialized Codegen API service for org {self.org_id}")

    async def start_agent_run(self, prompt: str, project_context: Optional[str] = None, 
                             planning_statement: Optional[str] = None) -> Dict[str, Any]:
        """Start a new agent run with the Codegen API"""
        try:
            # Construct the full prompt with context
            full_prompt = ""
            
            if planning_statement:
                full_prompt += f"{planning_statement}\n\n"
            
            if project_context:
                full_prompt += f"{project_context}\n\n"
            
            full_prompt += prompt
            
            payload = {
                "prompt": full_prompt,
                "metadata": {
                    "source": "CodegenCICD-Dashboard",
                    "timestamp": datetime.now().isoformat(),
                    "project_context": project_context
                }
            }
            
            url = f"{self.base_url}/organizations/{self.org_id}/agent/run"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self.headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Started agent run: {result.get('id', 'unknown')}")
                        return {
                            "success": True,
                            "agent_run_id": result.get("id"),
                            "status": result.get("status", "running"),
                            "data": result
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to start agent run: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"API request failed: {response.status}",
                            "details": error_text
                        }
                        
        except Exception as e:
            logger.error(f"Error starting agent run: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_agent_run_status(self, agent_run_id: str) -> Dict[str, Any]:
        """Get the status of an agent run"""
        try:
            url = f"{self.base_url}/organizations/{self.org_id}/agent/run/{agent_run_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "status": result.get("status", "unknown"),
                            "result": result.get("result"),
                            "data": result
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get agent run status: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"API request failed: {response.status}",
                            "details": error_text
                        }
                        
        except Exception as e:
            logger.error(f"Error getting agent run status: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_agent_run_logs(self, agent_run_id: str, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
        """Get logs for an agent run"""
        try:
            url = f"{self.base_url}/alpha/organizations/{self.org_id}/agent/run/{agent_run_id}/logs"
            params = {"skip": skip, "limit": limit}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "logs": result.get("logs", []),
                            "total_logs": result.get("total_logs", 0),
                            "data": result
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get agent run logs: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"API request failed: {response.status}",
                            "details": error_text
                        }
                        
        except Exception as e:
            logger.error(f"Error getting agent run logs: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def resume_agent_run(self, agent_run_id: str, prompt: str) -> Dict[str, Any]:
        """Resume an existing agent run with additional input"""
        try:
            payload = {
                "agent_run_id": int(agent_run_id),
                "prompt": prompt
            }
            
            url = f"{self.base_url}/organizations/{self.org_id}/agent/run/resume"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self.headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Resumed agent run: {agent_run_id}")
                        return {
                            "success": True,
                            "status": result.get("status", "running"),
                            "data": result
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to resume agent run: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"API request failed: {response.status}",
                            "details": error_text
                        }
                        
        except Exception as e:
            logger.error(f"Error resuming agent run: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def send_error_context(self, agent_run_id: str, error_context: Dict[str, Any]) -> Dict[str, Any]:
        """Send error context to continue an agent run for automatic fixes"""
        try:
            # Format error context for the agent
            error_prompt = f"""
VALIDATION ERROR CONTEXT:

Step: {error_context.get('step', 'unknown')}
Error: {error_context.get('error', 'unknown error')}

Logs:
{chr(10).join(error_context.get('logs', []))}

Please analyze this error and update the PR with the necessary code changes to resolve the issue.
Focus on fixing the specific problem identified in the validation step.
"""
            
            return await self.resume_agent_run(agent_run_id, error_prompt)
            
        except Exception as e:
            logger.error(f"Error sending error context: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def parse_agent_response(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse agent response to determine response type and extract relevant information"""
        try:
            result = agent_data.get("result", "")
            status = agent_data.get("status", "unknown")
            
            # Determine response type based on content
            response_type = "regular"  # default
            pr_url = None
            plan_data = None
            
            # Check for PR creation
            if "github.com" in result and "/pull/" in result:
                response_type = "pr"
                # Extract PR URL
                import re
                pr_match = re.search(r'https://github\.com/[^/]+/[^/]+/pull/\d+', result)
                if pr_match:
                    pr_url = pr_match.group(0)
            
            # Check for plan response
            elif "plan" in result.lower() or "steps:" in result.lower() or "1." in result:
                response_type = "plan"
                plan_data = {
                    "description": result,
                    "steps": self._extract_plan_steps(result)
                }
            
            return {
                "type": response_type,
                "content": result,
                "status": status,
                "pr_url": pr_url,
                "plan_data": plan_data,
                "raw_data": agent_data
            }
            
        except Exception as e:
            logger.error(f"Error parsing agent response: {str(e)}")
            return {
                "type": "regular",
                "content": str(agent_data),
                "status": "unknown",
                "error": str(e)
            }

    def _extract_plan_steps(self, content: str) -> List[str]:
        """Extract plan steps from agent response"""
        try:
            import re
            # Look for numbered steps
            steps = re.findall(r'\d+\.\s*(.+?)(?=\d+\.|$)', content, re.DOTALL)
            return [step.strip() for step in steps if step.strip()]
        except Exception:
            return []

    async def health_check(self) -> Dict[str, Any]:
        """Check if the Codegen API is accessible"""
        try:
            # Try to get organization info as a health check
            url = f"{self.base_url}/organizations/{self.org_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        return {
                            "success": True,
                            "status": "healthy",
                            "org_id": self.org_id
                        }
                    else:
                        return {
                            "success": False,
                            "status": "unhealthy",
                            "error": f"API returned status {response.status}"
                        }
                        
        except Exception as e:
            return {
                "success": False,
                "status": "unhealthy",
                "error": str(e)
            }


# Global service instance
codegen_service = CodegenAPIService()
