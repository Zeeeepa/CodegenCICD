"""
Projects router for managing GitHub projects and their configurations
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import logging

from backend.database import get_db
from backend.models.project import Project
from backend.services.github_service import GitHubService
from backend.services.projects_service import ProjectsService

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
from pydantic import BaseModel

class ProjectCreate(BaseModel):
    name: str
    github_owner: str
    github_repo: str
    webhook_url: Optional[str] = None
    auto_merge_enabled: bool = False
    auto_confirm_plans: bool = False

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None
    webhook_url: Optional[str] = None
    auto_merge_enabled: Optional[bool] = None
    auto_confirm_plans: Optional[bool] = None
    status: Optional[str] = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    github_owner: str
    github_repo: str
    webhook_url: str
    auto_merge_enabled: bool
    auto_confirm_plans: bool
    status: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

@router.get("/", response_model=List[ProjectResponse])
async def get_projects(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get all projects"""
    try:
        result = await db.execute(
            select(Project)
            .offset(skip)
            .limit(limit)
            .order_by(Project.created_at.desc())
        )
        projects = result.scalars().all()
        return [ProjectResponse.model_validate(project) for project in projects]
    except Exception as e:
        logger.error(f"Failed to get projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve projects"
        )

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific project by ID"""
    try:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        return ProjectResponse.model_validate(project)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project"
        )

@router.post("/", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new project"""
    try:
        # Validate GitHub repository exists
        github_service = GitHubService()
        repo_exists = await github_service.validate_repository(
            project_data.github_owner,
            project_data.github_repo
        )
        
        if not repo_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub repository not found or not accessible"
            )
        
        # Generate webhook URL if not provided
        webhook_url = project_data.webhook_url
        if not webhook_url:
            webhook_url = f"https://webhook-gateway.pixeliumperfecto.workers.dev/webhook/{project_data.github_owner}/{project_data.github_repo}"
        
        # Create project
        project = Project(
            name=project_data.name,
            github_owner=project_data.github_owner,
            github_repo=project_data.github_repo,
            webhook_url=webhook_url,
            auto_merge_enabled=project_data.auto_merge_enabled,
            auto_confirm_plans=project_data.auto_confirm_plans,
            status="active"
        )
        
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        # Set up GitHub webhook
        try:
            await github_service.setup_webhook(
                project_data.github_owner,
                project_data.github_repo,
                webhook_url
            )
        except Exception as e:
            logger.warning(f"Failed to setup GitHub webhook: {e}")
            # Don't fail the project creation if webhook setup fails
        
        logger.info(f"Created project: {project.name} ({project.id})")
        return ProjectResponse.model_validate(project)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project"
        )

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a project"""
    try:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Update fields
        update_data = project_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)
        
        await db.commit()
        await db.refresh(project)
        
        logger.info(f"Updated project: {project.name} ({project.id})")
        return ProjectResponse.model_validate(project)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project"
        )

@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a project"""
    try:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        await db.delete(project)
        await db.commit()
        
        logger.info(f"Deleted project: {project.name} ({project.id})")
        return {"message": "Project deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project"
        )

@router.get("/github-repos", response_model=List[dict])
async def get_github_repos():
    """Get available GitHub repositories"""
    try:
        github_service = GitHubService()
        repos = await github_service.get_user_repositories()
        return repos
    except Exception as e:
        logger.error(f"Failed to get GitHub repositories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve GitHub repositories"
        )

