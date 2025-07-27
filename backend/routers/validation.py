"""
Validation router for CodegenCICD Dashboard
"""
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import structlog
import uuid

from backend.database import AsyncSessionLocal
from backend.models import Project, ValidationRun, ValidationStep, ValidationResult
from backend.models.validation import ValidationStatus, ValidationStepType, ValidationStepStatus
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


class ValidationRunCreate(BaseModel):
    project_id: str = Field(..., description="Project ID")
    pr_url: str = Field(..., description="Pull request URL")
    pr_number: int = Field(..., description="Pull request number")
    pr_branch: str = Field(..., description="Pull request branch")
    pr_commit_sha: str = Field(..., description="Pull request commit SHA")
    agent_run_id: Optional[str] = Field(None, description="Associated agent run ID")


class ValidationRunResponse(BaseModel):
    id: str
    project_id: str
    agent_run_id: Optional[str]
    pr_url: str
    pr_number: int
    pr_branch: str
    pr_commit_sha: str
    status: str
    current_step_index: int
    progress_percentage: int
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_seconds: Optional[int]
    overall_score: Optional[float]
    passed_steps: int
    failed_steps: int
    skipped_steps: int
    auto_merge_eligible: bool
    auto_merge_executed: bool
    auto_merge_reason: Optional[str]
    error_message: Optional[str]
    retry_count: int
    max_retries: int
    grainchain_snapshot_id: Optional[str]
    web_eval_session_id: Optional[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class ValidationStepResponse(BaseModel):
    id: str
    validation_run_id: str
    step_index: int
    step_type: str
    step_name: str
    step_description: Optional[str]
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_seconds: Optional[int]
    confidence_score: Optional[float]
    weight: float
    is_critical: bool
    retry_count: int
    max_retries: int
    external_service_id: Optional[str]
    external_service_url: Optional[str]
    logs: Optional[str]
    error_message: Optional[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[ValidationRunResponse])
async def list_validation_runs(
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
) -> List[ValidationRunResponse]:
    """List validation runs with optional filtering"""
    try:
        # Build query
        query = select(ValidationRun)
        
        if project_id:
            # Validate UUID
            try:
                uuid.UUID(project_id)
                query = query.where(ValidationRun.project_id == project_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid project ID format")
        
        if status:
            try:
                status_enum = ValidationStatus(status)
                query = query.where(ValidationRun.status == status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        query = query.offset(skip).limit(limit).order_by(ValidationRun.created_at.desc())
        
        # Execute query
        result = await db.execute(query)
        validation_runs = result.scalars().all()
        
        logger.info("Listed validation runs", 
                   count=len(validation_runs), 
                   project_id=project_id,
                   status=status)
        
        return [ValidationRunResponse.from_orm(run) for run in validation_runs]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list validation runs", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve validation runs")


@router.post("/", response_model=ValidationRunResponse, status_code=201)
async def create_validation_run(
    run_data: ValidationRunCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> ValidationRunResponse:
    """Create a new validation run"""
    try:
        # Validate project exists
        project_query = select(Project).where(Project.id == run_data.project_id)
        result = await db.execute(project_query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if not project.is_active:
            raise HTTPException(status_code=400, detail="Project is not active")
        
        if not project.validation_enabled:
            raise HTTPException(status_code=400, detail="Validation is disabled for this project")
        
        # Check if validation run already exists for this PR
        existing_query = select(ValidationRun).where(
            and_(
                ValidationRun.project_id == run_data.project_id,
                ValidationRun.pr_number == run_data.pr_number,
                ValidationRun.status.in_([ValidationStatus.PENDING, ValidationStatus.RUNNING])
            )
        )
        result = await db.execute(existing_query)
        existing_run = result.scalar_one_or_none()
        
        if existing_run:
            raise HTTPException(
                status_code=400, 
                detail=f"Validation run already exists for PR #{run_data.pr_number}"
            )
        
        # Create validation run record
        validation_run = ValidationRun(
            project_id=run_data.project_id,
            agent_run_id=run_data.agent_run_id,
            pr_url=run_data.pr_url,
            pr_number=run_data.pr_number,
            pr_branch=run_data.pr_branch,
            pr_commit_sha=run_data.pr_commit_sha,
            status=ValidationStatus.PENDING,
            current_step_index=0,
            progress_percentage=0
        )
        
        db.add(validation_run)
        await db.commit()
        await db.refresh(validation_run)
        
        # Create validation steps
        await _create_validation_steps(validation_run.id, project, db)
        
        # Start validation pipeline in background
        background_tasks.add_task(
            _execute_validation_pipeline,
            str(validation_run.id)
        )
        
        logger.info("Created validation run", 
                   validation_run_id=str(validation_run.id),
                   project_id=run_data.project_id,
                   pr_number=run_data.pr_number)
        
        return ValidationRunResponse.from_orm(validation_run)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create validation run", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create validation run")


@router.get("/{validation_run_id}", response_model=ValidationRunResponse)
async def get_validation_run(
    validation_run_id: str,
    db: AsyncSession = Depends(get_db)
) -> ValidationRunResponse:
    """Get a specific validation run by ID"""
    try:
        # Validate UUID
        try:
            uuid.UUID(validation_run_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid validation run ID format")
        
        # Get validation run
        query = select(ValidationRun).where(ValidationRun.id == validation_run_id)
        result = await db.execute(query)
        validation_run = result.scalar_one_or_none()
        
        if not validation_run:
            raise HTTPException(status_code=404, detail="Validation run not found")
        
        return ValidationRunResponse.from_orm(validation_run)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get validation run", validation_run_id=validation_run_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve validation run")


@router.get("/{validation_run_id}/steps", response_model=List[ValidationStepResponse])
async def get_validation_steps(
    validation_run_id: str,
    db: AsyncSession = Depends(get_db)
) -> List[ValidationStepResponse]:
    """Get steps for a validation run"""
    try:
        # Validate UUID
        try:
            uuid.UUID(validation_run_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid validation run ID format")
        
        # Get validation steps
        query = select(ValidationStep).where(
            ValidationStep.validation_run_id == validation_run_id
        ).order_by(ValidationStep.step_index)
        
        result = await db.execute(query)
        steps = result.scalars().all()
        
        return [ValidationStepResponse.from_orm(step) for step in steps]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get validation steps", validation_run_id=validation_run_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve validation steps")


@router.get("/{validation_run_id}/results")
async def get_validation_results(
    validation_run_id: str,
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get results for a validation run"""
    try:
        # Validate UUID
        try:
            uuid.UUID(validation_run_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid validation run ID format")
        
        # Get validation results
        query = select(ValidationResult).where(
            ValidationResult.validation_run_id == validation_run_id
        ).order_by(ValidationResult.result_type, ValidationResult.result_name)
        
        result = await db.execute(query)
        results = result.scalars().all()
        
        return [result.to_dict() for result in results]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get validation results", validation_run_id=validation_run_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve validation results")


@router.post("/{validation_run_id}/retry", response_model=ValidationRunResponse)
async def retry_validation_run(
    validation_run_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> ValidationRunResponse:
    """Retry a failed validation run"""
    try:
        # Validate UUID
        try:
            uuid.UUID(validation_run_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid validation run ID format")
        
        # Get validation run
        query = select(ValidationRun).where(ValidationRun.id == validation_run_id)
        result = await db.execute(query)
        validation_run = result.scalar_one_or_none()
        
        if not validation_run:
            raise HTTPException(status_code=404, detail="Validation run not found")
        
        if validation_run.status not in [ValidationStatus.FAILED, ValidationStatus.CANCELLED]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot retry validation run with status: {validation_run.status.value}"
            )
        
        if validation_run.retry_count >= validation_run.max_retries:
            raise HTTPException(
                status_code=400, 
                detail=f"Maximum retries ({validation_run.max_retries}) exceeded"
            )
        
        # Reset validation run for retry
        validation_run.status = ValidationStatus.PENDING
        validation_run.current_step_index = 0
        validation_run.progress_percentage = 0
        validation_run.retry_count += 1
        validation_run.error_message = None
        validation_run.started_at = None
        validation_run.completed_at = None
        validation_run.duration_seconds = None
        
        # Reset all steps
        steps_query = select(ValidationStep).where(ValidationStep.validation_run_id == validation_run_id)
        result = await db.execute(steps_query)
        steps = result.scalars().all()
        
        for step in steps:
            step.status = ValidationStepStatus.PENDING
            step.started_at = None
            step.completed_at = None
            step.duration_seconds = None
            step.confidence_score = None
            step.logs = None
            step.error_message = None
            step.retry_count = 0
        
        await db.commit()
        
        # Start validation pipeline in background
        background_tasks.add_task(
            _execute_validation_pipeline,
            str(validation_run.id)
        )
        
        logger.info("Retrying validation run", 
                   validation_run_id=validation_run_id,
                   retry_count=validation_run.retry_count)
        
        return ValidationRunResponse.from_orm(validation_run)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retry validation run", validation_run_id=validation_run_id, error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to retry validation run")


# Helper functions
async def _create_validation_steps(validation_run_id: str, project: Project, db: AsyncSession) -> None:
    """Create the 7 validation steps for a validation run"""
    steps_config = [
        {
            "step_index": 0,
            "step_type": ValidationStepType.SNAPSHOT_CREATION,
            "step_name": "Snapshot Creation",
            "step_description": "Create grainchain sandbox environment",
            "weight": 1.0,
            "is_critical": True
        },
        {
            "step_index": 1,
            "step_type": ValidationStepType.CODE_CLONE,
            "step_name": "Code Clone",
            "step_description": "Clone PR branch to sandbox",
            "weight": 1.0,
            "is_critical": True
        },
        {
            "step_index": 2,
            "step_type": ValidationStepType.CODE_ANALYSIS,
            "step_name": "Code Analysis",
            "step_description": "Run graph-sitter code quality analysis",
            "weight": 2.0,
            "is_critical": False
        },
        {
            "step_index": 3,
            "step_type": ValidationStepType.DEPLOYMENT,
            "step_name": "Deployment",
            "step_description": "Execute project setup commands",
            "weight": 2.0,
            "is_critical": True
        },
        {
            "step_index": 4,
            "step_type": ValidationStepType.DEPLOYMENT_VALIDATION,
            "step_name": "Deployment Validation",
            "step_description": "Validate deployment success with Gemini AI",
            "weight": 2.0,
            "is_critical": True
        },
        {
            "step_index": 5,
            "step_type": ValidationStepType.UI_TESTING,
            "step_name": "UI Testing",
            "step_description": "Run comprehensive web-eval-agent tests",
            "weight": 3.0,
            "is_critical": False
        },
        {
            "step_index": 6,
            "step_type": ValidationStepType.AUTO_MERGE,
            "step_name": "Auto-merge",
            "step_description": "Check auto-merge eligibility and execute if applicable",
            "weight": 1.0,
            "is_critical": False
        }
    ]
    
    for step_config in steps_config:
        # Skip steps based on project configuration
        if step_config["step_type"] == ValidationStepType.CODE_ANALYSIS and not project.graph_sitter_enabled:
            continue
        if step_config["step_type"] == ValidationStepType.UI_TESTING and not project.web_eval_enabled:
            continue
        if step_config["step_type"] == ValidationStepType.AUTO_MERGE and not project.auto_merge_enabled:
            continue
        
        step = ValidationStep(
            validation_run_id=validation_run_id,
            step_index=step_config["step_index"],
            step_type=step_config["step_type"],
            step_name=step_config["step_name"],
            step_description=step_config["step_description"],
            weight=step_config["weight"],
            is_critical=step_config["is_critical"],
            status=ValidationStepStatus.PENDING
        )
        
        db.add(step)
    
    await db.commit()


async def _execute_validation_pipeline(validation_run_id: str) -> None:
    """Execute validation pipeline in background using ValidationService"""
    try:
        from backend.services.validation_service import ValidationService
        
        # Initialize and use validation service
        validation_service = ValidationService()
        await validation_service.initialize()
        
        try:
            await validation_service.execute_validation_pipeline(validation_run_id)
        finally:
            await validation_service.close()
            
    except Exception as e:
        logger.error("Failed to execute validation pipeline",
                    validation_run_id=validation_run_id,
                    error=str(e))
        
        # Update status to failed
        try:
            async with AsyncSessionLocal() as db:
                query = select(ValidationRun).where(ValidationRun.id == validation_run_id)
                result = await db.execute(query)
                validation_run = result.scalar_one_or_none()
                
                if validation_run:
                    validation_run.status = ValidationStatus.FAILED
                    validation_run.error_message = str(e)
                    validation_run.completed_at = _get_timestamp()
                    await db.commit()
        except Exception as update_error:
            logger.error("Failed to update validation run status after error",
                        validation_run_id=validation_run_id,
                        error=str(update_error))


def _get_timestamp() -> str:
    """Get current timestamp in ISO format"""
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"
