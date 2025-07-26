"""
Validation models for tracking validation pipeline execution
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Enum, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database import Base
from typing import Optional, Dict, Any, List
from enum import Enum as PyEnum
from datetime import datetime


class ValidationStatus(PyEnum):
    """Validation status enumeration"""
    NOT_STARTED = "not_started"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class ValidationStepType(PyEnum):
    """Validation step type enumeration"""
    SNAPSHOT_CREATION = "snapshot_creation"
    CODE_CLONING = "code_cloning"
    DEPLOYMENT = "deployment"
    GRAINCHAIN_VALIDATION = "grainchain_validation"
    GRAPH_SITTER_ANALYSIS = "graph_sitter_analysis"
    WEB_EVAL_TESTING = "web_eval_testing"
    MERGE_PREPARATION = "merge_preparation"


class ValidationRun(Base):
    __tablename__ = "validation_runs"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    agent_run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=True, index=True)
    
    # Validation details
    pr_number = Column(Integer, nullable=True)
    pr_url = Column(String(500), nullable=True)
    pr_branch = Column(String(255), nullable=True)
    commit_sha = Column(String(40), nullable=True)
    
    # Status and progress
    status = Column(Enum(ValidationStatus), default=ValidationStatus.NOT_STARTED, index=True)
    progress_percentage = Column(Integer, default=0)
    current_step = Column(String(255), nullable=True)
    
    # Results
    overall_result = Column(Boolean, nullable=True)  # True = passed, False = failed, None = not completed
    error_message = Column(Text, nullable=True)
    
    # Validation configuration
    validation_config = Column(JSON, nullable=True)  # Which validations to run
    
    # Snapshot information
    snapshot_id = Column(String(255), nullable=True)
    snapshot_url = Column(String(500), nullable=True)
    
    # Deployment information
    deployment_url = Column(String(500), nullable=True)
    deployment_logs = Column(Text, nullable=True)
    
    # Auto-merge settings
    auto_merge_enabled = Column(Boolean, default=False)
    merge_ready = Column(Boolean, default=False)
    merge_url = Column(String(500), nullable=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="validation_runs")
    agent_run = relationship("AgentRun", back_populates="validation_runs")
    steps = relationship("ValidationStep", back_populates="validation_run", cascade="all, delete-orphan")
    results = relationship("ValidationResult", back_populates="validation_run", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ValidationRun(id={self.id}, project_id={self.project_id}, status='{self.status.value}')>"
    
    @property
    def is_completed(self) -> bool:
        """Check if validation run is completed"""
        return self.status in [ValidationStatus.COMPLETED, ValidationStatus.FAILED, ValidationStatus.CANCELLED]
    
    @property
    def is_running(self) -> bool:
        """Check if validation run is currently running"""
        return self.status == ValidationStatus.RUNNING
    
    @property
    def duration(self) -> Optional[float]:
        """Get validation duration in seconds"""
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()
    
    @property
    def passed_steps(self) -> int:
        """Get number of passed validation steps"""
        return len([step for step in self.steps if step.status == ValidationStatus.COMPLETED])
    
    @property
    def failed_steps(self) -> int:
        """Get number of failed validation steps"""
        return len([step for step in self.steps if step.status == ValidationStatus.FAILED])
    
    def start_validation(self):
        """Start the validation run"""
        self.status = ValidationStatus.RUNNING
        self.started_at = func.now()
        self.updated_at = func.now()
    
    def complete_validation(self, success: bool, error_message: str = None):
        """Complete the validation run"""
        self.status = ValidationStatus.COMPLETED if success else ValidationStatus.FAILED
        self.overall_result = success
        self.completed_at = func.now()
        self.progress_percentage = 100
        if error_message:
            self.error_message = error_message
        self.updated_at = func.now()
    
    def update_progress(self, percentage: int, step: str = None):
        """Update validation progress"""
        self.progress_percentage = max(0, min(100, percentage))
        if step:
            self.current_step = step
        self.updated_at = func.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert validation run to dictionary for API responses"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "agent_run_id": self.agent_run_id,
            "pr_number": self.pr_number,
            "pr_url": self.pr_url,
            "pr_branch": self.pr_branch,
            "commit_sha": self.commit_sha,
            "status": self.status.value,
            "progress_percentage": self.progress_percentage,
            "current_step": self.current_step,
            "overall_result": self.overall_result,
            "error_message": self.error_message,
            "validation_config": self.validation_config,
            "snapshot_id": self.snapshot_id,
            "snapshot_url": self.snapshot_url,
            "deployment_url": self.deployment_url,
            "auto_merge_enabled": self.auto_merge_enabled,
            "merge_ready": self.merge_ready,
            "merge_url": self.merge_url,
            "is_completed": self.is_completed,
            "is_running": self.is_running,
            "duration": self.duration,
            "passed_steps": self.passed_steps,
            "failed_steps": self.failed_steps,
            "metadata": self.metadata,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ValidationStep(Base):
    __tablename__ = "validation_steps"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to validation run
    validation_run_id = Column(Integer, ForeignKey("validation_runs.id"), nullable=False, index=True)
    
    # Step details
    step_type = Column(Enum(ValidationStepType), nullable=False, index=True)
    step_name = Column(String(255), nullable=False)
    step_order = Column(Integer, nullable=False)
    
    # Status and results
    status = Column(Enum(ValidationStatus), default=ValidationStatus.NOT_STARTED, index=True)
    result = Column(Boolean, nullable=True)  # True = passed, False = failed, None = not completed
    error_message = Column(Text, nullable=True)
    
    # Execution details
    command = Column(Text, nullable=True)
    output = Column(Text, nullable=True)
    exit_code = Column(Integer, nullable=True)
    
    # Timing
    duration_seconds = Column(Float, nullable=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    validation_run = relationship("ValidationRun", back_populates="steps")
    
    def __repr__(self):
        return f"<ValidationStep(id={self.id}, step_type='{self.step_type.value}', status='{self.status.value}')>"
    
    def start_step(self):
        """Start the validation step"""
        self.status = ValidationStatus.RUNNING
        self.started_at = func.now()
        self.updated_at = func.now()
    
    def complete_step(self, success: bool, error_message: str = None, 
                     output: str = None, exit_code: int = None):
        """Complete the validation step"""
        self.status = ValidationStatus.COMPLETED if success else ValidationStatus.FAILED
        self.result = success
        self.completed_at = func.now()
        
        if error_message:
            self.error_message = error_message
        if output:
            self.output = output
        if exit_code is not None:
            self.exit_code = exit_code
        
        # Calculate duration
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        
        self.updated_at = func.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert validation step to dictionary for API responses"""
        return {
            "id": self.id,
            "validation_run_id": self.validation_run_id,
            "step_type": self.step_type.value,
            "step_name": self.step_name,
            "step_order": self.step_order,
            "status": self.status.value,
            "result": self.result,
            "error_message": self.error_message,
            "command": self.command,
            "output": self.output,
            "exit_code": self.exit_code,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ValidationResult(Base):
    __tablename__ = "validation_results"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to validation run
    validation_run_id = Column(Integer, ForeignKey("validation_runs.id"), nullable=False, index=True)
    
    # Result details
    validator_name = Column(String(255), nullable=False, index=True)  # e.g., "grainchain", "graph_sitter", "web_eval_agent"
    result_type = Column(String(100), nullable=False)  # e.g., "quality_score", "test_results", "security_scan"
    
    # Result data
    passed = Column(Boolean, nullable=False)
    score = Column(Float, nullable=True)  # Optional numeric score
    details = Column(JSON, nullable=True)  # Detailed results
    
    # Issues found
    issues_count = Column(Integer, default=0)
    critical_issues = Column(Integer, default=0)
    warning_issues = Column(Integer, default=0)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    validation_run = relationship("ValidationRun", back_populates="results")
    
    def __repr__(self):
        return f"<ValidationResult(id={self.id}, validator='{self.validator_name}', passed={self.passed})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary for API responses"""
        return {
            "id": self.id,
            "validation_run_id": self.validation_run_id,
            "validator_name": self.validator_name,
            "result_type": self.result_type,
            "passed": self.passed,
            "score": self.score,
            "details": self.details,
            "issues_count": self.issues_count,
            "critical_issues": self.critical_issues,
            "warning_issues": self.warning_issues,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

