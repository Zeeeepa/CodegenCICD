"""
Project model for CodegenCICD Dashboard
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    github_repository = Column(String(255), nullable=False)
    default_branch = Column(String(100), nullable=False, default="main")
    webhook_url = Column(String(500), nullable=True)
    auto_confirm_plan = Column(Boolean, default=False)
    auto_merge_validated_pr = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    configuration = relationship("ProjectConfiguration", back_populates="project", uselist=False)
    agent_runs = relationship("AgentRun", back_populates="project")

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}', repository='{self.github_repository}')>"

    def to_dict(self):
        """Convert project to dictionary for API responses"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "github_repository": self.github_repository,
            "default_branch": self.default_branch,
            "webhook_url": self.webhook_url,
            "auto_confirm_plan": self.auto_confirm_plan,
            "auto_merge_validated_pr": self.auto_merge_validated_pr,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "configuration": self.configuration.to_dict() if self.configuration else None
        }
