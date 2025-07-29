"""
Agent runs router for managing Codegen API interactions
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import logging

from backend.database import get_db
from backend.models.agent_run import AgentRun, AgentRunStatus, AgentRunType
from backend.models.project import Project
from backend.services.codegen_service import CodegenService
from backend.services.validation_service import ValidationService
from backend.websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models
from pydantic import BaseModel

class AgentRunCreate(BaseModel):
    project_id: int
    target_text: str
    planning_statement: Optional[str] = None

class AgentRunContinue(BaseModel):
    message: str

class AgentRunResponse(BaseModel):
    id: int
    project_id: int
    codegen_run_id: Optional[int] = None
    target_text: str
    planning_statement: Optional[str] = None
    status: str
    run_type: str
    result: Optional[str] = None
    error_message: Optional[str] = None
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    validation_status: str
    auto_merge_enabled: bool
    merge_completed: bool
    started_at: str
    completed_at: Optional[str] = None

    class Config:
        from_attributes = True

@router.get("/", response_model=List[AgentRunResponse])
async def get_agent_runs(
    project_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get agent runs, optionally filtered by project"""
    try:
        query = select(AgentRun).order_by(AgentRun.created_at.desc())
        
        if project_id:
            query = query.where(AgentRun.project_id == project_id)
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        agent_runs = result.scalars().all()
        
        return [AgentRunResponse.model_validate(run) for run in agent_runs]
    except Exception as e:
        logger.error(f"Failed to get agent runs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent runs"
        )

@router.get("/{agent_run_id}", response_model=AgentRunResponse)
async def get_agent_run(
    agent_run_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific agent run by ID"""
    try:
        result = await db.execute(select(AgentRun).where(AgentRun.id == agent_run_id))
        agent_run = result.scalar_one_or_none()
        
        if not agent_run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent run not found"
            )
        
        return AgentRunResponse.model_validate(agent_run)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent run {agent_run_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent run"
        )

@router.post("/", response_model=AgentRunResponse)
async def create_agent_run(
    agent_run_data: AgentRunCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a new agent run"""
    try:
        # Validate project exists
        result = await db.execute(select(Project).where(Project.id == agent_run_data.project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Create agent run record
        agent_run = AgentRun(
            project_id=agent_run_data.project_id,
            target_text=agent_run_data.target_text,
            planning_statement=agent_run_data.planning_statement,
            status=AgentRunStatus.PENDING,
            codegen_org_id=323,  # From environment
            auto_merge_enabled=project.auto_merge_enabled
        )
        
        db.add(agent_run)
        await db.commit()
        await db.refresh(agent_run)
        
        # Start agent run in background
        background_tasks.add_task(
            start_agent_run_background,
            agent_run.id,
            project
        )
        
        logger.info(f"Created agent run: {agent_run.id} for project {project.name}")
        return AgentRunResponse.model_validate(agent_run)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create agent run: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create agent run"
        )

@router.post("/{agent_run_id}/continue", response_model=AgentRunResponse)
async def continue_agent_run(
    agent_run_id: int,
    continue_data: AgentRunContinue,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Continue an existing agent run with additional input"""
    try:
        result = await db.execute(select(AgentRun).where(AgentRun.id == agent_run_id))
        agent_run = result.scalar_one_or_none()
        
        if not agent_run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent run not found"
            )
        
        if agent_run.status not in [AgentRunStatus.COMPLETED, AgentRunStatus.FAILED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent run must be completed or failed to continue"
            )
        
        # Update status to running
        agent_run.status = AgentRunStatus.RUNNING
        await db.commit()
        
        # Continue agent run in background
        background_tasks.add_task(
            continue_agent_run_background,
            agent_run_id,
            continue_data.message
        )
        
        logger.info(f"Continuing agent run: {agent_run_id}")
        return AgentRunResponse.model_validate(agent_run)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to continue agent run {agent_run_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to continue agent run"
        )

@router.post("/{agent_run_id}/cancel")
async def cancel_agent_run(
    agent_run_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Cancel a running agent run"""
    try:
        result = await db.execute(select(AgentRun).where(AgentRun.id == agent_run_id))
        agent_run = result.scalar_one_or_none()
        
        if not agent_run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent run not found"
            )
        
        if agent_run.status not in [AgentRunStatus.PENDING, AgentRunStatus.RUNNING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending or running agent runs can be cancelled"
            )
        
        # Update status
        agent_run.status = AgentRunStatus.CANCELLED
        await db.commit()
        
        # TODO: Cancel the actual Codegen API run if possible
        
        logger.info(f"Cancelled agent run: {agent_run_id}")
        return {"message": "Agent run cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel agent run {agent_run_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel agent run"
        )

# Background task functions
async def start_agent_run_background(agent_run_id: int, project: Project):
    """Background task to start an agent run"""
    try:
        from backend.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            # Get agent run
            result = await db.execute(select(AgentRun).where(AgentRun.id == agent_run_id))
            agent_run = result.scalar_one()
            
            # Update status to running
            agent_run.status = AgentRunStatus.RUNNING
            await db.commit()
            
            # Send WebSocket update
            connection_manager = ConnectionManager()
            await connection_manager.broadcast_to_project(
                project.id,
                {
                    "type": "agent_run_update",
                    "data": {
                        "id": agent_run.id,
                        "status": "running",
                        "project_id": project.id
                    }
                }
            )
            
            # Start Codegen API run
            codegen_service = CodegenService()
            
            # Build complete prompt
            prompt_parts = []
            
            # Add repository rules if available
            # TODO: Get from configuration
            
            # Add planning statement
            if agent_run.planning_statement:
                prompt_parts.append(agent_run.planning_statement)
            
            # Add target text
            prompt_parts.append(f"Target: {agent_run.target_text}")
            
            complete_prompt = "\n\n".join(prompt_parts)
            
            # Create Codegen run
            codegen_run = await codegen_service.create_agent_run(
                prompt=complete_prompt,
                project_context=f"Project: {project.name} ({project.github_owner}/{project.github_repo})"
            )
            
            # Update agent run with Codegen run ID
            agent_run.codegen_run_id = codegen_run.get("id")
            await db.commit()
            
            # Poll for completion
            await poll_agent_run_completion(agent_run_id, codegen_run.get("id"))
            
    except Exception as e:
        logger.error(f"Failed to start agent run {agent_run_id}: {e}")
        
        # Update status to failed
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(AgentRun).where(AgentRun.id == agent_run_id))
            agent_run = result.scalar_one()
            agent_run.status = AgentRunStatus.FAILED
            agent_run.error_message = str(e)
            await db.commit()

async def continue_agent_run_background(agent_run_id: int, message: str):
    """Background task to continue an agent run"""
    try:
        from backend.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(AgentRun).where(AgentRun.id == agent_run_id))
            agent_run = result.scalar_one()
            
            if not agent_run.codegen_run_id:
                raise Exception("No Codegen run ID found")
            
            # Continue with Codegen API
            codegen_service = CodegenService()
            await codegen_service.continue_agent_run(
                agent_run.codegen_run_id,
                message
            )
            
            # Poll for completion
            await poll_agent_run_completion(agent_run_id, agent_run.codegen_run_id)
            
    except Exception as e:
        logger.error(f"Failed to continue agent run {agent_run_id}: {e}")

