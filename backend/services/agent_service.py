"""
Agent service for managing Codegen agent runs and interactions
"""
import structlog
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from backend.models.agent_run import AgentRun
from backend.models.project import Project
from backend.models.configuration import Configuration
from backend.integrations.codegen_client import CodegenClient
from backend.websocket.connection_manager import ConnectionManager

logger = structlog.get_logger(__name__)


class AgentService:
    """Service for managing agent runs and Codegen API interactions"""
    
    def __init__(self):
        self.codegen_client = CodegenClient()
        self.connection_manager = ConnectionManager()
    
    async def create_agent_run(
        self,
        db: AsyncSession,
        project_id: str,
        prompt: str,
        created_by: str,
        use_planning_statement: bool = True
    ) -> AgentRun:
        """Create a new agent run"""
        logger.info("Creating agent run", project_id=project_id, created_by=created_by)
        
        # Verify project exists
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise ValueError("Project not found")
        
        # Create agent run record
        agent_run = AgentRun(
            project_id=project_id,
            prompt=prompt,
            status="pending",
            created_by=created_by
        )
        
        db.add(agent_run)
        await db.commit()
        await db.refresh(agent_run)
        
        logger.info("Agent run created", agent_run_id=agent_run.id)
        return agent_run
    
    async def execute_agent_run(
        self,
        db: AsyncSession,
        agent_run_id: str
    ) -> Dict[str, Any]:
        """Execute an agent run using Codegen API"""
        logger.info("Executing agent run", agent_run_id=agent_run_id)
        
        # Get agent run
        result = await db.execute(select(AgentRun).where(AgentRun.id == agent_run_id))
        agent_run = result.scalar_one_or_none()
        
        if not agent_run:
            raise ValueError("Agent run not found")
        
        # Get project and configuration
        project_result = await db.execute(select(Project).where(Project.id == agent_run.project_id))
        project = project_result.scalar_one_or_none()
        
        config_result = await db.execute(
            select(Configuration).where(Configuration.project_id == agent_run.project_id)
        )
        config = config_result.scalar_one_or_none()
        
        try:
            # Update status to running
            await db.execute(
                update(AgentRun)
                .where(AgentRun.id == agent_run_id)
                .values(status="running")
            )
            await db.commit()
            
            # Broadcast status update
            await self.connection_manager.broadcast_to_subscribers(
                f"agent_run_{agent_run_id}",
                {
                    "type": "agent_run_status",
                    "agent_run_id": agent_run_id,
                    "status": "running"
                }
            )
            
            # Execute with Codegen API
            planning_statement = config.planning_statement if config else None
            repository = project.repository_url if project else None
            
            response = await self.codegen_client.create_agent_run(
                prompt=agent_run.prompt,
                repository=repository,
                planning_statement=planning_statement
            )
            
            # Process response
            response_type = self._determine_response_type(response)
            pr_url = self._extract_pr_url(response) if response_type == "pr" else None
            
            # Update agent run with results
            await db.execute(
                update(AgentRun)
                .where(AgentRun.id == agent_run_id)
                .values(
                    status="completed",
                    response_type=response_type,
                    response_content=str(response.get("result", response)),
                    pr_url=pr_url
                )
            )
            await db.commit()
            
            # Broadcast completion
            await self.connection_manager.broadcast_to_subscribers(
                f"agent_run_{agent_run_id}",
                {
                    "type": "agent_run_completed",
                    "agent_run_id": agent_run_id,
                    "status": "completed",
                    "response_type": response_type,
                    "response_content": str(response.get("result", response)),
                    "pr_url": pr_url
                }
            )
            
            logger.info("Agent run completed", agent_run_id=agent_run_id, response_type=response_type)
            return response
            
        except Exception as e:
            logger.error("Agent run failed", agent_run_id=agent_run_id, error=str(e))
            
            # Update status to failed
            await db.execute(
                update(AgentRun)
                .where(AgentRun.id == agent_run_id)
                .values(
                    status="failed",
                    response_content=f"Error: {str(e)}"
                )
            )
            await db.commit()
            
            # Broadcast failure
            await self.connection_manager.broadcast_to_subscribers(
                f"agent_run_{agent_run_id}",
                {
                    "type": "agent_run_failed",
                    "agent_run_id": agent_run_id,
                    "status": "failed",
                    "error": str(e)
                }
            )
            
            raise
    
    async def continue_agent_run(
        self,
        db: AsyncSession,
        agent_run_id: str,
        continuation_prompt: str
    ) -> AgentRun:
        """Continue an existing agent run"""
        logger.info("Continuing agent run", agent_run_id=agent_run_id)
        
        # Get agent run
        result = await db.execute(select(AgentRun).where(AgentRun.id == agent_run_id))
        agent_run = result.scalar_one_or_none()
        
        if not agent_run:
            raise ValueError("Agent run not found")
        
        if agent_run.status not in ["completed", "failed"]:
            raise ValueError("Agent run is not in a continuable state")
        
        # Update agent run with continuation
        combined_prompt = f"{agent_run.prompt}\n\nContinuation: {continuation_prompt}"
        
        await db.execute(
            update(AgentRun)
            .where(AgentRun.id == agent_run_id)
            .values(
                prompt=combined_prompt,
                status="pending",
                response_type=None,
                response_content=None,
                pr_url=None
            )
        )
        await db.commit()
        await db.refresh(agent_run)
        
        logger.info("Agent run continuation prepared", agent_run_id=agent_run_id)
        return agent_run
    
    def _determine_response_type(self, response: Dict[str, Any]) -> str:
        """Determine the type of response from Codegen API"""
        if "task_object" in response:
            # Using official SDK
            task = response["task_object"]
            result = getattr(task, 'result', str(task.status))
            
            if hasattr(task, 'result') and task.result and 'github.com' in str(task.result):
                return "pr"
            elif 'plan' in str(result).lower():
                return "plan"
        else:
            # Using fallback HTTP client
            result = response.get("result", "")
            if 'github.com' in str(result):
                return "pr"
            elif 'plan' in str(result).lower():
                return "plan"
        
        return "regular"
    
    def _extract_pr_url(self, response: Dict[str, Any]) -> Optional[str]:
        """Extract PR URL from response"""
        import re
        
        if "task_object" in response:
            task = response["task_object"]
            result = getattr(task, 'result', '')
        else:
            result = response.get("result", "")
        
        # Look for GitHub PR URL pattern
        pr_match = re.search(r'https://github\.com/[^/]+/[^/]+/pull/\d+', str(result))
        return pr_match.group(0) if pr_match else None
    
    async def get_agent_run_status(
        self,
        db: AsyncSession,
        agent_run_id: str
    ) -> Optional[AgentRun]:
        """Get current status of an agent run"""
        result = await db.execute(select(AgentRun).where(AgentRun.id == agent_run_id))
        return result.scalar_one_or_none()
    
    async def list_agent_runs(
        self,
        db: AsyncSession,
        project_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 10
    ) -> List[AgentRun]:
        """List agent runs with optional project filtering"""
        query = select(AgentRun).offset(skip).limit(limit).order_by(AgentRun.created_at.desc())
        
        if project_id:
            query = query.where(AgentRun.project_id == project_id)
        
        result = await db.execute(query)
        return result.scalars().all()

