"""
Projects router for CodegenCICD Dashboard
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import structlog
import uuid

from backend.database import AsyncSessionLocal
from backend.models import Project, ProjectConfiguration, ProjectSecret
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


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    github_owner: str = Field(..., min_length=1, max_length=255)
    github_repo: str = Field(..., min_length=1, max_length=255)
    github_branch: str = Field(default="main", max_length=255)
    config_tier: str = Field(default="basic", regex="^(basic|intermediate|advanced)$")
    auto_merge_enabled: bool = Field(default=False)
    auto_merge_threshold: int = Field(default=80, ge=0, le=100)
    validation_enabled: bool = Field(default=True)
    grainchain_enabled: bool = Field(default=True)
    web_eval_enabled: bool = Field(default=True)
    graph_sitter_enabled: bool = Field(default=True)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    github_branch: Optional[str] = Field(None, max_length=255)
    config_tier: Optional[str] = Field(None, regex="^(basic|intermediate|advanced)$")
    auto_merge_enabled: Optional[bool] = None
    auto_merge_threshold: Optional[int] = Field(None, ge=0, le=100)
    validation_enabled: Optional[bool] = None
    grainchain_enabled: Optional[bool] = None
    web_eval_enabled: Optional[bool] = None
    graph_sitter_enabled: Optional[bool] = None
    is_active: Optional[bool] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    github_owner: str
    github_repo: str
    github_branch: str
    github_url: str
    webhook_url: Optional[str]
    webhook_active: bool
    is_active: bool
    auto_merge_enabled: bool
    auto_merge_threshold: int
    config_tier: str
    validation_enabled: bool
    grainchain_enabled: bool
    web_eval_enabled: bool
    graph_sitter_enabled: bool
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db)
) -> List[ProjectResponse]:
    """List all projects with pagination"""
    try:
        # Build query
        query = select(Project)
        if active_only:
            query = query.where(Project.is_active == True)
        
        query = query.offset(skip).limit(limit).order_by(Project.created_at.desc())
        
        # Execute query
        result = await db.execute(query)
        projects = result.scalars().all()
        
        logger.info("Listed projects", count=len(projects), skip=skip, limit=limit)
        
        return [ProjectResponse.from_orm(project) for project in projects]
        
    except Exception as e:
        logger.error("Failed to list projects", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve projects")


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db)
) -> ProjectResponse:
    """Create a new project"""
    try:
        # Check if project with same GitHub repo already exists
        existing_query = select(Project).where(
            and_(
                Project.github_owner == project_data.github_owner,
                Project.github_repo == project_data.github_repo
            )
        )
        result = await db.execute(existing_query)
        existing_project = result.scalar_one_or_none()
        
        if existing_project:
            raise HTTPException(
                status_code=400,
                detail=f"Project for {project_data.github_owner}/{project_data.github_repo} already exists"
            )
        
        # Create GitHub URL
        github_url = f"https://github.com/{project_data.github_owner}/{project_data.github_repo}"
        
        # Generate webhook URL
        webhook_url = f"{settings.base_url}/api/v1/webhooks/github"
        
        # Create project
        project = Project(
            name=project_data.name,
            description=project_data.description,
            github_owner=project_data.github_owner,
            github_repo=project_data.github_repo,
            github_branch=project_data.github_branch,
            github_url=github_url,
            webhook_url=webhook_url,
            config_tier=project_data.config_tier,
            auto_merge_enabled=project_data.auto_merge_enabled,
            auto_merge_threshold=project_data.auto_merge_threshold,
            validation_enabled=project_data.validation_enabled,
            grainchain_enabled=project_data.grainchain_enabled,
            web_eval_enabled=project_data.web_eval_enabled,
            graph_sitter_enabled=project_data.graph_sitter_enabled
        )
        
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        logger.info("Created project", 
                   project_id=str(project.id),
                   name=project.name,
                   github_repo=project.full_github_name)
        
        return ProjectResponse.from_orm(project)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create project", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create project")


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db)
) -> ProjectResponse:
    """Get a specific project by ID"""
    try:
        # Validate UUID
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")
        
        # Get project
        query = select(Project).where(Project.id == project_id)
        result = await db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return ProjectResponse.from_orm(project)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get project", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve project")


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    db: AsyncSession = Depends(get_db)
) -> ProjectResponse:
    """Update a project"""
    try:
        # Validate UUID
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")
        
        # Get project
        query = select(Project).where(Project.id == project_id)
        result = await db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Update project fields
        update_data = project_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)
        
        await db.commit()
        await db.refresh(project)
        
        logger.info("Updated project", 
                   project_id=project_id,
                   updated_fields=list(update_data.keys()))
        
        return ProjectResponse.from_orm(project)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update project", project_id=project_id, error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update project")


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a project (soft delete by setting is_active=False)"""
    try:
        # Validate UUID
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")
        
        # Get project
        query = select(Project).where(Project.id == project_id)
        result = await db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Soft delete
        project.is_active = False
        await db.commit()
        
        logger.info("Deleted project", project_id=project_id, name=project.name)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete project", project_id=project_id, error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete project")


@router.get("/{project_id}/stats")
async def get_project_stats(
    project_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get project statistics"""
    try:
        # Validate UUID
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")
        
        # Check if project exists
        query = select(Project).where(Project.id == project_id)
        result = await db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # TODO: Implement actual statistics queries
        # For now, return placeholder data
        stats = {
            "project_id": project_id,
            "total_agent_runs": 0,
            "successful_agent_runs": 0,
            "failed_agent_runs": 0,
            "total_validation_runs": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "average_validation_score": 0.0,
            "total_prs_created": 0,
            "total_prs_merged": 0,
            "last_activity": None
        }
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get project stats", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve project statistics")

