"""
Agent run management API endpoints
"""
import structlog
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, Field

from backend.database import get_db
from backend.models.project import Project
from backend.models.agent_run import AgentRun
from backend.models.configuration import Configuration
from backend.integrations.codegen_client import CodegenClient
from backend.websocket.connection_manager import ConnectionManager
from backend.middleware.auth import get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/agent-runs", tags=["agent-runs"])
connection_manager = ConnectionManager()


# Pydantic models
class AgentRunCreate(BaseModel):
    project_id: str
    prompt: str = Field(..., min_length=1, max_length=5000)
    use_planning_statement: bool = Field(default=True)


class AgentRunContinue(BaseModel):
    continuation_prompt: str = Field(..., min_length=1, max_length=5000)


class AgentRunResponse(BaseModel):
    id: str
    project_id: str
    prompt: str
    status: str
    response_type: Optional[str]
    response_content: Optional[str]
    pr_url: Optional[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


async def process_agent_run(agent_run_id: str, db: AsyncSession):
    """Background task to process agent run"""
    try:
        # Get agent run
        result = await db.execute(select(AgentRun).where(AgentRun.id == agent_run_id))
        agent_run = result.scalar_one_or_none()
        
        if not agent_run:
            logger.error("Agent run not found", agent_run_id=agent_run_id)
            return
        
        # Get project and configuration
        project_result = await db.execute(select(Project).where(Project.id == agent_run.project_id))
        project = project_result.scalar_one_or_none()
        
        config_result = await db.execute(
            select(Configuration).where(Configuration.project_id == agent_run.project_id)
        )
        config = config_result.scalar_one_or_none()
        
        # Update status to running
        await db.execute(
            update(AgentRun)
            .where(AgentRun.id == agent_run_id)
            .values(status="running")
        )
        await db.commit()
        
        # Broadcast status update
        await connection_manager.broadcast_to_subscribers(
            f"agent_run_{agent_run_id}",
            {
                "type": "agent_run_status",
                "agent_run_id": agent_run_id,
                "status": "running"
            }
        )
        
        # Create Codegen client and run agent
        codegen_client = CodegenClient()
        
        planning_statement = config.planning_statement if config else None
        repository = project.repository_url if project else None
        
        response = await codegen_client.create_agent_run(
            prompt=agent_run.prompt,
            repository=repository,
            planning_statement=planning_statement
        )
        
        # Determine response type
        response_type = "regular"
        pr_url = None
        
        if "task_object" in response:
            # Using official SDK
            task = response["task_object"]
            task.refresh()  # Get latest status
            
            response_content = getattr(task, 'result', str(task.status))
            
            # Check if response contains PR
            if hasattr(task, 'result') and task.result and 'github.com' in str(task.result):
                response_type = "pr"
                # Extract PR URL from result
                import re
                pr_match = re.search(r'https://github\.com/[^/]+/[^/]+/pull/\d+', str(task.result))
                if pr_match:
                    pr_url = pr_match.group(0)
            
            # Check if response contains plan
            elif 'plan' in str(response_content).lower():
                response_type = "plan"
        else:
            # Using fallback HTTP client
            response_content = response.get("result", "Agent run completed")
        
        # Update agent run with results
        await db.execute(
            update(AgentRun)
            .where(AgentRun.id == agent_run_id)
            .values(
                status="completed",
                response_type=response_type,
                response_content=response_content,
                pr_url=pr_url
            )
        )
        await db.commit()
        
        # Broadcast completion
        await connection_manager.broadcast_to_subscribers(
            f"agent_run_{agent_run_id}",
            {
                "type": "agent_run_completed",
                "agent_run_id": agent_run_id,
                "status": "completed",
                "response_type": response_type,
                "response_content": response_content,
                "pr_url": pr_url
            }
        )
        
        logger.info("Agent run completed", agent_run_id=agent_run_id, response_type=response_type)
        
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
        await connection_manager.broadcast_to_subscribers(
            f"agent_run_{agent_run_id}",
            {
                "type": "agent_run_failed",
                "agent_run_id": agent_run_id,
                "status": "failed",
                "error": str(e)
            }
        )


@router.post("/", response_model=AgentRunResponse)
async def create_agent_run(
    agent_run_data: AgentRunCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new agent run"""
    logger.info("Creating agent run", project_id=agent_run_data.project_id, user_id=current_user["id"])
    
    try:
        # Verify project exists
        result = await db.execute(select(Project).where(Project.id == agent_run_data.project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Create agent run
        agent_run = AgentRun(
            project_id=agent_run_data.project_id,
            prompt=agent_run_data.prompt,
            status="pending",
            created_by=current_user["id"]
        )
        
        db.add(agent_run)
        await db.commit()
        await db.refresh(agent_run)
        
        # Start background processing
        background_tasks.add_task(process_agent_run, agent_run.id, db)
        
        logger.info("Agent run created", agent_run_id=agent_run.id)
        return agent_run
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to create agent run", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create agent run")


@router.get("/", response_model=List[AgentRunResponse])
async def list_agent_runs(
    project_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List agent runs"""
    logger.info("Listing agent runs", project_id=project_id, user_id=current_user["id"])
    
    try:
        query = select(AgentRun).offset(skip).limit(limit).order_by(AgentRun.created_at.desc())
        
        if project_id:
            query = query.where(AgentRun.project_id == project_id)
        
        result = await db.execute(query)
        agent_runs = result.scalars().all()
        
        logger.info("Agent runs retrieved", count=len(agent_runs))
        return agent_runs
        
    except Exception as e:
        logger.error("Failed to list agent runs", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve agent runs")


@router.get("/{agent_run_id}", response_model=AgentRunResponse)
async def get_agent_run(
    agent_run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific agent run"""
    logger.info("Getting agent run", agent_run_id=agent_run_id, user_id=current_user["id"])
    
    try:
        result = await db.execute(select(AgentRun).where(AgentRun.id == agent_run_id))
        agent_run = result.scalar_one_or_none()
        
        if not agent_run:
            raise HTTPException(status_code=404, detail="Agent run not found")
        
        return agent_run
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get agent run", agent_run_id=agent_run_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve agent run")


@router.post("/{agent_run_id}/continue", response_model=AgentRunResponse)
async def continue_agent_run(
    agent_run_id: str,
    continue_data: AgentRunContinue,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Continue an existing agent run"""
    logger.info("Continuing agent run", agent_run_id=agent_run_id, user_id=current_user["id"])
    
    try:
        # Get agent run
        result = await db.execute(select(AgentRun).where(AgentRun.id == agent_run_id))
        agent_run = result.scalar_one_or_none()
        
        if not agent_run:
            raise HTTPException(status_code=404, detail="Agent run not found")
        
        if agent_run.status not in ["completed", "failed"]:
            raise HTTPException(status_code=400, detail="Agent run is not in a continuable state")
        
        # Update agent run with continuation
        await db.execute(
            update(AgentRun)
            .where(AgentRun.id == agent_run_id)
            .values(
                prompt=f"{agent_run.prompt}\n\nContinuation: {continue_data.continuation_prompt}",
                status="pending",
                response_type=None,
                response_content=None,
                pr_url=None
            )
        )
        await db.commit()
        await db.refresh(agent_run)
        
        # Start background processing
        background_tasks.add_task(process_agent_run, agent_run.id, db)
        
        logger.info("Agent run continuation started", agent_run_id=agent_run_id)
        return agent_run
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to continue agent run", agent_run_id=agent_run_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to continue agent run")

