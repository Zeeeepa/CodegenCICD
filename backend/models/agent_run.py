"""
Agent run models for tracking Codegen API interactions and logs
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database import Base
from typing import Optional, Dict, Any, List
from enum import Enum as PyEnum

class AgentRunStatus(PyEnum):
    """Agent run status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AgentRunType(PyEnum):
    """Agent run type enumeration"""
    REGULAR = "regular"
    PLAN = "plan"
    PR = "pr"

class ValidationStatus(PyEnum):
    """Validation status enumeration"""
    NOT_STARTED = "not_started"
    SNAPSHOT_CREATING = "snapshot_creating"
    CLONING = "cloning"
    DEPLOYING = "deploying"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"

class AgentRun(Base):
    __tablename__ = "agent_runs"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to project
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    # Codegen API information
    codegen_run_id = Column(Integer, nullable=True, index=True)
    codegen_org_id = Column(Integer, nullable=False)
    
    # Run details
    target_text = Column(Text, nullable=False)  # User's target/goal input
    planning_statement = Column(Text, nullable=True)  # Custom planning statement used
    
    # Status and type
    status = Column(Enum(AgentRunStatus), default=AgentRunStatus.PENDING, index=True)
    run_type = Column(Enum(AgentRunType), default=AgentRunType.REGULAR)
    
    # Results and metadata
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # PR information (if PR was created)
    pr_number = Column(Integer, nullable=True)
    pr_url = Column(String(500), nullable=True)
    pr_branch = Column(String(255), nullable=True)
    
    # Validation information
    validation_status = Column(Enum(ValidationStatus), default=ValidationStatus.NOT_STARTED)
    validation_logs = Column(JSON, nullable=True)
    validation_error = Column(Text, nullable=True)
    
    # Auto-merge settings
    auto_merge_enabled = Column(Boolean, default=False)
    merge_completed = Column(Boolean, default=False)
    merge_url = Column(String(500), nullable=True)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="agent_runs")
    logs = relationship("AgentRunLog", back_populates="agent_run", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AgentRun(id={self.id}, project_id={self.project_id}, status='{self.status.value}')>"
    
    @property
    def is_completed(self) -> bool:
        """Check if agent run is completed"""
        return self.status in [AgentRunStatus.COMPLETED, AgentRunStatus.FAILED, AgentRunStatus.CANCELLED]
    
    @property
    def has_pr(self) -> bool:
        """Check if agent run created a PR"""
        return bool(self.pr_number and self.pr_url)
    
    @property
    def validation_in_progress(self) -> bool:
        """Check if validation is in progress"""
        return self.validation_status not in [ValidationStatus.NOT_STARTED, ValidationStatus.COMPLETED, ValidationStatus.FAILED]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent run to dictionary for API responses"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "codegen_run_id": self.codegen_run_id,
            "codegen_org_id": self.codegen_org_id,
            "target_text": self.target_text,
            "planning_statement": self.planning_statement,
            "status": self.status.value,
            "run_type": self.run_type.value,
            "result": self.result,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "pr_number": self.pr_number,
            "pr_url": self.pr_url,
            "pr_branch": self.pr_branch,
            "validation_status": self.validation_status.value,
            "validation_logs": self.validation_logs,
            "validation_error": self.validation_error,
            "auto_merge_enabled": self.auto_merge_enabled,
            "merge_completed": self.merge_completed,
            "merge_url": self.merge_url,
            "is_completed": self.is_completed,
            "has_pr": self.has_pr,
            "validation_in_progress": self.validation_in_progress,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class AgentRunLog(Base):
    __tablename__ = "agent_run_logs"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to agent run
    agent_run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=False, index=True)
    
    # Log details
    message_type = Column(String(50), nullable=False, index=True)
    thought = Column(Text, nullable=True)
    tool_name = Column(String(100), nullable=True)
    tool_input = Column(JSON, nullable=True)
    tool_output = Column(JSON, nullable=True)
    observation = Column(JSON, nullable=True)
    
    # Metadata
    log_level = Column(String(20), default="INFO")
    source = Column(String(50), default="codegen")  # codegen, validation, system
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    agent_run = relationship("AgentRun", back_populates="logs")
    
    def __repr__(self):
        return f"<AgentRunLog(id={self.id}, agent_run_id={self.agent_run_id}, type='{self.message_type}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log to dictionary for API responses"""
        return {
            "id": self.id,
            "agent_run_id": self.agent_run_id,
            "message_type": self.message_type,
            "thought": self.thought,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_output": self.tool_output,
            "observation": self.observation,
            "log_level": self.log_level,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
