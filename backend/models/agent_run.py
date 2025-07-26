"""
Agent run models for tracking Codegen API interactions and logs
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Enum, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database import Base
from typing import Optional, Dict, Any, List
from enum import Enum as PyEnum
from datetime import datetime


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
    CONTINUATION = "continuation"


class LogLevel(PyEnum):
    """Log level enumeration"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AgentRun(Base):
    __tablename__ = "agent_runs"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to project
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    # Parent run for continuations
    parent_run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=True, index=True)
    
    # Codegen API information
    codegen_run_id = Column(Integer, nullable=True, index=True)
    codegen_org_id = Column(Integer, nullable=False)
    
    # Run details
    target_text = Column(Text, nullable=False)  # User's target/goal input
    planning_statement = Column(Text, nullable=True)  # Custom planning statement used
    
    # Status and type
    status = Column(Enum(AgentRunStatus), default=AgentRunStatus.PENDING, index=True)
    run_type = Column(Enum(AgentRunType), default=AgentRunType.REGULAR)
    
    # Progress tracking
    progress_percentage = Column(Integer, default=0)
    current_step = Column(String(255), nullable=True)
    
    # Results and metadata
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # PR information (if PR was created)
    pr_number = Column(Integer, nullable=True)
    pr_url = Column(String(500), nullable=True)
    pr_branch = Column(String(255), nullable=True)
    pr_title = Column(String(500), nullable=True)
    
    # Auto-merge settings
    auto_merge_enabled = Column(Boolean, default=False)
    merge_completed = Column(Boolean, default=False)
    merge_url = Column(String(500), nullable=True)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="agent_runs")
    parent_run = relationship("AgentRun", remote_side=[id], backref="child_runs")
    logs = relationship("AgentRunLog", back_populates="agent_run", cascade="all, delete-orphan")
    validation_runs = relationship("ValidationRun", back_populates="agent_run", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AgentRun(id={self.id}, project_id={self.project_id}, status='{self.status.value}')>"
    
    @property
    def is_completed(self) -> bool:
        """Check if agent run is completed"""
        return self.status in [AgentRunStatus.COMPLETED, AgentRunStatus.FAILED, AgentRunStatus.CANCELLED]
    
    @property
    def is_running(self) -> bool:
        """Check if agent run is currently running"""
        return self.status == AgentRunStatus.RUNNING
    
    @property
    def has_pr(self) -> bool:
        """Check if agent run created a PR"""
        return bool(self.pr_number and self.pr_url)
    
    @property
    def duration(self) -> Optional[float]:
        """Get agent run duration in seconds"""
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()
    
    def start_run(self):
        """Start the agent run"""
        self.status = AgentRunStatus.RUNNING
        self.started_at = func.now()
        self.updated_at = func.now()
    
    def mark_completed(self, result: str = None):
        """Mark agent run as completed"""
        self.status = AgentRunStatus.COMPLETED
        self.completed_at = func.now()
        self.progress_percentage = 100
        if result:
            self.result = result
        self.updated_at = func.now()
    
    def mark_failed(self, error_message: str):
        """Mark agent run as failed"""
        self.status = AgentRunStatus.FAILED
        self.completed_at = func.now()
        self.error_message = error_message
        self.updated_at = func.now()
    
    def update_progress(self, percentage: int, step: str = None):
        """Update agent run progress"""
        self.progress_percentage = max(0, min(100, percentage))
        if step:
            self.current_step = step
        self.updated_at = func.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent run to dictionary for API responses"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "parent_run_id": self.parent_run_id,
            "codegen_run_id": self.codegen_run_id,
            "codegen_org_id": self.codegen_org_id,
            "target_text": self.target_text,
            "planning_statement": self.planning_statement,
            "status": self.status.value,
            "run_type": self.run_type.value,
            "progress_percentage": self.progress_percentage,
            "current_step": self.current_step,
            "result": self.result,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "pr_number": self.pr_number,
            "pr_url": self.pr_url,
            "pr_branch": self.pr_branch,
            "pr_title": self.pr_title,
            "auto_merge_enabled": self.auto_merge_enabled,
            "merge_completed": self.merge_completed,
            "merge_url": self.merge_url,
            "is_completed": self.is_completed,
            "is_running": self.is_running,
            "has_pr": self.has_pr,
            "duration": self.duration,
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
    level = Column(Enum(LogLevel), nullable=False, index=True)
    message = Column(Text, nullable=False)
    source = Column(String(255), nullable=True)  # e.g., "codegen_api", "validation", "agent_service"
    
    # Optional structured data
    metadata = Column(JSON, nullable=True)
    
    # Step information
    step_name = Column(String(255), nullable=True)
    step_index = Column(Integer, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    agent_run = relationship("AgentRun", back_populates="logs")
    
    def __repr__(self):
        return f"<AgentRunLog(id={self.id}, level='{self.level.value}', message='{self.message[:50]}...')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary for API responses"""
        return {
            "id": self.id,
            "agent_run_id": self.agent_run_id,
            "level": self.level.value,
            "message": self.message,
            "source": self.source,
            "metadata": self.metadata,
            "step_name": self.step_name,
            "step_index": self.step_index,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def create_log(cls, agent_run_id: int, level: LogLevel, message: str, 
                   source: str = None, metadata: Dict[str, Any] = None, 
                   step_name: str = None, step_index: int = None) -> "AgentRunLog":
        """Create a new log entry"""
        return cls(
            agent_run_id=agent_run_id,
            level=level,
            message=message,
            source=source,
            metadata=metadata,
            step_name=step_name,
            step_index=step_index
        )

