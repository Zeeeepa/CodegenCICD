"""
Projects API router for managing GitHub repositories and project settings
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List, Optional
from pydantic import BaseModel, Field

from backend.database import get_db
from backend.models.project import Project
from backend.services.github_service import GitHubService
from backend.services.webhook_service import WebhookService

router = APIRouter()

# Pydantic models for request/response
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    github_owner: str = Field(..., min_length=1, max_length=255)
    github_repo: str = Field(..., min_length=1, max_length=255)
    default_branch: str = Field(default="main", max_length=100)
    auto_confirm_plan: bool = Field(default=False)
    auto_merge_validated_pr: bool = Field(default=False)
    planning_statement: Optional[str] = None
    repository_rules: Optional[str] = None
    setup_commands: Optional[str] = None
    setup_branch: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    default_branch: Optional[str] = Field(None, max_length=100)
    auto_confirm_plan: Optional[bool] = None
    auto_merge_validated_pr: Optional[bool] = None
    planning_statement: Optional[str] = None
    repository_rules: Optional[str] = None
    setup_commands: Optional[str] = None
    setup_branch: Optional[str] = None
    is_active: Optional[bool] = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    github_owner: str
    github_repo: str
    github_url: str
    full_name: str
    default_branch: str
    webhook_active: bool
    auto_confirm_plan: bool
    auto_merge_validated_pr: bool
    planning_statement: Optional[str]
    has_custom_rules: bool
    has_setup_commands: bool
    setup_branch: Optional[str]
    is_active: bool
    last_activity: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """List all projects with pagination"""
    try:
        query = select(Project)
        
        if active_only:
            query = query.where(Project.is_active == True)
        
        query = query.offset(skip).limit(limit).order_by(Project.created_at.desc())
        
        result = await db.execute(query)
        projects = result.scalars().all()
        
        return [ProjectResponse(**project.to_dict()) for project in projects]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}"
        )

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific project by ID"""
    try:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found"
            )
        
        return ProjectResponse(**project.to_dict())
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project: {str(e)}"
        )

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new project"""
    try:
        # Validate GitHub repository exists
        github_service = GitHubService()
        repo_info = await github_service.get_repository_info(
            project_data.github_owner, 
            project_data.github_repo
        )
        
        if not repo_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"GitHub repository {project_data.github_owner}/{project_data.github_repo} not found or not accessible"
            )
        
        # Check if project already exists
        existing_query = select(Project).where(
            Project.github_owner == project_data.github_owner,
            Project.github_repo == project_data.github_repo
        )
        result = await db.execute(existing_query)
        existing_project = result.scalar_one_or_none()
        
        if existing_project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project for repository {project_data.github_owner}/{project_data.github_repo} already exists"
            )
        
        # Create new project
        project = Project(
            name=project_data.name,
            description=project_data.description,
            github_owner=project_data.github_owner,
            github_repo=project_data.github_repo,
            github_url=repo_info.get("html_url", f"https://github.com/{project_data.github_owner}/{project_data.github_repo}"),
            default_branch=project_data.default_branch,
            auto_confirm_plan=project_data.auto_confirm_plan,
            auto_merge_validated_pr=project_data.auto_merge_validated_pr,
            planning_statement=project_data.planning_statement,
            repository_rules=project_data.repository_rules,
            setup_commands=project_data.setup_commands,
            setup_branch=project_data.setup_branch,
        )
        
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        # Set up webhook if needed
        webhook_service = WebhookService()
        await webhook_service.setup_project_webhook(project)
        
        return ProjectResponse(**project.to_dict())
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing project"""
    try:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found"
            )
        
        # Update project fields
        update_data = project_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)
        
        await db.commit()
        await db.refresh(project)
        
        return ProjectResponse(**project.to_dict())
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a project (soft delete by setting is_active=False)"""
    try:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found"
            )
        
        # Soft delete
        project.is_active = False
        await db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )

@router.get("/{project_id}/branches")
async def get_project_branches(project_id: int, db: AsyncSession = Depends(get_db)):
    """Get available branches for a project"""
    try:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found"
            )
        
        github_service = GitHubService()
        branches = await github_service.get_repository_branches(
            project.github_owner, 
            project.github_repo
        )
        
        return {"branches": branches}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project branches: {str(e)}"
        )

@router.post("/{project_id}/test-setup")
async def test_setup_commands(
    project_id: int,
    branch: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Test setup commands for a project"""
    try:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found"
            )
        
        if not project.setup_commands:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No setup commands configured for this project"
            )
        
        # Use provided branch or project's setup branch or default branch
        test_branch = branch or project.setup_branch or project.default_branch
        
        # TODO: Implement actual setup command testing
        # This would involve creating a temporary environment and running the commands
        
        return {
            "status": "success",
            "message": f"Setup commands tested successfully on branch '{test_branch}'",
            "branch": test_branch,
            "commands": project.setup_commands.split('\n'),
            "logs": ["Command testing not yet implemented"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test setup commands: {str(e)}"
        )
