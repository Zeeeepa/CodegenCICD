"""
Project model for GitHub project management
"""
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base


class Project(Base):
    """GitHub project model"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    github_id = Column(Integer, unique=True, index=True)  # GitHub repository ID
    name = Column(String(255), nullable=False, index=True)
    full_name = Column(String(500), nullable=False)  # owner/repo
    description = Column(Text)
    github_owner = Column(String(255), nullable=False)
    github_repo = Column(String(255), nullable=False)
    github_branch = Column(String(255), default="main")
    github_url = Column(String(500), nullable=False)
    
    # Webhook configuration
    webhook_active = Column(Boolean, default=False)
    webhook_url = Column(String(500))
    webhook_secret = Column(String(255))
    
    # Project settings
    auto_merge_enabled = Column(Boolean, default=False)
    auto_confirm_plans = Column(Boolean, default=False)
    auto_merge_threshold = Column(Integer, default=80)  # Validation score threshold
    
    # Status
    is_active = Column(Boolean, default=True)
    status = Column(String(50), default="active")  # active, paused, archived
    validation_enabled = Column(Boolean, default=True)
    
    # Visual indicators for settings
    has_repository_rules = Column(Boolean, default=False)
    has_setup_commands = Column(Boolean, default=False)
    has_secrets = Column(Boolean, default=False)
    has_planning_statement = Column(Boolean, default=False)
    
    # Statistics
    total_runs = Column(Integer, default=0)
    success_rate = Column(Integer, default=0)  # Percentage
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    settings = relationship("ProjectSettings", back_populates="project", uselist=False)
    agent_runs = relationship("AgentRun", back_populates="project")
    validation_runs = relationship("ValidationRun", back_populates="project")
    
    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}', owner='{self.github_owner}')>"


class ProjectSettings(Base):
    """Project-specific settings"""
    __tablename__ = "project_settings"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), unique=True)
    
    # Repository rules
    repository_rules = Column(Text)  # Additional rules for the agent
    
    # Setup commands
    setup_commands = Column(Text)  # Commands to run in sandbox
    setup_branch = Column(String(255), default="main")  # Branch for setup commands
    
    # Planning statement
    planning_statement = Column(Text)  # Pre-prompt for agent runs
    
    # Environment variables/secrets (encrypted)
    secrets = Column(JSON)  # Encrypted key-value pairs
    
    # Validation settings
    validation_timeout = Column(Integer, default=1800)  # 30 minutes
    max_validation_retries = Column(Integer, default=3)
    
    # Deployment settings
    deployment_commands = Column(Text)  # Commands for deployment validation
    health_check_url = Column(String(500))  # URL to check if deployment is healthy
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="settings")
    
    def __repr__(self):
        return f"<ProjectSettings(id={self.id}, project_id={self.project_id})>"


class ValidationRun(Base):
    """Validation run tracking"""
    __tablename__ = "validation_runs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    agent_run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=True)
    
    # PR information
    pr_number = Column(Integer)
    pr_url = Column(String(500))
    pr_branch = Column(String(255))
    commit_sha = Column(String(255))
    
    # Validation status
    status = Column(String(50), default="pending")  # pending, running, success, failed, cancelled
    validation_score = Column(Integer, default=0)  # 0-100
    
    # Validation steps
    snapshot_created = Column(Boolean, default=False)
    code_cloned = Column(Boolean, default=False)
    deployment_successful = Column(Boolean, default=False)
    ui_tests_passed = Column(Boolean, default=False)
    
    # Results
    deployment_logs = Column(Text)
    validation_logs = Column(Text)
    error_context = Column(Text)
    
    # Retry tracking
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    project = relationship("Project", back_populates="validation_runs")
    agent_run = relationship("AgentRun", back_populates="validation_runs")
    
    def __repr__(self):
        return f"<ValidationRun(id={self.id}, project_id={self.project_id}, status='{self.status}')>"

