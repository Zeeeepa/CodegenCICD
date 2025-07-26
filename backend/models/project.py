"""
Project model for GitHub repository management
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
    
    # GitHub repository information
    github_owner = Column(String(255), nullable=False)
    github_repo = Column(String(255), nullable=False)
    full_name = Column(String(511), nullable=False, unique=True, index=True)  # owner/repo
    default_branch = Column(String(255), default="main")
    
    # Repository URLs
    clone_url = Column(String(500), nullable=True)
    html_url = Column(String(500), nullable=True)
    
    # Webhook configuration
    webhook_url = Column(String(500), nullable=True)
    webhook_secret = Column(String(255), nullable=True)
    webhook_id = Column(Integer, nullable=True)
    
    # Project settings
    auto_merge_enabled = Column(Boolean, default=False)
    auto_confirm_plan = Column(Boolean, default=False)
    validation_enabled = Column(Boolean, default=True)
    
    # Repository rules and configuration
    repository_rules = Column(Text, nullable=True)
    planning_statement = Column(Text, nullable=True)
    setup_commands = Column(Text, nullable=True)
    
    # Project status
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
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
        return f"<Project(id={self.id}, name='{self.name}', full_name='{self.full_name}')>"
    
    @property
    def github_url(self) -> str:
        """Get GitHub repository URL"""
        return f"https://github.com/{self.full_name}"
    
    @property
    def has_repository_rules(self) -> bool:
        """Check if project has repository rules configured"""
        return bool(self.repository_rules and self.repository_rules.strip())
    
    @property
    def has_setup_commands(self) -> bool:
        """Check if project has setup commands configured"""
        return bool(self.setup_commands and self.setup_commands.strip())
    
    @property
    def has_planning_statement(self) -> bool:
        """Check if project has planning statement configured"""
        return bool(self.planning_statement and self.planning_statement.strip())
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get validation configuration for this project"""
        return {
            "grainchain_enabled": True,
            "graph_sitter_enabled": True,
            "web_eval_agent_enabled": True,
            "auto_merge_enabled": self.auto_merge_enabled,
            "validation_enabled": self.validation_enabled
        }
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = func.now()
        self.updated_at = func.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert project to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "github_owner": self.github_owner,
            "github_repo": self.github_repo,
            "full_name": self.full_name,
            "default_branch": self.default_branch,
            "clone_url": self.clone_url,
            "html_url": self.html_url,
            "github_url": self.github_url,
            "webhook_url": self.webhook_url,
            "webhook_id": self.webhook_id,
            "auto_merge_enabled": self.auto_merge_enabled,
            "auto_confirm_plan": self.auto_confirm_plan,
            "validation_enabled": self.validation_enabled,
            "repository_rules": self.repository_rules,
            "planning_statement": self.planning_statement,
            "setup_commands": self.setup_commands,
            "is_active": self.is_active,
            "has_repository_rules": self.has_repository_rules,
            "has_setup_commands": self.has_setup_commands,
            "has_planning_statement": self.has_planning_statement,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_github_repo(cls, repo_data: Dict[str, Any], **kwargs) -> "Project":
        """Create project from GitHub repository data"""
        return cls(
            name=repo_data.get("name", ""),
            description=repo_data.get("description", ""),
            github_owner=repo_data.get("owner", {}).get("login", ""),
            github_repo=repo_data.get("name", ""),
            full_name=repo_data.get("full_name", ""),
            default_branch=repo_data.get("default_branch", "main"),
            clone_url=repo_data.get("clone_url", ""),
            html_url=repo_data.get("html_url", ""),
            **kwargs
        )

