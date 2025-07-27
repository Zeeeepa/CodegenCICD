"""
Project-related database models
"""
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, Text, Boolean, JSON, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel


class Project(BaseModel):
    """Project model representing a GitHub repository and its CI/CD configuration"""
    __tablename__ = "projects"
    
    # Basic project information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    
    # GitHub repository information
    github_owner = Column(String(255), nullable=False)
    github_repo = Column(String(255), nullable=False)
    github_branch = Column(String(255), default="main", nullable=False)
    github_url = Column(String(500), nullable=False)
    
    # Webhook configuration
    webhook_url = Column(String(500))
    webhook_secret = Column(String(255))
    webhook_active = Column(Boolean, default=True, nullable=False)
    
    # Project status and settings
    is_active = Column(Boolean, default=True, nullable=False)
    auto_merge_enabled = Column(Boolean, default=False, nullable=False)
    auto_merge_threshold = Column(Integer, default=80)  # Confidence threshold for auto-merge
    
    # Configuration tier (basic, intermediate, advanced)
    config_tier = Column(String(50), default="basic", nullable=False)
    
    # Validation settings
    validation_enabled = Column(Boolean, default=True, nullable=False)
    grainchain_enabled = Column(Boolean, default=True, nullable=False)
    web_eval_enabled = Column(Boolean, default=True, nullable=False)
    graph_sitter_enabled = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    # Relationships
    configurations = relationship("ProjectConfiguration", back_populates="project", cascade="all, delete-orphan")
    secrets = relationship("ProjectSecret", back_populates="project", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="project", cascade="all, delete-orphan")
    validation_runs = relationship("ValidationRun", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Project(name={self.name}, github={self.github_owner}/{self.github_repo})>"
    
    @property
    def full_github_name(self) -> str:
        """Get full GitHub repository name"""
        return f"{self.github_owner}/{self.github_repo}"
    
    @property
    def github_clone_url(self) -> str:
        """Get GitHub clone URL"""
        return f"https://github.com/{self.github_owner}/{self.github_repo}.git"
    
    def get_configuration(self, config_type: str) -> Optional["ProjectConfiguration"]:
        """Get specific configuration by type"""
        for config in self.configurations:
            if config.config_type == config_type:
                return config
        return None
    
    def get_secret(self, secret_name: str) -> Optional["ProjectSecret"]:
        """Get specific secret by name"""
        for secret in self.secrets:
            if secret.name == secret_name:
                return secret
        return None


class ProjectConfiguration(BaseModel):
    """Project configuration for different aspects (repository rules, setup commands, etc.)"""
    __tablename__ = "project_configurations"
    
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    
    # Configuration type (repository_rules, setup_commands, planning_statement, etc.)
    config_type = Column(String(100), nullable=False, index=True)
    
    # Configuration content
    content = Column(Text, nullable=False)
    
    # Configuration metadata
    is_active = Column(Boolean, default=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    metadata = Column(JSON, default=dict)
    
    # Relationships
    project = relationship("Project", back_populates="configurations")
    
    def __repr__(self) -> str:
        return f"<ProjectConfiguration(project_id={self.project_id}, type={self.config_type})>"


class ProjectSecret(BaseModel):
    """Encrypted secrets for projects"""
    __tablename__ = "project_secrets"
    
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    
    # Secret information
    name = Column(String(255), nullable=False, index=True)
    encrypted_value = Column(Text, nullable=False)  # Encrypted with Fernet
    description = Column(Text)
    
    # Secret metadata
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(String(50))  # ISO timestamp as string
    metadata = Column(JSON, default=dict)
    
    # Relationships
    project = relationship("Project", back_populates="secrets")
    
    def __repr__(self) -> str:
        return f"<ProjectSecret(project_id={self.project_id}, name={self.name})>"

