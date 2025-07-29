"""
Projects API Router

This module provides REST API endpoints for managing pinned projects in the CodegenCICD dashboard.
It handles project pinning, unpinning, and metadata management with proper authentication and validation.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, validator
import logging
import uuid

from backend.database import get_db
from backend.services.project_service import ProjectService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])


# Pydantic models for request/response validation
class PinProjectRequest(BaseModel):
    """Request model for pinning a project."""
    github_repo_name: str = Field(..., min_length=1, max_length=255, description="GitHub repository name")
    github_repo_url: str = Field(..., min_length=1, max_length=500, description="GitHub repository URL")
    github_owner: str = Field(..., min_length=1, max_length=255, description="GitHub repository owner")
    display_name: str = Field(None, max_length=255, description="Custom display name for the project")
    description: str = Field(None, max_length=1000, description="Project description")
    
    @validator('github_repo_url')
    def validate_github_url(cls, v):
        """Validate that the URL is a valid GitHub repository URL."""
        if not v.startswith(('https://github.com/', 'http://github.com/')):
            raise ValueError('URL must be a valid GitHub repository URL')
        return v


class UpdateProjectRequest(BaseModel):
    """Request model for updating project metadata."""
    display_name: str = Field(None, max_length=255, description="Custom display name for the project")
    description: str = Field(None, max_length=1000, description="Project description")


class PinnedProjectResponse(BaseModel):
    """Response model for pinned project data."""
    id: int
    user_id: str
    github_repo_name: str
    github_repo_url: str
    github_owner: str
    display_name: str
    description: str = None
    pinned_at: str
    last_updated: str
    is_active: bool


class ApiResponse(BaseModel):
    """Generic API response model."""
    success: bool
    message: str
    data: Any = None


# Dependency for getting current user (mock implementation for now)
async def get_current_user() -> uuid.UUID:
    """
    Get the current authenticated user ID.
    
    TODO: Implement proper authentication middleware
    For now, returns a mock user ID for testing purposes.
    """
    # This is a mock implementation - replace with actual authentication
    return uuid.UUID("550e8400-e29b-41d4-a716-446655440000")


@router.get("/pinned", response_model=List[PinnedProjectResponse])
async def get_pinned_projects(
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user)
):
    """
    Get all pinned projects for the authenticated user.
    
    Returns:
        List of pinned projects with metadata
        
    Raises:
        HTTPException: If database error occurs
    """
    try:
        service = ProjectService(db)
        projects = await service.get_pinned_projects(current_user_id)
        
        logger.info(f"Retrieved {len(projects)} pinned projects for user {current_user_id}")
        return projects
        
    except Exception as e:
        logger.error(f"Error in get_pinned_projects: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve pinned projects"
        )


@router.post("/pin", response_model=ApiResponse)
async def pin_project(
    request: PinProjectRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user)
):
    """
    Pin a project to the user's dashboard.
    
    Args:
        request: Project data to pin
        
    Returns:
        API response with pinned project data
        
    Raises:
        HTTPException: If validation fails or project already pinned
    """
    try:
        service = ProjectService(db)
        project_data = request.dict()
        
        pinned_project = await service.pin_project(current_user_id, project_data)
        
        return ApiResponse(
            success=True,
            message="Project pinned successfully",
            data=pinned_project
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in pin_project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pin project"
        )


@router.delete("/unpin/{project_id}", response_model=ApiResponse)
async def unpin_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user)
):
    """
    Unpin a project from the user's dashboard.
    
    Args:
        project_id: ID of the project to unpin
        
    Returns:
        API response confirming unpinning
        
    Raises:
        HTTPException: If project not found or not owned by user
    """
    try:
        service = ProjectService(db)
        success = await service.unpin_project(current_user_id, project_id)
        
        if success:
            return ApiResponse(
                success=True,
                message="Project unpinned successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in unpin_project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unpin project"
        )


@router.put("/pinned/{project_id}", response_model=ApiResponse)
async def update_pinned_project(
    project_id: int,
    request: UpdateProjectRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user)
):
    """
    Update metadata for a pinned project.
    
    Args:
        project_id: ID of the project to update
        request: Updated project data
        
    Returns:
        API response with updated project data
        
    Raises:
        HTTPException: If project not found or validation fails
    """
    try:
        service = ProjectService(db)
        update_data = request.dict(exclude_unset=True)
        
        updated_project = await service.update_pinned_project(
            current_user_id, project_id, update_data
        )
        
        return ApiResponse(
            success=True,
            message="Project updated successfully",
            data=updated_project
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_pinned_project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project"
        )


@router.get("/pinned/{project_id}", response_model=PinnedProjectResponse)
async def get_pinned_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user)
):
    """
    Get a specific pinned project by ID.
    
    Args:
        project_id: ID of the project to retrieve
        
    Returns:
        Pinned project data
        
    Raises:
        HTTPException: If project not found
    """
    try:
        service = ProjectService(db)
        project = await service.get_project_by_id(current_user_id, project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        return project
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_pinned_project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project"
        )


# Health check endpoint for the projects API
@router.get("/health")
async def projects_health_check():
    """Health check endpoint for the projects API."""
    return {"status": "healthy", "service": "projects"}
