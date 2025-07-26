"""
Project management API endpoints
"""
import structlog
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from pydantic import BaseModel, Field

from backend.database import get_db
from backend.models.project import Project
from backend.models.configuration import Configuration
from backend.middleware.auth import get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/projects", tags=["projects"])


# Pydantic models for request/response
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    repository_url: str = Field(..., regex=r'^https://github\.com/[\w\-\.]+/[\w\-\.]+$')
    default_branch: str = Field(default="main", max_length=50)
    webhook_url: Optional[str] = None
    auto_merge_enabled: bool = Field(default=False)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    default_branch: Optional[str] = Field(None, max_length=50)
    webhook_url: Optional[str] = None
    auto_merge_enabled: Optional[bool] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    repository_url: str
    default_branch: str
    webhook_url: Optional[str]
    auto_merge_enabled: bool
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class ProjectConfigurationUpdate(BaseModel):
    repository_rules: Optional[str] = None
    setup_commands: Optional[str] = None
    planning_statement: Optional[str] = None
    secrets: Optional[dict] = None


@router.post("/", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new project"""
    logger.info("Creating project", name=project_data.name, user_id=current_user["id"])
    
    try:
        # Create project
        project = Project(
            name=project_data.name,
            description=project_data.description,
            repository_url=project_data.repository_url,
            default_branch=project_data.default_branch,
            webhook_url=project_data.webhook_url,
            auto_merge_enabled=project_data.auto_merge_enabled,
            created_by=current_user["id"]
        )
        
        db.add(project)
        await db.flush()  # Get the project ID
        
        # Create default configuration
        config = Configuration(
            project_id=project.id,
            repository_rules="",
            setup_commands="",
            planning_statement="",
            secrets={}
        )
        
        db.add(config)
        await db.commit()
        await db.refresh(project)
        
        logger.info("Project created", project_id=project.id)
        return project
        
    except Exception as e:
        await db.rollback()
        logger.error("Failed to create project", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create project")


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all projects"""
    logger.info("Listing projects", user_id=current_user["id"], skip=skip, limit=limit)
    
    try:
        result = await db.execute(
            select(Project)
            .offset(skip)
            .limit(limit)
            .order_by(Project.created_at.desc())
        )
        projects = result.scalars().all()
        
        logger.info("Projects retrieved", count=len(projects))
        return projects
        
    except Exception as e:
        logger.error("Failed to list projects", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve projects")


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific project"""
    logger.info("Getting project", project_id=project_id, user_id=current_user["id"])
    
    try:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return project
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get project", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve project")


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a project"""
    logger.info("Updating project", project_id=project_id, user_id=current_user["id"])
    
    try:
        # Check if project exists
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Update fields
        update_data = project_data.dict(exclude_unset=True)
        if update_data:
            await db.execute(
                update(Project)
                .where(Project.id == project_id)
                .values(**update_data)
            )
            await db.commit()
            await db.refresh(project)
        
        logger.info("Project updated", project_id=project_id)
        return project
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to update project", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update project")


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a project"""
    logger.info("Deleting project", project_id=project_id, user_id=current_user["id"])
    
    try:
        # Check if project exists
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Delete project (cascade will handle related records)
        await db.execute(delete(Project).where(Project.id == project_id))
        await db.commit()
        
        logger.info("Project deleted", project_id=project_id)
        return {"message": "Project deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to delete project", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete project")


@router.put("/{project_id}/configuration")
async def update_project_configuration(
    project_id: str,
    config_data: ProjectConfigurationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update project configuration"""
    logger.info("Updating project configuration", project_id=project_id, user_id=current_user["id"])
    
    try:
        # Check if project exists
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get or create configuration
        config_result = await db.execute(
            select(Configuration).where(Configuration.project_id == project_id)
        )
        config = config_result.scalar_one_or_none()
        
        if not config:
            config = Configuration(project_id=project_id)
            db.add(config)
        
        # Update configuration fields
        update_data = config_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(config, field, value)
        
        await db.commit()
        
        logger.info("Project configuration updated", project_id=project_id)
        return {"message": "Configuration updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to update configuration", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update configuration")


@router.get("/{project_id}/configuration")
async def get_project_configuration(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get project configuration"""
    logger.info("Getting project configuration", project_id=project_id, user_id=current_user["id"])
    
    try:
        # Check if project exists
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get configuration
        config_result = await db.execute(
            select(Configuration).where(Configuration.project_id == project_id)
        )
        config = config_result.scalar_one_or_none()
        
        if not config:
            # Return default configuration
            return {
                "repository_rules": "",
                "setup_commands": "",
                "planning_statement": "",
                "secrets": {}
            }
        
        return {
            "repository_rules": config.repository_rules,
            "setup_commands": config.setup_commands,
            "planning_statement": config.planning_statement,
            "secrets": list(config.secrets.keys()) if config.secrets else []  # Don't expose values
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get configuration", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve configuration")

