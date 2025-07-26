"""
Projects API router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid

from backend.database import get_db
from backend.models.project import Project
from backend.models.configuration import ProjectConfiguration


router = APIRouter()


# Pydantic models for request/response
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    github_repository: str = Field(..., min_length=1, max_length=255)
    default_branch: str = Field(default="main", max_length=100)
    webhook_url: Optional[str] = None
    auto_confirm_plan: bool = False
    auto_merge_validated_pr: bool = False


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    github_repository: Optional[str] = Field(None, min_length=1, max_length=255)
    default_branch: Optional[str] = Field(None, max_length=100)
    webhook_url: Optional[str] = None
    auto_confirm_plan: Optional[bool] = None
    auto_merge_validated_pr: Optional[bool] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    github_repository: str
    default_branch: str
    webhook_url: Optional[str]
    auto_confirm_plan: bool
    auto_merge_validated_pr: bool
    created_at: Optional[str]
    updated_at: Optional[str]
    configuration: Optional[dict] = None


@router.get("/", response_model=List[ProjectResponse])
async def get_projects(db: Session = Depends(get_db)):
    """Get all projects"""
    projects = db.query(Project).all()
    return [project.to_dict() for project in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: Session = Depends(get_db)):
    """Get a specific project by ID"""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format"
        )
    
    project = db.query(Project).filter(Project.id == project_uuid).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    return project.to_dict()


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(project_data: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project"""
    # Check if project with same name already exists
    existing_project = db.query(Project).filter(Project.name == project_data.name).first()
    if existing_project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project with this name already exists"
        )
    
    # Create project
    project = Project(**project_data.dict())
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Create default configuration
    config = ProjectConfiguration(project_id=project.id)
    db.add(config)
    db.commit()
    db.refresh(config)
    
    # Refresh project to include configuration
    db.refresh(project)
    
    return project.to_dict()


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str, 
    project_data: ProjectUpdate, 
    db: Session = Depends(get_db)
):
    """Update a project"""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format"
        )
    
    project = db.query(Project).filter(Project.id == project_uuid).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Update project fields
    update_data = project_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    db.commit()
    db.refresh(project)
    
    return project.to_dict()


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Delete a project"""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format"
        )
    
    project = db.query(Project).filter(Project.id == project_uuid).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    db.delete(project)
    db.commit()


@router.get("/{project_id}/branches")
async def get_project_branches(project_id: str, db: Session = Depends(get_db)):
    """Get available branches for a project"""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format"
        )
    
    project = db.query(Project).filter(Project.id == project_uuid).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # TODO: Implement GitHub API integration to fetch actual branches
    # For now, return default branches
    return {
        "branches": [
            project.default_branch,
            "develop",
            "staging",
            "feature/example"
        ]
    }
