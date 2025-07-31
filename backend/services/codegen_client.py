"""
Codegen API Client for agent run management
"""
import asyncio
import httpx
import json
import time
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime
import structlog

from backend.config import get_settings
from backend.models.agent_run import AgentRun, AgentRunStatus, AgentRunType, AgentRunStep, AgentRunResponse
from backend.database import get_db_session

logger = structlog.get_logger(__name__)
settings = get_settings()


class CodegenAPIError(Exception):
    """Custom exception for Codegen API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message)


class CodegenClient:
    """Client for interacting with the Codegen API"""
    
    def __init__(self):
        self.base_url = "https://api.codegen.com/v1"
        self.org_id = settings.codegen_org_id
        self.api_token = settings.codegen_api_token
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "User-Agent": "CodegenCICD/1.0"
            }
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def create_agent_run(
        self,
        project_id: str,
        target: str,
        planning_statement: Optional[str] = None,
        auto_confirm_plans: bool = False,
        max_iterations: int = 10
    ) -> Dict[str, Any]:
        """
        Create a new agent run via Codegen API
        """
        try:
            # Prepare the prompt
            full_prompt = target
            if planning_statement:
                full_prompt = f"{planning_statement}\n\nUser Request: {target}"
            
            payload = {
                "org_id": self.org_id,
                "prompt": full_prompt,
                "auto_confirm_plans": auto_confirm_plans,
                "max_iterations": max_iterations,
                "metadata": {
                    "project_id": project_id,
                    "source": "codegencd",
                    "created_at": datetime.utcnow().isoformat()
                }
            }
            
            logger.info("Creating agent run", project_id=project_id, prompt_length=len(full_prompt))
            
            response = await self.client.post(
                f"{self.base_url}/agents/runs",
                json=payload
            )
            
            if response.status_code != 201:
                error_data = response.json() if response.content else {}
                raise CodegenAPIError(
                    f"Failed to create agent run: {response.status_code}",
                    status_code=response.status_code,
                    response_data=error_data
                )
            
            result = response.json()
            logger.info("Agent run created successfully", run_id=result.get("id"))
            
            return result
            
        except httpx.RequestError as e:
            logger.error("Network error creating agent run", error=str(e))
            raise CodegenAPIError(f"Network error: {str(e)}")
        except Exception as e:
            logger.error("Unexpected error creating agent run", error=str(e))
            raise CodegenAPIError(f"Unexpected error: {str(e)}")
    
    async def get_agent_run_status(self, run_id: str) -> Dict[str, Any]:
        """
        Get the current status of an agent run
        """
        try:
            response = await self.client.get(f"{self.base_url}/agents/runs/{run_id}")
            
            if response.status_code == 404:
                raise CodegenAPIError(f"Agent run {run_id} not found", status_code=404)
            elif response.status_code != 200:
                error_data = response.json() if response.content else {}
                raise CodegenAPIError(
                    f"Failed to get agent run status: {response.status_code}",
                    status_code=response.status_code,
                    response_data=error_data
                )
            
            return response.json()
            
        except httpx.RequestError as e:
            logger.error("Network error getting agent run status", run_id=run_id, error=str(e))
            raise CodegenAPIError(f"Network error: {str(e)}")
    
    async def continue_agent_run(self, run_id: str, message: str) -> Dict[str, Any]:
        """
        Continue an agent run with additional input
        """
        try:
            payload = {
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            response = await self.client.post(
                f"{self.base_url}/agents/runs/{run_id}/continue",
                json=payload
            )
            
            if response.status_code == 404:
                raise CodegenAPIError(f"Agent run {run_id} not found", status_code=404)
            elif response.status_code != 200:
                error_data = response.json() if response.content else {}
                raise CodegenAPIError(
                    f"Failed to continue agent run: {response.status_code}",
                    status_code=response.status_code,
                    response_data=error_data
                )
            
            result = response.json()
            logger.info("Agent run continued successfully", run_id=run_id)
            
            return result
            
        except httpx.RequestError as e:
            logger.error("Network error continuing agent run", run_id=run_id, error=str(e))
            raise CodegenAPIError(f"Network error: {str(e)}")
    
    async def cancel_agent_run(self, run_id: str) -> Dict[str, Any]:
        """
        Cancel a running agent run
        """
        try:
            response = await self.client.post(f"{self.base_url}/agents/runs/{run_id}/cancel")
            
            if response.status_code == 404:
                raise CodegenAPIError(f"Agent run {run_id} not found", status_code=404)
            elif response.status_code != 200:
                error_data = response.json() if response.content else {}
                raise CodegenAPIError(
                    f"Failed to cancel agent run: {response.status_code}",
                    status_code=response.status_code,
                    response_data=error_data
                )
            
            result = response.json()
            logger.info("Agent run cancelled successfully", run_id=run_id)
            
            return result
            
        except httpx.RequestError as e:
            logger.error("Network error cancelling agent run", run_id=run_id, error=str(e))
            raise CodegenAPIError(f"Network error: {str(e)}")
    
    async def stream_agent_run_updates(self, run_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream real-time updates from an agent run
        """
        try:
            async with self.client.stream(
                "GET",
                f"{self.base_url}/agents/runs/{run_id}/stream",
                headers={"Accept": "text/event-stream"}
            ) as response:
                
                if response.status_code != 200:
                    raise CodegenAPIError(
                        f"Failed to stream agent run updates: {response.status_code}",
                        status_code=response.status_code
                    )
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])  # Remove "data: " prefix
                            yield data
                        except json.JSONDecodeError:
                            logger.warning("Invalid JSON in stream", line=line)
                            continue
                    elif line.startswith("event: "):
                        # Handle different event types if needed
                        continue
                        
        except httpx.RequestError as e:
            logger.error("Network error streaming agent run updates", run_id=run_id, error=str(e))
            raise CodegenAPIError(f"Network error: {str(e)}")


