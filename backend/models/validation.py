"""
Validation pipeline models for the 7-step validation process
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
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ValidationStepType(PyEnum):
    """Validation step types for the 7-step pipeline"""
    SNAPSHOT_CREATION = "snapshot_creation"
    CODE_CLONE = "code_clone"
    CODE_ANALYSIS = "code_analysis"
    DEPLOYMENT = "deployment"
    DEPLOYMENT_VALIDATION = "deployment_validation"
    UI_TESTING = "ui_testing"
    AUTO_MERGE = "auto_merge"


class ValidationPipeline(Base):
    __tablename__ = "validation_pipelines"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    agent_run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=True, index=True)
    
    # Pipeline information
    pr_number = Column(Integer, nullable=True)
    pr_url = Column(String(500), nullable=True)
    pr_branch = Column(String(255), nullable=True)
    base_branch = Column(String(255), default="main")
    
    # Status and progress
    status = Column(Enum(ValidationStatus), default=ValidationStatus.NOT_STARTED, index=True)
    current_step = Column(Integer, default=0)  # 0-6 for the 7 steps
    total_steps = Column(Integer, default=7)
    
    # Results and metrics
    overall_score = Column(Float, nullable=True)  # 0-100 overall validation score
    success_rate = Column(Float, nullable=True)  # Success rate of individual steps
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_context = Column(JSON, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Timing information
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Configuration
    config = Column(JSON, default=dict)  # Pipeline configuration
    environment_vars = Column(JSON, default=dict)  # Environment variables for validation
    
    # Results and logs
    results = Column(JSON, default=dict)  # Detailed results from each step
    logs = Column(JSON, default=list)  # Execution logs
    artifacts = Column(JSON, default=dict)  # Generated artifacts (screenshots, reports, etc.)
    
    # Auto-merge settings
    auto_merge_enabled = Column(Boolean, default=False)
    merge_threshold_score = Column(Float, default=80.0)  # Minimum score for auto-merge
    merge_completed = Column(Boolean, default=False)
    merge_url = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="validation_pipelines")
    agent_run = relationship("AgentRun", back_populates="validation_pipelines")
    steps = relationship("ValidationStep", back_populates="pipeline", cascade="all, delete-orphan", order_by="ValidationStep.step_index")
    
    def __repr__(self):
        return f"<ValidationPipeline(id={self.id}, project_id={self.project_id}, status='{self.status.value}')>"
    
    @property
    def is_running(self) -> bool:
        """Check if validation is currently running"""
        return self.status == ValidationStatus.RUNNING
    
    @property
    def is_completed(self) -> bool:
        """Check if validation is completed (success or failure)"""
        return self.status in [ValidationStatus.COMPLETED, ValidationStatus.FAILED, ValidationStatus.CANCELLED, ValidationStatus.TIMEOUT]
    
    @property
    def is_successful(self) -> bool:
        """Check if validation completed successfully"""
        return self.status == ValidationStatus.COMPLETED and self.overall_score and self.overall_score >= self.merge_threshold_score
    
    @property
    def progress_percentage(self) -> float:
        """Get validation progress as percentage"""
        if self.total_steps == 0:
            return 0.0
        return (self.current_step / self.total_steps) * 100
    
    @property
    def can_auto_merge(self) -> bool:
        """Check if pipeline can auto-merge"""
        return (
            self.auto_merge_enabled and 
            self.is_successful and 
            not self.merge_completed and
            self.pr_number is not None
        )
    
    def get_step_by_type(self, step_type: ValidationStepType) -> Optional["ValidationStep"]:
        """Get validation step by type"""
        for step in self.steps:
            if step.step_type == step_type:
                return step
        return None
    
    def get_current_step_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current step"""
        if self.current_step < len(self.steps):
            step = self.steps[self.current_step]
            return step.to_dict()
        return None
    
    def calculate_overall_score(self) -> float:
        """Calculate overall validation score based on step results"""
        if not self.steps:
            return 0.0
        
        total_score = 0.0
        completed_steps = 0
        
        for step in self.steps:
            if step.status == ValidationStatus.COMPLETED and step.score is not None:
                total_score += step.score
                completed_steps += 1
        
        if completed_steps == 0:
            return 0.0
        
        return total_score / completed_steps
    
    def update_progress(self, step_index: int, status: ValidationStatus, 
                       score: Optional[float] = None, error: Optional[str] = None) -> None:
        """Update pipeline progress"""
        self.current_step = step_index
        
        if status == ValidationStatus.COMPLETED:
            if step_index >= self.total_steps - 1:
                self.status = ValidationStatus.COMPLETED
                self.completed_at = func.now()
                if self.started_at:
                    duration = datetime.now() - self.started_at
                    self.duration_seconds = int(duration.total_seconds())
        elif status == ValidationStatus.FAILED:
            self.status = ValidationStatus.FAILED
            self.error_message = error
            self.completed_at = func.now()
        
        # Recalculate overall score
        self.overall_score = self.calculate_overall_score()
    
    def add_log(self, message: str, level: str = "INFO", step_index: Optional[int] = None) -> None:
        """Add log entry"""
        if not isinstance(self.logs, list):
            self.logs = []
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "step_index": step_index
        }
        self.logs.append(log_entry)
    
    def set_artifact(self, key: str, value: Any) -> None:
        """Set pipeline artifact"""
        if not isinstance(self.artifacts, dict):
            self.artifacts = {}
        self.artifacts[key] = value
    
    def get_artifact(self, key: str, default: Any = None) -> Any:
        """Get pipeline artifact"""
        if not isinstance(self.artifacts, dict):
            return default
        return self.artifacts.get(key, default)
    
    def to_dict(self, include_steps: bool = True, include_logs: bool = False) -> Dict[str, Any]:
        """Convert pipeline to dictionary for API responses"""
        data = {
            "id": self.id,
            "project_id": self.project_id,
            "agent_run_id": self.agent_run_id,
            "pr_number": self.pr_number,
            "pr_url": self.pr_url,
            "pr_branch": self.pr_branch,
            "base_branch": self.base_branch,
            "status": self.status.value,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "progress_percentage": self.progress_percentage,
            "overall_score": self.overall_score,
            "success_rate": self.success_rate,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "auto_merge_enabled": self.auto_merge_enabled,
            "merge_threshold_score": self.merge_threshold_score,
            "merge_completed": self.merge_completed,
            "merge_url": self.merge_url,
            "can_auto_merge": self.can_auto_merge,
            "is_running": self.is_running,
            "is_completed": self.is_completed,
            "is_successful": self.is_successful,
            "config": self.config,
            "results": self.results,
            "artifacts": self.artifacts,
            "duration_seconds": self.duration_seconds,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_steps:
            data["steps"] = [step.to_dict() for step in self.steps]
        
        if include_logs:
            data["logs"] = self.logs
        
        return data


class ValidationStep(Base):
    __tablename__ = "validation_steps"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key
    pipeline_id = Column(Integer, ForeignKey("validation_pipelines.id"), nullable=False, index=True)
    
    # Step information
    step_index = Column(Integer, nullable=False)  # 0-6 for the 7 steps
    step_type = Column(Enum(ValidationStepType), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Status and results
    status = Column(Enum(ValidationStatus), default=ValidationStatus.NOT_STARTED, index=True)
    score = Column(Float, nullable=True)  # 0-100 score for this step
    
    # Execution details
    command = Column(Text, nullable=True)  # Command executed
    output = Column(Text, nullable=True)  # Command output
    error_output = Column(Text, nullable=True)  # Error output
    exit_code = Column(Integer, nullable=True)  # Exit code
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Configuration and results
    config = Column(JSON, default=dict)  # Step-specific configuration
    results = Column(JSON, default=dict)  # Detailed results
    artifacts = Column(JSON, default=dict)  # Step artifacts
    
    # Retry information
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    pipeline = relationship("ValidationPipeline", back_populates="steps")
    
    def __repr__(self):
        return f"<ValidationStep(id={self.id}, step_type='{self.step_type.value}', status='{self.status.value}')>"
    
    @property
    def is_completed(self) -> bool:
        """Check if step is completed"""
        return self.status in [ValidationStatus.COMPLETED, ValidationStatus.FAILED, ValidationStatus.CANCELLED, ValidationStatus.TIMEOUT]
    
    @property
    def is_successful(self) -> bool:
        """Check if step completed successfully"""
        return self.status == ValidationStatus.COMPLETED
    
    @property
    def can_retry(self) -> bool:
        """Check if step can be retried"""
        return self.retry_count < self.max_retries and self.status == ValidationStatus.FAILED
    
    def start_execution(self) -> None:
        """Mark step as started"""
        self.status = ValidationStatus.RUNNING
        self.started_at = func.now()
    
    def complete_execution(self, success: bool, score: Optional[float] = None, 
                          output: Optional[str] = None, error: Optional[str] = None,
                          exit_code: Optional[int] = None) -> None:
        """Mark step as completed"""
        self.status = ValidationStatus.COMPLETED if success else ValidationStatus.FAILED
        self.completed_at = func.now()
        self.score = score
        
        if output:
            self.output = output
        if error:
            self.error_output = error
        if exit_code is not None:
            self.exit_code = exit_code
        
        # Calculate duration
        if self.started_at:
            duration = datetime.now() - self.started_at
            self.duration_seconds = int(duration.total_seconds())
    
    def set_result(self, key: str, value: Any) -> None:
        """Set step result"""
        if not isinstance(self.results, dict):
            self.results = {}
        self.results[key] = value
    
    def get_result(self, key: str, default: Any = None) -> Any:
        """Get step result"""
        if not isinstance(self.results, dict):
            return default
        return self.results.get(key, default)
    
    def set_artifact(self, key: str, value: Any) -> None:
        """Set step artifact"""
        if not isinstance(self.artifacts, dict):
            self.artifacts = {}
        self.artifacts[key] = value
    
    def get_artifact(self, key: str, default: Any = None) -> Any:
        """Get step artifact"""
        if not isinstance(self.artifacts, dict):
            return default
        return self.artifacts.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary for API responses"""
        return {
            "id": self.id,
            "pipeline_id": self.pipeline_id,
            "step_index": self.step_index,
            "step_type": self.step_type.value,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "score": self.score,
            "command": self.command,
            "output": self.output,
            "error_output": self.error_output,
            "exit_code": self.exit_code,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "can_retry": self.can_retry,
            "is_completed": self.is_completed,
            "is_successful": self.is_successful,
            "config": self.config,
            "results": self.results,
            "artifacts": self.artifacts,
            "duration_seconds": self.duration_seconds,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def create_default_steps(cls, pipeline_id: int) -> List["ValidationStep"]:
        """Create the default 7 validation steps"""
        steps = [
            cls(
                pipeline_id=pipeline_id,
                step_index=0,
                step_type=ValidationStepType.SNAPSHOT_CREATION,
                name="Snapshot Creation",
                description="Create sandbox environment with grainchain + web-eval-agent + graph-sitter"
            ),
            cls(
                pipeline_id=pipeline_id,
                step_index=1,
                step_type=ValidationStepType.CODE_CLONE,
                name="Code Clone",
                description="Clone PR branch to sandbox environment"
            ),
            cls(
                pipeline_id=pipeline_id,
                step_index=2,
                step_type=ValidationStepType.CODE_ANALYSIS,
                name="Code Analysis",
                description="Analyze code quality using graph-sitter"
            ),
            cls(
                pipeline_id=pipeline_id,
                step_index=3,
                step_type=ValidationStepType.DEPLOYMENT,
                name="Deployment",
                description="Execute setup commands and deploy application"
            ),
            cls(
                pipeline_id=pipeline_id,
                step_index=4,
                step_type=ValidationStepType.DEPLOYMENT_VALIDATION,
                name="Deployment Validation",
                description="Validate deployment success using Gemini API"
            ),
            cls(
                pipeline_id=pipeline_id,
                step_index=5,
                step_type=ValidationStepType.UI_TESTING,
                name="UI Testing",
                description="Run comprehensive UI tests with web-eval-agent"
            ),
            cls(
                pipeline_id=pipeline_id,
                step_index=6,
                step_type=ValidationStepType.AUTO_MERGE,
                name="Auto-merge",
                description="Merge PR if validation passes and auto-merge is enabled"
            )
        ]
        return steps

