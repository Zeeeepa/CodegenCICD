"""
Project Service

This module provides business logic for managing pinned projects in the CodegenCICD dashboard.
It handles CRUD operations, validation, and integration with GitHub API.
"""

from typing import List, Optional, Dict, Any
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
import logging

from backend.models.pinned_project import PinnedProject
from backend.models.user import User

logger = logging.getLogger(__name__)


class ProjectService:
    """Service class for managing pinned projects."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_pinned_projects(self, user_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Get all pinned projects for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of pinned project dictionaries
            
        Raises:
            HTTPException: If user not found or database error
        """
        try:
            # Query pinned projects for the user
            stmt = select(PinnedProject).where(
                and_(
                    PinnedProject.user_id == user_id,
                    PinnedProject.is_active == True
                )
            ).order_by(PinnedProject.pinned_at.desc())
            
            result = await self.db.execute(stmt)
            projects = result.scalars().all()
            
            return [project.to_dict() for project in projects]
            
        except Exception as e:
            logger.error(f"Error fetching pinned projects for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch pinned projects"
            )
    
    async def pin_project(self, user_id: uuid.UUID, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pin a project to user's dashboard.
        
        Args:
            user_id: ID of the user
            project_data: Dictionary containing project information
            
        Returns:
            Dictionary representation of the pinned project
            
        Raises:
            HTTPException: If validation fails or project already pinned
        """
        try:
            # Validate required fields
            required_fields = ["github_repo_name", "github_repo_url", "github_owner"]
            for field in required_fields:
                if not project_data.get(field):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Missing required field: {field}"
                    )
            
            # Check if project is already pinned
            existing_stmt = select(PinnedProject).where(
                and_(
                    PinnedProject.user_id == user_id,
                    PinnedProject.github_repo_name == project_data["github_repo_name"],
                    PinnedProject.is_active == True
                )
            )
            existing_result = await self.db.execute(existing_stmt)
            existing_project = existing_result.scalar_one_or_none()
            
            if existing_project:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Project is already pinned"
                )
            
            # Check user's pinned project limit (50 projects max)
            count_stmt = select(PinnedProject).where(
                and_(
                    PinnedProject.user_id == user_id,
                    PinnedProject.is_active == True
                )
            )
            count_result = await self.db.execute(count_stmt)
            current_count = len(count_result.scalars().all())
            
            if current_count >= 50:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Maximum number of pinned projects (50) reached"
                )
            
            # Create new pinned project
            pinned_project = PinnedProject(
                user_id=user_id,
                github_repo_name=project_data["github_repo_name"],
                github_repo_url=project_data["github_repo_url"],
                github_owner=project_data["github_owner"],
                display_name=project_data.get("display_name"),
                description=project_data.get("description")
            )
            
            self.db.add(pinned_project)
            await self.db.commit()
            await self.db.refresh(pinned_project)
            
            logger.info(f"Project {project_data['github_repo_name']} pinned for user {user_id}")
            return pinned_project.to_dict()
            
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error pinning project for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to pin project"
            )
    
    async def unpin_project(self, user_id: uuid.UUID, project_id: int) -> bool:
        """
        Unpin a project from user's dashboard.
        
        Args:
            user_id: ID of the user
            project_id: ID of the project to unpin
            
        Returns:
            True if project was unpinned successfully
            
        Raises:
            HTTPException: If project not found or not owned by user
        """
        try:
            # Find the project
            stmt = select(PinnedProject).where(
                and_(
                    PinnedProject.id == project_id,
                    PinnedProject.user_id == user_id,
                    PinnedProject.is_active == True
                )
            )
            result = await self.db.execute(stmt)
            project = result.scalar_one_or_none()
            
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pinned project not found"
                )
            
            # Soft delete (mark as inactive)
            project.is_active = False
            await self.db.commit()
            
            logger.info(f"Project {project.github_repo_name} unpinned for user {user_id}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error unpinning project {project_id} for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to unpin project"
            )
    
    async def update_pinned_project(self, user_id: uuid.UUID, project_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update metadata for a pinned project.
        
        Args:
            user_id: ID of the user
            project_id: ID of the project to update
            update_data: Dictionary containing fields to update
            
        Returns:
            Dictionary representation of the updated project
            
        Raises:
            HTTPException: If project not found or validation fails
        """
        try:
            # Find the project
            stmt = select(PinnedProject).where(
                and_(
                    PinnedProject.id == project_id,
                    PinnedProject.user_id == user_id,
                    PinnedProject.is_active == True
                )
            )
            result = await self.db.execute(stmt)
            project = result.scalar_one_or_none()
            
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pinned project not found"
                )
            
            # Update allowed fields
            allowed_fields = ["display_name", "description"]
            for field in allowed_fields:
                if field in update_data:
                    setattr(project, field, update_data[field])
            
            await self.db.commit()
            await self.db.refresh(project)
            
            logger.info(f"Project {project.github_repo_name} updated for user {user_id}")
            return project.to_dict()
            
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating project {project_id} for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update project"
            )
    
    async def get_project_by_id(self, user_id: uuid.UUID, project_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific pinned project by ID.
        
        Args:
            user_id: ID of the user
            project_id: ID of the project
            
        Returns:
            Dictionary representation of the project or None if not found
        """
        try:
            stmt = select(PinnedProject).where(
                and_(
                    PinnedProject.id == project_id,
                    PinnedProject.user_id == user_id,
                    PinnedProject.is_active == True
                )
            )
            result = await self.db.execute(stmt)
            project = result.scalar_one_or_none()
            
            return project.to_dict() if project else None
            
        except Exception as e:
            logger.error(f"Error fetching project {project_id} for user {user_id}: {str(e)}")
            return None
