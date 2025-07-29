"""
Pinned Project Model

This module defines the SQLAlchemy model for managing user-pinned GitHub projects
in the CodegenCICD dashboard. It provides persistent storage for project metadata
and user preferences.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base


class PinnedProject(Base):
    """
    Model for storing user-pinned GitHub projects.
    
    This model maintains the relationship between users and their pinned projects,
    storing essential metadata for dashboard display and management.
    """
    __tablename__ = "pinned_projects"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to users table
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # GitHub repository information
    github_repo_name = Column(String(255), nullable=False, index=True)
    github_repo_url = Column(String(500), nullable=False)
    github_owner = Column(String(255), nullable=False)
    
    # Display customization
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Metadata
    pinned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="pinned_projects")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'github_repo_name', name='unique_user_repo'),
    )
    
    def __repr__(self):
        return f"<PinnedProject(id={self.id}, user_id={self.user_id}, repo='{self.github_repo_name}')>"
    
    def to_dict(self):
        """Convert model instance to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": str(self.user_id),
            "github_repo_name": self.github_repo_name,
            "github_repo_url": self.github_repo_url,
            "github_owner": self.github_owner,
            "display_name": self.display_name or self.github_repo_name,
            "description": self.description,
            "pinned_at": self.pinned_at.isoformat() if self.pinned_at else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_github_repo(cls, user_id, repo_data: dict, display_name: str = None):
        """
        Create a PinnedProject instance from GitHub repository data.
        
        Args:
            user_id: ID of the user pinning the project
            repo_data: Dictionary containing GitHub repository information
            display_name: Optional custom display name
            
        Returns:
            PinnedProject instance ready for database insertion
        """
        return cls(
            user_id=user_id,
            github_repo_name=repo_data.get("name", ""),
            github_repo_url=repo_data.get("html_url", ""),
            github_owner=repo_data.get("owner", {}).get("login", ""),
            display_name=display_name,
            description=repo_data.get("description", "")
        )
