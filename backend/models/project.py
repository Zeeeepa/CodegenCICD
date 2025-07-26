"""
Project model for managing GitHub repositories and their configurations
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database import Base
from typing import Optional, Dict, Any, List
from datetime import datetime


class Project(Base):
    __tablename__ = "projects"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic project information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # GitHub information
    github_owner = Column(String(255), nullable=False, index=True)
    github_repo = Column(String(255), nullable=False, index=True)
    github_url = Column(String(500), nullable=False)
    default_branch = Column(String(100), default="main")
    
    # Webhook configuration
    webhook_url = Column(String(500), nullable=True)
    webhook_secret = Column(String(255), nullable=True)
    webhook_active = Column(Boolean, default=True)
    
    # Project settings
    auto_confirm_plans = Column(Boolean, default=False)
    auto_merge_enabled = Column(Boolean, default=False)
    planning_statement = Column(Text, nullable=True)
    repository_rules = Column(Text, nullable=True)
    
    # Setup commands
    setup_commands = Column(Text, nullable=True)
    setup_branch = Column(String(100), nullable=True)
    
    # Status and metadata
    is_active = Column(Boolean, default=True, index=True)
    last_activity = Column(DateTime(timezone=True), nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # Validation settings
    validation_enabled = Column(Boolean, default=True)
    grainchain_enabled = Column(Boolean, default=True)
    graph_sitter_enabled = Column(Boolean, default=True)
    web_eval_agent_enabled = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    agent_runs = relationship("AgentRun", back_populates="project", cascade="all, delete-orphan")
    configurations = relationship("ProjectConfiguration", back_populates="project", cascade="all, delete-orphan")
    secrets = relationship("ProjectSecret", back_populates="project", cascade="all, delete-orphan")
    validation_runs = relationship("ValidationRun", back_populates="project", cascade="all, delete-orphan")
    webhook_events = relationship("WebhookEvent", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}', github='{self.github_owner}/{self.github_repo}')>"
    
    @property
    def full_name(self) -> str:
        """Get full GitHub repository name"""
        return f"{self.github_owner}/{self.github_repo}"
    
    @property
    def is_configured(self) -> bool:
        """Check if project is properly configured"""
        return bool(
            self.github_owner and 
            self.github_repo and 
            self.webhook_url
        )
    
    @property
    def has_recent_activity(self) -> bool:
        """Check if project has recent activity (within 24 hours)"""
        if not self.last_activity:
            return False
        
        from datetime import timedelta
        return (datetime.utcnow() - self.last_activity) < timedelta(hours=24)
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = func.now()
    
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
            "webhook_url": self.webhook_url,
            "webhook_active": self.webhook_active,
            "auto_confirm_plans": self.auto_confirm_plans,
            "auto_merge_enabled": self.auto_merge_enabled,
            "planning_statement": self.planning_statement,
            "repository_rules": self.repository_rules,
            "setup_commands": self.setup_commands,
            "setup_branch": self.setup_branch,
            "is_active": self.is_active,
            "is_configured": self.is_configured,
            "has_recent_activity": self.has_recent_activity,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "validation_enabled": self.validation_enabled,
            "grainchain_enabled": self.grainchain_enabled,
            "graph_sitter_enabled": self.graph_sitter_enabled,
            "web_eval_agent_enabled": self.web_eval_agent_enabled,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_validation_config(self) -> Dict[str, bool]:
        """Get validation configuration for this project"""
        return {
            "validation_enabled": self.validation_enabled,
            "grainchain_enabled": self.grainchain_enabled,
            "graph_sitter_enabled": self.graph_sitter_enabled,
            "web_eval_agent_enabled": self.web_eval_agent_enabled
        }
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update project from dictionary data"""
        updatable_fields = [
            "name", "description", "default_branch", "auto_confirm_plans",
            "auto_merge_enabled", "planning_statement", "repository_rules",
            "setup_commands", "setup_branch", "is_active", "validation_enabled",
            "grainchain_enabled", "graph_sitter_enabled", "web_eval_agent_enabled",
            "metadata"
        ]
        
        for field in updatable_fields:
            if field in data:
                setattr(self, field, data[field])
        
        self.updated_at = func.now()

