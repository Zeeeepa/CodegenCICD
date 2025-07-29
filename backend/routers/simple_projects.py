"""
Simple Projects Router for Pinned Projects API
Uses separate database to avoid model conflicts
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import logging
import uuid

from backend.simple_database import get_simple_db, SimplePinnedProjectService, init_simple_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/simple-projects", tags=["simple-projects"])

# Pydantic models for request/response
class PinProjectRequest(BaseModel):
    """Request model for pinning a project."""
    github_repo_name: str = Field(..., description="GitHub repository name")
    github_repo_url: str = Field(..., description="GitHub repository URL")
    github_owner: str = Field(..., description="GitHub repository owner")
    display_name: str = Field(None, description="Custom display name for the project")
    description: str = Field(None, description="Project description")

class UpdateProjectRequest(BaseModel):
    """Request model for updating a pinned project."""
    display_name: str = Field(None, description="Updated display name")
    description: str = Field(None, description="Updated description")

class PinnedProjectResponse(BaseModel):
    """Response model for pinned project data."""
    id: int
    user_id: str
    github_repo_name: str
    github_repo_url: str
    github_owner: str
    display_name: str = None
    description: str = None
    pinned_at: str = None
    last_updated: str = None
    is_active: bool

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service: str

# Mock user dependency
async def get_current_user() -> uuid.UUID:
    """Get the current authenticated user ID."""
    return uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for simple projects service."""
    return HealthResponse(status="healthy", service="simple-projects")

@router.get("/pinned", response_model=List[PinnedProjectResponse])
async def get_pinned_projects(
    db: AsyncSession = Depends(get_simple_db),
    current_user_id: uuid.UUID = Depends(get_current_user)
):
    """Get all pinned projects for the authenticated user."""
    try:
        service = SimplePinnedProjectService(db)
        projects = await service.get_pinned_projects(current_user_id)
        return projects
    except Exception as e:
        logger.error(f"Error retrieving pinned projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve pinned projects"
        )

@router.post("/pin", response_model=PinnedProjectResponse, status_code=status.HTTP_201_CREATED)
async def pin_project(
    request: PinProjectRequest,
    db: AsyncSession = Depends(get_simple_db),
    current_user_id: uuid.UUID = Depends(get_current_user)
):
    """Pin a project to the user's dashboard."""
    try:
        service = SimplePinnedProjectService(db)
        project_data = request.dict()
        result = await service.pin_project(current_user_id, project_data)
        return result
    except Exception as e:
        logger.error(f"Error pinning project: {e}")
        if "already pinned" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Project is already pinned"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pin project"
        )

@router.delete("/unpin/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unpin_project(
    project_id: int,
    db: AsyncSession = Depends(get_simple_db),
    current_user_id: uuid.UUID = Depends(get_current_user)
):
    """Unpin a project from the user's dashboard."""
    try:
        service = SimplePinnedProjectService(db)
        success = await service.unpin_project(current_user_id, project_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
    except Exception as e:
        logger.error(f"Error unpinning project: {e}")
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unpin project"
        )

# Initialize database on startup
@router.on_event("startup")
async def startup_event():
    """Initialize simple database on startup."""
    try:
        await init_simple_db()
        logger.info("Simple database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize simple database: {e}")
        raise

