"""
Agent runs router for CodegenCICD Dashboard
"""
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import structlog
import uuid

from backend.database import AsyncSessionLocal
from backend.models import Project, AgentRun, AgentRunStep, AgentRunResponse
from backend.models.agent_run import AgentRunStatus, AgentRunType
from backend.integrations import CodegenClient
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter()


# Dependency to get database session
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Pydantic models for request/response
from pydantic import BaseModel, Field


class AgentRunCreate(BaseModel):
    project_id: str = Field(..., description="Project ID")
    target: str = Field(..., min_length=1, description="Target/goal for the agent")
    planning_statement: Optional[str] = Field(None, description="Custom planning statement")
    auto_confirm_plans: bool = Field(default=False, description="Auto-confirm plans")
    max_iterations: int = Field(default=10, ge=1, le=50, description="Maximum iterations")


class AgentRunContinue(BaseModel):
    user_input: str = Field(..., min_length=1, description="User input to continue the run")


class AgentRunResponse(BaseModel):
    id: str
    project_id: str
    codegen_run_id: Optional[str]
    target: str
    planning_statement: Optional[str]
    run_type: str
    status: str
    progress_percentage: int
    current_step: Optional[str]
    final_response: Optional[str]
    error_message: Optional[str]
    pr_url: Optional[str]
    pr_number: Optional[int]
    execution_time_seconds: Optional[int]
    tokens_used: Optional[int]
    cost_usd: Optional[str]
    auto_confirm_plans: bool
    max_iterations: int
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[AgentRunResponse])
async def list_agent_runs(
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
) -> List[AgentRunResponse]:
    """List agent runs with optional filtering"""
    try:
        # Build query
        query = select(AgentRun)
        
        if project_id:
            # Validate UUID
            try:
                uuid.UUID(project_id)
                query = query.where(AgentRun.project_id == project_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid project ID format")
        
        if status:
            try:
                status_enum = AgentRunStatus(status)
                query = query.where(AgentRun.status == status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        query = query.offset(skip).limit(limit).order_by(AgentRun.created_at.desc())
        
        # Execute query
        result = await db.execute(query)
        agent_runs = result.scalars().all()
        
        logger.info("Listed agent runs", 
                   count=len(agent_runs), 
                   project_id=project_id,
                   status=status)
        
        return [AgentRunResponse.from_orm(run) for run in agent_runs]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list agent runs", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve agent runs")


@router.post("/", response_model=AgentRunResponse, status_code=201)
async def create_agent_run(
    run_data: AgentRunCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> AgentRunResponse:
    """Create a new agent run"""
    try:
        # Validate project exists
        project_query = select(Project).where(Project.id == run_data.project_id)
        result = await db.execute(project_query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if not project.is_active:
            raise HTTPException(status_code=400, detail="Project is not active")
        
        # Create agent run record
        agent_run = AgentRun(
            project_id=run_data.project_id,
            target=run_data.target,
            planning_statement=run_data.planning_statement,
            auto_confirm_plans=run_data.auto_confirm_plans,
            max_iterations=run_data.max_iterations,
            status=AgentRunStatus.PENDING
        )
        
        db.add(agent_run)
        await db.commit()
        await db.refresh(agent_run)
        
        # Start agent run in background
        background_tasks.add_task(
            _execute_agent_run,
            str(agent_run.id),
            project.full_github_name
        )
        
        logger.info("Created agent run", 
                   agent_run_id=str(agent_run.id),
                   project_id=run_data.project_id,
                   target=run_data.target[:100])
        
        return AgentRunResponse.from_orm(agent_run)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create agent run", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create agent run")


@router.get("/{agent_run_id}", response_model=AgentRunResponse)
async def get_agent_run(
    agent_run_id: str,
    db: AsyncSession = Depends(get_db)
) -> AgentRunResponse:
    """Get a specific agent run by ID"""
    try:
        # Validate UUID
        try:
            uuid.UUID(agent_run_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid agent run ID format")
        
        # Get agent run
        query = select(AgentRun).where(AgentRun.id == agent_run_id)
        result = await db.execute(query)
        agent_run = result.scalar_one_or_none()
        
        if not agent_run:
            raise HTTPException(status_code=404, detail="Agent run not found")
        
        return AgentRunResponse.from_orm(agent_run)
        
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
    db: AsyncSession = Depends(get_db)
) -> AgentRunResponse:
    """Continue an agent run with user input"""
    try:
        # Validate UUID
        try:
            uuid.UUID(agent_run_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid agent run ID format")
        
        # Get agent run
        query = select(AgentRun).where(AgentRun.id == agent_run_id)
        result = await db.execute(query)
        agent_run = result.scalar_one_or_none()
        
        if not agent_run:
            raise HTTPException(status_code=404, detail="Agent run not found")
        
        if agent_run.status != AgentRunStatus.WAITING_FOR_INPUT:
            raise HTTPException(
                status_code=400, 
                detail=f"Agent run is not waiting for input (current status: {agent_run.status.value})"
            )
        
        # Update status to running
        agent_run.status = AgentRunStatus.RUNNING
        await db.commit()
        
        # Continue agent run in background
        background_tasks.add_task(
            _continue_agent_run,
            str(agent_run.id),
            continue_data.user_input
        )
        
        logger.info("Continuing agent run", 
                   agent_run_id=agent_run_id,
                   input_length=len(continue_data.user_input))
        
        return AgentRunResponse.from_orm(agent_run)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to continue agent run", agent_run_id=agent_run_id, error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to continue agent run")


@router.post("/{agent_run_id}/cancel", response_model=AgentRunResponse)
async def cancel_agent_run(
    agent_run_id: str,
    db: AsyncSession = Depends(get_db)
) -> AgentRunResponse:
    """Cancel an agent run"""
    try:
        # Validate UUID
        try:
            uuid.UUID(agent_run_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid agent run ID format")
        
        # Get agent run
        query = select(AgentRun).where(AgentRun.id == agent_run_id)
        result = await db.execute(query)
        agent_run = result.scalar_one_or_none()
        
        if not agent_run:
            raise HTTPException(status_code=404, detail="Agent run not found")
        
        if not agent_run.is_active:
            raise HTTPException(
                status_code=400, 
                detail=f"Agent run is not active (current status: {agent_run.status.value})"
            )
        
        # Cancel via Codegen API if we have a run ID
        if agent_run.codegen_run_id:
            try:
                async with CodegenClient() as client:
                    await client.cancel_agent_run(agent_run.codegen_run_id)
            except Exception as e:
                logger.warning("Failed to cancel agent run via API", 
                             codegen_run_id=agent_run.codegen_run_id,
                             error=str(e))
        
        # Update status
        agent_run.status = AgentRunStatus.CANCELLED
        await db.commit()
        
        logger.info("Cancelled agent run", agent_run_id=agent_run_id)
        
        return AgentRunResponse.from_orm(agent_run)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel agent run", agent_run_id=agent_run_id, error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to cancel agent run")


@router.get("/{agent_run_id}/steps")
async def get_agent_run_steps(
    agent_run_id: str,
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get steps for an agent run"""
    try:
        # Validate UUID
        try:
            uuid.UUID(agent_run_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid agent run ID format")
        
        # Get agent run steps
        query = select(AgentRunStep).where(
            AgentRunStep.agent_run_id == agent_run_id
        ).order_by(AgentRunStep.step_number)
        
        result = await db.execute(query)
        steps = result.scalars().all()
        
        return [step.to_dict() for step in steps]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get agent run steps", agent_run_id=agent_run_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve agent run steps")


@router.get("/{agent_run_id}/responses")
async def get_agent_run_responses(
    agent_run_id: str,
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get responses for an agent run"""
    try:
        # Validate UUID
        try:
            uuid.UUID(agent_run_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid agent run ID format")
        
        # Get agent run responses
        query = select(AgentRunResponse).where(
            AgentRunResponse.agent_run_id == agent_run_id
        ).order_by(AgentRunResponse.sequence_number)
        
        result = await db.execute(query)
        responses = result.scalars().all()
        
        return [response.to_dict() for response in responses]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get agent run responses", agent_run_id=agent_run_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve agent run responses")


# Background task functions
async def _execute_agent_run(agent_run_id: str, repo_name: str) -> None:
    """Execute agent run in background"""
    try:
        async with AsyncSessionLocal() as db:
            # Get agent run
            query = select(AgentRun).where(AgentRun.id == agent_run_id)
            result = await db.execute(query)
            agent_run = result.scalar_one_or_none()
            
            if not agent_run:
                logger.error("Agent run not found for execution", agent_run_id=agent_run_id)
                return
            
            # Update status to running
            agent_run.status = AgentRunStatus.RUNNING
            await db.commit()
            
            # Execute via Codegen API
            async with CodegenClient() as client:
                # Prepare target with planning statement
                full_target = agent_run.target
                if agent_run.planning_statement:
                    full_target = f"{agent_run.planning_statement}\n\n{agent_run.target}"
                
                # Create agent run
                codegen_response = await client.create_agent_run(
                    target=full_target,
                    repo_name=repo_name,
                    auto_confirm_plans=agent_run.auto_confirm_plans,
                    max_iterations=agent_run.max_iterations
                )
                
                # Update with Codegen run ID
                agent_run.codegen_run_id = codegen_response.get("id")
                await db.commit()
                
                # Wait for completion (this will poll the API)
                final_result = await client.wait_for_completion(agent_run.codegen_run_id)
                
                # Update agent run with final results
                agent_run.status = AgentRunStatus.COMPLETED if final_result.get("status") == "completed" else AgentRunStatus.FAILED
                agent_run.final_response = final_result.get("final_response")
                agent_run.error_message = final_result.get("error_message")
                agent_run.execution_time_seconds = final_result.get("execution_time_seconds")
                agent_run.tokens_used = final_result.get("tokens_used")
                agent_run.cost_usd = str(final_result.get("cost_usd", 0))
                
                # Extract PR information if available
                if final_result.get("pr_url"):
                    agent_run.pr_url = final_result["pr_url"]
                    # Extract PR number from URL
                    try:
                        agent_run.pr_number = int(final_result["pr_url"].split("/")[-1])
                    except (ValueError, IndexError):
                        pass
                
                await db.commit()
                
                logger.info("Agent run completed successfully",
                           agent_run_id=agent_run_id,
                           status=agent_run.status.value,
                           pr_url=agent_run.pr_url)
    
    except Exception as e:
        logger.error("Failed to execute agent run",
                    agent_run_id=agent_run_id,
                    error=str(e))
        
        # Update status to failed
        try:
            async with AsyncSessionLocal() as db:
                query = select(AgentRun).where(AgentRun.id == agent_run_id)
                result = await db.execute(query)
                agent_run = result.scalar_one_or_none()
                
                if agent_run:
                    agent_run.status = AgentRunStatus.FAILED
                    agent_run.error_message = str(e)
                    await db.commit()
        except Exception as update_error:
            logger.error("Failed to update agent run status after error",
                        agent_run_id=agent_run_id,
                        error=str(update_error))


async def _continue_agent_run(agent_run_id: str, user_input: str) -> None:
    """Continue agent run in background"""
    try:
        async with AsyncSessionLocal() as db:
            # Get agent run
            query = select(AgentRun).where(AgentRun.id == agent_run_id)
            result = await db.execute(query)
            agent_run = result.scalar_one_or_none()
            
            if not agent_run or not agent_run.codegen_run_id:
                logger.error("Agent run not found or missing Codegen run ID", 
                           agent_run_id=agent_run_id)
                return
            
            # Continue via Codegen API
            async with CodegenClient() as client:
                continue_response = await client.continue_agent_run(
                    agent_run.codegen_run_id,
                    user_input
                )
                
                # Wait for completion
                final_result = await client.wait_for_completion(agent_run.codegen_run_id)
                
                # Update agent run with results
                agent_run.status = AgentRunStatus.COMPLETED if final_result.get("status") == "completed" else AgentRunStatus.FAILED
                agent_run.final_response = final_result.get("final_response")
                agent_run.error_message = final_result.get("error_message")
                
                await db.commit()
                
                logger.info("Agent run continued successfully",
                           agent_run_id=agent_run_id,
                           status=agent_run.status.value)
    
    except Exception as e:
        logger.error("Failed to continue agent run",
                    agent_run_id=agent_run_id,
                    error=str(e))
        
        # Update status to failed
        try:
            async with AsyncSessionLocal() as db:
                query = select(AgentRun).where(AgentRun.id == agent_run_id)
                result = await db.execute(query)
                agent_run = result.scalar_one_or_none()
                
                if agent_run:
                    agent_run.status = AgentRunStatus.FAILED
                    agent_run.error_message = str(e)
                    await db.commit()
        except Exception as update_error:
            logger.error("Failed to update agent run status after continue error",
                        agent_run_id=agent_run_id,
                        error=str(update_error))

