"""
Agent service for managing Codegen agent runs
"""
import asyncio
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
import structlog

from backend.models.agent_run import AgentRun, AgentRunLog, AgentRunStatus, AgentRunType, LogLevel
from backend.models.project import Project
from backend.integrations.codegen_client import CodegenClient, CodegenTask
from backend.websocket.connection_manager import ConnectionManager

logger = structlog.get_logger(__name__)


class AgentService:
    """Service for managing agent runs and Codegen API interactions"""
    
    def __init__(self, db: AsyncSession, connection_manager: ConnectionManager):
        self.db = db
        self.connection_manager = connection_manager
        self.codegen_client = CodegenClient()
    
    async def create_agent_run(self, project_id: int, target_text: str,
                              planning_statement: Optional[str] = None,
                              parent_run_id: Optional[int] = None) -> AgentRun:
        """Create a new agent run"""
        try:
            # Get project information
            project = await self.db.get(Project, project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Create agent run record
            agent_run = AgentRun(
                project_id=project_id,
                codegen_org_id=self.codegen_client.org_id,
                target_text=target_text,
                planning_statement=planning_statement or project.planning_statement,
                parent_run_id=parent_run_id,
                run_type=AgentRunType.CONTINUATION if parent_run_id else AgentRunType.REGULAR,
                auto_merge_enabled=project.auto_merge_enabled
            )
            
            self.db.add(agent_run)
            await self.db.commit()
            await self.db.refresh(agent_run)
            
            # Log creation
            await self._add_log(agent_run.id, LogLevel.INFO, "Agent run created", "agent_service")
            
            # Start the agent run asynchronously
            asyncio.create_task(self._execute_agent_run(agent_run))
            
            # Notify via WebSocket
            await self._notify_agent_run_update(agent_run)
            
            logger.info("Agent run created", agent_run_id=agent_run.id, project_id=project_id)
            return agent_run
            
        except Exception as e:
            logger.error("Failed to create agent run", project_id=project_id, error=str(e))
            await self.db.rollback()
            raise
    
    async def _execute_agent_run(self, agent_run: AgentRun):
        """Execute agent run with Codegen API"""
        try:
            # Update status to running
            agent_run.status = AgentRunStatus.RUNNING
            agent_run.update_progress(10, "Starting Codegen agent")
            await self.db.commit()
            await self._notify_agent_run_update(agent_run)
            
            # Get project for context
            project = await self.db.get(Project, agent_run.project_id)
            
            # Prepare context
            context = {
                "project_name": project.name,
                "repository": project.full_name,
                "default_branch": project.default_branch,
                "repository_rules": project.repository_rules,
                "auto_merge_enabled": agent_run.auto_merge_enabled
            }
            
            # Create or continue agent run
            if agent_run.parent_run_id:
                # This is a continuation
                parent_run = await self.db.get(AgentRun, agent_run.parent_run_id)
                if parent_run and parent_run.codegen_run_id:
                    task = await self.codegen_client.continue_agent_run(
                        str(parent_run.codegen_run_id),
                        agent_run.target_text,
                        context
                    )
                else:
                    raise ValueError("Parent run not found or has no Codegen run ID")
            else:
                # This is a new run
                full_prompt = agent_run.target_text
                if agent_run.planning_statement:
                    full_prompt = f"{agent_run.planning_statement}\\n\\n{agent_run.target_text}"
                
                task = await self.codegen_client.create_agent_run(
                    full_prompt,
                    context,
                    project.full_name,
                    project.default_branch,
                    agent_run.planning_statement
                )
            
            # Update with Codegen task ID
            agent_run.codegen_run_id = int(task.id) if task.id else None
            agent_run.update_progress(30, "Agent run started")
            await self.db.commit()
            
            await self._add_log(agent_run.id, LogLevel.INFO, 
                              f"Codegen agent run started with ID: {task.id}", "codegen_api")
            
            # Monitor task progress
            await self._monitor_agent_task(agent_run, task)
            
        except Exception as e:
            logger.error("Agent run execution failed", agent_run_id=agent_run.id, error=str(e))
            agent_run.mark_failed(str(e))
            await self.db.commit()
            await self._add_log(agent_run.id, LogLevel.ERROR, f"Execution failed: {str(e)}", "agent_service")
            await self._notify_agent_run_update(agent_run)
    
    async def _monitor_agent_task(self, agent_run: AgentRun, task: CodegenTask):
        """Monitor Codegen task progress"""
        try:
            # Poll for updates
            while not task.is_completed and not task.is_failed:
                await asyncio.sleep(10)  # Poll every 10 seconds
                await task.refresh()
                
                # Update progress based on task status
                if task.status == "running":
                    agent_run.update_progress(50, "Agent is working")
                elif task.status == "pending":
                    agent_run.update_progress(20, "Agent run queued")
                
                await self.db.commit()
                await self._notify_agent_run_update(agent_run)
            
            # Handle completion
            if task.is_completed:
                await self._handle_agent_completion(agent_run, task)
            elif task.is_failed:
                await self._handle_agent_failure(agent_run, task)
                
        except Exception as e:
            logger.error("Error monitoring agent task", agent_run_id=agent_run.id, error=str(e))
            agent_run.mark_failed(f"Monitoring error: {str(e)}")
            await self.db.commit()
            await self._notify_agent_run_update(agent_run)
    
    async def _handle_agent_completion(self, agent_run: AgentRun, task: CodegenTask):
        """Handle successful agent completion"""
        try:
            agent_run.mark_completed(task.result)
            agent_run.metadata = task.metadata
            
            # Check if a PR was created
            if task.metadata and "pr_url" in task.metadata:
                agent_run.pr_url = task.metadata["pr_url"]
                agent_run.pr_number = task.metadata.get("pr_number")
                agent_run.pr_branch = task.metadata.get("pr_branch")
                agent_run.pr_title = task.metadata.get("pr_title")
                agent_run.run_type = AgentRunType.PR
                
                await self._add_log(agent_run.id, LogLevel.INFO, 
                                  f"PR created: {agent_run.pr_url}", "codegen_api")
                
                # Trigger validation if enabled
                if agent_run.project.validation_enabled:
                    from backend.services.validation_service import ValidationService
                    validation_service = ValidationService(self.db, self.connection_manager)
                    await validation_service.start_validation(agent_run)
            
            await self.db.commit()
            await self._add_log(agent_run.id, LogLevel.INFO, "Agent run completed successfully", "agent_service")
            await self._notify_agent_run_update(agent_run)
            
            logger.info("Agent run completed", agent_run_id=agent_run.id)
            
        except Exception as e:
            logger.error("Error handling agent completion", agent_run_id=agent_run.id, error=str(e))
            agent_run.mark_failed(f"Completion handling error: {str(e)}")
            await self.db.commit()
    
    async def _handle_agent_failure(self, agent_run: AgentRun, task: CodegenTask):
        """Handle agent failure"""
        try:
            error_message = task.error or "Agent run failed"
            agent_run.mark_failed(error_message)
            agent_run.metadata = task.metadata
            
            await self.db.commit()
            await self._add_log(agent_run.id, LogLevel.ERROR, f"Agent run failed: {error_message}", "codegen_api")
            await self._notify_agent_run_update(agent_run)
            
            logger.error("Agent run failed", agent_run_id=agent_run.id, error=error_message)
            
        except Exception as e:
            logger.error("Error handling agent failure", agent_run_id=agent_run.id, error=str(e))
    
    async def continue_agent_run(self, agent_run_id: int, target_text: str) -> AgentRun:
        """Continue an existing agent run"""
        try:
            # Get the original agent run
            original_run = await self.db.get(AgentRun, agent_run_id)
            if not original_run:
                raise ValueError(f"Agent run {agent_run_id} not found")
            
            if not original_run.is_completed:
                raise ValueError("Cannot continue a run that is not completed")
            
            # Create continuation run
            return await self.create_agent_run(
                original_run.project_id,
                target_text,
                original_run.planning_statement,
                agent_run_id
            )
            
        except Exception as e:
            logger.error("Failed to continue agent run", agent_run_id=agent_run_id, error=str(e))
            raise
    
    async def cancel_agent_run(self, agent_run_id: int) -> bool:
        """Cancel an agent run"""
        try:
            agent_run = await self.db.get(AgentRun, agent_run_id)
            if not agent_run:
                raise ValueError(f"Agent run {agent_run_id} not found")
            
            if agent_run.is_completed:
                return False  # Already completed
            
            # Cancel with Codegen API if possible
            if agent_run.codegen_run_id:
                await self.codegen_client.cancel_agent_run(str(agent_run.codegen_run_id))
            
            # Update status
            agent_run.status = AgentRunStatus.CANCELLED
            agent_run.completed_at = agent_run.updated_at
            await self.db.commit()
            
            await self._add_log(agent_run_id, LogLevel.INFO, "Agent run cancelled", "agent_service")
            await self._notify_agent_run_update(agent_run)
            
            logger.info("Agent run cancelled", agent_run_id=agent_run_id)
            return True
            
        except Exception as e:
            logger.error("Failed to cancel agent run", agent_run_id=agent_run_id, error=str(e))
            return False
    
    async def get_agent_run(self, agent_run_id: int) -> Optional[AgentRun]:
        """Get agent run by ID"""
        return await self.db.get(AgentRun, agent_run_id)
    
    async def list_agent_runs(self, project_id: Optional[int] = None, 
                             status: Optional[AgentRunStatus] = None,
                             limit: int = 50, offset: int = 0) -> List[AgentRun]:
        """List agent runs with filters"""
        try:
            query = select(AgentRun)
            
            conditions = []
            if project_id:
                conditions.append(AgentRun.project_id == project_id)
            if status:
                conditions.append(AgentRun.status == status)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            query = query.order_by(AgentRun.created_at.desc()).limit(limit).offset(offset)
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error("Failed to list agent runs", error=str(e))
            raise
    
    async def get_agent_run_logs(self, agent_run_id: int) -> List[AgentRunLog]:
        """Get logs for an agent run"""
        try:
            query = select(AgentRunLog).where(
                AgentRunLog.agent_run_id == agent_run_id
            ).order_by(AgentRunLog.created_at.asc())
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error("Failed to get agent run logs", agent_run_id=agent_run_id, error=str(e))
            raise
    
    async def _add_log(self, agent_run_id: int, level: LogLevel, message: str, 
                      source: str = None, metadata: Dict[str, Any] = None, 
                      step_name: str = None):
        """Add a log entry for an agent run"""
        try:
            log_entry = AgentRunLog.create_log(
                agent_run_id, level, message, source, metadata, step_name
            )
            self.db.add(log_entry)
            await self.db.commit()
            
            # Notify via WebSocket
            await self.connection_manager.broadcast_to_project(
                agent_run_id,  # Using agent_run_id as project identifier for now
                {
                    "type": "agent_run_log",
                    "agent_run_id": agent_run_id,
                    "log": log_entry.to_dict()
                }
            )
            
        except Exception as e:
            logger.error("Failed to add log entry", agent_run_id=agent_run_id, error=str(e))
    
    async def _notify_agent_run_update(self, agent_run: AgentRun):
        """Notify clients of agent run updates via WebSocket"""
        try:
            await self.connection_manager.broadcast_to_project(
                agent_run.project_id,
                {
                    "type": "agent_run_update",
                    "agent_run": agent_run.to_dict()
                }
            )
        except Exception as e:
            logger.error("Failed to notify agent run update", agent_run_id=agent_run.id, error=str(e))

