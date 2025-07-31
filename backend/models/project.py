"""
Project models for persistent storage
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Dict, Any, Optional, List
import json
from .base import Base


class Project(Base):
    """Project model for storing GitHub project configurations"""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    github_id = Column(Integer, unique=True, index=True)  # GitHub repo ID
    name = Column(String(255), nullable=False, index=True)
    full_name = Column(String(500), nullable=False)  # owner/repo
    description = Column(Text)
    github_owner = Column(String(255), nullable=False)
    github_repo = Column(String(255), nullable=False)
    github_url = Column(String(500), nullable=False)
    default_branch = Column(String(100), default="main")
    
    # Webhook configuration
    webhook_url = Column(String(500))
    webhook_active = Column(Boolean, default=False)
    webhook_secret = Column(String(255))
    
    # Project settings
    auto_confirm_plans = Column(Boolean, default=False)
    auto_merge_validated_pr = Column(Boolean, default=False)
    planning_statement = Column(Text)
    repository_rules = Column(Text)
    
    # Setup commands
    setup_commands = Column(Text)
    setup_branch = Column(String(100))
    
    # Status and metadata
    is_active = Column(Boolean, default=True)
    pinned_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    secrets = relationship("ProjectSecret", back_populates="project", cascade="all, delete-orphan")
    agent_runs = relationship("ProjectAgentRun", back_populates="project", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "github_id": self.github_id,
            "name": self.name,
            "full_name": self.full_name,
            "description": self.description,
            "github_owner": self.github_owner,
            "github_repo": self.github_repo,
            "github_url": self.github_url,
            "default_branch": self.default_branch,
            "webhook_url": self.webhook_url,
            "webhook_active": self.webhook_active,
            "auto_confirm_plans": self.auto_confirm_plans,
            "auto_merge_validated_pr": self.auto_merge_validated_pr,
            "planning_statement": self.planning_statement,
            "repository_rules": self.repository_rules,
            "setup_commands": self.setup_commands,
            "setup_branch": self.setup_branch,
            "is_active": self.is_active,
            "pinned_at": self.pinned_at.isoformat() if self.pinned_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "has_repository_rules": bool(self.repository_rules and self.repository_rules.strip()),
            "has_setup_commands": bool(self.setup_commands and self.setup_commands.strip()),
            "has_planning_statement": bool(self.planning_statement and self.planning_statement.strip()),
            "secrets_count": len(self.secrets) if self.secrets else 0,
        }


class ProjectSecret(Base):
    """Project environment variables/secrets"""
    __tablename__ = "project_secrets"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False)  # Should be encrypted in production
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="secrets")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "key": self.key,
            "value": self.value,  # In production, this should be masked
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ProjectAgentRun(Base):
    """Agent runs associated with projects"""
    __tablename__ = "project_agent_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    codegen_run_id = Column(Integer, index=True)  # ID from Codegen API
    
    # Run details
    target_text = Column(Text, nullable=False)
    status = Column(String(50), default="pending")  # pending, running, completed, failed, cancelled
    run_type = Column(String(50), default="regular")  # regular, plan, pr
    
    # Response data
    response_data = Column(JSON)
    pr_number = Column(Integer)
    pr_url = Column(String(500))
    
    # Validation
    validation_status = Column(String(50))  # pending, running, passed, failed
    validation_logs = Column(JSON)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="agent_runs")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "codegen_run_id": self.codegen_run_id,
            "target_text": self.target_text,
            "status": self.status,
            "run_type": self.run_type,
            "response_data": self.response_data,
            "pr_number": self.pr_number,
            "pr_url": self.pr_url,
            "validation_status": self.validation_status,
            "validation_logs": self.validation_logs,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


