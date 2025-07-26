"""
Project model with comprehensive configuration support
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database import Base
from typing import Optional, Dict, Any, List
from enum import Enum as PyEnum


class ProjectStatus(PyEnum):
    """Project status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    MAINTENANCE = "maintenance"


class Project(Base):
    __tablename__ = "projects"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic project information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # GitHub integration
    github_owner = Column(String(255), nullable=False)
    github_repo = Column(String(255), nullable=False)
    github_url = Column(String(500), nullable=False)
    default_branch = Column(String(255), default="main")
    
    # Webhook configuration
    webhook_url = Column(String(500), nullable=True)
    webhook_secret = Column(String(255), nullable=True)
    webhook_events = Column(JSON, default=list)  # List of events to listen for
    
    # Project status and settings
    status = Column(String(50), default=ProjectStatus.ACTIVE.value, index=True)
    is_public = Column(Boolean, default=True)
    
    # Auto-configuration flags
    auto_confirm_plans = Column(Boolean, default=False)
    auto_merge_validated_prs = Column(Boolean, default=False)
    
    # Repository rules and configuration
    repository_rules = Column(Text, nullable=True)  # Custom rules for the agent
    planning_statement = Column(Text, nullable=True)  # Default planning statement
    setup_commands = Column(Text, nullable=True)  # Commands to run in sandbox
    
    # Advanced settings (JSON for flexibility)
    settings = Column(JSON, default=dict)
    metadata = Column(JSON, default=dict)
    
    # Statistics and metrics
    total_agent_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)
    total_prs_created = Column(Integer, default=0)
    total_prs_merged = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    agent_runs = relationship("AgentRun", back_populates="project", cascade="all, delete-orphan")
    configurations = relationship("ProjectConfiguration", back_populates="project", cascade="all, delete-orphan")
    secrets = relationship("ProjectSecret", back_populates="project", cascade="all, delete-orphan")
    validation_pipelines = relationship("ValidationPipeline", back_populates="project", cascade="all, delete-orphan")
    webhook_events = relationship("WebhookEvent", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}', status='{self.status}')>"
    
    @property
    def full_name(self) -> str:
        """Get full GitHub repository name"""
        return f"{self.github_owner}/{self.github_repo}"
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate of agent runs"""
        if self.total_agent_runs == 0:
            return 0.0
        return (self.successful_runs / self.total_agent_runs) * 100
    
    @property
    def pr_merge_rate(self) -> float:
        """Calculate PR merge rate"""
        if self.total_prs_created == 0:
            return 0.0
        return (self.total_prs_merged / self.total_prs_created) * 100
    
    @property
    def is_active(self) -> bool:
        """Check if project is active"""
        return self.status == ProjectStatus.ACTIVE.value
    
    @property
    def has_repository_rules(self) -> bool:
        """Check if project has custom repository rules"""
        return bool(self.repository_rules and self.repository_rules.strip())
    
    @property
    def has_setup_commands(self) -> bool:
        """Check if project has setup commands"""
        return bool(self.setup_commands and self.setup_commands.strip())
    
    @property
    def has_planning_statement(self) -> bool:
        """Check if project has custom planning statement"""
        return bool(self.planning_statement and self.planning_statement.strip())
    
    def get_webhook_events(self) -> List[str]:
        """Get list of webhook events"""
        if isinstance(self.webhook_events, list):
            return self.webhook_events
        return ["pull_request", "push", "issues"]  # Default events
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a project setting"""
        if not isinstance(self.settings, dict):
            return default
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> None:
        """Set a project setting"""
        if not isinstance(self.settings, dict):
            self.settings = {}
        self.settings[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get project metadata"""
        if not isinstance(self.metadata, dict):
            return default
        return self.metadata.get(key, default)
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set project metadata"""
        if not isinstance(self.metadata, dict):
            self.metadata = {}
        self.metadata[key] = value
    
    def update_statistics(self, agent_run_success: Optional[bool] = None, 
                         pr_created: bool = False, pr_merged: bool = False) -> None:
        """Update project statistics"""
        if agent_run_success is not None:
            self.total_agent_runs += 1
            if agent_run_success:
                self.successful_runs += 1
            else:
                self.failed_runs += 1
        
        if pr_created:
            self.total_prs_created += 1
        
        if pr_merged:
            self.total_prs_merged += 1
        
        self.last_activity_at = func.now()
    
    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Convert project to dictionary for API responses"""
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "github_owner": self.github_owner,
            "github_repo": self.github_repo,
            "github_url": self.github_url,
            "full_name": self.full_name,
            "default_branch": self.default_branch,
            "status": self.status,
            "is_public": self.is_public,
            "is_active": self.is_active,
            
            # Configuration flags
            "auto_confirm_plans": self.auto_confirm_plans,
            "auto_merge_validated_prs": self.auto_merge_validated_prs,
            
            # Configuration presence indicators
            "has_repository_rules": self.has_repository_rules,
            "has_setup_commands": self.has_setup_commands,
            "has_planning_statement": self.has_planning_statement,
            
            # Statistics
            "total_agent_runs": self.total_agent_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "success_rate": self.success_rate,
            "total_prs_created": self.total_prs_created,
            "total_prs_merged": self.total_prs_merged,
            "pr_merge_rate": self.pr_merge_rate,
            
            # Settings and metadata
            "settings": self.settings,
            "metadata": self.metadata,
            
            # Timestamps
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
        }
        
        # Include configuration details if requested
        if include_secrets:
            data.update({
                "repository_rules": self.repository_rules,
                "planning_statement": self.planning_statement,
                "setup_commands": self.setup_commands,
                "webhook_url": self.webhook_url,
                "webhook_events": self.get_webhook_events(),
            })
        
        return data
    
    @classmethod
    def create_from_github_url(cls, github_url: str, name: Optional[str] = None, 
                              description: Optional[str] = None) -> "Project":
        """Create project from GitHub URL"""
        # Parse GitHub URL to extract owner and repo
        # Example: https://github.com/owner/repo -> owner, repo
        parts = github_url.rstrip('/').split('/')
        if len(parts) < 2:
            raise ValueError("Invalid GitHub URL format")
        
        github_repo = parts[-1]
        github_owner = parts[-2]
        
        return cls(
            name=name or github_repo,
            description=description,
            github_owner=github_owner,
            github_repo=github_repo,
            github_url=github_url,
            status=ProjectStatus.ACTIVE.value
        )

