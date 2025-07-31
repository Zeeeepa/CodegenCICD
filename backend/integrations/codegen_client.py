"""
Codegen API client for CodegenCICD Dashboard
"""
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

from .base_client import BaseClient, APIError
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class CodegenClient(BaseClient):
    """Client for interacting with Codegen API"""
    
    def __init__(self, api_token: Optional[str] = None, org_id: Optional[str] = None):
        self.api_token = api_token or settings.codegen_api_token
        self.org_id = org_id or settings.codegen_org_id
        
        if not self.api_token:
            raise ValueError("Codegen API token is required")
        if not self.org_id:
            raise ValueError("Codegen organization ID is required")
        
        super().__init__(
            service_name="codegen_api",
            base_url="https://api.codegen.com/v1",
            api_key=self.api_token,
            timeout=60,  # Longer timeout for agent runs
            max_retries=3
        )
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for Codegen API requests"""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "User-Agent": "CodegenCICD-Dashboard/1.0"
        }
    
    async def _health_check_request(self) -> None:
        """Health check by getting organization info"""
        await self.get(f"/organizations/{self.org_id}")
    
    # Agent Run Management
    async def create_agent_run(self,
                              target: str,
                              repo_name: str,
                              planning_statement: Optional[str] = None,
                              auto_confirm_plans: bool = False,
                              max_iterations: int = 10) -> Dict[str, Any]:
        """Create a new agent run"""
        try:
            payload = {
                "target": target,
                "repo_name": repo_name,
                "auto_confirm_plans": auto_confirm_plans,
                "max_iterations": max_iterations
            }
            
            if planning_statement:
                payload["planning_statement"] = planning_statement
            
            self.logger.info("Creating agent run",
                           target=target[:100],  # Truncate for logging
                           repo_name=repo_name,
                           auto_confirm_plans=auto_confirm_plans)
            
            response = await self.post(f"/organizations/{self.org_id}/agent-runs", data=payload)
            
            self.logger.info("Agent run created successfully",
                           run_id=response.get("id"),
                           status=response.get("status"))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to create agent run",
                            error=str(e),
                            target=target[:100])
            raise
    
    async def get_agent_run(self, run_id: str) -> Dict[str, Any]:
        """Get agent run details"""
        try:
            response = await self.get(f"/organizations/{self.org_id}/agent-runs/{run_id}")
            return response
        except Exception as e:
            self.logger.error("Failed to get agent run",
                            run_id=run_id,
                            error=str(e))
            raise
    
    async def continue_agent_run(self, run_id: str, user_input: str) -> Dict[str, Any]:
        """Continue an agent run with user input"""
        try:
            payload = {
                "user_input": user_input
            }
            
            self.logger.info("Continuing agent run",
                           run_id=run_id,
                           input_length=len(user_input))
            
            response = await self.post(
                f"/organizations/{self.org_id}/agent-runs/{run_id}/continue",
                data=payload
            )
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to continue agent run",
                            run_id=run_id,
                            error=str(e))
            raise
    
    async def cancel_agent_run(self, run_id: str) -> Dict[str, Any]:
        """Cancel an agent run"""
        try:
            response = await self.post(f"/organizations/{self.org_id}/agent-runs/{run_id}/cancel")
            
            self.logger.info("Agent run cancelled",
                           run_id=run_id)
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to cancel agent run",
                            run_id=run_id,
                            error=str(e))
            raise
    
    async def list_agent_runs(self,
                             limit: int = 50,
                             offset: int = 0,
                             status: Optional[str] = None) -> Dict[str, Any]:
        """List agent runs for the organization"""
        try:
            params = {
                "limit": limit,
                "offset": offset
            }
            
            if status:
                params["status"] = status
            
            response = await self.get(f"/organizations/{self.org_id}/agent-runs", params=params)
            return response
            
        except Exception as e:
            self.logger.error("Failed to list agent runs", error=str(e))
            raise
    
    # Repository Management
    async def list_repositories(self) -> List[Dict[str, Any]]:
        """List repositories accessible to the organization"""
        try:
            response = await self.get(f"/organizations/{self.org_id}/repositories")
            return response.get("repositories", [])
        except Exception as e:
            self.logger.error("Failed to list repositories", error=str(e))
            raise
    
    async def get_repository(self, repo_name: str) -> Dict[str, Any]:
        """Get repository details"""
        try:
            response = await self.get(f"/organizations/{self.org_id}/repositories/{repo_name}")
            return response
        except Exception as e:
            self.logger.error("Failed to get repository",
                            repo_name=repo_name,
                            error=str(e))
            raise
    
    # Organization Management
    async def get_organization(self) -> Dict[str, Any]:
        """Get organization details"""
        try:
            response = await self.get(f"/organizations/{self.org_id}")
            return response
        except Exception as e:
            self.logger.error("Failed to get organization", error=str(e))
            raise
    
    async def get_organization_usage(self) -> Dict[str, Any]:
        """Get organization usage statistics"""
        try:
            response = await self.get(f"/organizations/{self.org_id}/usage")
            return response
        except Exception as e:
            self.logger.error("Failed to get organization usage", error=str(e))
            raise
    
    # Utility Methods
    async def wait_for_completion(self,
                                 run_id: str,
                                 timeout: int = 1800,  # 30 minutes
                                 poll_interval: int = 5) -> Dict[str, Any]:
        """Wait for agent run to complete with polling"""
        start_time = datetime.utcnow()
        
        while True:
            try:
                run_data = await self.get_agent_run(run_id)
                status = run_data.get("status")
                
                # Check if completed
                if status in ["completed", "failed", "cancelled"]:
                    self.logger.info("Agent run completed",
                                   run_id=run_id,
                                   status=status,
                                   duration=(datetime.utcnow() - start_time).total_seconds())
                    return run_data
                
                # Check timeout
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > timeout:
                    self.logger.warning("Agent run timeout",
                                      run_id=run_id,
                                      elapsed=elapsed)
                    raise APIError(f"Agent run {run_id} timed out after {timeout} seconds")
                
                # Wait before next poll
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                self.logger.error("Error while waiting for agent run completion",
                                run_id=run_id,
                                error=str(e))
                raise
    
    async def get_run_logs(self, 
                          run_id: str, 
                          skip: int = 0, 
                          limit: int = 100) -> Dict[str, Any]:
        """Get logs for an agent run with pagination
        
        Args:
            run_id: The ID of the agent run
            skip: Number of logs to skip for pagination (default: 0)
            limit: Maximum number of logs to return (default: 100, max: 100)
            
        Returns:
            Dict containing agent run details and paginated logs
        """
        try:
            params = {
                "skip": skip,
                "limit": min(limit, 100)  # Enforce API limit
            }
            
            response = await self.get(
                f"/organizations/{self.org_id}/agent/run/{run_id}/logs",
                params=params
            )
            
            self.logger.info("Retrieved agent run logs",
                           run_id=run_id,
                           total_logs=response.get("total_logs", 0),
                           page=response.get("page", 1))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to get agent run logs",
                            run_id=run_id,
                            error=str(e))
            raise
    
    async def get_run_artifacts(self, run_id: str) -> List[Dict[str, Any]]:
        """Get artifacts created by an agent run"""
        try:
            response = await self.get(f"/organizations/{self.org_id}/agent-runs/{run_id}/artifacts")
            return response.get("artifacts", [])
        except Exception as e:
            self.logger.error("Failed to get agent run artifacts",
                            run_id=run_id,
                            error=str(e))
            raise
    
    async def get_run_logs_all(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all logs for an agent run (handles pagination automatically)"""
        all_logs = []
        skip = 0
        limit = 100
        
        try:
            while True:
                response = await self.get_run_logs(run_id, skip=skip, limit=limit)
                logs = response.get("logs", [])
                
                if not logs:
                    break
                    
                all_logs.extend(logs)
                
                # Check if we've retrieved all logs
                total_logs = response.get("total_logs", 0)
                if len(all_logs) >= total_logs:
                    break
                    
                skip += limit
            
            self.logger.info("Retrieved all agent run logs",
                           run_id=run_id,
                           total_logs=len(all_logs))
            
            return all_logs
            
        except Exception as e:
            self.logger.error("Failed to get all agent run logs",
                            run_id=run_id,
                            error=str(e))
            raise
    
    async def get_run_logs_by_type(self, 
                                  run_id: str, 
                                  message_types: List[str]) -> List[Dict[str, Any]]:
        """Get logs filtered by message type(s)
        
        Args:
            run_id: The ID of the agent run
            message_types: List of message types to filter by (e.g., ['ACTION', 'ERROR'])
        """
        try:
            all_logs = await self.get_run_logs_all(run_id)
            filtered_logs = [
                log for log in all_logs 
                if log.get("message_type") in message_types
            ]
            
            self.logger.info("Filtered agent run logs by type",
                           run_id=run_id,
                           message_types=message_types,
                           filtered_count=len(filtered_logs),
                           total_count=len(all_logs))
            
            return filtered_logs
            
        except Exception as e:
            self.logger.error("Failed to get filtered agent run logs",
                            run_id=run_id,
                            message_types=message_types,
                            error=str(e))
            raise
    
    async def get_run_errors(self, run_id: str) -> List[Dict[str, Any]]:
        """Get only error logs for an agent run"""
        return await self.get_run_logs_by_type(run_id, ["ERROR"])
    
    async def get_run_actions(self, run_id: str) -> List[Dict[str, Any]]:
        """Get only action logs for an agent run"""
        return await self.get_run_logs_by_type(run_id, ["ACTION"])
    
    # Error Recovery
    async def create_error_fix_run(self,
                                  original_run_id: str,
                                  error_context: str,
                                  repo_name: str) -> Dict[str, Any]:
        """Create an agent run to fix errors from a previous run"""
        try:
            # Get the original run details
            original_run = await self.get_agent_run(original_run_id)
            
            # Create a new run with error context
            target = f"Fix the following error from run {original_run_id}:\n\n{error_context}\n\nOriginal target: {original_run.get('target', 'Unknown')}"
            
            payload = {
                "target": target,
                "repo_name": repo_name,
                "auto_confirm_plans": True,  # Auto-confirm for error fixes
                "max_iterations": 5,  # Shorter iteration limit for fixes
                "parent_run_id": original_run_id,
                "run_type": "error_fix"
            }
            
            self.logger.info("Creating error fix run",
                           original_run_id=original_run_id,
                           repo_name=repo_name)
            
            response = await self.post(f"/organizations/{self.org_id}/agent-runs", data=payload)
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to create error fix run",
                            original_run_id=original_run_id,
                            error=str(e))
            raise
