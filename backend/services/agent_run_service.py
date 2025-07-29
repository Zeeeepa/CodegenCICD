"""
Agent run management service
"""
import asyncio
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
import structlog

from backend.database import get_db_session
from backend.models.project import Project, ProjectSettings
from backend.models.agent_run import AgentRun, AgentRunStatus, AgentRunType, AgentRunStep, AgentRunResponse
from backend.api import CodegenClient, ConfigPresets

logger = structlog.get_logger(__name__)


class AgentRunService:
    """Service for managing agent runs"""
    
    def __init__(self):
        self.codegen_client = CodegenClient(ConfigPresets.development())
    
    async def create_agent_run(self, project_id: int, target: str, 
                             auto_confirm_plans: bool = False) -> AgentRun:
        """Create a new agent run"""
        async with get_db_session() as session:
            try:
                # Get project and settings
                project = session.query(Project).filter(Project.id == project_id).first()
                if not project:
                    raise ValueError(f"Project {project_id} not found")
                
                settings = session.query(ProjectSettings).filter(
                    ProjectSettings.project_id == project_id
                ).first()
                
                # Prepare the prompt
                planning_statement = ""
                if settings and settings.planning_statement:
                    planning_statement = settings.planning_statement
                
                # Add repository rules if available
                repository_context = f"<Project='{project.name}'>"
                if settings and settings.repository_rules:
                    repository_context += f"\n\nRepository Rules:\n{settings.repository_rules}"
                
                full_prompt = f"{planning_statement}\n\n{repository_context}\n\nUser Request: {target}"
                
                # Create agent run via Codegen API
                api_response = self.codegen_client.create_agent_run(
                    org_id=int(self.codegen_client.config.org_id),
                    prompt=full_prompt,
                    metadata={
                        "project_id": project_id,
                        "project_name": project.name,
                        "source": "codegencd_dashboard"
                    }
                )
                
                # Create database record
                agent_run = AgentRun(
                    project_id=project_id,
                    codegen_run_id=str(api_response.id),
                    target=target,
                    planning_statement=planning_statement,
                    status=AgentRunStatus.PENDING,
                    run_type=AgentRunType.REGULAR,
                    auto_confirm_plans=auto_confirm_plans or project.auto_confirm_plans,
                    metadata={
                        "api_response": {
                            "id": api_response.id,
                            "status": api_response.status,
                            "web_url": api_response.web_url
                        }
                    }
                )
                
                session.add(agent_run)
                await session.commit()
                await session.refresh(agent_run)
                
                # Update project statistics
                project.total_runs += 1
                await session.commit()
                
                logger.info("Agent run created", 
                          agent_run_id=agent_run.id, 
                          codegen_run_id=api_response.id,
                          project_id=project_id)
                
                # Start monitoring the run in the background
                asyncio.create_task(self._monitor_agent_run(agent_run.id))
                
                return agent_run
                
            except Exception as e:
                await session.rollback()
                logger.error("Failed to create agent run", 
                           project_id=project_id, error=str(e))
                raise
    
    async def get_agent_run(self, agent_run_id: int) -> Optional[AgentRun]:
        """Get agent run by ID"""
        async with get_db_session() as session:
            try:
                agent_run = session.query(AgentRun).filter(
                    AgentRun.id == agent_run_id
                ).first()
                
                return agent_run
                
            except Exception as e:
                logger.error("Error fetching agent run", 
                           agent_run_id=agent_run_id, error=str(e))
                raise
    
    async def continue_agent_run(self, agent_run_id: int, message: str) -> Optional[AgentRun]:
        """Continue an agent run with user input"""
        async with get_db_session() as session:
            try:
                agent_run = session.query(AgentRun).filter(
                    AgentRun.id == agent_run_id
                ).first()
                
                if not agent_run:
                    return None
                
                if not agent_run.codegen_run_id:
                    raise ValueError(f"Agent run {agent_run_id} has no Codegen run ID")
                
                # Continue via Codegen API (using resume endpoint)
                # Note: This would need to be implemented in the Codegen client
                # For now, we'll simulate the continuation
                
                # Add response record
                response = AgentRunResponse(
                    agent_run_id=agent_run.id,
                    sequence_number=len(agent_run.responses) + 1,
                    response_type="continue",
                    content=message,
                    metadata={"user_input": True}
                )
                agent_run.responses.append(response)
                
                # Update status
                agent_run.status = AgentRunStatus.RUNNING
                
                await session.commit()
                await session.refresh(agent_run)
                
                logger.info("Agent run continued", agent_run_id=agent_run.id)
                
                return agent_run
                
            except Exception as e:
                await session.rollback()
                logger.error("Failed to continue agent run", 
                           agent_run_id=agent_run_id, error=str(e))
                raise
    
    async def cancel_agent_run(self, agent_run_id: int) -> bool:
        """Cancel an agent run"""
        async with get_db_session() as session:
            try:
                agent_run = session.query(AgentRun).filter(
                    AgentRun.id == agent_run_id
                ).first()
                
                if not agent_run:
                    return False
                
                # Update status
                agent_run.status = AgentRunStatus.CANCELLED
                
                await session.commit()
                
                logger.info("Agent run cancelled", agent_run_id=agent_run.id)
                
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error("Failed to cancel agent run", 
                           agent_run_id=agent_run_id, error=str(e))
                raise
    
    async def get_agent_run_responses(self, agent_run_id: int) -> List[AgentRunResponse]:
        """Get all responses for an agent run"""
        async with get_db_session() as session:
            try:
                agent_run = session.query(AgentRun).filter(
                    AgentRun.id == agent_run_id
                ).first()
                
                if not agent_run:
                    return []
                
                return agent_run.responses
                
            except Exception as e:
                logger.error("Error fetching agent run responses", 
                           agent_run_id=agent_run_id, error=str(e))
                raise
    
    async def get_agent_run_steps(self, agent_run_id: int) -> List[AgentRunStep]:
        """Get all steps for an agent run"""
        async with get_db_session() as session:
            try:
                agent_run = session.query(AgentRun).filter(
                    AgentRun.id == agent_run_id
                ).first()
                
                if not agent_run:
                    return []
                
                return agent_run.steps
                
            except Exception as e:
                logger.error("Error fetching agent run steps", 
                           agent_run_id=agent_run_id, error=str(e))
                raise
    
    async def _monitor_agent_run(self, agent_run_id: int):
        """Monitor an agent run for updates (background task)"""
        try:
            async with get_db_session() as session:
                agent_run = session.query(AgentRun).filter(
                    AgentRun.id == agent_run_id
                ).first()
                
                if not agent_run or not agent_run.codegen_run_id:
                    return
                
                # Poll for updates from Codegen API
                max_polls = 360  # 30 minutes with 5-second intervals
                poll_count = 0
                
                while poll_count < max_polls:
                    try:
                        # Get current status from Codegen API
                        api_run = self.codegen_client.get_agent_run(
                            int(self.codegen_client.config.org_id),
                            int(agent_run.codegen_run_id)
                        )
                        
                        # Update local status
                        await self._update_agent_run_from_api(agent_run_id, api_run)
                        
                        # Check if completed
                        if api_run.status in ["completed", "failed", "cancelled"]:
                            break
                        
                        # Wait before next poll
                        await asyncio.sleep(5)
                        poll_count += 1
                        
                    except Exception as poll_error:
                        logger.warning("Error polling agent run status", 
                                     agent_run_id=agent_run_id, 
                                     error=str(poll_error))
                        await asyncio.sleep(10)  # Wait longer on error
                        poll_count += 2
                
                logger.info("Agent run monitoring completed", agent_run_id=agent_run_id)
                
        except Exception as e:
            logger.error("Error monitoring agent run", 
                       agent_run_id=agent_run_id, error=str(e))
    
    async def _update_agent_run_from_api(self, agent_run_id: int, api_run):
        """Update agent run from Codegen API response"""
        async with get_db_session() as session:
            try:
                agent_run = session.query(AgentRun).filter(
                    AgentRun.id == agent_run_id
                ).first()
                
                if not agent_run:
                    return
                
                # Update status
                status_map = {
                    "pending": AgentRunStatus.PENDING,
                    "running": AgentRunStatus.RUNNING,
                    "waiting_for_input": AgentRunStatus.WAITING_FOR_INPUT,
                    "completed": AgentRunStatus.COMPLETED,
                    "failed": AgentRunStatus.FAILED,
                    "cancelled": AgentRunStatus.CANCELLED
                }
                
                if api_run.status in status_map:
                    agent_run.status = status_map[api_run.status]
                
                # Update result if completed
                if api_run.result:
                    agent_run.final_response = api_run.result
                
                # Update PR information if available
                if api_run.github_pull_requests:
                    pr = api_run.github_pull_requests[0]  # Take first PR
                    agent_run.pr_url = pr.url
                    agent_run.pr_number = pr.id
                    agent_run.run_type = AgentRunType.PR_CREATION
                
                # Update metadata
                agent_run.metadata = {
                    **(agent_run.metadata or {}),
                    "last_api_update": api_run.metadata or {},
                    "web_url": api_run.web_url
                }
                
                await session.commit()
                
                # TODO: Send WebSocket update to frontend
                
            except Exception as e:
                await session.rollback()
                logger.error("Failed to update agent run from API", 
                           agent_run_id=agent_run_id, error=str(e))


# Global instance
agent_run_service = AgentRunService()