class AgentRunManager:
    """High-level manager for agent runs with database integration"""
    
    def __init__(self):
        self.codegen_client = CodegenClient()
    
    async def start_agent_run(
        self,
        project_id: str,
        target: str,
        planning_statement: Optional[str] = None,
        auto_confirm_plans: bool = False,
        max_iterations: int = 10
    ) -> AgentRun:
        """
        Start a new agent run and create database record
        """
        async with get_db_session() as session:
            try:
                # Create agent run via Codegen API
                async with CodegenClient() as client:
                    api_response = await client.create_agent_run(
                        project_id=project_id,
                        target=target,
                        planning_statement=planning_statement,
                        auto_confirm_plans=auto_confirm_plans,
                        max_iterations=max_iterations
                    )
                
                # Create database record
                agent_run = AgentRun(
                    project_id=project_id,
                    codegen_run_id=api_response["id"],
                    target=target,
                    planning_statement=planning_statement,
                    status=AgentRunStatus.PENDING,
                    run_type=AgentRunType.REGULAR,
                    auto_confirm_plans=auto_confirm_plans,
                    max_iterations=max_iterations,
                    metadata={
                        "api_response": api_response,
                        "created_via": "codegencd"
                    }
                )
                
                session.add(agent_run)
                await session.commit()
                await session.refresh(agent_run)
                
                logger.info("Agent run started", agent_run_id=agent_run.id, codegen_run_id=api_response["id"])
                
                # Start monitoring the run in the background
                asyncio.create_task(self._monitor_agent_run(agent_run.id))
                
                return agent_run
                
            except Exception as e:
                await session.rollback()
                logger.error("Failed to start agent run", error=str(e))
                raise
    
    async def continue_agent_run(self, agent_run_id: str, message: str) -> AgentRun:
        """
        Continue an existing agent run
        """
        async with get_db_session() as session:
            try:
                # Get agent run from database
                agent_run = await session.get(AgentRun, agent_run_id)
                if not agent_run:
                    raise ValueError(f"Agent run {agent_run_id} not found")
                
                if not agent_run.codegen_run_id:
                    raise ValueError(f"Agent run {agent_run_id} has no Codegen run ID")
                
                # Continue via Codegen API
                async with CodegenClient() as client:
                    api_response = await client.continue_agent_run(
                        agent_run.codegen_run_id,
                        message
                    )
                
                # Update database record
                agent_run.status = AgentRunStatus.RUNNING
                agent_run.meta_data = {
                    **(agent_run.meta_data or {}),
                    "last_continued_at": datetime.utcnow().isoformat(),
                    "continue_response": api_response
                }
                
                # Add response record
                response = AgentRunResponse(
                    agent_run_id=agent_run.id,
                    sequence_number=len(agent_run.responses) + 1,
                    response_type="continue",
                    content=message,
                    metadata={"api_response": api_response}
                )
                agent_run.responses.append(response)
                
                await session.commit()
                await session.refresh(agent_run)
                
                logger.info("Agent run continued", agent_run_id=agent_run.id)
                
                return agent_run
                
            except Exception as e:
                await session.rollback()
                logger.error("Failed to continue agent run", agent_run_id=agent_run_id, error=str(e))
                raise
    
    async def cancel_agent_run(self, agent_run_id: str) -> AgentRun:
        """
        Cancel an agent run
        """
        async with get_db_session() as session:
            try:
                # Get agent run from database
                agent_run = await session.get(AgentRun, agent_run_id)
                if not agent_run:
                    raise ValueError(f"Agent run {agent_run_id} not found")
                
                if agent_run.codegen_run_id:
                    # Cancel via Codegen API
                    async with CodegenClient() as client:
                        api_response = await client.cancel_agent_run(agent_run.codegen_run_id)
                    
                    agent_run.meta_data = {
                        **(agent_run.meta_data or {}),
                        "cancelled_at": datetime.utcnow().isoformat(),
                        "cancel_response": api_response
                    }
                
                # Update database record
                agent_run.status = AgentRunStatus.CANCELLED
                
                await session.commit()
                await session.refresh(agent_run)
                
                logger.info("Agent run cancelled", agent_run_id=agent_run.id)
                
                return agent_run
                
            except Exception as e:
                await session.rollback()
                logger.error("Failed to cancel agent run", agent_run_id=agent_run_id, error=str(e))
                raise
    
    async def _monitor_agent_run(self, agent_run_id: str):
        """
        Monitor an agent run for updates (background task)
        """
        try:
            async with get_db_session() as session:
                agent_run = await session.get(AgentRun, agent_run_id)
                if not agent_run or not agent_run.codegen_run_id:
                    return
                
                async with CodegenClient() as client:
                    async for update in client.stream_agent_run_updates(agent_run.codegen_run_id):
                        await self._process_agent_run_update(agent_run_id, update)
                        
                        # Break if run is completed
                        if update.get("status") in ["completed", "failed", "cancelled"]:
                            break
                            
        except Exception as e:
            logger.error("Error monitoring agent run", agent_run_id=agent_run_id, error=str(e))
    
    async def _process_agent_run_update(self, agent_run_id: str, update: Dict[str, Any]):
        """
        Process an update from the Codegen API stream
        """
        async with get_db_session() as session:
            try:
                agent_run = await session.get(AgentRun, agent_run_id)
                if not agent_run:
                    return
                
                # Update status
                if "status" in update:
                    status_map = {
                        "pending": AgentRunStatus.PENDING,
                        "running": AgentRunStatus.RUNNING,
                        "waiting_for_input": AgentRunStatus.WAITING_FOR_INPUT,
                        "completed": AgentRunStatus.COMPLETED,
                        "failed": AgentRunStatus.FAILED,
                        "cancelled": AgentRunStatus.CANCELLED
                    }
                    agent_run.status = status_map.get(update["status"], AgentRunStatus.PENDING)
                
                # Update progress
                if "progress" in update:
                    agent_run.progress_percentage = update["progress"].get("percentage", 0)
                    agent_run.current_step = update["progress"].get("current_step")
                
                # Handle different update types
                update_type = update.get("type", "status")
                
                if update_type == "response":
                    # Add new response
                    response = AgentRunResponse(
                        agent_run_id=agent_run.id,
                        sequence_number=len(agent_run.responses) + 1,
                        response_type=update.get("response_type", "regular"),
                        content=update.get("content", ""),
                        is_final=update.get("is_final", False),
                        requires_user_input=update.get("requires_user_input", False),
                        plan_data=update.get("plan_data", {}),
                        pr_data=update.get("pr_data", {}),
                        metadata=update
                    )
                    agent_run.responses.append(response)
                    
                    # Update run type based on response
                    if update.get("response_type") == "plan":
                        agent_run.run_type = AgentRunType.PLAN
                    elif update.get("response_type") == "pr_created":
                        agent_run.run_type = AgentRunType.PR_CREATION
                        agent_run.pr_url = update.get("pr_data", {}).get("url")
                        agent_run.pr_number = update.get("pr_data", {}).get("number")
                
                elif update_type == "step":
                    # Add step information
                    step = AgentRunStep(
                        agent_run_id=agent_run.id,
                        step_number=len(agent_run.steps) + 1,
                        step_name=update.get("step_name", "Unknown"),
                        step_description=update.get("description"),
                        step_data=update,
                        is_completed=update.get("completed", False),
                        is_successful=update.get("successful", True)
                    )
                    agent_run.steps.append(step)
                
                # Update metadata
                agent_run.meta_data = {
                    **(agent_run.meta_data or {}),
                    "last_update": datetime.utcnow().isoformat(),
                    "latest_update": update
                }
                
                await session.commit()
                
                # TODO: Send WebSocket update to frontend
                # await self._send_websocket_update(agent_run_id, update)
                
            except Exception as e:
                await session.rollback()
                logger.error("Failed to process agent run update", agent_run_id=agent_run_id, error=str(e))


# Global instance
agent_run_manager = AgentRunManager()
