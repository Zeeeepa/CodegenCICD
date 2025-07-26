"""
Project model for storing GitHub repository information and settings
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database import Base
from typing import Optional, Dict, Any
import uuid

class Project(Base):
    __tablename__ = "projects"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # GitHub repository information
    github_owner = Column(String(255), nullable=False, index=True)
    github_repo = Column(String(255), nullable=False, index=True)
    github_url = Column(String(500), nullable=False)
    default_branch = Column(String(100), default="main")
    
    # Project metadata
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Webhook configuration
    webhook_url = Column(String(500), nullable=True)
    webhook_secret = Column(String(255), nullable=True)
    webhook_active = Column(Boolean, default=False)
    
    # Project settings
    auto_confirm_plan = Column(Boolean, default=False)
    auto_merge_validated_pr = Column(Boolean, default=False)
    
    # Planning statement (custom prompt prefix)
    planning_statement = Column(Text, nullable=True)
    
    # Repository rules
    repository_rules = Column(Text, nullable=True)
    
    # Setup commands and branch
    setup_commands = Column(Text, nullable=True)
    setup_branch = Column(String(100), nullable=True)
    
    # Status and metadata
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    agent_runs = relationship("AgentRun", back_populates="project", cascade="all, delete-orphan")
    configurations = relationship("ProjectConfiguration", back_populates="project", cascade="all, delete-orphan")
    secrets = relationship("ProjectSecret", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}', repo='{self.github_owner}/{self.github_repo}')>"
    
    @property
    def full_name(self) -> str:
        """Get full GitHub repository name"""
        return f"{self.github_owner}/{self.github_repo}"
    
    @property
    def has_custom_rules(self) -> bool:
        """Check if project has custom repository rules"""
        return bool(self.repository_rules and self.repository_rules.strip())
    
    @property
    def has_setup_commands(self) -> bool:
        """Check if project has setup commands configured"""
        return bool(self.setup_commands and self.setup_commands.strip())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert project to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "github_owner": self.github_owner,
            "github_repo": self.github_repo,
            "github_url": self.github_url,
            "full_name": self.full_name,
            "default_branch": self.default_branch,
            "webhook_active": self.webhook_active,
            "auto_confirm_plan": self.auto_confirm_plan,
            "auto_merge_validated_pr": self.auto_merge_validated_pr,
            "planning_statement": self.planning_statement,
            "has_custom_rules": self.has_custom_rules,
            "has_setup_commands": self.has_setup_commands,
            "setup_branch": self.setup_branch,
            "is_active": self.is_active,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
