"""
Validation pipeline related database models
"""
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, Text, Boolean, JSON, ForeignKey, Integer, Enum, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from .base import BaseModel


class ValidationStatus(enum.Enum):
    """Validation run status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ValidationStepType(enum.Enum):
    """Validation step types for the 7-step pipeline"""
    SNAPSHOT_CREATION = "snapshot_creation"
    CODE_CLONE = "code_clone"
    CODE_ANALYSIS = "code_analysis"
    DEPLOYMENT = "deployment"
    DEPLOYMENT_VALIDATION = "deployment_validation"
    UI_TESTING = "ui_testing"
    AUTO_MERGE = "auto_merge"


class ValidationStepStatus(enum.Enum):
    """Individual validation step status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ValidationRun(BaseModel):
    """Validation run model representing a complete 7-step validation pipeline"""
    __tablename__ = "validation_runs"
    
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    agent_run_id = Column(UUID(as_uuid=True), ForeignKey("agent_runs.id"), nullable=True)  # Optional link to agent run
    
    # PR information
    pr_url = Column(String(500), nullable=False)
    pr_number = Column(Integer, nullable=False)
    pr_branch = Column(String(255), nullable=False)
    pr_commit_sha = Column(String(255), nullable=False)
    
    # Validation configuration
    validation_config = Column(JSON, default=dict)  # Configuration for this validation run
    
    # Overall status and progress
    status = Column(Enum(ValidationStatus), default=ValidationStatus.PENDING, nullable=False, index=True)
    current_step_index = Column(Integer, default=0)
    progress_percentage = Column(Integer, default=0)
    
    # Timing information
    started_at = Column(String(50))  # ISO timestamp as string
    completed_at = Column(String(50))  # ISO timestamp as string
    duration_seconds = Column(Integer)
    
    # Results and scoring
    overall_score = Column(Float)  # Overall confidence score (0-100)
    passed_steps = Column(Integer, default=0)
    failed_steps = Column(Integer, default=0)
    skipped_steps = Column(Integer, default=0)
    
    # Auto-merge decision
    auto_merge_eligible = Column(Boolean, default=False, nullable=False)
    auto_merge_executed = Column(Boolean, default=False, nullable=False)
    auto_merge_reason = Column(Text)
    
    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # External service IDs
    grainchain_snapshot_id = Column(String(255))
    web_eval_session_id = Column(String(255))
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    # Relationships
    project = relationship("Project", back_populates="validation_runs")
    agent_run = relationship("AgentRun", back_populates="validation_runs")
    steps = relationship("ValidationStep", back_populates="validation_run", cascade="all, delete-orphan", order_by="ValidationStep.step_index")
    results = relationship("ValidationResult", back_populates="validation_run", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<ValidationRun(id={self.id}, pr_number={self.pr_number}, status={self.status.value})>"
    
    @property
    def is_active(self) -> bool:
        """Check if validation run is currently active"""
        return self.status in [ValidationStatus.PENDING, ValidationStatus.RUNNING]
    
    @property
    def is_completed(self) -> bool:
        """Check if validation run is completed"""
        return self.status in [ValidationStatus.COMPLETED, ValidationStatus.FAILED, ValidationStatus.CANCELLED]
    
    def get_step(self, step_type: ValidationStepType) -> Optional["ValidationStep"]:
        """Get specific validation step by type"""
        for step in self.steps:
            if step.step_type == step_type:
                return step
        return None
    
    def get_current_step(self) -> Optional["ValidationStep"]:
        """Get the currently executing step"""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None
    
    def calculate_overall_score(self) -> float:
        """Calculate overall confidence score based on step results"""
        if not self.steps:
            return 0.0
        
        total_weight = 0
        weighted_score = 0
        
        for step in self.steps:
            if step.status == ValidationStepStatus.COMPLETED and step.confidence_score is not None:
                weight = step.weight or 1.0
                total_weight += weight
                weighted_score += step.confidence_score * weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.0


class ValidationStep(BaseModel):
    """Individual step in the validation pipeline"""
    __tablename__ = "validation_steps"
    
    validation_run_id = Column(UUID(as_uuid=True), ForeignKey("validation_runs.id"), nullable=False)
    
    # Step identification
    step_index = Column(Integer, nullable=False)  # 0-6 for the 7 steps
    step_type = Column(Enum(ValidationStepType), nullable=False)
    step_name = Column(String(255), nullable=False)
    step_description = Column(Text)
    
    # Step execution
    status = Column(Enum(ValidationStepStatus), default=ValidationStepStatus.PENDING, nullable=False)
    started_at = Column(String(50))  # ISO timestamp as string
    completed_at = Column(String(50))  # ISO timestamp as string
    duration_seconds = Column(Integer)
    
    # Step configuration and inputs
    step_config = Column(JSON, default=dict)
    input_data = Column(JSON, default=dict)
    
    # Step results and outputs
    output_data = Column(JSON, default=dict)
    logs = Column(Text)
    error_message = Column(Text)
    
    # Scoring and validation
    confidence_score = Column(Float)  # 0-100 confidence score for this step
    weight = Column(Float, default=1.0)  # Weight for overall score calculation
    is_critical = Column(Boolean, default=False, nullable=False)  # If true, failure blocks auto-merge
    
    # Retry handling
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # External service references
    external_service_id = Column(String(255))  # ID from external service (grainchain, web-eval, etc.)
    external_service_url = Column(String(500))  # URL to external service results
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    # Relationships
    validation_run = relationship("ValidationRun", back_populates="steps")
    
    def __repr__(self) -> str:
        return f"<ValidationStep(validation_run_id={self.validation_run_id}, step={self.step_index}, type={self.step_type.value})>"
    
    @property
    def is_completed(self) -> bool:
        """Check if step is completed (success or failure)"""
        return self.status in [ValidationStepStatus.COMPLETED, ValidationStepStatus.FAILED, ValidationStepStatus.SKIPPED]
    
    @property
    def is_successful(self) -> bool:
        """Check if step completed successfully"""
        return self.status == ValidationStepStatus.COMPLETED


class ValidationResult(BaseModel):
    """Aggregated results and artifacts from validation runs"""
    __tablename__ = "validation_results"
    
    validation_run_id = Column(UUID(as_uuid=True), ForeignKey("validation_runs.id"), nullable=False)
    
    # Result identification
    result_type = Column(String(100), nullable=False)  # code_analysis, deployment_logs, ui_test_report, etc.
    result_name = Column(String(255), nullable=False)
    
    # Result content
    result_data = Column(JSON, default=dict)
    result_summary = Column(Text)
    
    # Result metadata
    file_path = Column(String(500))  # Path to result file if stored separately
    file_size_bytes = Column(Integer)
    mime_type = Column(String(100))
    
    # Result scoring
    confidence_score = Column(Float)
    severity_level = Column(String(50))  # info, warning, error, critical
    
    # Categorization
    tags = Column(JSON, default=list)  # List of tags for categorization
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    # Relationships
    validation_run = relationship("ValidationRun", back_populates="results")
    
    def __repr__(self) -> str:
        return f"<ValidationResult(validation_run_id={self.validation_run_id}, type={self.result_type}, name={self.result_name})>"

