"""
Agent runs API router for managing Codegen API interactions
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel, Field

from backend.database import get_db
from backend.models.agent_run import AgentRun, AgentRunStatus, AgentRunType

router = APIRouter()

# Pydantic models for request/response
class AgentRunCreate(BaseModel):
    project_id: int
    target_text: str = Field(..., min_length=1)
    planning_statement: Optional[str] = None
    auto_merge_enabled: bool = Field(default=False)

class AgentRunResponse(BaseModel):
    id: int
    project_id: int
    codegen_run_id: Optional[int]
    codegen_org_id: int
    target_text: str
    planning_statement: Optional[str]
    status: str
    run_type: str
    result: Optional[str]
    error_message: Optional[str]
    pr_number: Optional[int]
    pr_url: Optional[str]
    pr_branch: Optional[str]
    validation_status: str
    auto_merge_enabled: bool
    merge_completed: bool
    merge_url: Optional[str]
    is_completed: bool
    has_pr: bool
    validation_in_progress: bool
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

@router.get("/", response_model=List[AgentRunResponse])
async def list_agent_runs(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List agent runs with optional filtering"""
    try:
        query = select(AgentRun)
        
        if project_id:
            query = query.where(AgentRun.project_id == project_id)
        
        if status:
            try:
                status_enum = AgentRunStatus(status)
                query = query.where(AgentRun.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status}"
                )
        
        query = query.offset(skip).limit(limit).order_by(AgentRun.created_at.desc())
        
        result = await db.execute(query)
        agent_runs = result.scalars().all()
        
        return [AgentRunResponse(**run.to_dict()) for run in agent_runs]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list agent runs: {str(e)}"
        )

@router.get("/{run_id}", response_model=AgentRunResponse)
async def get_agent_run(run_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific agent run by ID"""
    try:
        result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
        agent_run = result.scalar_one_or_none()
        
        if not agent_run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent run with ID {run_id} not found"
            )
        
        return AgentRunResponse(**agent_run.to_dict())
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent run: {str(e)}"
        )

@router.post("/", response_model=AgentRunResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_run(
    run_data: AgentRunCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new agent run"""
    try:
        # TODO: Implement Codegen API integration
        agent_run = AgentRun(
            project_id=run_data.project_id,
            codegen_org_id=323,  # From environment
            target_text=run_data.target_text,
            planning_statement=run_data.planning_statement,
            auto_merge_enabled=run_data.auto_merge_enabled,
            status=AgentRunStatus.PENDING
        )
        
        db.add(agent_run)
        await db.commit()
        await db.refresh(agent_run)
        
        return AgentRunResponse(**agent_run.to_dict())
    
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent run: {str(e)}"
        )
