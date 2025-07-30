"""
Agent Run Manager - Central workflow orchestrator for CICD pipeline
"""
import asyncio
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from backend.database import get_db_session
from backend.models.agent_run import AgentRun, AgentRunStatus, AgentRunType
from backend.models.project import Project
from backend.services.codegen_api_client import CodegenAPIClient, AgentRunResponse, AgentRunResponseType
from backend.services.database_service import DatabaseService

logger = structlog.get_logger(__name__)


class AgentRunManagerError(Exception):
    """Custom exception for Agent Run Manager errors"""
    pass


class AgentRunManager:
    """
    Central workflow orchestrator for agent runs with complete CICD pipeline integration.
    
    This manager coordinates the entire lifecycle of agent runs from creation through
    completion, including plan confirmation, PR validation, and auto-merge decisions.
    """
    
    def __init__(self):
        self.db_service = DatabaseService()
        self._active_runs: Dict[str, asyncio.Task] = {}
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}
    
    async def create_agent_run(
        self,
        project_id: int,
        user_prompt: str,
        planning_statement: Optional[str] = None,
        auto_confirm_plans: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentRun:
        """
        Create a new agent run with complete workflow orchestration.
        
        Args:
            project_id: Database ID of the project
            user_prompt: User's requirements/request
            planning_statement: Optional planning statement for the project
            auto_confirm_plans: Whether to automatically confirm plans
            metadata: Additional metadata for the run
            
        Returns:
            AgentRun: Created agent run with database record
            
        Raises:
            AgentRunManagerError: If creation fails
        """
        async with get_db_session() as session:
            try:
                # Get project details
                project = await session.get(Project, project_id)
                if not project:
                    raise AgentRunManagerError(f"Project {project_id} not found")
                
                # Use project's planning statement if not provided
                effective_planning_statement = planning_statement or project.planning_statement
                
                # Create agent run via Codegen API
                async with CodegenAPIClient() as codegen_client:
                    logger.info("Creating agent run via Codegen API", 
                              project=project.full_name, 
                              prompt_length=len(user_prompt))
                    
                    api_response = await codegen_client.create_agent_run(
                        project_context=project.full_name,
                        user_prompt=user_prompt,
                        planning_statement=effective_planning_statement
                    )
                
                # Create database record
                agent_run = AgentRun(
                    project_id=project_id,
                    codegen_run_id=api_response.run_id,
                    user_prompt=user_prompt,
                    planning_statement=effective_planning_statement,
                    status=AgentRunStatus.PENDING,
                    run_type=AgentRunType.REGULAR,
                    auto_confirm_plans=auto_confirm_plans or project.auto_confirm_plans,
                    metadata={
                        **(metadata or {}),
                        "api_response": {
                            "run_id": api_response.run_id,
                            "status": api_response.status,
                            "response_type": api_response.response_type.value,
                            "created_at": api_response.created_at.isoformat()
                        },
                        "project_context": {
                            "name": project.name,
                            "full_name": project.full_name,
                            "github_url": project.github_url,
                            "default_branch": project.default_branch
                        },
                        "created_via": "agent_run_manager"
                    }
                )
                
                session.add(agent_run)
                await session.commit()
                await session.refresh(agent_run)
                
                logger.info("Agent run created successfully", 
                          agent_run_id=agent_run.id, 
                          codegen_run_id=api_response.run_id)
                
                # Start monitoring in background
                monitoring_task = asyncio.create_task(
                    self._monitor_agent_run(agent_run.id)
                )
                self._monitoring_tasks[agent_run.id] = monitoring_task
                
                return agent_run
                
            except Exception as e:
                await session.rollback()
                logger.error("Failed to create agent run", 
                           project_id=project_id, 
                           error=str(e))
                raise AgentRunManagerError(f"Failed to create agent run: {e}")
    
    async def get_agent_run(self, agent_run_id: int) -> Optional[AgentRun]:
        """Get agent run by ID with all related data."""
        async with get_db_session() as session:
            result = await session.execute(
                select(AgentRun)
                .options(selectinload(AgentRun.project))
                .where(AgentRun.id == agent_run_id)
            )
            return result.scalar_one_or_none()
    
    async def get_agent_runs_for_project(
        self, 
        project_id: int, 
        limit: int = 50,
        status_filter: Optional[AgentRunStatus] = None
    ) -> List[AgentRun]:
        """Get agent runs for a specific project."""
        async with get_db_session() as session:
            query = select(AgentRun).where(AgentRun.project_id == project_id)
            
            if status_filter:
                query = query.where(AgentRun.status == status_filter)
            
            query = query.order_by(AgentRun.created_at.desc()).limit(limit)
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def continue_agent_run(
        self, 
        agent_run_id: int, 
        continuation_prompt: str,
        action_type: str = "continue"
    ) -> AgentRun:
        """
        Continue an existing agent run with additional input.
        
        Args:
            agent_run_id: Database ID of the agent run
            continuation_prompt: Additional prompt/instructions
            action_type: Type of action (continue, confirm_plan, modify_plan)
            
        Returns:
            Updated agent run
        """
        async with get_db_session() as session:
            try:
                agent_run = await session.get(AgentRun, agent_run_id)
                if not agent_run:
                    raise AgentRunManagerError(f"Agent run {agent_run_id} not found")
                
                if not agent_run.codegen_run_id:
                    raise AgentRunManagerError(f"Agent run {agent_run_id} has no Codegen run ID")
                
                # Continue via Codegen API
                async with CodegenAPIClient() as codegen_client:
                    if action_type == "confirm_plan":
                        api_response = await codegen_client.confirm_plan(
                            agent_run.codegen_run_id, 
                            continuation_prompt
                        )
                    else:
                        api_response = await codegen_client.continue_agent_run(
                            agent_run.codegen_run_id, 
                            continuation_prompt
                        )
                
                # Update database record
                agent_run.status = AgentRunStatus.RUNNING
                agent_run.metadata = {
                    **(agent_run.metadata or {}),
                    "last_continued_at": datetime.utcnow().isoformat(),
                    "last_action": {
                        "type": action_type,
                        "prompt": continuation_prompt,
                        "timestamp": datetime.utcnow().isoformat(),
                        "api_response": {
                            "run_id": api_response.run_id,
                            "status": api_response.status,
                            "response_type": api_response.response_type.value
                        }
                    }
                }
                
                await session.commit()
                await session.refresh(agent_run)
                
                logger.info("Agent run continued", 
                          agent_run_id=agent_run.id, 
                          action_type=action_type)
                
                return agent_run
                
            except Exception as e:
                await session.rollback()
                logger.error("Failed to continue agent run", 
                           agent_run_id=agent_run_id, 
                           error=str(e))
                raise AgentRunManagerError(f"Failed to continue agent run: {e}")
    
    async def cancel_agent_run(self, agent_run_id: int) -> AgentRun:
        """Cancel an active agent run."""
        async with get_db_session() as session:
            try:
                agent_run = await session.get(AgentRun, agent_run_id)
                if not agent_run:
                    raise AgentRunManagerError(f"Agent run {agent_run_id} not found")
                
                # Cancel monitoring task
                if agent_run_id in self._monitoring_tasks:
                    self._monitoring_tasks[agent_run_id].cancel()
                    del self._monitoring_tasks[agent_run_id]
                
                # Cancel via Codegen API if we have a run ID
                if agent_run.codegen_run_id:
                    async with CodegenAPIClient() as codegen_client:
                        await codegen_client.cancel_agent_run(agent_run.codegen_run_id)
                
                # Update database record
                agent_run.status = AgentRunStatus.CANCELLED
                agent_run.metadata = {
                    **(agent_run.metadata or {}),
                    "cancelled_at": datetime.utcnow().isoformat(),
                    "cancelled_by": "agent_run_manager"
                }
                
                await session.commit()
                await session.refresh(agent_run)
                
                logger.info("Agent run cancelled", agent_run_id=agent_run.id)
                
                return agent_run
                
            except Exception as e:
                await session.rollback()
                logger.error("Failed to cancel agent run", 
                           agent_run_id=agent_run_id, 
                           error=str(e))
                raise AgentRunManagerError(f"Failed to cancel agent run: {e}")
    
    async def _monitor_agent_run(self, agent_run_id: int):
        """
        Monitor an agent run for status updates and handle workflow transitions.
        
        This is the core orchestration logic that handles:
        - Status polling and updates
        - Plan detection and confirmation workflows
        - PR creation detection and validation triggers
        - Error handling and recovery
        """
        try:
            logger.info("Starting agent run monitoring", agent_run_id=agent_run_id)
            
            async with get_db_session() as session:
                agent_run = await session.get(AgentRun, agent_run_id)
                if not agent_run or not agent_run.codegen_run_id:
                    logger.warning("Cannot monitor agent run - missing data", 
                                 agent_run_id=agent_run_id)
                    return
                
                async with CodegenAPIClient() as codegen_client:
                    # Poll for updates every 5 seconds
                    while True:
                        try:
                            # Get current status
                            status_response = await codegen_client.get_agent_run_status(
                                agent_run.codegen_run_id
                            )
                            
                            # Update database with latest status
                            await self._update_agent_run_status(
                                agent_run_id, 
                                status_response
                            )
                            
                            # Handle different response types
                            if status_response.response_type == AgentRunResponseType.PLAN:
                                await self._handle_plan_response(agent_run_id, status_response)
                            elif status_response.response_type == AgentRunResponseType.PR:
                                await self._handle_pr_response(agent_run_id, status_response)
                            elif status_response.response_type == AgentRunResponseType.ERROR:
                                await self._handle_error_response(agent_run_id, status_response)
                            
                            # Check if run is complete
                            if status_response.status in ["completed", "failed", "cancelled"]:
                                logger.info("Agent run monitoring complete", 
                                          agent_run_id=agent_run_id, 
                                          final_status=status_response.status)
                                break
                            
                            # Wait before next poll
                            await asyncio.sleep(5)
                            
                        except Exception as e:
                            logger.error("Error in monitoring loop", 
                                       agent_run_id=agent_run_id, 
                                       error=str(e))
                            await asyncio.sleep(10)  # Longer wait on error
                            
        except Exception as e:
            logger.error("Fatal error in agent run monitoring", 
                       agent_run_id=agent_run_id, 
                       error=str(e))
        finally:
            # Clean up monitoring task reference
            if agent_run_id in self._monitoring_tasks:
                del self._monitoring_tasks[agent_run_id]
    
    async def _update_agent_run_status(
        self, 
        agent_run_id: int, 
        status_response: AgentRunResponse
    ):
        """Update agent run status in database."""
        async with get_db_session() as session:
            try:
                # Map API status to our enum
                status_map = {
                    "pending": AgentRunStatus.PENDING,
                    "running": AgentRunStatus.RUNNING,
                    "waiting_for_input": AgentRunStatus.WAITING_FOR_INPUT,
                    "completed": AgentRunStatus.COMPLETED,
                    "failed": AgentRunStatus.FAILED,
                    "cancelled": AgentRunStatus.CANCELLED
                }
                
                new_status = status_map.get(status_response.status, AgentRunStatus.PENDING)
                
                await session.execute(
                    update(AgentRun)
                    .where(AgentRun.id == agent_run_id)
                    .values(
                        status=new_status,
                        metadata=AgentRun.metadata.op('||')({
                            "last_status_update": datetime.utcnow().isoformat(),
                            "latest_response": {
                                "status": status_response.status,
                                "response_type": status_response.response_type.value,
                                "content": status_response.content[:1000],  # Truncate for storage
                                "updated_at": datetime.utcnow().isoformat()
                            }
                        })
                    )
                )
                
                await session.commit()
                
            except Exception as e:
                await session.rollback()
                logger.error("Failed to update agent run status", 
                           agent_run_id=agent_run_id, 
                           error=str(e))
    
    async def _handle_plan_response(
        self, 
        agent_run_id: int, 
        status_response: AgentRunResponse
    ):
        """Handle plan response - trigger plan confirmation workflow."""
        logger.info("Plan detected for agent run", agent_run_id=agent_run_id)
        
        async with get_db_session() as session:
            agent_run = await session.get(AgentRun, agent_run_id)
            if not agent_run:
                return
            
            # Update run type to indicate plan phase
            agent_run.run_type = AgentRunType.PLAN
            agent_run.metadata = {
                **(agent_run.metadata or {}),
                "plan_detected_at": datetime.utcnow().isoformat(),
                "plan_content": status_response.content,
                "requires_confirmation": not agent_run.auto_confirm_plans
            }
            
            await session.commit()
            
            # Auto-confirm if enabled
            if agent_run.auto_confirm_plans:
                logger.info("Auto-confirming plan", agent_run_id=agent_run_id)
                await self.continue_agent_run(
                    agent_run_id, 
                    "Proceed with the plan", 
                    "confirm_plan"
                )
            else:
                # TODO: Trigger frontend notification for manual confirmation
                logger.info("Plan requires manual confirmation", agent_run_id=agent_run_id)
    
    async def _handle_pr_response(
        self, 
        agent_run_id: int, 
        status_response: AgentRunResponse
    ):
        """Handle PR creation response - trigger validation pipeline."""
        logger.info("PR creation detected for agent run", agent_run_id=agent_run_id)
        
        async with get_db_session() as session:
            agent_run = await session.get(AgentRun, agent_run_id)
            if not agent_run:
                return
            
            # Extract PR information from response
            pr_info = self._extract_pr_info(status_response.content)
            
            # Update run type and metadata
            agent_run.run_type = AgentRunType.PR_CREATION
            agent_run.metadata = {
                **(agent_run.metadata or {}),
                "pr_created_at": datetime.utcnow().isoformat(),
                "pr_info": pr_info,
                "validation_required": True
            }
            
            await session.commit()
            
            # TODO: Trigger validation pipeline
            logger.info("PR validation pipeline should be triggered", 
                      agent_run_id=agent_run_id, 
                      pr_info=pr_info)
    
    async def _handle_error_response(
        self, 
        agent_run_id: int, 
        status_response: AgentRunResponse
    ):
        """Handle error response - log and update status."""
        logger.error("Error detected in agent run", 
                   agent_run_id=agent_run_id, 
                   error_content=status_response.content)
        
        async with get_db_session() as session:
            await session.execute(
                update(AgentRun)
                .where(AgentRun.id == agent_run_id)
                .values(
                    status=AgentRunStatus.FAILED,
                    metadata=AgentRun.metadata.op('||')({
                        "error_detected_at": datetime.utcnow().isoformat(),
                        "error_content": status_response.content,
                        "error_metadata": status_response.metadata
                    })
                )
            )
            await session.commit()
    
    def _extract_pr_info(self, content: str) -> Dict[str, Any]:
        """Extract PR information from response content."""
        # Simple extraction - in production this would be more sophisticated
        pr_info = {
            "extracted_at": datetime.utcnow().isoformat(),
            "content_preview": content[:500]
        }
        
        # Look for common PR patterns
        if "pull request" in content.lower():
            pr_info["type"] = "pull_request"
        if "github.com" in content:
            # Extract GitHub URL if present
            import re
            github_urls = re.findall(r'https://github\.com/[^\s]+', content)
            if github_urls:
                pr_info["github_url"] = github_urls[0]
        
        return pr_info
    
    async def get_active_runs_count(self) -> int:
        """Get count of currently active agent runs."""
        async with get_db_session() as session:
            result = await session.execute(
                select(AgentRun)
                .where(AgentRun.status.in_([
                    AgentRunStatus.PENDING,
                    AgentRunStatus.RUNNING,
                    AgentRunStatus.WAITING_FOR_INPUT
                ]))
            )
            return len(result.scalars().all())
    
    async def cleanup_old_runs(self, days_old: int = 30):
        """Clean up old completed/failed runs."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        async with get_db_session() as session:
            await session.execute(
                update(AgentRun)
                .where(
                    AgentRun.created_at < cutoff_date,
                    AgentRun.status.in_([
                        AgentRunStatus.COMPLETED,
                        AgentRunStatus.FAILED,
                        AgentRunStatus.CANCELLED
                    ])
                )
                .values(metadata=AgentRun.metadata.op('||')({
                    "archived_at": datetime.utcnow().isoformat()
                }))
            )
            await session.commit()
            
            logger.info("Cleaned up old agent runs", cutoff_date=cutoff_date.isoformat())


# Global instance
agent_run_manager = AgentRunManager()