async def poll_agent_run_completion(agent_run_id: int, codegen_run_id: int):
    """Poll Codegen API for agent run completion"""
    import asyncio
    from backend.database import AsyncSessionLocal
    
    codegen_service = CodegenService()
    validation_service = ValidationService()
    
    try:
        while True:
            # Check status
            run_status = await codegen_service.get_agent_run_status(codegen_run_id)
            
            if run_status.get("status") == "completed":
                async with AsyncSessionLocal() as db:
                    result = await db.execute(select(AgentRun).where(AgentRun.id == agent_run_id))
                    agent_run = result.scalar_one()
                    
                    # Update agent run
                    agent_run.status = AgentRunStatus.COMPLETED
                    agent_run.result = run_status.get("result", "")
                    
                    # Determine run type based on result
                    result_text = agent_run.result.lower()
                    if "pull request" in result_text or "pr #" in result_text:
                        agent_run.run_type = AgentRunType.PR
                        # Extract PR info
                        # TODO: Parse PR number and URL from result
                        
                        # Start validation pipeline
                        await validation_service.start_validation_pipeline(agent_run_id)
                        
                    elif "plan" in result_text or "steps" in result_text:
                        agent_run.run_type = AgentRunType.PLAN
                    else:
                        agent_run.run_type = AgentRunType.REGULAR
                    
                    await db.commit()
                    
                    # Send WebSocket update
                    connection_manager = ConnectionManager()
                    await connection_manager.broadcast_to_project(
                        agent_run.project_id,
                        {
                            "type": "agent_run_update",
                            "data": {
                                "id": agent_run.id,
                                "status": "completed",
                                "run_type": agent_run.run_type.value,
                                "result": agent_run.result,
                                "project_id": agent_run.project_id
                            }
                        }
                    )
                
                break
                
            elif run_status.get("status") == "failed":
                async with AsyncSessionLocal() as db:
                    result = await db.execute(select(AgentRun).where(AgentRun.id == agent_run_id))
                    agent_run = result.scalar_one()
                    agent_run.status = AgentRunStatus.FAILED
                    agent_run.error_message = run_status.get("error", "Unknown error")
                    await db.commit()
                break
            
            # Wait before next poll
            await asyncio.sleep(5)
            
    except Exception as e:
        logger.error(f"Failed to poll agent run completion {agent_run_id}: {e}")

